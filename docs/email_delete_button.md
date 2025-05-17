# E-Mail-Löschbutton & Server-Löschfunktion (Papierkorb)

## Ziel
- User kann E-Mail im Frontend löschen.
- E-Mail wird auf dem IMAP-Server in den Papierkorb verschoben (nicht nur lokal gelöscht).
- Lokal wird sie als gelöscht markiert (`is_deleted_on_server=True`).
- UI aktualisiert sich sofort (WebSocket-Event).

## Frontend
- Button "Löschen" in der E-Mail-Detailansicht (`EmailDetail.tsx`).
- Klick → API-Call: `POST /api/v1/core/emails/{id}/move_to_trash/`.
- Nach Erfolg: E-Mail-Liste neu laden, Detailansicht schließen.
- Optional: Bestätigungsdialog.

## Backend
- Neue API-Action/Route: `POST /api/v1/core/emails/{id}/move_to_trash/`
- Ruft `move_email(email_id, 'Trash')` (imap/actions.py) auf.
- Nach Erfolg: Setzt `is_deleted_on_server=True` in der DB.
- Sendet WebSocket-Event `email.refresh` an User-Gruppe.
- Fehlerfälle werden geloggt und als API-Fehler zurückgegeben.

## IMAP
- Nutzt `imap_tools.MailBox.move([uid], trash_folder)`.
- Folder-Mapping via `map_folder_name_to_server(account, 'Trash')`.
- Fallback: `.flag([uid], [DELETED], set_flag=True)` + `.expunge()` falls Move nicht unterstützt.

## Fehlerfälle
- IMAP-Fehler (z.B. kein Trash-Ordner, Netzwerkfehler): API gibt Fehler zurück, UI zeigt Meldung.
- Lokale DB wird nur nach erfolgreichem IMAP-Move aktualisiert.

## Logging & Events
- Backend loggt alle Schritte und Fehler.
- Nach erfolgreichem Löschen: WebSocket-Event für sofortiges UI-Update.

## UX-Hinweise
- Löschen ist reversibel (Papierkorb).
- Endgültiges Löschen nur nach explizitem Expunge oder im Papierkorb.
- Nach Löschen: Auswahl auf nächste E-Mail oder keine E-Mail setzen.

### Frontend-Implementierung (Stand 2024-06)
- Delete-Button in `EmailDetail.tsx` (rot, mit Lade- und Fehlerstatus).
- Klick → ruft `moveEmailToTrash(email.id)` (API-Call) auf.
- Nach Erfolg: Detailansicht wird geschlossen, Liste aktualisiert sich (über WebSocket oder Store).
- Bei Fehler: Fehlermeldung unter dem Button.

### Backend-Implementierung (Stand 2024-06)
- API-Action: `POST /api/v1/core/emails/{id}/move_to_trash/` (im `EmailViewSet`)
- Verschiebt E-Mail per `move_email(email.id, 'Trash')` auf IMAP-Server (mit Logging für Trash).
- Bei Erfolg: Setzt `is_deleted_on_server=True` in der DB.
- Sendet WebSocket-Event `email.refresh` an die User-Gruppe (`user_{user.id}_events`).
- Response: `{"status": "moved_to_trash"}` bei Erfolg, `{"error": "move_failed"}` bei Fehler (Status 500).
- Fehler (IMAP, DB, WebSocket) werden geloggt und als API-Fehler zurückgegeben.
- Keine Änderung an der lokalen DB, falls der IMAP-Move fehlschlägt.

### Frontend-Update (2024-06)
- Beim Klick auf Löschen wird die E-Mail sofort per `removeEmail(id)` aus der Liste entfernt (Zustand/Store).
- Der API-Call läuft asynchron im Hintergrund, Fehler werden ignoriert.
- Die UI ist immer sofort aktuell, unabhängig vom Backend-Status. 