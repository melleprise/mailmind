#!/bin/bash

# Pfad zur docker-compose.dev.yml
COMPOSE_FILE="./docker-compose.dev.yml"

# Prüfen, ob die Datei existiert
if [ ! -f "$COMPOSE_FILE" ]; then
  echo "Fehler: $COMPOSE_FILE nicht gefunden!"
  exit 1
fi

echo "Stoppe crawl4ai-Container..."
docker-compose -f $COMPOSE_FILE stop crawl4ai

echo "Starte crawl4ai-Container neu..."
docker-compose -f $COMPOSE_FILE up -d crawl4ai

echo "Zeige logs des crawl4ai-Containers..."
docker-compose -f $COMPOSE_FILE logs -f --tail=50 crawl4ai 