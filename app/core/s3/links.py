"""Подписанные ссылки на файлы приватного бакета.

Для шаблонов ссылки собираются в роуте до рендера: подпись идёт через
асинхронный клиент, а фильтры Jinja синхронные.
"""

from app.core.config import settings
from app.core.s3.client import s3_client
from app.domain.uploads.urls import build_file_url_map


async def signed_url(key: str | None) -> str | None:
    """Подписанная ссылка на один файл."""
    if not key:
        return None
    return (await signed_urls_by_key([key]))[key]


async def signed_urls_by_key(keys: list[str | None]) -> dict[str, str]:
    """Карта «ключ → подписанная ссылка» для галерей, вместе с превью.

    Пустые ключи пропускаются, повторы подписываются один раз. В шаблоне:
    `file_urls[key | thumbnail]` — превью, `file_urls[key]` — оригинал.
    """
    return await build_file_url_map(
        keys, s3_client.sign_many, settings.s3.PRESIGNED_TTL_SECONDS
    )
