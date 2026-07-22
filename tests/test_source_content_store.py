from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from conversation_os.source_content_store import SourceContentStore


def test_put_get_metadata_and_dedupe(tmp_path: Path) -> None:
    store = SourceContentStore(tmp_path)
    raw = "Cafe\u0301 and emoji 😀\n".encode("utf-8")
    digest = store.put_bytes(raw)
    assert digest == hashlib.sha256(raw).hexdigest()
    assert store.put_bytes(raw) == digest
    assert store.exists(digest)
    assert store.exists(f"sha256:{digest}")
    assert store.get_bytes(digest) == raw
    metadata = store.metadata(digest)
    assert metadata["digest"] == digest
    assert metadata["length"] == len(raw)
    assert metadata["created_at"]


def test_missing_digest_fails_closed(tmp_path: Path) -> None:
    store = SourceContentStore(tmp_path)
    missing = "0" * 64
    assert not store.exists(missing)
    with pytest.raises(FileNotFoundError):
        store.get_bytes(missing)
