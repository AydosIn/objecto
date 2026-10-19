from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView

from .forms import ProfileForm, SignupForm
from .models import Profile


class SignupView(CreateView):
    form_class = SignupForm
    template_name = 'registration/signup.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)
        messages.success(self.request, "you're in. go find something to interview.")
        return redirect(settings.LOGIN_REDIRECT_URL)


class ProfileView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    form_class = ProfileForm
    template_name = 'accounts/profile.html'
    success_url = reverse_lazy('profile')
    success_message = 'saved. your stuff will judge you accordingly.'

    def get_object(self, queryset=None):
        # get_or_create covers users made before the signal existed (e.g. loaddata).
        profile, _ = Profile.objects.get_or_create(user=self.request.user)
        return profile
