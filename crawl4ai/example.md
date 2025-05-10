# Crawl4AI Beispiele

## Verwendung

Crawl4AI läuft als eigenständiger Service auf Port 11235 und bietet folgende Endpunkte:

### Basis-Gesundheitsprüfung

```bash
curl http://localhost:11235/health
```

### Markdown-Extraktion einer URL

```bash
curl -X POST "http://localhost:11235/md" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### Batch-Crawling mehrerer URLs

```bash
curl -X POST "http://localhost:11235/crawl" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com", "https://another-example.com"]}'
```

### Ansicht der Playground-Oberfläche

Öffne im Browser:
http://localhost:11235/playground

## Einschränkungen

- Der Service kann aktuell keine websites crawlen, die komplexe Browser-Interaktionen erfordern (Login, etc.)
- Die Standardinstallation enthält keine Browser-Unterstützung für JavaScript-intensive Websites

## Docker-Compose-Integration

Der Service ist in deiner docker-compose.dev.yml integriert und wird automatisch mit folgendem Befehl gestartet:

```bash
docker-compose -f docker-compose.dev.yml up -d crawl4ai
``` 