import logging
import time
from typing import Optional
from django.utils import timezone
from django.conf import settings
from cryptography.fernet import Fernet
from django_q.tasks import async_task
from imap_tools import MailBox, MailboxLoginError, MailboxFolderStatusError, MailboxFolderSelectError
from django.db import transaction # Import transaction

# Importiere Modelle und andere Module relativ zum imap-Paket oder absolut
from mailmind.core.models import EmailAccount
# Importiere Tasks explizit
from .tasks import process_folder_metadata_task 
# Importiere Verbindungskontext
from .connection import get_imap_connection

logger = logging.getLogger(__name__)

# Entfernt: Feste Konfiguration für INBOX
# folders_to_sync_config = ['INBOX']

# Mapping zu Standardnamen für Priorisierung etc.
# FOLDER_NAME_MAP = { ... entfernt ... }

# Entferne die Funktion find_all_mail_folder, da sie nicht mehr benötigt wird
# def find_all_mail_folder(mailbox: MailBox) -> str | None:
#    ...

def sync_account(account_id: int) -> None:
    """Synchronisiert einen Account, indem alle relevanten Ordner verarbeitet werden."""
    start_time = time.time()
    logger.info(f"=== Starting sync task dispatch for account ID: {account_id} ===")
    account = None # Initialisieren für finally Block
    dispatched_count = 0
    total_folders_processed = 0
    error_during_dispatch = False
    
    try:
        # Hole Account-Details
        fetch_start = time.time()
        logger.info(f"Fetching account details for ID: {account_id} (with lock)")
        with transaction.atomic():
            account = EmailAccount.objects.select_for_update().get(id=account_id)
            logger.info(f"Found account: {account.email}")
        logger.debug(f"Account details fetched in {time.time() - fetch_start:.2f}s")
        
        # Status auf syncing setzen (zu Beginn des Dispatch-Prozesses)
        try:
            with transaction.atomic():
                account_for_status = EmailAccount.objects.select_for_update().get(id=account_id)
                if account_for_status.sync_status != 'syncing': # Nur setzen, wenn nicht schon syncing
                    account_for_status.sync_status = 'syncing'
                    account_for_status.last_sync_started_at = timezone.now() # Zeitstempel setzen
                    account_for_status.last_sync_error = None # Fehler löschen
                    account_for_status.save(update_fields=['sync_status', 'last_sync_started_at', 'last_sync_error'])
                    logger.info(f"Set account {account_id} status to 'syncing'.")
                else:
                     logger.info(f"Account {account_id} status is already 'syncing'.")
        except Exception as status_e:
                logger.error(f"Error setting initial syncing status for account {account_id}: {status_e}")
                raise # Breche ab, wenn Status nicht gesetzt werden kann

        # Verbindung holen und Ordnerliste abrufen
        with get_imap_connection(account) as mailbox:
            try:
                logger.info(f"[{account.email}] Fetching folder list...")
                all_folders = mailbox.folder.list()
                logger.info(f"[{account.email}] Found {len(all_folders)} total folders.")
            except Exception as e_list:
                logger.error(f"[{account.email}] Failed to list folders: {e_list}", exc_info=True)
                raise # Breche ab, wenn Ordner nicht gelistet werden können

            # Filtere Ordner: Berücksichtige alle, die nicht \Noselect sind
            folders_to_process = []
            skipped_folders = []
            for f_info in all_folders:
                # Handle special use flags or specific folders to skip
                if "\\Noselect" in f_info.flags:
                    logger.debug(f"Skipping folder '{f_info.name}' due to \\Noselect flag.")
                    skipped_folders.append(f_info.name)
                    continue
                # Explizit [Gmail]/All Mail und lokalisierte Versionen überspringen
                normalized_folder_name = f_info.name.lower() # Normalisieren für Vergleich
                if normalized_folder_name == '[gmail]/all mail' or normalized_folder_name == '[gmail]/alle nachrichten':
                    logger.info(f"Skipping folder '{f_info.name}' because it duplicates content ('[Gmail]/All Mail' or similar).") # Log angepasst
                    skipped_folders.append(f_info.name)
                    continue
                    
                # Optional: \HasChildren ignorieren, wenn Unterordner nicht separat gesynct werden sollen?
                # if "\\HasChildren" in f_info.flags:
                #     logger.debug(f"Skipping folder '{f_info.name}' due to \\HasChildren flag.")
                #     skipped_folders.append(f_info.name)
                #     continue
                
                # Alle anderen Ordner hinzufügen
                folders_to_process.append(f_info.name)
                logger.debug(f"Added folder '{f_info.name}' to sync list.")

            if not folders_to_process:
                logger.warning(f"[{account.email}] No selectable folders found after filtering {len(all_folders)} total folders (skipped: {skipped_folders}). Nothing to dispatch.")
                error_during_dispatch = True # Zählt als Fehler, da nichts getan werden kann
            else:
                logger.info(f"[{account.email}] Will dispatch sync tasks for folders ({len(folders_to_process)}): {folders_to_process}")
                # Dispatch Tasks für jeden ausgewählten Ordner
                for folder_name in folders_to_process:
                    try:
                        logger.info(f"[{account.email}] Dispatching sync task for folder: {folder_name}")
                        async_task('mailmind.imap.tasks.process_folder_metadata_task', account_id, folder_name)
                        dispatched_count += 1
                    except Exception as e_dispatch:
                        logger.error(f"[{account.email}] Failed to dispatch task for folder '{folder_name}': {e_dispatch}", exc_info=True)
                        error_during_dispatch = True # Markiere Fehler, aber versuche weiter
        
        # Gesamtzahl der zu verarbeitenden Ordner speichern (optional)
        total_folders_processed = len(folders_to_process)

        # Erfolgsmeldung basiert nur noch darauf, ob Tasks dispatched wurden
        if dispatched_count > 0:
             logger.info(f"=== Sync task dispatch finished for account {account.email}. Dispatched {dispatched_count}/{total_folders_processed} task(s). Errors during dispatch: {error_during_dispatch} ===")
        else:
            # Entweder keine Ordner gefunden oder Dispatch-Fehler
            logger.warning(f"=== Sync task dispatch finished for account {account.email}. No tasks dispatched. Errors during dispatch: {error_during_dispatch} ===")
            # Wenn keine Tasks dispatched wurden und Fehler auftraten, setze Status auf Error
            if error_during_dispatch:
                 _update_account_status_sync(account, 'error', "Failed to dispatch sync tasks or list folders.")
            else: # Keine Ordner gefunden
                 _update_account_status_sync(account, 'synced', "No selectable folders found to sync.") # Oder 'idle'?

    except Exception as e:
        # ... (Generelles Error Handling bleibt ähnlich, Status wird auf error gesetzt) ...
        logger.error(f"Unexpected error during sync dispatch for account {account_id}: {e}", exc_info=True) 
        error_during_dispatch = True 
        if account:
            _update_account_status_sync(account, 'error', f"Sync Dispatch Error: {str(e)[:200]}")
    finally:
        # Status wird jetzt nicht mehr im finally zurückgesetzt.
        # Der Status bleibt 'syncing', bis die Tasks ihn ändern, oder er wurde auf 'error' gesetzt.
        logger.info(f"=== Sync account function finished for {getattr(account, 'email', account_id)} ===")
        logger.debug(f"Total sync dispatch function completed in {time.time() - start_time:.2f}s")

# Hilfsfunktion zum Setzen des Status (könnte in utils ausgelagert werden)
# Benötigt, da _update_account_status im Task-Modul ist
def _update_account_status_sync(account: EmailAccount, status: str, message: Optional[str] = None):
    """Helper to update account status from within sync_account."""
    # ... (Logik ähnlich wie _update_account_status in tasks.py, aber ohne Zeitstempel-Update hier)
    if not account:
        logger.error(f"Attempted to update status '{status}' (sync_account) but account object was None.")
        return
    try:
        with transaction.atomic():
            account_to_update = EmailAccount.objects.select_for_update().get(id=account.id)
            account_to_update.sync_status = status
            fields_to_update = ['sync_status']
            if message:
                 max_len = EmailAccount._meta.get_field('last_sync_error').max_length
                 account_to_update.last_sync_error = message[:max_len]
                 fields_to_update.append('last_sync_error')
            else:
                 # Optional: Fehler löschen, wenn Status nicht 'error' ist?
                 # account_to_update.last_sync_error = None
                 # fields_to_update.append('last_sync_error')
                 pass # Nur Status ändern

            account_to_update.save(update_fields=fields_to_update)
            logger.info(f"Updated account {account.id} status to '{status}' from sync_account. Error: {message if message else 'None'}")
    except EmailAccount.DoesNotExist:
         logger.warning(f"Account {account.id} not found during status update (sync_account). Status was '{status}'.")
    except Exception as e:
        logger.error(f"Failed to update status for account {account.id} from sync_account (target status '{status}'): {e}") 