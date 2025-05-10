import asyncio
import logging
import time
from typing import Dict, Optional
import threading
import ssl
import re
import base64

from django.conf import settings
from django.utils import timezone
from cryptography.fernet import Fernet, InvalidToken
from channels.layers import get_channel_layer
from channels.db import database_sync_to_async
from django_q.tasks import async_task
from aioimaplib import aioimaplib

# Importiere Modelle erst nach potenziellem django.setup() in start_idle_manager
# from mailmind.core.models import EmailAccount

logger = logging.getLogger(__name__)

# Konstanten für IDLE-Management
IDLE_COMMAND_TIMEOUT = 30  # Timeout für IDLE-Start in Sekunden
# Reduzierter Timeout für regelmäßigen Check, z.B. 5 Minuten
wait_timeout = 5 * 60 # 5 Minuten Timeout für IDLE-Wait

# Globales Dictionary zur Verfolgung laufender IDLE-Tasks
# Schlüssel: account_id, Wert: asyncio.Task
running_idle_tasks: Dict[int, asyncio.Task] = {}
_manager_stop_event = asyncio.Event()

# --- Account-spezifischer IDLE Task ---
async def run_idle_for_account(account_id: int, decrypted_password: Optional[str]):
    """Hauptfunktion für die IDLE-Verbindung eines einzelnen Kontos."""
    from mailmind.core.models import EmailAccount # Import hier, da in async context
    
    logger.info(f"[IDLE Task {account_id}] Starting for account {account_id}")
    imap_client = None
    retry_delay = 5 # Initial retry delay in seconds
    folder_to_monitor = 'INBOX' # TODO: Make configurable?
    known_uids = set() # Store known UIDs for this account/folder

    while not _manager_stop_event.is_set():
        imap_client = None
        idle_command_task = None
        idle_wait_task = None
        new_uids_after_idle = None # Initialize here
        try:
            # 0. Fetch account data (inside loop to get updates)
            try:
                account = await database_sync_to_async(EmailAccount.objects.get)(id=account_id, is_active=True)
                logger.debug(f"[IDLE Task {account_id}] Fetched active account data.")
            except EmailAccount.DoesNotExist:
                logger.warning(f"[IDLE Task {account_id}] Account {account_id} not found or inactive. Stopping task.")
                break

            # 1. Establish IMAP connection if needed
            # Check state instead of is_connected
            if not imap_client or not (hasattr(imap_client, 'protocol') and imap_client.protocol.state in ['AUTH', 'SELECTED']):
                logger.info(f"[IDLE Task {account_id}] Establishing connection...")
                connect_start_time = time.time()
                # --- Close previous connection if exists ---
                if imap_client:
                    try:
                       # Check state before calling methods
                       if hasattr(imap_client, 'protocol') and imap_client.protocol.state == 'SELECTED':
                           if hasattr(imap_client, 'is_idle') and imap_client.is_idle: 
                               try:
                                   await imap_client.idle_done()
                               except Exception as idle_err:
                                   logger.warning(f"[IDLE Task {account_id}] Error ending IDLE: {idle_err}")
                       if hasattr(imap_client, 'tcp_connector') and imap_client.tcp_connector and not imap_client.tcp_connector.closed:
                           imap_client.tcp_connector.close()
                    except Exception as close_err:
                       logger.warning(f"[IDLE Task {account_id}] Error closing previous connection: {close_err}")
                    finally:
                       imap_client = None
                # --- End close previous connection --- 
                try:
                    # Verwende E-Mail als Fallback für Benutzernamen
                    login_username = account.username
                    if not login_username:
                        login_username = account.email
                        logger.warning(f"[IDLE Task {account_id}] Username is empty for account {account.email}. Using email address as login username.")
                    
                    # Stelle sicher, dass der login_username nicht immer noch leer ist (sollte nicht passieren, wenn E-Mail Pflicht ist)
                    if not login_username:
                         logger.error(f"[IDLE Task {account_id}] Both username and email are empty for account ID {account_id}. Cannot login.")
                         raise ValueError("Username and Email cannot both be empty.")
                        
                    # Password Entschlüsselung via Model-Methode (asynchron)
                    # password = await database_sync_to_async(account.get_password)() # Entfernt
                    # Verwende das übergebene Passwort
                    password = decrypted_password
                    if not password:
                         logger.error(f"[IDLE Task {account_id}] No password provided to task or failed to decrypt earlier.")
                         raise aioimaplib.Abort("Missing credentials")
                    
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = True
                    ssl_context.verify_mode = ssl.CERT_REQUIRED
                    
                    # Connect with timeout
                    try:
                        imap_client = aioimaplib.IMAP4_SSL(
                            host=account.imap_server,
                            port=account.imap_port,
                            ssl_context=ssl_context,
                            timeout=60 # Erhöht von 15 auf 60 Sekunden
                        )
                        await imap_client.wait_hello_from_server()
                    except asyncio.TimeoutError:
                         logger.error(f"[IDLE Task {account_id}] Connection attempt timed out after 60s.")
                         raise aioimaplib.Abort('Connection timeout')
                    except Exception as conn_err:
                         logger.error(f"[IDLE Task {account_id}] Connection failed: {conn_err}")
                         raise aioimaplib.Abort(f'Connection failed: {conn_err}')

                    # Login mit dem (potenziell Fallback) Benutzernamen
                    logger.debug(f"[IDLE Task {account_id}] Attempting login with username: '{login_username}' and password: '*****'") # Log username
                    await imap_client.login(login_username, password)
                    
                    # Select folder (initial selection)
                    await imap_client.select(folder_to_monitor)
                    
                    # Fetch initial UIDs using FETCH 1:* (UID)
                    logger.debug(f"[IDLE Task {account_id}] Fetching initial UIDs via FETCH 1:* (UID)")
                    initial_fetch_resp = None
                    try:
                         initial_fetch_resp = await imap_client.fetch('1:*', '(UID)')
                         logger.debug(f"[IDLE Task {account_id}] Initial FETCH response: {initial_fetch_resp}")
                         
                         # Parse die FETCH-Antwort
                         initial_uids = set()
                         if initial_fetch_resp and initial_fetch_resp.result == 'OK':
                              for line in initial_fetch_resp.lines:
                                   if isinstance(line, bytes): line = line.decode()
                                   match = re.search(r'UID\s+(\d+)\)', line, re.IGNORECASE)
                                   if match:
                                        initial_uids.add(match.group(1))
                         known_uids = initial_uids # Setze known_uids korrekt
                         logger.info(f"[IDLE Task {account_id}] Initial UIDs in '{folder_to_monitor}': {len(known_uids)}")
                         # Logge ein paar UIDs zur Kontrolle
                         if known_uids:
                              logger.debug(f"[IDLE Task {account_id}] Sample initial UIDs: {list(known_uids)[:10]}")

                    except (aioimaplib.IMAP4.error, asyncio.TimeoutError, OSError) as init_fetch_err:
                         logger.error(f"[IDLE Task {account_id}] Error fetching initial UIDs via FETCH: {init_fetch_err}. known_uids remains empty.")
                         known_uids = set() # Sicherstellen, dass es leer ist bei Fehler
                    except Exception as init_parse_err:
                         logger.error(f"[IDLE Task {account_id}] Error parsing initial FETCH response: {init_parse_err}. known_uids remains empty.", exc_info=True)
                         known_uids = set() # Sicherstellen, dass es leer ist bei Fehler

                    retry_delay = 5 # Reset retry delay on successful connect
                    logger.info(f"[IDLE Task {account_id}] Connection established successfully in {time.time() - connect_start_time:.2f}s.")
                
                # Remove ReadOnly from exception handling
                except (aioimaplib.Abort,) as imap_err:
                    logger.error(f"[IDLE Task {account_id}] IMAP setup error: {imap_err}")
                    if imap_client: await imap_client.close()
                    imap_client = None
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 300) # Exponential backoff
                    continue
                except Exception as setup_err:
                    logger.error(f"[IDLE Task {account_id}] Unexpected setup error: {setup_err}", exc_info=True)
                    if imap_client: await imap_client.close()
                    imap_client = None
                    await asyncio.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, 300)
                    continue

            # 2. Enter IDLE mode
            try:
                logger.info(f"[IDLE Task {account_id}] Entering IDLE mode for folder '{folder_to_monitor}'...")
                idle_start_time = time.time()
                idle_command_task = asyncio.create_task(imap_client.idle_start())
                try:
                    # Wait for the IDLE command to complete or timeout
                    await asyncio.wait_for(idle_command_task, timeout=IDLE_COMMAND_TIMEOUT)
                    # logger.debug(f"[IDLE Task {account_id}] idle_start() task completed.") # Redundant logging
                except asyncio.TimeoutError:
                    logger.error(f"[IDLE Task {account_id}] Timed out waiting for IDLE command to start.")
                    if idle_command_task: idle_command_task.cancel()
                    raise aioimaplib.Abort("IDLE start timeout")
                except asyncio.CancelledError:
                     logger.info(f"[IDLE Task {account_id}] IDLE start task cancelled.")
                     raise # Propagate cancellation
                except Exception as idle_start_err:
                    logger.error(f"[IDLE Task {account_id}] Error starting IDLE: {idle_start_err}", exc_info=True)
                    raise aioimaplib.Abort(f"IDLE start failed: {idle_start_err}")

                logger.info(f"[IDLE Task {account_id}] IDLE mode active. Waiting for notifications or timeout ({wait_timeout}s)...")

                # --- Wait for IDLE Responses or Stop Event ---
                try:
                    idle_wait_task = asyncio.create_task(imap_client.wait_server_push(timeout=wait_timeout))
                    stop_wait_task = asyncio.create_task(_manager_stop_event.wait())

                    # Wait for either an IDLE response/timeout OR the stop event
                    done, pending = await asyncio.wait(
                        [idle_wait_task, stop_wait_task],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    logger.debug(f"[IDLE Task {account_id}] asyncio.wait finished. Done tasks: {[t.get_name() for t in done]}, Pending: {len(pending)}")

                    # --- Exit IDLE ---
                    # Always try to exit IDLE gracefully, regardless of what finished first
                    logger.debug(f"[IDLE Task {account_id}] Attempting to exit IDLE mode by sending DONE...")
                    try:
                        if imap_client and hasattr(imap_client, 'protocol') and imap_client.protocol.state == 'SELECTED':
                            # Sende DONE direkt, da idle_done() keine Coroutine ist
                            imap_client.idle_done()
                            logger.info(f"[IDLE Task {account_id}] Successfully sent DONE command.")
                        else:
                            logger.warning(f"[IDLE Task {account_id}] Cannot exit IDLE, client not in SELECTED state or disconnected.")
                    except asyncio.TimeoutError:
                        logger.warning(f"[IDLE Task {account_id}] Timeout while sending DONE command.")
                        if imap_client: 
                            try:
                                await asyncio.wait_for(imap_client.close(), timeout=5)
                            except (asyncio.TimeoutError, Exception) as close_err:
                                logger.warning(f"[IDLE Task {account_id}] Error closing connection after DONE timeout: {close_err}")
                        imap_client = None
                        raise aioimaplib.Abort("IDLE DONE timeout")
                    except (aioimaplib.Abort, ConnectionResetError, BrokenPipeError) as e_conn_done:
                        logger.warning(f"[IDLE Task {account_id}] Connection error sending DONE: {e_conn_done}. Retrying connection.")
                        if imap_client: 
                            try:
                                await asyncio.wait_for(imap_client.close(), timeout=5)
                            except (asyncio.TimeoutError, Exception) as close_err:
                                logger.warning(f"[IDLE Task {account_id}] Error closing connection after connection error: {close_err}")
                        imap_client = None
                        raise aioimaplib.Abort("Connection error during IDLE DONE")
                    except Exception as e_done:
                        logger.error(f"[IDLE Task {account_id}] Unexpected error sending DONE: {e_done}", exc_info=True)
                        if imap_client: 
                            try:
                                await asyncio.wait_for(imap_client.close(), timeout=5)
                            except (asyncio.TimeoutError, Exception) as close_err:
                                logger.warning(f"[IDLE Task {account_id}] Error closing connection after unexpected error: {close_err}")
                        imap_client = None
                        raise

                except asyncio.CancelledError:
                    logger.info(f"[IDLE Task {account_id}] IDLE wait task was cancelled.")
                    if imap_client: 
                        try:
                            await asyncio.wait_for(imap_client.close(), timeout=5)
                        except (asyncio.TimeoutError, Exception) as close_err:
                            logger.warning(f"[IDLE Task {account_id}] Error closing connection after cancellation: {close_err}")
                    imap_client = None
                    raise

                # --- Process Results (nach wait_server_push) ---
                # Logge, warum wait beendet wurde
                if stop_wait_task in done:
                    logger.info(f"[IDLE Task {account_id}] Stop event received. Exiting IDLE loop.")
                    if idle_wait_task in pending: idle_wait_task.cancel() # Cancel the wait task
                    break # Exit the main while loop
                elif idle_wait_task in done:
                    try:
                        responses = idle_wait_task.result()
                        if responses:
                             logger.info(f"[IDLE Task {account_id}] Received push notifications: {responses}. Proceeding with UID check.")
                        else:
                             logger.debug(f"[IDLE Task {account_id}] IDLE wait timed out after {wait_timeout}s. Proceeding with UID check.")
                    except asyncio.CancelledError:
                         logger.debug(f"[IDLE Task {account_id}] IDLE wait task cancelled before result (likely stop event).")
                         # Nicht breaken, damit die Verbindung sauber geschlossen wird
                    except Exception as e:
                         logger.error(f"[IDLE Task {account_id}] Error processing IDLE responses: {e}. Proceeding with UID check anyway.", exc_info=True)
                else:
                     # Sollte nicht passieren, da FIRST_COMPLETED verwendet wird
                     logger.warning(f"[IDLE Task {account_id}] asyncio.wait finished unexpectedly without idle_wait_task or stop_wait_task in done set. Proceeding with UID check.")

                # --- IMMER UIDs fetchen nach Beendigung von IDLE wait --- 
                logger.info(f"[IDLE Task {account_id}] Exited IDLE. Fetching current UIDs for comparison...")
                uid_response = None
                try:
                    # Versuche FETCH 1:* (UID)
                        logger.debug(f"[IDLE Task {account_id}] Attempting FETCH 1:* (UID)")
                        fetch_response = await imap_client.fetch('1:*', '(UID)')
                        logger.debug(f"[IDLE Task {account_id}] FETCH 1:* (UID) response: {fetch_response}")
                        
                        # Parse die FETCH-Antwort, um UIDs zu extrahieren
                        # Format: * N FETCH (UID XXXX)
                        new_uids_after_idle = set()
                        if fetch_response and fetch_response.result == 'OK':
                            for line in fetch_response.lines:
                                if isinstance(line, bytes): line = line.decode()
                                # Einfache und robuste Suche nach "UID XXXX)"
                                match = re.search(r'UID\s+(\d+)\)', line, re.IGNORECASE)
                                if match:
                                    new_uids_after_idle.add(match.group(1))
                        
                        # Logge das Ergebnis
                        logger.debug(f"[IDLE Task {account_id}] Parsed UIDs from FETCH: {new_uids_after_idle}")
                        logger.info(f"[IDLE Task {account_id}] UIDs after IDLE (from FETCH 1:*): {len(new_uids_after_idle)}")
                        
                        # Fallback, wenn Parsing fehlschlägt (sollte nicht passieren)
                        if not new_uids_after_idle and fetch_response and fetch_response.result != 'OK':
                             logger.warning(f"[IDLE Task {account_id}] Could not fetch UIDs after IDLE activity via FETCH 1:* (UID): {fetch_response.result}")
                             new_uids_after_idle = set()
                        elif not new_uids_after_idle and fetch_response and fetch_response.result == 'OK':
                             logger.warning(f"[IDLE Task {account_id}] FETCH 1:* (UID) was OK but parsing yielded no UIDs. Lines: {fetch_response.lines}")
                             new_uids_after_idle = set()

                except (aioimaplib.IMAP4.error, asyncio.TimeoutError, OSError) as fetch_err:
                    logger.error(f"[IDLE Task {account_id}] Connection error fetching UIDs after IDLE: {fetch_err}. Will retry loop.", exc_info=False)
                    # Trigger outer retry loop for connection issues
                    raise aioimaplib.Abort("UID fetch connection error") # Trigger outer retry
                except Exception as e:
                    logger.error(f"[IDLE Task {account_id}] Unexpected error fetching UIDs after IDLE: {e}. Will retry loop.", exc_info=True)
                    # Trigger outer retry loop for unexpected issues
                    raise aioimaplib.Abort("UID fetch unexpected error") # Trigger outer retry


                # --- Compare UIDs and start tasks (wenn fetch erfolgreich war) ---
                if new_uids_after_idle is not None: # Nur wenn Fetch erfolgreich
                    # --- Logge den Vergleich --- 
                    logger.debug(f"[IDLE Task {account_id}] Comparing UIDs. Known: {known_uids}")
                    added_uids = new_uids_after_idle - known_uids
                    logger.debug(f"[IDLE Task {account_id}] Calculated added_uids: {added_uids}")
                    # --- ENDE LOG ---

                    if added_uids:
                        logger.info(f"[IDLE Task {account_id}] Detected {len(added_uids)} new UIDs: {list(added_uids)[:10]}... Triggering full folder sync task.")
                        # Trigger EINE Task für den gesamten Ordner
                        async_task('mailmind.imap.tasks.sync_folder_on_idle_update', account_id, folder_to_monitor)
                        # --- Logge Update von known_uids ---
                        old_known_count = len(known_uids)
                        known_uids.update(added_uids) # Update known UIDs
                        logger.debug(f"[IDLE Task {account_id}] Updated known_uids. Old count: {old_known_count}, New count: {len(known_uids)}")
                        # --- ENDE LOG ---
                    # else: # Optional: Log, wenn keine neuen UIDs gefunden wurden
                    #    logger.debug(f"[IDLE Task {account_id}] No new UIDs detected after comparison.")
                # else: # Fetch der UIDs ist fehlgeschlagen (Fehler wurde oben geloggt)
                #    logger.warning(f"[IDLE Task {account_id}] Could not compare UIDs because fetching failed.")

                logger.debug(f"[IDLE Task {account_id}] Pausing briefly before next IDLE cycle...")
                await asyncio.sleep(1) # Kurze Pause vor dem nächsten IDLE

            # Remove ReadOnly from exception handling
            except (aioimaplib.Abort,) as imap_err:
                logger.error(f"[IDLE Task {account_id}] IMAP Error during IDLE loop: {imap_err}. Retrying in {retry_delay}s...", exc_info=True)
                if idle_wait_task and not idle_wait_task.done(): idle_wait_task.cancel()
                if idle_command_task and not idle_command_task.done(): idle_command_task.cancel()
                if imap_client: await imap_client.close()
                imap_client = None
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 300)

            except asyncio.CancelledError:
                 logger.info(f"[IDLE Task {account_id}] IDLE task explicitly cancelled.")
                 if idle_wait_task and not idle_wait_task.done(): idle_wait_task.cancel()
                 if idle_command_task and not idle_command_task.done(): idle_command_task.cancel()
                 break

            except Exception as e:
                logger.error(f"[IDLE Task {account_id}] Unexpected error in IDLE loop: {e}. Retrying in {retry_delay}s...", exc_info=True)
                if idle_wait_task and not idle_wait_task.done(): idle_wait_task.cancel()
                if idle_command_task and not idle_command_task.done(): idle_command_task.cancel()
                if imap_client: await imap_client.close()
                imap_client = None
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 300)

        # Remove ReadOnly from exception handling
        except (aioimaplib.Abort,) as imap_err:
            logger.error(f"[IDLE Task {account_id}] Outer IMAP Error: {imap_err}. Retrying in {retry_delay}s...", exc_info=True)
            if imap_client: await imap_client.close()
            imap_client = None
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 300) # Exponential backoff

        except asyncio.CancelledError:
             logger.info(f"[IDLE Task {account_id}] Task cancelled (outer loop).")
             break # Task beenden

        except Exception as e:
            logger.error(f"[IDLE Task {account_id}] Unexpected outer error: {e}. Retrying in {retry_delay}s...", exc_info=True)
            if imap_client: await imap_client.close()
            imap_client = None
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 300) # Exponential backoff


    # Verbindung sauber schließen, wenn die Schleife endet
    if imap_client:
        try:
            # Check state before calling methods
            if hasattr(imap_client, 'protocol') and imap_client.protocol.state == 'SELECTED':
                if imap_client.is_idle: await imap_client.idle_done()
            if imap_client.is_logged_in(): await imap_client.logout()
            logger.info(f"[IDLE Task {account_id}] Successfully logged out.")
        except Exception as logout_err:
            logger.error(f"[IDLE Task {account_id}] Error during final logout: {logout_err}")
        finally:
            await imap_client.close() # close() handles checks internally
            logger.info(f"[IDLE Task {account_id}] Connection closed.")

    logger.info(f"[IDLE Task {account_id}] Task finished.")
    # Entferne Task aus dem globalen Dictionary, wenn er beendet wird
    if account_id in running_idle_tasks:
        del running_idle_tasks[account_id]

# --- Manager Task ---
async def manage_idle_connections():
    """Verwaltet die IDLE-Tasks für alle aktiven Konten."""
    from mailmind.core.models import EmailAccount # Import hier
    logger.info("[IDLE Manager] Starting connection management loop...")
    while not _manager_stop_event.is_set():
        try:
            # Hole aktive Konten-Objekte statt nur IDs, um Passwörter zu holen
            # Mache die DB-Abfrage asynchron
            active_accounts_list = await database_sync_to_async(list)(
                EmailAccount.objects.filter(is_active=True)
            )
            active_account_ids = set(acc.id for acc in active_accounts_list)
            current_task_ids = set(running_idle_tasks.keys())

            # Erstelle ein Dict ID -> Account-Objekt für einfachen Zugriff
            active_accounts_dict = {acc.id: acc for acc in active_accounts_list}


            # Starte Tasks für neue/aktive Konten
            for acc_id in active_account_ids:
                if acc_id not in current_task_ids:
                     account_obj = active_accounts_dict.get(acc_id)
                     if not account_obj:
                          logger.warning(f"[IDLE Manager] Account object for ID {acc_id} not found unexpectedly. Skipping start.")
                          continue
                          
                     # Passwort hier asynchron holen
                     decrypted_password = None
                     try:
                          # Wickel get_password in database_sync_to_async
                          get_password_async = database_sync_to_async(account_obj.get_password)
                          decrypted_password = await get_password_async()
                          
                          if not decrypted_password:
                               logger.error(f"[IDLE Manager] Failed to get/decrypt password for account {acc_id}. Cannot start IDLE task.")
                               continue # Nicht starten ohne Passwort
                          # logger.debug(f"[IDLE Manager] Successfully decrypted password for account {acc_id}.") # Optional: Debug log
                     except InvalidToken:
                          logger.error(f"[IDLE Manager] Invalid encryption key or corrupted password data for account {acc_id}. Cannot start IDLE task.")
                          continue
                     except Exception as pwd_err:
                          logger.error(f"[IDLE Manager] Error getting password for account {acc_id}: {pwd_err}. Cannot start IDLE task.", exc_info=True)
                          continue

                     logger.info(f"[IDLE Manager] Starting IDLE task for active account {acc_id}...")
                     # Übergebe das entschlüsselte Passwort an den Task
                     task = asyncio.create_task(run_idle_for_account(acc_id, decrypted_password))
                     running_idle_tasks[acc_id] = task
                else:
                    # Optional: Prüfen, ob der Task noch läuft
                    if running_idle_tasks[acc_id].done():
                         logger.warning(f"[IDLE Manager] Task for account {acc_id} was finished. Restarting...")
                         # Hole evtl. Exception, um sie zu loggen
                         try:
                              running_idle_tasks[acc_id].result()
                         except Exception as task_exc:
                              logger.error(f"[IDLE Manager] Task for account {acc_id} finished with error: {task_exc}", exc_info=True)

                         # Task neu starten (Passwort erneut asynchron holen)
                         account_obj = active_accounts_dict.get(acc_id)
                         if not account_obj:
                              logger.warning(f"[IDLE Manager] Account object for ID {acc_id} not found on restart. Skipping.")
                              continue
                         decrypted_password = None
                         try:
                              # Wickel get_password in database_sync_to_async
                              get_password_async = database_sync_to_async(account_obj.get_password)
                              decrypted_password = await get_password_async()
                              
                              if not decrypted_password:
                                   logger.error(f"[IDLE Manager] Failed to get password for account {acc_id} on restart.")
                                   continue
                         except Exception as pwd_err:
                              logger.error(f"[IDLE Manager] Error getting password for account {acc_id} on restart: {pwd_err}.", exc_info=True)
                              continue
                              
                         task = asyncio.create_task(run_idle_for_account(acc_id, decrypted_password))
                         running_idle_tasks[acc_id] = task

            # Stoppe Tasks für inaktive/gelöschte Konten
            for acc_id in current_task_ids:
                if acc_id not in active_account_ids:
                    logger.info(f"[IDLE Manager] Account {acc_id} is no longer active. Stopping IDLE task...")
                    task = running_idle_tasks.get(acc_id)
                    if task and not task.done():
                        task.cancel()
                    # Task wird sich selbst aus running_idle_tasks entfernen

            logger.debug(f"[IDLE Manager] Active accounts: {len(active_account_ids)}, Running tasks: {len(running_idle_tasks)}")
            # Warte 60 Sekunden bis zur nächsten Prüfung
            await asyncio.sleep(60)

        except asyncio.CancelledError:
             logger.info("[IDLE Manager] Management loop cancelled.")
             break
        except Exception as e:
            logger.error(f"[IDLE Manager] Error in management loop: {e}. Retrying in 60s...", exc_info=True)
            await asyncio.sleep(60)

    # Aufräumen beim Stoppen des Managers
    logger.info("[IDLE Manager] Stopping all running IDLE tasks...")
    tasks_to_stop = list(running_idle_tasks.values())
    for task in tasks_to_stop:
        if not task.done():
            task.cancel()
    # Warte auf das Beenden der Tasks (optional, mit Timeout)
    if tasks_to_stop:
        await asyncio.wait(tasks_to_stop, timeout=30)
    logger.info("[IDLE Manager] Stopped.")


# --- Startfunktion ---
def start_idle_manager():
    """Startet den manage_idle_connections Task in einem separaten Thread."""
    def run_loop():
        # Stelle sicher, dass Django initialisiert ist, bevor Modelle importiert werden
        try:
            import django
            django.setup()
            logger.info("[IDLE Manager Thread] Django setup complete.")
        except Exception as e:
             logger.error(f"[IDLE Manager Thread] Django setup failed: {e}")
             return # Nicht starten, wenn Django nicht initialisiert werden kann

        asyncio.run(manage_idle_connections())

    # Prüfen, ob der Manager bereits läuft (um doppeltes Starten zu verhindern, z.B. bei Reloads)
    if not any(t.name == 'IdleManagerThread' for t in threading.enumerate()):
        logger.info("Starting IDLE Manager Thread...")
        manager_thread = threading.Thread(target=run_loop, name='IdleManagerThread', daemon=True)
        manager_thread.start()
    else:
        logger.info("IDLE Manager Thread already running.")

# --- Stoppfunktion (optional, z.B. für Tests oder sauberes Beenden) ---
def stop_idle_manager():
     logger.info("Requesting stop for IDLE Manager...")
     _manager_stop_event.set()
     # Der Thread wird sich selbst beenden, da er daemon=True ist oder wenn asyncio.run endet 