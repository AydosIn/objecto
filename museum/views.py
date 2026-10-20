import mimetypes
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DeleteView, DetailView, FormView, ListView, TemplateView
from django.views.generic.detail import SingleObjectMixin

from .forms import ExhibitUploadForm, RenameForm
from .models import Exhibit, GenerationLog
from .services.aura import RAMP, aura_from_bytes, aura_of, slide_fields
from .services.gemini import BiographyError, BiographyHints, generate_biography
from .services.limits import limit_reached, lock_quota, quota_context


def hints_for(user, object_type=''):
    profile = getattr(user, 'profile', None)
    return BiographyHints(
        object_type=object_type,
        owner_name=profile.display_name if profile else '',
        about_me=profile.about_me if profile else '',
    )


def log_generation(user, kind, started, *, biography=None, error=None, exhibit=None):
    """One GenerationLog row per Gemini call, success or not, with timing and tokens."""
    source = biography or error
    usage = getattr(source, 'usage', None) or {}
    GenerationLog.objects.create(
        user=user,
        kind=kind,
        success=error is None,
        error=str(error)[:255] if error else '',
        duration_ms=round((time.monotonic() - started) * 1000),
        input_tokens=usage.get('input_tokens', 0),
        output_tokens=usage.get('output_tokens', 0),
        thinking_tokens=usage.get('thinking_tokens', 0),
        model_name=biography.model_name if biography else settings.GEMINI_MODEL,
        prompt_version=getattr(source, 'prompt_version', None),
        exhibit=exhibit,
    )


class OwnedExhibitMixin(LoginRequiredMixin):
    """Every exhibit view only sees the current user's exhibits, so anyone
    else's is a 404 and its existence isn't revealed (FR-3)."""

    model = Exhibit
    context_object_name = 'exhibit'

    def get_queryset(self):
        return Exhibit.objects.filter(owner=self.request.user)


class LandingView(TemplateView):
    """The public front page. Logged-in visitors go straight to their museum."""

    template_name = 'landing.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('museum:index')
        return super().dispatch(request, *args, **kwargs)


class MuseumView(LoginRequiredMixin, ListView):
    """Your exhibits, newest first, as tiles in each one's aura colour."""

    template_name = 'museum/museum.html'
    paginate_by = 24

    def get_queryset(self):
        return Exhibit.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tiles'] = [(exhibit, aura_of(exhibit)) for exhibit in context['object_list']]
        return context


class ExhibitCreateView(LoginRequiredMixin, FormView):
    form_class = ExhibitUploadForm
    template_name = 'museum/exhibit_new.html'

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), **quota_context(self.request.user)}

    def form_valid(self, form):
        user = self.request.user
        photo = form.processed_image

        # The whole interview holds the quota lock, so parallel uploads can't all pass
        # the limit check before any of them is logged.
        with transaction.atomic():
            lock_quota(user)
            # Out of interviews: stop before Gemini, so it costs nothing.
            if message := limit_reached(user):
                form.add_error('image', message)
                return self.form_invalid(form)

            # Gemini first: if it fails, nothing (no exhibit, no file) has been saved yet.
            started = time.monotonic()
            try:
                biography = generate_biography(photo.content, photo.mime_type, hints_for(user))
            except BiographyError as error:
                log_generation(user, GenerationLog.Kind.CREATE, started, error=error)
                form.add_error('image', error.user_message)
                return self.form_invalid(form)

            exhibit = Exhibit(
                owner=user, aura=aura_from_bytes(photo.content).slug, **biography.as_model_fields()
            )
            # The stored file is the cleaned JPEG, never the original upload.
            exhibit.image.save('photo.jpg', ContentFile(photo.content), save=False)
            exhibit.save()
            log_generation(
                user, GenerationLog.Kind.CREATE, started, biography=biography, exhibit=exhibit
            )
        return redirect(exhibit)


def recap_colours(exhibit):
    """The exhibit's aura (from its photo) and one colour per recap slide."""
    aura = aura_of(exhibit)
    return {'aura': aura, 'fields': slide_fields(aura, len(RAMP))}


class ExhibitDetailView(OwnedExhibitMixin, DetailView):
    template_name = 'museum/exhibit_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rename_form'] = RenameForm(initial={'object_type': self.object.object_type})
        context.update(recap_colours(self.object))
        context.update(quota_context(self.request.user))
        # ?rename=1 opens the rename sheet from the server, for browsers without JavaScript.
        context['rename_open'] = self.request.GET.get('rename') == '1'
        return context


class RewriteBiographyView(OwnedExhibitMixin, SingleObjectMixin, View):
    """Base for Regenerate and Rename: send the stored photo to Gemini again and
    replace the biography. On failure the old biography stays untouched."""

    http_method_names = ['post']
    kind = None

    def rewrite(self, exhibit, object_type):
        # Holds the quota lock for the whole interview, like ExhibitCreateView.
        with transaction.atomic():
            lock_quota(self.request.user)
            return self._rewrite(exhibit, object_type)

    def _rewrite(self, exhibit, object_type):
        user = self.request.user
        if message := limit_reached(user):
            messages.error(self.request, message)
            return redirect(exhibit)
        try:
            with exhibit.image.open('rb') as stored:
                image_bytes = stored.read()
        except OSError:
            messages.error(self.request, "this one's photo is missing, so it can't be rewritten.")
            return redirect(exhibit)

        mime_type = mimetypes.guess_type(exhibit.image.name)[0] or 'image/jpeg'
        started = time.monotonic()
        try:
            biography = generate_biography(image_bytes, mime_type, hints_for(user, object_type))
        except BiographyError as error:
            log_generation(user, self.kind, started, error=error, exhibit=exhibit)
            messages.error(self.request, error.user_message)
            return redirect(exhibit)

        for field, value in biography.as_model_fields().items():
            setattr(exhibit, field, value)
        # Whatever Gemini calls it, the user's wording wins.
        exhibit.object_type = object_type
        exhibit.save()
        log_generation(user, self.kind, started, biography=biography, exhibit=exhibit)
        messages.success(self.request, self.success_message(exhibit))
        return redirect(exhibit)


class ExhibitRegenerateView(RewriteBiographyView):
    kind = GenerationLog.Kind.REGENERATE

    def post(self, request, *args, **kwargs):
        exhibit = self.get_object()
        # Keep the current object type, so a renamed object stays renamed.
        return self.rewrite(exhibit, exhibit.object_type)

    def success_message(self, exhibit):
        return f'{exhibit.name.lower()} sat down for a second interview.'


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
        return f'sorry, {exhibit.object_type.lower()}. your real story is up.'


class ExhibitDeleteView(OwnedExhibitMixin, DeleteView):
    template_name = 'museum/exhibit_confirm_delete.html'
    success_url = reverse_lazy('museum:index')

    def form_valid(self, form):
        # The photo file is removed by the post_delete signal (museum/signals.py).
        name = self.object.name
        response = super().form_valid(form)
        messages.success(self.request, f'{name.lower()} has left the museum.')
        return response
