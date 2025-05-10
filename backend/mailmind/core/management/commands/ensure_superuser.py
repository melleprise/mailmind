import os
from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Creates a superuser if none exists, using environment variables for credentials.'

    def handle(self, *args, **options):
        User = get_user_model()
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not email or not password:
            logger.info('--- Skipping ensure_superuser: DJANGO_SUPERUSER_EMAIL or DJANGO_SUPERUSER_PASSWORD not set ---')
            self.stdout.write(self.style.WARNING('Superuser creation skipped: Environment variables not set.'))
            return

        if User.objects.filter(email=email).exists():
            logger.info(f'--- Skipping ensure_superuser: Superuser with email {email} already exists ---')
            self.stdout.write(self.style.SUCCESS(f"Superuser '{email}' already exists."))
            # Optional: Update existing superuser's password?
            # user = User.objects.get(email=email)
            # user.set_password(password)
            # user.is_staff = True
            # user.is_superuser = True
            # user.save()
            # self.stdout.write(self.style.SUCCESS(f'Superuser '{email}' password updated.'))
        else:
            logger.info(f'--- Creating superuser: {email} ---')
            try:
                User.objects.create_superuser(email=email, password=password)
                logger.info(f'--- Superuser {email} created successfully ---')
                self.stdout.write(self.style.SUCCESS(f"Superuser '{email}' created successfully."))
            except Exception as e:
                 logger.error(f"--- Error creating superuser {email}: {e} ---", exc_info=True)
                 self.stderr.write(self.style.ERROR(f"Error creating superuser '{email}': {e}")) 