#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import warnings

warnings.filterwarnings("ignore", message=".*Retry and timeout are misconfigured.*", category=UserWarning)

def main():
    """Run administrative tasks."""
    # Setze DJANGO_SETTINGS_MODULE. Die Variablen aus .env.development
    # werden durch docker compose's env_file geladen.
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
    print(f"Using DJANGO_SETTINGS_MODULE: {os.environ.get('DJANGO_SETTINGS_MODULE')}")
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main() 