"""
WebSocket routing configuration for IMAP functionality.
"""

import json
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from django.urls import re_path
from . import consumers # Import the consumer

websocket_urlpatterns = [
    # WebSocket patterns will be added here later
    # Define the WebSocket URL pattern for the IMAP consumer
    re_path(r'ws/imap/(?P<account_id>\d+)/$', consumers.IMAPConsumer.as_asgi()),
] 