#!/usr/bin/env python3
"""
Test-Skript für den API-Key-Updater.
Sendet eine Anfrage an den Endpunkt, um einen API-Key zu aktualisieren.
"""

import requests
import argparse
import os
import logging
import json
import sys

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_api_key_updater')

def test_api_key_updater(provider, user_id=2, django_secret_key=None, crawl4ai_url=None):
    """
    Testet den API-Key-Updater-Endpunkt.
    
    Args:
        provider: Der Provider-Name (groq, google_gemini)
        user_id: Die ID des Nutzers (Standard: 2)
        django_secret_key: Der Django-Secret-Key für die Authentifizierung (optional)
        crawl4ai_url: Die URL des crawl4ai-Services (optional)
    """
    # Standardwerte überschreiben, wenn Parameter angegeben wurden
    crawl4ai_url = crawl4ai_url or os.environ.get('CRAWL4AI_URL', 'http://localhost:11235')
    django_secret_key = django_secret_key or os.environ.get('DJANGO_SECRET_KEY', '')
    
    if not django_secret_key:
        logger.error("DJANGO_SECRET_KEY nicht angegeben und nicht in Umgebungsvariablen gefunden")
        return False
    
    # Endpunkt für API-Key-Updates
    endpoint = f"{crawl4ai_url}/api-keys/update-api-keys"
    
    # Daten für Request
    payload = {
        "provider": provider,
        "user_id": user_id
    }
    
    # Headers mit Authentifizierung
    headers = {
        "Content-Type": "application/json",
        "X-Internal-Auth": django_secret_key[:32]  # Verwende ersten 32 Zeichen
    }
    
    # Request senden
    try:
        logger.info(f"Sende Update-Anfrage für {provider} API-Key (Nutzer {user_id}) an {endpoint}")
        
        response = requests.post(
            endpoint,
            json=payload,
            headers=headers,
            timeout=10  # 10 Sekunden Timeout
        )
        
        if response.status_code == 200:
            logger.info(f"API-Key-Update erfolgreich angefordert: {response.json()}")
            return True
        else:
            logger.error(f"Fehler bei API-Key-Update-Anfrage: HTTP {response.status_code} - {response.text}")
            return False
            
    except requests.RequestException as e:
        logger.error(f"Kommunikationsfehler mit crawl4ai-Service: {str(e)}")
        return False
    except Exception as e:
        logger.exception(f"Unerwarteter Fehler: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test des API-Key-Updater-Endpunkts')
    parser.add_argument('--provider', choices=['groq', 'google_gemini'], required=True, help='Provider (groq oder google_gemini)')
    parser.add_argument('--user-id', type=int, default=2, help='Nutzer-ID (Standard: 2)')
    parser.add_argument('--django-secret-key', help='Django Secret Key für Authentifizierung')
    parser.add_argument('--crawl4ai-url', help='URL des crawl4ai-Services (Standard: http://localhost:11235)')
    
    args = parser.parse_args()
    
    success = test_api_key_updater(
        args.provider, 
        args.user_id, 
        args.django_secret_key, 
        args.crawl4ai_url
    )
    
    sys.exit(0 if success else 1) 