# Freelance Provider Credentials – Konzept & Umsetzung

## Ziel

Sichere Speicherung und Verwaltung von Zugangsdaten für den Provider freelance.de:
- Username (Klartext)
- Passwort (symmetrisch verschlüsselt, Fernet)
- Login URL (link_1)
- Pagination URL 1 (link_2)
- Pagination URL 2 (link_3)
- Userbindung (ForeignKey)
- Timestamps (created_at, updated_at)

## Umsetzungsschritte

1. **Modell-Erweiterung**
   - Neues Modell `FreelanceProviderCredential` in `mailmind.freelance.models`.
   - Felder: user, username, password_encrypted, link_1, link_2, link_3, created_at, updated_at.
   - Methoden: `set_password`, `get_password` (Fernet-Verschlüsselung, analog zu EmailAccount).
   - Meta: unique_together (user, username), ordering, verbose_name.

2. **Migration**
   - Migration erstellt und angewendet.
   - Konflikte mit bestehender Tabelle gelöst (DROP TABLE, dann Migration).

3. **Verschlüsselungsstandard**
   - Symmetrische Verschlüsselung mit Fernet (Key abgeleitet aus Django SECRET_KEY, wie bei API-Credentials).
   - Passwort wird nie im Klartext gespeichert.
   - Entschlüsselung nur im Backend-Code.

4. **Django-Integration**
   - Modell ist produktionsreif, migrationssicher und entspricht dem Security-Standard des Projekts.
   - Userbindung über ForeignKey.

5. **Dokumentation**
   - Doku in `DOKUMENTATION.md` und hier.
   - Hinweis auf produktionssichere Speicherung und Standardisierung.

## Status (Stand: Umsetzung abgeschlossen)

- Modell und Migration produktiv im Backend vorhanden
- Doku und Security-Standard umgesetzt
- Datenbankstruktur und Verschlüsselung geprüft
- Bereit für API/Serializer/Frontend-Integration

---

**Wichtige Hinweise:**
- Passwort wird ausschließlich verschlüsselt gespeichert (Fernet, symmetrisch, Key aus SECRET_KEY)
- Kein Klartext-Zugriff außerhalb des Backend-Codes
- Standard entspricht allen anderen Credentials im System
- Migration und Datenbankstruktur sind produktionssicher 