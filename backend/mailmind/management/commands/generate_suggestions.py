import argparse
from django.core.management.base import BaseCommand, CommandError
from mailmind.core.models import Email
# Importiere die Suggestion-Funktion
from mailmind.ai.tasks import generate_ai_suggestion
from django_q.tasks import async_task
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generates AI suggestions for emails using previously generated embeddings (if available). Queues tasks for background processing.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email-id',
            type=int,
            help='Generate suggestions for a single email by its ID.',
        )
        parser.add_argument(
            '--all-pending', # Changed from --all to avoid confusion
            action='store_true',
            help='Generate suggestions for all emails that have not been marked as AI-processed yet (ai_processed=False). Assumes embeddings exist.',
        )
        parser.add_argument(
            '--regenerate-all', # Changed from --reprocess
            action='store_true',
            help='Regenerate suggestions for ALL emails, potentially overwriting existing ones. Assumes embeddings exist.',
        )
        # Add a flag to specifically target emails that HAVE embeddings but are not yet processed
        # parser.add_argument(
        #     '--embeddings-ready',
        #     action='store_true',
        #     help='Generate suggestions only for emails with embeddings but ai_processed=False (TODO: Need a flag on Email model for embedding status)'
        # )


    def handle(self, *args, **options):
        email_id = options['email_id']
        process_all_pending = options['all_pending']
        regenerate_all = options['regenerate_all']

        if email_id and (process_all_pending or regenerate_all):
            raise CommandError('Cannot use --email-id with --all-pending or --regenerate-all.')
        if not email_id and not process_all_pending and not regenerate_all:
            raise CommandError('Must specify either --email-id, --all-pending, or --regenerate-all.')

        emails_to_process = []
        if email_id:
            try:
                # No need to prefetch attachments here
                email = Email.objects.get(pk=email_id)
                emails_to_process.append(email)
                self.stdout.write(self.style.NOTICE(f'Found email with ID {email_id} for suggestion generation.'))
            except Email.DoesNotExist:
                raise CommandError(f'Email with ID "{email_id}" does not exist.')
        elif process_all_pending:
            # Target emails not yet processed
            emails_to_process = Email.objects.filter(ai_processed=False)
            count = emails_to_process.count()
            self.stdout.write(self.style.NOTICE(f'Found {count} emails pending AI suggestions (ai_processed=False).'))
        elif regenerate_all:
            # Target all emails
            emails_to_process = Email.objects.all()
            count = emails_to_process.count()
            self.stdout.write(self.style.WARNING(f'Queueing suggestion regeneration for all {count} emails.'))

        if not emails_to_process:
            self.stdout.write(self.style.SUCCESS('No emails found to generate suggestions for based on criteria.'))
            return

        queued_count = 0
        for email in emails_to_process:
            self.stdout.write(f'Queueing AI suggestion generation for email ID: {email.id} (Subject: "{email.subject[:50]}...")')
            try:
                logger.info(f"Scheduling AI suggestion task for email ID {email.id}")
                # Schedule the suggestion task
                async_task(generate_ai_suggestion, email.id)
                queued_count += 1
            except Exception as task_error:
                logger.error(f"Error scheduling suggestion task for email ID {email.id}: {task_error}")

        self.stdout.write(self.style.SUCCESS(f'Successfully queued {queued_count} email(s) for AI suggestion generation.')) 