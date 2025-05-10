import logging
import sys
from mailmind.core.models import EmailAccount
from mailmind.imap.connection import get_imap_connection
from imap_tools import A, MailboxFolderSelectError, MailboxFetchError
import os
# Django setup is needed if running as a standalone script
# If manage.py shell is used, this might not be strictly necessary, but safer
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development') 
try:
    import django
    django.setup()
except ImportError:
     print("Django not found or setup failed.")
     sys.exit(1)


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('manual_test')

ACCOUNT_ID = 1
FOLDER_NAME = 'INBOX'
# Take UID from command line argument if provided, otherwise use default
UID_TO_TEST = sys.argv[1] if len(sys.argv) > 1 else '35' 

logger.info(f'--- Manual Test for UID {UID_TO_TEST} Account {ACCOUNT_ID} Folder {FOLDER_NAME} ---')

try:
    account = EmailAccount.objects.get(id=ACCOUNT_ID)
    logger.info(f'Account found: {account.email}')

    with get_imap_connection(account) as mailbox:
        logger.info(f'Selecting folder: {FOLDER_NAME}')
        try:
            status = mailbox.folder.set(FOLDER_NAME)
            logger.info(f'Folder selected. Status: {status}')
        except MailboxFolderSelectError as e_select:
            logger.error(f'Failed to select folder {FOLDER_NAME}: {e_select}')
            sys.exit(1)

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
                # Access attributes safely
                subject = getattr(messages[0], 'subject', '[No Subject]')
                logger.info(f"UID {UID_TO_TEST} FOUND via mailbox.fetch(). Subject: {subject}")
            else:
                logger.warning(f'UID {UID_TO_TEST} NOT FOUND via mailbox.fetch()')
        except MailboxFetchError as e_fetch:
             logger.error(f'MailboxFetchError during fetch: {e_fetch}')
        except Exception as e_fetch_other:
             logger.error(f'Unexpected error during fetch: {e_fetch_other}', exc_info=True)

except EmailAccount.DoesNotExist:
    logger.error(f'Account with ID {ACCOUNT_ID} not found.')
except Exception as e:
    logger.error(f'An overall error occurred: {e}', exc_info=True)

logger.info('--- Manual Test End ---') 