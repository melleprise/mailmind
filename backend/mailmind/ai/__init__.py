"""
AI functionality for mailmind.
"""

# Task imports moved to where they are called/scheduled to avoid AppRegistryNotReady
# from .embedding_tasks import generate_embeddings_for_email
# from .generate_suggestion_task import generate_ai_suggestion
# from .correct_text_task import correct_text_with_ai
# from .refine_suggestion_task import refine_suggestion_with_prompt

# Client and utility imports are generally safe here
from .clients import get_text_model, get_image_model, get_qdrant_client, get_ai_model # Updated to get_ai_model
from .api_calls import call_ai_api # Updated to call_ai_api

default_app_config = 'mailmind.ai.apps.AiConfig' 