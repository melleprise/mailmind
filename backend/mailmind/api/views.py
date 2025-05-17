from rest_framework import viewsets, status, serializers, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.utils import timezone
from django_q.tasks import async_task
from django_q.models import Task
from django_q.cluster import Cluster
from mailmind.core.models import EmailAccount, Email, AISuggestion, Contact, AIRequestLog, AIAction, AISuggestionEditHistory
from mailmind.ai.tasks import generate_ai_suggestion
from mailmind.ai.correct_text_task import correct_text_with_ai
from mailmind.ai.refine_suggestion_task import refine_suggestion_task
from mailmind.ai.embedding_tasks import generate_embeddings_for_email
from mailmind.ai.clients import get_qdrant_client, get_gemini_model
from qdrant_client import models as qdrant_models
from qdrant_client.http import models as rest_models
from .serializers import (
    EmailAccountSerializer, EmailSerializer, 
    AISuggestionSerializer, ContactSerializer,
    EmailListSerializer, AIRequestLogSerializer, FolderSerializer, AIActionSerializer, DraftSerializer
)
import logging
from imap_tools import MailBox, MailboxLoginError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter
from rest_framework.pagination import PageNumberPagination
from cryptography.fernet import Fernet, InvalidToken
from rest_framework.views import APIView
from asgiref.sync import async_to_sync
from django.db.models import Q
from django.db import transaction, IntegrityError
from mailmind.ai.refinement_service import refine_text_content_sync
from apps.users.tasks import run_initial_sync_for_account_v2
from mailmind.imap.actions import move_email
from channels.layers import get_channel_layer
from .models import Draft

logger = logging.getLogger(__name__)

# Define a custom pagination class if you want to change the default limit
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'limit'
    max_page_size = 50

# --- Helper function to get text based on field --- 
def _get_text_to_process(suggestion: AISuggestion, field: str, selected_text: str | None) -> tuple[str | None, str | None]:
    """Helper to get the text to be processed (either selected or full field).
    Returns: (text_to_process, original_full_text) 
    Returns (None, None) if field is invalid.
    """
    if field == 'subject':
        original_full_text = suggestion.suggested_subject or ""
        text_to_process = selected_text if selected_text is not None else original_full_text
    elif field == 'body':
        original_full_text = suggestion.content or ""
        text_to_process = selected_text if selected_text is not None else original_full_text
    else: # Invalid field
        return None, None
    return text_to_process, original_full_text
# --- End Helper ---

class EmailViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint that allows emails to be viewed.
    Provides filtering by 'is_replied', 'is_read', 'is_flagged'
    and ordering by 'sent_at' or 'received_at'.
    Only shows emails belonging to the accounts of the currently authenticated user.
    Supports Limit/Offset pagination.
    """
    serializer_class = EmailSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['is_replied', 'is_read', 'is_flagged', 'folder_name']
    ordering_fields = ['sent_at', 'received_at']
    ordering = ['-sent_at', '-received_at']
    # Add pagination class
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        """Gibt den passenden Serializer je nach Aktion zurück."""
        if self.action == 'list':
            logger.debug("[EmailViewSet] Using EmailListSerializer for list action.")
            return EmailListSerializer
        logger.debug(f"[EmailViewSet] Using default EmailSerializer for action: {self.action}")
        return EmailSerializer # Default serializer for retrieve, etc.

    def get_queryset(self):
        """Gibt nur E-Mails zurück, die zu den Konten des aktuell authentifizierten Benutzers gehören.
           Filtert standardmäßig unbeantwortete, nicht gelöschte Mails, die keine Entwürfe sind."""
        user = self.request.user
        # Basic queryset, .only() will be applied in list method if needed
        logger.debug(f"[EmailViewSet] Getting base queryset for user: {user.email}")
        queryset = Email.objects.filter(
            account__user=user,
            is_replied=False,          # Nur unbeantwortete
            is_deleted_on_server=False,# Nur nicht gelöschte
            is_draft=False             # Keine Entwürfe
        )

        # Apply select_related/prefetch_related only for non-list actions (like retrieve)
        if self.action != 'list':
            logger.debug(f"[EmailViewSet] Applying prefetch/select related for action '{self.action}'")
            queryset = queryset.select_related(
                'account', 'from_contact'
            ).prefetch_related(
                'attachments', 'to_contacts', 'cc_contacts', 'bcc_contacts', 'reply_to_contacts', 'suggestions'
            )
        else:
             # Minimal prefetch for list view if using ContactSimpleSerializer later
             # queryset = queryset.select_related('from_contact')
             pass # Currently only needs fields from Email model itself
        
        logger.debug(f"[EmailViewSet] Base queryset count for user {user.email} (before action-specific optimization): {queryset.count()}") 
        return queryset

    def list(self, request, *args, **kwargs):
        logger.info(f"[EmailViewSet] List method called by user: {request.user.email}")
        logger.debug(f"[EmailViewSet] Request query params: {request.query_params}")
        queryset = None
        page = None
        serializer = None
        try:
            logger.debug("[EmailViewSet] Applying filters...")
            # Start with the base queryset
            queryset = self.get_queryset()
            # Apply filters defined in filter_backends
            filtered_queryset = self.filter_queryset(queryset)
            logger.info(f"[EmailViewSet] Filtered queryset count: {filtered_queryset.count()}")

            # Optimize DB query for list view *after* filtering
            logger.debug("[EmailViewSet] Applying .only() for list view optimization.")
            optimized_queryset = filtered_queryset.only(
                'id', 'subject', 'from_address', 'sent_at', 'is_read', 'is_flagged', 'account_id'
            )

            logger.debug("[EmailViewSet] Applying pagination...")
            page = self.paginate_queryset(optimized_queryset)
            if page is not None:
                logger.debug(f"[EmailViewSet] Paginated page size: {len(page)}")
                logger.debug("[EmailViewSet] Serializing page...")
                # Use the dynamically selected serializer (EmailListSerializer here)
                serializer = self.get_serializer(page, many=True)
                logger.debug("[EmailViewSet] Serialization complete.")
                logger.debug("[EmailViewSet] Returning paginated response...")
                response = self.get_paginated_response(serializer.data)
                logger.info(f"[EmailViewSet] Successfully prepared paginated response for user {request.user.email}")
                return response

            # Fallback if pagination is not used (shouldn't happen with StandardResultsSetPagination)
            logger.debug("[EmailViewSet] No pagination applied. Serializing full optimized queryset.")
            serializer = self.get_serializer(optimized_queryset, many=True)
            logger.debug("[EmailViewSet] Serialization complete.")
            logger.debug("[EmailViewSet] Returning non-paginated response...")
            response = Response(serializer.data)
            logger.info(f"[EmailViewSet] Successfully prepared non-paginated response for user {request.user.email}")
            return response
        except Exception as e:
            logger.error(f"[EmailViewSet] Error during list method for user {request.user.email}: {str(e)}", exc_info=True)
            raise
        finally:
            logger.info(f"[EmailViewSet] List method finished for user: {request.user.email}")

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """E-Mail als gelesen markieren."""
        email = self.get_object()
        email.is_read = True
        email.save(update_fields=['is_read'])
        return Response({'status': 'marked_read'})

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        """E-Mail markieren/entmarkieren."""
        email = self.get_object()
        email.is_flagged = not email.is_flagged
        email.save(update_fields=['is_flagged'])
        return Response({'status': 'flag_toggled', 'is_flagged': email.is_flagged})

    @action(detail=True, methods=['post'], url_path='generate-suggestions')
    def regenerate_suggestions(self, request, pk=None):
        """Triggers the ASYNC AI suggestion generation task for a specific email.
           Deletes old suggestions first, then queues the task.
           Passes the triggering user ID to the task.
        """
        email = None 
        triggering_user_id = request.user.id # Get ID of the user making the request

        try:
            # Get email object
            email = self.get_object() # Uses get_queryset 

            # Permission check remains based on get_object/get_queryset
            logger.info(f"User {request.user.email} (ID: {triggering_user_id}) requested ASYNC suggestion regeneration for Email ID {email.id}") # Log triggering user

            # --- Delete existing suggestions FIRST ---
            try:
                deleted_count, _ = AISuggestion.objects.filter(email=email).delete()
                logger.info(f"Deleted {deleted_count} existing suggestion(s) before ASYNC regenerating for Email ID {email.id}")
            except Exception as delete_err:
                logger.error(f"Error deleting existing suggestions for Email ID {email.id}: {delete_err}", exc_info=True)
                return Response({'error': 'Failed to delete old suggestions before regenerating.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # --- End Deletion ---
            
            # --- Queue the background task --- 
            try:
                # Queue the generation task, passing triggering_user_id
                async_task(
                    'mailmind.ai.suggestion_tasks.generate_ai_suggestion', 
                    email.id, 
                    triggering_user_id=triggering_user_id # Pass the ID here
                )
                logger.info(f"Queued generate_ai_suggestion task for Email ID {email.id} triggered by user {triggering_user_id}.")
            except Exception as queue_err:
                 logger.error(f"Error queueing suggestion task for Email ID {pk} by user {request.user.email}: {queue_err}", exc_info=True)
                 return Response({'error': 'Failed to queue suggestion task.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            # --- End Queueing --- 

            # Return 202 Accepted immediately
            return Response({'status': 'suggestion_generation_queued'}, status=status.HTTP_202_ACCEPTED)

        except Email.DoesNotExist: 
             logger.warning(f"Attempt by user {request.user.email} to regenerate suggestions for non-existent Email ID {pk}")
             return Response({'error': 'Email not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # General error during setup or unexpected issues
            logger.error(f"Unexpected error during ASYNC suggestion regeneration setup for Email ID {pk} by user {request.user.email}: {e}", exc_info=True)
            return Response({'error': 'An unexpected server error occurred during setup.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='suggestions')
    def get_suggestions(self, request, pk=None):
        """Gibt alle AI-Vorschläge für die angegebene E-Mail zurück."""
        logger.info(f"[EmailViewSet] get_suggestions called for Email ID {pk} by user {request.user.email}")
        try:
            email = self.get_object() # Holt die E-Mail oder gibt 404 zurück, prüft Berechtigungen
            # --- ADD LOGGING for the raw suggestions queryset ---
            suggestions_qs = email.suggestions.all().order_by('created_at')
            logger.info(f"[EmailViewSet] Raw suggestions queryset count for Email ID {pk}: {suggestions_qs.count()}")
            # Optional: Log details of each suggestion if needed for deeper debugging
            # for idx, suggestion in enumerate(suggestions_qs):
            #     logger.info(f"[EmailViewSet] Suggestion {idx+1} ID: {suggestion.id}, Type: {suggestion.type}, Subject: {suggestion.suggested_subject}")
            
            serializer = AISuggestionSerializer(suggestions_qs, many=True) # Use the queryset variable
            logger.info(f"[EmailViewSet] Found and will serialize {len(suggestions_qs)} suggestions for Email ID {pk}")
            return Response(serializer.data)
        except Email.DoesNotExist:
            logger.warning(f"[EmailViewSet] get_suggestions: Email ID {pk} not found for user {request.user.email}")
            return Response({'error': 'Email not found.'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"[EmailViewSet] Error retrieving suggestions for Email ID {pk}: {e}", exc_info=True)
            return Response({'error': 'An error occurred while retrieving suggestions.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], url_path='move_to_trash')
    def move_to_trash(self, request, pk=None):
        """Verschiebt die E-Mail in den Papierkorb (IMAP + DB), setzt is_deleted_on_server und triggert WebSocket-Event."""
        from mailmind.imap.actions import move_email
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync
        email = self.get_object()
        user = request.user
        logger.info(f"[EmailViewSet] User {user.email} verschiebt Email ID {email.id} in den Papierkorb.")
        # Sofort als gelöscht markieren
        email.is_deleted_on_server = True
        email.save(update_fields=['is_deleted_on_server'])
        success = move_email(email.id, 'Trash')
        if success:
            # WebSocket-Event an User-Gruppe
            try:
                group_name = f'user_{user.id}_events'
                channel_layer = get_channel_layer()
                async_to_sync(channel_layer.group_send)(group_name, {
                    'type': 'email.refresh',
                    'payload': {'folder': 'Trash'}
                })
                logger.info(f"[EmailViewSet] WebSocket-Event 'email.refresh' an Gruppe {group_name} gesendet.")
            except Exception as ws_err:
                logger.error(f"[EmailViewSet] WebSocket-Event fehlgeschlagen: {ws_err}", exc_info=True)
            return Response({'status': 'moved_to_trash'}, status=200)
        else:
            logger.error(f"[EmailViewSet] Verschieben in den Papierkorb fehlgeschlagen für Email ID {email.id}.")
            return Response({'error': 'move_failed'}, status=500)

class AISuggestionViewSet(viewsets.ModelViewSet):
    """ViewSet für KI-Vorschläge mit Update-Funktion."""
    
    serializer_class = AISuggestionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Gibt nur Vorschläge zurück, die zu E-Mails gehören, 
           die wiederum zu Konten des aktuell authentifizierten Benutzers gehören."""
        user = self.request.user
        return AISuggestion.objects.filter(email__account__user=user).order_by('-created_at')

    @action(detail=True, methods=['post'], url_path='correct-text', url_name='correct-text')
    def correct(self, request, pk=None):
        """Trigger text correction for a specific field of a suggestion."""
        suggestion = self.get_object() # Use the standard get_object for permission checks
        field = request.data.get('field') # 'subject', 'body', or None/invalid
        selected_text = request.data.get('selected_text') # Optional selected text
        logger.info(f"Korrektur-Anfrage für Suggestion {suggestion.id}, Feld: {field}, Selektion: {selected_text is not None}")

        # Validate field
        if field not in ['subject', 'body']:
            logger.warning(f"Ungültiges Feld '{field}' für Korrektur von Suggestion {suggestion.id}")
            return Response({'error': 'Invalid field specified. Must be "subject" or "body".'}, status=status.HTTP_400_BAD_REQUEST)

        # Get text to process (selected or full)
        text_to_correct, field_to_update = _get_text_to_process(suggestion, field, selected_text)

        if text_to_correct is None:
             logger.warning(f"Nichts zum Korrigieren gefunden für Suggestion {suggestion.id}, Feld {field}")
             # Return 404 if no text found for the specified field?
             return Response({'error': f'No text found in field \'{field}\' to correct.'}, status=status.HTTP_404_NOT_FOUND)

        try:
            # Call the correction function using async_to_sync
            # Pass context only if selected_text is present
            # ... (call correct_text_with_ai) ...
            # --- (No change needed in the AI call part) ---
            # Determine original subject/body for context based on which field is being fully corrected
            if field == 'subject' and selected_text is None:
                original_subject_for_context = None # Don't provide the text being corrected as context
                original_body_for_context = suggestion.content
            elif field == 'body' and selected_text is None:
                original_subject_for_context = suggestion.suggested_subject
                original_body_for_context = suggestion.content
            else: # Snippet correction or other cases
                original_subject_for_context = suggestion.suggested_subject
                original_body_for_context = suggestion.content

            # Wenn selected_text gesetzt ist, erzwinge Snippet-Modus im Task
            corrected_text_result = async_to_sync(correct_text_with_ai)(
                text_to_correct, 
                request.user,
                original_subject=original_subject_for_context, 
                original_body=original_body_for_context,
                is_snippet=True if selected_text is not None else None
            )

            if corrected_text_result is None:
                logger.error(f"Korrektur-Task ist fehlgeschlagen für Suggestion {suggestion.id}, Feld {field}")
                return Response({'error': 'AI correction failed.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Unterscheide Rückgabetyp (dict = full, str = snippet)
            if isinstance(corrected_text_result, dict):
                # Full correction: JSON mit subject/body
                final_subject = corrected_text_result.get('corrected_subject', suggestion.suggested_subject)
                final_body = corrected_text_result.get('corrected_body', suggestion.content)
                update_fields = []
                # Backup vor Überschreiben
                suggestion.subject_backup = suggestion.suggested_subject
                suggestion.content_backup = suggestion.content
                # Truncate subject if necessary
                if len(final_subject) > 255:
                    logger.warning(f"Final subject '{final_subject[:50]}...' is too long ({len(final_subject)} chars). Truncating to 255.")
                    suggestion.suggested_subject = final_subject[:255]
                else:
                    suggestion.suggested_subject = final_subject
                suggestion.content = final_body
                update_fields = ['suggested_subject', 'subject_backup', 'content', 'content_backup', 'updated_at']
                try:
                    suggestion.save(update_fields=update_fields)
                    logger.info(f"Full field (subject+body) corrected and saved for suggestion {suggestion.id}.")
                except Exception as save_err:
                    logger.error(f"Error saving corrected fields for suggestion {suggestion.id}: {save_err}", exc_info=True)
                    raise save_err
                serializer = self.get_serializer(suggestion)
                return Response(serializer.data, status=status.HTTP_200_OK)
            elif selected_text is not None:
                # Snippet correction: Return only the corrected snippet
                import re
                snippet = corrected_text_result.strip()
                match = re.search(r"Corrected Text:\s*(.*)", snippet, re.IGNORECASE | re.DOTALL)
                if match:
                    lines = match.group(1).splitlines()
                    for l in lines:
                        l = l.strip()
                        if l:
                            snippet = l
                            break
                else:
                    lines = snippet.splitlines()
                    for line in lines:
                        l = line.strip()
                        if l and not l.lower().startswith(('original', 'context', 'the corrected text is')):
                            snippet = l
                            break
                return Response({'corrected_snippet': snippet}, status=status.HTTP_200_OK)
            else:
                # Fallback: wie bisher, Parsing für KI-Antwort (ganzer Body/Subject)
                final_text_to_save = None
                import re
                quoted_match = re.search(r'["](.+?)["]$', corrected_text_result, re.DOTALL)
                if quoted_match:
                    extracted = quoted_match.group(1).strip()
                    if extracted:
                        final_text_to_save = extracted
                        logger.info(f"Extracted quoted text from AI response: '{final_text_to_save[:100]}...'")
                if final_text_to_save is None:
                    intro_patterns = [
                        r"Here is the corrected text:\s*\n*",
                        r"Corrected text:\s*\n*",
                    ]
                    temp_text = corrected_text_result
                    for pattern in intro_patterns:
                        temp_text = re.sub(f"^{pattern}", "", temp_text, flags=re.IGNORECASE).strip()
                    if temp_text != corrected_text_result and temp_text:
                        final_text_to_save = temp_text
                        logger.info(f"Removed intro phrase, extracted text: '{final_text_to_save[:100]}...'")
                    else:
                        logger.warning(f"Could not reliably extract corrected text from AI response. Using original text instead. AI Response: '{corrected_text_result[:100]}...'")
                        if field == 'subject':
                             final_text_to_save = suggestion.suggested_subject
                        else:
                             final_text_to_save = suggestion.content
                if final_text_to_save is None:
                    logger.error(f"Extraction resulted in None for field '{field}'. Aborting save.")
                    serializer = self.get_serializer(suggestion)
                    return Response(serializer.data, status=status.HTTP_200_OK)
                update_fields = []
                if field == 'subject':
                    suggestion.subject_backup = suggestion.suggested_subject
                    if len(final_text_to_save) > 255:
                        logger.warning(f"Final subject '{final_text_to_save[:50]}...' is too long ({len(final_text_to_save)} chars). Truncating to 255.")
                        suggestion.suggested_subject = final_text_to_save[:255]
                    else:
                        suggestion.suggested_subject = final_text_to_save
                    update_fields = ['suggested_subject', 'subject_backup', 'updated_at']
                else:
                    suggestion.content_backup = suggestion.content
                    suggestion.content = final_text_to_save 
                    update_fields = ['content', 'content_backup', 'updated_at']
                try:
                    suggestion.save(update_fields=update_fields)
                    logger.info(f"Full field '{field}' corrected and saved for suggestion {suggestion.id}.")
                except Exception as save_err:
                    logger.error(f"Error saving corrected field '{field}' for suggestion {suggestion.id}: {save_err}", exc_info=True)
                    raise save_err
                serializer = self.get_serializer(suggestion)
                return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.exception(f"Fehler während Text-Korrektur für Suggestion {suggestion.id}, Feld {field}: {e}")
            return Response({'error': 'An unexpected error occurred during correction.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    @action(detail=True, methods=['post'], url_path='undo-correction', url_name='undo-correction')
    def undo_correction(self, request, pk=None):
        """Undo: Setzt das Feld auf den letzten Wert aus der EditHistory und legt einen Redo-Eintrag an."""
        from mailmind.core.models import AISuggestionEditHistory
        suggestion = self.get_object()
        field = request.data.get('field')  # 'subject' oder 'body'
        if field not in ('subject', 'body'):
            return Response({'error': "Feld muss 'subject' oder 'body' sein."}, status=status.HTTP_400_BAD_REQUEST)
        # Finde letzten EditHistory-Eintrag für dieses Feld (egal ob KI oder manuell)
        last_edit = AISuggestionEditHistory.objects.filter(suggestion=suggestion, field=field).order_by('-created_at').first()
        if not last_edit:
            return Response({'error': f'Kein Undo-Eintrag für {field} vorhanden.'}, status=status.HTTP_400_BAD_REQUEST)
        # Lege Redo-Eintrag an (aktueller Wert → Redo)
        current_value = getattr(suggestion, 'suggested_subject' if field == 'subject' else 'content')
        AISuggestionEditHistory.objects.create(
            suggestion=suggestion,
            field=field,
            old_value=last_edit.new_value,
            new_value=current_value,
            edit_type='redo',
            user=request.user
        )
        # Setze Feld auf old_value
        if field == 'subject':
            suggestion.suggested_subject = last_edit.old_value
        else:
            suggestion.content = last_edit.old_value
        suggestion.save(update_fields=['suggested_subject' if field == 'subject' else 'content', 'updated_at'])
        serializer = self.get_serializer(suggestion)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='redo-correction', url_name='redo-correction')
    def redo_correction(self, request, pk=None):
        """Redo: Stellt den letzten Redo-Eintrag für das Feld wieder her."""
        from mailmind.core.models import AISuggestionEditHistory
        suggestion = self.get_object()
        field = request.data.get('field')  # 'subject' oder 'body'
        if field not in ('subject', 'body'):
            return Response({'error': "Feld muss 'subject' oder 'body' sein."}, status=status.HTTP_400_BAD_REQUEST)
        # Finde letzten Redo-Eintrag
        last_redo = AISuggestionEditHistory.objects.filter(suggestion=suggestion, field=field, edit_type='redo').order_by('-created_at').first()
        if not last_redo:
            return Response({'error': f'Kein Redo-Eintrag für {field} vorhanden.'}, status=status.HTTP_400_BAD_REQUEST)
        # Lege neuen Undo-Eintrag an (aktueller Wert → Undo)
        current_value = getattr(suggestion, 'suggested_subject' if field == 'subject' else 'content')
        AISuggestionEditHistory.objects.create(
            suggestion=suggestion,
            field=field,
            old_value=current_value,
            new_value=last_redo.new_value,
            edit_type='manual',
            user=request.user
        )
        # Setze Feld auf new_value
        if field == 'subject':
            suggestion.suggested_subject = last_redo.new_value
        else:
            suggestion.content = last_redo.new_value
        suggestion.save(update_fields=['suggested_subject' if field == 'subject' else 'content', 'updated_at'])
        serializer = self.get_serializer(suggestion)
        return Response(serializer.data, status=status.HTTP_200_OK)

class ContactViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response([])

    def retrieve(self, request, pk=None):
        return Response({})

class EmailAccountViewSet(viewsets.ModelViewSet):
    """ViewSet für E-Mail-Konten."""
    
    serializer_class = EmailAccountSerializer
    permission_classes = [IsAuthenticated]
    queryset = EmailAccount.objects.all()
    
    def get_queryset(self):
        return EmailAccount.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # Passwort extrahieren, BEVOR es aus validated_data entfernt wird
        password = serializer.validated_data.get('password')
        email_address_for_log = serializer.validated_data.get('email', 'unknown')

        # --- Perform Connection Test BEFORE Saving ---
        logger.info(f"Performing pre-save connection test for {email_address_for_log}")
        try:
            imap_server = serializer.validated_data.get('imap_server')
            imap_port = serializer.validated_data.get('imap_port')
            username = serializer.validated_data.get('username')
            if not password:
                 raise ValueError("Password is required for connection test.")

            with MailBox(imap_server).login(username, password, initial_folder='INBOX') as mailbox:
                logger.info(f"Pre-save IMAP connection successful for {email_address_for_log}")
                pass
        except MailboxLoginError as e:
            logger.warning(f"Pre-save IMAP login failed for {email_address_for_log}: {e}")
            raise serializers.ValidationError(
                {"non_field_errors": [f"Authentication failed. Please check username/password. (Error: {e})"]}
            )
        except Exception as e:
            logger.error(f"Pre-save IMAP connection or other error for {email_address_for_log}: {e}", exc_info=True)
            raise serializers.ValidationError(
                {"non_field_errors": [f"Could not connect to IMAP server. Please check server/port details. (Error: {e})"]}
            )

        # --- Save Account (ohne Passwort-Verschlüsselung durch Serializer) ---
        logger.info(f"Connection test passed. Saving account {email_address_for_log}.")
        print("--- DEBUG: Before serializer.save() ---")
        account = serializer.save(user=self.request.user)
        logger.info(f"[DEBUG] Nach serializer.save(): Account-ID: {account.id}, User-ID: {account.user_id}, User-Email: {self.request.user.email}")
        user_email = self.request.user.email
        user_id = self.request.user.id

        # --- Passwort verschlüsseln und speichern ---
        password_set_successfully = False
        if password:
            print(f"--- DEBUG: Attempting to set password for account {account.id} ---")
            try:
                account.set_password(password) # Modellmethode verwenden
                account.save(update_fields=['password']) # Nur Passwortfeld speichern
                password_set_successfully = True # Flag setzen bei Erfolg
                logger.info(f"[DEBUG] Password successfully set for account {account.id}")
            except Exception as e:
                logger.error(f"[DEBUG] Failed to set/encrypt password for account {account.id}: {e}", exc_info=True)
        logger.info(f"[DEBUG] password_set_successfully={password_set_successfully}, password={'***' if password else None}")
        if password_set_successfully or not password:
            logger.info(f"[DEBUG] Starte initial_sync_task_v2 direkt nach Account-Save für Account {account.id}")
            try:
                async_task('apps.users.tasks.run_initial_sync_for_account_v2', account.id, user_email, user_id)
                logger.info(f"Initial sync v2 task für Account {account.id} wurde direkt gestartet.")
            except Exception as e:
                logger.error(f"[DEBUG] Fehler beim Starten des initial_sync v2 Tasks für Account {account.id}: {e}", exc_info=True)
        else:
            logger.warning(f"[DEBUG] Skipping initial sync task trigger for account {account.id} because password setting failed.")

        logger.info(f"Email account {account.email} (ID: {account.id}) creation process finished in perform_create.")
        print(f"--- DEBUG: Exiting perform_create for account {account.id} ---")
    
    def perform_update(self, serializer):
        """Überschreibt perform_update, um das Passwort korrekt zu behandeln."""
        # Passwort aus validated_data holen, bevor super().save() es entfernt (da write_only)
        password = serializer.validated_data.get('password')
        # OAuth Token ebenfalls hier behandeln
        oauth_token = serializer.validated_data.get('oauth_refresh_token')
        
        # Speichere die restlichen Daten mit dem Serializer
        account = serializer.save()
        
        # Setze das Passwort explizit über die Modellmethode, falls vorhanden
        password_updated = False
        if password:
            try:
                account.set_password(password)
                password_updated = True
                logger.info(f"Password updated and encrypted for account {account.id}")
            except Exception as e:
                logger.error(f"Failed to set/encrypt password during update for account {account.id}: {e}", exc_info=True)
                # Im Fehlerfall wird das Passwort nicht geändert
        elif 'password' in serializer.validated_data and not password:
             # Erlaube explizites Leeren des Passworts
             account.password = ''
             password_updated = True
             logger.info(f"Password explicitly cleared for account {account.id}")
             
        # TODO: OAuth Token verschlüsseln (falls nicht bereits im Serializer/Modell passiert)
        # Aktuell wird oauth_refresh_token nicht im Serializer verschlüsselt
        oauth_token_updated = False
        if oauth_token:
            # Hier fehlt noch die Verschlüsselung für oauth_token!
            # Beispiel: account.set_oauth_token(oauth_token)
            account.oauth_refresh_token = oauth_token # Provisorisch unverschlüsselt speichern!
            oauth_token_updated = True
            logger.warning(f"OAuth token for account {account.id} updated BUT NOT ENCRYPTED!") # Warnung!
        elif 'oauth_refresh_token' in serializer.validated_data and not oauth_token:
             account.oauth_refresh_token = ''
             oauth_token_updated = True
             logger.info(f"OAuth token explicitly cleared for account {account.id}")

        # Speichere das geänderte Passwort/Token, falls nötig
        update_fields = []
        if password_updated:
            update_fields.append('password')
        if oauth_token_updated:
            update_fields.append('oauth_refresh_token')
        
        if update_fields:
            account.save(update_fields=update_fields)
            logger.info(f"Updated fields {update_fields} saved for account {account.id}")
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """IMAP-Verbindung testen."""
        account = self.get_object()
        try:
            # Asynchronen Test starten
            async_task('mailmind.imap.utils.test_connection', account.id)
            return Response({'status': 'test_started'})
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Startet den Initial-Sync-Task für EINEN Account asynchron (wie initial_sync Management Command)."""
        account = self.get_object()
        logger.info(f"[SYNC-DEBUG] (api) Initial-Sync: Account-ID: {account.id}, Account-Email: {account.email}, User-ID: {account.user_id}, User-Email: {account.user.email}")
        from django_q.tasks import async_task
        try:
            task_id = async_task('apps.users.tasks.run_initial_sync_for_account_v2', account.id, account.user.email, account.user_id)
            logger.info(f"[SYNC-DEBUG] (api) async_task Rückgabe: {task_id}")
            if not task_id:
                logger.error(f"[SYNC-DEBUG] (api) async_task hat KEINE Task-ID zurückgegeben! Task wurde NICHT gequeued.")
            else:
                logger.info(f"[SYNC-DEBUG] (api) Task-ID: {task_id} für Account-ID: {account.id}, Account-Email: {account.email}")
        except Exception as e:
            logger.error(f"[SYNC-DEBUG] (api) Fehler beim Queuen des Tasks: {e}", exc_info=True)
        return Response({'status': 'initial_sync_task_queued'})

    def destroy(self, request, *args, **kwargs):
        """Löscht ein E-Mail-Konto und bereinigt zugehörige Tasks und Vektordaten."""
        instance = self.get_object() # Holt das EmailAccount Objekt
        account_id = instance.id
        user_id = instance.user_id
        email_address = instance.email # Für Logging
        logger.info(f"Attempting to delete EmailAccount {account_id} ({email_address}) for user {user_id}")

        # 1. Laufende django-q Tasks stoppen (asynchron, 'delete' löscht nur den Task aus der DB)
        # Task-Namen, die potenziell für diesen Account laufen könnten
        relevant_task_names = [
            'mailmind.imap.tasks.process_folder_metadata_task',
            'mailmind.imap.tasks.process_individual_email_task',
            'mailmind.imap.tasks.save_metadata_task',
            'mailmind.imap.tasks.save_content_task',
            'mailmind.ai.tasks.generate_email_embedding',
            'mailmind.ai.tasks.generate_attachment_embedding',
            'mailmind.ai.tasks.generate_ai_suggestion',
            'mailmind.ai.tasks.generate_embeddings_for_email',
            # Sync-Task hinzufügen (aus perform_create)
            'mailmind.imap.sync.sync_account',
        ]
        
        # 1. Filter tasks by function names first
        candidate_tasks = Task.objects.filter(func__in=relevant_task_names)
        
        # 2. Filter in Python by checking args/kwargs for account_id
        task_ids_to_delete = []
        for task in candidate_tasks:
            try:
                task_args = task.args # This will unpickle
                task_kwargs = task.kwargs # This will unpickle
                
                # Check if account_id is in args (positional arguments)
                # Assumes account_id is usually the first argument for sync
                if isinstance(task_args, tuple) and len(task_args) > 0 and task_args[0] == account_id:
                    task_ids_to_delete.append(task.id)
                    continue # Go to next task
                
                # Check if account_id is in kwargs (keyword arguments)
                if isinstance(task_kwargs, dict) and task_kwargs.get('account_id') == account_id:
                    task_ids_to_delete.append(task.id)
                    continue # Go to next task

            except Exception as e_unpickle: # Handle potential unpickling errors
                logger.warning(f"Could not unpickle arguments for task {task.id} (func: {task.func}): {e_unpickle}")

        deleted_task_count = 0
        if task_ids_to_delete:
            logger.info(f"Found {len(task_ids_to_delete)} queued tasks related to account {account_id}. Attempting to delete...")
            for task_id in task_ids_to_delete:
                try:
                    task = Task.objects.get(id=task_id)
                    # Hinweis: `task.delete()` entfernt den Task nur aus der Queue-DB.
                    # Ein bereits gestarteter Task läuft weiter. Ein robustes Stoppen
                    # würde erfordern, dass die Tasks selbst regelmäßig prüfen, ob
                    # sie abgebrochen werden sollen (z.B. über ein Flag im Account-Modell).
                    logger.info(f"Deleting queued task '{task.name}' (ID: {task.id}) related to account {account_id}")
                    task.delete()
                    deleted_task_count += 1
                except Task.DoesNotExist:
                    logger.warning(f"Task with ID {task_id} not found during deletion for account {account_id}, might have finished or been deleted already.")
                except Exception as e_task_delete:
                    logger.error(f"Error deleting task ID {task_id} for account {account_id}: {e_task_delete}", exc_info=True)
            logger.info(f"Successfully deleted {deleted_task_count} queued tasks related to account {account_id}")
        else:
            logger.info(f"No queued tasks found for account {account_id} to delete.")

        # 2. Qdrant Einträge löschen
        qdrant_error = False
        try:
            logger.info(f"Attempting to delete Qdrant entries for account {account_id}...")
            qdrant_client = get_qdrant_client()
            if not qdrant_client:
                 raise Exception("Failed to get Qdrant client.") # Expliziter Fehler wenn Client None ist
            
            # Definiere den Filter für account_id
            qdrant_filter = rest_models.Filter(
                must=[
                    rest_models.FieldCondition(
                        key="payload.account_id", # Zugriff auf das Feld im Payload
                        match=rest_models.MatchValue(value=account_id)
                    )
                ]
            )
            
            # Löschen in E-Mail-Collection
            email_collection_name = "email_embeddings"
            logger.info(f"Deleting points from Qdrant collection '{email_collection_name}' for account {account_id}")
            email_delete_result = qdrant_client.delete(\
                collection_name=email_collection_name,\
                points_selector=qdrant_filter, # Directly use the filter object\
                wait=True # Warten bis die Operation abgeschlossen ist\
            )
            logger.info(f"Qdrant delete result for '{email_collection_name}' (account {account_id}): {email_delete_result}")

            # Löschen in Attachment-Collection
            attachment_collection_name = "attachment_embeddings"
            logger.info(f"Deleting points from Qdrant collection '{attachment_collection_name}' for account {account_id}")
            attachment_delete_result = qdrant_client.delete(\
                collection_name=attachment_collection_name,\
                points_selector=qdrant_filter, # Directly use the filter object\
                wait=True \
            )
            logger.info(f"Qdrant delete result for '{attachment_collection_name}' (account {account_id}): {attachment_delete_result}")
            logger.info(f"Successfully finished Qdrant deletion process for account {account_id}.")

        except Exception as e:
            qdrant_error = True # Flag setzen bei Fehler
            logger.error(f"CRITICAL: Error deleting Qdrant entries for account {account_id}. Manual cleanup might be required. Error: {e}", exc_info=True)
            # Optional: Fehler an Frontend zurückgeben und Abbruch vor DB-Löschung
            # return Response({"error": "Failed to delete associated vector data. Account not deleted."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. DB Objekt löschen (Standardverhalten der Superklasse)
        if not qdrant_error:
             logger.info(f"Proceeding to delete EmailAccount object {account_id} from database...")
             response = super().destroy(request, *args, **kwargs)
             logger.info(f"EmailAccount {account_id} ({email_address}) successfully deleted from database.")
             return response
        else:
             logger.error(f"Database entry for EmailAccount {account_id} ({email_address}) was NOT deleted due to previous Qdrant error.")
             # Fehler zurückgeben, da Qdrant fehlschlug
             return Response({"error": "Failed to delete associated vector data. Account not deleted."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'], url_path='folders')
    def folders(self, request, pk=None):
        """Ruft die eindeutigen Ordnernamen aus der DB für ein Konto ab."""
        logger.info(f"User {request.user.email} requested DB folder list for account ID {pk}")
        try:
            # Stelle sicher, dass der Account existiert und dem User gehört
            account = self.get_queryset().get(pk=pk)
        except EmailAccount.DoesNotExist:
            logger.warning(f"User {request.user.email} tried to access non-existent or unauthorized account ID {pk} for folder list")
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        
        try:
            # Hole eindeutige Ordnernamen für diesen Account aus der Email-Tabelle
            # Filtere None oder leere Strings heraus, falls vorhanden
            folder_names_qs = Email.objects.filter(account=account).values_list('folder_name', flat=True).distinct()
            # Konvertiere zu Liste und entferne None/leere Werte sauberer
            unique_folder_names = sorted([name for name in folder_names_qs if name]) # Sortiert für Konsistenz
            
            logger.info(f"Found {len(unique_folder_names)} unique folder names in DB for account {pk}")
            # Gib die Liste direkt zurück (Struktur kann vom Frontend angepasst werden)
            return Response({'folders': unique_folder_names})

        except Exception as e:
            logger.error(f"Error fetching unique folder names from DB for account {pk}: {e}", exc_info=True)
            return Response({"detail": f"Error fetching folder list from database: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'], url_path='suggest-settings')
    def suggest_settings(self, request):
        """
        Versucht, IMAP/SMTP-Einstellungen basierend auf der E-Mail-Domain vorzuschlagen.
        Nimmt die E-Mail-Adresse aus dem 'email'-Query-Parameter.
        """
        email_address = request.query_params.get('email', None)
        if not email_address:
            return Response({"error": "Email query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Placeholder for actual suggestion logic
            suggested_data = get_suggested_settings_for_email(email_address)
            logger.info(f"Suggested settings for {email_address}: {suggested_data}")
            return Response(suggested_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error suggesting settings for {email_address}: {e}", exc_info=True)
            return Response({"error": "Failed to suggest settings."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ContactViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet für Kontakte."""
    
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    queryset = Contact.objects.all()
    
    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

class RefreshSuggestionsView(APIView):
    """
    API View to trigger the regeneration of AI suggestions for a specific email.
    Deletes old suggestions, resets the flag, and queues a new task.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, email_id, format=None):
        logger.info(f"Received request to refresh suggestions for email ID: {email_id}")
        try:
            email = Email.objects.get(pk=email_id, account__user=request.user)
            logger.debug(f"Found email {email.id} for user {request.user.email}")

            # 1. Delete existing suggestions for this email
            deleted_count, _ = AISuggestion.objects.filter(email=email).delete()
            logger.info(f"Deleted {deleted_count} existing suggestion(s) for email {email.id}")

            # 2. Reset AI processed flag
            email.ai_processed = False
            email.ai_processed_at = None
            email.save(update_fields=['ai_processed', 'ai_processed_at'])
            logger.info(f"Reset ai_processed flag for email {email.id}")

            # 3. Queue the generation task again
            async_task('mailmind.ai.suggestion_tasks.generate_ai_suggestion', email.id)
            logger.info(f"Queued generate_ai_suggestion task for email {email.id}")

            # Return 202 Accepted status to indicate the process has started
            return Response({"message": "Suggestion refresh initiated."}, status=status.HTTP_202_ACCEPTED)

        except Email.DoesNotExist:
            logger.warning(f"Email with ID {email_id} not found for user {request.user.email}")
            return Response({"error": "Email not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error refreshing suggestions for email {email_id}: {e}", exc_info=True)
            return Response({"error": "An internal error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- Optional: Add view to fetch suggestions if needed for polling ---
# class EmailSuggestionsView(APIView):
#     permission_classes = [permissions.IsAuthenticated]
# 
#     def get(self, request, email_id, format=None):
#         try:
#             email = Email.objects.get(pk=email_id, account__user=request.user)
#             suggestions = AISuggestion.objects.filter(email=email)
#             serializer = AISuggestionSerializer(suggestions, many=True)
#             return Response(serializer.data, status=status.HTTP_200_OK)
#         except Email.DoesNotExist:
#             return Response({"error": "Email not found."}, status=status.HTTP_404_NOT_FOUND)
#         except Exception as e:
#             logger.error(f"Error fetching suggestions for email {email_id}: {e}", exc_info=True)
#             return Response({"error": "An internal error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def correct_text(self, request, pk=None):
        email = self.get_object()
        # Check permissions (e.g., if the email belongs to the user)
        if email.account.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
            
        # Verwende den neuen Pfad für den Suggestion-Task
        async_task('mailmind.ai.suggestion_tasks.generate_ai_suggestion', email.id, triggering_user_id=request.user.id)
        return Response({'status': 'suggestion_task_queued'}, status=status.HTTP_202_ACCEPTED)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def trigger_suggestion(self, request, pk=None):
        email = self.get_object()
        # Check permissions (e.g., if the email belongs to the user)
        if email.account.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
            
        # Verwende den neuen Pfad für den Suggestion-Task
        async_task('mailmind.ai.suggestion_tasks.generate_ai_suggestion', email.id, triggering_user_id=request.user.id)
        return Response({'status': 'suggestion_task_queued'}, status=status.HTTP_202_ACCEPTED) 

# NEU: ViewSet für AI Request Logs
class AIRequestLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API-Endpunkt zum Anzeigen von AI Request Logs.

    Nur Logs des aktuellen Benutzers werden angezeigt.
    Filtert nach: provider, model_name, is_success, triggering_source
    Sortiert nach: timestamp (standardmäßig absteigend)
    Unterstützt Limit/Offset-Pagination.
    """
    serializer_class = AIRequestLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ['provider', 'model_name', 'is_success', 'triggering_source']
    ordering_fields = ['timestamp', 'duration_ms']
    ordering = ['-timestamp'] # Neueste zuerst standardmäßig
    pagination_class = StandardResultsSetPagination # Standard-Pagination verwenden

    def get_queryset(self):
        """Gibt nur Logs zurück, die zum aktuell authentifizierten Benutzer gehören."""
        user = self.request.user
        logger.debug(f"[AIRequestLogViewSet] Getting queryset for user: {user.email}")
        return AIRequestLog.objects.filter(user=user)

    # Override list and retrieve for logging if needed, otherwise standard behavior is fine
    def list(self, request, *args, **kwargs):
        logger.info(f"[AIRequestLogViewSet] List method called by user: {request.user.email}")
        return super().list(request, *args, **kwargs)

    def retrieve(self, request, *args, **kwargs):
        logger.info(f"[AIRequestLogViewSet] Retrieve method called by user: {request.user.email} for PK {kwargs.get('pk')}")
        return super().retrieve(request, *args, **kwargs) 

# Placeholder für die tatsächliche Logik zum Vorschlagen von Einstellungen
def get_suggested_settings_for_email(email_address: str) -> dict:
    logger.info(f"Attempting to find suggested settings for {email_address}")
    # TODO: Implement logic using a library (like email-autodiscover)
    # or a predefined dictionary based on domain.
    # Returning dummy data for now.
    domain = email_address.split('@')[-1].lower()
    if 'gmail.com' in domain:
        return {
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
            "imap_security": "SSL",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 465, # Or 587 for TLS
            "smtp_security": "SSL", # Or "TLS" for port 587
            "username": email_address, # Pre-fill username
            "email": email_address # Pre-fill email
        }
    elif 'outlook.com' in domain or 'hotmail.com' in domain:
         return {
            "imap_server": "outlook.office365.com",
            "imap_port": 993,
            "imap_security": "SSL",
            "smtp_server": "smtp.office365.com",
            "smtp_port": 587,
            "smtp_security": "TLS",
            "username": email_address,
            "email": email_address
        }
    # Fallback/default or error if domain unknown
    logger.warning(f"No predefined settings found for domain: {domain}")
    return {
         "email": email_address # Return at least the email
    } 

class AIActionViewSet(viewsets.ModelViewSet):
    queryset = AIAction.objects.all()
    serializer_class = AIActionSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["post"])
    def run(self, request, pk=None):
        action_obj = self.get_object()
        # Hier: MCP-Task starten (Platzhalter)
        # task_id = start_mcp_action(action_obj, user=request.user)
        return Response({"status": "started", "action": action_obj.name}) 

# NEUE VIEW für direktes Text-Refinement
class RefineTextView(APIView):
    """
    API endpoint to refine text content (subject and body) directly.
    Can be used for general refinement with a custom_prompt OR for pure correction.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        custom_prompt = request.data.get('custom_prompt') # Kann leer sein für reine Korrektur
        current_subject = request.data.get('current_subject')
        current_body = request.data.get('current_body')
        # NEU: Flag, ob es sich um eine reine Korrektur handelt (kein inhaltliches Refinement)
        is_pure_correction = request.data.get('is_pure_correction', False)
        user = request.user

        # current_subject and current_body can be empty strings, but should be present
        if current_subject is None:
            return Response({"error": "current_subject is required (can be empty string)."}, status=status.HTTP_400_BAD_REQUEST)
        if current_body is None:
            return Response({"error": "current_body is required (can be empty string)."}, status=status.HTTP_400_BAD_REQUEST)
        # Custom prompt ist nur erforderlich, wenn es KEINE reine Korrektur ist
        if not is_pure_correction and not custom_prompt:
            return Response({"error": "custom_prompt is required for refinement."}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"RefineTextView: Received request from user {user.email}. Pure correction: {is_pure_correction}")

        # Wähle den Prompt basierend auf is_pure_correction
        prompt_to_use = custom_prompt
        if is_pure_correction:
            # Hier könnte man einen spezifischen Prompt für reine Korrektur laden/generieren
            # Fürs Erste verwenden wir einen einfachen Hinweis oder einen speziellen Prompt aus einer anderen Quelle
            # Beispiel: prompt_to_use = get_correction_prompt() # Diese Funktion müsste erstellt werden
            # Oder wir signalisieren es dem refine_text_content_sync anders, falls es das unterstützt.
            # Für diese Implementierung gehen wir davon aus, dass refine_text_content_sync
            # einen leeren custom_prompt als Signal für reine Korrektur interpretiert oder einen speziellen Prompt intern wählt.
            # Wenn ein spezifischer Prompt für Korrektur geladen werden soll, muss das hier geschehen.
            # Für den Moment, wenn is_pure_correction=True und custom_prompt leer ist, wird das so an refine_text_content_sync gehen.
             logger.info(f"Pure correction mode. Effective prompt for AI: 'Correct grammar and spelling only.' (Conceptual)")

        try:
            # Hinweis: refine_text_content_sync muss ggf. angepasst werden, um is_pure_correction zu berücksichtigen
            # oder einen leeren custom_prompt als reine Korrektur zu interpretieren.
            refined_subject, refined_body = refine_text_content_sync(
                custom_prompt=prompt_to_use, # Wird leer sein, wenn is_pure_correction und kein custom_prompt explizit gesetzt wurde
                original_subject=current_subject,
                original_body=current_body,
                user=user,
                # Optional: is_pure_correction direkt an die Funktion übergeben, falls diese das unterstützt
                # is_pure_correction=is_pure_correction 
            )

            if refined_subject is not None and refined_body is not None:
                logger.info(f"RefineTextView: Successfully refined text for user {user.email}.")
                return Response({
                    "refined_subject": refined_subject,
                    "refined_body": refined_body
                }, status=status.HTTP_200_OK)
            else:
                logger.error(f"RefineTextView: refine_text_content_sync returned None for user {user.email}.")
                return Response({"error": "Failed to refine text. AI service might have failed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        except Exception as e:
            logger.error(f"RefineTextView: Unexpected error for user {user.email}: {e}", exc_info=True)
            return Response({"error": "An unexpected server error occurred during text refinement."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

class DraftViewSet(viewsets.ModelViewSet):
    serializer_class = DraftSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Draft.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        from django.db import transaction, IntegrityError
        try:
            with transaction.atomic():
                serializer.save(user=self.request.user)
        except IntegrityError as e:
            # Upsert-Logik außerhalb des atomic-Blocks!
            email_id = serializer.validated_data.get('email').id if 'email' in serializer.validated_data else None
            if email_id:
                draft = Draft.objects.filter(user=self.request.user, email_id=email_id).first()
                if draft:
                    # Update Draft mit neuen Feldern
                    for field, value in serializer.validated_data.items():
                        if field != 'user' and hasattr(draft, field):
                            setattr(draft, field, value)
                    draft.save()
                    return draft
            raise e

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({'error': 'Forbidden'}, status=403)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({'error': 'Forbidden'}, status=403)
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user:
            return Response({'error': 'Forbidden'}, status=403)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def by_email(self, request):
        email_id = request.query_params.get('email_id')
        if not email_id:
            return Response({'error': 'email_id required'}, status=400)
        draft = Draft.objects.filter(user=request.user, email_id=email_id).first()
        if not draft:
            return Response({}, status=404)
        return Response(DraftSerializer(draft).data) 