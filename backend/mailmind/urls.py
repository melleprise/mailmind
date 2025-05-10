from django.contrib import admin
from django.urls import path, include # re_path nicht mehr nötig
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
# Router wird jetzt in api/urls.py definiert
# from rest_framework.routers import SimpleRouter
# from mailmind.api.views import EmailAccountViewSet, EmailViewSet, ContactViewSet, AISuggestionViewSet, RefreshSuggestionsView, AIRequestLogViewSet

# Import nur noch für RefreshSuggestionsView (falls nicht in api/urls.py)
# from mailmind.api.views import RefreshSuggestionsView # Auskommentiert, da jetzt in config/urls oder api/urls

def home(request):
    return HttpResponse("MailMind API is running!")

# Router hier nicht mehr definieren
# router = SimpleRouter()
# router.register(r'email-accounts', EmailAccountViewSet, basename='emailaccount')
# router.register(r'emails', EmailViewSet, basename='email')
# router.register(r'contacts', ContactViewSet, basename='contact')
# router.register(r'ai-request-logs', AIRequestLogViewSet, basename='airequestlog')

# urlpatterns hier nicht mehr definieren, wird in config/urls.py gemacht
urlpatterns = [
    path('', home, name='home'), # Home view bleibt hier für den Root-Pfad
    # path('admin/', admin.site.urls), # Admin wird in config/urls eingebunden
    # Binde alle URLs aus mailmind.api.urls unter api/v1/ ein
    # path('api/v1/', include('mailmind.api.urls')), # Wird in config/urls gemacht
    # Entferne die separate AISuggestionViewSet-Pfade
    # path('api/v1/test-debug/', lambda request: HttpResponse("DEBUG ROUTE OK"), name='debug-test'),
    # path('api/v1/ai-suggestions/', AISuggestionViewSet.as_view(...)
    # re_path(r'^api/v1/ai-suggestions/(?P<pk>[a-f0-9\-]+)/$', ...)
    # re_path(r'^api/v1/ai-suggestions/(?P<pk>[a-f0-9\-]+)/correct-text/$', ...)

    # Andere spezifische Pfade (falls nicht in api/urls.py oder anderen Apps)
    # path('emails/<int:email_id>/refresh-suggestions/', RefreshSuggestionsView.as_view(), name='email-refresh-suggestions'), # Jetzt in api/urls.py

    # Binde andere App-URLs ein (falls nötig und nicht schon unter /api/v1/ durch mailmind.api.urls abgedeckt)
    # Diese könnten überflüssig sein, wenn api/urls.py sie bereits enthält
    # path('api/v1/imap/', include('mailmind.imap.urls')),
    # path('api/v1/users/', include('mailmind.users.urls')),
    # path('api/v1/core/', include('mailmind.core.urls')),
    # path('api/v1/prompts/', include('mailmind.prompt_templates.urls')),
]
# Static/Media werden in config/urls behandelt
# ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)