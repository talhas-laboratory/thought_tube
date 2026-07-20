"""Bridge vault ingest identity to Shape normalization source requests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from conversation_os.shape_population.contracts import ValidationError
from conversation_os.vault_ingest import load_chunk_index_raw, load_source_registry_raw

MODULE_ID = "kernel.shape_population.vault_bridge"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "reconstruct_vault_source_text",
    "source_request_from_vault",
)
__all__ = list(PUBLIC_API)


def reconstruct_vault_source_text(root: Path | str, vault_source_id: str) -> tuple[str, dict[str, Any]]:
    """Rebuild source text from durable vault chunks for Shape normalization.

    Vault chunking may drop exact byte identity (for example trailing newlines).
    Shape normalization then assigns its own content digest to the reconstructed text.
    """

    root_path = Path(root)
    source_id = str(vault_source_id or "").strip()
    if not source_id:
        raise ValidationError("vault_source_id required")
    registry = load_source_registry_raw(root_path)
    entry = next((row for row in registry if str(row.get("source_id") or "") == source_id), None)
    if entry is None:
        raise ValidationError(f"unknown vault source: {source_id}")
    chunks = [
        row
        for row in load_chunk_index_raw(root_path)
        if str(row.get("source_id") or "") == source_id
    ]
    if not chunks:
        raise ValidationError(f"vault source has no chunks: {source_id}")
    chunks.sort(key=lambda row: int(row.get("chunk_index") or 0))
    parts = [str(row.get("content") or "") for row in chunks]
    kinds = {str(row.get("content_kind") or "") for row in chunks}
    if "paragraph" in kinds or len(parts) > 1:
        text = "\n\n".join(part for part in parts if part)
    else:
        text = "\n".join(parts)
    if not text.strip():
        raise ValidationError(f"vault source content empty: {source_id}")
    if not text.endswith("\n"):
        text = text + "\n"
    return text, dict(entry)


def source_request_from_vault(
    root: Path | str,
    vault_source_id: str,
    *,
    modality: str = "plain_text",
) -> dict[str, Any]:
    """Build a normalize_source request from a committed vault source."""

    text, entry = reconstruct_vault_source_text(root, vault_source_id)
    source_ref = str(entry.get("source_ref") or "")
    suffix = Path(source_ref).suffix.lower() if source_ref else ""
    resolved_modality = modality
    if suffix in {".md", ".markdown"}:
        resolved_modality = "markdown"
    metadata = dict(entry.get("metadata") or {})
    metadata.update(
        {
            "vault_source_id": str(entry.get("source_id") or vault_source_id),
            "vault_content_hash": str(entry.get("content_hash") or ""),
            "vault_source_ref": source_ref,
            "vault_title": str(entry.get("title") or ""),
        }
    )
    return {
        "content": text,
        "modality": resolved_modality,
        "locator": source_ref or f"vault:{vault_source_id}",
        "raw_ref": source_ref or f"vault:{vault_source_id}",
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
