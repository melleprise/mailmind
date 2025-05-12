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

## API-Key und Cookie Handling (Freelance Provider)

Crawl4AI benötigt für den `freelance.de`-Provider nicht direkt einen API-Key im klassischen Sinne, sondern gültige Session-Cookies, um auf geschützte Bereiche zugreifen zu können.

**Workflow:**
1.  **Anfrage von `crawl4ai`:** Wenn `crawl4ai` Cookies für einen bestimmten `user_id` benötigt (entweder initial oder weil vorhandene Cookies abgelaufen sind), sendet es eine Anfrage an den `playwright-login`-Dienst.
    *   Anfrage-URL: `http://playwright-login:3000/login-by-user-id`
    *   Methode: `POST`
    *   Body: `{ "user_id": <ID des Benutzers> }`
2.  **`playwright-login`-Dienst:**
    *   Empfängt die `user_id`.
    *   Fragt das Django-Backend (`http://backend:8000/api/v1/freelance/credentials/<user_id>/`) mit einem speziellen Header (`X-Playwright-Login-Service: true`) an, um die Login-URL, den Benutzernamen und das **entschlüsselte** Passwort für den User zu erhalten.
    *   Startet eine Playwright-Instanz, navigiert zur Login-Seite von `freelance.de`, gibt die erhaltenen Credentials ein und speichert die resultierenden Cookies.
    *   Gibt die Cookies (oder einen Fehler) an `crawl4ai` zurück.
3.  **`crawl4ai`:**
    *   Empfängt die Cookies und verwendet sie für nachfolgende Anfragen an `freelance.de`.
    *   Die Cookies werden im Volume `crawl4ai_cookies` zwischengespeichert, um wiederholte Logins zu minimieren.

**Sicherheitsaspekte:**
-   Die Übermittlung des entschlüsselten Passworts vom Backend an den `playwright-login`-Dienst geschieht nur, wenn der spezielle Header `X-Playwright-Login-Service: true` gesetzt ist. Dieser Endpunkt im Backend (`/api/v1/freelance/credentials/<user_id>/`) ist weiterhin durch `permissions.AllowAny` geschützt, was für die interne Docker-Kommunikation vorerst akzeptabel ist, aber langfristig durch eine robustere Service-zu-Service-Authentifizierung (z.B. ein geteiltes Secret oder ein dediziertes Service-Token) ersetzt werden sollte.
-   Der `playwright-login`-Dienst benötigt die Umgebungsvariablen `EMAIL_ACCOUNT_ENCRYPTION_KEY` und `DJANGO_SECRET_KEY` nicht mehr direkt, da er die Credentials entschlüsselt vom Backend erhält.

- Standardmäßig liest Crawl4AI API-Keys aus `.llm.env`. -> Entfällt für Cookies
- Ziel: Adapter/Custom-Backend, der API-Keys pro User aus der DB bereitstellt. -> Erreicht durch Playwright-Login-Service für Cookies
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

## Custom Endpunkte

### POST /crawl-freelance-sync
Startet einen synchronen Crawl-Prozess für freelance.de für einen bestimmten User.
- Header: `X-User-Id: <user_id>` (Pflicht)
- Response: `{ "status": "started", "detail": "Freelance-Crawl für User-ID <id> wurde gestartet." }`
- Hinweis: Keine Authentifizierung über X-Internal-Auth, sondern User-Id-Header.

### POST /update-api-keys
Aktualisiert API-Keys für einen Provider und User.
- Body: `{ "provider": "groq", "user_id": 2 }`
- Header: `X-Internal-Auth: <SECRET_KEY>` (Pflicht)
- Response: `{ "message": "API-Key-Update für <provider> wurde gestartet" }`

### Sicherheit
- /update-api-keys ist durch den Secret-Key geschützt.
- /crawl-freelance-sync ist nur im internen Netzwerk verfügbar und benötigt die User-ID im Header.
- Beide Endpunkte sind für interne Service-Kommunikation gedacht. 