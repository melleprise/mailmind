#!/usr/bin/env python3
"""
Datenbank-Integration für Freelance-Projekte
"""
import os
import sys
import asyncio
import logging
import asyncpg
import json
import argparse
from typing import List, Dict, Any, Optional

# Konfiguration
DB_USER = os.environ.get("DB_USER", "mailmind")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "mailmind")
DB_HOST = os.environ.get("DB_HOST", "postgres")
DB_PORT = os.environ.get("DB_PORT", "5432")
DB_NAME = os.environ.get("DB_NAME", "mailmind")
DB_SCHEMA = "public"
DB_TABLE = "freelance_projects"
DEFAULT_PAGE_SIZE = 100  # Standardwert für pageSize

# Logging konfigurieren
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Pfad zum providers-Verzeichnis hinzufügen
current_dir = os.path.dirname(os.path.abspath(__file__))
providers_dir = os.path.dirname(current_dir)
if providers_dir not in sys.path:
    sys.path.insert(0, providers_dir)

# Import aus dem freelance-Verzeichnis
from freelance.fetch_and_process import crawl_until_existing

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

async def create_table_if_not_exists(conn):
    """Erstellt die Projekttabelle, falls sie nicht existiert"""
    try:
        await conn.execute(f'''
        CREATE TABLE IF NOT EXISTS {DB_TABLE} (
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
        logger.info(f"Tabelle {DB_TABLE} überprüft/erstellt.")
        return True
    except Exception as e:
        logger.error(f"Fehler beim Erstellen der Tabelle: {e}")
        return False

async def insert_or_update_projects(conn, projects: List[Dict[str, Any]]):
    """Fügt Projekte in die Datenbank ein oder aktualisiert sie"""
    if not projects:
        logger.info("Keine Projekte zum Einfügen.")
        return 0
    
    try:
        # Transaktionsbasierte Verarbeitung
        inserted = 0
        updated = 0
        
        async with conn.transaction():
            for project in projects:
                # Prüfe, ob das Projekt bereits existiert
                exists = await conn.fetchval('''
                SELECT COUNT(*) FROM {} 
                WHERE project_id = $1 AND provider = $2
                '''.format(DB_TABLE), project['project_id'], project['provider'])
                
                if exists:
                    # Aktualisiere das bestehende Projekt
                    await conn.execute('''
                    UPDATE {} SET 
                        title = $1,
                        company = $2,
                        end_date = $3,
                        location = $4,
                        remote = $5,
                        last_updated = $6,
                        skills = $7,
                        url = $8,
                        applications = $9,
                        description = $10
                    WHERE project_id = $11 AND provider = $12
                    '''.format(DB_TABLE),
                    project['title'],
                    project['company'],
                    project['end_date'],
                    project['location'],
                    project['remote'],
                    project['last_updated'],
                    json.dumps(project['skills']),
                    project['url'],
                    project['applications'],
                    project['description'],
                    project['project_id'],
                    project['provider'])
                    updated += 1
                else:
                    # Füge ein neues Projekt ein
                    await conn.execute('''
                    INSERT INTO {} (
                        project_id, title, company, end_date, location, remote,
                        last_updated, skills, url, applications, description, provider
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                    '''.format(DB_TABLE),
                    project['project_id'],
                    project['title'],
                    project['company'],
                    project['end_date'],
                    project['location'],
                    project['remote'],
                    project['last_updated'],
                    json.dumps(project['skills']),
                    project['url'],
                    project['applications'],
                    project['description'],
                    project['provider'])
                    inserted += 1
        
        logger.info(f"{inserted} Projekte eingefügt, {updated} Projekte aktualisiert.")
        return inserted + updated
    except Exception as e:
        logger.error(f"Fehler beim Einfügen/Aktualisieren der Projekte: {e}")
        return 0

async def main(user_id=1, max_pages=100, page_size=100):
    """
    Hauptfunktion: Crawlt und speichert Projekte in der Datenbank
    """
    logger.info(f"Starte Crawling aller Freelance-Projekte mit page_size={page_size} für user_id={user_id}...")
    projects = await crawl_until_existing(user_id, max_pages, page_size, fetch_descriptions=True)
    if not projects:
        logger.error("Keine Projekte gefunden oder Fehler beim Crawling!")
        return False
    logger.info(f"{len(projects)} neue Projekte erfolgreich gecrawlt.")
    # DB-Verbindung herstellen
    conn = await get_db_connection()
    if not conn:
        return False
    try:
        if not await create_table_if_not_exists(conn):
            return False
        count = await insert_or_update_projects(conn, projects)
        logger.info(f"Insgesamt {count} Projekte in die Datenbank gespeichert.")
        return count > 0
    except Exception as e:
        logger.error(f"Fehler bei der Datenbankoperation: {e}")
        return False
    finally:
        await conn.close()
        logger.info("DB-Verbindung geschlossen.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Crawlt Freelance-Projekte und speichert sie in der Datenbank")
    parser.add_argument("--user-id", type=int, default=1, help="User-ID für die Credentials (Standard: 1)")
    parser.add_argument("--max-pages", type=int, default=100, help="Maximale Anzahl der zu crawlenden Seiten (Standard: 100)")
    parser.add_argument("--page-size", type=int, default=100, help="Anzahl der Projekte pro Seite (Standard: 100)")
    args = parser.parse_args()
    success = asyncio.run(main(args.user_id, args.max_pages, args.page_size))
    sys.exit(0 if success else 1) 