from django.urls import path
from .views import EmailRefreshSuggestionsView, SuggestionListView, SuggestionDetailView, SuggestionCorrectTextView, SuggestionRefineView, EmailRefineReplyView

urlpatterns = [
    path('emails/<int:email_id>/refresh-suggestions/', EmailRefreshSuggestionsView.as_view(), name='email-refresh-suggestions'),
    # --- Suggestions Endpoints ---
    path('suggestions/', SuggestionListView.as_view(), name='suggestion-list'),
    path('suggestions/<uuid:pk>/', SuggestionDetailView.as_view(), name='suggestion-detail'),
    path('suggestions/<uuid:pk>/correct-text/', SuggestionCorrectTextView.as_view(), name='suggestion-correct-text'),
    path('suggestions/<uuid:pk>/refine/', SuggestionRefineView.as_view(), name='suggestion-refine'), # Behalten falls noch anderweitig genutzt?
    # --- NEU: Endpoint zum Verfeinern des aktuellen Reply-Entwurfs --- 
    path('emails/<int:email_pk>/refine-reply/', EmailRefineReplyView.as_view(), name='email-refine-reply'),
]

# Include DRF browsable API URLs if DEBUG is True 