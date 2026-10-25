"""Ключи файлов хранилища, на которые ссылается база.

Проектный файл: у каждого проекта свои колонки. Новая колонка с ключом
файла — строка в `KEY_COLUMNS` (JSONB с ключами внутри — в `JSON_KEY_COLUMNS`).
Иначе чистка сирот сочтёт её файлы ненужными и удалит.
"""

from collections.abc import Iterator
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

KEY_COLUMNS: tuple[InstrumentedAttribute[Any], ...] = ()
JSON_KEY_COLUMNS: tuple[InstrumentedAttribute[Any], ...] = ()


async def get_referenced_keys(async_session: AsyncSession) -> set[str]:
    """Все ключи из колонок файлов и все строки из JSONB-колонок с ключами.

    Лишняя строка в наборе лишь сохранит файл, нехватка — удалит. Чтение —
    одним снимком (REPEATABLE READ): правка, переносящая ключ из одной
    таблицы в другую между запросами, иначе потеряла бы его.
    """
    await async_session.connection(
        execution_options={'isolation_level': 'REPEATABLE READ'}
    )
    keys: set[str] = set()
    for column in KEY_COLUMNS:
        keys.update(
            await async_session.scalars(select(column).where(column.is_not(None)))
        )
    for column in JSON_KEY_COLUMNS:
        for value in await async_session.scalars(select(column)):
            keys.update(_strings_in(value))
    return keys


async def get_rows_with_key_prefix(
    async_session: AsyncSession, prefix: str
) -> list[tuple[Any, str]]:
    """Строки, где ключ файла начинается с `prefix`: пары (строка, имя колонки)."""
    rows: list[tuple[Any, str]] = []
    for column in KEY_COLUMNS:
        query = select(column.class_).where(column.startswith(prefix))
        rows += [(row, column.key) for row in await async_session.scalars(query)]
    return rows


def _strings_in(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings_in(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings_in(item)
