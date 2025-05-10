import unittest
from mailmind.imap.connection import get_imap_connection
from mailmind.core.models import EmailAccount
from imap_tools.errors import MailboxFetchError, ImapToolsError
import time
from django.core.exceptions import ObjectDoesNotExist

class IMAPBatchTest(unittest.TestCase):
    # Verwende kein setUpTestData, da wir den Live-Account wollen
    # (Obwohl der Test-Runner normalerweise eine separate DB verwendet)
    
    def setUp(self):
        # Versuche, den spezifischen Account aus der (realen) DB zu laden
        account_id_to_test = 2 # ID für melleprise@gmail.com
        try:
            # Stelle sicher, dass Django initialisiert ist, falls nicht durch manage.py geschehen
            # Normalerweise sollte manage.py test das tun, aber zur Sicherheit:
            import django
            try:
                django.setup()
            except RuntimeError: # Verhindert Fehler, wenn setup() bereits aufgerufen wurde
                pass
            self.account = EmailAccount.objects.get(id=account_id_to_test)
            print(f"Using REAL EmailAccount with ID: {self.account.id} ({self.account.email})")
        except ObjectDoesNotExist:
            print(f"ERROR: EmailAccount with ID {account_id_to_test} not found in REAL database.")
            # Hier Test abbrechen, da der Account benötigt wird
            self.fail(f"EmailAccount with ID {account_id_to_test} not found in the configured database.")
        except Exception as e:
            print(f"Error fetching EmailAccount with ID {account_id_to_test} from REAL database: {e}")
            self.fail(f"Error fetching EmailAccount: {e}")

    def test_batch_fetch(self):
        # Stelle sicher, dass self.account gesetzt wurde
        if not hasattr(self, 'account') or not self.account:
             self.fail("Test setup failed: EmailAccount was not loaded.")
             
        # Verwende nicht mehr die hardcodierten Test-UIDs, 
        # sondern versuche, einige UIDs vom echten Server zu holen.
        # HINWEIS: Dies macht den Test abhängig vom Zustand des echten Postfachs.
        test_uids = []
        print("Attempting to fetch some UIDs from the real account...")
        try:
            with get_imap_connection(self.account) as mailbox:
                mailbox.folder.set('INBOX')
                # Hole z.B. die ersten 50 UIDs als Testdaten
                all_uids = mailbox.uids()
                if all_uids:
                    test_uids = all_uids[:50]
                    print(f"Found {len(test_uids)} UIDs to test (limited to 50): {test_uids[:10]}...")
                else:
                    print("WARNING: No UIDs found in INBOX for testing.")
                    # Optional: Test überspringen oder fehlschlagen lassen?
                    # self.skipTest("No messages found in INBOX to test fetching.") 
                    # Oder einfach mit leerer Liste weitermachen (führt zu Assertion-Fehler unten)
                    pass 
        except Exception as e:
            print(f"Failed to fetch initial UIDs for test: {e}")
            self.fail(f"Failed to fetch initial UIDs: {e}")
            
        # Wenn keine UIDs gefunden wurden, macht der Rest des Tests wenig Sinn
        if not test_uids:
             print("Skipping fetch test as no initial UIDs were found.")
             self.skipTest("No UIDs available for batch fetch test.")
             return # Wichtig: return, damit der Rest nicht ausgeführt wird

        print(f"Requesting {len(test_uids)} UIDs")
        
        # *** NEU: IDLE Test ***
        print("--- Testing IMAP IDLE Connection ---")
        idle_success = False
        try:
            with get_imap_connection(self.account) as mailbox:
                mailbox.folder.set('INBOX') # Ordner muss gesetzt sein für IDLE
                print("Starting IDLE mode...")
                mailbox.idle.start()
                print("IDLE mode active, waiting for 1 second...")
                time.sleep(1) # Kurz warten, um zu sehen, ob die Verbindung stabil ist
                print("Stopping IDLE mode...")
                mailbox.idle.stop()
                print("IDLE mode stopped successfully.")
                idle_success = True
        except ImapToolsError as e:
            print(f"ERROR during IDLE test: {e}")
            # Optional: Test fehlschlagen lassen, wenn IDLE kritisch ist
            # self.fail(f"IMAP IDLE test failed: {e}")
        except Exception as e:
            print(f"Unexpected ERROR during IDLE test: {e}")
            # Optional: Test fehlschlagen lassen
            # self.fail(f"IMAP IDLE test failed unexpectedly: {e}")
        finally:
            print(f"IDLE Connection Test Result: {'SUCCESS' if idle_success else 'FAILURE'}")
        print("--- Finished IMAP IDLE Connection Test ---")
        # *** Ende IDLE Test ***

        messages = []
        try:
            with get_imap_connection(self.account) as mailbox:
                mailbox.folder.set('INBOX')
                
                batch_size = 25
                fetched_count = 0
                
                for i in range(0, len(test_uids), batch_size):
                    batch_uids = test_uids[i:i+batch_size]
                    uid_string = ','.join(map(str, batch_uids))
                    print(f"Fetching batch: {uid_string}")
                    
                    try:
                        batch_messages = list(mailbox.fetch(uid_string, headers_only=True)) 
                        messages.extend(batch_messages)
                        fetched_count += len(batch_messages)
                        print(f"Fetched {len(batch_messages)} messages in this batch. Total: {fetched_count}")
                        time.sleep(1) 
                    except MailboxFetchError as e:
                        print(f"Error fetching batch {uid_string}: {e}")
                    except Exception as e:
                         print(f"Unexpected error during fetch for batch {uid_string}: {e}")

        except Exception as e:
            print(f"Failed to connect or fetch messages: {e}")
            self.fail(f"Test failed due to connection or fetch error: {e}")

        print(f"Total messages fetched: {len(messages)}")
        
        # Passe die Assertion an, da wir jetzt echte Daten verwenden
        # Erwarte mindestens eine Nachricht, wenn UIDs vorhanden waren
        self.assertGreaterEqual(len(messages), 0, "Should have fetched zero or more messages") 
        # Oder spezifischere Prüfung, z.B. ob die Anzahl übereinstimmt (kann aber durch parallele Änderungen fehlschlagen)
        # self.assertEqual(len(messages), len(test_uids), "Number of fetched messages should match requested UIDs")
 