import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from museum.models import Exhibit


def make_image_file(name='mug.jpg', size=(64, 48), color=(180, 90, 60), format='JPEG'):
    """A real (tiny) image, generated in memory."""
    buffer = io.BytesIO()
    Image.new('RGB', size, color).save(buffer, format=format)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type=f'image/{format.lower()}')


def make_exhibit(owner, **fields):
    defaults = {
        'image': make_image_file(),
        'object_type': 'ceramic mug',
        'name': 'Gerald',
        'title': 'Mug of the Third Shelf',
        'placard': 'Survived three moves and one terrible latte.',
        'origin_story': 'Born in a kiln in Stoke-on-Trent.',
        'trauma': 'The Great Microwave Incident of 2023.',
        'rivals': [{'name': 'The Dishwasher', 'reason': 'It knows what it did.'}],
        'hopes_and_fears': 'Hopes for tea. Fears the floor.',
        'opinion_of_owner': 'Means well. Rinses poorly.',
    }
    defaults.update(fields)
    return Exhibit.objects.create(owner=owner, **defaults)


class TempMediaMixin:
    """Uploads in tests go to a throwaway folder instead of the real media/ or R2 bucket."""

    @classmethod
    def setUpClass(cls):
        cls._media_root = tempfile.mkdtemp()
        cls._media_override = override_settings(
            MEDIA_ROOT=cls._media_root,
            STORAGES={
                'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
                'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
            },
        )
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)
