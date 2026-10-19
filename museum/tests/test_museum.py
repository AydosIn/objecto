from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .utils import TempMediaMixin, make_exhibit

User = get_user_model()
PASSWORD = 's3cret-mug'


class MuseumViewTests(TempMediaMixin, TestCase):
    url = reverse('museum:index')

    def setUp(self):
        self.owner = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        self.client.force_login(self.owner)

    def test_requires_login(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_empty_state_invites_a_first_object(self):
        response = self.client.get(self.url)
        self.assertContains(response, "it's quiet in here.")
        self.assertContains(response, reverse('museum:new'))

    def test_shows_own_exhibits_newest_first_with_aura(self):
        make_exhibit(self.owner, name='Older')
        make_exhibit(self.owner, name='Newer')
        stranger = User.objects.create_user(email='stranger@mail.com', password=PASSWORD)
        make_exhibit(stranger, name='Secret')

        response = self.client.get(self.url)
        names = [exhibit.name for exhibit, _ in response.context['tiles']]
        self.assertEqual(names, ['Newer', 'Older'])
        self.assertNotContains(response, 'secret')
        self.assertContains(response, '2 objects with opinions about you.')
        aura = response.context['tiles'][0][1]
        self.assertContains(response, f'class="tile field--{aura.slug}"')

    def test_tiles_link_to_their_recap(self):
        exhibit = make_exhibit(self.owner)
        self.assertContains(self.client.get(self.url), exhibit.get_absolute_url())

    def test_paginates_at_24(self):
        for n in range(25):
            make_exhibit(self.owner, name=f'Object {n}')
        first = self.client.get(self.url)
        self.assertEqual(len(first.context['tiles']), 24)
        self.assertContains(first, 'page 1 of 2')
        self.assertContains(first, 'tile--add')
        second = self.client.get(self.url, {'page': 2})
        self.assertEqual(len(second.context['tiles']), 1)
        self.assertNotContains(second, 'tile--add')

    def test_app_bar_and_exhibit_link_back_to_the_museum(self):
        exhibit = make_exhibit(self.owner)
        response = self.client.get(exhibit.get_absolute_url())
        self.assertContains(response, 'back to your museum')
        self.assertContains(response, f'href="{self.url}"')
