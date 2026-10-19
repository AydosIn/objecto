"""The daily interview limit.

Every user gets DAILY_GENERATION_LIMIT interviews per day (a new exhibit, a reroll or a
rename each count as one). "Today" is the calendar day in settings.TIME_ZONE
(Uzbekistan). Only calls Gemini actually answered count: stories and "that's not an
object" refusals. Failures on Google's side (timeouts, overload) don't use one up.
Staff accounts are not limited.
"""

import datetime

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from museum.analytics import REFUSAL_PREFIX
from museum.models import GenerationLog

LIMIT_MESSAGE = "your stuff needs a break. that's all {limit} interviews for today, come back tomorrow."


def start_of_today(now=None):
    today = timezone.localdate(now)
    return timezone.make_aware(datetime.datetime.combine(today, datetime.time.min))


def used_today(user, now=None):
    return (
        GenerationLog.objects.filter(user=user, created_at__gte=start_of_today(now))
        .filter(Q(success=True) | Q(error__startswith=REFUSAL_PREFIX))
        .count()
    )


def remaining_today(user):
    """How many interviews are left today, or None for staff (unlimited)."""
    if user.is_staff:
        return None
    return max(0, settings.DAILY_GENERATION_LIMIT - used_today(user))


def limit_message():
    return LIMIT_MESSAGE.format(limit=settings.DAILY_GENERATION_LIMIT)


def quota_context(user):
    """For templates: what's left, and one dot per interview (filled = still available)."""
    remaining = remaining_today(user)
    if remaining is None:
        return {'remaining': None}
    used = settings.DAILY_GENERATION_LIMIT - remaining
    return {'remaining': remaining, 'quota_dots': [True] * remaining + [False] * used}
