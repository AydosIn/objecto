from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from museum.models import Exhibit, GenerationLog

from .utils import TempMediaMixin, make_exhibit, make_image_file

User = get_user_model()


class ExhibitAdminTests(TempMediaMixin, TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email='curator@mail.com', password='s3cret-mug')
        self.client.force_login(self.admin)

    def test_pages_load_and_show_thumbnail(self):
        exhibit = make_exhibit(self.admin)
        response = self.client.get(reverse('admin:museum_exhibit_changelist'))
        self.assertContains(response, exhibit.image.url)
        for url in [
            reverse('admin:museum_exhibit_add'),
            reverse('admin:museum_exhibit_change', args=[exhibit.pk]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_search(self):
        make_exhibit(self.admin, name='Gerald')
        make_exhibit(self.admin, name='Brenda', object_type='armchair')
        response = self.client.get(reverse('admin:museum_exhibit_changelist'), {'q': 'armchair'})
        self.assertContains(response, 'Brenda')
        self.assertNotContains(response, 'Gerald,')

    def test_add_exhibit_by_hand(self):
        response = self.client.post(
            reverse('admin:museum_exhibit_add'),
            {
                'owner': self.admin.pk,
                'image': make_image_file(),
                'object_type': 'kettle',
                'name': 'Kevin',
                'title': 'Boiler of Mornings',
                'placard': 'Has seen things.',
                'origin_story': 'A shop.',
                'trauma': 'Limescale.',
                'rivals': '[{"name": "The Toaster", "reason": "Gets all the attention."}]',
                'hopes_and_fears': 'Hopes for descaling.',
                'opinion_of_owner': 'Overfills me.',
                'model_name': '',
                '_save': 'Save',
            },
        )
        self.assertEqual(response.status_code, 302)
        exhibit = Exhibit.objects.get(name='Kevin')
        self.assertEqual(exhibit.rivals[0]['name'], 'The Toaster')

    def test_badly_shaped_rivals_are_rejected(self):
        response = self.client.post(
            reverse('admin:museum_exhibit_add'),
            {
                'owner': self.admin.pk,
                'image': make_image_file(),
                'object_type': 'kettle',
                'name': 'Kevin',
                'title': 'Boiler of Mornings',
                'placard': 'Has seen things.',
                'origin_story': 'A shop.',
                'trauma': 'Limescale.',
                'rivals': '["The Toaster"]',
                'hopes_and_fears': 'Hopes for descaling.',
                'opinion_of_owner': 'Overfills me.',
                '_save': 'Save',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Exhibit.objects.exists())


class GenerationLogAdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email='curator@mail.com', password='s3cret-mug')
        self.client.force_login(self.admin)

    def test_list_loads(self):
        GenerationLog.objects.create(user=self.admin, success=True)
        response = self.client.get(reverse('admin:museum_generationlog_changelist'))
        self.assertEqual(response.status_code, 200)

    def test_logs_cannot_be_added_by_hand(self):
        response = self.client.get(reverse('admin:museum_generationlog_add'))
        self.assertEqual(response.status_code, 403)
