from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Connects the post_save handler that gives every new user a Profile.
        from . import signals  # noqa: F401
