from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.shortcuts import redirect
from django.views.generic import DetailView, FormView

from .forms import ExhibitUploadForm
from .models import Exhibit


def placeholder_biography():
    """Stands in for Gemini until Phase 5, with the same fields Gemini will return."""
    return {
        'object_type': 'mysterious object',
        'name': 'Gerald the Placeholder',
        'title': 'Keeper of the Unwritten Story',
        'placard': 'Waiting patiently for an AI to tell its tale.',
        'origin_story': 'Nobody knows where Gerald came from. Not even Gerald.',
        'trauma': 'Being photographed before the biography service was installed.',
        'rivals': [{'name': 'Lorem Ipsum', 'reason': 'Also pretends to be real text.'}],
        'hopes_and_fears': 'Hopes for Phase 5. Fears staying a placeholder forever.',
        'opinion_of_owner': 'Clearly a developer. Respects the process.',
        'model_name': 'placeholder',
    }


class ExhibitCreateView(LoginRequiredMixin, FormView):
    form_class = ExhibitUploadForm
    template_name = 'museum/exhibit_new.html'

    def form_valid(self, form):
        photo = form.processed_image
        exhibit = Exhibit(owner=self.request.user, **placeholder_biography())
        # The stored file is the cleaned JPEG, never the original upload.
        exhibit.image.save('photo.jpg', ContentFile(photo.content), save=False)
        exhibit.save()
        return redirect(exhibit)


class ExhibitDetailView(LoginRequiredMixin, DetailView):
    template_name = 'museum/exhibit_detail.html'
    context_object_name = 'exhibit'

    def get_queryset(self):
        # Someone else's exhibit is a 404, so its existence isn't revealed (FR-3).
        return Exhibit.objects.filter(owner=self.request.user)
