from rest_framework import serializers
from knowledge.models import KnowledgeField

class KnowledgeFieldSerializer(serializers.ModelSerializer):
    """Serializer for the KnowledgeField model."""
    # Make user read-only as it's set automatically based on the request user
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    # Add validation for key format (already handled by model validator, but good practice)
    key = serializers.CharField(max_length=100) # Add validators later if needed here
    
    class Meta:
        model = KnowledgeField
        fields = ['id', 'user', 'key', 'value', 'created_at', 'updated_at']
        read_only_fields = ['user', 'created_at', 'updated_at']

    def validate_key(self, value):
        """Perform DRF-level validation (supplements model validation)."""
        # Re-use model validation logic if possible, or add DRF specific checks
        from knowledge.models import validate_key_format
        try:
            validate_key_format(value)
        except serializers.ValidationError as e:
            raise serializers.ValidationError(str(e))
        return value
    
    def create(self, validated_data):
        """Associate the current user with the knowledge field upon creation."""
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data) 