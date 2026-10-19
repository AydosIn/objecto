from django.contrib.auth import authenticate, get_user_model
from django.test import TestCase

User = get_user_model()


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
