import re

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from museum.models import Exhibit, GenerationLog, exhibit_upload_to, validate_rivals

from .utils import TempMediaMixin, make_exhibit

User = get_user_model()


class UploadPathTests(TestCase):
    def test_path_is_random_and_dated(self):
        path = exhibit_upload_to(None, 'My Bedroom.JPG')
        self.assertRegex(path, r'^exhibits/\d{4}/\d{2}/[0-9a-f]{32}\.jpg$')
        self.assertNotIn('Bedroom', path)

    def test_two_uploads_never_share_a_name(self):
        self.assertNotEqual(exhibit_upload_to(None, 'a.jpg'), exhibit_upload_to(None, 'a.jpg'))


class RivalsValidatorTests(TestCase):
    def test_valid_rivals(self):
        validate_rivals([])
        validate_rivals([{'name': 'The Cat', 'reason': 'Pushes it off tables.'}])

    def test_invalid_rivals(self):
        for bad in [
            'The Cat',
            [{'name': 'The Cat'}],
            [{'name': 'The Cat', 'reason': 'x', 'extra': 'y'}],
            [{'name': 3, 'reason': 'x'}],
            ['The Cat'],
        ]:
            with self.subTest(rivals=bad), self.assertRaises(ValidationError):
                validate_rivals(bad)


class ExhibitTests(TempMediaMixin, TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='gerald@mail.com', password='s3cret-mug')

    def test_str(self):
        exhibit = make_exhibit(self.owner)
        self.assertEqual(str(exhibit), 'Gerald, Mug of the Third Shelf')

    def test_image_is_stored_under_a_random_name(self):
        exhibit = make_exhibit(self.owner)
        self.assertRegex(exhibit.image.name, r'^exhibits/\d{4}/\d{2}/[0-9a-f]{32}\.jpg$')
        self.assertTrue(exhibit.image.storage.exists(exhibit.image.name))

    def test_newest_first(self):
        first = make_exhibit(self.owner, name='First')
        second = make_exhibit(self.owner, name='Second')
        self.assertEqual(list(Exhibit.objects.all()), [second, first])

    def test_deleting_exhibit_deletes_its_photo(self):
        exhibit = make_exhibit(self.owner)
        storage, name = exhibit.image.storage, exhibit.image.name
        with self.captureOnCommitCallbacks(execute=True):
            exhibit.delete()
        self.assertFalse(storage.exists(name))

    def test_deleting_user_deletes_their_photos(self):
        exhibit = make_exhibit(self.owner)
        storage, name = exhibit.image.storage, exhibit.image.name
        with self.captureOnCommitCallbacks(execute=True):
            self.owner.delete()
        self.assertFalse(Exhibit.objects.exists())
        self.assertFalse(storage.exists(name))


class GenerationLogTests(TestCase):
    def test_str(self):
        user = User.objects.create_user(email='gerald@mail.com', password='s3cret-mug')
        log = GenerationLog.objects.create(user=user, success=False, error='timeout')
        self.assertEqual(str(log), 'gerald@mail.com · New exhibit · failed')
