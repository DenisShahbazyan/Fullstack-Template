import logging

from app.core.s3.client import s3_client
from app.domain.uploads.errors import FileStorageUnavailableError
from app.domain.uploads.urls import is_external, thumbnail_key

logger = logging.getLogger(__name__)


async def discard_files(*keys: str | None) -> None:
    """Удаляет из S3 файлы, на которые больше никто не ссылается.

    Зовётся после commit. Превью уходит вместе с файлом. Ошибку хранилища не
    пробрасываем: запись уже изменена, и падать из-за неудалённого файла
    незачем — его подберёт ночная чистка сирот.
    """
    live = {key for key in keys if key and not is_external(key)}
    doomed = sorted(live | {thumbnail_key(key) for key in live})
    if not doomed:
        return
    try:
        result = await s3_client.delete_many(doomed)
    except FileStorageUnavailableError:
        logger.warning('uploads not discarded', extra={'keys': doomed}, exc_info=True)
        return
    if result.failed:
        logger.warning('uploads not discarded', extra={'keys': result.failed})
