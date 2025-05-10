import logging
import os
# Entferne SentenceTransformer Import, da wir nur herunterladen
# from sentence_transformers import SentenceTransformer
from huggingface_hub import snapshot_download # Importiere snapshot_download

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Definiere den Cache-Pfad BASIEREND AUF ENV Variablen (wie im Container gesetzt)
HF_HOME = os.getenv('HF_HOME') # Wird durch docker-compose gesetzt
# SENTENCE_TRANSFORMERS_HOME wird oft relativ zu HF_HOME erwartet oder kann explizit gesetzt sein
DEFAULT_ST_CACHE = os.path.join(HF_HOME, 'hub') if HF_HOME else None
CACHE_DIR = os.getenv('SENTENCE_TRANSFORMERS_HOME', DEFAULT_ST_CACHE)

if not CACHE_DIR:
    # Fallback, falls HF_HOME nicht gesetzt ist (sollte im Container nicht passieren)
    CACHE_DIR = os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub") 
    logger.warning(f"HF_HOME nicht gesetzt, verwende Fallback-Cache: {CACHE_DIR}")

# Stelle sicher, dass der Cache-Pfad existiert
try:
    os.makedirs(CACHE_DIR, exist_ok=True)
    logger.info(f"Verwende Cache-Verzeichnis für Downloads: {CACHE_DIR}")
except OSError as e:
    logger.error(f"Konnte Cache-Verzeichnis nicht erstellen/zugreifen: {CACHE_DIR} - Fehler: {e}")
    # Hier ggf. abbrechen oder mit Fehler fortfahren?
    CACHE_DIR = None # Verhindert Downloadversuch

# Liste der Modelle, die heruntergeladen werden sollen
MODELS_TO_DOWNLOAD = [
    # 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2', # Großes Modell auskommentiert
    'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2', # Kleineres Modell hinzugefügt
    # Füge hier weitere Modelle hinzu, falls benötigt
    # 'openai/clip-vit-base-patch32' # Beispiel
]

def download_models_to_cache():
    if not CACHE_DIR:
        logger.error("Kein gültiges Cache-Verzeichnis verfügbar. Überspringe Download.")
        return
        
    logger.info(f"Starte Download der benötigten ML-Modelldateien nach {CACHE_DIR}...")
    for repo_id in MODELS_TO_DOWNLOAD:
        # Prüfe, ob das Modell bereits im Cache existiert (vereinfachte Prüfung)
        # snapshot_download prüft intern detaillierter, aber eine Vorabprüfung schadet nicht
        model_folder_name = 'models--' + repo_id.replace('/', '--')
        expected_model_path = os.path.join(CACHE_DIR, model_folder_name)
        
        if os.path.exists(expected_model_path):
            logger.info(f"Modell-Verzeichnis {expected_model_path} existiert bereits. Überspringe Download für {repo_id}.")
            continue
            
        try:
            logger.info(f"Starte Download für: {repo_id} nach {CACHE_DIR}...")
            snapshot_download(
                repo_id=repo_id,
                cache_dir=CACHE_DIR, # Nutze den ermittelten Cache-Pfad
                local_dir_use_symlinks=False,
                resume_download=True,
            )
            logger.info(f"Dateien für {repo_id} erfolgreich heruntergeladen/im Cache: {CACHE_DIR}.")
        except Exception as e:
            logger.error(f"Fehler beim Download von Modell {repo_id}: {e}", exc_info=True)
            # Hier nicht abbrechen, damit Entrypoint weitermachen kann
            # raise e 

if __name__ == "__main__":
    # Dieser Teil wird normalerweise nicht mehr direkt aufgerufen,
    # sondern das Skript wird vom Entrypoint importiert oder aufgerufen.
    # Wir behalten es für potenzielle manuelle Ausführung auf dem Host.
    download_models_to_cache()
    logger.info("Download-Prozess für Modelldateien abgeschlossen.") 