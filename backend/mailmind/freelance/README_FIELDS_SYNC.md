# Wichtiger Hinweis: Model- und Serializer-Felder synchron halten

**Problem:**
Wenn im Model (z.B. FreelanceProject) neue Felder ergänzt werden, müssen diese auch im zugehörigen Serializer (z.B. FreelanceProjectSerializer) ergänzt werden.

**Folgen bei Nichtbeachtung:**
- REST-API wirft Fehler oder liefert unvollständige Daten
- WebSocket-Verbindungen (z.B. LeadConsumer) brechen kommentarlos ab, wenn ein Feld fehlt
- Fehler sind oft nicht direkt im Log sichtbar

**Best Practice:**
- Nach jeder Model-Änderung: Alle zugehörigen Serializer prüfen und anpassen
- Test: Nach Migration immer WebSocket und REST-API testen
- Doku und Code-Kommentare aktuell halten

**Checkliste:**
- [ ] Model geändert? → Serializer anpassen!
- [ ] Migration gemacht? → WebSocket/REST testen!

**Letztes Update:** 2025-05-16 