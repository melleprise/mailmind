from rest_framework import generics, permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import sync_to_async
from django_celery_beat.models import PeriodicTask, IntervalSchedule
import json
from django.template import Template, Context
from django.core.exceptions import ObjectDoesNotExist

from .models import EmailAccount, Email, Folder, APICredential, AIRequestLog, PromptTemplate # Add PromptTemplate
from .serializers import (
    EmailAccountSerializer,
    EmailAccountCreateSerializer,
    EmailSerializer,
    FolderSerializer,
    APICredentialSerializer,
    AIRequestLogSerializer # Add AIRequestLogSerializer
)
from .tasks import sync_emails_task, process_email_ai_task
from .utils.email_fetcher import EmailFetcher
from .utils.ai_client_factory import get_ai_client, get_ai_client_config

# --- AI Action Views ---

class SuggestFolderStructureView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @method_decorator(csrf_exempt)
    async def post(self, request, *args, **kwargs):
        user = await sync_to_async(lambda: request.user)()
        
        # Fetch email subjects and folders for the user asynchronously
        emails_data = await sync_to_async(list)(
            Email.objects.filter(user=user).values_list('subject', 'folder__name')
        )
        
        if not emails_data:
            return Response({"error": "No emails found to suggest folder structure."}, status=status.HTTP_404_NOT_FOUND)

        # Prepare data for the prompt template context
        email_list_str = "\n".join([f"Subject: {subj or '(No Subject)'}, Current Folder: {folder or '(None)'}" for subj, folder in emails_data])
        prompt_context = Context({"email_list_str": email_list_str})

        try:
            # Load the prompt template from the database asynchronously
            try:
                prompt_template_obj = await sync_to_async(PromptTemplate.objects.get)(
                    name='suggest_folder_structure', 
                    is_active=True
                    # Optionally filter by provider/model if needed later
                )
                prompt_template = Template(prompt_template_obj.template)
                prompt = prompt_template.render(prompt_context)
            except ObjectDoesNotExist:
                 return Response({"error": "'suggest_folder_structure' prompt template not found or not active."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Get the configured AI client
            ai_config = await sync_to_async(get_ai_client_config)(user=user)
            if not ai_config:
                 return Response({"error": "AI provider not configured or API key missing."}, status=status.HTTP_400_BAD_REQUEST)

            # Use the specific model from the loaded template if available and matches the configured provider?
            # For now, let get_ai_client handle the model based on config/defaults.
            # model_override = prompt_template_obj.model_name if prompt_template_obj.provider == ai_config['provider'] else None
            
            ai_client = await sync_to_async(get_ai_client)(
                provider_config=ai_config, 
                action_name="suggest_folder_structure", 
                user=user,
                # model_override=model_override # Pass model if logic added above
            )
            
            # Call the AI provider asynchronously
            ai_response = await ai_client.generate_text(prompt)
            
            # Attempt to parse the JSON response
            try:
                suggested_structure = json.loads(ai_response)
                return Response({"suggested_structure": suggested_structure}, status=status.HTTP_200_OK)
            except json.JSONDecodeError:
                # Log the raw response for debugging
                print(f"AI response (non-JSON) for suggest_folder_structure:\n{ai_response}")
                return Response({"error": "AI response was not valid JSON.", "raw_response": ai_response}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            # Log the exception for debugging
            print(f"Error suggesting folder structure: {e}") 
            # Consider logging the traceback for complex errors
            # import traceback
            # traceback.print_exc()
            return Response({"error": f"An error occurred: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AIRequestLogListView(generics.ListAPIView):
    serializer_class = AIRequestLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # Return logs only for the current user, ordered by timestamp descending
        return AIRequestLog.objects.filter(user=self.request.user).order_by('-timestamp')


class CheckApiKeysView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    async def post(self, request, *args, **kwargs):
        user = await sync_to_async(lambda: request.user)()
        results = {}
        has_error = False

        # Fetch all credentials for the user asynchronously
        credentials = await sync_to_async(list)(APICredential.objects.filter(user=user))
        
        credential_map = {cred.provider: cred for cred in credentials}

        # Check each supported provider
        for provider_config in settings.SUPPORTED_AI_PROVIDERS:
            provider_id = provider_config['id']
            provider_name = provider_config['name']
            results[provider_id] = {'name': provider_name, 'status': 'not_configured', 'error': None}

            if provider_id in credential_map:
                credential = credential_map[provider_id]
                if not credential.api_key:
                    results[provider_id]['status'] = 'configured_no_key'
                    results[provider_id]['error'] = 'API Key is configured but empty.'
                    has_error = True
                    continue
                
                try:
                    # Get a client instance to test the key
                    ai_client_config = await sync_to_async(get_ai_client_config)(user=user, provider_id=provider_id)
                    if not ai_client_config:
                        # Should not happen if credential exists, but check anyway
                         results[provider_id]['status'] = 'error'
                         results[provider_id]['error'] = 'Could not retrieve client configuration.'
                         has_error = True
                         continue

                    ai_client = await sync_to_async(get_ai_client)(
                        provider_config=ai_client_config,
                        action_name="check_api_key", 
                        user=user
                    )
                    
                    # Perform a simple test call (e.g., list models or a small generation)
                    # This needs to be implemented in the specific client classes
                    # We wrap this potentially synchronous call from the library using sync_to_async
                    is_valid = await sync_to_async(ai_client.check_connection)() 

                    if is_valid:
                        results[provider_id]['status'] = 'valid'
                    else:
                        # The check_connection method should ideally raise an exception on failure,
                        # but we handle a boolean return just in case.
                        results[provider_id]['status'] = 'invalid'
                        results[provider_id]['error'] = 'API key validation failed (client returned false).'
                        has_error = True
                        
                except Exception as e:
                    # Specific exceptions (like AuthenticationError) are better, 
                    # but catch broadly for now.
                    print(f"Error checking API key for {provider_name}: {e}")
                    results[provider_id]['status'] = 'invalid'
                    results[provider_id]['error'] = f'Validation failed: {str(e)}'
                    has_error = True
            
        # Determine overall status code
        response_status = status.HTTP_200_OK if not has_error else status.HTTP_400_BAD_REQUEST
        
        return Response(results, status=response_status)

# --- Other Views ---
# ... rest of the views ... 