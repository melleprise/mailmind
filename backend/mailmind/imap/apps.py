import logging
from django.apps import AppConfig
import sys

logger = logging.getLogger(__name__)

class ImapConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'mailmind.imap'

    def ready(self):
        """Wird ausgeführt, wenn die App bereit ist."""
        # Verhindere das Starten im migrate/makemigrations oder anderen Management-Befehlen
        # und stelle sicher, dass es der Hauptprozess ist (nicht der Reload-Prozess).
        # `runserver` startet oft zwei Prozesse.
        is_management_command = any(cmd in sys.argv for cmd in ['makemigrations', 'migrate', 'shell', 'test', 'collectstatic', 'qcluster'])
        is_runserver = 'runserver' in sys.argv

        # Starte den Manager nur im Haupt-runserver-Prozess (oder wenn Daphne/Gunicorn läuft)
        # und nicht bei Management-Befehlen.
        # Dies ist eine Heuristik und muss ggf. für die Produktionsumgebung angepasst werden.
        # Für Daphne/Gunicorn läuft `ready` normalerweise nur einmal pro Worker.
        if not is_management_command:
            logger.info("ImapConfig.ready(): Attempting to start IDLE Manager...")
            try:
                from . import idle_manager
                idle_manager.start_idle_manager()
            except Exception as e:
                logger.error(f"Failed to start IDLE Manager in AppConfig.ready(): {e}", exc_info=True)
        else:
            logger.info(f"ImapConfig.ready(): Skipping IDLE Manager start due to management command: {sys.argv}") 