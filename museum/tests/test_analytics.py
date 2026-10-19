import datetime
from dataclasses import replace
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from museum import analytics
from museum.models import Exhibit, GenerationLog, SystemPrompt
from museum.services.gemini import GenerationFailed, NotAnObject
from museum.templatetags.analytics_format import compact, percent, seconds, usd

from .test_views import FAKE_BIOGRAPHY
from .utils import TempMediaMixin, make_exhibit, make_image_file

User = get_user_model()
PASSWORD = 's3cret-mug'


def log(user, *, days_ago=0, success=True, error='', duration_ms=9000, input_tokens=0,
        output_tokens=0, thinking_tokens=0, prompt=None, kind=GenerationLog.Kind.CREATE):
    entry = GenerationLog.objects.create(
        user=user, kind=kind, success=success, error=error, duration_ms=duration_ms,
        input_tokens=input_tokens, output_tokens=output_tokens, thinking_tokens=thinking_tokens,
        prompt_version=prompt,
    )
    if days_ago:
        GenerationLog.objects.filter(pk=entry.pk).update(
            created_at=timezone.now() - datetime.timedelta(days=days_ago)
        )
    return entry


class GenerationLoggingTests(TempMediaMixin, TestCase):
    """Every Gemini call made from the views records time, tokens and prompt version."""

    def setUp(self):
        self.user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        self.client.force_login(self.user)
        self.prompt = SystemPrompt.active()
        patcher = mock.patch('museum.views.generate_biography')
        self.generate = patcher.start()
        self.addCleanup(patcher.stop)

    def test_success_records_everything(self):
        self.generate.return_value = replace(
            FAKE_BIOGRAPHY,
            usage={'input_tokens': 1732, 'output_tokens': 462, 'thinking_tokens': 10},
            prompt_version=self.prompt,
        )
        self.client.post(reverse('museum:new'), {'image': make_image_file()})

        entry = GenerationLog.objects.get()
        self.assertTrue(entry.success)
        self.assertEqual((entry.input_tokens, entry.output_tokens, entry.thinking_tokens), (1732, 462, 10))
        self.assertEqual(entry.billed_output_tokens, 472)
        self.assertEqual(entry.model_name, 'gemini-test-flash')
        self.assertEqual(entry.prompt_version, self.prompt)
        self.assertEqual(entry.exhibit, Exhibit.objects.get())
        self.assertIsNotNone(entry.duration_ms)

    def test_refusal_records_tokens_it_used(self):
        self.generate.side_effect = NotAnObject(
            'That is a cat.', usage={'input_tokens': 1700, 'output_tokens': 20}, prompt_version=self.prompt
        )
        self.client.post(reverse('museum:new'), {'image': make_image_file()})

        entry = GenerationLog.objects.get()
        self.assertFalse(entry.success)
        self.assertEqual((entry.input_tokens, entry.output_tokens), (1700, 20))
        self.assertEqual(entry.prompt_version, self.prompt)
        self.assertIsNone(entry.exhibit)

    def test_error_records_zero_tokens(self):
        self.generate.side_effect = GenerationFailed('Gemini API error 503: overloaded')
        self.client.post(reverse('museum:new'), {'image': make_image_file()})
        entry = GenerationLog.objects.get()
        self.assertEqual((entry.input_tokens, entry.output_tokens), (0, 0))
        self.assertIsNotNone(entry.duration_ms)

    def test_regenerate_links_log_to_exhibit(self):
        exhibit = make_exhibit(self.user)
        self.generate.return_value = FAKE_BIOGRAPHY
        self.client.post(reverse('museum:regenerate', args=[exhibit.pk]))
        entry = GenerationLog.objects.get()
        self.assertEqual((entry.kind, entry.exhibit), ('regenerate', exhibit))


@override_settings(GEMINI_PRICE_INPUT_PER_M=1.0, GEMINI_PRICE_OUTPUT_PER_M=4.0)
class BuildReportTests(TempMediaMixin, TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(email='alice@mail.com', password=PASSWORD)
        self.bob = User.objects.create_user(email='bob@mail.com', password=PASSWORD)
        self.v1 = SystemPrompt.active()

    def test_empty(self):
        report = analytics.build_report(7)
        self.assertEqual(report['totals']['calls'], 0)
        self.assertIsNone(report['totals']['success_rate'])
        self.assertEqual(len(report['daily']), 7)

    def test_totals_rates_and_cost(self):
        log(self.alice, input_tokens=1_000_000, output_tokens=500_000, thinking_tokens=500_000,
            duration_ms=8000, prompt=self.v1)
        log(self.alice, input_tokens=1_000_000, output_tokens=1_000_000, duration_ms=12000, prompt=self.v1)
        log(self.bob, success=False, error='Not an object: That is a cat.', input_tokens=1000, prompt=self.v1)
        log(self.bob, success=False, error='Gemini API error 503: overloaded', duration_ms=None)
        make_exhibit(self.alice)

        totals = analytics.build_report(7)['totals']
        self.assertEqual((totals['calls'], totals['succeeded'], totals['refused'], totals['errored']), (4, 2, 1, 1))
        self.assertEqual(totals['success_rate'], 0.5)
        self.assertEqual(totals['users'], 2)
        self.assertEqual(totals['billed_output_tokens'], 2_000_000)
        # 2.001M input at $1 + 2M output at $4
        self.assertAlmostEqual(totals['cost'], 2.001 + 8.0)
        self.assertAlmostEqual(totals['cost_per_success'], 10.001 / 2)
        self.assertEqual((totals['median_ms'], totals['p90_ms']), (8000, 12000))
        self.assertEqual(totals['calls_with_tokens'], 3)

    def test_period_excludes_older_calls_and_fills_empty_days(self):
        log(self.alice)
        log(self.alice, days_ago=3, success=False, error='boom')
        log(self.alice, days_ago=10)

        report = analytics.build_report(7)
        self.assertEqual(report['totals']['calls'], 2)
        daily = report['daily']
        self.assertEqual(len(daily), 7)
        self.assertEqual(daily[-1]['date'], timezone.localdate().isoformat())
        self.assertEqual((daily[-1]['succeeded'], daily[-1]['failed']), (1, 0))
        self.assertEqual((daily[-4]['succeeded'], daily[-4]['failed']), (0, 1))
        self.assertEqual(sum(d['succeeded'] + d['failed'] for d in daily), 2)
        self.assertEqual(analytics.build_report(30)['totals']['calls'], 3)

    def test_by_prompt_compares_versions(self):
        v2 = SystemPrompt.objects.create(label='Noir', text='x' * 200)
        log(self.alice, prompt=self.v1, duration_ms=10000, input_tokens=2000, output_tokens=500)
        log(self.alice, prompt=v2, duration_ms=4000, input_tokens=2000, output_tokens=300)
        log(self.alice, prompt=v2, success=False, error='Not an object: blurry', input_tokens=2000)

        rows = {row['prompt_version']: row for row in analytics.build_report(7)['by_prompt']}
        self.assertEqual((rows[v2.pk]['calls'], rows[v2.pk]['refused']), (2, 1))
        self.assertEqual(rows[v2.pk]['avg_ms'], 4000)
        self.assertEqual(rows[v2.pk]['avg_output_tokens'], 300)
        self.assertTrue(rows[self.v1.pk]['prompt_version__is_active'])
        # (4000 in × $1 + 300 out × $4) / 1M ÷ 1 success
        self.assertAlmostEqual(rows[v2.pk]['cost_per_success'], (4000 + 1200) / 1_000_000)

    def test_failures_grouped_by_reason(self):
        for _ in range(3):
            log(self.alice, success=False, error='Gemini API error 503: overloaded')
        log(self.alice, success=False, error='Not an object: a cat')
        failures = analytics.build_report(7)['failures']
        self.assertEqual((failures[0]['error'], failures[0]['count']), ('Gemini API error 503: overloaded', 3))
        self.assertEqual(len(failures), 2)

    def test_top_users_ordered_by_calls(self):
        log(self.bob)
        log(self.alice)
        log(self.alice, input_tokens=1_000_000)
        users = analytics.build_report(7)['top_users']
        self.assertEqual([u['user__email'] for u in users], ['alice@mail.com', 'bob@mail.com'])
        self.assertAlmostEqual(users[0]['cost'], 1.0)


class FormattingTests(SimpleTestCase):
    def test_percentile(self):
        self.assertIsNone(analytics.percentile([], 0.5))
        self.assertEqual(analytics.percentile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 0.9), 9)
        self.assertEqual(analytics.percentile([7], 0.9), 7)

    def test_filters(self):
        self.assertEqual(seconds(9634), '9.6 s')
        self.assertEqual(seconds(None), '—')
        self.assertEqual(usd(0.0017), '$0.0017')
        self.assertEqual(usd(12.3), '$12.30')
        self.assertEqual(usd(0), '$0')
        self.assertEqual(percent(0.9523), '95%')
        self.assertEqual(compact(1284), '1,284')
        self.assertEqual(compact(12940), '12.9K')
        self.assertEqual(compact(4_200_000), '4.2M')


class AnalyticsPageTests(TempMediaMixin, TestCase):
    url = reverse('admin-analytics')

    def setUp(self):
        self.admin = User.objects.create_superuser(email='curator@mail.com', password=PASSWORD)

    def test_staff_sees_the_page(self):
        log(self.admin, input_tokens=1732, output_tokens=462, prompt=SystemPrompt.active())
        log(self.admin, success=False, error='Gemini API error 503: overloaded')
        self.client.force_login(self.admin)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        for text in ['Gemini calls per day', 'By prompt version', 'Texting voice (redesign)',
                     'Gemini API error 503: overloaded', 'curator@mail.com', 'id="daily-data"']:
            with self.subTest(text=text):
                self.assertContains(response, text)
        self.assertEqual(response.context['report']['days'], 30)

    def test_empty_state(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(self.url), 'No Gemini calls in this period')

    def test_period_switch_and_bad_values(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(self.url, {'days': 7}).context['report']['days'], 7)
        self.assertEqual(self.client.get(self.url, {'days': 9999}).context['report']['days'], 30)
        self.assertEqual(self.client.get(self.url, {'days': 'abc'}).context['report']['days'], 30)

    def test_non_staff_and_anonymous_are_sent_to_admin_login(self):
        visitor = User.objects.create_user(email='visitor@mail.com', password=PASSWORD)
        for user in [None, visitor]:
            with self.subTest(user=user):
                self.client.logout()
                if user:
                    self.client.force_login(user)
                response = self.client.get(self.url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse('admin:login'), response['Location'])

    def test_admin_home_links_to_analytics(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse('admin:index')), self.url)

    def test_generation_log_list_shows_time_and_tokens(self):
        log(self.admin, duration_ms=9634, input_tokens=1732, output_tokens=462, thinking_tokens=10)
        self.client.force_login(self.admin)
        response = self.client.get(reverse('admin:museum_generationlog_changelist'))
        self.assertContains(response, '9.6 s')
        self.assertContains(response, '1,732 / 472')
