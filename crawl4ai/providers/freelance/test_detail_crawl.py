#!/usr/bin/env python3
"""
Testet den Crawler für Freelance.de mit Detailseiten:
1. Crawlt eine Listenseite (max. 5 Projekte)
2. Für jedes Projekt wird die Detailseite gecrawlt
3. Die Daten werden in der Datenbank gespeichert
"""
import os
import sys
import json
import asyncio
import logging
import re
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

# Import benötigter Funktionen
from freelance.fetch_and_process import (
    check_cookies, get_cookie_from_playwright_login, fetch_protected_page_via_playwright,
    extract_project_data, extract_json_from_html, extract_project_data_from_json,
    BASE_URL
)

# Datenbank-Konfiguration
DB_USER = os.environ.get("DB_USER", "mailmind")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "mailmind")
DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "mailmind")
DB_TABLE = "freelance_projects"
DB_DETAILS_TABLE = "freelance_project_details"

async def fetch_project_details_page(project_url: str) -> str:
    """Lädt die Detailseite eines Projekts"""
    logger.info(f"Lade Detailseite: {project_url}")
    html_content = await fetch_protected_page_via_playwright(project_url)
    
    if html_content:
        # Speichere HTML für Debugging
        with open(f'/tmp/freelance_detail_{project_url.split("/")[-1]}.html', 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Detailseite erfolgreich geladen: {len(html_content)} Bytes")
        return html_content
    
    logger.error(f"Konnte Detailseite nicht laden: {project_url}")
    return None

async def extract_project_details(html_content: str, project_id: str, provider: str) -> dict:
    """Extrahiert detaillierte Informationen aus der Projektdetailseite"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        details = {
            'project_id': project_id,
            'provider': provider,
            'full_description': '',
            'start_date': '',
            'project_duration': '',
            'hourly_rate': '',
            'reference_number': '',
            'company_url': '',
            'logo_url': '',
            'contact_person': '',
            'contact_address': '',
            'contact_email': '',
            'contact_phone': '',
            'company_active_since': '',
            'view_count': 0,
            'application_count': 0,
            'categories': [],
            'related_projects': []
        }
        
        # Vollständige Beschreibung - in der Panel-Body der Projektbeschreibung
        description_panel = soup.select_one('.panel-default .panel-heading h2[title^="Projektbeschreibung"]')
        if description_panel:
            description_elem = description_panel.parent.parent.select_one('.panel-body.highlight-text')
            if description_elem:
                details['full_description'] = description_elem.get_text(strip=True)
        
        # Alternativ: Beschreibung über direkten Selektor versuchen
        if not details['full_description']:
            description_elem = soup.select_one('.panel-white .panel-body.highlight-text')
            if description_elem:
                details['full_description'] = description_elem.get_text(strip=True)
        
        # Übersichtsinformationen aus der Detailansicht
        overview_items = soup.select('.overview .icon-list li')
        for item in overview_items:
            icon = item.select_one('i')
            if not icon:
                continue
            
            text = item.get_text(strip=True)
            icon_class = icon.get('class', [])
            tooltip = icon.get('data-original-title', '')
            
            # Start/Ende
            if 'fa-calendar-star' in str(icon_class) or 'Geplanter Start' in tooltip:
                details['start_date'] = text
            elif 'fa-calendar-times' in str(icon_class) or 'Voraussichtliches Ende' in tooltip:
                details['end_date'] = text
            # Stundensatz
            elif 'fa-coins' in str(icon_class) or 'Stundensatz' in tooltip:
                details['hourly_rate'] = text
            # Letztes Update
            elif 'fa-history' in str(icon_class) or 'Letztes Update' in tooltip:
                details['last_updated'] = text
        
        # Logo URL
        logo_elem = soup.select_one('.avatar-logo img')
        if logo_elem and logo_elem.has_attr('src'):
            details['logo_url'] = urljoin(BASE_URL, logo_elem['src'])
        
        # Firmen-Name und URL
        company_link = soup.select_one('.company-name a')
        if company_link:
            details['company'] = company_link.get_text(strip=True)
            if company_link.has_attr('href'):
                details['company_url'] = urljoin(BASE_URL, company_link['href'])
        
        # Projektansichten und Bewerbungen aus dem Insights-Panel
        insights_panel = soup.select_one('.panel-heading h3:contains("Projekt Insights")')
        if insights_panel:
            insights_body = insights_panel.parent.parent.select_one('.panel-body')
            if insights_body:
                actions = insights_body.select('.action')
                for action in actions:
                    action_text = action.get_text(strip=True)
                    if 'Projektansichten' in action_text:
                        view_match = re.search(r'(\d+)\s+Projektansichten', action_text)
                        if view_match:
                            details['view_count'] = int(view_match.group(1))
                    elif 'Bewerbungen' in action_text:
                        app_match = re.search(r'(\d+)\s+Bewerbungen', action_text)
                        if app_match:
                            details['application_count'] = int(app_match.group(1))
                    elif 'Aktiv seit' in action_text:
                        active_match = re.search(r'Aktiv seit\s+(\d+)', action_text)
                        if active_match:
                            details['company_active_since'] = active_match.group(1)
        
        # Kontaktdaten
        contact_section = soup.select_one('.panel-heading h3:contains("Kontaktdaten")')
        if contact_section:
            # Ansprechpartner
            contact_panel = contact_section.parent.parent.select_one('.panel-default h3:contains("Ansprechpartner")')
            if contact_panel:
                contact_body = contact_panel.parent.parent
                contact_name = contact_body.select_one('.h5')
                if contact_name:
                    details['contact_person'] = contact_name.get_text(strip=True).strip(',')
                
                # Email und Telefon
                email_elem = contact_body.select_one('a[href^="mailto:"]')
                if email_elem:
                    details['contact_email'] = email_elem['href'].replace('mailto:', '')
                
                phone_label = contact_body.find(string=lambda text: 'Telefon' in text if text else False)
                if phone_label:
                    phone_parent = phone_label.parent
                    if phone_parent:
                        phone_text = phone_parent.get_text().replace('Telefon:', '').strip()
                        details['contact_phone'] = phone_text
                
                # Adresse
                address_label = contact_body.find(string=lambda text: 'Adresse' in text if text else False)
                if address_label:
                    address_parent = address_label.parent.parent
                    if address_parent:
                        address_lines = [line.strip() for line in address_parent.get_text().replace('Adresse:', '').strip().split('\n') if line.strip()]
                        details['contact_address'] = ', '.join(address_lines)
        
        # Kategorien
        category_section = soup.select_one('.panel-heading h3:contains("Kategorien und Skills")')
        if category_section:
            category_body = category_section.parent.parent
            category_items = category_body.select('ul.project-categories li a')
            categories = []
            for cat in category_items:
                cat_name = cat.get_text(strip=True)
                if cat_name:
                    categories.append(cat_name)
            details['categories'] = categories
        
        # Ähnliche Projekte
        related_section = soup.select_one('.panel-heading h3:contains("Ähnliche Projekte")')
        if related_section:
            related_items = related_section.parent.parent.select('.related-item a')
            related = []
            for rel in related_items:
                rel_title = rel.select_one('h3')
                if rel_title and rel.has_attr('href'):
                    rel_url = urljoin(BASE_URL, rel['href'])
                    rel_text = rel_title.get('title', rel_title.get_text(strip=True))
                    related.append({
                        'title': rel_text,
                        'url': rel_url
                    })
            details['related_projects'] = related
        
        logger.info(f"Extrahierte Details für Projekt {project_id}: Beschreibungslänge={len(details['full_description'])}, Kategorien={len(details['categories'])}")
        return details
    except Exception as e:
        logger.error(f"Fehler beim Extrahieren der Projektdetails: {e}")
        return {
            'project_id': project_id,
            'provider': provider,
            'full_description': '',
            'error': str(e)
        }

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

async def create_tables_if_not_exist(conn):
    """Überprüft, ob die Tabellen existieren"""
    try:
        # Prüfe, ob die Projekttabelle existiert
        project_table_exists = await conn.fetchval('''
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = $1
        )
        ''', DB_TABLE)
        
        # Prüfe, ob die Detailtabelle existiert
        details_table_exists = await conn.fetchval('''
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = $1
        )
        ''', DB_DETAILS_TABLE)
        
        if project_table_exists and details_table_exists:
            logger.info(f"Tabellen {DB_TABLE} und {DB_DETAILS_TABLE} existieren bereits.")
            return True
        else:
            logger.error(f"Mindestens eine der benötigten Tabellen existiert nicht.")
            return False
    except Exception as e:
        logger.error(f"Fehler beim Überprüfen der Tabellen: {e}")
        return False

async def save_project_to_db(conn, project: dict):
    """Speichert ein Projekt in der Datenbank"""
    try:
        project_id = project['project_id']
        provider = project['provider']
        
        # Prüfen, ob das Projekt bereits existiert
        exists = await conn.fetchval(f'''
        SELECT COUNT(*) FROM {DB_TABLE} 
        WHERE project_id = $1 AND provider = $2
        ''', project_id, provider)
        
        # Konvertiere Python-Liste zu JSON
        skills_json = json.dumps(project.get('skills', []))
        
        if exists:
            # Projekt aktualisieren
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
            
            logger.info(f"Projekt {project_id} aktualisiert")
            return "updated"
        else:
            # Neues Projekt einfügen
            await conn.execute(f'''
            INSERT INTO {DB_TABLE} 
            (project_id, provider, title, company, end_date, location, remote, last_updated, skills, url, applications, description) 
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            ''', project_id, provider, project['title'], project['company'], 
            project.get('end_date', ''), project.get('location', ''), 
            project.get('remote', False), project.get('last_updated', ''),
            skills_json, project.get('url', ''), project.get('applications', 0),
            project.get('description', ''))
            
            logger.info(f"Projekt {project_id} eingefügt")
            return "inserted"
    except Exception as e:
        logger.error(f"Fehler beim Speichern des Projekts {project.get('project_id')}: {e}")
        return "error"

async def save_project_details_to_db(conn, details: dict):
    """Speichert die Projektdetails in der Datenbank"""
    try:
        project_id = details['project_id']
        provider = details['provider']
        
        # Prüfen, ob bereits Details existieren
        exists = await conn.fetchval(f'''
        SELECT COUNT(*) FROM {DB_DETAILS_TABLE} 
        WHERE project_id = $1 AND provider = $2
        ''', project_id, provider)
        
        # Listen in JSON konvertieren
        categories_json = json.dumps(details.get('categories', []))
        related_projects_json = json.dumps(details.get('related_projects', []))
        
        if exists:
            # Details aktualisieren
            await conn.execute(f'''
            UPDATE {DB_DETAILS_TABLE} SET 
                full_description = $3,
                start_date = $4,
                project_duration = $5,
                hourly_rate = $6,
                reference_number = $7,
                company_url = $8,
                logo_url = $9,
                contact_person = $10,
                contact_address = $11,
                contact_email = $12,
                contact_phone = $13,
                company_active_since = $14,
                view_count = $15,
                application_count = $16,
                categories = $17,
                related_projects = $18,
                details_last_updated = CURRENT_TIMESTAMP
            WHERE project_id = $1 AND provider = $2
            ''', project_id, provider, 
                details.get('full_description', ''),
                details.get('start_date', ''),
                details.get('project_duration', ''),
                details.get('hourly_rate', ''),
                details.get('reference_number', ''),
                details.get('company_url', ''),
                details.get('logo_url', ''),
                details.get('contact_person', ''),
                details.get('contact_address', ''),
                details.get('contact_email', ''),
                details.get('contact_phone', ''),
                details.get('company_active_since', ''),
                details.get('view_count', 0),
                details.get('application_count', 0),
                categories_json,
                related_projects_json)
            
            logger.info(f"Projektdetails für {project_id} aktualisiert")
            return "updated"
        else:
            # Neue Details einfügen
            await conn.execute(f'''
            INSERT INTO {DB_DETAILS_TABLE}
            (project_id, provider, full_description, start_date, project_duration, 
             hourly_rate, reference_number, company_url, logo_url, contact_person,
             contact_address, contact_email, contact_phone, company_active_since,
             view_count, application_count, categories, related_projects)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
            ''', project_id, provider, 
                details.get('full_description', ''),
                details.get('start_date', ''),
                details.get('project_duration', ''),
                details.get('hourly_rate', ''),
                details.get('reference_number', ''),
                details.get('company_url', ''),
                details.get('logo_url', ''),
                details.get('contact_person', ''),
                details.get('contact_address', ''),
                details.get('contact_email', ''),
                details.get('contact_phone', ''),
                details.get('company_active_since', ''),
                details.get('view_count', 0),
                details.get('application_count', 0),
                categories_json,
                related_projects_json)
            
            logger.info(f"Projektdetails für {project_id} eingefügt")
            return "inserted"
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Projektdetails für {details.get('project_id')}: {e}")
        return "error"

async def test_project_and_detail_crawl():
    """Führt einen Test-Crawl für die Projektliste und Detailseiten durch"""
    try:
        # 1. Lade eine Projektliste mit max. 5 Projekten
        logger.info("Starte Test-Crawl für Projektliste und Detailseiten")
        list_url = f"{BASE_URL}/projekte?pageSize=5"  # Begrenze auf 5 Projekte für den Test
        
        logger.info(f"Lade Projektliste von {list_url}")
        list_html = await fetch_protected_page_via_playwright(list_url)
        
        if not list_html:
            logger.error("Konnte Projektliste nicht laden.")
            return False
        
        # Speichere die Liste für Debugging
        with open('/tmp/freelance_list.html', 'w', encoding='utf-8') as f:
            f.write(list_html)
        logger.info("Projektliste in /tmp/freelance_list.html gespeichert")
        
        # 2. Extrahiere Projekte aus der Liste
        projects = extract_project_data(list_html)
        logger.info(f"{len(projects)} Projekte aus der Liste extrahiert")
        
        if not projects:
            logger.error("Keine Projekte gefunden.")
            return False
        
        # 3. Verbindung zur Datenbank herstellen
        conn = await get_db_connection()
        if not conn:
            logger.error("Konnte keine Datenbankverbindung herstellen.")
            return False
        
        # 4. Tabellen überprüfen
        if not await create_tables_if_not_exist(conn):
            await conn.close()
            return False
        
        # 5. Jedes Projekt verarbeiten und Details crawlen
        project_count = 0
        detail_count = 0
        
        for project in projects:
            # Projekt in DB speichern
            result = await save_project_to_db(conn, project)
            if result in ["inserted", "updated"]:
                project_count += 1
            
            # Detailseite laden und verarbeiten
            project_url = project.get('url')
            project_id = project.get('project_id')
            provider = project.get('provider')
            
            if project_url and project_id and provider:
                # Lade die Detailseite
                detail_html = await fetch_project_details_page(project_url)
                
                if detail_html:
                    # Extrahiere Details
                    details = await extract_project_details(detail_html, project_id, provider)
                    
                    # Details in DB speichern
                    if details:
                        result = await save_project_details_to_db(conn, details)
                        if result in ["inserted", "updated"]:
                            detail_count += 1
                
                # Kleine Pause zwischen den Requests einlegen
                await asyncio.sleep(1)
        
        # 6. Verbindung schließen
        await conn.close()
        
        logger.info(f"Test abgeschlossen. {project_count} Projekte und {detail_count} Detailseiten verarbeitet.")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Test-Crawl: {e}")
        return False

if __name__ == "__main__":
    # Führe den Test asynchron aus
    success = asyncio.run(test_project_and_detail_crawl())
    
    # Exit-Code basierend auf Erfolg/Misserfolg
    sys.exit(0 if success else 1) 