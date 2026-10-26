"""Пометка колонок с ключами файлов S3.

Колонка с файлом объявляется один раз: `mapped_column(info=file_folder(FOLDER))`.
По пометке чистка сирот узнаёт и колонки, на которые смотреть, и папки, которые
обходить, — папка без своей колонки в чистку не попадает. Тип колонки не
меняется: для базы это та же строка или JSONB, миграция не нужна.
"""

from typing import Any

from sqlalchemy.orm import InstrumentedAttribute, registry

_FOLDER = 'file_folder'
_KEYS_IN_JSON = 'file_keys_in_json'


def file_folder(folder: str) -> dict[str, Any]:
    """`info` колонки с ключом файла из папки `folder`."""
    return {_FOLDER: folder}


def file_keys_in_json() -> dict[str, Any]:
    """`info` JSONB-колонки, где среди значений бывают ключи файлов.

    Папок она не добавляет: ключи в ней — из папок помеченных колонок.
    """
    return {_KEYS_IN_JSON: True}


def folder_of(attribute: InstrumentedAttribute[Any]) -> str:
    """Папка помеченной колонки."""
    return attribute.info[_FOLDER]


def key_columns(mappers: registry) -> list[InstrumentedAttribute[Any]]:
    """Колонки, помеченные `file_folder`."""
    return _marked(mappers, _FOLDER)


def json_key_columns(mappers: registry) -> list[InstrumentedAttribute[Any]]:
    """Колонки, помеченные `file_keys_in_json`."""
    return _marked(mappers, _KEYS_IN_JSON)


def key_folders(mappers: registry) -> set[str]:
    """Папки всех колонок, помеченных `file_folder`."""
    return {folder_of(column) for column in key_columns(mappers)}


def _marked(mappers: registry, mark: str) -> list[InstrumentedAttribute[Any]]:
    attributes = [
        getattr(mapper.class_, prop.key)
        for mapper in mappers.mappers
        for prop in mapper.column_attrs
        if mark in prop.columns[0].info
    ]
    return sorted(attributes, key=lambda column: (column.class_.__name__, column.key))
