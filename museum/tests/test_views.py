import os
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from museum.models import Exhibit, GenerationLog
from museum.services.gemini import BiographyResult, GenerationFailed, NotAnObject

from .utils import TempMediaMixin, make_exhibit, make_image_file

User = get_user_model()
PASSWORD = 's3cret-mug'

FAKE_BIOGRAPHY = BiographyResult(
    object_type='ceramic mug',
    name='Gerald',
    title='Mug of the Third Shelf',
    placard='Survived three moves and one terrible latte.',
    origin_story='Born in a kiln.',
    trauma='The Great Microwave Incident.',
    rivals=[{'name': 'The Dishwasher', 'reason': 'It knows what it did.'}],
    hopes_and_fears='Hopes for tea. Fears the floor.',
    opinion_of_owner='Means well. Rinses poorly.',
    model_name='gemini-test-flash',
)


class ExhibitCreateViewTests(TempMediaMixin, TestCase):
    url = reverse('museum:new')

    def setUp(self):
        self.user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        patcher = mock.patch('museum.views.generate_biography', return_value=FAKE_BIOGRAPHY)
        self.generate = patcher.start()
        self.addCleanup(patcher.stop)

    def stored_files(self):
        return {name for _, _, names in os.walk(self._media_root) for name in names}

    def post_and_count_new_files(self, data):
        before = self.stored_files()
        response = self.client.post(self.url, data)
        return response, len(self.stored_files() - before)

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_page_has_photo_input(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, 'accept="image/*"')
        self.assertContains(response, 'enctype="multipart/form-data"')

    def test_upload_creates_exhibit_with_clean_jpeg(self):
        self.client.force_login(self.user)
        upload = make_image_file(size=(3200, 2400), format='PNG', name='Kitchen Mug.png')
        response = self.client.post(self.url, {'image': upload})

        exhibit = Exhibit.objects.get()
        self.assertRedirects(response, exhibit.get_absolute_url())
        self.assertEqual(exhibit.owner, self.user)
        self.assertTrue(exhibit.image.name.endswith('.jpg'))
        self.assertNotIn('Kitchen', exhibit.image.name)
        with exhibit.image.open() as stored, Image.open(stored) as image:
            self.assertEqual((image.format, image.size), ('JPEG', (1600, 1200)))

    def test_upload_saves_the_biography_and_logs_success(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {'image': make_image_file()})

        exhibit = Exhibit.objects.get()
        self.assertEqual(exhibit.name, 'Gerald')
        self.assertEqual(exhibit.rivals[0]['name'], 'The Dishwasher')
        self.assertEqual(exhibit.model_name, 'gemini-test-flash')
        log = GenerationLog.objects.get()
        self.assertEqual((log.user, log.kind, log.success), (self.user, 'create', True))

    def test_gemini_gets_the_cleaned_jpeg_and_profile_hints(self):
        self.user.profile.display_name = 'Aydos'
        self.user.profile.about_me = 'I drink too much tea.'
        self.user.profile.save()
        self.client.force_login(self.user)
        self.client.post(self.url, {'image': make_image_file(format='PNG', name='mug.png')})

        image_bytes, mime_type, hints = self.generate.call_args.args
        self.assertTrue(image_bytes.startswith(b'\xff\xd8'))  # JPEG magic bytes
        self.assertEqual(mime_type, 'image/jpeg')
        self.assertEqual((hints.owner_name, hints.about_me), ('Aydos', 'I drink too much tea.'))

    def test_not_an_object_shows_reason_and_saves_nothing(self):
        self.generate.side_effect = NotAnObject('That looks like a person.')
        self.client.force_login(self.user)
        response, new_files = self.post_and_count_new_files({'image': make_image_file()})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'That looks like a person.')
        self.assertFalse(Exhibit.objects.exists())
        self.assertEqual(new_files, 0)
        log = GenerationLog.objects.get()
        self.assertFalse(log.success)
        self.assertIn('person', log.error)

    def test_gemini_failure_shows_retry_message_and_saves_nothing(self):
        self.generate.side_effect = GenerationFailed('Gemini API error 503: overloaded')
        self.client.force_login(self.user)
        response, new_files = self.post_and_count_new_files({'image': make_image_file()})

        self.assertContains(response, 'The object is being shy.')
        self.assertFalse(Exhibit.objects.exists())
        self.assertEqual(new_files, 0)
        self.assertEqual(GenerationLog.objects.get().error, 'Gemini API error 503: overloaded')

    def test_invalid_upload_never_reaches_gemini(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {'image': SimpleUploadedFile('mug.jpg', b'not a photo')})
        self.generate.assert_not_called()
        self.assertFalse(GenerationLog.objects.exists())

    def test_non_image_shows_error_and_saves_nothing(self):
        self.client.force_login(self.user)
        upload = SimpleUploadedFile('mug.jpg', b'not a photo', content_type='image/jpeg')
        response = self.client.post(self.url, {'image': upload})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "isn&#x27;t an image we can read")
        self.assertFalse(Exhibit.objects.exists())

    def test_missing_photo_shows_error(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {})
        self.assertContains(response, 'Choose or take a photo first.')
        self.assertFalse(Exhibit.objects.exists())


class ExhibitDetailViewTests(TempMediaMixin, TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        self.exhibit = make_exhibit(self.owner)

    def test_owner_sees_biography(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.exhibit.get_absolute_url())
        self.assertContains(response, 'Mug of the Third Shelf')
        self.assertContains(response, 'The Dishwasher')
        self.assertContains(response, self.exhibit.image.url)

    def test_other_user_gets_404(self):
        stranger = User.objects.create_user(email='stranger@mail.com', password=PASSWORD)
        self.client.force_login(stranger)
        response = self.client.get(self.exhibit.get_absolute_url())
        self.assertEqual(response.status_code, 404)

    def test_requires_login(self):
        response = self.client.get(self.exhibit.get_absolute_url())
        self.assertEqual(response.status_code, 302)
