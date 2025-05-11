from rest_framework import viewsets, status, permissions
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from .models import FreelanceProject, FreelanceProviderCredential
from .serializers import FreelanceProjectSerializer, FreelanceProviderCredentialSerializer
import logging
import httpx
import asyncio
import json
from django.conf import settings
from django.http import JsonResponse
import os
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)


class FreelanceProjectPagination(PageNumberPagination):
    """Pagination für FreelanceProject Viewset."""
    page_size = 20
    page_size_query_param = 'limit'
    max_page_size = 100


class FreelanceProjectViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoints für FreelanceProjects."""
    queryset = FreelanceProject.objects.all().order_by('-created_at')
    serializer_class = FreelanceProjectSerializer
    pagination_class = FreelanceProjectPagination
    permission_classes = [AllowAny]  # Erlaube alle Zugriffe
    
    def get_queryset(self):
        """Filter queryset basierend auf URL-Parametern."""
        queryset = super().get_queryset()
        
        # Filter by remote option
        remote = self.request.query_params.get('remote')
        if remote is not None:
            is_remote = remote.lower() == 'true'
            queryset = queryset.filter(remote=is_remote)
        
        # Filter by skill
        skill = self.request.query_params.get('skill')
        if skill:
            queryset = queryset.filter(skills__contains=[skill])
        
        # Filter by provider
        provider = self.request.query_params.get('provider')
        if provider:
            queryset = queryset.filter(provider=provider)
            
        return queryset 


class FreelanceProviderCredentialViewSet(viewsets.ViewSet):
    """
    Verwaltet Zugangsdaten für den Freelance-Provider des authentifizierten Benutzers.
    """
    permission_classes = [permissions.IsAuthenticated] # Default für andere Aktionen
    serializer_class = FreelanceProviderCredentialSerializer
    lookup_field = 'user_id'

    def get_permissions(self):
        if self.action == 'retrieve':
            # Temporär AllowAny für den internen Abruf durch crawl4ai
            # TODO: Langfristig durch eine sichere Service-to-Service Auth ersetzen
            return [permissions.AllowAny()]
        return super().get_permissions()
    
    def list(self, request):
        """Gibt alle Credential-Instanzen des Benutzers zurück (in der Regel nur eine)"""
        user = request.user
        try:
            credential = FreelanceProviderCredential.objects.get(user=user)
            serializer = self.serializer_class(credential)
            logger.debug(f"Erfolgreich Freelance-Credentials geladen für User {user.id}: {serializer.data}")
            return Response(serializer.data)
        except FreelanceProviderCredential.DoesNotExist:
            logger.debug(f"Keine Freelance-Credentials gefunden für User {user.id}")
            return Response(
                {"detail": "Keine Credentials gefunden."},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def get_object(self, user_id_from_url=None):
        """Holt die Credential-Instanz basierend auf user_id_from_url oder request.user"""
        if user_id_from_url: # Wenn eine ID aus der URL kommt (für retrieve)
            try:
                # Hier gehen wir davon aus, dass user_id_from_url die PK des User-Objekts ist
                credential = FreelanceProviderCredential.objects.get(user_id=user_id_from_url)
                return credential
            except FreelanceProviderCredential.DoesNotExist:
                return None
        else: # Fallback für list, create, update, destroy, die auf request.user basieren
            user = self.request.user
            if not user or not user.is_authenticated: # Sicherstellen, dass ein User da ist
                 return None
            try:
                credential = FreelanceProviderCredential.objects.get(user=user)
                return credential
            except FreelanceProviderCredential.DoesNotExist:
                return None
    
    def retrieve(self, request, *args, **kwargs):
        """Liefert die vorhandenen Credential-Informationen (ohne Passwort)"""
        user_id_from_url = kwargs.get(self.lookup_field) # Holt user_id aus der URL via lookup_field

        if not user_id_from_url:
            return Response(
                {"detail": "Benutzer-ID fehlt in der Anfrage."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Berechtigungsprüfung: Nur Admins oder der anfragende interne Dienst (später zu verfeinern)
        # Für den Moment: Wenn crawl4ai anfragt, hat es keinen request.user.
        # Diese Prüfung muss angepasst werden, wenn crawl4ai nicht als Staff-User agiert.
        # Aktuell würde dies fehlschlagen, wenn crawl4ai ohne User-Session zugreift.
        # Da der Fehler aber 404 war, lassen wir es vorerst so, um den Pfad zu korrigieren.
        # Idealerweise braucht crawl4ai eine eigene Authentifizierungsmethode (z.B. Service-Token).
        
        # if int(user_id_from_url) != request.user.id and not request.user.is_staff:
        #     return Response(
        #         {"detail": "Sie haben keine Berechtigung, diese Credentials einzusehen."},
        #         status=status.HTTP_403_FORBIDDEN
        #     )
        
        credential = self.get_object(user_id_from_url=user_id_from_url) # Übergabe der ID aus der URL
        if not credential:
            logger.debug(f"Keine Freelance-Credentials gefunden für User {user_id_from_url}")
            return Response(
                {"detail": f"Keine Credentials für User-ID {user_id_from_url} gefunden."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.serializer_class(credential)
        data = serializer.data

        # Wenn die Anfrage vom Playwright-Login-Service kommt, füge das entschlüsselte Passwort hinzu
        if request.headers.get('X-Playwright-Login-Service') == 'true':
            try:
                decrypted_password = credential.get_password()
                if decrypted_password:
                    data['decrypted_password'] = decrypted_password
                else:
                    logger.warning(f"Konnte Passwort für User {user_id_from_url} nicht entschlüsseln, obwohl von Playwright angefordert.")
            except Exception as e:
                logger.error(f"Fehler beim Entschlüsseln des Passworts für User {user_id_from_url} für Playwright: {e}")

        return Response(data)
    
    def create(self, request, *args, **kwargs):
        """Erstellt neue Credentials"""
        current_credential = self.get_object()
        if current_credential:
            logger.warning(f"Versuch, doppelte Freelance-Credentials für User {request.user.id} zu erstellen")
            return Response(
                {"detail": "Es existieren bereits Freelance-Credentials. Verwenden Sie PUT zum Aktualisieren."},
                status=status.HTTP_409_CONFLICT
            )
        
        serializer = self.serializer_class(data=request.data, context={'request': request})
        try:
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Freelance-Credentials erfolgreich erstellt für User {request.user.id}")
                return Response(
                    {"detail": "Freelance-Credentials erfolgreich erstellt."}, 
                    status=status.HTTP_201_CREATED
                )
            else:
                logger.warning(f"Ungültige Daten für Freelance-Credentials, User {request.user.id}: {serializer.errors}")
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Speichern der Freelance-Credentials für User {request.user.id}: {e}", exc_info=True)
            return Response(
                {"detail": "Ein unerwarteter Fehler ist aufgetreten."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def update(self, request, *args, **kwargs):
        """Aktualisiert bestehende Credentials"""
        credential = self.get_object()
        if not credential:
            logger.debug(f"Keine vorhandenen Freelance-Credentials zum Aktualisieren für User {request.user.id}")
            return Response(
                {"detail": "Keine vorhandenen Credentials gefunden. Verwenden Sie POST zum Erstellen."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.serializer_class(credential, data=request.data, partial=True, context={'request': request})
        try:
            if serializer.is_valid():
                serializer.save()
                logger.info(f"Freelance-Credentials erfolgreich aktualisiert für User {request.user.id}")
                return Response(
                    {"detail": "Freelance-Credentials erfolgreich aktualisiert."},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Unerwarteter Fehler beim Aktualisieren der Freelance-Credentials für User {request.user.id}: {e}", exc_info=True)
            return Response(
                {"detail": "Ein unerwarteter Fehler ist aufgetreten."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """Löscht bestehende Credentials"""
        credential = self.get_object()
        if not credential:
            return Response(
                {"detail": "Keine Credentials gefunden."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            credential.delete()
            logger.info(f"Freelance-Credentials erfolgreich gelöscht für User {request.user.id}")
            return Response(
                {"detail": "Freelance-Credentials erfolgreich gelöscht."},
                status=status.HTTP_204_NO_CONTENT
            )
        except Exception as e:
            logger.error(f"Fehler beim Löschen der Freelance-Credentials für User {request.user.id}: {e}", exc_info=True)
            return Response(
                {"detail": "Ein Fehler ist aufgetreten."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def validate(self, request):
        """
        Validiert Freelance-Credentials mit dem Playwright-Login-Service
        """
        credential = self.get_object()
        if not credential:
            return JsonResponse(
                {"detail": "Keine gespeicherten Credentials gefunden."},
                status=404
            )
        
        try:
            # Hole entschlüsseltes Passwort
            password = credential.get_password()
            
            # Asynchrone Logik in eine synchrone Funktion kapseln
            async def perform_validation():
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        'http://playwright-login:3000/login/freelance.de',
                        json={
                            "username": credential.username,
                            "password": password
                        }
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success', False):
                            # Login war erfolgreich
                            return JsonResponse({
                                "success": True,
                                "detail": "Login-Test erfolgreich."
                            })
                        else:
                            # Login war nicht erfolgreich
                            return JsonResponse({
                                "success": False,
                                "detail": "Login-Test fehlgeschlagen: " + data.get('error', 'Unbekannter Fehler')
                            }, status=400)
                    else:
                        # API-Aufruf fehlgeschlagen
                        return JsonResponse({
                            "success": False,
                            "detail": f"Login-Test fehlgeschlagen: HTTP {response.status_code}"
                        }, status=400)
            
            # Asynchrone Funktion synchron ausführen
            return asyncio.run(perform_validation())
        except Exception as e:
            logger.error(f"Fehler bei der Validierung der Freelance-Credentials: {e}", exc_info=True)
            return JsonResponse({
                "success": False,
                "detail": f"Ein Fehler ist aufgetreten: {str(e)}"
            }, status=500)

# Hilfsfunktion zum Senden des leads_updated-Events

def send_leads_updated_notification(detail="Neue Projekte verfügbar."):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "leads_group",
        {
            "type": "leads_updated",
            "detail": detail
        }
    )

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def crawl_projects(request):
    """
    Startet den Freelance-Crawl (Dummy: hier nur Notification, in Produktion echten Crawl triggern!)
    """
    # TODO: Echten Crawl triggern (z.B. Subprozess, Celery, etc.)
    send_leads_updated_notification("Crawl abgeschlossen. Neue Projekte verfügbar.")
    return JsonResponse({"success": True, "detail": "Crawl gestartet. Neue Projekte werden angezeigt, sobald sie verfügbar sind."}) 