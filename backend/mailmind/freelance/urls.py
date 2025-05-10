from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FreelanceProjectViewSet, FreelanceProviderCredentialViewSet, crawl_projects

router = DefaultRouter()
router.register(r'projects', FreelanceProjectViewSet, basename='freelance-projects')

# Registriere ViewSet mit expliziten Methoden
credentials_list = FreelanceProviderCredentialViewSet.as_view({
    'get': 'list',      # Für /api/freelance/credentials/ (zeigt Credentials des request.user)
    'post': 'create',   # Für /api/freelance/credentials/
})

# Eigene View für Update und Delete, die auf request.user basiert
#credentials_self_detail = FreelanceProviderCredentialViewSet.as_view({
#    'put': 'update',    # Für /api/freelance/credentials/me/ (oder ähnlich, zur Bearbeitung eigener Credentials)
#    'delete': 'destroy' # Für /api/freelance/credentials/me/
#})

# View für den Abruf durch interne Dienste oder Admins anhand der User-ID in der URL
credentials_detail_by_userid = FreelanceProviderCredentialViewSet.as_view({
    'get': 'retrieve', # Für /api/freelance/credentials/<user_id>/
})

credentials_validate = FreelanceProviderCredentialViewSet.as_view({
    'post': 'validate',
})

urlpatterns = [
    path('', include(router.urls)),
    path('credentials/', credentials_list, name='freelance-credentials-list-create'),
    # Ein neuer Endpunkt für crawl4ai, um Credentials per User-ID abzurufen:
    path('credentials/<int:user_id>/', credentials_detail_by_userid, name='freelance-credentials-detail-by-userid'),
    path('credentials/validate/', credentials_validate, name='freelance-credentials-validate'),
    # path('credentials/me/', credentials_self_detail, name='freelance-credentials-self-detail'), # Optional für Frontend
    path('crawl/', crawl_projects, name='freelance-crawl'),
] 