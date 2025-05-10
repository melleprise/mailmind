# API Endpunkte

Dieses Dokument beschreibt die API-Endpunkte der Mailmind-Anwendung.

**Basis-URL:** `/api/v1/`

## Authentifizierung (`/auth/`)

*   `POST /auth/login/`
*   `POST /auth/register/`
*   `GET /auth/verify-email/<str:token>/`
*   `POST /auth/verify-email/`
*   `GET /auth/user/`

## Core (`/core/`)

*   **E-Mail-Konten (`/core/email-accounts/`)**
    *   `GET /core/email-accounts/`
    *   `POST /core/email-accounts/`
    *   `PUT /core/email-accounts/<int:pk>/`
    *   `DELETE /core/email-accounts/<int:pk>/`
    *   `POST /core/email-accounts/test-connection/`
    *   `POST /core/email-accounts/<int:pk>/sync/`
    *   `POST /core/email-accounts/suggest-settings/`
*   **API-Credentials (`/core/api-credentials/`)**
    *   `GET /core/api-credentials/<str:provider>/`
    *   `POST /core/api-credentials/`
    *   `PUT /core/api-credentials/<str:provider>/`
    *   `DELETE /core/api-credentials/<str:provider>/`
    *   `POST /core/credentials/<str:provider>/check/`
*   **AI Models (`/core/ai/`)**
    *   `GET /core/ai/available-models/<str:provider>/`
    *   `POST /core/ai/suggest-folder-structure/`
    *   `POST /core/ai/check-api-keys/`
*   **Logs (`/core/ai-request-logs/`)**
    *   `GET /core/ai-request-logs/`
    *   `GET /core/ai-request-logs/<int:pk>/`
*   **Verification (`/core/`)**
    *   `POST /core/resend-verification/`

## API App (`/` relativ zur Basis-URL `/api/v1/`)

*   **E-Mails (`/emails/`)**
    *   `GET /emails/` (Handled by `/core/emails/` now? TODO: Verify)
    *   `GET /emails/<int:pk>/` (Handled by `/core/emails/<id>/` now? TODO: Verify)
    *   `POST /emails/<int:pk>/mark-read/` (Handled by `/core/emails/<id>/mark-read/` now? TODO: Verify)
    *   `POST /emails/<int:pk>/flag/` (Handled by `/core/emails/<id>/flag/` now? TODO: Verify)
    *   `POST /emails/<int:pk>/unflag/` (Handled by `/core/emails/<id>/unflag/` now? TODO: Verify)
    *   `POST /emails/<int:email_id>/refresh-suggestions/`
    *   `POST /emails/<int:pk>/generate-suggestions/` (Handled by `/core/emails/<id>/generate-suggestions/` now? TODO: Verify)
    *   `POST /emails/<int:email_pk>/refine-reply/` **(NEU)**
    *   `POST /emails/<int:id>/mark-spam/` **(NEU)**
*   **E-Mail-Konten (`/email-accounts/`)**
    *   `GET /email-accounts/<int:pk>/folders/`
*   **Suggestions (`/suggestions/`)**
    *   `GET /suggestions/` (Handled by `/core/suggestions/` now? TODO: Verify)
    *   `GET /suggestions/<uuid:pk>/` (Handled by `/core/suggestions/<id>/` now? TODO: Verify)
    *   `POST /suggestions/<uuid:pk>/correct-text/`
    *   `POST /suggestions/<uuid:pk>/refine/`
*   **Kontakte (`/contacts/`)**
    *   `GET /contacts/` (Handled by `/core/contacts/` now? TODO: Verify)
    *   `GET /contacts/<int:pk>/` (Handled by `/core/contacts/<id>/` now? TODO: Verify)

## Prompt Templates (`/prompts/templates/`)

*   `GET /prompts/templates/`

## Schema & Docs

*   `/api/v1/schema/`
*   `/api/v1/docs/`

**Hinweis:** Einige Endpunkte scheinen sowohl unter `/core/` als auch direkt unter `/api/v1/` definiert zu sein (z.B. `/emails/`). Dies sollte überprüft und konsolidiert werden, um Klarheit zu schaffen. Die Pfade in der Frontend-`api.ts` sollten den *tatsächlich funktionierenden* Pfaden entsprechen. 

## Freelance (`/freelance/`)

*   **Credentials (`/freelance/credentials/`)**
    *   `GET /freelance/credentials/` - Vorhandene Credentials abrufen
    *   `POST /freelance/credentials/` - Neue Credentials erstellen 
    *   `PUT /freelance/credentials/` - Vorhandene Credentials aktualisieren
    *   `DELETE /freelance/credentials/` - Credentials löschen
    *   `POST /freelance/credentials/validate/` - Test-Login mit gespeicherten Credentials
*   **Projects (`/freelance/projects/`)**
    *   `GET /freelance/projects/` - Liste aller gecrawlten Projekte 