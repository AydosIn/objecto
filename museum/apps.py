from django.apps import AppConfig


class MuseumConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'museum'

    def ready(self):
        # Teach Pillow to open iPhone HEIC photos, everywhere in the app.
        from pillow_heif import register_heif_opener

        register_heif_opener()

        # Connects the post_delete handler that removes an exhibit's photo file,
        # and registers the startup warning for missing Gemini settings.
        from . import checks, signals  # noqa: F401
