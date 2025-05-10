#!/bin/bash

# Debug-Ausgabe für Umgebungsvariablen
echo "### DEBUG: Umgebungsvariablen ###"
echo "BACKEND_API_URL: $BACKEND_API_URL"
echo "DJANGO_SECRET_KEY existiert: $([ -n "$DJANGO_SECRET_KEY" ] && echo 'JA' || echo 'NEIN')"
echo "DJANGO_SECRET_KEY Länge: ${#DJANGO_SECRET_KEY}"
if [ -n "$DJANGO_SECRET_KEY" ]; then
  echo "DJANGO_SECRET_KEY Anfang: ${DJANGO_SECRET_KEY:0:5}..."
else
  echo "DJANGO_SECRET_KEY ist leer oder nicht gesetzt!"
  # Testweise manuelle Zuweisung
  export DJANGO_SECRET_KEY="django-insecure-8^3k9#m2p5@v7x1j4h6n8q0r2t4y6u8i0o2p4s6u8w0y2"
  echo "DJANGO_SECRET_KEY manuell gesetzt in start-script: ${DJANGO_SECRET_KEY:0:5}..."
fi
echo "#########################"

# Installiere zusätzliche Abhängigkeiten, falls erforderlich
if [ -f /app/crawl4ai/requirements.txt ]; then
  echo "Installiere zusätzliche Abhängigkeiten..."
  pip install -r /app/crawl4ai/requirements.txt
fi

# Warte auf das Backend
echo "Warte auf Backend..."
attempts=0
max_attempts=30
backend_url="${BACKEND_API_URL:-http://backend:8000}"

while ! curl -s "$backend_url/health" > /dev/null; do
  attempts=$((attempts + 1))
  if [ $attempts -ge $max_attempts ]; then
    echo "Backend ist nach $max_attempts Versuchen nicht erreichbar. Fahre trotzdem fort."
    break
  fi
  echo "Backend noch nicht erreichbar (Versuch $attempts/$max_attempts). Warte 5 Sekunden..."
  sleep 5
done

# Nochmals Umgebungsvariablen prüfen nach dem Warten
echo "### DEBUG: Umgebungsvariablen nach Warten ###"
echo "DJANGO_SECRET_KEY existiert: $([ -n "$DJANGO_SECRET_KEY" ] && echo 'JA' || echo 'NEIN')"
echo "DJANGO_SECRET_KEY Länge: ${#DJANGO_SECRET_KEY}"
echo "#########################"

# Hole die API Keys
echo "Hole API-Keys vom Backend..."
python /app/crawl4ai/api_key_provider.py --config /app/config.json --provider both

# Starte den crawl4ai-Service
echo "Starte crawl4ai-Service..."
supervisord -c /app/supervisord.conf 