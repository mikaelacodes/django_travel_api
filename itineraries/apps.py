from django.apps import AppConfig


class ItinerariesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'itineraries'

    def ready(self):
        # hook up the audit-trail signals once the app is loaded
        from . import signals  # noqa: F401
