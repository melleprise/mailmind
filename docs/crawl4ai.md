# Crawl4AI Integration

## Ziel
- Crawl4AI als Service im Docker-Setup.
- Nutzung der bestehenden Postgres-DB für persistente Speicherung.
- API-Keys werden aus der User-DB geladen (nicht aus .llm.env).
- Erst-Setup manuell, künftig automatisiert per Shell-Script.

## Docker Compose
- Service `crawl4ai` in `docker-compose.dev.yml` integriert.
- Nutzt das gleiche Netzwerk und die gleiche Postgres-DB wie die Hauptanwendung.
- Eigene Config per Volume-Mount: `./crawl4ai-config.yml:/app/config.yml`.

## Konfiguration (`crawl4ai-config.yml`)
- Postgres-URL zeigt auf die Projekt-DB.
- LLM-Provider und API-Key-Handling: Platzhalter, da API-Key dynamisch aus der User-DB geladen werden soll.

## API-Key Handling
- Standardmäßig liest Crawl4AI API-Keys aus `.llm.env`.
- Ziel: Adapter/Custom-Backend, der API-Keys pro User aus der DB bereitstellt.
- Mögliche Ansätze:
  - Crawl4AI forken und DB-Query für API-Key einbauen.
  - REST-Endpoint im Backend, den Crawl4AI abfragt.
  - DB-View oder Trigger, der API-Keys bereitstellt.
- TODO: Technische Umsetzung und Anpassung in Crawl4AI.

## Automatisiertes Setup
- Shell-Script (`crawl4ai-setup.sh`) geplant:
  - Prüft und migriert DB-Struktur für Crawl4AI.
  - Kopiert/erstellt Config.
  - Startet/Restartet Service.

## Offene Punkte
- API-Key-Adapter/Integration umsetzen.
- Automatisiertes Setup-Script schreiben.
- Doku regelmäßig aktualisieren.

## Healthcheck & Monitoring
- Healthcheck via `/health` Endpoint.
- Playground unter `http://localhost:11235/playground`.

## Siehe auch
- [Crawl4AI Docker Guide](https://docs.crawl4ai.com/core/docker-deployment/)
- [Crawl4AI Konfiguration](https://docs.crawl4ai.com/core/installation/) 