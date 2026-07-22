from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Sequence, Tuple

from .models import ChunkRecord, SourceRegistryEntry
from .runtime_layout import product_runtime_dir
from .source_content_store import SourceContentStore
from .storage import ensure_dir, read_jsonl, utc_now, write_jsonl

PostIngestHook = Callable[..., Any]


MODULE_ID = "kernel.ingest.vault_ingest"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "tokenize",
    "shorten",
    "_runtime_chunk_view",
    "infer_speaker_role",
    "speaker_role_weight",
    "chunk_source_text",
    "load_source_registry_raw",
    "load_chunk_index_raw",
    "load_source_registry",
    "load_chunk_index",
    "write_vault_files",
    "infer_source_family",
    "infer_sensitivity_tier",
    "ingest_text_content",
    "ingest_text_items_batch",
    "ingest_source_file",
    "remove_source_by_ref",
    "bootstrap_legacy_source_items",
)
__all__ = list(PUBLIC_API)


STOPWORDS = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "from",
    "into",
    "your",
    "this",
    "have",
    "will",
    "not",
    "are",
    "but",
    "was",
    "how",
    "what",
    "when",
    "why",
    "who",
    "can",
    "should",
    "would",
    "could",
    "about",
    "then",
    "them",
    "they",
    "their",
    "there",
    "than",
    "just",
    "like",
    "through",
    "using",
    "work",
    "works",
    "user",
    "users",
    "system",
}

COMMAND_PREFIXES = (
    "python ",
    "openclaw ",
    "ssh ",
    "systemctl ",
    "journalctl ",
    "docker ",
    "lsof ",
    "pgrep ",
    "tail ",
    "cat ",
    "cp ",
    "mv ",
)

ROLE_MARKERS = {
    "user": "user",
    "assistant": "assistant",
    "agent": "assistant",
    "system": "system",
    "model": "assistant",
}

CONVERSATION_SOURCE_MARKERS = (
    "brain-vomit",
    "cast",
    "chat",
    "conversation",
    "transcript",
)

CONVERSATION_LINE_PREFIX = re.compile(
    r"^\s*(?:user|assistant|system|agent|model|you said|assistant said|user said)\s*:\s*",
    re.IGNORECASE,
)

LOW_SIGNAL_CONVERSATION_LINES = {
    "assistant",
    "current url",
    "label",
    "refresh",
    "source",
    "text",
    "uploaded image",
    "user",
    "you said",
}

LOW_SIGNAL_CONVERSATION_PREFIXES = (
    "# in app browser",
    "assistant said",
    "## my request for codex",
    "current url",
    "files mentioned by the user",
    "my request for codex",
    "user said",
    "you said",
)

STRICT_PROCEDURAL_PREFIXES = (
    "check",
    "click",
    "open",
    "please",
    "refresh",
    "run",
    "scroll",
    "show",
    "tap",
)


def tokenize(text: str) -> List[str]:
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9-]{2,}", text.lower())
    return [token for token in tokens if token not in STOPWORDS]


def shorten(text: str, limit: int) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)].rstrip() + "…"


def _slug(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", value.lower())
    return re.sub(r"-+", "-", value).strip("-") or "item"


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _data_dir(root: Path) -> Path:
    return product_runtime_dir(root, "inner_world_v1", "data")


def _source_registry_path(root: Path) -> Path:
    return _data_dir(root) / "source_registry.jsonl"


def _chunk_index_path(root: Path) -> Path:
    return _data_dir(root) / "chunk_index.jsonl"


def _legacy_source_items_path(root: Path) -> Path:
    return _data_dir(root) / "source_items.jsonl"


def _looks_like_command(text: str) -> bool:
    stripped = text.strip().strip("`").lower()
    if not stripped:
        return False
    if stripped.startswith("- "):
        stripped = stripped[2:].strip().strip("`")
    return any(stripped.startswith(prefix) for prefix in COMMAND_PREFIXES)


def _normalized_surface(text: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _is_conversation_like_row(row: Dict) -> bool:
    hay = " ".join(
        [
            str(row.get("source_type", "")),
            str(row.get("source_family", "")),
            str(row.get("source_ref", "")),
            str(row.get("metadata", {}).get("path_name", "")),
        ]
    ).lower()
    return any(marker in hay for marker in CONVERSATION_SOURCE_MARKERS)


def _clean_conversation_line(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    normalized = _normalized_surface(stripped)
    if normalized in LOW_SIGNAL_CONVERSATION_LINES:
        return ""
    if any(normalized.startswith(prefix) for prefix in LOW_SIGNAL_CONVERSATION_PREFIXES):
        return ""
    if "<heartbeat" in stripped.lower() or "</heartbeat" in stripped.lower():
        return ""
    stripped = CONVERSATION_LINE_PREFIX.sub("", stripped).strip()
    normalized = _normalized_surface(stripped)
    if not stripped or normalized in LOW_SIGNAL_CONVERSATION_LINES:
        return ""
    return stripped


def _clean_conversation_text(text: str) -> str:
    blocks: List[str] = []
    for raw_block in re.split(r"\n\s*\n", text):
        lines = [_clean_conversation_line(line) for line in raw_block.splitlines()]
        cleaned_lines = [line for line in lines if line]
        if cleaned_lines:
            block = "\n".join(cleaned_lines).strip()
            if not blocks or blocks[-1] != block:
                blocks.append(block)
    return "\n\n".join(blocks).strip()


def _runtime_chunk_view(row: Dict) -> Dict:
    resolved = dict(row)
    if not _is_conversation_like_row(row):
        return resolved
    profile = str(row.get("normalization_profile", "default") or "default").strip().lower()
    raw_title = str(row.get("title", ""))
    raw_content = str(row.get("content", ""))
    cleaned_title = raw_title
    cleaned_content = raw_content
    if profile not in {"off", "raw", "verbatim"}:
        cleaned_content = _clean_conversation_text(raw_content)
        cleaned_title = _clean_conversation_text(raw_title).replace("\n", " ").strip() or raw_title
        if profile in {"aggressive", "conversation_strict", "strict"}:
            strict_blocks: List[str] = []
            for block in re.split(r"\n\s*\n", cleaned_content):
                lines = []
                for line in block.splitlines():
                    normalized = _normalized_surface(line)
                    if not normalized:
                        continue
                    token_count = len(tokenize(line))
                    if token_count <= 6 and any(normalized.startswith(prefix) for prefix in STRICT_PROCEDURAL_PREFIXES):
                        continue
                    lines.append(line.strip())
                if lines:
                    strict_blocks.append("\n".join(lines).strip())
            cleaned_content = "\n\n".join(strict_blocks).strip()
    resolved["raw_title"] = raw_title
    resolved["raw_content"] = raw_content
    resolved["semantic_title"] = cleaned_title or raw_title
    resolved["semantic_content"] = cleaned_content
    resolved["normalization_profile_applied"] = profile
    resolved["normalized_runtime"] = cleaned_content != raw_content or (cleaned_title and cleaned_title != raw_title)
    resolved["title"] = cleaned_title or shorten(cleaned_content or raw_title, 80)
    resolved["content"] = cleaned_content
    return resolved


def infer_speaker_role(
    section_path: List[str] | None = None,
    title: str = "",
    content: str = "",
) -> str:
    candidates = list(section_path or [])
    if title:
        candidates.append(title)
    content_prefix = content.strip().splitlines()[0] if content.strip() else ""
    if content_prefix:
        candidates.append(content_prefix[:24])
    for candidate in reversed(candidates):
        normalized = re.sub(r"[^a-z]+", "", candidate.lower())
        for marker, role in ROLE_MARKERS.items():
            if normalized == marker or normalized.startswith(marker):
                return role
    return ""


def speaker_role_weight(role: str) -> float:
    if role == "user":
        return 1.0
    if role == "assistant":
        return 0.72
    if role == "system":
        return 0.55
    return 0.8


def _is_low_signal_chunk(text: str, content_kind: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return True
    if content_kind == "code":
        return True
    if _looks_like_command(stripped):
        return True
    if len(tokenize(stripped)) < 2 and len(stripped) < 48:
        return True
    return False


def _chunk_plain_text(source_path: Path, text: str) -> List[Dict]:
    lines = [line.rstrip() for line in text.splitlines()]
    non_empty = [line.strip() for line in lines if line.strip()]
    if not non_empty:
        return []
    blocks: List[Tuple[str, str]] = []
    if "\n\n" in text:
        for block in re.split(r"\n\s*\n", text):
            normalized = block.strip()
            if normalized:
                blocks.append(("paragraph", normalized))
    else:
        for line in non_empty:
            blocks.append(("line", line))
    chunks: List[Dict] = []
    for idx, (kind, content) in enumerate(blocks, start=1):
        if _is_low_signal_chunk(content, kind):
            continue
        chunks.append(
            {
                "chunk_index": idx,
                "title": shorten(content, 80),
                "content": content,
                "content_kind": kind,
                "section_path": [],
            }
        )
    return chunks


def _chunk_markdown(source_path: Path, text: str) -> List[Dict]:
    headings: List[str] = []
    chunks: List[Dict] = []
    lines = text.splitlines()
    buffer: List[str] = []
    buffer_kind = "paragraph"
    in_code = False
    chunk_index = 0

    def flush() -> None:
        nonlocal buffer, buffer_kind, chunk_index
        if not buffer:
            return
        content = "\n".join(line.rstrip() for line in buffer).strip()
        buffer = []
        if _is_low_signal_chunk(content, buffer_kind):
            buffer_kind = "paragraph"
            return
        chunk_index += 1
        title_source = re.sub(r"^[-*]\s+|^\d+\.\s+", "", content.splitlines()[0]).strip()
        title_parts = [headings[-1]] if headings else []
        title_parts.append(title_source)
        chunks.append(
            {
                "chunk_index": chunk_index,
                "title": shorten(" · ".join(part for part in title_parts if part), 80),
                "content": content,
                "content_kind": buffer_kind,
                "section_path": list(headings),
            }
        )
        buffer_kind = "paragraph"

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                in_code = False
                flush()
            else:
                flush()
                in_code = True
                buffer_kind = "code"
                buffer = [line]
            continue
        if in_code:
            buffer.append(line)
            continue
        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            flush()
            level = len(heading_match.group(1))
            heading_text = heading_match.group(2).strip()
            headings[:] = headings[: level - 1]
            headings.append(heading_text)
            continue
        if not stripped:
            flush()
            continue
        if re.match(r"^[-*]\s+", stripped) or re.match(r"^\d+\.\s+", stripped):
            flush()
            buffer_kind = "bullet"
            buffer = [stripped]
            flush()
            continue
        if not buffer:
            buffer_kind = "paragraph"
        buffer.append(line)

    flush()
    return chunks


def chunk_source_text(source_path: Path, text: str) -> List[Dict]:
    if source_path.suffix.lower() in {".md", ".markdown"}:
        return _chunk_markdown(source_path, text)
    return _chunk_plain_text(source_path, text)


def load_source_registry_raw(root: Path) -> List[Dict]:
    return read_jsonl(_source_registry_path(root))


def load_chunk_index_raw(root: Path) -> List[Dict]:
    return read_jsonl(_chunk_index_path(root))


def load_source_registry(root: Path) -> List[Dict]:
    from .library_tracker import resolve_governed_source_rows

    raw_rows = load_source_registry_raw(root)
    return [
        row
        for row in resolve_governed_source_rows(root, raw_rows)
        if row.get("include_in_runtime", True)
    ]


def load_chunk_index(root: Path) -> List[Dict]:
    from .library_tracker import resolve_governed_chunk_rows

    raw_rows = load_chunk_index_raw(root)
    runtime_rows: List[Dict] = []
    for row in resolve_governed_chunk_rows(root, raw_rows):
        if not row.get("include_in_runtime", True):
            continue
        normalized = _runtime_chunk_view(row)
        if not str(normalized.get("content", "")).strip():
            continue
        runtime_rows.append(normalized)
    return runtime_rows


def write_vault_files(root: Path, source_rows: List[Dict], chunk_rows: List[Dict]) -> None:
    write_jsonl(_source_registry_path(root), source_rows)
    write_jsonl(_chunk_index_path(root), chunk_rows)
    write_jsonl(_legacy_source_items_path(root), chunk_rows)


def _replace_by_key(rows: List[Dict], key: str, values_to_remove: set[str], additions: List[Dict]) -> List[Dict]:
    kept = [row for row in rows if row.get(key) not in values_to_remove]
    kept.extend(additions)
    return kept


def infer_source_family(source_type: str, source_ref: str) -> str:
    hay = f"{source_type} {source_ref}".lower()
    if "openclaw" in hay or "conversation" in hay or "session" in hay:
        return "openclaw_conversations"
    if "thread" in hay:
        return "thread_derivations"
    return "manual_imports"


def infer_sensitivity_tier(source_type: str, source_ref: str) -> str:
    hay = f"{source_type} {source_ref}".lower()
    if "personal" in hay or "journal" in hay:
        return "tier_personal_sensitive"
    if "reasoning" in hay or "metacognition" in hay:
        return "tier_cognition_metacognition"
    return "tier_work_product"


def _build_source_and_chunk_entries(
    *,
    title: str,
    content: str,
    source_ref: str,
    source_type: str = "manual_import",
    source_family: str | None = None,
    sensitivity_tier: str | None = None,
    metadata: Dict | None = None,
) -> tuple[Dict, List[Dict]]:
    source_family = source_family or infer_source_family(source_type, source_ref)
    sensitivity_tier = sensitivity_tier or infer_sensitivity_tier(source_type, source_ref)
    content_hash = _content_hash(content)
    source_id = f"source-{hashlib.sha256(source_ref.encode('utf-8')).hexdigest()[:12]}"
    pseudo_path = Path(source_ref)
    raw_chunks = chunk_source_text(pseudo_path, content)
    now = utc_now()
    registry_entry = SourceRegistryEntry(
        source_id=source_id,
        title=title,
        source_ref=source_ref,
        source_type=source_type,
        source_family=source_family,
        sensitivity_tier=sensitivity_tier,
        content_hash=content_hash,
        chunk_count=len(raw_chunks),
        updated_at=now,
        metadata=metadata or {},
    ).to_dict()

    chunk_entries: List[Dict] = []
    for chunk in raw_chunks:
        chunk_signature = f"{source_id}:{chunk['chunk_index']}:{chunk['content_kind']}:{chunk['content']}"
        chunk_id = f"chunk-{hashlib.sha256(chunk_signature.encode('utf-8')).hexdigest()[:12]}"
        speaker_role = infer_speaker_role(
            section_path=chunk.get("section_path", []),
            title=chunk["title"],
            content=chunk["content"],
        )
        record = ChunkRecord(
            chunk_id=chunk_id,
            source_id=source_id,
            source_item_id=chunk_id,
            chunk_index=chunk["chunk_index"],
            title=chunk["title"],
            content=chunk["content"],
            content_kind=chunk["content_kind"],
            source_ref=source_ref,
            source_type=source_type,
            source_family=source_family,
            sensitivity_tier=sensitivity_tier,
            created_at=now,
            section_path=chunk.get("section_path", []),
            metadata={
                "path_name": pseudo_path.name,
                "speaker_role": speaker_role,
                "speaker_weight": speaker_role_weight(speaker_role),
                **(metadata or {}),
            },
        ).to_dict()
        for key, value in (metadata or {}).items():
            if key not in record:
                record[key] = value
        chunk_entries.append(record)
    return registry_entry, chunk_entries


def _run_post_ingest_hooks(
    root: Path,
    *,
    source_id: str,
    hooks: Sequence[PostIngestHook] | None,
) -> Dict[str, Any]:
    """Invoke generic post-ingest adapters. Failures are recorded, never raised."""
    receipts: List[Dict[str, Any]] = []
    for index, hook in enumerate(hooks or ()):
        try:
            result = hook(root, source_id=source_id)
            receipts.append(
                {
                    "hook_index": index,
                    "ok": True,
                    "result": result if isinstance(result, dict) else {"value": result},
                }
            )
        except Exception as exc:  # noqa: BLE001 - ingest must remain successful
            receipts.append(
                {
                    "hook_index": index,
                    "ok": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return {"hook_count": len(hooks or ()), "receipts": receipts}


def _persist_original_source_bytes(root: Path, content: str, *, content_hash: str) -> str:
    """Store exact ingested bytes once under their content hash (lossless knowledge-ocean ownership)."""

    raw = content.encode("utf-8")
    digest = SourceContentStore(root).put_bytes(raw)
    expected = str(content_hash or "").strip().lower()
    if expected and digest != expected:
        raise ValueError(
            f"source content store digest mismatch: stored={digest} expected={expected}"
        )
    return digest


def ingest_text_content(
    root: Path,
    *,
    title: str,
    content: str,
    source_ref: str,
    source_type: str = "manual_import",
    source_family: str | None = None,
    sensitivity_tier: str | None = None,
    metadata: Dict | None = None,
    post_ingest_hooks: Sequence[PostIngestHook] | None = None,
) -> Dict:
    source_rows = load_source_registry_raw(root)
    chunk_rows = load_chunk_index_raw(root)
    registry_entry, chunk_entries = _build_source_and_chunk_entries(
        title=title,
        content=content,
        source_ref=source_ref,
        source_type=source_type,
        source_family=source_family,
        sensitivity_tier=sensitivity_tier,
        metadata=metadata,
    )
    source_id = registry_entry["source_id"]
    content_digest = _persist_original_source_bytes(
        root,
        content,
        content_hash=str(registry_entry.get("content_hash") or ""),
    )
    registry_entry["content_pointer"] = f"sha256:{content_digest}"
    source_rows = _replace_by_key(source_rows, "source_id", {source_id}, [registry_entry])
    chunk_rows = _replace_by_key(chunk_rows, "source_id", {source_id}, chunk_entries)
    write_vault_files(root, source_rows, chunk_rows)
    # Generic async adapters only — no Shape-specific branching here.
    post_ingest = _run_post_ingest_hooks(root, source_id=source_id, hooks=post_ingest_hooks)
    return {
        "source_id": source_id,
        "content_hash": content_digest,
        "seeded_count": len(chunk_entries),
        "total_count": len(chunk_rows),
        "source_registry_path": str(_source_registry_path(root)),
        "chunk_index_path": str(_chunk_index_path(root)),
        "post_ingest": post_ingest,
    }


def ingest_text_items_batch(root: Path, items: List[Dict]) -> Dict:
    source_rows = load_source_registry_raw(root)
    chunk_rows = load_chunk_index_raw(root)
    registry_entries: List[Dict] = []
    chunk_entries: List[Dict] = []
    source_ids: set[str] = set()
    seeded_count = 0
    for item in items:
        registry_entry, built_chunks = _build_source_and_chunk_entries(
            title=item["title"],
            content=item["content"],
            source_ref=item["source_ref"],
            source_type=item.get("source_type", "manual_import"),
            source_family=item.get("source_family"),
            sensitivity_tier=item.get("sensitivity_tier"),
            metadata=item.get("metadata"),
        )
        digest = _persist_original_source_bytes(
            root,
            str(item["content"]),
            content_hash=str(registry_entry.get("content_hash") or ""),
        )
        registry_entry["content_pointer"] = f"sha256:{digest}"
        source_ids.add(registry_entry["source_id"])
        registry_entries.append(registry_entry)
        chunk_entries.extend(built_chunks)
        seeded_count += len(built_chunks)
    source_rows = _replace_by_key(source_rows, "source_id", source_ids, registry_entries)
    chunk_rows = _replace_by_key(chunk_rows, "source_id", source_ids, chunk_entries)
    write_vault_files(root, source_rows, chunk_rows)
    return {
        "source_count": len(registry_entries),
        "seeded_count": seeded_count,
        "total_count": len(chunk_rows),
        "source_registry_path": str(_source_registry_path(root)),
        "chunk_index_path": str(_chunk_index_path(root)),
    }


def ingest_source_file(root: Path, source_path: Path, source_type: str = "manual_import") -> Dict:
    text = source_path.read_text(encoding="utf-8")
    return ingest_text_content(
        root,
        title=source_path.stem.replace("-", " ").replace("_", " "),
        content=text,
        source_ref=str(source_path.resolve()),
        source_type=source_type,
    )


def remove_source_by_ref(root: Path, source_ref: str) -> Dict:
    source_rows = load_source_registry_raw(root)
    chunk_rows = load_chunk_index_raw(root)
    target_source_ids = {row["source_id"] for row in source_rows if row.get("source_ref") == source_ref}
    if not target_source_ids:
        target_source_ids.add(f"source-{hashlib.sha256(source_ref.encode('utf-8')).hexdigest()[:12]}")
    remaining_sources = [row for row in source_rows if row.get("source_ref") != source_ref]
    remaining_chunks = [
        row
        for row in chunk_rows
        if row.get("source_id") not in target_source_ids and row.get("source_ref") != source_ref
    ]
    removed_source_count = len(source_rows) - len(remaining_sources)
    removed_chunk_count = len(chunk_rows) - len(remaining_chunks)
    write_vault_files(root, remaining_sources, remaining_chunks)
    return {
        "source_ref": source_ref,
        "removed_source_count": removed_source_count,
        "removed_chunk_count": removed_chunk_count,
    }


def bootstrap_legacy_source_items(root: Path) -> Dict:
    legacy_rows = read_jsonl(_legacy_source_items_path(root))
    source_rows = load_source_registry_raw(root)
    chunk_rows = load_chunk_index_raw(root)
    if (source_rows and chunk_rows) or not legacy_rows:
        return {
            "source_count": len(source_rows),
            "chunk_count": len(chunk_rows),
            "migrated": 0,
        }

    grouped: Dict[str, List[Dict]] = {}
    for row in legacy_rows:
        grouped.setdefault(row["source_ref"], []).append(row)

    migrated_sources = []
    migrated_chunks = []
    for source_ref, rows in grouped.items():
        source_type = rows[0].get("source_type", "legacy_import")
        source_family = rows[0].get("source_family") or infer_source_family(source_type, source_ref)
        sensitivity_tier = rows[0].get("sensitivity_tier") or infer_sensitivity_tier(source_type, source_ref)
        source_id = f"source-{hashlib.sha256(source_ref.encode('utf-8')).hexdigest()[:12]}"
        content = "\n\n".join(row.get("content", "") for row in rows)
        registry_entry = SourceRegistryEntry(
            source_id=source_id,
            title=Path(source_ref).stem.replace("-", " ").replace("_", " "),
            source_ref=source_ref,
            source_type=source_type,
            source_family=source_family,
            sensitivity_tier=sensitivity_tier,
            content_hash=_content_hash(content),
            chunk_count=len(rows),
            updated_at=rows[0].get("created_at", utc_now()),
            metadata={},
        ).to_dict()
        migrated_sources.append(registry_entry)
        for idx, row in enumerate(rows, start=1):
            chunk_id = row.get("chunk_id") or row.get("source_item_id") or f"chunk-{hashlib.sha256(f'{source_id}:{idx}'.encode('utf-8')).hexdigest()[:12]}"
            migrated_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "source_id": source_id,
                    "source_item_id": chunk_id,
                    "chunk_index": row.get("chunk_index", idx),
                    "title": row.get("title", shorten(row.get("content", ""), 80)),
                    "content": row.get("content", ""),
                    "content_kind": row.get("content_kind", "paragraph"),
                    "source_ref": source_ref,
                    "source_type": source_type,
                    "source_family": source_family,
                    "sensitivity_tier": sensitivity_tier,
                    "created_at": row.get("created_at", utc_now()),
                    "section_path": row.get("section_path", []),
                    "metadata": {"path_name": Path(source_ref).name},
                }
            )

    write_vault_files(root, migrated_sources, migrated_chunks)
    return {
        "source_count": len(migrated_sources),
        "chunk_count": len(migrated_chunks),
        "migrated": len(migrated_sources),
    }
