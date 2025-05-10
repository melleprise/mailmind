# Funktionenübersicht Freelance-Crawler

Diese Datei dokumentiert alle Funktionen des Freelance-Testcrawlers (Stand: automatisch generiert).

## test_crawler.py
- `async def test_crawler(max_pages=1, page_size=100)`: Testet das Crawlen von Projekten (Standard: 1 Seite, 100 Projekte).

## test_detail_crawl.py
- `async def fetch_project_details_page(project_url: str) -> str`: Lädt HTML einer Projekt-Detailseite.
- `async def extract_project_details(html_content: str, project_id: str, provider: str) -> dict`: Extrahiert Detaildaten aus HTML.
- `async def get_db_connection()`: Stellt DB-Verbindung her.
- `async def create_tables_if_not_exist(conn)`: Erstellt Tabellen, falls nicht vorhanden.
- `async def save_project_to_db(conn, project: dict)`: Speichert Projekt in DB.
- `async def save_project_details_to_db(conn, details: dict)`: Speichert Detaildaten in DB.
- `async def test_project_and_detail_crawl()`: Testet kompletten Crawl inkl. Detailseiten.

## fetch_project_details.py
- Diverse Extraktionsmethoden (z.B. `extract_company_url`, `extract_logo_url`, ...): Extrahieren einzelne Felder aus HTML.
- `async def fetch_project_details_page(project_id: str, url: str = None) -> Optional[str]`: Lädt Detailseite.
- `async def get_db_connection()`, `async def create_details_table_if_not_exists(conn)`, `async def get_projects_without_details(conn, ...)`, `async def save_project_details(conn, details)`, `async def process_project_details(...)`, `async def process_projects_without_details(...)`, `async def process_with_semaphore(project)`, `async def main(...)`: Verschiedene DB- und Crawl-Operationen.

## test_project_scraper.py
- `async def test_detail_scrape(project_id: str = None, url: str = None)`: Testet Detailseiten-Scraping.
- `async def main()`: Einstiegspunkt.

## crawl_with_login.py
- `def freelance_cookies_valid()`: Prüft Cookies.
- `def run_freelance_login_script()`: Führt Login-Skript aus.
- `def crawl_with_login(url_to_crawl)`: Crawlt mit Login.
- `async def run()`: Async-Runner.

## test_overview_scrape.py
- `async def extract_project_from_card(project_card: BeautifulSoup)`: Extrahiert Projektdaten aus Card.
- `async def scrape_overview_page()`: Scraped Übersichtsseite.
- `async def main()`: Einstiegspunkt.

## fetch_and_process.py
- `def to_db_dict(self)`: Wandelt Daten in DB-Format um.
- `async def check_cookies()`, `async def get_cookie_from_playwright_login()`, `async def execute_node_login_script()`, `async def fetch_page_with_cookies(url)`: Cookie- und Fetch-Logik.
- `def extract_project_id(url)`, `def extract_applications_info(text)`, `def extract_json_from_html(html)`, `def extract_project_data_from_json(project_json)`, `def extract_project_data(html)`, `def get_pagination_info(html)`, `def build_pagination_url(...)`: Extraktions- und Hilfsfunktionen.
- `async def fetch_projects_with_pagination(...)`, `async def fetch_and_process_projects(...)`, `async def save_to_json(...)`, `async def main()`: Crawl- und Speicherlogik.

## test_one_page.py
- `def extract_json_from_html(html_content)`, `def extract_project_data_from_json(project_json)`, `async def extract_projects_from_page(html_content)`, `def extract_project_data(item)`: Extrahieren Projektdaten aus HTML/JSON.
- `async def get_db_connection()`, `async def process_projects_in_db(projects)`, `async def create_table_if_not_exists(conn)`: DB-Operationen.
- `async def test_one_page_crawl()`: Testet Crawl einer Seite.

## db_integration.py
- `async def get_db_connection()`, `async def create_table_if_not_exists(conn)`, `async def insert_or_update_projects(conn, projects)`: DB-Operationen.
- `async def main(max_pages=100, page_size=100)`: Hauptfunktion für DB-Integration.

## crawl_ten_projects.py
- `async def fetch_project_description(project_url)`: Holt Projektbeschreibung.
- `async def crawl_one_project()`: Crawlt ein Projekt.
- `async def main()`: Einstiegspunkt.

## test_detail_debug.py
- `async def debug_html_structure(html_content)`: Debuggt HTML-Struktur.
- `async def test_detail_scrape_debug()`: Testet Detail-Scraping mit Debug.
- `async def main()`: Einstiegspunkt.

## crawl_all_projects.py
- `async def fetch_project_description(project_url)`, `async def extract_project_from_card(project_card)`, `async def get_pagination_info(html_content)`, `async def build_pagination_url(...)`, `async def scrape_projects_page(url)`, `async def get_db_connection()`, `async def create_table_if_not_exists(conn)`, `async def save_projects_to_db(conn, projects)`: Verschiedene Crawl- und DB-Funktionen.
- `async def crawl_all_projects(...)`: Crawlt alle Projekte.
- `async def save_to_json(projects, filename)`: Speichert als JSON.
- `async def main()`: Einstiegspunkt.

## test_detail_scrape.py
- `async def test_detail_scrape()`: Testet Detailseiten-Scraping.
- `async def main()`: Einstiegspunkt.

## crawl_all_pages.py
- `async def fetch_page(url)`, `def build_page_url(page)`, `async def extract_projects_from_page(html_content)`, `async def get_total_pages(html_content)`, `async def get_db_connection()`, `async def create_table_if_not_exists(conn)`, `async def insert_or_update_projects(conn, projects)`, `async def process_page(html_content, page_number)`: Crawl- und DB-Funktionen.
- `async def crawl_all_pages()`: Crawlt alle Seiten.

## crawl_until_existing.py
- `async def get_existing_project_ids(conn, project_ids: list) -> set`: Prüft, welche Projekt-IDs bereits in der DB existieren.
- `async def crawl_until_existing(...)`: Crawlt Seiten, bis eine bekannte Projekt-ID gefunden wird, dann Detailseiten für neue IDs. 