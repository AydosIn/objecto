"""The daily interview limit.

Every user gets DAILY_GENERATION_LIMIT interviews per day (a new exhibit, a reroll or a
rename each count as one). "Today" is the calendar day in settings.TIME_ZONE
(Uzbekistan). Only calls Gemini actually answered count: stories and "that's not an
object" refusals. Failures on Google's side (timeouts, overload) don't use one up.
Staff accounts are not limited.

On top of that, the whole site gets SITE_DAILY_GENERATION_LIMIT interviews per day, so
nobody can use up the shared Gemini quota by making lots of accounts.
"""

import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.utils import timezone

from museum.analytics import REFUSAL_PREFIX
from museum.models import GenerationLog

LIMIT_MESSAGE = "your stuff needs a break. that's all {limit} interviews for today, come back tomorrow."
SITE_LIMIT_MESSAGE = "the museum is full for today. too many interviews. come back tomorrow."


def start_of_today(now=None):
    today = timezone.localdate(now)
    return timezone.make_aware(datetime.datetime.combine(today, datetime.time.min))


def counted_today(now=None):
    """Today's interviews that count toward a limit, for every user."""
    return GenerationLog.objects.filter(created_at__gte=start_of_today(now)).filter(
        Q(success=True) | Q(error__startswith=REFUSAL_PREFIX)
    )


def used_today(user, now=None):
    return counted_today(now).filter(user=user).count()


def remaining_today(user):
    """How many interviews are left today, or None for staff (unlimited)."""
    if user.is_staff:
        return None
    return max(0, settings.DAILY_GENERATION_LIMIT - used_today(user))


def limit_message():
    return LIMIT_MESSAGE.format(limit=settings.DAILY_GENERATION_LIMIT)


def lock_quota(user):
    """Call inside transaction.atomic(), before limit_reached(). Locks this user's row
    until the transaction ends, so parallel requests from one user wait in line: each
    one sees the interviews logged by the ones before it, and none can slip past the
    limit while another is still waiting on Gemini."""
    get_user_model().objects.select_for_update().only('pk').get(pk=user.pk)


def limit_reached(user):
    """Why this user can't have another interview right now, or None if they can."""
    if user.is_staff:
        return None
    if counted_today().count() >= settings.SITE_DAILY_GENERATION_LIMIT:
        return SITE_LIMIT_MESSAGE
    if remaining_today(user) == 0:
        return limit_message()
    return None


def quota_context(user):
    """For templates: what's left, and one dot per interview (filled = still available)."""
    remaining = remaining_today(user)
    if remaining is None:
        return {'remaining': None}
    used = settings.DAILY_GENERATION_LIMIT - remaining
    return {'remaining': remaining, 'quota_dots': [True] * remaining + [False] * used}
