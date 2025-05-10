from django.core.management.base import BaseCommand
from mailmind.ai.download_models import download_models

class Command(BaseCommand):
    help = 'Download required ML models'

    def handle(self, *args, **options):
        self.stdout.write('Downloading ML models...')
        try:
            download_models()
            self.stdout.write(self.style.SUCCESS('Successfully downloaded models'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error downloading models: {e}'))
            raise 