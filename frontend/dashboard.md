# Dashboard & AI Suggestions - Kernfunktionen

Dieses Dokument beschreibt die Hauptfunktionen der `Dashboard.tsx` und `AISuggestions.tsx` Komponenten, um bei zukünftigen Änderungen Regressionen zu vermeiden.

## `Dashboard.tsx`

- **E-Mail-Liste:**
    - Lädt E-Mails paginiert (`EMAILS_PAGE_SIZE`).
    - Speichert und lädt die zuletzt ausgewählte E-Mail-ID im `localStorage`.
    - Scrollt automatisch zur gespeicherten E-Mail bzw. lädt weitere Seiten nach, bis sie gefunden wird.
    - Wählt automatisch die erste E-Mail aus, wenn keine ID gespeichert ist.
    - Ermöglicht manuelles Nachladen via Scrollen.
    - Zeigt Lade- und Fehlerzustände an.
- **E-Mail-Detailansicht:**
    - Zeigt den Inhalt der ausgewählten E-Mail (`EmailDetail`).
- **AI Vorschläge (Verwaltung):**
    - Holt initiale Vorschläge für die ausgewählte E-Mail via API (`getAiSuggestionsForEmail`).
    - Verwaltet den Lade-/Fehlerzustand für Vorschläge (`loadingSuggestions`, `errorSuggestions`).
    - Stellt die Callback-Funktion `handleRefreshSuggestions` bereit:
        - Löscht alte Vorschläge im State.
        - Setzt den Ladezustand.
        - Ruft die Backend-API zum *asynchronen* Neu-Generieren der Vorschläge auf (`regenerateSuggestions`).
    - Stellt die Callback-Funktion `handleArchive` bereit.
- **WebSocket-Verbindung:**
    - Baut eine WebSocket-Verbindung zu `/ws/suggestions/` auf, wenn die Komponente mountet.
    - Sendet den Auth-Token aus `localStorage` als Query-Parameter mit.
    - Empfängt `suggestions.updated`-Nachrichten.
    - Aktualisiert den `currentSuggestions`-State und beendet den Ladezustand (`loadingSuggestions`), wenn eine Nachricht für die *aktuell ausgewählte* E-Mail ankommt.
- **Layout:**
    - Drei Spalten: Liste, Detail, Vorschläge.
    - Die Breite der linken und rechten Spalte passt sich an, wenn der Vorschlagsbereich (über `AISuggestions` gesteuert) aus-/eingeklappt wird.

## `AISuggestions.tsx`

- **Props:** Erhält `selectedEmailId`, `suggestions`, `loading`, `error` und Callbacks vom `Dashboard`.
- **Ansichten:**
    - **Übersicht (Standard):** Zeigt alle erhaltenen Vorschläge untereinander an. Jeder Vorschlag nimmt die gleiche Höhe ein. Der Titel (`title` oder `type`) wird angezeigt. Der Inhalt (`content`) wird gekürzt, Leerzeilen werden entfernt (`truncateAndClean`). Ein Klick auf einen Vorschlag wechselt zur Detailansicht.
    - **Detailansicht (Ein Vorschlag ausgewählt):**
        - Zeigt oben die Titel der *anderen* Vorschläge als klickbare `Chip`-Elemente an.
        - Zeigt in einem größeren Bereich (ca. 3/4 der Höhe) den Betreff (`suggested_subject`) und den *vollen* Inhalt (`content`) des ausgewählten Vorschlags. Dieser Bereich ist bei Bedarf scrollbar.
        - Zeigt darunter (ca. 1/4 der Höhe) ein `TextField` für benutzerdefinierte Prompts an.
- **Bearbeitungsmodus (Detailansicht):**
    - Startet, wenn der Benutzer in den Inhaltsbereich (`Typography`) des ausgewählten Vorschlags klickt.
    - Ersetzt die Textanzeige durch ein `TextField`.
    - Speichert den bearbeiteten Text im `editingSuggestion`-State.
    - Endet, wenn das `TextField` den Fokus verliert (`onBlur`). (Speichern der Änderung muss ggf. noch implementiert werden).
- **Interaktionen:**
    - Ruft `onRefreshSuggestions` auf, wenn der Refresh-Button geklickt wird.
    - Ruft `onArchive` auf, wenn der Spam-Button geklickt wird.
    - Speichert den Inhalt des Prompt-Felds im `localStorage` pro E-Mail-ID.
- **Layout:**
    - Die gesamte Komponente ist **nicht** scrollbar.
    - Die interne Aufteilung (Übersicht oder Detail) nutzt Flexbox, um den verfügbaren Platz (ohne die Button-Leiste) zu füllen.
    - Die Button-Leiste (Send, Spam, Correct, Refine, Refresh) ist immer am unteren Rand fixiert.

*Zuletzt aktualisiert: [Datum - bitte manuell pflegen]* 