import logging
import os
import sys
import time

# Configure basic logging to see output
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("--- Starting embedding test script ---")

# Explicitly set OMP_NUM_THREADS=1 for this test
os.environ['OMP_NUM_THREADS'] = '1'
logger.info(f"OMP_NUM_THREADS explicitly set to: {os.environ.get('OMP_NUM_THREADS')}")

try:
    logger.info("Importing SentenceTransformer...")
    time.sleep(1) # Short pause
    from sentence_transformers import SentenceTransformer
    logger.info("SentenceTransformer imported successfully.")

    model_name = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
    logger.info(f"Attempting to instantiate SentenceTransformer: {model_name}...")
    instantiation_start = time.time()

    # Entferne low_cpu_mem_usage, da ungültig für SentenceTransformer
    model = SentenceTransformer(model_name)

    instantiation_end = time.time()
    logger.info(f"SentenceTransformer model instantiated successfully in {instantiation_end - instantiation_start:.2f} seconds.")

    test_sentence = "Das ist ein einfacher Testtext für die manuelle Überprüfung."
    logger.info(f"Encoding test sentence: '{test_sentence}'")
    encoding_start = time.time()

    embedding = model.encode(test_sentence)

    encoding_end = time.time()
    logger.info(f"Encoding successful in {encoding_end - encoding_start:.2f} seconds.")
    logger.info(f"Embedding type: {type(embedding)}")
    if hasattr(embedding, 'shape'):
        logger.info(f"Embedding shape: {embedding.shape}") # type: ignore
    else:
        logger.warning("Could not determine embedding shape.")
    # logger.info(f"Embedding snippet: {embedding[:10]}") # Optionally print part of it

    logger.info("--- Embedding test script finished successfully ---")
    sys.exit(0) # Explicitly exit with success code

except Exception as e:
    logger.error(f"An error occurred during the test script: {e}", exc_info=True)
    logger.info("--- Embedding test script failed ---")
    sys.exit(1) # Explicitly exit with error code 