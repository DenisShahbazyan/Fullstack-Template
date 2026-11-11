"""Приём временных загрузок: отказы случаются до копирования в хранилище."""

from unittest.mock import AsyncMock

import pytest

from app.core.config import settings
from app.core.s3 import claim
from app.core.s3.claim import IMAGE_EXTENSIONS, claim_uploads
from app.domain.uploads.errors import (
    DuplicateUploadError,
    ForeignUploadError,
    UnsupportedFileTypeError,
)

TOKEN = '0f8fad5b-d9cb-469f-a165-70867728950e'


def tmp_key(user_id: int, extension: str = 'webp') -> str:
    return f'{settings.s3.TMP_PATH}/{user_id}/{TOKEN}.{extension}'


@pytest.fixture(autouse=True)
def storage(monkeypatch):
    copy = AsyncMock()
    monkeypatch.setattr(claim.s3_client, 'copy_many', copy)
    return copy


async def test_someone_elses_upload_is_refused(storage):
    with pytest.raises(ForeignUploadError):
        await claim_uploads(1, [tmp_key(2)], 'portfolio')
    storage.assert_not_awaited()


async def test_same_upload_twice_is_refused(storage):
    with pytest.raises(DuplicateUploadError):
        await claim_uploads(1, [tmp_key(1), tmp_key(1)], 'portfolio')
    storage.assert_not_awaited()


async def test_document_in_photo_field_is_refused(storage):
    with pytest.raises(UnsupportedFileTypeError):
        await claim_uploads(
            1, [tmp_key(1, 'pdf')], 'portfolio', extensions=IMAGE_EXTENSIONS
        )
    storage.assert_not_awaited()


async def test_own_photo_moves_to_folder(storage):
    kept = 'portfolio/kept.webp'
    claimed = await claim_uploads(
        1, [kept, tmp_key(1)], 'portfolio', kept={kept}, extensions=IMAGE_EXTENSIONS
    )
    assert claimed[0] == kept
    assert claimed[1].startswith('portfolio/') and claimed[1].endswith('.webp')
    storage.assert_awaited_once()
