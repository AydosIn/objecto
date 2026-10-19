import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


def exhibit_upload_to(instance, filename):
    """exhibits/2026/10/<random hex>.jpg — the original filename is never used,
    so photo paths can't be guessed and can't leak names like 'my-bedroom.jpg'."""
    extension = Path(filename).suffix.lower() or '.jpg'
    return f'exhibits/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{extension}'


def validate_rivals(value):
    """Rivals must look like [{"name": "...", "reason": "..."}, ...]."""
    if not isinstance(value, list):
        raise ValidationError('Rivals must be a list.')
    for rival in value:
        if (
            not isinstance(rival, dict)
            or set(rival) != {'name', 'reason'}
            or not all(isinstance(rival[key], str) for key in ('name', 'reason'))
        ):
            raise ValidationError('Each rival needs exactly a "name" and a "reason", both text.')


class Exhibit(models.Model):
    """One photographed object and its biography."""

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exhibits'
    )
    image = models.ImageField(upload_to=exhibit_upload_to)
    object_type = models.CharField(
        max_length=100, help_text='What the object is, e.g. "ceramic mug".'
    )

    # The biography
    name = models.CharField(max_length=100, help_text='e.g. "Gerald"')
    title = models.CharField(max_length=200, help_text='e.g. "Mug of the Third Shelf"')
    placard = models.CharField(max_length=255, help_text='One line for the gallery card.')
    origin_story = models.TextField()
    trauma = models.TextField()
    rivals = models.JSONField(
        default=list,
        blank=True,
        validators=[validate_rivals],
        help_text='A list like [{"name": "The Dishwasher", "reason": "..."}]',
    )
    hopes_and_fears = models.TextField('hopes and fears')
    opinion_of_owner = models.TextField('opinion of owner')

    model_name = models.CharField(
        max_length=100, blank=True, help_text='Which Gemini model wrote the biography.'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # The museum grid: one owner's exhibits, newest first.
            models.Index(fields=['owner', '-created_at']),
        ]

    def __str__(self):
        return f'{self.name}, {self.title}'


class GenerationLog(models.Model):
    """One row per Gemini call. Used for the daily limit and for debugging in the admin."""

    class Kind(models.TextChoices):
        CREATE = 'create', 'New exhibit'
        REGENERATE = 'regenerate', 'Regenerate'
        RENAME = 'rename', 'Rename + regenerate'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='generation_logs'
    )
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.CREATE)
    success = models.BooleanField()
    error = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # The daily limit: count one user's generations since midnight.
            models.Index(fields=['user', 'created_at']),
        ]

    def __str__(self):
        status = 'ok' if self.success else 'failed'
        return f'{self.user} · {self.get_kind_display()} · {status}'
