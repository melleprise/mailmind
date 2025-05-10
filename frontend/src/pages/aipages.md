# AI Pages Documentation

This document describes the functionality of the AI-related pages in the application.

## AI Search Page (`AISearchPage.tsx`)

This page allows users to perform AI-powered searches within their email folders.

### Features

*   **Folder Selection:** Users can select a specific email account and folder, or view folders from "All Accounts".
    *   If a specific account is selected, its folder structure is displayed.
    *   If "All Accounts" is selected, folders from all configured accounts are fetched, deduplicated, and displayed as a flat list.
*   **Search Input:** (Placeholder) Input field for AI search queries.
*   **Search Results:** (Placeholder) Area to display search results.
*   **Email List:** Displays emails from the selected folder with pagination (infinite scroll).
*   **Email Detail:** Displays the content of a selected email, loaded via the `EmailDetail` component.

### Implementation Notes

*   Folder fetching logic resides within the `useEffect` hook, triggered by changes in the selected account.
*   Uses the `emailAccounts.list()` and `emailAccounts.getFolders()` API endpoints defined in `src/services/api.ts`.
*   Relies on an external state management solution (e.g., AccountContext, Zustand store) to provide the `selectedAccountId`. `null` for `selectedAccountId` indicates "All Accounts".
*   Loading and error states are handled during folder fetching.
*   Reuses the `EmailList` and `EmailDetail` components for displaying email data.
*   Email fetching logic (`api.getEmails`, `api.getEmailById`) is handled within the component. 

## Leads Page (`LeadsPage.tsx`)

Diese Seite zeigt eine Liste von Freelance-Projekten (Leads) und Details zum ausgewählten Lead.

### Features

*   **Action-Buttons:** Die Aktionen "Bewerben", "Ignorieren" und "Zum Original" werden exakt wie im Mail-Bereich gerendert:
    *   Paper-Komponente, kein klassischer Button
    *   Icon + Text nebeneinander
    *   Primärfarbene Icons/Text (`primary.main`)
    *   Abgerundete Ecken (`borderRadius: 1`)
    *   Border (`1px solid`, `divider`)
    *   Hover: Border und Hintergrund (`borderColor: 'primary.main', bgcolor: 'action.hover'`)
    *   Abstand und Layout identisch zu `ActionButtonsView.tsx`
*   **Lead-Details:** Zeigt Projektbeschreibung, Skills, Bewerbungsanzahl, Provider, Enddatum etc.
*   **Textfeld unten:** Für geplante Aktionen, aktuell als Platzhalter.

### Hinweise

*   Das Design der Action-Buttons ist 1:1 an die Mail-Action-Buttons angepasst. Änderungen am Design müssen synchron in beiden Bereichen erfolgen.
*   Die Implementierung der Action-Buttons befindet sich direkt in `LeadsPage.tsx`. 