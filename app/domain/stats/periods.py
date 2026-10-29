"""Периоды статистики: месяц, квартал, год или свой диапазон дат (скилл admin-stats).

Данные в прошлом (продажи, заказы): текущий период — по сегодня и
сравнивается с тем же отрезком прошлого. Если данные лежат и в будущем
(брони), `calendar_period` не обрезают сегодняшним днём — см. скилл.
"""

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class PeriodKind(StrEnum):
    MONTH = 'month'
    QUARTER = 'quarter'
    YEAR = 'year'


_MONTHS_IN: dict[PeriodKind, int] = {
    PeriodKind.MONTH: 1,
    PeriodKind.QUARTER: 3,
    PeriodKind.YEAR: 12,
}


@dataclass(frozen=True)
class Period:
    """Дни с `start` по `end` включительно и отрезок, с которым сравниваем.

    `kind` — календарный месяц, квартал или год; None — свой диапазон.
    """

    start: date
    end: date
    previous_start: date
    previous_end: date
    kind: PeriodKind | None


def _shift_months(day: date, months: int) -> date:
    """Тот же день на `months` месяцев раньше или позже; 31-е — в последний день."""
    index = day.year * 12 + day.month - 1 + months
    year, month = divmod(index, 12)
    last_day = calendar.monthrange(year, month + 1)[1]
    return date(year, month + 1, min(day.day, last_day))


def period_start(day: date, kind: PeriodKind) -> date:
    """Первое число месяца, квартала или года, в который попадает `day`."""
    months = _MONTHS_IN[kind]
    return date(day.year, (day.month - 1) // months * months + 1, 1)


def shift_period(start: date, kind: PeriodKind, steps: int) -> date:
    """Начало соседнего периода того же вида: -1 — предыдущего, 1 — следующего."""
    return _shift_months(start, steps * _MONTHS_IN[kind])


def calendar_period(day: date, kind: PeriodKind, today: date) -> Period:
    """Месяц, квартал или год с `day`. Текущий — по сегодня и сравнивается с
    тем же отрезком прошлого (1–25 октября с 1–25 сентября), прошедший —
    целиком с предыдущим целиком. Будущий не выбрать: данных за него нет."""
    start = period_start(min(day, today), kind)
    months = _MONTHS_IN[kind]
    full_end = _shift_months(start, months) - timedelta(days=1)
    if full_end <= today:
        end, previous_end = full_end, start - timedelta(days=1)
    else:
        end, previous_end = today, _shift_months(today, -months)
    return Period(
        start=start,
        end=end,
        previous_start=_shift_months(start, -months),
        previous_end=previous_end,
        kind=kind,
    )


def _whole_months(start: date, end: date) -> int | None:
    """Сколько целых месяцев в диапазоне: с 1-го числа по последнее."""
    is_month_end = (end + timedelta(days=1)).day == 1
    if start.day != 1 or not is_month_end:
        return None
    return (end.year - start.year) * 12 + end.month - start.month + 1


def range_period(first: date, last: date) -> Period:
    """Свой диапазон; сравнение — с отрезком прямо перед ним: целые месяцы — с
    теми же целыми месяцами (III квартал — со II), остальное — с тем же числом
    дней."""
    start, end = min(first, last), max(first, last)
    previous_end = start - timedelta(days=1)
    months = _whole_months(start, end)
    if months is None:
        previous_start = previous_end - (end - start)
    else:
        previous_start = _shift_months(start, -months)
    return Period(
        start=start,
        end=end,
        previous_start=previous_start,
        previous_end=previous_end,
        kind=None,
    )


def change_percent(current: int, previous: int) -> int | None:
    """На сколько процентов изменилось; None — сравнивать не с чем."""
    if previous <= 0:
        return None
    return round((current - previous) * 100 / previous)
