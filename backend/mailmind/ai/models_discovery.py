import logging
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import httpx
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

async def discover_google_gemini_models(api_key: str) -> List[Dict[str, str]]:
    """Fetches available models from the Google Gemini API."""
    if not api_key:
        logger.warning("Google Gemini API key is not configured.")
        return []
    try:
        genai.configure(api_key=api_key)
        models_list = []
        # Note: genai.list_models() might be synchronous. If running in async context,
        # consider running it in a thread pool executor if it blocks.
        # For now, assuming it's okay or the calling context handles it.
        for m in genai.list_models():
            # Example: Include models usable for content generation
            if 'generateContent' in m.supported_generation_methods:
                models_list.append({"id": m.name, "name": m.display_name})
        logger.info(f"Discovered {len(models_list)} Google Gemini models.")
        return models_list
    except google_exceptions.PermissionDenied:
        logger.warning("Google Gemini API key is invalid or lacks permissions.")
        raise ValueError("Invalid Google Gemini API Key") # Raise specific error for handling
    except Exception as e:
        logger.error(f"Error discovering Google Gemini models: {e}", exc_info=True)
        # Don't raise here, maybe the API is temporarily down, return empty list
        return []

async def discover_groq_models(api_key: str) -> List[Dict[str, str]]:
    """Fetches available models from the Groq API (OpenAI compatible endpoint)."""
    if not api_key:
        logger.warning("Groq API key is not configured.")
        return []

    groq_api_base = "https://api.groq.com/openai/v1"
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{groq_api_base}/models", headers=headers)

            if response.status_code == 401:
                 logger.warning("Groq API key is invalid.")
                 raise ValueError("Invalid Groq API Key") # Raise specific error for handling
            
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            data = response.json()
            models_data = data.get("data", []) # Hole die Liste
            
            # --- DEBUG: Logge das erste Modell-Objekt --- 
            if models_data:
                 logger.info(f"[DEBUG] First Groq model object structure: {models_data[0]}")
            # --- END DEBUG ---
            
            # Aktuelle Extraktion (kann später angepasst werden)
            models_list = [{"id": model.get("id"), "name": model.get("id")} 
                           for model in models_data if model.get("id")]
                           
            logger.info(f"Discovered {len(models_list)} Groq models.")
            return models_list
    except httpx.RequestError as e:
        logger.error(f"HTTP Request Error discovering Groq models: {e}")
        return [] # Network error, return empty
    except httpx.HTTPStatusError as e:
         # We already handled 401, log other HTTP errors
         logger.error(f"HTTP Status Error discovering Groq models: {e.response.status_code} - {e.response.text}")
         return [] # Server error, return empty
    except Exception as e:
        logger.error(f"Unexpected error discovering Groq models: {e}", exc_info=True)
        return [] # General error, return empty


async def discover_models_for_provider(provider: str, api_key: str) -> List[Dict[str, str]]:
    """Dispatches model discovery based on the provider."""
    if provider == 'google_gemini':
        return await discover_google_gemini_models(api_key)
    elif provider == 'groq':
        return await discover_groq_models(api_key)
    # Add other providers here
    # elif provider == 'openai':
    #     return await discover_openai_models(api_key)
    else:
        logger.warning(f"Model discovery not implemented for provider: {provider}")
        return [] 