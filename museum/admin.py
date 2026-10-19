from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.utils.html import format_html

from .models import Exhibit, GenerationLog, SystemPrompt


class SystemPromptForm(forms.ModelForm):
    # A plain checkbox, not the model's is_active field: if it were, form validation
    # would reject activating this version while another one is still active, before
    # save_model gets the chance to switch the old one off.
    activate = forms.BooleanField(
        label='Active',
        required=False,
        help_text='The active version is used for every new biography. Only one can be active.',
    )

    class Meta:
        model = SystemPrompt
        fields = ('label', 'text')
        widgets = {
            'text': forms.Textarea(
                attrs={
                    'rows': 34,
                    'style': 'width: 100%; font-family: ui-monospace, Menlo, monospace; font-size: 13px;',
                }
            ),
        }

    def clean_text(self):
        text = normalize_prompt(self.cleaned_data['text'])
        if len(text) < 100:
            raise ValidationError('That is too short to guide Gemini. Describe the voice, rules and fields.')
        return text

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['activate'].initial = self.instance.is_active


def normalize_prompt(text):
    # Browsers send textarea line breaks as \r\n; store and compare them as \n.
    return text.replace('\r\n', '\n').strip()


@admin.register(SystemPrompt)
class SystemPromptAdmin(admin.ModelAdmin):
    """Edit the museum's voice without touching code. Editing the text never changes an
    existing version: it is saved as a new one, so every past version stays available."""

    form = SystemPromptForm
    list_display = ('version', 'label', 'is_active', 'exhibit_count', 'created_at', 'created_by')
    list_display_links = ('version', 'label')
    list_filter = ('is_active',)
    list_select_related = ('created_by',)
    search_fields = ('label', 'text')
    readonly_fields = ('word_count', 'exhibit_count', 'created_at', 'created_by')
    actions = ['make_active']
    fieldsets = (
        (
            None,
            {
                'fields': ('label', 'activate', 'text', 'word_count'),
                'description': (
                    'Saving a change to the text creates a <strong>new version</strong>; this one '
                    'stays as it is. Tick "active" to use it for every new biography right away. '
                    'The answer\'s structure (name, title, trauma, rivals…) is enforced by the code, '
                    'so a prompt edit can change the stories but cannot break the app. Keep the '
                    'field descriptions in the text so Gemini knows what each field is for.'
                ),
            },
        ),
        ('History', {'fields': ('exhibit_count', 'created_at', 'created_by')}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(exhibit_total=Count('exhibits'))

    def get_changeform_initial_data(self, request):
        # "Add" starts from the active text, so a new version is an edit, not a blank page.
        initial = super().get_changeform_initial_data(request)
        active = SystemPrompt.active()
        if active:
            initial.setdefault('text', active.text)
        return initial

    def save_model(self, request, obj, form, change):
        text_changed = change and obj.text != normalize_prompt(form.initial.get('text', ''))
        obj.is_active = form.cleaned_data['activate']
        with transaction.atomic():
            if text_changed:
                old_version = obj.pk
                obj.pk = None
                obj._state.adding = True
                self.message_user(
                    request,
                    f'Your edit was saved as a new version. v{old_version} is unchanged.',
                    messages.INFO,
                )
            if obj.pk is None:
                obj.created_by = request.user
            if obj.is_active:
                SystemPrompt.objects.filter(is_active=True).exclude(pk=obj.pk).update(is_active=False)
            obj.save()
        if not SystemPrompt.active():
            self.message_user(
                request,
                'No version is active, so the default prompt from the code is being used.',
                messages.WARNING,
            )

    def has_delete_permission(self, request, obj=None):
        # The active version can't be deleted; activate another one first.
        if obj is not None and obj.is_active:
            return False
        return super().has_delete_permission(request, obj)

    def get_actions(self, request):
        # Bulk delete would bypass the "not the active one" rule above.
        actions = super().get_actions(request)
        actions.pop('delete_selected', None)
        return actions

    @admin.action(description='Make the selected version active')
    def make_active(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Select exactly one version to activate.', messages.ERROR)
            return
        prompt = queryset.get()
        with transaction.atomic():
            SystemPrompt.objects.filter(is_active=True).exclude(pk=prompt.pk).update(is_active=False)
            SystemPrompt.objects.filter(pk=prompt.pk).update(is_active=True)
        self.message_user(request, f'{prompt} is now active.', messages.SUCCESS)

    @admin.display(description='Version', ordering='pk')
    def version(self, obj):
        return f'v{obj.pk}'

    @admin.display(description='Exhibits written', ordering='exhibit_total')
    def exhibit_count(self, obj):
        return getattr(obj, 'exhibit_total', None) if obj.pk else 0

    @admin.display(description='Length')
    def word_count(self, obj):
        return f'{len(obj.text.split())} words' if obj.text else '—'


@admin.register(Exhibit)
class ExhibitAdmin(admin.ModelAdmin):
    list_display = ('thumbnail', 'name', 'title', 'object_type', 'owner', 'created_at')
    list_display_links = ('thumbnail', 'name')
    list_filter = ('owner', 'model_name', 'prompt_version')
    list_select_related = ('owner',)
    search_fields = ('name', 'title', 'object_type', 'placard', 'owner__email')
    date_hierarchy = 'created_at'
    autocomplete_fields = ('owner',)
    readonly_fields = ('image_preview', 'created_at', 'updated_at')

    fieldsets = (
        ('Object', {'fields': ('owner', 'image', 'image_preview', 'object_type')}),
        (
            'Biography',
            {
                'fields': (
                    'name',
                    'title',
                    'placard',
                    'origin_story',
                    'trauma',
                    'rivals',
                    'hopes_and_fears',
                    'opinion_of_owner',
                )
            },
        ),
        ('Generation', {'fields': ('model_name', 'prompt_version', 'created_at', 'updated_at')}),
    )

    @admin.display(description='Photo')
    def thumbnail(self, obj):
        return self._img(obj, size=48)

    @admin.display(description='Preview')
    def image_preview(self, obj):
        return self._img(obj, size=240)

    def _img(self, obj, size):
        if not obj.image:
            return '—'
        return format_html(
            '<img src="{}" alt="{}" style="width:{}px;height:{}px;object-fit:cover;border-radius:4px">',
            obj.image.url,
            obj.name,
            size,
            size,
        )


@admin.register(GenerationLog)
class GenerationLogAdmin(admin.ModelAdmin):
    """Read-only: logs are written by the app, never by hand."""

    list_display = ('created_at', 'user', 'kind', 'success', 'error')
    list_filter = ('success', 'kind')
    list_select_related = ('user',)
    search_fields = ('user__email', 'error')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
