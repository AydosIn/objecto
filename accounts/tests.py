import re

from django.contrib.auth import authenticate, get_user_model
from django.core import mail
from django.test import TestCase
from django.urls import reverse

from .models import Profile

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
        user = authenticate(email='GERALD@mail.com', password='s3cret-mug')
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
        self.assertRedirects(response, reverse('profile'))
        user = User.objects.get(email='new.visitor@mail.com')
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_duplicate_email_in_other_case_is_rejected(self):
        User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        response = self.post(email='GERALD@mail.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'An account with this email already exists.')
        self.assertEqual(User.objects.count(), 1)

    def test_mismatched_passwords_are_rejected(self):
        response = self.post(password2='something-else')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.exists())

    def test_logged_in_user_is_redirected_away(self):
        user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        self.client.force_login(user)
        self.assertRedirects(self.client.get(self.url), reverse('profile'))


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)

    def test_login_with_email(self):
        response = self.client.post(
            reverse('login'), {'username': 'Gerald@mail.com', 'password': PASSWORD}
        )
        self.assertRedirects(response, reverse('profile'))

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
        self.assertContains(response, 'Every object in your home has a past.')
        self.assertContains(response, reverse('signup'))

    def test_logged_in_user_sees_add_object(self):
        user = User.objects.create_user(email='gerald@mail.com', password=PASSWORD)
        self.client.force_login(user)
        response = self.client.get(reverse('landing'))
        self.assertContains(response, reverse('museum:new'))
        self.assertNotContains(response, f'href="{reverse("signup")}"')
