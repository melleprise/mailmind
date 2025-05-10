from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import KnowledgeFieldViewSet

router = DefaultRouter()
router.register(r'knowledge-fields', KnowledgeFieldViewSet, basename='knowledgefield')

urlpatterns = [
    path('', include(router.urls)),
] 