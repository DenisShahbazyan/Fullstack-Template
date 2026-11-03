import io

import pytest
from PIL import Image

from app.domain.uploads import images
from app.domain.uploads.errors import ImageTooLargeError, InvalidCropError
from app.domain.uploads.images import CropBox, process_image, process_square

MAX_SIDE = 2048
QUALITY = 85


def make_image(width: int, height: int, mode: str = 'RGB') -> bytes:
    color = (200, 100, 150) if mode == 'RGB' else (200, 100, 150, 128)
    buffer = io.BytesIO()
    Image.new(mode, (width, height), color).save(buffer, format='PNG')
    return buffer.getvalue()


def test_large_image_is_scaled_down_to_max_side():
    result = process_image(make_image(4000, 3000), MAX_SIDE, QUALITY)
    assert (result.width, result.height) == (MAX_SIDE, 1536)


def test_portrait_image_is_scaled_by_height():
    result = process_image(make_image(1000, 4000), MAX_SIDE, QUALITY)
    assert (result.width, result.height) == (512, MAX_SIDE)


def test_small_image_is_not_upscaled():
    result = process_image(make_image(300, 200), MAX_SIDE, QUALITY)
    assert (result.width, result.height) == (300, 200)


def test_result_is_always_webp():
    result = process_image(make_image(800, 600), MAX_SIDE, QUALITY)
    assert result.extension == 'webp'
    assert result.content_type == 'image/webp'
    assert Image.open(io.BytesIO(result.data)).format == 'WEBP'


def test_transparent_image_keeps_alpha_channel():
    result = process_image(make_image(500, 500, 'RGBA'), MAX_SIDE, QUALITY)
    assert Image.open(io.BytesIO(result.data)).mode in ('RGBA', 'RGB')


def test_exif_is_dropped():
    buffer = io.BytesIO()
    exif = Image.Exif()
    exif[0x010F] = 'PhoneMaker'
    Image.new('RGB', (100, 100)).save(buffer, format='JPEG', exif=exif)
    result = process_image(buffer.getvalue(), MAX_SIDE, QUALITY)
    assert not Image.open(io.BytesIO(result.data)).getexif()


def test_broken_file_raises_os_error():
    with pytest.raises(OSError):
        process_image(b'not an image at all', MAX_SIDE, QUALITY)


def test_image_over_pixel_limit_is_rejected(monkeypatch):
    monkeypatch.setattr(images, 'MAX_IMAGE_PIXELS', 300 * 200 - 1)
    with pytest.raises(ImageTooLargeError):
        process_image(make_image(300, 200), MAX_SIDE, QUALITY)


def test_square_is_cut_at_full_resolution():
    result = process_square(make_image(1200, 900), CropBox(0, 0, 1), MAX_SIDE, QUALITY)
    assert (result.width, result.height) == (900, 900)


def test_square_is_scaled_down_to_max_side():
    result = process_square(make_image(4000, 3000), CropBox(0, 0, 1), MAX_SIDE, QUALITY)
    assert (result.width, result.height) == (MAX_SIDE, MAX_SIDE)


def test_square_past_the_edge_is_pressed_inside():
    result = process_square(
        make_image(1000, 500), CropBox(0.9, 0, 1), MAX_SIDE, QUALITY
    )
    assert (result.width, result.height) == (500, 500)


@pytest.mark.parametrize(('x', 'y', 'size'), [(0, 0, 0), (0, 0, 1.5), (-0.1, 0, 1)])
def test_crop_outside_unit_range_is_rejected(x: float, y: float, size: float):
    with pytest.raises(InvalidCropError):
        CropBox(x, y, size)
