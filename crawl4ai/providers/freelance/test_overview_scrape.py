#!/usr/bin/env python3
"""
Testskript zum Scrapen der Freelance Projektübersichtsseite.
Diese Seite ist ohne Login zugänglich.
"""
import os
import sys
import json
import asyncio
import logging
import re
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Pfad zum providers-Verzeichnis hinzufügen
current_dir = os.path.dirname(os.path.abspath(__file__))
providers_dir = os.path.dirname(current_dir)
if providers_dir not in sys.path:
    sys.path.insert(0, providers_dir)

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import aus dem freelance-Verzeichnis für die vorhandenen Funktionen
from freelance.fetch_and_process import BASE_URL, fetch_protected_page_via_playwright

async def extract_project_from_card(project_card: BeautifulSoup) -> Optional[Dict[str, Any]]:
    """Extrahiert ein Projekt aus einer Projektkarte der Übersichtsseite"""
    try:
        # Link und ID extrahieren
        link_elem = project_card.select_one('a')
        if not link_elem or not link_elem.get('href'):
            return None
            
        project_url = urljoin(BASE_URL, link_elem.get('href'))
        project_id_match = re.search(r'projekt-(\d+)', project_url)
        if not project_id_match:
            return None
            
        project_id = project_id_match.group(1)
        
        # Titel extrahieren
        title_elem = project_card.select_one('h3')
        title = title_elem.text.strip() if title_elem else "Unbekannter Titel"
        
        # Firma extrahieren
        company_elem = project_card.select_one('small span')
        company = company_elem.text.strip() if company_elem else "Unbekannte Firma"
        
        # Skills extrahieren
        skills = []
        skill_elems = project_card.select('a.badge')
        for skill_elem in skill_elems:
            skill_text = skill_elem.text.strip()
            if skill_text:
                skills.append(skill_text)
        
        # Standort extrahieren
        location_elem = project_card.select_one('i.fa-map-marker-alt')
        location = ""
        if location_elem and location_elem.parent:
            location_text = location_elem.parent.text.strip()
            location = location_text.replace('Ort:', '').strip()
        
        # Remote-Status prüfen
        remote_elem = project_card.select_one('i.fa-laptop-house')
        remote = bool(remote_elem)
        
        # Projektstart extrahieren
        start_date_elem = project_card.select_one('i.fa-calendar-star')
        start_date = ""
        if start_date_elem and start_date_elem.parent:
            start_date = start_date_elem.parent.text.strip()
        
        # Letztes Update extrahieren
        update_elem = project_card.select_one('i.fa-history')
        last_updated = ""
        if update_elem and update_elem.parent:
            last_updated = update_elem.parent.text.strip()
        
        # Bewerbungen extrahieren
        applications = 0
        applications_elem = project_card.select_one('a.small.fw-semibold.link-warning')
        if applications_elem:
            applications_text = applications_elem.text.strip()
            if "Jetzt als Erstes bewerben" in applications_text:
                applications = 0
            elif "Zu den ersten Bewerbern" in applications_text:
                applications = 1
            else:
                applications_match = re.search(r'(\d+)', applications_text)
                if applications_match:
                    applications = int(applications_match.group(1))
        
        return {
            'project_id': project_id,
            'title': title,
            'company': company,
            'location': location,
            'remote': remote,
            'start_date': start_date,
            'last_updated': last_updated,
            'skills': skills,
            'url': project_url,
            'applications': applications,
            'provider': 'freelance.de'
        }
    except Exception as e:
        logger.error(f"Fehler beim Extrahieren der Projektkarte: {e}")
        return None

async def scrape_overview_page() -> List[Dict[str, Any]]:
    """Scrapt die Projektübersichtsseite von Freelance.de"""
    url = "https://www.freelance.de/projekte?remotePreference=remote_remote--remote&pageSize=100"
    logger.info(f"Lade Übersichtsseite: {url}")
    
    html_content = await fetch_protected_page_via_playwright(url)
    if not html_content:
        logger.error("Fehler beim Laden der Übersichtsseite.")
        return []
    
    logger.info(f"Übersichtsseite geladen: {len(html_content)} Bytes")
    
    # HTML für Debugging speichern
    debug_file = "/tmp/freelance_overview.html"
    with open(debug_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    logger.info(f"HTML gespeichert in: {debug_file}")
    
    # Parsen der HTML-Seite
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Prüfen, ob wir auf der richtigen Seite sind
    title = soup.title.text if soup.title else "Kein Titel gefunden"
    logger.info(f"Seitentitel: {title}")
    
    # Projektcards finden
    project_cards = soup.select('search-project-card')
    if not project_cards:
        # Alternative Suche nach Projektkarten
        project_cards = soup.select('.card.rounded.w-100')
    
    logger.info(f"Gefundene Projektkarten: {len(project_cards)}")
    
    projects = []
    for card in project_cards[:5]:  # Begrenzen auf 5 Projekte zum Testen
        project = await extract_project_from_card(card)
        if project:
            projects.append(project)
            logger.info(f"Projekt extrahiert: {project['title']} (ID: {project['project_id']})")
    
    return projects

async def main():
    """Hauptfunktion"""
    projects = await scrape_overview_page()
    
    if projects:
        # Speichern der Ergebnisse in JSON-Datei
        output_file = "freelance_projects_overview.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(projects, f, indent=2, ensure_ascii=False)
        logger.info(f"{len(projects)} Projekte wurden in {output_file} gespeichert.")
        
        return True
    return False

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Test durch Benutzer abgebrochen.")
    except Exception as e:
        logger.exception(f"Fehler bei der Ausführung: {e}") 