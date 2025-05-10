# API Credential Management

This document outlines the features and functionality related to managing external API credentials (like Groq, Google Gemini) within the MailMind application.

## Core Features

*   **Secure Storage:** API keys are stored securely in the database, encrypted at rest.
*   **Provider Support:** Supports multiple AI providers (e.g., Groq, Google Gemini).
*   **Status Check:** Allows checking if an API key is set for a provider.
*   **CRUD Operations:** Provides API endpoints for creating, reading, updating, and deleting credentials.
*   **Real-time Validation (via WebSocket):** Provides real-time feedback on the validity of a stored API key upon request.
*   **(Neu) Model Discovery:** Upon checking/saving a key, available models for the provider are fetched and stored.
*   **(Neu) Model Listing:** An API endpoint allows fetching the stored available models for a provider.

## Database Models

*   `ApiCredential`: Stores the provider name, user association, and the encrypted API key.
*   `(Neu) AvailableApiModel`: Stores the model ID/name retrieved from a provider, linked to the corresponding `ApiCredential`'s provider type.

## API Endpoints

*   `GET /api/v1/credentials/`: List all credential statuses for the user.
*   `POST /api/v1/credentials/`: Create a new credential.
*   `GET /api/v1/credentials/{provider}/`: Get the status of a specific credential.
*   `PUT /api/v1/credentials/{provider}/`: Update a specific credential.
*   `DELETE /api/v1/credentials/{provider}/`: Delete a specific credential.
*   `POST /api/v1/credentials/{provider}/check/`: Trigger a validation check for the credential. (Erweitert um Model Discovery)
*   `(Neu) GET /api/v1/credentials/{provider}/models/`: Get the list of available models stored for the provider.

## WebSocket Events

*   `api_key_status`: Pushes the validation status (`checking`, `valid`, `invalid`, `error`) for a specific provider to the connected client.

## Implementation Notes

*   API key validation logic resides in the backend.
*   Model discovery logic uses the respective provider's official APIs/SDKs.
*   Frontend components (`ApiCredentialForm.tsx`, `SettingsPage.tsx`) interact with these backend endpoints. 