"""
Signal-Handler für APICredential-Modell, um crawl4ai über neue/geänderte API-Keys zu informieren.
"""

import logging
import requests
import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import APICredential
from django.conf import settings

logger = logging.getLogger(__name__)

@receiver(post_save, sender=APICredential)
def notify_crawl4ai_api_key_change(sender, instance, created, **kwargs):
    """
    Benachrichtigt den crawl4ai-Service, wenn ein API-Key hinzugefügt oder aktualisiert wurde.
    """
    # Nur für bestimmte Provider weiterleiten (Groq, Google Gemini)
    if instance.provider not in ['groq', 'google_gemini']:
        return
        
    # Abrufen der notwendigen Umgebungsvariablen
    crawl4ai_url = os.environ.get('CRAWL4AI_URL', 'http://crawl4ai:11235')
    django_secret_key = getattr(settings, 'SECRET_KEY', '')
    
    if not django_secret_key:
        logger.error("Django SECRET_KEY nicht verfügbar für crawl4ai-Benachrichtigung")
        return
        
    # Endpunkt für API-Key-Updates
    endpoint = f"{crawl4ai_url}/api-keys/update-api-keys"
    
    # Daten für Request
    payload = {
        "provider": instance.provider,
        "user_id": instance.user.id
    }
    
    # Headers mit Authentifizierung
    headers = {
        "Content-Type": "application/json",
        "X-Internal-Auth": django_secret_key[:32]  # Verwende ersten 32 Zeichen
    }
    
    # Request senden
    try:
        logger.info(f"Benachrichtige crawl4ai über {instance.provider} API-Key-Änderung für Nutzer {instance.user.id}")
        
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=10  # 10 Sekunden Timeout
        )
        
        if response.status_code == 200:
            logger.info(f"crawl4ai erfolgreich über API-Key-Änderung benachrichtigt: {response.json()}")
        else:
            logger.warning(f"Fehler bei der Benachrichtigung von crawl4ai: HTTP {response.status_code} - {response.text}")
            
    except requests.RequestException as e:
        logger.error(f"Kommunikationsfehler mit crawl4ai-Service: {str(e)}")
    except Exception as e:
        logger.exception(f"Unerwarteter Fehler bei der Benachrichtigung von crawl4ai: {str(e)}") 