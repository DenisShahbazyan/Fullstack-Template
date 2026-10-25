"""Суточная чистка осиротевших загрузок — процесс сервиса uploads_sweep.

    python -m scripts.uploads.sweep_scheduler

Отдельный сервис, а не задача в web: инстансов web может быть несколько, а
чистка должна идти одна. Очереди с расписанием в каркасе нет, поэтому —
простой цикл: проснуться в SWEEP_AT (UTC), почистить, ждать следующих суток.
Время выбрано после суточной копии бакета (uploads_backup, полночь UTC):
удалённое ещё 30 дней лежит в её архиве.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, time, timedelta

from app.core.logs import setup_logging
from app.core.s3.sweep import sweep_orphans
from app.domain.errors import DomainError

SWEEP_AT = time(4, 30, tzinfo=UTC)

logger = logging.getLogger(__name__)


def seconds_until_next_run(now: datetime) -> float:
    run_at = datetime.combine(now.date(), SWEEP_AT)
    if run_at <= now:
        run_at += timedelta(days=1)
    return (run_at - now).total_seconds()


async def run_forever() -> None:
    while True:
        await asyncio.sleep(seconds_until_next_run(datetime.now(UTC)))
        try:
            await sweep_orphans()
        except DomainError:
            # Хранилище не ответило или сирот подозрительно много — ждём
            # следующих суток, а не падаем: падение перезапустило бы сервис.
            logger.exception('orphan uploads sweep skipped')


def main() -> None:
    setup_logging()
    asyncio.run(run_forever())


if __name__ == '__main__':
    main()
