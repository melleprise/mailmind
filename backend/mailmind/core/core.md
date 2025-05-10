# Mailmind Core App Documentation

This document describes key models and functionalities within the `core` app of Mailmind.

## Models

### `EmailAccount`

Represents a user's email account configuration.

- **Password Handling:**
  - Passwords (`password` field) are stored encrypted in the database using the Fernet symmetric encryption scheme (`cryptography` library).
  - The encryption key is derived from Django's `SECRET_KEY` using a salt (`core.models.get_encryption_key`).
  - Use `instance.set_password(plain_password)` to encrypt and set the password.
  - Use `instance.get_password()` to decrypt and retrieve the plain password. Returns `None` on error or if no password is set.
  - OAuth refresh tokens (`oauth_refresh_token`) are intended to be stored similarly encrypted (ensure this is implemented if OAuth is used).

### `APICredential`

Stores API keys for external services (e.g., Google Gemini, Groq) linked to a user.

- **Encryption:** Uses the same Fernet encryption mechanism as `EmailAccount` for the `api_key_encrypted` field.
  - `instance.set_api_key(plain_key)`
  - `instance.get_api_key()`

## API Endpoints (`core.urls` & `core.views`)

Base path: `/api/v1/core/`

### Email Accounts (`/email-accounts/`)

- **Viewset:** `EmailAccountViewSet` (ModelViewSet)
- **URL:** `/api/v1/core/email-accounts/`
- **Methods:** GET (list), POST (create), GET (retrieve), PUT/PATCH (update), DELETE
- **Authentication:** Required (IsAuthenticated)
- **Permissions:** User can only access/modify their own accounts.
- **Creation:** Uses `set_password` automatically via the `EmailAccountSerializer` to encrypt the password.
- **Actions:**
  - `/sync/` (POST): Placeholder to trigger account synchronization.

### API Credentials (`/api-credentials/`)

- **Viewset:** `APICredentialViewSet` (GenericViewSet with specific mixins)
- **URL:** `/api/v1/core/api-credentials/`
- **Lookup Field:** `provider` (e.g., `google_gemini`)
- **Detail URL:** `/api/v1/core/api-credentials/{provider}/`
- **Methods:** POST (create), GET (retrieve), PUT/PATCH (update), DELETE
- **Authentication:** Required (IsAuthenticated)
- **Permissions:** User can only manage their own credentials.
- **Retrieve (`GET /{provider}/`):**
  - Checks if a credential exists for the user and provider.
  - Returns `200 OK` with `{"provider": "...", "exists": true/false}`. If `exists` is true, it means a key is stored (not necessarily valid).
  - **Returns `404 Not Found` if NO credential entry exists for the user/provider combination.** The frontend should handle this 404 specifically to mean "key does not exist".
- **Create (`POST /`):** Requires `provider` and `api_key` in the body. Tests the key before saving.
- **Update (`PUT/PATCH /{provider}/`):** Requires `api_key` in the body. Tests the key before saving.
- **Delete (`DELETE /{provider}/`):** Removes the credential entry.

### Suggest Settings (`/suggest-settings/`)

- **View:** `SuggestEmailSettingsView` (APIView)
- **URL:** `/api/v1/core/suggest-settings/`
- **Method:** POST
- **Authentication:** Required (IsAuthenticated)
- **Functionality:** Suggests IMAP/SMTP settings based on the email domain provided in the POST body (`{"email": "..."}`). Uses a predefined dictionary (`KNOWN_PROVIDER_SETTINGS`).

### Test Connection (`/test-connection/`)

- **View:** `EmailAccountTestConnectionView` (APIView)
- **URL:** `/api/v1/core/test-connection/`
- **Method:** POST
- **Authentication:** Required (IsAuthenticated)
- **Functionality:** Tests provided IMAP credentials (server, port, ssl, username, password) without saving them.

## AI Integration (`mailmind.ai`)

- **API Key Usage:** Tasks like `generate_ai_suggestion` fetch the relevant `APICredential` for the user associated with the email being processed. The decrypted key is then used for API calls (e.g., to Google Gemini via `call_gemini_api`). Ensure the correct key (`API_CREDENTIAL_ENCRYPTION_KEY`) is configured in settings. 