from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserAdminChangeForm, UserAdminCreationForm
from .models import Profile, User


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserAdminChangeForm
    add_form = UserAdminCreationForm

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        (
            'Permissions',
            {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')},
        ),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'usable_password', 'password1', 'password2'),
            },
        ),
    )

    list_display = ('email', 'display_name', 'is_staff', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    list_select_related = ('profile',)
    search_fields = ('email', 'profile__display_name')
    ordering = ('-date_joined',)

    def get_inlines(self, request, obj):
        # On the add page the post_save signal creates the profile, so an inline
        # there would try to create a second one.
        return [ProfileInline] if obj else []

    @admin.display(description='Display name', ordering='profile__display_name')
    def display_name(self, obj):
        return obj.profile.display_name


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'display_name', 'about_me')
    list_select_related = ('user',)
    search_fields = ('user__email', 'display_name')
