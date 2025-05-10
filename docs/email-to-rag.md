# E-Mail-Verarbeitung für RAG (Retrieval-Augmented Generation) (Stand: 2024-07-29)

Dieser Prozess beschreibt, wie E-Mails und ihre Anhänge in durchsuchbare Vektor-Embeddings umgewandelt und in der Vektordatenbank Qdrant gespeichert werden. Dies ist die Grundlage, um später relevante Informationen (Kontext) für die Generierung von AI-Antworten oder Zusammenfassungen abrufen zu können (der "Retrieval"-Teil von RAG).

Die Kernlogik befindet sich in `backend/mailmind/ai/tasks.py` und wird als Hintergrundaufgaben (via Django-Q) ausgeführt.

**Hauptfunktionen für Embedding-Generierung:**

1.  **`generate_embeddings_for_email(email_id: int)`**:
    *   Dies ist die Haupt-Task-Funktion, die typischerweise nach dem Empfang einer neuen E-Mail oder manuell (z.B. durch einen Management-Befehl) für eine spezifische E-Mail ausgelöst wird.
    *   Lädt das `Email`-Objekt und die zugehörigen `Attachment`-Objekte aus der Datenbank.
    *   Ruft `generate_email_embedding(email)` auf, um das Embedding für den E-Mail-Text zu erstellen.
    *   Iteriert durch alle Anhänge der E-Mail und ruft für jeden `generate_attachment_embedding(attachment)` auf.
    *   **Wichtig:** Diese Funktion markiert die E-Mail **nicht** als `ai_processed`.

2.  **`generate_email_embedding(email: Email)`**:
    *   Ist verantwortlich für das Embedding des E-Mail-Hauptinhalts.
    *   Kombiniert `email.subject` und `email.body_text` zu einem einzelnen Textblock.
    *   Verwendet die Funktion `get_text_model()` (die aktuell `sentence-transformers/all-MiniLM-L6-v2` lädt), um einen Vektor-Embedding für diesen Text zu generieren.
    *   Verwendet `get_qdrant_client()`, um eine Verbindung zur Qdrant-Datenbank herzustellen.
    *   Speichert (Upsert) das generierte Vektor-Embedding in der Qdrant-Collection `email_embeddings`.
        *   Die ID des Punkts in Qdrant ist die `email.id`.
        *   Das Payload des Punkts enthält Metadaten wie `subject`, `from_address`, `received_at`, `account_id` und den ursprünglichen Text (`text`).

3.  **`generate_attachment_embedding(attachment: Attachment)`**:
    *   Ist verantwortlich für das Embedding von Anhängen.
    *   Prüft, ob für den Anhang bereits Text extrahiert wurde (Feld `attachment.extracted_text`). Dieser Text könnte z.B. bei der initialen E-Mail-Verarbeitung mittels OCR (für Bilder) oder anderer Extraktionstools (für PDFs etc.) erzeugt worden sein.
    *   **Wenn `extracted_text` vorhanden ist:**
        *   Verwendet `get_text_model()`, um ein Vektor-Embedding für diesen Text zu generieren.
        *   Speichert (Upsert) das Embedding in der Qdrant-Collection `attachment_embeddings`.
            *   Die ID des Punkts in Qdrant ist die `attachment.id`.
            *   Das Payload enthält Metadaten wie `filename`, `content_type`, `email_id`, `account_id` und den extrahierten Text (`text`).
    *   **Wenn kein `extracted_text` vorhanden ist (oder der Anhang kein unterstützter Typ ist):** Aktuell wird für diesen Anhang **kein** Embedding generiert und nichts in Qdrant gespeichert. Die frühere Logik für Bild-Embeddings (CLIP) und on-the-fly OCR in dieser Funktion ist derzeit deaktiviert/entfernt.

**Hilfsfunktionen:**

*   `get_text_model()`: Lädt das SentenceTransformer-Modell (aktuell `all-MiniLM-L6-v2`) und gibt es zurück.
*   `get_image_model()`: Platzhalter, lädt derzeit kein Bild-Modell.
*   `get_qdrant_client()`: Stellt die Verbindung zu Qdrant her und sorgt dafür, dass die Collections `email_embeddings` (Vektorgröße 384) und `attachment_embeddings` (Vektorgröße 384) existieren.

**RAG - Der "Retrieval"-Teil:**

Die oben beschriebenen Funktionen kümmern sich nur um die **Indexierung** der Daten in Qdrant. Der eigentliche Abruf (Retrieval) dieser Daten, um Kontext für LLM-Prompts zu erhalten, ist derzeit **noch nicht implementiert**. Dies wäre der nächste Schritt, um RAG zu vervollständigen.

*   In der Funktion `generate_ai_suggestion` gibt es einen Platzhalter (`rag_context = ""`). Hier müsste die Logik eingefügt werden, um:
    1.  Eine Suchanfrage an Qdrant zu senden (basierend auf dem Inhalt der aktuellen E-Mail).
    2.  Die relevantesten Ergebnisse (Textstücke aus E-Mails oder Anhängen) aus Qdrant abzurufen.
    3.  Diesen abgerufenen Kontext in den Prompt für die Gemini API einzufügen.
