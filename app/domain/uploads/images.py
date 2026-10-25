"""Обработка загружаемых изображений: ресайз и конвертация в WebP."""

import io
from dataclasses import dataclass

from PIL import Image, ImageOps

from app.domain.uploads.errors import ImageTooLargeError

WEBP_FORMAT = 'WEBP'
WEBP_EXTENSION = 'webp'
WEBP_CONTENT_TYPE = 'image/webp'

# Снимок с телефона — до 50 Мп. Больше — почти наверняка «бомба»: PNG на 20 МБ
# разворачивается при декодировании в гигабайты памяти. Размер известен до
# декодирования, поэтому проверка дешёвая.
MAX_IMAGE_PIXELS = 60_000_000


@dataclass(frozen=True)
class ProcessedImage:
    """Готовое к загрузке изображение."""

    data: bytes
    extension: str
    content_type: str
    width: int
    height: int


def process_image(raw: bytes, max_side: int, quality: int) -> ProcessedImage:
    """Ужимает изображение по большей стороне и переводит в WebP.

    Пропорции сохраняются, картинки меньше max_side не увеличиваются.
    EXIF-поворот применяется, а сам EXIF отбрасывается — в нём бывают
    геометки, а это персональные данные.

    Raises:
        ImageTooLargeError: в изображении больше MAX_IMAGE_PIXELS точек.
        OSError: файл не читается как изображение.
    """
    with open_image(raw) as source:
        image = to_display_mode(source)
        image.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        return encode_webp(image, quality)


def open_image(raw: bytes) -> Image.Image:
    """Открывает изображение, не декодируя его, и отсекает слишком большие.

    Raises:
        ImageTooLargeError: в изображении больше MAX_IMAGE_PIXELS точек.
        OSError: файл не читается как изображение.
    """
    try:
        source = Image.open(io.BytesIO(raw))
    except Image.DecompressionBombError as error:
        raise ImageTooLargeError() from error
    if source.width * source.height > MAX_IMAGE_PIXELS:
        source.close()
        raise ImageTooLargeError()
    return source


def to_display_mode(source: Image.Image) -> Image.Image:
    """Поворот по EXIF и режим цвета, который умеет WebP."""
    image = ImageOps.exif_transpose(source)
    return image.convert('RGBA' if _has_alpha(image) else 'RGB')


def encode_webp(image: Image.Image, quality: int) -> ProcessedImage:
    buffer = io.BytesIO()
    image.save(buffer, format=WEBP_FORMAT, quality=quality, method=6)
    return ProcessedImage(
        data=buffer.getvalue(),
        extension=WEBP_EXTENSION,
        content_type=WEBP_CONTENT_TYPE,
        width=image.width,
        height=image.height,
    )


def _has_alpha(image: Image.Image) -> bool:
    return image.mode in ('RGBA', 'LA', 'PA') or 'transparency' in image.info
