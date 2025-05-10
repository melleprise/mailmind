import logging
import json
from mailmind.ai.api_calls import call_ai_api_sync # Annahme: Es gibt/wird eine synchrone Version geben
from mailmind.prompt_templates.utils import get_prompt_details_sync # Annahme: Es gibt/wird eine synchrone Version geben
from mailmind.core.models import User # Für User-Objekt
from knowledge.models import KnowledgeField

logger = logging.getLogger(__name__)

def refine_text_content_sync(
    custom_prompt: str | None, # Erlaube None oder leeren String
    original_subject: str, 
    original_body: str, 
    user: User
) -> tuple[str | None, str | None]:
    """
    Synchronously refines subject and body based on a custom prompt or performs pure correction.
    Uses the 'refine_suggestion' prompt template for refinement or 'correct_text_full' for pure correction.
    Returns a tuple (refined_subject, refined_body) or (None, None) on error.
    """
    # User ist immer erforderlich
    if not user:
        logger.error("refine_text_content_sync: Missing user.")
        return None, None

    # Entscheide, welcher Prompt verwendet wird
    is_pure_correction_mode = not custom_prompt
    prompt_name_to_use = 'correct_text_full' if is_pure_correction_mode else 'refine_suggestion'
    effective_prompt_for_ai = custom_prompt # Wird nur für Refinement verwendet

    logger.info(f"Refining text for user {user.email}. Pure correction: {is_pure_correction_mode}. Using prompt: '{prompt_name_to_use}'")

    try:
        # Hole Prompt-Details synchron
        prompt_details = get_prompt_details_sync(prompt_name_to_use)
        if not prompt_details:
            logger.error(f"Prompt template '{prompt_name_to_use}' not found or inactive.")
            return None, None

        logger.info(f"Using Provider: {prompt_details['provider']}, Model: {prompt_details['model_name']}")

        # Bereite den Kontext spezifisch für das verwendete Prompt-Template vor
        prompt_context = {}
        knowledge_context = {}

        if prompt_name_to_use == 'correct_text_full':
            prompt_context = {
                "text_subject_to_correct": original_subject, 
                "text_body_to_correct": original_body,
                "context": "", # Leerer Kontext oder spezifischer Korrektur-Kontext?
            }
            # Kein Knowledge context für reine Korrektur?
            # knowledge_context = {field.key: field.value for field in KnowledgeField.objects.filter(user=user)}
        elif prompt_name_to_use == 'refine_suggestion':
            prompt_context = {
                "original_subject": original_subject,      
                "original_body": original_body,          
                "refinement_prompt": effective_prompt_for_ai, 
            }
            # KnowledgeFields nur für Refinement übernehmen?
            knowledge_context = {field.key: field.value for field in KnowledgeField.objects.filter(user=user)}
            # Füge Agent und CV hinzu, falls im Prompt erwartet (muss im Template stehen!)
            prompt_context['agent'] = knowledge_context.get('agent', '') # Beispiel
            prompt_context['cv'] = knowledge_context.get('cv', '') # Beispiel
        
        # Kombiniere Basis-Kontext und Knowledge-Kontext (nur wenn Knowledge verwendet wird)
        # final_prompt_context = {**prompt_context, **knowledge_context}
        # WICHTIG: Nur die Variablen übergeben, die im jeweiligen Template SIND!
        # Wir gehen davon aus, dass .format() nur die benötigten nimmt und andere ignoriert,
        # ABER sicherer ist, nur die zu übergeben, die da sind. 
        # --> Ändere Logik, um nur relevante Keys zu sammeln
        
        final_prompt_context = {}
        if prompt_name_to_use == 'correct_text_full':
            final_prompt_context = {
                "text_subject_to_correct": original_subject,
                "text_body_to_correct": original_body,
                "context": prompt_context.get("context", ""), # Nimm den vorbereiteten Kontext
            }
        elif prompt_name_to_use == 'refine_suggestion':
             # Knowledge Kontexte explizit laden
             knowledge_context = {field.key: field.value for field in KnowledgeField.objects.filter(user=user)}
             final_prompt_context = {
                "original_subject": original_subject,      
                "original_body": original_body,          
                "refinement_prompt": effective_prompt_for_ai if effective_prompt_for_ai else "", # Stelle sicher, dass es ein String ist
                # Füge Knowledge-Felder hinzu, wenn sie existieren
                "cv": knowledge_context.get('cv', ''),
                "agent": knowledge_context.get('agent', ''),
                # Füge hier weitere erwartete Knowledge-Felder hinzu
             }

        try:
            logger.debug(f"Formatting prompt '{prompt_name_to_use}' with context keys: {list(final_prompt_context.keys())}")
            formatted_prompt = prompt_details['prompt'].format(**final_prompt_context)
        except KeyError as e_format:
            logger.error(f"Missing variable in prompt template '{prompt_name_to_use}': {e_format}. Context keys provided: {list(final_prompt_context.keys())}", exc_info=True)
            return None, None

        # 3. Call AI API (synchronous version)
        logger.info(f"Sending text for refinement to {prompt_details['provider']} API.")
        
        # Annahme: call_ai_api_sync ist die synchrone Version von call_ai_api
        # Diese muss ggf. in api_calls.py erstellt werden.
        response_str = call_ai_api_sync(
            prompt=formatted_prompt,
            user=user, # User-Objekt für Logging/Auditing im API Call
            provider=prompt_details['provider'],
            model_name=prompt_details['model_name'],
            # Falls der API Call eine Quelle erwartet, hier ggf. setzen
            triggering_source="direct_refine_text_content_sync" 
        )

        # 4. Process JSON response
        if response_str is None:
            logger.error("AI API call failed during refinement (returned None).")
            return None, None
        
        try:
            # KI-Antwort von Codefences befreien
            response_str = response_str.strip()
            if response_str.startswith("```json"):
                response_str = response_str[7:-3].strip() # Korrigierter Index
            elif response_str.startswith("```"):
                 response_str = response_str[3:-3].strip()
            # Remove potential trailing ```
            # if response_str.endswith("```"):
            #      response_str = response_str[:-3]
            
            response_str = response_str.strip()
            refined_data = json.loads(response_str)

            # Passe die erwarteten Schlüssel basierend auf dem verwendeten Prompt an
            if prompt_name_to_use == 'correct_text_full':
                refined_subject = refined_data.get('corrected_subject')
                refined_body = refined_data.get('corrected_body')
                required_keys = ['corrected_subject', 'corrected_body']
            else: # Annahme: refine_suggestion
                refined_subject = refined_data.get('refined_subject')
                refined_body = refined_data.get('refined_body')
                required_keys = ['refined_subject', 'refined_body']

            if refined_subject is None or refined_body is None:
                logger.error(f"AI response JSON missing required keys {required_keys} for prompt '{prompt_name_to_use}'. Response: {response_str}")
                return None, None
            
            logger.info(f"Successfully refined text for user {user.email}.")
            return refined_subject, refined_body

        except json.JSONDecodeError as e_json:
            logger.error(f"Failed to decode AI JSON response during refinement: {e_json}. Response: {response_str}", exc_info=True)
            return None, None
        except Exception as e_update: # General exception during processing
            logger.error(f"Error processing AI response after refinement: {e_update}", exc_info=True)
            return None, None

    except Exception as e:
        logger.error(f"General error in refine_text_content_sync for user {user.email}: {e}", exc_info=True)
        return None, None 