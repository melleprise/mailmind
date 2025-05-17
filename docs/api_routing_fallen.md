# API-Routing-Fallen & Best Practices (DRF, ViewSets, Actions)

## Problem: Falsche oder doppelte API-URLs
- DRF-ViewSets erzeugen automatisch Routen wie `/api/v1/emails/<id>/action/`.
- Im Projekt gibt es oft mehrere Router (z.B. `api/urls.py` und `core/urls.py`).
- Actions sind **nur** unter dem Pfad verfügbar, wo der ViewSet-Router tatsächlich eingebunden ist.
- Frontend-Calls auf `/api/v1/core/emails/...` funktionieren **nicht**, wenn der Router nur unter `/api/v1/emails/...` registriert ist.

## Typische Fehlerquellen
- Falscher Prefix im Frontend (`/core/emails/` vs. `/emails/`).
- Doppelte oder inkonsistente Registrierung von Routern.
- Backend-Action im Code, aber nicht im gewünschten API-Pfad verfügbar.
- Änderungen an URLs im Backend werden nicht im Frontend nachgezogen.

## Best Practices
- **Immer prüfen, unter welchem Pfad der ViewSet-Router eingebunden ist.**
- **Frontend-API-Calls immer mit dem tatsächlich verfügbaren Pfad testen (z.B. per curl/Postman).**
- **Nie blind `/core/` oder andere Prefixe annehmen – immer gegen die Router-Registrierung prüfen.**
- **Nach jeder Änderung an API-URLs: Doku und Frontend-Calls synchronisieren.**
- **Im Zweifel: `/api/v1/emails/...` verwenden, wenn der ViewSet im Hauptrouter (`api/urls.py`) registriert ist.**

## Quick-Check-Liste
- [ ] Ist der ViewSet im richtigen Router registriert?
- [ ] Ist die Action im DRF-ViewSet korrekt als `@action` deklariert?
- [ ] Ist der API-Call im Frontend exakt auf den verfügbaren Pfad gemappt?
- [ ] Funktioniert der Call per curl/Postman?
- [ ] Ist die Doku (`.md`) aktuell?

**Nie wieder Routing-Fail!** 