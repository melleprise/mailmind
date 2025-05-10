#!/usr/bin/env python3
"""
Skript zum Crawlen aller Freelance.de-Projekte von der Übersichtsseite.
Da der Zugriff auf Detailseiten Authentifizierungsprobleme hat, extrahiert
dieses Skript alle verfügbaren Informationen direkt von den Übersichtsseiten.
"""
import os
import sys
import json
import asyncio
import logging
import re
import time
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import asyncpg

# Pfad zum providers-Verzeichnis hinzufügen
current_dir = os.path.dirname(os.path.abspath(__file__))
providers_dir = os.path.dirname(current_dir)
if providers_dir not in sys.path:
    sys.path.insert(0, providers_dir)

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Import aus dem freelance-Verzeichnis für die vorhandenen Funktionen
from freelance.fetch_and_process import BASE_URL, fetch_page_with_cookies

# Datenbank-Konfiguration
DB_USER = os.environ.get("DB_USER", "mailmind")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "mailmind")
DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "mailmind")
DB_SCHEMA = "public"
DB_TABLE = "freelance_projects"
PROVIDER = "freelance.de"

async def fetch_project_description(project_url: str) -> str:
    """Scrape die Projektbeschreibung von der Detailseite"""
    try:
        logger.info(f"Lade Projektdetails: {project_url}")
        html_content = await fetch_page_with_cookies(project_url)
        
        if not html_content:
            logger.error(f"Fehler beim Laden der Projektdetails: {project_url}")
            return ""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Suche nach dem Beschreibungsbereich (kann je nach Seitenstruktur angepasst werden)
        description_elem = soup.select_one('.project-description') or soup.select_one('.project-details')
        
        if description_elem:
            # Extrahiere den Text und entferne überflüssige Whitespaces
            description = description_elem.get_text(strip=True)
            # Formatierung verbessern
            description = re.sub(r'\s+', ' ', description).strip()
            return description
        
        return ""
    except Exception as e:
        logger.error(f"Fehler beim Extrahieren der Projektbeschreibung: {e}")
        return ""

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
            if isinstance(location_elem.parent, BeautifulSoup) and location_elem.parent.name == 'li':
                location = location_elem.parent.get_text(strip=True)
            else:
                location = location_text
            
            # Formatierung bereinigen
            location = location.replace('Ort:', '').strip()
        
        # Remote-Status prüfen
        remote_elem = project_card.select_one('i.fa-laptop-house')
        remote = bool(remote_elem)
        
        # Projektdaten extrahieren
        start_date = ""
        end_date = ""
        
        start_date_elem = project_card.select_one('i.fa-calendar-star')
        if start_date_elem and start_date_elem.parent:
            start_date = start_date_elem.parent.text.strip()
        
        # Versuche, end_date zu extrahieren (falls vorhanden)
        end_date_elem = project_card.select_one('i.fa-calendar-times')
        if end_date_elem and end_date_elem.parent:
            end_date = end_date_elem.parent.text.strip()
        
        # Letztes Update extrahieren
        last_updated = ""
        update_elem = project_card.select_one('i.fa-history')
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
        
        # Logo URL extrahieren
        logo_url = ""
        logo_elem = project_card.select_one('img')
        if logo_elem and logo_elem.has_attr('src'):
            logo_url = urljoin(BASE_URL, logo_elem['src'])
        
        # Stundensatz extrahieren (falls vorhanden)
        hourly_rate = ""
        rate_elem = project_card.select_one('i.fa-coins')
        if rate_elem and rate_elem.parent:
            hourly_rate = rate_elem.parent.text.strip()
        
        return {
            'project_id': project_id,
            'title': title,
            'company': company,
            'location': location,
            'remote': remote,
            'start_date': start_date,
            'end_date': end_date,
            'last_updated': last_updated,
            'skills': skills,
            'url': project_url,
            'applications': applications,
            'provider': PROVIDER,
            'logo_url': logo_url,
            'hourly_rate': hourly_rate,
            'description': "",  # Wird später von der Detailseite ergänzt
            'created_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        logger.error(f"Fehler beim Extrahieren der Projektkarte: {e}")
        return None

async def get_pagination_info(html_content: str) -> Dict[str, Any]:
    """Extrahiert Informationen über die Paginierung"""
    soup = BeautifulSoup(html_content, 'html.parser')
    pagination_info = {
        "current_page": 1,
        "total_pages": 1,
        "has_next_page": False,
        "next_page": None,
        "total_projects": 0
    }
    
    # Anzahl der Projekte aus dem Titel extrahieren
    title_elem = soup.select_one('h2.fs-4 span')
    if title_elem and title_elem.next_sibling:
        total_projects_match = re.search(r'\((\d+)\)', title_elem.next_sibling.text)
        if total_projects_match:
            pagination_info["total_projects"] = int(total_projects_match.group(1))
    
    # Pagination Elements finden
    pagination = soup.select('.pagination')
    if pagination:
        # Aktuelle Seite finden
        active_page = soup.select_one('.page-item.active')
        if active_page:
            page_link = active_page.select_one('a')
            if page_link and page_link.text.strip().isdigit():
                pagination_info["current_page"] = int(page_link.text.strip())
        
        # Letzte Seite finden
        last_page = 1
        page_items = soup.select('.page-item a')
        for item in page_items:
            if item.text.strip().isdigit():
                page_num = int(item.text.strip())
                if page_num > last_page:
                    last_page = page_num
        
        pagination_info["total_pages"] = last_page
        pagination_info["has_next_page"] = pagination_info["current_page"] < pagination_info["total_pages"]
        
        if pagination_info["has_next_page"]:
            pagination_info["next_page"] = pagination_info["current_page"] + 1
    
    return pagination_info

async def build_pagination_url(base_url: str, page: int, page_size: int = 100, remote: bool = True) -> str:
    """Baut eine URL für eine bestimmte Seite der Paginierung"""
    url = f"{base_url}?pageSize={page_size}&page={page}"
    
    if remote:
        url += "&remotePreference=remote_remote--remote"
    
    return url

async def scrape_projects_page(url: str) -> List[Dict[str, Any]]:
    """Scrapt eine Projektübersichtsseite von Freelance.de"""
    logger.info(f"Lade Übersichtsseite: {url}")
    
    html_content = await fetch_page_with_cookies(url)
    if not html_content:
        logger.error("Fehler beim Laden der Übersichtsseite.")
        return []
    
    logger.info(f"Übersichtsseite geladen: {len(html_content)} Bytes")
    
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
    
    # Paginierungs-Informationen holen
    pagination = await get_pagination_info(html_content)
    logger.info(f"Pagination: Seite {pagination['current_page']} von {pagination['total_pages']}, insgesamt {pagination['total_projects']} Projekte")
    
    projects = []
    for card in project_cards:
        project = await extract_project_from_card(card)
        if project:
            projects.append(project)
    
    logger.info(f"{len(projects)} Projekte von der Seite extrahiert")
    return projects, pagination

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
        await conn.execute(f'''
            CREATE TABLE IF NOT EXISTS {DB_SCHEMA}.{DB_TABLE} (
                id SERIAL PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                company TEXT NOT NULL,
                location TEXT,
                remote BOOLEAN DEFAULT FALSE,
                end_date TEXT,
                last_updated TEXT,
                skills JSONB DEFAULT '[]',
                url TEXT NOT NULL,
                applications INTEGER,
                provider TEXT NOT NULL,
                logo_url TEXT,
                hourly_rate TEXT,
                description TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT NOW(),
                UNIQUE(project_id, provider)
            )
        ''')
        logger.info(f"Tabelle {DB_TABLE} überprüft/erstellt.")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Tabelle: {e}")
        return False

async def save_projects_to_db(conn, projects: List[Dict[str, Any]]):
    """Speichert Projekte in der Datenbank"""
    if not projects:
        return 0
    
    try:
        # Tabelle erstellen, falls nötig
        await create_table_if_not_exists(conn)
        
        # Projekte speichern
        inserted_count = 0
        updated_count = 0
        
        for project in projects:
            # JSON-Felder konvertieren
            skills_json = json.dumps(project.get('skills', []))
            
            # Prüfen, ob das Projekt bereits existiert
            existing = await conn.fetchrow(
                f"SELECT id FROM {DB_SCHEMA}.{DB_TABLE} WHERE project_id = $1 AND provider = $2",
                project['project_id'], project['provider']
            )
            
            if existing:
                # Update
                await conn.execute(f'''
                    UPDATE {DB_SCHEMA}.{DB_TABLE} SET 
                    title = $1, company = $2, location = $3, remote = $4, 
                    end_date = $5, last_updated = $6, skills = $7, 
                    url = $8, applications = $9, description = $10
                    WHERE project_id = $11 AND provider = $12
                ''', 
                project['title'], project['company'], project['location'], project['remote'],
                project.get('end_date', ''), project['last_updated'], skills_json,
                project['url'], project['applications'], project.get('description', ''),
                project['project_id'], project['provider']
                )
                updated_count += 1
            else:
                # Insert
                await conn.execute(f'''
                    INSERT INTO {DB_SCHEMA}.{DB_TABLE} 
                    (project_id, title, company, location, remote, end_date, 
                    last_updated, skills, url, applications, provider, description) 
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ''',
                project['project_id'], project['title'], project['company'], project['location'], 
                project['remote'], project.get('end_date', ''), project['last_updated'], 
                skills_json, project['url'], project['applications'], project['provider'],
                project.get('description', '')
                )
                inserted_count += 1
        
        logger.info(f"{inserted_count} Projekte eingefügt, {updated_count} aktualisiert.")
        return inserted_count + updated_count
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Projekte: {e}")
        return 0

async def crawl_all_projects(max_pages: int = 10, page_size: int = 100, save_to_db: bool = True, remote_only: bool = True, delay_seconds: float = 1.0, fetch_descriptions: bool = False):
    """Crawlt alle Projekte mit Paginierung"""
    all_projects = []
    current_page = 1
    base_url = f"{BASE_URL}/projekte"
    has_next_page = True
    conn = None
    
    if save_to_db:
        conn = await get_db_connection()
        if not conn:
            logger.error("Konnte keine Datenbankverbindung herstellen. Fahre ohne DB-Speicherung fort.")
            save_to_db = False
    
    try:
        while has_next_page and current_page <= max_pages:
            # URL für die aktuelle Seite erstellen
            url = await build_pagination_url(base_url, current_page, page_size, remote_only)
            
            # Seite crawlen
            projects, pagination = await scrape_projects_page(url)
            
            if not projects:
                logger.warning(f"Keine Projekte auf Seite {current_page} gefunden. Beende das Crawling.")
                break
            
            # Optional: Beschreibungen von den Detailseiten laden
            if fetch_descriptions and projects:
                logger.info(f"Lade Beschreibungen für {len(projects)} Projekte...")
                for project in projects:
                    if project.get('url'):
                        # Beschreibung laden und etwas Pause zwischen den Anfragen
                        project['description'] = await fetch_project_description(project['url'])
                        await asyncio.sleep(delay_seconds)
            
            # Projekte speichern
            if save_to_db and conn:
                saved_count = await save_projects_to_db(conn, projects)
                logger.info(f"{saved_count} Projekte in der Datenbank gespeichert.")
            
            all_projects.extend(projects)
            
            # Prüfen, ob es eine nächste Seite gibt
            has_next_page = pagination["has_next_page"]
            if has_next_page:
                current_page += 1
                # Kurze Pause einlegen, um den Server nicht zu überlasten
                await asyncio.sleep(delay_seconds)
            else:
                logger.info("Keine weiteren Seiten verfügbar.")
        
        logger.info(f"Crawling abgeschlossen. Insgesamt {len(all_projects)} Projekte extrahiert.")
        return all_projects
    finally:
        if conn:
            await conn.close()
            logger.info("Datenbankverbindung geschlossen.")

async def save_to_json(projects: List[Dict[str, Any]], filename: str = "freelance_projects_all.json"):
    """Speichert die Projekte als JSON für Tests"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(projects, f, indent=2, ensure_ascii=False)
        logger.info(f"Projekte in {filename} gespeichert.")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Projekte: {e}")

async def main():
    """Hauptfunktion"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Crawlt Freelance.de-Projekte")
    parser.add_argument("--no-db", action="store_true", help="Nicht in Datenbank speichern")
    parser.add_argument("--no-remote", action="store_true", help="Auch nicht-remote Projekte anzeigen")
    parser.add_argument("--max-pages", type=int, default=10, help="Maximale Anzahl an Seiten (default: 10)")
    parser.add_argument("--delay", type=float, default=1.0, help="Verzögerung zwischen Requests in Sekunden (default: 1.0)")
    parser.add_argument("--json", type=str, help="Speicherpfad für JSON-Output")
    parser.add_argument("--fetch-descriptions", action="store_true", help="Projektbeschreibungen von Detailseiten laden")
    
    args = parser.parse_args()
    
    # Projekte crawlen
    projects = await crawl_all_projects(
        max_pages=args.max_pages,
        save_to_db=not args.no_db,
        remote_only=not args.no_remote,
        delay_seconds=args.delay,
        fetch_descriptions=args.fetch_descriptions
    )
    
    if projects:
        await save_to_json(projects, args.json)
        return True
    return False

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Crawling durch Benutzer abgebrochen.")
    except Exception as e:
        logger.exception(f"Fehler bei der Ausführung: {e}") 