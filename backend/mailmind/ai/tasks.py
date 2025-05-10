# This file is intentionally left empty after refactoring.
# Tasks are now located in specific files like:
# - embedding_tasks.py
# - generate_suggestion_task.py
# - correct_text_task.py
# - refine_suggestion_task.py
# - summary_tasks.py # Added new task file
#
# Helper functions are in:
# - clients.py
# - api_calls.py
# - utils.py
#
# Prompt template logic is handled by:
# - mailmind/prompt_templates/utils.py
# - mailmind/prompt_templates/models.py

# Keeping imports needed by other modules that might still import from here during transition
# (Ideally these imports should be moved too)
import logging
import time
import json
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from mailmind.core.models import Email, Attachment, User, AISuggestion, AvailableApiModel, AIRequestLog
from django.utils import timezone
from django.core.cache import cache
from .api_calls import call_ai_api
from ..prompt_templates.utils import get_prompt_details
# from .embedding_tasks import generate_embeddings_for_email # Example of potential needed import
# from .generate_suggestion_task import generate_ai_suggestion # Example
# from .correct_text_task import correct_text_with_ai # Example
# from .refine_suggestion_task import refine_suggestion_with_prompt # Example
# from .summary_tasks import generate_summary_task # Example

# WebSocket related imports
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from mailmind.core.serializers import AISuggestionSerializer

# Other imports needed by helper functions within this file (like Qdrant/SentenceTransformers)
from django.conf import settings
import os
import gc
import sys
from qdrant_client import QdrantClient, models as qdrant_models
from qdrant_client.http.models import PointStruct
from PIL import Image
import pytesseract
import httpx
from groq import Groq, APIConnectionError, AuthenticationError
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from django.db import transaction
from multiprocessing import Value
from knowledge.models import KnowledgeField # Import the new model


logger = logging.getLogger(__name__)

# If any tasks are still triggered via this file path, add stubs or re-exports:
# Example:
# from .generate_suggestion_task import generate_ai_suggestion
# from .embedding_tasks import generate_embeddings_for_email
# ... (add other re-exports if needed)

# It's better to update the callers to import directly from the new locations.

# --- WebSocket Send Helper ---
def send_suggestions_to_client(email_id: int, user_id: int, suggestions_data: list):
    """Sends a notification that suggestions have been updated."""
    try:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.error("[WS Send Helper] Channel layer is None. Cannot send WebSocket notification.")
            return

        group_name = f'user_{user_id}_events'
        # Send a simple notification message, the consumer will fetch the data
        message_data = {
            'type': 'suggestions.updated', # Match the consumer handler
            'email_id': email_id, 
            # 'suggestions': suggestions_data, # Data is no longer needed here
        }
        logger.info(f"[WS Send Helper] Sending notification to group {group_name} for email {email_id}: {repr(message_data)}")
        async_to_sync(channel_layer.group_send)(group_name, message_data)
        logger.info(f"[WS Send Helper] Notification sent successfully to {group_name}.")

    except Exception as ws_err:
        logger.error(f"[WS Send Helper] Error sending WebSocket notification for email {email_id}: {ws_err}", exc_info=True)
# --- End WebSocket Send Helper ---

# --- Modell Initialisierung entfernt ---
# Das Laden des Text-Modells geschieht jetzt in apps.py -> AiConfig.ready(),
# gesteuert durch die Umgebungsvariable LOAD_AI_MODELS.
# text_model = _load_text_model_once()

# Globale Modelle (Qdrant/Gemini bleiben beim alten Ladevorgang in get_...)
_text_model = None # Wieder aktivieren für lazy loading
image_model = None
qdrant_client = None
gemini_model = None

def get_text_model():
    """Lädt das SentenceTransformer-Modell beim ersten Aufruf im Prozess und gibt es zurück."""
    global _text_model
    if _text_model is None:
        logger.info("--- get_text_model: _text_model is None, attempting to load. ---")
        load_models_env = os.getenv('LOAD_AI_MODELS', 'false').lower() == 'true'
        if not load_models_env:
             logger.warning("LOAD_AI_MODELS ist nicht auf 'true' gesetzt. Text-Modell wird nicht geladen.")
             raise RuntimeError("Text-Embedding-Modell-Laden nicht aktiviert (LOAD_AI_MODELS!=true).")
             
        logger.info("Importing SentenceTransformer library...")
        try:
            from sentence_transformers import SentenceTransformer
            logger.info("SentenceTransformer library imported successfully.")
            
            # --- TEMPORARY: Use a smaller model for testing ---
            # model_name = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
            model_name = 'sentence-transformers/all-MiniLM-L6-v2' 
            logger.info(f"Attempting to instantiate SentenceTransformer with model: {model_name}...")
            
            # Explizit den Cache-Ordner übergeben
            cache_folder = os.getenv('SENTENCE_TRANSFORMERS_HOME')
            
            # --- HIER: Robuster try...except NUR um die Instanziierung --- 
            try:
                 # Explizite Garbage Collection vor dem Laden
                 logger.debug("Running garbage collection before model load...")
                 gc.collect()
                 logger.debug("Garbage collection finished.")
                 
                 if cache_folder:
                      logger.info(f"Using explicit cache folder: {cache_folder}")
                      _text_model = SentenceTransformer(model_name, cache_folder=cache_folder)
                 else:
                      logger.warning("SENTENCE_TRANSFORMERS_HOME not set, relying on default cache.")
                      _text_model = SentenceTransformer(model_name)
                 
                 logger.info(f"SentenceTransformer model '{model_name}' instantiated successfully.")
                 
            except Exception as model_load_e:
                 # Logge den Fehler SEHR explizit und beende den Prozess hart,
                 # damit wir den Fehler sicher sehen.
                 logger.critical(f"!!! CRITICAL ERROR DURING SentenceTransformer INSTANTIATION: {model_load_e} !!!", exc_info=True)
                 # Optional: Zusätzliche Debug-Infos loggen?
                 # logger.info(f"Environment: {os.environ}")
                 # logger.info(f"Cache Folder: {cache_folder}")
                 # Beende den Prozess, um Reinkarnation mit derselben Ursache zu vermeiden
                 sys.exit(f"Worker exiting due to model load failure: {model_load_e}") 
            # --- Ende des robusten try...except --- 
                 
        except ImportError:
             logger.error("sentence-transformers ist nicht installiert.", exc_info=True)
             raise RuntimeError("Fehler beim Laden des Text-Modells: sentence-transformers nicht installiert.")
        # Den äußeren Exception-Handler brauchen wir hier nicht mehr unbedingt,
        # da der innere try..except mit sys.exit() den Prozess beendet.
        # except Exception as e:
        #     logger.error(f"Exception during SentenceTransformer instantiation: {e}", exc_info=True)
        #     raise RuntimeError(f"Fehler beim Laden des Text-Modells: {e}")
        logger.info("--- get_text_model: Model loaded and assigned to _text_model. ---")
            
    else:
        logger.debug("--- get_text_model: _text_model already loaded, returning cached instance. ---")
    return _text_model

def get_image_model():
    """Lädt und gibt das CLIP-Modell für Bild-Embeddings zurück."""
    global image_model
    if image_model is None:
        logger.info("Lade Bild-Embedding-Modell (CLIP)...")
        # TODO: CLIP-Modell laden, falls benötigt und konfiguriert
        logger.warning("Bild-Embedding-Modell (CLIP) ist derzeit nicht aktiv geladen.")
    return image_model

def get_qdrant_client():
    """Initialisiert und gibt den Qdrant Client zurück. Erstellt Collections falls nötig."""
    global qdrant_client
    if qdrant_client is None:
        qdrant_url = settings.QDRANT_URL
        qdrant_api_key = getattr(settings, 'QDRANT_API_KEY', None)
        logger.info(f"Versuche, Qdrant Client zu initialisieren. URL: {qdrant_url}, Key vorhanden: {qdrant_api_key is not None}")
        try:
            # --> Punkt 1: Vor der Initialisierung
            logger.debug("Versuche QdrantClient(url=..., api_key=...)")
            qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=20) # Timeout hinzufügen
            # --> Punkt 2: Nach der Initialisierung
            logger.info("Qdrant Client erfolgreich initialisiert.")
            
            # Vector size für das neue Modell
            new_vector_size = 384 # Dimension von MiniLM
            
            # Collection für E-Mail-Embeddings (Text)
            email_collection_name = "email_embeddings"
            try:
                # --> Punkt 3: Vor get_collection (email)
                logger.debug(f"Prüfe Collection: {email_collection_name}")
                collection_info = qdrant_client.get_collection(collection_name=email_collection_name)
                # Prüfe, ob die Vektorgröße übereinstimmt (KORRIGIERTER ZUGRIFF)
                current_vector_size = collection_info.config.params.vectors.size
                if current_vector_size != new_vector_size:
                    logger.warning(f"Vektorgröße in Qdrant Collection '{email_collection_name}' ({current_vector_size}) stimmt nicht mit dem neuen Modell ({new_vector_size}) überein! Alte Collection wird gelöscht.")
                    qdrant_client.delete_collection(collection_name=email_collection_name)
                    raise ValueError("Collection mit falscher Vektorgröße gelöscht.") # Provoziert Neuerstellung
                logger.info(f"Qdrant Collection '{email_collection_name}' existiert bereits mit korrekter Größe {new_vector_size}.")
            except Exception as e_get_email:
                 # --> Punkt 5: Bei Fehler get_collection (email) oder nach Löschung
                logger.warning(f"Collection {email_collection_name} nicht gefunden oder Fehler bei Prüfung/Größenabgleich: {e_get_email}. Versuche zu erstellen...")
                try:
                    # --> Punkt 6: Vor create_collection (email)
                    logger.debug(f"Erstelle Collection: {email_collection_name} mit Vektorgröße {new_vector_size}")
                    qdrant_client.create_collection(
                        collection_name=email_collection_name,
                        vectors_config=qdrant_models.VectorParams(size=new_vector_size, distance=qdrant_models.Distance.COSINE)
                    )
                    # --> Punkt 7: Nach create_collection (email)
                    logger.info(f"Collection {email_collection_name} erfolgreich erstellt.")
                except Exception as e_create_email:
                    # --> Punkt 8: Bei Fehler create_collection (email)
                    logger.error(f"Fehler beim Erstellen der Collection {email_collection_name}: {e_create_email}", exc_info=True)
                    raise # Erneutes Auslösen, damit der Task fehlschlägt
                
            # Collection für Anhang-Embeddings (Text)
            attachment_collection_name = "attachment_embeddings"
            # attachment_vector_size = 768 # Alt
            attachment_vector_size = new_vector_size # Verwende die gleiche Größe
            try:
                 # --> Punkt 9: Vor get_collection (attachment)
                logger.debug(f"Prüfe Collection: {attachment_collection_name}")
                collection_info_attach = qdrant_client.get_collection(collection_name=attachment_collection_name)
                # Prüfe, ob die Vektorgröße übereinstimmt (KORRIGIERTER ZUGRIFF)
                current_attach_vector_size = collection_info_attach.config.params.vectors.size
                if current_attach_vector_size != attachment_vector_size:
                    logger.warning(f"Vektorgröße in Qdrant Collection '{attachment_collection_name}' ({current_attach_vector_size}) stimmt nicht mit dem neuen Modell ({attachment_vector_size}) überein! Alte Collection wird gelöscht.")
                    qdrant_client.delete_collection(collection_name=attachment_collection_name)
                    raise ValueError("Collection mit falscher Vektorgröße gelöscht.")
                logger.info(f"Qdrant Collection '{attachment_collection_name}' existiert bereits mit korrekter Größe {attachment_vector_size}.")
            except Exception as e_get_attach:
                # --> Punkt 11: Bei Fehler get_collection (attachment) oder nach Löschung
                logger.warning(f"Collection {attachment_collection_name} nicht gefunden oder Fehler bei Prüfung/Größenabgleich: {e_get_attach}. Versuche zu erstellen...")
                try:
                    # --> Punkt 12: Vor create_collection (attachment)
                    logger.debug(f"Erstelle Collection: {attachment_collection_name} mit Vektorgröße {attachment_vector_size}")
                    qdrant_client.create_collection(
                        collection_name=attachment_collection_name,
                        vectors_config=qdrant_models.VectorParams(size=attachment_vector_size, distance=qdrant_models.Distance.COSINE)
                    )
                    # --> Punkt 13: Nach create_collection (attachment)
                    logger.info(f"Collection {attachment_collection_name} erfolgreich erstellt.")
                except Exception as e_create_attach:
                     # --> Punkt 14: Bei Fehler create_collection (attachment)
                    logger.error(f"Fehler beim Erstellen der Collection {attachment_collection_name}: {e_create_attach}", exc_info=True)
                    raise # Erneutes Auslösen
                
            logger.info("Qdrant Client verbunden und Collections initialisiert.")
        except Exception as e_init:
            # --> Punkt 15: Bei Fehler Initialisierung
            logger.error(f"Fehler beim Initialisieren des Qdrant Clients: {e_init}", exc_info=True)
            raise # Kritischer Fehler
    return qdrant_client

async def correct_text_with_ai(text_to_correct: str, user) -> str | None:
    """
    Sends text to the AI using the 'correct_text' prompt template.
    Uses the generic call_ai_api function.
    Returns the corrected text or None on error.
    """
    from mailmind.core.models import User
    from ..prompt_templates.utils import get_prompt_details

    if not text_to_correct:
        logger.debug("correct_text_with_ai: No text provided.")
        return text_to_correct
    if not user:
        logger.error("correct_text_with_ai: User object is required for API call.")
        return None

    try:
        prompt_details = await get_prompt_details('correct_text')
        if not prompt_details:
            logger.error("Could not find active prompt template 'correct_text'.")
            return None

        prompt_context = {'text_to_correct': text_to_correct}
        try:
            formatted_prompt = prompt_details['template'].format(**prompt_context)
        except KeyError as e:
            logger.error(f"Missing variable in prompt template 'correct_text': {e}", exc_info=True)
            return None
        except Exception as e_format:
            logger.error(f"Error formatting prompt template 'correct_text': {e_format}", exc_info=True)
            return None

        logger.info(f"Sending text for correction to {prompt_details['provider']} API: '{text_to_correct[:50]}...' for User {user.id}")
        response_str = await call_ai_api(
            prompt=formatted_prompt,
            user=user,
            provider=prompt_details['provider'],
            model_name=prompt_details['model_name']
        )

        # Process response (assuming direct text or error JSON)
        try:
            response_data = json.loads(response_str)
            if isinstance(response_data, dict) and 'error' in response_data:
                logger.error(f"Error from AI API during correction: {response_data['error']}")
                return None
            logger.warning(f"Unexpected JSON response during correction: {response_data}")
            return None
        except json.JSONDecodeError:
            corrected_text = response_str.strip().strip('\"`')
            logger.info(f"Corrected text received: '{corrected_text[:50]}...'")
            return corrected_text
        except Exception as e_proc:
            logger.error(f"Error processing AI response during correction: {e_proc}", exc_info=True)
            return None

    except Exception as e:
        logger.error(f"Error in correct_text_with_ai: {e}", exc_info=True)
        return None

async def refine_suggestion_with_prompt(text_to_refine: str, custom_prompt: str, user) -> str | None:
    """
    Sends text and a custom prompt to the AI using the 'refine_suggestion' template.
    Uses the generic call_ai_api function.
    Returns the refined text or None on error.
    """
    from mailmind.core.models import User
    from ..prompt_templates.utils import get_prompt_details

    if not text_to_refine or not custom_prompt:
        logger.debug("refine_suggestion_with_prompt: Missing text or custom prompt.")
        return None
    if not user:
        logger.error("refine_suggestion_with_prompt: User object is required for API call.")
        return None

    try:
        prompt_details = await get_prompt_details('refine_suggestion')
        if not prompt_details:
            logger.error("Could not find active prompt template 'refine_suggestion'.")
            return None

        prompt_context = {
            'text_to_refine': text_to_refine,
            'custom_prompt': custom_prompt
        }
        prompt_context.update(knowledge_context)
        try:
            formatted_prompt = prompt_details['template'].format(**prompt_context)
        except KeyError as e:
            logger.error(f"Missing variable in prompt template 'refine_suggestion': {e}", exc_info=True)
            return None
        except Exception as e_format:
            logger.error(f"Error formatting prompt template 'refine_suggestion': {e_format}", exc_info=True)
            return None

        logger.info(f"Sending text for refinement to {prompt_details['provider']} API: '{text_to_refine[:50]}...' for User {user.id}")
        response_str = await call_ai_api(
            prompt=formatted_prompt,
            user=user,
            provider=prompt_details['provider'],
            model_name=prompt_details['model_name']
        )

        # Process response (assuming direct text or error JSON)
        try:
            response_data = json.loads(response_str)
            if isinstance(response_data, dict) and 'error' in response_data:
                logger.error(f"Error from AI API during refinement: {response_data['error']}")
                return None
            logger.warning(f"Unexpected JSON response during refinement: {response_data}")
            return None
        except json.JSONDecodeError:
            refined_text = response_str.strip().strip('\"`')
            logger.info(f"Refined text received: '{refined_text[:50]}...'")
            return refined_text
        except Exception as e_proc:
            logger.error(f"Error processing AI response during refinement: {e_proc}", exc_info=True)
            return None

    except Exception as e:
        logger.error(f"Error in refine_suggestion_with_prompt: {e}", exc_info=True)
        return None

def generate_email_embedding(email: Email):
    """Generiert Text-Embedding für eine E-Mail und speichert es in Qdrant."""
    try:
        model = get_text_model()
        client = get_qdrant_client()
        
        text_content = f"Betreff: {email.subject}\nAbsender: {email.from_address}\n\n{email.body_text}"
        embedding = model.encode(text_content)
        
        to_addresses = list(email.to_contacts.values_list('email', flat=True))
        cc_addresses = list(email.cc_contacts.values_list('email', flat=True))
        bcc_addresses = list(email.bcc_contacts.values_list('email', flat=True))
        attachment_filenames = list(email.attachments.values_list('filename', flat=True))
        attachment_ids = list(email.attachments.values_list('id', flat=True))

        payload = {
            'email_id': email.id,
            'subject': email.subject or "",
            'from_address': email.from_address or "",
            'to_addresses': to_addresses,
            'cc_addresses': cc_addresses,
            'bcc_addresses': bcc_addresses,
            'received_at': email.received_at.isoformat() if email.received_at else None,
            'sent_at': email.sent_at.isoformat() if email.sent_at else None,
            'body_snippet': (email.body_text or "")[:250], # Gekürzt
            'has_attachments': email.attachments.exists(),
            'attachment_filenames': attachment_filenames,
            'attachment_ids': attachment_ids, 
            'account_id': email.account_id,
            'user_id': email.account.user_id,
            'is_read': email.is_read,
            'is_flagged': email.is_flagged,
            'is_replied': email.is_replied,
            'is_deleted': email.is_deleted_on_server,
            'is_draft': email.is_draft,
            'folder_name': email.folder_name or "",
        }
        
        point = PointStruct(
            id=email.id,
            vector=embedding.tolist(),
            payload=payload
        )
        
        client.upsert(
            collection_name="email_embeddings",
            points=[point],
            wait=True 
        )
        logger.info(f"Text-Embedding für Email ID {email.id} in Qdrant gespeichert.")
        
        # Markieren, dass Embedding erstellt wurde (direkt hier statt am Ende des Haupt-Tasks)
        # Entfernt: Wird jetzt im Haupttask durch ai_processed ersetzt
        # if not email.embedding_generated:
        #    email.embedding_generated = True
        #    email.save(update_fields=['embedding_generated', 'updated_at'])
            
    except Exception as e:
        logger.error(f"Fehler beim Generieren/Speichern des E-Mail-Embeddings für ID {email.id}: {e}", exc_info=True)

def generate_attachment_embedding(attachment: Attachment):
    """Generiert Embedding für einen Anhang (OCR für Bilder) und speichert es in Qdrant."""
    try:
        text_model = get_text_model()
        client = get_qdrant_client()
        
        extracted_text = ""
        embedding = None
        is_image = attachment.content_type.startswith('image/')

        if is_image:
            try:
                # Prüfen ob Datei existiert
                if not attachment.file or not attachment.file.path:
                     logger.warning(f"Anhang-Datei für ID {attachment.id} nicht gefunden.")
                     return # Frühzeitiger Ausstieg, wenn kein Pfad vorhanden
                
                # Versuche, das Bild zu öffnen und OCR durchzuführen
                try:
                    image = Image.open(attachment.file.path)
                    extracted_text = pytesseract.image_to_string(image, lang='deu+eng')
                    logger.info(f"OCR für Anhang {attachment.id} ({attachment.filename}) durchgeführt.")
                except FileNotFoundError:
                    logger.error(f"Datei für Anhang {attachment.id} nicht gefunden unter Pfad: {attachment.file.path}")
                    return # Abbruch, wenn Datei fehlt
                except Exception as ocr_error:
                    logger.error(f"OCR Fehler für Anhang {attachment.id}: {ocr_error}", exc_info=True)
                    extracted_text = "" # Setze leeren String bei OCR-Fehler

            except Exception as outer_exception:
                 # Fängt andere Fehler ab, z.B. Probleme beim Zugriff auf attachment.file.path
                 logger.error(f"Fehler beim Vorbereiten der OCR für Anhang {attachment.id}: {outer_exception}", exc_info=True)
                 return

        else:
            # TODO: Text-Extraktion für andere Typen (PDF, DOCX)
            extracted_text = attachment.extracted_text or f"Dateiname: {attachment.filename}"

        # Nur Text-Embeddings aktuell
        if extracted_text:
            embedding = text_model.encode(extracted_text)
            embedding_list = embedding.tolist()
        else:
            logger.warning(f"Kein Text für Embedding für Anhang {attachment.id} vorhanden.")
            return 

        payload = {
            'attachment_id': attachment.id,
            'parent_email_id': attachment.email_id,
            'filename': attachment.filename or "",
            'content_type': attachment.content_type or "",
            'extracted_text_snippet': (extracted_text or "")[:250], 
            'size': attachment.size,
            'is_image': is_image,
            'account_id': attachment.email.account_id,
            'user_id': attachment.email.account.user_id,
        }

        point = PointStruct(
            id=attachment.id,
            vector=embedding_list,
            payload=payload
        )

        client.upsert(
            collection_name="attachment_embeddings",
            points=[point],
            wait=True
        )
        logger.info(f"Embedding für Anhang ID {attachment.id} in Qdrant gespeichert.")

        # Nur speichern, wenn Text extrahiert wurde (optional)
        # if extracted_text and not attachment.extracted_text:
        #    attachment.save(update_fields=['extracted_text', 'updated_at'])
        
    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten/Speichern des Anhang-Embeddings für ID {attachment.id}: {e}", exc_info=True)

# Haupt-Task zur Generierung von Vorschlägen für eine E-Mail
@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_ai_suggestion(self, email_id: int, triggering_user_id: int):
    """
    Celery task to generate AI suggestions for a given email ID.
    """
    # --> Punkt 2: Start des Tasks
    logger.info(f"[TASK Start] Starting AI suggestion generation for Email ID: {email_id} triggered by User ID: {triggering_user_id}")
    start_time = time.time()

    try:
        # Hole User und Email Objekte
        try:
            user = User.objects.get(id=triggering_user_id)
            email = Email.objects.select_related('account__user').prefetch_related(
                'to_contacts', 'cc_contacts', 'bcc_contacts', 'attachments' # Prefetch für Effizienz
            ).get(id=email_id)
            # Stelle sicher, dass die E-Mail zum auslösenden Benutzer gehört
            if email.account.user != user:
                 logger.error(f"[TASK] Sicherheitsverletzung: User {triggering_user_id} versuchte, Vorschläge für E-Mail {email_id} von User {email.account.user.id} zu generieren.")
                 # Wir brechen hier ab, statt einen Fehler auszulösen, der Retries verursacht
                 return f"Error: Permission denied. User {triggering_user_id} cannot access email {email_id}."
        except User.DoesNotExist:
            logger.error(f"[TASK] User mit ID {triggering_user_id} nicht gefunden.")
            # Kein Retry hier sinnvoll
            return f"Error: Triggering user {triggering_user_id} not found."
        except Email.DoesNotExist:
            logger.error(f"[TASK] Email mit ID {email_id} nicht gefunden.")
            # Kein Retry hier sinnvoll
            return f"Error: Email {email_id} not found."
            
        # Prüfe, ob die Verarbeitung bereits läuft oder kürzlich abgeschlossen wurde
        cache_key = f"ai_suggestion_lock_email_{email_id}"
        if cache.get(cache_key):
            logger.warning(f"[TASK] AI suggestion generation for Email ID: {email_id} is already running or was recently completed. Skipping.")
            return "Skipped: Task already running or recently completed."
        # Setze Lock mit Timeout (z.B. 15 Minuten)
        cache.set(cache_key, True, timeout=900) 

        # --> Punkt 3: Markiere E-Mail als in Bearbeitung
        email.ai_processed = False # Markiere als "in Bearbeitung"
        email.ai_processed_at = None
        email.save(update_fields=['ai_processed', 'ai_processed_at'])
        
        # Lösche alte Vorschläge, bevor neue generiert werden
        logger.info(f"[TASK] Lösche alte AI-Vorschläge für Email ID: {email_id}")
        AISuggestion.objects.filter(email=email).delete()

        # Load Email object
        try:
            email = Email.objects.get(pk=email_id)
        except Email.DoesNotExist:
            logger.error(f"[TASK] Email with ID {email_id} not found.")
            cache.delete(cache_key) # Clean up cache lock
            return f"Error: Email with ID {email_id} not found."
            
        # Check if email object exists before accessing attributes
        if not email:
            logger.error(f"[TASK] Failed to load Email object for ID {email_id}. Stopping task.")
            cache.delete(cache_key)
            return f"Error: Could not load email {email_id}."

        # Get prompt details for 'generate_suggestions'
        prompt_details = async_to_sync(get_prompt_details)('generate_suggestions')
        if not prompt_details:
            logger.error("Could not find active prompt template 'generate_suggestions'.")
            cache.delete(cache_key)
            return "Error: Active prompt template 'generate_suggestions' not found."

        # [LOGIC] 1. Kontext sammeln (RAG + Knowledge Fields)
        logger.info(f"[TASK Step 1/4] Sammle Kontext für Email ID: {email_id}")
        rag_context = "" # Initialize rag_context
        # TODO: Implement RAG search here

        # Fetch user's knowledge fields
        knowledge_context = {}
        MAX_KNOWLEDGE_FIELD_LENGTH = 4000 # Max length in characters for each knowledge field value
        try:
            knowledge_fields = KnowledgeField.objects.filter(user=user)
            original_lengths = {} # Optional: Zum Loggen der originalen Längen
            truncated_count = 0
            for field in knowledge_fields:
                original_lengths[field.key] = len(field.value)
                if len(field.value) > MAX_KNOWLEDGE_FIELD_LENGTH:
                    knowledge_context[field.key] = field.value[:MAX_KNOWLEDGE_FIELD_LENGTH] + "\n[... Content truncated ...]"
                    truncated_count += 1
                    logger.warning(f"[TASK] Knowledge field '{field.key}' for user {user.id} truncated from {original_lengths[field.key]} to {MAX_KNOWLEDGE_FIELD_LENGTH} characters.")
                else:
                    knowledge_context[field.key] = field.value
            logger.info(f"Loaded {len(knowledge_context)} knowledge fields for user {user.id}. Truncated {truncated_count} fields exceeding {MAX_KNOWLEDGE_FIELD_LENGTH} chars.")
            # Optional: Detaillierteres Logging der Längen
            # logger.debug(f"[TASK] Original knowledge field lengths: {original_lengths}")
        except Exception as e_knowledge:
            logger.error(f"[TASK] Error fetching/processing knowledge fields for user {user.id}: {e_knowledge}", exc_info=True)
            # Continue without knowledge fields, but log the error
            knowledge_context = {} # Ensure it's empty on error

        # [LOGIC] 2. Create Prompt using the template from DB
        logger.info(f"[TASK Step 2/4] Erstelle Prompt für {prompt_details['provider']} für E-Mail {email.id}")
        
        # Build the prompt context dictionary
        prompt_context = {
            'rag_context': rag_context if rag_context else 'Kein zusätzlicher Kontext verfügbar.',
            'intent': '[Intent Placeholder]',
            'email_from': email.from_address,
            'email_to': list(email.to_contacts.values_list('email', flat=True)),
            'email_cc': list(email.cc_contacts.values_list('email', flat=True)),
            'email_subject': email.subject,
            'email_received_at': email.received_at,
            'email_body': email.body_text if email.body_text else '(Kein Textinhalt vorhanden)',
        }
        prompt_context.update(knowledge_context)

        try:
            formatted_prompt = prompt_details['template'].format(**prompt_context)
        except KeyError as e:
            logger.error(f"Missing variable in prompt template or knowledge fields: {e}", exc_info=True)
            # Schreibe Prompt-Log auch bei Fehler
            AIRequestLog.objects.create(
                user=user,
                provider=prompt_details['provider'],
                model_name=prompt_details['model_name'],
                triggering_source='generate_suggestions_task',
                prompt_text=prompt_details['template'],
                is_success=False,
                error_message=f"Missing variable in prompt template or knowledge fields: {e}"
            )
            cache.delete(cache_key)
            return f"Error: Missing variable {e} in prompt template or knowledge fields."
        except Exception as e_format:
            logger.error(f"Error formatting prompt template 'generate_suggestions': {e_format}", exc_info=True)
            AIRequestLog.objects.create(
                user=user,
                provider=prompt_details['provider'],
                model_name=prompt_details['model_name'],
                triggering_source='generate_suggestions_task',
                prompt_text=prompt_details['template'],
                is_success=False,
                error_message=f"Error formatting prompt template 'generate_suggestions': {e_format}"
            )
            cache.delete(cache_key)
            return f"Error formatting prompt template 'generate_suggestions': {e_format}"
        
        # --- Log the final prompt --- 
        # Split the logging for clarity and to avoid syntax issues with multi-line f-string
        logger.debug(f"[TASK] Sending prompt for Email ID {email.id} to {prompt_details['provider']} ({prompt_details['model_name']})") 
        logger.debug(f"------PROMPT START------\n{formatted_prompt}\n------PROMPT END------")

        # [LOGIC] 4. Call the correct AI API function
        logger.info(f"[TASK Step 3/4] Calling {prompt_details['provider']} API ({prompt_details['model_name']}) for Email ID {email.id}")
        # Use the central call_ai_api function
        api_response_str = async_to_sync(call_ai_api)(
            prompt=formatted_prompt, 
            user=user, 
            provider=prompt_details['provider'], 
            model_name=prompt_details['model_name'],
            triggering_source='generate_suggestions_task'
        )
        # --> Punkt 6: Verarbeite Antwort

        # --- Log the raw response string for debugging ---
        logger.debug(f"[TASK] Raw response string from {prompt_details['provider']}: >>>{api_response_str}<<<" )

        logger.info(f"[TASK Step 4/4] Verarbeite {prompt_details['provider']}-Antwort und speichere Vorschläge für E-Mail {email.id}")
        # ... (Verarbeitung der Antwort bleibt weitgehend gleich)
        try:
            # --- Verbesserte JSON-Bereinigung --- 
            raw_response = api_response_str # Arbeite mit Kopie
            logger.debug(f"[TASK] Raw AI response before cleaning: {repr(raw_response)}")

            # 1. Finde den Start und das Ende des JSON-Objekts
            json_start_index = raw_response.find('{')
            json_end_index = raw_response.rfind('}')

            if json_start_index != -1 and json_end_index != -1 and json_end_index > json_start_index:
                # Extrahiere den vermuteten JSON-Teil
                potential_json = raw_response[json_start_index : json_end_index + 1]
                logger.debug(f"[TASK] Extracted potential JSON block: {repr(potential_json)}")
                
                # Versuche, den extrahierten Teil zu parsen
                try:
                    api_response_data = json.loads(potential_json)
                    logger.info("[TASK] Successfully parsed extracted JSON block.")
                except json.JSONDecodeError as e_parse:
                    logger.error(f"[TASK] Failed to parse extracted JSON block. Error: {e_parse}. Extracted block: {repr(potential_json)}", exc_info=True)
                    # Wenn das Parsen des extrahierten Blocks fehlschlägt, löse den ursprünglichen Fehler aus
                    raise json.JSONDecodeError(f"Failed to parse extracted JSON from AI response", api_response_str, 0) from e_parse
            else:
                # Kein klares JSON-Objekt gefunden, versuche altes Fallback oder löse Fehler aus
                logger.warning("[TASK] Could not find clear JSON boundaries '{' and '}' in the response. Falling back to previous cleanup or failing.")
                # Hier könnten wir den alten Cleanup-Code als Fallback einfügen oder direkt fehlschlagen.
                # Wir gehen erstmal davon aus, dass, wenn kein {..} gefunden wird, die Antwort ungültig ist.
                raise json.JSONDecodeError("Could not find JSON object boundaries in AI response", api_response_str, 0)

            # --- Ende verbesserte JSON-Bereinigung --- 

            # Alte Bereinigung (kann entfernt oder als Fallback behalten werden, aber die neue Methode sollte besser sein)
            # cleaned_response_str = api_response_str.strip()
            # if cleaned_response_str.startswith('```json') and cleaned_response_str.endswith('```'):
            #     cleaned_response_str = cleaned_response_str[7:-3].strip()
            # elif cleaned_response_str.startswith('```') and cleaned_response_str.endswith('```'):
            #      cleaned_response_str = cleaned_response_str[3:-3].strip()
            # try:
            #     cleaned_response_str = cleaned_response_str.encode('utf-8').decode('utf-8', 'ignore')
            # except Exception as clean_err:
            #     logger.warning(f"[TASK] Error during extra string cleanup: {clean_err}", exc_info=True)
            # logger.debug(f"[TASK] Attempting to parse JSON. Type: {type(cleaned_response_str)}, repr: {repr(cleaned_response_str)}")
            # api_response_data = json.loads(cleaned_response_str)

            # --- Ab hier Verarbeitung des geparsten api_response_data --- 
            if isinstance(api_response_data, dict) and "error" in api_response_data:
                logger.error(f"[TASK] Fehler von {prompt_details['provider']} API erhalten für Email {email.id}: {api_response_data['error']}")
                # Markiere als nicht erfolgreich verarbeitet
                email.ai_processed = False 
                email.ai_processed_at = timezone.now()
                email.save(update_fields=['ai_processed', 'ai_processed_at'])
                # Lösche den Lock, damit es erneut versucht werden kann (falls kein Retry)
                cache.delete(cache_key) 
                return f"Error during {prompt_details['provider']} API call: {api_response_data['error']}"
            elif 'suggestions' in api_response_data and isinstance(api_response_data['suggestions'], list):
                 suggestions_data = api_response_data['suggestions'][:3] # Limitiere auf 3 Vorschläge
                 logger.info(f"[TASK] Received suggestions list from {prompt_details['provider']}: {len(suggestions_data)} items")
                 # Log extracted summaries
                 short_summary_log = api_response_data.get('short_summary', 'N/A')
                 medium_summary_log = api_response_data.get('medium_summary', 'N/A')
                 logger.debug(f"[TASK] Extracted short_summary: '{short_summary_log}'")
                 logger.debug(f"[TASK] Extracted medium_summary: '{medium_summary_log}'")
                 logger.debug(f"[TASK] Extracted suggestions_data: {suggestions_data}")

                 suggestions_saved_count = 0 # Zähler für erfolgreich gespeicherte Vorschläge
                 newly_created_suggestion_ids = [] # Liste für IDs neuer Vorschläge

                 # --> Punkt 10: Speichere neue Vorschläge
                 with transaction.atomic(): # Stelle sicher, dass alle Vorschläge oder keiner gespeichert werden
                     for suggestion_data in suggestions_data:
                         if isinstance(suggestion_data, dict) and \
                            'intent_summary' in suggestion_data and \
                            'subject' in suggestion_data and \
                            'reply_text' in suggestion_data:

                             intent = suggestion_data.get('intent_summary', '').strip()
                             subject = suggestion_data.get('subject', '').strip()
                             content = suggestion_data.get('reply_text', '').strip()
                             
                             # Skip suggestions with empty reply_text as they might not be useful
                             if not content:
                                 logger.warning(f"[TASK] Skipping suggestion for email {email.id} because reply_text is empty. Intent: '{intent}', Subject: '{subject}'")
                                 continue
                             
                             processing_start_time = time.time() # Reset timer for each suggestion? Or use overall?
                             suggestion_processing_time = time.time() - processing_start_time
                             
                             # Truncate intent and title BEFORE using them
                             MAX_TITLE_LENGTH = 100
                             MAX_INTENT_LENGTH = 100
                             original_intent = intent
                             original_title_base = intent # Title is based on intent
                             
                             if len(intent) > MAX_INTENT_LENGTH:
                                 intent = intent[:MAX_INTENT_LENGTH]
                                 logger.warning(f"[TASK] Truncated intent_summary from {len(original_intent)} to {len(intent)} chars for email {email.id}. Original: '{original_intent[:110]}...' ")
                             
                             # Derive title from potentially truncated intent or content
                             title = intent if intent else (content[:80] + '...' if len(content) > 80 else content)
                             if len(title) > MAX_TITLE_LENGTH:
                                 original_title = title
                                 title = title[:MAX_TITLE_LENGTH]
                                 logger.warning(f"[TASK] Truncated title from {len(original_title)} to {len(title)} chars for email {email.id}. Original: '{original_title[:110]}...' ")

                             # Log data being saved
                             logger.debug(f"[TASK] Creating AISuggestion - Email: {email.id}, Type: 'reply', Title: '{title}', Content: '{content[:50]}...', Intent: '{intent}', Subject: '{subject}'")

                             new_suggestion = AISuggestion.objects.create(
                                 email=email,
                                 type='reply',
                                 title=title, # Use truncated title
                                 content=content,
                                 intent_summary=intent, # Use truncated intent
                                 suggested_subject=subject,
                                 processing_time=suggestion_processing_time, 
                             )
                             newly_created_suggestion_ids.append(new_suggestion.id)
                             logger.info(f"[TASK] Created suggestion {new_suggestion.id} for email {email.id}")
                             suggestions_saved_count += 1
                         else:
                             logger.warning(f"[TASK] Ungültigen Vorschlag von {prompt_details['provider']} übersprungen für Email {email.id}: {suggestion_data}")

                     # Speichere auch die Zusammenfassungen im Email-Objekt
                     email.short_summary = api_response_data.get('short_summary', '').strip()
                     email.medium_summary = api_response_data.get('medium_summary', '').strip()

                     # Markiere E-Mail als erfolgreich verarbeitet NUR wenn Vorschläge erstellt wurden
                     if suggestions_saved_count > 0:
                         ai_processed = True
                         ai_processed_at = timezone.now()

                         # Update Email fields
                         email.short_summary = api_response_data.get('short_summary')
                         
                         # --- Truncate medium_summary if needed --- 
                         medium_summary_raw = api_response_data.get('medium_summary')
                         max_len_medium = Email._meta.get_field('medium_summary').max_length
                         if medium_summary_raw and len(medium_summary_raw) > max_len_medium:
                             email.medium_summary = medium_summary_raw[:max_len_medium - 5] + ' [...]' # Truncate and add indicator
                             logger.warning(f"[TASK] Truncated medium_summary for email {email.id} from {len(medium_summary_raw)} to {max_len_medium} chars.")
                         else:
                             email.medium_summary = medium_summary_raw
                         # --- End Truncation --- 
                         
                         email.ai_processed = ai_processed
                         email.ai_processed_at = ai_processed_at
                         email.save(update_fields=['ai_processed', 'ai_processed_at', 'short_summary', 'medium_summary', 'updated_at'])
                         logger.info(f"[TASK] Email {email.id} als AI-verarbeitet markiert, da {len(suggestions_data)} Vorschläge erstellt wurden.")
                         
                         # Send suggestions via WebSocket AFTER successful DB save
                         if suggestions_saved_count > 0:
                             try:
                                 channel_layer = get_channel_layer()
                                 if channel_layer:
                                     group_name = f'user_{user.id}_events'
                                     # Hole die neu erstellten Suggestion-Objekte
                                     new_suggestions = AISuggestion.objects.filter(id__in=newly_created_suggestion_ids)
                                     # Serialisiere die Daten
                                     serializer = AISuggestionSerializer(new_suggestions, many=True)
                                     serialized_suggestions = serializer.data
                                     
                                     # Nachricht mit korrektem Typ und Daten erstellen
                                     message_data = {
                                         'type': 'email.updated', # Allgemeiner Typ
                                         'data': {
                                             'email_id': email.id
                                         }
                                     }
                                     logger.info(f"[TASK] Sending '{message_data['type']}' to group {group_name} for email {email.id} with {len(serialized_suggestions)} suggestions.")
                                     async_to_sync(channel_layer.group_send)(group_name, message_data)
                                     logger.info(f"[TASK] WebSocket message sent successfully to {group_name}.")
                                 else:
                                     logger.error("[TASK] Channel layer is None. Cannot send WebSocket notification.")
                             except Exception as ws_err:
                                 logger.error(f"[TASK] Error sending WebSocket notification for email {email.id}: {ws_err}", exc_info=True)
                         # --- Ende KORREKTE WebSocket Benachrichtigung ---

                         # Log success only if suggestions were actually saved
                         if suggestions_saved_count > 0:
                              logger.info(f"[TASK Success] {suggestions_saved_count} AI suggestions successfully generated and saved for Email ID: {email.id}")
                         # else: The warning about no suggestions saved was logged above
                         
                     # Entferne den Lock nach erfolgreicher Verarbeitung
                     cache.delete(cache_key)

            else:
                 logger.error(f"[TASK] Unerwartetes Format der {prompt_details['provider']}-Antwort für Email {email.id}: {api_response_str}")
                 email.ai_processed = False # Nicht erfolgreich
                 email.ai_processed_at = timezone.now()
                 email.save(update_fields=['ai_processed', 'ai_processed_at'])
                 cache.delete(cache_key)
                 return f"Error: Unexpected response format from {prompt_details['provider']} API for email {email.id}."

        except json.JSONDecodeError as json_err:
            logger.error(f"[TASK Failure] Fehler beim Parsen der {prompt_details['provider']} JSON-Antwort für Email {email_id}. Antwort: {repr(api_response_str)}", exc_info=True)
            # Markiere E-Mail als verarbeitet (mit Fehler)
            try:
                email = Email.objects.get(id=email_id)
                email.ai_processed = False
                email.ai_processed_at = timezone.now()
                email.save(update_fields=['ai_processed', 'ai_processed_at'])
            except Email.DoesNotExist:
                logger.warning(f"[TASK] Email {email_id} konnte zum Setzen des JSON-Fehlerstatus nicht gefunden werden.")
            
            # Kein Retry hier, da das Modell wahrscheinlich wieder ungültiges JSON liefert.
            # Stattdessen den Task als fehlgeschlagen markieren und beenden.
            cache.delete(f"ai_suggestion_lock_email_{email_id}") # Lock entfernen
            # Rückgabe einer Fehlermeldung, oder raise einer spezifischen Exception?
            # Wir geben hier eine Fehlermeldung zurück, Celery sollte den Task als FAILURE werten.
            return f"Error: Failed to parse {prompt_details['provider']} JSON response for email {email.id}. Details: {json_err}"

    except Exception as e:
        # --> Punkt 14: Allgemeine Fehlerbehandlung im Task (bleibt bestehen)
        logger.error(f"[TASK Failure] Fehler bei der AI-Vorschlagsgenerierung für Email ID: {email_id}. Fehler: {e}", exc_info=True)
        # Markiere als nicht erfolgreich, falls möglich
        try:
             email = Email.objects.get(id=email_id)
             email.ai_processed = False
             email.ai_processed_at = timezone.now()
             email.save(update_fields=['ai_processed', 'ai_processed_at'])
        except Email.DoesNotExist:
             logger.warning(f"[TASK] Email {email_id} konnte zum Setzen des Fehlerstatus nicht gefunden werden.")
        
        # Lösche den Lock bei Fehlern, um erneute Versuche zu ermöglichen
        cache.delete(f"ai_suggestion_lock_email_{email_id}")

        # Erneutes Auslösen für Retry-Mechanismus von Celery
        try:
            # Wirft die Exception erneut, damit Celery den Retry handhabt
            self.retry(exc=e) 
        except MaxRetriesExceededError:
            logger.error(f"[TASK] Max retries exceeded for AI suggestion generation for email {email.id}.")
            # Endgültiger Fehlerstatus zurückgeben
            return f"Error: Max retries exceeded for AI suggestion generation for email {email.id}. Last error: {e}"
        except Exception as retry_e: # Falls self.retry selbst einen Fehler wirft
            logger.error(f"[TASK] Exception during retry mechanism for email {email.id}: {retry_e}", exc_info=True)
            return f"Error during retry mechanism: {retry_e}"

    finally:
        # Berechne und logge die Dauer
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"[TASK End] Finished AI suggestion generation for Email ID: {email.id}. Duration: {duration:.2f} seconds.")

# Task zum Generieren von Embeddings für eine E-Mail
@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def generate_embeddings_for_email(self, email_id: int):
    logger.info(f"--- START: generate_embeddings_for_email for Email ID {email_id} ---")
    start_time = time.time()
    email = None # Initialize email
    try:
        # Lade E-Mail mit zugehörigen Anhängen
        email = Email.objects.prefetch_related('attachments').select_related('account').get(id=email_id)
        logger.info(f"Starte Embedding-Generierung für Email ID {email_id} (Betreff: {email.subject[:50]}...)")

        # 1. Embeddings generieren und in Qdrant speichern
        logger.info(f"[Schritt 1/2] Generiere E-Mail-Embedding für ID {email_id}")
        generate_email_embedding(email)

        logger.info(f"[Schritt 2/2] Generiere Attachment-Embeddings für ID {email_id}")
        attachments_processed = 0
        for attachment in email.attachments.all():
            logger.debug(f"Verarbeite Anhang ID {attachment.id} für E-Mail {email_id}")
            generate_attachment_embedding(attachment)
            attachments_processed += 1
        logger.info(f"{attachments_processed} Anhänge für Email ID {email_id} für Embeddings verarbeitet.")

        # KEIN AI_PROCESSED Flag hier setzen

    except Email.DoesNotExist:
        logger.error(f"Email mit ID {email_id} nicht gefunden für Embedding-Generierung.")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler in generate_embeddings_for_email für ID {email_id}: {e}", exc_info=True)
        # Hier kein ai_processed Flag ändern
    finally:
        logger.info(f"--- END: generate_embeddings_for_email for Email ID {email_id} ---")
        # finally Block nicht mehr nötig für Gesamtdauer, da nur Embeddings

# Alte Funktion - wird durch die neuen Funktionen ersetzt
# def process_email_with_ai(email_id: int):
#    pass # Leave the old function definition commented out or remove it

# Alte Funktionen entfernen
# def process_attachment(attachment_id): 
#    pass

# def call_groq_api(prompt):
#    pass 

# --- Add the new correction task ---

# --- Ende der neuen Korrektur-Task ---

# --- NEUE TASK: API Key Check ---
@shared_task(bind=True, max_retries=1) # Wenig Sinn in Retries hier
def check_api_key_task(self, user_id: int, provider: str, api_key: str):
    """Checks the validity of an API key and sends status via WebSocket."""
    logger.info(f"Starting API key check task for user {user_id}, provider {provider}.")
    status_to_send = 'checking' # Initial status
    message_to_send = f'Checking {provider} API key...'
    
    channel_layer = get_channel_layer()
    group_name = f'user_{user_id}_events'

    def send_status(check_status, message):
        if channel_layer:
             logger.info(f"Sending WS status '{check_status}' for {provider} to {group_name}: {message}")
             async_to_sync(channel_layer.group_send)(
                 group_name,
                 {
                     'type': 'api_key_status', # Match consumer handler
                     'data': {
                         'provider': provider,
                         'status': check_status,
                         'message': message,
                     }
                 }
             )
        else:
            logger.error("Cannot send WS status update: Channel layer not available.")

    # Send initial 'checking' status
    send_status(status_to_send, message_to_send)

    try:
        # Führe den eigentlichen Check durch (ähnlich wie in der View)
        # Diese Logik sollte idealerweise ausgelagert werden, aber hier als Beispiel:
        if provider == 'google_gemini':
            try:
                # Verwende den übergebenen api_key!
                genai.configure(api_key=api_key) 
                _ = genai.list_models()
                status_to_send = 'valid'
                message_to_send = f'Google Gemini API key is valid.'
                logger.info(f"Google Gemini key check successful for user {user_id}.")

                # -------- NEU: Modelle für Gemini abrufen und speichern --------
                try:
                    logger.info(f"Attempting to fetch and store Google Gemini models for user {user_id}.")
                    # -- NEU: API-Aufruf und direktes Logging --
                    raw_gemini_response = None
                    try:
                        raw_gemini_response = genai.list_models()
                        logger.info(f"Successfully called genai.list_models(). Response type: {type(raw_gemini_response)}")
                        # Logge die rohe Antwort so gut wie möglich
                        logger.debug(f"Raw Gemini models response content: {raw_gemini_response!r}")
                    except Exception as api_call_err:
                        logger.error(f"Error calling genai.list_models(): {api_call_err}", exc_info=True)
                        raise # Fehler weitergeben, damit der äußere Block ihn fängt
                    # -- ENDE NEU --
                        
                    # Verarbeite die Antwort nur, wenn sie nicht None ist
                    if raw_gemini_response is None:
                         logger.error("genai.list_models() returned None or failed. Skipping model processing.")
                         raise ValueError("Failed to retrieve models from Gemini API")

                    # Konvertiere zu Liste für weitere Verarbeitung und Logging
                    try:
                        gemini_models_list = list(raw_gemini_response)
                        logger.debug(f"Converted Gemini response to list. Count: {len(gemini_models_list)}. Content: {gemini_models_list!r}")
                    except Exception as list_conv_err:
                        logger.error(f"Error converting Gemini response to list: {list_conv_err}", exc_info=True)
                        raise # Fehler weitergeben

                    # Stelle sicher, dass es iterierbar ist (redundant nach list(), aber sicher ist sicher)
                    # if not hasattr(gemini_models_list, '__iter__'):
                    #      logger.error(f"Gemini models response is not iterable: {type(gemini_models_list)}")
                    #      raise TypeError("Gemini models response is not iterable")
                    
                    # Model direkt importieren
                    # from mailmind.core.models import AvailableApiModel # Oben verschoben
                    
                    models_saved_count = 0
                    current_model_ids = set() # Sammle die aktuellen IDs
                    
                    with transaction.atomic():
                        for model_info in gemini_models_list: # Direkt über die Liste iterieren
                            # Das Gemini Model-Objekt hat Attribute wie name und display_name
                            model_id = getattr(model_info, 'name', None) # z.B. 'models/gemini-pro'
                            display_name = getattr(model_info, 'display_name', None) # z.B. 'Gemini Pro'
                            
                            if model_id:
                                # Verwende display_name wenn vorhanden, sonst model_id als Name
                                model_name_to_save = display_name if display_name else model_id 
                                
                                # Extrahiere den kürzeren ID-Teil (optional, aber oft benutzerfreundlicher)
                                simple_model_id = model_id.split('/')[-1] if '/' in model_id else model_id
                                logger.debug(f"Processing Gemini model: ID='{model_id}', SimpleID='{simple_model_id}', Name='{model_name_to_save}'")
                                
                                obj, created = AvailableApiModel.objects.update_or_create(
                                    provider=provider,
                                    model_id=simple_model_id, # Speichere die einfache ID
                                    defaults={
                                        'model_name': model_name_to_save,
                                        'discovered_at': timezone.now(),
                                    }
                                )
                                models_saved_count += 1
                                current_model_ids.add(simple_model_id) # Füge die gespeicherte ID hinzu
                            else:
                                logger.warning(f"Skipping Gemini model due to missing 'name' attribute: {model_info!r}")

                        # Lösche veraltete Gemini-Modelle
                        deleted_count, _ = AvailableApiModel.objects.filter(provider=provider).exclude(model_id__in=current_model_ids).delete()
                        if deleted_count > 0:
                            logger.info(f"Deleted {deleted_count} stale Gemini models from DB for user {user_id}.")
                            
                    logger.info(f"Successfully saved/updated {models_saved_count} Google Gemini models for user {user_id}.")
                    
                except Exception as e_models:
                    logger.error(f"Failed to fetch or save Google Gemini models for user {user_id} after successful key check: {e_models}", exc_info=True)
                    message_to_send = f'Google Gemini API key is valid, but failed to retrieve/store model list: {e_models}'
                # -------- ENDE NEU --------
                    
            except (google_exceptions.PermissionDenied, google_exceptions.InvalidArgument) as e:
                status_to_send = 'invalid'
                message_to_send = f'Google Gemini API key is invalid or lacks permissions: {str(e)}'
                logger.warning(f"Google Gemini key check failed (Invalid) for user {user_id}: {str(e)}")
            except google_exceptions.GoogleAPIError as e:
                 status_to_send = 'error'
                 message_to_send = f'Error communicating with Google Gemini API: {str(e)}'
                 logger.error(f"Google Gemini key check failed (API Error) for user {user_id}: {str(e)}")
            except Exception as e:
                status_to_send = 'error'
                message_to_send = f'Unexpected error checking Google Gemini key: {str(e)}'
                logger.error(f"Unexpected error during Google Gemini check for user {user_id}: {str(e)}", exc_info=True)

        elif provider == 'groq':
            http_client = None # Initialize http_client variable
            try:
                # Verwende den übergebenen api_key!
                # Erstelle explizit einen httpx Client ohne Umgebungsvariablen (Proxies)
                http_client = httpx.Client(trust_env=False, timeout=10.0)
                client = Groq(api_key=api_key, http_client=http_client)
                _ = client.models.list()
                status_to_send = 'valid'
                message_to_send = f'Groq API key is valid.'
                logger.info(f"Groq key check successful for user {user_id}.")
                
                # -------- NEU: Modelle abrufen und speichern --------
                try:
                    logger.info(f"Attempting to fetch and store Groq models for user {user_id}.")
                    models_response = client.models.list() # Hole die gesamte Antwort zuerst
                    logger.debug(f"Raw Groq models response type: {type(models_response)}, content: {models_response!r}")
                    
                    # Prüfe, ob .data existiert und eine Liste ist
                    if hasattr(models_response, 'data') and isinstance(models_response.data, list):
                        models_list = models_response.data
                        logger.info(f"Extracted {len(models_list)} models from response data.")
                    elif isinstance(models_response, list): # Fallback: Antwort IST die Liste
                        models_list = models_response
                        logger.info(f"Groq response is directly a list of {len(models_list)} models.")
                    else:
                        logger.error(f"Unexpected Groq models response structure: {type(models_response)}. Cannot extract model list.")
                        raise TypeError("Unexpected Groq models response structure")
                        
                    # Logge das erste Modell zur Prüfung der Attribute (falls vorhanden)
                    if models_list:
                        logger.debug(f"First model object details: {models_list[0]!r}")
                        if not hasattr(models_list[0], 'id'):
                             logger.warning("First model object does not have an 'id' attribute!")

                    # Importiere das benötigte Model (redundant, da oben verschoben)
                    # from mailmind.core.models import AvailableApiModel 
                    
                    models_saved_count = 0
                    with transaction.atomic(): # Stelle atomares Speichern sicher
                        # Lösche alte Modelle für diesen Provider, bevor neue gespeichert werden
                        # Das stellt sicher, dass nur aktuell verfügbare Modelle angezeigt werden
                        # deleted_count, _ = AvailableApiModel.objects.filter(provider=provider).delete()
                        # logger.debug(f"Deleted {deleted_count} old Groq models before saving new ones.")
                        # BESSER: Update oder Create verwenden, um Löschen zu vermeiden und 
                        # discovered_at zu aktualisieren
                        
                        # Hole alle IDs der aktuell gefundenen Modelle
                        current_model_ids = {model.id for model in models_list if hasattr(model, 'id')}
                        
                        # Aktualisiere vorhandene oder erstelle neue Modelle
                        for model_info in models_list:
                            if hasattr(model_info, 'id'):
                                obj, created = AvailableApiModel.objects.update_or_create(
                                    provider=provider,
                                    model_id=model_info.id,
                                    defaults={
                                        'model_name': getattr(model_info, 'name', model_info.id), # Fallback Name
                                        'discovered_at': timezone.now(),
                                        # Füge hier ggf. weitere Felder hinzu, falls die API sie liefert
                                    }
                                )
                                models_saved_count += 1
                                # logger.debug(f"Saved/Updated Groq model: {obj.model_id} (Created: {created})")
                        
                        # Lösche Modelle aus der DB, die nicht mehr von der API zurückgegeben wurden
                        deleted_count, _ = AvailableApiModel.objects.filter(provider=provider).exclude(model_id__in=current_model_ids).delete()
                        if deleted_count > 0:
                            logger.info(f"Deleted {deleted_count} stale Groq models from DB for user {user_id}.")
                            
                    logger.info(f"Successfully saved/updated {models_saved_count} Groq models for user {user_id}.")
                    
                except Exception as e_models:
                    logger.error(f"Failed to fetch or save Groq models for user {user_id} after successful key check: {e_models}", exc_info=True)
                    # Der Key ist gültig, aber Modelle konnten nicht gespeichert werden.
                    # Sende trotzdem 'valid', aber logge den Fehler deutlich.
                    message_to_send = f'Groq API key is valid, but failed to retrieve/store model list: {e_models}'
                # -------- ENDE NEU --------
                    
            except AuthenticationError as e:
                status_to_send = 'invalid'
                message_to_send = f'Groq API key is invalid: {str(e)}'
                logger.warning(f"Groq key check failed (Invalid) for user {user_id}: {str(e)}")
            except APIConnectionError as e:
                status_to_send = 'error'
                message_to_send = f'Error connecting to Groq API: {str(e)}'
                logger.error(f"Groq key check failed (Connection Error) for user {user_id}: {str(e)}")
            except Exception as e:
                status_to_send = 'error'
                message_to_send = f'Unexpected error checking Groq key: {str(e)}'
                logger.error(f"Unexpected error during Groq check for user {user_id}: {str(e)}", exc_info=True)
            finally:
                 # Stelle sicher, dass der Client geschlossen wird
                 if http_client:
                      http_client.close()
                      logger.debug(f"Closed httpx client for Groq check in task for user {user_id}.")

        else:
            status_to_send = 'error'
            message_to_send = f'API key check not implemented for provider: {provider}'
            logger.error(message_to_send)

    except Exception as e:
        status_to_send = 'error'
        message_to_send = f'An unexpected error occurred during the check task: {str(e)}'
        logger.error(f"General error in check_api_key_task for user {user_id}, provider {provider}: {e}", exc_info=True)

    finally:
        # Send final status
        send_status(status_to_send, message_to_send)

        logger.info(f"[TASK End] Finished API key check for User ID: {user_id}, Provider: {provider}. Final Status: {status_to_send}")
        # Gib den finalen Status zurück
        return f"Check complete for {provider}. Status: {status_to_send}"

# --- ENDE NEUE TASK --- 