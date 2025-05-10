import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
# from aioimaplib import aioimaplib # Nicht mehr benötigt
from django.core.exceptions import ObjectDoesNotExist
from mailmind.core.models import EmailAccount # Email nicht mehr direkt benötigt
# from .store import save_email_metadata_from_dict # Nicht mehr benötigt
# from .mapper import map_metadata_from_dict # Nicht mehr benötigt
import logging
# from mailmind.core.crypto import decrypt_password # Nicht mehr benötigt
# from django.conf import settings # Nicht mehr benötigt
# from cryptography.fernet import Fernet, InvalidToken # Nicht mehr benötigt

logger = logging.getLogger(__name__)

# Entferne die lokale Entschlüsselungsfunktion
# def decrypt_password_local(encrypted_password: str) -> str:
#     ...

class IMAPConsumer(AsyncWebsocketConsumer):
    """WebSocket Consumer, der auf IMAP-Updates lauscht und sie weiterleitet."""

    async def connect(self):
        """Verbindung herstellen, Benutzer authentifizieren und Gruppe beitreten."""
        self.user = self.scope["user"]
        if not self.user or not self.user.is_authenticated:
            await self.close(code=4001)
            return

        self.account_id = self.scope['url_route']['kwargs']['account_id']
        self.group_name = f'imap_updates_{self.account_id}'

        # Prüfen, ob der Benutzer Zugriff auf diesen Account hat
        try:
            has_access = await database_sync_to_async(EmailAccount.objects.filter(id=self.account_id, user=self.user).exists)()
            if not has_access:
                logger.warning(f"User {self.user.email} tried to connect to unauthorized account {self.account_id}")
                await self.close(code=4004)
                return
        except Exception as e:
            logger.error(f"Error checking account access for user {self.user.email}, account {self.account_id}: {e}")
            await self.close(code=5000)
            return

        # Join room group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )

        await self.accept()
        logger.info(f"IMAP Update WebSocket connected for account {self.account_id}, user {self.user.email}")
        # Sende initialen Status, dass wir auf Updates lauschen
        await self.send_status('listening', 'Waiting for real-time email updates...')

    async def disconnect(self, close_code):
        """Verbindung trennen und Gruppe verlassen."""
        logger.info(f"IMAP Update WebSocket disconnecting for account {self.account_id}, code: {close_code}")
        # Leave room group
        if hasattr(self, 'group_name'): # Sicherstellen, dass group_name existiert
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        logger.info(f"IMAP Update WebSocket disconnected for account {self.account_id}")

    async def receive(self, text_data):
        """Nachrichten vom WebSocket empfangen (nicht verwendet)."""
        pass

    async def send_status(self, status, message=None):
        """Status an den Client senden."""
        try:
            await self.send(text_data=json.dumps({
                'type': 'status',
                'status': status,
                'message': message
            }))
        except Exception as e:
            logger.warning(f"Failed to send status update to WebSocket for account {self.account_id}: {e}")

    async def send_update(self, update_type, data):
        """Update an den Client senden."""
        try:
            await self.send(text_data=json.dumps({
                'type': update_type,
                'data': data
            }))
        except Exception as e:
            logger.warning(f"Failed to send data update to WebSocket for account {self.account_id}: {e}")

    # --- Event-Handler für Nachrichten vom Channel Layer --- 
    async def imap_refresh_event(self, event):
        """Behandelt Nachrichten vom Typ 'imap.refresh_event' aus der Gruppe."""
        data = event.get('data', {})
        message = data.get('message', 'New data available.')
        processed_count = data.get('processed_count', 0)
        logger.info(f"Received imap.refresh_event for account {self.account_id}. Message: {message}")
        # Sende generisches Update an das Frontend
        await self.send_update('refresh_needed', {
            'message': message,
            'processed_count': processed_count
        })

    # --- Entfernte Methoden --- 
    # async def setup_imap_connection(self):
    #     ...
    # async def idle_loop(self):
    #     ...
    # async def fetch_and_process_new_emails(self):
    #     ...
    # async def imap_update(self, event): # Ersetzt durch spezifischeren Handler
    #     ...

    # Gruppen-Nachrichten-Handler (optional, falls andere Teile Updates senden sollen)
    async def imap_update(self, event):
        update_type = event.get('update_type', 'generic_update')
        data = event.get('data', {})
        logger.info(f"Received message from group {self.group_name}: type={update_type}")
        await self.send_update(update_type, data) 