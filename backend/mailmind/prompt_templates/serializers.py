from rest_framework import serializers
from .models import PromptTemplate
import logging # Import logging

logger = logging.getLogger(__name__) # Define logger

class PromptTemplateSerializer(serializers.ModelSerializer):
    """Serializer for the PromptTemplate model."""
    logger.debug("Initializing PromptTemplateSerializer...") # Log bei Initialisierung

    # Make provider choices readable in the API
    # ACHTUNG: Dieser Aufruf könnte fehlschlagen, wenn das Model/die Choices nicht verfügbar sind!
    try:
        provider = serializers.ChoiceField(choices=PromptTemplate.ProviderChoices.choices)
        logger.debug("PromptTemplateSerializer: Successfully set provider ChoiceField.")
    except Exception as e:
        logger.exception("PromptTemplateSerializer: Failed to set provider ChoiceField!")
        provider = serializers.CharField() # Fallback

    class Meta:
        model = PromptTemplate
        fields = [
            'id',        # Read-only
            'name',      # Read-only (lookup field)
            'description', # Writable
            'prompt',      # Writable (Corrected field name)
            'provider',    # Writable
            'model_name',  # Writable
            'created_at',  # Read-only
            'updated_at'   # Read-only
        ]
        # Explicitly define read_only_fields
        read_only_fields = ['id', 'name', 'created_at', 'updated_at']
        logger.debug(f"PromptTemplateSerializer Meta defined with fields: {fields}")
        # Make name read-only after creation? Maybe not needed for this use case.
        # read_only_fields = ['created_at', 'updated_at'] 

    # Explicitly override update to log validated data before saving
    def update(self, instance, validated_data):
        # Log the data that has passed validation and is about to be saved
        logger.debug(f"PromptTemplateSerializer attempting update for '{instance.name}'. Validated data: {validated_data}")
        try:
            # Call the original update method
            updated_instance = super().update(instance, validated_data)
            logger.info(f"PromptTemplateSerializer successfully updated instance '{instance.name}'.")
            return updated_instance
        except Exception as e:
            logger.exception(f"PromptTemplateSerializer error during super().update for '{instance.name}'.")
            raise # Re-raise the exception

    # Optional: Logging in to_representation
    # def to_representation(self, instance):
    #     logger.debug(f"Serializing PromptTemplate instance: {instance.name}")
    #     try:
    #         rep = super().to_representation(instance)
    #         logger.debug(f"Serialization successful for: {instance.name}")
    #         return rep
    #     except Exception as e:
    #         logger.exception(f"Error serializing PromptTemplate: {instance.name}")
    #         raise 