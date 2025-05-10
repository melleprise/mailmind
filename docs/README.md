# MailMind - AI E-Mail Assistant

Ein intelligenter E-Mail-Assistent, der die E-Mail-Kommunikation durch KI-gestützte Analyse und Vorschläge effizienter gestaltet.

## Docker Caching

Das Projekt verwendet Docker BuildKit Caching für schnellere Builds:

### NPM Cache
- Persistenter npm Cache über Docker Volumes
- `npm_cache:/root/.npm` für globalen npm Cache
- `frontend_node_modules:/app/node_modules` für projekt-spezifische Module
- Deutlich schnellere Frontend-Builds durch Wiederverwendung gecachter Pakete

### PIP Cache
- Persistenter pip Cache über Docker Volumes
- `pip_cache_dev:/root/.cache/pip` für Python-Pakete
- Beschleunigt Backend-Builds erheblich
- Cache bleibt auch nach Container-Neustarts erhalten

WICHTIG: Die Cache-Volumes niemals manuell löschen, da sie essentiell für die Build-Performance sind!

## Features (v1.0)

- Sichere E-Mail-Konto-Verwaltung (IMAP/OAuth2)
- Echtzeit E-Mail-Empfang via IMAP IDLE
- KI-gestützte Analyse und Vorschlagsgenerierung
- OCR und Embedding von Anhängen
- Intuitive "Tinder-Style" Benutzeroberfläche
- Verwaltung ausstehender E-Mails

## Umgebungen

### Entwicklungsumgebung (MacBook)

Die lokale Entwicklungsumgebung läuft auf dem MacBook und verwendet `docker-compose`:
- Alle Services (Backend, Frontend, Worker, Postgres, Redis, Qdrant, Caddy) werden über `docker-compose.dev.yml` gestartet.
- Debug-Modus ist im Backend aktiviert (siehe `backend/.env`).
- Hot-Reloading für Backend (Django) und Frontend (Vite) ist konfiguriert.
- Datenbank und Redis laufen in Docker-Containern, Daten sind in Docker Volumes persistiert (standardmäßig nicht gelöscht beim Stoppen).
- Qdrant läuft ebenfalls in einem Container.
- Caddy dient als Reverse Proxy für einfaches lokales Routing.

**Setup lokale Entwicklung:**
```bash
# 1. Abhängigkeiten installieren (falls noch nicht geschehen, z.B. Docker Desktop/Colima)
# Siehe docs/Development Environment für Details

# 2. Umgebungsvariablen vorbereiten
# Kopiere backend/.env.example nach backend/.env und passe ggf. an (insbesondere GEMINI_API_KEY)
cp backend/.env.example backend/.env

# 3. Docker Services starten
# Stellt sicher, dass Docker läuft (z.B. Docker Desktop oder `colima start`)
docker compose -f docker-compose.dev.yml up -d --build

# 4. Datenbankmigrationen ausführen (einmalig oder nach Modelländerungen)
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate

# 5. Superuser erstellen (einmalig)
docker compose -f docker-compose.dev.yml exec backend python manage.py createsuperuser
# Folgen Sie den Anweisungen (Email, Passwort)

# 6. Logs anzeigen (optional)
docker compose -f docker-compose.dev.yml logs -f backend worker frontend
```

Die Anwendung ist nun unter folgenden URLs erreichbar (via Caddy Reverse Proxy):
- Frontend: http://localhost (oder die in Caddyfile definierte Domain, falls geändert)
- Backend API: http://localhost/api/ (oder die in Caddyfile definierte Domain)
- Admin Interface: http://localhost/admin/
- Qdrant UI: http://localhost:6333/dashboard
- Caddy Admin API (falls aktiviert): http://localhost:2019

(Der Zugriff auf Postgres direkt ist über Port-Mapping möglich, falls in `docker-compose.dev.yml` konfiguriert, aber pgAdmin ist nicht standardmäßig enthalten).

### Produktionsumgebung (Hetzner)

Die Produktionsumgebung läuft auf Hetzner (IP: `XXX.XXX.XXX.XXX` - Details ggf. im Deployment-Skript oder sicherer Verwaltung)
- Verwendet `docker-compose.prod.yml` (oder Docker Swarm / Kubernetes Konfiguration).
- NGINX oder Caddy als Reverse Proxy mit SSL.
- Persistente Volumes für Datenbank, Redis, Qdrant und Anhänge.
- Produktions-Credentials aus sicherer Quelle (z.B. Secret Management).
- Debug-Modus deaktiviert.
- Strikte Sicherheitseinstellungen.

**Produktions-Zugangsdaten:**
- **[WARNUNG: Produktions-Credentials sollten niemals direkt in der README stehen. Sie sollten über sichere Mechanismen wie Secret Management Tools oder verschlüsselte Umgebungsvariablen verwaltet werden.]**

**Deployment in Produktion:**
(Beispiel - tatsächlicher Prozess kann abweichen)
```bash
# 1. SSH auf den Produktionsserver
ssh user@your_production_server_ip

# 2. Zum Projektverzeichnis navigieren
cd /path/to/mailmind

# 3. Neuesten Code holen
git pull origin main # oder entsprechender Branch

# 4. Produktions-Konfiguration laden (z.B. .env.prod)
# export $(grep -v '^#' .env.prod | xargs)

# 5. Docker Compose Services neu starten/updaten
docker compose -f docker-compose.prod.yml pull # Neueste Images holen
docker compose -f docker-compose.prod.yml up -d --build # Services neu bauen/starten

# 6. Datenbankmigrationen ausführen (falls nötig)
docker compose -f docker-compose.prod.yml exec backend python manage.py migrate
```

### Domains und SSL

**Produktions-Domains:**
- Frontend & API: https://your.production.domain

**SSL-Zertifikate:**
(Beispiel für Certbot mit Nginx/Caddy)
```bash
# Beispiel: Zertifikate erneuern
docker compose -f docker-compose.prod.yml exec your_proxy_service certbot renew

# Beispiel: Status prüfen
docker compose -f docker-compose.prod.yml exec your_proxy_service certbot certificates
```

### Umgebungsvariablen

Die Konfiguration erfolgt über Umgebungsvariablen, die typischerweise aus `.env`-Dateien geladen werden:

**Lokale Entwicklung** (`backend/.env`):
- `DEBUG=True`
- Localhost URLs für Services (Postgres, Redis, Qdrant)
- Entwicklungs-Credentials (z.B. `GEMINI_API_KEY`)
- Wird von `docker-compose.dev.yml` verwendet.

**Produktion** (`.env.prod` oder über Secret Management):
- `DEBUG=False`
- Produktions-URLs/Hostnames für Services
- Sichere Produktions-Credentials (Datenbank-Passwort, Secret Key etc.)
- Wird von `docker-compose.prod.yml` oder dem Deployment-System geladen.

### Sicherheitshinweise

1. **Entwicklung**:
   - Keine echten Produktions-Credentials verwenden
   - Sensitive Daten nicht committen
   - Lokale .env nicht ins Git aufnehmen

2. **Produktion**:
   - Alle Passwörter sicher generieren
   - Separate Datenbank-Benutzer verwenden
   - SSL/TLS erzwingen
   - Firewall konfigurieren
   - Regelmäßige Backups
   - Monitoring aktivieren

### Datenbank-Management

**Entwicklung**:
```bash
# Die Datenbank wird automatisch im Postgres-Container erstellt, wenn er zum ersten Mal gestartet wird.
# (Siehe `POSTGRES_DB` in `docker-compose.dev.yml`)

# Migrationen anwenden (nach dem Starten der Container)
docker compose -f docker-compose.dev.yml exec backend python manage.py migrate

# Superuser für Admin-Interface erstellen (einmalig)
docker compose -f docker-compose.dev.yml exec backend python manage.py createsuperuser
# Folgen Sie den Anweisungen für Email und Passwort.

# Testdaten laden (optional, falls fixtures vorhanden)
# docker compose -f docker-compose.dev.yml exec backend python manage.py loaddata fixtures/dev_data.json
```

**Admin Interface**:
```
URL: http://localhost/admin/ (oder Ihre konfigurierte lokale Domain)
Login: Die bei createsuperuser eingegebenen Zugangsdaten verwenden

Verfügbare Verwaltungsfunktionen:
1. Benutzerverwaltung
   - Benutzer erstellen, bearbeiten, deaktivieren
   - Berechtigungen verwalten
   - E-Mail-Verifizierungsstatus prüfen

2. E-Mail-Konten
   - IMAP/SMTP-Konfigurationen verwalten
   - Verbindungsstatus überprüfen
   - Konten aktivieren/deaktivieren

3. Systemverwaltung
   - Datenbankeinträge direkt bearbeiten
   - Logs einsehen
   - Systemstatus überwachen

Sicherheitshinweise:
- Superuser hat vollständigen Zugriff auf alle Funktionen
- Admin-Zugangsdaten niemals weitergeben
- Regelmäßige Passwortänderungen empfohlen
- Bei Verdacht auf unbefugten Zugriff sofort Passwort ändern
```

**pgAdmin Zugriff**:
(pgAdmin ist nicht standardmäßig im dev-Setup enthalten. Falls hinzugefügt:)
```
URL: http://localhost:5050 (oder konfigurierter Port)
Email: admin@example.com (oder konfigurierte E-Mail)
Passwort: IhrAdminPasswort

Server hinzufügen:
1. Rechtsklick auf "Servers" -> "Register" -> "Server"
2. Name: z.B. "Mailmind Dev DB"
3. Connection Tab:
   - Host name/address: `postgres` (der Service-Name aus Docker Compose)
   - Port: `5432`
   - Maintenance database: `mailmind_dev` (oder der Wert von POSTGRES_DB)
   - Username: `mailmind_dev_user` (oder der Wert von POSTGRES_USER)
   - Password: Das Passwort aus Ihrer `.env`-Datei (POSTGRES_PASSWORD)
4. Save
```

## Technologie-Stack

### Backend
- Python 3.10+
- Django 4.2+ (ASGI)
- Django Channels
- Django REST Framework
- Django-Q
- PostgreSQL
- Qdrant (Vector DB)
- Tesseract OCR
- SentenceTransformers

### Frontend
- React 18
- Material UI (MUI)
- Zustand
- TypeScript

### AI/ML
- Groq API (Llama 3 8B)
- CLIP (Image Embeddings)
- Tesseract OCR

### Infrastruktur
- Docker & Docker Compose
- Caddy (Reverse Proxy)
- Prometheus & Grafana

## Lokale Entwicklung

### Voraussetzungen

- Docker und Docker Compose
- Python 3.10+
- Node.js 18+
- Tesseract OCR

### Setup

1. Repository klonen:
```bash
git clone https://github.com/yourusername/mailmind.git
cd mailmind
```

2. Umgebungsvariablen konfigurieren:
```bash
cp .env.example .env
# .env Datei mit eigenen Werten anpassen
```

3. Docker-Container starten:
```bash
docker-compose up -d
```

4. Backend-Dependencies installieren:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # oder `venv\Scripts\activate` unter Windows
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
```

5. Frontend-Dependencies installieren:
```bash
cd frontend
npm install
npm start
```

Die Anwendung ist nun unter folgenden URLs erreichbar:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api/
- Admin Interface: http://localhost:8000/admin/ (Zugriff nur mit Superuser-Account)
- pgAdmin: http://localhost:5050 (Login: admin@admin.com / admin)

## Deployment

### Voraussetzungen

- Docker und Docker Compose
- Domain mit SSL-Zertifikat
- OpenAI API-Schlüssel
- E-Mail-Server-Zugangsdaten

### Deployment-Schritte

1. Repository klonen:
   ```bash
   git clone https://github.com/yourusername/mailmind.git
   cd mailmind
   ```

2. Umgebungsvariablen konfigurieren:
   ```bash
   cp .env.prod.example .env.prod
   cp .env.prod.db.example .env.prod.db
   ```
   Bearbeiten Sie die `.env.prod` und `.env.prod.db` Dateien und fügen Sie Ihre Konfigurationswerte ein.

3. SSL-Zertifikate platzieren:
   ```bash
   mkdir -p docker/nginx/ssl/live/your-domain.com
   ```
   Kopieren Sie Ihre SSL-Zertifikate in das Verzeichnis:
   - `fullchain.pem` -> `docker/nginx/ssl/live/your-domain.com/fullchain.pem`
   - `privkey.pem` -> `docker/nginx/ssl/live/your-domain.com/privkey.pem`

4. Nginx-Konfiguration anpassen:
   Bearbeiten Sie `docker/nginx/nginx.conf` und aktualisieren Sie den `server_name` und SSL-Zertifikatspfade.

5. Docker-Images bauen und Container starten:
   ```bash
   docker-compose -f docker-compose.prod.yml build
   docker-compose -f docker-compose.prod.yml up -d
   ```

6. Datenbank-Migrationen ausführen:
   ```bash
   docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
   ```

7. Superuser erstellen:
   ```bash
   docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
   ```

8. Statische Dateien sammeln:
   ```bash
   docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic
   ```

### Wartung

- Logs überprüfen:
  ```bash
  docker-compose -f docker-compose.prod.yml logs -f
  ```

- Container neustarten:
  ```bash
  docker-compose -f docker-compose.prod.yml restart
  ```

- Updates einspielen:
  ```bash
  git pull
  docker-compose -f docker-compose.prod.yml build
  docker-compose -f docker-compose.prod.yml up -d
  docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate
  ```

### Backup

1. Datenbank sichern:
   ```bash
   docker-compose -f docker-compose.prod.yml exec db pg_dump -U mailmind_user mailmind > backup.sql
   ```

2. Datenbank wiederherstellen:
   ```bash
   cat backup.sql | docker-compose -f docker-compose.prod.yml exec -T db psql -U mailmind_user mailmind
   ```

### Monitoring

- Container-Status überprüfen:
  ```bash
  docker-compose -f docker-compose.prod.yml ps
  ```

- Ressourcennutzung überwachen:
  ```bash
  docker stats
  ```

## Sicherheit

- Alle Passwörter und API-Schlüssel sicher aufbewahren
- Regelmäßige Sicherheitsupdates durchführen
- SSL-Zertifikate aktuell halten
- Firewall-Regeln überprüfen
- Backup-Strategie implementieren

## Lizenz

[MIT](LICENSE)

## Beitragende

- [Ihr Name] - Initialer Entwickler

## Test Deployment
Testing automatic deployment to production server.
Deployment status: 
- ✅ GitHub Actions configured
- ✅ Docker Hub integration added
- 🔄 Testing simplified deployment pipeline
- ⏱️ Starting deployment: $(date)

Last test: April 18, 2025 

## Development Environment

### Backend Requirements

- Python 3.11
- Virtual environment recommended

Key dependencies:
- sentence-transformers >= 4.1.0
- numpy >= 2.0.0 
- huggingface-hub >= 0.23.0

### Setup Development Environment

1. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r backend/requirements.txt
```

### Docker Environment 

The application runs in Docker containers:

#### Backend Container
- Base image: python:3.11-slim
- Python packages installed from wheels for better performance
- Key ML dependencies:
  - sentence-transformers >= 4.1.0 (for text embeddings)
  - numpy >= 2.0.0 (required by ML components)
  - huggingface-hub >= 0.23.0 (model management)

#### Frontend Container  
- Node 18 Alpine base image
- npm packages installed with --legacy-peer-deps

### Building & Running

1. Build containers:
```bash
docker compose build
```

2. Run application:
```bash
docker compose up
```

Access the application at http://localhost:3000 

## Container-Entwicklung und Sicherheit

### Manuelle Container-Tests

Bevor ein neuer Container-Build durchgeführt wird, sollten die Änderungen manuell getestet werden:

1. **Container-Umgebung starten und prüfen**:
```bash
# Container starten
docker run -it --name mailmind-backend-test python:3.11-slim /bin/bash

# SOFORT nach dem Start diese Funktion kopieren und ausführen
check_container() {
    if [ ! -f /.dockerenv ]; then
        echo "🛑 STOP! GEFAHR! 🛑"
        echo "Du bist auf dem Host-System, NICHT im Container!"
        return 1
    else
        echo "✅ Container-Check bestanden"
        return 0
    fi
}

# Prüfen ob im Container
check_container || exit 1
```

2. **Basis-Setup als root**:
```bash
# WICHTIG: Diese Befehle müssen als root ausgeführt werden!
[ -f /.dockerenv ] && {
    # System-Pakete aktualisieren
    apt-get update
    apt-get install -y --no-install-recommends \
        python3-venv \
        python3-pip \
        python3-dev

    # Benutzer erstellen
    groupadd -r appgroup
    useradd -r -g appgroup appuser
    
    # Verzeichnisse erstellen mit korrekten Rechten
    mkdir -p /app /wheels /home/appuser
    chown -R appuser:appgroup /app /wheels /home/appuser
    chmod 755 /home/appuser
    
    # Python-Verzeichnisse vorbereiten
    mkdir -p /home/appuser/.local
    chown -R appuser:appgroup /home/appuser/.local
    
    echo "Basis-Setup abgeschlossen ✓"
}
```

3. **Python-Umgebung als appuser einrichten**:
```bash
# Als appuser wechseln
su - appuser  # WICHTIG: Das "-" lädt das komplette Benutzerprofil

# Überprüfen ob man appuser ist
whoami | grep "appuser" || {
    echo "FEHLER: Nicht als appuser angemeldet!"
    exit 1
}

# Python-Umgebung einrichten
cd /app
python3 -m venv venv
source venv/bin/activate

# Überprüfen ob venv aktiv ist
which python | grep "/app/venv" || {
    echo "FEHLER: Virtual Environment nicht aktiv!"
    exit 1
}

# Basis-Pakete installieren
pip install --upgrade pip wheel setuptools
```

4. **Entwicklungs-Dependencies installieren**:
```bash
# WICHTIG: Erst prüfen ob venv aktiv ist!
which python | grep "/app/venv" && {
    # Requirements installieren
    pip install \
        "sentence-transformers>=4.1.0" \
        "numpy>=2.0.0" \
        "huggingface-hub>=0.23.0"
    
    # Weitere projektspezifische Pakete...
    pip install -r requirements.txt  # wenn die Datei verfügbar ist
}
```

5. **Erfolgreiche Schritte dokumentieren**:
   - Alle funktionierenden Befehle in einer temporären Datei speichern
   - Fehler und deren Lösungen notieren
   - Reihenfolge-Abhängigkeiten dokumentieren
   - Besonders auf Berechtigungsprobleme achten

6. **In Dockerfile übertragen**:
   - Getestete und funktionierende Befehle ins Dockerfile übernehmen
   - Dokumentierte Fehler als Kommentare hinzufügen
   - Build testen: `docker build -t mailmind-backend .`

### Wichtige Prüfungen

**Benutzer und Berechtigungen**:
```bash
# Aktuellen Benutzer prüfen
whoami

# Virtual Environment prüfen
which python
echo $VIRTUAL_ENV

# Verzeichnisberechtigungen prüfen
ls -la /app
ls -la /home/appuser/.local
ls -la $VIRTUAL_ENV
```

**Python-Umgebung**:
```bash
# Python-Version und Pfad prüfen
python --version
which python
pip --version
which pip

# Installierte Pakete auflisten
pip list
```

### Container-Sicherheit

**Wichtige Sicherheitsregeln:**

1. **Container-Check vor Befehlen**:
```bash
# Bash-Funktion für sicheres Ausführen von Befehlen
safe_execute() {
    if [ -f /.dockerenv ]; then
        echo "Container-Umgebung bestätigt ✓"
        eval "$@"
    else
        echo "WARNUNG: Nicht im Container! Befehl wurde NICHT ausgeführt: $@"
        return 1
    fi
}

# Beispiel Verwendung
safe_execute "pip install package_name"
```

2. **Berechtigungsprüfung**:
```bash
# Prüfen ob man als root oder normaler Benutzer arbeitet
check_user() {
    if [ $(id -u) = 0 ]; then
        echo "WARNUNG: Als root angemeldet!"
        echo "Wechsle zu einem normalen Benutzer mit 'su appuser'"
        return 1
    else
        echo "Normaler Benutzer ✓"
        return 0
    fi
}
```

3. **Verzeichnis-Berechtigungen**:
```bash
# Berechtigungen prüfen und setzen
check_permissions() {
    local dir=$1
    if [ -w "$dir" ]; then
        echo "Schreibrechte für $dir vorhanden ✓"
    else
        echo "FEHLER: Keine Schreibrechte für $dir"
        echo "Führe aus: chown -R appuser:appgroup $dir"
        return 1
    fi
}
```

### Best Practices für Container-Entwicklung

1. **Schrittweise Entwicklung**:
   - Erst manuell im Container testen
   - Erfolgreiche Befehle dokumentieren
   - In Dockerfile übertragen
   - Build testen
   - Bei Fehlern: Zurück zu manuellem Test

2. **Debugging**:
   - Container mit Shell starten: `docker run -it --rm image_name /bin/bash`
   - Logs überprüfen: `docker logs container_name`
   - Prozesse prüfen: `ps aux` im Container
   - Berechtigungen prüfen: `ls -la` für relevante Verzeichnisse

3. **Sicherheit**:
   - Nie als root arbeiten wenn möglich
   - Berechtigungen explizit setzen
   - Umgebungsvariablen prüfen
   - Netzwerkzugriffe minimieren

4. **Dokumentation**:
   - Alle erfolgreichen Änderungen dokumentieren
   - Fehlgeschlagene Versuche und Lösungen notieren
   - Abhängigkeiten zwischen Schritten festhalten
   - Build-Prozess dokumentieren 

## ⚠️ WICHTIG: Container vs. Host Ausführung

### Kritische Sicherheitswarnung

**NIEMALS** Befehle blind kopieren und ausführen! Immer erst prüfen, ob man im Container oder auf dem Host-System ist.

### Container-Check Funktion

Kopiere diese Funktion zu Beginn in deine Shell:
```bash
check_container() {
    if [ ! -f /.dockerenv ]; then
        echo "🛑 STOP! GEFAHR! 🛑"
        echo "Du bist auf dem Host-System, NICHT im Container!"
        echo "Dieser Befehl könnte dein System beschädigen."
        echo ""
        echo "Schritte zur Korrektur:"
        echo "1. Prüfe ob du im richtigen Terminal-Fenster bist"
        echo "2. Starte ggf. einen neuen Container mit:"
        echo "   docker run -it --name mailmind-backend-test python:3.11-slim /bin/bash"
        return 1
    else
        echo "✅ Container-Check bestanden"
        echo "🔒 Du bist sicher im Container"
        return 0
    fi
}

# Alias für häufige Befehle
alias safe_pip='check_container && pip'
alias safe_apt='check_container && apt-get'
```

### Verwendung

1. **IMMER** zuerst prüfen:
```bash
check_container || exit 1
```

2. **NIEMALS** Befehle ausführen, wenn der Check fehlschlägt:
```bash
# FALSCH ❌
apt-get update

# RICHTIG ✅
check_container && apt-get update
# oder
safe_apt update
```

3. **Bei jedem neuen Terminal** neu prüfen:
```bash
# Nach dem Öffnen eines neuen Terminals
check_container || { echo "Falsches Terminal!"; exit 1; }
```

### Typische Gefahrensituationen

1. **Mehrere Terminal-Fenster offen**:
   - Einige im Container
   - Andere auf dem Host
   - ➡️ Immer `check_container` ausführen!

2. **Nach Container-Neustart**:
   - Altes Terminal zeigt noch auf Host
   - ➡️ `check_container` vor jedem Befehl!

3. **Copy & Paste von Befehlen**:
   - Nie blind einfügen
   - ➡️ Erst `check_container`, dann ausführen

### Best Practices

1. **Terminal-Kennzeichnung**:
```bash
# Im Container-Terminal ausführen
PS1="🐳 Container \w # "
```

2. **Befehle gruppieren**:
```bash
# Mehrere Befehle sicher ausführen
check_container && {
    command1
    command2
    command3
}
```

3. **Automatische Prüfung**:
```bash
# In ~/.bashrc oder ~/.zshrc im Container
if [ -f /.dockerenv ]; then
    echo "🐳 Container-Umgebung"
    PS1="🐳 \w # "
else
    echo "⚠️ Host-System!"
    PS1="🏠 \w $ "
fi
``` 

## Cursor-IDE Container Entwicklung

### Container-Session Setup

1. **Container Status prüfen**:
```bash
# Zeige alle laufenden Container
docker ps

# Notiere die Container-ID des Backend-Containers
# Format: email-ai-tinder-backend-run-XXXXXXXX
```

2. **Vor JEDEM Befehl prüfen**:
```bash
# Prüfe ob du im Host-System bist
if [ -z "$DOCKER_CONTAINER" ]; then
    echo "⚠️ WARNUNG: Du bist auf dem Host-System!"
    echo "Starte eine neue Container-Session mit:"
    echo "docker exec -it CONTAINER_ID bash"
    exit 1
fi

# Prüfe ob du im richtigen Container bist
if [ "$DOCKER_CONTAINER" != "email-ai-tinder-backend" ]; then
    echo "⚠️ WARNUNG: Falscher Container!"
    echo "Aktueller Container: $DOCKER_CONTAINER"
    echo "Erwarteter Container: email-ai-tinder-backend"
    exit 1
fi
```

3. **Neue Container-Session starten**:
```bash
# Container-ID aus docker ps verwenden
docker exec -it CONTAINER_ID bash

# Sofort nach dem Verbinden prüfen
echo $DOCKER_CONTAINER
```

### Sicherheits-Checks

1. **Host vs. Container Check**:
```bash
# Diese Funktion in deine .bashrc oder .zshrc kopieren
check_environment() {
    if [ -z "$DOCKER_CONTAINER" ]; then
        echo "🏠 Host-System"
        PS1="🏠 \w $ "
        return 1
    elif [ "$DOCKER_CONTAINER" = "email-ai-tinder-backend" ]; then
        echo "🐳 Backend-Container"
        PS1="🐳 \w # "
        return 0
    else
        echo "⚠️ Falscher Container: $DOCKER_CONTAINER"
        PS1="⚠️ \w # "
        return 1
    fi
}

# Bei jedem Befehl prüfen
check_environment || exit 1
```

2. **Automatische Prüfung einrichten**:
```bash
# In die .bashrc oder .zshrc des Containers einfügen
if [ -f /.dockerenv ]; then
    export DOCKER_CONTAINER=$(cat /etc/hostname)
    check_environment || {
        echo "⚠️ Falsche Umgebung!"
        return 1
    }
fi
```

### Best Practices für Cursor-IDE

1. **Vor jedem Befehl**:
   - Container-Status prüfen
   - Umgebungsvariablen verifizieren
   - Berechtigungen kontrollieren

2. **Nach Container-Neustart**:
   - Neue Session mit `docker exec` starten
   - Umgebung sofort prüfen
   - Benutzerkontext verifizieren

3. **Bei mehreren Terminals**:
   - Jedes Terminal einzeln prüfen
   - Container-ID verifizieren
   - Benutzerkontext bestätigen 





docker befehle

docker compose -f docker-compose.dev.yml exec frontend

docker compose -f docker-compose.dev.yml backend up -d --build

docker compose -f docker-compose.dev.yml down && docker compose -f docker-compose.dev.yml build backend && docker compose -f docker-compose.dev.yml up -d

docker compose -f docker-compose.dev.yml down && \
docker compose -f docker-compose.dev.yml build backend && \
docker compose -f docker-compose.dev.yml up -d

docker compose -f docker-compose.dev.yml down && docker system prune -af && docker volume prune -f && docker network prune -f

docker compose -f docker-compose.dev.yml logs -f mailmind-dev-frontend

docker compose -f docker-compose.dev.yml run --entrypoint sh frontend

