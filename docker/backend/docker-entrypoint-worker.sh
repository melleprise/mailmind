#!/bin/bash
set -e

# Warte auf PostgreSQL
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "Postgres is up."

# --- Modell-Download-Prüfung entfernt --- 
# Der Download wird jetzt durch den 'model_downloader'-Service sichergestellt,
# auf den dieser Worker mittels 'depends_on' wartet.
# Das Modell sollte im gemounteten Cache-Verzeichnis vorhanden sein.
# ----------------------------------------

>&2 echo "Starting QCluster..."

# Starte den QCluster
exec python manage.py qcluster 