"""
WSGI config for mailmind project.
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mailmind.settings')

application = get_wsgi_application() 