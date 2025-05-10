# Freelance.de Crawler für Crawl4AI

Diese Dokumentation beschreibt die Integration des Freelance.de-Crawlers in die Crawl4AI-Plattform.

## Überblick

Der Freelance-Crawler ermöglicht das automatisierte Crawlen von Projekten auf freelance.de und speichert diese in einer Postgres-Datenbank. Die Integration umfasst:

1. Automatisierte Authentifizierung über den Playwright-Login Service
2. Extrahieren von Projektdaten aus der Projektliste
3. Strukturierte Aufbereitung der Daten für die Datenbank 
4. Speicherung in der PostgreSQL-Datenbank

## Komponenten

### 1. Authentifizierung

Die Authentifizierung erfolgt über zwei alternative Wege:

- **Playwright-Login Service**: Ein separater Docker-Container, der sich per Playwright bei freelance.de einloggt und Cookies speichert
- **Integriertes Login-Skript**: Ein Node.js-Skript, das direkt aus dem Crawler heraus ausgeführt werden kann

Der Crawler prüft automatisch, ob gültige Cookies vorhanden sind. Falls nicht, wird je nach Umgebung der Playwright-Login Service aufgerufen oder das integrierte Login-Skript ausgeführt.

### 2. Datenextraktion

Der Crawler verwendet:
- BeautifulSoup für das HTML-Parsing
- Ein strukturiertes Pydantic-Modell zur Datentransformation

Folgende Daten werden extrahiert:
- Projekt-ID
- Titel
- Unternehmen
- Enddatum
- Standort
- Remote-Status
- Skills
- Bewerbungsstatus
- URL
- Aktualisierungsdatum

### 3. Datenbankintegration

Die gescrapten Daten werden in der PostgreSQL-Datenbank in der Tabelle `freelance_projects` gespeichert. Die Speicherung erfolgt transaktionsbasiert und unterstützt sowohl das Einfügen neuer als auch das Aktualisieren bestehender Datensätze.

## Installation

### Abhängigkeiten

```
httpx
pydantic 
beautifulsoup4
python-slugify
asyncpg
```

Alle Abhängigkeiten sind in der `requirements.txt` von Crawl4AI enthalten.

## Verwendung

### Grundlegende Verwendung

Der Crawler kann auf verschiedene Weise verwendet werden:

1. **Als Test-Skript**:

```bash
python providers/freelance/test_crawler.py
```

Dies führt einen Test-Crawl durch und speichert die Ergebnisse in einer JSON-Datei.

2. **Mit Datenbankintegration**:

```bash
python providers/freelance/db_integration.py
```

Dies führt einen Crawl durch und speichert die Ergebnisse direkt in der Datenbank.

### Automatisiertes Crawling im Docker-Container

Im Docker-Container kann das Crawling automatisiert ausgeführt werden:

```bash
# Crawlen und in JSON speichern (für Tests)
docker-compose exec crawl4ai python /app/providers/freelance/test_crawler.py

# Crawlen und in Datenbank speichern
docker-compose exec crawl4ai python /app/providers/freelance/db_integration.py
```

## Architektur

```
/crawl4ai
  /providers
    /freelance
      - fetch_and_process.py      # Hauptlogik zum Crawlen und Verarbeiten
      - db_integration.py         # Datenbankintegration
      - test_crawler.py           # Test-Skript
      - login.sh                  # Shell-Skript für Login
      - login.js                  # Node.js-Skript für Login
      - freelance_cookies.json    # Speicherort für Cookies
```

## Zukünftige Erweiterungen

Für die Zukunft sind folgende Erweiterungen geplant:

1. **UI-Integration**: Crawling-Konfiguration und Anzeige der gescrapten Daten über http://localhost:8080/leads
2. **Dynamische User-ID**: Integration mit dem Benutzer-Authentifizierungssystem

## Fehlerbehebung

### Problem: Login funktioniert nicht

1. Prüfen Sie, ob der Playwright-Login-Container läuft: `docker-compose ps | grep playwright-login`
2. Prüfen Sie die Logs des Containers: `docker-compose logs playwright-login`
3. Prüfen Sie die Login-Daten in `fetch_and_process.py` oder `login.js`

### Problem: Datenbank-Verbindung schlägt fehl

1. Prüfen Sie, ob die Datenbank läuft: `docker-compose ps | grep postgres`
2. Prüfen Sie die Datenbankverbindungsparameter in `db_integration.py`

### Problem: Keine Projekte gefunden

1. Prüfen Sie, ob die Cookies gültig sind: `cat providers/freelance/freelance_cookies.json`
2. Prüfen Sie die Logs auf HTTP-Statuscodes oder andere Fehler 