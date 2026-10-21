from urllib.parse import quote

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from museum.services.aura import RAMP
from museum.services.pdf import build_pdf, clean

from .utils import TempMediaMixin, make_exhibit, make_image_file

User = get_user_model()


class SharingTestCase(TempMediaMixin, TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(email='gerald@mail.com', password='s3cret-mug')
        self.other = User.objects.create_user(email='kettle@mail.com', password='s3cret-mug')
        self.exhibit = make_exhibit(self.owner)

    def share(self):
        self.client.force_login(self.owner)
        self.client.post(reverse('museum:share', args=[self.exhibit.pk]))
        self.client.logout()
        self.exhibit.refresh_from_db()
        return self.exhibit.share_token


class ShareLinkTests(SharingTestCase):
    def test_exhibits_are_private_until_shared(self):
        self.assertFalse(self.exhibit.is_shared)

    def test_sharing_makes_a_link_and_reopens_the_sheet(self):
        self.client.force_login(self.owner)
        response = self.client.post(reverse('museum:share', args=[self.exhibit.pk]))
        self.assertRedirects(response, f'{self.exhibit.get_absolute_url()}?share=1')
        self.exhibit.refresh_from_db()
        self.assertTrue(self.exhibit.is_shared)
        self.assertGreaterEqual(len(self.exhibit.share_token), 20)
        self.assertIsNotNone(self.exhibit.shared_at)

    def test_sharing_again_keeps_the_same_link(self):
        token = self.share()
        self.assertEqual(self.share(), token)

    def test_sharing_needs_post(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse('museum:share', args=[self.exhibit.pk]))
        self.assertEqual(response.status_code, 405)

    def test_only_the_owner_can_share_or_unshare(self):
        self.client.force_login(self.other)
        for name in ('museum:share', 'museum:unshare'):
            response = self.client.post(reverse(name, args=[self.exhibit.pk]))
            self.assertEqual(response.status_code, 404)

    def test_stopping_kills_the_old_link_and_a_new_share_gets_a_new_one(self):
        old = self.share()
        self.client.force_login(self.owner)
        response = self.client.post(reverse('museum:unshare', args=[self.exhibit.pk]))
        self.assertRedirects(response, self.exhibit.get_absolute_url())
        self.client.logout()
        for name in ('shared', 'shared-photo', 'shared-pdf'):
            self.assertEqual(self.client.get(reverse(name, args=[old])).status_code, 404)
        self.assertNotEqual(self.share(), old)

    def test_detail_page_offers_a_link_until_there_is_one(self):
        self.client.force_login(self.owner)
        url = self.exhibit.get_absolute_url()
        response = self.client.get(url)
        self.assertContains(response, 'make a link')
        self.assertContains(response, reverse('museum:pdf', args=[self.exhibit.pk]))

        token = self.share()
        self.client.force_login(self.owner)
        response = self.client.get(f'{url}?share=1')
        share_url = f'http://testserver/s/{token}/'
        self.assertContains(response, f'value="{share_url}"')
        self.assertContains(response, f'https://t.me/share/url?url={quote(share_url, safe="")}')
        self.assertContains(response, 'sms:?&amp;body=')
        self.assertContains(response, 'delete the link')
        self.assertContains(response, 'id="share-sheet" aria-labelledby="share-title" open')


class SharedPageTests(SharingTestCase):
    def test_anyone_with_the_link_can_read_the_story(self):
        token = self.share()
        response = self.client.get(reverse('shared', args=[token]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'gerald')
        self.assertContains(response, 'means well. rinses poorly.')
        self.assertContains(response, 'what it thinks of its human')

    def test_visitors_get_no_owner_buttons(self):
        token = self.share()
        response = self.client.get(reverse('shared', args=[token]))
        for name in ('regenerate', 'rename', 'delete', 'unshare'):
            self.assertNotContains(response, reverse(f'museum:{name}', args=[self.exhibit.pk]))
        # The photo comes from the shared address, not the owner's storage link.
        self.assertNotContains(response, self.exhibit.image.url)

    def test_link_previews_get_a_title_and_a_full_image_address(self):
        token = self.share()
        response = self.client.get(reverse('shared', args=[token]))
        self.assertContains(response, '<meta property="og:title" content="gerald, the ceramic mug">')
        self.assertContains(
            response, f'<meta property="og:image" content="http://testserver/s/{token}/photo.jpg">'
        )

    def test_search_engines_are_kept_out(self):
        token = self.share()
        for name in ('shared', 'shared-photo', 'shared-pdf'):
            response = self.client.get(reverse(name, args=[token]))
            self.assertEqual(response['X-Robots-Tag'], 'noindex, nofollow')

    def test_unknown_or_unshared_links_are_404(self):
        self.assertEqual(self.client.get(reverse('shared', args=['nope'])).status_code, 404)

    def test_visitors_get_the_download_but_not_send_the_pdf(self):
        token = self.share()
        response = self.client.get(reverse('shared', args=[token]))
        self.assertContains(response, 'download the pdf')
        self.assertNotContains(response, 'data-share-pdf')

    def test_link_preview_crawlers_can_check_the_photo_with_head(self):
        token = self.share()
        response = self.client.head(reverse('shared-photo', args=[token]))
        self.assertEqual(response.status_code, 200)

    def test_photo(self):
        token = self.share()
        response = self.client.get(reverse('shared-photo', args=[token]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/jpeg')
        self.assertEqual(b''.join(response.streaming_content)[:2], b'\xff\xd8')

    def test_visitors_can_download_the_pdf(self):
        token = self.share()
        response = self.client.get(reverse('shared-pdf', args=[token]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF'))


class PdfTests(SharingTestCase):
    url_name = 'museum:pdf'

    def url(self):
        return reverse(self.url_name, args=[self.exhibit.pk])

    def test_requires_login(self):
        response = self.client.get(self.url())
        self.assertRedirects(response, f"{reverse('login')}?next={self.url()}")

    def test_someone_elses_exhibit_is_404(self):
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_owner_gets_a_pdf_named_after_the_object(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(
            response['Content-Disposition'], 'attachment; filename="gerald-the-ceramic-mug.pdf"'
        )
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF'))

    def test_missing_photo_is_404(self):
        self.exhibit.image.storage.delete(self.exhibit.image.name)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url()).status_code, 404)

    def test_long_story_with_emoji_and_no_rivals(self):
        exhibit = make_exhibit(
            self.owner,
            name='Sir Reginald Fluffington-Whiskerbottom the Third',
            rivals=[],
            origin_story='very long. ' * 400,
            opinion_of_owner='you are my favourite human 💀🔥 tho',
            image=make_image_file(size=(40, 300)),
        )
        with exhibit.image.open('rb') as stored:
            pdf = build_pdf(exhibit, stored.read(), RAMP[0], 'https://example.com')
        self.assertTrue(pdf.startswith(b'%PDF'))

    def test_clean_drops_what_the_font_cant_draw(self):
        self.assertEqual(clean('Still My Favourite 💀  Human “tho”'), 'still my favourite human “tho”')
