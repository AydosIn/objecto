from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from museum.models import SystemPrompt
from museum.prompts import DEFAULT_SYSTEM_PROMPT

from .utils import TempMediaMixin, make_exhibit

User = get_user_model()
LONG_TEXT = ('You are a very dramatic museum curator. ' * 5).strip()


class SystemPromptModelTests(TestCase):
    def test_migration_created_active_version_one_from_code(self):
        first = SystemPrompt.objects.get()
        self.assertTrue(first.is_active)
        self.assertEqual(first.text, DEFAULT_SYSTEM_PROMPT)
        self.assertEqual(SystemPrompt.active(), first)

    def test_active_is_none_when_nothing_is_active(self):
        SystemPrompt.objects.update(is_active=False)
        self.assertIsNone(SystemPrompt.active())

    def test_database_refuses_two_active_versions(self):
        with self.assertRaises(IntegrityError):
            SystemPrompt.objects.create(label='Second', text=LONG_TEXT, is_active=True)


class SystemPromptAdminTests(TempMediaMixin, TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email='curator@mail.com', password='s3cret-mug')
        self.client.force_login(self.admin)
        self.v1 = SystemPrompt.objects.get()

    def change_url(self, prompt):
        return reverse('admin:museum_systemprompt_change', args=[prompt.pk])

    def post_change(self, prompt, **data):
        payload = {'label': prompt.label, 'text': prompt.text, 'activate': 'on' if prompt.is_active else ''}
        payload.update(data)
        if not payload['activate']:
            del payload['activate']
        return self.client.post(self.change_url(prompt), payload, follow=True)

    def test_pages_load(self):
        for url in [
            reverse('admin:museum_systemprompt_changelist'),
            reverse('admin:museum_systemprompt_add'),
            self.change_url(self.v1),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_add_page_starts_from_active_text(self):
        response = self.client.get(reverse('admin:museum_systemprompt_add'))
        self.assertEqual(response.context['adminform'].form.initial['text'], self.v1.text)

    def test_editing_active_text_creates_new_active_version(self):
        response = self.post_change(self.v1, label='More dramatic', text=LONG_TEXT)
        self.assertContains(response, f'saved as a new version. v{self.v1.pk} is unchanged')

        self.v1.refresh_from_db()
        self.assertEqual(self.v1.text, DEFAULT_SYSTEM_PROMPT)
        self.assertFalse(self.v1.is_active)
        new = SystemPrompt.active()
        self.assertNotEqual(new.pk, self.v1.pk)
        self.assertEqual((new.label, new.text.strip()), ('More dramatic', LONG_TEXT.strip()))
        self.assertEqual(new.created_by, self.admin)

    def test_editing_inactive_text_creates_new_inactive_version(self):
        draft = SystemPrompt.objects.create(label='Draft', text=LONG_TEXT)
        self.post_change(draft, text=LONG_TEXT + ' Be brief.')
        self.assertEqual(SystemPrompt.objects.count(), 3)
        self.assertEqual(SystemPrompt.active(), self.v1)

    def test_renaming_label_only_edits_in_place(self):
        self.post_change(self.v1, label='The classic')
        self.assertEqual(SystemPrompt.objects.count(), 1)
        self.v1.refresh_from_db()
        self.assertEqual(self.v1.label, 'The classic')

    def test_saving_unchanged_text_from_a_browser_does_not_create_a_version(self):
        # Browsers send \r\n line breaks and may add a trailing newline.
        browser_text = self.v1.text.replace('\n', '\r\n') + '\r\n'
        self.post_change(self.v1, text=browser_text, label='Renamed only')
        self.assertEqual(SystemPrompt.objects.count(), 1)

    def test_ticking_active_on_old_version_switches_the_active_one(self):
        draft = SystemPrompt.objects.create(label='Draft', text=LONG_TEXT)
        self.post_change(draft, activate='on')
        self.assertEqual(SystemPrompt.active(), draft)
        self.v1.refresh_from_db()
        self.assertFalse(self.v1.is_active)

    def test_unticking_active_warns_about_fallback(self):
        response = self.post_change(self.v1, activate='')
        self.assertIsNone(SystemPrompt.active())
        self.assertContains(response, 'default prompt from the code is being used')

    def test_too_short_text_is_rejected(self):
        response = self.post_change(self.v1, text='Be funny.')
        self.assertContains(response, 'too short to guide Gemini')
        self.assertEqual(SystemPrompt.objects.count(), 1)

    def test_make_active_action(self):
        draft = SystemPrompt.objects.create(label='Draft', text=LONG_TEXT)
        self.client.post(
            reverse('admin:museum_systemprompt_changelist'),
            {'action': 'make_active', '_selected_action': [draft.pk]},
        )
        self.assertEqual(SystemPrompt.active(), draft)

    def test_make_active_needs_exactly_one(self):
        draft = SystemPrompt.objects.create(label='Draft', text=LONG_TEXT)
        response = self.client.post(
            reverse('admin:museum_systemprompt_changelist'),
            {'action': 'make_active', '_selected_action': [draft.pk, self.v1.pk]},
            follow=True,
        )
        self.assertContains(response, 'Select exactly one version')
        self.assertEqual(SystemPrompt.active(), self.v1)

    def test_active_version_cannot_be_deleted(self):
        url = reverse('admin:museum_systemprompt_delete', args=[self.v1.pk])
        self.assertEqual(self.client.post(url, {'post': 'yes'}).status_code, 403)
        self.assertTrue(SystemPrompt.objects.filter(pk=self.v1.pk).exists())

    def test_inactive_version_can_be_deleted_and_exhibits_survive(self):
        old = SystemPrompt.objects.create(label='Old', text=LONG_TEXT)
        exhibit = make_exhibit(self.admin, prompt_version=old)
        url = reverse('admin:museum_systemprompt_delete', args=[old.pk])
        self.client.post(url, {'post': 'yes'})
        exhibit.refresh_from_db()
        self.assertIsNone(exhibit.prompt_version)

    def test_list_shows_exhibits_written_per_version(self):
        make_exhibit(self.admin, prompt_version=self.v1)
        make_exhibit(self.admin, prompt_version=self.v1)
        response = self.client.get(reverse('admin:museum_systemprompt_changelist'))
        self.assertContains(response, '<td class="field-exhibit_count">2</td>', html=True)
