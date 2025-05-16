#!/usr/bin/env python3
"""
Crawler für Projektdetails von Freelance.de
Extrahiert Detailinformationen aus den Projektdetailseiten
"""
import os
import sys
import json
import asyncio
import logging
import argparse
import re
from typing import Dict, Any, List, Optional
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup, Tag
import asyncpg

# Konfiguration
BASE_URL = "https://www.freelance.de"
COOKIE_PATH = os.path.join(os.path.dirname(__file__), 'freelance_cookies.json')

# Datenbank-Konfiguration
DB_USER = os.environ.get("DB_USER", "mailmind")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "mailmind")
DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "mailmind")
PROJECTS_TABLE = "freelance_projects"
DETAILS_TABLE = "freelance_project_details"

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pfad zum providers-Verzeichnis hinzufügen
current_dir = os.path.dirname(os.path.abspath(__file__))
providers_dir = os.path.dirname(current_dir)
if providers_dir not in sys.path:
    sys.path.insert(0, providers_dir)

# Import aus dem freelance-Verzeichnis für die vorhandenen Funktionen
from freelance.fetch_and_process import check_cookies, get_cookie_from_playwright_login, fetch_protected_page_via_playwright

class ProjectDetailExtractor:
    """Extrahiert Detailinformationen aus Projektdetailseiten"""
    
    def __init__(self, html: str, project_id: str, provider: str = "freelance.de"):
        self.soup = BeautifulSoup(html, 'html.parser')
        self.project_id = project_id
        self.provider = provider
        self.base_url = BASE_URL
        
    def extract_all_details(self) -> Dict[str, Any]:
        """Extrahiert alle verfügbaren Details aus der Projektseite"""
        details = {
            'project_id': self.project_id,
            'provider': self.provider
        }
        
        # Basisdaten
        company_url = self.extract_company_url()
        if company_url:
            details['company_url'] = company_url
        
        logo_url = self.extract_logo_url()
        if logo_url:
            details['logo_url'] = logo_url
        
        # Projektdaten
        start_date = self.extract_start_date()
        if start_date:
            details['start_date'] = start_date
            
        project_duration = self.extract_project_duration()
        if project_duration:
            details['project_duration'] = project_duration
            
        reference_number = self.extract_reference_number()
        if reference_number:
            details['reference_number'] = reference_number
            
        hourly_rate = self.extract_hourly_rate()
        if hourly_rate:
            details['hourly_rate'] = hourly_rate
        
        # Statistiken
        company_active_since = self.extract_company_active_since()
        if company_active_since:
            details['company_active_since'] = company_active_since
            
        view_count = self.extract_view_count()
        if view_count is not None:
            details['view_count'] = view_count
            
        application_count = self.extract_application_count()
        if application_count is not None:
            details['application_count'] = application_count
        
        # Detaillierte Beschreibung
        full_description = self.extract_full_description()
        if full_description:
            details['full_description'] = full_description
        
        # Kontaktdaten
        contact_person = self.extract_contact_person()
        if contact_person:
            details['contact_person'] = contact_person
            
        contact_address = self.extract_contact_address()
        if contact_address:
            details['contact_address'] = contact_address
            
        contact_email = self.extract_contact_email()
        if contact_email:
            details['contact_email'] = contact_email
            
        contact_phone = self.extract_contact_phone()
        if contact_phone:
            details['contact_phone'] = contact_phone
        
        # Kategorien und Skills
        categories = self.extract_categories_and_skills()
        if categories:
            details['categories'] = json.dumps(categories)
        
        # Ähnliche Projekte
        related_projects = self.extract_related_projects()
        if related_projects:
            details['related_projects'] = json.dumps(related_projects)
        
        return details
    
    def extract_company_url(self) -> Optional[str]:
        """Extrahiert die Firmen-URL"""
        company_link = self.soup.select_one('.company-name a')
        if company_link and 'href' in company_link.attrs:
            return urljoin(self.base_url, company_link['href'])
        return None
    
    def extract_logo_url(self) -> Optional[str]:
        """Extrahiert die Logo-URL"""
        logo_img = self.soup.select_one('.avatar-logo img')
        if logo_img and 'src' in logo_img.attrs:
            return urljoin(self.base_url, logo_img['src'])
        return None
    
    def extract_start_date(self) -> Optional[str]:
        """Extrahiert das Startdatum"""
        start_date_elem = self.soup.select_one('li:has(i.fa-calendar-star)')
        if start_date_elem:
            text = start_date_elem.get_text(strip=True)
            return text
        return None
    
    def extract_project_duration(self) -> Optional[str]:
        """Extrahiert die Projektdauer"""
        duration_elem = self.soup.select_one('li:has(i.fa-calendar-times)')
        if duration_elem:
            text = duration_elem.get_text(strip=True)
            return text
        return None
    
    def extract_reference_number(self) -> Optional[str]:
        """Extrahiert die Referenznummer"""
        ref_elem = self.soup.select_one('li:has(i.fa-tag)')
        if ref_elem:
            text = ref_elem.get_text(strip=True)
            return text
        return None
    
    def extract_hourly_rate(self) -> Optional[str]:
        """Extrahiert den Stundensatz"""
        rate_elem = self.soup.select_one('li:has(i.fa-coins)')
        if rate_elem:
            text = rate_elem.get_text(strip=True)
            return text
        return None
    
    def extract_company_active_since(self) -> Optional[str]:
        """Extrahiert die Information, seit wann die Firma aktiv ist"""
        active_elem = self.soup.select_one('.action:has(img)') 
        if active_elem:
            text = active_elem.get_text(strip=True)
            return text
        return None
    
    def extract_view_count(self) -> Optional[int]:
        """Extrahiert die Anzahl der Ansichten"""
        views_elem = self.soup.select_one('.action:has(i.fa-eye)')
        if views_elem:
            text = views_elem.get_text(strip=True)
            match = re.search(r'(\d+)', text)
            if match:
                return int(match.group(1))
        return None
    
    def extract_application_count(self) -> Optional[int]:
        """Extrahiert die Anzahl der Bewerbungen"""
        apps_elem = self.soup.select_one('.action:has(i.fa-user)')
        if apps_elem:
            text = apps_elem.get_text(strip=True)
            match = re.search(r'(\d+)', text)
            if match:
                return int(match.group(1))
        return None
    
    def extract_full_description(self) -> Optional[str]:
        """Extrahiert die vollständige Projektbeschreibung"""
        desc_elem = self.soup.select_one('.panel-body.highlight-text')
        if desc_elem:
            return desc_elem.get_text(strip=True).replace('\xa0', ' ')
        return None
    
    def extract_contact_person(self) -> Optional[str]:
        """Extrahiert den Kontaktnamen"""
        contact_div = self.soup.select_one('#contact_data .col-md-6')
        if contact_div:
            lines = contact_div.get_text(strip=True).split('\n')
            if lines:
                return lines[0]
        return None
    
    def extract_contact_address(self) -> Optional[str]:
        """Extrahiert die Kontaktadresse"""
        contact_div = self.soup.select_one('#contact_data .col-md-6')
        if contact_div:
            return contact_div.get_text(strip=True)
        return None
    
    def extract_contact_email(self) -> Optional[str]:
        """Extrahiert die Kontakt-E-Mail"""
        email_link = self.soup.select_one('#contact_data .col-md-6 a[href^="mailto:"]')
        if email_link:
            return email_link.get_text(strip=True)
        return None
    
    def extract_contact_phone(self) -> Optional[str]:
        """Extrahiert die Kontakttelefonnummer"""
        phone_div = self.soup.select_one('#contact_data .col-md-6:nth-of-type(2)')
        if phone_div and phone_div.contents:
            for content in phone_div.contents:
                if isinstance(content, str) and "Geschäftlich:" in content:
                    return content.strip()
        return None
    
    def extract_categories_and_skills(self) -> List[Dict[str, Any]]:
        """Extrahiert Kategorien und Skills"""
        categories = []
        category_headings = self.soup.select('.panel-default .panel-body h6')
        
        for heading in category_headings:
            category_name = heading.get_text(strip=True).rstrip(':')
            category_data = {
                'name': category_name,
                'subcategories': []
            }
            
            # Finde die entsprechende Kategorie-Liste
            ul_elem = heading.find_next('ul', class_='project-categories')
            if ul_elem:
                for li in ul_elem.select('> li'):
                    subcategory_link = li.select_one('a')
                    if subcategory_link:
                        subcategory = {
                            'name': subcategory_link.get_text(strip=True),
                            'url': urljoin(self.base_url, subcategory_link['href']),
                            'skills': []
                        }
                        
                        # Finde die Skills für diese Unterkategorie
                        skills_ul = li.select_one('ul')
                        if skills_ul:
                            for skill_li in skills_ul.select('li'):
                                skill_link = skill_li.select_one('a')
                                if skill_link:
                                    skill = {
                                        'name': skill_link.get_text(strip=True),
                                        'url': urljoin(self.base_url, skill_link['href'])
                                    }
                                    subcategory['skills'].append(skill)
                        
                        category_data['subcategories'].append(subcategory)
            
            categories.append(category_data)
            
        return categories
    
    def extract_related_projects(self) -> List[Dict[str, Any]]:
        """Extrahiert ähnliche Projekte"""
        related = []
        related_items = self.soup.select('.related-item')
        
        for item in related_items:
            link = item.select_one('a')
            if not link:
                continue
                
            project_url = urljoin(self.base_url, link['href'])
            project_id_match = re.search(r'projekt-(\d+)', project_url)
            project_id = project_id_match.group(1) if project_id_match else None
            
            title_elem = item.select_one('h3')
            title = title_elem.get('title', '') if title_elem else ''
            
            location_elem = item.select_one('i.fa-map-marker-alt')
            location = location_elem.next_sibling.strip() if location_elem else ''
            
            date_elem = item.select_one('i.fa-clock')
            start_date = date_elem.next_sibling.strip() if date_elem else ''
            
            logo_elem = item.select_one('img')
            logo_url = urljoin(self.base_url, logo_elem['src']) if logo_elem and 'src' in logo_elem.attrs else ''
            
            related.append({
                'project_id': project_id,
                'title': title,
                'url': project_url,
                'location': location,
                'start_date': start_date,
                'logo_url': logo_url
            })
            
        return related

async def fetch_project_details_page(project_id: str, url: str = None) -> Optional[str]:
    """Lädt die Projektdetailseite"""
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
        
        # Verwende die vollständige URL, wenn verfügbar, oder baue die URL mit der ID
        if url and '/projekte/projekt-' in url:
            detail_url = url
        else:
            detail_url = f"{BASE_URL}/projekte/projekt-{project_id}"
            
        logger.info(f"Lade Projektdetails für ID {project_id} von URL: {detail_url}")
        
        # NEU: Playwright-Login-Service für geschützte Seite nutzen
        html = await fetch_protected_page_via_playwright(detail_url)
        if html:
            # HTML-Dump speichern
            logger.info(f"[DUMP-DEBUG] Versuche Dump zu schreiben: {dump_path}")
            dump_path = os.path.join(os.path.dirname(__file__), 'detail_dump.html')
            with open(dump_path, 'w') as dumpfile:
                dumpfile.write(html)
            logger.info(f"[DUMP-DEBUG] Dump erfolgreich geschrieben: {dump_path}")
            return html
            else:
            logger.error(f"Fehler beim Laden der Projektdetailseite für ID {project_id} via Playwright")
                return None
    except Exception as e:
        logger.error(f"Fehler beim Laden der Projektdetailseite für ID {project_id}: {e}")
        return None

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

async def create_details_table_if_not_exists(conn):
    """Erstellt die Detailtabelle, falls sie nicht existiert"""
    try:
        # SQL aus der Datei laden
        script_path = os.path.join(os.path.dirname(__file__), 'db_schema_details.sql')
        with open(script_path, 'r') as f:
            sql_script = f.read()
        
        # Skript ausführen
        await conn.execute(sql_script)
        logger.info(f"Tabelle {DETAILS_TABLE} überprüft/erstellt.")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Detailtabelle: {e}")
        return False

async def get_projects_without_details(conn, limit: int = 100) -> List[Dict[str, Any]]:
    """Holt Projekte, für die noch keine Details vorhanden sind"""
    try:
        query = f"""
        SELECT p.project_id, p.provider, p.url 
        FROM {PROJECTS_TABLE} p
        LEFT JOIN {DETAILS_TABLE} d ON p.project_id = d.project_id AND p.provider = d.provider
        WHERE d.id IS NULL
        LIMIT $1
        """
        rows = await conn.fetch(query, limit)
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Fehler beim Abrufen von Projekten ohne Details: {e}")
        return []

async def save_project_details(conn, details: Dict[str, Any]) -> bool:
    """Speichert die Projektdetails in der Datenbank"""
    try:
        # JSON-Felder vorbereiten
        categories = details.get('categories', '[]')
        related_projects = details.get('related_projects', '[]')
        
        # Prüfen, ob der Eintrag bereits existiert
        existing = await conn.fetchrow(
            f"SELECT id FROM {DETAILS_TABLE} WHERE project_id = $1 AND provider = $2",
            details['project_id'], details['provider']
        )
        
        if existing:
            # Update
            query = f"""
                UPDATE {DETAILS_TABLE} SET 
                company_url = $1, logo_url = $2, start_date = $3, 
                project_duration = $4, reference_number = $5, hourly_rate = $6,
                company_active_since = $7, view_count = $8, application_count = $9,
                full_description = $10, contact_person = $11, contact_address = $12,
                contact_email = $13, contact_phone = $14, categories = $15::jsonb, 
                related_projects = $16::jsonb, details_last_updated = NOW()
                WHERE project_id = $17 AND provider = $18
            """
            
            await conn.execute(query, 
                details.get('company_url'), details.get('logo_url'), details.get('start_date'),
                details.get('project_duration'), details.get('reference_number'), details.get('hourly_rate'),
                details.get('company_active_since'), details.get('view_count'), details.get('application_count'),
                details.get('full_description'), details.get('contact_person'), details.get('contact_address'),
                details.get('contact_email'), details.get('contact_phone'), categories, 
                related_projects, details['project_id'], details['provider']
            )
            logger.info(f"Projektdetails für ID {details['project_id']} aktualisiert.")
        else:
            # Insert
            query = f"""
                INSERT INTO {DETAILS_TABLE}
                (project_id, provider, company_url, logo_url, start_date, 
                project_duration, reference_number, hourly_rate, company_active_since,
                view_count, application_count, full_description, contact_person,
                contact_address, contact_email, contact_phone, categories, related_projects)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17::jsonb, $18::jsonb)
            """
            
            await conn.execute(query,
                details['project_id'], details['provider'], details.get('company_url'), 
                details.get('logo_url'), details.get('start_date'), details.get('project_duration'),
                details.get('reference_number'), details.get('hourly_rate'), details.get('company_active_since'),
                details.get('view_count'), details.get('application_count'), details.get('full_description'),
                details.get('contact_person'), details.get('contact_address'), details.get('contact_email'),
                details.get('contact_phone'), categories, related_projects
            )
            logger.info(f"Projektdetails für ID {details['project_id']} eingefügt.")
        
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Projektdetails für ID {details['project_id']}: {e}")
        return False

async def process_project_details(project_id: str, url: str = None, provider: str = "freelance.de") -> bool:
    """Verarbeitet die Details eines Projekts"""
    # HTML laden
    html = await fetch_project_details_page(project_id, url)
    if not html:
        return False
    
    # Details extrahieren
    extractor = ProjectDetailExtractor(html, project_id, provider)
    details = extractor.extract_all_details()
    
    # In Datenbank speichern
    conn = await get_db_connection()
    if not conn:
        return False
    
    try:
        # Tabelle erstellen, falls nötig
        if not await create_details_table_if_not_exists(conn):
            return False
        
        # Details speichern
        if not await save_project_details(conn, details):
            return False
        
        return True
    finally:
        # Verbindung schließen
        await conn.close()
        logger.info("DB-Verbindung geschlossen.")

async def process_projects_without_details(limit: int = 100, max_parallel: int = 5) -> int:
    """Verarbeitet mehrere Projekte ohne Details parallel"""
    conn = await get_db_connection()
    if not conn:
        return 0
    
    try:
        # Tabelle erstellen, falls nötig
        if not await create_details_table_if_not_exists(conn):
            return 0
        
        # Projekte ohne Details holen
        projects = await get_projects_without_details(conn, limit)
        logger.info(f"{len(projects)} Projekte ohne Details gefunden.")
        
        if not projects:
            return 0
        
        # Verbindung schließen vor dem parallelen Crawling
        await conn.close()
        
        # Semaphor für Parallelausführungsbegrenzung
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def process_with_semaphore(project):
            async with semaphore:
                return await process_project_details(
                    project['project_id'], 
                    project.get('url'), 
                    project.get('provider', 'freelance.de')
                )
        
        # Alle Projekte asynchron verarbeiten
        tasks = [process_with_semaphore(project) for project in projects]
        results = await asyncio.gather(*tasks)
        
        # Zählen, wie viele erfolgreich waren
        success_count = sum(1 for result in results if result)
        logger.info(f"{success_count} von {len(projects)} Projektdetails erfolgreich verarbeitet.")
        
        return success_count
    except Exception as e:
        logger.error(f"Fehler bei der Verarbeitung von Projekten ohne Details: {e}")
        return 0
    finally:
        # Sicherstellen, dass die Verbindung geschlossen wird
        if not conn.is_closed():
            await conn.close()

async def main(project_id: str = None, limit: int = 100, max_parallel: int = 5):
    """Hauptfunktion"""
    if project_id:
        # Einzelnes Projekt verarbeiten
        success = await process_project_details(project_id)
        if success:
            logger.info(f"Projektdetails für ID {project_id} erfolgreich verarbeitet.")
        else:
            logger.error(f"Fehler bei der Verarbeitung von Projektdetails für ID {project_id}.")
    else:
        # Projekte ohne Details verarbeiten
        processed = await process_projects_without_details(limit, max_parallel)
        logger.info(f"Insgesamt {processed} Projekte verarbeitet.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawler für Projektdetails von Freelance.de")
    parser.add_argument("--project-id", help="Spezifische Projekt-ID für die Detailabfrage", type=str)
    parser.add_argument("--limit", help="Maximale Anzahl an Projekten, die verarbeitet werden sollen", type=int, default=100)
    parser.add_argument("--max-parallel", help="Maximale Anzahl paralleler Anfragen", type=int, default=5)
    args = parser.parse_args()
    
    # Asynchron ausführen
    asyncio.run(main(args.project_id, args.limit, args.max_parallel)) 