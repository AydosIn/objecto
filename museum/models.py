import uuid
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
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


class SystemPrompt(models.Model):
    """A version of the instructions Gemini gets. Edited in the admin, never in place:
    every edit is saved as a new version, and exactly one version is active."""

    label = models.CharField(
        max_length=100, help_text='A short note on what changed, e.g. "More dramatic narrator".'
    )
    text = models.TextField()
    is_active = models.BooleanField(
        'active',
        default=False,
        help_text='The active version is used for every new biography. Only one can be active.',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
    )

    class Meta:
        ordering = ['-created_at']
        constraints = [
            # The database itself refuses a second active prompt.
            models.UniqueConstraint(
                fields=['is_active'],
                condition=models.Q(is_active=True),
                name='only_one_active_system_prompt',
            ),
        ]

    def __str__(self):
        return f'v{self.pk} · {self.label}'

    @classmethod
    def active(cls):
        """The active version, or None (then the default prompt in prompts.py is used)."""
        return cls.objects.filter(is_active=True).first()


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
    aura = models.CharField(
        max_length=20,
        blank=True,
        help_text='Colour of its recap, from the photo (services/aura.py). Empty = not worked out yet.',
    )
    prompt_version = models.ForeignKey(
        SystemPrompt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='exhibits',
        help_text='Which system prompt wrote the biography. Empty = the default prompt in code.',
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

    def get_absolute_url(self):
        return reverse('museum:detail', args=[self.pk])


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

    # For the analytics page. Rows from before these fields existed have no
    # duration and zero tokens; analytics treats them as "not recorded".
    duration_ms = models.PositiveIntegerField(
        null=True, blank=True, help_text='How long the Gemini call took.'
    )
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    thinking_tokens = models.PositiveIntegerField(default=0, help_text='Billed as output.')
    model_name = models.CharField(max_length=100, blank=True)
    prompt_version = models.ForeignKey(
        SystemPrompt,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generation_logs',
    )
    exhibit = models.ForeignKey(
        Exhibit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='generation_logs',
        help_text='The exhibit this call created or rewrote (empty if it failed or was deleted).',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            # The daily limit: count one user's generations since midnight.
            models.Index(fields=['user', 'created_at']),
            # Analytics: everything in a date range.
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        status = 'ok' if self.success else 'failed'
        return f'{self.user} · {self.get_kind_display()} · {status}'

    @property
    def billed_output_tokens(self):
        return self.output_tokens + self.thinking_tokens
