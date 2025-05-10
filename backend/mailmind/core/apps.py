from django.apps import AppConfig

class CoreConfig(AppConfig):
    name = 'mailmind.core'
    verbose_name = 'MailMind Core'
    
    def ready(self):
        """
        Import signal handlers when app is ready.
        """
        # Import signals to register them
        import mailmind.core.signals 