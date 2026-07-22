"""Content-addressed immutable source byte ownership."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

from conversation_os.storage import utc_now

MODULE_ID = "kernel.ingest.source_content_store"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "source_content_dir",
    "SourceContentStore",
)
__all__ = list(PUBLIC_API)


def source_content_dir(root: Path) -> Path:
    return Path(root) / "product" / "inner_world_v1" / "data" / "source_content"


def _normalize_digest(digest: str) -> str:
    value = str(digest or "").strip()
    if value.startswith("sha256:"):
        value = value.split(":", 1)[1]
    if len(value) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise ValueError("digest must be a sha256 hex digest")
    return value.lower()


def _fsync_directory(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        _fsync_directory(path.parent)
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


class SourceContentStore:
    """File-backed immutable byte store keyed by SHA-256 of original bytes."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.base = source_content_dir(self.root)
        self.base.mkdir(parents=True, exist_ok=True)

    def _blob_path(self, digest: str) -> Path:
        value = _normalize_digest(digest)
        return self.base / value[:2] / value

    def _metadata_path(self, digest: str) -> Path:
        return self._blob_path(digest).with_suffix(".json")

    def _verify_existing(self, digest: str) -> None:
        raw = self._blob_path(digest).read_bytes()
        actual = hashlib.sha256(raw).hexdigest()
        if actual != _normalize_digest(digest):
            raise ValueError(f"stored source content digest mismatch for {digest}")

    def put_bytes(self, raw: bytes | bytearray | memoryview) -> str:
        payload = bytes(raw)
        digest = hashlib.sha256(payload).hexdigest()
        blob_path = self._blob_path(digest)
        metadata_path = self._metadata_path(digest)
        if blob_path.exists():
            self._verify_existing(digest)
            if not metadata_path.exists():
                self._write_metadata(digest, len(payload), created_at=utc_now())
            return digest

        _atomic_write(blob_path, payload)
        self._verify_existing(digest)
        self._write_metadata(digest, len(payload), created_at=utc_now())
        return digest

    def _write_metadata(self, digest: str, length: int, *, created_at: str) -> None:
        payload = {
            "digest": _normalize_digest(digest),
            "algorithm": "sha256",
            "length": int(length),
            "created_at": created_at,
        }
        _atomic_write(self._metadata_path(digest), json.dumps(payload, sort_keys=True).encode("utf-8") + b"\n")

    def get_bytes(self, digest: str) -> bytes:
        value = _normalize_digest(digest)
        blob_path = self._blob_path(value)
        if not blob_path.exists():
            raise FileNotFoundError(f"source content not found: sha256:{value}")
        raw = blob_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != value:
            raise ValueError(f"stored source content digest mismatch for {value}")
        return raw

    def exists(self, digest: str) -> bool:
        try:
            value = _normalize_digest(digest)
        except ValueError:
            return False
        return self._blob_path(value).exists()

    def metadata(self, digest: str) -> Dict[str, Any]:
        value = _normalize_digest(digest)
        blob_path = self._blob_path(value)
        if not blob_path.exists():
            raise FileNotFoundError(f"source content not found: sha256:{value}")
        self._verify_existing(value)
        metadata_path = self._metadata_path(value)
        if metadata_path.exists():
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        else:
            stat = blob_path.stat()
            payload = {
                "digest": value,
                "algorithm": "sha256",
                "length": stat.st_size,
                "created_at": utc_now(),
            }
            self._write_metadata(value, stat.st_size, created_at=payload["created_at"])
        if int(payload.get("length", -1)) != blob_path.stat().st_size:
            raise ValueError(f"stored source content metadata length mismatch for {value}")
        return dict(payload)
