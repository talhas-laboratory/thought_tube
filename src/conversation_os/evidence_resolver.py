"""Bounded lazy evidence resolution for disclosure frame blocks (R-007)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping

from .disclosure_budget_allocator import estimate_tokens
from .storage import read_json


MODULE_ID = "kernel.disclosure.evidence_resolver"
CONTRACT_VERSION = "1.0"

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "bounded_evidence_resolution_enabled",
    "load_evidence_resolver_config",
    "resolve_frame_blocks",
    "build_evidence_ref",
)
__all__ = list(PUBLIC_API)

REQUIRED_REF_FIELDS = ("source_id", "fragment_id", "content_hash", "corpus_revision")


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def load_evidence_resolver_config(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    resolver = disclosure.get("evidence_resolver", {}) or {}
    return {
        "bounded_evidence_resolution_v1": bool(
            resolver.get(
                "bounded_evidence_resolution_v1",
                disclosure.get("bounded_evidence_resolution_v1", True),
            )
        ),
        "default_byte_budget": max(0, int(resolver.get("default_byte_budget", 65536) or 65536)),
    }


def bounded_evidence_resolution_enabled(root: Path) -> bool:
    return bool(load_evidence_resolver_config(root)["bounded_evidence_resolution_v1"])


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_evidence_ref(
    *,
    source_id: str,
    fragment_id: str,
    content_hash: str,
    corpus_revision: str,
    branch_id: str = "",
    scope_id: str = "",
    source_ref: str = "",
) -> Dict[str, str]:
    return {
        "source_id": str(source_id or "").strip(),
        "fragment_id": str(fragment_id or "").strip(),
        "content_hash": str(content_hash or "").strip(),
        "corpus_revision": str(corpus_revision or "").strip(),
        "branch_id": str(branch_id or "").strip(),
        "scope_id": str(scope_id or "").strip(),
        "source_ref": str(source_ref or "").strip(),
    }


@dataclass
class _ChunkLookup:
    by_fragment_id: Dict[str, Dict[str, Any]]
    sources_by_id: Dict[str, Dict[str, Any]]

    @classmethod
    def for_refs(cls, root: Path, fragment_ids: Iterable[str]) -> "_ChunkLookup":
        from .vault_ingest import _chunk_index_path

        wanted = {str(item).strip() for item in fragment_ids if str(item).strip()}
        chunks: Dict[str, Dict[str, Any]] = {}
        if wanted:
            path = _chunk_index_path(root)
            if path.exists():
                remaining = set(wanted)
                for line in path.read_text(encoding="utf-8").splitlines():
                    if not line.strip() or not remaining:
                        break
                    row = json.loads(line)
                    fragment_id = str(row.get("chunk_id") or row.get("source_item_id") or "").strip()
                    if fragment_id in remaining:
                        chunks[fragment_id] = dict(row)
                        remaining.remove(fragment_id)
        source_ids = {
            str(row.get("source_id", "") or "").strip()
            for row in chunks.values()
            if str(row.get("source_id", "") or "").strip()
        }
        sources: Dict[str, Dict[str, Any]] = {}
        if source_ids:
            from .vault_ingest import _source_registry_path

            registry_path = _source_registry_path(root)
            if registry_path.exists():
                remaining_sources = set(source_ids)
                for line in registry_path.read_text(encoding="utf-8").splitlines():
                    if not line.strip() or not remaining_sources:
                        break
                    row = json.loads(line)
                    source_id = str(row.get("source_id", "") or "").strip()
                    if source_id in remaining_sources:
                        sources[source_id] = dict(row)
                        remaining_sources.remove(source_id)
        return cls(by_fragment_id=chunks, sources_by_id=sources)


def _allowed_refs(effective_grant: Mapping[str, Any]) -> set[str]:
    allowed: set[str] = set()
    for value in list(effective_grant.get("effective_refs", []) or []):
        text = str(value or "").strip()
        if text:
            allowed.add(text)
    for value in list(effective_grant.get("explicit_pins", []) or []):
        text = str(value or "").strip()
        if text:
            allowed.add(text)
    return allowed


def _grant_branch_scope(effective_grant: Mapping[str, Any]) -> tuple[str, str]:
    provenance = dict(effective_grant.get("provenance", {}) or {})
    return (
        str(provenance.get("branch_id", "") or "").strip(),
        str(provenance.get("scope_id", "") or "").strip(),
    )


def _resolve_byte_budget(effective_grant: Mapping[str, Any], root: Path) -> int:
    provenance = dict(effective_grant.get("provenance", {}) or {})
    if "byte_budget" in provenance:
        return max(0, int(provenance.get("byte_budget", 0) or 0))
    token_budget = max(0, int(effective_grant.get("token_budget", 0) or 0))
    if token_budget:
        return token_budget * 4
    return int(load_evidence_resolver_config(root)["default_byte_budget"])


def _legacy_passthrough(block: Mapping[str, Any]) -> Dict[str, Any]:
    row = dict(block)
    row["resolution_status"] = "reference_only"
    row["bytes_resolved"] = 0
    return row


def _validate_evidence_ref(ref: Mapping[str, Any]) -> str | None:
    for field in REQUIRED_REF_FIELDS:
        if not str(ref.get(field, "") or "").strip():
            return f"missing_{field}"
    return None


def _ref_allowed(ref: Mapping[str, Any], *, allowed_refs: set[str]) -> bool:
    if not allowed_refs:
        return True
    candidates = {
        str(ref.get("source_ref", "") or "").strip(),
        str(ref.get("source_id", "") or "").strip(),
        str(ref.get("fragment_id", "") or "").strip(),
    }
    return bool(candidates & allowed_refs)


def _branch_scope_allowed(
    ref: Mapping[str, Any],
    chunk: Mapping[str, Any],
    *,
    grant_branch_id: str,
    grant_scope_id: str,
) -> str | None:
    ref_branch = str(ref.get("branch_id", "") or chunk.get("branch_id", "") or "").strip()
    ref_scope = str(ref.get("scope_id", "") or chunk.get("scope_id", "") or "").strip()
    metadata = dict(chunk.get("metadata", {}) or {})
    if not ref_branch:
        ref_branch = str(metadata.get("branch_id", "") or "").strip()
    if not ref_scope:
        ref_scope = str(metadata.get("scope_id", "") or "").strip()
    if grant_branch_id and ref_branch and ref_branch != grant_branch_id:
        return "branch_mismatch"
    if grant_scope_id and ref_scope and ref_scope != grant_scope_id:
        return "scope_mismatch"
    return None


def resolve_frame_blocks(
    root: Path,
    *,
    included_blocks: list[Dict[str, Any]],
    effective_grant: Mapping[str, Any],
) -> Dict[str, Any]:
    """Resolve admitted compact references into whole provenance-preserving blocks."""
    if not bounded_evidence_resolution_enabled(root):
        return {
            "resolved_blocks": [dict(row) for row in included_blocks],
            "resolution_audit": {
                "enabled": False,
                "included_spans": [],
                "omitted": [],
                "bytes_resolved": 0,
                "lookup_count": 0,
            },
        }

    refs_by_block: Dict[str, Dict[str, Any]] = {}
    fragment_ids: List[str] = []
    for block in included_blocks:
        block_id = str(block.get("block_id", "") or "").strip()
        evidence_ref = dict(block.get("evidence_ref", {}) or {})
        if evidence_ref:
            refs_by_block[block_id] = evidence_ref
            fragment_id = str(evidence_ref.get("fragment_id", "") or "").strip()
            if fragment_id:
                fragment_ids.append(fragment_id)

    lookup = _ChunkLookup.for_refs(root, fragment_ids)
    allowed_refs = _allowed_refs(effective_grant)
    grant_branch_id, grant_scope_id = _grant_branch_scope(effective_grant)
    byte_budget = _resolve_byte_budget(effective_grant, root)
    bytes_resolved = 0
    lookup_count = 0
    resolved_blocks: List[Dict[str, Any]] = []
    included_spans: List[Dict[str, Any]] = []
    omitted: List[Dict[str, Any]] = []

    for block in included_blocks:
        block_id = str(block.get("block_id", "") or "").strip()
        evidence_ref = refs_by_block.get(block_id)
        if not evidence_ref:
            resolved_blocks.append(_legacy_passthrough(block))
            continue

        missing = _validate_evidence_ref(evidence_ref)
        if missing:
            omitted.append(
                {
                    "block_id": block_id,
                    "reason_code": missing,
                    "reason": f"Evidence reference is incomplete ({missing})",
                }
            )
            continue

        if not _ref_allowed(evidence_ref, allowed_refs=allowed_refs):
            omitted.append(
                {
                    "block_id": block_id,
                    "reason_code": "denied_ref",
                    "reason": "Evidence reference is outside the effective grant",
                }
            )
            continue

        fragment_id = str(evidence_ref.get("fragment_id", "") or "").strip()
        lookup_count += 1
        chunk = lookup.by_fragment_id.get(fragment_id)
        if chunk is None:
            omitted.append(
                {
                    "block_id": block_id,
                    "reason_code": "missing_span",
                    "reason": f"Fragment {fragment_id} was not found in the chunk index",
                }
            )
            continue

        source_id = str(evidence_ref.get("source_id", "") or "").strip()
        if str(chunk.get("source_id", "") or "").strip() != source_id:
            omitted.append(
                {
                    "block_id": block_id,
                    "reason_code": "source_id_mismatch",
                    "reason": "Evidence reference source_id does not match indexed fragment",
                }
            )
            continue

        scope_issue = _branch_scope_allowed(
            evidence_ref,
            chunk,
            grant_branch_id=grant_branch_id,
            grant_scope_id=grant_scope_id,
        )
        if scope_issue:
            omitted.append(
                {
                    "block_id": block_id,
                    "reason_code": scope_issue,
                    "reason": "Evidence reference failed branch or scope validation",
                }
            )
            continue

        content = str(chunk.get("content", "") or "")
        actual_hash = _content_hash(content)
        expected_hash = str(evidence_ref.get("content_hash", "") or "").strip()
        if actual_hash != expected_hash:
            omitted.append(
                {
                    "block_id": block_id,
                    "reason_code": "hash_mismatch",
                    "reason": "Indexed fragment content hash does not match evidence reference",
                }
            )
            continue

        expected_revision = str(evidence_ref.get("corpus_revision", "") or "").strip()
        grant_revision = str(dict(effective_grant.get("provenance", {}) or {}).get("corpus_revision", "") or "").strip()
        if grant_revision and expected_revision and grant_revision != expected_revision:
            omitted.append(
                {
                    "block_id": block_id,
                    "reason_code": "stale_revision",
                    "reason": "Evidence reference corpus revision does not match active grant revision",
                }
            )
            continue

        byte_count = len(content.encode("utf-8"))
        if byte_budget and bytes_resolved + byte_count > byte_budget:
            omitted.append(
                {
                    "block_id": block_id,
                    "reason_code": "budget_insufficient",
                    "reason": "Whole evidence block exceeds remaining byte budget",
                }
            )
            continue

        source = lookup.sources_by_id.get(source_id, {})
        source_ref = str(evidence_ref.get("source_ref", "") or chunk.get("source_ref", "") or source.get("source_ref", "") or "")
        resolved = {
            **dict(block),
            "resolution_status": "resolved",
            "bytes_resolved": byte_count,
            "token_estimate": estimate_tokens(content),
            "bounded_text": content,
            "source_span": {
                "source_id": source_id,
                "fragment_id": fragment_id,
                "source_ref": source_ref,
                "content_hash": actual_hash,
                "corpus_revision": expected_revision,
                "branch_id": str(evidence_ref.get("branch_id", "") or chunk.get("branch_id", "") or ""),
                "scope_id": str(evidence_ref.get("scope_id", "") or chunk.get("scope_id", "") or ""),
            },
            "provenance_ref": source_ref,
            "content_hash": actual_hash,
        }
        bytes_resolved += byte_count
        resolved_blocks.append(resolved)
        included_spans.append(
            {
                "block_id": block_id,
                "source_id": source_id,
                "fragment_id": fragment_id,
                "source_ref": source_ref,
                "content_hash": actual_hash,
                "byte_count": byte_count,
            }
        )

    return {
        "resolved_blocks": resolved_blocks,
        "resolution_audit": {
            "enabled": True,
            "included_spans": included_spans,
            "omitted": omitted,
            "bytes_resolved": bytes_resolved,
            "lookup_count": lookup_count,
            "byte_budget": byte_budget,
        },
    }
