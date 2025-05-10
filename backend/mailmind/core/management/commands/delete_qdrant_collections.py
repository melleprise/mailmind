import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from qdrant_client import QdrantClient, models
from qdrant_client.http.exceptions import UnexpectedResponse

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Deletes specified collections from Qdrant.'

    # Definiere hier die Collections, die gelöscht werden sollen
    COLLECTIONS_TO_DELETE = ["email_embeddings", "attachment_embeddings"]

    def handle(self, *args, **options):
        qdrant_url = settings.QDRANT_URL
        qdrant_api_key = getattr(settings, 'QDRANT_API_KEY', None)
        client = None
        deleted_count = 0

        self.stdout.write(f"Attempting to connect to Qdrant at {qdrant_url}...")

        try:
            client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key, timeout=10)
            # client.health_check() # Veraltet/Nicht verfügbar
            client.get_collections() # Versuche stattdessen, Collections aufzulisten, um Verbindung zu prüfen
            self.stdout.write(self.style.SUCCESS("Successfully connected to Qdrant."))

            for collection_name in self.COLLECTIONS_TO_DELETE:
                self.stdout.write(f"Attempting to delete collection: {collection_name}...")
                try:
                    # Prüfen ob Collection existiert bevor sie gelöscht wird
                    try:
                         client.get_collection(collection_name=collection_name)
                         # Wenn obiges keinen Fehler wirft, existiert die Collection
                         client.delete_collection(collection_name=collection_name)
                         self.stdout.write(self.style.SUCCESS(f"Successfully deleted collection: {collection_name}"))
                         deleted_count += 1
                    except UnexpectedResponse as e:
                         if e.status_code == 404:
                              self.stdout.write(self.style.WARNING(f"Collection {collection_name} not found, skipping deletion."))
                         else:
                              # Anderer unerwarteter Fehler beim Prüfen
                              raise e # Weiterwerfen, um im äußeren Block gefangen zu werden
                    except Exception as e_check: # Fängt auch andere Fehler beim Check ab
                         self.stdout.write(self.style.ERROR(f"Error checking collection {collection_name}: {e_check}"))


                except Exception as e_del:
                    self.stdout.write(self.style.ERROR(f"Could not delete collection {collection_name}: {e_del}"))
                    logger.error(f"Failed to delete Qdrant collection {collection_name}", exc_info=True)

        except Exception as e_conn:
            self.stdout.write(self.style.ERROR(f"Qdrant connection or operation failed: {e_conn}"))
            logger.error("Failed to connect to Qdrant or perform initial operation", exc_info=True)
        finally:
             # Qdrant Client hat keine explizite close() Methode mehr in neueren Versionen
             pass 

        self.stdout.write(f"Finished deleting RAG data. Deleted {deleted_count} collection(s).") 