"""Bridge vault ingest identity to Shape normalization source requests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from conversation_os.source_content_store import SourceContentStore
from conversation_os.shape_population.contracts import ValidationError
from conversation_os.vault_ingest import load_source_registry_raw

MODULE_ID = "kernel.shape_population.vault_bridge"
CONTRACT_VERSION = "1.1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "load_vault_source_bytes",
    "source_request_from_vault",
    "merge_job_payload_with_vault",
)
__all__ = list(PUBLIC_API)


def _vault_entry(root: Path, vault_source_id: str) -> dict[str, Any]:
    source_id = str(vault_source_id or "").strip()
    if not source_id:
        raise ValidationError("vault_source_id required")
    registry = load_source_registry_raw(root)
    entry = next((row for row in registry if str(row.get("source_id") or "") == source_id), None)
    if entry is None:
        raise ValidationError(f"unknown vault source: {source_id}")
    return dict(entry)


def load_vault_source_bytes(
    root: Path | str,
    vault_source_id: str,
    *,
    content_store: SourceContentStore | None = None,
) -> tuple[bytes, dict[str, Any]]:
    """Load the exact original vault source bytes from the content-addressed store.

    Requires ingest to have persisted original bytes under ``content_hash``.
    Does not reconstruct from chunks (chunk joins are lossy).
    """

    root_path = Path(root)
    entry = _vault_entry(root_path, vault_source_id)
    digest = str(entry.get("content_hash") or "").strip()
    pointer = str(entry.get("content_pointer") or "").strip()
    if not digest and pointer.startswith("sha256:"):
        digest = pointer.split(":", 1)[1]
    if not digest:
        raise ValidationError(f"vault source missing content_hash: {vault_source_id}")
    store = content_store or SourceContentStore(root_path)
    try:
        raw = store.get_bytes(digest)
    except FileNotFoundError as exc:
        raise ValidationError(
            f"original vault source bytes unavailable for {vault_source_id}; "
            "ingest must persist content-addressed bytes before Shape enqueue"
        ) from exc
    actual = __import__("hashlib").sha256(raw).hexdigest()
    if actual != digest.lower():
        raise ValidationError(f"vault source digest mismatch for {vault_source_id}")
    return raw, entry


def source_request_from_vault(
    root: Path | str,
    vault_source_id: str,
    *,
    modality: str = "plain_text",
    content_store: SourceContentStore | None = None,
) -> dict[str, Any]:
    """Build a normalize_source request from exact original vault bytes."""

    raw, entry = load_vault_source_bytes(root, vault_source_id, content_store=content_store)
    digest = str(entry.get("content_hash") or "")
    source_ref = str(entry.get("source_ref") or "")
    suffix = Path(source_ref).suffix.lower() if source_ref else ""
    resolved_modality = modality
    if suffix in {".md", ".markdown"}:
        resolved_modality = "markdown"
    metadata = dict(entry.get("metadata") or {})
    metadata.update(
        {
            "vault_source_id": str(entry.get("source_id") or vault_source_id),
            "vault_content_hash": digest,
            "vault_source_ref": source_ref,
            "vault_title": str(entry.get("title") or ""),
            "lossless_original": True,
        }
    )
    # Prefer digest+content_store load inside normalize_source; also pass bytes for callers
    # that do not yet wire a content store.
    return {
        "content": raw,
        "content_sha256": digest,
        "modality": resolved_modality,
        "locator": source_ref or f"vault:{vault_source_id}",
        "raw_ref": f"sha256:{digest}",
        "metadata": metadata,
    }


def merge_job_payload_with_vault(
    payload: Mapping[str, Any] | None,
    *,
    vault_source_id: str,
    vault_root: Path | str | None,
) -> dict[str, Any]:
    body = dict(payload or {})
    body.setdefault("vault_source_id", vault_source_id)
    if vault_root is not None:
        body.setdefault("vault_root", str(Path(vault_root)))
    body.setdefault("enqueued_by", body.get("enqueued_by") or "post_ingest_hook")
    return body
