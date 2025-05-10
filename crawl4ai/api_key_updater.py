#!/usr/bin/env python3
"""
API-Key-Updater für crawl4ai.
Stellt einen Endpunkt bereit, um API-Keys zur Laufzeit zu aktualisieren.
"""

# import sys # sys.path Manipulation wird entfernt
# from pathlib import Path # sys.path Manipulation wird entfernt

# Füge das Verzeichnis dieser Datei (und damit das 'providers'-Unterverzeichnis) zum sys.path hinzu
# Damit 'from providers...' funktioniert.
# CURRENT_DIR = Path(__file__).resolve().parent # Entfernt
# if str(CURRENT_DIR) not in sys.path: # Entfernt
#     sys.path.insert(0, str(CURRENT_DIR)) # Entfernt

import os
import json
import logging
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks, Query, Header
from pydantic import BaseModel
from typing import Optional
# Geändert zu relativem Import, da api_key_updater.py Teil des crawl4ai Pakets ist
from .providers.freelance.fetch_and_process import crawl_until_existing 
import asyncio

# Api-Key-Provider importieren - dieser Import muss ggf. auch angepasst werden, falls api_key_provider.py außerhalb liegt
# Annahme: api_key_provider.py ist im selben Verzeichnis oder korrekt im PYTHONPATH
from .api_key_provider import get_api_key_from_backend, write_api_key_to_config

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('api_key_updater')

# APIRouter erstellen (ersetzt die frühere FastAPI-Instanz)
router = APIRouter(
    # Ein Prefix kann hier oder beim Inkludieren in der Haupt-App gesetzt werden.
    # prefix="/service", # Beispiel, falls alle Routen hier ein gemeinsames Präfix haben sollen
    tags=["custom_services"] # Tags für die OpenAPI-Doku
)

# Auth-Funktion für DJANGO_SECRET_KEY
async def verify_auth_token(request: Request):
    django_secret_key = os.environ.get('DJANGO_SECRET_KEY')
    if not django_secret_key:
        raise HTTPException(status_code=500, detail="DJANGO_SECRET_KEY nicht konfiguriert")
    
    auth_token = request.headers.get('X-Internal-Auth')
    if not auth_token or auth_token != django_secret_key[:32]: # Vergleiche mit einem Teil des Keys
        logger.warning(f"Nicht autorisierter Zugriff versucht mit Token: {auth_token}")
        raise HTTPException(status_code=401, detail="Nicht autorisiert")
    return True

# Request-Modell
class UpdateRequest(BaseModel):
    provider: str
    user_id: Optional[int] = 2

# Hintergrundaufgabe zum Aktualisieren der API-Keys
def update_api_keys(provider: str, user_id: int = 2):
    config_path = "/app/config.json" # Pfad im Container
    logger.info(f"Aktualisiere API-Keys für Provider {provider}, User-ID {user_id}")
    
    api_key = get_api_key_from_backend(provider, user_id)
    if api_key:
        if write_api_key_to_config(config_path, provider, api_key):
            logger.info(f"API-Key für {provider} erfolgreich aktualisiert")
            return True
    
    logger.error(f"Fehler beim Aktualisieren des API-Keys für {provider}")
    return False

# Endpunkt zum Aktualisieren von API-Keys
@router.post("/update-api-keys")
async def update_keys(
    request_data: UpdateRequest, # Name geändert, um Verwechslung mit 'request: Request' zu vermeiden
    background_tasks: BackgroundTasks,
    _: bool = Depends(verify_auth_token)
):
    background_tasks.add_task(update_api_keys, request_data.provider, request_data.user_id)
    return {"message": f"API-Key-Update für {request_data.provider} wurde gestartet"}

@router.post("/crawl-freelance-sync")
async def crawl_freelance_sync(
    background_tasks: BackgroundTasks, 
    x_user_id: int = Header(..., alias="X-User-Id") # ... bedeutet, dass der Header erforderlich ist
):
    """Startet den Freelance-Crawl-Prozess asynchron (für Sync-Button)."""
    # Die Authentifizierung wird hier nicht mehr durch Depends(verify_auth_token) gehandhabt,
    # da der X-Internal-Auth Header vom Frontend nicht gesendet wird.
    # Der User wird über X-User-Id identifiziert.
    logger.info(f"Aufruf von /crawl-freelance-sync für User-ID: {x_user_id}")

    def run_crawl_task(): # Innere Funktion umbenannt, um Konflikte zu vermeiden
        try:
            logger.info(f"Starte Freelance-Crawl für User-ID: {x_user_id} im Hintergrund.")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            # max_pages und page_size können hier bei Bedarf angepasst/konfigurierbar gemacht werden
            loop.run_until_complete(crawl_until_existing(user_id=x_user_id, max_pages=10, page_size=100, fetch_descriptions=True))
            logger.info(f"Freelance-Crawl für User-ID: {x_user_id} abgeschlossen.")
        except Exception as e:
            logger.error(f"Fehler beim Freelance-Crawl für User-ID {x_user_id}: {e}", exc_info=True)
    
    background_tasks.add_task(run_crawl_task)
    return {"status": "started", "detail": f"Freelance-Crawl für User-ID {x_user_id} wurde gestartet."}

# Die setup_routes Funktion wird nicht mehr benötigt, da der Router direkt importiert wird. 