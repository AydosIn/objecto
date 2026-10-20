import datetime
import re

from django.contrib.auth import authenticate, get_user_model
from django.core import mail
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import Profile
from .security import client_ip

User = get_user_model()
PASSWORD = 's3cret-mug'


class UserModelTests(TestCase):
    def test_create_user_uses_email_and_lowercases_it(self):
        user = User.objects.create_user(email='Gerald@Mail.COM', password='s3cret-mug')
        self.assertEqual(user.email, 'gerald@mail.com')
        self.assertFalse(user.is_staff)
        self.assertTrue(user.check_password('s3cret-mug'))

    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email='', password='s3cret-mug')

    def test_create_superuser_sets_flags(self):
        admin = User.objects.create_superuser(email='curator@mail.com', password='s3cret-mug')
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)

    def test_login_email_is_case_insensitive(self):
        User.objects.create_user(email='gerald@mail.com', password='s3cret-mug')
        # django-axes needs the request to know who is trying.
        request = RequestFactory().post('/accounts/login/')
        user = authenticate(request, username='GERALD@mail.com', password='s3cret-mug')
        self.assertIsNotNone(user)

    def test_new_user_gets_a_profile(self):
        user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        self.assertTrue(Profile.objects.filter(user=user).exists())


class SignupTests(TestCase):
    url = reverse('signup')

    def post(self, email='gerald@mail.com', password1=PASSWORD, password2=PASSWORD):
        return self.client.post(
            self.url, {'email': email, 'password1': password1, 'password2': password2}
        )

    def test_page_loads(self):
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_signup_creates_user_and_logs_in(self):
        response = self.post(email='New.Visitor@Mail.com')
        self.assertRedirects(response, reverse('museum:index'))
        user = User.objects.get(email='new.visitor@mail.com')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_duplicate_email_in_other_case_is_rejected(self):
        User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        response = self.post(email='GERALD@mail.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'there&#x27;s already an account with this email.')
        self.assertEqual(User.objects.count(), 1)

    def test_mismatched_passwords_are_rejected(self):
        response = self.post(password2='something-else')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_logged_in_user_is_redirected_away(self):
        user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        self.client.force_login(user)
        self.assertRedirects(self.client.get(self.url), reverse('museum:index'))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)

    def test_login_with_email(self):
        response = self.client.post(
            reverse('login'), {'username': 'Gerald@mail.com', 'password': PASSWORD}
        )
        self.assertRedirects(response, reverse('museum:index'))

    def test_wrong_password_shows_error(self):
        response = self.client.post(
            reverse('login'), {'username': 'gerald@mail.com', 'password': 'nope'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_requires_post_and_redirects_to_landing(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('landing'))
        self.assertNotIn('_auth_user_id', self.client.session)


class ProfileTests(TestCase):
    url = reverse('profile')

    def setUp(self):
        self.user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)

    def test_requires_login(self):
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('login')}?next={self.url}")

    def test_profile_page_has_log_out(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertContains(response, f'action="{reverse("logout")}"')
        self.assertContains(response, 'gerald@mail.com')

    def test_update_profile(self):
        self.client.force_login(self.user)
        response = self.client.post(
            self.url, {'display_name': 'Aydos', 'about_me': 'I drink too much tea.'}
        )
        self.assertRedirects(response, self.url)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.display_name, 'Aydos')
        self.assertEqual(self.user.profile.about_me, 'I drink too much tea.')

    def test_about_me_is_limited_to_300_characters(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {'display_name': '', 'about_me': 'x' * 301})
        self.assertEqual(response.status_code, 200)
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.about_me, '')


class PasswordResetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)

    def test_full_reset_flow(self):
        response = self.client.post(reverse('password_reset'), {'email': 'gerald@mail.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 1)

        link = re.search(r'http://testserver(/accounts/password-reset/\S+/)', mail.outbox[0].body)
        self.assertIsNotNone(link)
        # The first visit swaps the token in the URL for one kept in the session.
        response = self.client.get(link.group(1), follow=True)
        set_password_url = response.redirect_chain[-1][0]
        response = self.client.post(
            set_password_url,
            {'new_password1': 'brand-new-kettle', 'new_password2': 'brand-new-kettle'},
        )
        self.assertRedirects(response, reverse('password_reset_complete'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('brand-new-kettle'))

    def test_unknown_email_sends_nothing_but_looks_the_same(self):
        response = self.client.post(reverse('password_reset'), {'email': 'nobody@mail.com'})
        self.assertRedirects(response, reverse('password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)


class AdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email='curator@mail.com', password=PASSWORD)
        self.client.force_login(self.admin)

    def test_admin_pages_load(self):
        for url in [
            reverse('admin:accounts_user_changelist'),
            reverse('admin:accounts_user_add'),
            reverse('admin:accounts_user_change', args=[self.admin.pk]),
            reverse('admin:accounts_profile_changelist'),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_adding_user_in_admin_creates_exactly_one_profile(self):
        response = self.client.post(
            reverse('admin:accounts_user_add'),
            {
                'email': 'Visitor@Mail.com',
                'usable_password': 'true',
                'password1': PASSWORD,
                'password2': PASSWORD,
                '_save': 'Save',
            },
        )
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='visitor@mail.com')
        self.assertEqual(Profile.objects.filter(user=user).count(), 1)

    def test_non_staff_cannot_open_admin(self):
        visitor = User.objects.create_user(email='visitor@mail.com', password=PASSWORD)
        self.client.force_login(visitor)
        response = self.client.get(reverse('admin:accounts_user_changelist'))
        self.assertEqual(response.status_code, 302)


class LandingPageTests(TestCase):
    def test_visitor_sees_sign_up(self):
        response = self.client.get(reverse('landing'))
        self.assertContains(response, 'this is gerald.')
        self.assertContains(response, reverse('signup'))

    def test_logged_in_user_goes_to_their_museum(self):
        user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        self.client.force_login(user)
        response = self.client.get(reverse('landing'))
        self.assertRedirects(response, reverse('museum:index'))


class LoginLockoutTests(TestCase):
    """django-axes: 5 wrong passwords for one email from one IP locks that pair out."""

    def setUp(self):
        self.user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)

    def try_login(self, email='gerald@mail.com', password='wrong-password', ip='203.0.113.7', url=None):
        return self.client.post(
            url or reverse('login'),
            {'username': email, 'password': password},
            HTTP_X_VERCEL_FORWARDED_FOR=ip,
        )

    def test_fifth_wrong_password_locks_the_login(self):
        for _ in range(4):
            self.assertEqual(self.try_login().status_code, 200)
        response = self.try_login()
        self.assertEqual(response.status_code, 429)
        self.assertContains(response, 'too many tries', status_code=429)

    def test_right_password_is_refused_while_locked(self):
        for _ in range(5):
            self.try_login()
        response = self.try_login(password=PASSWORD)
        self.assertEqual(response.status_code, 429)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_changing_the_email_case_does_not_reset_the_count(self):
        for email in ['gerald@mail.com', 'GERALD@mail.com', 'Gerald@Mail.com', 'gerald@MAIL.com']:
            self.try_login(email=email)
        self.assertEqual(self.try_login(email='GeRaLd@mail.com').status_code, 429)

    def test_lockout_is_per_ip(self):
        """Someone else on another network can still log in to their own account."""
        for _ in range(5):
            self.try_login()
        response = self.try_login(password=PASSWORD, ip='198.51.100.20')
        self.assertRedirects(response, reverse('museum:index'))

    def test_success_resets_the_count(self):
        for _ in range(4):
            self.try_login()
        self.try_login(password=PASSWORD)
        self.client.logout()
        for _ in range(4):
            self.assertEqual(self.try_login().status_code, 200)

    def test_admin_login_is_protected_too(self):
        User.objects.create_superuser(email='curator@mail.com', password=PASSWORD)
        url = reverse('admin:login')
        for _ in range(5):
            response = self.try_login(email='curator@mail.com', url=url)
        self.assertEqual(response.status_code, 429)


class SignupLimitTests(TestCase):
    def sign_up(self, n, ip='203.0.113.7'):
        return self.client.post(
            reverse('signup'),
            {'email': f'gerald{n}@mail.com', 'password1': PASSWORD, 'password2': PASSWORD},
            HTTP_X_VERCEL_FORWARDED_FOR=ip,
        )

    def test_signup_remembers_the_ip(self):
        self.sign_up(1)
        self.assertEqual(User.objects.get(email='gerald1@mail.com').profile.signup_ip, '203.0.113.7')

    @override_settings(SIGNUPS_PER_IP_PER_DAY=2)
    def test_too_many_signups_from_one_ip_are_refused(self):
        for n in range(2):
            self.sign_up(n)
            self.client.logout()
        response = self.sign_up(3)
        self.assertContains(response, 'too many new accounts from this network today')
        self.assertFalse(User.objects.filter(email='gerald3@mail.com').exists())

    @override_settings(SIGNUPS_PER_IP_PER_DAY=2)
    def test_other_networks_and_old_signups_are_not_counted(self):
        for n in range(2):
            self.sign_up(n)
            self.client.logout()
        User.objects.update(date_joined=timezone.now() - datetime.timedelta(hours=25))
        self.assertRedirects(self.sign_up(3), reverse('museum:index'))
        self.client.logout()
        self.assertRedirects(self.sign_up(4, ip='198.51.100.20'), reverse('museum:index'))


class ClientIpTests(TestCase):
    def test_uses_vercels_header_when_present(self):
        request = RequestFactory().get('/', HTTP_X_VERCEL_FORWARDED_FOR='203.0.113.7', REMOTE_ADDR='10.0.0.1')
        self.assertEqual(client_ip(request), '203.0.113.7')

    def test_falls_back_to_the_connection_address(self):
        request = RequestFactory().get('/', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(client_ip(request), '127.0.0.1')

    def test_plain_x_forwarded_for_is_ignored(self):
        """Anyone can send X-Forwarded-For, so it must not change the IP."""
        request = RequestFactory().get('/', HTTP_X_FORWARDED_FOR='1.2.3.4', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(client_ip(request), '127.0.0.1')
