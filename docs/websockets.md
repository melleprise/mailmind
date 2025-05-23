# WebSocket Implementation Standards\n\nThis document outlines the standard practices for implementing WebSocket functionality within the MailMind project.\n\n## 1. Overview\n\nWebSockets provide real-time, bidirectional communication between the frontend (React) and the backend (Django Channels). They are primarily used for:\n\n- Notifying the frontend of new or updated emails.\n- Pushing status updates for background tasks (e.g., IMAP sync).\n- Sending real-time updates like AI suggestions.\n\n## 2. Backend (Django Channels)\n\n### 2.1. Consumers\n\n- **Base Class:** Use `channels.generic.websocket.AsyncWebsocketConsumer` for asynchronous handling.\n- **Authentication:**\n    - Authentication is handled by Django Channels middleware (`AuthMiddlewareStack` or similar configured in `asgi.py`). This middleware populates `self.scope['user']` based on the user's session or token established via standard HTTP login.\n    - The `connect` method in the consumer **MUST** check `self.scope['user']` and `self.scope['user'].is_authenticated`.\n    - If the user is not found or not authenticated, the connection **MUST** be rejected using `await self.close()`.\n    - **DO NOT** attempt to handle token authentication directly within the consumer's `connect` method (e.g., by reading query parameters). Rely solely on the `scope` populated by the middleware.\n- **Grouping:**\n    - Use user-specific groups to target messages (e.g., `f'user_{self.user.id}_events'`).\n    - Add the channel to the group in `connect` (`await self.channel_layer.group_add(...)`).\n    - Remove the channel from the group in `disconnect` (`await self.channel_layer.group_discard(...)`).\n- **Message Handling:**\n    - Consumers primarily *receive* messages broadcasted to their group from elsewhere in the Django application (e.g., from signals or background tasks).\n    - Implement specific handler methods for different message types broadcasted to the group (e.g., `async def email_new(self, event):`). The method name corresponds to the `type` field in the message sent to the group.\n    - Use `await self.send(text_data=json.dumps({...}))` to send messages to the connected client.\n- **Logging:** Use standard Python logging (`logging.getLogger(__name__)`) for connection, disconnection, and important events.\n\n### 2.2. Routing\n\n- Define WebSocket URL patterns in `routing.py` files (e.g., `backend/mailmind/api/routing.py`).\n- Use `django.urls.re_path` to define routes.\n- Aggregate `websocket_urlpatterns` in the main `asgi.py` configuration (`AuthMiddlewareStack` should wrap the `URLRouter`).\n- Aim for fewer, more general consumers if possible. For instance, a single `EmailConsumer` handles `/ws/dashboard/` and potentially other user-specific events by differentiating messages via group broadcasts.\n\n### 2.3. Broadcasting Messages\n\n- To send a message to a user's WebSocket from anywhere in the backend (e.g., after an email is saved):\n  ```python\n  from channels.layers import get_channel_layer\n  import json\n\n  channel_layer = get_channel_layer()\n  user_id = ... # Get the target user's ID\n  group_name = f'user_{user_id}_events'\n  message = {\n      'type': 'email.new', # This calls the 'email_new' method on the consumer\n      'payload': { ... } # Your data payload\n  }\n  await channel_layer.group_send(group_name, message)\n  ```\n\n## 3. Frontend (React)\n\n### 3.1. Connection Management\n\n- **Trigger:** Use a `useEffect` hook in the relevant component (e.g., `Dashboard.tsx`).\n- **Authentication Context:**\n    - Import `useAuth` from `../contexts/AuthContext`.\n    - Get the `token` state: `const { token } = useAuth();`.\n    - The `useEffect` hook **MUST** have `token` in its dependency array: `useEffect(() => { ... }, [token]);`. This ensures the effect re-runs when the token becomes available after login, or becomes null after logout.\n    - **Crucially, this avoids race conditions where the effect might run before the token is set in localStorage or the context is updated after login.**\n- **Connection Logic:**\n    - Inside the `useEffect`, first check if `token` (from `useAuth`) exists. If not, ensure any existing connection/timers are cleaned up and `return`. This prevents connection attempts while logged out or before login completes.\n    - Define a `connect` function *inside* the `useEffect`.\n    - Inside `connect`, retrieve the token *again* to ensure the most current value is used (either from `token` context variable or fallback to `localStorage.getItem('authToken')`). Check this `currentToken` before proceeding.\n    - Use a `useRef` (e.g., `wsRef`) to hold the WebSocket instance (`wsRef.current`). Check `wsRef.current` and its `readyState` to prevent multiple connection attempts.\n    - Use another `useRef` (e.g., `retryTimeoutRef`) to manage reconnect timers.\n    - Instantiate the WebSocket: `wsRef.current = new WebSocket(WS_URL);`. The URL **MUST** include the authentication token as a query parameter (e.g., `ws://.../ws/general/?token=YOUR_TOKEN_HERE`).\n    - **Note:** The backend's `AuthMiddlewareStack` expects the token to be passed this way for initial authentication of the WebSocket connection.\n- **Event Handlers:**\n    - Assign `onopen`, `onmessage`, `onerror`, and `onclose` handlers to the WebSocket instance.\n    - `onopen`: Log success, clear reconnect timers.\n    - `onmessage`: Parse the JSON data (`event.data`). Use a `type` field in the data to determine how to handle the message (e.g., update state, refetch data). **Ensure state updates (like setting loading states to false) happen correctly based on received message types (e.g., `suggestion_generation_complete`).**\n    - `onerror`: Log errors, potentially update UI state (e.g., set loading to false, show error message).\n    - `onclose`: Log closure details. Implement reconnection logic here:\n        - Clear the `wsRef.current`.\n        - Check if reconnection is appropriate (e.g., token still exists via `useAuth`, closure was not clean/intentional like code 1000, component is still active).\n        - Use `setTimeout` to call the `connect` function again after a delay, storing the timer ID in `reconnectTimeoutRef` (clear any previous timer first).\n- **Cleanup:**\n    - The `useEffect`'s return function **MUST** handle cleanup.\n    - Set an `isActive` flag to false.\n    - Clear any active reconnect timer (`clearTimeout(retryTimeoutRef.current)`).\n    - Close the WebSocket connection if it exists and is open (`wsRef.current?.close(1000, 'Cleanup reason');`). Check the `isActive` flag within handlers before updating state to prevent updates on unmounted components.\n    - Set `wsRef.current = null;`.
\n\n### 3.2. State Updates\n\n- Based on messages received in `onmessage`, update component state appropriately (e.g., `setAiSuggestions(...)`, trigger data refetches using React Query's `queryClient.invalidateQueries(...)`).\n\n## 4. Message Format\n\n- All messages between backend and frontend should be JSON strings.\n- Messages sent *from* the backend *to* the frontend via group broadcasts should follow this structure:\n  ```json\n  {\n    \"type\": \"event.type.name\", \/\/ e.g., \"email.new\", \"sync.status\"\n    \"payload\": { ... }        \/\/ Data specific to the event\n  }\n  ```\n- The `type` corresponds to the consumer handler method (e.g., `email_new`).\n\n## 5. Environment Variables

- **Frontend (`VITE_WS_BASE_URL`):**
    - **Purpose:** Specifies the base hostname and port the frontend React application should use to establish the WebSocket connection. This variable is read via `import.meta.env.VITE_WS_BASE_URL`.
    - **Example:** `ws://localhost:8000` (for local development without TLS) or `wss://yourdomain.com` (for production with TLS).
    - **Configuration:** Set in the frontend's environment (e.g., `.env` file or Docker environment variables).
    - **Note:** If not set, the frontend might default to a fallback like `${window.location.hostname}:8000`.

- **Backend:**
    - The backend WebSocket server (Daphne/Uvicorn) host and port are typically configured directly in the server startup command (e.g., `-b 0.0.0.0 -p 8000` in `docker/backend/docker-entrypoint.sh`).
    - There isn't a standard environment variable like `WS_BASE_URL` consumed by the backend *server* itself in this project to define where it listens.
    - The scheme (`ws://` vs `wss://`) for external connections is usually determined by the reverse proxy (e.g., Caddy, Nginx) configuration based on TLS settings, or constructed by the frontend based on `window.location.protocol`.

## 1. URL-Konventionen

- **Lokale Entwicklung (Browser):**
  - WebSocket-URL: `ws://localhost:8000/ws/leads/`
  - Beispiel für das Frontend:
    ```js
    const WS_BASE = import.meta.env.VITE_WS_BASE_URL || (window.location.hostname === 'localhost' ? 'ws://localhost:8000' : 'ws://backend:8000');
    const WS_URL = WS_BASE + '/ws/leads/';
    ```
- **Docker-Container (im Compose-Netzwerk):**
  - WebSocket-URL: `ws://backend:8000/ws/leads/`
  - Vorteil: Funktioniert containerübergreifend ohne Port-Mapping.
- **Flexible Umgebungen:**
  - Setze die Umgebungsvariable `VITE_WS_BASE_URL` im Frontend, um die URL zu überschreiben (z.B. für Reverse-Proxy oder Produktion).

## 2. Authentifizierung

- Das Auth-Token wird als Query-Parameter übergeben: `?token=...`
- Das Backend (Django Channels) erwartet das Token im Query-String und authentifiziert über die Middleware.

## 3. Fehlerbehandlung

- Stelle sicher, dass das Token vorhanden ist, bevor du die Verbindung aufbaust.
- Bei fehlendem Token keine Verbindung versuchen (siehe Beispiel oben).

## 4. Hinweise

- Für lokale Entwicklung immer `localhost` im Browser verwenden, nicht den Docker-Service-Namen.
- Für Container-zu-Container-Kommunikation im Compose-Netzwerk immer den Service-Namen (z.B. `backend`) verwenden.
- Die Umgebungsvariable `VITE_WS_BASE_URL` ist der empfohlene Weg für flexible Deployments.

## 6. E-Mail-Benachrichtigung nach Import (Initial & IDLE)

- Nach jedem erfolgreichen Speichern einer neuen E-Mail (egal ob durch initialen Import, IDLE oder Einzelabruf) sendet das Backend automatisch ein WebSocket-Event an die Gruppe `user_{user_id}_events`.
- Das Event hat den Typ `email.new` und enthält als Payload die vollständigen E-Mail-Daten (wie in der API, serialisiert mit `EmailDetailSerializer`).
- Das Frontend kann so in Echtzeit neue E-Mails anzeigen, ohne Polling.
- Fehler beim Senden des Events werden geloggt, blockieren aber nicht den Import.
- Beispiel-Payload:
  ```json
  {
    "type": "email.new",
    "payload": {
      "id": 123,
      "subject": "...",
      "body_html": "...",
      "markdown_body": "...",
      ...
    }
  }
  ```

## 7. Soft-Delete von E-Mails (IMAP Sync)

- Wenn beim IMAP-Sync (z.B. nach IDLE) eine UID nicht mehr im Server-Listing eines Folders ist, wird die entsprechende E-Mail in der lokalen DB mit `is_deleted_on_server=True` markiert (Soft-Delete).
- Das Frontend filtert E-Mails mit `is_deleted_on_server=true` automatisch aus der Inbox-Ansicht heraus.
- Die E-Mail bleibt in der Datenbank (z.B. für Undo, Logs, spätere echte Löschung).
- Erst bei explizitem User-Wunsch oder nach längerer Zeit werden solche Mails endgültig gelöscht (Cleanup-Job).

## 8. Inbox-Refresh nach IDLE-Sync

- Nach jedem abgeschlossenen IDLE-Sync sendet das Backend ein WebSocket-Event `email.refresh` an die User-Gruppe (`user_{user_id}_events`).
- Das Frontend reagiert auf dieses Event und lädt die E-Mail-Liste neu (API-Call oder Reload).
- Dadurch werden neue, gelöschte und verschobene E-Mails sofort korrekt angezeigt – ohne Polling oder Reload.
- Beispiel-Payload:
  ```json
  {
    "type": "email.refresh",
    "payload": { "folder": "INBOX" }
  }
  ```

## Aktuelles Verhalten (2025-05-17)

- Das Frontend lauscht auf die Events `email.refresh`, `email_new` und `email.new`.
- Nach Empfang eines Events wird die E-Mail-Liste gezielt neu geladen (kein window.location.reload()).
- Falls Folder/AccountId nicht gesetzt sind, wird auf 'INBOX' und 'all' zurückgegriffen.
- Ausführliches Logging in der Browser-Konsole für Connect, Event, fetchEmailBatch, Fehler.
- Typische Fehlerursachen (z.B. Store-Werte undefined, require im Browser) und Debugging-Tipps sind dokumentiert.
 