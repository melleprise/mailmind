# Sichtbarer Browser in Docker mit XQuartz/X11 (Playwright & Crawl4AI)

## Ziel
- Playwright und Crawl4AI können wahlweise im sichtbaren Modus (GUI) laufen, sodass der Browser auf dem Mac via XQuartz angezeigt wird.
- Umschaltbar per ENV-Variable (`VISIBLE_BROWSER=true/false`).
- Alle nötigen X11-Bibliotheken sind im Container installiert.

---

## 1. Voraussetzungen (Host/Mac)
- **XQuartz** installieren: https://www.xquartz.org/
- XQuartz starten.
- Im Terminal ausführen:
  ```sh
  xhost +local:docker
  export DISPLAY=:0
  ```

---

## 2. Dockerfile-Anpassungen (beide Container)
Füge in beide Dockerfiles (Playwright & Crawl4AI) hinzu:

```Dockerfile
RUN apt-get update && apt-get install -y \
    x11-apps \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxi6 \
    libxtst6 \
    libnss3 \
    libxrandr2 \
    libasound2 \
    libpangocairo-1.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdrm2 \
    libgbm1 \
    libxss1 \
    libxshmfence1 \
    libxinerama1 \
    libxkbcommon0 \
    && rm -rf /var/lib/apt/lists/*
```

---

## 3. docker-compose.dev.yml

```yaml
volumes:
  - /tmp/.X11-unix:/tmp/.X11-unix

environment:
  - DISPLAY=${DISPLAY}
  - VISIBLE_BROWSER=${VISIBLE_BROWSER:-false}
```

---

## 4. Umschaltbar machen (ENV)

**Playwright-Start (Node.js):**
```js
const headless = process.env.VISIBLE_BROWSER !== 'true';
const browser = await chromium.launch({ headless });
```

**Python (falls relevant):**
```python
import os
headless = os.environ.get("VISIBLE_BROWSER", "false").lower() != "true"
browser = await playwright.chromium.launch(headless=headless)
```

---

## 5. Aktivieren/Deaktivieren

**Aktivieren (sichtbar):**
```sh
export DISPLAY=:0
export VISIBLE_BROWSER=true
xhost +local:docker
docker compose -f docker-compose.dev.yml up
```

**Deaktivieren (headless):**
```sh
export VISIBLE_BROWSER=false
docker compose -f docker-compose.dev.yml up
```

---

## 6. Troubleshooting (Mac)
- XQuartz muss laufen, bevor der Container startet.
- `xhost +local:docker` nach jedem XQuartz-Neustart ausführen.
- Wenn kein Fenster erscheint: DISPLAY prüfen (`echo $DISPLAY` → sollte `:0` sein).
- Firewall/Privacy-Einstellungen von XQuartz prüfen.

---

## 7. Hinweise
- Die Umschaltung ist jederzeit per ENV möglich, ein Rebuild ist nicht nötig.
- Für CI/Server immer `VISIBLE_BROWSER=false` lassen.

---

**Fertig! Jetzt kannst du den Browser im Container sichtbar machen, wann immer du willst.** 