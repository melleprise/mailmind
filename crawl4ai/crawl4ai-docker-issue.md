# Chromium/Crashpad-Fehler im Docker-Container trotz Best Practices (Playwright + Crawl4AI)

## Beschreibung
Wir betreiben Crawl4AI als Service in einem Docker-Setup (gemeinsam mit Django/Postgres). Playwright-Browser werden im Container installiert, alle relevanten Umgebungsvariablen und Verzeichnisse (HOME, XDG_CONFIG_HOME, XDG_CACHE_HOME, /tmp, /app/.crawl4ai etc.) sind gesetzt und mit Schreibrechten versehen. Trotzdem schlägt der Start der Browser mit folgendem Fehler fehl:

```
chrome_crashpad_handler: --database is required
```

## Bisherige Maßnahmen
- Verschiedene Base-Images (python, node, debian, alpine, mcr.microsoft.com/playwright) getestet
- Installation via pip, python -m playwright, npm
- explizite Umgebungsvariablen (HOME, XDG_CONFIG_HOME, XDG_CACHE_HOME)
- Verzeichnisse mit chmod 777 bzw. 1777
- Symlinks und explizite Profile
- Start als root und non-root
- Community- und Doku-Best Practices umgesetzt
- Manuelles Testen im Container (bash, playwright install, playwright codegen etc.)

## Dockerfile-Auszug
```dockerfile
FROM python:3.12-slim
USER root
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
ENV HOME=/app
# ... weitere ENV und Installationen ...
RUN mkdir -p /ms-playwright && \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright python -m playwright install --with-deps
RUN mkdir -p /app/.crawl4ai && chmod 777 /app/.crawl4ai
RUN ln -s /app/.crawl4ai /.crawl4ai
RUN mkdir -p /app/.config /app/.cache /app/.pki /app/.local /app/.chromium-profile /app/.cache/ms-playwright /app/.cache/puppeteer && \
    chmod -R 777 /app/.config /app/.cache /app/.pki /app/.local /app/.chromium-profile /app/.cache/ms-playwright /app/.cache/puppeteer
RUN chmod 1777 /tmp
USER 1000:1000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "11235"]
```

## docker-compose.dev.yml (crawl4ai-Service)
```yaml
  crawl4ai:
    build:
      context: ./external/crawl4ai/deploy
      dockerfile: Dockerfile
    image: crawl4ai-local:latest
    ports:
      - "11235:11235"
    depends_on:
      - postgres
    environment:
      - DATABASE_URL=postgresql://mailmind:mailmind@postgres:5432/mailmind
      - PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
      - HOME=/app
    volumes:
      - /dev/shm:/dev/shm
      - ./crawl4ai-config.yml:/app/config.yml
      - ./crawl4ai:/app/custom-scripts
      - playwright-cookies:/cookies
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 1G
    restart: unless-stopped
    networks:
      - mailmind-dev-network
```

## config.yml (Browser-Args)
```yaml
crawler:
  browser:
    kwargs:
      headless: true
      text_mode: true
    extra_args:
      - "--no-sandbox"
      - "--disable-dev-shm-usage"
      - "--disable-gpu"
      - "--disable-software-rasterizer"
      - "--disable-web-security"
      - "--allow-insecure-localhost"
      - "--ignore-certificate-errors"
```

## Systeminfos
- Host: macOS (Apple Silicon)
- Docker: 24.x
- Python: 3.12
- Crawl4AI: aktuellster Stand (lokal gebaut)
- Playwright: via pip, aktuellste Version
- User: root und non-root getestet
- Alle relevanten Verzeichnisse mit Schreibrechten, Symlinks, explizite Umgebungsvariablen

## Fragen
- Gibt es bekannte Inkompatibilitäten mit Crawl4AI + Playwright im Container?
- Welche weiteren Debugging-Schritte werden empfohlen?
- Gibt es ein Minimal-Setup, das garantiert funktioniert?

---
Gerne stelle ich weitere Logs, Details oder ein Minimal-Repo bereit. 