from django.apps import AppConfig


class MuseumConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'museum'

    def ready(self):
        # Connects the post_delete handler that removes an exhibit's photo file.
        from . import signals  # noqa: F401
