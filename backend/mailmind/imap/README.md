# Mailmind IMAP Module

Dieses Modul ist verantwortlich für die Interaktion mit IMAP-Servern, um E-Mails abzurufen, zu verarbeiten und in der Django-Datenbank zu speichern.

## Core Workflow (Batch Sync)

Der primäre Arbeitsablauf für die Synchronisierung eines E-Mail-Kontos über den periodischen Task `schedule_account_sync` läuft wie folgt ab:

1.  **Task Scheduling (`sync.py` -> Django Q):**
    *   Ein geplanter Django Q Task (`schedule_account_sync`) wird periodisch ausgeführt.
    *   Dieser Task ruft `sync_account_task` für jedes aktive `EmailAccount` auf.

2.  **Account Sync Dispatch (`tasks.py: sync_account_task`):
    *   Der `sync_account_task` holt die Details des Kontos (Account-ID wird übergeben).
    *   Stellt eine IMAP-Verbindung her (`connection.py`).
    *   Holt die Liste aller Ordner vom Server.
    *   Filtert die Ordner, die synchronisiert werden sollen (basierend auf `FOLDER_PRIORITIES` und Flags wie `\Noselect`).
    *   Startet **für jeden** zu synchronisierenden Ordner einen separaten `process_folder_metadata_task`.

3.  **Folder Metadata Processing (`tasks.py: process_folder_metadata_task`):
    *   Dieser Task erhält die Account-ID und den Ordnernamen.
    *   Holt die Liste der bereits in der DB vorhandenen UIDs für diesen Ordner/Account.
    *   Ruft `fetch_folder_uids` (`fetch.py`) auf, um die UIDs vom Server zu holen und mit den DB-UIDs abzugleichen.

4.  **UID Fetching & Metadata Mapping (`fetch.py: fetch_folder_uids`):
    *   Selektiert den entsprechenden Ordner auf dem Server.
    *   Holt *alle* UIDs aus dem Ordner.
    *   Vergleicht die Server-UIDs mit den bekannten DB-UIDs.
    *   Für jede **neue** UID:
        *   Extrahiert die grundlegenden Metadaten (Absender, Empfänger, Datum, Betreff, Flags, Labels etc.) mittels `imap_tools`.
        *   Ruft `map_metadata_to_db` (`mapper.py`) auf, um die rohen Daten in ein Dictionary zu mappen, das den Feldern des `Email`-Modells entspricht.
        *   Fügt die UID zur Liste `new_uids_to_fetch_full` hinzu.
    *   Gibt die Liste `new_uids_to_fetch_full` zurück an `process_folder_metadata_task`.

5.  **Full Content Fetch Dispatch (`tasks.py: process_folder_metadata_task`):
    *   Wenn `fetch_folder_uids` neue UIDs zurückgegeben hat, ruft dieser Task `fetch_uids_full` (`fetch.py`) auf und übergibt die Liste der neuen UIDs.

6.  **Full Content Fetching & Batch Task Queuing (`fetch.py: fetch_uids_full`):
    *   Nimmt die Liste der neuen UIDs entgegen.
    *   Iteriert über die UIDs in Batches (Größe definiert durch `FULL_EMAIL_BATCH_SIZE`).
    *   Für jeden Batch:
        *   Holt den **vollen Inhalt** (Body Text, Body HTML, Header, Größe, Anhänge) für die UIDs im Batch vom Server.
        *   Ruft für jede E-Mail im Batch `map_full_email_to_db` (`mapper.py`) auf. Diese Funktion erweitert das Metadaten-Mapping um die Inhaltsfelder.
        *   Sammelt die resultierenden Dictionaries (eines pro E-Mail) in einer Liste (`batch_content_data`).
        *   Startet **einen** `save_batch_content_task` (`tasks.py`) und übergibt die `batch_content_data` und die `account_id`.

7.  **Content Saving & Markdown Trigger (`tasks.py: save_batch_content_task` -> `store.py`):
    *   Der Task erhält die Liste der E-Mail-Daten-Dictionaries für den Batch.
    *   Iteriert durch die Liste und ruft für jedes Dictionary `save_email_content_from_dict` (`store.py`) auf.
    *   `save_email_content_from_dict` führt ein `Email.objects.update_or_create` aus, basierend auf `account`, `uid` und `folder_name`.
        *   Wenn die E-Mail neu ist (basierend auf UID/Folder), wird sie mit allen Metadaten und Inhaltsfeldern erstellt.
        *   Wenn die E-Mail bereits existiert (sollte im normalen "neue E-Mails"-Flow nicht passieren, aber zur Sicherheit), werden die Felder aktualisiert.
    *   Verarbeitet Anhänge (`_process_attachments_from_dict`).
    *   Wenn `body_html` vorhanden ist, startet es asynchron den `generate_markdown_for_email_task`.

8.  **Markdown Generation (`tasks.py: generate_markdown_for_email_task`):
    *   Dieser asynchrone Task erhält die `email_id`.
    *   Holt das `Email`-Objekt.
    *   Konvertiert `body_html` zu Markdown mittels `html2text`.
    *   Speichert das Ergebnis im Feld `markdown_body`.

## Wichtige Komponenten

*   **`sync.py`:** Enthält die Hauptlogik zum Starten des Synchronisationsprozesses für ein Konto und die Iteration über die zu synchronisierenden Ordner.
*   **`tasks.py`:** Definiert die `django-q`-Hintergrundtasks (`process_folder_metadata_task`, `save_metadata_task`, `save_batch_content_task`), die die eigentliche Arbeit asynchron ausführen.
*   **`fetch.py`:** Verantwortlich für das Abrufen von Daten vom IMAP-Server. Enthält Funktionen zum Holen von Metadaten (`fetch_folder_uids`), zum Berechnen von Batches (`calculate_batches`) und zum Holen der vollständigen E-Mail-Inhalte in Batches (`fetch_uids_full`).
*   **`store.py`:** Beinhaltet die Logik zum Speichern und Aktualisieren von `Email`-Objekten und zugehörigen Daten (wie `Contact`, `Attachment`) in der Django-Datenbank. Hier findet auch die Bestimmung des `folder_name` und die Konvertierung von HTML zu Markdown (`body_markdown` via `html2text`) statt. Die Konvertierung von HTML zu Markdown (`body_markdown` via `html2text`) wurde in einen separaten Task ausgelagert.
*   **`connection.py`:** Verwaltet IMAP-Verbindungen, inklusive Authentifizierung, Pooling und Fehlerbehandlung. Bietet den `get_imap_connection`-Context-Manager.
*   **`mapper.py`:** Übersetzt die Datenstrukturen von `imap_tools` (`MailMessage`) oder Dictionaries in Dictionaries, die für das Speichern im `Email`-Modell geeignet sind.
*   **`consumers.py`:** Enthält den WebSocket-Consumer für die IMAP `IDLE`-Funktionalität (Echtzeit-Benachrichtigungen über neue E-Mails). Dies ist ein separater Workflow vom Batch-Sync.
*   **`utils.py`:** Diverse Hilfsfunktionen, z.B. zum Dekodieren von Headern, Priorisierung von Ordnern.

## Wichtige Konzepte & Überlegungen

*   **Asynchrone Verarbeitung:** Der gesamte Sync-Prozess läuft über `django-q`-Background-Tasks. Der `worker`-Dienst muss laufen.
*   **Zwei-Phasen-Sync:** Metadaten werden zuerst geholt und gespeichert, danach erst die Inhalte. Das stellt sicher, dass E-Mails schnell in der UI sichtbar sind, auch wenn das Holen großer Inhalte länger dauert.
*   **Batching:** Sowohl Metadaten als auch Inhalte werden in Batches vom IMAP-Server geholt, um die Anzahl der Anfragen zu reduzieren. Die Inhalts-Speicherung erfolgt ebenfalls pro Batch in einem Task.
*   **Ordnernamen (`folder_name`):** Der in der DB gespeicherte `folder_name` wird nicht direkt vom IMAP-Ordner übernommen (wie `[Gmail]/All Mail`), sondern versucht, den "logischen" Ordner anhand von IMAP-Flags und Gmail-Labels (`X-GM-LABELS`) zu bestimmen (z.B. 'Sent Mail', 'Drafts', 'MyCustomLabel'). Siehe `_determine_folder_name` in `store.py`.
*   **Fehlerbehandlung:** Es gibt grundlegende Fehlerbehandlung (z.B. bei Verbindungsfehlern, fehlenden Konten), aber sie könnte noch robuster sein (z.B. Wiederholungsversuche für fehlgeschlagene Tasks/Batches).
*   **Message-ID:** Die `message_id` wird als primärer Schlüssel (zusammen mit `account`) verwendet, um E-Mails in der Datenbank eindeutig zu identifizieren und Updates korrekt zuzuordnen.
*   **IMAP-Eigenheiten:** Speziell die Verwendung von `X-GM-LABELS` ist Gmail-spezifisch. Die Robustheit für andere IMAP-Server ist möglicherweise eingeschränkt.
*   **Rate Limiting:** Es gibt rudimentäre Ansätze für Rate Limiting in `utils.py`, die aber aktuell nicht aktiv im Haupt-Sync-Flow verwendet werden.

## Persistenter IDLE Workflow (Real-Time Updates)

Zusätzlich zum Batch-Sync gibt es einen Mechanismus für Echtzeit-Benachrichtigungen über neue E-Mails:

1.  **Start:** Beim Start der Django-Anwendung (`ImapConfig.ready()` in `apps.py`) wird ein Manager-Thread (`idle_manager.py:start_idle_manager`) gestartet.
2.  **Manager (`idle_manager.py:manage_idle_connections`):**
    *   Dieser asynchrone Task läuft kontinuierlich.
    *   Er überwacht alle als `is_active=True` markierten `EmailAccount`-Objekte.
    *   Für jeden aktiven Account startet und überwacht er einen dedizierten `asyncio`-Task (`run_idle_for_account`).
    *   Er beendet Tasks für Accounts, die inaktiv werden.
3.  **Account IDLE Task (`idle_manager.py:run_idle_for_account`):**
    *   Dieser Task läuft persistent für einen spezifischen Account.
    *   Er baut eine IMAP-Verbindung mit `aioimaplib` auf (inklusive Passwort-Entschlüsselung).
    *   Er geht in den IMAP `IDLE`-Modus und wartet auf Server-Benachrichtigungen (`wait_server_push`).
    *   Bei einer `EXISTS`-Benachrichtigung (neue Mail): Startet einen Django Q Task (`tasks.py:process_idle_update_task`) mit der `account_id` und geht sofort wieder in den `IDLE`-Modus.
    *   Behandelt Verbindungsfehler und versucht, sich neu zu verbinden.
4.  **Worker Task (`tasks.py:process_idle_update_task`):**
    *   Wird von Django Q ausgeführt.
    *   Holt eine `imap-tools`-Verbindung über `connection.py:get_imap_connection`.
    *   Sucht **nur** nach `UNSEEN` E-Mails für den Account.
    *   Ruft die vollständigen Daten dieser E-Mails in Batches ab (`mailbox.fetch(..., mark_seen=False)`).
    *   Verarbeitet jede neue E-Mail:
        *   Mappt die Daten mit `mapper.py:map_full_email_to_db`.
        *   Speichert Metadaten mit `store.py:save_email_metadata_from_dict`.
        *   Speichert den Inhalt mit `store.py:save_email_content_from_dict`.
        *   **Neu:** Nach dem Speichern wird der `generate_markdown_for_email_task` angestoßen, um `body_markdown` via `html2text` zu generieren.
    *   Wenn erfolgreich, sendet der Task eine Nachricht (`type='imap.refresh_event'`) an die Channels-Gruppe `imap_updates_{account_id}`.
5.  **WebSocket Consumer (`consumers.py:IMAPConsumer`):**
    *   Wird gestartet, wenn das Frontend eine WebSocket-Verbindung zu `/ws/imap/{account_id}/` aufbaut.
    *   Baut **keine** eigene IMAP-Verbindung mehr auf.
    *   Tritt der Channels-Gruppe `imap_updates_{account_id}` bei.
    *   Empfängt die `imap.refresh_event`-Nachricht vom Worker-Task.
    *   Leitet eine `refresh_needed`-Nachricht an das verbundene Frontend weiter.
6.  **Frontend:** Das Frontend muss auf die `refresh_needed`-Nachricht reagieren und z.B. die E-Mail-Liste neu laden.

Dieser Ansatz trennt das dauerhafte Lauschen (IDLE-Manager) vom ressourcenintensiven Abrufen und Verarbeiten (Worker-Task) und informiert das Frontend nur nach erfolgreicher Speicherung. 