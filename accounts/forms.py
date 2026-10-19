from django import forms
from django.contrib.auth.forms import (
    AdminUserCreationForm,
    BaseUserCreationForm,
    UserChangeForm as BaseUserChangeForm,
)
from django.core.exceptions import ValidationError

from .models import Profile, User


class UniqueEmailMixin:
    """Stores emails lowercased and rejects ones that differ only in case."""

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("there's already an account with this email.")
        return email


class SignupForm(UniqueEmailMixin, BaseUserCreationForm):
    class Meta:
        model = User
        fields = ('email',)


class UserAdminCreationForm(UniqueEmailMixin, AdminUserCreationForm):
    class Meta:
        model = User
        fields = ('email',)


class UserAdminChangeForm(BaseUserChangeForm):
    class Meta:
        model = User
        fields = '__all__'


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('display_name', 'about_me')
        widgets = {
            'about_me': forms.Textarea(attrs={'rows': 4}),
        }
