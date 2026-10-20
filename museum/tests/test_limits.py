import datetime
from unittest import mock
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from museum.models import GenerationLog
from museum.services.limits import remaining_today, start_of_today, used_today

from .test_views import FAKE_BIOGRAPHY
from .utils import TempMediaMixin, make_exhibit, make_image_file

User = get_user_model()
PASSWORD = 's3cret-mug'
TASHKENT = ZoneInfo('Asia/Tashkent')


def log(user, *, success=True, error='', at=None):
    entry = GenerationLog.objects.create(user=user, success=success, error=error)
    if at:
        GenerationLog.objects.filter(pk=entry.pk).update(created_at=at)
    return entry


@override_settings(DAILY_GENERATION_LIMIT=5)
class CountingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)

    def test_stories_and_refusals_count_but_google_errors_do_not(self):
        log(self.user)
        log(self.user, success=False, error='Not an object: that is a cat.')
        log(self.user, success=False, error='Gemini API error 503: overloaded')
        log(self.user, success=False, error='Network error talking to Gemini')
        self.assertEqual(used_today(self.user), 2)
        self.assertEqual(remaining_today(self.user), 3)

    def test_never_below_zero(self):
        for _ in range(7):
            log(self.user)
        self.assertEqual(remaining_today(self.user), 0)

    def test_staff_are_unlimited(self):
        admin = User.objects.create_superuser(email='curator@mail.com', password=PASSWORD)
        for _ in range(9):
            log(admin)
        self.assertIsNone(remaining_today(admin))

    def test_today_starts_at_midnight_in_uzbekistan(self):
        # 00:30 in Tashkent on 20 Oct is 19:30 UTC on 19 Oct.
        now = datetime.datetime(2026, 10, 20, 0, 30, tzinfo=TASHKENT)
        self.assertEqual(start_of_today(now), datetime.datetime(2026, 10, 20, tzinfo=TASHKENT))
        log(self.user, at=datetime.datetime(2026, 10, 19, 23, 50, tzinfo=TASHKENT))  # yesterday
        log(self.user, at=datetime.datetime(2026, 10, 20, 0, 10, tzinfo=TASHKENT))   # today
        self.assertEqual(used_today(self.user, now), 1)


@override_settings(DAILY_GENERATION_LIMIT=5)
class LimitInViewsTests(TempMediaMixin, TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        self.client.force_login(self.user)
        patcher = mock.patch('museum.views.generate_biography', return_value=FAKE_BIOGRAPHY)
        self.generate = patcher.start()
        self.addCleanup(patcher.stop)

    def use_all(self):
        for _ in range(5):
            log(self.user)

    def test_upload_page_shows_whats_left(self):
        log(self.user)
        log(self.user)
        response = self.client.get(reverse('museum:new'))
        self.assertContains(response, '3 interviews left today')
        self.assertEqual(response.context['quota_dots'], [True, True, True, False, False])

    def test_upload_page_turns_into_come_back_tomorrow(self):
        self.use_all()
        response = self.client.get(reverse('museum:new'))
        self.assertContains(response, 'come back tomorrow')
        self.assertNotContains(response, 'data-upload-form')

    def test_upload_blocked_without_calling_gemini(self):
        self.use_all()
        response = self.client.post(reverse('museum:new'), {'image': make_image_file()})
        self.assertEqual(response.status_code, 200)
        self.generate.assert_not_called()
        self.assertEqual(GenerationLog.objects.count(), 5)  # the blocked try isn't logged

    def test_fifth_interview_is_allowed_sixth_is_not(self):
        for _ in range(4):
            log(self.user)
        self.client.post(reverse('museum:new'), {'image': make_image_file()})
        self.assertEqual(self.generate.call_count, 1)
        self.client.post(reverse('museum:new'), {'image': make_image_file()})
        self.assertEqual(self.generate.call_count, 1)

    def test_reroll_and_rename_are_blocked_too(self):
        exhibit = make_exhibit(self.user)
        self.use_all()
        for url, data in [
            (reverse('museum:regenerate', args=[exhibit.pk]), {}),
            (reverse('museum:rename', args=[exhibit.pk]), {'object_type': 'glass vase'}),
        ]:
            with self.subTest(url=url):
                response = self.client.post(url, data, follow=True)
                messages = [str(m) for m in response.context['messages']]
                self.assertTrue(any('come back tomorrow' in m for m in messages))
        self.generate.assert_not_called()

    def test_exhibit_reroll_row_shows_whats_left(self):
        exhibit = make_exhibit(self.user)
        log(self.user)
        self.assertContains(self.client.get(exhibit.get_absolute_url()), '4 left today')
        for _ in range(4):
            log(self.user)
        self.assertContains(self.client.get(exhibit.get_absolute_url()), 'back tomorrow')

    def test_staff_never_see_or_hit_the_limit(self):
        admin = User.objects.create_superuser(email='curator@mail.com', password=PASSWORD)
        self.client.force_login(admin)
        for _ in range(8):
            log(admin)
        response = self.client.get(reverse('museum:new'))
        self.assertNotContains(response, 'left today')
        self.client.post(reverse('museum:new'), {'image': make_image_file()})
        self.generate.assert_called_once()


@override_settings(DAILY_GENERATION_LIMIT=5, SITE_DAILY_GENERATION_LIMIT=3)
class SiteLimitTests(TempMediaMixin, TestCase):
    """Many accounts together can't go past the site's daily total."""

    def setUp(self):
        self.user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        self.client.force_login(self.user)
        patcher = mock.patch('museum.views.generate_biography', return_value=FAKE_BIOGRAPHY)
        self.generate = patcher.start()
        self.addCleanup(patcher.stop)

    def fill_site(self):
        for n in range(3):
            log(User.objects.create_user(email=f'other{n}@mail.com', password=PASSWORD))

    def test_upload_blocked_when_the_site_is_full(self):
        self.fill_site()
        response = self.client.post(reverse('museum:new'), {'image': make_image_file()})
        self.assertContains(response, 'the museum is full for today')
        self.generate.assert_not_called()

    def test_reroll_blocked_when_the_site_is_full(self):
        exhibit = make_exhibit(self.user)
        self.fill_site()
        response = self.client.post(reverse('museum:regenerate', args=[exhibit.pk]), follow=True)
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('the museum is full for today' in m for m in messages))
        self.generate.assert_not_called()

    def test_google_errors_do_not_fill_the_site(self):
        for n in range(3):
            other = User.objects.create_user(email=f'other{n}@mail.com', password=PASSWORD)
            log(other, success=False, error='Gemini API error 503: overloaded')
        self.client.post(reverse('museum:new'), {'image': make_image_file()})
        self.generate.assert_called_once()

    def test_staff_can_still_interview_when_the_site_is_full(self):
        self.fill_site()
        self.client.force_login(User.objects.create_superuser(email='curator@mail.com', password=PASSWORD))
        self.client.post(reverse('museum:new'), {'image': make_image_file()})
        self.generate.assert_called_once()


@override_settings(DAILY_GENERATION_LIMIT=5)
class QuotaLockTests(TempMediaMixin, TestCase):
    """Parallel requests can't all pass the limit check: each interview checks the limit
    only after taking the user's row lock. (SQLite can't lock rows, so the real race is
    checked against PostgreSQL by hand; these tests pin down the order of the calls.)"""

    def setUp(self):
        self.user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        self.client.force_login(self.user)
        patcher = mock.patch('museum.views.generate_biography', return_value=FAKE_BIOGRAPHY)
        self.generate = patcher.start()
        self.addCleanup(patcher.stop)

    def test_upload_locks_before_checking_the_limit(self):
        calls = []
        with mock.patch('museum.views.lock_quota', side_effect=lambda u: calls.append('lock')), \
                mock.patch('museum.views.limit_reached', side_effect=lambda u: calls.append('check')):
            self.client.post(reverse('museum:new'), {'image': make_image_file()})
        self.assertEqual(calls, ['lock', 'check'])

    def test_reroll_locks_before_checking_the_limit(self):
        exhibit = make_exhibit(self.user)
        calls = []
        with mock.patch('museum.views.lock_quota', side_effect=lambda u: calls.append('lock')), \
                mock.patch('museum.views.limit_reached', side_effect=lambda u: calls.append('check')):
            self.client.post(reverse('museum:regenerate', args=[exhibit.pk]))
        self.assertEqual(calls, ['lock', 'check'])
