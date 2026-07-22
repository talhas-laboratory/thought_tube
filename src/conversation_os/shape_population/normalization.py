"""Lossless structural normalize_source capability."""

from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Iterable, List, Mapping, Optional

from conversation_os.source_content_store import SourceContentStore
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
_CODE_FENCE_RE = re.compile(r"^\s*```")
_TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _stable_id(*parts: str) -> str:
    digest = hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()
    return digest[:32]


def _rejected(
    request: Mapping[str, Any],
    *,
    modality: str,
    content_sha256: str,
    reason: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> NormalizedSource:
    return NormalizedSource(
        source_id="",
        content_sha256=content_sha256,
        modality=modality or "unknown",
        metadata=dict(metadata if metadata is not None else request.get("metadata") or {}),
        normalization_version=NORMALIZATION_VERSION,
        segments=[],
        raw_ref=str(request.get("raw_ref") or request.get("locator") or (f"sha256:{content_sha256}" if content_sha256 else "")),
        locator=str(request.get("locator") or ""),
        ingested_at=str(request.get("ingested_at") or ""),
        rejected=True,
        rejection_reason=reason,
    )


def _read_raw_bytes(request: Mapping[str, Any], content_store: Optional[SourceContentStore], encoding: str) -> bytes:
    if "content" in request:
        content = request.get("content")
        if isinstance(content, str):
            return content.encode(encoding)
        if isinstance(content, (bytes, bytearray, memoryview)):
            return bytes(content)
        raise ValidationError("source content must be str or bytes")
    digest = str(request.get("content_sha256") or request.get("content_digest") or "")
    raw_ref = str(request.get("raw_ref") or "")
    if not digest and raw_ref.startswith("sha256:"):
        digest = raw_ref
    if digest:
        if content_store is None:
            raise ValidationError("content_store is required to load source content by digest")
        return content_store.get_bytes(digest)
    return b""


def _byte_lines(raw: bytes) -> Iterable[bytes]:
    if raw == b"":
        yield b""
        return
    for line in raw.splitlines(keepends=True):
        yield line


def _section_prefix(heading_stack: List[tuple[int, int]]) -> str:
    if not heading_stack:
        return ""
    return "/section/" + ".".join(str(ordinal) for _, ordinal in heading_stack)


def _structure_path_for_line(
    line: str,
    *,
    modality: str,
    in_code: bool,
    heading_stack: List[tuple[int, int]],
    ordinal: int,
) -> str:
    if modality == "code" or in_code:
        return f"/code/{ordinal}"
    if modality == "table" or _TABLE_RE.match(line):
        return f"{_section_prefix(heading_stack)}/table/{ordinal}"
    heading = _HEADING_RE.match(line)
    if modality == "markdown" and heading:
        level = len(heading.group(1))
        return f"/heading/{level}/{ordinal}"
    speaker = _SPEAKER_RE.match(line)
    if modality == "transcript" and speaker:
        safe_speaker = re.sub(r"[^A-Za-z0-9_]+", "_", speaker.group(1).strip()).strip("_") or "speaker"
        return f"{_section_prefix(heading_stack)}/transcript/{safe_speaker}/{ordinal}"
    return f"{_section_prefix(heading_stack)}/paragraph/{ordinal}"


def _decode_segments(
    raw: bytes,
    *,
    source_id: str,
    content_sha256: str,
    modality: str,
    encoding: str,
    decode_errors: str,
) -> List[SegmentRecord]:
    segments: List[SegmentRecord] = []
    char_cursor = 0
    byte_cursor = 0
    in_code = False
    heading_stack: List[tuple[int, int]] = []

    for ordinal, line_bytes in enumerate(_byte_lines(raw)):
        byte_start = byte_cursor
        byte_end = byte_start + len(line_bytes)
        try:
            text = line_bytes.decode(encoding, errors=decode_errors)
        except UnicodeDecodeError as exc:
            raise ValidationError(f"undecodable bytes: {exc}") from exc
        line_no_eol = text.rstrip("\r\n")
        is_fence = modality in {"markdown", "code"} and bool(_CODE_FENCE_RE.match(line_no_eol))
        structure_path = _structure_path_for_line(
            line_no_eol,
            modality=modality,
            in_code=in_code and not is_fence,
            heading_stack=heading_stack,
            ordinal=ordinal,
        )
        if is_fence:
            structure_path = f"/code/fence/{ordinal}"
        char_start = char_cursor
        char_end = char_start + len(text)
        text_sha = _sha256_text(text)
        segment_id = _stable_id(
            content_sha256,
            NORMALIZATION_VERSION,
            structure_path,
            str(ordinal),
            text_sha,
        )
        segments.append(
            SegmentRecord(
                segment_id=segment_id,
                source_id=source_id,
                ordinal=ordinal,
                char_start=char_start,
                char_end=char_end,
                structure_path=structure_path,
                text=text,
                text_sha256=text_sha,
                byte_start=byte_start,
                byte_end=byte_end,
                source_content_sha256=content_sha256,
                normalization_version=NORMALIZATION_VERSION,
            )
        )

        heading = _HEADING_RE.match(line_no_eol)
        if modality == "markdown" and heading and not in_code:
            level = len(heading.group(1))
            heading_stack = [(existing_level, existing_ordinal) for existing_level, existing_ordinal in heading_stack if existing_level < level]
            heading_stack.append((level, ordinal))
        if is_fence:
            in_code = not in_code
        char_cursor = char_end
        byte_cursor = byte_end

    if byte_cursor != len(raw):
        raise ValidationError("segmentation failed to cover full source bytes")
    return segments


def _persist_source(store: PopulationStore, normalized: NormalizedSource) -> None:
    payload = normalized.to_dict()
    payload["segments"] = []
    for segment in normalized.segments:
        row = segment.to_dict()
        row["text"] = ""
        row["text_ref"] = {
            "content_sha256": normalized.content_sha256,
            "byte_start": segment.byte_start,
            "byte_end": segment.byte_end,
            "char_start": segment.char_start,
            "char_end": segment.char_end,
            "encoding": normalized.metadata.get("detected_encoding") or normalized.metadata.get("declared_encoding") or "utf-8",
        }
        payload["segments"].append(row)
    existing = store.get_source(normalized.source_id)
    if existing is None:
        store.put_source(payload)


def normalize_source(
    request: Mapping[str, Any],
    *,
    store: Optional[PopulationStore] = None,
    content_store: Optional[SourceContentStore] = None,
) -> NormalizedSource:
    """Deterministic lossless normalization. Not an agent tool."""
    modality = str(request.get("modality") or "").strip()
    metadata = dict(request.get("metadata") or {})
    if modality not in SUPPORTED_MODALITIES:
        return _rejected(
            request,
            modality=modality,
            content_sha256="",
            metadata=metadata,
            reason=f"unsupported modality: {modality or 'missing'}",
        )

    encoding = str(request.get("encoding") or "utf-8")
    decode_errors = str(request.get("decode_errors") or request.get("errors") or "strict")
    if decode_errors not in {"strict", "replace"}:
        raise ValidationError("decode_errors must be 'strict' or 'replace'")
    try:
        raw = _read_raw_bytes(request, content_store, encoding)
    except ValidationError as exc:
        return _rejected(request, modality=modality, content_sha256="", metadata=metadata, reason=str(exc))

    content_sha = _sha256_bytes(raw)
    if content_store is not None and "content" in request:
        stored_digest = content_store.put_bytes(raw)
        if stored_digest != content_sha:
            raise ValidationError("content store digest mismatch")

    max_source_bytes = request.get("max_source_bytes")
    if max_source_bytes is None and "max_chars" in request:
        max_source_bytes = request.get("max_chars")
    if max_source_bytes is not None:
        try:
            max_bytes = int(max_source_bytes)
        except (TypeError, ValueError) as exc:
            raise ValidationError("max_source_bytes must be an integer") from exc
        if max_bytes <= 0:
            raise ValidationError("max_source_bytes must be positive")
        if len(raw) > max_bytes:
            metadata.update(
                {
                    "observed_source_bytes": len(raw),
                    "max_source_bytes": max_bytes,
                    "receipt_reason": "source_exceeds_max_source_bytes",
                }
            )
            return _rejected(
                request,
                modality=modality,
                content_sha256=content_sha,
                metadata=metadata,
                reason=f"source exceeds max_source_bytes budget ({len(raw)} > {max_bytes})",
            )

    source_id = _stable_id(content_sha, NORMALIZATION_VERSION, modality)
    metadata.update(
        {
            "source_content_sha256": content_sha,
            "byte_length": len(raw),
            "declared_encoding": str(request.get("encoding") or ""),
            "detected_encoding": encoding,
            "decode_errors": decode_errors,
            "content_pointer": f"sha256:{content_sha}",
        }
    )
    if "redactions" in request:
        metadata["redactions"] = list(request.get("redactions") or [])

    forbidden = {"shape", "topic", "summary", "embedding", "canonical"}
    if forbidden.intersection(metadata):
        raise ValidationError("normalized metadata cannot include semantic Shape fields")

    try:
        segments = _decode_segments(
            raw,
            source_id=source_id,
            content_sha256=content_sha,
            modality=modality,
            encoding=encoding,
            decode_errors=decode_errors,
        )
    except ValidationError as exc:
        return _rejected(request, modality=modality, content_sha256=content_sha, metadata=metadata, reason=str(exc))

    normalized = NormalizedSource(
        source_id=source_id,
        content_sha256=content_sha,
        modality=modality,
        metadata=metadata,
        normalization_version=NORMALIZATION_VERSION,
        segments=segments,
        raw_ref=str(request.get("raw_ref") or f"sha256:{content_sha}"),
        locator=str(request.get("locator") or ""),
        ingested_at=str(request.get("ingested_at") or ""),
        rejected=False,
        rejection_reason="",
    )

    if store is not None:
        _persist_source(store, normalized)
    return normalized
