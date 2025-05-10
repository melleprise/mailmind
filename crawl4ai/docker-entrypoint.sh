#!/bin/bash

# Dieser Entrypoint wird im Docker-Container ausgeführt
# und stellt sicher, dass der Crawl4AI-Service richtig gestartet wird

# Setze Ausführungsrechte für das Start-Skript
chmod +x /app/crawl4ai/start-crawl4ai.sh

# Starte den supervisord-Prozess
# Der Container braucht dies, um zu laufen
supervisord -c /app/supervisord.conf 