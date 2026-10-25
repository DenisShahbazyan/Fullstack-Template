"""Клиент S3 поверх aioboto3.

Ошибки хранилища наружу уходят доменными: `StoredFileMissingError`, если
объекта нет, `FileStorageUnavailableError` — на всё остальное. Вызывающему
коду botocore знать незачем.
"""

import base64
import hashlib
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from functools import cached_property
from typing import Any

import aioboto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import S3, settings
from app.domain.uploads.errors import (
    FileStorageUnavailableError,
    StoredFileMissingError,
)
from app.domain.uploads.orphans import StoredFile

_CONFIG = Config(
    signature_version='s3v4',
    s3={'addressing_style': 'path'},
    retries={'max_attempts': 3, 'mode': 'standard'},
)
# «Того, что просили, нет» — объекта, загрузки частями или конфига бакета.
# NoSuchBucket сюда не входит: это ошибка настройки, а не пропавший файл.
_MISSING_CODES = frozenset(
    {
        'NoSuchKey',
        '404',
        'NotFound',
        'NoSuchUpload',
        'NoSuchCORSConfiguration',
        'NoSuchLifecycleConfiguration',
    }
)


@dataclass(frozen=True)
class DeleteResult:
    deleted: list[str]
    failed: list[str]


class S3Client:
    def __init__(self, config: S3) -> None:
        self._config = config

    @cached_property
    def _session(self) -> aioboto3.Session:
        # Сессия кэширует описания API: клиент из неё поднимается в разы быстрее,
        # чем из новой сессии на каждый вызов.
        return aioboto3.Session(
            aws_access_key_id=self._config.ACCESS_KEY,
            aws_secret_access_key=self._config.SECRET_KEY,
            region_name=self._config.REGION,
        )

    @property
    def bucket(self) -> str:
        return self._config.BUCKET_NAME

    @asynccontextmanager
    async def raw(self) -> AsyncGenerator[Any]:
        """Клиент aioboto3 для проектных операций, которых здесь нет (multipart).

        Ошибки botocore внутри блока переводятся в доменные, как и у методов.
        """
        with _storage_errors():
            async with self._session.client(
                's3', endpoint_url=self._config.URL, config=_CONFIG
            ) as client:
                yield client

    async def save(self, key: str, data: bytes, content_type: str) -> None:
        async with self.raw() as client:
            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                ChecksumSHA256=_sha256(data),
            )

    async def read(self, key: str) -> bytes:
        async with self.raw() as client:
            response = await client.get_object(Bucket=self.bucket, Key=key)
            async with response['Body'] as stream:
                return await stream.read()

    async def read_head(self, key: str, size: int) -> bytes:
        """Первые `size` байт объекта — чтобы узнать формат, не скачивая файл."""
        async with self.raw() as client:
            response = await client.get_object(
                Bucket=self.bucket, Key=key, Range=f'bytes=0-{size - 1}'
            )
            async with response['Body'] as stream:
                return await stream.read()

    async def copy(self, source: str, target: str) -> None:
        async with self.raw() as client:
            await client.copy_object(
                Bucket=self.bucket,
                CopySource={'Bucket': self.bucket, 'Key': source},
                Key=target,
            )

    async def delete_many(self, keys: list[str]) -> DeleteResult:
        """Удаляет до 1000 объектов за запрос."""
        async with self.raw() as client:
            response = await client.delete_objects(
                Bucket=self.bucket,
                Delete={'Objects': [{'Key': key} for key in keys], 'Quiet': False},
            )
        return DeleteResult(
            deleted=[item['Key'] for item in response.get('Deleted', [])],
            failed=[item['Key'] for item in response.get('Errors', [])],
        )

    async def list_files(self, prefix: str) -> list[StoredFile]:
        """Объекты под префиксом вместе со временем последней записи."""
        files: list[StoredFile] = []
        async with self.raw() as client:
            paginator = client.get_paginator('list_objects_v2')
            async for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                files += [
                    StoredFile(item['Key'], item['LastModified'])
                    for item in page.get('Contents', [])
                ]
        return files

    async def sign_many(self, keys: list[str], expires_in: int) -> list[str]:
        """Подписанные ссылки на чтение — все на одном клиенте.

        Сама подпись локальная и стоит доли миллисекунды, а поднять клиент —
        заметно дольше. Галерея подписывает десятки ключей за запрос.
        """
        if not keys:
            return []
        async with self.raw() as client:
            return [
                await client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': self.bucket, 'Key': key},
                    ExpiresIn=expires_in,
                )
                for key in keys
            ]


@contextmanager
def _storage_errors() -> Generator[None]:
    try:
        yield
    except ClientError as error:
        code = error.response.get('Error', {}).get('Code', '')
        if code in _MISSING_CODES:
            raise StoredFileMissingError() from error
        raise FileStorageUnavailableError() from error
    except BotoCoreError as error:
        raise FileStorageUnavailableError() from error


def _sha256(data: bytes) -> str:
    return base64.b64encode(hashlib.sha256(data).digest()).decode()


s3_client = S3Client(settings.s3)
