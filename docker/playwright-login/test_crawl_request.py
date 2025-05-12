import json
import httpx
import sys
from bs4 import BeautifulSoup

COOKIES_PATH = 'freelance_cookies.json'
DETAIL_URL = 'https://www.freelance.de/projekte/projekt-1158325-Ausbilder-m-w-d-fuer-den-Fachbereich-Asbest'
REFERER = 'https://www.freelance.de/projekte?city=19107&county=53&pageSize=100&page=1'


def load_cookies():
    with open(COOKIES_PATH) as f:
        data = json.load(f)
    # Playwright-Format: [{name, value, domain, ...}]
    return {c['name']: c['value'] for c in data['cookies'] if 'name' in c and 'value' in c}


def main():
    cookies = load_cookies()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'de,en-GB;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': REFERER,
    }
    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        resp = client.get(DETAIL_URL, cookies=cookies, headers=headers)
        print(f"Status: {resp.status_code}, URL: {resp.url}")
        if 'promotion/postlogin.php' in str(resp.url):
            print("[WARN] Promo-/Postlogin-Seite erhalten!")
            with open('promo_page_dump.html', 'w') as f:
                f.write(resp.text)
            print("HTML-Dump gespeichert: promo_page_dump.html")
            sys.exit(1)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            h1 = soup.find('h1')
            print(f"Erste Überschrift: {h1.text if h1 else 'N/A'}")
            print("[OK] Echte Detailseite geladen!")
        else:
            print(f"[ERROR] Status {resp.status_code}")
            sys.exit(2)

if __name__ == '__main__':
    main() 