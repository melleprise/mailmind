import logging
import time
import json
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache

from mailmind.core.models import Email, User
from mailmind.prompt_templates.utils import get_prompt_details
from .api_calls import call_ai_api

# WebSocket related imports
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from knowledge.models import KnowledgeField

logger = logging.getLogger(__name__)

# Lock timeout (in seconds) - how long to wait before allowing another task for the same email
SUMMARY_GENERATION_LOCK_TIMEOUT = 5 * 60 # 5 minutes

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_summary_task(self, email_id: int, triggering_user_id: int | None = None):
    """
    Generiert Short und Medium Summaries für eine E-Mail mithilfe einer AI-API
    und sendet eine WebSocket-Benachrichtigung.
    Verwendet einen Lock, um doppelte Ausführungen zu verhindern.
    Nutzt den 'generate_suggestions' Prompt, extrahiert aber nur Summary-Daten.
    """
    start_time = time.time()
    cache_key = f"lock_summary_generation_email_{email_id}"
    processed_successfully = False

    # --- Task Lock ---
    if not cache.add(cache_key, "locked", timeout=SUMMARY_GENERATION_LOCK_TIMEOUT):
        logger.warning(f"[TASK_SUMMARY] Summary generation for email {email_id} is already running or locked. Skipping.")
        # Optional: Retry logic if skipping isn't desired
        # try:
        #     self.retry(countdown=10) # Retry in 10 seconds
        # except MaxRetriesExceededError:
        #     logger.error(f"[TASK_SUMMARY] Max retries exceeded for summary generation lock on email {email_id}.")
        return f"Skipped: Summary generation for email {email_id} locked."
    logger.info(f"--- START: generate_summary_task for Email ID {email_id} (Triggered by User: {triggering_user_id}) ---")

    try:
        # --- Fetch Email and User ---
        try:
            email = Email.objects.select_related('account', 'account__user').get(id=email_id)
            user = email.account.user
            if not user:
                logger.error(f"[TASK_SUMMARY] User not found for EmailAccount {email.account.id} (Email ID: {email.id}). Aborting summary generation.")
                cache.delete(cache_key)
                return # Cannot proceed without a user
        except Email.DoesNotExist:
            logger.error(f"[TASK_SUMMARY] Email with ID {email_id} not found.")
            cache.delete(cache_key)
            return
        except Exception as e_fetch:
             logger.error(f"[TASK_SUMMARY] Error fetching email {email_id}: {e_fetch}", exc_info=True)
             cache.delete(cache_key)
             return

        # --- Get Prompt Details ---
        logger.info(f"[TASK_SUMMARY Step 1/4] Fetching prompt template details for 'generate_suggestions'")
        prompt_details = get_prompt_details('generate_suggestions') # Use the combined prompt for now
        if not prompt_details:
            logger.error(f"[TASK_SUMMARY] Could not find active prompt template 'generate_suggestions'. Aborting.")
            cache.delete(cache_key)
            return
        logger.info(f"[TASK_SUMMARY] Using Provider: {prompt_details['provider']}, Model: {prompt_details['model_name']}")

        # --- Format Prompt ---
        logger.info(f"[TASK_SUMMARY Step 2/4] Formatting prompt for Email {email.id}")
        # Basic context for summary generation
        prompt_context = {
            'email_from': email.from_address,
            'email_to': list(email.to_contacts.values_list('email', flat=True)),
            'email_cc': list(email.cc_contacts.values_list('email', flat=True)),
            'email_subject': email.subject,
            'email_received_at': email.received_at,
            'email_body': email.body_text if email.body_text else '(Kein Textinhalt vorhanden)',
            # Ensure all placeholders required by 'generate_suggestions' prompt are present, even if empty
            'rag_context': 'Kein zusätzlicher Kontext verfügbar (Nur Summary).',
            'intent': 'Kein Intent (Nur Summary).',
        }
        # KnowledgeFields übernehmen
        knowledge_context = {field.key: field.value for field in KnowledgeField.objects.filter(user=user)}
        prompt_context.update(knowledge_context)

        try:
            formatted_prompt = prompt_details['prompt'].format(**prompt_context)
        except KeyError as e_format:
            logger.error(f"[TASK_SUMMARY] Missing variable in prompt template 'generate_suggestions': {e_format}. Context provided: {list(prompt_context.keys())}", exc_info=True)
            cache.delete(cache_key)
            return
        except Exception as e_format_general:
             logger.error(f"[TASK_SUMMARY] Error formatting prompt template 'generate_suggestions': {e_format_general}", exc_info=True)
             cache.delete(cache_key)
             return

        # --- Call AI API ---
        logger.info(f"[TASK_SUMMARY Step 3/4] Calling {prompt_details['provider']} API for Email ID {email.id}")
        ai_response_str = call_ai_api(
            prompt=formatted_prompt,
            user=user,
            provider=prompt_details['provider'],
            model_name=prompt_details['model_name'],
            triggering_source=f"generate_summary_task_email_{email_id}" # Add source
        )

        # --- Process Response & Save Summaries ---
        logger.info(f"[TASK_SUMMARY Step 4/4] Processing {prompt_details['provider']} response for Email {email.id}")
        if not ai_response_str:
            logger.error(f"[TASK_SUMMARY] Received empty response from {prompt_details['provider']} API for Email {email.id}.")
            cache.delete(cache_key)
            return "Failed: Empty API response"

        ai_response_data = {}
        try:
            # Try parsing as JSON first
            ai_response_data = json.loads(ai_response_str)
            logger.debug(f"[TASK_SUMMARY] Parsed JSON response for Email {email.id}")
        except json.JSONDecodeError:
            logger.warning(f"[TASK_SUMMARY] Response for Email {email.id} is not valid JSON. Treating as plain text. Response: {ai_response_str[:200]}...")
            # Handle plain text if needed, or assume structure is required
            # For now, we assume the structure from 'generate_suggestions' is needed
            cache.delete(cache_key)
            return "Failed: Non-JSON response" # Or handle plain text if applicable

        # Check for error key within the parsed data
        if "error" in ai_response_data:
             logger.error(f"[TASK_SUMMARY] Error received from {prompt_details['provider']} API for Email {email.id}: {ai_response_data['error']}")
             cache.delete(cache_key)
             return f"Failed: API Error - {ai_response_data['error']}"

        # Extract Summaries
        short_summary = ai_response_data.get('short_summary', '').strip()
        medium_summary_raw = ai_response_data.get('medium_summary', '').strip()

        if not short_summary and not medium_summary_raw:
             logger.warning(f"[TASK_SUMMARY] No 'short_summary' or 'medium_summary' found in the response for Email {email.id}. Response keys: {list(ai_response_data.keys())}")
             # Decide if this is an error or acceptable
             cache.delete(cache_key)
             # Still send WS update below, even if empty? Or return failure?
             # Let's assume it's okay if summaries are empty, but log it.
             # return "Failed: No summaries found in response"

        update_fields = ['updated_at']
        email_updated = False

        if short_summary:
             # Optional: Check if summary already exists and is the same
             if email.short_summary != short_summary:
                 email.short_summary = short_summary
                 update_fields.append('short_summary')
                 logger.info(f"[TASK_SUMMARY] Extracted and updated short_summary for Email ID {email.id}: '{short_summary}'")
                 email_updated = True
             else:
                 logger.info(f"[TASK_SUMMARY] Existing short_summary is identical for Email ID {email.id}. Skipping update.")
        else:
             logger.info(f"[TASK_SUMMARY] No short_summary provided in response for Email ID {email.id}.")


        if medium_summary_raw:
            # Truncate medium_summary if needed
            max_len_medium = Email._meta.get_field('medium_summary').max_length
            medium_summary = medium_summary_raw
            if len(medium_summary_raw) > max_len_medium:
                medium_summary = medium_summary_raw[:max_len_medium - 5] + ' [... M]' # Truncate and add indicator
                logger.warning(f"[TASK_SUMMARY] Truncated medium_summary for email {email.id} from {len(medium_summary_raw)} to {len(medium_summary)} chars.")

            if email.medium_summary != medium_summary:
                email.medium_summary = medium_summary
                update_fields.append('medium_summary')
                logger.info(f"[TASK_SUMMARY] Extracted and updated medium_summary for Email ID {email.id}: '{medium_summary[:100]}...'")
                email_updated = True
            else:
                 logger.info(f"[TASK_SUMMARY] Existing medium_summary is identical for Email ID {email.id}. Skipping update.")
        else:
             logger.info(f"[TASK_SUMMARY] No medium_summary provided in response for Email ID {email.id}.")


        # Save email updates only if something changed
        if email_updated:
            try:
                # Use transaction.atomic for safety, though less critical here than with suggestions
                with transaction.atomic():
                    email.save(update_fields=list(set(update_fields)))
                logger.debug(f"[TASK_SUMMARY] Saved summaries for email {email.id}")
                processed_successfully = True # Mark as success only if saved
            except Exception as e_save:
                 logger.error(f"[TASK_SUMMARY] Error saving summaries for email {email.id}: {e_save}", exc_info=True)
                 processed_successfully = False # Mark as failed on save error
                 # Don't delete lock yet, allow potential retry
                 try:
                      self.retry(exc=e_save)
                 except MaxRetriesExceededError:
                      logger.error(f"[TASK_SUMMARY] Max retries exceeded after save failure for email {email_id}.")
                      # Now delete the lock as retries are exhausted
                      cache.delete(cache_key)
                 return f"Failed: DB Save Error - {e_save}"
        else:
             logger.info(f"[TASK_SUMMARY] No changes to summaries for email {email.id}. Nothing to save.")
             processed_successfully = True # Consider it success if no update was needed


    except Exception as e_outer:
        logger.error(f"[TASK_SUMMARY] Outer unexpected error in generate_summary_task for ID {email_id}: {e_outer}", exc_info=True)
        processed_successfully = False
        # Attempt retry for unexpected errors
        try:
            self.retry(exc=e_outer)
        except MaxRetriesExceededError:
            logger.error(f"[TASK_SUMMARY] Max retries exceeded after outer error for email {email_id}.")
            # Delete lock after exhausting retries
            cache.delete(cache_key)
        return f"Failed: Outer Exception - {e_outer}"

    finally:
        # --- Release Lock ---
        # Only delete the lock if the task wasn't retried or max retries were hit in error handling
        # Check if task is being retried
        is_retrying = self.request.retries < self.max_retries and not processed_successfully
        if not is_retrying:
             deleted = cache.delete(cache_key)
             logger.debug(f"[TASK_SUMMARY] Lock {cache_key} deleted: {deleted}")


        # --- WebSocket Notification (regardless of save success/failure, to update UI state) ---
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                group_name = f"user_{user.id}"

                # Fetch the latest state of the email for the notification
                try:
                    email.refresh_from_db(fields=['short_summary', 'medium_summary'])
                except Email.DoesNotExist:
                    logger.error(f"[TASK_SUMMARY] Email {email_id} not found when refreshing for WS send.")
                    # Cannot send update if email is gone
                except Exception as e_refresh:
                    logger.error(f"[TASK_SUMMARY] Error refreshing email {email_id} for WS send: {e_refresh}")
                    # Proceed without refresh? Or skip WS? Let's proceed cautiously.

                message_data = {
                    'type': 'summary_generation_complete', # New specific type
                    'data': {
                        'email_id': email.id,
                        'short_summary': email.short_summary,
                        'medium_summary': email.medium_summary,
                        # Add status if needed, e.g., 'success': processed_successfully
                    }
                }
                logger.info(f"[TASK_SUMMARY] Sending WS message to group {group_name} for email {email.id}. Data: {repr(message_data)}")
                async_to_sync(channel_layer.group_send)(group_name, message_data)
                logger.info(f"[TASK_SUMMARY] WS Message sent successfully to {group_name}.")

            else:
                logger.error("[TASK_SUMMARY] Channel layer is None. Cannot send WebSocket notification.")
        except Exception as ws_err:
            logger.error(f"[TASK_SUMMARY] Error sending WebSocket notification for email {email.id}: {ws_err}", exc_info=True)

        end_time = time.time()
        total_time = end_time - start_time
        logger.info(f"--- END: generate_summary_task for Email ID {email_id} completed in {total_time:.2f} seconds (Success: {processed_successfully}) ---")
        return f"Completed in {total_time:.2f}s (Success: {processed_successfully})" 