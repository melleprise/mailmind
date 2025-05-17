# Geräteübergreifende Persistenz von Drafts und Suggestion-Auswahl

## Ziel
Drafts (Korrekturen) und die zuletzt ausgewählte Suggestion sollen für jeden User backendbasiert gespeichert werden, sodass sie auf jedem Gerät nach Login wiederhergestellt werden.

---

## Aktueller Stand
- Drafts und Suggestion-Auswahl werden **nur im Frontend (localStorage)** gespeichert.
- Nach Login auf einem anderen Gerät sind diese Daten **nicht** verfügbar.

---

## Konzept für Backend-Persistenz

### 1. Backend-Modell
- Neues Modell `Draft`:
  - `user` (ForeignKey)
  - `email` (ForeignKey)
  - `subject` (Text)
  - `body` (Text)
  - `selected_suggestion_index` (Integer, optional)
  - `updated_at` (DateTime)

### 2. API-Endpunkte
- `GET /drafts/?email_id=...` → Lade Draft für Email/User
- `POST /drafts/` → Speichere/aktualisiere Draft (inkl. Auswahl)
- Optional: `DELETE /drafts/?email_id=...` → Draft löschen

### 3. Frontend-Integration
- Beim Ändern von Draft oder Suggestion-Auswahl: Sofort per API speichern
- Beim Laden einer Email: Draft und Auswahl per API laden und im State setzen
- Fallback: Bei Offline-Nutzung weiterhin localStorage nutzen, bei Login synchronisieren

### 4. Migration
- Beim ersten Backend-Login: LocalStorage-Drafts an Backend senden
- Danach: Nur noch Backend als Quelle

---

## Vorteile
- Drafts und Auswahl sind auf allen Geräten synchron
- Kein Datenverlust bei Browser-Reset
- Bessere Kollaboration und Nachvollziehbarkeit

---

## Hinweise
- Datenschutz: Drafts sind usergebunden, nicht global
- API-Auth beachten (Token)
- Optional: Versionierung/Änderungshistorie für Drafts

---

## ToDo
- Backend-Modell und Migration
- API-Endpoints
- Frontend-Integration
- Tests und Doku

## API-Sicherheit & Fehlerbehandlung
- Jeder Draft ist eindeutig usergebunden (`unique_together`).
- Alle API-Methoden prüfen Authentifizierung (Token).
- Update, Patch und Delete prüfen Ownership (kein Zugriff auf fremde Drafts möglich, sonst 403).
- Fehlerfälle: 400 (fehlende Parameter), 403 (kein Zugriff), 404 (nicht gefunden), 200/201 (OK).

## Endpunkte (final)
- `GET /drafts/?email_id=...` → Liste aller eigenen Drafts (optional Filter)
- `GET /drafts/by_email/?email_id=...` → Lade Draft für Email/User
- `POST /drafts/` → Neuen Draft anlegen
- `PATCH /drafts/<id>/` → Draft aktualisieren
- `DELETE /drafts/<id>/` → Draft löschen

## Hinweise (final)
- Drafts sind immer usergebunden, keine Fremdzugriffe möglich
- Ownership wird serverseitig geprüft
- Fehler werden als JSON mit passendem Statuscode geliefert 