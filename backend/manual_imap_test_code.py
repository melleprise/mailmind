import logging
import sys
from mailmind.core.models import EmailAccount
from mailmind.imap.connection import get_imap_connection
from imap_tools import A, MailboxFolderSelectError, MailboxFetchError
from mailmind.imap.mapper import map_full_email_to_db
from mailmind.imap.store import save_or_update_email_from_dict

# Kein Django-Setup hier, da es über manage.py shell läuft

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('manual_test')

ACCOUNT_ID = 1
FOLDER_NAME = 'INBOX'
# Verwende einen Standardwert, da sys.argv in exec nicht direkt funktioniert
UID_TO_TEST = '10' # Teste mit UID 37

logger.info(f'--- Manual Test for UID {UID_TO_TEST} Account {ACCOUNT_ID} Folder {FOLDER_NAME} ---')

try:
    account = EmailAccount.objects.get(id=ACCOUNT_ID)
    logger.info(f'Account found: {account.email}')

    with get_imap_connection(account) as mailbox:
        logger.info(f'Selecting folder: {FOLDER_NAME}')
        folder_status = ('ERROR', []) # Default status
        try:
            folder_status = mailbox.folder.set(FOLDER_NAME)
            logger.info(f'Folder selected. Status: {folder_status}')
        except MailboxFolderSelectError as e_select:
            logger.error(f'Failed to select folder {FOLDER_NAME}: {e_select}')
            # Lasse folder_status auf ERROR

        if folder_status[0] == 'OK': # Nur testen wenn Ordner OK
            # --- NOOP Test (ignoriert Fehler, da Methode nicht existiert) ---
            logger.info("Attempting NOOP command...")
            try:
                # Versuche über das client-Attribut zuzugreifen
                if hasattr(mailbox, 'client'):
                     noop_status, noop_data = mailbox.client.noop()
                     logger.info(f"NOOP response: Status={noop_status}, Data={noop_data}")
                else:
                    logger.warning("Mailbox object has no 'client' attribute for NOOP.")
            except Exception as e_noop:
                logger.warning(f"Error sending NOOP via client: {e_noop}")
            # --- ENDE NOOP Test ---

            # Test 1: mailbox.uids()
            logger.info(f"Testing mailbox.uids(criteria='UID {UID_TO_TEST}')")
            try:
                uids_result = mailbox.uids(criteria=f'UID {UID_TO_TEST}')
                logger.info(f'mailbox.uids() result: {uids_result}')
                if UID_TO_TEST in uids_result:
                    logger.info(f'UID {UID_TO_TEST} FOUND via mailbox.uids()')
                else:
                    logger.warning(f'UID {UID_TO_TEST} NOT FOUND via mailbox.uids()')
            except Exception as e_uids:
                logger.error(f'Error during mailbox.uids(): {e_uids}') 

            # Test 2: mailbox.fetch()
            logger.info(f"Testing mailbox.fetch(A(uid='{UID_TO_TEST}'), bulk=False, mark_seen=False)")
            try:
                # Fetch returns a generator, convert to list to see results
                messages = list(mailbox.fetch(A(uid=UID_TO_TEST), bulk=False, mark_seen=False))
                logger.info(f'mailbox.fetch() result count: {len(messages)}')
                if messages:
                    msg = messages[0]
                    subject = getattr(msg, 'subject', '[No Subject]')
                    logger.info(f"UID {UID_TO_TEST} FOUND via mailbox.fetch(). Subject: {subject}")
                    
                    # --- NEU: Mapping und Speichern --- 
                    logger.info(f"Attempting to map email data for UID {UID_TO_TEST}...")
                    db_data = None
                    try:
                        db_data = map_full_email_to_db(msg, FOLDER_NAME, account.email)
                        logger.info(f"Successfully mapped data for UID {UID_TO_TEST}.")
                    except ValueError as e_map:
                        logger.error(f"Mapping failed for UID {UID_TO_TEST}: {e_map}")
                    except Exception as e_map_other:
                         logger.error(f"Unexpected error during mapping for UID {UID_TO_TEST}: {e_map_other}", exc_info=True)

                    if db_data:
                        logger.info(f"Attempting to save email data for UID {UID_TO_TEST}...")
                        try:
                            save_or_update_email_from_dict(db_data, account, FOLDER_NAME)
                            logger.info(f"Successfully saved/updated data for UID {UID_TO_TEST}.")
                        except Exception as e_save:
                            logger.error(f"Error saving/updating data for UID {UID_TO_TEST}: {e_save}", exc_info=True)
                    # --- ENDE NEU ---
                else:
                    logger.warning(f'UID {UID_TO_TEST} NOT FOUND via mailbox.fetch()')
            except MailboxFetchError as e_fetch:
                 logger.error(f'MailboxFetchError during fetch: {e_fetch}')
            except Exception as e_fetch_other:
                 logger.error(f'Unexpected error during fetch: {e_fetch_other}', exc_info=True)
        else:
            logger.error("Folder selection failed, skipping IMAP tests.")

except EmailAccount.DoesNotExist:
    logger.error(f'Account with ID {ACCOUNT_ID} not found.')
except Exception as e:
    logger.error(f'An overall error occurred: {e}', exc_info=True)

logger.info('--- Manual Test End ---') 