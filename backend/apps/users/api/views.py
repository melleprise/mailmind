from django_q.tasks import async_task
from django.core.management import call_command
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)

class EmailAccountViewSet(ModelViewSet):
    @action(detail=True, methods=['post'], url_path='trigger-sync')
    def trigger_sync(self, request, pk=None):
        \"\"\"
        Triggers an asynchronous initial sync task for the email account.
        \"\"\"
        account = self.get_object() # Gets the account instance, handles 404
        
        # Permission check (ensure the requesting user owns the account)
        if account.user != request.user:
            return Response({"detail": "You do not have permission to sync this account."}, status=status.HTTP_403_FORBIDDEN)

        logger.info(f"Triggering initial sync task for account {account.id} (Email: {account.email}) by user {request.user.id}")

        # Enqueue the task
        async_task(
            'apps.users.tasks.run_initial_sync_for_account_v2', # Neuer Task-Name
            account.id,
            account.user.email, # User-E-Mail
            request.user.id, # Pass user ID for WebSocket targeting
            task_name=f"Initial Sync for Account {account.id}",
            hook='apps.users.tasks.sync_task_complete_hook' # Optional: hook on completion
        )

        return Response({"detail": "Sync task queued successfully."}, status=status.HTTP_202_ACCEPTED)

    # ... rest of the ViewSet ... 