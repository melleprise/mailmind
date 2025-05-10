#!/usr/bin/env python3
"""
Debug-Skript zum Testen der Extraktion von Freelance-Projektdetails.
Zeigt zusätzliche Debugging-Informationen zur HTML-Struktur an.
"""
import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

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

async def debug_html_structure(html_content: str) -> None:
    """Analysiert die HTML-Struktur und gibt Debug-Informationen aus"""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Prüfe, ob wir auf der richtigen Seite sind
    title = soup.title.text if soup.title else "Kein Titel gefunden"
    logger.info(f"Seitentitel: {title}")
    
    # Prüfe, ob Zugriff verweigert wurde
    if "Zugriff verweigert" in html_content or "Access Denied" in html_content:
        logger.error("Die Seite enthält eine Zugriffsverweigerung. Authentifizierung erforderlich.")
        
    # Prüfe, ob wir zur Login-Seite umgeleitet wurden
    if "login" in title.lower() or "anmelden" in title.lower():
        logger.error("Wir wurden zur Login-Seite umgeleitet.")
    
    # Prüfe wichtige Elemente für die Detailseite
    project_title = soup.select_one('h1.h2') or soup.select_one('h2.title')
    if project_title:
        logger.info(f"Projekt-Titel: {project_title.text.strip()}")
    else:
        logger.error("Kein Projekt-Titel gefunden. Möglicherweise sind wir nicht auf der Detailseite.")
    
    # Prüfe Übersichtsinformationen
    overview = soup.select('.overview li')
    logger.info(f"Anzahl der Übersichtselemente: {len(overview)}")
    for item in overview[:5]:  # Zeige nur die ersten 5 Elemente an
        logger.info(f"  Übersichtselement: {item.text.strip()}")
    
    # Prüfe Beschreibungspanel
    description_panel = soup.select_one('.panel-heading h2[title^="Projektbeschreibung"]')
    if description_panel:
        logger.info("Beschreibungspanel gefunden.")
    else:
        logger.error("Kein Beschreibungspanel gefunden.")
        
        # Alternative Beschreibungssuche
        alt_desc = soup.select_one('.panel-body.highlight-text')
        if alt_desc:
            logger.info(f"Alternative Beschreibung gefunden: {alt_desc.text[:100]}...")
        else:
            logger.error("Keine alternative Beschreibung gefunden.")
    
    # Zeige alle Panel-Überschriften an
    panel_headings = soup.select('.panel-heading h2, .panel-heading h3')
    logger.info(f"Anzahl der Panel-Überschriften: {len(panel_headings)}")
    for heading in panel_headings:
        logger.info(f"  Panel-Überschrift: {heading.text.strip()}")
    
    # Zeige HTML-Struktur der wichtigsten Container an
    main_container = soup.select_one('main') or soup.select_one('.container') or soup.select_one('body')
    if main_container:
        logger.info("Hauptcontainer-Struktur:")
        for child in main_container.find_all(recursive=False):
            if child.name:
                logger.info(f"  {child.name}: {child.get('class', [''])[0] if child.get('class') else 'keine Klasse'}")
    
    return None

async def test_detail_scrape_debug() -> Optional[Dict[str, Any]]:
    """
    Testet das Scrapen einer aktuellen Projektdetailseite mit zusätzlichem Debugging.
    
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
    
    # HTML-Struktur analysieren
    await debug_html_structure(html_content)
    
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
    details = await test_detail_scrape_debug()
    
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