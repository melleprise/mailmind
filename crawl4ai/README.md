# Crawl4AI Custom Scripts

## Struktur
- `crawl4ai/providers/<provider>/login.js` – Login-Skript für jeweiligen Provider
- `crawl4ai/providers/<provider>/login.sh` – Shell-Wrapper für Login
- `crawl4ai/install-deps.sh` – Installiert alle benötigten Node-Module (z.B. playwright)

## Nutzung
- Die Skripte werden per Volume ins Crawl4AI-Containerverzeichnis `/app/custom-scripts` gemountet.
- Vor jedem Crawl kann das passende Login-Skript ausgeführt werden.

## Beispielstruktur
```
crawl4ai/
  install-deps.sh
  providers/
    freelance/
      login.js
      login.sh
    anotherprovider/
      login.js
      login.sh
```

## Installation im Container
- `install-deps.sh` wird beim Build oder Start ausgeführt und installiert z.B. Playwright global.

## Best Practice
- Provider-spezifische Logik bleibt gekapselt.
- Erweiterbar für beliebig viele Logins.
- Keine Abhängigkeiten im Hostsystem nötig.

# Crawl4AI Docker-Integration

## Features
- Headless-Browser-Crawling (Playwright, Chromium)
- Markdown- und strukturierte Datenausgabe
- API-Server (FastAPI/Uvicorn, Port 11235)
- REST-API: /crawl, /html, /screenshot, /pdf, /execute_js
- MCP-Schnittstelle für LLM-Tools (Claude Code etc.)
- Prometheus-Metriken, Health-Check
- Flexible Konfiguration per YAML
- LLM-Integration (OpenAI, Anthropic, Ollama, etc.)
- Rate-Limiting, Security-Optionen, Redis-Support

## Docker-Betrieb
- Basis-Image: mcr.microsoft.com/playwright
- User: pwuser (kein Root-Betrieb)
- Konfigurationsdatei: `/app/config.yml` (wird per Volume gemountet)
- Datenbank: Postgres, URL via `database_url` in config.yml
- LLM-Keys: per Umgebungsvariable oder `.llm.env` (siehe Doku)

## Konfigurationsbeispiel (config.yml)
```yaml
app:
  title: "Crawl4AI API"
  version: "1.0.0"
  host: "0.0.0.0"
  port: 11235
  reload: false
  timeout_keep_alive: 300
llm:
  provider: "openai/gpt-4o-mini"
  api_key_env: "OPENAI_API_KEY"
redis:
  host: "localhost"
  port: 6379
  db: 0
  password: ""
rate_limiting:
  enabled: true
  default_limit: "1000/minute"
  trusted_proxies: []
  storage_uri: "memory://"
security:
  enabled: false
  jwt_enabled: false
  https_redirect: false
  trusted_hosts: ["*"]
  headers:
    x_content_type_options: "nosniff"
    x_frame_options: "DENY"
    content_security_policy: "default-src 'self'"
    strict_transport_security: "max-age=63072000; includeSubDomains"
crawler:
  memory_threshold_percent: 95.0
  rate_limiter:
    base_delay: [1.0, 2.0]
  timeouts:
    stream_init: 30.0
    batch_process: 300.0
logging:
  level: "INFO"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
observability:
  prometheus:
    enabled: true
    endpoint: "/metrics"
  health_check:
    endpoint: "/health"
database_url: postgresql://mailmind:mailmind@postgres:5432/mailmind
```

## Hinweise
- Die Datei muss vollständig sein, da sie die Default-Konfiguration im Container überschreibt.
- LLM-Keys (z.B. OpenAI) werden per Umgebungsvariable oder `.llm.env` bereitgestellt.
- Für produktiven Betrieb: Security-Optionen aktivieren und trusted_hosts einschränken.
- Playground-UI: http://localhost:11235/playground
- Health-Check: http://localhost:11235/health
- Prometheus: http://localhost:11235/metrics

## API-Endpoints (Auswahl)
- POST `/crawl` – Startet Crawl-Job (siehe Doku für Payload)
- POST `/html` – Extrahiert HTML
- POST `/screenshot` – Screenshot einer Seite
- POST `/pdf` – PDF-Export
- POST `/execute_js` – Führt JS auf Seite aus
- GET `/metrics` – Prometheus-Metriken
- GET `/health` – Health-Check
- GET `/playground` – Interaktive UI

### CORS-Konfiguration
Der `crawl4ai`-Dienst ist so konfiguriert, dass er Cross-Origin Resource Sharing (CORS) Anfragen vom Frontend (standardmäßig `http://localhost:8080`) und anderen localhost-Adressen akzeptiert. Dies wird in `server.py` durch die FastAPI `CORSMiddleware` gehandhabt. Die erlaubten Origins sind:
- `http://localhost:8080`
- `http://localhost`
- `http://127.0.0.1:8080`
- `http://127.0.0.1`

Dies ermöglicht es dem Frontend, direkt API-Anfragen an den `crawl4ai`-Dienst zu senden, z.B. für den Sync-Vorgang der Freelance-Projekte.

## MCP-Integration
- SSE: `http://localhost:11235/mcp/sse`
- WebSocket: `ws://localhost:11235/mcp/ws`

## Troubleshooting
- Bei Browser-Problemen: Container mit ausreichend `/dev/shm` starten
- Rechteprobleme vermeiden: Immer als `pwuser` im Container laufen lassen
- Konfigurationsfehler: Log-Ausgabe im Container prüfen

## Weiterführende Links
- [Crawl4AI Doku](https://docs.crawl4ai.com/core/docker-deployment/)
- [GitHub Repo](https://github.com/unclecode/crawl4ai)

# API Key Integration für crawl4ai

Diese Integration ermöglicht es, API-Keys aus der Django-Datenbank für den crawl4ai-Service zu verwenden, ohne die Keys doppelt speichern zu müssen.

## Funktionsweise

1. Der crawl4ai-Container bezieht API-Keys (Groq, Google Gemini) über einen internen API-Endpunkt vom Backend
2. Der interne Zugriff wird durch den Django SECRET_KEY abgesichert
3. Ein Python-Skript holt die Keys und schreibt sie in die crawl4ai-Konfigurationsdatei
4. Bei jedem Container-Start werden die aktuellen Keys aus der Datenbank geholt

## Komponenten

### 1. Backend-Endpunkt

Ein interner API-Endpunkt im Django-Backend stellt die API-Keys bereit:
- URL: `/api/v1/internal/get-api-key/`
- Authentifizierung: Über Header `X-Internal-Auth` mit Django SECRET_KEY
- Gibt API-Keys für bestimmte Provider und Nutzer zurück

### 2. API-Key-Provider

Das Python-Skript `api_key_provider.py` dient als Vermittler:
- Es ruft die API-Keys vom Backend-Server ab (über den internen API-Endpunkt)
- Es aktualisiert die crawl4ai-Konfigurationsdatei mit den abgerufenen Schlüsseln
- Die API-Keys gehören standardmäßig dem Benutzer mit user_id=2
- Der Standardwert kann über den Parameter `--user-id` angepasst werden

### 3. Start-Skript

Das Skript `start-crawl4ai-with-keys.sh`:
- Wird als Entrypoint im Docker-Container ausgeführt
- Wartet auf das Backend
- Ruft den API-Key-Provider auf, um die Keys zu holen
- Startet dann den crawl4ai-Service

### 4. API-Key-Updater (Neu)

Das Feature `api_key_updater.py` ermöglicht die Aktualisierung von API-Keys zur Laufzeit:
- Bietet einen FastAPI-Endpunkt: `/api-keys/update-api-keys`
- Authentifizierung über Django SECRET_KEY
- Wird automatisch durch Signal-Handler im Backend bei API-Key-Änderungen aufgerufen
- Aktualisiert die Keys im laufenden Container ohne Neustart

## Konfiguration

Die Integration wird über die `docker-compose.dev.yml` konfiguriert:
- Der Django SECRET_KEY wird als Umgebungsvariable übergeben
- Die Backend-URL wird angegeben
- Das Startskript wird als Entrypoint konfiguriert

## Sicherheitsaspekte

- Die API-Keys werden nur zur Laufzeit im Container verwendet
- Der interne API-Endpunkt ist nur im Docker-Netzwerk erreichbar
- Die Authentifizierung erfolgt über den Django SECRET_KEY

## Fehlerbehebung

- Überprüfe, ob Backend-Endpunkt erreichbar ist
- Überprüfe, ob die API-Keys in der Django-Datenbank vorhanden sind
- Prüfe die Logs des crawl4ai-Containers
- Stelle sicher, dass die Docker-Netzwerkkonfiguration korrekt ist

## Verwendung

Starte den Container mit `docker-compose -f docker-compose.dev.yml up -d crawl4ai`

### API-Key-Aktualisierung

API-Keys werden automatisch aktualisiert, wenn:
1. Ein neuer API-Key im Django-Backend hinzugefügt wird
2. Ein vorhandener API-Key im Backend aktualisiert wird

Es ist kein manueller Eingriff oder Container-Neustart erforderlich. 