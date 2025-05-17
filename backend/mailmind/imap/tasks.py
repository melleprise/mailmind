import logging
import time
import socket
import imaplib
from django.utils import timezone
from django_q.tasks import async_task, Task
from mailmind.core.models import EmailAccount, Email
from .connection import get_imap_connection
from .fetch import fetch_uids_full, fetch_single_full_email
from .store import save_or_update_email_from_dict, save_email_content_from_dict
from imap_tools import MailboxFolderSelectError, MailboxFetchError, MailboxLoginError
from typing import List, Dict, Any, Optional
from django.db import transaction
from .utils import FOLDER_PRIORITIES
import html2text
from django.conf import settings
import re # Importiere das re Modul

logger = logging.getLogger(__name__)

# Konstante für den Ordner-Update-Timeout
FOLDER_UPDATE_TIMEOUT = 30 * 60 # 30 Minuten

# --- Retry Konstanten für IDLE Task ---
IDLE_FETCH_RETRIES = 3
IDLE_FETCH_DELAY = 7 # Sekunden (Erhöht)

@transaction.atomic
def process_folder_metadata_task(account_id: int, folder_name: str):
    """
    Task to fetch all UIDs for a folder and then fetch their full content.
    This is the main task for initial/full folder synchronization.
    """
    start_time = time.time()
    logger.info(f"--- Starting INITIAL sync for folder '{folder_name}' account {account_id} ---")
    account = None
    all_uids = []
    total_processed = 0
    total_errors = 0

    try:
        account = EmailAccount.objects.get(id=account_id)
        logger.debug(f"Fetched account {account.email} for task.")

        with get_imap_connection(account) as mailbox:
            logger.debug(f"Selecting folder '{folder_name}'...")
            mailbox.folder.set(folder_name)
            logger.debug(f"Folder '{folder_name}' selected successfully.")

            fetch_uids_start = time.time()
            all_uids = mailbox.uids(criteria='ALL', charset='UTF-8')
            fetch_uids_duration = time.time() - fetch_uids_start
            logger.info(f"Fetched {len(all_uids)} UIDs from '{folder_name}' in {fetch_uids_duration:.2f}s.")

            if all_uids:
                total_processed, total_errors = fetch_uids_full(mailbox, all_uids, account, folder_name)
            else:
                logger.info(f"No emails found in folder '{folder_name}'. Skipping full fetch.")

        if total_errors > 0:
             logger.warning(f"Folder sync '{folder_name}' completed with {total_errors} errors.")
        else:
             logger.info(f"Folder sync '{folder_name}' completed without errors reported by fetch_uids_full.")

    except MailboxLoginError as e_login:
        logger.error(f"Login failed for account {account_id}: {e_login}")
        if account: _update_account_status(account, 'error', "Login Failed")
    except MailboxFolderSelectError as e_select:
        logger.error(f"Error selecting folder '{folder_name}' for account {account_id}: {e_select}", exc_info=True)
        if account: _update_account_status(account, 'error', f"Folder Error: {folder_name}")
    except MailboxFetchError as e_fetch:
        logger.error(f"Error fetching UIDs from '{folder_name}' for account {account_id}: {e_fetch}", exc_info=True)
        if account: _update_account_status(account, 'error', f"Fetch UIDs Error: {folder_name}")
    except EmailAccount.DoesNotExist:
        logger.error(f"Account with ID {account_id} not found.")
    except Exception as e:
        logger.error(f"Unexpected error processing folder '{folder_name}' for account {account_id}: {e}", exc_info=True)
        if account: _update_account_status(account, 'error', f"Unexpected Error: {folder_name}")
    finally:
        duration = time.time() - start_time
        logger.info(f"--- Finished INITIAL sync for '{folder_name}' account {account_id} in {duration:.2f}s. Processed: {total_processed}, Errors: {total_errors} ---")

def process_individual_email_task(account_id: int, folder_name: str, uid: str):
    """Processes a single email, fetching its full content."""
    try:
        account = EmailAccount.objects.get(id=account_id)
        logger.info(f"--- Starting FULL fetch for account {account_id}, folder '{folder_name}', UID {uid} ---")

        with get_imap_connection(account) as mailbox:
            try:
                logger.debug(f"Selecting folder '{folder_name}' for full fetch UID {uid}")
                mailbox.folder.set(folder_name)
                
                logger.info(f"Fetching full content for UID {uid}...")
                total_processed, total_errors = fetch_uids_full(mailbox, [uid], account, folder_name)

                if total_errors > 0:
                    logger.error(f"Error during full fetch for individual UID {uid}. See fetch_uids_full logs.")
                    raise MailboxFetchError(f"Failed to fetch full content for UID {uid}")

                logger.info(f"--- Finished FULL fetch for account {account_id}, folder '{folder_name}', UID {uid}. Status: processed ---")
            
            except (MailboxFolderSelectError, MailboxFetchError) as e_imap:
                 logger.error(f"IMAP error processing individual email UID {uid}: {e_imap}", exc_info=True)
                 raise
            except Exception as e:
                 logger.error(f"Unexpected error processing individual email UID {uid}: {e}", exc_info=True)
                 raise

    except MailboxLoginError as e_login:
        logger.error(f"Login failed for account {account_id} in individual task: {e_login}")
        if account: _update_account_status(account, 'error', "Login Failed")
    except EmailAccount.DoesNotExist:
         logger.error(f"Account {account_id} not found for process_individual_email_task.")
    except Exception as e:
        logger.error(f"Outer error in process_individual_email_task for UID {uid}: {e}", exc_info=True)
        try:
            account_final = EmailAccount.objects.get(id=account_id)
            error_msg_short = str(e)[:200]
            _update_account_status(account_final, 'error', f"Error processing UID {uid}: {error_msg_short}")
        except EmailAccount.DoesNotExist:
             pass
        except Exception as e_status:
            logger.error(f"Failed to update account status after error processing UID {uid}: {e_status}")

def process_idle_update_task(account_id: int, uid: str, folder_name: str):
    """
    Task triggered by IDLE manager to fetch and save a single new email.
    Includes retries for fetch issues.
    """
    start_time = time.time()
    logger.info(f"--- Starting IDLE update task for UID {uid}, Folder '{folder_name}', Account {account_id} ---")
    account = None
    mailbox = None # Initialize mailbox
    db_data = None # Initialize db_data
    success = False

    try:
        # Get account details
        account = EmailAccount.objects.get(id=account_id)
        logger.debug(f"Fetched account {account.email} for IDLE update.")
        logger.debug(f"Incoming UID: {uid} (Type: {type(uid)})")

        # Get connection using the context manager
        with get_imap_connection(account) as mailbox:
            # Select folder
            try:
                 logger.debug(f"IDLE: Ensuring folder '{folder_name}' is selected...")
                 select_status = mailbox.folder.set(folder_name)
                 logger.debug(f"IDLE: Folder '{folder_name}' selected. Status: {select_status}")
                 # Kurze initiale Wartezeit (kann helfen)
                 logger.debug("Initial wait 1 second before checking/fetching...")
                 time.sleep(1)
            except MailboxFolderSelectError as e_select:
                 logger.error(f"IDLE: Error selecting folder '{folder_name}' for account {account_id}: {e_select}", exc_info=True)
                 _update_account_status(account, 'error', f"IDLE Folder Error: {folder_name}")
                 return # Exit if folder selection fails

            # --- Retry Loop for UID Check and Fetch --- 
            for attempt in range(1, IDLE_FETCH_RETRIES + 1):
                logger.info(f"Attempt {attempt}/{IDLE_FETCH_RETRIES} to check and fetch UID {uid}...")
                # Entferne uid_visible Flag und spezifischen Check
                db_data = None # Reset for this attempt
                fetch_successful = False
                try:
                    # 1. Hole ALLE UIDs im Ordner
                    logger.debug(f"[{attempt}] Fetching ALL UIDs in folder '{folder_name}'...")
                    all_uids_in_folder_list = mailbox.uids(criteria='ALL', charset='UTF-8')
                    if all_uids_in_folder_list:
                        logger.debug(f"[{attempt}] Type of first UID from mailbox.uids(): {type(all_uids_in_folder_list[0])}")
                    all_uids_in_folder = set(all_uids_in_folder_list) # Umwandlung in Set für schnelle Prüfung
                    logger.debug(f"[{attempt}] Found {len(all_uids_in_folder)} UIDs in folder.")

                    # 2. Prüfe, ob die gesuchte UID dabei ist
                    if uid in all_uids_in_folder:
                        logger.info(f"[{attempt}] Target UID {uid} IS VISIBLE within all fetched UIDs.")
                        # 3. Fetch die spezifische UID
                        logger.debug(f"[{attempt}] Attempting to fetch single email UID {uid}...")
                        db_data = fetch_single_full_email(mailbox, uid, account, folder_name)
                        
                        if db_data:
                            logger.info(f"[{attempt}] Successfully fetched data for UID {uid}.")
                            fetch_successful = True
                            break # Exit retry loop on successful fetch
                        else:
                            logger.warning(f"[{attempt}] fetch_single_full_email returned None for UID {uid} although it was in the initial UID list.")
                            # Bleibe in der Schleife, um es erneut zu versuchen
                    else:
                         logger.warning(f"[{attempt}] Target UID {uid} IS NOT VISIBLE in the list of all UIDs ({len(all_uids_in_folder)} found). Retrying...")
                         logger.debug(f"[{attempt}] Contents of all_uids_in_folder set: {all_uids_in_folder}")
                         # Bleibe in der Schleife, um es erneut zu versuchen

                except MailboxFetchError as e_fetch_attempt:
                     logger.warning(f"[{attempt}] MailboxFetchError during fetch attempt for UID {uid}: {e_fetch_attempt}")
                except Exception as e_attempt:
                    logger.error(f"[{attempt}] Unexpected error checking/fetching UID {uid}: {e_attempt}", exc_info=True)
                
                # If not successful and not the last attempt, wait before retrying
                if not fetch_successful and attempt < IDLE_FETCH_RETRIES:
                    logger.info(f"[{attempt}] UID {uid} not fetched successfully, waiting {IDLE_FETCH_DELAY}s before next attempt...")
                    time.sleep(IDLE_FETCH_DELAY)
            # --- End Retry Loop ---

            # Process data if fetch was eventually successful
            if fetch_successful and db_data: # Check both flags
                try:
                    save_or_update_email_from_dict(db_data, account, folder_name)
                    success = True # Mark as successful only after saving
                except Exception as e_save:
                     logger.error(f"IDLE: Error saving email data for UID {uid} after successful fetch: {e_save}", exc_info=True)
                     _update_account_status(account, 'error', f"IDLE Save Error UID: {uid}")
            else:
                logger.error(f"IDLE: Failed to fetch email data for UID {uid} after {IDLE_FETCH_RETRIES} attempts. Cannot save.")
                _update_account_status(account, 'error', f"IDLE Fetch Failed UID: {uid} after retries")

    except MailboxLoginError as e_login:
        logger.error(f"IDLE: Login failed for account {account_id}: {e_login}")
        if account: _update_account_status(account, 'error', "IDLE Login Failed")
    except EmailAccount.DoesNotExist:
        logger.error(f"IDLE: Account with ID {account_id} not found.")
    except Exception as e:
        logger.error(f"IDLE: Unexpected error processing update for UID {uid}, Account {account_id}: {e}", exc_info=True)
        if account and not success: # Only set error status if not already successful
            _update_account_status(account, 'error', f"IDLE Unexpected Error UID: {uid}")
    finally:
        duration = time.time() - start_time
        status_msg = "successful" if success else "failed"
        logger.info(f"--- Finished IDLE update task for UID {uid}, Account {account_id} in {duration:.2f}s (Status: {status_msg}) ---")

def _update_account_status(account: EmailAccount, status: str, message: Optional[str] = None):
    """Helper to update account status and log it."""
    if not account:
        logger.error(f"Attempted to update status '{status}' but account object was None.")
        return
    try:
        # Re-fetch the account to avoid potential state issues
        account_to_update = EmailAccount.objects.get(id=account.id)
        account_to_update.sync_status = status
        account_to_update.last_sync = timezone.now()
        if message:
             # Ensure message fits in the field
             max_len = EmailAccount._meta.get_field('last_sync_error').max_length
             account_to_update.last_sync_error = message[:max_len]
        else:
            account_to_update.last_sync_error = None

        fields_to_update = ['sync_status', 'last_sync', 'last_sync_error']
        account_to_update.save(update_fields=fields_to_update)
        logger.info(f"Updated account {account.id} status to '{status}'. Error: {message if message else 'None'}")
    except EmailAccount.DoesNotExist:
         logger.warning(f"Account {account.id} not found during status update. Status was '{status}'.")
    except Exception as e:
        logger.error(f"Failed to update status for account {account.id} (target status '{status}'): {e}")

def generate_markdown_for_email_task(email_id: int):
    """Generates markdown from HTML content for a given email ID and saves it."""
    try:
        email_instance = Email.objects.get(id=email_id)
        logger.debug(f"Starting markdown generation for email ID: {email_id}")
        logger.info(f"Markdown-Trigger: body_html vorhanden: {bool(email_instance.body_html)}, body_text vorhanden: {bool(email_instance.body_text)}")
        if not email_instance.body_html:
            logger.debug(f"No HTML body found for email {email_id}. Checking for body_text.")
            if email_instance.body_text:
                 logger.info(f"Markdown-Entscheidung: Kein HTML, aber body_text vorhanden. Kopiere body_text als Markdown.")
                 email_instance.markdown_body = email_instance.body_text
                 logger.info(f"No HTML body for email {email_id}, copied body_text to markdown_body.")
            else:
                 logger.info(f"Markdown-Entscheidung: Weder HTML noch body_text vorhanden. Setze Markdown leer.")
                 email_instance.markdown_body = ""
                 logger.debug(f"No HTML or Text body found for email {email_id}, setting empty markdown.")
            email_instance.save(update_fields=['markdown_body'])
            return

        h = html2text.HTML2Text()
        h.ignore_images = True
        h.body_width = 0
        h.ignore_emphasis = False
        h.ignore_links = False
        h.single_line_break = True

        markdown_raw = h.handle(email_instance.body_html).strip()

        # --- Post-Processing: Füge Leerzeilen zwischen Absätzen ein, aber nicht in Listen oder Links ---
        def add_blank_lines(md):
            lines = md.replace('\r\n', '\n').replace('\r', '\n').split('\n')
            new_lines = []
            prev_blank = True
            for i, line in enumerate(lines):
                stripped = line.strip()
                # Wenn aktuelle Zeile nicht leer und vorherige auch nicht, Leerzeile einfügen
                if stripped and not prev_blank:
                    # Keine Leerzeile zwischen Listeneinträgen
                    if not (line.lstrip().startswith(('-', '*', '+')) or
                            (new_lines and new_lines[-1].lstrip().startswith(('-', '*', '+')))):
                        new_lines.append('')
                new_lines.append(line)
                prev_blank = not stripped
            return '\n'.join(new_lines)

        markdown_processed = add_blank_lines(markdown_raw)
        # Maximal zwei Leerzeilen hintereinander
        markdown_processed = re.sub(r'\n{3,}', '\n\n', markdown_processed).strip()

        logger.info(f"Markdown-Entscheidung: HTML vorhanden, Markdown wird erzeugt und gespeichert.")
        email_instance.markdown_body = markdown_processed
        email_instance.save(update_fields=['markdown_body'])
        logger.info(f"Successfully generated and saved markdown for email ID: {email_id}")

    except Email.DoesNotExist:
        logger.error(f"Markdown generation failed: Email with ID {email_id} not found.")
    except Exception as e:
        logger.error(f"Error generating markdown for email ID {email_id}: {e}", exc_info=True)

# Task to save content for a batch of emails
def save_batch_content_task(batch_data: List[Dict[str, Any]], account_id: int):
    """Saves the content (body, attachments) for a batch of emails."""
    logger.info(f"!!! Task save_batch_content_task RECEIVED for account {account_id}, batch size: {len(batch_data)} !!!")
    start_time = time.time()
    processed_count = 0
    error_count = 0
    account = None
    try:
        account = EmailAccount.objects.get(id=account_id)
        logger.info(f"Starting save_batch_content_task for account {account_id}, batch size: {len(batch_data)}")
        for email_content_dict in batch_data:
            try:
                # Ruft jetzt die modifizierte Funktion in store.py auf, die update_or_create verwendet
                save_email_content_from_dict(email_content_dict, account)
                processed_count += 1
            except Exception as e:
                # Fehlermeldung sollte jetzt von save_email_content_from_dict kommen
                # Hier nur noch zählen oder allgemeinen Fehler loggen?
                logger.error(f"Error processing one email in save_batch_content_task for account {account_id}: {e}", exc_info=True)
                error_count += 1
    except EmailAccount.DoesNotExist:
        logger.error(f"Account {account_id} not found for save_batch_content_task.")
        error_count = len(batch_data) # Alle als Fehler zählen
    except Exception as e:
        logger.error(f"Unexpected error in save_batch_content_task for account {account_id}: {e}", exc_info=True)
        error_count = len(batch_data) # Alle als Fehler zählen
    finally:
        duration = time.time() - start_time
        logger.info(f"Finished save_batch_content_task for account {account_id}. Processed: {processed_count}, Errors: {error_count}. Duration: {duration:.2f}s")

# --- NEUE TASK für IDLE Update --- 
@transaction.atomic # Verwende Transaktion für Konsistenz
def sync_folder_on_idle_update(account_id: int, folder_name: str):
    """Task triggered by IDLE manager to fetch ALL missing emails in a folder."""
    start_time = time.time()
    logger.info(f"--- Starting IDLE SYNC for folder '{folder_name}' account {account_id} ---")
    account = None
    server_uids = set()
    local_uids = set()
    missing_uids = set()
    total_processed = 0
    total_errors = 0

    try:
        account = EmailAccount.objects.get(id=account_id)
        logger.debug(f"IDLE SYNC: Fetched account {account.email} for task.")

        with get_imap_connection(account) as mailbox:
            logger.debug(f"IDLE SYNC: Selecting folder '{folder_name}'...")
            mailbox.folder.set(folder_name)
            logger.debug(f"IDLE SYNC: Folder '{folder_name}' selected successfully.")

            # 1. Fetch all UIDs from server
            fetch_server_uids_start = time.time()
            server_uids_list = mailbox.uids(criteria='ALL', charset='UTF-8')
            server_uids = set(server_uids_list)
            fetch_server_uids_duration = time.time() - fetch_server_uids_start
            logger.info(f"IDLE SYNC: Fetched {len(server_uids)} UIDs from server folder '{folder_name}' in {fetch_server_uids_duration:.2f}s.")

            # 2. Fetch all UIDs from local DB
            fetch_local_uids_start = time.time()
            local_uids = set(Email.objects.filter(account_id=account_id, folder_name=folder_name).values_list('uid', flat=True))
            fetch_local_uids_duration = time.time() - fetch_local_uids_start
            logger.info(f"IDLE SYNC: Fetched {len(local_uids)} UIDs from local DB for folder '{folder_name}' in {fetch_local_uids_duration:.2f}s.")

            # 3. Calculate missing UIDs
            missing_uids = server_uids - local_uids
            logger.info(f"IDLE SYNC: Calculated {len(missing_uids)} missing UIDs for folder '{folder_name}'.")
            if missing_uids:
                 logger.debug(f"IDLE SYNC: Missing UIDs: {list(missing_uids)[:20]}...") # Log first 20
                 # 4. Fetch full content for missing UIDs using the existing function
                 total_processed, total_errors = fetch_uids_full(mailbox, list(missing_uids), account, folder_name)
                 logger.info(f"IDLE SYNC: fetch_uids_full processed {total_processed} missing emails with {total_errors} errors.")
            else:
                logger.info(f"IDLE SYNC: No missing UIDs found in folder '{folder_name}'. Nothing to fetch.")
                total_processed = 0
                total_errors = 0

        # Optional: Update Status? Hier nicht unbedingt nötig, da es nur ein Update ist.
        # if total_errors > 0:
        #      logger.warning(f"IDLE SYNC for '{folder_name}' completed with {total_errors} errors.")

    except MailboxLoginError as e_login:
        logger.error(f"IDLE SYNC: Login failed for account {account_id}: {e_login}")
        if account: _update_account_status(account, 'error', "IDLE Sync Login Failed")
    except MailboxFolderSelectError as e_select:
        logger.error(f"IDLE SYNC: Error selecting folder '{folder_name}' for account {account_id}: {e_select}", exc_info=True)
        if account: _update_account_status(account, 'error', f"IDLE Sync Folder Error: {folder_name}")
    except MailboxFetchError as e_fetch:
        logger.error(f"IDLE SYNC: Error fetching data from '{folder_name}' for account {account_id}: {e_fetch}", exc_info=True)
        if account: _update_account_status(account, 'error', f"IDLE Sync Fetch Error: {folder_name}")
    except EmailAccount.DoesNotExist:
        logger.error(f"IDLE SYNC: Account with ID {account_id} not found.")
    except Exception as e:
        logger.error(f"IDLE SYNC: Unexpected error processing folder '{folder_name}' for account {account_id}: {e}", exc_info=True)
        if account: _update_account_status(account, 'error', f"IDLE Sync Unexpected Error: {folder_name}")
    finally:
        duration = time.time() - start_time
        logger.info(f"--- Finished IDLE SYNC for '{folder_name}' account {account_id} in {duration:.2f}s. Fetched: {total_processed}, Errors: {total_errors} ---")