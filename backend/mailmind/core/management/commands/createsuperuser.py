from django.contrib.auth.management.commands.createsuperuser import Command as BaseCommand, NotRunningInTTYException
from django.core.management.base import CommandError


class Command(BaseCommand):
    email_field = 'email'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            dest='email',
            help='Specifies the email for the superuser.',
        )
        parser.add_argument(
            '--noinput', '--no-input',
            action='store_false', dest='interactive', default=True,
            help='Tells Django to NOT prompt the user for input of any kind.',
        )

    def handle(self, *args, **options):
        email = options.get('email')
        database = options.get('database')
        user_data = {}
        
        try:
            if not email and not options.get('interactive'):
                raise CommandError('You must use --email with --noinput.')
            
            if not email:
                try:
                    email = self.get_input_data(self.email_field, 'Email address')
                except KeyboardInterrupt:
                    self.stderr.write('\nOperation cancelled.')
                    return
                
            user_data[self.email_field] = email
            user_data['password'] = options.get('password')
            
            self.UserModel._default_manager.db_manager(database).create_superuser(**user_data)
            
            if options.get('verbosity', 1) >= 1:
                self.stdout.write("Superuser created successfully.")
        except KeyboardInterrupt:
            self.stderr.write('\nOperation cancelled.')
            return
        except Exception as e:
            raise CommandError(e)