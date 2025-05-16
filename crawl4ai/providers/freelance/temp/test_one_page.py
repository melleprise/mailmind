#!/usr/bin/env python3
"""
Testet den Crawler für eine Seite von Freelance.de
"""
import os
import sys
import json
import asyncio
import logging
import re
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

# Import benötigter Funktionen
from freelance.fetch_and_process import check_cookies, get_cookie_from_playwright_login, fetch_protected_page_via_playwright

# Konfiguration
BASE_URL = "https://www.freelance.de"
TEST_URL = f"{BASE_URL}/projekte?pageSize=100"  # Eine Seite mit 100 Projekten

def extract_json_from_html(html_content):
    """Extrahiert die JSON-Daten aus dem HTML-Inhalt"""
    
    # Versuche, das JSON mit einem regulären Ausdruck direkt aus dem HTML zu extrahieren
    # Wir suchen nach dem Array von Projekten
    pattern = r'"projects":\[(.*?)\],"pagination":'
    projects_match = re.search(pattern, html_content, re.DOTALL)
    
    if projects_match:
        # Extrahiere das JSON-Array der Projekte
        projects_json_str = '[' + projects_match.group(1) + ']'
        
        try:
            # Versuche, das JSON zu parsen
            projects = json.loads(projects_json_str)
            logger.info(f"Erfolgreich {len(projects)} Projekte aus JSON extrahiert")
            return projects
        except json.JSONDecodeError as e:
            logger.error(f"Fehler beim Parsen des JSON: {e}")
            
            # Versuche, die einzelnen Projekte manuell zu extrahieren
            project_pattern = r'{"id":"(\d+)".*?"linkToDetail":"[^"]+"}'
            projects = []
            
            for match in re.finditer(project_pattern, projects_json_str, re.DOTALL):
                try:
                    project_json_str = match.group(0)
                    project_data = json.loads(project_json_str)
                    projects.append(project_data)
                except json.JSONDecodeError:
                    continue
            
            logger.info(f"Extrahierte {len(projects)} Projekte mit alternativer Methode")
            return projects
    
    logger.warning("Konnte keine JSON-Projektdaten im HTML finden")
    return []

def extract_project_data_from_json(project_json) -> dict:
    """Extrahiert die Daten für ein einzelnes Projekt aus dem JSON"""
    try:
        # Projekt-ID
        project_id = project_json.get("id", "")
        
        # Titel
        title = project_json.get("projectTitle", "")
        
        # Firma
        company = project_json.get("companyName", "Unbekannt")
        
        # Skills extrahieren
        skills = []
        skill_tags = project_json.get("skillTags", [])
        for skill in skill_tags:
            skill_name = skill.get("skillName", "")
            if skill_name:
                skills.append(skill_name)
        
        # Enddatum extrahieren
        start_date = project_json.get("projectStartDate", "")
        
        # Standort extrahieren
        locations = project_json.get("locations", [])
        location = ""
        if locations and len(locations) > 0:
            location_city = locations[0].get("city", "")
            location_county = locations[0].get("county", "")
            if location_city and location_county:
                location = f"{location_city}, {location_county}"
            elif location_city:
                location = location_city
            elif location_county:
                location = location_county
        
        # Remote-Status
        remote = bool(project_json.get("remote", ""))
        
        # Letztes Update
        last_updated = project_json.get("lastUpdate", "")
        
        # URL
        detail_url = project_json.get("linkToDetail", "")
        full_url = urljoin(BASE_URL, detail_url) if detail_url else ""
        
        # Bewerbungen
        applications = 0
        insight_apps = project_json.get("insightApplicants", {})
        if insight_apps:
            app_text = insight_apps.get("link", {}).get("text", "")
            if "Jetzt als Erstes bewerben" in app_text:
                applications = 0
            elif "Zu den ersten Bewerbern" in app_text:
                applications = 1
            elif "<" in app_text:
                # Format wie "<10 Bewerbungen"
                app_match = re.search(r'<\s*(\d+)', app_text)
                if app_match:
                    applications = int(app_match.group(1)) - 1  # Nehme einen weniger an als Maximum
        
        # Beschreibung (in dieser JSON-Ansicht nicht vorhanden, muss später durch Details ergänzt werden)
        description = ""
        
        return {
            'project_id': project_id,
            'title': title,
            'company': company,
            'end_date': start_date,  # Nutze start_date als Ersatz
            'location': location,
            'remote': remote,
            'last_updated': last_updated,
            'skills': skills,
            'url': full_url,
            'applications': applications,
            'description': description,
            'provider': 'freelance.de'
        }
    except Exception as e:
        logger.error(f"Fehler beim Extrahieren der Projektdaten aus JSON: {e}")
        return None

async def extract_projects_from_page(html_content: str) -> list:
    """Extrahiert alle Projekte von einer HTML-Seite"""
    # Versuche erst, die JSON-Daten zu extrahieren
    projects_json = extract_json_from_html(html_content)
    
    if projects_json:
        logger.info(f"Gefundene Projekte im JSON: {len(projects_json)}")
        
        projects = []
        for project_json in projects_json:
            project_data = extract_project_data_from_json(project_json)
            if project_data:
                projects.append(project_data)
        
        logger.info(f"Extrahierte Projektdaten: {len(projects)}")
        return projects
    
    # Fallback: Versuche die alte Methode mit BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    project_items = soup.select('.project-item.online')
    
    logger.info(f"Gefundene Projekt-Items im HTML: {len(project_items)}")
    
    projects = []
    for item in project_items:
        project_data = extract_project_data(item)
        if project_data:
            projects.append(project_data)
    
    return projects

def extract_project_data(item) -> dict:
    """Extrahiert die Daten für ein einzelnes Projekt (alte Methode)"""
    try:
        # Link extrahieren
        link_element = item.select_one('h2.title a')
        if not link_element:
            return None
            
        link = link_element['href']
        full_url = urljoin(BASE_URL, link)
        
        # Projekt-ID extrahieren
        project_id_match = re.search(r'projekt-(\d+)', link)
        if not project_id_match:
            return None
            
        project_id = project_id_match.group(1)
        
        # Titel extrahieren
        title = link_element.get_text(strip=True)
        
        # Firma extrahieren
        company_element = item.select_one('.company')
        company = company_element.get_text(strip=True) if company_element else "Unbekannt"
        
        # Skills extrahieren
        skills = []
        skills_elements = item.select('.skills li')
        for skill_elem in skills_elements:
            skill_text = skill_elem.get_text(strip=True)
            if skill_text:
                skills.append(skill_text)
        
        # Enddatum extrahieren
        info_elements = item.select('.info li')
        end_date = ""
        location = ""
        remote = False
        last_updated = ""
        
        for info in info_elements:
            info_text = info.get_text(strip=True)
            
            if 'Projektende:' in info_text:
                end_date = info_text.replace('Projektende:', '').strip()
            elif 'Remote' in info_text:
                remote = True
            elif 'Ort:' in info_text:
                location = info_text.replace('Ort:', '').strip()
            elif 'vor' in info_text and ('Stunde' in info_text or 'Tag' in info_text or 'Minute' in info_text):
                last_updated = info_text.strip()
        
        # Bewerbungen extrahieren
        applications_element = item.select_one('.applications')
        applications = 0
        if applications_element:
            applications_text = applications_element.get_text(strip=True)
            applications_match = re.search(r'(\d+)', applications_text)
            if applications_match:
                applications = int(applications_match.group(1))
        
        # Beschreibung extrahieren
        description_element = item.select_one('.description')
        description = ""
        if description_element:
            description = description_element.get_text(strip=True)
        
        return {
            'project_id': project_id,
            'title': title,
            'company': company,
            'end_date': end_date,
            'location': location,
            'remote': remote,
            'last_updated': last_updated,
            'skills': skills,
            'url': full_url,
            'applications': applications,
            'description': description,
            'provider': 'freelance.de'
        }
    except Exception as e:
        logger.error(f"Fehler beim Extrahieren der Projektdaten: {e}")
        return None

async def get_db_connection():
    """Stellt eine Verbindung zur Datenbank her"""
    import asyncpg
    
    DB_USER = "mailmind"
    DB_PASSWORD = "mailmind"
    DB_HOST = "postgres"
    DB_PORT = "5432"
    DB_NAME = "mailmind"
    
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

async def process_projects_in_db(projects: list) -> bool:
    """Speichert die Projekte in der Datenbank"""
    if not projects:
        logger.info("Keine Projekte zum Speichern vorhanden")
        return True
    
    import asyncpg
    import json
    
    DB_TABLE = "freelance_projects"
    
    try:
        # Verbindung zur Datenbank herstellen
        conn = await get_db_connection()
        if not conn:
            return False
        
        # Projekte in die Datenbank einfügen
        inserted = 0
        updated = 0
        
        async with conn.transaction():
            for project in projects:
                project_id = project['project_id']
                provider = project['provider']
                
                # Prüfen, ob das Projekt bereits existiert
                exists = await conn.fetchval('''
                SELECT COUNT(*) FROM freelance_projects 
                WHERE project_id = $1 AND provider = $2
                ''', project_id, provider)
                
                if exists:
                    # Projekt aktualisieren
                    skill_json = json.dumps(project['skills']) if 'skills' in project else '[]'
                    await conn.execute('''
                    UPDATE freelance_projects SET 
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
                    skill_json, project.get('url', ''), project.get('applications', 0),
                    project.get('description', ''))
                    
                    updated += 1
                else:
                    # Neues Projekt einfügen
                    skill_json = json.dumps(project['skills']) if 'skills' in project else '[]'
                    await conn.execute('''
                    INSERT INTO freelance_projects 
                    (project_id, provider, title, company, end_date, location, remote, last_updated, skills, url, applications, description) 
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    ''', project_id, provider, project['title'], project['company'], 
                    project.get('end_date', ''), project.get('location', ''), 
                    project.get('remote', False), project.get('last_updated', ''),
                    skill_json, project.get('url', ''), project.get('applications', 0),
                    project.get('description', ''))
                    
                    inserted += 1
        
        logger.info(f"{inserted} Projekte eingefügt, {updated} Projekte aktualisiert")
        
        # Verbindung schließen
        await conn.close()
        
        return True
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Projekte in der Datenbank: {e}")
        return False

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
        logger.info(f"Tabelle freelance_projects überprüft/erstellt.")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Tabelle: {e}")
        return False

async def test_one_page_crawl():
    """Testet das Crawlen einer Seite"""
    logger.info(f"Starte Test-Crawling von {TEST_URL}")
    
    # Seite laden
    html_content = await fetch_protected_page_via_playwright(TEST_URL)
    if not html_content:
        logger.error("Seite konnte nicht geladen werden.")
        return False
    
    # Speichere den HTML-Inhalt zur Inspektion
    with open('/tmp/freelance_page.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    logger.info("HTML-Inhalt in /tmp/freelance_page.html gespeichert")
    
    # Projekte extrahieren
    projects = await extract_projects_from_page(html_content)
    
    logger.info(f"{len(projects)} Projekte auf der Seite gefunden.")
    
    # Ein paar Beispielprojekte anzeigen
    if projects:
        for i, project in enumerate(projects[:3]):
            logger.info(f"Projekt {i+1}: {project['title']} (ID: {project['project_id']}, URL: {project['url']})")
    
    # In Datenbank speichern
    conn = await get_db_connection()
    if conn:
        await create_table_if_not_exists(conn)
        await conn.close()
    
    success = await process_projects_in_db(projects)
    
    if success:
        logger.info(f"Test erfolgreich: {len(projects)} Projekte in Datenbank gespeichert.")
    else:
        logger.error("Test fehlgeschlagen: Projekte konnten nicht in der Datenbank gespeichert werden.")
    
    return success

if __name__ == "__main__":
    # Führe den Test asynchron aus
    success = asyncio.run(test_one_page_crawl())
    
    # Exit-Code basierend auf Erfolg/Misserfolg
    sys.exit(0 if success else 1) 