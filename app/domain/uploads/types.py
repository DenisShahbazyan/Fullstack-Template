"""Формат файла по первым байтам.

Имени и типу от браузера не верим: телефоны отдают расширение, не совпадающее
с содержимым, а при прямой загрузке в S3 тип объекта задаёт сам браузер.
"""

from collections.abc import Collection

from app.domain.uploads.errors import UnsupportedFileTypeError

# Сколько байт начала файла нужно, чтобы узнать его формат.
HEAD_SIZE = 16

JPEG = 'image/jpeg'
PNG = 'image/png'
WEBP = 'image/webp'
GIF = 'image/gif'
BMP = 'image/bmp'
TIFF = 'image/tiff'
PDF = 'application/pdf'
MP4 = 'video/mp4'
QUICKTIME = 'video/quicktime'
WEBM = 'video/webm'

# То, что Pillow открывает и перекодирует в WebP.
IMAGE_TYPES = frozenset({JPEG, PNG, WEBP, GIF, BMP, TIFF})
# Расширение ключа для файлов, которые хранятся как есть.
EXTENSIONS = {PDF: 'pdf', MP4: 'mp4', QUICKTIME: 'mov', WEBM: 'webm'}

_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b'\xff\xd8\xff', JPEG),
    (b'\x89PNG\r\n\x1a\n', PNG),
    (b'GIF87a', GIF),
    (b'GIF89a', GIF),
    (b'BM', BMP),
    (b'II*\x00', TIFF),
    (b'MM\x00*', TIFF),
    (b'%PDF-', PDF),
    (b'\x1a\x45\xdf\xa3', WEBM),
)
# MP4 и MOV — один контейнер ISO BMFF: первым ящиком почти всегда идёт ftyp,
# у старых QuickTime-файлов — moov, mdat, wide или free.
_ISO_FIRST_BOXES = frozenset({b'ftyp', b'moov', b'mdat', b'wide', b'free', b'skip'})
_ISO_TYPES = frozenset({MP4, QUICKTIME})


def sniff_content_type(head: bytes) -> str | None:
    """MIME-тип по первым HEAD_SIZE байтам; None — формат не из известных."""
    for signature, content_type in _SIGNATURES:
        if head.startswith(signature):
            return content_type
    if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
        return WEBP
    if head[4:8] in _ISO_FIRST_BOXES:
        return QUICKTIME if head[8:12] == b'qt  ' else MP4
    return None


def ensure_type_allowed(head: bytes, allowed: Collection[str]) -> str:
    """Тип файла по содержимому, если он среди разрешённых.

    Raises:
        UnsupportedFileTypeError: формат неизвестен или не разрешён.
    """
    content_type = sniff_content_type(head)
    if content_type is None or content_type not in allowed:
        raise UnsupportedFileTypeError()
    return content_type


def ensure_content_matches(declared: str, head: bytes) -> None:
    """Содержимое — того формата, что заявил клиент.

    MP4 и MOV браузер называет как придётся, поэтому внутри семейства тип
    не сверяем.

    Raises:
        UnsupportedFileTypeError: содержимое другого формата.
    """
    sniffed = sniff_content_type(head)
    if sniffed != declared and not {sniffed, declared} <= _ISO_TYPES:
        raise UnsupportedFileTypeError()
