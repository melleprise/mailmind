# KI-Features & Prompt-Handling

## API-Key Handling & Provider-Authentifizierung
- API-Keys und OAuth-Tokens werden für verschiedene Provider (z.B. Google Gemini, Groq, Qdrant) verwendet.
- Speicherung erfolgt in den jeweiligen Account-Objekten oder in Umgebungsvariablen (z.B. QDRANT_API_KEY in settings).
- Zugriff auf API-Keys erfolgt in folgenden Modulen:
  - `ai/models_discovery.py`: Übergabe der API-Keys an Provider-Discovery-Funktionen.
  - `ai/clients.py` & `ai/tasks.py`: Initialisierung von Provider-Clients mit API-Key aus Settings oder User-Account.
  - `api/views.py`: Speicherung und (noch nicht verschlüsselte) Behandlung von OAuth-Tokens im Account-Modell.
  - `middleware.py`: Token-Authentifizierung für Websockets via DRF Token.
- Sensible Daten wie OAuth-Tokens sollten verschlüsselt gespeichert werden (siehe TODO in `api/views.py`).
- Secrets für Deployment (z.B. DockerHub, SSH) werden in GitHub Actions Workflows als `${{ secrets.* }}` gehandhabt.

## Prompt-Templates 