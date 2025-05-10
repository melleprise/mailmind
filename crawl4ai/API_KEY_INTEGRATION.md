# API-Key-Integration für Crawl4AI

## Überblick

Diese Dokumentation beschreibt die API-Key-Integration zwischen dem Django-Backend und dem Crawl4AI-Service. Der Crawl4AI-Service ruft API-Keys für LLM-Provider (Groq, Google Gemini) aus der Django-Datenbank ab, um sie für Crawling- und Analysefunktionen zu verwenden.

## Aktuelle Implementierung

### Komponenten

1. **Backend-Endpunkt**:
   - URL: `/api/v1/core/internal/get-api-key/`
   - Authentifizierung: `X-Internal-Auth`-Header mit Django SECRET_KEY
   - Liefert API-Keys für bestimmte Provider und Nutzer

2. **API-Key-Provider**:
   - Skript: `api_key_provider.py`
   - Funktion: Ruft API-Keys vom Backend ab und schreibt sie in die Crawl4AI-Konfigurationsdatei
   - Aktuell: Verwendet standardmäßig `user_id=2` für API-Key-Abfragen

3. **API-Key-Updater**:
   - Skript: `api_key_updater.py`
   - Funktion: FastAPI-Endpunkt für Aktualisierung von API-Keys zur Laufzeit
   - Aktuell: Verwendet standardmäßig `user_id=2`

4. **Signal-Handler**:
   - Im Django-Backend
   - Funktion: Benachrichtigt Crawl4AI über API-Key-Änderungen

5. **Start-Skript**:
   - Skript: `start-crawl4ai-with-keys.sh`
   - Funktion: Startet den Crawl4AI-Service und ruft API-Keys beim Start ab

### Konfiguration

- Docker-Integration über `docker-compose.dev.yml`
- Umgebungsvariablen:
  - `DJANGO_SECRET_KEY`: Für Authentifizierung
  - `BACKEND_API_URL`: Endpunkt-URL

## Verwendung des Services

### Start des Services

Der Crawl4AI-Service wird automatisch beim Hochfahren der Docker-Umgebung gestartet:

```bash
docker-compose -f docker-compose.dev.yml up -d crawl4ai
```

Bei Änderungen der Konfiguration kann der Service neu gestartet werden:

```bash
docker-compose -f docker-compose.dev.yml restart crawl4ai
```

### Verfügbare API-Endpunkte

Der Service ist unter `http://localhost:11235` erreichbar:

- `/crawl`: Hauptendpunkt für Crawling-Operationen
- `/html`: Extrahieren von HTML-Inhalten
- `/screenshot`: Screenshot einer Webseite erstellen
- `/execute_js`: JavaScript auf einer Webseite ausführen
- `/playground/`: Interaktives UI zum Testen des Services
- `/health`: Health-Check des Services

### Beispiel-Anfragen

#### Einfacher Crawl einer Webseite:

```bash
curl -X POST "http://localhost:11235/crawl" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://example.com/"], "depth": 0, "extract_text": true}'
```

#### Screenshot einer Webseite erstellen:

```bash
curl -X POST "http://localhost:11235/screenshot" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/"}'
```

### Überprüfung der API-Key-Konfiguration

Die aktuelle API-Key-Konfiguration kann wie folgt überprüft werden:

```bash
docker-compose -f docker-compose.dev.yml exec crawl4ai cat /app/config.json
```

Ergebnis sollte etwa so aussehen:

```json
{
  "llm": {
    "provider": "groq/llama3-8b-8192",
    "api_key": "gsk_abc123..."
  },
  "groq_api_key": "gsk_abc123...",
  "gemini_api_key": "AIza..."
}
```

### Debugging und Logs

Logs des Services können wie folgt angezeigt werden:

```bash
docker-compose -f docker-compose.dev.yml logs -f crawl4ai
```

## Geplante Erweiterung: Dynamische User-ID

Aktuell verwendet die Integration eine fest codierte `user_id=2` in allen Komponenten. Für eine vollständige Multi-User-Unterstützung muss die User-ID dynamisch ermittelt werden.

### Anforderungen

1. Die aktuelle Benutzer-ID soll zur Laufzeit ermittelt werden, basierend auf dem eingeloggten Benutzer
2. Jeder Benutzer soll seine eigenen API-Keys verwenden können
3. Die Integration muss mit dem Django-Authentifizierungssystem zusammenarbeiten

### Implementierungsplan

1. **Frontend-Integration**:
   - Erweitern des Frontend, um die aktuelle Benutzer-ID beim API-Aufruf an Crawl4AI zu übergeben
   - Beispiel: `POST /crawl` mit zusätzlichem Parameter `user_id`

2. **Crawl4AI-Endpunkte anpassen**:
   - Alle relevanten Endpunkte erweitern, um den `user_id`-Parameter zu akzeptieren
   - Übergabe der `user_id` an die API-Key-Abruffunktion

3. **API-Key-Provider anpassen**:
   ```python
   def get_api_key_from_backend(provider, user_id=None):
       # Wenn keine user_id übergeben wurde, verwende Default (Admin)
       if user_id is None:
           user_id = 1  # Default auf Admin-User oder eingeloggten User
       
       # Rest der Funktion wie bisher
       # ...
   ```

4. **Session-Management**:
   - Implementieren eines Session-Managements in Crawl4AI
   - Speichern der Benutzer-ID in der Session
   - Automatisches Abrufen der API-Keys für den aktuellen Benutzer

5. **Authentifizierung erweitern**:
   - Erweiterung des Authentifizierungsmechanismus zwischen Django und Crawl4AI
   - Übergabe von Benutzerinformationen bei der Authentifizierung

### Beispiel für dynamische User-ID-Integration

```python
# In einem Flask/FastAPI-Route-Handler:
@app.post("/crawl")
async def crawl(request_data: CrawlRequest):
    user_id = request_data.user_id if request_data.user_id else get_default_user_id()
    
    # API-Keys für den spezifischen Benutzer abrufen
    api_keys = await get_user_api_keys(user_id)
    
    # Crawling mit den benutzerspezifischen API-Keys durchführen
    # ...
    
    return {"result": "..."}

async def get_user_api_keys(user_id):
    # API-Keys vom Backend abrufen
    backend_url = os.environ.get('BACKEND_API_URL', 'http://backend:8000')
    endpoint = f"{backend_url}/api/v1/core/internal/get-api-key/"
    
    # Django Secret Key für interne Authentifizierung
    django_secret_key = os.environ.get('DJANGO_SECRET_KEY')
    
    # API-Keys für beide Provider abrufen
    keys = {}
    for provider in ['groq', 'google_gemini']:
        response = await httpx.post(
            endpoint,
            json={
                'provider': provider,
                'user_id': user_id
            },
            headers={
                'Content-Type': 'application/json',
                'X-Internal-Auth': django_secret_key[:32]
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('api_key'):
                keys[provider] = result['api_key']
                
    return keys
```

## Sicherheitsüberlegungen

- Sicherstellen, dass Benutzer nur auf ihre eigenen API-Keys zugreifen können
- Verwenden von sicheren Kommunikationskanälen zwischen den Services
- Regelmäßiges Rotieren von Authentifizierungsschlüsseln

## Testing

- Unit-Tests für die dynamische User-ID-Funktion entwickeln
- End-to-End-Tests für verschiedene Benutzerszenarien
- Lasttests mit mehreren Benutzern gleichzeitig

## Fehlersuche und Behebung

### Problem: API-Keys werden nicht gefunden

1. Prüfen, ob API-Keys in der Datenbank vorhanden sind:
   ```bash
   docker-compose -f docker-compose.dev.yml exec backend python manage.py shell -c "from mailmind.core.models import APICredential; print(APICredential.objects.filter(user_id=2).values())"
   ```

2. Prüfen, ob der Backend-Endpunkt erreichbar ist:
   ```bash
   docker-compose -f docker-compose.dev.yml exec crawl4ai curl -v http://backend:8000/health
   ```

3. Prüfen, ob der DJANGO_SECRET_KEY korrekt übertragen wird:
   ```bash
   docker-compose -f docker-compose.dev.yml logs crawl4ai | grep "DJANGO_SECRET_KEY"
   ```

### Problem: Crawl4AI-Service startet nicht

1. Prüfen der Docker-Logs:
   ```bash
   docker-compose -f docker-compose.dev.yml logs crawl4ai
   ```

2. Prüfen, ob alle benötigten Umgebungsvariablen gesetzt sind:
   ```bash
   docker-compose -f docker-compose.dev.yml config
   ```

## Fazit

Die Erweiterung der API-Key-Integration mit einer dynamischen User-ID ermöglicht eine vollständige Multi-User-Unterstützung für Crawl4AI. Jeder Benutzer kann seine eigenen API-Keys verwenden, was die Sicherheit und Isolation zwischen Benutzern verbessert.

Die Implementation erfordert Änderungen an mehreren Komponenten, insbesondere am API-Key-Provider, den Crawl4AI-Endpunkten und dem Authentifizierungsmechanismus. 