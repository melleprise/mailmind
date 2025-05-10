import logging
# from .clients import get_gemini_model # Replaced with call_ai_api
from .api_calls import call_ai_api
from ..prompt_templates.utils import get_prompt_details
import json

logger = logging.getLogger(__name__)

# Modify signature to accept optional context
async def correct_text_with_ai(text_to_correct: str, user, 
                             original_subject: str | None = None, 
                             original_body: str | None = None) -> str | dict | None:
    """
    Korrigiert entweder ein Snippet (plain) oder den gesamten Body+Betreff (JSON).
    Gibt korrigierten Text (Snippet) oder dict (full) zurück.
    """
    from mailmind.core.models import User
    from ..prompt_templates.utils import get_prompt_details

    if not text_to_correct:
        logger.debug("correct_text_with_ai: No text provided.")
        return text_to_correct

    if not user:
        logger.error("correct_text_with_ai: User object is required for API call.")
        return None

    # --- Kontext bauen ---
    context_parts = []
    if original_subject:
        context_parts.append(f"Subject: {original_subject}")
    if original_body:
        truncated_body = (original_body[:500] + '...') if len(original_body) > 500 else original_body
        context_parts.append(f"\n\nOriginal Email Body (Excerpt):\n{truncated_body}")
    context_string = "\n".join(context_parts) if context_parts else "(No context provided)"

    # --- Template-Auswahl ---
    is_snippet = False
    if (original_body and text_to_correct.strip() not in original_body) and (original_subject and text_to_correct.strip() not in original_subject):
        is_snippet = True
    elif not original_body and not original_subject:
        is_snippet = True
    # explizit: Wenn nur ein Ausschnitt übergeben wird, ist_snippet = True

    # NEU: Bei full correction ohne Body abbrechen
    if not is_snippet and not original_body:
        logger.error("Full correction requested, aber original_body ist leer. Abbruch.")
        return {"error": "Originalnachricht (Body) fehlt. Korrektur nicht möglich."}

    template_name = 'correct_text_snippet' if is_snippet else 'correct_text_full'
    prompt_details = await get_prompt_details(template_name)
    if not prompt_details:
        logger.error(f"Could not find active prompt template '{template_name}'.")
        return None
    logger.info(f"Using Provider: {prompt_details['provider']}, Model: {prompt_details['model_name']} for text correction (template: {template_name})")

    prompt_context = {
        'text_subject_to_correct': original_subject or "",
        'text_body_to_correct': original_body or "",
        'text_snippet_to_correct': text_to_correct or "",
        'context': context_string or ""
    }
    try:
        formatted_prompt = prompt_details['template'].format(**prompt_context)
    except KeyError as e:
        logger.error(f"Missing variable in prompt template '{template_name}': {e}", exc_info=True)
        return None
    except Exception as e_format:
        logger.error(f"Error formatting prompt template '{template_name}': {e_format}", exc_info=True)
        return None

    logger.info(f"Sending text for correction to {prompt_details['provider']} API: '{text_to_correct[:50]}...'")
    response_str = await call_ai_api(
        prompt=formatted_prompt,
        user=user,
        provider=prompt_details['provider'],
        model_name=prompt_details['model_name']
    )

    if not response_str:
        logger.warning("AI API returned an empty response during correction.")
        return None

    corrected_text = response_str.strip().strip('"`')
    if is_snippet:
        # Nur das Snippet zurückgeben
        logger.info(f"Corrected snippet received: '{corrected_text[:50]}...'")
        return corrected_text
    else:
        # JSON parsen
        try:
            result = json.loads(corrected_text)
            logger.info(f"Corrected full text received: subject='{result.get('corrected_subject','')[:30]}...', body='{result.get('corrected_body','')[:30]}...'")
            return result
        except Exception as e:
            logger.error(f"Failed to parse JSON from full correction: {e}", exc_info=True)
            return None 