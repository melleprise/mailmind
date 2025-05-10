import logging
import json
from datetime import datetime
from django.utils import timezone
from imap_tools import MailMessage, MailMessageFlags
from email.utils import parseaddr, parsedate_to_datetime
from typing import Optional, Union, Tuple, Any, Dict
from bs4 import BeautifulSoup
from mailmind.core.models import EmailAccount

# Importiere Hilfsfunktionen aus utils
from .utils import decode_email_header

logger = logging.getLogger(__name__)

def _addr_to_dict(addr: Any) -> Optional[Dict[str, str]]:
    """Converts various address representations to a {'name': ..., 'email': ...} dict."""
    if isinstance(addr, str):
        # Handle email string
        parsed_name, parsed_email = parseaddr(addr)
        email_part = parsed_email.lower().strip() if parsed_email else addr.lower().strip() # Fallback email
        if not email_part: # Skip if no email could be determined
            logger.warning(f"Could not determine email from address string: {addr}")
            return None
        # Use parsed name if available, otherwise generate fallback
        name_part = decode_email_header(parsed_name) if parsed_name else email_part.split('@')[0]
        return {'name': name_part, 'email': email_part}
    elif hasattr(addr, 'email'):
        # Handle MailAddress object (or similar)
        name = getattr(addr, 'name', None)
        email = getattr(addr, 'email', '')
        email_part = email.lower().strip() if email else ''
        if not email_part: # Skip if no email
            logger.warning(f"Address object lacks email attribute: {addr}")
            return None
        # Use object name if available, otherwise generate fallback
        name_part = decode_email_header(name) if name else email_part.split('@')[0]
        return {'name': name_part, 'email': email_part}
    else:
        # Log unexpected types
        logger.warning(f"Unexpected address type in recipient list: {type(addr)}, value: {addr}")
        return None

def _get_datetime_from_header(date_header: Optional[str]) -> Optional[datetime]:
    """Konvertiert einen Date-Header-String in ein timezone-aware datetime Objekt."""
    if not date_header:
        return None
    try:
        dt_naive = parsedate_to_datetime(date_header)
        if dt_naive:
            # Wenn das Datum keine Zeitzone hat, nehmen wir UTC an (häufig bei IMAP internaldate)
            if timezone.is_naive(dt_naive):
                return timezone.make_aware(dt_naive, timezone.utc)
            return dt_naive # Already timezone-aware
    except Exception as e:
        logger.warning(f"Could not parse date header '{date_header}': {e}")
    return None

def _extract_conversation_id(headers_lower: dict) -> Optional[str]:
    """Extracts conversation ID from headers."""
    gm_thrid = headers_lower.get('x-gm-thrid', None)
    conv_id_fallback = None

    references_val = headers_lower.get('references')
    if references_val:
        ref_header_str = None
        if isinstance(references_val, tuple):
            ref_header_str = references_val[-1] if references_val else None
        elif isinstance(references_val, str):
            ref_header_str = references_val
        
        if isinstance(ref_header_str, str):
            ref_list = ref_header_str.split()
            if ref_list: 
                conv_id_fallback = ref_list[-1].strip('<>') 

    if not conv_id_fallback:
        in_reply_to_val = headers_lower.get('in-reply-to')
        if in_reply_to_val:
            in_reply_to_header_str = None
            if isinstance(in_reply_to_val, tuple):
                in_reply_to_header_str = in_reply_to_val[-1] if in_reply_to_val else None
            elif isinstance(in_reply_to_val, str):
                in_reply_to_header_str = in_reply_to_val
            
            if isinstance(in_reply_to_header_str, str):
                 conv_id_fallback = in_reply_to_header_str.strip('<>')
        
    return gm_thrid if gm_thrid else conv_id_fallback

def _extract_common_metadata(uid: str, folder_name: str, account_email: str, subject: str,
                             from_values: Optional[Any], date_str: Optional[str], date_obj: Optional[datetime],
                             flags: Union[set, list], headers_lower: dict, size_rfc822: Optional[int]) -> dict:
    """Extracts metadata common to both MailMessage and dictionary sources."""
    
    # --- Message-ID --- 
    message_id_raw = headers_lower.get('message-id', None)
    message_id_str = None
    if isinstance(message_id_raw, tuple):
        if message_id_raw: message_id_str = message_id_raw[0]
    elif isinstance(message_id_raw, str):
        message_id_str = message_id_raw
    if not message_id_str or not isinstance(message_id_str, str):
        raise ValueError(f"Message UID {uid} has invalid/missing Message-ID.")
    message_id = message_id_str.strip().strip('<>')

    # --- Absender --- 
    from_name = ''
    from_address = ''
    logger.debug(f"Mapper: Processing From info for UID {uid}. Raw from_values: {from_values} (type: {type(from_values)})")
    if from_values: # Kann MailAddress sein oder ein dict/SimpleNamespace
        name_raw = getattr(from_values, 'name', None)
        email_raw = getattr(from_values, 'email', '')
        logger.debug(f"Mapper: Extracted from from_values - Raw Name: {name_raw}, Raw Email: {email_raw}")
        from_name = decode_email_header(name_raw) if name_raw else ''
        from_address = email_raw.lower().strip() if email_raw else ''
    elif headers_lower.get('from'): # Fallback auf From-Header
        from_header = headers_lower.get('from')
        logger.debug(f"Mapper: Falling back to From header. Raw value: {from_header} (type: {type(from_header)})")
        if isinstance(from_header, tuple):
            from_header = from_header[0]
        if isinstance(from_header, str):
            real_name, email_addr = parseaddr(from_header)
            logger.debug(f"Mapper: Parsed From header - Raw Name: {real_name}, Raw Email: {email_addr}")
            from_name = decode_email_header(real_name) if real_name else ''
            from_address = email_addr.lower().strip() if email_addr else ''
        else:
            logger.warning(f"Mapper: From header fallback was not a string or tuple: {from_header}")
    else:
        logger.warning(f"Mapper: No from_values and no From header found for UID {uid}")
    
    logger.debug(f"Mapper: Final extracted - From Name: '{from_name}', From Address: '{from_address}'")

    # --- Datum --- 
    dt_header = _get_datetime_from_header(date_str) 
    dt_to_use = date_obj if date_obj else dt_header # Prioritize parsed date object

    sent_at_dt = None
    received_at_dt = None
    if from_address and account_email and from_address == account_email.lower().strip():
        sent_at_dt = dt_to_use
    else:
        received_at_dt = dt_to_use

    # --- Flags --- 
    flags_set = set(flags)
    is_read = MailMessageFlags.SEEN in flags_set
    is_flagged = MailMessageFlags.FLAGGED in flags_set
    is_replied = MailMessageFlags.ANSWERED in flags_set
    is_deleted_on_server = MailMessageFlags.DELETED in flags_set
    is_draft = MailMessageFlags.DRAFT in flags_set

    # --- Konversations-ID ---
    conversation_id = _extract_conversation_id(headers_lower)

    # --- Mapping Dictionary --- 
    db_data = {
        '_message_id_for_lookup': message_id,
        'message_id': message_id,
        'uid': uid,
        'folder_name': folder_name,
        'subject': decode_email_header(subject),
        'from_address': from_address,
        'from_name': from_name,
        'sent_at': sent_at_dt,
        'received_at': received_at_dt,
        'date_str': date_str,
        'is_read': is_read,
        'is_flagged': is_flagged,
        'is_replied': is_replied,
        'is_deleted_on_server': is_deleted_on_server,
        'is_draft': is_draft,
        'headers': headers_lower,
        'size_rfc822': size_rfc822,
        'conversation_id': conversation_id if conversation_id else '',
    }
    return db_data

def map_metadata_to_db(msg: MailMessage, folder_name: str, account_email: str) -> dict:
    """Maps metadata from MailMessage (fetched via ENVELOPE etc.) to a dict for DB defaults."""
    headers_lower = {k.lower(): v for k, v in msg.headers.items()} if hasattr(msg, 'headers') else {}
    
    # Versuche, Date-Objekt aus msg.date zu holen (kann datetime oder None sein)
    dt_internal = None
    if isinstance(msg.date, datetime):
        dt_internal = msg.date
        if timezone.is_naive(dt_internal):
             dt_internal = timezone.make_aware(dt_internal, timezone.utc)

    return _extract_common_metadata(
        uid=msg.uid,
        folder_name=folder_name,
        account_email=account_email,
        subject=msg.subject,
        from_values=msg.from_values, # MailAddress object
        date_str=msg.date_str,
        date_obj=dt_internal,
        flags=msg.flags, # set
        headers_lower=headers_lower,
        size_rfc822=msg.size_rfc822
    )

def map_metadata_from_dict(msg_dict: dict, folder_name: str, account_email: str) -> dict:
    """Maps metadata from a dictionary to a dict for DB defaults."""
    headers_lower = msg_dict.get('headers', {})
    
    # Versuche, Date-Objekt aus ISO-String zu holen
    date_iso = msg_dict.get('date_iso')
    dt_from_iso = None
    if date_iso:
        try:
            dt_from_iso = datetime.fromisoformat(date_iso)
            if dt_from_iso and timezone.is_naive(dt_from_iso):
                dt_from_iso = timezone.make_aware(dt_from_iso, timezone.utc)
        except ValueError:
            pass # Fehler wird bereits in _extract_common_metadata behandelt, falls date_str auch fehlt

    # Erstelle ein einfaches Objekt für from_values
    from_values_dict = {
        'name': msg_dict.get('from_name'), 
        'email': msg_dict.get('from_email')
    }
    # Wandle das Dict in ein Objekt um, das Attributzugriff erlaubt
    from types import SimpleNamespace
    from_values_obj = SimpleNamespace(**from_values_dict)

    return _extract_common_metadata(
        uid=msg_dict.get('uid'),
        folder_name=folder_name,
        account_email=account_email,
        subject=msg_dict.get('subject', ''),
        from_values=from_values_obj,
        date_str=msg_dict.get('date_str'),
        date_obj=dt_from_iso,
        flags=msg_dict.get('flags', []), # list
        headers_lower=headers_lower,
        size_rfc822=msg_dict.get('size_rfc822')
    )

def map_full_email_to_db(msg: MailMessage, folder_name: str, account_email: str) -> dict:
    """Maps data from a fully fetched MailMessage to a dict for updating the DB record."""
    try:
        db_data = map_metadata_to_db(msg, folder_name, account_email)
    except ValueError as e:
        logger.error(f"Could not map metadata as basis for full email mapping (UID: {msg.uid}): {e}")
        raise

    # --- Body ---
    body_plain = msg.text or ''
    body_html = msg.html or ''

    # --- To, Cc, Bcc ---
    to_list = [_addr_to_dict(addr) for addr in msg.to] if msg.to else []
    cc_list = [_addr_to_dict(addr) for addr in msg.cc] if msg.cc else []
    bcc_list = [_addr_to_dict(addr) for addr in msg.bcc] if msg.bcc else []
    reply_to_list = [_addr_to_dict(addr) for addr in msg.reply_to] if msg.reply_to else []

    to_list = [addr for addr in to_list if addr]
    cc_list = [addr for addr in cc_list if addr]
    bcc_list = [addr for addr in bcc_list if addr]
    reply_to_list = [addr for addr in reply_to_list if addr]

    # --- Anhänge ---
    attachments_list = []
    if msg.attachments:
        for att in msg.attachments:
            att_data = {
                'filename': decode_email_header(att.filename),
                'content_type': att.content_type,
                'size': att.size,
                'payload': att.payload, # Bytes
                'content_id': att.content_id,
                'content_disposition': att.content_disposition,
            }
            attachments_list.append(att_data)

    # --- Aktualisiere db_data Dict ---
    db_data.update({
        'body_text': body_plain,
        'body_html': body_html,
        'to_addresses': to_list,
        'cc_addresses': cc_list,
        'bcc_addresses': bcc_list,
        'reply_to_addresses': reply_to_list,
        'attachments': attachments_list,
        'size': msg.size,
    })

    # --- ENTFERNT: Ordnernamen korrigieren (Gmail-Label-Logik) ---
    # Der übergebene folder_name wird jetzt als korrekt angenommen,
    # da der Sync-Prozess Ordner einzeln durchgehen soll.
    logger.debug(f"UID {msg.uid}: Using folder_name '{folder_name}' as provided by sync task.")
    # db_data['folder_name'] = folder_name # Ist bereits durch map_metadata_to_db gesetzt

    return db_data

def map_imap_message_to_dict(msg_bytes: bytes, account: EmailAccount, folder_name: str) -> dict:
    """Konvertiert eine IMAP-Nachricht in ein Dictionary für die Datenbank."""
    from email import message_from_bytes
    from email.utils import parsedate_to_datetime
    from datetime import datetime
    
    msg = message_from_bytes(msg_bytes)
    
    # Extrahiere Header
    headers = dict(msg.items())
    headers_lower = {k.lower(): v for k, v in headers.items()}
    
    # Extrahiere Message-ID
    message_id = headers_lower.get('message-id', '')
    if message_id:
        message_id = message_id.strip('<>')
    
    # Extrahiere Datum
    date_str = headers_lower.get('date')
    date = None
    if date_str:
        try:
            date = parsedate_to_datetime(date_str)
        except:
            date = datetime.now()
    
    # Extrahiere Absender
    from_ = headers_lower.get('from', '')
    
    # Extrahiere Empfänger
    to = headers_lower.get('to', '')
    
    # Extrahiere Betreff
    subject = headers_lower.get('subject', '')
    
    # Extrahiere Flags
    flags = []
    if 'x-gm-labels' in headers_lower:
        flags.extend(headers_lower['x-gm-labels'].split())
    
    # Extrahiere Conversation ID
    conversation_id = _extract_conversation_id(headers_lower)
    
    return {
        'message_id': message_id,
        'date': date,
        'from_': from_,
        'to': to,
        'subject': subject,
        'flags': flags,
        'folder_name': folder_name,
        'conversation_id': conversation_id,
        'size_rfc822': len(msg_bytes),
        'account': account
    } 