from django.urls import re_path
from . import consumers
from mailmind.imap.routing import websocket_urlpatterns as imap_websocket_urlpatterns

websocket_urlpatterns = [
    # API WebSocket patterns
    re_path(r'ws/general/$', consumers.GeneralConsumer.as_asgi()),
    re_path(r'ws/leads/$', consumers.LeadConsumer.as_asgi()),
] + imap_websocket_urlpatterns  # Add IMAP WebSocket patterns

# General WebSocket route handled by EmailConsumer
# This single consumer can handle different message types based on group messages
# re_path(r'ws/(?P<path>.*)/?$', consumers.EmailConsumer.as_asgi()), # <-- AUSKOMMENTIERT, um IMAP-Route zu priorisieren
# Original suggestion route (removed as EmailConsumer handles it):
# re_path(r'ws/suggestions/?$', consumers.SuggestionConsumer.as_asgi()), 