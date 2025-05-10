# Aktuelle Funktionsweise der AI-Vorschlagsgenerierung (Stand: 2024-07-29)

Die Logik für AI-Vorschläge befindet sich in der Funktion `generate_ai_suggestion` in `backend/mailmind/ai/tasks.py`. Diese Funktion wird als Hintergrundaufgabe (via Django-Q) ausgeführt, typischerweise nach dem Empfang einer neuen E-Mail oder manuell getriggert.

**Wichtige Punkte:**
- Die Funktion ist **aktiv** und wird verwendet.
- Sie interagiert mit der Gemini API, der Datenbank und dem WebSocket-System (Channels).
- Sie generiert nicht nur Antwortvorschläge, sondern auch kurze und mittellange Zusammenfassungen der E-Mail.

**Ablauf der Funktion:**

1.  **E-Mail laden:**
    - Nimmt eine `email_id` und optional eine `triggering_user_id` (für WebSocket) entgegen.
    - Lädt das zugehörige `Email`-Objekt aus der Datenbank, inklusive Account, Benutzer, Empfänger (To, Cc).

2.  **RAG Kontext (Platzhalter):**
    - Versucht, zusätzlichen Kontext mittels RAG zu finden. Dieser Teil ist aktuell als **TODO** markiert und holt noch keinen echten Kontext.

3.  **Prompt erstellen:**
    - Baut einen detaillierten Text-Prompt für die Gemini API.
    - Der Prompt enthält Anweisungen zur Generierung einer `short_summary` (1-5 Wörter), einer `medium_summary` (6-12 Wörter) und genau 3 `suggestions` (Antwortvorschläge).
    - Jeder Vorschlag soll die Felder `intent_summary`, `subject` und `reply_text` enthalten.
    - Der Prompt übergibt die relevanten E-Mail-Daten (Absender, Empfänger, Betreff, Text, Datum) und den (aktuell leeren) RAG-Kontext.
    - Er fordert explizit eine **JSON-Antwort** im definierten Format.

4.  **API-Aufruf:**
    - Ruft die Hilfsfunktion `call_gemini_api` auf, welche:
        - Das konfigurierte Gemini-Modell holt (`get_gemini_model`).
        - Den Prompt an die Gemini API sendet.
        - Die Antwort als Text-String zurückgibt (oder ein Fehler-JSON).

5.  **Antwort verarbeiten & speichern:**
    - Der zurückgegebene Text-String wird bereinigt (z.B. Markdown ` ```json ` entfernt).
    - Der String wird als JSON geparst.
    - Fehlerbehandlung für API-Fehler (z.B. geblockte Prompts) und JSON-Parse-Fehler.
    - **Zusammenfassungen:** Extrahiert `short_summary` und `medium_summary` aus dem JSON und speichert sie direkt im `Email`-Objekt.
    - **Vorschläge:**
        - Extrahiert die Liste `suggestions` aus dem JSON (max. 3).
        - Iteriert über die Vorschlags-Objekte in der Liste.
        - Validiert jedes Objekt (prüft auf `intent_summary`, `subject`, `reply_text`).
        - Für jeden gültigen Vorschlag wird ein neues `AISuggestion`-Objekt in der Datenbank erstellt und mit der `Email` verknüpft. Die Felder `title`, `content`, `intent_summary`, `suggested_subject` werden befüllt.
        - Zählt die erfolgreich gespeicherten Vorschläge.

6.  **Status aktualisieren:**
    - Die ursprüngliche E-Mail wird in der Datenbank als `ai_processed = True` markiert und bekommt einen Zeitstempel (`ai_processed_at`), **aber nur, wenn mindestens ein Vorschlag erfolgreich gespeichert wurde**.
    - Das `Email`-Objekt wird mit den Updates (Zusammenfassungen, AI-Status) gespeichert.

7.  **WebSocket Benachrichtigung:**
    - **Nach** Abschluss der Verarbeitung (im `finally`-Block) wird eine Nachricht über Django Channels gesendet.
    - Die Nachricht wird an eine benutzerspezifische Gruppe gesendet (`user_{user_id}_events`), basierend auf der `triggering_user_id`.
    - Die Nachricht hat den Typ `suggestion_generation_complete`.
    - Die Nutzlast (`data`) enthält die `email_id`, die neu erstellten und serialisierten `AISuggestion`-Objekte, die gespeicherten Zusammenfassungen und den AI-Verarbeitungsstatus der E-Mail.
    - Dies ermöglicht es dem Frontend, die UI für die betreffende E-Mail sofort zu aktualisieren, ohne dass ein Neuladen der Seite erforderlich ist.

**Zusammenfassung des Workflows:**
E-Mail holen -> Prompt bauen -> An Gemini senden -> JSON-Antwort parsen -> Zusammenfassungen & Vorschläge als Objekte speichern -> E-Mail-Status updaten -> WebSocket-Nachricht an Frontend senden.
