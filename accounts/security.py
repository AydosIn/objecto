"""Who is knocking: the visitor's IP and login name, for lockouts and signup limits."""

import datetime

from django.conf import settings
from django.utils import timezone

from .models import Profile


def client_ip(request):
    """The visitor's IP address.

    On Vercel every request arrives through Vercel's proxy, so REMOTE_ADDR is the proxy.
    Vercel puts the real address in X-Vercel-Forwarded-For and overwrites any value the
    visitor sends, so it can't be faked there. Off Vercel the header is missing, and the
    direct connection address is used. Behind any other proxy this header would be
    forgeable, so check this function before moving hosts.
    """
    forwarded = request.META.get('HTTP_X_VERCEL_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


def login_username(request, credentials):
    """The email being tried, lowercased, so GERALD@mail.com and gerald@mail.com share
    one lockout counter (logins match emails in any case, see UserManager)."""
    username = (credentials or {}).get('username') or request.POST.get('username', '')
    return username.strip().lower()


def signups_from_ip_today(ip):
    """Accounts created from this IP in the last 24 hours."""
    since = timezone.now() - datetime.timedelta(hours=24)
    return Profile.objects.filter(signup_ip=ip, user__date_joined__gte=since).count()


def signup_limit_reached(ip):
    return bool(ip) and signups_from_ip_today(ip) >= settings.SIGNUPS_PER_IP_PER_DAY
