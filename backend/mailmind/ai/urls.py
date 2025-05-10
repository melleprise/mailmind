from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AIProviderListView, AISuggestionViewSet

app_name = "ai"

# Router erstellen und ViewSet registrieren
router = DefaultRouter()
router.register(r'suggestions', AISuggestionViewSet, basename='ai-suggestion')

urlpatterns = [
    path("providers/", AIProviderListView.as_view(), name="provider-list"),
    # Add other AI-related API endpoints here if needed
    path("", include(router.urls)),
] 