from rest_framework import serializers
from django.contrib.auth.models import User
from .models import EmailAccount, Email, Folder, APICredential, AIRequestLog # Add AIRequestLog
from django.conf import settings

class APICredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = APICredential
        fields = ['id', 'user', 'provider', 'api_key']
        read_only_fields = ['user']

    def validate_provider(self, value):
        valid_providers = [p['id'] for p in settings.SUPPORTED_AI_PROVIDERS]
        if value not in valid_providers:
            raise serializers.ValidationError(f"Invalid provider. Must be one of {valid_providers}")
        return value

# New Serializer for AIRequestLog
class AIRequestLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIRequestLog
        fields = [
            'id',
            'timestamp',
            'action_name',
            'provider',
            'model',
            'prompt_tokens',
            'completion_tokens',
            'status_code',
            'success',
            'response_time_ms',
            'user_id' # Keep it simple, just the ID
        ]
        read_only_fields = fields # Logs should be read-only via API 