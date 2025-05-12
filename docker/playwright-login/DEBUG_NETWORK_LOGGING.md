# Debug & Netzwerk-Logging Playwright-Login

## Features & Debug-Setup

- **Netzwerk-Logging:**
  - Alle Requests und Responses werden mit URL, Headern, Body, Status etc. in `network_log.json` geschrieben.
  - Logging erfolgt über Playwright-Events (`page.on('request')`, `page.on('response')`, `page.on('requestfailed')`).
  - Datei liegt durch Volume-Mount immer synchron im Host- und Container-Verzeichnis.

- **Debug-Ausgaben:**
  - Alle Netzwerk-Events werden zusätzlich im Container-Log ausgegeben (`console.log`).
  - Fehler beim Schreiben der Datei werden explizit geloggt.

- **Fehlerbehandlung:**
  - Globale Handler für `uncaughtException` und `unhandledRejection` loggen alle Fehler im Prozess.
  - Das Browserfenster bleibt nach Login und Fehlern offen (kein automatisches Schließen).

- **Volume-Mount:**
  - `./docker/playwright-login:/app` sorgt für sofortige Synchronisation von Code und Logs.

- **Backup:**
  - Vor jeder Änderung wird ein Backup der `index.js` als `index.js.bak` erstellt.

## Hinweise
- Die Datei `network_log.json` wird automatisch erstellt, sobald Requests auftreten.
- Für manuelles Debugging können automatische Klicks/Navigationsschritte im Skript auskommentiert werden.
- Alle Änderungen sind reversibel über das Backup.

## Produktivbetrieb

- Die Datei `freelance_cookies.json` enthält alle für authentifizierte Requests nötigen Cookies, LocalStorage und SessionStorage.
- Für crawl4ai werden diese Daten automatisch übernommen, um authentifizierte Requests zu ermöglichen.
- Die Datei wird nach jedem erfolgreichen Login überschrieben und ist immer aktuell.
- Header-Informationen (z.B. User-Agent) sind im `network_log.json` enthalten und können bei Bedarf übernommen werden.
- Für Produktion: Volume-Mount und Pfade so konfigurieren, dass crawl4ai und playwright-login auf dieselbe `freelance_cookies.json` zugreifen.
- Die Logs und Cookies werden nicht automatisch gelöscht – Rotation/Archivierung ggf. extern einrichten. 