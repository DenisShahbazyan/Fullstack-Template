import pytest

from app.domain.uploads.urls import (
    build_file_url_map,
    new_key,
    thumbnail_key,
    tmp_folder,
    tmp_owner,
)

TOKEN = '0f8fad5b-d9cb-469f-a165-70867728950e'
TTL = 900


async def fake_sign_many(keys: list[str], expires_in: int) -> list[str]:
    return [f'https://s3.example.com/{key}?exp={expires_in}' for key in keys]


def test_tmp_owner_is_read_from_own_folder():
    key = new_key(tmp_folder('tmp', 42), 'webp', TOKEN)
    assert key == f'tmp/42/{TOKEN}.webp'
    assert tmp_owner(key, 'tmp') == 42


@pytest.mark.parametrize(
    'key',
    [
        f'portfolio/{TOKEN}.webp',
        f'tmp/{TOKEN}.webp',
        f'tmp/42/{TOKEN}_thumb.webp',
        f'tmp/42/nested/{TOKEN}.webp',
        f'tmp/../42/{TOKEN}.webp',
        f'tmp/4x/{TOKEN}.webp',
        f'tmp/42/{TOKEN}',
        'tmp/42/not-a-uuid.webp',
        f'tmp/42/{TOKEN.replace("-", "")}.webp',
        f'https://evil.example/tmp/42/{TOKEN}.webp',
    ],
)
def test_foreign_key_has_no_owner(key):
    assert tmp_owner(key, 'tmp') is None


def test_thumbnail_sits_next_to_webp():
    assert thumbnail_key('portfolio/a.webp') == 'portfolio/a_thumb.webp'


@pytest.mark.parametrize('key', ['certificates/a.pdf', 'rooms/1/a.mp4'])
def test_non_webp_has_no_thumbnail(key):
    assert thumbnail_key(key) == key


async def test_url_map_signs_files_and_thumbnails_once():
    urls = await build_file_url_map(['a.webp', None, 'a.webp'], fake_sign_many, TTL)
    assert urls == {
        'a.webp': f'https://s3.example.com/a.webp?exp={TTL}',
        'a_thumb.webp': f'https://s3.example.com/a_thumb.webp?exp={TTL}',
    }


async def test_external_url_is_not_signed():
    external = 'https://example.com/photo.jpg'
    assert await build_file_url_map([external], fake_sign_many, TTL) == {
        external: external
    }
