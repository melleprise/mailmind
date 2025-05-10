from django.conf import settings
from django.urls import path, include # Added include
from rest_framework.routers import DefaultRouter, SimpleRouter

# Imports from your apps' API views
# Assuming you have viewsets in these locations
from mailmind.core.api.views import UserViewSet # Example
from mailmind.prompt_templates.api.views import PromptTemplateViewSet # Example
# Import the new ViewSet
from knowledge.api.views import KnowledgeFieldViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

# Register your ViewSets here
router.register("users", UserViewSet, basename="user") # Example basename
router.register("prompt-templates", PromptTemplateViewSet, basename="prompttemplate") # Example
# Register the new KnowledgeFieldViewSet
router.register("knowledge-fields", KnowledgeFieldViewSet, basename="knowledgefield")


app_name = "api"
urlpatterns = [
    # Include the router's URLs under the main path
    path("", include(router.urls)),
    # Add other specific API paths if needed
    # e.g., path('auth/', include('djoser.urls.authtoken')),
] 