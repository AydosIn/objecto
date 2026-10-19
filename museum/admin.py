from django.contrib import admin
from django.utils.html import format_html

from .models import Exhibit, GenerationLog


@admin.register(Exhibit)
class ExhibitAdmin(admin.ModelAdmin):
    list_display = ('thumbnail', 'name', 'title', 'object_type', 'owner', 'created_at')
    list_display_links = ('thumbnail', 'name')
    list_filter = ('owner', 'model_name')
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
        ('Generation', {'fields': ('model_name', 'created_at', 'updated_at')}),
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
