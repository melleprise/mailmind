from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import RefreshSuggestionsView, AIActionViewSet, AISuggestionViewSet, RefineTextView, DraftViewSet
from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError

# app_name = "api" # Removed to avoid potential conflicts

router = DefaultRouter()
router.register(r'email-accounts', views.EmailAccountViewSet, basename='emailaccount')
router.register(r'emails', views.EmailViewSet, basename='email')
router.register(r'suggestions', AISuggestionViewSet, basename='suggestion')
router.register(r'contacts', views.ContactViewSet, basename='contact')
router.register(r'log', views.AIRequestLogViewSet, basename='airequestlog')
router.register(r'actions', AIActionViewSet, basename='aiaction')
router.register(r'drafts', DraftViewSet, basename='draft')

def health_check(request):
    try:
        db_conn = connections['default']
        db_conn.cursor()
        return JsonResponse({"status": "ok"})
    except OperationalError:
        return JsonResponse({"status": "error", "detail": "DB not available"}, status=500)

urlpatterns = [
    path('', include(router.urls)),
    path('emails/<int:email_id>/refresh-suggestions/', RefreshSuggestionsView.as_view(), name='email-refresh-suggestions'),
    path('ai/refine-text/', RefineTextView.as_view(), name='ai-refine-text'),
    path('health', health_check, name='health'),
] 