from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model, authenticate
from django.core.mail import send_mail
from django.conf import settings
import uuid
from django.db import transaction
from .models import EmailVerification, Email, EmailAccount, APICredential, AvailableApiModel, AIRequestLog
from .serializers import UserRegistrationSerializer, EmailVerificationSerializer, LoginSerializer, EmailAccountSerializer, EmailAccountTestSerializer, SuggestSettingsSerializer, UserSerializer, EmailSerializer, APICredentialSerializer, APICredentialCheckSerializer, AvailableApiModelSerializer, AIRequestLogListSerializer, AIRequestLogDetailSerializer, CreateFoldersSerializer, EmailDetailSerializer
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.authtoken.models import Token
import logging
import secrets
from django.shortcuts import render, get_object_or_404
from rest_framework import generics, viewsets, permissions, mixins
from imap_tools import MailBox
from imap_tools.errors import MailboxLoginError, ImapToolsError
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from rest_framework.decorators import action
from django_q.tasks import async_task
# from mailmind.ai.tasks import generate_ai_suggestion # Auskommentiert, da Task deaktiviert ist
from allauth.account.views import ConfirmEmailView as AllauthConfirmEmailView
from allauth.account.utils import send_email_confirmation
from allauth.account.models import EmailAddress
from groq import Groq, AuthenticationError, APIConnectionError, GroqError, APIError as GroqAPIError # Import GroqAPIError
from rest_framework.exceptions import ValidationError, AuthenticationFailed
from rest_framework.authentication import TokenAuthentication
from google.api_core import exceptions as google_exceptions
import google.generativeai as genai # Import google.generativeai as genai
from django.http import Http404, JsonResponse, HttpResponseNotAllowed
# Imports for manual encryption in view
from cryptography.fernet import Fernet
import base64
from .models import get_api_credential_encryption_key
import httpx
import os
import json
from datetime import timedelta, timezone
from django.db import IntegrityError
from mailmind.ai.models_discovery import discover_models_for_provider # <-- Import model discovery function
from asgiref.sync import sync_to_async, async_to_sync # <-- Import sync_to_async and async_to_sync
# Import pagination class
from rest_framework.pagination import PageNumberPagination
from mailmind.ai.clients import get_groq_client, get_gemini_model # Nur die benötigten importieren
from rest_framework.exceptions import NotAuthenticated, PermissionDenied, APIException # Import specific exceptions
import re
# Import the new async auth class
# from .authentication import AsyncTokenAuthentication # No longer needed here
# Import the PromptTemplate model
from mailmind.prompt_templates.models import PromptTemplate
from .utils import get_imap_connection # Assuming you have a helper like this

# Import IMAP actions (needed for MarkEmailSpamView)
from mailmind.imap import actions as imap_actions
from mailmind.imap.utils import map_folder_name_to_server
from imap_tools import MailMessageFlags
import smtplib

User = get_user_model()
logger = logging.getLogger(__name__)

# Custom Pagination Class with default page size
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'limit'
    max_page_size = 1000

@method_decorator(csrf_exempt, name='dispatch')
class UserRegistrationView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        # Logge die eingehenden Daten als ERROR, um sicherzustellen, dass sie angezeigt werden
        logger.error(f"Registration request data received: {request.data}")
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"Registration validation failed: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        # Rückgabe einer Erfolgsmeldung anstelle der Userdaten
        return Response({
            "message": "Registration successful. Please check your email to verify your account."
        }, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        user = None # Initialize user to None
        try:
            # Keep user creation within the transaction
            with transaction.atomic():
                user = serializer.save()
                # Create verification token immediately after user save
                verification = EmailVerification.objects.create(
                    user=user,
                    token=secrets.token_urlsafe(32)
                )

            # Attempt to send email AFTER the transaction is committed
            if user and verification: # Check if user and verification object exist
                try:
                    verification_url = f"{settings.FRONTEND_URL}/verify-email/{verification.token}"
                    logger.info(f"Attempting to send verification email to {user.email} using backend {settings.EMAIL_BACKEND}")
                    # Stelle den ursprünglichen Inhalt wieder her:
                    send_mail(
                        'Verify your email', # Ursprünglicher Betreff
                        f'Please click the following link to verify your email: {verification_url}', # Ursprünglicher Body mit Link
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False, # Keep this False to raise errors
                    )
                    logger.info(f"Successfully called send_mail for {user.email}")
                except Exception as mail_error:
                    # Log the specific email sending error
                    logger.error(f"Failed to send verification email to {user.email}: {mail_error}", exc_info=True)
                    # Decide if you want to raise an error here or just log it.
                    # If you don't raise, the registration appears successful even if email fails.

        except Exception as e:
            # This will catch errors during user/token creation inside the transaction
            logger.error(f"Error during user or token creation for data {serializer.validated_data}: {str(e)}", exc_info=True)
            # Re-raise the exception to indicate failure of registration
            raise e

def send_verification_email(user):
    from django.core.mail import send_mail
    from django.conf import settings
    from .models import EmailVerification
    verification, _ = EmailVerification.objects.get_or_create(user=user)
    verification_url = f"{settings.FRONTEND_URL}/verify-email/{verification.token}"
    subject = 'Verify your email'
    message = f'Please click the following link to verify your email: {verification_url}'
    old_debug = smtplib.SMTP.debuglevel
    smtplib.SMTP.debuglevel = 1
    try:
        result = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
    finally:
        smtplib.SMTP.debuglevel = old_debug
    return result

class ResendVerificationEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        logger.debug(f"ResendVerificationEmailView aufgerufen mit Email: {email}")
        try:
            user = User.objects.get(email=email)
            logger.debug(f"User gefunden: {user.email}, is_active={user.is_active}")
        except User.DoesNotExist:
            logger.warning(f"User mit Email {email} nicht gefunden.")
            return Response({'message': 'User not found.'}, status=404)
        if user.is_active:
            logger.info(f"User {email} ist bereits aktiv. Keine Mail gesendet.")
            return Response({'message': 'User already active.'}, status=200)
        # Für inaktive User: Mail senden!
        try:
            logger.info(f"Sende Verification-Mail an {user.email} mit Backend {settings.EMAIL_BACKEND}")
            result = send_verification_email(user)
            logger.debug(f"send_verification_email Rückgabe: {result}")
        except Exception as e:
            logger.error(f"Fehler beim Senden der Verification-Mail: {e}", exc_info=True)
            return Response({'message': 'Fehler beim Senden der Mail.'}, status=500)
        return Response({'message': 'Verification email sent.'}, status=200)

class EmailVerificationView(APIView):
    permission_classes = [AllowAny]
    serializer_class = EmailVerificationSerializer

    def get(self, request, token):
        try:
            verification = EmailVerification.objects.get(token=token)
            
            if verification.is_expired():
                verification.delete()
                return Response(
                    {'error': 'Verification token has expired'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = verification.user
            if user.is_email_verified:
                return Response(
                    {'error': 'Email is already verified'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.is_email_verified = True
            user.is_active = True
            user.save()
            verification.delete()

            return Response(
                {'message': 'Email verification successful'},
                status=status.HTTP_200_OK
            )

        except EmailVerification.DoesNotExist:
            return Response(
                {'error': 'Invalid verification token'},
                status=status.HTTP_400_BAD_REQUEST
            )

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        token = serializer.validated_data['token']
        try:
            verification = EmailVerification.objects.get(token=token)
            
            if verification.is_expired():
                verification.delete()
                return Response(
                    {'error': 'Verification token has expired'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user = verification.user
            if user.is_email_verified:
                return Response(
                    {'message': 'Email is already verified'},
                    status=status.HTTP_200_OK
                )
                
            user.is_email_verified = True
            user.is_active = True
            user.save()
            verification.delete()
            
            return Response({
                'message': 'Email verification successful. You can now log in.'
            }, status=status.HTTP_200_OK)
                
        except EmailVerification.DoesNotExist:
            return Response({
                'error': 'Invalid verification token'
            }, status=status.HTTP_400_BAD_REQUEST)

@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Log received data
        logger.error(f"Login request data received: {request.data}")

        # Accept either 'username' or 'email'
        username = request.data.get('username') or request.data.get('email')
        password = request.data.get('password')

        logger.error(f"Attempting authentication with username/email: '{username}'")

        if not username or not password:
            logger.error("Login failed: Username/Email or Password missing.")
            return Response({'error': 'Username/Email and password are required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Use Django's authenticate function - try authenticating with email first, then username
        # This handles cases where ACCOUNT_AUTHENTICATION_METHOD might be 'email' or 'username_email'
        user = authenticate(request, email=username, password=password)
        if user is None:
            # If email auth failed, try treating the input as a username
            user = authenticate(request, username=username, password=password)

        if user is not None:
            logger.info(f"Authentication successful for user: {user.email}")
            if user.is_active:
                logger.info(f"User {user.email} is active. Generating token.")
                token, _ = Token.objects.get_or_create(user=user)
                serializer = UserSerializer(user)
                logger.info(f"Returning token and user data for {user.email}")
                return Response({'token': token.key, 'user': serializer.data})
            else:
                logger.warning(f"Authentication failed: User {user.email} is inactive.")
                return Response({'error': 'Account is inactive. Please verify your email.'}, status=status.HTTP_403_FORBIDDEN)
        else:
            logger.warning(f"Authentication failed for username/email: '{username}'.")
            # Check if user exists but password was wrong
            try:
                User.objects.get(email=username)
                logger.warning(f"Login failed: User '{username}' exists, but password was incorrect.")
                # Avoid giving away too much info, keep generic message but log specifics
                return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)
            except User.DoesNotExist:
                logger.warning(f"Login failed: User '{username}' does not exist.")
                # Avoid giving away too much info, keep generic message but log specifics
                return Response({'error': 'Invalid Credentials'}, status=status.HTTP_401_UNAUTHORIZED)

@method_decorator(csrf_exempt, name='dispatch')
class EmailAccountTestConnectionView(APIView):
    """Tests IMAP connection settings without saving them."""
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = EmailAccountTestSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Email account test validation failed: {serializer.errors}")
            return Response({
                "status": "validation_error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        logger.info(f"Testing IMAP connection for {data['email']} on {data['imap_server']}")

        try:
            # Versuche Login mit imap-tools
            with MailBox(data['imap_server']).login(data['username'], data['password'], initial_folder='INBOX') as mailbox:
                # Login war erfolgreich, wenn hier kein Fehler auftritt
                logger.info(f"IMAP connection successful for {data['email']}")
                # Optional: Kurze Info holen, z.B. Ordnerliste (nicht notwendig für reinen Login-Test)
                # folders = mailbox.folder.list()
                # print(f"Folders: {folders}") 
                pass # Nichts weiter tun, nur Login testen

            return Response({
                "status": "success",
                "message": "IMAP connection successful!"
            }, status=status.HTTP_200_OK)

        except MailboxLoginError as e:
            logger.error(f"IMAP login failed for {data['email']}: {e}")
            return Response({
                "status": "error",
                "message": f"Authentication failed. Please check username/password. (Error: {e})"
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Unterscheide hier ggf. noch, aber für den Test erstmal allgemein
            logger.error(f"IMAP connection or other error for {data['email']}: {e}")
            return Response({
                "status": "error",
                # Passe die Fehlermeldung an
                "message": f"Could not connect or other error occurred. Please check server/port or logs. (Error: {e})"
            }, status=status.HTTP_400_BAD_REQUEST) 

@method_decorator(csrf_exempt, name='dispatch')
class SuggestEmailSettingsView(APIView):
    """Suggests IMAP/SMTP settings based on email domain."""
    permission_classes = [AllowAny]

    # Einfaches Dictionary für bekannte Provider
    # TODO: Dies könnte in eine Datenbanktabelle oder Konfigurationsdatei ausgelagert werden
    KNOWN_PROVIDER_SETTINGS = {
        'gmail.com': {
            'imap_server': 'imap.gmail.com',
            'imap_port': 993,
            'imap_use_ssl': True,
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587, 
            'smtp_use_tls': True, 
        },
        'googlemail.com': { # Alias für Gmail
            'imap_server': 'imap.gmail.com',
            'imap_port': 993,
            'imap_use_ssl': True,
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587, 
            'smtp_use_tls': True, 
        },
        'outlook.com': {
            'imap_server': 'outlook.office365.com', 
            'imap_port': 993,
            'imap_use_ssl': True,
            'smtp_server': 'smtp.office365.com',
            'smtp_port': 587,
            'smtp_use_tls': True,
        },
        'hotmail.com': { # Alias für Outlook
            'imap_server': 'outlook.office365.com', 
            'imap_port': 993,
            'imap_use_ssl': True,
            'smtp_server': 'smtp.office365.com',
            'smtp_port': 587,
            'smtp_use_tls': True,
        },
        'gmx.net': {
            'imap_server': 'imap.gmx.net',
            'imap_port': 993,
            'imap_use_ssl': True,
            'smtp_server': 'mail.gmx.net',
            'smtp_port': 587,
            'smtp_use_tls': True,
        },
        'web.de': {
            'imap_server': 'imap.web.de',
            'imap_port': 993,
            'imap_use_ssl': True,
            'smtp_server': 'smtp.web.de',
            'smtp_port': 587,
            'smtp_use_tls': True,
        },
        # ... weitere Provider hier hinzufügen ...
    }

    def post(self, request, *args, **kwargs):
        serializer = SuggestSettingsSerializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Suggest settings validation failed: {serializer.errors}")
            return Response({
                "status": "validation_error",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        email = serializer.validated_data['email']
        domain = email.split('@')[1].lower() if '@' in email else None

        if not domain:
             return Response({
                "status": "error",
                "message": "Invalid email address provided."
            }, status=status.HTTP_400_BAD_REQUEST)

        settings = self.KNOWN_PROVIDER_SETTINGS.get(domain)

        if settings:
            logger.info(f"Suggested settings found for domain: {domain}")
            return Response({
                "status": "success",
                "settings": settings
            }, status=status.HTTP_200_OK)
        else:
            logger.info(f"No suggested settings found for domain: {domain}")
            # Optional: Standardwerte für unbekannte Domains zurückgeben?
            # settings = { 'imap_server': '', 'imap_port': 993, ... }
            return Response({
                "status": "not_found",
                "message": f"Could not automatically determine settings for {domain}. Please enter them manually."
            }, status=status.HTTP_404_NOT_FOUND) 

class UserDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data) 

# ViewSet for Email model
class EmailViewSet(viewsets.ReadOnlyModelViewSet): # ReadOnly for now
    """API endpoint that allows emails to be viewed."""
    authentication_classes = [TokenAuthentication]
    # Use EmailDetailSerializer by default to include markdown_body
    permission_classes = [IsAuthenticated]
    # Use the custom pagination class
    pagination_class = StandardResultsSetPagination # <-- Use custom pagination

    def get_serializer_class(self):
        """Return appropriate serializer class based on action."""
        if self.action == 'list':
            return EmailSerializer
        elif self.action == 'retrieve':
            return EmailDetailSerializer
        # Default to EmailSerializer for other potential actions if any
        return EmailSerializer 

    def get_queryset(self):
        """Return emails for the current authenticated user only."""
        user = self.request.user
        # Filter by folder name if provided in query params
        folder_name = self.request.query_params.get('folder_name')
        if folder_name:
            # Correct filter: Access user through the 'account' relation
            return Email.objects.filter(account__user=user, folder_name=folder_name).order_by('-received_at') # Order newest first
        else:
            # Default to INBOX if no folder specified, or maybe all folders?
            # Let's default to INBOX for now.
            # Correct filter: Access user through the 'account' relation
            return Email.objects.filter(account__user=user, folder_name='INBOX').order_by('-received_at')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            # Ensure the serializer context includes the request for potential use in serializers
            serializer = self.get_serializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        # Ensure the serializer context includes the request
        serializer = self.get_serializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object() # get_object handles the 404 if not found for the user
        # Ensure the serializer context includes the request
        serializer = self.get_serializer(instance, context={'request': request})
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='generate-suggestions')
    def generate_suggestions(self, request, pk=None):
        """Triggers the asynchronous generation of AI suggestions for a specific email."""
        email = self.get_object() # Gets the email instance based on pk
        triggering_user_id = request.user.id # Get the ID of the user making the request
        logger.info(f"Received request from User ID {triggering_user_id} to generate suggestions for Email ID: {email.id}")
        
        # Start the background task and pass email ID and triggering user ID
        async_task('mailmind.ai.tasks.generate_ai_suggestion', email.id, triggering_user_id=triggering_user_id)
        
        # Return a success response immediately
        logger.info(f"Task to generate suggestions for Email ID {email.id} queued successfully.")
        return Response({"status": "Suggestion generation task queued."}, status=status.HTTP_202_ACCEPTED)

# ViewSet for EmailAccount model (New)
class EmailAccountViewSet(viewsets.ModelViewSet):
    """API endpoint that allows email accounts to be viewed or edited."""
    authentication_classes = [TokenAuthentication]
    serializer_class = EmailAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """This view should return a list of all email accounts for the currently authenticated user."""
        return EmailAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """Ensure the account belongs to the requesting user."""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Leitet den Sync-Call an die neue Logik in mailmind.api.views weiter."""
        from mailmind.api.views import EmailAccountViewSet as NewEmailAccountViewSet
        return NewEmailAccountViewSet.sync(self, request, pk)

# ViewSet for APICredential model
class APICredentialViewSet(mixins.CreateModelMixin,
                           mixins.RetrieveModelMixin,
                           mixins.UpdateModelMixin,
                           mixins.DestroyModelMixin,
                           viewsets.GenericViewSet):
    """
    Manages API Credentials for the authenticated user.
    Allows users to GET, POST, PUT, DELETE their own credentials for specific providers.
    Uses provider name in the URL for retrieve, update, destroy.
    """
    serializer_class = APICredentialSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'provider'

    def get_queryset(self):
        """Ensures users only see their own credentials."""
        return APICredential.objects.filter(user=self.request.user)

    def get_object(self):
        """
        Override get_object to lookup by user and provider from URL.
        Raises Http404 if not found for the current user and provider.
        """
        queryset = self.get_queryset()
        provider = self.kwargs.get(self.lookup_field)
        if not provider:
             raise Http404("Provider not found in URL.")

        obj = get_object_or_404(queryset, provider=provider)
        
        # <<< Logging added >>>
        logger.debug(f"APICredentialViewSet: Checking object permissions for user {self.request.user.id}, provider {provider}, object {obj.id}")
        try:
            self.check_object_permissions(self.request, obj)
            logger.debug(f"APICredentialViewSet: Object permissions check passed for user {self.request.user.id}, provider {provider}")
        except Exception as perm_error:
            logger.error(f"APICredentialViewSet: Object permissions check FAILED for user {self.request.user.id}, provider {provider}: {perm_error}", exc_info=True)
            raise # Re-raise the permission error
        # <<< End Logging added >>>
            
        return obj

    def retrieve(self, request, *args, **kwargs):
        """GET /api/v1/core/api-credentials/{provider}/"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            # --- DEBUGGING --- 
            print(f"DEBUG: Serializer data for provider {kwargs.get(self.lookup_field)}: {serializer.data}")
            # --- END DEBUGGING ---
            return Response(serializer.data)
        except Http404:
            logger.debug(f"No API credential found for user {request.user.id}, provider {kwargs.get(self.lookup_field)}")
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider = serializer.validated_data['provider']
        api_key = serializer.validated_data['api_key']

        # Check if credential already exists for this user and provider
        existing_credential = APICredential.objects.filter(
            user=request.user,
            provider=provider
        ).first()

        if existing_credential:
            logger.warning(f"Attempt to POST duplicate API credential for user {request.user.id} and provider {provider}")
            return Response(
                {"detail": f"API credential for {provider} already exists. Use PUT to update."},
                status=status.HTTP_409_CONFLICT
            )

        # Test the API key before saving
        try:
            self._test_api_key(provider, api_key)
            logger.info(f"API key test successful for user {request.user.id}, provider {provider}")
        except Exception as e:
            if isinstance(e, (google_exceptions.PermissionDenied, google_exceptions.InvalidArgument, GroqAPIError)):
                error_message = f"The provided API key for {provider} appears to be invalid or lacks permissions. Please check the key. (Details: {str(e)})"
                logger.warning(f"API key test failed (Invalid Key?) for user {request.user.id}, provider {provider}: {str(e)}")
                return Response({"detail": error_message}, status=status.HTTP_400_BAD_REQUEST)
            elif isinstance(e, google_exceptions.GoogleAPIError):
                error_message = f"Could not connect or communicate with the {provider} API. Check network/service status. (Details: {str(e)})"
                logger.error(f"API communication error for user {request.user.id}, provider {provider}: {error_message}")
                return Response({"detail": error_message}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            elif isinstance(e, NotImplementedError):
                error_message = str(e)
                logger.error(f"API key test configuration error for user {request.user.id}, provider {provider}: {error_message}")
                return Response({"detail": f"Internal configuration error: {error_message}"}, status=status.HTTP_501_NOT_IMPLEMENTED)
            else:
                error_message = f"An unexpected error occurred while testing the {provider} API key. Error: {str(e)}"
                logger.exception(f"Unexpected API key test error for user {request.user.id}, provider {provider}")
                return Response({"detail": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # --- Key test passed, proceed with saving --- 
        try:
            # Call perform_create correctly
            instance = self.perform_create(serializer) # perform_create returns the instance
            logger.info(f"API credential for provider {provider} created successfully for user {request.user.id}")

            # --- NEU: Trigger Model Discovery Task nach erfolgreichem Erstellen ---
            if instance:
                try:
                    logger.info(f"Triggering check_api_key_task for {instance.provider} after creation for user {instance.user.id}")
                    decrypted_key = instance.get_api_key() # Entschlüsseln für den Task
                    if decrypted_key:
                         async_task('mailmind.ai.tasks.check_api_key_task', instance.user.id, instance.provider, decrypted_key)
                    else:
                        logger.error(f"Could not trigger check_api_key_task after creation because key decryption failed for instance ID {instance.id}.")
                except Exception as task_err:
                     # Fehler beim Queuen des Tasks loggen, aber den ursprünglichen Erfolg nicht überschreiben
                     logger.error(f"Failed to queue check_api_key_task for provider {instance.provider} after creation: {task_err}", exc_info=True)
            # --- ENDE NEU ---

            # FIX: Serialize the *instance* first, then get headers from *that* serializer's data
            response_serializer = self.get_serializer(instance)
            headers = self.get_success_headers(response_serializer.data) # Get headers from the representation of the instance

            return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        
        except IntegrityError as e:
             # Keep IntegrityError catch
            logger.error(f"IntegrityError during API credential creation for user {request.user.id}, provider {provider}: {e}", exc_info=True)
            return Response({"detail": "Conflict: Could not create API credential due to a race condition or existing entry."}, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"Unexpected error during API credential creation/saving for user {request.user.id}, provider {provider}: {e}", exc_info=True)
            return Response({"detail": "An unexpected error occurred while saving the API credential."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_create(self, serializer):
        """
        Creates the APICredential instance, calls set_api_key for encryption,
        and saves it. Returns the created instance.
        Called by create().
        """
        # Don't save the serializer directly yet.
        # Create an instance without saving.
        instance = APICredential(
            user=self.request.user,
            provider=serializer.validated_data['provider']
            # Don't pass api_key or encrypted_api_key here
        )
        # Call the instance method to encrypt and set the key
        instance.set_api_key(serializer.validated_data['api_key'])
        # Now save the instance with the encrypted key
        instance.save()
        logger.debug(f"perform_create created and saved instance with encrypted key for user {self.request.user.id}, provider {serializer.validated_data['provider']}")
        return instance # Return the saved instance

    def update(self, request, *args, **kwargs):
        # FIX: Set partial=True to allow partial updates even with PUT
        partial = True
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial) # Pass partial=True
        serializer.is_valid(raise_exception=True) # Validation should now pass without 'provider' in body

        provider = instance.provider # Get provider from instance
        api_key = serializer.validated_data['api_key'] # api_key is still required by serializer

        # Test the API key before saving the update
        try:
            self._test_api_key(provider, api_key)
            logger.info(f"API key test successful for user {request.user.id}, provider {provider} during update")
        except Exception as e:
            # Similar exception handling as in create
            if isinstance(e, (google_exceptions.PermissionDenied, google_exceptions.InvalidArgument, GroqAPIError)):
                error_message = f"The provided API key for {provider} appears to be invalid or lacks permissions. Please check the key. (Details: {str(e)})"
                logger.warning(f"API key test failed (Invalid Key?) during update for user {request.user.id}, provider {provider}: {str(e)}")
                return Response({"detail": error_message}, status=status.HTTP_400_BAD_REQUEST)
            elif isinstance(e, google_exceptions.GoogleAPIError):
                error_message = f"Could not connect or communicate with the {provider} API during update. Check network/service status. (Details: {str(e)})"
                logger.error(f"API communication error during update for user {request.user.id}, provider {provider}: {error_message}")
                return Response({"detail": error_message}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
            elif isinstance(e, NotImplementedError):
                 error_message = str(e)
                 logger.error(f"API key test configuration error during update for user {request.user.id}, provider {provider}: {error_message}")
                 return Response({"detail": f"Internal configuration error: {error_message}"}, status=status.HTTP_501_NOT_IMPLEMENTED)
            else:
                error_message = f"An unexpected error occurred while testing the {provider} API key during update. Error: {str(e)}"
                logger.exception(f"Unexpected API key test error during update for user {request.user.id}, provider {provider}")
                return Response({"detail": error_message}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # --- Key test passed, proceed with update --- 
        try:
            # Call perform_update correctly
            instance = self.perform_update(serializer) # perform_update now returns the instance
            logger.info(f"API credential for provider {provider} updated successfully for user {request.user.id}")

            # --- NEU: Trigger Model Discovery Task nach erfolgreichem Update ---
            if instance:
                try:
                    logger.info(f"Triggering check_api_key_task for {instance.provider} after update for user {instance.user.id}")
                    decrypted_key = instance.get_api_key() # Entschlüsseln für den Task
                    if decrypted_key:
                         async_task('mailmind.ai.tasks.check_api_key_task', instance.user.id, instance.provider, decrypted_key)
                    else:
                        logger.error(f"Could not trigger check_api_key_task after update because key decryption failed for instance ID {instance.id}.")
                except Exception as task_err:
                     # Fehler beim Queuen des Tasks loggen, aber den ursprünglichen Erfolg nicht überschreiben
                     logger.error(f"Failed to queue check_api_key_task for provider {instance.provider} after update: {task_err}", exc_info=True)
            # --- ENDE NEU ---

            # FIX: Muss NACH dem Trigger stehen, damit instance bekannt ist
            if getattr(instance, '_prefetched_objects_cache', None):
                instance._prefetched_objects_cache = {}

            # Return the updated data using the serializer with the updated instance
            response_serializer = self.get_serializer(instance)
            return Response(response_serializer.data)
        except Exception as e:
            logger.error(f"Unexpected error during API credential update/saving for user {request.user.id}, provider {provider}: {e}", exc_info=True)
            return Response({"detail": "An unexpected error occurred while updating the API credential."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_update(self, serializer):
        """
        Updates the APICredential instance by calling set_api_key and saving.
        Returns the updated instance. Called by update().
        """
        instance = serializer.instance # Get the instance from the serializer
        # Call the instance method to encrypt and set the new key
        instance.set_api_key(serializer.validated_data['api_key'])
        # Save the updated instance
        instance.save()
        logger.debug(f"perform_update updated and saved instance with encrypted key for user {instance.user.id}, provider {instance.provider}")
        return instance # Return the updated instance

    def destroy(self, request, *args, **kwargs):
        """DELETE /api/v1/core/api-credentials/{provider}/"""
        instance = self.get_object()
        provider = instance.provider # Get provider name for logging
        try:
            self.perform_destroy(instance)
            logger.info(f"API credential for provider {provider} deleted successfully for user {request.user.id}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting API credential for provider {provider}, user {request.user.id}: {e}", exc_info=True)
            return Response({"detail": "An error occurred while deleting the API credential."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # perform_destroy is inherited from DestroyModelMixin and just calls instance.delete()

    def _test_api_key(self, provider, api_key):
        """
        Tests the provided API key with the corresponding service.
        Raises specific exceptions on failure.
        """
        logger.info(f"Testing {provider} API key for user {self.request.user.id}")
        if provider == 'google_gemini':
            try:
                genai.configure(api_key=api_key)
                _ = genai.list_models()
                logger.info(f"Google Gemini API key test successful for user {self.request.user.id}")
                return True
            except (google_exceptions.PermissionDenied, google_exceptions.InvalidArgument) as e:
                logger.error(f"Google Gemini API key test failed (Permission/Argument Error) for user {self.request.user.id}: {str(e)}")
                raise e
            except google_exceptions.GoogleAPIError as e:
                 logger.error(f"Google Gemini API key test failed (API Error) for user {self.request.user.id}: {str(e)}")
                 raise e
            except Exception as e:
                logger.error(f"Unexpected error during Google Gemini API key test for user {self.request.user.id}: {str(e)}", exc_info=True)
                raise e

        elif provider == 'groq':
            http_client = None
            try:
                # Explicitly create httpx client, ignoring environment proxies
                http_client = httpx.Client(trust_env=False, timeout=10.0)
                client = Groq(api_key=api_key, http_client=http_client)
                _ = client.models.list()
                logger.info(f"Groq API key test successful for user {self.request.user.id}")
                return True
            except GroqAPIError as e:
                logger.error(f"Groq API key test failed for user {self.request.user.id}: {str(e)}")
                raise e
            except Exception as e:
                logger.error(f"Unexpected error during Groq API key test for user {self.request.user.id}: {str(e)}", exc_info=True)
                raise e
            finally:
                 if http_client:
                     http_client.close()
                     logger.debug("Closed explicit httpx client for Groq test.")
        else:
            raise NotImplementedError(f"API key testing is not implemented for the provider '{provider}'.")

# New function to update models in DB (atomic transaction)
@transaction.atomic
def update_available_models(provider: str, models_data: list):
    """Deletes old models for the provider and saves new ones."""
    # Delete existing models for this provider first
    AvailableApiModel.objects.filter(provider=provider).delete()
    
    # Create new model entries
    models_to_create = []
    for model_info in models_data:
        if model_info.get('id'): # Ensure model ID exists
            models_to_create.append(
                AvailableApiModel(
                    provider=provider,
                    model_id=model_info['id'],
                    model_name=model_info.get('name', '') # Use name if available, else empty
                )
            )
    
    if models_to_create:
        AvailableApiModel.objects.bulk_create(models_to_create, ignore_conflicts=True) # ignore_conflicts for safety
        logger.info(f"Saved {len(models_to_create)} models for provider {provider}.")
    else:
        logger.info(f"No new models to save for provider {provider}.")

# Helper function remains static or can be moved outside
@staticmethod
def get_user_from_token_sync(token_key):
    try:
        return Token.objects.select_related('user').get(key=token_key).user
    except Token.DoesNotExist:
        raise AuthenticationFailed('Invalid token.')

# Importiere csrf_exempt wieder
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseNotAllowed

# Wandle zurück zu synchroner Funktion, aber mit GET und Key aus DB
#@csrf_exempt # Nicht mehr nötig für GET
def api_credential_check_view(request, provider):
    """Synchronous function-based view to check the user's stored API key."""
    
    # Manuelle Prüfung der HTTP-Methode
    if request.method != 'POST': 
        logger.warning(f"Method {request.method} not allowed for api_credential_check_view (expecting POST).")
        return HttpResponseNotAllowed(['POST'])
    
    # --- Manuelle Token-Authentifizierung (wie gehabt) --- 
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.lower().startswith('token '):
        return JsonResponse({"error": "Authorization header missing or invalid."}, status=401)
    
    token_key = auth_header.split()[1]
    try:
        user = get_user_from_token_sync(token_key) 
        if not user.is_active:
             return JsonResponse({"error": "User inactive or deleted."}, status=401)
    except AuthenticationFailed as e:
         return JsonResponse({"error": str(e)}, status=401)
    except Exception as e:
         logger.error(f"Unexpected error during manual token auth: {e}", exc_info=True)
         return JsonResponse({"error": "Authentication error."}, status=500)
    # --- Ende Manuelle Authentifizierung --- 
    
    current_user = user 

    # Provider kommt jetzt direkt als Argument von der URL
    if not provider:
        return JsonResponse({"error": "Provider not specified in URL."}, status=400)

    # Validate provider against choices
    valid_providers = [choice[0] for choice in APICredential.PROVIDER_CHOICES]
    if provider not in valid_providers:
        return JsonResponse({"error": f"Invalid provider: {provider}."}, status=400)
        
    # API-Key aus der Datenbank holen und entschlüsseln
    try:
        credential = APICredential.objects.get(user=current_user, provider=provider)
        api_key = credential.get_api_key() # Holt und entschlüsselt den Key
        if not api_key:
             # Fehler, wenn Key nicht gesetzt oder Entschlüsselung fehlschlägt
             logger.warning(f"Failed to get/decrypt API key for user {current_user.id}, provider {provider}.")
             return JsonResponse({"error": f"API key for {provider} is not set or could not be decrypted."}, status=404)
    except APICredential.DoesNotExist:
        logger.warning(f"No API credential found for user {current_user.id}, provider {provider}.")
        return JsonResponse({"error": f"API credential for {provider} not found."}, status=404)
    except Exception as e:
         # Andere Fehler beim Holen/Entschlüsseln
         logger.error(f"Error retrieving/decrypting API key for user {current_user.id}, provider {provider}: {e}", exc_info=True)
         return JsonResponse({"error": "Failed to retrieve API key."}, status=500)

    # Trigger the asynchronous check task mit dem entschlüsselten Key
    async_task('mailmind.ai.tasks.check_api_key_task', current_user.id, provider, api_key)
    
    # Modelerkennung wird asynchron im Task gemacht, hier nur Bestätigung
    logger.info(f"Check task queued for provider: {provider}, user: {current_user.id}")
    return JsonResponse({"message": f"Check initiated for {provider}. Status will be updated via WebSocket."}, status=202)

# --- END: Convert Class View to Function View ---

class AvailableApiModelListView(generics.ListAPIView):
    """API endpoint to list available models discovered for a specific provider."""
    serializer_class = AvailableApiModelSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Filter models based on the provider specified in the URL."""
        provider = self.kwargs.get('provider')
        if not provider:
            # This should ideally not happen due to URL routing, but good practice
            return AvailableApiModel.objects.none()
            
        # Validate provider against choices
        valid_providers = [choice[0] for choice in APICredential.PROVIDER_CHOICES]
        if provider not in valid_providers:
             raise Http404("Invalid provider specified.") # Raise 404 if provider is invalid

        # Return models for the specific provider
        return AvailableApiModel.objects.filter(provider=provider).order_by('model_id')

# --- BEGIN: AIRequestLog ViewSet ---

class AIRequestLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint to view AI request logs for the authenticated user."""
    permission_classes = [permissions.IsAuthenticated]
    # Use different serializers for list and retrieve
    serializer_class = AIRequestLogListSerializer # Default for list

    def get_queryset(self):
        """Users can only see their own request logs."""
        return AIRequestLog.objects.filter(user=self.request.user).order_by('-timestamp')

    def get_serializer_class(self):
        """Return different serializers for list and retrieve actions."""
        if self.action == 'retrieve':
            return AIRequestLogDetailSerializer
        return super().get_serializer_class()

# --- END: AIRequestLog ViewSet ---

# --- BEGIN: Suggest Folder Structure View ---

@method_decorator(transaction.non_atomic_requests, name='dispatch')
class SuggestFolderStructureView(APIView):
    """
    Uses AI to suggest a folder structure based on the user's emails.
    Requires an active AI provider configuration.
    """
    # Use the standard synchronous authentication class
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    # Define a simple structure for the expected AI response
    def _validate_ai_response(self, data):
        if not isinstance(data, dict):
            return False
        for key, value in data.items():
            if not isinstance(key, str) or not isinstance(value, dict):
                return False
            # Allow empty dicts as valid leaf nodes
            if value != {} and not self._validate_ai_response(value):
                 return False
        return True

    def post(self, request, *args, **kwargs):
        # Use request.user directly, handled by standard TokenAuthentication
        user = request.user
        
        if not user or not user.is_authenticated:
            raise NotAuthenticated()

        logger.info(f"Folder structure suggestion requested by user: {user.email}")

        # 1. Get User's AI Credential (use request.user)
        try:
            # Use standard sync filter and get, or wrap afirst if needed
            # Assuming APICredential access is infrequent, a sync call might be okay,
            # but let's wrap afirst for consistency with async nature of the operation.
            credential = async_to_sync(APICredential.objects.filter(user=request.user).afirst)()
            if not credential:
                 raise APIException("No AI provider configured. Please configure an API key in settings.", code=status.HTTP_400_BAD_REQUEST)
            
            provider = credential.provider
            # get_api_key is sync, no need to wrap sync_to_async call
            api_key = credential.get_api_key()
            if not api_key:
                raise APIException(f"Could not decrypt API key for provider '{provider}'.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            logger.info(f"Using AI provider '{provider}' for folder suggestion for user {user.email}")

        except Exception as e:
            logger.exception(f"Error retrieving or decrypting API credential for user {user.email}: {e}")
            raise APIException(f"Error accessing AI configuration: {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2. Initialize Provider-Specific Client/Model
        ai_client_instance = None
        gemini_model_instance = None
        try:
            if provider == 'groq':
                # Use await with sync_to_async if get_groq_client isn't async itself
                # Assuming get_groq_client is synchronous as it involves httpx.Client
                ai_client_instance = get_groq_client(api_key)
                if not ai_client_instance:
                    raise APIException("Failed to initialize Groq client.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif provider == 'google_gemini':
                # Configure Gemini API key
                try:
                    # configure is likely synchronous
                    genai.configure(api_key=api_key)
                    # get_gemini_model is likely synchronous
                    gemini_model_instance = get_gemini_model() # Use default model or get from settings
                    if not gemini_model_instance:
                         raise APIException("Failed to initialize Gemini model.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)
                except Exception as gemini_e:
                     raise APIException(f"Failed to configure or initialize Gemini: {gemini_e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                raise APIException(f"AI provider '{provider}' is not supported for folder suggestions yet.", code=status.HTTP_501_NOT_IMPLEMENTED)
        except Exception as e:
             logger.exception(f"Error initializing AI provider '{provider}' for user {user.email}: {e}")
             raise APIException(f"Error setting up AI connection for '{provider}': {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. Gather Email Metadata (wrap async list call)
        logger.info(f"Fetching email metadata for user {user.email}...")
        try:
            # Fetch full Email objects instead of just values to access related fields easily
            email_objects_queryset = Email.objects.filter(account__user=user).select_related(
                'from_contact' # Optimize if needed
            ).prefetch_related(
                'to_contacts' # Prefetch the contacts
            ).order_by('-received_at')[:1000] # Limit the number of emails fetched

            # Define the synchronous operation
            def get_email_objects_list(qs):
                return list(qs) # This triggers the DB query

            # Wrap it to be awaitable (DB access is thread sensitive)
            async_get_list = sync_to_async(get_email_objects_list, thread_sensitive=True)

            # Call the awaitable from the sync context
            email_objects = async_to_sync(async_get_list)(email_objects_queryset)
            # --- End correct async handling ---

            logger.info(f"Fetched {len(email_objects)} email objects for user {user.email} (limit 1000).")
            if not email_objects:
                return Response({"message": "No emails found to analyze."}, status=status.HTTP_200_OK)
        except Exception as e:
            logger.exception(f"Error fetching email objects for folder suggestion (user {user.email}): {e}")
            raise APIException("Error retrieving email data.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        prompt_metadata = []
        for email in email_objects:
             # Extract contact emails from the related field
             to_contact_emails = [contact.email for contact in email.to_contacts.all()[:5]]
             prompt_metadata.append({
                 "subject": getattr(email, 'subject', '')[:100],
                 "from": getattr(email, 'from_address', ''),
                 "to": to_contact_emails, # Use the extracted list of emails
                 "folder": getattr(email, 'folder_name', 'INBOX')
             })

        # 4. Construct the Prompt (load from DB)
        try:
            # Load the template from the database
            template = PromptTemplate.objects.get(name='suggest_folder_structure')
            # TODO: Consider matching template provider/model with the user's configured AI provider?
            # For now, just use the template as defined.
            
            # Prepare context for formatting
            context = {
                "user_email": user.email,
                "email_metadata_json": json.dumps(prompt_metadata, indent=2)
            }
            prompt = template.prompt.format(**context)
            logger.info(f"Using prompt template '{template.name}' for user {user.email}.")
            # Potentially override provider/model based on template? Or ensure they match credential?
            # provider = template.provider
            # model_to_use = template.model_name
            # Re-initialize client if provider/model changed? (Might be complex)
            
        except PromptTemplate.DoesNotExist:
            logger.error("Prompt template 'suggest_folder_structure' not found in the database.")
            raise APIException("Required prompt template is missing.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except KeyError as e:
            logger.error(f"Missing key '{e}' in prompt template context.")
            raise APIException(f"Error formatting prompt template: Missing key {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 5. Call the AI (Provider-Specific)
        logger.info(f"Sending prompt to AI provider '{provider}' for user {user.email}...")
        ai_response_text = None
        try:
            if provider == 'groq' and isinstance(ai_client_instance, Groq):
                # Groq API call remains synchronous based on current implementation
                completion = ai_client_instance.chat.completions.create(
                   messages=[{"role": "user", "content": prompt}],
                   model="llama3-8b-8192", # Or another suitable model
                   temperature=0.2, # Lower temperature for more predictable structure
                   response_format={"type": "json_object"} # Request JSON directly if supported
                )
                ai_response_text = completion.choices[0].message.content

            elif provider == 'google_gemini' and gemini_model_instance:
                # Gemini API call (generate_content might be async or sync)
                # Assuming generate_content is synchronous here
                response = gemini_model_instance.generate_content(prompt)
                ai_response_text = response.text

            else:
                # Ensure this block has the correct indentation
                raise APIException(f"AI provider '{provider}' is not supported for folder suggestions yet.", code=status.HTTP_501_NOT_IMPLEMENTED)

            if not ai_response_text:
                # Ensure this block has the correct indentation
                raise APIException("AI returned an empty response.", code=status.HTTP_500_INTERNAL_SERVER_ERROR)

            logger.debug(f"Raw AI response for user {user.email}:\n{ai_response_text}")

            # 6. Parse and Validate JSON Response (same as before)
            # Ensure this block has the correct indentation
            try:
                json_match = re.search(r'\{.*\}', ai_response_text, re.DOTALL)
                if not json_match:
                    raise ValueError("No JSON object found in the AI response.")
                suggested_structure = json.loads(json_match.group(0))
                if not self._validate_ai_response(suggested_structure):
                    raise ValueError("AI response is not a valid nested dictionary structure.")
                logger.info(f"Successfully parsed folder structure suggestion for user {user.email}.")
                return Response(suggested_structure, status=status.HTTP_200_OK)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to decode JSON from AI response for user {user.email}: {e}\nRaw Response: {ai_response_text}")
                raise APIException(f"AI response was not valid JSON: {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR)
            except ValueError as e:
                logger.error(f"Invalid structure in AI response for user {user.email}: {e}\nRaw Response: {ai_response_text}")
                raise APIException(f"AI response format was invalid: {e}", code=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            # Generic AI call error handling (same as before)
            # Ensure this block has the correct indentation
            logger.exception(f"Error during AI call for folder suggestion (user {user.email}, provider {provider}): {e}")
            error_detail = str(e)
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            # ... (rest of error handling remains the same) ...
            if "authentication" in error_detail.lower() or "api key" in error_detail.lower():
                error_detail = "AI authentication failed. Check your API key."
                status_code = status.HTTP_401_UNAUTHORIZED
            elif "quota" in error_detail.lower():
                error_detail = "AI request failed due to quota limits."
                status_code = status.HTTP_429_TOO_MANY_REQUESTS
            elif "connection" in error_detail.lower():
                error_detail = "Could not connect to the AI service."
                status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            raise APIException(f"AI request failed: {error_detail}", code=status_code)
        finally:
            # Ensure Groq client's http_client is closed if it exists
            # Ensure this block has the correct indentation
            if provider == 'groq' and isinstance(ai_client_instance, Groq):
                # Check if the client has an http_client attribute and close it
                # Check both _client and http_client attributes
                client_to_close = getattr(ai_client_instance, '_client', None) or getattr(ai_client_instance, 'http_client', None)

                if client_to_close and hasattr(client_to_close, 'is_closed') and not client_to_close.is_closed():
                    # httpx clients have a sync close method
                    if hasattr(client_to_close, 'close'):
                        try:
                            client_to_close.close()
                            logger.info(f"Closed Groq HTTP client (sync) for user {user.email}.")
                        except Exception as close_err:
                            logger.error(f"Error closing Groq sync client: {close_err}", exc_info=True)
                    # Check for async close if sync isn't available (less likely for httpx.Client)
                    elif hasattr(client_to_close, 'aclose'):
                        try:
                            async_to_sync(client_to_close.aclose)()
                            logger.info(f"Closed Groq HTTP client (async wrapped) for user {user.email}.")
                        except Exception as aclose_err:
                            logger.error(f"Error closing Groq async client: {aclose_err}", exc_info=True)

# --- END: Suggest Folder Structure View ---

# --- BEGIN: Create Folders View ---
@method_decorator(transaction.non_atomic_requests, name='dispatch')
class CreateFoldersView(APIView):
    """
    Creates IMAP folders based on a list of paths for a specific account.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = CreateFoldersSerializer
    authentication_classes = [TokenAuthentication] # Add authentication

    def post(self, request, account_id, *args, **kwargs):
        logger.info(f"Folder creation requested for account ID {account_id} by user {request.user.id}")

        # 1. Get and validate the EmailAccount
        try:
            account = EmailAccount.objects.get(pk=account_id, user=request.user)
        except EmailAccount.DoesNotExist:
            logger.warning(f"Folder creation failed: Account {account_id} not found or not owned by user {request.user.id}")
            return Response({"detail": "Email account not found or access denied."}, status=status.HTTP_404_NOT_FOUND)
        
        if not account.is_active:
             logger.warning(f"Folder creation failed: Account {account_id} is inactive.")
             return Response({"detail": "Email account is inactive."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. Validate incoming folder paths
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Folder creation validation failed for account {account_id}: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        folder_paths_to_create = serializer.validated_data['folder_paths']
        logger.info(f"Attempting to create {len(folder_paths_to_create)} folders for account {account.id}")

        # 3. Define the prefix
        FOLDER_PREFIX = "MailMind" # Changed prefix

        created_folders = []
        failed_folders = {}
        
        # 4. Connect to IMAP and create folders (synchronously for now)
        try:
            with get_imap_connection(account) as mailbox:
                # Get the delimiter used by the server
                delimiter = mailbox.folder().delimiter or '/' # Default to /
                logger.info(f"Using delimiter '{delimiter}' for account {account.id}")
                
                for relative_path in folder_paths_to_create:
                    # Construct the full path with prefix and correct delimiter
                    full_path = f"{FOLDER_PREFIX}{delimiter}{relative_path.replace('/', delimiter)}" # Ensure internal slashes use the correct delimiter
                    logger.info(f"Attempting to create folder: '{full_path}'")
                    try:
                        # Check if folder exists before creating
                        if not mailbox.folder.exists(full_path):
                             create_result = mailbox.folder.create(full_path)
                             if create_result: # Check if create returns success (might vary by server/library version)
                                 logger.info(f"Successfully created folder: '{full_path}'")
                                 created_folders.append(full_path)
                             else:
                                 # Handle cases where create returns false/None without error
                                 logger.warning(f"Folder creation command for '{full_path}' did not return success, but no error raised.")
                                 failed_folders[relative_path] = "Creation command did not confirm success."
                        else:
                            logger.info(f"Folder '{full_path}' already exists, skipping.")
                            # Optionally add to created_folders if existing is considered success
                            created_folders.append(full_path + " (already existed)") 
                            
                    except Exception as folder_err: # Catch other potential errors during creation
                        logger.error(f"Unexpected error creating folder '{full_path}': {folder_err}", exc_info=True)
                        failed_folders[relative_path] = f"Unexpected error: {folder_err}"

        except MailboxLoginError as login_err:
            logger.error(f"IMAP login failed during folder creation for account {account.id}: {login_err}", exc_info=True)
            return Response({"detail": f"IMAP login failed: {login_err}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except ImapToolsError as imap_err:
            logger.error(f"IMAP error during folder creation for account {account.id}: {imap_err}", exc_info=True)
            return Response({"detail": f"IMAP communication error: {imap_err}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            logger.exception(f"Unexpected error during folder creation process for account {account.id}: {e}")
            return Response({"detail": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 5. Return result
        response_data = {
            "message": "Folder creation process completed.",
            "created_count": len(created_folders),
            "failed_count": len(failed_folders),
            "created_folders": created_folders, # Include list of created/existing folders
            "failed_folders": failed_folders # Include specific errors for failed folders
        }
        
        status_code = status.HTTP_200_OK
        if failed_folders:
             response_data["message"] = "Folder creation process completed with errors."
        
        logger.info(f"Folder creation result for account {account.id}: {response_data}")
        return Response(response_data, status=status_code)

# --- END: Create Folders View ---

# --- ADD MarkEmailSpamView HERE --- 
class MarkEmailSpamView(APIView):
    """API View to mark an email as read and move it to the Spam folder."""
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [TokenAuthentication] # Ensure authentication is checked

    def post(self, request, pk):
        """Handles POST request to mark email as Spam."""
        try:
            # Ensure the email belongs to the requesting user
            email = get_object_or_404(Email.objects.select_related('account'), pk=pk, account__user=request.user)
            account = email.account

            logger.info(f"User {request.user.id} marking email {email.id} as spam.")

            # 1. Mark as Read (Set \Seen flag)
            # Use the generic flag_email function with the SEEN flag
            logger.warning(f"Calling flag_email synchronously to mark email {email.id} as SEEN")
            from mailmind.imap.actions import flag_email # Import the correct function
            from imap_tools import MailMessageFlags # Import the flags enum
            
            # Call flag_email to SET the SEEN flag
            flag_success = flag_email(email.id, [str(MailMessageFlags.SEEN)], True) 
            
            if flag_success:
                email.is_read = True # Optimistically update instance state
                logger.info(f"Synchronously marked email {email.id} as read (called flag_email).")
            else:
                logger.error(f"flag_email call to mark {email.id} as read failed.")

            # 2. Move to Spam folder
            move_success = imap_actions.move_email(email.id, 'Spam') # Use logical name

            if move_success:
                logger.info(f"Successfully marked email {email.id} as spam (moved/flagged).")
                # Optionally: Trigger WebSocket update if needed
                return Response({"message": "Email marked as spam."}, status=status.HTTP_200_OK)
            else:
                # Even if marking read failed, the primary action (move) failed here.
                 logger.error(f"Failed to move email {email.id} to Spam folder via IMAP.")
                 return Response({"error": "Failed to move email to spam folder."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Email.DoesNotExist:
             # Use 404 for not found
             return Response({"error": "Email not found or access denied."}, status=status.HTTP_404_NOT_FOUND)
        except EmailAccount.DoesNotExist: # Should be caught by the initial query, but good practice
             logger.error(f"Consistency error: EmailAccount not found for email {pk}")
             return Response({"error": "Associated email account not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error marking email {pk} as spam: {e}", exc_info=True)
            return Response({"error": "An unexpected error occurred."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
# --- END MarkEmailSpamView ---

@api_view(['POST'])
@permission_classes([])
def internal_get_api_key_view(request):
    """
    Interner Endpunkt zum Abrufen von API-Schlüsseln für andere Services.
    Authentifizierung erfolgt über den X-Internal-Auth Header.
    
    Erwartet POST mit JSON:
    {
        "provider": "google_gemini", # oder andere Provider
        "user_id": 2  # optional, Standard ist user_id=2
    }
    
    Gibt API-Schlüssel für den Provider zurück:
    {
        "api_key": "abc123",
        "error": null
    }
    """
    # Authentifizierung über SECRET_KEY
    auth_header = request.headers.get('X-Internal-Auth')
    if not auth_header or auth_header[:32] != settings.SECRET_KEY[:32]:
        return Response(
            {"error": "Ungültiger Authentifizierungstoken", "api_key": None},
            status=403
        )
    
    provider = request.data.get('provider')
    user_id = request.data.get('user_id', 2)
    
    if not provider:
        return Response(
            {"error": "Provider muss angegeben werden", "api_key": None},
            status=400
        )
        
    try:
        # Suche nach API-Credentials für den angegebenen Nutzer und Provider
        credential = APICredential.objects.filter(
            user_id=user_id,
            provider=provider
        ).first()
        
        if not credential:
            return Response(
                {"error": f"Keine API-Credentials für Nutzer {user_id} und Provider {provider} gefunden", "api_key": None},
                status=200  # Sende 200 OK, um Existenz von Credentials nicht preiszugeben
            )
        
        # Test-Modus: Wenn der API-Key mit "TEST-" beginnt, gib ihn direkt zurück
        if credential.api_key_encrypted.startswith('TEST-'):
            return Response({"api_key": credential.api_key_encrypted, "error": None}, status=200)
            
        try:
            # API-Key entschlüsseln
            api_key = credential.get_api_key()
            return Response({"api_key": api_key, "error": None}, status=200)
        except Exception as e:
            return Response(
                {"error": f"API-Key für Nutzer {user_id} und Provider {provider} konnte nicht entschlüsselt werden", "api_key": None},
                status=200
            )
            
    except Exception as e:
        return Response(
            {"error": str(e), "api_key": None},
            status=500
        )