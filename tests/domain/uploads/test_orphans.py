from datetime import UTC, datetime, timedelta

import pytest

from app.domain.uploads.errors import ImplausibleOrphanSweepError
from app.domain.uploads.orphans import (
    MIN_GUARDED_TOTAL,
    StoredFile,
    ensure_sweep_plausible,
    find_orphans,
    sweep_prefixes,
)

NOW = datetime(2026, 10, 25, 12, tzinfo=UTC)
CUTOFF = NOW - timedelta(hours=24)
OLD = NOW - timedelta(days=3)


def stored(key: str, modified_at: datetime = OLD) -> StoredFile:
    return StoredFile(key, modified_at)


def test_unreferenced_old_file_is_orphan():
    files = [stored('portfolio/a.webp')]
    assert find_orphans(files, set(), CUTOFF) == ['portfolio/a.webp']


def test_referenced_file_is_kept():
    files = [stored('portfolio/a.webp')]
    assert find_orphans(files, {'portfolio/a.webp'}, CUTOFF) == []


def test_thumbnail_of_referenced_file_is_kept():
    files = [stored('portfolio/a.webp'), stored('portfolio/a_thumb.webp')]
    assert find_orphans(files, {'portfolio/a.webp'}, CUTOFF) == []


def test_thumbnail_goes_with_its_orphaned_original():
    files = [stored('portfolio/a.webp'), stored('portfolio/a_thumb.webp')]
    assert find_orphans(files, set(), CUTOFF) == [
        'portfolio/a.webp',
        'portfolio/a_thumb.webp',
    ]


def test_fresh_unreferenced_file_is_kept():
    files = [stored('tmp/a.webp', NOW - timedelta(hours=1))]
    assert find_orphans(files, set(), CUTOFF) == []


def test_referenced_pdf_is_kept():
    files = [stored('certificates/a.pdf')]
    assert find_orphans(files, {'certificates/a.pdf'}, CUTOFF) == []


def test_sweep_of_most_files_is_refused():
    with pytest.raises(ImplausibleOrphanSweepError):
        ensure_sweep_plausible(MIN_GUARDED_TOTAL, MIN_GUARDED_TOTAL // 2 + 1)


def test_sweep_of_half_the_files_is_allowed():
    ensure_sweep_plausible(MIN_GUARDED_TOTAL, MIN_GUARDED_TOTAL // 2)


def test_small_bucket_is_not_guarded():
    ensure_sweep_plausible(MIN_GUARDED_TOTAL - 1, MIN_GUARDED_TOTAL - 1)


def test_nested_folder_is_swept_with_its_parent():
    folders = {'avatars', 'avatars/source', 'tmp'}
    assert sweep_prefixes(folders) == ['avatars/', 'tmp/']


def test_folder_sharing_a_name_prefix_is_swept_separately():
    assert sweep_prefixes({'avatars', 'avatars-old'}) == ['avatars-old/', 'avatars/']
