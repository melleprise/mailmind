#!/usr/bin/env python3
"""
Integration für die Einbindung des API-Key-Updaters in die crawl4ai-Anwendung.
Diese Datei wird beim Start der crawl4ai-App geladen, um den API-Key-Updater zu registrieren.
"""

import os
import sys
import logging
from pathlib import Path

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('crawl4ai_integration')

def register_api_key_updater(app):
    """
    Registriert den API-Key-Updater in der FastAPI-App.
    
    Args:
        app: Die FastAPI-Anwendung
    """
    try:
        # Importiere den API-Key-Updater
        current_dir = os.path.dirname(os.path.abspath(__file__))
        if current_dir not in sys.path:
            sys.path.append(current_dir)
            
        from api_key_updater import setup_routes
        
        # Registriere die Routen
        setup_routes(app)
        
        logger.info("API-Key-Updater wurde erfolgreich registriert")
        
        # Prüfe, ob die Konfigurationsdatei existiert
        config_path = "/app/config.json"
        if not os.path.exists(config_path):
            logger.warning(f"Konfigurationsdatei {config_path} nicht gefunden. API-Keys können nicht aktualisiert werden")
            
    except ImportError as e:
        logger.error(f"Fehler beim Importieren des API-Key-Updaters: {str(e)}")
    except Exception as e:
        logger.exception(f"Unerwarteter Fehler bei der Registrierung des API-Key-Updaters: {str(e)}")

# Wird automatisch beim Import der Datei aufgerufen
def plugin_init(app):
    """
    Hook-Funktion, die von crawl4ai beim Start aufgerufen wird.
    """
    logger.info("Initialisiere MailMind-Integration für crawl4ai")
    register_api_key_updater(app)
    return True 