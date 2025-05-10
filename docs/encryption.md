# Verschlüsselungs-Strategie

Dieses Dokument beschreibt, wie sensible Daten wie Passwörter und API-Schlüssel in der Anwendung verschlüsselt werden.

## 1. Verschlüsselung von EmailAccount-Passwörtern

Für die Ver- und Entschlüsselung der Passwörter von E-Mail-Konten (`EmailAccount.password`) wird die `cryptography.fernet`-Bibliothek verwendet.

### Schlüsselverwaltung

- Es wird ein **dedizierter Fernet-Schlüssel** benötigt.
- Dieser Schlüssel **muss** als Umgebungsvariable namens `EMAIL_ACCOUNT_ENCRYPTION_KEY` definiert sein.
- Der Wert muss ein **gültiger, URL-safe Base64-kodierter 32-Byte-Schlüssel** sein.
- **WICHTIG:** Dieser Schlüssel muss persistent sein. Wenn der Schlüssel verloren geht oder geändert wird, können zuvor verschlüsselte Passwörter nicht mehr entschlüsselt werden.
- Der Schlüssel wird in `backend/mailmind/core/models.py` über die Funktion `get_email_account_encryption_key()` aus `os.environ` gelesen und validiert.

### Implementierung

- Die Methoden `set_password(plain_password)` und `get_password()` im Modell `EmailAccount` (`backend/mailmind/core/models.py`) übernehmen die Ver- und Entschlüsselung.
- Beim Erstellen oder Aktualisieren eines `EmailAccount` über die API (`EmailAccountViewSet` in `backend/mailmind/api/views.py`) wird die `set_password()`-Methode des Modells aufgerufen, um das Passwort *vor* dem endgültigen Speichern in der Datenbank zu verschlüsseln.
- Wenn Passwörter in der Anwendung benötigt werden (z.B. für IMAP-Verbindungen durch den `idle_manager` oder `sync_account`-Task), wird die `get_password()`-Methode aufgerufen.

## 2. Verschlüsselung von API-Schlüsseln (z.B. Gemini, Groq)

Für die Ver- und Entschlüsselung von API-Schlüsseln, die im Modell `APICredential` (`backend/mailmind/core/models.py`) gespeichert werden, wird ebenfalls `cryptography.fernet` verwendet.

### Schlüsselverwaltung

- **Anders als bei EmailAccount-Passwörtern** wird hier **keine separate Umgebungsvariable** benötigt.
- Der Fernet-Schlüssel wird stattdessen **dynamisch aus dem Django `SECRET_KEY` abgeleitet**. Dies geschieht in der Funktion `get_api_credential_encryption_key()` in `backend/mailmind/core/models.py` mittels SHA256-Hashing und Base64-Kodierung.
- **WICHTIG:** Das bedeutet, dass der Django `SECRET_KEY` **niemals geändert werden darf**, ohne dass zuvor alle gespeicherten API-Schlüssel neu verschlüsselt werden! Eine Änderung des `SECRET_KEY` führt dazu, dass die alten API-Schlüssel nicht mehr entschlüsselt werden können.

### Implementierung

- Die Methoden `set_api_key(api_key)` und `get_api_key()` im Modell `APICredential` übernehmen die Ver- und Entschlüsselung unter Verwendung des aus `SECRET_KEY` abgeleiteten Schlüssels.

## Zusammenfassung der benötigten Umgebungsvariablen

- `EMAIL_ACCOUNT_ENCRYPTION_KEY`: Ein persistenter, URL-safe Base64-kodierter 32-Byte-Schlüssel für EmailAccount-Passwörter.
- `DJANGO_SECRET_KEY`: Der standardmäßige Django Secret Key, der auch zur Ableitung des Schlüssels für API Credentials verwendet wird. 