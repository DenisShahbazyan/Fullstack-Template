"""Какие файлы хранилища осиротели: на них не ссылается ни одна запись."""

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from datetime import datetime

from app.domain.uploads.errors import ImplausibleOrphanSweepError
from app.domain.uploads.urls import thumbnail_key

# Чистка, которая собралась удалить больше половины файлов, скорее всего видит
# не ту базу или пустой ответ. Небольшой бакет так не блокируем: там половина —
# это пара файлов из незавершённых загрузок.
MAX_ORPHAN_SHARE = 0.5
MIN_GUARDED_TOTAL = 100


@dataclass(frozen=True)
class StoredFile:
    key: str
    modified_at: datetime


def find_orphans(
    files: Iterable[StoredFile],
    referenced: Collection[str],
    written_before: datetime,
) -> list[str]:
    """Ключи файлов без ссылок, записанных раньше `written_before`.

    Превью живёт, пока жив его оригинал. Свежие файлы не трогаем: их загрузили,
    а запись о них ещё не сохранена.
    """
    live = set(referenced) | {thumbnail_key(key) for key in referenced}
    return sorted(
        file.key
        for file in files
        if file.key not in live and file.modified_at < written_before
    )


def ensure_sweep_plausible(total: int, orphans: int) -> None:
    """Останавливает чистку, которая удалила бы подозрительно много.

    Raises:
        ImplausibleOrphanSweepError: сирот больше MAX_ORPHAN_SHARE от всех файлов.
    """
    if total >= MIN_GUARDED_TOTAL and orphans > total * MAX_ORPHAN_SHARE:
        raise ImplausibleOrphanSweepError()
