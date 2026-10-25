import pytest

from app.domain.uploads import types
from app.domain.uploads.errors import UnsupportedFileTypeError

HEADS = {
    types.JPEG: b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01',
    types.PNG: b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR',
    types.WEBP: b'RIFF\x24\x00\x00\x00WEBPVP8 ',
    types.GIF: b'GIF89a\x01\x00\x01\x00\x00\x00\x00\x00\x00\x00',
    types.PDF: b'%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0',
    types.MP4: b'\x00\x00\x00\x20ftypisom\x00\x00\x02\x00',
    types.QUICKTIME: b'\x00\x00\x00\x14ftypqt  \x00\x00\x00\x00',
    types.WEBM: b'\x1a\x45\xdf\xa3\x01\x00\x00\x00\x00\x00\x00\x1fB\x86\x81\x01',
}


@pytest.mark.parametrize(('content_type', 'head'), HEADS.items())
def test_format_is_sniffed_from_content(content_type, head):
    assert types.sniff_content_type(head) == content_type


def test_html_is_not_an_image():
    with pytest.raises(UnsupportedFileTypeError):
        types.ensure_type_allowed(b'<html><script>', types.IMAGE_TYPES)


def test_pdf_is_rejected_where_only_images_are_allowed():
    with pytest.raises(UnsupportedFileTypeError):
        types.ensure_type_allowed(HEADS[types.PDF], types.IMAGE_TYPES)


def test_mp4_and_mov_are_one_family():
    types.ensure_content_matches(types.MP4, HEADS[types.QUICKTIME])
    types.ensure_content_matches(types.QUICKTIME, HEADS[types.MP4])


def test_declared_type_must_match_content():
    with pytest.raises(UnsupportedFileTypeError):
        types.ensure_content_matches(types.JPEG, HEADS[types.PNG])
