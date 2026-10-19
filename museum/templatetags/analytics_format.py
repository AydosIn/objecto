from django import template

register = template.Library()


@register.filter
def seconds(milliseconds):
    """9634 → '9.6 s'"""
    if milliseconds is None:
        return '—'
    return f'{milliseconds / 1000:.1f} s'


@register.filter
def usd(amount):
    """Small amounts keep enough digits to be meaningful: $0.0017, $0.42, $12.30"""
    if amount is None:
        return '—'
    if amount == 0:
        return '$0'
    if amount < 0.01:
        return f'${amount:.4f}'
    return f'${amount:,.2f}'


@register.filter
def percent(rate):
    """0.9523 → '95%'"""
    if rate is None:
        return '—'
    return f'{rate * 100:.0f}%'


@register.filter
def compact(number):
    """1284 → '1,284', 12940 → '12.9K', 4200000 → '4.2M'"""
    if number is None:
        return '—'
    number = round(number)
    if number >= 1_000_000:
        return f'{number / 1_000_000:.1f}M'
    if number >= 10_000:
        return f'{number / 1_000:.1f}K'
    return f'{number:,}'
