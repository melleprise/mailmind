#!/usr/bin/env python3
"""
API-Key-Provider für crawl4ai.
Ruft API-Keys aus der Django-Datenbank ab und stellt sie für crawl4ai bereit.
"""

import os
import sys
import requests
import json
import logging
import argparse
from pathlib import Path

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('api_key_provider')

def get_api_key_from_backend(provider, user_id=2):
    """
    Ruft einen API-Key vom Backend ab.
    
    Args:
        provider: String mit dem Provider-Namen (z.B. 'google_gemini', 'groq')
        user_id: ID des Nutzers, standardmäßig 2 (korrekte Benutzer-ID für API-Keys)
        
    Returns:
        Der API-Key oder None im Fehlerfall
    """
    backend_url = os.environ.get('BACKEND_API_URL', 'http://backend:8000')
    endpoint = f"{backend_url}/api/v1/core/internal/get-api-key/"
    
    # Django Secret Key für interne Authentifizierung
    django_secret_key = os.environ.get('DJANGO_SECRET_KEY')
    
    # Debug-Ausgabe für Umgebungsvariablen
    logger.info(f"Umgebungsvariablen: BACKEND_API_URL={backend_url}, DJANGO_SECRET_KEY existiert: {bool(django_secret_key)}")
    if django_secret_key:
        logger.info(f"DJANGO_SECRET_KEY Länge: {len(django_secret_key)}, Anfang: {django_secret_key[:5]}...")
    else:
        all_env_vars = ', '.join([f"{k}={v[:5]}..." if isinstance(v, str) and len(v) > 5 else f"{k}={v}" for k, v in os.environ.items()])
        logger.info(f"Alle Umgebungsvariablen: {all_env_vars}")
        logger.error("DJANGO_SECRET_KEY fehlt in den Umgebungsvariablen")
        return None
    
    try:
        response = requests.post(
            endpoint,
            json={
                'provider': provider,
                'user_id': user_id
            },
            headers={
                'Content-Type': 'application/json',
                'X-Internal-Auth': django_secret_key[:32]  # Verwende ersten 32 Zeichen als Auth-Token
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('api_key'):
                logger.info(f"API-Key für Provider {provider} erfolgreich abgerufen")
                return result['api_key']
            else:
                logger.error(f"Kein API-Key in der Antwort: {result}")
                return None
        else:
            logger.error(f"Backend-Anfrage fehlgeschlagen: HTTP {response.status_code} - {response.text}")
            return None
            
    except Exception as e:
        logger.exception(f"Fehler beim Abrufen des API-Keys von Backend: {str(e)}")
        return None

def write_api_key_to_config(config_path, provider, api_key):
    """
    Schreibt einen API-Key in die crawl4ai-Konfigurationsdatei.
    
    Args:
        config_path: Pfad zur crawl4ai-Konfigurationsdatei
        provider: Provider-Name (z.B. 'google_gemini', 'groq')
        api_key: Der zu speichernde API-Key
    """
    config = {}
    
    # Existierende Konfigurationsdatei lesen, falls vorhanden
    if Path(config_path).exists():
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logger.warning(f"Fehler beim Lesen der Konfigurationsdatei: {str(e)}. Erstelle neue Datei.")
            config = {}
    
    # API Key entsprechend dem Provider speichern
    if 'llm' not in config:
        config['llm'] = {}
        
    # Speichere beide API-Keys
    if provider == 'google_gemini':
        # Speichere Google Gemini API-Key
        config['gemini_api_key'] = api_key
    elif provider == 'groq':
        # Speichere Groq API-Key und setze als Standard-Provider
        config['groq_api_key'] = api_key
        config['llm']['provider'] = 'groq/llama3-8b-8192'
        config['llm']['api_key'] = api_key
    
    # Stelle sicher, dass Groq als Standard verwendet wird, wenn verfügbar
    if provider == 'google_gemini' and 'groq_api_key' in config:
        # Wenn wir Gemini aktualisieren, aber Groq schon konfiguriert ist, behalte Groq als Standard
        config['llm']['provider'] = 'groq/llama3-8b-8192'
        config['llm']['api_key'] = config['groq_api_key']
    
    # Konfigurationsdatei speichern
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"API-Key für {provider} in {config_path} gespeichert")
        return True
    except Exception as e:
        logger.exception(f"Fehler beim Schreiben der Konfigurationsdatei: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='API-Key-Provider für crawl4ai')
    parser.add_argument('--config', default='/app/config.json', help='Pfad zur crawl4ai-Konfigurationsdatei')
    parser.add_argument('--user-id', type=int, default=2, help='Nutzer-ID (Standard: 2)')
    parser.add_argument('--provider', default='both', choices=['groq', 'google_gemini', 'both'], 
                        help='Provider (groq, google_gemini, oder both für beide)')
    
    args = parser.parse_args()
    
    providers = ['groq', 'google_gemini'] if args.provider == 'both' else [args.provider]
    success = False
    
    for provider in providers:
        api_key = get_api_key_from_backend(provider, args.user_id)
        if api_key:
            if write_api_key_to_config(args.config, provider, api_key):
                success = True
    
    if not success:
        logger.error("Keine API-Keys konnten abgerufen oder gespeichert werden")
        sys.exit(1)
    
    logger.info("API-Key-Provider erfolgreich ausgeführt")
    sys.exit(0)

if __name__ == "__main__":
    main() 