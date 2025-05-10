from django.urls import re_path
from channels.routing import URLRouter

from mailmind.consumers import EmailConsumer
from .imap.routing import websocket_urlpatterns as imap_websocket_urlpatterns
from mailmind.api.consumers import LeadConsumer

# Import consumers here later
# from .imap import consumers

# Routing for WebSocket connections (if needed for UI updates later)
websocket_urlpatterns = [
    # re_path(r'ws/some_path/(?P<param>\w+)/$', consumers.SomeWebSocketConsumer.as_asgi()),
    re_path(r'ws/general/$', EmailConsumer.as_asgi()),
    re_path(r'ws/leads/$', LeadConsumer.as_asgi()),
] + imap_websocket_urlpatterns

# Routing for standard channel layer messages (e.g., background tasks, IMAP control)
channel_urlpatterns = [
    # re_path(r'^imap/start/(?P<account_id>\d+)/$', consumers.ImapIdleConsumer.as_asgi()), # Example
]

# Remove duplicate definition at the end
# websocket_urlpatterns = [
#     re_path(r'ws/email/$', EmailConsumer.as_asgi()),
# ] 