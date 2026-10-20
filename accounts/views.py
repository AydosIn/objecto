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
from .security import client_ip, signup_limit_reached


class SignupView(CreateView):
    form_class = SignupForm
    template_name = 'registration/signup.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        # Every account gets its own daily interviews, so unlimited signups would mean
        # unlimited Gemini calls. Cap how many accounts one network makes per day.
        ip = client_ip(self.request)
        if signup_limit_reached(ip):
            form.add_error(None, 'too many new accounts from this network today. try again tomorrow.')
            return self.form_invalid(form)

        user = form.save()
        Profile.objects.filter(user=user).update(signup_ip=ip or None)
        # Named, because with django-axes there are two backends; the new user's
        # password was just set, so there is nothing for axes to check.
        login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
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
