"""Обработка изображений вне цикла событий.

Ресайз и WebP с `method=6` занимают секунды CPU: в самом цикле они стопорили бы
все запросы воркера.
"""

import asyncio
from collections.abc import Callable

from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.domain.uploads.errors import ImageProcessingError
from app.domain.uploads.images import (
    CropBox,
    ProcessedImage,
    process_image,
    process_square,
)

# Декодированный снимок — сотни мегабайт даже из файла в 200 КБ (однотонный PNG):
# десяток загрузок разом съел бы память процесса. Остальные ждут очереди.
_DECODING = asyncio.Semaphore(2)


async def _in_thread[T](work: Callable[..., T], *args: object) -> T:
    async with _DECODING:
        return await run_in_threadpool(work, *args)


async def process_image_in_thread(
    raw: bytes, max_side: int, quality: int
) -> ProcessedImage:
    """`process_image` в пуле потоков.

    Raises:
        ImageProcessingError: файл не удалось прочитать как изображение.
        ImageTooLargeError: в изображении слишком много точек.
    """
    try:
        return await _in_thread(process_image, raw, max_side, quality)
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
    return processed, await _thumbnail_of(processed, settings.s3.THUMBNAIL_SIDE)


async def process_square_with_thumbnail(
    raw: bytes, box: CropBox
) -> tuple[ProcessedImage, ProcessedImage]:
    """Квадрат по кадру не больше IMAGE_MAX_SIDE и превью к нему.

    Превью — SQUARE_THUMBNAIL_SIDE: квадрат показывают кружком, а не карточкой.

    Raises:
        ImageProcessingError: файл не удалось прочитать как изображение.
        ImageTooLargeError: в изображении слишком много точек.
    """
    try:
        processed = await _in_thread(
            process_square,
            raw,
            box,
            settings.s3.IMAGE_MAX_SIDE,
            settings.s3.WEBP_QUALITY,
        )
    except OSError as error:
        raise ImageProcessingError() from error
    return processed, await _thumbnail_of(processed, settings.s3.SQUARE_THUMBNAIL_SIDE)


async def _thumbnail_of(processed: ProcessedImage, side: int) -> ProcessedImage:
    # Превью — из уже ужатого WebP: разбирать его дешевле, чем исходник
    # с телефона на десятки мегапикселей.
    return await process_image_in_thread(processed.data, side, settings.s3.WEBP_QUALITY)
