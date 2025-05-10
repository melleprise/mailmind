from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PromptTemplateViewSet

app_name = "prompt_templates"

router = DefaultRouter()
router.register(r"templates", PromptTemplateViewSet, basename="prompttemplate")

urlpatterns = [
    path("", include(router.urls)),
] 