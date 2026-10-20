from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    """Every user gets a Profile, however they were created (signup, admin, createsuperuser)."""
    # raw: loaddata is restoring a fixture, which brings its own Profile rows.
    if created and not kwargs.get('raw'):
        Profile.objects.create(user=instance)
