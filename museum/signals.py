from django.db import transaction
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Exhibit


@receiver(post_delete, sender=Exhibit)
def delete_exhibit_image(sender, instance, **kwargs):
    """Deleting a row doesn't touch the file on disk, so remove the photo too.
    Runs for every delete: the museum's delete button, the admin, and a user being deleted.
    Waits for the commit, so a rolled-back delete doesn't leave an exhibit without its photo."""
    if instance.image:
        storage, name = instance.image.storage, instance.image.name
        transaction.on_commit(lambda: storage.delete(name))
