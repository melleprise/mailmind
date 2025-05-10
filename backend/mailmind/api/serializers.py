from rest_framework import serializers
from mailmind.core.models import EmailAccount, Email, Attachment, AISuggestion, Contact, AIRequestLog, AIAction
from mailmind.prompt_templates.models import PromptTemplate
import logging

logger = logging.getLogger(__name__)

class EmailAccountSerializer(serializers.ModelSerializer):
    """Serializer für E-Mail-Konten.
       Passwort wird als write_only akzeptiert und im ViewSet verschlüsselt.
    """

    class Meta:
        model = EmailAccount
        fields = [
            'id', 'name', 'email', 'provider',
            'imap_server', 'imap_port', 'imap_use_ssl',
            'smtp_server', 'smtp_port', 'smtp_use_tls',
            'username', 'password', 'oauth_refresh_token', # password bleibt hier
            'is_active', 'last_sync', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_sync', 'created_at', 'updated_at']
        extra_kwargs = {
            'username': {'required': True, 'allow_blank': False},
            # Passwort ist optional und write_only
            'password': {'write_only': True, 'required': False, 'allow_blank': True, 'style': {'input_type': 'password'}}, 
            'oauth_refresh_token': {'write_only': True, 'required': False, 'allow_blank': True}
        }

    def create(self, validated_data):
        # Setze user aus dem request context (wird im ViewSet gemacht)
        # Hinweis: user wird jetzt besser im ViewSet gesetzt
        # validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Passwort-Handling wird im ViewSet gemacht
        validated_data.pop('password', None) 
        validated_data.pop('oauth_refresh_token', None) # Auch Token im ViewSet behandeln?

        # Update andere Felder
        return super().update(instance, validated_data)

class AttachmentSerializer(serializers.ModelSerializer):
    """Serializer für E-Mail-Anhänge."""
    
    class Meta:
        model = Attachment
        fields = [
            'id', 'filename', 'content_type', 'size',
            'file', 'extracted_text', 'created_at',
            'content_id'
        ]
        read_only_fields = ['id', 'created_at', 'content_id']

class ContactSimpleSerializer(serializers.ModelSerializer):
    """Ein einfacher Serializer für die Darstellung von Kontakten in E-Mails."""
    class Meta:
        model = Contact
        fields = ['id', 'name', 'email']
        read_only_fields = fields

class EmailSerializer(serializers.ModelSerializer):
    """Serializer für E-Mails."""
    
    attachments = AttachmentSerializer(many=True, read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)
    from_contact = ContactSimpleSerializer(read_only=True)
    to_contacts = ContactSimpleSerializer(many=True, read_only=True)
    cc_contacts = ContactSimpleSerializer(many=True, read_only=True)
    bcc_contacts = ContactSimpleSerializer(many=True, read_only=True)
    reply_to_contacts = ContactSimpleSerializer(many=True, read_only=True)
    
    def validate_email_list(self, value):
        """Validiert eine Liste von E-Mail-Adressen."""
        if not isinstance(value, list):
            raise serializers.ValidationError("E-Mail-Adressen müssen als Liste übergeben werden.")
        for email in value:
            if not isinstance(email, str) or '@' not in email:
                raise serializers.ValidationError(f"Ungültige E-Mail-Adresse: {email}")
        return value

    def validate_from_address(self, value):
        """Validiert die Absender-E-Mail-Adresse."""
        if not isinstance(value, str) or '@' not in value:
            raise serializers.ValidationError("Ungültige Absender-E-Mail-Adresse")
        return value

    def validate(self, data):
        """Validiert die E-Mail-Adressfelder."""
        for field in ['to_addresses', 'cc_addresses', 'bcc_addresses']:
            if field in data:
                data[field] = self.validate_email_list(data[field])
        return data
    
    class Meta:
        model = Email
        fields = [
            'id', 'account', 'account_name',
            'message_id', 'conversation_id',
            'from_address', 'from_name', 'from_contact',
            'to_contacts', 'cc_contacts', 'bcc_contacts', 'reply_to_contacts',
            'subject',
            'short_summary', 'medium_summary',
            'body_text', 'body_html',
            'received_at', 'sent_at',
            'is_read', 'is_flagged', 'is_replied',
            'is_deleted_on_server', 'is_draft',
            'embedding_generated', 'ai_processed',
            'attachments', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'account', 'account_name',
            'message_id', 'conversation_id',
            'received_at',
            'sent_at',
            'from_address', 'from_name',
            'from_contact', 'to_contacts', 'cc_contacts', 'bcc_contacts', 'reply_to_contacts',
            'subject',
            'short_summary', 'medium_summary',
            'body_text', 'body_html',
            'is_read', 'is_flagged', 'is_replied',
            'is_deleted_on_server', 'is_draft',
            'embedding_generated', 'ai_processed',
            'attachments',
            'created_at', 'updated_at'
        ]

# Add the new lean serializer for list view
class EmailListSerializer(serializers.ModelSerializer):
    """Schlanker Serializer für die E-Mail-Listenansicht."""
    # from_contact = ContactSimpleSerializer(read_only=True) # Optional: Falls Name statt nur Adresse benötigt wird

    class Meta:
        model = Email
        fields = [
            'id',
            'subject',
            'short_summary',
            'from_address', # Direct email address from Email model
            'from_name',
            # 'from_contact', # Uncomment if Contact object (with name) is preferred
            'sent_at',
            'is_read',
            'is_flagged',
            'account', # Needed for frontend logic? Check if required.
        ]
        read_only_fields = fields # All fields are read-only in the list view

class AISuggestionSerializer(serializers.ModelSerializer):
    """Serializer für KI-Vorschläge."""
    
    email_subject = serializers.CharField(source='email.subject', read_only=True)
    
    class Meta:
        model = AISuggestion
        fields = [
            'id', 'email', 'email_subject', 'type',
            'title', 'content', 'suggested_subject',
            'metadata', 'status', 'user_feedback',
            'confidence_score', 'processing_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'email', 'type', 'title', 
            'metadata', 'confidence_score', 'processing_time',
            'created_at', 'updated_at'
        ]

    def update(self, instance, validated_data):
        from mailmind.core.models import AISuggestionEditHistory
        user = self.context['request'].user if 'request' in self.context else None
        # Prüfe Änderungen an content und suggested_subject
        for field in ['content', 'suggested_subject']:
            if field in validated_data:
                old_value = getattr(instance, field, None) or ''
                new_value = validated_data[field] or ''
                if old_value != new_value:
                    AISuggestionEditHistory.objects.create(
                        suggestion=instance,
                        field='body' if field == 'content' else 'subject',
                        old_value=old_value,
                        new_value=new_value,
                        edit_type='manual',
                        user=user
                    )
        return super().update(instance, validated_data)

class ContactSerializer(serializers.ModelSerializer):
    """Serializer für Kontakte."""
    
    class Meta:
        model = Contact
        fields = [
            'id', 'email', 'name',
            'organization', 'title',
            'last_interaction', 'interaction_count',
            'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'last_interaction', 'interaction_count',
            'created_at', 'updated_at'
        ]

class AIRequestLogSerializer(serializers.ModelSerializer):
    """Serializer für AI API Request Logs."""
    user_email = serializers.EmailField(source='user.email', read_only=True, allow_null=True)

    class Meta:
        model = AIRequestLog
        fields = [
            'id', 'user', 'user_email', 'timestamp', 'provider', 'model_name',
            'prompt_text', 'raw_response_text', 'status_code',
            'duration_ms', 'is_success', 'error_message', 'triggering_source'
        ]
        read_only_fields = fields # Alle Felder sind nur lesend

    def __init__(self, *args, **kwargs):
        # Import AIRequestLog locally if not already imported at the top level
        # to ensure it's available when the Meta class is processed.
        super().__init__(*args, **kwargs) 

# Neuer Serializer für die Ordnerstruktur
class FolderSerializer(serializers.Serializer):
    """Serializer für die Darstellung einer IMAP-Ordnerhierarchie."""
    name = serializers.CharField()
    full_path = serializers.CharField() # Eindeutiger Pfad/Name des Ordners
    delimiter = serializers.CharField()
    flags = serializers.ListField(child=serializers.CharField())
    # Rekursives Feld für Unterordner
    children = serializers.SerializerMethodField()

    def get_children(self, obj):
        # 'obj' ist hier ein Dictionary, das wir im View erstellen
        children_data = obj.get('children', [])
        # Ruft denselben Serializer für jedes Kind-Element auf
        return FolderSerializer(children_data, many=True, context=self.context).data


    # class Meta:
    #     # Da dies kein ModelSerializer ist, brauchen wir keine Meta-Klasse
    #     # Define fields if needed, but often inferred or explicitly defined
    #     fields = ['name', 'full_path', 'delimiter', 'flags', 'children']


    def __init__(self, *args, **kwargs):
        # Import AIRequestLog locally if not already imported at the top level
        # to ensure it's available when the Meta class is processed.
        # Remove this init if AIRequestLog is already imported globally
        # from mailmind.core.models import AIRequestLog 
        super().__init__(*args, **kwargs) 

class PromptTemplateSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromptTemplate
        fields = ["id", "name", "description"]

class AIActionSerializer(serializers.ModelSerializer):
    prompts = PromptTemplateSimpleSerializer(many=True, read_only=True)
    prompt_ids = serializers.PrimaryKeyRelatedField(
        queryset=PromptTemplate.objects.all(),
        many=True,
        write_only=True,
        source="prompts"
    )

    class Meta:
        model = AIAction
        fields = [
            "id", "name", "description", "is_active", "sort_order", "created_at", "updated_at", "prompts", "prompt_ids"
        ] 