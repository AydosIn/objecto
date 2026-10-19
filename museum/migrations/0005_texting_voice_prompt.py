from django.db import migrations

from museum.prompts import DEFAULT_SYSTEM_PROMPT


def add_texting_voice(apps, schema_editor):
    """Add the lowercase texting-voice prompt as a new version. It only becomes the
    active one when nobody has customised the prompt in the admin yet (the active
    version is still the untouched original seeded from code)."""
    SystemPrompt = apps.get_model('museum', 'SystemPrompt')
    if SystemPrompt.objects.filter(text=DEFAULT_SYSTEM_PROMPT).exists():
        return  # fresh database: version 1 already has this text
    active = SystemPrompt.objects.filter(is_active=True).first()
    untouched = active is None or (active.label == 'Original (from code)' and active.created_by_id is None)
    if untouched:
        SystemPrompt.objects.filter(is_active=True).update(is_active=False)
    SystemPrompt.objects.create(
        label='Texting voice (redesign)', text=DEFAULT_SYSTEM_PROMPT, is_active=untouched
    )


class Migration(migrations.Migration):
    dependencies = [
        ('museum', '0004_richer_generation_logs'),
    ]

    operations = [
        migrations.RunPython(add_texting_voice, migrations.RunPython.noop),
    ]
