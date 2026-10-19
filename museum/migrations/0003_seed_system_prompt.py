from django.db import migrations

from museum.prompts import DEFAULT_SYSTEM_PROMPT


def create_first_version(apps, schema_editor):
    """Version 1 = the prompt that used to live in code, so behaviour doesn't change."""
    SystemPrompt = apps.get_model('museum', 'SystemPrompt')
    if not SystemPrompt.objects.exists():
        SystemPrompt.objects.create(
            label='Original (from code)', text=DEFAULT_SYSTEM_PROMPT, is_active=True
        )


class Migration(migrations.Migration):
    dependencies = [
        ('museum', '0002_system_prompt'),
    ]

    operations = [
        migrations.RunPython(create_first_version, migrations.RunPython.noop),
    ]
