from sentence_transformers import SentenceTransformer
import logging

MODEL_NAME = 'paraphrase-multilingual-MiniLM-L12-v2'

logger = logging.getLogger(__name__)

def download_models():
    """Download required ML models."""
    try:
        logger.info(f"Lade Modell: {MODEL_NAME}...")
        model = SentenceTransformer(MODEL_NAME)
        logger.info(f"Modell '{MODEL_NAME}' erfolgreich geladen/überprüft.")
        return model
    except Exception as e:
        logger.error(f"Error downloading model: {e}")
        raise

if __name__ == "__main__":
    download_models() 