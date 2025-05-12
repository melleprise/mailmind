from rest_framework import serializers
from .models import FreelanceProject, FreelanceProviderCredential


class FreelanceProjectSerializer(serializers.ModelSerializer):
    """Serializer für FreelanceProject model."""
    
    description = serializers.CharField(default="")
    application_status = serializers.CharField(allow_null=True, required=False)
    
    class Meta:
        model = FreelanceProject
        fields = ['id', 'project_id', 'title', 'company', 'end_date', 'location', 'remote', 'last_updated', 'skills', 'url', 'applications', 'description', 'provider', 'created_at', 'application_status']

class FreelanceProviderCredentialSerializer(serializers.ModelSerializer):
    """Serializer für FreelanceProviderCredential model."""
    
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, style={'input_type': 'password'})
    link_1 = serializers.SerializerMethodField()
    
    class Meta:
        model = FreelanceProviderCredential
        fields = ['id', 'username', 'password', 'link', 'link_1', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        
    def get_link_1(self, obj):
        return obj.link
        
    def create(self, validated_data):
        user = self.context['request'].user
        password = validated_data.pop('password')
        
        credential = FreelanceProviderCredential.objects.create(
            user=user,
            **validated_data
        )
        credential.set_password(password)
        credential.save()
        return credential
        
    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
            
        if password is not None and password != '':
            instance.set_password(password)
        
        instance.save()
        return instance 