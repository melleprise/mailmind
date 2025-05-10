import argparse
from django.core.management.base import BaseCommand, CommandError
from mailmind.core.models import Email
# Import direkt aus embedding_tasks, da __init__ nicht mehr alle Tasks exportiert
from mailmind.ai.embedding_tasks import generate_embeddings_for_email
from django_q.tasks import async_task
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Processes emails using AI to generate suggestions and prepare for RAG. Queues tasks for background processing.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email-id',
            type=int,
            help='Process a single email by its ID.',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all emails that have not been AI-processed yet (ai_processed=False).',
        )
        parser.add_argument(
            '--reprocess',
            action='store_true',
            help='Reprocess all emails, generating new embeddings and AI suggestions, overwriting existing ones.',
        )

    def handle(self, *args, **options):
        email_id = options['email_id']
        process_all = options['all']
        reprocess = options['reprocess']

        if email_id and (process_all or reprocess):
            raise CommandError('Cannot use --email-id with --all or --reprocess.')
        if not email_id and not process_all and not reprocess:
            raise CommandError('Must specify either --email-id, --all, or --reprocess.')

        emails_to_process = []
        if email_id:
            try:
                email = Email.objects.prefetch_related('attachments').get(pk=email_id)
                emails_to_process.append(email)
                self.stdout.write(self.style.NOTICE(f'Found email with ID {email_id}.'))
            except Email.DoesNotExist:
                raise CommandError(f'Email with ID "{email_id}" does not exist.')
        elif process_all:
            emails_to_process = Email.objects.filter(ai_processed=False).prefetch_related('attachments')
            count = emails_to_process.count()
            self.stdout.write(self.style.NOTICE(f'Found {count} emails not yet AI-processed.'))
        elif reprocess:
            emails_to_process = Email.objects.all().prefetch_related('attachments')
            count = emails_to_process.count()
            self.stdout.write(self.style.WARNING(f'Queueing reprocessing for all {count} emails.'))

        if not emails_to_process:
            self.stdout.write(self.style.SUCCESS('No emails found to process based on criteria.'))
            return

        queued_count = 0
        for email in emails_to_process:
            self.stdout.write(f'Queueing AI processing for email ID: {email.id} (Subject: "{email.subject[:50]}...")')
            try:
                logger.info(f"Scheduling embedding generation task for email ID {email.id}")
                async_task('mailmind.ai.embedding_tasks.generate_embeddings_for_email', email.id)
                queued_count += 1
            except Exception as task_error:
                logger.error(f"Error scheduling task for email ID {email.id}: {task_error}")
        
        self.stdout.write(self.style.SUCCESS(f'Successfully queued {queued_count} email(s) for AI processing.')) 