from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .storage import read_jsonl, write_jsonl
from .vault_ingest import load_chunk_index, speaker_role_weight, tokenize


def _analysis_units_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "analysis_units.jsonl"


def load_analysis_units(root: Path) -> List[Dict]:
    return read_jsonl(_analysis_units_path(root))


def _unit_id(source_id: str, section_key: Tuple[str, ...], start_chunk_id: str, end_chunk_id: str) -> str:
    digest = hashlib.sha256(
        "::".join([source_id, "|".join(section_key), start_chunk_id, end_chunk_id]).encode("utf-8")
    ).hexdigest()[:12]
    return f"unit-{digest}"


def _build_unit(group: List[Dict]) -> Dict:
    first = group[0]
    last = group[-1]
    section_path = first.get("section_path") or []
    title = " · ".join(section_path) if section_path else first["title"]
    content = "\n\n".join(row["content"].strip() for row in group if row["content"].strip())
    unit_id = _unit_id(first["source_id"], tuple(section_path), first["chunk_id"], last["chunk_id"])
    roles = [row.get("metadata", {}).get("speaker_role", "") for row in group if row.get("metadata", {}).get("speaker_role")]
    speaker_role = roles[0] if roles and len(set(roles)) == 1 else (roles[0] if roles else "")
    merged_metadata = dict(first.get("metadata", {}))
    dimension_values: Dict[str, List[str]] = defaultdict(list)
    related_chunk_ids = set()
    for row in group:
        related_chunk_ids.update(row.get("related_chunk_ids", []))
        for key, value in (row.get("metadata_dimensions") or {}).items():
            values = value if isinstance(value, list) else [value]
            for item in values:
                text = str(item).strip()
                if text and text not in dimension_values[key]:
                    dimension_values[key].append(text)
    aggregated_dimensions: Dict[str, Any] = {}
    for key, values in dimension_values.items():
        aggregated_dimensions[key] = values[0] if len(values) == 1 else values
    return {
        "unit_id": unit_id,
        "source_id": first["source_id"],
        "source_ref": first["source_ref"],
        "source_type": first["source_type"],
        "source_family": first["source_family"],
        "sensitivity_tier": first["sensitivity_tier"],
        "title": title[:180],
        "content": content,
        "section_path": section_path,
        "chunk_ids": [row["chunk_id"] for row in group],
        "chunk_indexes": [row["chunk_index"] for row in group],
        "anchor_chunk_id": first["chunk_id"],
        "created_at": first["created_at"],
        "metadata": merged_metadata,
        "metadata_dimensions": aggregated_dimensions,
        "speaker_role": speaker_role,
        "speaker_weight": speaker_role_weight(speaker_role),
        "role_sequence": roles,
        "related_chunk_ids": sorted(related_chunk_ids),
        "tokens": tokenize(content)[:16],
    }


def build_analysis_units(root: Path, *, max_chars: int = 2800, max_chunks: int = 12) -> Dict:
    chunks = sorted(
        load_chunk_index(root),
        key=lambda row: (
            row["source_id"],
            row["chunk_index"],
        ),
    )
    units: List[Dict] = []
    current_group: List[Dict] = []
    current_key: Tuple[str, Tuple[str, ...]] | None = None
    current_chars = 0

    def flush() -> None:
        nonlocal current_group, current_key, current_chars
        if not current_group:
            return
        units.append(_build_unit(current_group))
        current_group = []
        current_key = None
        current_chars = 0

    for chunk in chunks:
        key = (
            chunk["source_id"],
            tuple(chunk.get("section_path") or []),
            chunk.get("metadata", {}).get("speaker_role", ""),
        )
        content = chunk["content"].strip()
        content_length = len(content)
        oversized = content_length >= max_chars
        would_overflow = current_group and (
            key != current_key or len(current_group) >= max_chunks or current_chars + content_length > max_chars
        )
        if would_overflow:
            flush()
        current_key = key
        current_group.append(chunk)
        current_chars += content_length
        if oversized:
            flush()
    flush()

    write_jsonl(_analysis_units_path(root), units)
    return {
        "chunk_count": len(chunks),
        "analysis_unit_count": len(units),
    }
