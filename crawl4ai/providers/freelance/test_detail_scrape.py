#!/usr/bin/env python3
"""
Einfaches Testskript zum Scrapen einer aktuellen Freelance-Projektdetailseite.
Testet das Scrapen der Detailseite für das Projekt 'INTERIM GIS-Applikationsbetreuer'.
"""
import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional

# Pfad zum providers-Verzeichnis hinzufügen
current_dir = os.path.dirname(os.path.abspath(__file__))
providers_dir = os.path.dirname(current_dir)
if providers_dir not in sys.path:
    sys.path.insert(0, providers_dir)

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import aus dem freelance-Verzeichnis für die vorhandenen Funktionen
from freelance.fetch_and_process import fetch_page_with_cookies
from freelance.fetch_project_details import ProjectDetailExtractor, fetch_project_details_page

async def test_detail_scrape() -> Optional[Dict[str, Any]]:
    """
    Testet das Scrapen einer aktuellen Projektdetailseite.
    
    Returns:
        Die extrahierten Projektdetails oder None im Fehlerfall.
    """
    # Aktuelle Projekt-ID und URL
    project_id = "1207966"
    url = f"https://www.freelance.de/projekte/projekt-{project_id}-INTERIM-GIS-Applikationsbetreuer-m-w-d-gesucht"
    
    logger.info(f"Teste Detail-Scrape für Projekt-ID: {project_id}, URL: {url}")
    
    # Detailseite laden
    html_content = await fetch_project_details_page(project_id, url)
    
    if not html_content:
        logger.error("Fehler beim Laden der Detailseite.")
        return None
    
    logger.info(f"Detailseite geladen: {len(html_content)} Bytes")
    
    # HTML für Debugging speichern
    debug_file = f"/tmp/freelance_detail_{project_id}.html"
    with open(debug_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info(f"HTML gespeichert in: {debug_file}")
    
    # Extractor initialisieren und Daten extrahieren
    extractor = ProjectDetailExtractor(html_content, project_id)
    details = extractor.extract_all_details()
    
    # Ergebnisse anzeigen
    logger.info("Extrahierte Details:")
    
    # Formatierte Ausgabe der Details im Log
    for key, value in details.items():
        if key in ["categories", "related_projects"] and value:
            try:
                logger.info(f"{key}: {json.dumps(value, indent=2, ensure_ascii=False)}")
            except:
                logger.info(f"{key}: [Komplexes Objekt]")
        else:
            logger.info(f"{key}: {value}")
    
    return details

async def main():
    """Hauptfunktion"""
    details = await test_detail_scrape()
    
    if details:
        # Speichern der Ergebnisse in JSON-Datei
        output_file = f"project_details_{details['project_id']}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(details, f, indent=2, ensure_ascii=False)
        logger.info(f"Details wurden in {output_file} gespeichert.")
        
        return True
    return False

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test durch Benutzer abgebrochen.")
    except Exception as e:
        logger.exception(f"Fehler bei der Ausführung: {e}") 