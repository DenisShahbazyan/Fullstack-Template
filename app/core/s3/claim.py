"""Временные загрузки: файл сначала ложится в tmp/, запись потом его принимает.

Так устроены загрузки через API (`POST /api/public/v1/files/upload`): клиент
получает ключ и присылает его, сохраняя запись. Принимаем только свои загрузки
— владелец записан в пути ключа. Иначе чужим ключом можно было бы показать
чужой файл или удалить его вместе со своей записью. Принятый файл копируется в
постоянную папку под новым именем: временная не попадает в копию бакета, её
чистит чистка сирот, а повторный приём того же ключа не свяжет две записи с
одним файлом.
"""

import uuid
from collections.abc import Collection, Sequence

from app.core.config import settings
from app.core.s3.client import s3_client
from app.core.s3.store import store_upload
from app.domain.uploads.errors import (
    DuplicateUploadError,
    ForeignUploadError,
    UnsupportedFileTypeError,
)
from app.domain.uploads.images import WEBP_EXTENSION
from app.domain.uploads.urls import (
    extension_of,
    new_key,
    thumbnail_key,
    tmp_folder,
    tmp_owner,
)

# Поле только для фото: любое изображение сервер уже сохранил в WebP, а документ
# из той же временной папки (PDF) сюда не годится.
IMAGE_EXTENSIONS = frozenset({WEBP_EXTENSION})


async def store_tmp_upload(raw: bytes, user_id: int) -> str:
    """Кладёт файл во временную папку пользователя, отдаёт ключ.

    Raises:
        UnsupportedFileTypeError, ImageProcessingError, ImageTooLargeError,
        FileStorageUnavailableError: как у `store_upload`.
    """
    stored = await store_upload(raw, tmp_folder(settings.s3.TMP_PATH, user_id))
    return stored.key


async def claim_uploads(
    user_id: int,
    keys: Sequence[str],
    folder: str,
    kept: Collection[str] = (),
    extensions: Collection[str] | None = None,
) -> list[str]:
    """Переносит временные загрузки пользователя в `folder`, отдаёт итоговые ключи.

    Ключи из `kept` — уже привязанные к той же записи — остаются как есть.
    `extensions` — какие файлы годятся полю (для фото — `IMAGE_EXTENSIONS`);
    None — любые из временной папки. Порядок ключей сохраняется.

    Raises:
        ForeignUploadError: ключ не временной загрузки этого пользователя.
        DuplicateUploadError: один ключ передан дважды.
        UnsupportedFileTypeError: файл не того вида, что ждёт поле.
        StoredFileMissingError: загрузку уже удалила чистка сирот.
        FileStorageUnavailableError: хранилище не скопировало файл.
    """
    # Два ключа на один файл дали бы две записи с одним файлом: удаление
    # одной стёрло бы картинку у другой.
    if len(set(keys)) != len(keys):
        raise DuplicateUploadError()
    fresh = [key for key in keys if key not in kept]
    if any(tmp_owner(key, settings.s3.TMP_PATH) != user_id for key in fresh):
        raise ForeignUploadError()
    if extensions is not None and any(
        extension_of(key) not in extensions for key in fresh
    ):
        raise UnsupportedFileTypeError()
    moved = {key: _new_key_in(folder, key) for key in fresh}
    await s3_client.copy_many(_with_thumbnails(moved))
    return [moved.get(key, key) for key in keys]


async def copy_to_folder(key: str, folder: str) -> str:
    """Копирует файл с превью в `folder` под новым именем, отдаёт новый ключ.

    Raises:
        StoredFileMissingError: исходного файла нет.
        FileStorageUnavailableError: хранилище не скопировало файл.
    """
    target = _new_key_in(folder, key)
    await s3_client.copy_many(_with_thumbnails({key: target}))
    return target


def _new_key_in(folder: str, key: str) -> str:
    return new_key(folder, extension_of(key), str(uuid.uuid4()))


def _with_thumbnails(moved: dict[str, str]) -> list[tuple[str, str]]:
    """Пары (откуда, куда) вместе с превью — у документа его нет."""
    pairs: list[tuple[str, str]] = []
    for source, target in moved.items():
        pairs.append((source, target))
        if thumbnail_key(source) != source:
            pairs.append((thumbnail_key(source), thumbnail_key(target)))
    return pairs
