"""Чистка осиротевших файлов: то, что лежит в папках сайта без ссылок из базы."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import batched

from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.core.s3.client import s3_client
from app.crud.public.stored_file import get_referenced_keys
from app.domain.uploads.orphans import (
    StoredFile,
    ensure_sweep_plausible,
    find_orphans,
)
from app.domain.uploads.project import SITE_FOLDERS

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SweepPlan:
    total: int
    orphans: list[str]


async def plan_orphan_sweep() -> SweepPlan:
    """Сироты среди файлов сайта, записанных раньше, чем ORPHAN_TTL_HOURS назад.

    Ссылки читаются до листинга: файл, загруженный после чтения базы, свежий,
    и чистка его не тронет.
    """
    async with AsyncSessionLocal() as session:
        referenced = await get_referenced_keys(session)
    files: list[StoredFile] = []
    for folder in (*SITE_FOLDERS, settings.s3.TMP_PATH):
        files += await s3_client.list_files(f'{folder}/')
    written_before = datetime.now(UTC) - timedelta(hours=settings.s3.ORPHAN_TTL_HOURS)
    return SweepPlan(len(files), find_orphans(files, referenced, written_before))


async def delete_orphans(keys: list[str]) -> int:
    """Удаляет файлы пачками, отдаёт число удалённых."""
    deleted = 0
    for batch in batched(keys, settings.s3.SWEEP_BATCH_SIZE):
        result = await s3_client.delete_many(list(batch))
        deleted += len(result.deleted)
        if result.failed:
            logger.warning('orphan uploads not deleted', extra={'keys': result.failed})
    return deleted


async def sweep_orphans() -> int:
    """Удаляет сирот, если их не подозрительно много; отдаёт число удалённых.

    Raises:
        ImplausibleOrphanSweepError: сирот больше половины файлов — разобраться
            и запустить руками: `scripts/uploads/sweep_orphans.py --force`.
    """
    plan = await plan_orphan_sweep()
    ensure_sweep_plausible(plan.total, len(plan.orphans))
    deleted = await delete_orphans(plan.orphans)
    logger.info('orphan uploads swept', extra={'total': plan.total, 'deleted': deleted})
    return deleted
