from rest_framework import serializers
from .models import FreelanceProject, FreelanceProviderCredential


class FreelanceProjectSerializer(serializers.ModelSerializer):
    """Serializer für FreelanceProject model."""
    
    description = serializers.CharField(default="")
    
    class Meta:
        model = FreelanceProject
        fields = '__all__' 

class FreelanceProviderCredentialSerializer(serializers.ModelSerializer):
    """Serializer für FreelanceProviderCredential model."""
    
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, style={'input_type': 'password'})
    
    class Meta:
        model = FreelanceProviderCredential
        fields = ['id', 'username', 'password', 'link_1', 'link_2', 'link_3', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
        
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