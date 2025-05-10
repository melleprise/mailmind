# AI Suggestions Component (`AISuggestions.tsx`)

This component is responsible for displaying AI-generated suggestions for a selected email and allowing user interaction.

## Features

- **Display Modes:**
    - **Overview (Default):** Shows a list of all available suggestions, each with a title/type and a truncated preview of the content. Clicking a suggestion switches to Detail Mode.
    - **Detail Mode:** Shows the full content of a selected suggestion, along with chips for all other suggestion titles for easy switching. Allows editing the suggestion content and entering a custom prompt.
- **Loading State:** Displays a loading spinner while suggestions are being fetched or regenerated.
- **Error State:** Shows an error message if fetching/regeneration fails.
- **No Suggestions/No Email:** Displays informative messages if no email is selected or if no suggestions are available for the selected email.
- **Suggestion Selection:**
    - Clicking a suggestion in Overview Mode selects it and enters Detail Mode.
    - In Detail Mode, clicking a title chip selects that suggestion.
    - Clicking the currently selected title chip deselects it and returns to Overview Mode.
    - Clicking the background area *around* the detail components (chips, content, prompt) also returns to Overview Mode.
- **Content Editing:** In Detail Mode, clicking the suggestion content makes it editable within a TextField. Changes are currently logged on blur but not persisted to the backend.
- **Custom Prompt:** A text field allows users to enter custom instructions (prompt) to refine suggestions. The prompt is saved per email in `localStorage`.
- **Actions:**
    - **Refresh:** Triggers regeneration of suggestions for the current email (`onRefreshSuggestions` prop).
    - **Archive/Spam:** Triggers archiving of the current email (`onArchive` prop).
    - **Send (Dummy):** A button, currently not functional.
    - **Correct (Dummy):** A button, currently logs to console.
    - **Refine (Dummy):** A button, currently logs the custom prompt to console, enabled only if a prompt is entered.
    - **Cmd/Ctrl + Enter Shortcut:** Pressing `Cmd+Enter` or `Ctrl+Enter` within the custom prompt text field will trigger the "Refine" action, if the button is enabled.
- **Panel Expansion:** Notifies the parent component (`Dashboard`) whether the detail panel is expanded (`onPanelExpansionChange` prop) based on whether a suggestion is selected.
- **Content Truncation:** Suggestion previews in the Overview Mode are truncated and cleaned for display.

## Props

- `selectedEmailId: number | null`: The ID of the currently selected email.
- `suggestions: AISuggestion[]`: An array of suggestion objects.
- `loading: boolean`: Indicates if suggestions are being loaded/generated.
- `error: string | null`: An error message, if any.
- `onArchive: (emailId: number) => void`: Callback function triggered when the archive/spam button is clicked.
- `onRefreshSuggestions: (emailId: number) => void`: Callback function triggered when the refresh button is clicked.
- `onPanelExpansionChange: (isExpanded: boolean) => void`: Callback function triggered when the selection state changes (entering/leaving Detail Mode).

## State Management

- Manages the index of the selected suggestion (`selectedSuggestionIndex`).
- Manages the content of the custom prompt (`customPrompt`), persisting it to `localStorage`.
- Manages the editing state of a suggestion (`editingSuggestion`).

## Interactions

- Uses `localStorage` to remember the custom prompt for each email.
- Uses `stopPropagation` extensively to control click behavior and differentiate between clicks on interactive elements and the background.
- The custom prompt field is cleared automatically when the "Refine" action is triggered. 