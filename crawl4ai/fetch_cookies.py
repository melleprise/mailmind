import json
import requests

def fetch_and_save():
    resp = requests.post('http://playwright-login:3000/login', json={
        "username": "DEIN_USER",
        "password": "DEIN_PASS"
    })
    resp.raise_for_status()
    cookies = resp.json()['cookies']
    with open('/cookies/freelance.json', 'w') as f:
        json.dump(cookies, f)

if __name__ == "__main__":
    fetch_and_save() 