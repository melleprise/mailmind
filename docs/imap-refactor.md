
Okay, verstanden. Wenn es sich um den **initialen Sync** handelt und du davon ausgehst, dass lokal noch *keine* UIDs für diesen Ordner bekannt sind, dann können wir den Vergleich überspringen. Das vereinfacht den Ablauf für diesen speziellen Fall:

1.  **Ordner auswählen:** Wähle `[Gmail]/All Mail`.
2.  **Server UIDs holen:** Rufe *alle* UIDs vom Server für `[Gmail]/All Mail` ab. (`new_uids` = `server_uids`).
3.  **Metadaten holen:** Hole Metadaten (`UID`, `FLAGS`, `INTERNALDATE`, `RFC822.SIZE`) für *alle* Server-UIDs.
4.  **Filtern & Sortieren:**
    *   Filtere optional nach Alter (`max_age_days`).
    *   Sortiere die verbleibenden UIDs (z.B. Größe, Datum).
5.  **Batch-Download (nach Größe):**
    *   Erstelle Batches der sortierten UIDs basierend auf Gesamtgröße.
    *   Lade den vollen Inhalt (`RFC822`) pro Batch herunter.
6.  **Verarbeiten:**
    *   Serialisiere jede Nachricht aus den Batches.
    *   Starte den Task `process_individual_email_task` für jede Nachricht.
7.  **Status speichern:** Speichere *alle* UIDs (die verarbeitet oder übersprungen wurden) als initial synchronisiert für `[Gmail]/All Mail`.

Für **nachfolgende Syncs** desselben Ordners müsstest du dann aber wieder den UID-Vergleich (Schritt 2 im vorherigen Plan) durchführen, um nur die *wirklich* neuen Nachrichten seit dem letzten Sync zu holen.



Okay, ich recherchiere kurz online in der Dokumentation von `imap_tools`, welche Metadaten über das `MailMessage`-Objekt verfügbar sind.

Ran tool
Die Dokumentation von `imap_tools` listet folgende Haupt-Attribute für ein `MailMessage`-Objekt auf:

*   `uid`: Eindeutige ID der Nachricht (wird bereits genutzt).
*   `subject`: Betreff (wird bereits genutzt).
*   `from_`: Absenderadresse als String.
*   `to`: Empfängeradressen (To) als Tupel von Strings.
*   `cc`: Empfängeradressen (Cc) als Tupel von Strings.
*   `bcc`: Empfängeradressen (Bcc) als Tupel von Strings.
*   `reply_to`: Antwortadressen als Tupel von Strings.
*   `date`: Datum und Zeit als `datetime.datetime`-Objekt (wird bereits genutzt).
*   `date_str`: Originaler Datumsstring aus dem Header (wird bereits genutzt).
*   `text`: Nur-Text-Body der E-Mail.
*   `html`: HTML-Body der E-Mail.
*   `flags`: Flags der Nachricht als Tupel von Strings (z.B. `\\Seen`, `\\Flagged`) (wird bereits genutzt).
*   `headers`: Alle Header als Dictionary (wird bereits genutzt).
*   `size_rfc822`: Größe der Nachricht laut Server (wird bereits genutzt).
*   `size`: Tatsächliche Größe der heruntergeladenen Nachricht (relevant, wenn Body/Anhänge geholt werden).
*   `attachments`: Liste von `MailAttachment`-Objekten (relevant, wenn Anhänge geholt werden).
*   `from_values`: Absenderadresse als `EmailAddress`-Objekt (enthält Name und E-Mail).
*   `to_values`: Empfänger (To) als Tupel von `EmailAddress`-Objekten.
*   `cc_values`: Empfänger (Cc) als Tupel von `EmailAddress`-Objekten.
*   `bcc_values`: Empfänger (Bcc) als Tupel von `EmailAddress`-Objekten.
*   `reply_to_values`: Antwortadressen als Tupel von `EmailAddress`-Objekten.
*   `obj`: Das ursprüngliche `email.message.Message`-Objekt.

Zusätzlich zu dem, was wir bereits speichern (UID, Subject, Date, Flags, Headers, Size, From, Conversation ID), könnten wir also noch hinzufügen:

*   **To-Adressen** (`to`, `to_values`)
*   **Cc-Adressen** (`cc`, `cc_values`)
*   **Bcc-Adressen** (`bcc`, `bcc_values`) - *Hinweis: Bcc ist oft nicht im Header enthalten, wenn man nicht selbst der Absender ist.*
*   **Reply-To-Adressen** (`reply_to`, `reply_to_values`)

Sollen diese Adressfelder (To, Cc, Bcc, Reply-To) ebenfalls in der Datenbank gespeichert werden? Das würde es ermöglichen, später nach E-Mails zu suchen, die an bestimmte Adressen gesendet wurden.
