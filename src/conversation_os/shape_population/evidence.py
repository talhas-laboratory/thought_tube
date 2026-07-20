"""Deterministic build_evidence_packet capability."""

from __future__ import annotations

import hashlib
from typing import Any, Dict, List, Mapping, Optional, Sequence

from conversation_os.shape_population.contracts import (
    EVIDENCE_POLICY_VERSION,
    EvidenceBlock,
    EvidenceInquiry,
    EvidencePacket,
    ValidationError,
    fingerprint_payload,
)
from conversation_os.shape_population.storage import PopulationStore

MODULE_ID = "kernel.shape_population.evidence"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "build_evidence_packet",
)
__all__ = list(PUBLIC_API)


def _packet_id(request: Mapping[str, Any], inquiry: EvidenceInquiry) -> str:
    digest = fingerprint_payload(
        {
            "inquiry": inquiry.to_dict(),
            "segment_ids": list(request.get("segment_ids") or []),
            "policy_version": request.get("policy_version") or EVIDENCE_POLICY_VERSION,
            "corpus_revision": request.get("corpus_revision") or "",
            "token_budget": request.get("token_budget"),
            "segment_budget": request.get("segment_budget"),
            "anchor_ranges": request.get("anchor_ranges") or [],
        }
    )
    return f"pkt-{digest[:20]}"


def _estimate_tokens(text: str) -> int:
    # Deterministic coarse budget measure; not semantic ranking.
    return max(1, (len(text) + 3) // 4) if text else 0


def build_evidence_packet(
    request: Mapping[str, Any],
    *,
    store: PopulationStore,
) -> EvidencePacket:
    """Execute a declared evidence inquiry deterministically. Not an agent tool."""
    inquiry_raw = request.get("evidence_inquiry") or request.get("inquiry") or {}
    if not isinstance(inquiry_raw, Mapping):
        raise ValidationError("evidence_inquiry must be an object")
    question = str(inquiry_raw.get("question") or "").strip()
    if not question:
        raise ValidationError("evidence_inquiry.question is required")
    inquiry = EvidenceInquiry(
        question=question,
        anchors=[str(item) for item in (inquiry_raw.get("anchors") or [])],
        scope=str(inquiry_raw.get("scope") or "declared_segments"),
        requested_by=str(inquiry_raw.get("requested_by") or request.get("requested_by") or ""),
    )
    if not inquiry.requested_by:
        raise ValidationError("evidence inquiry requires requested_by intelligence/authorized identity")

    policy_version = str(request.get("policy_version") or EVIDENCE_POLICY_VERSION)
    corpus_revision = str(request.get("corpus_revision") or "local")
    segment_ids: Sequence[str] = list(request.get("segment_ids") or [])
    token_budget = int(request.get("token_budget") or 2048)
    segment_budget = int(request.get("segment_budget") or 32)
    denied = set(str(item) for item in (request.get("denied_segment_ids") or []))

    omitted: List[Dict[str, Any]] = []
    blocks: List[EvidenceBlock] = []
    used_tokens = 0

    if not segment_ids:
        packet = EvidencePacket(
            packet_id=_packet_id(request, inquiry),
            inquiry=inquiry,
            blocks=[],
            omitted=[{"reason": "empty_request", "segment_id": ""}],
            budget={
                "token_budget": token_budget,
                "segment_budget": segment_budget,
                "tokens_used": 0,
                "segments_used": 0,
            },
            policy_version=policy_version,
            corpus_revision=corpus_revision,
            safe=True,
            empty_reason="no segment_ids declared",
        )
        store.put_packet(packet.to_dict())
        return packet

    for ordinal, segment_id in enumerate(segment_ids):
        if segment_id in denied:
            omitted.append({"segment_id": segment_id, "reason": "denied"})
            continue
        segment = store.get_segment(segment_id)
        if segment is None:
            omitted.append({"segment_id": segment_id, "reason": "missing"})
            continue
        text = str(segment.get("text") or "")
        tokens = _estimate_tokens(text)
        if len(blocks) >= segment_budget:
            omitted.append({"segment_id": segment_id, "reason": "segment_budget"})
            continue
        if used_tokens + tokens > token_budget and blocks:
            omitted.append({"segment_id": segment_id, "reason": "token_budget"})
            continue
        # Whole-block include; if single block exceeds budget, truncate with exact span mapping.
        included_text = text
        char_start = int(segment["char_start"])
        char_end = int(segment["char_end"])
        if tokens > token_budget and not blocks:
            # Truncate to budget while retaining original span start and mapped end.
            max_chars = token_budget * 4
            included_text = text[:max_chars]
            char_end = char_start + len(included_text)
            omitted.append(
                {
                    "segment_id": segment_id,
                    "reason": "truncated",
                    "original_char_start": int(segment["char_start"]),
                    "original_char_end": int(segment["char_end"]),
                    "retained_char_start": char_start,
                    "retained_char_end": char_end,
                }
            )
            tokens = _estimate_tokens(included_text)
        block_id = hashlib.sha256(f"{segment_id}:{char_start}:{char_end}".encode("utf-8")).hexdigest()[:20]
        blocks.append(
            EvidenceBlock(
                block_id=f"blk-{block_id}",
                source_id=str(segment["source_id"]),
                segment_id=segment_id,
                char_start=char_start,
                char_end=char_end,
                text=included_text,
                structure_path=str(segment.get("structure_path") or ""),
                ordinal=ordinal,
            )
        )
        used_tokens += tokens

    empty_reason = ""
    if not blocks:
        reasons = {row["reason"] for row in omitted}
        if "denied" in reasons and reasons <= {"denied"}:
            empty_reason = "all segments denied"
        elif "missing" in reasons:
            empty_reason = "declared segments missing"
        else:
            empty_reason = "no includable evidence"

    packet = EvidencePacket(
        packet_id=_packet_id(request, inquiry),
        inquiry=inquiry,
        blocks=blocks,
        omitted=omitted,
        budget={
            "token_budget": token_budget,
            "segment_budget": segment_budget,
            "tokens_used": used_tokens,
            "segments_used": len(blocks),
        },
        policy_version=policy_version,
        corpus_revision=corpus_revision,
        safe=True,
        empty_reason=empty_reason,
    )
    # No hidden retrieval: only declared segment IDs are considered.
    store.put_packet(packet.to_dict())
    return packet
