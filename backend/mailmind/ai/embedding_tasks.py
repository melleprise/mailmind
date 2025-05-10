import logging
import time
from PIL import Image
import pytesseract
from qdrant_client.http.models import PointStruct
from .clients import get_text_model, get_qdrant_client

logger = logging.getLogger(__name__)

def generate_email_embedding(email):
    """Generiert Text-Embedding für eine E-Mail und speichert es in Qdrant."""
    from mailmind.core.models import Email
    # Ensure type hint is still useful if possible, or remove if it causes issues
    # email: Email

    try:
        model = get_text_model()
        client = get_qdrant_client()

        text_content = f"Betreff: {email.subject}\nAbsender: {email.from_address}\n\n{email.body_text}"
        embedding = model.encode(text_content)

        to_addresses = list(email.to_contacts.values_list('email', flat=True))
        cc_addresses = list(email.cc_contacts.values_list('email', flat=True))
        bcc_addresses = list(email.bcc_contacts.values_list('email', flat=True))
        attachment_filenames = list(email.attachments.values_list('filename', flat=True))
        attachment_ids = list(email.attachments.values_list('id', flat=True))

        payload = {
            'email_id': email.id,
            'subject': email.subject or "",
            'from_address': email.from_address or "",
            'to_addresses': to_addresses,
            'cc_addresses': cc_addresses,
            'bcc_addresses': bcc_addresses,
            'received_at': email.received_at.isoformat() if email.received_at else None,
            'sent_at': email.sent_at.isoformat() if email.sent_at else None,
            'body_snippet': (email.body_text or "")[:250], # Gekürzt
            'has_attachments': email.attachments.exists(),
            'attachment_filenames': attachment_filenames,
            'attachment_ids': attachment_ids,
            'account_id': email.account_id,
            'user_id': email.account.user_id,
            'is_read': email.is_read,
            'is_flagged': email.is_flagged,
            'is_replied': email.is_replied,
            'is_deleted': email.is_deleted_on_server,
            'is_draft': email.is_draft,
            'folder_name': email.folder_name or "",
        }

        point = PointStruct(
            id=email.id,
            vector=embedding.tolist(),
            payload=payload
        )

        client.upsert(
            collection_name="email_embeddings",
            points=[point],
            wait=True
        )
        logger.info(f"Text-Embedding für Email ID {email.id} in Qdrant gespeichert.")

    except Exception as e:
        logger.error(f"Fehler beim Generieren/Speichern des E-Mail-Embeddings für ID {email.id}: {e}", exc_info=True)

def generate_attachment_embedding(attachment):
    """Generiert Embedding für einen Anhang (OCR für Bilder) und speichert es in Qdrant."""
    from mailmind.core.models import Attachment
    # attachment: Attachment

    try:
        text_model = get_text_model()
        client = get_qdrant_client()

        extracted_text = ""
        embedding = None
        is_image = attachment.content_type.startswith('image/')

        if is_image:
            try:
                if not attachment.file or not attachment.file.path:
                     logger.warning(f"Anhang-Datei für ID {attachment.id} nicht gefunden.")
                     return

                try:
                    image = Image.open(attachment.file.path)
                    extracted_text = pytesseract.image_to_string(image, lang='deu+eng')
                    logger.info(f"OCR für Anhang {attachment.id} ({attachment.filename}) durchgeführt.")
                except FileNotFoundError:
                    logger.error(f"Datei für Anhang {attachment.id} nicht gefunden unter Pfad: {attachment.file.path}")
                    return
                except Exception as ocr_error:
                    logger.error(f"OCR Fehler für Anhang {attachment.id}: {ocr_error}", exc_info=True)
                    extracted_text = "" # Setze leeren String bei OCR-Fehler

            except Exception as outer_exception:
                 logger.error(f"Fehler beim Vorbereiten der OCR für Anhang {attachment.id}: {outer_exception}", exc_info=True)
                 return

        else:
            extracted_text = attachment.extracted_text or f"Dateiname: {attachment.filename}"

        if extracted_text:
            embedding = text_model.encode(extracted_text)
            embedding_list = embedding.tolist()
        else:
            logger.warning(f"Kein Text für Embedding für Anhang {attachment.id} vorhanden.")
            return

        payload = {
            'attachment_id': attachment.id,
            'parent_email_id': attachment.email_id,
            'filename': attachment.filename or "",
            'content_type': attachment.content_type or "",
            'extracted_text_snippet': (extracted_text or "")[:250],
            'size': attachment.size,
            'is_image': is_image,
            'account_id': attachment.email.account_id,
            'user_id': attachment.email.account.user_id,
        }

        point = PointStruct(
            id=attachment.id,
            vector=embedding_list,
            payload=payload
        )

        client.upsert(
            collection_name="attachment_embeddings",
            points=[point],
            wait=True
        )
        logger.info(f"Embedding für Anhang ID {attachment.id} in Qdrant gespeichert.")

    except Exception as e:
        logger.error(f"Fehler beim Verarbeiten/Speichern des Anhang-Embeddings für ID {attachment.id}: {e}", exc_info=True)


def generate_embeddings_for_email(email_id: int):
    """
    Generiert Embeddings für eine E-Mail und ihre Anhänge und speichert sie in Qdrant.
    """
    from mailmind.core.models import Email

    logger.info(f"--- START: generate_embeddings_for_email for Email ID {email_id} ---")
    start_time = time.time()
    email = None # Initialize email
    try:
        email = Email.objects.prefetch_related('attachments').select_related('account').get(id=email_id)
        logger.info(f"Starte Embedding-Generierung für Email ID {email_id} (Betreff: {email.subject[:50]}...)")

        logger.info(f"[Schritt 1/2] Generiere E-Mail-Embedding für ID {email_id}")
        generate_email_embedding(email)

        logger.info(f"[Schritt 2/2] Generiere Attachment-Embeddings für ID {email_id}")
        attachments_processed = 0
        for attachment in email.attachments.all():
            logger.debug(f"Verarbeite Anhang ID {attachment.id} für E-Mail {email_id}")
            generate_attachment_embedding(attachment)
            attachments_processed += 1
        logger.info(f"{attachments_processed} Anhänge für Email ID {email_id} für Embeddings verarbeitet.")

    except Email.DoesNotExist:
        logger.error(f"Email mit ID {email_id} nicht gefunden für Embedding-Generierung.")
    except Exception as e:
        logger.error(f"Unerwarteter Fehler in generate_embeddings_for_email für ID {email_id}: {e}", exc_info=True)
    finally:
        logger.info(f"--- END: generate_embeddings_for_email for Email ID {email_id} ---") 