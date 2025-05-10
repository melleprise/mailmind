#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Funktion zum Überprüfen der Postgres-Verbindung
wait_for_postgres() {
# ... existing code ...

echo "--- DEBUG: Checking Cache before download script --- (backend)"
echo "SENTENCE_TRANSFORMERS_HOME Env Var: $SENTENCE_TRANSFORMERS_HOME"
echo "Listing contents of /root/.cache/torch/sentence_transformers:"
ls -la /root/.cache/torch/sentence_transformers || echo "Cache directory not found or empty."
echo "--- DEBUG: End Cache Check --- (backend)"

# Überprüfe und lade ML-Modelle beim Start, falls nötig
echo "Checking/Downloading ML models..."
python /app/download_models.py
echo "ML model check complete."

# Führe Django-Management-Befehle aus (z.B. Migrationen)
echo "Running Django migrations..."
python manage.py migrate
echo "Migrations complete."

# } # ENDE DER FUNKTION (falls vorhanden und hier platziert war)

# Starte den ASGI Server mit Daphne (AUSSERHALB jeder Funktion)
echo "Starting Daphne ASGI server..."
exec daphne -b 0.0.0.0 -p 8000 mailmind.asgi:application 