from django.apps import AppConfig

class EventsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'events'

    def ready(self):
        """
        This method is called when the Django application is ready.
        It's the perfect place to start our background scheduler.
        This simplified version ensures the scheduler runs reliably.
        """
        # We import here to prevent premature loading issues.
        from . import scheduler
        scheduler.start()

