#!/usr/bin/env python3
"""
Test-Skript für den Freelance-Crawler
"""
import asyncio
import json
import os
import sys
import argparse
from datetime import datetime

# Pfad zum providers-Verzeichnis hinzufügen
current_dir = os.path.dirname(os.path.abspath(__file__))
providers_dir = os.path.dirname(current_dir)
if providers_dir not in sys.path:
    sys.path.insert(0, providers_dir)

# Import aus dem freelance-Verzeichnis
from freelance.fetch_and_process import crawl_until_existing, save_to_json

async def test_crawler(user_id=1, max_pages=5, page_size=100):
    """
    Führt einen Test-Crawl mit den angegebenen Pagination-Parametern durch
    
    Args:
        user_id: User-ID für die Credentials
        max_pages: Maximale Anzahl der zu crawlenden Seiten (Standard: 5)
        page_size: Anzahl der Projekte pro Seite (Standard: 100)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"freelance_projects_{timestamp}.json"
    
    print(f"Starte Test-Crawl von freelance.de/projekte (user_id={user_id}, max_pages={max_pages}, page_size={page_size})...")
    
    # Projekte abrufen und verarbeiten
    projects = await crawl_until_existing(user_id, max_pages, page_size, fetch_descriptions=True)
    
    if not projects:
        print("Keine neuen Projekte gefunden.")
        return False
    
    # Speichere Ergebnisse als JSON
    await save_to_json(projects, output_file)
    
    print(f"Test abgeschlossen. {len(projects)} neue Projekte wurden in {output_file} gespeichert.")
    
    # Zeige ein paar Beispiel-Projekte
    if projects:
        print("\nBeispiel-Projekte:")
        for i, project in enumerate(projects[:3], 1):
            print(f"\n--- Projekt {i} ---")
            print(f"ID: {project['project_id']}")
            print(f"Titel: {project['title']}")
            print(f"Firma: {project['company']}")
            print(f"Skills: {', '.join(project['skills'])}")
            print(f"URL: {project['url']}")
    
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test des Freelance Crawlers")
    parser.add_argument("--user-id", type=int, default=1, help="User-ID für die Credentials (Standard: 1)")
    parser.add_argument("--max-pages", type=int, default=5, help="Maximale Anzahl der zu crawlenden Seiten (Standard: 5)")
    parser.add_argument("--page-size", type=int, default=100, help="Anzahl der Projekte pro Seite (Standard: 100)")
    args = parser.parse_args()
    
    # Führe den Test asynchron aus
    result = asyncio.run(test_crawler(args.user_id, args.max_pages, args.page_size))
    
    # Exit-Code basierend auf Erfolg/Misserfolg
    sys.exit(0 if result else 1) 