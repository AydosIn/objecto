import base64
import hashlib
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from museum.tests.utils import TempMediaMixin, make_exhibit

User = get_user_model()
PASSWORD = 's3cret-mug'

INLINE_SCRIPT = re.compile(r'<script(?![^>]*\bsrc=)(?![^>]*type="application/json")[^>]*>(.*?)</script>', re.S)
EVENT_HANDLER = re.compile(r'<[^>]+\son[a-z]+\s*=', re.I)


def script_hash(body):
    return "'sha256-" + base64.b64encode(hashlib.sha256(body.encode()).digest()).decode() + "'"


class ContentSecurityPolicyTests(TempMediaMixin, TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(email='curator@mail.com', password=PASSWORD)
        self.exhibit = make_exhibit(self.admin)

    def test_every_response_has_the_header(self):
        header = self.client.get(reverse('landing'))['Content-Security-Policy']
        self.assertIn("default-src 'self'", header)
        self.assertIn("object-src 'none'", header)
        self.assertIn("frame-ancestors 'none'", header)

    def test_every_inline_script_is_allowed_by_its_hash(self):
        """A new inline <script> or onclick="" would be blocked in the browser. This
        fails first, so the page doesn't silently break in production."""
        allowed = settings.CONTENT_SECURITY_POLICY['script-src']
        public = ['landing', 'login', 'signup', 'password_reset']
        private = [
            reverse('museum:index'),
            reverse('museum:new'),
            reverse('museum:detail', args=[self.exhibit.pk]),
            reverse('profile'),
            reverse('admin:index'),
            reverse('admin:museum_exhibit_changelist'),
            reverse('admin:museum_exhibit_change', args=[self.exhibit.pk]),
            reverse('admin:museum_systemprompt_add'),
            reverse('admin-analytics'),
        ]
        pages = [(reverse(name), False) for name in public] + [(url, True) for url in private]
        for url, logged_in in pages:
            with self.subTest(url=url):
                if logged_in:
                    self.client.force_login(self.admin)
                else:
                    self.client.logout()
                html = self.client.get(url).content.decode()
                for body in INLINE_SCRIPT.findall(html):
                    self.assertIn(script_hash(body), allowed, f'inline script on {url}: {body[:60]!r}')
                self.assertIsNone(EVENT_HANDLER.search(html), f'inline event handler on {url}')
