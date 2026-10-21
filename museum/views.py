import io
import mimetypes
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.utils.text import slugify
from django.views import View
from django.views.generic import DeleteView, DetailView, FormView, ListView, TemplateView
from django.views.generic.detail import SingleObjectMixin

from .forms import ExhibitUploadForm, RenameForm
from .models import Exhibit, GenerationLog
from .services.aura import RAMP, aura_from_bytes, aura_of, slide_fields
from .services.gemini import BiographyError, BiographyHints, generate_biography
from .services.limits import limit_reached, lock_quota, quota_context
from .services.pdf import build_pdf


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


def read_photo(exhibit):
    """The stored photo's bytes, or None when the file is missing."""
    try:
        with exhibit.image.open('rb') as stored:
            return stored.read()
    except OSError:
        return None


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


def share_context(request, exhibit, pdf_url):
    """What the share buttons need: the public link (if sharing is on), the words that
    go with it, and the PDF."""
    return {
        'share_url': (
            request.build_absolute_uri(reverse('shared', args=[exhibit.share_token]))
            if exhibit.is_shared
            else ''
        ),
        'share_text': f'{exhibit.name}, the {exhibit.object_type}: “{exhibit.placard}”'.lower(),
        'pdf_url': pdf_url,
        'pdf_filename': pdf_filename(exhibit),
    }


def pdf_filename(exhibit):
    return f'{slugify(f"{exhibit.name} the {exhibit.object_type}") or "exhibit"}.pdf'


def pdf_response(request, exhibit, opinion_heading):
    image_bytes = read_photo(exhibit)
    if image_bytes is None:
        raise Http404('The photo is missing.')
    site_url = request.build_absolute_uri('/').rstrip('/')
    pdf = build_pdf(exhibit, image_bytes, aura_of(exhibit), site_url, opinion_heading)
    return FileResponse(
        io.BytesIO(pdf), as_attachment=True, filename=pdf_filename(exhibit),
        content_type='application/pdf',
    )


class ExhibitDetailView(OwnedExhibitMixin, DetailView):
    template_name = 'museum/exhibit_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rename_form'] = RenameForm(initial={'object_type': self.object.object_type})
        context.update(recap_colours(self.object))
        context.update(quota_context(self.request.user))
        context.update(
            share_context(self.request, self.object, reverse('museum:pdf', args=[self.object.pk]))
        )
        # ?rename=1 and ?share=1 open their sheets from the server, for browsers without
        # JavaScript (and ?share=1 right after making a link).
        context['rename_open'] = self.request.GET.get('rename') == '1'
        context['share_open'] = self.request.GET.get('share') == '1'
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
        image_bytes = read_photo(exhibit)
        if image_bytes is None:
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


# --- Sharing -------------------------------------------------------------------------


class ExhibitShareView(OwnedExhibitMixin, SingleObjectMixin, View):
    """Turn on the public link and reopen the share sheet with it."""

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        exhibit = self.get_object()
        exhibit.start_sharing()
        return redirect(f'{exhibit.get_absolute_url()}?share=1')


class ExhibitUnshareView(OwnedExhibitMixin, SingleObjectMixin, View):
    """Turn the public link off. The old link 404s from now on, even if shared again."""

    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        exhibit = self.get_object()
        exhibit.stop_sharing()
        messages.success(request, f'link deleted. only you can see {exhibit.name.lower()} now.')
        return redirect(exhibit)


class ExhibitPdfView(OwnedExhibitMixin, SingleObjectMixin, View):
    """The owner's PDF. Works whether or not sharing is on."""

    http_method_names = ['get', 'head']

    def get(self, request, *args, **kwargs):
        return pdf_response(request, self.get_object(), 'what it thinks of you')


class SharedExhibitMixin(SingleObjectMixin):
    """The public side of a shared exhibit: anyone with the link, no login needed.
    Only the exhibit with that token, so stopping sharing turns all of these into 404s.
    Search engines are asked to stay out: a link is for the people it was sent to."""

    model = Exhibit
    context_object_name = 'exhibit'
    slug_field = 'share_token'
    slug_url_kwarg = 'token'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response


class SharedExhibitView(SharedExhibitMixin, DetailView):
    template_name = 'museum/shared.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        token = self.object.share_token
        context.update(recap_colours(self.object))
        context.update(share_context(self.request, self.object, reverse('shared-pdf', args=[token])))
        context['photo_url'] = reverse('shared-photo', args=[token])
        # Link previews (Telegram, iMessage, WhatsApp) need the full address.
        context['preview_image'] = self.request.build_absolute_uri(context['photo_url'])
        return context


class SharedPhotoView(SharedExhibitMixin, View):
    """The photo at a stable address, for the page and for link previews (stored photos
    otherwise get signed links that expire)."""

    http_method_names = ['get', 'head']

    def get(self, request, *args, **kwargs):
        image_bytes = read_photo(self.get_object())
        if image_bytes is None:
            raise Http404('The photo is missing.')
        response = FileResponse(io.BytesIO(image_bytes), content_type='image/jpeg')
        response['Cache-Control'] = 'max-age=3600'
        return response


class SharedPdfView(SharedExhibitMixin, View):
    http_method_names = ['get', 'head']

    def get(self, request, *args, **kwargs):
        return pdf_response(request, self.get_object(), 'what it thinks of its human')
