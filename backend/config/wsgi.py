"""
WSGI config for mailmind project.
"""

import os
from django.core.wsgi import get_wsgi_application

# Setze DJANGO_SETTINGS_MODULE. Die Variablen aus .env.development
# werden durch docker compose's env_file geladen.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

application = get_wsgi_application() 