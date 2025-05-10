import logging
import json
# Move imports inside the function to delay loading
# import google.generativeai as genai # Now imported inside
# from google.api_core import exceptions as google_exceptions # Now imported inside
# from groq import Groq, APIError as GroqAPIError
# from .clients import get_groq_client
# from django.utils import timezone
# import time
# from mailmind.core.models import User, AIRequestLog, APICredential
# from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

# Make the function async
async def call_ai_api(prompt: str, user, provider: str, model_name: str, triggering_source: str = "unknown") -> str:
    """Generic function to call different AI provider APIs.
    Handles logging, API key retrieval, client instantiation, and basic error handling.
    Returns the AI response content as a string, or an error JSON string.
    """
    # Import necessary modules here
    import time
    from django.utils import timezone
    from asgiref.sync import sync_to_async
    from mailmind.core.models import User, AIRequestLog, APICredential # Moved model import here
    # Import provider specific libraries here to avoid loading everything always
    client = None
    model = None # Variable for Gemini model
    if provider == 'groq':
        from .clients import get_groq_client # Moved client import
        from groq import Groq, APIError as GroqAPIError # Moved Groq imports
    elif provider == 'google_gemini':
        try:
            import google.generativeai as genai
            from google.api_core import exceptions as google_exceptions
        except ImportError:
             logger.error("Google Generative AI library not installed. Cannot use google_gemini provider.")
             # Return error immediately if library is missing
             return json.dumps({"error": "Google Generative AI library not installed."})
    # Add other provider imports here if needed

    log_entry = None
    start_time = time.time()
    
    # Type hint user properly if possible (needs User model imported)
    typed_user: User = user

    # Create initial log entry (using sync_to_async)
    try:
        log_entry = await sync_to_async(AIRequestLog.objects.create)(
            user=typed_user,
            provider=provider,
            model_name=model_name,
            triggering_source=triggering_source,
            prompt_text=prompt, # Log the potentially long prompt
            is_success=False # Default to False
        )
        # Log prompt length for debugging context issues
        logger.debug(f"Created initial AIRequestLog entry {log_entry.id} for {provider}/{model_name}. Prompt length: {len(prompt)} chars.")
    except Exception as e_log_create:
        logger.error(f"Failed to create initial AIRequestLog: {e_log_create}", exc_info=True)

    # Get API Key by fetching the credential object first
    api_key = None
    credential = None
    try:
        credential = await sync_to_async(APICredential.objects.get)(user=typed_user, provider=provider)
        api_key = await sync_to_async(credential.get_api_key)()
        if not api_key:
             raise ValueError(f"API key for {provider} could not be retrieved or decrypted.")
    except APICredential.DoesNotExist:
        error_msg = f"API credential for {provider} not found for User {typed_user.id}."
        logger.error(error_msg)
        if log_entry:
            log_entry.is_success = False
            log_entry.error_message = error_msg
            log_entry.duration_ms = int((time.time() - start_time) * 1000)
            await sync_to_async(log_entry.save)()
        return json.dumps({"error": error_msg})
    except Exception as e_key:
        error_msg = f"Error retrieving API credential or key for {provider}, User {typed_user.id}: {e_key}"
        logger.error(error_msg, exc_info=True)
        if log_entry:
            log_entry.is_success = False
            log_entry.error_message = f"API Key Retrieval Error: {error_msg}"
            log_entry.duration_ms = int((time.time() - start_time) * 1000)
            await sync_to_async(log_entry.save)()
        return json.dumps({"error": f"Error retrieving API key: {e_key}"})

    # --- API Call Logic ---
    response = None
    response_content = None
    raw_response_str = None
    try:
        # --- Groq ---
        if provider == 'groq':
            client = get_groq_client(api_key=api_key)
            if not client:
                raise Exception(f"Failed to initialize Groq client.")

            logger.debug(f"Calling Groq client chat completions with model '{model_name}'")
            response = client.chat.completions.create(
                 messages=[{"role": "user", "content": prompt}],
                 model=model_name,
            )
            response_content = response.choices[0].message.content
            # Serialize raw Groq response
            try:
                raw_response_str = response.model_dump_json()
            except Exception as e_dump:
                logger.warning(f"Could not serialize raw Groq response object: {e_dump}")
                raw_response_str = repr(response)

        # --- Google Gemini ---
        elif provider == 'google_gemini':
            logger.debug(f"Configuring Google Gemini API key...")
            genai.configure(api_key=api_key)
            logger.debug(f"Instantiating Google Gemini model '{model_name}'")
            model = genai.GenerativeModel(model_name)

            # Safety settings example (adjust as needed)
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            # Generation config example (adjust as needed)
            generation_config = genai.types.GenerationConfig(
                # temperature=0.7, # Example setting
                # max_output_tokens=2048 # Example setting
            )

            logger.debug(f"Calling Google Gemini generate_content_async with model '{model_name}'")
            # Use generate_content_async as call_ai_api is async
            response = await model.generate_content_async(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
                )

            # Handle potential blocks or errors in response
            if not response.candidates:
                 block_reason = getattr(response, 'prompt_feedback', {}).get('block_reason', 'Unknown')
                 logger.warning(f"Google Gemini response blocked or empty. Reason: {block_reason}. Full feedback: {response.prompt_feedback}")
                 raise ValueError(f"Google Gemini response blocked or empty. Reason: {block_reason}")
            
            # Extract text, handle potential errors
            try:
                 response_content = response.text
                 logger.debug("Successfully extracted text from Gemini response.")
            except ValueError as e_text: # Gemini might raise ValueError if text extraction fails (e.g., blocked)
                 logger.error(f"Could not extract text from Gemini response: {e_text}. Response parts: {response.parts}", exc_info=True)
                 raise ValueError(f"Could not extract text content from Gemini response: {e_text}") from e_text
            
            # Serialize raw Gemini response (might be complex)
            try:
                 # Attempt to serialize parts if available, otherwise fallback
                 if hasattr(response, 'parts') and response.parts:
                      raw_response_str = json.dumps([part.to_dict() for part in response.parts])
                 else:
                      raw_response_str = repr(response) # Fallback
            except Exception as e_dump:
                 logger.warning(f"Could not serialize raw Gemini response object: {e_dump}")
                 raw_response_str = repr(response) # Fallback
            
        # --- Add other providers here ---
        # elif provider == 'openai': ...
        # elif provider == 'anthropic': ...

        else:
            # This should ideally not be reached if provider check is done earlier, but as a safeguard:
            raise ValueError(f"Unsupported or unimplemented AI provider logic reached: {provider}")

        # --- Success Logging ---
        if log_entry:
            log_entry.response_text = response_content
            log_entry.raw_response_text = raw_response_str
            log_entry.is_success = True
            log_entry.duration_ms = int((time.time() - start_time) * 1000)
            # Add provider-specific token counts if available
            if provider == 'groq' and hasattr(response, 'usage'):
                log_entry.completion_tokens = response.usage.completion_tokens
                log_entry.prompt_tokens = response.usage.prompt_tokens
                log_entry.total_tokens = response.usage.total_tokens
            elif provider == 'google_gemini' and hasattr(response, 'usage_metadata'):
                # Gemini's usage_metadata structure might differ
                 log_entry.completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', None)
                 log_entry.prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', None)
                 log_entry.total_tokens = getattr(response.usage_metadata, 'total_token_count', None)
            # Add other providers here
            
            logger.debug(f"Saving successful AIRequestLog entry {log_entry.id}. Value for raw_response_text: {repr(log_entry.raw_response_text)}")
            await sync_to_async(log_entry.save)()
            logger.debug(f"Updated AIRequestLog entry {log_entry.id}. Success: True, Duration: {log_entry.duration_ms}ms")

        return response_content # Return the extracted content

    # --- Exception Handling ---
    except Exception as e:
        # Default error message
        error_msg = f"Error calling {provider} API: {str(e)}"
        
        # Refine error message based on exception type
        if provider == 'groq':
            if isinstance(e, GroqAPIError): # Catch specific Groq errors
                 error_msg = f"Groq API Error ({e.status_code}): {e.message}"
                 logger.error(error_msg, exc_info=False) # Don't need full traceback for known API errors
            else:
                 logger.error(f"Unexpected Error during Groq call: {e}", exc_info=True)
                 error_msg = f"Unexpected Error during Groq call: {str(e)}"
        elif provider == 'google_gemini':
             if isinstance(e, (google_exceptions.PermissionDenied, google_exceptions.InvalidArgument)):
                  error_msg = f"Google Gemini API Error (Permission/Argument): {str(e)}"
                  logger.error(error_msg, exc_info=False)
             elif isinstance(e, google_exceptions.GoogleAPIError):
                  error_msg = f"Google Gemini API Error (General): {str(e)}"
                  logger.error(error_msg, exc_info=False)
             elif isinstance(e, ValueError) and "response blocked" in str(e): # Catch specific block error
                 error_msg = f"Google Gemini request failed: {str(e)}" # Already logged reason above
                 logger.warning(error_msg) # Log as warning as it's a content issue
             else:
                  logger.error(f"Unexpected Error during Google Gemini call: {e}", exc_info=True)
                  error_msg = f"Unexpected Error during Google Gemini call: {str(e)}"
        # Add other providers here
        else:
            # Error for an unknown or unhandled provider during the API call phase
            logger.error(f"Unexpected Error during call for unknown/unhandled provider '{provider}': {e}", exc_info=True)
            error_msg = f"Unexpected error for provider '{provider}': {str(e)}"

        # Update log entry on failure
        if log_entry:
            log_entry.is_success = False
            # Use the refined error message
            log_entry.error_message = error_msg 
            # Save the exception details as raw response on error
            log_entry.raw_response_text = json.dumps({"error": str(e), "detail": error_msg, "type": type(e).__name__}) 
            log_entry.duration_ms = int((time.time() - start_time) * 1000)
            logger.debug(f"Saving AIRequestLog entry {log_entry.id} on error. Value for raw_response_text: {repr(log_entry.raw_response_text)}")
            await sync_to_async(log_entry.save)()
            logger.debug(f"Updated AIRequestLog entry {log_entry.id} on error. Success: False, Duration: {log_entry.duration_ms}ms")
            
        # Return JSON error string
        return json.dumps({"error": error_msg}) 

# NEUE SYNCHRONE VERSION
def call_ai_api_sync(
    prompt: str, 
    user, # Typ hier explizit setzen, falls möglich: from mailmind.core.models import User
    provider: str, 
    model_name: str, 
    triggering_source: str = "unknown"
) -> str:
    """Synchronous version to call different AI provider APIs.
    Handles logging, API key retrieval, client instantiation, and basic error handling.
    Returns the AI response content as a string, or an error JSON string.
    WARNING: This function will BLOCK until the AI API call completes.
    """
    # Import necessary modules here (synchronous versions if needed)
    import time
    from django.utils import timezone
    # from asgiref.sync import sync_to_async # Not needed here
    from mailmind.core.models import User, AIRequestLog, APICredential # Import models
    
    # Import provider specific libraries (can stay here)
    client = None
    model = None # Variable for Gemini model
    if provider == 'groq':
        from .clients import get_groq_client
        from groq import Groq, APIError as GroqAPIError
    elif provider == 'google_gemini':
        try:
            import google.generativeai as genai
            from google.api_core import exceptions as google_exceptions
        except ImportError:
             logger.error("Google Generative AI library not installed. Cannot use google_gemini provider.")
             return json.dumps({"error": "Google Generative AI library not installed."})
    # Add other provider imports here if needed

    log_entry = None
    start_time = time.time()
    typed_user: User = user

    # Create initial log entry (SYNCHRONOUS)
    try:
        log_entry = AIRequestLog.objects.create(
            user=typed_user,
            provider=provider,
            model_name=model_name,
            triggering_source=triggering_source,
            prompt_text=prompt,
            is_success=False
        )
        logger.debug(f"Created initial AIRequestLog entry (sync) {log_entry.id} for {provider}/{model_name}. Prompt length: {len(prompt)} chars.")
    except Exception as e_log_create:
        logger.error(f"Failed to create initial AIRequestLog (sync): {e_log_create}", exc_info=True)

    # Get API Key (SYNCHRONOUS)
    api_key = None
    credential = None
    try:
        credential = APICredential.objects.get(user=typed_user, provider=provider)
        api_key = credential.get_api_key()
        if not api_key:
             raise ValueError(f"API key for {provider} could not be retrieved or decrypted.")
    except APICredential.DoesNotExist:
        error_msg = f"API credential for {provider} not found for User {typed_user.id}."
        logger.error(error_msg)
        if log_entry:
            log_entry.is_success = False
            log_entry.error_message = error_msg
            log_entry.duration_ms = int((time.time() - start_time) * 1000)
            log_entry.save() # Synchronous save
        return json.dumps({"error": error_msg})
    except Exception as e_key:
        error_msg = f"Error retrieving API credential or key (sync) for {provider}, User {typed_user.id}: {e_key}"
        logger.error(error_msg, exc_info=True)
        if log_entry:
            log_entry.is_success = False
            log_entry.error_message = f"API Key Retrieval Error: {error_msg}"
            log_entry.duration_ms = int((time.time() - start_time) * 1000)
            log_entry.save() # Synchronous save
        return json.dumps({"error": f"Error retrieving API key: {e_key}"})

    # --- API Call Logic (SYNCHRONOUS) ---
    response = None
    response_content = None
    raw_response_str = None
    try:
        # --- Groq ---
        if provider == 'groq':
            client = get_groq_client(api_key=api_key)
            if not client:
                raise Exception(f"Failed to initialize Groq client.")

            logger.debug(f"Calling Groq client chat completions (sync) with model '{model_name}'")
            # Groq SDK is likely synchronous by default
            response = client.chat.completions.create(
                 messages=[{"role": "user", "content": prompt}],
                 model=model_name,
            )
            response_content = response.choices[0].message.content
            try:
                raw_response_str = response.model_dump_json()
            except Exception as e_dump:
                logger.warning(f"Could not serialize raw Groq response object: {e_dump}")
                raw_response_str = repr(response)

        # --- Google Gemini ---
        elif provider == 'google_gemini':
            logger.debug(f"Configuring Google Gemini API key (sync)...")
            genai.configure(api_key=api_key)
            logger.debug(f"Instantiating Google Gemini model (sync) '{model_name}'")
            model = genai.GenerativeModel(model_name)
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            generation_config = genai.types.GenerationConfig()

            logger.debug(f"Calling Google Gemini generate_content (sync) with model '{model_name}'")
            # Use the SYNCHRONOUS method generate_content
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
                )

            if not response.candidates:
                 block_reason = getattr(response, 'prompt_feedback', {}).get('block_reason', 'Unknown')
                 logger.warning(f"Google Gemini response blocked or empty (sync). Reason: {block_reason}. Full feedback: {response.prompt_feedback}")
                 raise ValueError(f"Google Gemini response blocked or empty (sync). Reason: {block_reason}")
            
            try:
                 response_content = response.text
                 logger.debug("Successfully extracted text from Gemini response (sync).")
            except ValueError as e_text:
                 logger.error(f"Could not extract text from Gemini response (sync): {e_text}. Response parts: {response.parts}", exc_info=True)
                 raise ValueError(f"Could not extract text content from Gemini response (sync): {e_text}") from e_text
            
            try:
                 if hasattr(response, 'parts') and response.parts:
                      raw_response_str = json.dumps([part.to_dict() for part in response.parts])
                 else:
                      raw_response_str = repr(response)
            except Exception as e_dump:
                 logger.warning(f"Could not serialize raw Gemini response object (sync): {e_dump}")
                 raw_response_str = repr(response)
            
        # --- Add other providers here ---
        else:
            raise ValueError(f"Unsupported AI provider logic reached (sync): {provider}")

        # --- Success Logging (SYNCHRONOUS) ---
        if log_entry:
            log_entry.response_text = response_content
            log_entry.raw_response_text = raw_response_str
            log_entry.is_success = True
            log_entry.duration_ms = int((time.time() - start_time) * 1000)
            # Token counts (identical logic as async)
            if provider == 'groq' and hasattr(response, 'usage'):
                log_entry.completion_tokens = response.usage.completion_tokens
                log_entry.prompt_tokens = response.usage.prompt_tokens
                log_entry.total_tokens = response.usage.total_tokens
            elif provider == 'google_gemini' and hasattr(response, 'usage_metadata'):
                 log_entry.completion_tokens = getattr(response.usage_metadata, 'candidates_token_count', None)
                 log_entry.prompt_tokens = getattr(response.usage_metadata, 'prompt_token_count', None)
                 log_entry.total_tokens = getattr(response.usage_metadata, 'total_token_count', None)
            
            logger.debug(f"Saving successful AIRequestLog entry {log_entry.id} (sync). Value for raw_response_text: {repr(log_entry.raw_response_text)}")
            log_entry.save() # Synchronous save
            logger.debug(f"Updated AIRequestLog entry {log_entry.id} (sync). Success: True, Duration: {log_entry.duration_ms}ms")

        return response_content # Return the extracted content

    # --- Exception Handling (SYNCHRONOUS) ---
    except Exception as e:
        error_msg = f"Error during AI API call (sync) for {provider}/{model_name}, User {typed_user.id}: {e}"
        logger.error(error_msg, exc_info=True)
        if log_entry:
            log_entry.is_success = False
            log_entry.error_message = str(e) # Log the error message
            log_entry.duration_ms = int((time.time() - start_time) * 1000)
            # Try to save the log entry even on error
            try:
                 log_entry.save() # Synchronous save
            except Exception as e_log_save:
                 logger.error(f"Failed to save error details to AIRequestLog {log_entry.id}: {e_log_save}")
        # Return error JSON
        # Check for specific provider errors if needed (e.g., GroqAPIError, google_exceptions.GoogleAPIError)
        status_code = 500 # Default internal server error
        # Add specific error mapping here if needed
        # if isinstance(e, GroqAPIError): ...
        # if isinstance(e, google_exceptions.GoogleAPIError): ...
        return json.dumps({"error": f"AI API Error: {str(e)}", "status_code": status_code}) 