import logging
import time
import json
from django.utils import timezone
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from .api_calls import call_ai_api

logger = logging.getLogger(__name__)

def generate_ai_suggestion(email_id: int, triggering_user_id: int = None):
    """Generiert KI-Vorschläge für eine E-Mail und sendet eine WS-Benachrichtigung,
       basierend auf einem dynamischen Prompt Template.

    Args:
        email_id: Die ID der E-Mail.
        triggering_user_id: Die ID des Benutzers, der die Aktion ausgelöst hat.
    """
    from mailmind.core.models import Email, AISuggestion
    from ..prompt_templates.utils import get_prompt_details

    logger.info(f"--- START: generate_ai_suggestion for Email ID {email_id} (triggered by User ID: {triggering_user_id}) ---")
    start_time = time.time()
    email = None # Initialize email
    suggestions_saved_successfully = False
    newly_created_suggestion_ids = []

    try:
        email = Email.objects.select_related('account', 'account__user').prefetch_related('to_contacts', 'cc_contacts').get(id=email_id)
        user = email.account.user
        if not user:
            logger.error(f"[TASK] User not found for EmailAccount {email.account.id} (Email ID: {email.id}). Aborting suggestion generation.")
            return # Cannot proceed without a user

        logger.info(f"[TASK] Starting AI suggestion generation for Email ID {email.id} (User: {user.id}) ...")

        # 1. Get Prompt Template Details
        logger.info(f"[TASK Step 1/5] Fetching prompt template details for 'generate_suggestions'")
        prompt_details = get_prompt_details('generate_suggestions')
        if not prompt_details:
            logger.error(f"[TASK] Could not find active prompt template 'generate_suggestions'. Aborting.")
            # Mark as failed? Or just return?
            email.ai_processed = False # Mark as not processed
            email.save(update_fields=['ai_processed', 'updated_at'])
            return
        logger.info(f"[TASK] Using Provider: {prompt_details['provider']}, Model: {prompt_details['model_name']}")

        # 2. Perform RAG search (TODO - Placeholder)
        logger.info(f"[TASK Step 2/5] RAG search for Email {email.id} (TODO)")
        rag_context = "" # Placeholder
        intent = "" # Placeholder for intent detection

        # 3. Format the Prompt Template
        logger.info(f"[TASK Step 3/5] Formatting prompt for Email {email.id}")
        prompt_context = {
            'email': email,
            'to_addresses': list(email.to_contacts.values_list('email', flat=True)),
            'cc_addresses': list(email.cc_contacts.values_list('email', flat=True)),
            'rag_context': rag_context if rag_context else 'Kein zusätzlicher Kontext verfügbar.',
            'intent': intent if intent else 'Kein Intent erkannt.'
            # Add any other variables the prompt template might need
        }
        try:
            formatted_prompt = prompt_details['template'].format(**prompt_context)
        except KeyError as e_format:
            logger.error(f"[TASK] Missing variable in prompt template 'generate_suggestions': {e_format}. Context provided: {list(prompt_context.keys())}", exc_info=True)
            email.ai_processed = False
            email.save(update_fields=['ai_processed', 'updated_at'])
            return
        except Exception as e_format_general:
             logger.error(f"[TASK] Error formatting prompt template 'generate_suggestions': {e_format_general}", exc_info=True)
             email.ai_processed = False
             email.save(update_fields=['ai_processed', 'updated_at'])
             return

        logger.debug(f"Formatted prompt for {prompt_details['provider']} API (Email ID {email.id}):\n{formatted_prompt}")

        # 4. Call AI API (using the generic function)
        logger.info(f"[TASK Step 4/5] Calling {prompt_details['provider']} API for Email ID {email.id}")
        ai_response_str = call_ai_api(
            prompt=formatted_prompt,
            user=user,
            provider=prompt_details['provider'],
            model_name=prompt_details['model_name']
        )

        # 5. Parse response and save suggestions
        logger.info(f"[TASK Step 5/5] Processing {prompt_details['provider']} response and saving suggestions for Email {email.id}")
        suggestions_saved_count = 0
        processing_start_time = time.time()
        ai_response_data = {}

        try:
            # Attempt to parse potential JSON string
            try:
                # Basic cleaning for markdown code blocks
                if ai_response_str.strip().startswith('```json'):
                     ai_response_str_cleaned = ai_response_str.strip()[7:-3].strip()
                elif ai_response_str.strip().startswith('```'):
                     ai_response_str_cleaned = ai_response_str.strip()[3:-3].strip()
                else:
                    ai_response_str_cleaned = ai_response_str

                ai_response_data = json.loads(ai_response_str_cleaned)

            except json.JSONDecodeError:
                 # If it's not JSON, treat the whole string as potential error message or direct text?
                 # For this specific prompt, we expect JSON.
                 logger.error(f"[TASK] Failed to parse JSON response from {prompt_details['provider']} for Email {email.id}. Response: {ai_response_str}", exc_info=True)
                 ai_response_data = {"error": "Invalid JSON response received from AI."} # Simulate error structure

            # Check for error key within the parsed data or if parsing failed
            if "error" in ai_response_data:
                 logger.error(f"[TASK] Error received from {prompt_details['provider']} API for Email {email.id}: {ai_response_data['error']}")
                 email.ai_processed = False
            elif 'suggestions' in ai_response_data and isinstance(ai_response_data['suggestions'], list):
                suggestions_data = ai_response_data['suggestions'][:3] # Limit to 3
                logger.info(f"[TASK] Received suggestions list for email {email.id}: {len(suggestions_data)} items")

                for suggestion_data in suggestions_data:
                    if isinstance(suggestion_data, dict) and \
                       'intent_summary' in suggestion_data and \
                       'subject' in suggestion_data and \
                       'reply_text' in suggestion_data:

                        intent = suggestion_data.get('intent_summary', '').strip()
                        subject = suggestion_data.get('subject', '').strip()
                        content = suggestion_data.get('reply_text', '').strip()

                        if not content:
                             logger.warning(f"[TASK] Skipping suggestion for email {email.id} because reply_text is empty.")
                             continue

                        suggestion_processing_time = time.time() - processing_start_time
                        # Use intent as title, fallback to snippet
                        title = intent if intent else (content[:80] + '...' if len(content) > 80 else content)

                        new_suggestion = AISuggestion.objects.create(
                            email=email,
                            type='reply',
                            title=title,
                            content=content,
                            intent_summary=intent,
                            suggested_subject=subject,
                            processing_time=suggestion_processing_time,
                            # Store which prompt generated this
                            source_prompt_name='generate_suggestions'
                        )
                        newly_created_suggestion_ids.append(new_suggestion.id)
                        logger.info(f"[TASK] Created suggestion {new_suggestion.id} for email {email.id} using '{prompt_details['provider']}/{prompt_details['model_name']}'")
                        suggestions_saved_count += 1
                    else:
                        logger.warning(f"[TASK] Invalid suggestion format from {prompt_details['provider']} skipped for Email {email.id}: {suggestion_data}")

                if suggestions_saved_count > 0:
                    suggestions_saved_successfully = True
                    logger.info(f"[TASK] {suggestions_saved_count} suggestions saved for Email ID {email.id}.")
                else:
                    logger.error(f"[TASK] No valid suggestions saved from {prompt_details['provider']} response for Email {email.id}.")
                    email.ai_processed = False # Mark as failed if no suggestions saved
            else:
                 logger.error(f"[TASK] Unexpected format in {prompt_details['provider']} response for Email {email.id}: Missing 'suggestions' list. Response: {ai_response_str}")
                 email.ai_processed = False

        except Exception as e_parse:
            logger.error(f"[TASK] Unexpected error during response processing/saving for Email {email.id}: {e_parse}", exc_info=True)
            email.ai_processed = False # Mark as failed on unexpected error

        # Mark email as processed ONLY if suggestions were successfully saved
        if suggestions_saved_successfully:
            email.ai_processed = True
            email.ai_processed_at = timezone.now()
            update_fields = ['updated_at']
            update_fields.extend(['ai_processed', 'ai_processed_at'])
            logger.info(f"[TASK] Email ID {email.id} marked as AI-processed.")
        else:
            # Ensure ai_processed is False if we failed somewhere
            email.ai_processed = False
            update_fields = ['ai_processed']
            # Do not update ai_processed_at if it failed
            if 'ai_processed_at' in update_fields:
                update_fields.remove('ai_processed_at')

        # Save email updates (summaries, processed status)
        if len(update_fields) > 1: # Only save if more than just updated_at changed
            email.save(update_fields=list(set(update_fields))) # Use set to avoid duplicates
            logger.debug(f"[TASK] Saved final status and summaries for email {email.id} (processed: {email.ai_processed})")

    except Email.DoesNotExist:
        logger.error(f"[TASK] Email with ID {email_id} not found for suggestion generation.")
    except Exception as e_outer:
        logger.error(f"[TASK] Outer unexpected error in generate_ai_suggestion for ID {email_id}: {e_outer}", exc_info=True)
        # Try to mark as unprocessed if email object exists
        try:
            if email and not suggestions_saved_successfully:
                email.ai_processed = False
                email.save(update_fields=['ai_processed', 'updated_at'])
        except Exception as e_save_fail:
            logger.error(f"[TASK] Error saving failure status for Email ID {email_id}: {e_save_fail}")

    # --- Send WebSocket Signal --- (Only if successful)
    finally:
        if suggestions_saved_successfully and email:
            try:
                from mailmind.api.serializers import AISuggestionSerializer
                channel_layer = get_channel_layer()
                if channel_layer:
                    if triggering_user_id is None:
                        logger.error(f"[TASK] Triggering User ID is None for email {email.id}. Cannot determine target group. Skipping WS send.")
                        return # Changed from continue to return

                    target_user_id = triggering_user_id
                    group_name = f'user_{target_user_id}_events'

                    serialized_suggestions = []
                    try:
                        # Ensure AISuggestion is imported here if not globally
                        from mailmind.core.models import AISuggestion
                        new_suggestions = AISuggestion.objects.filter(id__in=newly_created_suggestion_ids).order_by('created_at')
                        serializer = AISuggestionSerializer(new_suggestions, many=True)
                        serialized_suggestions = serializer.data
                        logger.info(f"[TASK] Serialized {len(serialized_suggestions)} new suggestions for WS message.")
                    except Exception as ser_err:
                        logger.error(f"[TASK] Error serializing new suggestions for WS message (Email: {email.id}): {ser_err}", exc_info=True)

                    message_data = {
                        'type': 'suggestion_generation_complete',
                        'data': {
                            'email_id': email.id,
                            'suggestions': serialized_suggestions,
                            'ai_processed': email.ai_processed,
                            'ai_processed_at': email.ai_processed_at.isoformat() if email.ai_processed_at else None
                        }
                    }
                    logger.info(f"[TASK] Data being sent via group_send: {repr(message_data)}")
                    logger.info(f"[TASK] Sending message to group {group_name} for email {email.id}")

                    async_to_sync(channel_layer.group_send)(group_name, message_data)
                    logger.info(f"[TASK] Message sent successfully to {group_name}.")

                else:
                    logger.error("[TASK] Channel layer is None. Cannot send WebSocket notification.")
            except Exception as ws_err:
                logger.error(f"[TASK] Error sending WebSocket notification for email {email.id}: {ws_err}", exc_info=True)

        end_time = time.time()
        total_time = end_time - start_time
        logger.info(f"--- END: generate_ai_suggestion for Email ID {email_id} completed in {total_time:.2f} seconds (Success: {suggestions_saved_successfully}) ---") 