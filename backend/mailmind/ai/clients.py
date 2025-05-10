import logging
import os
import sys
import gc
import torch
import google.generativeai as genai
from django.conf import settings
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient, models as qdrant_models
from groq import Groq
import httpx

logger = logging.getLogger(__name__)

_text_model = None
image_model = None
qdrant_client = None

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
            logger.info("SentenceTransformer library imported successfully.")

            model_name = 'sentence-transformers/all-MiniLM-L6-v2'
            logger.info(f"Attempting to instantiate SentenceTransformer with model: {model_name}...")

            cache_folder = os.getenv('SENTENCE_TRANSFORMERS_HOME')

            try:
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
                 logger.critical(f"!!! CRITICAL ERROR DURING SentenceTransformer INSTANTIATION: {model_load_e} !!!", exc_info=True)
                 sys.exit(f"Worker exiting due to model load failure: {model_load_e}")

        except ImportError:
             logger.error("sentence-transformers ist nicht installiert.", exc_info=True)
             raise RuntimeError("Fehler beim Laden des Text-Modells: sentence-transformers nicht installiert.")
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
            logger.debug("Versuche QdrantClient(url=..., api_key=...)")
            qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=20)
            logger.info("Qdrant Client erfolgreich initialisiert.")

            new_vector_size = 384

            email_collection_name = "email_embeddings"
            try:
                logger.debug(f"Prüfe Collection: {email_collection_name}")
                collection_info = qdrant_client.get_collection(collection_name=email_collection_name)
                current_vector_size = collection_info.config.params.vectors.size
                if current_vector_size != new_vector_size:
                    logger.warning(f"Vektorgröße in Qdrant Collection '{email_collection_name}' ({current_vector_size}) stimmt nicht mit dem neuen Modell ({new_vector_size}) überein! Alte Collection wird gelöscht.")
                    qdrant_client.delete_collection(collection_name=email_collection_name)
                    raise ValueError("Collection mit falscher Vektorgröße gelöscht.")
                logger.info(f"Qdrant Collection '{email_collection_name}' existiert bereits mit korrekter Größe {new_vector_size}.")
            except Exception as e_get_email:
                logger.warning(f"Collection {email_collection_name} nicht gefunden oder Fehler bei Prüfung/Größenabgleich: {e_get_email}. Versuche zu erstellen...")
                try:
                    logger.debug(f"Erstelle Collection: {email_collection_name} mit Vektorgröße {new_vector_size}")
                    qdrant_client.create_collection(
                        collection_name=email_collection_name,
                        vectors_config=qdrant_models.VectorParams(size=new_vector_size, distance=qdrant_models.Distance.COSINE)
                    )
                    logger.info(f"Collection {email_collection_name} erfolgreich erstellt.")
                except Exception as e_create_email:
                    logger.error(f"Fehler beim Erstellen der Collection {email_collection_name}: {e_create_email}", exc_info=True)
                    raise

            attachment_collection_name = "attachment_embeddings"
            attachment_vector_size = new_vector_size
            try:
                logger.debug(f"Prüfe Collection: {attachment_collection_name}")
                collection_info_attach = qdrant_client.get_collection(collection_name=attachment_collection_name)
                current_attach_vector_size = collection_info_attach.config.params.vectors.size
                if current_attach_vector_size != attachment_vector_size:
                    logger.warning(f"Vektorgröße in Qdrant Collection '{attachment_collection_name}' ({current_attach_vector_size}) stimmt nicht mit dem neuen Modell ({attachment_vector_size}) überein! Alte Collection wird gelöscht.")
                    qdrant_client.delete_collection(collection_name=attachment_collection_name)
                    raise ValueError("Collection mit falscher Vektorgröße gelöscht.")
                logger.info(f"Qdrant Collection '{attachment_collection_name}' existiert bereits mit korrekter Größe {attachment_vector_size}.")
            except Exception as e_get_attach:
                logger.warning(f"Collection {attachment_collection_name} nicht gefunden oder Fehler bei Prüfung/Größenabgleich: {e_get_attach}. Versuche zu erstellen...")
                try:
                    logger.debug(f"Erstelle Collection: {attachment_collection_name} mit Vektorgröße {attachment_vector_size}")
                    qdrant_client.create_collection(
                        collection_name=attachment_collection_name,
                        vectors_config=qdrant_models.VectorParams(size=attachment_vector_size, distance=qdrant_models.Distance.COSINE)
                    )
                    logger.info(f"Collection {attachment_collection_name} erfolgreich erstellt.")
                except Exception as e_create_attach:
                    logger.error(f"Fehler beim Erstellen der Collection {attachment_collection_name}: {e_create_attach}", exc_info=True)
                    raise

            logger.info("Qdrant Client verbunden und Collections initialisiert.")
        except Exception as e_init:
            logger.error(f"Fehler beim Initialisieren des Qdrant Clients: {e_init}", exc_info=True)
            raise
    return qdrant_client

def get_groq_client(api_key: str) -> Groq | None:
    """Initializes and returns a Groq client instance using the provided API key."""
    if not api_key:
        logger.error("Cannot initialize Groq client: API key is missing.")
        return None
    http_client = None # Initialize
    try:
        # Explicitly create httpx client, ignoring environment proxies
        logger.debug("Creating httpx client for Groq (trust_env=False)...")
        http_client = httpx.Client(trust_env=False, timeout=20.0)
        logger.debug("Initializing Groq client...")
        # Pass the explicit client
        client = Groq(api_key=api_key, http_client=http_client)
        logger.info("Groq client initialized successfully.")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Groq client: {e}", exc_info=True)
        # Ensure client is closed on error if initialized partially
        if http_client:
            try:
                http_client.close()
                logger.debug("Closed httpx client after initialization error.")
            except Exception as close_err:
                 logger.error(f"Error closing httpx client during exception handling: {close_err}", exc_info=True)
        return None

def get_gemini_model(model_name: str = 'gemini-1.5-flash'):
    """Erstellt und gibt eine Instanz des Gemini GenerativeModel zurück.
    
    Der API-Schlüssel muss separat über genai.configure() gesetzt werden,
    bevor API-Aufrufe mit dem zurückgegebenen Modell erfolgen.
    
    Args:
        model_name: Der Name des zu verwendenden Gemini-Modells.
        
    Returns:
        Eine Instanz von genai.GenerativeModel.
        
    Raises:
        Exception: Wenn das Modell nicht geladen werden kann.
    """
    try:
        logger.info(f"Erstelle Instanz des Gemini-Modells: {model_name}")
        model = genai.GenerativeModel(model_name)
        logger.info(f"Gemini-Modell Instanz '{model_name}' erstellt.")
        return model
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Gemini-Modell Instanz '{model_name}': {e}", exc_info=True)
        raise

def get_openai_model(model_name: str):
    """Placeholder function to get an OpenAI model instance."""
    logger.warning(f"OpenAI provider not yet implemented. Cannot get model: {model_name}")
    raise NotImplementedError("OpenAI provider support is not yet implemented.")
    # Example (requires openai library):
    # from openai import OpenAI
    # client = OpenAI(api_key=...)
    # return client # Or specific model interface if needed

def get_anthropic_model(model_name: str):
    """Placeholder function to get an Anthropic model instance."""
    logger.warning(f"Anthropic provider not yet implemented. Cannot get model: {model_name}")
    raise NotImplementedError("Anthropic provider support is not yet implemented.")
    # Example (requires anthropic library):
    # from anthropic import Anthropic
    # client = Anthropic(api_key=...)
    # return client # Or specific model interface if needed

def get_ai_model(provider: str, model_name: str):
    """Factory function to get an AI model instance based on the provider.
       Returns None for providers like Groq where the client is handled differently.
    """
    logger.info(f"Getting AI model object for provider: {provider}, model: {model_name}")
    if provider == 'google_gemini':
        return get_gemini_model(model_name=model_name)
    elif provider == 'openai':
        return get_openai_model(model_name=model_name)
    elif provider == 'anthropic':
        return get_anthropic_model(model_name=model_name)
    elif provider == 'groq':
        logger.debug(f"Groq provider does not require a specific model object here. Client handled separately.")
        return None
    else:
        logger.error(f"Unsupported AI provider specified in get_ai_model: {provider}")
        raise ValueError(f"Unsupported AI provider in get_ai_model: {provider}") 