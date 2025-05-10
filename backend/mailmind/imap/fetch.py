import logging
from typing import List, Iterable, Dict, Tuple, Optional
from imap_tools import MailBox, MailMessage, MailboxFolderSelectError, MailboxFetchError, A
from mailmind.core.models import EmailAccount
# Entferne nicht mehr existierende Imports
# from .store import save_email_metadata, save_full_email 
import time
# Importiere async_task zum Starten von Hintergrundtasks
from django_q.tasks import async_task 
import datetime # Import datetime
from imap_tools import MailMessageFlags # Import MailMessageFlags
import base64 # Import base64
import html2text # NEU: Importieren
# Importiere die Speicherfunktion
from .store import save_or_update_email_from_dict
# Importiere die Mapping-Funktion
from .mapper import map_full_email_to_db
from django.conf import settings # Import settings
# Importiere utils, um auf decode_email_header zuzugreifen, falls benötigt
from . import utils 

logger = logging.getLogger(__name__)

DEFAULT_METADATA_FETCH_ITEMS = ['UID', 'FLAGS', 'RFC822.SIZE', 'INTERNALDATE', 'ENVELOPE']
METADATA_BATCH_SIZE = 25 # Standard Batch-Größe für Metadaten
# Standard Batch-Größen, anpassbar über Settings
FULL_EMAIL_BATCH_SIZE = getattr(settings, 'IMAP_FULL_EMAIL_BATCH_SIZE', 50) # Z.B. 50 für volle E-Mails
MAX_BATCH_SIZE_BYTES = 10 * 1024 * 1024 # 10MB maximale Batch-Größe

def fetch_folder_uids(mailbox: MailBox, account: EmailAccount, folder_name: str, existing_uids_in_db: set) -> List[str]:
    """Selects a folder, fetches metadata including X-GM-LABELS, dispatches save tasks, and returns UIDs/Sizes."""
    start_time = time.time()
    logger.debug(f"Fetching UIDs and metadata for folder '{folder_name}'...")
    
    new_uids_to_fetch_full = []
    uids_metadata_to_save = []
    
    try:
        # Select folder
        select_start = time.time()
        mailbox.folder.set(folder_name)
        logger.debug(f"Folder '{folder_name}' selected successfully in {time.time() - select_start:.2f}s")
        
        # Fetch messages with metadata (Generator)
        # Explicitly request X-GM-LABELS along with other metadata
        fetch_parts = list(DEFAULT_METADATA_FETCH_ITEMS) # Start with defaults
        fetch_parts.append('X-GM-LABELS') # Add Gmail Labels
        # logger.debug(f"Fetching with parts: {fetch_parts}") # Nicht mehr benötigt
        
        fetch_start = time.time()
        # Entferne den fehlerhaften Parameter wieder. Vertraue darauf, dass Standard-Fetch reicht.
        # messages = mailbox.fetch(criteria='ALL', mail_parts=fetch_parts, mark_seen=False) # FALSCH
        # messages = mailbox.fetch(criteria='ALL', fetch_items=fetch_parts, mark_seen=False) # AUCH FALSCH
        # messages = mailbox.fetch(criteria='ALL', fetch_parts=fetch_parts, mark_seen=False) # AUCH FALSCH
        messages = mailbox.fetch(criteria='ALL', mark_seen=False, bulk=True) # Zurück zum Standard, bulk=True für Metadaten
        logger.debug(f"Initial fetch command completed in {time.time() - fetch_start:.2f}s. Iterating messages and dispatching save tasks...")

        # Iterate messages, dispatch save tasks, collect UIDs/Sizes
        process_start = time.time()
        uids_with_metadata = []
        message_count = 0
        for msg in messages:
            # Kombiniertes Log für Iteration und Dispatch
            logger.debug(f"---> Iterating and dispatching save task for UID {msg.uid}...") 
            message_count += 1
            try:
                # Collect UID and Size for later full fetch
                uid_data = {
                    'uid': msg.uid,
                    'size': msg.size_rfc822 or 0, 
                }
                uids_with_metadata.append(uid_data)

                # Extract X-GM-LABELS from headers
                # Header keys are case-insensitive in practice, but lowercase is safer
                x_gm_labels = None
                if msg.headers:
                    headers_lower = {k.lower(): v for k, v in msg.headers.items()}
                    x_gm_labels_tuple = headers_lower.get('x-gm-labels') # Returns a tuple
                    if x_gm_labels_tuple and isinstance(x_gm_labels_tuple, tuple):
                        # Take the first element if it's a tuple (usually contains the string)
                        x_gm_labels = x_gm_labels_tuple[0] 
                    elif isinstance(x_gm_labels_tuple, str): # Fallback if it's just a string
                         x_gm_labels = x_gm_labels_tuple
                
                logger.debug(f"UID {msg.uid} - X-GM-LABELS: {x_gm_labels}")

                # Extrahiere serialisierbare Daten für den Task
                # Konvertiere datetime zu ISO string, set zu list
                msg_dict_for_task = {
                    'uid': msg.uid,
                    'headers': dict(msg.headers) if msg.headers else {},
                    'subject': msg.subject,
                    'from_name': msg.from_values.name if msg.from_values else None,
                    'from_email': msg.from_values.email if msg.from_values else None,
                    'date_str': msg.date_str,
                    'date_iso': msg.date.isoformat() if isinstance(msg.date, datetime.datetime) else None,
                    'flags': list(msg.flags) if msg.flags else [],
                    'size_rfc822': msg.size_rfc822 or 0,
                    'x_gm_labels': x_gm_labels, # Füge die Labels hinzu
                }
                
                # Dispatch background task to save metadata
                async_task(
                    'mailmind.imap.tasks.save_metadata_task',
                    account_id=account.id,
                    folder_name=folder_name,
                    msg_dict=msg_dict_for_task 
                )
                
            except Exception as e:
                # Fehler beim Sammeln von UID/Size oder Dispatching
                logger.error(f"Error processing/dispatching metadata task for UID {msg.uid}: {e}", exc_info=True)
                continue
        
        logger.debug(f"Finished iterating and dispatching save tasks for {message_count} messages in {time.time() - process_start:.2f}s")
        logger.info(f"Collected UID/Size info for {len(uids_with_metadata)} messages from folder '{folder_name}' for later processing.")
        logger.debug(f"Total metadata iteration/dispatch completed in {time.time() - start_time:.2f}s")
        return uids_with_metadata # Gibt nur noch UID/Size zurück
    except Exception as e:
        logger.error(f"Error fetching UIDs/Metadata for folder '{folder_name}': {e}")
        raise

def calculate_batches(uids_with_metadata: List[dict], max_batch_size_bytes: int = 9.5 * 1024 * 1024, max_uids_per_batch: int = 50) -> List[List[dict]]:
    """Calculates optimal batches based on UID sizes and count."""
    if not uids_with_metadata:
        return []

    # Sort UIDs by size (largest first)
    sorted_uids = sorted(uids_with_metadata, key=lambda x: x['size'], reverse=True)
    batches = []
    current_batch = []
    current_batch_size = 0
    current_batch_count = 0 # Zähler für UIDs im Batch

    for uid_data in sorted_uids:
        size = uid_data['size']
        
        # If single UID is larger than max size, create single batch
        if size > max_batch_size_bytes:
            if current_batch:
                batches.append(current_batch)
            batches.append([uid_data])
            # Reset counters for next potential batch
            current_batch = []
            current_batch_size = 0
            current_batch_count = 0
            continue

        # If adding this UID would exceed batch size OR count, start new batch
        if (current_batch_size + size > max_batch_size_bytes) or (current_batch_count >= max_uids_per_batch):
            if current_batch:
                batches.append(current_batch)
            current_batch = [uid_data]
            current_batch_size = size
            current_batch_count = 1 # Starte Zählung für neuen Batch
        else:
            current_batch.append(uid_data)
            current_batch_size += size
            current_batch_count += 1 # Inkrementiere Zähler

    # Add remaining batch
    if current_batch:
        batches.append(current_batch)

    return batches

def fetch_uids_full(mailbox: MailBox, uids: List[str], account: EmailAccount, folder_name: str) -> Tuple[int, int]:
    """
    Fetches full email content for the given UIDs in batches and saves them directly using save_or_update_email_from_dict.

    Args:
        mailbox: The MailBox instance connected and folder selected.
        uids: A list of UIDs (strings) to fetch.
        account: The EmailAccount instance.
        folder_name: The name of the folder being processed.

    Returns:
        A tuple containing: (total_emails_processed, total_errors)
    """
    if not uids:
        logger.debug(f"fetch_uids_full: No UIDs to fetch for folder '{folder_name}'")
        return 0, 0

    batch_size = FULL_EMAIL_BATCH_SIZE
    logger.info(f"Fetching full content for {len(uids)} UIDs from '{folder_name}' in batches of {batch_size}...")

    total_emails_processed = 0 # Zählt erfolgreich *gespeicherte* Mails (vom Task gemeldet)
    total_errors = 0           # Zählt Fehler beim Holen/Mappen *vor* dem Speichern

    for i in range(0, len(uids), batch_size):
        batch_uids = uids[i:i + batch_size]
        current_batch_num = i // batch_size + 1
        total_batches = (len(uids) + batch_size - 1) // batch_size
        
        logger.info(f"--- Processing Batch {current_batch_num}/{total_batches} (UIDs: {batch_uids[:5]}...{batch_uids[-1:]}) ---")
        
        fetch_start_time = time.time()
        processed_in_batch = 0 # Zählt erfolgreich *geholte/gemappte* Mails in diesem Batch
        errors_in_batch = 0
        messages_generator = None
        batch_content_data = [] # <<< NEU: Liste zum Sammeln der Daten

        try:
            logger.debug(f"[{current_batch_num}] Calling mailbox.fetch for {len(batch_uids)} UIDs...")
            messages_generator = mailbox.fetch(A(uid=batch_uids), bulk=False, mark_seen=False)
            logger.debug(f"[{current_batch_num}] mailbox.fetch returned. Iterating...")
            
            received_uids_in_batch = []
            for msg in messages_generator:
                received_uids_in_batch.append(msg.uid)
                try:
                    logger.debug(f"[{current_batch_num}] Mapping UID: {msg.uid}") # Geändert von "Processing"
                    
                    # Step 1: Map data
                    db_data = map_full_email_to_db(msg, folder_name, account.email)
                    
                    # Step 2: Add mapped data to batch list <<< GEÄNDERT >>>
                    batch_content_data.append(db_data) 
                    processed_in_batch += 1
                    
                    # Entferne direkten Speicheraufruf
                    # save_or_update_email_from_dict(db_data, account, folder_name)

                except ValueError as e_map: # Errors from mapper (e.g., missing message_id)
                    logger.error(f"[{current_batch_num}] Mapping failed for UID {msg.uid}: {e_map}")
                    errors_in_batch += 1
                except Exception as e_proc: # Andere Fehler beim Verarbeiten einer einzelnen Mail
                    logger.error(f"[{current_batch_num}] Error processing email data for UID {msg.uid}: {e_proc}", exc_info=True)
                    errors_in_batch += 1
                
            # Optional: Check for missing UIDs in the response vs request
            if set(batch_uids) != set(received_uids_in_batch):
                 missing_uids = set(batch_uids) - set(received_uids_in_batch)
                 logger.warning(f"[{current_batch_num}] Mismatch between requested ({len(batch_uids)}) and received ({len(received_uids_in_batch)}) UIDs! Missing: {missing_uids}")

        except MailboxFetchError as e_fetch:
            logger.error(f"IMAP Fetch Error during batch {current_batch_num}: {e_fetch}", exc_info=True)
            # Assume all in this batch failed if the fetch itself fails
            errors_in_batch = len(batch_uids) - processed_in_batch 
        except Exception as e_batch:
            logger.error(f"Unexpected error during processing of batch {current_batch_num}: {e_batch}", exc_info=True)
             # Assume all remaining in this batch failed 
            errors_in_batch = len(batch_uids) - processed_in_batch
        finally:
            # Clean up generator if it exists and iteration was interrupted
            if messages_generator and hasattr(messages_generator, 'close'):
                 try:
                     messages_generator.close() # Ensure resources are released if loop breaks early
                 except Exception: pass # Ignore errors during close

            # total_emails_processed += processed_in_batch # Wird nicht mehr hier gezählt
            total_errors += errors_in_batch # Zähle nur Fehler *vor* dem Queuing
            batch_duration = time.time() - fetch_start_time
            logger.info(f"--- Finished FETCHING Batch {current_batch_num}/{total_batches} in {batch_duration:.2f}s. Mapped: {processed_in_batch}, Mapping Errors: {errors_in_batch} ---")

        # --- Step 3: Queue the batch content saving task <<< NEU/WICHTIG >>> ---
        if batch_content_data:
            try:
                logger.info(f"Enqueuing save_batch_content_task for Batch {current_batch_num} ({len(batch_content_data)} items)...")
                async_task('mailmind.imap.tasks.save_batch_content_task',
                           batch_content_data, 
                           account.id)
                logger.debug(f"Successfully enqueued save_batch_content_task for Batch {current_batch_num}.")
            except Exception as q_err:
                logger.error(f"Failed to enqueue save_batch_content_task for Batch {current_batch_num}: {q_err}", exc_info=True)
                # Markiere alle erfolgreich gemappten Mails dieses Batches als Fehler, da sie nicht gespeichert werden
                total_errors += len(batch_content_data)
        elif errors_in_batch > 0 and not batch_content_data:
             logger.warning(f"Batch {current_batch_num} resulted in {errors_in_batch} mapping errors and no data to queue.")
        else:
             logger.info(f"Batch {current_batch_num} resulted in no data to queue (likely empty fetch or all mapping errors).")
        # ---------------------------------------------------------------------

    # Anmerkung: total_emails_processed wird hier nicht mehr final geloggt, da das Speichern asynchron ist.
    # Der Hook könnte das Gesamtergebnis loggen oder den Account-Status aktualisieren.
    logger.info(f"=== Finished dispatching fetch/save tasks for folder '{folder_name}'. Total FETCH/MAP Errors: {total_errors} ===")
    # Return value needs reconsidering - we don't know the final processed count here.
    # Returning (0, total_errors) might be misleading. Maybe just return errors?
    return 0, total_errors # Temporär, bis Hook-Logik implementiert ist

def fetch_single_full_email(mailbox: MailBox, uid: str, account: EmailAccount, folder_name: str) -> Optional[Dict]:
    """
    Fetches the full content of a single email by UID and maps it.
    Used primarily by the IDLE process.
    """
    logger.debug(f"Fetching single full email UID {uid} from folder '{folder_name}'")
    # Initialize html2text converter
    h = html2text.HTML2Text()
    h.ignore_images = True
    h.body_width = 0
    messages = None
    try:
        # Fetch the single message
        fetch_criteria = A(uid=uid)
        logger.debug(f"Using fetch criteria: {fetch_criteria}")
        
        # Log raw fetch result before list conversion
        try:
            raw_messages_generator = mailbox.fetch(fetch_criteria, bulk=False, mark_seen=False)
            logger.debug(f"Raw fetch result (generator object): {raw_messages_generator}")
            # Using list() to force generator execution for a single item
            messages = list(raw_messages_generator)
            logger.debug(f"Fetched messages (after list conversion): Count={len(messages)}, Content Preview={messages[:1]}") # Log count and first item if exists
        except MailboxFetchError as e_fetch:
            logger.error(f"MailboxFetchError during fetch for UID {uid}: {e_fetch}", exc_info=True)
            messages = [] # Ensure messages is empty on fetch error
        except Exception as e_fetch_other:
            logger.error(f"Unexpected error during mailbox.fetch for UID {uid}: {e_fetch_other}", exc_info=True)
            messages = [] # Ensure messages is empty on other fetch error
        
        if not messages:
            logger.warning(f"Could not fetch email with UID {uid} from folder '{folder_name}'. Fetch result was empty.") # Added more detail
            return None
        
        msg = messages[0]
        
        # Map the data
        db_data = map_full_email_to_db(msg, folder_name, account.email)
        logger.debug(f"Successfully fetched and mapped single email UID {uid}.")
        return db_data

    except MailboxFetchError as e:
        logger.error(f"IMAP Fetch Error fetching single UID {uid}: {e}", exc_info=True)
        return None
    except ValueError as e_map: # Errors from mapper
        logger.error(f"Mapping failed for single UID {uid}: {e_map}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching single UID {uid}: {e}", exc_info=True)
        return None

def fetch_uids_metadata(mailbox: MailBox, uids: List[str], batch_size: int = METADATA_BATCH_SIZE) -> Iterable[MailMessage]:
    """Fetches metadata for a list of UIDs in batches, yielding MailMessage objects."""
    if not uids:
        logger.debug("fetch_uids_metadata called with empty UID list.")
        return

    logger.info(f"Fetching metadata for {len(uids)} UIDs in batches of {batch_size}...")
    
    # First, fetch all UIDs to ensure they exist
    try:
        logger.debug("Verifying all UIDs exist...")
        all_uids = mailbox.uids()
        valid_uids = [uid for uid in uids if uid in all_uids]
        logger.debug(f"Found {len(valid_uids)} valid UIDs out of {len(uids)} requested")
    except Exception as e:
        logger.error(f"Error verifying UIDs: {e}", exc_info=True)
        return

    # Then fetch metadata in batches
    for i in range(0, len(valid_uids), batch_size):
        batch_uids = valid_uids[i:i + batch_size]
        logger.debug(f"Fetching metadata batch {i//batch_size + 1}, UIDs: {batch_uids}")
        try:
            criteria = ','.join(batch_uids) 
            logger.debug(f"Fetching with criteria: {criteria}")
            
            for msg in mailbox.fetch(criteria=criteria, bulk=True):
                logger.debug(f"+++ Yielding msg for UID {msg.uid} +++")
                yield msg
                logger.debug(f"--- Finished yielding msg for UID {msg.uid} ---")
            logger.debug(f"Successfully fetched metadata batch {i//batch_size + 1}.")
        except MailboxFetchError as e_fetch:
            logger.error(f"Error fetching metadata batch {i//batch_size + 1} (UIDs: {batch_uids}): {e_fetch}", exc_info=True)
            continue 
        except Exception as e_batch:
            logger.error(f"Unexpected error during metadata fetch batch {i//batch_size + 1}: {e_batch}", exc_info=True)
            continue

    logger.info(f"Finished fetching metadata for {len(valid_uids)} UIDs.") 