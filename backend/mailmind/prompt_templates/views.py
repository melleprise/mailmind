from django.shortcuts import render
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from .models import PromptTemplate
from .serializers import PromptTemplateSerializer
import logging # Logging importieren
from django.core.cache import cache # Cache importieren

logger = logging.getLogger(__name__) # Logger definieren

# Create your views here.

class PromptTemplateViewSet(viewsets.ModelViewSet):
    """API endpoint that allows prompt templates to be viewed or edited."""
    queryset = PromptTemplate.objects.all().order_by('name')
    serializer_class = PromptTemplateSerializer
    # Allow any authenticated user
    permission_classes = [permissions.IsAuthenticated]
    # Use name (slug) as the lookup field in the URL instead of ID
    lookup_field = 'name'
    # Optional: Add pagination, filtering, etc. later if needed
    # pagination_class = ...
    # filter_backends = [...] 
    # filterset_fields = [...] 

    # Überschreibe list für besseres Logging
    def list(self, request, *args, **kwargs):
        logger.info(f"PromptTemplateViewSet: Received list request from user {request.user.id}")
        try:
            queryset = self.filter_queryset(self.get_queryset())
            logger.debug(f"PromptTemplateViewSet: Found {queryset.count()} templates.")

            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                logger.debug("PromptTemplateViewSet: Paginated response prepared.")
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(queryset, many=True)
            logger.info("PromptTemplateViewSet: Successfully serialized templates.")
            # Logging direkt vor der Response
            logger.debug(f"PromptTemplateViewSet: Attempting to return response with data: {serializer.data}")
            return Response(serializer.data)
        except Exception as e:
            logger.exception("PromptTemplateViewSet: An unexpected error occurred during list!")
            return Response({"detail": "An internal server error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Logging für andere Aktionen (retrieve, update, etc.) kann bei Bedarf ähnlich hinzugefügt werden
    # Beispiel für retrieve:
    def retrieve(self, request, *args, **kwargs):
        logger.info(f"PromptTemplateViewSet: Received retrieve request for name '{kwargs.get('name')}' from user {request.user.id}")
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            logger.info(f"PromptTemplateViewSet: Successfully retrieved template '{instance.name}'.")
            return Response(serializer.data)
        except Exception as e:
            logger.exception(f"PromptTemplateViewSet: An unexpected error occurred during retrieve for name '{kwargs.get('name')}'!")
            return Response({"detail": "An internal server error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Überschreibe partial_update, um Cache zu löschen
    def partial_update(self, request, *args, **kwargs):
        template_name = kwargs.get(self.lookup_field)
        logger.info(f"PromptTemplateViewSet: Received partial_update request for name '{template_name}' from user {request.user.id}")
        try:
            # Rufe die ursprüngliche Methode auf, um das Objekt zu speichern
            response = super().partial_update(request, *args, **kwargs)

            # Lösche den Cache-Eintrag NACH erfolgreichem Speichern
            if response.status_code >= 200 and response.status_code < 300:
                cache_key = f"prompt_{template_name}_details"
                cache.delete(cache_key)
                logger.info(f"PromptTemplateViewSet: Cache invalidated for '{cache_key}' after successful update.")
            else:
                 logger.warning(f"PromptTemplateViewSet: Update for '{template_name}' did not succeed (Status: {response.status_code}). Cache NOT invalidated.")

            logger.info(f"PromptTemplateViewSet: Successfully processed partial_update for template '{template_name}'. Status: {response.status_code}")
            return response
        except Exception as e:
            logger.exception(f"PromptTemplateViewSet: An unexpected error occurred during partial_update for name '{template_name}'!")
            return Response({"detail": "An internal server error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Die Methode 'update' (für PUT) sollte ebenfalls angepasst werden, falls sie verwendet wird.
    def update(self, request, *args, **kwargs):
        template_name = kwargs.get(self.lookup_field)
        logger.info(f"PromptTemplateViewSet: Received update (PUT) request for name '{template_name}' from user {request.user.id}")
        try:
            response = super().update(request, *args, **kwargs)
            if response.status_code >= 200 and response.status_code < 300:
                cache_key = f"prompt_{template_name}_details"
                cache.delete(cache_key)
                logger.info(f"PromptTemplateViewSet: Cache invalidated for '{cache_key}' after successful PUT update.")
            else:
                 logger.warning(f"PromptTemplateViewSet: PUT Update for '{template_name}' did not succeed (Status: {response.status_code}). Cache NOT invalidated.")
            logger.info(f"PromptTemplateViewSet: Successfully processed update (PUT) for template '{template_name}'. Status: {response.status_code}")
            return response
        except Exception as e:
            logger.exception(f"PromptTemplateViewSet: An unexpected error occurred during update (PUT) for name '{template_name}'!")
            return Response({"detail": "An internal server error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='providers')
    def list_providers(self, request):
        """Returns a list of available AI providers and their models."""
        # Assuming PROVIDER_CHOICES and MODEL_CHOICES (or similar structure)
        # are defined in settings or a central config.
        # For now, hardcode or read from settings if available.

        # Example structure based on PROVIDER_CHOICES in models.py
        available_providers = []
        # Fetch provider choices from model
        provider_choices = PromptTemplate.PROVIDER_CHOICES

        # Fetch models configured in settings (example structure)
        # This is a placeholder; you might need to adjust based on actual settings structure
        configured_models = getattr(settings, 'AI_CONFIGURED_MODELS', {})

        for code, name in provider_choices:
            provider_data = {
                'code': code,
                'name': name,
                'models': configured_models.get(code, []) # Get models configured for this provider
            }
            available_providers.append(provider_data)

        return Response(available_providers)
