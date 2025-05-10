# KI-Features & Prompt-Handling

## Prompt-Templates
- Alle Prompts liegen als Template mit Platzhaltern (z.B. {cv}, {agent}, {email_body}) vor.
- Die Templates werden per Fixture geladen (siehe: mailmind/prompt_templates/fixtures/prompt_templates.json).
- Das Template `summarize_email` erzeugt `short_summary` und `medium_summary`.

## KnowledgeFields
- User können beliebige Key-Value-Paare als KnowledgeField speichern.
- Alle KnowledgeFields werden beim Prompt-Building automatisch in den Kontext übernommen:
  - Beispiel: KnowledgeField mit key `cv` und value `Mein Lebenslauf...` → Platzhalter `{cv}` im Prompt wird ersetzt.
- Die Übernahme erfolgt in allen relevanten Tasks (z.B. generate_suggestions, refine, summary_tasks).
- Fehlende Platzhalter führen zu KeyError, werden aber geloggt (AIRequestLog).

## summary_tasks.py
- Lädt KnowledgeFields des Users und übernimmt sie in den Prompt-Kontext.
- Nutzt das Template `generate_suggestions` oder `summarize_email` (je nach Konfiguration).
- Antwort der KI wird als JSON erwartet und geparst.
- Fehlerhafte oder fehlende Platzhalter werden geloggt.

## Hinweise
- Beispiel für KnowledgeField-Nutzung im Prompt:
  - Prompt: `... Kontext: {cv} ...`
  - KnowledgeField: key=`cv`, value=`Mein Lebenslauf...`
- Alle neuen/angepassten Funktionen müssen hier dokumentiert werden. 