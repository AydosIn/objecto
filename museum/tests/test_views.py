import os
from dataclasses import replace
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from museum.models import Exhibit, GenerationLog, SystemPrompt
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

    def test_exhibit_remembers_which_prompt_wrote_it(self):
        prompt = SystemPrompt.active()
        self.generate.return_value = replace(FAKE_BIOGRAPHY, prompt_version=prompt)
        self.client.force_login(self.user)
        self.client.post(self.url, {'image': make_image_file()})
        self.assertEqual(Exhibit.objects.get().prompt_version, prompt)

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


class ExhibitActionTestCase(TempMediaMixin, TestCase):
    """Owner, stranger and an exhibit, with Gemini mocked."""

    def setUp(self):
        self.owner = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        self.stranger = User.objects.create_user(email='stranger@mail.com', password=PASSWORD)
        self.exhibit = make_exhibit(
            self.owner, name='Old Name', object_type='ceramic mug', trauma='Old trauma.'
        )
        self.new_story = replace(FAKE_BIOGRAPHY, name='Fresh Gerald', trauma='A brand new trauma.')
        patcher = mock.patch('museum.views.generate_biography', return_value=self.new_story)
        self.generate = patcher.start()
        self.addCleanup(patcher.stop)

    def follow_messages(self, response):
        return [str(message) for message in response.context['messages']]


class ExhibitRegenerateViewTests(ExhibitActionTestCase):
    def url(self):
        return reverse('museum:regenerate', args=[self.exhibit.pk])

    def test_replaces_biography_and_keeps_photo(self):
        photo_name = self.exhibit.image.name
        self.client.force_login(self.owner)
        response = self.client.post(self.url(), follow=True)

        self.assertRedirects(response, self.exhibit.get_absolute_url())
        self.exhibit.refresh_from_db()
        self.assertEqual(self.exhibit.name, 'Fresh Gerald')
        self.assertEqual(self.exhibit.trauma, 'A brand new trauma.')
        self.assertEqual(self.exhibit.image.name, photo_name)
        self.assertIn('Fresh Gerald sat down for a second interview.', self.follow_messages(response))
        log = GenerationLog.objects.get()
        self.assertEqual((log.kind, log.success), ('regenerate', True))

    def test_sends_stored_photo_and_keeps_object_type(self):
        self.client.force_login(self.owner)
        self.client.post(self.url())

        image_bytes, mime_type, hints = self.generate.call_args.args
        with self.exhibit.image.open('rb') as stored:
            self.assertEqual(image_bytes, stored.read())
        self.assertEqual(mime_type, 'image/jpeg')
        self.assertEqual(hints.object_type, 'ceramic mug')

    def test_failure_keeps_old_biography(self):
        self.generate.side_effect = GenerationFailed('Gemini API error 503: overloaded')
        self.client.force_login(self.owner)
        response = self.client.post(self.url(), follow=True)

        self.exhibit.refresh_from_db()
        self.assertEqual(self.exhibit.trauma, 'Old trauma.')
        self.assertIn('The object is being shy. Try again in a moment.', self.follow_messages(response))
        self.assertFalse(GenerationLog.objects.get().success)

    def test_get_is_not_allowed(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url()).status_code, 405)
        self.generate.assert_not_called()

    def test_stranger_gets_404(self):
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.post(self.url()).status_code, 404)
        self.generate.assert_not_called()


class ExhibitRenameViewTests(ExhibitActionTestCase):
    def url(self):
        return reverse('museum:rename', args=[self.exhibit.pk])

    def test_rewrites_with_new_object_type(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url(), {'object_type': '  glass vase '}, follow=True)

        self.assertEqual(self.generate.call_args.args[2].object_type, 'glass vase')
        self.exhibit.refresh_from_db()
        # Gemini's fake says "ceramic mug"; the user's wording must win.
        self.assertEqual(self.exhibit.object_type, 'glass vase')
        self.assertEqual(self.exhibit.name, 'Fresh Gerald')
        self.assertIn(
            'Apologies to the glass vase. Its real story has been written.',
            self.follow_messages(response),
        )
        self.assertEqual(GenerationLog.objects.get().kind, 'rename')

    def test_regenerate_after_rename_keeps_the_new_type(self):
        self.client.force_login(self.owner)
        self.client.post(self.url(), {'object_type': 'glass vase'})
        self.client.post(reverse('museum:regenerate', args=[self.exhibit.pk]))
        self.assertEqual(self.generate.call_args.args[2].object_type, 'glass vase')

    def test_empty_name_is_rejected_without_calling_gemini(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url(), {'object_type': '   '}, follow=True)
        self.assertIn('Tell us what the object really is.', self.follow_messages(response))
        self.generate.assert_not_called()

    def test_too_long_name_is_rejected(self):
        self.client.force_login(self.owner)
        response = self.client.post(self.url(), {'object_type': 'v' * 101}, follow=True)
        self.assertIn('Keep it under 100 characters.', self.follow_messages(response))
        self.generate.assert_not_called()

    def test_stranger_gets_404(self):
        self.client.force_login(self.stranger)
        response = self.client.post(self.url(), {'object_type': 'glass vase'})
        self.assertEqual(response.status_code, 404)
        self.generate.assert_not_called()


class ExhibitDeleteViewTests(ExhibitActionTestCase):
    def url(self):
        return reverse('museum:delete', args=[self.exhibit.pk])

    def test_confirm_page(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.url())
        self.assertContains(response, 'Remove Old Name from the museum?')
        self.assertTrue(Exhibit.objects.filter(pk=self.exhibit.pk).exists())

    def test_delete_removes_row_and_photo(self):
        storage, photo_name = self.exhibit.image.storage, self.exhibit.image.name
        self.client.force_login(self.owner)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.url(), follow=True)

        self.assertRedirects(response, reverse('landing'))
        self.assertIn('Old Name has left the museum.', self.follow_messages(response))
        self.assertFalse(Exhibit.objects.filter(pk=self.exhibit.pk).exists())
        self.assertFalse(storage.exists(photo_name))

    def test_stranger_cannot_see_or_delete(self):
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.url()).status_code, 404)
        self.assertEqual(self.client.post(self.url()).status_code, 404)
        self.assertTrue(Exhibit.objects.filter(pk=self.exhibit.pk).exists())

    def test_requires_login(self):
        response = self.client.post(self.url())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Exhibit.objects.filter(pk=self.exhibit.pk).exists())


class ExhibitDetailActionsTests(ExhibitActionTestCase):
    def test_detail_page_shows_all_actions(self):
        self.client.force_login(self.owner)
        response = self.client.get(self.exhibit.get_absolute_url())
        for url in ['regenerate', 'rename', 'delete']:
            with self.subTest(action=url):
                self.assertContains(response, reverse(f'museum:{url}', args=[self.exhibit.pk]))
        self.assertContains(response, 'value="ceramic mug"')
        self.assertContains(response, 'data-loading=')
