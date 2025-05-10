import os
import sys
import django
import time
import logging # Logging importieren
# import imaplib # Wird nicht mehr direkt benötigt, wenn Debug weg ist

# Logging konfigurieren, um DEBUG-Meldungen von imap_tools anzuzeigen
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(name)-15s %(message)s')
logging.getLogger('imap_tools').setLevel(logging.DEBUG)
# Optional: Standard imaplib Debugging (sehr ausführlich)
# imaplib.Debug = 4 # Entferne oder kommentiere diese Zeile aus

# Pfad zum Django-Projekt hinzufügen
project_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(project_path)

# Django-Settings laden
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

try:
    django.setup()
    logging.info("Django setup successful.") # Geändert zu logging.info
except Exception as e:
    logging.error(f"FEHLER beim Initialisieren von Django: {e}") # Geändert zu logging.error
    sys.exit(1)

# Erst nach django.setup() importieren
from mailmind.core.models import EmailAccount
from mailmind.imap.connection import get_imap_connection
from django.core.exceptions import ObjectDoesNotExist
from imap_tools.errors import MailboxFetchError
from imap_tools import A # Importiere den Query Builder

def test_dynamic_uid_fetch(account_id):
    logging.info(f"--- Testing Dynamic UID Fetch for Account ID: {account_id} ---") # Geändert zu logging
    
    account = None
    try:
        account = EmailAccount.objects.get(id=account_id)
        logging.info(f"Account gefunden: {account.email} (ID: {account.id})") # Geändert zu logging
    except ObjectDoesNotExist:
        logging.error(f"FEHLER: EmailAccount mit ID {account_id} nicht in der Datenbank gefunden.") # Geändert zu logging
        return
    except Exception as e:
        logging.error(f"FEHLER beim Laden des Accounts {account_id}: {e}") # Geändert zu logging
        return

    if not account:
        logging.error("FEHLER: Account Objekt konnte nicht geladen werden.") # Geändert zu logging
        return

    uids_to_fetch = []
    fetched_messages = []
    try:
        logging.info("Versuche Verbindung mit get_imap_connection...") # Geändert zu logging
        start_time = time.time()
        with get_imap_connection(account) as mailbox:
            connection_time = time.time() - start_time
            logging.info(f"Verbindung erfolgreich hergestellt in {connection_time:.2f} Sekunden.") # Geändert zu logging
            
            logging.info("Wähle Ordner 'INBOX'...") # Geändert zu logging
            mailbox.folder.set('INBOX')
            logging.info("Ordner 'INBOX' erfolgreich ausgewählt.") # Geändert zu logging

            # Dynamisch einige UIDs abrufen (z.B. die ersten 20)
            logging.info("Rufe aktuelle UIDs aus INBOX ab...")
            dynamic_uids = mailbox.uids()
            if not dynamic_uids:
                logging.warning("WARNUNG: Keine UIDs in INBOX gefunden zum Testen.")
                logging.info("--- Test Skript beendet (keine UIDs zum Fetchen) ---")
                return
            else:
                uids_to_fetch_all = dynamic_uids
                uids_to_fetch = uids_to_fetch_all[:20]
                logging.info(f"{len(uids_to_fetch_all)} UIDs insgesamt gefunden. Verwende die ersten {len(uids_to_fetch)} für den Fetch: {uids_to_fetch}")

            # Fetch durchführen mit A(uid=...)
            logging.info(f"Starte Fetch-Vorgang für {len(uids_to_fetch)} UIDs mit A(uid=...) Kriterium...")
            fetch_start_time = time.time()
            try:
                if uids_to_fetch:
                    # HIER sollte das Debug-Logging von imaplib die Details zeigen
                    fetched_messages = list(mailbox.fetch(A(uid=uids_to_fetch))) # Zurück zu A(uid=...) geändert
                else:
                    fetched_messages = []
                fetch_time = time.time() - fetch_start_time
                logging.info(f"Fetch-Vorgang abgeschlossen in {fetch_time:.2f} Sekunden. {len(fetched_messages)} Nachrichten empfangen.")
            except MailboxFetchError as e_fetch:
                 logging.error(f"FEHLER (MailboxFetchError) während des Fetch-Vorgangs mit A(uid=...): {e_fetch}")
            except Exception as e_fetch_general:
                 logging.error(f"ALLGEMEINER FEHLER während des Fetch-Vorgangs mit A(uid=...): {type(e_fetch_general).__name__} - {e_fetch_general}")

        logging.info("Verbindung erfolgreich geschlossen (Context Manager).") # Geändert zu logging

    except Exception as e: # Fängt Verbindungsfehler etc.
        logging.error(f"ALLGEMEINER FEHLER während des IMAP-Tests für Account {account_id} ({account.email}):") # Geändert zu logging
        logging.error(f"  Error Type: {type(e).__name__}") # Geändert zu logging
        logging.error(f"  Error Details: {e}") # Geändert zu logging
        
    # Ergebnisse ausgeben
    logging.info(f"--- Fetch Ergebnisse ({len(fetched_messages)} Nachrichten) ---") # Geändert zu logging
    if fetched_messages:
        # Nur eine begrenzte Anzahl ausgeben, um die Konsole nicht zu überfluten
        max_messages_to_print = 5 
        count = 0
        for msg in fetched_messages:
            if count >= max_messages_to_print:
                logging.info(f"... (und {len(fetched_messages) - count} weitere Nachrichten)") # Geändert zu logging
                break
            logging.info("--- Nachricht --- ") # Geändert zu logging
            logging.info(f"  UID: {msg.uid}") # Geändert zu logging
            logging.info(f"  Subject: {msg.subject}") # Geändert zu logging
            logging.info(f"  From: {msg.from_}") # Geändert zu logging
            logging.info(f"  Date: {msg.date}") # Geändert zu logging
            count += 1
    else:
        logging.info("Keine Nachrichten für die angeforderten UIDs empfangen oder Fehler beim Fetch.") # Geändert zu logging

if __name__ == "__main__":
    account_id_to_test = 7
    test_dynamic_uid_fetch(account_id_to_test)
    logging.info("--- Test Skript beendet ---") # Geändert zu logging 