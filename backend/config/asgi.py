"""
ASGI config for email-ai-tinder project.

It exposes the ASGI callable as a module-level variable named `application`.
"""

import os
import sys
from pathlib import Path
import warnings

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator # For security

# DO NOT Import middleware here yet
# from mailmind.middleware import TokenAuthMiddleware

# This allows easy placement of apps within the interior
# mailmind directory.
ROOT_DIR = Path(__file__).resolve(strict=True).parent.parent
sys.path.append(str(ROOT_DIR / "mailmind"))

# If DJANGO_SETTINGS_MODULE is unset, default to the local settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# NOW import routing AFTER Django apps are ready
import mailmind.api.routing
from mailmind.middleware import TokenAuthMiddleware # Import hierher verschoben und einkommentiert

warnings.filterwarnings("ignore", message=r".*Retry and timeout are misconfigured.*", category=UserWarning)

application = ProtocolTypeRouter(
    {
        # Django's ASGI application to handle standard HTTP requests
    "http": django_asgi_app,

        # --- WebSocket Handling Re-enabled ---
        "websocket": TokenAuthMiddleware( # TokenAuthMiddleware umschließt jetzt den Rest
            AllowedHostsOriginValidator(
                AuthMiddlewareStack(
                    URLRouter(
                        mailmind.api.routing.websocket_urlpatterns
                    )
                )
            )
        ),
        # --- End WebSocket Handling ---
    }
) 