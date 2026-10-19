from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from museum.models import Exhibit

from .utils import TempMediaMixin, make_exhibit, make_image_file

User = get_user_model()
PASSWORD = 's3cret-mug'


class ExhibitCreateViewTests(TempMediaMixin, TestCase):
    url = reverse('museum:new')

    def setUp(self):
        self.user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)

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
        self.assertEqual(exhibit.model_name, 'placeholder')
        self.assertTrue(exhibit.image.name.endswith('.jpg'))
        self.assertNotIn('Kitchen', exhibit.image.name)
        with exhibit.image.open() as stored, Image.open(stored) as image:
            self.assertEqual((image.format, image.size), ('JPEG', (1600, 1200)))

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
