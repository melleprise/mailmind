import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from django.conf import settings
from collections import defaultdict
from mailmind.core.models import AvailableApiModel # Import the model
from mailmind.core.models import AISuggestion # Import AISuggestion model
from mailmind.core.serializers import AISuggestionSerializer # Import AISuggestionSerializer from core app
from rest_framework import viewsets # Import viewsets
from rest_framework.decorators import action # Import action decorator
from .tasks import correct_text_with_ai # Import correction task
from django.db.models.functions import Now # Import Now function
from django.db.models.expressions import F # Import F expression
from django.db.models import Q # Import Q object for complex queries
from django.db.models.fields.json import JSONField # Import JSONField for JSON fields
from .generate_suggestion_task import generate_ai_suggestion
from .summary_tasks import generate_summary_task # Import the new summary task
from mailmind.core.models import Email # Ensure Email is imported

logger = logging.getLogger(__name__)

# Example structure for defining providers and models
# This could be moved to settings or a database model later
# Make sure model names match those expected by the client libraries/API calls
AVAILABLE_PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "models": [
            {"id": "gemini-1.5-flash-latest", "name": "Gemini 1.5 Flash (Latest)"},
            {"id": "gemini-1.5-pro-latest", "name": "Gemini 1.5 Pro (Latest)"},
            {"id": "gemini-1.0-pro", "name": "Gemini 1.0 Pro"},
            # Add other relevant Gemini models
        ],
    },
    "openai": {
        "name": "OpenAI",
        "models": [
            {"id": "gpt-4o", "name": "GPT-4o"},
            {"id": "gpt-4-turbo", "name": "GPT-4 Turbo"},
            {"id": "gpt-3.5-turbo", "name": "GPT-3.5 Turbo"},
        ],
    },
    "anthropic": {
        "name": "Anthropic Claude",
        "models": [
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus"},
            {"id": "claude-3-sonnet-20240229", "name": "Claude 3 Sonnet"},
            {"id": "claude-3-haiku-20240307", "name": "Claude 3 Haiku"},
        ],
    },
    # Add other configured providers here
}

class AIProviderListView(APIView):
    """
    API view to list available AI providers and their discovered models.
    Requires authentication.
    """
    permission_classes = [permissions.IsAuthenticated] # Changed from IsAdminUser

    def get(self, request, *args, **kwargs):
        """Returns the list of available providers and models from the database."""
        logger.info(f"AIProviderListView: Received GET request from user {request.user.id}")
        try:
            # Fetch distinct providers and their models from AvailableApiModel
            logger.debug("AIProviderListView: Fetching models from DB...")
            models_queryset = AvailableApiModel.objects.order_by('provider', 'model_id').values('provider', 'model_id')
            logger.debug(f"AIProviderListView: Found {models_queryset.count()} model entries.")

            # Group models by provider
            provider_models = defaultdict(list)
            for item in models_queryset:
                provider_models[item['provider']].append(item['model_id'])
            logger.debug(f"AIProviderListView: Grouped models: {dict(provider_models)}")

            # Format the output
            output_data = [
                {
                    "provider": provider,
                    "models": models
                }
                for provider, models in provider_models.items()
            ]
            logger.info(f"AIProviderListView: Successfully formatted provider data. Count: {len(output_data)}")

            if not output_data:
                logger.warning(f"AIProviderListView: No available AI models found in the database for user {request.user.id}")
                # Return empty list as per standard
            
            # Logging direkt vor der Response
            logger.debug(f"AIProviderListView: Attempting to return response with data: {output_data}")
            return Response(output_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception("AIProviderListView: An unexpected error occurred!") # Loggt den Traceback
            # Gebe einen generischen Fehler zurück, um keine Details preiszugeben
            return Response({"detail": "An internal server error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# NEU: ViewSet für AI Suggestions
class AISuggestionViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and managing AI suggestions.
    Allows partial updates (PATCH) for content/subject.
    """
    serializer_class = AISuggestionSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options'] # Erlaube nur GET, PATCH, DELETE
    lookup_field = 'pk' # Standardmäßig PK, aber UUID wird verwendet, das passt

    def get_queryset(self):
        """Ensure users only see suggestions related to their emails."""
        # Annahme: AISuggestion hat ein ForeignKey 'email', und Email hat ein ForeignKey 'account',
        # und EmailAccount hat ein ForeignKey 'user'.
        user = self.request.user
        return AISuggestion.objects.filter(email__account__user=user)

    # Optional: Implementiere perform_update oder perform_destroy, falls spezielle Logik nötig ist.
    # Beispiel: Nur bestimmte Felder erlauben
    def partial_update(self, request, *args, **kwargs):
        logger.debug(f"AISuggestionViewSet: Received PATCH request for suggestion {kwargs.get('pk')} with data: {request.data}")
        # Stelle sicher, dass nur erlaubte Felder aktualisiert werden können (z.B. content, suggested_subject)
        allowed_fields = {'content', 'suggested_subject'}
        if not set(request.data.keys()).issubset(allowed_fields):
             logger.warning(f"AISuggestionViewSet: Attempt to update disallowed fields: {set(request.data.keys()) - allowed_fields}")
             return Response({'error': 'Only content and suggested_subject can be updated.'}, status=status.HTTP_400_BAD_REQUEST)
        
        return super().partial_update(request, *args, **kwargs) 

    def trigger_generation(self, request, *args, **kwargs):
        email_id = kwargs.get('pk')
        email = self.get_object()
        serializer = self.get_serializer(email)
        try:
            logger.info(f"Triggering AI suggestion generation for email {email_id} by user {request.user.id}")
            generate_ai_suggestion.delay(email.id, request.user.id)
            # logger.info(f"Triggering AI summary generation for email {email_id} by user {request.user.id}")
            # generate_summary_task.delay(email.id, request.user.id) # Entfernt: Summary-Task wird nicht mehr automatisch getriggert

            # Mark as processing initiated (optional, could also be done within the task)
            # email.ai_processing_triggered = True

            return Response({"detail": "AI generation triggered successfully."}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception("An error occurred while triggering AI generation.")
            return Response({"detail": "An error occurred while triggering AI generation."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)