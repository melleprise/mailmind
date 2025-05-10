import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from mailmind.core.models import AISuggestion
from mailmind.api.serializers import AISuggestionSerializer

logger = logging.getLogger(__name__)

class SuggestionConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]

        if not self.user or not self.user.is_authenticated:
            logger.warning("WebSocket connection attempt by unauthenticated user.")
            await self.close()
            return

        self.user_group_name = f'user_{self.user.id}'

        # Join user group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"WebSocket connected for user {self.user.id}. Added to group {self.user_group_name}")

    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            logger.info(f"WebSocket disconnected for user {getattr(self.user, 'id', 'unknown')}. Removing from group {self.user_group_name}")
            # Leave user group
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
        else:
             logger.info("WebSocket disconnected for unauthenticated or partially connected user.")

    # Receive message from WebSocket (We don't expect messages from client in this simple case)
    async def receive(self, text_data):
        logger.debug(f"Received message from WebSocket (User {getattr(self.user, 'id', 'unknown')}): {text_data}")
        # We can ignore messages from the client for now
        pass

    @database_sync_to_async
    def _get_suggestions_from_db(self, email_id):
        """Helper function to query suggestions from DB asynchronously."""
        try:
            suggestions = AISuggestion.objects.filter(email_id=email_id).order_by('created_at')
            serializer = AISuggestionSerializer(suggestions, many=True)
            logger.debug(f"Fetched and serialized {len(serializer.data)} suggestions for email {email_id} in consumer helper.")
            return serializer.data
        except Exception as e:
            logger.error(f"Error fetching/serializing suggestions in consumer helper for email {email_id}: {e}", exc_info=True)
            return []

    # --- Handler for messages sent to the group --- 
    async def suggestions_updated(self, event):
        # Event contains only {'type': 'suggestions.updated', 'email_id': ...}
        email_id = event.get('email_id')
        event_type = event.get('type')

        if not email_id or event_type != 'suggestions.updated':
            logger.warning(f"SuggestionConsumer received invalid event: {repr(event)}")
            return

        logger.info(f"SuggestionConsumer received simple notification for email {email_id}. Fetching suggestions from DB...")
        
        # Fetch suggestions from DB asynchronously using the helper
        suggestions_payload = await self._get_suggestions_from_db(email_id)
        logger.info(f"SuggestionConsumer fetched {len(suggestions_payload)} suggestions from DB for email {email_id}.")

        # Construct the full message to send to the client
        message_to_send = {
            'type': event_type,
            'email_id': email_id,
            'suggestions': suggestions_payload
        }

        logger.info(f"SuggestionConsumer sending FULL suggestions.updated event to user {self.user.id} for email {email_id}.")
        await self.send(text_data=json.dumps(message_to_send)) 

class LeadConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info(f"LeadConsumer connect attempt. Scope keys: {list(self.scope.keys())}")
        query_string = self.scope.get('query_string', b'').decode()
        logger.info(f"LeadConsumer query_string: {query_string}")
        
        self.user = self.scope.get("user") # Safely get user
        
        logger.info(f"LeadConsumer user from scope: {self.user}")
        if self.user:
            logger.info(f"LeadConsumer user.is_authenticated: {self.user.is_authenticated}")

        if not self.user or not self.user.is_authenticated:
            logger.warning(f"WebSocket connection attempt by unauthenticated user (LeadConsumer). User: {self.user}, Auth: {self.user.is_authenticated if self.user else 'No user'}. Closing connection.")
            await self.close()
            return
        
        self.group_name = "leads_group" # Alle User in der gleichen Gruppe für Leads
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        logger.info(f"WebSocket connected for user {getattr(self.user, 'id', 'unknown')} (LeadConsumer). Added to group {self.group_name}")
        # Sende initiale Projektdaten nach Connect
        await self.send_leads_init(page=1, page_size=20)

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            logger.info(f"WebSocket disconnected for user {getattr(self.user, 'id', 'unknown')} (LeadConsumer). Removed from group {self.group_name}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            event_type = data.get('type')
            if event_type == 'get_leads':
                page = data.get('page', 1)
                page_size = data.get('page_size', 20)
                filter_data = data.get('filter', {})
                await self.send_leads_init(page=page, page_size=page_size, filter_data=filter_data)
            elif event_type == 'lead_details':
                project_id = data.get('project_id')
                await self.send_lead_details(project_id)
            else:
                await self.send_error('Unbekannter Event-Typ.')
        except Exception as e:
            logger.error(f"Fehler beim Verarbeiten der WebSocket-Nachricht: {e}", exc_info=True)
            await self.send_error('Ungültige Nachricht oder Serverfehler.')

    @database_sync_to_async
    def get_projects(self, page=1, page_size=20, filter_data=None):
        from mailmind.freelance.models import FreelanceProject
        from mailmind.freelance.serializers import FreelanceProjectSerializer
        queryset = FreelanceProject.objects.all().order_by('-created_at')
        if filter_data:
            if 'remote' in filter_data:
                queryset = queryset.filter(remote=filter_data['remote'])
            if 'provider' in filter_data:
                queryset = queryset.filter(provider=filter_data['provider'])
            if 'skill' in filter_data:
                queryset = queryset.filter(skills__contains=[filter_data['skill']])
        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        projects = queryset[start:end]
        serializer = FreelanceProjectSerializer(projects, many=True)
        return serializer.data, total

    @database_sync_to_async
    def get_project_details(self, project_id):
        from mailmind.freelance.models import FreelanceProject
        from mailmind.freelance.serializers import FreelanceProjectSerializer
        try:
            project = FreelanceProject.objects.get(project_id=project_id)
            serializer = FreelanceProjectSerializer(project)
            return serializer.data
        except FreelanceProject.DoesNotExist:
            return None

    async def send_leads_init(self, page=1, page_size=20, filter_data=None):
        projects, total = await self.get_projects(page, page_size, filter_data)
        message = {
            'type': 'leads_init',
            'projects': projects,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total
            }
        }
        await self.send(text_data=json.dumps(message))

    async def send_lead_details(self, project_id):
        details = await self.get_project_details(project_id)
        if details:
            message = {
                'type': 'lead_details',
                'project_id': project_id,
                'details': details
            }
        else:
            message = {
                'type': 'error',
                'detail': f'Projekt mit ID {project_id} nicht gefunden.'
            }
        await self.send(text_data=json.dumps(message))

    async def send_error(self, detail):
        message = {
            'type': 'error',
            'detail': detail
        }
        await self.send(text_data=json.dumps(message))

    async def leads_updated(self, event):
        # Sende Notification und aktualisierte Projektdaten
        await self.send_leads_init(page=1, page_size=20) 