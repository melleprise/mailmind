"""
ASGI config for mailmind project.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mailmind.settings')

# Get ASGI application first to ensure Django is fully loaded and apps are ready
django_asgi_app = get_asgi_application()

# Now that Django is loaded, import Channels routing and our middleware
from channels.routing import ProtocolTypeRouter, URLRouter
from mailmind.middleware import TokenAuthMiddleware
from mailmind.routing import websocket_urlpatterns 

# Define the application using the imported components
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": TokenAuthMiddleware(
         URLRouter(
            websocket_urlpatterns
        )
    ),
}) 