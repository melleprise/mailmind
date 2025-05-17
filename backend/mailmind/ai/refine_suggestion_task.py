import logging
import json
# from .clients import get_gemini_model # Replaced
from .api_calls import call_ai_api
# from ..prompt_templates.utils import get_prompt_details # Moved inside
from mailmind.core.models import AISuggestion, User # Added AISuggestion
# Import get_user_model
from django.contrib.auth import get_user_model
# Import async_to_sync
from asgiref.sync import async_to_sync, sync_to_async # Import sync_to_async
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

# Updated signature: Accept user_id instead of user object
async def refine_suggestion_task(suggestion_id: str, custom_prompt: str, user_id: int):
    """
    Task to refine BOTH subject and body of an AISuggestion based on a custom prompt.
    Fetches the suggestion, calls the AI with the new 'refine_suggestion' template,
    parses the JSON response, and updates the suggestion object.
    """
    from ..prompt_templates.utils import get_prompt_details # Moved here

    # Fetch User object from user_id using sync_to_async
    UserModel = get_user_model()
    try:
        user = await sync_to_async(UserModel.objects.get)(pk=user_id)
    except UserModel.DoesNotExist:
        logger.error(f"refine_suggestion_task: User with id {user_id} not found.")
        return
    except Exception as e_user:
        logger.error(f"refine_suggestion_task: Error fetching user {user_id}: {e_user}", exc_info=True)
        return

    if not suggestion_id or not custom_prompt:
        logger.error("refine_suggestion_task: Missing suggestion_id or custom_prompt.")
        return

    try:
        # 1. Fetch the suggestion object using sync_to_async
        try:
            # Wrap the synchronous DB call
            get_suggestion = sync_to_async(AISuggestion.objects.get)
            suggestion = await get_suggestion(id=suggestion_id, email__account__user=user)
        except AISuggestion.DoesNotExist:
            logger.error(f"AISuggestion with id {suggestion_id} not found for user {user.id}.")
            return
        except Exception as e_fetch:
            logger.error(f"Error fetching AISuggestion {suggestion_id}: {e_fetch}", exc_info=True)
            return

        original_subject = suggestion.suggested_subject
        original_body = suggestion.content

        # 2. Get prompt details
        prompt_details = await get_prompt_details('refine_suggestion')
        if not prompt_details:
            logger.error("Could not find active prompt template 'refine_suggestion'.")
            return
        logger.info(f"Using Provider: {prompt_details['provider']}, Model: {prompt_details['model_name']} for suggestion refinement")

        # 3. Format prompt (using new variables)
        prompt_context = {
            'original_subject': original_subject,
            'original_body': original_body,
            'custom_prompt': custom_prompt,
        }
        try:
            formatted_prompt = prompt_details['prompt'].format(**prompt_context)
        except KeyError as e:
            logger.error(f"Missing variable in prompt template 'refine_suggestion': {e}", exc_info=True)
            return
        except Exception as e_format:
            logger.error(f"Error formatting prompt template 'refine_suggestion': {e_format}", exc_info=True)
            return

        # 4. Call generic AI API function
        logger.info(f"Sending subject/body for refinement to {prompt_details['provider']} API.")
        response_str = await call_ai_api(
            prompt=formatted_prompt,
            user=user,
            provider=prompt_details['provider'],
            model_name=prompt_details['model_name']
        )

        # 5. Process JSON response
        if response_str is None:
            logger.error(f"AI API call failed during refinement (returned None).")
            return
        
        try:
            # Attempt to parse the JSON response
            refined_data = json.loads(response_str)
            refined_subject = refined_data.get('refined_subject')
            refined_body = refined_data.get('refined_body')

            if refined_subject is None or refined_body is None:
                logger.error(f"AI response JSON missing required keys ('refined_subject' or 'refined_body'). Response: {response_str}")
                return

            # 6. Update the suggestion object using sync_to_async
            suggestion.suggested_subject = refined_subject
            suggestion.content = refined_body
            # Wrap the synchronous save call
            save_suggestion = sync_to_async(suggestion.save)
            await save_suggestion()
            logger.info(f"Successfully refined and updated suggestion {suggestion_id}.")

        except json.JSONDecodeError as e_json:
            logger.error(f"Failed to decode AI JSON response during refinement: {e_json}. Response: {response_str}", exc_info=True)
        except Exception as e_update:
            logger.error(f"Error updating suggestion {suggestion_id} after refinement: {e_update}", exc_info=True)

    except Exception as e:
        logger.error(f"General error in refine_suggestion_task for {suggestion_id}: {e}", exc_info=True)

# NEW Synchronous wrapper function
def refine_suggestion_task_sync_wrapper(suggestion_id: str, custom_prompt: str, user_id: int):
    """Synchronous wrapper to call the async refine_suggestion_task."""
    logger.info(f"Sync wrapper called for suggestion {suggestion_id}, user {user_id}")
    try:
        # Use async_to_sync to run the async task from this sync context
        async_to_sync(refine_suggestion_task)(suggestion_id, custom_prompt, user_id)
        logger.info(f"Sync wrapper finished calling async task for suggestion {suggestion_id}")
    except Exception as e:
        logger.error(f"Error calling async task from sync wrapper for suggestion {suggestion_id}: {e}", exc_info=True)

# Keep the old function signature temporarily if needed elsewhere, or remove it.
# async def refine_suggestion_with_prompt(...) -> str | None:
#    ...

# Added user, field_name, subject_text parameters
async def refine_suggestion_with_prompt(text_to_refine: str, custom_prompt: str, user, field_name: str, subject_text: str | None) -> str | None:
    """
    Sends text and a custom prompt to the AI using the 'refine_suggestion' template.
    Includes subject context and specifies which field is being refined.
    Uses the generic call_ai_api function.
    Returns the refined text or None on error.
    """
    from mailmind.core.models import User # For type hint if needed
    from ..prompt_templates.utils import get_prompt_details # Moved here
    # user: User

    if not text_to_refine or not custom_prompt:
        logger.debug("refine_suggestion_with_prompt: Missing text or custom prompt.")
        return None # Return None as original text cannot be refined meaningfully
    
    if field_name not in ['subject', 'body']:
        logger.error(f"refine_suggestion_with_prompt: Invalid field_name '{field_name}'.")
        return None

    if not user:
        logger.error("refine_suggestion_with_prompt: User object is required for API call.")
        return None

    try:
        # 1. Get prompt details (Await the async call)
        prompt_details = await get_prompt_details('refine_suggestion')
        if not prompt_details:
            logger.error("Could not find active prompt template 'refine_suggestion'.")
            return None
        logger.info(f"Using Provider: {prompt_details['provider']}, Model: {prompt_details['model_name']} for suggestion refinement")

        # 2. Format prompt
        # The template now expects 'text_to_refine', 'custom_prompt', 'field_name', 'subject_text'
        prompt_context = {
            'text_to_refine': text_to_refine,
            'custom_prompt': custom_prompt,
            'field_name': field_name,
            'subject_text': subject_text or "(Kein Betreff vorhanden)" # Provide fallback text
        }
        try:
            formatted_prompt = prompt_details['prompt'].format(**prompt_context)
        except KeyError as e:
            logger.error(f"Missing variable in prompt template 'refine_suggestion': {e}", exc_info=True)
            return None
        except Exception as e_format:
            logger.error(f"Error formatting prompt template 'refine_suggestion': {e_format}", exc_info=True)
            return None

        # 3. Call generic AI API function
        # Note sync/async issue mentioned in correct_text_task
        logger.info(f"Sending text for refinement to {prompt_details['provider']} API: '{text_to_refine[:50]}...'")
        response_str = await call_ai_api(
            prompt=formatted_prompt,
            user=user,
            provider=prompt_details['provider'],
            model_name=prompt_details['model_name']
        )

        # 4. Process response
        if response_str is None:
            # call_ai_api likely returns None on error
            logger.error(f"AI API call failed during refinement (returned None).")
            return None
        elif isinstance(response_str, str) and response_str.strip():
            # Success - we got a non-empty string
            refined_text = response_str.strip().strip('"`') # Basic cleaning
            logger.info(f"Refined text received: '{refined_text[:50]}...'")
            return refined_text
        else:
            # Unexpected response (e.g., empty string, or maybe error object not handled by call_ai_api)
            logger.warning(f"Unexpected or empty response from AI API during refinement: {response_str}")
            return None # Treat unexpected responses as failure

    except Exception as e:
        logger.error(f"Error in refine_suggestion_with_prompt: {e}", exc_info=True)
        return None 