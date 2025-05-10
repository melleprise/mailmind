import imaplib
import logging
from contextlib import contextmanager
from typing import Generator
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken
from imap_tools import MailBox, MailboxLoginError
from mailmind.core.models import EmailAccount
import threading
import time
import ssl
import socket
import os
import atexit
import multiprocessing

logger = logging.getLogger(__name__)

# Globaler Verbindungspool
_connection_pool = {}
_pool_lock = threading.Lock()
_max_connections = 3  # Maximale Anzahl gleichzeitiger Verbindungen pro Account
_connection_timeout = 300  # Timeout in Sekunden (5 Minuten)
_connect_timeout = 60  # Timeout für Verbindungsaufbau und Login (erhöht)
_max_retries = 3  # Maximale Anzahl von Verbindungsversuchen

# Socket Timeouts
socket.setdefaulttimeout(_connect_timeout)

def cleanup_connections():
    """Cleanup alle Verbindungen beim Beenden."""
    with _pool_lock:
        for account_id, pool in _connection_pool.items():
            for conn_data in pool:
                try:
                    conn_data['connection'].logout()
                except:
                    pass
        _connection_pool.clear()

# Registriere Cleanup beim Beenden
atexit.register(cleanup_connections)

def _get_connection_key(account_id: int) -> str:
    """Generiert einen eindeutigen Schlüssel für die Verbindung."""
    return f"{account_id}_{os.getpid()}"

@contextmanager
def get_imap_connection(account: EmailAccount) -> Generator[MailBox, None, None]:
    """Gibt eine IMAP-Verbindung aus dem Pool zurück oder erstellt eine neue."""
    account_id = account.id
    mailbox = None
    start_time = time.time()
    logger.debug(f"Getting IMAP connection for account {account_id}")

    try:
        with _pool_lock:
            if account_id not in _connection_pool:
                _connection_pool[account_id] = []
            
            pool = _connection_pool[account_id]
            current_time = time.time()

            # Bereinige abgelaufene Verbindungen und finde eine nutzbare Verbindung
            usable_connection = None
            active_connections = []
            for conn_data in pool:
                if current_time - conn_data['last_used'] < _connection_timeout:
                    active_connections.append(conn_data)
                    if not conn_data.get('in_use'):
                        try:
                            # Teste die Verbindung über den darunterliegenden imaplib-Client
                            if hasattr(conn_data['connection'], 'client'):
                                conn_data['connection'].client.noop()
                            else:
                                raise AttributeError("MailBox object has no 'client' attribute")
                            # Wenn erfolgreich, Verbindung wiederverwenden
                            usable_connection = conn_data['connection']
                            conn_data['in_use'] = True
                            conn_data['last_used'] = current_time
                            logger.debug(f"Reusing existing connection for account {account_id}")
                            break 
                        except Exception as e:
                            # Wenn Test fehlschlägt, Verbindung entfernen
                            logger.debug(f"Connection test failed, will create new one: {e}")
                            try:
                                conn_data['connection'].logout()
                            except: 
                                pass # Logout-Fehler hier ignorieren
                else:
                    # Abgelaufene Verbindung ausloggen
                    try:
                        conn_data['connection'].logout()
                    except Exception as logout_e:
                        logger.warning(f"Could not logout expired connection for {account_id}: {logout_e}")
            
            _connection_pool[account_id] = active_connections
            pool = _connection_pool[account_id]

            if usable_connection:
                mailbox = usable_connection
            else:
                # Warte, wenn maximale Verbindungen erreicht sind
                while len(pool) >= _max_connections:
                    logger.debug(f"Max connections reached for {account_id}, waiting...")
                    _pool_lock.release()
                    time.sleep(1)
                    _pool_lock.acquire()
                    
                    current_time = time.time()
                    pool[:] = [conn for conn in pool if current_time - conn['last_used'] < _connection_timeout]
                    if len(pool) < _max_connections:
                        break

                # Erstelle neue Verbindung
                logger.debug(f"Creating new connection for account {account_id}")
                connect_start = time.time()
                
                # SSL-Kontext konfigurieren
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = True
                ssl_context.verify_mode = ssl.CERT_REQUIRED
                
                # Verbindung mit Timeouts und SSL
                mb = MailBox(
                    host=account.imap_server,
                    port=993,  # Standard IMAPS Port
                    ssl_context=ssl_context,
                    timeout=_connect_timeout
                )
                logger.debug(f"MailBox created in {time.time() - connect_start:.2f}s")

                # Passwort entschlüsseln
                decrypt_start = time.time()
                password = account.get_password()
                if not password:
                    logger.error(f"Failed to get password for account {account_id}. Check if set and encryption key.")
                    raise ValueError("Could not retrieve or decrypt password for account.")
                logger.debug(f"Password decrypted in {time.time() - decrypt_start:.2f}s")

                # Login mit Retry-Logik
                login_start = time.time()
                retry_count = 0
                while retry_count < _max_retries:
                    try:
                        mailbox = mb.login(account.email, password)
                        # Warte kurz nach erfolgreichem Login
                        time.sleep(1)
                        break
                    except Exception as e:
                        retry_count += 1
                        if retry_count == _max_retries:
                            logger.error(f"Login failed after {_max_retries} attempts for account {account_id}: {e}")
                            raise
                        logger.warning(f"Login attempt {retry_count} failed for account {account_id}, retrying...")
                        time.sleep(2)  # Längere Pause zwischen Versuchen
                
                # Setze den Socket-Timeout für IMAP-Operationen
                if hasattr(mailbox, 'client') and hasattr(mailbox.client, 'socket') and callable(mailbox.client.socket):
                    actual_socket = mailbox.client.socket()
                    if hasattr(actual_socket, 'settimeout'):
                        actual_socket.settimeout(600) # Socket-Timeout für IMAP-Kommandos
                    else:
                         logger.warning(f"Could not set socket timeout for account {account_id}. Socket object lacks settimeout.")
                elif hasattr(mailbox, 'client') and hasattr(mailbox.client, 'sock'): # Fallback, falls 'sock' Attribut existiert
                     if hasattr(mailbox.client.sock, 'settimeout'):
                         mailbox.client.sock.settimeout(600)
                     else:
                         logger.warning(f"Could not set socket timeout via 'sock' for account {account_id}.")
                else:
                    logger.warning(f"Could not access socket to set timeout for account {account_id}.")
                
                logger.debug(f"Login completed in {time.time() - login_start:.2f}s")
                
                pool.append({'connection': mailbox, 'last_used': time.time(), 'in_use': True})
                logger.debug(f"Connection created and stored in pool in {time.time() - start_time:.2f}s")
        
        yield mailbox
        
    except ValueError as e:
        logger.error(f"IMAP connection failed for account {account_id} ({account.email}) due to password issue: {e}")
        raise
    except MailboxLoginError as e:
        logger.error(f"IMAP login failed for account {account_id} ({account.email}): {e}")
        raise
    except Exception as e:
        logger.error(f"Error getting IMAP connection for {account_id}: {e}")
        raise
    finally:
        if mailbox:
            with _pool_lock:
                if account_id in _connection_pool:
                    for conn_data in _connection_pool[account_id]:
                        if conn_data['connection'] == mailbox:
                            conn_data['in_use'] = False
                            conn_data['last_used'] = time.time()
                            logger.debug(f"Released connection for account {account_id}")
                            break 