from channels.generic.websocket import AsyncWebsocketConsumer
import json
from channels.db import database_sync_to_async
import logging # Import logging
# Removed unused imports for this consumer
# from mailmind.core.models import AISuggestion
# from mailmind.api.serializers import AISuggestionSerializer

logger = logging.getLogger(__name__) # Get logger

class EmailConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user') # Use .get() to be safe
        
        # --- Re-enable authentication check ---
        if not self.user:
            logger.warning("WebSocket connect attempt failed: No user found in scope.")
            await self.close()
            return
        if not self.user.is_authenticated:
            # Log the actual user object found in scope for debugging
            logger.warning(f"WebSocket connect attempt failed: User '{self.user}' (Type: {type(self.user)}) found in scope is not authenticated.")
            await self.close()
            return
        # --- End re-enabled check ---

        # Proceed only if authenticated
        self.group_name = f'user_{self.user.id}_events'
        user_info = f"user {self.user.id} ('{self.user.email}')"

        # Gruppe beitreten
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"WebSocket connected for {user_info}, joined group {self.group_name}")

    async def disconnect(self, close_code):
        # Use logger for disconnect message
        if hasattr(self, 'group_name') and self.user and self.user.is_authenticated: # Check if user exists and authenticated
            logger.info(f"WebSocket disconnected for user {self.user.id} ('{self.user.email}'). Close code: {close_code}. Left group {self.group_name}")
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        else:
             logger.info(f"WebSocket disconnected for unauthenticated user or user without group. Close code: {close_code}")

    # receive wird nicht mehr benötigt, um nur zu empfangen
    # async def receive(self, text_data):
    #     pass 

    # Handler für "email.new" Nachrichten von der Gruppe
    async def email_new(self, event):
        email_data = event['email_data']
        logger.debug(f"Sending email_new event to user {self.user.id}: {email_data.get('id', 'N/A')}")
        # Sende Nachricht an WebSocket
        await self.send(text_data=json.dumps({
            'type': 'email.new',
            'payload': email_data
        }))

    # Handler für "email.update" Nachrichten von der Gruppe
    async def email_updated(self, event):
        event_data = event.get('data', {}) # Hole das 'data' Objekt
        email_id = event_data.get('email_id')
        logger.debug(f"Sending email.updated event to user {self.user.id} for Email ID: {email_id}")
        # Sende Nachricht an WebSocket mit dem korrekten Typ und Datenstruktur
        await self.send(text_data=json.dumps({
            'type': 'email.updated', # Der Typ der Nachricht, die das Frontend erhält
            'data': event_data # Die Daten (nur email_id) weitergeben
        }))

    # Handler für "sync.status" Nachrichten von der Gruppe (Beispiel)
    async def sync_status(self, event):
        status_data = event['status_data']
        logger.debug(f"Sending sync_status event to user {self.user.id}: {status_data}")
        # Sende Nachricht an WebSocket
        await self.send(text_data=json.dumps({
            'type': 'sync.status',
            'payload': status_data
        })) 

    # --- ADD HANDLER for suggestion_generation_complete --- 
    async def suggestion_generation_complete(self, event):
        """Handles the suggestion_generation_complete message type from the channel layer.
           Sends the new suggestions data directly to the connected client.
        """
        event_data = event.get('data', {})
        email_id = event_data.get('email_id')
        suggestions_payload = event_data.get('suggestions', [])
        
        logger.info(f"[Consumer] Received suggestion_generation_complete for email {email_id} for user {self.user.id}. Sending {len(suggestions_payload)} suggestions to client.")
        
        # Forward the data received from the task to the WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'suggestion_generation_complete', # Match the type expected by the frontend
            'data': { # Keep the nested 'data' structure as sent by the task
                'email_id': email_id,
                'suggestions': suggestions_payload
            }
        })) 

    # --- NEUER HANDLER für API Key Status ---
    async def api_key_status(self, event):
        """Handles the api_key_status message type from the channel layer."""
        event_data = event.get('data', {})
        provider = event_data.get('provider')
        status = event_data.get('status')
        logger.debug(f"[Consumer] Received api_key_status for provider {provider} for user {self.user.id}. Status: {status}")
        
        # Forward the data received from the task to the WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'api_key_status', # Match the type expected by the frontend
            'data': event_data # Forward the whole data dict (provider, status, message)
        }))
    # --- ENDE NEUER HANDLER --- 