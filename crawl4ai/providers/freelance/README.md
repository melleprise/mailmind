# Freelance Provider für Crawl4AI

Der Freelance-Provider ermöglicht das Crawlen von Projekten auf freelance.de und speichert diese in eine PostgreSQL-Datenbank.

## Funktionsweise

Der Provider bietet folgende Funktionen:

1. **Automatisierte Authentifizierung**: Verwendet den Playwright-Login-Service, um sich bei freelance.de einzuloggen
2. **Extrahieren von Projektdaten**: Extrahiert Projekt-Details aus der Projektliste (jetzt direkt aus JSON-Daten)
3. **Datenbank-Integration**: Speichert Projekte in PostgreSQL
4. **Pagination-Unterstützung**: Kann mehrere Seiten von Projektergebnissen verarbeiten
5. **Detailseiten-Scraping**: Crawlt die Projektdetailseiten und speichert zusätzliche Informationen

## Installation

Der Provider ist bereits im Crawl4AI Docker-Image enthalten.

### Voraussetzungen

- Docker und Docker Compose
- PostgreSQL-Datenbank (Teil des Mailmind-Projekts)
- Playwright-Login-Service

## Verwendung

### Projekttests

Um den Provider zu testen und die Ergebnisse als JSON zu speichern:

```bash
# Standardmäßig eine Seite crawlen
docker-compose -f docker-compose.dev.yml exec crawl4ai python /app/providers/freelance/test_crawler.py

# Eine einzelne Seite mit JSON-Extraktion testen
docker-compose -f docker-compose.dev.yml exec crawl4ai python /app/providers/freelance/test_one_page.py

# Listenseite und Detailseiten crawlen
docker-compose -f docker-compose.dev.yml exec crawl4ai python /app/providers/freelance/test_detail_crawl.py
```

### Datenbank-Integration

Um Projekte zu crawlen und direkt in der Datenbank zu speichern:

```bash
# Standardmäßig 5 Seiten crawlen
docker-compose -f docker-compose.dev.yml exec crawl4ai python /app/providers/freelance/db_integration.py

# Remote-Projekte crawlen (mit begrenzter Seitenzahl)
docker-compose -f docker-compose.dev.yml exec crawl4ai python /app/providers/freelance/crawl_all_pages.py --max-pages 3
```

### Manuelle Überprüfung

Um zu prüfen, ob Daten in der Datenbank gespeichert wurden:

```bash
docker-compose -f docker-compose.dev.yml exec postgres psql -U mailmind -c "SELECT COUNT(*) FROM freelance_projects;"
docker-compose -f docker-compose.dev.yml exec postgres psql -U mailmind -c "SELECT project_id, title FROM freelance_projects LIMIT 5;"
docker-compose -f docker-compose.dev.yml exec postgres psql -U mailmind -c "SELECT COUNT(*) FROM freelance_project_details;"
```

## Datenmodell

Die gescrapten Daten werden in zwei Tabellen gespeichert:

### Projekttabelle (freelance_projects)

```sql
CREATE TABLE IF NOT EXISTS freelance_projects (
    id SERIAL PRIMARY KEY,
    project_id TEXT NOT NULL,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    end_date TEXT,
    location TEXT,
    remote BOOLEAN DEFAULT FALSE,
    last_updated TEXT,
    skills JSONB DEFAULT '[]'::jsonb,
    url TEXT NOT NULL,
    applications INTEGER,
    description TEXT DEFAULT '',
    provider TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, provider)
)
```

### Detailtabelle (freelance_project_details)

```sql
CREATE TABLE IF NOT EXISTS freelance_project_details (
    id SERIAL PRIMARY KEY,
    project_id TEXT NOT NULL,
    full_description TEXT,
    application_deadline TEXT,
    project_duration TEXT,
    hourly_rate TEXT,
    contact_person TEXT,
    additional_skills JSONB DEFAULT '[]'::jsonb,
    attachments JSONB DEFAULT '[]'::jsonb,
    date_posted TEXT,
    crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id),
    FOREIGN KEY (project_id) REFERENCES freelance_projects(project_id)
)
```

## JSON-Extraktion

Seit Mai 2025 hat freelance.de seine Webseite aktualisiert und stellt die Projektdaten direkt als JSON-Objekt in der HTML-Seite bereit. Der Crawler wurde entsprechend angepasst:

1. **JSON-Extraktion**: Der Crawler identifiziert und extrahiert das JSON-Objekt aus dem HTML mittels regulärer Ausdrücke
2. **Fallback-Methode**: Bei Problemen mit der JSON-Extraktion greift der Crawler auf die klassische HTML-Extraktion zurück
3. **Verbesserte Datenqualität**: Durch die direkte Extraktion aus dem JSON werden mehr strukturierte Daten gewonnen

Die Änderungen wurden in folgenden Dateien implementiert:
- `fetch_and_process.py`: Grundlegende JSON-Extraktionsfunktionen
- `test_one_page.py`: Demonstration der JSON-Extraktion für eine einzelne Seite
- `crawl_all_pages.py`: Multi-Page-Crawler mit JSON-Extraktion
- `test_detail_crawl.py`: Crawler für Listenseite und Detailseiten

## Pagination

Der Crawler unterstützt die Navigation durch mehrere Seiten von Projekten:

- Standardmäßig crawlt `test_crawler.py` nur die erste Seite (max_pages=1)
- Standardmäßig crawlt `db_integration.py` bis zu 5 Seiten (max_pages=5)
- `crawl_all_pages.py` crawlt standardmäßig alle verfügbaren Seiten (bei Remote-Projekten bis zu 14)
- Die Seitengröße kann mit dem Parameter `--page-size` angepasst werden (Standard: 100)
- Der Crawler respektiert die auf der Webseite angegebene Gesamtseitenanzahl

## Detailseiten-Scraping

Der Provider unterstützt jetzt auch das Crawlen von Projektdetailseiten. Dabei werden folgende Informationen extrahiert:

1. **Vollständige Beschreibung**: Der komplette Projektbeschreibungstext
2. **Projektdauer**: Geplante Dauer des Projekts
3. **Stundensatz**: Angebotener Stundensatz oder Gehaltsrahmen
4. **Bewerbungsfrist**: Deadline für Bewerbungen
5. **Ansprechpartner**: Kontaktperson für das Projekt
6. **Zusätzliche Skills**: Detaillierte technische Anforderungen
7. **Anlagen/Attachments**: Zugehörige Dateien und Dokumente

Das Scraping der Detailseiten wird durch folgende Komponenten umgesetzt:
- `test_detail_crawl.py`: Testet das Crawlen von Listenseite und zugehörigen Detailseiten
- Separate Datenbanktabelle `freelance_project_details` für die detaillierten Informationen
- Foreign-Key-Beziehung zur Hauptprojekttabelle für Datenintegrität

## Fehlerbehebung

### Login funktioniert nicht

1. Prüfen Sie, ob der Playwright-Login-Container läuft:
   ```bash
   docker-compose -f docker-compose.dev.yml ps | grep playwright-login
   ```

2. Prüfen Sie die Logs des Containers:
   ```bash
   docker-compose -f docker-compose.dev.yml logs playwright-login
   ```

3. Erstellen Sie einen manuellen Test-Cookie:
   ```bash
   docker-compose -f docker-compose.dev.yml exec crawl4ai python -c "import json; open('/app/providers/freelance/freelance_cookies.json', 'w').write(json.dumps([{\"name\": \"SID\", \"value\": \"test-cookie\", \"domain\": \"freelance.de\", \"path\": \"/\", \"expires\": 1999999999, \"httpOnly\": True, \"secure\": True, \"sameSite\": \"None\"}]))"
   ```

### Datenbank-Integration

Wenn die Datenbankverbindung fehlschlägt:

1. Prüfen Sie, ob die Datenbank läuft:
   ```bash
   docker-compose -f docker-compose.dev.yml ps | grep postgres
   ```

2. Prüfen Sie, ob die Tabelle existiert:
   ```bash
   docker-compose -f docker-compose.dev.yml exec postgres psql -U mailmind -c "\dt freelance_projects"
   docker-compose -f docker-compose.dev.yml exec postgres psql -U mailmind -c "\dt freelance_project_details"
   ```

### JSON-Extraktion funktioniert nicht

Wenn die JSON-Extraktion fehlschlägt:

1. Speichern Sie den HTML-Inhalt zur Inspektion:
   ```bash
   docker-compose -f docker-compose.dev.yml exec crawl4ai python /app/providers/freelance/test_one_page.py
   docker-compose -f docker-compose.dev.yml exec crawl4ai cat /tmp/freelance_page.html | head -n 100
   ```

2. Prüfen Sie das JSON-Format in der Seite:
   ```bash
   docker-compose -f docker-compose.dev.yml exec crawl4ai grep -A 10 "projects" /tmp/freelance_page.html
   ```

### Detailseiten-Crawling funktioniert nicht

Wenn das Crawlen der Detailseiten fehlschlägt:

1. Prüfen Sie die gespeicherten HTML-Dateien:
   ```bash
   docker-compose -f docker-compose.dev.yml exec crawl4ai ls /tmp/freelance_detail_*
   docker-compose -f docker-compose.dev.yml exec crawl4ai head -n 50 /tmp/freelance_detail_*.html
   ```

2. Prüfen Sie, ob die Detailtabelle korrekt erstellt wurde:
   ```bash
   docker-compose -f docker-compose.dev.yml exec postgres psql -U mailmind -c "\d freelance_project_details"
   ```

### Pagination-Probleme

Wenn es Probleme mit der Pagination gibt:

1. Prüfen Sie die Logs auf Paginationsinformationen:
   ```bash
   docker-compose -f docker-compose.dev.yml logs crawl4ai | grep "Seiten gefunden"
   ```

2. Prüfen Sie, ob die URLs korrekt generiert werden:
   ```bash
   docker-compose -f docker-compose.dev.yml logs crawl4ai | grep "Sende Anfrage an"
   ```

## Zukünftige Erweiterungen

- UI-Integration über http://localhost:8080/leads
- Automatisierte regelmäßige Crawls
- Benachrichtigungen bei neuen Projekten
- Filtern nach bestimmten Skills oder Regionen
- Erweiterter Abgleich der Projektdetails mit Nutzerprofilen

## Konfiguration

Die Konfiguration erfolgt über Umgebungsvariablen:

- `DB_USER`: Datenbank-Benutzer (Standard: "mailmind")
- `DB_PASSWORD`: Datenbank-Passwort (Standard: "mailmind")
- `DB_HOST`: Datenbank-Host (Standard: "postgres")
- `DB_PORT`: Datenbank-Port (Standard: "5432")
- `DB_NAME`: Datenbank-Name (Standard: "mailmind")

## Neue Crawl-Logik (ab Juni 2024)

- Der Crawler lädt Projektlisten-Seiten und prüft nach jeder Seite, ob eine Projekt-ID bereits in der Datenbank existiert.
- Sobald eine bekannte Projekt-ID gefunden wird, wird das Crawling der Listen-Seiten abgebrochen.
- Für alle neuen Projekt-IDs werden die Detailseiten gecrawlt und gespeichert.
- Logging, Fehlerbehandlung und Retry-Logik sind integriert.

Beispielablauf:
1. Projektlisten-Seiten werden iteriert, IDs gesammelt.
2. Nach jeder Seite: IDs gegen DB prüfen. Bei bekannter ID → Abbruch.
3. Für neue IDs: Detailseiten werden gecrawlt und gespeichert. 