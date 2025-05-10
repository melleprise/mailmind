import logging
from django.core.management import call_command
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

def run_initial_sync_for_account(account_id: int, account_email: str, user_id: int):
    \"\"\"
    Task to run the initial_sync management command for a specific email account.
    Sends a WebSocket message upon completion or failure.
    \"\"\"
    logger.info(f"Starting initial_sync task for account_id={account_id}, email={account_email}, user_id={user_id}")
    channel_layer = get_channel_layer()
    group_name = f"user_{user_id}" # Assuming user-specific groups
    sync_status = 'failed'
    message = "An unexpected error occurred during synchronization."

    try:
        # Ensure the command runs non-interactively if it supports it
        # Add --no-input or similar flags if required by the command
        call_command('initial_sync', f'--user-email={account_email}', interactive=False)
        sync_status = 'completed'
        message = f"Synchronization for {account_email} completed successfully."
        logger.info(f"Initial_sync command completed successfully for account {account_id}")

    except Exception as e:
        logger.error(f"Error running initial_sync for account {account_id}: {e}", exc_info=True)
        message = f"Synchronization failed for {account_email}: {str(e)}"
        # Keep sync_status as 'failed'

    finally:
        # Send WebSocket notification
        logger.info(f"Sending WebSocket sync status '{sync_status}' for account {account_id} to group {group_name}")
        try:
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "sync.status", # Matches the handler type in the consumer
                    "account_id": account_id,
                    "status": sync_status,
                    "message": message,
                },
            )
        except Exception as ws_e:
            logger.error(f"Failed to send WebSocket notification for account {account_id} to group {group_name}: {ws_e}", exc_info=True)

def sync_task_complete_hook(task):
    \"\"\"
    Optional hook function called by Django Q upon task completion (success or failure).
    Logs the task result.
    Note: The primary WebSocket notification is sent from within the task itself.
    \"\"\"
    if task.success:
        logger.info(f"Django Q Task '{task.name}' (ID: {task.id}) completed successfully. Result: {task.result}")
    else:
        logger.warning(f"Django Q Task '{task.name}' (ID: {task.id}) failed. Result: {task.result}") 