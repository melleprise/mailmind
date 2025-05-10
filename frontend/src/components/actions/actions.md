# AI Actions

## Übersicht
Dieses Modul ermöglicht die Verwaltung und Ausführung von AI Actions (AI Agenten), die per MCP ausgeführt werden und beliebige Prompts/Tasks abbilden können.

## Features
- Anzeige aller Actions im Settings-Menü
- Erstellen, Bearbeiten, Löschen von Actions
- Jede Action kann mehrere Prompts enthalten
- Ausführung per Button (MCP)
- Statusanzeige und Ergebnisrückgabe

## Komponenten
- **ActionList**: Listet alle Actions auf, bietet Ausführen-Button
- **ActionForm**: Formular zum Erstellen/Bearbeiten einer Action inkl. Prompts
- **ActionRunner**: Startet eine Action und zeigt Status/Ergebnis

## Hinweise
- Die Actions werden in der Datenbank gespeichert
- Prompts können frei definiert werden (z.B. "Hole alle Links", "Finde Unsubscribe-Link")
- Die Ausführung erfolgt asynchron über das Backend (MCP)
- Erweiterbar für beliebige AI Tasks

## ActionButton

Wiederverwendbare Komponente für Action-Buttons (Paper, Icon+Text, Styles wie Mail-Bereich).

**Props:**
- `icon: ReactNode` – Icon-Komponente (z.B. <ReplyIcon />)
- `label: string` – Text
- `onClick?: () => void` – Klick-Handler
- `sx?: object` – optionale Style-Erweiterung

**Design:**
- Paper, kein klassischer Button
- Icon + Text nebeneinander
- Primärfarbene Icons/Text (`primary.main`)
- Abgerundete Ecken (`borderRadius: 1`)
- Border (`1px solid`, `divider`)
- Hover: Border und Hintergrund (`borderColor: 'primary.main', bgcolor: 'action.hover'`)
- Padding: `p: 1.5`, `gap: 1`

**Verwendung:**
- Wird in Mail (ActionButtonsView) und Leads (LeadsPage) verwendet.
- Änderungen am Design wirken überall synchron.

---
Letzte Aktualisierung: $(date) 