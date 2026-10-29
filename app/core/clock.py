"""Местное время проекта: всё, что человек видит как дату и час, — в его поясе.

Сервер живёт в UTC, а «сегодня» у посетителя наступает по местным часам.
"""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.core.config import settings

_ZONE = ZoneInfo(settings.site.TIMEZONE)


def local_now() -> datetime:
    """Местное время без пояса, с точностью до минуты."""
    return datetime.now(_ZONE).replace(tzinfo=None, second=0, microsecond=0)


def local_today() -> date:
    return local_now().date()


def utc_to_local(moment: datetime) -> datetime:
    """Время из `created_at` (UTC без пояса) — в местное без пояса."""
    return moment.replace(tzinfo=UTC).astimezone(_ZONE).replace(tzinfo=None)
