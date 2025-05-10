# Projektdokumentation (Entwicklungsumgebung)

Dieses Dokument fasst wichtige Aspekte der Konfiguration und des Setups der Entwicklungsumgebung zusammen, insbesondere im Hinblick auf Docker, Machine Learning Modelle und IMAP-Synchronisierung.

## Docker Entwicklungsumgebung

-   **Konfiguration:** `docker-compose.dev.yml`
-   **Umgebungsvariablen:** Werden aus `.env.development` geladen (und `.env` für Produktion). Diese Datei enthält sensible Daten wie API-Keys und Datenbank-Credentials und sollte **nicht** ins Git eingecheckt werden.
-   **Build & Start:**
    ```bash
    # Baut Images neu (falls nötig) und startet alle Services
    docker compose -f docker-compose.dev.yml up --build -d
    ```
-   **Nur Start/Neustart:**
    ```bash
    # Startet Services (ohne Build)
    docker compose -f docker-compose.dev.yml up -d

    # Startet spezifische Services neu (z.B. nach Code-Änderung in Volumes)
    docker compose -f docker-compose.dev.yml restart backend worker
    ```
-   **Logs anzeigen:**
    ```bash
    docker compose -f docker-compose.dev.yml logs -f [service_name]
    # z.B.: docker compose -f docker-compose.dev.yml logs -f backend worker
    ```

## Machine Learning Modell (Sentence Transformer)

### Verwendetes Modell

Aktuell wird das Modell `paraphrase-multilingual-MiniLM-L12-v2` verwendet. Dies wurde von `paraphrase-multilingual-mpnet-base-v2` geändert, um einen lokalen Cache zu nutzen und Build-Probleme zu umgehen.

Die Anpassung erfolgte in:
- `backend/download_models.py`
- `backend/mailmind/ai/download_models.py`
- `backend/mailmind/ai/tasks.py`

### Modell-Cache & Einbindung

Um Speicherprobleme und lange Downloadzeiten beim Docker-Build zu vermeiden, wurde der Modell-Download aus dem `Dockerfile.dev` entfernt.

-   **Download-Logik:** Das Skript `backend/download_models.py` wird nun beim **Start** der Container `backend` und `worker` über die jeweiligen `docker-entrypoint*.sh`-Skripte ausgeführt. Dieses Skript prüft, ob das Modell im Cache vorhanden ist und lädt es nur bei Bedarf herunter.
-   **Lokaler Cache:** Es wird ein lokaler Ordner `./model-cache` im Projektverzeichnis erwartet. Hier sollte das verwendete Modell (`models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2`) liegen.
-   **Volume Mapping:** In `docker-compose.dev.yml` wird dieser lokale Ordner in die Container gemappt:
    ```yaml
    volumes:
      # ... andere volumes ...
      - ./model-cache:/root/.cache/torch/sentence_transformers
    ```
-   **Umgebungsvariable:** Damit die `sentence-transformers`-Bibliothek den Cache-Pfad im Container findet, ist die Umgebungsvariable `SENTENCE_TRANSFORMERS_HOME` in den Services `backend` und `worker` in `docker-compose.dev.yml` auf diesen Pfad gesetzt:
    ```yaml
    environment:
      # ... andere Variablen ...
      - SENTENCE_TRANSFORMERS_HOME=/root/.cache/torch/sentence_transformers
    ```
-   **Vorteil:** Solange das Modell im lokalen `./model-cache` vorhanden ist, wird es beim Container-Start sofort gefunden und nicht erneut heruntergeladen.

## IMAP Ordner Synchronisierung

### Problem: Lokalisierte Ordnernamen

Gmail und andere IMAP-Provider verwenden oft lokalisierte Ordnernamen (z.B. `[Gmail]/All Mail` auf Englisch, `[Gmail]/Alle Nachrichten` auf Deutsch). Ein fester, hartcodierter Ordnername wie `[Gmail]/All Mail` im Code führt zu Fehlern (`[NONEXISTENT] Unknown Mailbox`), wenn die Sprache des Mail-Accounts nicht Englisch ist.

### Robuste Lösung (Bevorzugt, aktuell auskommentiert)

Die zuverlässigste Methode ist, den "Alle Nachrichten"-Ordner über sein standardisiertes IMAP-Flag `\All` zu identifizieren, unabhängig vom Namen.

-   **Implementierung:** Die Funktion `find_all_mail_folder` in `backend/mailmind/imap/sync.py` nutzt `mailbox.folder.list()`, iteriert durch die Ordner und prüft die `flags` jedes Ordners:
    ```python
    # In find_all_mail_folder(mailbox):
    for f in mailbox.folder.list():
        if '\\All' in f.flags: # Direkt auf den String prüfen
            return f.name
    ```
-   Der gefundene (korrekte) Name wird dann an den Sync-Task übergeben.

### Aktueller Workaround (Temporär)

Um schnell einen funktionierenden Stand zu haben, wurde in `backend/mailmind/imap/sync.py` die robuste Lösung (`find_all_mail_folder`) auskommentiert und stattdessen der Ordner `INBOX` fest für die Synchronisierung eingetragen:

```python
# In sync_account(account_id):
# Auskommentiert: Suche nach \All Ordner
# with get_imap_connection(account) as mailbox:
#    target_folder_name = find_all_mail_folder(mailbox)

# Synchronisiere explizit INBOX
target_folder_name = 'INBOX'
logger.info(f"[{account.email}] Explicitly dispatching sync task for folder: {target_folder_name}")
async_task('mailmind.imap.tasks.process_folder_metadata_task', account_id, target_folder_name)
# ...
```

**Empfehlung:** Für eine stabile Lösung sollte zur Methode mit `find_all_mail_folder` und dem `\All`-Flag zurückgekehrt werden, wenn alle relevanten E-Mails synchronisiert werden sollen.

## Troubleshooting Hinweise

-   **Speicherfehler beim Docker Build (`cannot allocate memory`):** Oft beim Modell-Download. Lösung: Speicher für Docker Desktop erhöhen oder (wie hier umgesetzt) Download in Container-Startzeit verlagern und lokalen Cache nutzen.
-   **`AttributeError: 'Settings' object has no attribute 'XYZ'`:** Prüfen, ob die Einstellung `XYZ` in `.env.development` und/oder `backend/config/settings/*.py` korrekt definiert ist und im Code (`settings.XYZ`) richtig darauf zugegriffen wird. Manchmal hilft auch das Löschen alter `.pyc`-Dateien.
-   **Code-Änderungen nicht wirksam:** Sicherstellen, dass der richtige Service neu gestartet wurde (`docker compose restart ...`). Bei tiefergehenden Problemen alte Python-Bytecode-Dateien (`.pyc`) im Container löschen: `docker exec <container_name> find /app -name '*.pyc' -delete` und dann neu starten. 

## API Endpunkte

### `/api/v1/email-accounts/{account_id}/folders/` (GET)

*   **Beschreibung:** Ruft die hierarchische Ordnerstruktur für das angegebene E-Mail-Konto ab.
*   **Berechtigungen:** Nur der authentifizierte Benutzer, dem das Konto gehört.
*   **Antwort (Erfolg, 200 OK):** Ein Array von `FolderItem`-Objekten.
    ```json
    [
      {
        "name": "INBOX",
        "full_path": "INBOX",
        "delimiter": "/",
        "flags": ["\\HasChildren"], // Beispiel-Flags
        "children": [
          {
            "name": "Subfolder",
            "full_path": "INBOX/Subfolder",
            "delimiter": "/",
            "flags": [],
            "children": []
          }
        ]
      },
      {
        "name": "Sent",
        "full_path": "Sent",
        "delimiter": "/",
        "flags": [],
        "children": []
      }
      // ... weitere Ordner
    ]
    ```
*   **Antwort (Fehler):**
    *   `401 Unauthorized`: IMAP-Login fehlgeschlagen.
    *   `404 Not Found`: E-Mail-Konto nicht gefunden oder gehört nicht zum Benutzer.
    *   `400 Bad Request`: Konto nicht korrekt konfiguriert (z.B. kein Passwort/Token).
    *   `500 Internal Server Error`: Allgemeiner Fehler beim Abrufen der Ordner.


## Frontend Komponenten

### `Subheader.tsx`

*   **Ort:** `frontend/src/components/Subheader.tsx`
*   **Beschreibung:** Zeigt eine zweite Kopfzeile unterhalb der Haupt-Navbar an, *ausschließlich* auf der `/aisearch`-Route.
*   **Funktionalität:**
    *   Zeigt ein Dropdown-Menü (`Select`) an, um ein E-Mail-Konto auszuwählen ("All Accounts" oder spezifische Konten des Benutzers).
    *   Ruft die Liste der E-Mail-Konten über `emailAccounts.list()` (`@tanstack/react-query`) ab.
    *   Bei Auswahl eines spezifischen Kontos wird die Ordnerstruktur für dieses Konto über `emailAccounts.getFolders()` angefordert.
    *   Zeigt einen Ladezustand (`CircularProgress`) oder eine Fehlermeldung während des Ordnerabrufs an.
    *   Rendert die `FolderTree`-Komponente zur Anzeige der abgerufenen Ordner.
    *   Enthält ein Such-Icon (`SearchIcon`), dessen Funktionalität noch implementiert werden muss.

### `FolderTree.tsx`

*   **Ort:** `frontend/src/components/FolderTree.tsx`
*   **Beschreibung:** Stellt eine hierarchische Ordnerstruktur mithilfe von MUI `TreeView` dar.
*   **Props:**
    *   `folders: FolderItem[]`: Das Array der Ordnerdaten (verschachtelt), wie es vom API-Endpunkt `/api/v1/email-accounts/{account_id}/folders/` zurückgegeben wird.
    *   `onFolderSelect?: (folderPath: string) => void`: Optionaler Callback, der aufgerufen wird, wenn ein Ordner angeklickt wird. Übergibt den `full_path` des Ordners.
*   **Abhängigkeiten:** `@mui/x-tree-view`
*   **Funktionalität:** Rendert rekursiv `TreeItem`-Elemente für jeden Ordner und dessen Kinder. 

## Dashboard Komponente (`frontend/src/pages/Dashboard.tsx`)

### Beschreibung

Die `Dashboard`-Komponente ist die Hauptansicht nach dem Login und zeigt die E-Mail-Liste, die Detailansicht einer ausgewählten E-Mail und AI-Vorschläge an.

### Kernfunktionalität

*   **E-Mail-Liste**: Zeigt E-Mails für das ausgewählte Konto und den ausgewählten Ordner an (Standard: INBOX). Lädt weitere E-Mails beim Scrollen nach (Infinite Scrolling).
*   **E-Mail-Auswahl**: Der Benutzer kann eine E-Mail aus der Liste auswählen, um sie im Detailbereich anzuzeigen.
*   **Persistenz der Auswahl**: Die ID der zuletzt ausgewählten E-Mail wird im `localStorage` gespeichert. Beim Neuladen der Seite oder beim Wechsel zurück zu einem Ordner wird versucht, diese E-Mail automatisch wieder auszuwählen.
*   **Detailansicht**: Zeigt den Inhalt der ausgewählten E-Mail an (Header, Body). Ermöglicht das Umschalten zwischen HTML-, Markdown- (Standard) und Text-Ansicht, falls verfügbar. Die bevorzugte Ansicht wird ebenfalls im `localStorage` gespeichert.
*   **AI-Vorschläge**: Zeigt kontextbezogene AI-Vorschläge für die ausgewählte E-Mail an (dieser Bereich ist separat implementiert).

### Status des Refactorings (E-Mail-Auswahl-Persistenz, Stand: 07.05.2025)

*   Die Logik zum Laden der E-Mail-Liste und zur Wiederherstellung der Auswahl wurde umfassend überarbeitet, um die Stabilität zu erhöhen.
*   Die Komponente verwendet nun interne Zustände und Refs (`useState`, `useRef`, `useCallback`), um den Ladezustand, die aktuelle Auswahl und die aus `localStorage` geladene Ziel-ID zu verwalten.
*   Die Logik sucht nach der gespeicherten E-Mail-ID auch über mehrere Seiten hinweg.
*   Falls die gespeicherte ID nicht gefunden werden kann (z.B. weil die E-Mail gelöscht wurde oder in einem anderen Ordner ist), wird standardmäßig die erste E-Mail der aktuellen Liste ausgewählt.
*   **Aktueller Stand:** Die grundlegende Funktionalität (Anzeige der Liste, Laden von Details) ist wiederhergestellt. Das Problem, dass nach dem Neuladen eine falsche ID aus dem `localStorage` gelesen wird, wird aktuell untersucht. Das Überschreiben des `localStorage` durch den `FolderEffect` wurde behoben. Finale Tests zur Zuverlässigkeit der Wiederherstellung stehen noch aus.
*   Die Standardansicht für den E-Mail-Inhalt wurde auf Markdown geändert. 

## Freelance Provider Zugangsdaten

Für den Provider freelance.de werden Zugangsdaten wie folgt gespeichert:

- Username (im Klartext)
- Passwort (symmetrisch verschlüsselt mit Fernet, analog zu EmailAccount)
- Zwei Links (z.B. Login-URL, API-URL)
- User-Zuordnung (ForeignKey)
- Timestamps (created_at, updated_at)

Das Passwort wird **niemals** im Klartext gespeichert, sondern ausschließlich verschlüsselt abgelegt. Die Entschlüsselung erfolgt nur im Backend-Code über den symmetrischen Schlüssel (Fernet, abgeleitet aus SECRET_KEY). Die Speicherung und Logik ist produktionssicher und entspricht dem Standard für API-Credentials im System.

Modell: `FreelanceProviderCredential` in `mailmind.freelance.models`. 