from .views import (
    # ... other views ...
    EmailViewSet,
    SuggestFolderStructureView,
    AIRequestLogListView,
    CheckApiKeysView,
)

urlpatterns = [
    # ... other urls ...
    path('core/ai/suggest-folder-structure/', SuggestFolderStructureView.as_view(), name='suggest_folder_structure'),
    path('core/ai/request-logs/', AIRequestLogListView.as_view(), name='ai_request_logs'),
    path('core/ai/check-api-keys/', CheckApiKeysView.as_view(), name='check_api_keys'),
    path('core/emails/<int:pk>/process-ai/', ProcessAIEmailView.as_view(), name='process_ai_email'),
    # ... other urls ...
] 