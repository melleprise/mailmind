# EmailList Komponente - Datenfelder (aus EmailListSerializer)

Diese Komponente (`EmailList.tsx`) zeigt eine Liste von E-Mails an. Die Daten für jedes Listenelement kommen vom Backend-Endpunkt, der den `EmailListSerializer` verwendet.

Folgende Felder sind **tatsächlich** in den Daten für jedes E-Mail-Objekt in der Liste verfügbar (Stand der Prüfung des `backend/mailmind/api/serializers.py`):

- `id` (number): Eindeutige ID der E-Mail.
- `subject` (string): Betreff der E-Mail.
- `short_summary` (string | null): Eine kurze KI-generierte Zusammenfassung (kann null sein).
- `from_address` (string): Die E-Mail-Adresse des Absenders. **Wichtig:** Das Feld `from_name` ist in diesem Serializer *nicht* enthalten!
- `sent_at` (string): Sendezeitpunkt der E-Mail (ISO-Format String).
- `is_read` (boolean): Gibt an, ob die E-Mail als gelesen markiert ist.
- `is_flagged` (boolean): Gibt an, ob die E-Mail markiert ist.
- `account` (number): ID des zugehörigen E-Mail-Kontos.

**Konsequenz für die Anzeige:**

Da `from_name` fehlt, kann die Komponente nur die `from_address` oder Teile davon (z.B. die Domain) anzeigen. Wenn der Absendername angezeigt werden soll, muss der `EmailListSerializer` im Backend angepasst werden, um das Feld `from_name` (oder `from_contact`) einzuschließen. 