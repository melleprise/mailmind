from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView, UserRegistrationView, EmailVerificationView, UserDetailView,
    EmailAccountTestConnectionView, SuggestEmailSettingsView, EmailViewSet, 
    EmailAccountViewSet, APICredentialViewSet, api_credential_check_view, 
    AvailableApiModelListView, AIRequestLogViewSet, SuggestFolderStructureView,
    ResendVerificationEmailView,
    CreateFoldersView,
    MarkEmailSpamView,
    internal_get_api_key_view
)
from knowledge.api.views import KnowledgeFieldViewSet

app_name = 'core'

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'emails', EmailViewSet, basename='email')
router.register(r'api-credentials', APICredentialViewSet, basename='api-credential')
router.register(r'email-accounts', EmailAccountViewSet, basename='email-account')
router.register(r'ai-request-logs', AIRequestLogViewSet, basename='ai-request-log')
router.register(r'knowledge-fields', KnowledgeFieldViewSet, basename='knowledgefield')

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('auth/register/', UserRegistrationView.as_view(), name='user_register'),
    path('auth/login/', LoginView.as_view(), name='user_login'),
    path('auth/verify-email/<str:token>/', EmailVerificationView.as_view(), name='email_verify'),
    path('auth/verify-email/', EmailVerificationView.as_view(), name='email_verify_post'),
    path('auth/resend-verification/', ResendVerificationEmailView.as_view(), name='resend_verification'),
    path('auth/user/', UserDetailView.as_view(), name='user_detail'),
    path('email-accounts/test-connection/', EmailAccountTestConnectionView.as_view(), name='test_connection'),
    path('email-accounts/suggest-settings/', SuggestEmailSettingsView.as_view(), name='suggest_settings'),
    path('api-credentials/check/<str:provider>/', api_credential_check_view, name='api_credential_check'),
    path('ai/available-models/<str:provider>/', AvailableApiModelListView.as_view(), name='available_models_list'),
    path('ai/suggest-folder-structure/', SuggestFolderStructureView.as_view(), name='suggest_folder_structure'),
    path('email-accounts/<int:account_id>/create-folders/', CreateFoldersView.as_view(), name='create_folders'),
    path('', include(router.urls)),
    path('emails/<int:pk>/mark-spam/', MarkEmailSpamView.as_view(), name='email-mark-spam'),
    path('internal/get-api-key/', internal_get_api_key_view, name='internal_get_api_key'),
] 