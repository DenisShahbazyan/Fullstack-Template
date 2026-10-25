"""Обработка изображений вне цикла событий.

Ресайз и WebP с `method=6` занимают секунды CPU: в самом цикле они стопорили бы
все запросы воркера.
"""

from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.domain.uploads.errors import ImageProcessingError
from app.domain.uploads.images import ProcessedImage, process_image


async def process_image_in_thread(
    raw: bytes, max_side: int, quality: int
) -> ProcessedImage:
    """`process_image` в пуле потоков.

    Raises:
        ImageProcessingError: файл не удалось прочитать как изображение.
        ImageTooLargeError: в изображении слишком много точек.
    """
    try:
        return await run_in_threadpool(process_image, raw, max_side, quality)
    except OSError as error:
        raise ImageProcessingError() from error


async def process_with_thumbnail(raw: bytes) -> tuple[ProcessedImage, ProcessedImage]:
    """Ужимает изображение до IMAGE_MAX_SIDE и делает к нему превью.

    Raises:
        ImageProcessingError: файл не удалось прочитать как изображение.
        ImageTooLargeError: в изображении слишком много точек.
    """
    processed = await process_image_in_thread(
        raw, settings.s3.IMAGE_MAX_SIDE, settings.s3.WEBP_QUALITY
    )
    # Превью — из уже ужатого WebP: разбирать его дешевле, чем исходник
    # с телефона на десятки мегапикселей.
    thumbnail = await process_image_in_thread(
        processed.data, settings.s3.THUMBNAIL_SIDE, settings.s3.WEBP_QUALITY
    )
    return processed, thumbnail
