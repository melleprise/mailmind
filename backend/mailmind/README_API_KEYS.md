# API Keys im Backend-System

Das Backend verwendet ein sicheres System zur Speicherung und Verwaltung von API-Schlüsseln für externe Dienste wie Groq und Google Gemini. Diese Dokumentation erklärt, wie das System funktioniert und wie API-Keys programmatisch abgerufen und verwendet werden können.

## Grundkonzept

API-Keys werden verschlüsselt in der Datenbank gespeichert und nur bei Bedarf entschlüsselt. Das System bietet:
- Verschlüsselung mit Fernet (symmetrische Verschlüsselung)
- Benutzerspezifische Speicherung (jeder Nutzer hat eigene API-Keys)
- Providerunabhängigkeit (verschiedene Anbieter werden unterstützt)

## Datenmodell

Die zentrale Klasse für API-Keys ist `APICredential` in `mailmind/core/models.py`:

```python
class APICredential(models.Model):
    PROVIDER_CHOICES = [
        ('google_gemini', 'Google Gemini'),
        ('groq', 'Groq'),
        # Weitere Provider können hinzugefügt werden
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_credentials')
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES)
    api_key_encrypted = models.TextField(blank=True, help_text="Verschlüsselter API Key")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'provider')  # Ein Key pro User und Provider
```

## Verschlüsselung

Die Verschlüsselung verwendet den Django SECRET_KEY als Basis für den Schlüssel:

```python
def get_api_credential_encryption_key():
    secret_key = getattr(settings, 'SECRET_KEY', None)
    hasher = hashlib.sha256()
    hasher.update(secret_key.encode('utf-8'))
    derived_key = base64.urlsafe_b64encode(hasher.digest())
    return derived_key
```

## API-Keys speichern und abrufen

### API-Keys speichern:

```python
# APICredential-Objekt muss existieren
credential = APICredential.objects.get(user=user, provider='groq')
credential.set_api_key('your-api-key-here')
credential.save()
```

### API-Keys abrufen:

```python
# APICredential-Objekt abrufen
credential = APICredential.objects.get(user=user, provider='groq')
api_key = credential.get_api_key()

# API-Key verwenden
if api_key:
    # Verwende den API-Key mit dem entsprechenden Client
    client = Groq(api_key=api_key)
```

## REST-API

Der `APICredentialViewSet` in `mailmind/core/views.py` stellt die REST-API bereit:

- `GET /api/v1/core/api-credentials/` - Liste aller API-Credentials des aktuellen Nutzers
- `GET /api/v1/core/api-credentials/{provider}/` - Details einer spezifischen API-Credential
- `POST /api/v1/core/api-credentials/` - Neue API-Credential erstellen
- `PUT /api/v1/core/api-credentials/{provider}/` - API-Credential aktualisieren
- `DELETE /api/v1/core/api-credentials/{provider}/` - API-Credential löschen

## Beispielcode

Ein vollständiges Beispiel zur Verwendung von API-Keys befindet sich in `mailmind/example_api_key_usage.py`. Hier ist ein Ausschnitt:

```python
def get_api_key_for_user(user_id, provider):
    try:
        user = User.objects.get(id=user_id)
        credential = APICredential.objects.get(user=user, provider=provider)
        api_key = credential.get_api_key()
        return api_key
    except Exception as e:
        logger.exception(f"Fehler beim Abrufen des API-Keys: {str(e)}")
        return None

def use_groq_api(user_id):
    api_key = get_api_key_for_user(user_id, 'groq')
    if api_key:
        client = Groq(api_key=api_key)
        # API verwenden
```

## Sicherheitshinweise

1. Der APICredential-Verschlüsselungsmechanismus verwendet den Django SECRET_KEY zur Ableitung des Verschlüsselungsschlüssels. 
   Falls der SECRET_KEY geändert wird, können bestehende verschlüsselte API-Keys nicht mehr entschlüsselt werden.

2. API-Keys sollten niemals in Logs, temporären Dateien oder anderen persistenten Speichern unverschlüsselt abgelegt werden.

3. API-Keys sollten nur so lange im Speicher gehalten werden, wie sie benötigt werden.

## Fehlerbehandlung

Bei Problemen mit API-Keys ist es ratsam, folgende Fehlerquellen zu prüfen:

- Fehler beim `get_api_key()`: API-Key könnte nicht entschlüsselbar sein (z.B. wenn der SECRET_KEY geändert wurde)
- `APICredential.DoesNotExist`: Kein API-Key für den angegebenen Provider gespeichert
- Exceptions bei API-Aufrufen: Der API-Key könnte ungültig sein oder fehlerhafte Berechtigungen haben 