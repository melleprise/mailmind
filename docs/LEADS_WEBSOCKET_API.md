# WebSocket-basierte Leads-API (Freelance & Multi-Provider)

## Ziel
Alle Projekt-/Leads-Daten werden ausschließlich über WebSockets zwischen Backend und Frontend ausgetauscht. Kein REST-GET mehr für `/api/v1/freelance/projects/` nötig.

---

## Architektur
- **Backend:** Django Channels (ASGI), ein Consumer pro Provider-Gruppe (z.B. `/ws/leads/`)
- **Frontend:** Öffnet WebSocket, erhält alle Daten und Events live
- **Provider:** Übertragbar auf beliebige Plattformen (freelance.de, xing, etc.)

---

## WebSocket-Endpoint
- URL: `ws(s)://<host>/ws/leads/`
- Authentifizierung: Per Session oder Token (wie bisher)

---

## Event-Formate

### 1. Initiale Datenübertragung (nach Connect)
```json
{
  "type": "leads_init",
  "projects": [
    { "project_id": "...", "title": "...", ... },
    ...
  ],
  "pagination": {
    "page": 1,
    "page_size": 100,
    "total": 1234
  }
}
```

### 2. Update-Event nach Crawl
```json
{
  "type": "leads_updated",
  "projects": [ ... ],
  "pagination": { ... }
}
```

### 3. Detaildaten für einzelne Projekte
```json
{
  "type": "lead_details",
  "project_id": "...",
  "details": { ... }
}
```

### 4. Fehler/Status
```json
{
  "type": "error",
  "detail": "..."
}
```

---

## Pagination & Filter
- Das Frontend kann per WebSocket-Nachricht gezielt Seiten/Filter anfordern:
```json
{
  "type": "get_leads",
  "page": 2,
  "page_size": 100,
  "filter": { "remote": true }
}
```
- Das Backend antwortet mit `leads_init` oder `leads_updated` für die angeforderte Seite.

---

## Frontend-Integration
- Nach Connect: Ladezustand, bis `leads_init` kommt
- Bei `leads_updated`: Liste aktualisieren, Sync-Button wieder aktivieren
- Bei Pagination/Filter: Anfrage per WebSocket senden, auf Antwort warten
- Kein REST-GET mehr nötig

---

## Authentifizierung
- Wie bisher: Token im Query-String oder Cookie
- Backend prüft Auth beim Connect

---

## Migration von REST zu WebSocket
- REST-GET `/api/v1/freelance/projects/` entfällt
- Alle Datenflüsse laufen über WebSocket
- Backend muss State für Pagination/Filter pro Client verwalten

---

## Best Practices
- Events immer mit `type`-Feld
- Initiale Daten nach Connect senden
- Updates (nach Crawl) als `leads_updated` pushen
- Fehler als eigenes Event
- Für große Datenmengen: Pagination/Filter unterstützen
- Provider-agnostisch: `provider`-Feld in Events/Requests möglich

---

## Beispiel-Flow
1. Frontend öffnet WebSocket `/ws/leads/`
2. Backend sendet `leads_init` mit aktuellen Projekten
3. User klickt "Sync" → API-Call startet Crawl
4. Nach Crawl sendet Backend `leads_updated` (mit neuen Projekten)
5. Frontend aktualisiert Liste, Sync-Button wieder aktiv
6. Für Details/Pagination: Frontend sendet gezielte Requests per WebSocket

---

## Erweiterung für weitere Provider
- Im Event/Request: `{ "provider": "freelance.de" }`
- Backend routed an passenden Crawler/Datenspeicher
- Einheitliches Event-Format für alle Provider

---

## Backend-Status (Stand Umsetzung)
- Die WebSocket-API ist im LeadConsumer (Django Channels) nach diesem Plan umgesetzt.
- Unterstützte Events: leads_init, leads_updated, lead_details, error, Pagination/Filter, Authentifizierung, Fehlerbehandlung.
- REST-GET für Projekte entfällt.
- Siehe Code (LeadConsumer) für Details und Erweiterungen. 