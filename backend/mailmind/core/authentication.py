from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions
from django.utils.translation import gettext_lazy as _
from asgiref.sync import sync_to_async
from rest_framework.authtoken.models import Token # Ensure Token model is imported

class AsyncTokenAuthentication(TokenAuthentication):
    """
    Async-safe version of TokenAuthentication.
    Uses sync_to_async to wrap the database query in authenticate_credentials
    and overrides authenticate to be async.
    """
    keyword = 'Token' # Keep the keyword defined

    @sync_to_async
    def _get_token(self, key):
        try:
            return Token.objects.select_related('user').get(key=key)
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid token.'))

    async def authenticate(self, request):
        """Overrides the base authenticate method to be async."""
        auth = self.get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None

        if len(auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid token header. Token string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Token string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)

        # Call the async authenticate_credentials method
        return await self.authenticate_credentials(token)

    async def authenticate_credentials(self, key):
        token = await self._get_token(key)

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

        return (token.user, token) 