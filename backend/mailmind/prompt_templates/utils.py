import logging
from django.core.exceptions import ObjectDoesNotExist
from .models import PromptTemplate
from django.core.cache import cache
from django.conf import settings
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

async def get_prompt_details(name: str) -> dict | None:
    """Fetch active prompt details by name, using cache."""
    cache_key = f"prompt_{name}_details"
    cached_details = cache.get(cache_key)

    if cached_details:
        logger.debug(f"Cache hit for prompt details: {name}")
        return cached_details

    logger.debug(f"Cache miss for prompt details: {name}. Fetching from DB.")
    try:
        # Use sync_to_async for the database query
        template = await sync_to_async(PromptTemplate.objects.get)(name=name)
        
        prompt_details = {
            'prompt': template.prompt,
            'provider': template.provider,
            'model_name': template.model_name
        }
        # Cache for specified timeout (e.g., 1 hour)
        cache.set(cache_key, prompt_details, timeout=settings.PROMPT_CACHE_TIMEOUT if hasattr(settings, 'PROMPT_CACHE_TIMEOUT') else 3600)
        logger.info(f"Fetched and cached prompt details for '{name}'")
        return prompt_details
    except PromptTemplate.DoesNotExist:
        logger.warning(f"Prompt template with name '{name}' not found.")
        return None
    except Exception as e:
        # Log the specific error during database access or caching
        logger.error(f"Error fetching prompt template '{name}': {e}", exc_info=True)
        return None

def get_prompt_details_sync(name: str) -> dict | None:
    """Fetch active prompt details by name, using cache (SYNCHRONOUS)."""
    cache_key = f"prompt_{name}_details"
    # Synchroner Cache-Zugriff
    cached_details = cache.get(cache_key)

    if cached_details:
        logger.debug(f"Cache hit for prompt details (sync): {name}")
        return cached_details

    logger.debug(f"Cache miss for prompt details (sync): {name}. Fetching from DB.")
    try:
        # Direkter synchroner DB-Zugriff
        # Stelle sicher, dass PromptTemplate importiert ist
        from .models import PromptTemplate 
        template = PromptTemplate.objects.get(name=name)
        
        prompt_details = {
            # Verwende den tatsächlichen Feldnamen aus dem Modell
            'prompt': template.prompt, 
            'provider': template.provider,
            'model_name': template.model_name
        }
        # Cache synchron setzen
        cache.set(cache_key, prompt_details, timeout=settings.PROMPT_CACHE_TIMEOUT if hasattr(settings, 'PROMPT_CACHE_TIMEOUT') else 3600)
        logger.info(f"Fetched and cached prompt details (sync) for '{name}'")
        return prompt_details
    except PromptTemplate.DoesNotExist:
        logger.warning(f"Prompt template (sync) with name '{name}' not found.")
        return None
    except Exception as e:
        logger.error(f"Error fetching prompt template (sync) '{name}': {e}", exc_info=True)
        return None 