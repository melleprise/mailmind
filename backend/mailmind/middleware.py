import traceback
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
import logging

logger = logging.getLogger(__name__)

@database_sync_to_async
def get_user_from_token(token_key):
    """
    Async function to retrieve user from token key.
    """
    try:
        token = Token.objects.select_related('user').get(key=token_key)
        return token.user
    except Token.DoesNotExist:
        logger.warning(f"TokenAuthMiddleware: Token key '{token_key[:6]}...' not found.")
        return AnonymousUser()
    except Exception as e:
        logger.error(f"TokenAuthMiddleware: Error retrieving user for token '{token_key[:6]}...': {e}")
        logger.debug(traceback.format_exc()) # Log full traceback for debugging
        return AnonymousUser()

class TokenAuthMiddleware:
    """
    Custom middleware for Django Channels Websocket authentication using DRF tokens passed in query string.
    """

    def __init__(self, app):
        # Store the ASGI application we were passed
        self.app = app

    async def __call__(self, scope, receive, send):
        # Add critical log at the very beginning
        logger.critical(f"--- TokenAuthMiddleware __call__ entered for scope path: {scope.get('path')} ---")

        # Look up query string
        query_string = scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        token_key = query_params.get('token', [None])[0]

        if token_key:
            logger.info(f"TokenAuthMiddleware: Attempting to authenticate WebSocket with token key: {token_key[:6]}...")
            scope['user'] = await get_user_from_token(token_key)
            if not isinstance(scope['user'], AnonymousUser):
                 logger.info(f"TokenAuthMiddleware: WebSocket authentication successful for user {scope['user']}")
            else:
                 logger.info(f"TokenAuthMiddleware: WebSocket authentication failed or token invalid for key {token_key[:6]}...")
        else:
            # If no token provided, default to AnonymousUser (AuthMiddlewareStack might still populate from session)
            logger.info("TokenAuthMiddleware: No token found in query string.")
            # Important: Don't overwrite scope['user'] if it might be set by session auth later in the stack
            if 'user' not in scope:
                scope['user'] = AnonymousUser()


        # Pass control to the next middleware or the consumer
        return await self.app(scope, receive, send) 