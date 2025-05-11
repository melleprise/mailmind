#!/usr/bin/env python3
import sys
import re
import os
import json

# Füge das backend-Verzeichnis zum Python-Path hinzu
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import django

# Django Setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from mailmind.freelance.models import FreelanceProject

if len(sys.argv) != 2:
    print("Usage: getprojectbyurl <projekt-url>")
    sys.exit(1)

url = sys.argv[1]

# Extrahiere die project_id aus der URL
match = re.search(r'projekt-(\d+)', url)
if not match:
    print("Keine project_id in der URL gefunden.")
    sys.exit(2)
project_id = match.group(1)

try:
    projekt = FreelanceProject.objects.get(project_id=project_id)
    print(json.dumps({
        'project_id': projekt.project_id,
        'title': projekt.title,
        'company': projekt.company,
        'end_date': projekt.end_date,
        'location': projekt.location,
        'remote': projekt.remote,
        'last_updated': projekt.last_updated,
        'skills': projekt.skills,
        'url': projekt.url,
        'applications': projekt.applications,
        'description': projekt.description,
        'provider': projekt.provider,
        'created_at': projekt.created_at.isoformat(),
    }, ensure_ascii=False, indent=2))
except FreelanceProject.DoesNotExist:
    print(f"Kein Projekt mit project_id {project_id} gefunden.")
    sys.exit(3) 