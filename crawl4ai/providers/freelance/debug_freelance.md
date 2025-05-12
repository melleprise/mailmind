# Debugging & Testing: Freelance-Crawl

## Standard-Befehle

### 1. Playwright-Login-Service neu starten
```sh
docker compose -f docker-compose.dev.yml restart playwright-login crawl4ai
```

### 2. Datenbank leeren (alle Freelance-Projekte löschen)
```sh
docker compose -f docker-compose.dev.yml exec -T postgres psql -U mailmind -d mailmind -c "DELETE FROM public.freelance_projects;"
```

### 3. Crawl anstoßen (wie Sync-Button im Frontend)
```sh
curl -X POST http://localhost:11235/crawl-freelance-sync -H 'Content-Type: application/json' -H 'X-User-Id: 2' -d '{"user_id":2}'
```

### 4. DB-Einträge prüfen
```sh
docker compose -f docker-compose.dev.yml exec -T postgres psql -U mailmind -d mailmind -c "SELECT project_id, title, description FROM public.freelance_projects ORDER BY created_at DESC LIMIT 5;"
```

### 5. Playwright-Logs anzeigen
```sh
docker compose -f docker-compose.dev.yml logs --tail=300 playwright-login
```

---

## Sichtbaren Browser (EYES) aktivieren/deaktivieren

- **Aktivieren (sichtbar):**
  - In `docker-compose.dev.yml` im Service `playwright-login`:
    ```yaml
    environment:
      - VISIBLE_BROWSER=true
    ```
- **Deaktivieren (headless):**
  - In `docker-compose.dev.yml` im Service `playwright-login`:
    ```yaml
    environment:
      - VISIBLE_BROWSER=false
    ```
- Danach immer:
  ```sh
  docker compose -f docker-compose.dev.yml restart playwright-login
  ```

---

## HTML-Dump für Debugging aktivieren/deaktivieren

- **Aktivieren:**
  - In `docker-compose.dev.yml` beim Service `playwright-login`:
    ```yaml
    environment:
      - DEBUG_HTML_DUMP=true
    ```
  - Oder im Code: Setze die Variable `DEBUG_HTML_DUMP=true` (z.B. als ENV oder direkt im Code).
- **Deaktivieren:**
  - Entferne oder setze `DEBUG_HTML_DUMP=false` in der ENV.
- Danach immer:
  ```sh
  docker compose -f docker-compose.dev.yml restart playwright-login
  ```

**Hinweis:**
- Dumps werden im Container unter `/app/crawl4ai/providers/freelance/detail_dump.html` gespeichert.

---

**Tipp:**
- Alle Befehle können direkt kopiert und ausgeführt werden.
- Änderungen an der Sichtbarkeit werden erst nach einem Restart des Containers aktiv.

---

## Feld: application_status

- Speichert den Bewerbungsstatus aus der Detailseite (z.B. "Am 12.05.25 beworben").
- Wird aus `<div class="panel-body">` (ohne highlight-text) extrahiert.
- Ist `None`, wenn kein Status gefunden wird.

---

## Persistente Session-Tests (ab Mai 2024)

### 1. Einzelne geschützte Seite im User-Context laden
```sh
curl -X POST http://localhost:3000/fetch-protected-page -H 'Content-Type: application/json' -d '{"user_id":2,"url":"https://www.freelance.de/projekte/projekt-1234567-Testprojekt"}'
```

### 2. Komplette Crawl-Session (Übersicht + Details, alles in einer Session)
```sh
curl -X POST http://localhost:3000/crawl-session -H 'Content-Type: application/json' -d '{"user_id":2,"overview_urls":["https://www.freelance.de/projekte/"],"detail_urls":["https://www.freelance.de/projekte/projekt-1234567-Testprojekt"]}'
```

### 3. Session explizit schließen
```sh
curl -X POST http://localhost:3000/close-session -H 'Content-Type: application/json' -d '{"user_id":2}'
```

**Hinweise:**
- Für denselben User bleibt der Browser/Context offen, alle Requests laufen in derselben Session (kein erneuter Login).
- Nach `/close-session` ist die Session beendet und ein neuer Request erzeugt wieder einen Login.
- Logs prüfen bei Problemen:
```sh
docker compose -f docker-compose.dev.yml logs --tail=300 playwright-login
```
- Felder wie `description` und `application_status` sollten nach erfolgreichem Crawl korrekt befüllt sein. 