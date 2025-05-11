# server.py
# Minimales Skript zum Starten der Crawl4AI FastAPI App mit Uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # CORS importiert
import uvicorn

# Importiere den Router aus api_key_updater.py
# Stelle sicher, dass der sys.path so angepasst ist, dass dieser Import funktioniert.
# Da server.py und api_key_updater.py im selben Verzeichnis im Container liegen (/app/crawl4ai/ bzw. /app/server.py)
# und __init__.py in crawl4ai vorhanden ist, sollte der direkte Import funktionieren, wenn Uvicorn aus /app gestartet wird.
# Wenn server.py in /app liegt und api_key_updater in /app/crawl4ai, dann:
# from crawl4ai.api_key_updater import router as api_updater_router # Alter Import

print("CUSTOM SERVER.PY: Wird diese Zeile erreicht? START")

app = FastAPI(title="Custom Crawl4AI Wrapper")

print("CUSTOM SERVER.PY: FastAPI Instanz erstellt.")

# CORS Middleware hinzufügen
origins = [
    "http://localhost:8080",      # Frontend-Entwicklungsserver
    "http://localhost",           # Allgemeine localhost-Anfragen
    "http://127.0.0.1:8080",      # Alternative für Frontend
    "http://127.0.0.1",           # Allgemeine 127.0.0.1 Anfragen
    # Füge hier bei Bedarf weitere Origins hinzu (z.B. Produktions-URL)
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Erlaube alle Methoden (GET, POST, etc.)
    allow_headers=["*"],  # Erlaube alle Header
)
print("CUSTOM SERVER.PY: CORS Middleware hinzugefügt.")


# Binde den Router aus api_key_updater.py ein
try:
    # Neuer Importpfad-Versuch, falls der obige nicht geht, wenn Uvicorn anders startet:
    # Gegeben sei: server.py ist /app/server.py, api_key_updater.py ist /app/crawl4ai/api_key_updater.py
    # Der PYTHONPATH im Container sollte /app enthalten.
    from crawl4ai.api_key_updater import router as api_updater_router
    app.include_router(api_updater_router)
    print("CUSTOM SERVER.PY: api_updater_router ERFOLGREICH eingebunden.")
except ImportError as e_import:
    print(f"CUSTOM SERVER.PY: Fehler beim IMPORTIEREN von api_updater_router: {e_import}")
except Exception as e_general:
    print(f"CUSTOM SERVER.PY: ALLGEMEINER Fehler beim Einbinden von api_updater_router: {e_general}")


@app.get("/test-route")
async def read_test_route():
    print("CUSTOM SERVER.PY: /test-route aufgerufen")
    return {"message": "Test route is working!"}

@app.get("/health") # Wichtig für den Docker Healthcheck
async def health_check():
    # print("CUSTOM SERVER.PY: /health aufgerufen")
    return {"status": "healthy"}

print("CUSTOM SERVER.PY: Routen /test-route und /health definiert.")


# Das Mounten der originalen App lassen wir vorerst auskommentiert,
# um die Basisfunktionalität zu testen.
# try:
#     from crawl4ai.main import app as crawl4ai_original_app
#     app.mount("/crawl4ai-original", crawl4ai_original_app)
#     print("CUSTOM SERVER.PY: Original crawl4ai app gemountet unter /crawl4ai-original")
# except ImportError as e:
#     print(f"CUSTOM SERVER.PY: Original crawl4ai app konnte nicht importiert werden: {e}")


if __name__ == "__main__":
    print("CUSTOM SERVER.PY: Starte Uvicorn für lokale Entwicklung (nicht im Docker)...")
    # Dieser Teil wird nur ausgeführt, wenn server.py direkt gestartet wird,
    # nicht wenn Uvicorn die 'app' Instanz lädt (wie im Docker CMD)
    uvicorn.run("server:app", host="0.0.0.0", port=11235, reload=True)

print("CUSTOM SERVER.PY: Wird diese Zeile erreicht? ENDE") 