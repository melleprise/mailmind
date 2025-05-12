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
# from slugify import slugify
import subprocess
import asyncpg
import argparse

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

async def get_db_connection():
    """Stellt eine Verbindung zur PostgreSQL-Datenbank her."""
    try:
        conn = await asyncpg.connect(
            user=os.environ.get('PG_USER', 'mailmind'),
            password=os.environ.get('PG_PASSWORD', 'mailmind'),
            database=os.environ.get('PG_DB', 'mailmind'),
            host=os.environ.get('PG_HOST', 'postgres')
        )
        logger.info("Erfolgreich mit der Datenbank verbunden.")
        return conn
    except Exception as e:
        logger.error(f"Fehler beim Verbinden mit der Datenbank: {e}", exc_info=True)
        return None

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
    application_status: Optional[str] = None
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
            "application_status": self.application_status,
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

async def get_cookie_from_playwright_login(user_id: int) -> bool:
    """Holt einen neuen Cookie vom Playwright-Login-Service anhand der User-ID"""
    try:
        logger.info(f"Hole neuen Cookie vom Playwright-Login-Service für User-ID: {user_id}...")
        
        playwright_login_service_url = f"{PLAYWRIGHT_LOGIN_URL}-by-user-id"
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.info(f"Sende Anfrage an {playwright_login_service_url} für User-ID {user_id}")
            response = await client.post(
                playwright_login_service_url,
                json={"user_id": user_id}
            )
            logger.info(f"Response Status vom Playwright-Login-Service: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                if data.get('success', False) and data.get('cookies'):
                    logger.info("Erfolgreiche Antwort und Cookies vom Login-Service erhalten")
                    # Cookies lokal speichern (primärer Speicherort)
                    with open(COOKIE_PATH, 'w') as f:
                        json.dump(data.get('cookies', []), f, indent=2)
                    logger.info(f"Cookie in {COOKIE_PATH} gespeichert")
                    
                    # Versuche, auch ins Volume zu schreiben, aber fange Fehler ab
                    volume_path = "/cookies/freelance.json"
                    try:
                        os.makedirs(os.path.dirname(volume_path), exist_ok=True)
                        with open(volume_path, 'w') as f:
                            json.dump(data.get('cookies', []), f, indent=2)
                        logger.info(f"Cookie auch in {volume_path} gespeichert")
                    except PermissionError as pe:
                        logger.error(f"PermissionError beim Schreiben des Cookies nach {volume_path}: {pe}. Der lokale Cookie unter {COOKIE_PATH} wurde jedoch gespeichert.")
                        # Da der lokale Cookie gespeichert wurde, betrachten wir dies nicht als fatalen Fehler für diese Funktion.
                    except Exception as e_vol:
                        logger.error(f"Anderer Fehler beim Schreiben des Cookies nach {volume_path}: {e_vol}. Der lokale Cookie unter {COOKIE_PATH} wurde jedoch gespeichert.")
                    
                    return True # Erfolg, da der lokale Cookie geschrieben wurde
                else:
                    logger.error(f"Login-Service meldete Fehler oder keine Cookies: {data.get('error', 'Keine Details')}")
                    return False
            else:
                logger.error(f"Fehlerhafte Antwort vom Playwright-Login-Service: {response.status_code} - {response.text}")
                return False
    except Exception as e:
        logger.error(f"Genereller Fehler beim Versuch, Cookie via User-ID vom Playwright-Login-Service zu holen: {e}", exc_info=True)
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

async def fetch_page_with_cookies(url: str, user_id: int, specific_referer: Optional[str] = None) -> Optional[str]:
    """Lädt eine Seite mit Cookies, holt sie ggf. mit Userdaten neu"""
    try:
        if not await check_cookies():
            if not await get_cookie_from_playwright_login(user_id):
                logger.error(f"Konnte keine Cookies für User {user_id} erhalten. Abbruch für URL: {url}")
                return None
        logger.info(f"Lade Cookies aus {COOKIE_PATH} für URL: {url}")
        with open(COOKIE_PATH) as f:
            cookie_data = json.load(f)
        # Logge alle Cookies ausführlich
        for c in cookie_data:
            logger.info(f"Cookie: {c['name']}={str(c['value'])[:8]}... Domain={c.get('domain','')}, Expires={c.get('expires','')} ")
        cookies = {cookie['name']: cookie['value'] for cookie in cookie_data}
        logger.info(f"Cookies für {url} geladen: {len(cookies)} Cookies")
        # Bestimme den Referer
        actual_referer = None
        if specific_referer:
            actual_referer = specific_referer
            logger.info(f"Verwende spezifischen Referer: {actual_referer} für Anfrage an {url}")
        elif "/projekt-" in url: # Nur für Detailseiten einen Fallback-Referer setzen
            creds = await get_user_credentials(user_id)
            if creds and creds.get("link"):
                actual_referer = creds.get("link") # link ist die Projektübersichtsseite mit Parametern
                logger.info(f"Verwende link als Fallback-Referer: {actual_referer} für Anfrage an {url}")
            else:
                # Fallback auf statischen Referer, wenn link nicht verfügbar
                actual_referer = f"{BASE_URL}/projekte"
                logger.info(f"Verwende statischen Fallback-Referer: {actual_referer} für Anfrage an {url}")
        else:
            logger.info(f"Kein spezifischer Referer für URL {url} gesetzt (keine Detailseite oder kein spezifischer Referer übergeben).")
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'de,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
                'Sec-CH-UA': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"',
                'Sec-CH-UA-Mobile': '?0',
                'Sec-CH-UA-Platform': '"macOS"',
            }
            if actual_referer:
                 headers['Referer'] = actual_referer
            request_to_log = client.build_request("GET", url, cookies=cookies, headers=headers)
            logger.info(f"Vorbereitete Anfrage-Header für {url}: {request_to_log.headers}")
            response = await client.get(url, cookies=cookies, headers=headers)
            # Logge Response-Header und Set-Cookie
            logger.info(f"Response-Status: {response.status_code} für {url}")
            logger.info(f"Response-Header für {url}: {dict(response.headers)}")
            set_cookie_headers = response.headers.get_list('set-cookie') if hasattr(response.headers, 'get_list') else response.headers.get('set-cookie')
            if set_cookie_headers:
                logger.info(f"Set-Cookie-Header für {url}: {set_cookie_headers}")
            final_url_after_redirects = str(response.url)
            if url != final_url_after_redirects:
                logger.info(f"Ursprüngliche URL: {url}, Finale URL nach Redirects: {final_url_after_redirects}")
            else:
                logger.info(f"Keine Redirects. Finale URL: {final_url_after_redirects}")
            if response.status_code == 200:
                if "promotion/postlogin.php" in final_url_after_redirects or "login.php" in final_url_after_redirects:
                    logger.warning(f"Obwohl Status 200, scheint die finale URL ({final_url_after_redirects}) eine Login/Promo-Seite zu sein. Inhalt wird als ungültig betrachtet.")
                    logger.info(f"HTML-Anfang der unerwünschten Seite: {response.text[:500]}")
                    return None
                logger.info(f"Seite {url} (final: {final_url_after_redirects}) erfolgreich geladen. Content-Length: {len(response.text)}")
                return response.text
            else:
                logger.error(f"Fehler beim Laden der Seite {url} (final: {final_url_after_redirects}): {response.status_code}")
                logger.error(f"Response Text (Auszug): {response.text[:500]}")
                return None
    except Exception as e:
        logger.error(f"Fehler beim Laden der Seite {url}: {e}")
        return None

def extract_project_id(url: str) -> str:
    """Extrahiert die Projekt-ID aus der URL"""
    return f"unknown-{url.replace('/', '_')}"

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

async def save_projects_to_db(conn, projects: List[FreelanceProject]):
    """Speichert eine Liste von FreelanceProject-Objekten in der Datenbank."""
    if not projects:
        logger.info("Keine Projekte zum Speichern in der DB vorhanden.")
        return

    insert_query = f"""
        INSERT INTO {DB_SCHEMA}.{DB_TABLE} (
            project_id, title, company, end_date, location, remote,
            last_updated, skills, url, applications, description, application_status, provider, created_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
        )
        ON CONFLICT (project_id) DO UPDATE SET
            title = EXCLUDED.title,
            company = EXCLUDED.company,
            end_date = EXCLUDED.end_date,
            location = EXCLUDED.location,
            remote = EXCLUDED.remote,
            last_updated = EXCLUDED.last_updated,
            skills = EXCLUDED.skills,
            url = EXCLUDED.url,
            applications = EXCLUDED.applications,
            description = EXCLUDED.description,
            application_status = EXCLUDED.application_status,
            provider = EXCLUDED.provider,
            created_at = EXCLUDED.created_at;
    """
    try:
        # Konvertiere Projektobjekte in Tupel von Werten für den Batch-Insert
        records_to_insert = []
        for project in projects:
            p_dict = project.to_db_dict()
            records_to_insert.append((
                p_dict['project_id'], p_dict['title'], p_dict['company'], p_dict['end_date'],
                p_dict['location'], p_dict['remote'], p_dict['last_updated'], 
                json.dumps(p_dict['skills']) if p_dict['skills'] else None, # Skills als JSON String Array
                p_dict['url'], p_dict['applications'], p_dict['description'], p_dict['application_status'], p_dict['provider'],
                datetime.fromisoformat(p_dict['created_at']) # created_at als datetime-Objekt
            ))

        await conn.executemany(insert_query, records_to_insert)
        logger.info(f"{len(projects)} Projekte erfolgreich in die Datenbank gespeichert/aktualisiert.")
    except Exception as e:
        logger.error(f"Fehler beim Speichern der Projekte in die Datenbank: {e}", exc_info=True)

async def fetch_protected_page_via_playwright(url: str, user_id: int) -> Optional[str]:
    """Holt eine geschützte Seite über den Playwright-Login-Service (Browser-Kontext)."""
    try:
        playwright_url = "http://playwright-login:3000/fetch-protected-page"
        logger.info(f"[DEBUG] Sende POST an {playwright_url} mit url={url} und user_id={user_id}")
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(playwright_url, json={"user_id": user_id, "url": url})
            logger.info(f"[DEBUG] Response Status: {resp.status_code}, Content-Type: {resp.headers.get('content-type')}, Body (Anfang): {resp.text[:300]}")
            if resp.status_code == 200 and resp.json().get("success"):
                logger.info(f"[DEBUG] Playwright-Response success=true, HTML-Länge: {len(resp.json().get('html',''))}")
                # HTML-Dump speichern
                try:
                    import os
                    dump_path = os.path.join(os.path.dirname(__file__), 'detail_dump.html')
                    with open(dump_path, 'w') as dumpfile:
                        dumpfile.write(resp.json().get('html',''))
                    logger.info(f"[DUMP-DEBUG] Dump erfolgreich geschrieben: {dump_path}")
                except Exception as dump_exc:
                    logger.error(f"[DUMP-DEBUG] Fehler beim Schreiben des Dumps: {dump_exc}")
                return resp.json().get("html")
            else:
                logger.error(f"Fehler beim Abruf via Playwright-Login-Service: {resp.text}")
                return None
    except Exception as e:
        logger.error(f"Exception beim Abruf via Playwright-Login-Service: {e}")
        return None

async def fetch_project_description(project_url: str, user_id: int, PaginierungsReferrer: Optional[str] = None) -> str:
    """Lädt die Detailseite eines Projekts und extrahiert die Beschreibung."""
    try:
        html = await fetch_protected_page_via_playwright(project_url, user_id)
        if not html:
            logger.warning(f"Konnte HTML-Inhalt für {project_url} nicht laden (Playwright-Bypass).")
            return ""
        soup = BeautifulSoup(html, 'html.parser')
        description = ""
        # NEU: Bewerbungsstatus extrahieren
        if soup.find(id="marker_application_sent"):
            application_status = soup.find(id="marker_application_sent").get_text(separator=' ', strip=True)
        else:
            status_panel = soup.find('div', class_='panel-body')
            application_status = None
            if status_panel and 'highlight-text' not in status_panel.get('class', []):
                status_text = status_panel.get_text(separator='\n', strip=True)
                if re.search(r'beworben|Sie haben sich am|Bewerbung am|Bewerbungsdatum', status_text, re.IGNORECASE):
                    application_status = status_text
                else:
                    application_status = None
        desc_panel = soup.find('div', class_='panel-body highlight-text')
        if desc_panel:
            description = desc_panel.get_text(separator='\n', strip=True)
        else:
            desc = soup.find('div', class_='project-description')
            description = desc.text.strip() if desc else ""
        return description
    except Exception as e:
        logger.error(f"Fehler beim Laden der Projektbeschreibung für {project_url}: {e}")
        return ""

async def crawl_until_existing(user_id: int, max_pages: int = 10, page_size: int = 100, delay_seconds: float = 1.0, fetch_descriptions: bool = False, retry_count: int = 3):
    conn = await get_db_connection()
    if not conn:
        logger.error("Konnte keine DB-Verbindung herstellen.")
        return []
    try:
        creds = await get_user_credentials(user_id)
        if not creds:
            logger.error(f"Keine gültigen Basis-Credentials (URL etc.) für user_id={user_id} gefunden. Abbruch.")
            return []
        projects_base_url = creds.get("link")
        if not projects_base_url:
            logger.error(f"Keine projects_base_url (link) in den Credentials für user_id={user_id} gefunden. Abbruch.")
            return []
        all_projects = []
        all_new_ids = set()
        # --- Pagination-Logik wie in der Doku: ---
        # 1. Erste Seite laden
        first_overview_url = build_pagination_url(projects_base_url, 1, page_size)
        logger.info(f"Lade erste Übersichtsseite: {first_overview_url}")
        first_html = None
        try:
            first_html = await fetch_protected_page_via_playwright(first_overview_url, user_id)
        except Exception as e:
            logger.error(f"Fehler beim Laden der ersten Übersichtsseite: {e}")
        if not first_html:
            logger.error("Konnte erste Übersichtsseite nicht laden. Abbruch.")
            return []
        pagination = get_pagination_info(first_html)
        total_pages = min(pagination.get('total_pages', 1), max_pages)
        logger.info(f"Gefundene Seitenanzahl: {total_pages}")
        # 2. Alle echten Seiten-URLs bauen
        overview_urls = [build_pagination_url(projects_base_url, p, page_size) for p in range(1, total_pages+1)]
        session_html_map = {overview_urls[0]: first_html}
        # 3. Restliche Seiten in einer Session laden
        if fetch_descriptions and len(overview_urls) > 1:
            try:
                playwright_url = "http://playwright-login:3000/crawl-session"
                logger.info(f"[SESSION] Sende {len(overview_urls)-1} weitere Übersichtsseiten an Playwright-Login-Service...")
                async with httpx.AsyncClient(timeout=300.0) as client:
                    resp = await client.post(playwright_url, json={"user_id": user_id, "overview_urls": overview_urls[1:], "detail_urls": []})
                    if resp.status_code == 200 and resp.json().get("success"):
                        for entry in resp.json()["overview_results"]:
                            if entry.get("success"):
                                session_html_map[entry["url"]] = entry["html"]
                            else:
                                logger.error(f"[SESSION] Fehler für {entry.get('url')}: {entry.get('error')}")
                    else:
                        logger.error(f"[SESSION] Fehlerhafte Antwort vom Playwright-Login-Service: {resp.text}")
            except Exception as e:
                logger.error(f"[SESSION] Exception beim Session-Request: {e}")
        # --- NEU: Projektdaten aus den geladenen HTMLs extrahieren ---
        for url in overview_urls:
            html_content_for_page = session_html_map.get(url)
            if not html_content_for_page:
                continue
            projects_on_this_page = extract_project_data(html_content_for_page)
            if not projects_on_this_page:
                continue
            ids_on_this_page = [p['project_id'] for p in projects_on_this_page]
            existing_ids_on_this_page = await get_existing_project_ids(conn, ids_on_this_page)
            new_projects_from_this_page = []
            for p in projects_on_this_page:
                if p['project_id'] not in existing_ids_on_this_page:
                    p['_source_page_url'] = url
                    new_projects_from_this_page.append(p)
            all_projects.extend(new_projects_from_this_page)
            all_new_ids.update(p['project_id'] for p in new_projects_from_this_page)
        logger.info(f"Starte Detailseiten-Crawl für {len(all_projects)} potenziell neue Projekte...")
        projects_to_fetch_details_for = [p for p in all_projects if '_source_page_url' in p]
        # --- Detailseiten-Session-Request ---
        detail_urls = [p['url'] for p in all_projects if p.get('url')]
        session_html_map = {}
        if fetch_descriptions and detail_urls:
            try:
                playwright_url = "http://playwright-login:3000/crawl-session"
                logger.info(f"[SESSION] Sende {len(detail_urls)} Detailseiten an Playwright-Login-Service...")
                async with httpx.AsyncClient(timeout=300.0) as client:
                    resp = await client.post(playwright_url, json={"user_id": user_id, "overview_urls": [], "detail_urls": detail_urls})
                    if resp.status_code == 200 and resp.json().get("success"):
                        for entry in resp.json()["detail_results"]:
                            if entry.get("success"):
                                session_html_map[entry["url"]] = entry["html"]
                            else:
                                logger.error(f"[SESSION] Fehler für {entry.get('url')}: {entry.get('error')}")
                    else:
                        logger.error(f"[SESSION] Fehlerhafte Antwort vom Playwright-Login-Service: {resp.text}")
            except Exception as e:
                logger.error(f"[SESSION] Exception beim Session-Request: {e}")
        final_projects_for_db = []
        for project_dict in projects_to_fetch_details_for:
            if fetch_descriptions and project_dict.get('url'):
                html = session_html_map.get(project_dict['url'])
                if html:
                    soup = BeautifulSoup(html, 'html.parser')
                    description = ""
                    # NEU: Bewerbungsstatus extrahieren
                    if soup.find(id="marker_application_sent"):
                        application_status = soup.find(id="marker_application_sent").get_text(separator=' ', strip=True)
                    else:
                        status_panel = soup.find('div', class_='panel-body')
                        application_status = None
                        if status_panel and 'highlight-text' not in status_panel.get('class', []):
                            status_text = status_panel.get_text(separator='\n', strip=True)
                            if re.search(r'beworben|Sie haben sich am|Bewerbung am|Bewerbungsdatum', status_text, re.IGNORECASE):
                                application_status = status_text
                            else:
                                application_status = None
                    desc_panel = soup.find('div', class_='panel-body highlight-text')
                    if desc_panel:
                        description = desc_panel.get_text(separator='\n', strip=True)
                    else:
                        desc = soup.find('div', class_='project-description')
                        description = desc.text.strip() if desc else ""
                    project_dict['application_status'] = application_status
                else:
                    description = ""
                    project_dict['application_status'] = None
                project_dict['description'] = description
            project_dict.pop('_source_page_url', None)
            try:
                logger.info(f"[DEBUG] Projekt {project_dict.get('project_id')} Beschreibung: {project_dict.get('description')}")
                final_projects_for_db.append(FreelanceProject(**project_dict))
            except Exception as e:
                logger.error(f"Fehler beim Erstellen des FreelanceProject-Objekts für {project_dict.get('project_id')}: {e} - Daten: {project_dict}")
        if final_projects_for_db:
            await save_projects_to_db(conn, final_projects_for_db)
        else:
            logger.info("Keine neuen Projekte zum Speichern in der DB nach Detailabruf.")
        return [p.model_dump() for p in final_projects_for_db]
    finally:
        await conn.close()
        logger.info("DB-Verbindung geschlossen.")

async def fetch_and_process_projects(user_id: int, max_pages: int = 5, page_size: int = DEFAULT_PAGE_SIZE, fetch_descriptions: bool = False) -> List[Dict[str, Any]]:
    return await crawl_until_existing(user_id, max_pages, page_size, fetch_descriptions=fetch_descriptions)

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
    # Dieser Endpunkt liefert jetzt Username, verschlüsseltes Passwort (optional), URLs
    credentials_url = f"{DJANGO_BACKEND_URL}/api/v1/freelance/credentials/{user_id}/"
    logger.info(f"Versuche, Basis-Credentials von {credentials_url} für User {user_id} abzurufen.")
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(credentials_url)
            if response.status_code == 200:
                data = response.json()
                # Die Prüfung auf 'password' wird hier entfernt, da es nicht mehr direkt benötigt/erwartet wird.
                # Playwright-Login-Service holt es sich oder bekommt es entschlüsselt.
                if data.get("username") and data.get("link"): 
                    safe_data = {key: value for key, value in data.items() if key != 'password'}
                    logger.info(f"Basis-Credentials für User {user_id} erfolgreich abgerufen: {safe_data}") # Log ohne PW
                    return data
                else:
                    logger.error(f"Unvollständige Basis-Credentials für User {user_id} (username oder link fehlt): {data}")
            else:
                logger.error(f"Fehler beim Abrufen der Basis-Credentials für User {user_id}: {response.status_code}")
    except Exception as e:
        logger.error(f"Fehler beim API-Call für Basis-Credentials: {e}")
    return None

async def import_single_project_by_url(user_id: int, project_url: str):
    """Importiert ein einzelnes Projekt anhand der URL in die Datenbank."""
    conn = await get_db_connection()
    if not conn:
        logger.error("Konnte keine DB-Verbindung herstellen.")
        return
    try:
        # Lade die Projektseite
        html_content = await fetch_protected_page_via_playwright(project_url, user_id)
        if not html_content:
            logger.error(f"Konnte HTML-Inhalt für {project_url} nicht laden.")
            return
        # Extrahiere Projektdaten
        projects = extract_project_data(html_content)
        if not projects:
            logger.error(f"Konnte keine Projektdaten aus {project_url} extrahieren.")
            return
        project = projects[0]  # Es sollte nur ein Projekt auf der Detailseite sein
        # Hole die Beschreibung
        description = await fetch_project_description(project_url, user_id)
        project['description'] = description
        # Speichere in die DB
        from datetime import datetime
        from pydantic import ValidationError
        try:
            project_obj = FreelanceProject(**project, created_at=datetime.now().isoformat())
        except ValidationError as e:
            logger.error(f"Fehler beim Erstellen des FreelanceProject-Objekts: {e}")
            return
        await save_projects_to_db(conn, [project_obj])
        logger.info(f"Projekt {project_obj.project_id} erfolgreich importiert und gespeichert.")
    finally:
        await conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--import-project", type=str, help="Projekt-URL, die importiert werden soll")
    parser.add_argument("--user-id", type=int, default=2, help="User-ID für die Credentials")
    args = parser.parse_args()
    
    if args.import_project:
        asyncio.run(import_single_project_by_url(args.user_id, args.import_project))
    else:
        asyncio.run(main()) 