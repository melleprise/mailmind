def create_email_prompt(email):
    """Prompt für die E-Mail-Analyse erstellen."""
    prompt = f"""Analysiere die folgende E-Mail und generiere passende Vorschläge für Aktionen oder Antworten.

Von: {email.from_name} <{email.from_address}>
Betreff: {email.subject}

{email.body_text}

Berücksichtige folgende Aspekte:
1. Ist eine Antwort erforderlich oder handelt es sich um eine reine Information?
2. Gibt es Termine oder Deadlines, die beachtet werden müssen?
3. Werden Aktionen oder Entscheidungen von mir erwartet?
4. Ist die E-Mail Teil einer laufenden Konversation?
5. Wie dringend ist eine Reaktion erforderlich?

Generiere strukturierte Vorschläge im folgenden Format:
- Typ: [reply/forward/task/calendar/flag]
- Titel: [Kurze Beschreibung der Aktion]
- Inhalt: [Detaillierter Vorschlag/Text]
- Metadaten: [Relevante zusätzliche Informationen]
- Konfidenz: [0.0-1.0]

Antworte in einem sachlichen, professionellen Stil."""

    return prompt

def create_attachment_prompt(attachment):
    """Prompt für die Analyse von Anhängen erstellen."""
    prompt = f"""Analysiere den folgenden Anhang und extrahiere relevante Informationen.

Dateiname: {attachment.filename}
Typ: {attachment.content_type}
Extrahierter Text:
{attachment.extracted_text}

Berücksichtige folgende Aspekte:
1. Art des Dokuments (z.B. Rechnung, Vertrag, Präsentation)
2. Wichtige Daten oder Zahlen
3. Erforderliche Aktionen
4. Verbindung zum E-Mail-Kontext

Generiere eine strukturierte Analyse im folgenden Format:
- Dokumenttyp: [Klassifizierung]
- Schlüsselinformationen: [Liste wichtiger Punkte]
- Vorgeschlagene Aktionen: [Falls zutreffend]
- Kontext: [Verbindung zur E-Mail]"""

    return prompt 