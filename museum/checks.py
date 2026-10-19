from django.conf import settings
from django.core.checks import Warning, register


@register()
def gemini_settings_check(app_configs, **kwargs):
    """Shown when runserver starts, so a missing key is obvious before the first upload."""
    missing = [name for name in ('GEMINI_API_KEY', 'GEMINI_MODEL') if not getattr(settings, name)]
    if not missing:
        return []
    return [
        Warning(
            f'{" and ".join(missing)} not set: biographies cannot be generated.',
            hint='Add them to .env (see .env.example).',
            id='museum.W001',
        )
    ]
