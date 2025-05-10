import subprocess
import json
import time
import os
import sys
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig

COOKIE_PATH = os.path.join(os.path.dirname(__file__), 'freelance_cookies.json')
LOGIN_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), 'login.js')

# Prüft, ob ein gültiger freelance.de-Cookie existiert
def freelance_cookies_valid():
    try:
        with open(COOKIE_PATH) as f:
            cookies = json.load(f)
        now = time.time()
        for c in cookies:
            if c.get('domain', '').endswith('freelance.de') and c.get('expires', now+1) > now:
                return True
        return False
    except Exception:
        return False

# Führt das Login-Skript aus
def run_freelance_login_script():
    print("Führe Login-Skript aus...")
    try:
        # login.js direkt mit node ausführen
        subprocess.run(['node', LOGIN_SCRIPT_PATH], check=True, cwd=os.path.dirname(__file__))
        print("Login-Skript erfolgreich ausgeführt.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Fehler beim Ausführen des Login-Skripts: {e}")
        return False
    except FileNotFoundError:
        print(f"Fehler: Node.js oder das Login-Skript nicht gefunden. Stelle sicher, dass Node.js installiert ist und das Skript unter {LOGIN_SCRIPT_PATH} existiert.")
        return False

# Crawlt die gegebene URL mit freelance.de Logins
def crawl_with_login(url_to_crawl):
    if not freelance_cookies_valid():
        if not run_freelance_login_script():
            print("Login fehlgeschlagen, breche Crawl ab.")
            return
    else:
        print("Gültiger Cookie gefunden.")

    async def run():
        print(f"Starte Crawl für {url_to_crawl}")
        # BrowserConfig ohne executable_path
        browser_config = BrowserConfig(
            browser_type="chromium",
            headless=True
            # executable_path hier entfernt
        )
        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url_to_crawl)
            print(f"Crawl-Ergebnis für {url_to_crawl}:")
            if result:
                print(f"  URL: {result.url}")
                print(f"  Status: {result.status_code}")
            else:
                print("  Kein Ergebnis erhalten.")

    asyncio.run(run())

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Bitte eine URL zum Crawlen angeben.")
        sys.exit(1)
    crawl_with_login(sys.argv[1]) 