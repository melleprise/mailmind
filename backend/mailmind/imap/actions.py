import logging
from typing import List, Tuple
from imap_tools import MailMessageFlags
from mailmind.core.models import Email, EmailAccount
from .connection import get_imap_connection
from .utils import map_folder_name_to_server # Assuming this utility exists or will be created

logger = logging.getLogger(__name__)

def move_email(email_id: int, target_folder: str) -> bool:
    """Moves an email to the specified target folder on the IMAP server and updates the local DB record.

    Args:
        email_id: The database ID of the Email object.
        target_folder: The name of the target folder (e.g., 'Spam', 'Archive').

    Returns:
        True if the operation was successful, False otherwise.
    """
    try:
        email = Email.objects.select_related('account').get(pk=email_id)
        account = email.account
        uid = email.uid # Assumes UID is stored on the Email model

        if not uid:
            logger.error(f"Cannot move email {email_id}: UID not found.")
            return False
            
        # Map the logical folder name (e.g., 'Spam') to the actual server folder name
        # This might require logic specific to the email provider (e.g., '\Junk' or '[Gmail]/Spam')
        # We assume a utility function exists for this mapping
        server_target_folder = map_folder_name_to_server(account, target_folder)
        if not server_target_folder:
             logger.error(f"Cannot map target folder '{target_folder}' to server folder for account {account.id}. Move failed.")
             return False

        with get_imap_connection(account) as mailbox:
            # We need to be in the folder where the email currently resides (or assume it works globally, less safe)
            # For simplicity, let's assume UID is unique across folders for this account or that we know the source folder.
            # A more robust implementation might need the source folder.
            # Example: mailbox.folder.set(email.original_folder) # If original_folder is stored

            logger.info(f"Attempting to move email UID {uid} for account {account.id} to folder '{server_target_folder}'")
            response = mailbox.move([str(uid)], server_target_folder) # UIDs need to be strings

            if response and response[0].ok: # Check if the command succeeded
                logger.info(f"Successfully moved email UID {uid} to '{server_target_folder}' on server.")
                # Update local database
                email.folder_name = target_folder # Store the logical name
                # Optionally clear flags if moving implies state change (e.g., moving from Inbox removes implicit 'Inbox' state)
                # email.flags = [] # Example, adjust as needed
                email.save(update_fields=['folder_name']) # Add 'flags' if modified
                return True
            else:
                logger.error(f"Failed to move email UID {uid} to '{server_target_folder}' on server. Response: {response}")
                return False

    except Email.DoesNotExist:
        logger.error(f"Cannot move email: Email with ID {email_id} not found.")
        return False
    except EmailAccount.DoesNotExist:
         logger.error(f"Cannot move email {email_id}: Corresponding EmailAccount not found.")
         return False
    except Exception as e:
        logger.error(f"Error moving email {email_id} to folder '{target_folder}': {e}", exc_info=True)
        return False

def flag_email(email_id: int, flags: List[str], set_flag: bool = True) -> bool:
    """Sets or removes flags for an email on the IMAP server and updates the local DB record.

    Args:
        email_id: The database ID of the Email object.
        flags: A list of flags to set or remove (e.g., [MailMessageFlags.SEEN, MailMessageFlags.FLAGGED]).
        set_flag: True to set the flags, False to remove them.

    Returns:
        True if the operation was successful, False otherwise.
    """
    try:
        email = Email.objects.select_related('account').get(pk=email_id)
        account = email.account
        uid = email.uid

        if not uid:
            logger.error(f"Cannot flag email {email_id}: UID not found.")
            return False

        action = "Setting" if set_flag else "Removing"
        with get_imap_connection(account) as mailbox:
            # Assume UID is unique or we know the source folder
            logger.info(f"Attempting to {action.lower()} flags {flags} for email UID {uid} for account {account.id}")
            response = mailbox.flag([str(uid)], flags, set_flag)

            # Correct check: mailbox.flag returns the server response status (e.g., 'OK', 'NO')
            # or sometimes a more complex structure. Check for 'OK' status within the response.
            success = False
            if response:
                if isinstance(response, str) and response.upper() == 'OK':
                    success = True
                elif isinstance(response, (list, tuple)) and response:
                    try:
                        first_item = response[0] # Can be str or tuple/list
                        status_str = ""
                        if isinstance(first_item, str):
                            status_str = first_item
                        elif isinstance(first_item, (list, tuple)) and first_item:
                            # Handle potential nesting like [(('OK', ...), ...)]
                            first_sub_item = first_item[0]
                            if isinstance(first_sub_item, str):
                                status_str = first_sub_item
                            elif isinstance(first_sub_item, (list, tuple)) and first_sub_item:
                                # Accessing the first element of the nested tuple/list
                                status_str = str(first_sub_item[0]) 

                        if status_str.upper() == 'OK':
                            success = True
                    except (IndexError, TypeError, AttributeError) as e: # Added AttributeError
                        logger.warning(f"Could not determine success status from complex response structure for UID {uid}. Response: {response}. Error: {e}")

            if success: 
                logger.info(f"Successfully {action.lower()} flags {flags} for email UID {uid} on server.")
                # Update local database
                current_flags = set(email.flags or [])
                flags_to_change = set(flags)
                if set_flag:
                    new_flags = list(current_flags.union(flags_to_change))
                else:
                    new_flags = list(current_flags.difference(flags_to_change))
                
                email.flags = new_flags
                email.save(update_fields=['flags'])
                return True
            else:
                logger.error(f"Failed to {action.lower()} flags {flags} for email UID {uid}. Response: {response}")
                return False

    except Email.DoesNotExist:
        logger.error(f"Cannot flag email: Email with ID {email_id} not found.")
        return False
    except EmailAccount.DoesNotExist:
         logger.error(f"Cannot flag email {email_id}: Corresponding EmailAccount not found.")
         return False
    except Exception as e:
        logger.error(f"Error {action.lower()} flags {flags} for email {email_id}: {e}", exc_info=True)
        return False

# Example standard flags from imap_tools you might use:
# MailMessageFlags.ANSWERED
# MailMessageFlags.FLAGGED
# MailMessageFlags.DELETED
# MailMessageFlags.SEEN
# MailMessageFlags.DRAFT
# MailMessageFlags.RECENT (usually read-only)

# Note: For custom flags (keywords) or moving to 'Spam' (often '\Junk' flag or a specific folder),
# you might need adjustments or specific handling.
# Moving to Spam might be better handled by `move_email(email_id, 'Spam')`
# which would internally map 'Spam' to the correct server folder or potentially set the '\Junk' flag if MOVE isn't supported for that. 