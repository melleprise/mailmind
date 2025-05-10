"""
Dokumentation der Datenfelder für IMAP-Verarbeitung und DB-Mapping.
"""

# =====================================
# Email Model Fields (core/models.py)
# =====================================
# account (ForeignKey to EmailAccount)
# message_id (CharField, db_index=True)
# uid (CharField, nullable, blank, db_index=True)
# folder_name (CharField, nullable, blank, db_index=True)
# conversation_id (CharField, db_index=True, blank)
# 
# from_address (EmailField)
# from_name (CharField, blank)
# from_contact (ForeignKey to Contact, nullable, blank)
# 
# to_contacts (ManyToManyField to Contact)
# cc_contacts (ManyToManyField to Contact)
# bcc_contacts (ManyToManyField to Contact)
# reply_to_contacts (ManyToManyField to Contact)
# 
# subject (CharField, blank)
# body_text (TextField, blank)
# body_html (TextField, blank)
# 
# received_at (DateTimeField, db_index=True)
# sent_at (DateTimeField, nullable, blank, db_index=True)
# date_str (CharField, nullable, blank)
# 
# is_read (BooleanField, default=False, db_index=True)
# is_flagged (BooleanField, default=False, db_index=True)
# is_replied (BooleanField, default=False, db_index=True) -> \Answered flag
# is_deleted_on_server (BooleanField, default=False, db_index=True) -> \Deleted flag
# is_draft (BooleanField, default=False, db_index=True) -> \Draft flag
# 
# headers (JSONField, nullable, blank)
# size_rfc822 (PositiveIntegerField, nullable, blank) -> from server fetch
# size (PositiveIntegerField, nullable, blank) -> actual downloaded size?
# 
# embedding_generated (BooleanField, default=False)
# ai_processed (BooleanField, default=False)
# 
# created_at (DateTimeField, auto_now_add=True)
# updated_at (DateTimeField, auto_now=True)

# =================================================================
# Fields from Metadata Fetch (imap_tools MailMessage, partial)
# Using fetch_uids_metadata -> DEFAULT_METADATA_FETCH_ITEMS
# ['UID', 'FLAGS', 'RFC822.SIZE', 'INTERNALDATE', 'ENVELOPE']
# =================================================================
# msg.uid (str)
# msg.flags (tuple of str) -> e.g., ('\Seen', '\Flagged', '$NotJunk')
# msg.size_rfc822 (int)
# msg.date (datetime.datetime, parsed from INTERNALDATE or Date header)
# msg.date_str (str, original Date header)
# msg.subject (str, from ENVELOPE)
# msg.from_ (str, simple address from ENVELOPE)
# msg.to (tuple of str, simple addresses from ENVELOPE)
# msg.cc (tuple of str, simple addresses from ENVELOPE)
# msg.bcc (tuple of str, simple addresses from ENVELOPE)
# msg.reply_to (tuple of str, simple addresses from ENVELOPE)
# msg.message_id (str, from ENVELOPE)
# msg.in_reply_to (str, from ENVELOPE)
# msg.from_values (EmailAddress object, parsed from ENVELOPE)
# msg.to_values (tuple of EmailAddress objects, parsed from ENVELOPE)
# msg.cc_values (tuple of EmailAddress objects, parsed from ENVELOPE)
# msg.bcc_values (tuple of EmailAddress objects, parsed from ENVELOPE)
# msg.reply_to_values (tuple of EmailAddress objects, parsed from ENVELOPE)
# msg.headers (dict, likely incomplete without full fetch, but contains some basics)
#   -> msg.headers.get('x-gm-thrid') for conversation_id (example)

# User Provided Metadata Example (subset of possible headers):
#   to (list of str)
#   date (list of str)
#   from (list of str)
#   subject (list of str)
#   arc-seal (list of str)
#   received (list of str)
#   reply-to (list of str)
#   message-id (list of str)
#   x-received (list of str)
#   feedback-id (list of str)
#   return-path (list of str)
#   content-type (list of str)
#   delivered-to (list of str)
#   mime-version (list of str)
#   received-spf (list of str)
#   dkim-signature (list of str)
#   x-notifications (list of str)
#   x-gm-message-state (list of str)
#   x-google-smtp-source (list of str)
#   arc-message-signature (list of str)
#   authentication-results (list of str)
#   x-google-dkim-signature (list of str)
#   arc-authentication-results (list of str)
#   x-notifications-bounce-info (list of str)

# ==============================================================
# Fields from Full Email Fetch (imap_tools MailMessage, full)
# Using fetch_uids_full -> ['RFC822']
# ==============================================================
# All fields from Metadata Fetch are potentially available, but parsed from the full message.
# Plus:
# msg.text (str, plain text body)
# msg.html (str, html body)
# msg.attachments (list of MailAttachment objects)
#   att.filename (str)
#   att.payload (bytes)
#   att.content_id (str)
#   att.content_type (str)
#   att.content_disposition (str)
#   att.part (email.message.Message object)
#   att.size (int)
# msg.obj (email.message.Message, the root object)
# msg.headers (dict, should be complete)
# msg.size (int, actual downloaded size) 