# AI Suggestions Dokumentation

Dieses Verzeichnis enthält Komponenten, die für die Generierung und Anzeige von KI-gestützten E-Mail-Antwortvorschlägen zuständig sind.

## Komponenten

- **`AISuggestions.tsx`**: Die Hauptkomponente, die den Zustand verwaltet und die verschiedenen Ansichten (Aktionsbuttons, Antwortansicht) rendert.
- **`ReplyView.tsx`**: Zeigt die Detailansicht für die Bearbeitung und Verfeinerung eines KI-Vorschlags an. Enthält:
    - Empfängeranzeige: Zeigt den ursprünglichen Empfänger (falls vorhanden) und hinzugefügte Dummy-Empfänger als löschbare Chips (To, Cc, Bcc) an.
    - Buttons zum Hinzufügen weiterer To-, Cc-, Bcc-Empfänger (+ Icon und Text). Bei Klick wird eine Dummy-E-Mail hinzugefügt.
    - Betreff- und Nachrichten-Eingabefelder.
    - Buttons/Chips zur Auswahl, Korrektur und Verfeinerung von KI-Vorschlägen.
- **`ActionButtonsView.tsx`**: Zeigt die anfänglichen Aktionsbuttons (z.B. "Generate Reply") an, bevor ein Vorschlag generiert wird.
- **`DummyActionInput.tsx`**: Ein Platzhalter oder Eingabefeld, das im Zusammenhang mit den Aktionen stehen könnte (genauer Zweck TBD).
- **`useAISuggestionHandlers.ts`**: Ein Hook, der die Logik für die Interaktion mit dem Backend (API-Aufrufe zum Generieren/Verfeinern von Vorschlägen) und die Zustandsverwaltung kapselt.
- **`types.ts`**: Definiert TypeScript-Typen, die in den AISuggestions-Komponenten verwendet werden.
- **`utils.ts`**: Hilfsfunktionen für die AISuggestions-Komponenten.

## Funktionsweise

1.  Der Benutzer wählt eine E-Mail aus.
2.  Die `AISuggestions`-Komponente (oder `ActionButtonsView`) zeigt Optionen an, um eine KI-Antwort zu generieren.
3.  Bei Klick wird über `useAISuggestionHandlers` ein API-Aufruf gestartet.
4.  Nach Erhalt der Antwort wird die `ReplyView`-Komponente angezeigt.
5.  `ReplyView` zeigt den vorgeschlagenen Text, Empfänger (ursprünglich und hinzugefügt, alle löschbar) usw. an.
6.  Der Benutzer kann den Vorschlag bearbeiten, Empfänger hinzufügen/löschen (To, Cc, Bcc über Buttons und löschbare Chips), den Vorschlag mit eigenen Anweisungen verfeinern oder einen neuen Vorschlag anfordern.
7.  Änderungen und Aktionen werden über `useAISuggestionHandlers` verarbeitet. 