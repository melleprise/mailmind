#!/usr/bin/env python3
"""
Multi-Page-Crawler für Freelance.de Projekte
Crawlt alle verfügbaren Seiten und speichert sie in der Datenbank
"""
import os
import sys
import json
import asyncio
import argparse
import logging
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
import httpx
from bs4 import BeautifulSoup
import asyncpg
from typing import List, Dict, Any, Optional
import re

# Konfiguration
BASE_URL = "https://www.freelance.de"
PROJECTS_URL = f"{BASE_URL}/projekte?remotePreference=remote_remote--remote"
PAGE_SIZE = 100
COOKIE_PATH = os.path.join(os.path.dirname(__file__), 'freelance_cookies.json')

# Datenbank-Konfiguration
DB_USER = os.environ.get("DB_USER", "mailmind")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "mailmind")
DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "mailmind")
DB_TABLE = "freelance_projects"

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pfad zum providers-Verzeichnis hinzufügen
current_dir = os.path.dirname(os.path.abspath(__file__))
providers_dir = os.path.dirname(current_dir)
if providers_dir not in sys.path:
    sys.path.insert(0, providers_dir)

# Import aus dem freelance-Verzeichnis für die vorhandenen Funktionen
from freelance.fetch_and_process import (
    check_cookies, get_cookie_from_playwright_login, 
    extract_project_data, FreelanceProject
)

async def fetch_page(url: str) -> Optional[str]:
    """Fetch einer Seite mit den Cookies"""
    try:
        if not await check_cookies():
            if not await get_cookie_from_playwright_login():
                logger.error("Konnte keine Cookies erhalten.")
                return None
        
        # Cookies laden
        with open(COOKIE_PATH) as f:
            cookie_data = json.load(f)
        
        # Cookie-Header bauen
        cookies = {}
        for cookie in cookie_data:
            cookies[cookie['name']] = cookie['value']
        
        # HTTP-Request mit Cookies ausführen
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            logger.info(f"Sende Anfrage an {url}")
            response = await client.get(url, cookies=cookies, headers=headers)
            
            if response.status_code == 200:
                logger.info(f"Seite {url} erfolgreich geladen. Content-Length: {len(response.text)}")
                return response.text
            else:
                logger.error(f"Fehler beim Laden der Seite {url}: {response.status_code}")
                return None
    except Exception as e:
        logger.error(f"Fehler beim Laden der Seite {url}: {e}")
        return None

def build_page_url(page: int) -> str:
    """Baut die URL für eine bestimmte Seite"""
    # Prüfen, ob die Basis-URL bereits Parameter enthält
    if "?" in PROJECTS_URL:
        # URL enthält bereits Parameter, weitere mit & anhängen
        separator = "&"
    else:
        # URL enthält noch keine Parameter
        separator = "?"
    
    return f"{PROJECTS_URL}{separator}page={page}&pageSize={PAGE_SIZE}"

async def extract_projects_from_page(html_content: str) -> List[Dict[str, Any]]:
    """Extrahiert alle Projekte von einer HTML-Seite"""
    return extract_project_data(html_content)

async def get_total_pages(html_content: str) -> int:
    """Extrahiert die Gesamtanzahl der Seiten aus dem HTML"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Suche nach dem Remote-Filter-Text
        remote_filter_text = None
        filter_elements = soup.select('.filter-item-list .filter-item')
        for filter_elem in filter_elements:
            text = filter_elem.get_text(strip=True)
            if "Remote" in text:
                remote_filter_text = text
                break
        
        # Versuche, die Anzahl der Remote-Projekte zu extrahieren
        if remote_filter_text:
            count_match = re.search(r'\((\d+(?:,\d+)*)\)', remote_filter_text)
            if count_match:
                count_text = count_match.group(1).replace(',', '')
                total_projects = int(count_text)
                total_pages = (total_projects + PAGE_SIZE - 1) // PAGE_SIZE  # Aufrunden
                logger.info(f"Insgesamt {total_projects} Remote-Projekte gefunden, das ergibt {total_pages} Seiten.")
                return total_pages
        
        # Fallback: Suche nach den Pagination-Links
        pagination = soup.select('.pagination .pagination-item a')
        if pagination:
            page_numbers = []
            for page_link in pagination:
                try:
                    page_text = page_link.get_text(strip=True)
                    if page_text.isdigit():
                        page_numbers.append(int(page_text))
                except (ValueError, TypeError):
                    continue
            
            if page_numbers:
                max_page = max(page_numbers)
                logger.info(f"Insgesamt {max_page} Seiten gefunden über Pagination-Links.")
                return max_page
        
        # Zweiter Fallback: Suche nach total in JSON
        pattern = r'"pagination":.*?"pagesCount":(\d+)'
        match = re.search(pattern, html_content)
        if match:
            total_pages = int(match.group(1))
            logger.info(f"Insgesamt {total_pages} Seiten gefunden über JSON-Daten.")
            return total_pages
        
        # Wenn nichts gefunden wurde, gehe von einer Seite aus
        logger.warning("Konnte die Gesamtanzahl der Seiten nicht ermitteln, nehme 1 an.")
        return 1
    except Exception as e:
        logger.error(f"Fehler beim Ermitteln der Gesamtseitenzahl: {e}")
        return 1

async def get_db_connection():
    """Stellt eine Verbindung zur Datenbank her"""
    try:
        conn = await asyncpg.connect(
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME
        )
        logger.info("DB-Verbindung hergestellt.")
        return conn
    except Exception as e:
        logger.error(f"Fehler bei DB-Verbindung: {e}")
        return None

async def create_table_if_not_exists(conn):
    """Erstellt die Projekttabelle, falls sie nicht existiert"""
    try:
        await conn.execute('''
        CREATE TABLE IF NOT EXISTS freelance_projects (
            id SERIAL PRIMARY KEY,
            project_id TEXT NOT NULL,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            end_date TEXT,
            location TEXT,
            remote BOOLEAN DEFAULT FALSE,
            last_updated TEXT,
            skills JSONB DEFAULT '[]'::jsonb,
            url TEXT NOT NULL,
            applications INTEGER,
            description TEXT DEFAULT '',
            provider TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(project_id, provider)
        )
        ''')
        logger.info(f"Tabelle {DB_TABLE} überprüft/erstellt.")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Tabelle: {e}")
        return False

async def insert_or_update_projects(conn, projects: List[Dict[str, Any]]):
    """Fügt Projekte in die Datenbank ein oder aktualisiert sie"""
    if not projects:
        logger.info("Keine Projekte zum Speichern.")
        return 0, 0
    
    inserted = 0
    updated = 0
    
    try:
        async with conn.transaction():
            for project in projects:
                project_id = project['project_id']
                provider = project['provider']
                
                # Prüfen, ob das Projekt bereits existiert
                exists = await conn.fetchval(f'''
                SELECT COUNT(*) FROM {DB_TABLE} 
                WHERE project_id = $1 AND provider = $2
                ''', project_id, provider)
                
                if exists:
                    # Projekt aktualisieren
                    # Konvertiere Python-Liste zu JSON
                    skills_json = json.dumps(project.get('skills', []))
                    
                    await conn.execute(f'''
                    UPDATE {DB_TABLE} SET 
                        title = $3, 
                        company = $4, 
                        end_date = $5, 
                        location = $6, 
                        remote = $7, 
                        last_updated = $8, 
                        skills = $9,
                        url = $10,
                        applications = $11,
                        description = $12
                    WHERE project_id = $1 AND provider = $2
                    ''', project_id, provider, project['title'], project['company'], 
                    project.get('end_date', ''), project.get('location', ''), 
                    project.get('remote', False), project.get('last_updated', ''),
                    skills_json, project.get('url', ''), project.get('applications', 0),
                    project.get('description', ''))
                    
                    updated += 1
                else:
                    # Neues Projekt einfügen
                    # Konvertiere Python-Liste zu JSON
                    skills_json = json.dumps(project.get('skills', []))
                    
                    await conn.execute(f'''
                    INSERT INTO {DB_TABLE} 
                    (project_id, provider, title, company, end_date, location, remote, last_updated, skills, url, applications, description) 
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ''', project_id, provider, project['title'], project['company'], 
                    project.get('end_date', ''), project.get('location', ''), 
                    project.get('remote', False), project.get('last_updated', ''),
                    skills_json, project.get('url', ''), project.get('applications', 0),
                    project.get('description', ''))
                    
                    inserted += 1
        
        logger.info(f"{inserted} Projekte eingefügt, {updated} Projekte aktualisiert.")
        return inserted, updated
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Projekte in der Datenbank: {e}")
        return 0, 0

async def process_page(html_content: str, page_number: int) -> List[Dict[str, Any]]:
    """Verarbeitet eine einzelne Seite mit Projekten"""
    logger.info(f"Verarbeite Seite {page_number}...")
    
    # Projekte extrahieren
    projects = await extract_projects_from_page(html_content)
    
    logger.info(f"{len(projects)} Projekte auf Seite {page_number} gefunden.")
    return projects

async def crawl_all_pages():
    """Crawlt alle Seiten von Freelance.de"""
    logger.info("Starte Crawling aller Remote-Projektseiten...")
    
    # Erste Seite laden, um die Gesamtanzahl der Seiten zu ermitteln
    html_content = await fetch_page(build_page_url(1))
    if not html_content:
        logger.error("Konnte die erste Seite nicht laden.")
        return False
    
    # Gesamtanzahl der Seiten ermitteln
    total_pages = await get_total_pages(html_content)
    max_pages = min(args.max_pages, total_pages) if args.max_pages > 0 else total_pages
    
    logger.info(f"Crawle maximal {max_pages} von {total_pages} Seiten...")
    
    # DB-Verbindung herstellen
    conn = await get_db_connection()
    if not conn:
        logger.error("Konnte keine Datenbankverbindung herstellen.")
        return False
    
    # Tabelle erstellen, falls sie nicht existiert
    await create_table_if_not_exists(conn)
    
    # Erste Seite verarbeiten
    projects = await process_page(html_content, 1)
    inserted, updated = await insert_or_update_projects(conn, projects)
    total_projects = len(projects)
    
    # Verbleibende Seiten crawlen
    for page in range(2, max_pages + 1):
        page_url = build_page_url(page)
        page_projects = await crawl_page(page_url, page)
        if page_projects:
            page_inserted, page_updated = await insert_or_update_projects(conn, page_projects)
            inserted += page_inserted
            updated += page_updated
            total_projects += len(page_projects)
    
    # Verbindung schließen
    await conn.close()
    
    logger.info(f"Crawling abgeschlossen. Insgesamt {total_projects} Projekte gefunden.")
    logger.info(f"Insgesamt {inserted} Projekte eingefügt, {updated} Projekte aktualisiert.")
    
    return True

async def crawl_page(page_url: str, page_number: int) -> List[Dict[str, Any]]:
    """Crawlt eine einzelne Seite"""
    html_content = await fetch_page(page_url)
    if not html_content:
        logger.error(f"Konnte Seite {page_number} nicht laden.")
        return []
    
    return await process_page(html_content, page_number)

async def process_projects_in_db(projects: List[Dict[str, Any]]) -> bool:
    """Speichert die Projekte in der Datenbank"""
    if not projects:
        logger.info("Keine Projekte zum Speichern vorhanden")
        return True
    
    try:
        # Verbindung zur Datenbank herstellen
        conn = await get_db_connection()
        if not conn:
            return False
        
        # Tabelle erstellen, falls sie nicht existiert
        await create_table_if_not_exists(conn)
        
        # Projekte in die Datenbank einfügen
        inserted, updated = await insert_or_update_projects(conn, projects)
        
        # Verbindung schließen
        await conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Projekte in der Datenbank: {e}")
        return False

if __name__ == "__main__":
    # Kommandozeilenargumente parsen
    parser = argparse.ArgumentParser(description='Crawlt alle Remote-Projektseiten von Freelance.de')
    parser.add_argument('--max-pages', type=int, default=0, help='Maximale Anzahl zu crawlender Seiten (0 = alle)')
    args = parser.parse_args()
    
    # Asynchrone Hauptfunktion ausführen
    asyncio.run(crawl_all_pages()) 