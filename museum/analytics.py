"""Numbers for the admin analytics page, computed from GenerationLog and Exhibit.

Kept apart from the view so every figure can be tested without rendering HTML.
"""

import datetime
import math

from django.conf import settings
from django.db.models import Avg, Count, Max, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import Exhibit, GenerationLog

PERIODS = {7: 'Last 7 days', 30: 'Last 30 days', 90: 'Last 90 days'}
DEFAULT_PERIOD = 30

# A refusal ("that's a person / a drawing") is a working answer from Gemini,
# not an error, so the page counts the two separately.
REFUSAL_PREFIX = 'Not an object:'

SUCCEEDED = Q(success=True)
REFUSED = Q(success=False, error__startswith=REFUSAL_PREFIX)
ERRORED = Q(success=False) & ~Q(error__startswith=REFUSAL_PREFIX)


def estimate_cost(input_tokens, billed_output_tokens):
    """USD, using the per-1M prices in settings. Thinking tokens count as output."""
    return (
        input_tokens / 1_000_000 * settings.GEMINI_PRICE_INPUT_PER_M
        + billed_output_tokens / 1_000_000 * settings.GEMINI_PRICE_OUTPUT_PER_M
    )


def percentile(sorted_values, fraction):
    """Nearest-rank percentile of an already sorted list (None if empty)."""
    if not sorted_values:
        return None
    rank = max(1, math.ceil(fraction * len(sorted_values)))
    return sorted_values[rank - 1]


def period_start(days, now=None):
    """Midnight at the start of the first day in the period, so 'last 7 days' means
    today plus the six days before it."""
    today = timezone.localdate(now)
    first_day = today - datetime.timedelta(days=days - 1)
    return first_day, timezone.make_aware(datetime.datetime.combine(first_day, datetime.time.min))


def build_report(days=DEFAULT_PERIOD, now=None):
    first_day, since = period_start(days, now)
    logs = GenerationLog.objects.filter(created_at__gte=since)

    totals = logs.aggregate(
        calls=Count('id'),
        succeeded=Count('id', filter=SUCCEEDED),
        refused=Count('id', filter=REFUSED),
        errored=Count('id', filter=ERRORED),
        users=Count('user', distinct=True),
        # Named *_sum so they don't shadow the fields that calls_with_tokens filters on.
        input_sum=Sum('input_tokens', default=0),
        output_sum=Sum('output_tokens', default=0),
        thinking_sum=Sum('thinking_tokens', default=0),
        calls_with_tokens=Count('id', filter=Q(input_tokens__gt=0)),
    )
    totals['input_tokens'] = totals.pop('input_sum')
    totals['output_tokens'] = totals.pop('output_sum')
    totals['thinking_tokens'] = totals.pop('thinking_sum')
    billed_output = totals['output_tokens'] + totals['thinking_tokens']
    cost = estimate_cost(totals['input_tokens'], billed_output)

    durations = sorted(
        logs.filter(SUCCEEDED, duration_ms__isnull=False).values_list('duration_ms', flat=True)
    )

    return {
        'days': days,
        'first_day': first_day,
        'exhibits_created': Exhibit.objects.filter(created_at__gte=since).count(),
        'totals': {
            **totals,
            'billed_output_tokens': billed_output,
            'success_rate': _rate(totals['succeeded'], totals['calls']),
            'cost': cost,
            'cost_per_success': cost / totals['succeeded'] if totals['succeeded'] else None,
            'median_ms': percentile(durations, 0.5),
            'p90_ms': percentile(durations, 0.9),
        },
        'daily': _daily(logs, first_day, days),
        'by_kind': _by_kind(logs),
        'by_prompt': _by_prompt(logs),
        'failures': _failures(logs),
        'top_users': _top_users(logs),
        'prices': {
            'input': settings.GEMINI_PRICE_INPUT_PER_M,
            'output': settings.GEMINI_PRICE_OUTPUT_PER_M,
        },
    }


def _rate(part, whole):
    return part / whole if whole else None


def _daily(logs, first_day, days):
    """One row per day, including days with no calls, oldest first."""
    counts = {
        row['day']: row
        for row in logs.annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(succeeded=Count('id', filter=SUCCEEDED), failed=Count('id', filter=~SUCCEEDED))
    }
    rows = []
    for offset in range(days):
        day = first_day + datetime.timedelta(days=offset)
        row = counts.get(day, {})
        rows.append(
            {'date': day.isoformat(), 'succeeded': row.get('succeeded', 0), 'failed': row.get('failed', 0)}
        )
    return rows


def _by_kind(logs):
    labels = dict(GenerationLog.Kind.choices)
    rows = (
        logs.values('kind')
        .annotate(calls=Count('id'), succeeded=Count('id', filter=SUCCEEDED))
        .order_by('-calls')
    )
    return [
        {**row, 'label': labels.get(row['kind'], row['kind']), 'success_rate': _rate(row['succeeded'], row['calls'])}
        for row in rows
    ]


def _by_prompt(logs):
    """Compare prompt versions: are newer prompts slower, longer, or refused more?"""
    rows = (
        logs.values('prompt_version', 'prompt_version__label', 'prompt_version__is_active')
        .annotate(
            calls=Count('id'),
            succeeded=Count('id', filter=SUCCEEDED),
            refused=Count('id', filter=REFUSED),
            avg_ms=Avg('duration_ms', filter=SUCCEEDED),
            avg_output_tokens=Avg('output_tokens', filter=SUCCEEDED & Q(output_tokens__gt=0)),
            input_tokens=Sum('input_tokens', default=0),
            billed_output=Sum('output_tokens', default=0) + Sum('thinking_tokens', default=0),
        )
        .order_by('-prompt_version')
    )
    return [
        {
            **row,
            'success_rate': _rate(row['succeeded'], row['calls']),
            'cost_per_success': (
                estimate_cost(row['input_tokens'], row['billed_output']) / row['succeeded']
                if row['succeeded']
                else None
            ),
        }
        for row in rows
    ]


def _failures(logs, limit=8):
    return list(
        logs.filter(success=False)
        .values('error')
        .annotate(count=Count('id'), last_seen=Max('created_at'))
        .order_by('-count', '-last_seen')[:limit]
    )


def _top_users(logs, limit=10):
    rows = (
        logs.values('user', 'user__email')
        .annotate(
            calls=Count('id'),
            succeeded=Count('id', filter=SUCCEEDED),
            input_tokens=Sum('input_tokens', default=0),
            billed_output=Sum('output_tokens', default=0) + Sum('thinking_tokens', default=0),
            last_seen=Max('created_at'),
        )
        .order_by('-calls', 'user__email')[:limit]
    )
    return [{**row, 'cost': estimate_cost(row['input_tokens'], row['billed_output'])} for row in rows]
