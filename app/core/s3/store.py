"""Сохранение загруженного файла: проверка, обработка и укладка в S3."""

import uuid
from collections.abc import Collection
from dataclasses import dataclass

from fastapi import UploadFile

from app.core.config import settings
from app.core.images import process_with_thumbnail
from app.core.s3.client import s3_client
from app.domain.uploads.errors import FileTooLargeError
from app.domain.uploads.images import ProcessedImage
from app.domain.uploads.project import UPLOAD_TYPES
from app.domain.uploads.types import (
    EXTENSIONS,
    HEAD_SIZE,
    IMAGE_TYPES,
    ensure_type_allowed,
)
from app.domain.uploads.urls import new_key, thumbnail_key


@dataclass(frozen=True)
class StoredUpload:
    """Файл, который лёг в S3: ключ, тип и размер сохранённого (не исходника)."""

    key: str
    content_type: str
    size: int


async def read_upload(file: UploadFile) -> bytes:
    """Содержимое файла из формы, не больше MAX_UPLOAD_BYTES.

    Raises:
        FileTooLargeError: файл больше MAX_UPLOAD_BYTES.
    """
    limit = settings.s3.MAX_UPLOAD_BYTES
    data = await file.read(limit + 1)
    if len(data) > limit:
        raise FileTooLargeError()
    return data


async def store_upload(
    raw: bytes, folder: str, allowed: Collection[str] = UPLOAD_TYPES
) -> StoredUpload:
    """Кладёт файл в `folder`.

    Изображение уходит в WebP с превью рядом (`thumbnail_key`), документ из
    DOCUMENT_TYPES — как есть. Формат определяется по содержимому.

    Raises:
        UnsupportedFileTypeError: формат не из `allowed`.
        ImageProcessingError: изображение не читается.
        ImageTooLargeError: в изображении слишком много точек.
        FileStorageUnavailableError: хранилище не приняло файл.
    """
    content_type = ensure_type_allowed(raw[:HEAD_SIZE], allowed)
    if content_type in IMAGE_TYPES:
        return await store_image(raw, folder)
    key = new_key(folder, EXTENSIONS[content_type], str(uuid.uuid4()))
    await s3_client.save(key, raw, content_type)
    return StoredUpload(key, content_type, len(raw))


async def store_image(raw: bytes, folder: str) -> StoredUpload:
    """Кладёт изображение в WebP и его превью рядом.

    Raises:
        ImageProcessingError: изображение не читается.
        ImageTooLargeError: в изображении слишком много точек.
        FileStorageUnavailableError: хранилище не приняло файл.
    """
    processed, thumbnail = await process_with_thumbnail(raw)
    key = new_key(folder, processed.extension, str(uuid.uuid4()))
    await save_processed(processed, key)
    await save_processed(thumbnail, thumbnail_key(key))
    return StoredUpload(key, processed.content_type, len(processed.data))


async def save_processed(image: ProcessedImage, key: str) -> None:
    await s3_client.save(key, image.data, image.content_type)
