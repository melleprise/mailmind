# Refine Suggestion Feature Dokumentation

## 1. Übersicht

Das "Refine Suggestion"-Feature ermöglicht es Benutzern, eine existierende KI-generierte E-Mail-Suggestion (Betreff und Inhalt) mithilfe von benutzerdefinierten Anweisungen weiter zu verfeinern. Der Benutzer gibt spezifische Instruktionen in ein Textfeld ein, und das System generiert eine aktualisierte Version der Suggestion basierend auf diesen Anweisungen und dem aktuellen Entwurf.

## 2. Frontend

Die Frontend-Logik ist hauptsächlich in `ReplyView.tsx` für die Darstellung und `useAISuggestionHandlers.ts` für die Geschäftslogik und API-Interaktion implementiert.

### 2.1. Komponenten und State

**`frontend/src/components/AISuggestions/ReplyView.tsx`**

*   **Refine Input Area (`Box`):**
    *   Container für das Textfeld und den Button.
    *   Code-Block (ca. Zeile 469-535):
      ```tsx
      <Box sx={{ display: 'flex', border: 1, borderColor: 'divider', borderRadius: 1, position: 'relative' }}>
        <TextField
          fullWidth
          multiline
          minRows={3}
          maxRows={8}
          placeholder="Enter custom instructions to refine..."
          variant="outlined"
          value={customPrompt} // from useAISuggestionHandlers
          onChange={(e) => setCustomPrompt(e.target.value)} // from useAISuggestionHandlers
          onKeyDown={...} // Handler für Cmd/Ctrl+Enter
          disabled={!selectedEmailId || loading || isRefining}
          sx={{...}}
        />
        <Button
          size="small"
          variant="outlined"
          onClick={handleRefineClick} // from useAISuggestionHandlers
          disabled={isButtonDisabled} // Berechnet in ReplyView basierend auf States vom Hook
          sx={{...}}
        >
          {isRefining ? <CircularProgress size={14} sx={{ mr: 0.5 }} /> : null}
          Refine
        </Button>
      </Box>
      ```

*   **Zustände und Handler aus `useAISuggestionHandlers`:**
    *   `customPrompt: string`: Der Inhalt des Refine-Textfeldes.
    *   `setCustomPrompt: (value: string) => void`: Funktion zum Aktualisieren von `customPrompt`.
    *   `handleRefineClick: () => Promise<void>`: Funktion, die bei Klick auf "Refine" oder per Shortcut ausgelöst wird.
    *   `isRefining: boolean`: Zeigt an, ob gerade ein Refine-Vorgang läuft (für Ladeindikatoren und Deaktivierung von UI-Elementen).
    *   `isButtonDisabled: boolean`: Kombinierter Zustand, der den Refine-Button deaktiviert, wenn keine E-Mail/Suggestion ausgewählt ist, ein Ladevorgang aktiv ist, der Prompt leer ist etc.

**`frontend/src/components/AISuggestions/useAISuggestionHandlers.ts`**

*   **`internalCustomPrompt: string`**:
    *   Lokaler State im Hook, der den Text für die Verfeinerungsanweisungen speichert.
    *   Wird beim Initialisieren und bei Änderung der `selectedEmailId` aus dem `localStorage` geladen (`mailmind_customPrompt_{selectedEmailId}`).
    *   Änderungen werden im `localStorage` persistiert.
*   **`setCustomPromptWrapper` (exportiert als `setCustomPrompt`):**
    *   Aktualisiert `internalCustomPrompt` und damit auch den `localStorage`.
*   **`isRefining: boolean`**:
    *   State, der anzeigt, ob ein API-Call für das Refinement gerade aktiv ist.
*   **`handleRefineClick` Funktion**:
    *   Setzt `isRefining` auf `true`.
    *   Ruft `refineAiSuggestion` aus dem API-Service auf.
    *   Parameter für `refineAiSuggestion`:
        *   ID der ausgewählten Suggestion (`suggestions[selectedSuggestionIndex].id`).
        *   `internalCustomPrompt`.
        *   Aktueller `draftSubject`.
        *   Aktueller `draftBody`.
    *   Nach erfolgreichem API-Call:
        *   Aktualisiert den `draftSubject` und `draftBody` mit den Werten aus der API-Antwort über `onDraftSubjectChange` und `onDraftBodyChange`.
        *   Die API (`refineAiSuggestion`) gibt das vollständig aktualisierte Suggestion-Objekt zurück. Das Backend aktualisiert die Suggestion direkt in der Datenbank.
        *   Der separate Aufruf von `onUpdateSuggestion` ist nicht mehr notwendig und wurde entfernt.
        *   Setzt `internalCustomPrompt` zurück.
    *   Bei einem Fehler während des `refineAiSuggestion`-Aufrufs wird ein `refineError`-State gesetzt.
    *   Setzt `isRefining` im `finally`-Block auf `false`.

### 2.2. Workflow

1.  Benutzer wählt eine E-Mail und eine KI-Suggestion aus.
2.  Der aktuelle Betreff und Inhalt der Suggestion werden in die Editorfelder (`draftSubject`, `draftBody`) geladen.
3.  Benutzer tippt Verfeinerungsanweisungen in das "Enter custom instructions to refine..."-Textfeld (`customPrompt`).
4.  Der eingegebene Text wird im `localStorage` gespeichert, gekoppelt an die `selectedEmailId`.
5.  Benutzer klickt auf "Refine" oder drückt Cmd/Ctrl+Enter.
6.  `handleRefineClick` in `useAISuggestionHandlers.ts` wird aufgerufen.
7.  Der Ladezustand `isRefining` wird aktiviert. UI-Elemente werden entsprechend (de-)aktiviert.
8.  Ein API-Aufruf an den Backend-Endpunkt (siehe Abschnitt 3) wird mit der Suggestion-ID, dem `customPrompt` und dem aktuellen `draftSubject` und `draftBody` gesendet.
9.  Das Backend verarbeitet die Anfrage, verfeinert die Suggestion und **aktualisiert sie direkt in der Datenbank** (siehe Abschnitt 3).
10. Bei Erfolg gibt das Backend die **vollständig aktualisierte, verfeinerte Suggestion** (neuer Titel, neuer Inhalt) zurück.
11. Im Frontend:
    *   `draftSubject` und `draftBody` werden mit den neuen Werten aus der API-Antwort aktualisiert, was die Textfelder in `ReplyView.tsx` aktualisiert.
    *   Das `customPrompt`-Feld wird geleert.
12. Der Ladezustand `isRefining` wird deaktiviert.
13. Bei einem Fehler während des Refine-Vorgangs:
    *   Wird ein `refineError` im `useAISuggestionHandlers`-Hook gesetzt.
    *   Dieser Fehler wird dem Benutzer über eine `<Alert>`-Komponente in `ReplyView.tsx` angezeigt.
    *   Der Ladezustand `isRefining` wird ebenfalls deaktiviert.

## 3. Backend

Der Backend-Teil wird durch die Funktion `refineAiSuggestion` im Frontend (aus `frontend/src/services/api.ts`) angesprochen.

### 3.1. API Endpunkt (Annahme)

*   **URL:** `/api/ai-suggestions/{suggestion_id}/refine` (oder eine ähnliche Route)
*   **Methode:** `POST`
*   **Authentifizierung:** Erforderlich (Standard-Authentifizierungsmechanismus der Anwendung)

### 3.2. Request Payload

```json
{
  "custom_prompt": "string",        // Die Verfeinerungsanweisung vom Benutzer
  "current_subject": "string",      // Der aktuelle Betreff des Entwurfs
  "current_body": "string"          // Der aktuelle Inhalt des Entwurfs
}
```

### 3.3. Response Payload (Erfolg)

```json
// Erwartet wird ein Objekt, das der AISuggestion-Struktur entspricht
{
  "id": "string",                   // ID der ursprünglichen Suggestion
  "title": "string",                // Der neu generierte, verfeinerte Betreff
  "content": "string",              // Der neu generierte, verfeinerte Inhalt
  "type": "string",                 // Typ der Suggestion (z.B. "positive_reply")
  // ... weitere mögliche Felder einer AISuggestion
}
```

### 3.4. Backend Logik (Konzept)

1.  Der Endpunkt empfängt die POST-Anfrage mit der `suggestion_id` im Pfad und dem Payload im Body.
2.  Validierung der Eingabedaten (z.B. ist `custom_prompt` vorhanden?).
3.  Abrufen der existierenden Suggestion (optional, falls Kontext benötigt wird, der nicht im `current_subject`/`current_body` ist).
4.  Konstruktion eines Prompts für ein Large Language Model (LLM), der Folgendes enthält:
    *   Den `current_subject`.
    *   Den `current_body`.
    *   Den `custom_prompt` (die Verfeinerungsanweisung).
    *   Ggf. weitere Kontextinformationen oder systemseitige Anweisungen für das LLM, um die Qualität der Verfeinerung zu steuern.
5.  Senden des konstruierten Prompts an das LLM.
6.  Empfangen der Antwort vom LLM (verfeinerter Betreff und Inhalt).
7.  Formatierung der LLM-Antwort in das erwartete Response-Payload-Format.
8.  **Aktualisierung der Suggestion-Entität in der Datenbank mit dem neuen Titel und Inhalt.**
9.  Senden der **vollständig aktualisierten Suggestion** an das Frontend.

    *Wichtiger Hinweis:* Die Frontend-Logik verlässt sich nun darauf, dass der `/refine` Endpunkt die Suggestion direkt in der Datenbank persistiert und das aktualisierte Objekt zurückgibt. Der separate `onUpdateSuggestion`-Aufruf aus dem Frontend nach dem Refine-Vorgang wurde entfernt.

## 4. Hinweise und Potenziale

*   **Fehlerbehandlung:** Die Fehlerbehandlung für den Refine-Vorgang wurde im Frontend implementiert (Anzeige einer `Alert`-Nachricht).
*   **Ladezustand:** Der `isRefining`-Zustand wird korrekt verwendet, um UI-Interaktionen während des API-Aufrufs zu steuern.
*   **localStorage:** Die Nutzung von `localStorage` für den `customPrompt` ermöglicht Persistenz über Sitzungen hinweg pro E-Mail, was benutzerfreundlich ist.
*   **Debouncing/Throttling:** Für den `customPrompt` selbst gibt es kein Debouncing beim Tippen für eine Backend-Aktion, was hier auch nicht nötig ist, da die Aktion explizit durch Button-Klick/Shortcut ausgelöst wird.
*   **Backend-Update-Strategie:** Die Strategie wurde dahingehend geändert, dass der `refine`-Endpunkt die Suggestion direkt im Backend aktualisiert und die vollständige, aktualisierte Suggestion zurückgibt. Dies reduziert die Anzahl der API-Aufrufe vom Frontend. 