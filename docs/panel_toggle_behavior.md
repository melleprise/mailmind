# Panel-Toggle-Verhalten (AISuggestions & Dashboard)

## Übersicht
- Das Panel-Toggle (Erweitern/Reduzieren des Suggestion-Panels) wird zentral über `suggestionPanelExpanded` (Dashboard) gesteuert.
- Die Steuerung erfolgt über Props `isExpanded` und `onExpandRequest`, die von Dashboard an AISuggestions, ActionButtonsView und AIAgentInput durchgereicht werden.
- Das Panel wird erweitert, wenn:
  - `handleClickContainer` in AISuggestions aufgerufen wird und `isExpanded` false ist → ruft `onExpandRequest` (→ Dashboard: `setSuggestionPanelExpanded(true)`)
  - In AIAgentInput bei bestimmten Aktionen, wenn `isExpanded` false ist → ruft `onExpandRequest`
- Das Panel wird reduziert, wenn:
  - Ein Klick außerhalb des Panels erkannt wird (Dashboard: `setSuggestionPanelExpanded(false)`)
  - Escape-Taste gedrückt wird

## Relevante Stellen
- **Dashboard.tsx**: State `suggestionPanelExpanded`, Handler `handleExpandPanelRequest`, Panel-Layout.
- **AISuggestions.tsx**: `handleClickContainer`, Props `isExpanded`, `onExpandRequest`.
- **ActionButtonsView.tsx**: Reicht Props weiter.
- **AIAgentInput.tsx**: Ruft ggf. `onExpandRequest`.

## Ausnahme: Delete-Dialog
- **Soll:** Wenn der Delete-Dialog offen ist, darf **kein** Panel-Toggle (Expand/Collapse) ausgelöst werden – weder durch Klicks noch durch andere Aktionen.
- **Restliches Verhalten:** Alle anderen Panel-Toggle-Mechanismen bleiben unverändert.

## ToDo
- In allen relevanten Click-Handlern und onExpandRequest-Aufrufen prüfen: Wenn Delete-Dialog offen, keine Panel-Änderung durchführen. 