# Plan: Dynamische Prompts mit Provider-/Modell-Auswahl

1.  **Datenbank:**
    *   Neue Django-App `prompt_templates` erstellen (`backend/mailmind/prompt_templates`).
    *   App zu `INSTALLED_APPS` in `base.py` hinzufügen (`mailmind.prompt_templates`).
    *   Django-Modell `PromptTemplate` in `prompt_templates/models.py` definieren:
        *   Felder: `name` (unique slug), `description` (Text), `template` (TextField), `provider` (CharField mit Choices), `model_name` (CharField), `is_active` (Boolean), `created_at`, `updated_at`.
    *   Django-Migration erstellen und ausführen.

2.  **Initialdaten:**
    *   Fixture (`prompt_templates.json`) erstellen, die initiale Prompts mit Standard-Provider/Modell enthält.

3.  **Backend-Anpassungen:**
    *   Hilfsfunktion `get_prompt_details(name: str) -> dict` in `prompt_templates/utils.py` erstellen (oder einem ähnlichen Ort). Gibt `template`, `provider`, `model_name` zurück.
    *   **AI Client Logik anpassen (`clients.py`, Tasks):**
        *   API-Aufruffunktionen (z.B. `call_gemini_api`) anpassen, um `provider` und `model_name` als Argumente zu akzeptieren.
        *   Factory/Dispatch-Logik implementieren, um basierend auf `provider` den korrekten Client zu nutzen und `model_name` zu übergeben.
    *   In AI-Tasks (`tasks.py`, etc.):
        *   `get_prompt_details(prompt_name)` aufrufen.
        *   Template formatieren: `details['template'].format(**context)`.
        *   API-Aufruffunktion mit formatiertem Prompt, `details['provider']` und `details['model_name']` aufrufen.
        *   Fehlerbehandlung erweitern (Prompt nicht gefunden, Provider/Modell ungültig).

4.  **Admin-Interface:**
    *   `PromptTemplate`-Modell in `prompt_templates/admin.py` registrieren.

5.  **API für Frontend:**
    *   Neuen DRF ViewSet (`PromptTemplateViewSet` in `prompt_templates/views.py`), Serializer (`PromptTemplateSerializer`) und URLs (`prompt_templates/urls.py`, `config/urls.py`) für CRUD-Operationen erstellen.
    *   **Neuer API-Endpunkt:** `/api/ai/providers/` erstellen, der verfügbare Provider und Modelle zurückgibt (z.B. aus Django Settings).
    *   Berechtigungen setzen (z.B. nur Admins).

6.  **Frontend-Einstellungen:**
    *   Neuen Menüpunkt "Einstellungen" -> "Prompts" hinzufügen.
    *   Neue Seite/Komponente (`SettingsPrompts.tsx`):
        *   Ruft `/api/prompt-templates/` und `/api/ai/providers/` auf.
        *   Zeigt Liste der Prompts an.
        *   Bearbeitungsfunktion (Modal/Inline):
            *   Textfeld für `template`.
            *   Dropdown für `provider`.
            *   Dropdown für `model_name` (gefiltert nach Provider).
            *   Speichern-Funktion (ruft API auf).
            *   Hinweis auf Platzhalter.
    *   Material UI verwenden.

7.  **Dokumentation:**
    *   Diese `settings-prompts.md` aktuell halten.
    *   Andere `.md`-Dateien anpassen/veralten lassen.

8.  **Testing:**
    *   Backend/Frontend-Tests hinzufügen/anpassen.
    *   End-to-End-Tests durchführen.

## KnowledgeFields und Platzhalter im Prompt-Kontext

- Platzhalter wie `{cv}` und `{agent}` können in Prompt-Templates verwendet werden.
- Diese werden dynamisch aus den KnowledgeFields des Benutzers befüllt (siehe Modell `KnowledgeField`).
- Falls kein Wert für einen Platzhalter vorhanden ist, wird ein Default-Text wie `[Kein Lebenslauf hinterlegt]` oder `[Kein Agenten-Text hinterlegt]` eingesetzt.
- Die Pflege der KnowledgeFields erfolgt im Admin oder über ein passendes Frontend.
- Die Prompt-Kontext-Logik im Backend sorgt dafür, dass alle im Template verwendeten Platzhalter entweder aus den KnowledgeFields oder mit einem Default-Wert belegt werden.
- Fehlerhafte oder fehlende Platzhalter führen so nicht mehr zu einem Abbruch der Task. 