"""Показ чисел и дат в шаблонах: одинаково на сайте и в админке."""

from datetime import date, datetime
from decimal import Decimal

from app.core.clock import local_today, utc_to_local

# Узкий неразрывный пробел: «1 500» не разрывается на конце строки.
_THIN_SPACE = ' '


def ru_plural(count: int, forms: str) -> str:
    """`forms` — три формы через `|`: «запись|записи|записей»."""
    one, few, many = forms.split('|')
    n = abs(count) % 100
    if 11 <= n <= 14:
        return many
    rem = n % 10
    if rem == 1:
        return one
    if 2 <= rem <= 4:
        return few
    return many


def money(value: Decimal | float | int | None) -> str:
    """1500 → «1 500», 1500.5 → «1 500,50»: копейки, только если они есть."""
    if value is None:
        return ''
    amount = Decimal(str(value)).quantize(Decimal('0.01'))
    whole = f'{int(amount):,}'.replace(',', _THIN_SPACE)
    cents = int(abs(amount) * 100) % 100
    return f'{whole},{cents:02d}' if cents else whole


def local_dt(value: datetime, fmt: str = '%d.%m.%Y %H:%M') -> str:
    """Время из базы (`created_at`, UTC без пояса) — по местным часам."""
    return utc_to_local(value).strftime(fmt)


def relative_day(value: date) -> str:
    """Местный день относительно сегодня: «вчера», «через 3 дня», «12 дней назад».

    Ждёт местное время: `created_at` сначала через фильтр `to_local`.
    """
    day = value.date() if isinstance(value, datetime) else value
    days = (day - local_today()).days
    named = {0: 'сегодня', 1: 'завтра', -1: 'вчера'}
    if days in named:
        return named[days]
    label = f'{abs(days)} {ru_plural(abs(days), "день|дня|дней")}'
    return f'через {label}' if days > 0 else f'{label} назад'
