import logging
import os
import uuid
import shlex  # Import shlex for parsing
import base64 # Import base64
from django.utils import timezone
from django.conf import settings
from django.core.files.base import ContentFile # Import ContentFile
from imap_tools import MailMessage
from mailmind.core.models import Email, Contact, Attachment, EmailAccount, User
from .mapper import map_metadata_to_db, map_full_email_to_db, map_metadata_from_dict
from .utils import decode_email_header, FOLDER_PRIORITIES
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from types import SimpleNamespace
from django.db import transaction
# --- Markdown Imports --- 
# Remove unused BeautifulSoup and re
# from bs4 import BeautifulSoup 
# import re
import html2text # Import html2text
from email.utils import parseaddr, parsedate_to_datetime
from django_q.tasks import async_task # Import für async_task
# ------------------------

logger = logging.getLogger(__name__)

def _parse_x_gm_labels(label_string: Optional[str]) -> List[str]:
    """Parses the X-GM-LABELS string into a list of labels."""
    if not label_string:
        return []
    try:
        # shlex.split handles quoted labels correctly
        return shlex.split(label_string)
    except Exception as e:
        logger.warning(f"Could not parse X-GM-LABELS string '{label_string}': {e}")
        # Fallback: einfache Trennung nach Leerzeichen (kann bei Anführungszeichen fehlschlagen)
        return label_string.split(' ')

def _determine_folder_name(flags: List[str], x_gm_labels: Optional[str], original_folder: str) -> str:
    """Determines the most appropriate folder name based on flags and labels."""
    
    # 1. Prioritize standard flags/folders
    flag_map = {
        '\Sent': 'Sent Mail',
        '\Draft': 'Drafts',
        '\Junk': 'Spam',
        '\Trash': 'Trash',
        # '\Deleted' ist oft synonym mit '\Trash', wird aber hier ignoriert, da weniger gebräuchlich
    }
    for flag, folder in flag_map.items():
        if flag in flags:
            logger.debug(f"Determined folder '{folder}' based on flag '{flag}'")
            return folder

    # 2. Use X-GM-LABELS if no standard flag matched
    parsed_labels = _parse_x_gm_labels(x_gm_labels)
    
    # Filter out system/irrelevant labels
    system_labels = {'\Sent', '\Draft', '\Junk', '\Trash', '\Deleted', 
                     '\Important', '\Starred', '\Inbox', '[Gmail]/All Mail'}
    
    meaningful_labels = [
        label for label in parsed_labels 
        if label not in system_labels and not label.startswith('[Gmail]/') # Auch andere [Gmail] ausschließen
    ]

    if meaningful_labels:
        # Take the first meaningful custom label found
        chosen_label = meaningful_labels[0]
        logger.debug(f"Determined folder '{chosen_label}' based on X-GM-LABELS: {meaningful_labels}")
        return chosen_label

    # 3. Fallback logic
    # If Inbox flag or label is present, use 'Inbox'
    if '\Inbox' in flags or 'Inbox' in parsed_labels or '\Inbox' in parsed_labels: # Check both flag and parsed label
        logger.debug("Determined folder 'Inbox' based on flag/label.")
        return 'Inbox'
        
    # If the original folder seems more specific than 'Inbox' or '[Gmail]/All Mail'
    if original_folder and original_folder.lower() not in ['inbox', '[gmail]/all mail']:
         logger.debug(f"Using original fetched folder '{original_folder}' as fallback.")
         return original_folder

    # Default to 'Inbox' if nothing else matches
    logger.debug("Defaulting folder name to 'Inbox'.")
    return 'Inbox'

def get_folder_priority(folder_name: str) -> int:
    """Gibt die Priorität für einen gegebenen Ordnernamen zurück."""
    if not folder_name:
        return -99 # Sollte nicht vorkommen
    
    # Normalisiere den Ordnernamen und verwende die importierte Map
    normalized_folder = folder_name.lower()
    
    # Versuche, eine Priorität für bekannte Standardnamen zu finden
    # Direkter Check für Inbox, Sent, etc. (Groß-/Kleinschreibung wird durch FOLDER_PRIORITIES abgedeckt)
    if folder_name in FOLDER_PRIORITIES:
        return FOLDER_PRIORITIES[folder_name]
    # Check für Gmail-Varianten
    elif normalized_folder == '[gmail]/sent mail':
        return FOLDER_PRIORITIES.get("Sent", FOLDER_PRIORITIES["__default__"])
    elif normalized_folder == '[gmail]/drafts':
        return FOLDER_PRIORITIES.get("Drafts", FOLDER_PRIORITIES["__default__"])
    elif normalized_folder == '[gmail]/spam':
        return FOLDER_PRIORITIES.get("Spam", FOLDER_PRIORITIES["__default__"])
    elif normalized_folder == '[gmail]/trash':
        return FOLDER_PRIORITIES.get("Trash", FOLDER_PRIORITIES["__default__"])
    elif normalized_folder == '[gmail]/all mail': # Beispiel für 'All Mail'
        return FOLDER_PRIORITIES.get("Archive", FOLDER_PRIORITIES["__default__"])
    
    # Fallback auf Standard-Priorität
    return FOLDER_PRIORITIES["__default__"] # Unbekannte Ordner bekommen Standard-Priorität

def _get_or_create_contact(user, address_info):
    """Hilfsfunktion zum Abrufen oder Erstellen eines Kontakts."""
    if not address_info or not address_info.email:
        return None
    
    email = address_info.email.lower().strip()
    name = decode_email_header(address_info.name) if address_info.name else email.split('@')[0]
    
    contact, created = Contact.objects.get_or_create(
        user=user,
        email=email,
        defaults={'name': name}
    )
    if created:
        logger.debug(f"Created new contact: {name} <{email}>")
    # Optional: Update name if different?
    # elif contact.name != name:
    #     contact.name = name
    #     contact.save(update_fields=['name'])
    return contact

def _process_attachments(msg: MailMessage, email_instance: Email):
    """Processes and saves attachments from a MailMessage object."""
    saved_attachments = []
    # Stelle sicher, dass Anhänge nur einmal verarbeitet werden (relevant bei Updates)
    # Hole bestehende Anhänge für dieses Email-Objekt
    existing_filenames = set(email_instance.attachments.values_list('filename', flat=True))
    
    if msg.attachments:
        logger.debug(f"Processing {len(msg.attachments)} attachments for email {email_instance.id}")
        for att in msg.attachments:
            try:
                filename_orig = att.filename or 'unknown_attachment'
                payload_bytes = att.payload
                content_type = att.content_type or 'application/octet-stream'
                content_id = att.content_id
                content_disposition = att.content_disposition
                size = att.size

                # Überspringe, wenn der Anhang bereits existiert (basierend auf Dateinamen)
                if filename_orig in existing_filenames:
                    logger.debug(f"Skipping existing attachment '{filename_orig}' for email {email_instance.id}")
                    continue

                if not payload_bytes:
                    logger.warning(f"Skipping attachment '{filename_orig}' with missing payload for email {email_instance.id}")
                    continue
                
                # Generiere einen Fallback-Namen basierend auf Content-Type und Zeitstempel
                if not filename_orig:
                    extension = content_type.split('/')[-1]
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename_orig = f"attachment_{timestamp}.{extension}"
                
                unique_filename = f"{uuid.uuid4()}_{filename_orig}"
                # Pfad anpassen, relativ zum MEDIA_ROOT
                relative_path = os.path.join('attachments', email_instance.account.user.username, str(email_instance.id), unique_filename)
                full_path = os.path.join(settings.MEDIA_ROOT, relative_path)

                os.makedirs(os.path.dirname(full_path), exist_ok=True)

                with open(full_path, 'wb') as f:
                    f.write(payload_bytes)

                attachment_instance = Attachment.objects.create(
                    email=email_instance,
                    filename=filename_orig,
                    content_type=content_type,
                    size=size or len(payload_bytes), # Nutze att.size wenn verfügbar
                    content_id=content_id,
                    content_disposition=content_disposition,
                    file=relative_path # Speichere relativen Pfad
                )
                saved_attachments.append(attachment_instance)
                logger.info(f"Saved attachment '{filename_orig}' ({attachment_instance.id}) for email {email_instance.id}")
                existing_filenames.add(filename_orig) # Füge hinzu, um Duplikate im selben Lauf zu vermeiden

            except Exception as e:
                logger.error(f"Error saving attachment '{getattr(att, 'filename', 'unknown')}' for email {email_instance.id}: {e}", exc_info=True)
    else:
        logger.debug(f"No attachments found in MailMessage for email {email_instance.id}")
    return saved_attachments

def _update_or_create_email(account: EmailAccount, uid: str, folder_name: str, db_data: dict) -> Tuple[Email, bool]:
    """Handles the core logic of finding/creating an Email record and updating its fields based on db_data.
       Expects db_data to contain already processed fields.
    """
    created = False
    email_instance = None
    
    try:
        # Use update_or_create with account, uid, and folder_name as lookup keys
        # db_data contains all fields to set/update (including markdown_body if generated)
        email_instance, created = Email.objects.update_or_create(
            account=account,
            uid=uid, 
            folder_name=folder_name, 
            defaults=db_data
        )
        
        if created:
            logger.info(f"CREATED email record for UID {uid} in folder '{folder_name}'. ID: {email_instance.id}")
        else:
            # Optional: Log specific updated fields if needed (more complex)
            logger.info(f"UPDATED existing email record for UID {uid} in folder '{folder_name}'. ID: {email_instance.id}")
            
    except Email.MultipleObjectsReturned:
        # This case should ideally not happen if (account, uid, folder_name) is unique
        logger.error(f"Multiple emails found for account {account.id}, UID {uid}, folder '{folder_name}'. This indicates a potential data integrity issue. Using the first one found.")
        email_instance = Email.objects.filter(account=account, uid=uid, folder_name=folder_name).first()
        created = False # Treat as update if multiple found
    except Exception as e:
        logger.error(f"Error in _update_or_create_email for UID {uid}, Folder '{folder_name}': {e}", exc_info=True)
        raise # Re-raise the exception to signal failure

    return email_instance, created

def _update_contacts_for_email(email_instance: Email, contact_data: dict, user: User):
    """Aktualisiert die ManyToMany-Kontaktfelder für eine Email-Instanz."""
    if not email_instance or not contact_data:
        return

    address_fields_map = {
        'to_addresses': 'to_contacts',
        'cc_addresses': 'cc_contacts',
        'bcc_addresses': 'bcc_contacts',
        'reply_to_addresses': 'reply_to_contacts',
    }

    try:
        with transaction.atomic(): # Eigene Transaktion für Kontakt-Updates
            for address_list_key, m2m_field_name in address_fields_map.items():
                address_list = contact_data.get(address_list_key, [])
                if not address_list: # Wenn Liste leer oder nicht vorhanden, überspringen
                    continue
                
                contact_instances = []
                for addr_info_item in address_list: # Umbenannt von addr_info_tuple
                    # Erstelle addr_info_obj (SimpleNamespace) konsistent,
                    # egal ob das Item ein Tuple oder Dict ist.
                    addr_info_obj = None
                    if isinstance(addr_info_item, dict):
                        addr_info_obj = SimpleNamespace(name=addr_info_item.get('name'), email=addr_info_item.get('email'))
                    elif isinstance(addr_info_item, tuple) and len(addr_info_item) > 1:
                         # Fallback für Tuple (name, email)
                        addr_info_obj = SimpleNamespace(name=addr_info_item[0], email=addr_info_item[1])
                    elif hasattr(addr_info_item, 'email'): # Prüfe auf Objekt mit .email Attribut
                        addr_info_obj = addr_info_item # Direkt verwenden
                    else:
                         logger.warning(f"Skipping unknown address format in list for email {email_instance.id}: {type(addr_info_item)} - {addr_info_item}")
                         continue # Überspringe dieses Item

                    # Stelle sicher, dass wir ein Objekt haben, bevor wir es weitergeben
                    if addr_info_obj:
                        contact = _get_or_create_contact(user, addr_info_obj)
                        if contact:
                            contact_instances.append(contact)
                    # else: Fehler wurde bereits geloggt
                
                # Hole das ManyToMany-Feld und setze die Kontakte
                m2m_field = getattr(email_instance, m2m_field_name)
                m2m_field.set(contact_instances)
                logger.debug(f"Updated {m2m_field_name} for email {email_instance.id} with {len(contact_instances)} contacts.")

    except Exception as e:
        logger.error(f"Error updating contacts for email {email_instance.id}: {e}", exc_info=True)
        # Fehler hier nicht weitergeben, um Hauptprozess nicht zu blockieren?
        # Oder doch? Hängt von der gewünschten Robustheit ab.
        # raise # -> Würde die übergeordnete Transaktion (falls vorhanden) rückgängig machen

def _process_attachments_from_dict(attachments_list: List[Dict[str, Any]], email_instance: Email):
    """Processes and saves attachments from a list of attachment dictionaries."""
    saved_attachments_count = 0
    if not attachments_list:
        # logger.debug(f"No attachments data found in dict for email {email_instance.id}") # Zu Vebose
        return saved_attachments_count

    # Hole bestehende Content-IDs, um Duplikate zu vermeiden (besser als nur Filename)
    existing_content_ids = set(email_instance.attachments.filter(content_id__isnull=False).values_list('content_id', flat=True))
    # Hole bestehende Filenames für den Fall, dass keine Content-ID vorhanden ist
    existing_filenames = set(email_instance.attachments.values_list('filename', flat=True))

    logger.debug(f"Processing {len(attachments_list)} attachments from dict for email {email_instance.id}")
    for att_data in attachments_list:
        try:
            filename = att_data.get('filename', 'unknown_attachment')
            payload_b64 = att_data.get('payload_base64')
            content_type = att_data.get('content_type', 'application/octet-stream')
            content_id = att_data.get('content_id')
            content_disposition = att_data.get('content_disposition')
            size = att_data.get('size')

            # Logge den abgerufenen Wert und Typ von payload_base64 (korrigierter Schlüssel im Log)
            logger.debug(f"UID {email_instance.uid}: Inside loop for '{filename}'. Value from att_data.get('payload_base64'): TYPE={type(payload_b64)}, VALUE_START='{str(payload_b64)[:50]}...'")

            # Prüfe auf Duplikate
            is_duplicate = False
            if content_id and content_id in existing_content_ids:
                is_duplicate = True
                logger.debug(f"Skipping duplicate attachment based on Content-ID '{content_id}' for email {email_instance.id}")
            elif not content_id and filename in existing_filenames:
                 is_duplicate = True
                 logger.debug(f"Skipping duplicate attachment based on filename '{filename}' (no Content-ID) for email {email_instance.id}")

            if is_duplicate:
                continue

            if not payload_b64:
                logger.warning(f"Skipping attachment '{filename}' with missing base64 payload for email {email_instance.id}")
                continue

            # Dekodiere Base64 Payload
            try:
                payload_bytes = base64.b64decode(payload_b64)
            except Exception as e_decode:
                logger.error(f"Error decoding base64 payload for attachment '{filename}' (email {email_instance.id}): {e_decode}")
                continue

            # Erstelle ContentFile
            # filename ist wichtig für Django, um den Pfad zu generieren!
            attachment_file = ContentFile(payload_bytes, name=filename)

            # Erstelle Attachment-Instanz und übergebe ContentFile an das FileField
            # Django kümmert sich um das Speichern basierend auf upload_to
            attachment_instance = Attachment.objects.create(
                email=email_instance,
                filename=filename, # Originalfilename für Anzeige speichern
                content_type=content_type,
                size=size or len(payload_bytes),
                content_id=content_id,
                content_disposition=content_disposition,
                file=attachment_file # Hier das ContentFile übergeben
            )
            saved_attachments_count += 1
            logger.info(f"Saved attachment '{filename}' ({attachment_instance.id}, path: {attachment_instance.file.name}) for email {email_instance.id}")
            
            # Update existing sets to prevent duplicates within the same batch run
            if content_id:
                existing_content_ids.add(content_id)
            existing_filenames.add(filename)

        except Exception as e:
            logger.error(f"Error processing attachment data '{att_data.get('filename', 'unknown')}' from dict for email {email_instance.id}: {e}", exc_info=True)
    
    return saved_attachments_count

def save_email_content_from_dict(content_dict: dict, account: EmailAccount):
    """Creates or updates an Email record using uid/folder_name and updates its content fields.
       Also processes attachments and triggers markdown generation.
    """
    uid = content_dict.get('uid')
    folder_name = content_dict.get('folder_name')
    message_id_for_log = content_dict.get('message_id', '') # For logging

    if not uid or not folder_name:
        logger.error(f"Skipping save/update: uid ({uid}) or folder_name ({folder_name}) missing in content_dict for MsgID {message_id_for_log}.")
        return # Cannot proceed without lookup keys

    try:
        # --- Prepare data for update_or_create ---
        # Extract all relevant fields from the dictionary passed by the mapper
        db_data = {}
        valid_email_fields = {f.name for f in Email._meta.get_fields()} - {'id', 'account', 'attachments', 'to_contacts', 'cc_contacts', 'bcc_contacts', 'reply_to_contacts'} # Exclude relations/pk
        
        for field in valid_email_fields:
             if field in content_dict:
                 db_data[field] = content_dict[field]

        # Ensure essential fields for lookup are present, even if not in defaults
        db_data['account_id'] = account.id # Use account_id for direct assignment
        db_data['uid'] = uid
        db_data['folder_name'] = folder_name

        # Separate content fields for potential later use/logging
        body_text = content_dict.get('body_text')
        body_html = content_dict.get('body_html')
        size_rfc822 = content_dict.get('size_rfc822')
        attachments_list = content_dict.get('attachments', [])
        
        # --- Use update_or_create ---
        with transaction.atomic(): # Ensure atomicity for create/update + attachments + markdown task
            email_instance, created = Email.objects.update_or_create(
                account=account, # Lookup field
                uid=uid,         # Lookup field
                folder_name=folder_name, # Lookup field
                defaults=db_data # Fields to set on create or update
            )

            if created:
                logger.info(f"CREATED email record via content task for UID {uid} in folder '{folder_name}'. ID: {email_instance.id}")
            else:
                logger.info(f"UPDATED email record via content task for UID {uid} in folder '{folder_name}'. ID: {email_instance.id}")
            # Process attachments (using the existing function)
            if attachments_list:
                _process_attachments_from_dict(attachments_list, email_instance)
        # --- Markdown-Task jetzt außerhalb der Transaktion triggern ---
        if 'body_html' in db_data and db_data['body_html'] is not None:
            try:
                logger.info(f"Triggering markdown generation for email {email_instance.id}: body_html present (len={len(db_data['body_html']) if db_data['body_html'] else 0}) [AFTER TRANSACTION]")
                async_task('mailmind.imap.tasks.generate_markdown_for_email_task', email_instance.id)
                logger.info(f"Queued markdown generation task for email {email_instance.id} ({'created' if created else 'updated'}) [AFTER TRANSACTION]")
            except Exception as q_err:
                logger.error(f"Failed to queue markdown generation task for email {email_instance.id}: {q_err}", exc_info=True)
        else:
            logger.info(f"No body_html for email {email_instance.id} (UID: {uid}, folder: {folder_name}). Markdown generation not triggered. body_html in db_data: {'body_html' in db_data}, value: {db_data.get('body_html')}")
        # --- WebSocket-Broadcast für neue E-Mails ---
        try:
            from channels.layers import get_channel_layer
            from asgiref.sync import async_to_sync
            from mailmind.core.serializers import EmailDetailSerializer
            user_id = email_instance.account.user.id
            channel_layer = get_channel_layer()
            group_name = f'user_{user_id}_events'
            serializer = EmailDetailSerializer(email_instance)
            email_data = serializer.data
            logger.info(f"[store.py] Versuche WebSocket-Broadcast: user_id={user_id}, group={group_name}, email_id={email_instance.id}, data_keys={list(email_data.keys())}")
            message = {
                'type': 'email.new',
                'email_data': email_data
            }
            async_to_sync(channel_layer.group_send)(group_name, message)
            logger.info(f"[store.py] WebSocket-Broadcast: Neue E-Mail {email_instance.id} an Gruppe {group_name} gesendet.")
        except Exception as ws_err:
            logger.error(f"[store.py] WebSocket-Broadcast für neue E-Mail {email_instance.id} fehlgeschlagen: {ws_err}", exc_info=True)
        # End of the with transaction.atomic() block

    except Email.MultipleObjectsReturned:
         # This should ideally not happen with unique constraint on (account, uid, folder_name)
         logger.error(f"Multiple emails found for account {account.id}, UID {uid}, folder '{folder_name}' during update_or_create. This indicates a data integrity issue.")
    except Exception as e:
        logger.error(f"Error saving/updating content for email with UID '{uid}' in folder '{folder_name}': {e}", exc_info=True)

def save_or_update_email_from_dict(content_dict: dict, account: EmailAccount, folder_name: str):
    """Primary function to save email data from a dictionary (likely from mapper).
       DEPRECATED: Text extraction is now handled in save_email_content_from_dict.
    """
    email_instance = None
    created = False
    message_id = content_dict.get('message_id')
    uid = content_dict.get('uid') # UID is crucial

    if not uid:
        logger.error(f"Missing uid in content_dict for MsgID {message_id} in folder {folder_name}. Skipping.")
        return None, False
        
    if not message_id:
        logger.warning(f"Missing message_id in content_dict for UID {uid} in folder {folder_name}. Proceeding with UID.")
        # message_id = f"UID_{uid}_placeholder" # Assign placeholder if needed downstream, but UID is key

    try:
        # Create a copy to work with
        db_data = content_dict.copy()

        # --- Clean db_data: Remove fields not directly on Email model --- 
        # Fields to keep are actual Email model fields
        # Get actual field names from the Email model to be safe
        # (Avoid hardcoding list if possible, but simpler for now)
        valid_email_fields = {
            'account', 'message_id', 'subject', 'from_address',
            'from_name', 'from_contact', 'body_text', 'body_html', 
            'received_at', 'sent_at', 'folder_name', 'is_read', 'is_flagged', 
            'is_replied', 'is_draft', 'is_deleted_on_server', 'size_rfc822', 
            'headers', 
            # 'user' removed, association is via 'account'
            # 'markdown_body' is NOT set here anymore, but later in save_email_content_from_dict
            # Potentially add summaries if they are direct fields and calculated before this point
            # 'short_summary', 'medium_summary' # Assume these are added later or handled differently
        }
        # Create a new dict containing only the valid fields for update_or_create defaults
        defaults_data = {k: v for k, v in db_data.items() if k in valid_email_fields}
        # -----------------------------------------------------------------

        # 1. Create/Update the Email record using the helper function
        # Pass uid and folder_name for lookup, cleaned defaults_data for defaults
        email_instance, created = _update_or_create_email(
            account=account,
            uid=uid,
            folder_name=folder_name, 
            db_data=defaults_data # Pass the CLEANED data (without markdown_body)
        )

        if email_instance:
            # 2. Update contacts (using original content_dict with address lists)
            _update_contacts_for_email(email_instance, content_dict, account.user)
            
            # 3. Process attachments (using original content_dict with attachment data)
            # Note: Attachments are now processed in save_email_content_from_dict as well.
            # Consider if this is redundant or if metadata-only attachments should be saved here.
            # For now, keep it, but review if double processing occurs.
            attachments_list = content_dict.get('attachments', [])
            if attachments_list:
                 # Commenting out for now, seems redundant with save_email_content_from_dict
                 # logger.debug(f"Processing attachments in save_or_update (UID: {uid}). May be redundant.")
                 # _process_attachments_from_dict(attachments_list, email_instance)
                 pass # Decide later if attachment metadata should be processed here.

        # Logging moved inside _update_or_create_email

    except Exception as e:
        logger.error(f"Error in save_or_update_email_from_dict for UID {uid} (MsgID: {message_id}): {e}", exc_info=True)
        return None, False # Fehler signalisieren

    return email_instance, created