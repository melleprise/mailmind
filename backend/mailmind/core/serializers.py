from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import EmailVerification, Email, EmailAccount, AISuggestion, Attachment, APICredential, AvailableApiModel, AIRequestLog
import logging
from rest_framework.validators import UniqueTogetherValidator

User = get_user_model()
logger = logging.getLogger(__name__)

class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""
    confirm_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ('email', 'password', 'confirm_password')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def validate(self, data):
        """Validate that passwords match."""
        if 'confirm_password' in data and data['password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        
        # Validate password
        try:
            validate_password(data['password'])
        except ValidationError as e:
            raise serializers.ValidationError({
                'password': list(e.messages)
            })
            
        return data

    def create(self, validated_data):
        """Create and return a new user."""
        # Remove confirm_password as it's not needed for user creation
        validated_data.pop('confirm_password', None)
        
        # Create an inactive user that needs email verification
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password']
        )
        
        return user

class EmailVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmailVerification
        fields = ('token',)

    def validate_token(self, value):
        """Validate that the token exists and is not expired."""
        try:
            verification = EmailVerification.objects.get(token=value)
            if verification.is_expired():
                raise serializers.ValidationError("Verification token has expired.")
            return value
        except EmailVerification.DoesNotExist:
            raise serializers.ValidationError("Invalid verification token.")

class LoginSerializer(serializers.Serializer):
    """Serializer for user login."""
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        """Validate user credentials."""
        email = data.get('email')
        password = data.get('password')

        if email and password:
            user = authenticate(email=email, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                data['user'] = user
            else:
                raise serializers.ValidationError("Unable to log in with provided credentials.")
        else:
            raise serializers.ValidationError("Must include 'email' and 'password'.")

        return data 

class EmailAccountTestSerializer(serializers.Serializer):
    """Serializer for testing email account connection settings."""
    email = serializers.EmailField()
    imap_server = serializers.CharField(max_length=255)
    imap_port = serializers.IntegerField(default=993)
    imap_use_ssl = serializers.BooleanField(default=True)
    username = serializers.CharField(max_length=255) # Oft gleich wie email, aber nicht immer
    password = serializers.CharField(write_only=True)
    
    # Optional: SMTP Felder, falls auch diese getestet werden sollen (fürs Erste weggelassen)
    # smtp_server = serializers.CharField(max_length=255, required=False)
    # smtp_port = serializers.IntegerField(default=587, required=False)
    # smtp_use_tls = serializers.BooleanField(default=True, required=False)

    def validate(self, data):
        # Hier könnten komplexere Validierungen hin, z.B. Port-Ranges prüfen
        if data['imap_port'] <= 0 or data['imap_port'] > 65535:
            raise serializers.ValidationError({"imap_port": "Invalid port number."})
        # if data.get('smtp_port') and (data['smtp_port'] <= 0 or data['smtp_port'] > 65535):
        #     raise serializers.ValidationError({"smtp_port": "Invalid port number."})    
        return data

# Serializer for EmailAccount Model (New)
class EmailAccountSerializer(serializers.ModelSerializer):
    """Serializer for EmailAccount model (excluding sensitive fields like password)."""
    # user = UserSerializer(read_only=True) # Optional: Include user details

    class Meta:
        model = EmailAccount
        fields = (
            'id', 'user', 'name', 'email', 'provider', 
            'imap_server', 'imap_port', 'imap_use_ssl',
            'smtp_server', 'smtp_port', 'smtp_use_tls',
            'sync_status', 'last_sync', 'last_sync_error',
            'created_at', 'updated_at'
        )
        read_only_fields = ('id', 'user', 'sync_status', 'last_sync', 'last_sync_error', 'created_at', 'updated_at')
        # Password fields are excluded entirely for security

    def create(self, validated_data):
        # Set the user to the request user automatically
        validated_data['user'] = self.context['request'].user
        # Handle password setting (assuming form includes password field)
        password = self.context['request'].data.get('password')
        # TODO: Add validation for password if required here
        instance = EmailAccount(**validated_data)
        if password:
            instance.set_password(password) # Use the encryption method
        instance.save()
        return instance

    def update(self, instance, validated_data):
        # Handle password update separately if provided
        password = self.context['request'].data.get('password')
        if password:
            instance.set_password(password)
            # Don't save password in validated_data
            validated_data.pop('password', None) 

        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance

# Neuer Serializer zum Vorschlagen von Einstellungen
class SuggestSettingsSerializer(serializers.Serializer):
    """Serializer to validate email for suggesting settings."""
    email = serializers.EmailField() 

# Serializer für User-Details (fehlte)
class UserSerializer(serializers.ModelSerializer):
    """Serializer for basic user details."""
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name') # Oder welche Felder du brauchst
        read_only_fields = ('id', 'email') # Email sollte nicht änderbar sein hier 

# Serializer for AISuggestion Model
class AISuggestionSerializer(serializers.ModelSerializer):
    # Include fields needed by the frontend
    # Example: suggested_subject and intent_summary might be useful
    class Meta:
        model = AISuggestion
        fields = (
            'id',
            'type',
            'title',
            'content',
            'status',
            'created_at',
            'processing_time',
            'intent_summary',
            'suggested_subject'
        )
        read_only_fields = fields # Mark all as read-only for now

# Serializer for Attachment Model (NEU)
class AttachmentSerializer(serializers.ModelSerializer):
    # file_url = serializers.SerializerMethodField() # Alternative zu file.url, falls nötig

    class Meta:
        model = Attachment
        fields = (
            'id', 
            'filename', 
            'content_type', 
            'size', 
            'content_id',
            'file' # Standardmäßig wird file.url ausgegeben, was wir wollen
            # 'file_url' # Falls SerializerMethodField verwendet wird
        )
        read_only_fields = fields # Alle Felder sind nur lesend

    # Falls SerializerMethodField verwendet wird:
    # def get_file_url(self, obj):
    #     request = self.context.get('request')
    #     if request and obj.file:
    #         return request.build_absolute_uri(obj.file.url)
    #     elif obj.file:
    #         return obj.file.url # Fallback
    #     return None

# Serializer for Email (List and potentially Base for Detail)
class EmailSerializer(serializers.ModelSerializer):
    suggestions = AISuggestionSerializer(many=True, read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True) # AttachmentSerializer hinzufügen
    has_attachments = serializers.SerializerMethodField() # Use method field
    # Add short and medium summary fields from the Email model
    short_summary = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)
    medium_summary = serializers.CharField(read_only=True, allow_blank=True, allow_null=True)
    # Add contact fields (read-only)
    to_addresses = serializers.ListField(child=serializers.EmailField(), read_only=True)
    cc_addresses = serializers.ListField(child=serializers.EmailField(), read_only=True)
    bcc_addresses = serializers.ListField(child=serializers.EmailField(), read_only=True)
    is_deleted_on_server = serializers.BooleanField(read_only=True)

    class Meta:
        model = Email
        fields = (
            'id', 'account', 'message_id', 'uid', 'conversation_id',
            'from_address', 'from_name',
            'to_addresses', 'cc_addresses', 'bcc_addresses', # Add recipient fields
            'subject', 'body_text', 'body_html', # REMOVE markdown_body from LIST serializer
            'received_at', 'sent_at', 'is_read', 'is_flagged', 'is_replied',
            'has_attachments', 
            'attachments', # attachments-Feld hinzufügen
            'ai_processed', 'ai_processed_at',
            'suggestions',
            # Add the summary fields here
            'short_summary',
            'medium_summary',
            'created_at', 'updated_at',
            'is_deleted_on_server'
        )
        read_only_fields = ('id', 'account', 'message_id', 'uid', 'conversation_id',
                            'from_address', 'from_name',
                            'to_addresses', 'cc_addresses', 'bcc_addresses',
                            'subject', 'body_text', 'body_html', # REMOVE markdown_body from LIST serializer
                            'received_at', 'sent_at', 'is_read', 'is_flagged', 'is_replied',
                            'has_attachments',
                            'attachments',
                            'ai_processed', 'ai_processed_at',
                            'suggestions',
                            'short_summary', 'medium_summary',
                            'created_at', 'updated_at',
                            'is_deleted_on_server'
                           )

    def get_has_attachments(self, obj):
        """Check if there are any attachments associated with the email."""
        return obj.attachments.exists()
        
# Serializer for Email Detail View (inherits from EmailSerializer)
class EmailDetailSerializer(EmailSerializer):
    """Serializer for the detailed view of an Email, includes full bodies."""
    # Inherits fields from EmailSerializer. Explicitly add markdown_body for detail view.
    class Meta(EmailSerializer.Meta): # Inherit Meta from base
        fields = EmailSerializer.Meta.fields + ('markdown_body',) # Add markdown_body to the fields tuple
        # Read-only fields are typically the same, or add markdown_body if needed
        read_only_fields = EmailSerializer.Meta.read_only_fields + ('markdown_body',)
    # If you needed fields ONLY in detail view, add them here.
    # For now, inheriting is sufficient as markdown_body was added to the base.
    # pass # Remove pass, define Meta explicitly

# Serializer for APICredential Model
class APICredentialSerializer(serializers.ModelSerializer):
    # Use a write-only field for receiving the plain text key
    api_key = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})
    # Add a read-only field to indicate if the key is set
    api_key_set = serializers.SerializerMethodField()

    class Meta:
        model = APICredential
        # Explicitly list fields, exclude encrypted one by default from reads
        # Include api_key_set for read operations
        fields = ['provider', 'api_key', 'api_key_set', 'created_at', 'updated_at']
        # Remove provider from read_only_fields; it MUST be provided on create
        read_only_fields = ['api_key_set', 'created_at', 'updated_at']
        # Make 'provider' required on create/update explicitly if needed,
        # though it's implicitly required by being in 'fields' and not read_only
        # extra_kwargs = {
        #     'provider': {'required': True} # Usually not needed if not read_only
        # }

    def get_api_key_set(self, obj):
        """Check if the encrypted key field is populated."""
        # FIX: Access the correct model field name
        return bool(obj.api_key_encrypted) # Use api_key_encrypted

    def create(self, validated_data):
        """
        Handles creation. User is added in the view.
        Encryption happens in the view (perform_create).
        """
        # The view's perform_create now handles encryption and setting the user.
        # We just need to ensure validated_data contains what's needed (provider, api_key).
        # The actual instance creation is done by serializer.save() called in perform_create.
        
        # Remove api_key before calling super() or model manager if encryption is done there
        # In our current setup, the view handles encryption before calling serializer.save(),
        # so we don't need to do much here.
        
        # If we were calling super().create(), we'd need to handle encryption here.
        # For now, this method doesn't need to do much as the view controls creation logic.
        logger.debug(f"APICredentialSerializer create called with validated_data: {validated_data.keys()}")
        # The view will call serializer.save(user=..., encrypted_api_key=...)
        return super().create(validated_data) # This might not even be called if view overrides perform_create


    def update(self, instance, validated_data):
        """
        Handles update. User and provider are fixed.
        Encryption happens in the view (perform_update).
        """
        # The view's perform_update now handles encryption and saving.
        # We just need to ensure validated_data contains api_key.
        
        # If we were calling super().update(), we'd need to handle encryption here.
        # For now, this method doesn't need to do much as the view controls update logic.
        logger.debug(f"APICredentialSerializer update called for provider {instance.provider} with validated_data: {validated_data.keys()}")
        # The view will call serializer.save(encrypted_api_key=...)
        return super().update(instance, validated_data) # This might not even be called if view overrides perform_update

    def to_representation(self, instance):
        """Ensure api_key is never included in the output."""
        representation = super().to_representation(instance)
        # Remove the write-only api_key field if present
        representation.pop('api_key', None)
        # Ensure api_key_set is present (it should be added by SerializerMethodField)
        representation['api_key_set'] = self.get_api_key_set(instance)
        return representation

# --- NEUER Serializer für API Key Check ---
class APICredentialCheckSerializer(serializers.Serializer):
    """Serializer to validate provider and api_key for the check endpoint."""
    provider = serializers.ChoiceField(choices=APICredential.PROVIDER_CHOICES)
    # api_key = serializers.CharField(required=True, allow_blank=False) # Entfernen

    # def validate_api_key(self, value):
    #     # Einfache Längenprüfung oder andere Basischecks hier möglich
    #     if len(value) < 10: # Beispiel: Mindestlänge
    #         raise serializers.ValidationError("API key seems too short.")
    #     return value
    # --- End validate_api_key --- 
# --- ENDE NEUER Serializer --- 

class AvailableApiModelSerializer(serializers.ModelSerializer):
    """Serializer for the AvailableApiModel model."""
    class Meta:
        model = AvailableApiModel
        fields = ['provider', 'model_id', 'model_name', 'discovered_at']
        read_only_fields = fields # These are discovered, not set by user

# --- BEGIN: AIRequestLog Serializers ---

class AIRequestLogListSerializer(serializers.ModelSerializer):
    """Serializer for listing AIRequestLog entries (minimal fields)."""
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = AIRequestLog
        fields = [
            'id',
            'timestamp',
            'user_email',
            'provider',
            'model_name',
            'is_success',
            'triggering_source',
            'duration_ms',
        ]
        read_only_fields = fields # All fields are read-only in list view

class AIRequestLogDetailSerializer(serializers.ModelSerializer):
    """Serializer for the detail view of an AIRequestLog entry."""
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = AIRequestLog
        fields = '__all__' # Show all fields in detail view

# --- Serializer für Ordnererstellung ---
class CreateFoldersSerializer(serializers.Serializer):
    folder_paths = serializers.ListField(
        child=serializers.CharField(max_length=255, allow_blank=False),
        allow_empty=False,
        help_text="Liste der vollständigen Ordnerpfade, die erstellt werden sollen (ohne Präfix)."
    )

# --- END Serializer für Ordnererstellung ---