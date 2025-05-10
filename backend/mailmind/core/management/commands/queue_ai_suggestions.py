from django.core.management.base import BaseCommand
from django.db.models import Q
from mailmind.core.models import Email
from django_q.tasks import async_task

class Command(BaseCommand):
    help = 'Queues AI suggestion generation for unprocessed emails.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Queue tasks for ALL emails, ignoring the ai_processed flag.',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of emails to queue.',
        )
        parser.add_argument(
            '--exclude_processed',
            action='store_true',
            default=True, # Standardmäßig nur unverarbeitete
            help='Exclude emails already marked as ai_processed (default). Use --no-exclude_processed to override.',
        )
        parser.add_argument(
            '--task_name',
            type=str,
            default='mailmind.ai.tasks.generate_ai_suggestion',
            help='Name of the async task function to queue.',
        )

    def handle(self, *args, **options):
        task_name = options['task_name']
        self.stdout.write(f"Querying emails to queue for task '{task_name}'...")

        email_query = Email.objects.all()

        if not options['all'] and options['exclude_processed']:
            self.stdout.write("Excluding emails already marked as ai_processed.")
            email_query = email_query.filter(ai_processed=False)
        elif options['all']:
             self.stdout.write(self.style.WARNING("Processing ALL emails (including already processed ones)."))
        else: # --no-exclude_processed wurde verwendet
             self.stdout.write("Including emails already marked as ai_processed.")

        limit = options['limit']
        if limit:
            self.stdout.write(f"Limiting to {limit} emails.")
            email_query = email_query[:limit]

        count = 0
        queued_ids = []
        
        # Verwende iterator() für Speichereffizienz bei vielen E-Mails
        for email in email_query.iterator():
            try:
                async_task(task_name, email.id)
                count += 1
                queued_ids.append(email.id)
                if count % 100 == 0:
                    self.stdout.write(f"Queued {count} emails so far...")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error queuing task for email ID {email.id}: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"Successfully queued {count} email(s) for AI processing."))
        # Optional: Logge die ersten paar IDs für Debugging
        if queued_ids:
             self.stdout.write(f"Queued IDs (first 10): {queued_ids[:10]}") 