"""Lossless structural normalize_source capability."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Union

from conversation_os.shape_population.contracts import (
    NORMALIZATION_VERSION as NORMALIZATION_VERSION,
    NormalizedSource,
    SegmentRecord,
    ValidationError,
)
from conversation_os.shape_population.storage import PopulationStore

MODULE_ID = "kernel.shape_population.normalization"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "NORMALIZATION_VERSION",
    "SUPPORTED_MODALITIES",
    "normalize_source",
)
__all__ = list(PUBLIC_API)

SUPPORTED_MODALITIES = frozenset({"plain_text", "markdown", "transcript", "code", "table"})
_HEADING_RE = re.compile(r"^(#{1,6})\s+.*$")
_SPEAKER_RE = re.compile(r"^([A-Za-z][\w\s]{0,40}):\s+.*$")
_CODE_FENCE_RE = re.compile(r"^```")
_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_id(*parts: str) -> str:
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:24]


def _decode_source(raw: Union[str, bytes], encoding: str = "utf-8") -> str:
    if isinstance(raw, str):
        return raw
    if not isinstance(raw, (bytes, bytearray)):
        raise ValidationError("source must be str or bytes")
    try:
        return bytes(raw).decode(encoding)
    except UnicodeDecodeError as exc:
        raise ValidationError(f"undecodable bytes: {exc}") from exc


def _structure_path_for_line(line: str, *, in_code: bool, ordinal: int) -> str:
    if in_code:
        return f"/code/{ordinal}"
    if _HEADING_RE.match(line):
        level = len(_HEADING_RE.match(line).group(1))
        return f"/heading/{level}/{ordinal}"
    if _SPEAKER_RE.match(line):
        speaker = _SPEAKER_RE.match(line).group(1).strip().replace(" ", "_")
        return f"/transcript/{speaker}/{ordinal}"
    if _TABLE_RE.match(line):
        return f"/table/{ordinal}"
    return f"/paragraph/{ordinal}"


def _segment_lines(text: str) -> List[Dict[str, Any]]:
    """Split into ordered segments while preserving exact text coverage."""
    if text == "":
        return [
            {
                "ordinal": 0,
                "char_start": 0,
                "char_end": 0,
                "structure_path": "/empty/0",
                "text": "",
            }
        ]

    segments: List[Dict[str, Any]] = []
    # Keep line breaks attached to each line so reconstruction is exact.
    parts = re.split(r"(?<=\n)", text)
    # re.split with lookbehind may yield a trailing empty string.
    if parts and parts[-1] == "" and text.endswith("\n"):
        parts = parts[:-1]
    if not parts:
        parts = [text]

    cursor = 0
    in_code = False
    ordinal = 0
    for part in parts:
        if part == "" and cursor >= len(text):
            continue
        stripped = part[:-1] if part.endswith("\n") else part
        if _CODE_FENCE_RE.match(stripped):
            in_code = not in_code
        structure_path = _structure_path_for_line(stripped, in_code=in_code and not _CODE_FENCE_RE.match(stripped), ordinal=ordinal)
        char_start = cursor
        char_end = cursor + len(part)
        if char_end > len(text) or text[char_start:char_end] != part:
            raise ValidationError("offset ambiguity during segmentation")
        segments.append(
            {
                "ordinal": ordinal,
                "char_start": char_start,
                "char_end": char_end,
                "structure_path": structure_path,
                "text": part,
            }
        )
        cursor = char_end
        ordinal += 1

    if cursor != len(text):
        raise ValidationError("segmentation failed to cover full source")
    return segments


def normalize_source(
    request: Mapping[str, Any],
    *,
    store: Optional[PopulationStore] = None,
) -> NormalizedSource:
    """Deterministic lossless normalization. Not an agent tool."""
    modality = str(request.get("modality") or "").strip()
    if modality not in SUPPORTED_MODALITIES:
        return NormalizedSource(
            source_id="",
            content_sha256="",
            modality=modality or "unknown",
            metadata=dict(request.get("metadata") or {}),
            normalization_version=NORMALIZATION_VERSION,
            segments=[],
            raw_ref=str(request.get("raw_ref") or ""),
            locator=str(request.get("locator") or ""),
            ingested_at=str(request.get("ingested_at") or ""),
            rejected=True,
            rejection_reason=f"unsupported modality: {modality or 'missing'}",
        )

    encoding = str(request.get("encoding") or "utf-8")
    try:
        text = _decode_source(request.get("content", b"" if "content" in request else ""), encoding=encoding)
    except ValidationError as exc:
        return NormalizedSource(
            source_id="",
            content_sha256="",
            modality=modality,
            metadata=dict(request.get("metadata") or {}),
            normalization_version=NORMALIZATION_VERSION,
            segments=[],
            raw_ref=str(request.get("raw_ref") or ""),
            locator=str(request.get("locator") or ""),
            ingested_at=str(request.get("ingested_at") or ""),
            rejected=True,
            rejection_reason=str(exc),
        )

    # Optional budget bound for large inputs.
    max_chars = int(request.get("max_chars") or 500_000)
    if len(text) > max_chars:
        return NormalizedSource(
            source_id="",
            content_sha256=_sha256_text(text),
            modality=modality,
            metadata=dict(request.get("metadata") or {}),
            normalization_version=NORMALIZATION_VERSION,
            segments=[],
            raw_ref=str(request.get("raw_ref") or ""),
            locator=str(request.get("locator") or ""),
            ingested_at=str(request.get("ingested_at") or ""),
            rejected=True,
            rejection_reason=f"source exceeds max_chars budget ({max_chars})",
        )

    content_sha = _sha256_text(text)
    source_id = _stable_id(content_sha, NORMALIZATION_VERSION, modality)
    try:
        raw_segments = _segment_lines(text)
    except ValidationError as exc:
        return NormalizedSource(
            source_id=source_id,
            content_sha256=content_sha,
            modality=modality,
            metadata=dict(request.get("metadata") or {}),
            normalization_version=NORMALIZATION_VERSION,
            segments=[],
            raw_ref=str(request.get("raw_ref") or ""),
            locator=str(request.get("locator") or ""),
            ingested_at=str(request.get("ingested_at") or ""),
            rejected=True,
            rejection_reason=str(exc),
        )

    encoded = text.encode("utf-8")
    segments: List[SegmentRecord] = []
    for item in raw_segments:
        text_sha = _sha256_text(item["text"])
        segment_id = _stable_id(source_id, item["structure_path"], text_sha, str(item["ordinal"]))
        # Byte offsets for UTF-8 when unambiguous.
        prefix = text[: item["char_start"]].encode("utf-8")
        piece = item["text"].encode("utf-8")
        byte_start = len(prefix)
        byte_end = byte_start + len(piece)
        if encoded[byte_start:byte_end] != piece:
            raise ValidationError("byte offset ambiguity")
        segments.append(
            SegmentRecord(
                segment_id=segment_id,
                source_id=source_id,
                ordinal=item["ordinal"],
                char_start=item["char_start"],
                char_end=item["char_end"],
                structure_path=item["structure_path"],
                text=item["text"],
                text_sha256=text_sha,
                byte_start=byte_start,
                byte_end=byte_end,
            )
        )

    metadata = dict(request.get("metadata") or {})
    # Preserve redaction provenance markers when supplied; never invent them.
    if "redactions" in request:
        metadata["redactions"] = list(request.get("redactions") or [])

    normalized = NormalizedSource(
        source_id=source_id,
        content_sha256=content_sha,
        modality=modality,
        metadata=metadata,
        normalization_version=NORMALIZATION_VERSION,
        segments=segments,
        raw_ref=str(request.get("raw_ref") or request.get("locator") or ""),
        locator=str(request.get("locator") or ""),
        ingested_at=str(request.get("ingested_at") or ""),
        rejected=False,
        rejection_reason="",
    )

    # Semantic fields are forbidden on normalized records.
    forbidden = {"shape", "topic", "summary", "embedding", "canonical"}
    if forbidden.intersection(normalized.metadata):
        raise ValidationError("normalized metadata cannot include semantic Shape fields")

    if store is not None and not normalized.rejected:
        existing = store.get_source(normalized.source_id)
        if existing is None:
            store.put_source(normalized.to_dict())
        # Re-ingest idempotency: identical IDs/digests already stored.
    return normalized
