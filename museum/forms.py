from django import forms
from django.core.exceptions import ValidationError

from .services.images import InvalidImage, process_upload


class ExhibitUploadForm(forms.Form):
    # A plain FileField: services/images.py does all the image checks in one place.
    # No `capture` attribute, so phones offer both "Take Photo" and "Photo Library".
    image = forms.FileField(
        label='Photo of the object',
        widget=forms.FileInput(attrs={'accept': 'image/*'}),
        error_messages={'required': 'Choose or take a photo first.'},
    )

    def clean_image(self):
        upload = self.cleaned_data['image']
        try:
            # Kept on the form so the view can save the cleaned JPEG.
            self.processed_image = process_upload(upload)
        except InvalidImage as error:
            raise ValidationError(str(error))
        return upload


class RenameForm(forms.Form):
    object_type = forms.CharField(
        label='What is it really?',
        max_length=100,
        strip=True,
        error_messages={
            'required': 'Tell us what the object really is.',
            'max_length': 'Keep it under 100 characters.',
        },
        widget=forms.TextInput(
            attrs={'placeholder': 'e.g. glass vase', 'autocomplete': 'off', 'autofocus': True}
        ),
    )
