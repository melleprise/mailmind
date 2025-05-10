import email
from email.utils import parseaddr, parsedate_to_datetime
from email.header import decode_header, make_header
import logging
import re
import imaplib
import time
from typing import List, Dict, Any, Optional, Tuple, Union
from django.conf import settings
from ..core.models import EmailAccount, Email
from cryptography.fernet import Fernet
from datetime import datetime, timedelta
from django.db import transaction
from django.utils import timezone
import threading

# Mapping von IMAP-Ordnernamen zu Standardtypen
FOLDER_TYPE_MAP = {
    "sent": "[Gmail]/Sent Mail",
    "drafts": "[Gmail]/Drafts",
    "spam": "[Gmail]/Spam",
    "trash": "[Gmail]/Trash",
    "inbox": "[Gmail]/Inbox",
    "all": "[Gmail]/All Mail"
}

# Prioritäten für Ordner (niedrigere Zahl = höhere Priorität)
FOLDER_PRIORITIES: Dict[str, int] = {
    "INBOX": 1,
    "Sent": 2,
    "Drafts": 3,
    "Archive": 4,
    "Junk": 5,
    "Spam": 5, 
    "Trash": 6,
    "Sent Mail": 100,
    "Sent": 100,
    "Spam": -10,
    "Junk": -10,
    "Deleted": -20,
    "__default__": -1
}

# Behalte nur die allgemeinen Hilfsfunktionen

logger = logging.getLogger(__name__)

# Helper function to extract email addresses from a header string
EMAIL_REGEX = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')

# Rate-Limiting Einstellungen
RATE_LIMIT = {
    'requests_per_minute': 48,  # 80% von 60 Requests/Minute
    'min_delay': 1.25,  # Mindestverzögerung zwischen Requests in Sekunden
}

# Thread-lokaler Speicher für Rate-Limiting
_rate_limit_lock = threading.Lock()
_last_request_time = {}
_request_count = {}
_request_window_start = {}

def _check_rate_limit(account_id: int) -> None:
    """Überprüft und wartet bei Bedarf für Rate-Limiting."""
    current_time = time.time()
    
    with _rate_limit_lock:
        if account_id not in _last_request_time:
            _last_request_time[account_id] = 0
            _request_count[account_id] = 0
            _request_window_start[account_id] = current_time
        
        # Prüfe ob wir in einem neuen Zeitfenster sind
        if current_time - _request_window_start[account_id] >= 60:
            _request_count[account_id] = 0
            _request_window_start[account_id] = current_time
        
        # Warte wenn nötig
        time_since_last = current_time - _last_request_time[account_id]
        if time_since_last < RATE_LIMIT['min_delay']:
            time.sleep(RATE_LIMIT['min_delay'] - time_since_last)
        
        # Prüfe ob wir das Limit erreicht haben
        if _request_count[account_id] >= RATE_LIMIT['requests_per_minute']:
            wait_time = 60 - (current_time - _request_window_start[account_id])
            if wait_time > 0:
                time.sleep(wait_time)
            _request_count[account_id] = 0
            _request_window_start[account_id] = time.time()
        
        _last_request_time[account_id] = time.time()
        _request_count[account_id] += 1

def decode_email_header(header_value: Optional[str]) -> str:
    """E-Mail-Header dekodieren."""
    if not header_value:
        return ""
    
    decoded_parts = []
    for part, charset in decode_header(header_value):
        if isinstance(part, bytes):
            try:
                decoded_parts.append(part.decode(charset or 'utf-8', errors='replace'))
            except (LookupError, TypeError):
                decoded_parts.append(part.decode('utf-8', errors='replace'))
        else:
            decoded_parts.append(str(part))
    
    return ' '.join(decoded_parts)

# Hinweis: extract_email_addresses_from_values wurde nicht mehr verwendet,
# da die Kontakt-Erstellung jetzt direkt in store.py mit den MailAddress-Objekten arbeitet.
# Daher wurde sie entfernt.

# Hinweis: get_email_body_from_data wurde nicht mehr verwendet,
# da map_full_email_to_db direkt auf msg.text/msg.html zugreift.
# Daher wurde sie entfernt.

# Hinweis: process_attachments_from_data wurde nach store.py verschoben (_process_attachments).

# Hinweis: serialize_message_data und serialize_address_list sind nicht mehr notwendig,
# da die neuen Tasks direkt UIDs übergeben und die Daten selbst fetchen.
# Daher wurden sie entfernt.

# Hinweis: process_new_email, process_individual_email_task, 
# process_folder_task, save_email_metadata wurden in die neuen Dateien 
# store.py und tasks.py verschoben/umstrukturiert.
# Daher wurden sie entfernt. 

def sync_account(account: EmailAccount) -> None:
    """Synchronisiert E-Mails für ein Konto mit Rate-Limiting."""
    try:
        _check_rate_limit(account.id)
        
        # Verbindung aufbauen
        imap_server = imaplib.IMAP4_SSL(account.imap_server)
        imap_server.login(account.email, account.decrypt_password())
        
        # Select the default mailbox
        # TODO: Make the default mailbox configurable or smarter
        imap_server.select('[Gmail]/All Mail')
        logger.info(f"Selected mailbox: [Gmail]/All Mail")
        
        # Fetch UIDs
        _, message_numbers = imap_server.search(None, 'ALL')
        
        for num in message_numbers[0].split():
            _check_rate_limit(account.id)  # Rate-Limit vor jedem Request prüfen
            _, msg_data = imap_server.fetch(num, '(RFC822)')
            # ... Rest der Verarbeitung ...
        
        imap_server.close()
        imap_server.logout()
        
    except Exception as e:
        logger.error(f"Fehler beim Synchronisieren von {account.email}: {str(e)}")
        raise 

def rate_limit_check(account_id: int, operation: str, limit: int = 5, period: int = 60) -> bool:
    # ... (existing code)
    pass

def get_email_domain(email_address: str) -> Optional[str]:
    # ... (existing code)
    pass

def map_folder_name_to_server(account: EmailAccount, logical_folder: str) -> Optional[str]:
    """Maps a logical folder name (like 'Spam') to the likely server-side name.

    This is a basic implementation and might need adjustments based on specific providers.
    Args:
        account: The EmailAccount instance (provider info might be relevant later).
        logical_folder: The logical folder name ('Spam', 'Trash', 'Archive', 'Sent', 'Drafts').

    Returns:
        The potential server folder name or None if mapping fails.
    """
    logical_folder_lower = logical_folder.lower()
    provider = account.provider.lower() if account.provider else "unknown"

    # Provider-specific mappings (Example for Gmail)
    if provider == 'gmail':
        if logical_folder_lower == 'spam':
            return '[Gmail]/Spam'
        elif logical_folder_lower == 'trash':
            return '[Gmail]/Trash'
        elif logical_folder_lower == 'sent':
            return '[Gmail]/Sent Mail'
        elif logical_folder_lower == 'drafts':
            return '[Gmail]/Drafts'
        elif logical_folder_lower == 'archive':
            # Gmail doesn't have a dedicated Archive folder, moving removes Inbox label.
            # For MOVE operation, target might be tricky. Often handled by removing flags.
            # Returning None might be safer for MOVE, or handle archive via flags.
            logger.warning(f"Gmail 'Archive' mapping for MOVE is ambiguous. Returning None.")
            return None 
        # Add other Gmail specific mappings if needed

    # General mappings (common defaults)
    if logical_folder_lower == 'spam':
        # Common alternatives for Spam
        return 'Spam' # Or 'Junk'
    elif logical_folder_lower == 'trash':
        return 'Trash' # Or 'Deleted Items', 'Deleted Messages'
    elif logical_folder_lower == 'sent':
        return 'Sent' # Or 'Sent Items', 'Sent Messages'
    elif logical_folder_lower == 'drafts':
        return 'Drafts'
    elif logical_folder_lower == 'archive':
        return 'Archive' # Or 'Archived'

    # If it's not a standard logical folder, assume it's already the correct server name
    # or handle custom folders differently if needed.
    logger.warning(f"No specific mapping found for logical folder '{logical_folder}' for provider '{provider}'. Using the name directly.")
    # Be cautious returning the name directly, might fail if it's not a real server folder.
    # Consider returning None or raising an error if direct mapping is unreliable.
    return logical_folder # Fallback: Use the name as is 