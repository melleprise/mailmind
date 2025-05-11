# Playwright-Login Debugging mit sichtbarem Browser (Mac + Docker + X11)

## Voraussetzungen
- Mac mit XQuartz installiert (`brew install --cask xquartz`)
- Docker läuft
- Projekt ist gebaut (`docker-compose.dev.yml`)

## 1. XQuartz starten und konfigurieren
- Starte XQuartz:
  ```bash
  open -a XQuartz
  ```
- Einstellungen → Sicherheit → Haken bei „Verbindungen von Netzwerk-Clients erlauben“
- Im Mac-Terminal:
  ```bash
  export DISPLAY=:0
  xhost +
  ```

## 2. Playwright-Login-Container vorbereiten
- Im Mac-Terminal:
  ```bash
  export DISPLAY=host.docker.internal:0
  docker compose -f docker-compose.dev.yml exec playwright-login bash
  ```

docker-compose -f docker-compose.dev.yml exec postgres psql -U mailmind -d mailmind -c "DELETE FROM freelance_projects;"

## 3. Im Container: Debug-Skript ausführen
- Im Container:
  ```bash
  cd /app
  export DISPLAY=host.docker.internal:0
  node debug_manual_login.js
  ```
- Der Chromium-Browser öffnet sich auf deinem Mac (über XQuartz).
- Das Skript loggt sich ein, **setzt explizit das Promo-Cookie** und lädt eine Detailseite.
- Nach dem Laden der Detailseite wird ein Cookiebot-Consent-Request direkt an Cookiebot gesendet und das Dialog per JS entfernt. Dadurch verschwindet das Cookie-Fenster zuverlässig – auch wenn es Playwright nicht klicken kann.
- Das Fenster bleibt 10 Minuten offen für manuelle Interaktion.
- Am Ende werden die Cookies in `debug_cookies.json` gespeichert.

## 4. Tipps
- Wenn kein Fenster erscheint: Prüfe XQuartz, DISPLAY, xhost, Firewall.
- **Wichtig:** Das Promo-Cookie `no_postlogin_FL_-_Post_Login_315468` wird nach Login gesetzt, um die Weiterleitung auf die Promo-Seite zu verhindern. Ohne dieses Cookie funktionieren Detailseiten nicht!
- Du kannst im Skript Username/Passwort hardcoden oder als ENV setzen.
- Für weitere Debugs: `xeyes` im Container testen.

---
**Kurz:**
1. XQuartz starten, xhost +
2. DISPLAY setzen, Container öffnen
3. Im Container: DISPLAY setzen, Skript starten
4. Browser erscheint auf dem Mac 