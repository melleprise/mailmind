from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import EmailValidator
from django.utils.translation import gettext_lazy as _
from django.utils.crypto import get_random_string
import uuid
from django.utils import timezone
from datetime import timedelta
from django.db.models import JSONField
import os
from django.db.models.signals import post_delete
from django.dispatch import receiver
import shutil
from django.conf import settings
import logging
from cryptography.fernet import Fernet, InvalidToken
import base64
import hashlib # Import hashlib
from django.contrib.postgres.fields import ArrayField # Use ArrayField if using PostgreSQL
from mailmind.prompt_templates.models import PromptTemplate

logger = logging.getLogger(__name__)

class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""
    use_in_migrations = True

    def _create_user(self, email, password=None, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', False)  # User needs to verify email first
        extra_fields.setdefault('is_email_verified', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_email_verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model with email as the username field."""
    username = None  # Remove username field
    email = models.EmailField(_('email address'), unique=True)
    first_name = models.CharField(_('first name'), max_length=150, blank=True)
    last_name = models.CharField(_('last name'), max_length=150, blank=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    is_email_verified = models.BooleanField(default=False)
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Custom related_names to avoid clashes
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=_('groups'),
        blank=True,
        help_text=_(
            'The groups this user belongs to. A user will get all permissions '
            'granted to each of their groups.'
        ),
        related_name='core_user_set',
        related_query_name='core_user',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=_('user permissions'),
        blank=True,
        help_text=_('Specific permissions for this user.'),
        related_name='core_user_set',
        related_query_name='core_user',
    )
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []  # Email field is automatically required
    
    def __str__(self):
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name} <{self.email}>"
        return self.email

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = '%s %s' % (self.first_name, self.last_name)
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

class EmailVerification(models.Model):
    """Model for storing email verification tokens."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    def is_expired(self):
        return timezone.now() > self.expires_at

    class Meta:
        verbose_name = 'Email Verification'
        verbose_name_plural = 'Email Verifications'

class EmailAccount(models.Model):
    """E-Mail-Konto-Konfiguration eines Nutzers."""
    
    PROVIDER_CHOICES = [
        ('gmail', 'Google Mail'),
        ('outlook', 'Microsoft Outlook'),
        ('custom', 'Custom IMAP'),
    ]

    SYNC_STATUS_CHOICES = [
        ('idle', 'Idle'),
        ('pending', 'Pending'), # Wartet auf ersten Sync
        ('syncing', 'Syncing'),
        ('synced', 'Synced'),
        ('error', 'Error'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_accounts')
    name = models.CharField(max_length=100, help_text="Anzeigename für das Konto")
    email = models.EmailField(validators=[EmailValidator()])
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    
    # IMAP-Konfiguration
    imap_server = models.CharField(max_length=255)
    imap_port = models.IntegerField(default=993)
    imap_use_ssl = models.BooleanField(default=True)
    
    # SMTP-Konfiguration
    smtp_server = models.CharField(max_length=255)
    smtp_port = models.IntegerField(default=587)
    smtp_use_tls = models.BooleanField(default=True)
    
    # Authentifizierung
    username = models.CharField(max_length=255, help_text="IMAP/SMTP Benutzername")
    password = models.CharField(max_length=255, blank=True, help_text="Nur für Basic Auth - verschlüsselt")
    oauth_refresh_token = models.TextField(blank=True, help_text="OAuth2 Refresh Token - verschlüsselt")
    
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    sync_status = models.CharField(
        max_length=10,
        choices=SYNC_STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    last_sync_error = models.TextField(null=True, blank=True)
    last_sync_started_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'email']
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.email})"

    def save(self, *args, **kwargs):
        """Überschreibt save, um sicherzustellen, dass username gesetzt ist."""
        if not self.username:
            self.username = self.email
            logger.info(f"EmailAccount save: Username was empty, setting to email: {self.email}")
        super().save(*args, **kwargs)

    def set_password(self, plain_password):
        """Verschlüsselt das Passwort vor dem Speichern."""
        key = None # Initialisiere key mit None
        if not plain_password:
            self.password = ""
            return
        try:
            key = get_email_account_encryption_key() # Holt den base64-kodierten key (bytes)
            logger.debug(f"!!! DEBUG KEY USED for Fernet: {key!r}") # NEUE DEBUG-AUSGABE
            logger.debug(f"Attempting to initialize Fernet for account {self.id} with key (bytes, first 10): {key[:10]}...")
            f = Fernet(key)                          # Fernet validiert den Key hier
            encrypted_password_bytes = f.encrypt(plain_password.encode('utf-8'))
            self.password = encrypted_password_bytes.decode('utf-8')
            logger.debug(f"Successfully encrypted password for account {self.id}. Stored value starts with: {self.password[:10]}...")
        except Exception as e:
            # Logge Fehler ohne den Key, da er die Ursache sein könnte oder nicht zugewiesen wurde
            logger.error(f"Error encrypting password for account {self.id}: {e}", exc_info=True)
            self.password = "" # Setze auf leer bei Fehler

    def get_password(self):
        """Entschlüsselt das Passwort."""
        # Logge den gespeicherten Wert, bevor versucht wird zu entschlüsseln
        logger.debug(f"Attempting get_password for account {self.id}. Stored value starts with: {self.password[:10] if self.password else '[EMPTY]'}...")

        if not self.password:
            return None
        try:
            key = get_email_account_encryption_key()
            f = Fernet(key)
            password_bytes = self.password.encode('utf-8')
            decrypted_password = f.decrypt(password_bytes).decode('utf-8')
            logger.debug(f"Successfully decrypted password for account {self.id}")
            return decrypted_password
        except (InvalidToken, base64.binascii.Error, ValueError) as e:
            logger.warning(f"DECRYPTION FAILED for account {self.id} (InvalidToken/Encoding/Key): {e}")
            return None # Korrekte Einrückung sichergestellt
        except Exception as e:
            logger.error(f"UNEXPECTED DECRYPTION ERROR for account {self.id}", exc_info=True)
            return None

# NEU: Signal-Handler zum Löschen des Account-Attachment-Ordners
@receiver(post_delete, sender=EmailAccount)
def delete_account_attachment_folder(sender, instance, **kwargs):
    """Löscht den gesamten Attachment-Ordner für einen Account, wenn dieser gelöscht wird."""
    try:
        account_folder_path = os.path.join(settings.MEDIA_ROOT, 'attachments', f'account_{instance.id}')
        if os.path.isdir(account_folder_path):
            shutil.rmtree(account_folder_path)
            logger.info(f"Deleted attachment folder for account {instance.id}: {account_folder_path}")
        # else:
            # logger.debug(f"Attachment folder for account {instance.id} not found, nothing to delete: {account_folder_path}")
    except Exception as e:
        logger.error(f"Error deleting attachment folder for account {instance.id} at {account_folder_path}: {e}")

class Email(models.Model):
    """Repräsentiert eine einzelne E-Mail."""
    
    account = models.ForeignKey(EmailAccount, on_delete=models.CASCADE, related_name='emails')
    message_id = models.CharField(max_length=255, db_index=True)
    uid = models.CharField(max_length=255, null=True, blank=True, db_index=True, help_text="UID des E-Mails im IMAP-Ordner")
    folder_name = models.CharField(max_length=255, db_index=True, null=True, blank=True)
    conversation_id = models.CharField(max_length=255, db_index=True, blank=True)
    
    from_address = models.EmailField()
    from_name = models.CharField(max_length=255, blank=True)
    from_contact = models.ForeignKey('Contact', on_delete=models.SET_NULL, null=True, blank=True, related_name='emails_from')
    
    to_contacts = models.ManyToManyField(
        'Contact',
        related_name='emails_received_to',
        blank=True
    )
    cc_contacts = models.ManyToManyField(
        'Contact',
        related_name='emails_received_cc',
        blank=True
    )
    bcc_contacts = models.ManyToManyField(
        'Contact',
        related_name='emails_received_bcc',
        blank=True
    )
    reply_to_contacts = models.ManyToManyField('Contact', related_name='emails_reply_to', blank=True)
    
    subject = models.CharField(max_length=1000, blank=True)
    body_text = models.TextField(blank=True)
    body_html = models.TextField(blank=True)
    flags = JSONField(default=list, blank=True, db_index=True)
    markdown_body = models.TextField(null=True, blank=True)
    
    received_at = models.DateTimeField(db_index=True, null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True, db_index=True, help_text="Datum/Zeit aus dem 'Date'-Header der E-Mail")
    date_str = models.CharField(max_length=255, null=True, blank=True, help_text="Originaler 'Date'-String aus dem Header")
    
    is_read = models.BooleanField(default=False, db_index=True)
    is_flagged = models.BooleanField(default=False, db_index=True)
    is_replied = models.BooleanField(default=False, db_index=True, help_text="Entspricht \\Answered Flag")
    is_deleted_on_server = models.BooleanField(default=False, db_index=True, help_text="Entspricht \\Deleted Flag")
    is_draft = models.BooleanField(default=False, db_index=True, help_text="Entspricht \\Draft Flag")
    
    headers = JSONField(null=True, blank=True, help_text="E-Mail Header als JSON")
    size_rfc822 = models.PositiveIntegerField(null=True, blank=True, help_text="Größe laut Server (RFC822)")
    size = models.PositiveIntegerField(null=True, blank=True, help_text="Tatsächliche Größe der heruntergeladenen Nachricht")
    
    embedding_generated = models.BooleanField(default=False)
    ai_processed = models.BooleanField(default=False)
    ai_processed_at = models.DateTimeField(null=True, blank=True, help_text="Zeitstempel der letzten AI-Verarbeitung")
    
    # --- ADD NEW SUMMARY FIELDS --- 
    short_summary = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        help_text="Sehr kurze Zusammenfassung (max 5 Worte)"
    )
    medium_summary = models.CharField(
        max_length=150, 
        blank=True, 
        null=True, 
        help_text="Mittellange Zusammenfassung (6-12 Worte)"
    )
    # --- END NEW FIELDS --- 

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-sent_at', '-received_at']
        indexes = [
            models.Index(fields=['account', 'sent_at']),
            models.Index(fields=['account', 'received_at']),
            models.Index(fields=['message_id']),
            models.Index(fields=['uid']),
            models.Index(fields=['folder_name']),
            models.Index(fields=['conversation_id']),
            models.Index(fields=['is_read']),
            models.Index(fields=['is_flagged']),
            models.Index(fields=['is_replied']),
        ]

    def __str__(self):
        return f"{self.subject} (From: {self.from_address}, Sent: {self.sent_at})"

def attachment_upload_path(instance, filename):
    # filename ist der ursprüngliche Dateiname
    # instance ist die Attachment-Instanz
    account_id = instance.email.account.id
    email_pk = instance.email.pk
    # Erstelle einen Pfad wie: attachments/account_1/email_123/original_filename.pdf
    return os.path.join('attachments', f'account_{account_id}', f'email_{email_pk}', filename)

class Attachment(models.Model):
    """E-Mail-Anhang mit extrahiertem Text und Embedding."""
    
    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name='attachments')
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.IntegerField()
    
    content_id = models.CharField(max_length=255, null=True, blank=True, db_index=True, help_text="Content-ID des Anhangs (für Inline-Bilder)")
    content_disposition = models.CharField(max_length=255, null=True, blank=True, help_text="Content-Disposition (inline/attachment)")
    
    # Verwende die neue Funktion für upload_to
    file = models.FileField(upload_to=attachment_upload_path)
    
    # Extrahierte Informationen
    extracted_text = models.TextField(blank=True)
    embedding_vector = models.BinaryField(null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.filename} ({self.email.subject})"

# NEU: Signal-Handler zum Löschen der Datei, wenn das Attachment-Objekt gelöscht wird
@receiver(post_delete, sender=Attachment)
def delete_attachment_file(sender, instance, **kwargs):
    """Löscht die Datei vom Dateisystem, wenn ein Attachment-Objekt gelöscht wird."""
    # Stelle sicher, dass instance.file existiert und eine Datei hat
    if instance.file:
        if os.path.isfile(instance.file.path):
            try:
                os.remove(instance.file.path)
                # Optional: Loggen, dass die Datei gelöscht wurde
                # logger.info(f"Deleted attachment file: {instance.file.path}")
            except Exception as e:
                # Optional: Fehler beim Löschen loggen
                # logger.error(f"Error deleting attachment file {instance.file.path}: {e}")
                pass # Fehler ignorieren oder spezifischer behandeln

class AISuggestion(models.Model):
    """KI-generierte Vorschläge für E-Mails."""
    
    TYPE_CHOICES = [
        ('reply', 'Antwort'),
        ('forward', 'Weiterleitung'),
        ('task', 'Aufgabe'),
        ('calendar', 'Kalendereintrag'),
        ('flag', 'Markierung'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Ausstehend'),
        ('accepted', 'Akzeptiert'),
        ('modified', 'Modifiziert'),
        ('rejected', 'Abgelehnt'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.ForeignKey(Email, on_delete=models.CASCADE, related_name='suggestions')
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    
    # Vorschlagsinhalt
    title = models.CharField(max_length=100, help_text="Kurzer Titel/Zusammenfassung des Vorschlags")
    content = models.TextField()
    intent_summary = models.CharField(max_length=100, blank=True, help_text="Kurze Intent-Zusammenfassung (max. 5 Worte)")
    suggested_subject = models.CharField(max_length=255, blank=True, help_text="Vorgeschlagener Betreff für die Antwort")
    metadata = models.JSONField(default=dict)

    # Backup-Felder für Undo
    content_backup = models.TextField(blank=True)
    subject_backup = models.CharField(max_length=255, blank=True)
    
    # Verarbeitung
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    user_feedback = models.TextField(blank=True)
    
    confidence_score = models.FloatField(default=0.0)
    processing_time = models.FloatField(help_text="Verarbeitungszeit in Sekunden")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-confidence_score', '-created_at']

    def __str__(self):
        return f"{self.type}: {self.title}"

class Contact(models.Model):
    """Extrahierte Kontaktinformationen aus E-Mails."""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts')
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=255, blank=True)
    
    # Statistiken
    last_interaction = models.DateTimeField(auto_now=True)
    interaction_count = models.IntegerField(default=0)
    
    # Extrahierte Informationen
    organization = models.CharField(max_length=255, blank=True)
    title = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-interaction_count']

    def __str__(self):
        return f"{self.name} <{self.email}>"

# You might want to add your UserProfile model or other core models here as well 

# --- Encryption Key Functions ---

def get_email_account_encryption_key():
    """Retrieves the encryption key for EmailAccount passwords from environment variable.
       Returns the key as bytes, assuming it's a valid URL-safe base64 encoded string.
       Fernet() will perform the final validation.
    """
    secret_key_raw = os.environ.get('EMAIL_ACCOUNT_ENCRYPTION_KEY')
    logger.debug(f"!!! DEBUG RAW KEY from env: {secret_key_raw!r}") # ADDED
    if not secret_key_raw:
        logger.critical("EMAIL_ACCOUNT_ENCRYPTION_KEY environment variable is not set!")
        raise ValueError("EMAIL_ACCOUNT_ENCRYPTION_KEY environment variable is not set!")

    # Nur Whitespace entfernen
    secret_key = secret_key_raw.strip()
    logger.debug(f"!!! DEBUG STRIPPED KEY: {secret_key!r}") # ADDED
    key_bytes = secret_key.encode('utf-8')
    logger.debug(f"!!! DEBUG KEY BYTES to be used: {key_bytes!r}") # RENAMED for clarity
    # logger.debug("Returning stripped EMAIL_ACCOUNT_ENCRYPTION_KEY as bytes.") # Old log
    return key_bytes

def get_api_credential_encryption_key():
    """
    Derives a Fernet encryption key from the Django SECRET_KEY.
    DO NOT CHANGE SECRET_KEY without re-encrypting credentials!
    Returns the key as bytes.
    """
    secret_key = getattr(settings, 'SECRET_KEY', None)
    if not secret_key:
        logger.critical("Django SECRET_KEY is not set in settings! Cannot derive encryption key.")
        raise ValueError("Django SECRET_KEY is not set. Cannot derive encryption key.")

    hasher = hashlib.sha256()
    hasher.update(secret_key.encode('utf-8'))
    derived_key = base64.urlsafe_b64encode(hasher.digest())

    logger.debug(f"Derived encryption key. Length: {len(derived_key)}, Starts with: {derived_key[:4]}...")
    return derived_key # Return bytes

# --- End Encryption Key Functions ---

# --- BEGIN RE-ADDED APICredential MODEL ---
class APICredential(models.Model):
    PROVIDER_CHOICES = [
        ('google_gemini', 'Google Gemini'),
        ('groq', 'Groq'),
        # Füge hier bei Bedarf weitere Provider hinzu
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_credentials')
    provider = models.CharField(max_length=50, choices=PROVIDER_CHOICES)
    api_key_encrypted = models.TextField(blank=True, help_text="Verschlüsselter API Key")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'provider') # Ein Key pro User und Provider
        verbose_name = "API Credential"
        verbose_name_plural = "API Credentials"
        ordering = ['user', 'provider']

    def __str__(self):
        return f"{self.user.email} - {self.get_provider_display()}"

    def set_api_key(self, api_key):
        logger.debug(f"set_api_key called for user {self.user_id}, provider {self.provider}.")
        encryption_key = get_api_credential_encryption_key() # Holt abgeleiteten Key (bytes)
        if not encryption_key:
             logger.critical("Cannot encrypt API key because derived encryption key is missing (SECRET_KEY not set?).")
             raise ValueError("Cannot encrypt API key: Encryption key derivation failed (SECRET_KEY missing?).")
        
        logger.debug(f"Using derived key (len {len(encryption_key)}, starts {encryption_key[:4]}...) for encryption.")
        try:
            f = Fernet(encryption_key) # Übergebe bytes direkt
            encrypted_data = f.encrypt(api_key.encode())
            self.api_key_encrypted = encrypted_data.decode() # Store as string
            logger.debug(f"Successfully encrypted API key (Stored length: {len(self.api_key_encrypted)}). Starts with: {self.api_key_encrypted[:10]}...")
        except Exception as e:
             logger.error(f"Fehler beim Verschlüsseln des API-Keys für User {self.user_id}, Provider {self.provider}: {e}", exc_info=True)
             raise ValueError("API Key konnte nicht verschlüsselt werden.") from e

    def get_api_key(self):
        logger.debug(f"get_api_key called for user {self.user_id}, provider {self.provider}.")
        encryption_key = get_api_credential_encryption_key() # Holt abgeleiteten Key (bytes)
        encrypted_data_str = self.api_key_encrypted

        if not encryption_key or not encrypted_data_str:
            logger.warning(f"Cannot decrypt API key. Key available: {bool(encryption_key)}, Encrypted data exists: {bool(encrypted_data_str)}")
            return None
        
        logger.debug(f"Using derived key (len {len(encryption_key)}, starts {encryption_key[:4]}...) for decryption.")
        logger.debug(f"Attempting to decrypt data (len {len(encrypted_data_str)}): {encrypted_data_str[:10]}...")
        try:
            f = Fernet(encryption_key) # Übergebe bytes direkt
            decrypted_key = f.decrypt(encrypted_data_str.encode()).decode()
            logger.debug(f"Successfully decrypted API key (Decrypted length: {len(decrypted_key)}).")
            return decrypted_key
        except InvalidToken:
             logger.error(f"Invalid token when decrypting API key for user {self.user_id}, provider {self.provider}. SECRET_KEY potentially changed?", exc_info=False) # No need for full trace here
             return None
        except Exception as e:
             logger.error(f"Fehler beim Entschlüsseln des API-Keys für User {self.user_id}, Provider {self.provider}: {e}", exc_info=True)
             return None # Explizit None zurückgeben bei Fehler
# --- END RE-ADDED APICredential MODEL --- 

class AvailableApiModel(models.Model):
    """Stores information about AI models discovered via API for selection."""
    PROVIDER_CHOICES = APICredential.PROVIDER_CHOICES # Reuse choices

    provider = models.CharField(
        max_length=50,
        choices=PROVIDER_CHOICES,
        db_index=True,
        help_text="The API provider this model belongs to."
    )
    model_id = models.CharField(
        max_length=255,
        help_text="The unique identifier of the model as provided by the API."
    )
    model_name = models.CharField(
        max_length=255,
        blank=True, # Name might not always be present or easily derivable
        help_text="A human-readable name for the model (optional)."
    )
    # Add other relevant fields if needed, e.g., context window, capabilities
    discovered_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when this model was first discovered or last updated."
    )

    class Meta:
        unique_together = ('provider', 'model_id') # Ensure unique models per provider
        verbose_name = "Available API Model"
        verbose_name_plural = "Available API Models"
        ordering = ['provider', 'model_id']

    def __str__(self):
        return f"{self.get_provider_display()} - {self.model_id}" + (f" ({self.model_name})" if self.model_name else "")

# --- BEGIN: AIRequestLog MODEL ---
class AIRequestLog(models.Model):
    """Logs individual requests made to external AI APIs."""
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='ai_request_logs', help_text="User who triggered the request (if available).")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True, help_text="When the request was initiated.")
    provider = models.CharField(max_length=50, help_text="AI provider used (e.g., 'groq', 'google_gemini').")
    model_name = models.CharField(max_length=100, help_text="Specific model used.")
    prompt_text = models.TextField(help_text="The exact prompt sent to the API.")
    raw_response_text = models.TextField(blank=True, help_text="The raw text response received from the API.")
    # processed_response = models.JSONField(null=True, blank=True, help_text="Parsed JSON response (if applicable).") # Consider adding later if needed for analysis
    status_code = models.IntegerField(null=True, blank=True, help_text="HTTP status code of the API response.")
    duration_ms = models.PositiveIntegerField(null=True, blank=True, help_text="Duration of the API call in milliseconds.")
    is_success = models.BooleanField(default=False, help_text="Whether the API call was considered successful (e.g., got a valid response).")
    error_message = models.TextField(blank=True, help_text="Error details if the call failed or response processing failed.")
    triggering_source = models.CharField(max_length=100, blank=True, help_text="Where the request originated (e.g., 'generate_suggestions_task', 'api_key_check').") # Optional context

    class Meta:
        verbose_name = "AI Request Log"
        verbose_name_plural = "AI Request Logs"
        ordering = ['-timestamp'] # Show newest logs first

    def __str__(self):
        status = "Success" if self.is_success else "Failure"
        user_email = self.user.email if self.user else "System/Unknown"
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {user_email} - {self.provider}/{self.model_name} - {status}"

# --- END: AIRequestLog MODEL --- 

class AIAction(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    prompts = models.ManyToManyField(PromptTemplate, related_name='actions')
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name 

class AISuggestionEditHistory(models.Model):
    """Historie aller Änderungen an einer Suggestion (Undo/Redo)."""
    suggestion = models.ForeignKey(AISuggestion, on_delete=models.CASCADE, related_name='edit_history')
    field = models.CharField(max_length=16, choices=[('subject', 'Subject'), ('body', 'Body')])
    old_value = models.TextField()
    new_value = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    edit_type = models.CharField(max_length=8, choices=[('manual', 'Manuell'), ('ai', 'KI')], default='manual')
    user = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.suggestion_id} {self.field} {self.edit_type} @ {self.created_at}" 