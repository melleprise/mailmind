#!/usr/bin/env python3
import os
import json
import asyncio
import httpx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import sys
import re
from datetime import datetime
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode, urlunparse
from slugify import slugify
import subprocess
import asyncpg

# Konfiguration
BASE_URL = "https://www.freelance.de"
PROJECTS_URL = f"{BASE_URL}/projekte"
COOKIE_PATH = os.path.join(os.path.dirname(__file__), 'freelance_cookies.json')
LOGIN_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), 'login.js')
PLAYWRIGHT_LOGIN_URL = "http://playwright-login:3000/login"
DB_SCHEMA = "public"
DB_TABLE = "freelance_projects"
PROVIDER = "freelance"
DEFAULT_PAGE_SIZE = 100
DJANGO_BACKEND_URL = os.environ.get("DJANGO_BACKEND_URL", "http://backend:8000")

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Datenmodell für ein Projekt
class FreelanceProject(BaseModel):
    project_id: str
    title: str
    company: str
    end_date: Optional[str] = None
    location: Optional[str] = None
    remote: bool = False
    last_updated: Optional[str] = None
    skills: List[str] = []
    url: str
    applications: Optional[int] = None
    description: str = ""
    provider: str = PROVIDER
    created_at: str = datetime.now().isoformat()
    
    def to_db_dict(self) -> Dict[str, Any]:
        """Konvertiert das Projekt in ein Dictionary für die Datenbank"""
        return {
            "project_id": self.project_id,
            "title": self.title,
            "company": self.company,
            "end_date": self.end_date,
            "location": self.location,
            "remote": self.remote,
            "last_updated": self.last_updated,
            "skills": self.skills,
            "url": self.url,
            "applications": self.applications,
            "description": self.description,
            "provider": self.provider,
            "created_at": self.created_at
        }

async def check_cookies() -> bool:
    """Prüft, ob ein gültiger Cookie existiert"""
    try:
        cookie_paths = [
            COOKIE_PATH,  # Lokaler Cookie im Provider-Ordner
            "/cookies/freelance.json"  # Docker-Volume-Cookie
        ]
        
        for path in cookie_paths:
            if os.path.exists(path) and os.path.getsize(path) > 0:
                logger.info(f"Cookie-Datei gefunden: {path}")
                with open(path) as f:
                    cookies = json.load(f)
                
                now = datetime.now().timestamp()
                valid_cookies = False
                
                for cookie in cookies:
                    if cookie.get('domain', '').endswith('freelance.de') and cookie.get('expires', now+1) > now:
                        valid_cookies = True
                        break
                        
                if valid_cookies:
                    logger.info(f"Gültiger Cookie gefunden in {path}")
                    # Bei Docker-Volume-Cookie, kopiere den Cookie in den Provider-Ordner
                    if path != COOKIE_PATH:
                        logger.info(f"Kopiere Cookie von {path} nach {COOKIE_PATH}")
                        with open(COOKIE_PATH, 'w') as f:
                            json.dump(cookies, f, indent=2)
                    return True
                else:
                    logger.info(f"Cookie in {path} ist abgelaufen.")
            else:
                logger.info(f"Keine Cookie-Datei gefunden unter {path} oder Datei ist leer.")
        
        logger.info("Keine gültigen Cookies gefunden.")
        return False
    except Exception as e:
        logger.error(f"Fehler beim Prüfen der Cookies: {e}")
        return False

async def get_cookie_from_playwright_login(username: str, password: str) -> bool:
    """Holt einen neuen Cookie vom Playwright-Login-Service mit Userdaten"""
    try:
        logger.info("Hole neuen Cookie vom Playwright-Login-Service...")
        if os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER", ""):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    logger.info(f"Sende Anfrage an {PLAYWRIGHT_LOGIN_URL}")
                    response = await client.post(
                        PLAYWRIGHT_LOGIN_URL,
                        json={"username": username, "password": password}
                    )
                    logger.info(f"Response Status: {response.status_code}")
                    if response.status_code == 200:
                        data = response.json()
                        logger.info("Erfolgreiche Antwort vom Login-Service erhalten")
                        with open(COOKIE_PATH, 'w') as f:
                            json.dump(data.get('cookies', []), f, indent=2)
                        logger.info(f"Cookie in {COOKIE_PATH} gespeichert")
                        volume_path = "/cookies/freelance.json"
                        os.makedirs(os.path.dirname(volume_path), exist_ok=True)
                        with open(volume_path, 'w') as f:
                            json.dump(data.get('cookies', []), f, indent=2)
                        logger.info(f"Cookie auch in {volume_path} gespeichert")
                        return True
                    else:
                        logger.error(f"Fehler beim Login: {response.text}")
                        return False
            except Exception as e:
                logger.error(f"Fehler bei HTTP-Anfrage an Playwright-Login: {e}")
                logger.info("Versuche direktes Ausführen des Node.js-Skripts...")
                return await execute_node_login_script()
        else:
            logger.info("Lokale Ausführung erkannt")
            return await execute_node_login_script()
    except Exception as e:
        logger.error(f"Fehler beim Login: {e}")
        return False

async def execute_node_login_script() -> bool:
    """Führt das Node.js-Login-Skript direkt aus"""
    try:
        logger.info("Starte Node.js-Login-Skript...")
        result = subprocess.run(['node', LOGIN_SCRIPT_PATH], 
                                cwd=os.path.dirname(__file__),
                                capture_output=True,
                                text=True)
        
        logger.info(f"Node.js-Skript Exit-Code: {result.returncode}")
        logger.info(f"Node.js-Skript Ausgabe: {result.stdout}")
        
        if result.returncode == 0:
            logger.info("Login-Skript erfolgreich ausgeführt")
            return True
        else:
            logger.error(f"Fehler beim Ausführen des Login-Skripts: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Fehler beim Ausführen des Node.js-Skripts: {e}")
        return False

async def fetch_page_with_cookies(url: str, username: str, password: str) -> Optional[str]:
    """Lädt eine Seite mit Cookies, holt sie ggf. mit Userdaten neu"""
    try:
        if not await check_cookies():
            if not await get_cookie_from_playwright_login(username, password):
                logger.error("Konnte keine Cookies erhalten.")
                return None
        
        # Cookies laden
        logger.info(f"Lade Cookies aus {COOKIE_PATH}")
        with open(COOKIE_PATH) as f:
            cookie_data = json.load(f)
        
        # Cookie-Header bauen
        cookies = {}
        for cookie in cookie_data:
            cookies[cookie['name']] = cookie['value']
        
        logger.info(f"Cookies geladen: {len(cookies)} Cookies")
        
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

def extract_project_id(url: str) -> str:
    """Extrahiert die Projekt-ID aus der URL"""
    match = re.search(r'projekt-(\d+)', url)
    if match:
        return match.group(1)
    return f"unknown-{slugify(url)}"

def extract_applications_info(text: str) -> Optional[int]:
    """Extrahiert die Anzahl der Bewerbungen aus dem Text"""
    if "Noch keine Bewerbungen" in text:
        return 0
    elif "Weniger als 5 Bewerbungen" in text:
        return 1  # Wir verwenden 1 als Annäherung für "weniger als 5"
    return None

def extract_json_from_html(html_content: str) -> List[Dict[str, Any]]:
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

def extract_project_data_from_json(project_json: Dict[str, Any]) -> Dict[str, Any]:
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
        
        # Enddatum extrahieren (verwenden wir Projektstart als Ersatz)
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
            'provider': PROVIDER
        }
    except Exception as e:
        logger.error(f"Fehler beim Extrahieren der Projektdaten aus JSON: {e}")
        return None

def extract_project_data(html_content: str) -> List[Dict[str, Any]]:
    """Extrahiert Projektdaten aus dem HTML"""
    try:
        # Versuche zuerst, die JSON-Daten zu extrahieren
        projects_json = extract_json_from_html(html_content)
        
        if projects_json:
            # Wenn JSON-Daten gefunden wurden, diese verarbeiten
            projects = []
            for project_json in projects_json:
                project_data = extract_project_data_from_json(project_json)
                if project_data:
                    projects.append(project_data)
            
            logger.info(f"{len(projects)} Projekte aus JSON extrahiert")
            return projects
        
        # Fallback: Alte Methode mit BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        project_items = soup.select('.project-item.online')
        logger.info(f"{len(project_items)} Projekte auf der Seite gefunden (mit HTML-Parser).")
        
        projects = []
        for item in project_items:
            try:
                # Link extrahieren
                link_element = item.select_one('h2.title a')
                if not link_element:
                    continue
                    
                link = link_element['href']
                full_url = urljoin(BASE_URL, link)
                
                # Projekt-ID extrahieren
                project_id = extract_project_id(link)
                
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
                
                projects.append({
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
                    'provider': PROVIDER
                })
            except Exception as e:
                logger.error(f"Fehler beim Extrahieren der Projektdaten: {e}")
                continue
        
        return projects
    except Exception as e:
        logger.error(f"Fehler bei der Extraktion von Projektdaten: {e}")
        return []

def get_pagination_info(html_content: str) -> Dict[str, Any]:
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
    pagination_items = soup.select('ngb-pagination li.page-item')
    if not pagination_items:
        return pagination_info
    
    # Aktuelle Seite finden
    for item in pagination_items:
        if "active" in item.get("class", []):
            try:
                pagination_info["current_page"] = int(item.select_one("a").text.strip())
                break
            except (ValueError, AttributeError):
                pass
    
    # Letzte Seite finden (vor dem "»" Element)
    for item in reversed(pagination_items):
        if item.select_one("a span") and "»" in item.select_one("a span").text:
            continue
        try:
            last_page = int(item.select_one("a").text.strip())
            pagination_info["total_pages"] = last_page
            break
        except (ValueError, AttributeError):
            pass
    
    # Prüfen, ob eine nächste Seite existiert
    pagination_info["has_next_page"] = pagination_info["current_page"] < pagination_info["total_pages"]
    if pagination_info["has_next_page"]:
        pagination_info["next_page"] = pagination_info["current_page"] + 1
    
    return pagination_info

def build_pagination_url(base_url: str, page: int, page_size: int = DEFAULT_PAGE_SIZE) -> str:
    """Baut eine URL für eine bestimmte Seite der Paginierung"""
    parsed_url = urlparse(base_url)
    query = parse_qs(parsed_url.query)
    
    # Neue Query-Parameter setzen
    query["page"] = [str(page)]
    query["pageSize"] = [str(page_size)]
    
    # URL neu zusammenbauen
    new_query = urlencode(query, doseq=True)
    parts = list(parsed_url)
    parts[4] = new_query  # index 4 ist der query part
    
    return urlunparse(parts)

async def get_existing_project_ids(conn, project_ids: list) -> set:
    """Gibt die Menge der bereits in der DB vorhandenen Projekt-IDs zurück."""
    if not project_ids:
        return set()
    rows = await conn.fetch(f"SELECT project_id FROM {DB_SCHEMA}.{DB_TABLE} WHERE project_id = ANY($1)", project_ids)
    return set(row['project_id'] for row in rows)

async def crawl_until_existing(user_id: int, max_pages: int = 10, page_size: int = 100, delay_seconds: float = 1.0, fetch_descriptions: bool = False, retry_count: int = 3):
    creds = await get_user_credentials(user_id)
    if not creds:
        logger.error(f"Keine gültigen Freelance-Credentials für user_id={user_id} gefunden. Abbruch.")
        return []
    username = creds["username"]
    password = creds["password"]
    base_url = creds["link_1"]
    all_projects = []
    all_new_ids = set()
    current_page = 1
    has_next_page = True
    conn = await get_db_connection()
    if not conn:
        logger.error("Konnte keine DB-Verbindung herstellen.")
        return []
    try:
        while has_next_page and current_page <= max_pages:
            url = build_pagination_url(base_url, current_page, page_size)
            logger.info(f"Crawle Seite {current_page} mit URL: {url}")
            for attempt in range(retry_count):
                try:
                    html_content = await fetch_page_with_cookies(url, username, password)
                    if html_content:
                        break
                except Exception as e:
                    logger.error(f"Fehler beim Laden von Seite {current_page} (Versuch {attempt+1}): {e}")
                    await asyncio.sleep(2)
            else:
                logger.error(f"Seite {current_page} konnte nach {retry_count} Versuchen nicht geladen werden.")
                break
            projects = extract_project_data(html_content)
            if not projects:
                logger.info(f"Keine Projekte mehr auf Seite {current_page} gefunden. Beende Crawling.")
                break
            ids = [p['project_id'] for p in projects]
            existing_ids = await get_existing_project_ids(conn, ids)
            new_projects = [p for p in projects if p['project_id'] not in existing_ids]
            all_projects.extend(new_projects)
            all_new_ids.update(p['project_id'] for p in new_projects)
            logger.info(f"{len(new_projects)} neue Projekte, {len(existing_ids)} bekannte IDs auf Seite {current_page}.")
            if existing_ids:
                logger.info("Bekannte Projekt-ID gefunden. Breche das Crawling ab.")
                break
            pagination = get_pagination_info(html_content)
            has_next_page = pagination["has_next_page"]
            current_page += 1
            await asyncio.sleep(delay_seconds)
        logger.info(f"Starte Detailseiten-Crawl für {len(all_new_ids)} neue Projekte...")
        for project in all_projects:
            if fetch_descriptions and project.get('url'):
                for attempt in range(retry_count):
                    try:
                        project['description'] = await fetch_project_description(project['url'])
                        break
                    except Exception as e:
                        logger.error(f"Fehler beim Laden der Detailseite {project['url']} (Versuch {attempt+1}): {e}")
                        await asyncio.sleep(2)
        return all_projects
    finally:
        await conn.close()
        logger.info("DB-Verbindung geschlossen.")

async def fetch_and_process_projects(user_id: int, max_pages: int = 5, page_size: int = DEFAULT_PAGE_SIZE) -> List[Dict[str, Any]]:
    return await crawl_until_existing(user_id, max_pages, page_size)

async def save_to_json(projects: List[Dict[str, Any]], filename: str = "freelance_projects.json"):
    """Speichert die Projekte als JSON für Tests"""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(projects, f, indent=2, ensure_ascii=False)
        logger.info(f"Projekte in {filename} gespeichert.")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Projekte: {e}")

async def get_user_credentials(user_id: int) -> Optional[dict]:
    """Holt die Freelance-Credentials für einen bestimmten User vom Backend."""
    credentials_url = f"{DJANGO_BACKEND_URL}/api/v1/freelance/credentials/{user_id}/"
    logger.info(f"Versuche, Credentials von {credentials_url} für User {user_id} abzurufen.")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(credentials_url)
            if response.status_code == 200:
                data = response.json()
                if data.get("username") and data.get("password") and data.get("link_1"):
                    return data
                else:
                    logger.error(f"Unvollständige Credentials für User {user_id}: {data}")
            else:
                logger.error(f"Fehler beim Abrufen der Credentials für User {user_id}: {response.status_code}")
    except Exception as e:
        logger.error(f"Fehler beim API-Call für Credentials: {e}")
    return None

if __name__ == "__main__":
    async def main():
        projects = await fetch_and_process_projects(1)
        if projects:
            await save_to_json(projects)
            logger.info(f"Insgesamt {len(projects)} Projekte verarbeitet.")
        else:
            logger.error("Keine Projekte gefunden oder Fehler beim Verarbeiten.")
            
    asyncio.run(main()) 