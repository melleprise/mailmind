#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Funktion zum Überprüfen der Postgres-Verbindung
wait_for_postgres() {
# ... existing code ...
}

# Funktion zum Überprüfen der Redis-Verbindung
wait_for_redis() {
# ... existing code ...
}

echo "--- DEBUG: Checking Cache before download script --- (worker)"
echo "SENTENCE_TRANSFORMERS_HOME Env Var: $SENTENCE_TRANSFORMERS_HOME"
echo "Listing contents of /root/.cache/torch/sentence_transformers:"
ls -la /root/.cache/torch/sentence_transformers || echo "Cache directory not found or empty."
echo "--- DEBUG: End Cache Check --- (worker)"

# Überprüfe und lade ML-Modelle beim Start, falls nötig
echo "Checking/Downloading ML models (worker)..."
python /app/download_models.py
echo "ML model check complete (worker)."


# Starte den Django Q Cluster Worker
echo "Starting QCluster..."
# ... existing code ... 