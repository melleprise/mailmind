import logging
from rest_framework.response import Response
from rest_framework import status
from groq import Groq, AuthenticationError, APIConnectionError
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
import httpx
# Add imports for IMAP connection
from imap_tools import MailBox
from imap_tools.errors import MailboxLoginError
from contextlib import contextmanager
from .models import EmailAccount # To get account details

logger = logging.getLogger(__name__)

@contextmanager
def get_imap_connection(account: EmailAccount):
    """
    Context manager to establish and close an IMAP connection for a given EmailAccount.
    Handles fetching the password securely.
    Raises MailboxLoginError on login failure.
    Yields the MailBox instance.
    """
    if not account or not isinstance(account, EmailAccount):
        raise ValueError("Valid EmailAccount instance is required.")

    mailbox = None
    try:
        password = account.get_password() # Fetch decrypted password
        if not password:
            raise MailboxLoginError(f"No password available for account {account.email}")
        
        logger.debug(f"Attempting IMAP connection to {account.imap_server}:{account.imap_port} for {account.email}...")
        mailbox = MailBox(account.imap_server, port=account.imap_port, ssl=account.imap_use_ssl)
        mailbox.login(account.email, password) # Use account.email as username if separate username not stored
        logger.debug(f"IMAP login successful for {account.email}.")
        yield mailbox
    except MailboxLoginError as e:
        logger.error(f"IMAP login failed for {account.email}: {e}")
        raise # Re-raise the specific login error
    except Exception as e:
        logger.exception(f"Unexpected error during IMAP connection/login for {account.email}: {e}")
        raise ImapToolsError(f"Unexpected IMAP connection error: {e}") # Raise a general IMAP error
    finally:
        if mailbox and mailbox.is_logged_in():
            try:
                mailbox.logout()
                logger.debug(f"IMAP logout successful for {account.email}.")
            except Exception as logout_err:
                logger.warning(f"Error during IMAP logout for {account.email}: {logout_err}")

def validate_api_key(provider, api_key, user_id='unknown'):
    """
    Tests the API key for the given provider. 
    Returns a dictionary with 'status' ('valid' or 'invalid') and 'message'.
    """
    if not api_key:
        return {'status': 'invalid', 'message': 'API key cannot be empty for testing.'}

    if provider == 'groq':
        logger.info(f"Validating Groq API key for user {user_id}")
        http_client = None # Initialize
        try:
            # Explicitly create httpx client, ignoring environment proxies
            http_client = httpx.Client(trust_env=False, timeout=10.0)
            client = Groq(api_key=api_key, http_client=http_client)
            client.models.list()
            logger.info(f"Groq API key validation successful for user {user_id}.")
            return {'status': 'valid', 'message': 'Groq API Key is working.'}
        except AuthenticationError as e:
            logger.warning(f"Groq API key validation failed for user {user_id}: AuthenticationError - {e}")
            return {'status': 'invalid', 'message': 'Groq API Key is invalid or expired.'}
        except APIConnectionError as e:
            logger.error(f"Groq API key validation failed for user {user_id}: APIConnectionError - {e}")
            return {'status': 'invalid', 'message': f"Could not connect to Groq API. Check network/status. Error: {e}"}
        except Exception as e:
            logger.exception(f"Groq API key validation failed for user {user_id}: Unexpected error - {e}")
            return {'status': 'invalid', 'message': f"An unexpected error occurred: {e}"}
        finally:
            # Ensure client is closed
            if http_client:
                try:
                    http_client.close()
                    logger.debug(f"Closed httpx client for Groq validation in utils for user {user_id}.")
                except Exception as close_err:
                    logger.error(f"Error closing httpx client during Groq validation: {close_err}", exc_info=True)
    
    elif provider == 'google_gemini': 
        logger.info(f"Validating Google Gemini API key for user {user_id}")
        try:
            genai.configure(api_key=api_key)
            models = genai.list_models()
            if not any(m for m in models if 'generateContent' in m.supported_generation_methods):
                logger.warning(f"Google Gemini API key validation failed for user {user_id}: No usable models found.")
                return {'status': 'invalid', 'message': "Key valid, but no usable models found. Check GCP permissions/APIs."}
            logger.info(f"Google Gemini API key validation successful for user {user_id}.")
            return {'status': 'valid', 'message': 'Google Gemini API Key is working.'}
        except (google_exceptions.PermissionDenied, google_exceptions.Unauthenticated) as e:
             logger.warning(f"Google Gemini API key validation failed for user {user_id}: PermissionDenied/Unauthenticated - {e}")
             return {'status': 'invalid', 'message': f"Key invalid or permissions denied. Check key and GCP settings. Error: {e}"}
        except google_exceptions.GoogleAPIError as e:
             logger.error(f"Google Gemini API key validation failed for user {user_id}: GoogleAPIError - {e}")
             return {'status': 'invalid', 'message': f"Could not connect to Google API. Check network/status. Error: {e}"}
        except Exception as e:
            logger.exception(f"Google Gemini API key validation failed for user {user_id}: Unexpected error - {e}")
            return {'status': 'invalid', 'message': f"An unexpected error occurred: {e}"}
    else:
        logger.warning(f"No specific API key validation implemented for provider '{provider}' for user {user_id}. Assuming valid.")
        # Betrachte unbekannte Provider als gültig
        return {'status': 'valid', 'message': f"Validation not implemented for {provider}, assuming okay."} 