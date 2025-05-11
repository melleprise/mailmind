from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import FreelanceProjectViewSet, FreelanceProviderCredentialViewSet, crawl_projects

router = DefaultRouter()
router.register(r'projects', FreelanceProjectViewSet, basename='freelance-projects')

# Registriere ViewSet für LIST (GET) und CREATE (POST) auf /api/freelance/credentials/
credentials_list_create = FreelanceProviderCredentialViewSet.as_view({
    'get': 'list',
    'post': 'create'
})

# Eigene View für UPDATE (PUT) und DELETE auf /api/freelance/credentials/me/
# Diese Aktionen beziehen sich immer auf den request.user.
credentials_self_manage = FreelanceProviderCredentialViewSet.as_view({
    'get': 'list', # Kann hier auch list sein, um eigene Daten abzurufen, alternativ eine eigene 'retrieve_self' action
    'put': 'update',
    'delete': 'destroy'
})

# View für den Abruf durch interne Dienste oder Admins anhand der User-ID in der URL
credentials_detail_by_userid = FreelanceProviderCredentialViewSet.as_view({
    'get': 'retrieve', # Für /api/freelance/credentials/<user_id>/
})

credentials_validate = FreelanceProviderCredentialViewSet.as_view({
    'post': 'validate',
})

urlpatterns = [
    path('', include(router.urls)),
    # URLs für den authentifizierten User (Management der eigenen Credentials)
    path('credentials/me/', credentials_self_manage, name='freelance-credentials-self-manage'),
    # URLs für das Auflisten (GET) und Erstellen (POST) von Credentials (allgemein, aber auf request.user bezogen)
    # Beachte: PUT und DELETE wurden hier entfernt und auf /me/ verschoben
    path('credentials/', credentials_list_create, name='freelance-credentials-list-create'),
    # Ein neuer Endpunkt für crawl4ai, um Credentials per User-ID abzurufen:
    path('credentials/<int:user_id>/', credentials_detail_by_userid, name='freelance-credentials-detail-by-userid'),
    path('credentials/validate/', credentials_validate, name='freelance-credentials-validate'),
    path('crawl/', crawl_projects, name='freelance-crawl'),
] 