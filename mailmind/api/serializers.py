from rest_framework import serializers

class RefineReplySerializer(serializers.Serializer):
    custom_prompt = serializers.CharField()
    current_subject = serializers.CharField(allow_blank=True)
    current_body = serializers.CharField(allow_blank=True)

    def update(self, instance, validated_data):
        pass # Nicht benötigt für diesen Serializer
        
    def create(self, validated_data):
        pass # Nicht benötigt für diesen Serializer

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'
        read_only_fields = ('id', 'email_account', 'name', 'flags', 'total_messages', 'unread_messages', 'last_synced') 