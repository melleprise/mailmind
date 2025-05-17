#!/bin/bash
set -e

export PYTHONWARNINGS="ignore:Retry and timeout are misconfigured:UserWarning"

# Warte auf PostgreSQL
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c '\q'; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "Postgres is up - executing migrations"

# Führe Migrationen aus
python -W "ignore:Retry and timeout are misconfigured:UserWarning" manage.py migrate --noinput

# Lade initiale Daten (Prompt Templates)
# Der Fixture-Name entspricht dem Dateinamen ohne Endung
>&2 echo "Loading initial prompt templates..."
python -W "ignore:Retry and timeout are misconfigured:UserWarning" manage.py loaddata prompt_templates

# Erstelle/Aktualisiere Superuser mit dem Management-Befehl
python -W "ignore:Retry and timeout are misconfigured:UserWarning" manage.py ensure_superuser

# Starte den eigentlichen Server (Hauptprozess) mit Daphne
>&2 echo "Starting Daphne ASGI server..."
python -W "ignore:Retry and timeout are misconfigured:UserWarning" -m daphne -b 0.0.0.0 -p 8000 mailmind.asgi:application 