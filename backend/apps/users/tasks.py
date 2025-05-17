import logging
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from mailmind.imap.sync import sync_account

logger = logging.getLogger(__name__)

def run_initial_sync_for_account_v2(account_id: int, user_email: str, user_id: int):
    """
    Task to run the sync_account function for a specific email account.
    Sends a WebSocket message upon completion or failure.
    """
    logger.info(f"Starting sync_account task for account_id={account_id}, user_email={user_email}, user_id={user_id}")
    channel_layer = get_channel_layer()
    group_name = f"user_{user_id}" # Assuming user-specific groups
    sync_status = 'failed'
    message = "An unexpected error occurred during synchronization."

    try:
        sync_account(account_id)
        sync_status = 'completed'
        message = f"Synchronization for account {account_id} completed successfully."
        logger.info(f"sync_account completed successfully for account {account_id}")

    except Exception as e:
        logger.error(f"Error running sync_account for account {account_id}: {e}", exc_info=True)
        message = f"Synchronization failed for account {account_id}: {str(e)}"
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
    """
    Optional hook function called by Django Q upon task completion (success or failure).
    Logs the task result.
    Note: The primary WebSocket notification is sent from within the task itself.
    """
    if task.success:
        logger.info(f"Django Q Task '{task.name}' (ID: {task.id}) completed successfully. Result: {task.result}")
    else:
        logger.warning(f"Django Q Task '{task.name}' (ID: {task.id}) failed. Result: {task.result}") 