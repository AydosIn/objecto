import mimetypes

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DeleteView, DetailView, FormView
from django.views.generic.detail import SingleObjectMixin

from .forms import ExhibitUploadForm, RenameForm
from .models import Exhibit, GenerationLog
from .services.gemini import BiographyError, BiographyHints, generate_biography


def hints_for(user, object_type=''):
    profile = getattr(user, 'profile', None)
    return BiographyHints(
        object_type=object_type,
        owner_name=profile.display_name if profile else '',
        about_me=profile.about_me if profile else '',
    )


class OwnedExhibitMixin(LoginRequiredMixin):
    """Every exhibit view only sees the current user's exhibits, so anyone
    else's is a 404 and its existence isn't revealed (FR-3)."""

    model = Exhibit
    context_object_name = 'exhibit'

    def get_queryset(self):
        return Exhibit.objects.filter(owner=self.request.user)


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


class ExhibitDetailView(OwnedExhibitMixin, DetailView):
    template_name = 'museum/exhibit_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rename_form'] = RenameForm(initial={'object_type': self.object.object_type})
        return context


class RewriteBiographyView(OwnedExhibitMixin, SingleObjectMixin, View):
    """Base for Regenerate and Rename: send the stored photo to Gemini again and
    replace the biography. On failure the old biography stays untouched."""

    http_method_names = ['post']
    kind = None

    def rewrite(self, exhibit, object_type):
        user = self.request.user
        try:
            with exhibit.image.open('rb') as stored:
                image_bytes = stored.read()
        except OSError:
            messages.error(self.request, "This exhibit's photo is missing, so it can't be rewritten.")
            return redirect(exhibit)

        mime_type = mimetypes.guess_type(exhibit.image.name)[0] or 'image/jpeg'
        try:
            biography = generate_biography(image_bytes, mime_type, hints_for(user, object_type))
        except BiographyError as error:
            GenerationLog.objects.create(
                user=user, kind=self.kind, success=False, error=str(error)[:255]
            )
            messages.error(self.request, error.user_message)
            return redirect(exhibit)

        with transaction.atomic():
            for field, value in biography.as_model_fields().items():
                setattr(exhibit, field, value)
            # Whatever Gemini calls it, the user's wording wins.
            exhibit.object_type = object_type
            exhibit.save()
            GenerationLog.objects.create(user=user, kind=self.kind, success=True)
        messages.success(self.request, self.success_message(exhibit))
        return redirect(exhibit)


class ExhibitRegenerateView(RewriteBiographyView):
    kind = GenerationLog.Kind.REGENERATE

    def post(self, request, *args, **kwargs):
        exhibit = self.get_object()
        # Keep the current object type, so a renamed object stays renamed.
        return self.rewrite(exhibit, exhibit.object_type)

    def success_message(self, exhibit):
        return f'{exhibit.name} sat down for a second interview.'


class ExhibitRenameView(RewriteBiographyView):
    kind = GenerationLog.Kind.RENAME

    def post(self, request, *args, **kwargs):
        exhibit = self.get_object()
        form = RenameForm(request.POST)
        if not form.is_valid():
            messages.error(request, ' '.join(form.errors['object_type']))
            return redirect(exhibit)
        return self.rewrite(exhibit, form.cleaned_data['object_type'])

    def success_message(self, exhibit):
        return f'Apologies to the {exhibit.object_type}. Its real story has been written.'


class ExhibitDeleteView(OwnedExhibitMixin, DeleteView):
    template_name = 'museum/exhibit_confirm_delete.html'
    success_url = reverse_lazy('landing')  # becomes the museum grid in Phase 7

    def form_valid(self, form):
        # The photo file is removed by the post_delete signal (museum/signals.py).
        name = self.object.name
        response = super().form_valid(form)
        messages.success(self.request, f'{name} has left the museum.')
        return response
