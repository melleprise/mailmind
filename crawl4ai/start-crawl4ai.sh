#!/bin/bash

# Stoppe und entferne bestehenden Container, falls vorhanden
docker stop mailmind-dev-crawl4ai 2>/dev/null || true
docker rm mailmind-dev-crawl4ai 2>/dev/null || true

# Starte crawl4ai mit korrekter Konfiguration
echo "Starte crawl4ai Service..."
docker run -d --name mailmind-dev-crawl4ai \
  -p 11235:11235 \
  --network mailmind-dev-network \
  --shm-size=1g \
  unclecode/crawl4ai:latest

# Warte auf den Start des Services
echo "Warte auf Start des crawl4ai Services..."
sleep 5

# Prüfe den Gesundheitsstatus
curl http://localhost:11235/health

echo ""
echo "crawl4ai Service läuft jetzt auf http://localhost:11235"
echo "Du kannst die Playground-Oberfläche unter http://localhost:11235/playground aufrufen"
echo ""
echo "Beispielverwendung:"
echo "curl -X POST \"http://localhost:11235/md\" -H \"Content-Type: application/json\" -d '{\"url\": \"https://example.com\"}'" 