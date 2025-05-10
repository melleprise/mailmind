import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from mailmind.core.models import Email, AISuggestion

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Deletes all AI suggestions and resets the ai_processed flag on related emails.'

    def handle(self, *args, **options):
        self.stdout.write("Starting to reset AI suggestions...")

        # IDs der Emails sammeln, die Vorschläge haben (BEVOR wir sie löschen)
        email_ids_with_suggestions = set(AISuggestion.objects.values_list('email_id', flat=True))
        self.stdout.write(f"Found {len(email_ids_with_suggestions)} emails with existing suggestions.")

        # Alle AI Suggestions löschen
        deleted_count, _ = AISuggestion.objects.all().delete()
        self.stdout.write(self.style.SUCCESS(f"Successfully deleted {deleted_count} AI suggestion(s)."))

        # ai_processed Flag für die betroffenen Emails zurücksetzen
        if email_ids_with_suggestions:
            self.stdout.write(f"Resetting ai_processed flag for {len(email_ids_with_suggestions)} email(s)...")
            updated_email_count = Email.objects.filter(pk__in=email_ids_with_suggestions).update(
                ai_processed=False,
                ai_processed_at=None
            )
            self.stdout.write(self.style.SUCCESS(f"Successfully reset flags for {updated_email_count} email(s)."))
        else:
            self.stdout.write("No emails found with suggestions, skipping flag reset.")

        self.stdout.write("Finished resetting AI suggestions.") 