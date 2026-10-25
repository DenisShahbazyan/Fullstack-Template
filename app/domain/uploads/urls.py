"""Ключи файлов хранилища и ссылки на них.

В БД хранится ключ (`portfolio/<uuid>.webp`), а не абсолютный URL: домен и имя
бакета — это инфраструктура. Бакет приватный, поэтому наружу отдаются
подписанные ссылки с ограниченным сроком жизни.

Временная загрузка лежит под `<tmp>/<id пользователя>/<uuid>.<расширение>`:
путь сам говорит, чья она, и принять её может только этот пользователь.
"""

import uuid
from collections.abc import Awaitable, Callable

_EXTERNAL_SCHEMES = ('http://', 'https://')
_THUMBNAIL_SOURCE_EXTENSION = '.webp'
_THUMBNAIL_SUFFIX = '_thumb'
_PDF_EXTENSION = '.pdf'

SignUrls = Callable[[list[str], int], Awaitable[list[str]]]


def new_key(folder: str, extension: str, token: str) -> str:
    """Ключ нового файла: случайное имя, а не имя файла пользователя."""
    return f'{folder}/{token}.{extension}'


def tmp_folder(tmp_root: str, user_id: int) -> str:
    """Папка временных загрузок пользователя."""
    return f'{tmp_root}/{user_id}'


def tmp_owner(key: str, tmp_root: str) -> int | None:
    """Автор временной загрузки по её ключу; None — ключ не временной загрузки.

    Превью и посторонние пути владельца не дают: принять можно только сам файл.
    """
    parts = key.split('/')
    if len(parts) != 3 or parts[0] != tmp_root or is_thumbnail(key):
        return None
    owner, name = parts[1], parts[2]
    if not owner.isascii() or not owner.isdigit() or not _is_token_name(name):
        return None
    return int(owner)


def _is_token_name(name: str) -> bool:
    token, dot, extension = name.partition('.')
    if not dot or not extension.isalnum():
        return False
    try:
        return str(uuid.UUID(token)) == token
    except ValueError:
        return False


def extension_of(key: str) -> str:
    return key.rsplit('.', 1)[-1]


def is_external(key: str) -> bool:
    """Ключ — абсолютная ссылка на чужой домен, а не файл нашего бакета."""
    return key.startswith(_EXTERNAL_SCHEMES)


def is_pdf(key: str) -> bool:
    """Файл — PDF: в <img> его не показать, открывается ссылкой."""
    return key.lower().endswith(_PDF_EXTENSION)


def is_thumbnail(key: str) -> bool:
    """Ключ сам указывает на превью, а не на оригинал."""
    return key.endswith(f'{_THUMBNAIL_SUFFIX}{_THUMBNAIL_SOURCE_EXTENSION}')


def thumbnail_key(key: str) -> str:
    """Ключ превью: `portfolio/<uuid>.webp` → `portfolio/<uuid>_thumb.webp`.

    Превью есть только у перекодированных в WebP изображений; для документов,
    видео и чужих ссылок возвращается сам ключ — показывать больше нечего.
    """
    if is_external(key) or not key.endswith(_THUMBNAIL_SOURCE_EXTENSION):
        return key
    stem = key.removesuffix(_THUMBNAIL_SOURCE_EXTENSION)
    return f'{stem}{_THUMBNAIL_SUFFIX}{_THUMBNAIL_SOURCE_EXTENSION}'


async def build_file_url_map(
    keys: list[str | None],
    sign_many: SignUrls,
    expires_in: int,
) -> dict[str, str]:
    """Карта «ключ → ссылка»: пустые пропущены, повторы подписаны раз.

    Вместе с каждым ключом подписывается и его превью: какой размер нужен,
    решает шаблон, а роут о размерах не знает. Абсолютные ссылки подписи не
    требуют и отдаются как есть.
    """
    unique = {variant for key in keys if key for variant in (key, thumbnail_key(key))}
    external = {key for key in unique if is_external(key)}
    to_sign = sorted(unique - external)

    signed = await sign_many(to_sign, expires_in) if to_sign else []
    return {key: key for key in external} | dict(zip(to_sign, signed, strict=True))
