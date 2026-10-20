from django.conf import settings


class ContentSecurityPolicyMiddleware:
    """Sends settings.CONTENT_SECURITY_POLICY on every response. If an attacker ever
    gets HTML into a page, the browser still refuses to run their scripts or send data
    to their servers. (Django 6 has this built in; 5.2 doesn't.)"""

    def __init__(self, get_response):
        self.get_response = get_response
        self.header = '; '.join(
            f"{directive} {' '.join(sources)}".strip()
            for directive, sources in settings.CONTENT_SECURITY_POLICY.items()
        )

    def __call__(self, request):
        response = self.get_response(request)
        response.headers.setdefault('Content-Security-Policy', self.header)
        return response
