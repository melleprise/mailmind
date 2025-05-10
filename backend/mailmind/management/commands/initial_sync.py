from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.conf import settings
from mailmind.core.models import EmailAccount
from django_q.tasks import async_task

User = get_user_model()

class Command(BaseCommand):
    help = 'Queues a full initial synchronization task for all email accounts of a specified user.'

    def add_arguments(self, parser):
        parser.add_argument('--user-id', type=int, help='ID of the user to sync accounts for.')
        parser.add_argument('--user-email', type=str, help='Email of the user to sync accounts for.')
        # Remove the timeout argument as it's no longer relevant here
        # parser.add_argument(
        #     '--timeout', 
        #     type=int, 
        #     default=60, 
        #     help='Timeout in seconds for IMAP operations like SELECT (default: 60).'
        # )

    # Make handle synchronous again
    def handle(self, *args, **options):
        user_id = options['user_id']
        user_email = options['user_email']

        if not user_id and not user_email:
            raise CommandError('You must provide either --user-id or --user-email.')
        if user_id and user_email:
            raise CommandError('Provide either --user-id or --user-email, not both.')

        try:
            if user_id:
                # Use synchronous get
                user = User.objects.get(id=user_id) 
            else:
                # Use synchronous get
                user = User.objects.get(email=user_email) 
            self.stdout.write(self.style.SUCCESS(f'Found user: {user.email}'))
        except User.DoesNotExist:
            raise CommandError(f'User with specified identifier not found.')

        # Use synchronous filter and count
        accounts = EmailAccount.objects.filter(user=user)
        account_count = accounts.count() 

        if account_count == 0:
            self.stdout.write(self.style.WARNING(f'No email accounts found for user {user.email}.'))
            return

        self.stdout.write(f'Found {account_count} email account(s) for user {user.email}. Queuing sync tasks...')

        queued_count = 0
        # Iterate synchronously
        for account in accounts:
            self.stdout.write(f'--- Queuing sync for account: {account.email} (ID: {account.id}) ---')
            try:
                # Queue the existing background task with the CORRECT path
                async_task('mailmind.imap.sync.sync_account', account.id)
                self.stdout.write(self.style.SUCCESS(f'Successfully queued sync task for account ID: {account.id}'))
                queued_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'Failed to queue task for account {account.email} (ID: {account.id}): {e}'))

        self.stdout.write(self.style.SUCCESS(f'Finished queuing {queued_count}/{account_count} sync tasks.')) 