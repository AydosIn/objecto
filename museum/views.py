from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import redirect
from django.views.generic import DetailView, FormView

from .forms import ExhibitUploadForm
from .models import Exhibit, GenerationLog
from .services.gemini import BiographyError, BiographyHints, generate_biography


def hints_for(user, object_type=''):
    profile = getattr(user, 'profile', None)
    return BiographyHints(
        object_type=object_type,
        owner_name=profile.display_name if profile else '',
        about_me=profile.about_me if profile else '',
    )


class ExhibitCreateView(LoginRequiredMixin, FormView):
    form_class = ExhibitUploadForm
    template_name = 'museum/exhibit_new.html'

    def form_valid(self, form):
        user = self.request.user
        photo = form.processed_image

        # Gemini first: if it fails, nothing (no row, no file) has been saved yet.
        try:
            biography = generate_biography(photo.content, photo.mime_type, hints_for(user))
        except BiographyError as error:
            GenerationLog.objects.create(
                user=user, kind=GenerationLog.Kind.CREATE, success=False, error=str(error)[:255]
            )
            form.add_error('image', error.user_message)
            return self.form_invalid(form)

        with transaction.atomic():
            exhibit = Exhibit(owner=user, **biography.as_model_fields())
            # The stored file is the cleaned JPEG, never the original upload.
            exhibit.image.save('photo.jpg', ContentFile(photo.content), save=False)
            exhibit.save()
            GenerationLog.objects.create(user=user, kind=GenerationLog.Kind.CREATE, success=True)
        return redirect(exhibit)


class ExhibitDetailView(LoginRequiredMixin, DetailView):
    template_name = 'museum/exhibit_detail.html'
    context_object_name = 'exhibit'

    def get_queryset(self):
        # Someone else's exhibit is a 404, so its existence isn't revealed (FR-3).
        return Exhibit.objects.filter(owner=self.request.user)
