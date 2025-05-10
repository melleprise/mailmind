import os
import logging
from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)

# Globale Variable auf Modulebene, um das geladene Modell zu halten
# Wird nur gefüllt, wenn im Worker-Kontext geladen wird.
# LOADED_TEXT_MODEL = None # Wieder auskommentieren

class AiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mailmind.ai'

    def ready(self):
        """
        Diese Methode wird beim Django-Start aufgerufen.
        Prüft, ob Modelle im Worker geladen werden sollen (ENV Variable).
        Das eigentliche Laden geschieht jetzt bei Bedarf in den get_... Funktionen in tasks.py.
        """
        # global LOADED_TEXT_MODEL # Auskommentieren
        
        load_models = os.getenv('LOAD_AI_MODELS', 'false').lower() == 'true'
        
        if load_models:
            logger.info(f"LOAD_AI_MODELS=true erkannt. Modelle werden bei Bedarf im Worker geladen (z.B. in tasks.py).") # Log anpassen
            
            # Lade Text-Modell - Hier nicht mehr laden
            # try:
            # from sentence_transformers import SentenceTransformer
            # model_name = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
            
            # # Explizit den Cache-Ordner übergeben
            # cache_folder = os.getenv('SENTENCE_TRANSFORMERS_HOME')
            # if cache_folder:
            #      logger.info(f"[apps.ready] Using explicit cache folder: {cache_folder}")
            #      # LOADED_TEXT_MODEL = SentenceTransformer(model_name, cache_folder=cache_folder)
            # else:
            #      logger.warning("[apps.ready] SENTENCE_TRANSFORMERS_HOME not set, relying on default cache.")
            #      # LOADED_TEXT_MODEL = SentenceTransformer(model_name)
            # 
            # logger.info(f"Text-Modell {model_name} erfolgreich in AiConfig.ready() geladen.")
            # except ImportError:
            #      logger.error("sentence-transformers ist nicht installiert.")
            #      # LOADED_TEXT_MODEL = None
            # except Exception as e:
            #     logger.error(f"Fehler beim Laden des Text-Modells in AiConfig.ready(): {e}", exc_info=True)
            #     # LOADED_TEXT_MODEL = None
            #     # Optional: Fehler weiterwerfen, um Start zu verhindern?
            #     # raise RuntimeError(f"Konnte Text-Modell nicht laden: {e}")

        else:
            logger.info("LOAD_AI_MODELS ist nicht auf 'true' gesetzt. Überspringe Modell-Laden in AiConfig.ready().")

# Funktion, um das Modell sicher abzurufen (wird von tasks.py verwendet)
# def get_loaded_text_model(): # Wieder auskommentieren
#     # if LOADED_TEXT_MODEL is None:
#     #     # Dieser Fall sollte im Worker nicht auftreten, wenn das Laden in ready() erfolgreich war.
#     #     # Im Backend-Prozess ist das der Normalfall.
#     #     logger.warning("Text-Modell wurde nicht vorab geladen (LOADED_TEXT_MODEL is None).")
#     #     # Fehler auslösen, wenn im Worker-Kontext erwartet, aber nicht geladen?
#     #     if os.getenv('LOAD_AI_MODELS', 'false').lower() == 'true':
#     #          raise RuntimeError("Text-Modell sollte im Worker-Kontext geladen sein, ist aber None!")
#     #     return None 
#     # return LOADED_TEXT_MODEL 