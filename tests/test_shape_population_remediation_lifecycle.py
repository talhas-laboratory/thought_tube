"""Lifecycle and ingest-hook remediation tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.shape_population.orchestrator import enqueue_after_ingest
from conversation_os.shape_population.storage import ShapePopulationStore
from conversation_os.source_content_store import SourceContentStore
from conversation_os.vault_ingest import ingest_text_content


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    return tmp_path


def test_post_ingest_hook_enqueues_without_blocking(root: Path) -> None:
    store = ShapePopulationStore(root)

    def hook(path: Path, *, source_id: str):
        return enqueue_after_ingest(source_id, store=store)

    result = ingest_text_content(
        root,
        title="Shape source",
        content="A mechanism appears when boundary B holds.\n",
        source_ref="manual://shape-1",
        post_ingest_hooks=[hook],
    )
    assert result["source_id"]
    assert result["post_ingest"]["hook_count"] == 1
    assert result["post_ingest"]["receipts"][0]["ok"] is True

    def boom(path: Path, *, source_id: str):
        raise RuntimeError("worker down")

    result2 = ingest_text_content(
        root,
        title="Shape source 2",
        content="Another line.\n",
        source_ref="manual://shape-2",
        post_ingest_hooks=[boom],
    )
    assert result2["source_id"]
    assert result2["post_ingest"]["receipts"][0]["ok"] is False
    assert "worker down" in result2["post_ingest"]["receipts"][0]["error"]


def test_content_store_dedupe_and_source_bytes_once(root: Path) -> None:
    content = SourceContentStore(root)
    raw = b"repeatable payload " * 1000
    a = content.put_bytes(raw)
    b = content.put_bytes(raw)
    assert a == b
    assert content.get_bytes(a) == raw
    blob_dir = root / "product" / "inner_world_v1" / "data" / "source_content"
    files = [p for p in blob_dir.rglob("*") if p.is_file() and p.suffix != ".json"]
    assert len(files) == 1


def test_rejected_promotion_is_terminal(root: Path) -> None:
    from conversation_os.shape_population.candidate_submission import submit_candidate
    from conversation_os.shape_population.contracts import ForbiddenTransitionError
    from conversation_os.shape_population.critique import submit_evaluation
    from conversation_os.shape_population.evidence import build_evidence_packet
    from conversation_os.shape_population.execution_context import agent_context, human_context
    from conversation_os.shape_population.identities import (
        CRITIC_IDENTITY,
        EVALUATOR_IDENTITY,
        HUMAN_APPROVER_ROLE,
        PROPOSER_IDENTITY,
    )
    from conversation_os.shape_population.normalization import normalize_source
    from conversation_os.shape_population.promotion import apply_promotion, record_human_decision, request_promotion

    store = ShapePopulationStore(root)
    normalized = normalize_source(
        {"content": "Evidence for a clear mechanism.\n", "modality": "plain_text"},
        store=store,
    )
    ctx_inq = agent_context(
        PROPOSER_IDENTITY,
        capabilities={"shape.evidence.inquire", "shape.candidate.submit"},
    )
    packet = build_evidence_packet(
        {
            "segment_ids": [seg.segment_id for seg in normalized.segments],
            "evidence_inquiry": {"question": "shape?", "requested_by": PROPOSER_IDENTITY},
        },
        store=store,
        context=ctx_inq,
    )
    refs = []
    for block in packet.blocks:
        segment = store.get_segment(block.segment_id)
        refs.append(
            {
                "packet_id": packet.packet_id,
                "block_id": block.block_id,
                "source_id": block.source_id,
                "segment_id": block.segment_id,
                "char_start": block.char_start,
                "char_end": block.char_end,
                "text_sha256": segment["text_sha256"],
            }
        )
    cand = submit_candidate(
        {
            "packet_id": packet.packet_id,
            "title": "Mech",
            "statement": "A causes B",
            "boundary": "B",
            "mechanism": "A->B",
            "dimensions": ["causality"],
            "evidence_refs": refs,
            "counter_hypotheses": ["alt"],
            "uncertainty": "low",
            "recommended_disposition": "proposed",
            "idempotency_key": "term-1",
        },
        store=store,
        context=agent_context(PROPOSER_IDENTITY, capabilities={"shape.candidate.submit"}),
    )["candidate"]
    evaluation = submit_evaluation(
        {
            "candidate_id": cand["candidate_id"],
            "disposition": "recommended",
            "critique": "ok",
            "evidence_refs": refs,
            "uncertainty": "low",
            "relationship_findings": [],
            "idempotency_key": "term-eval",
        },
        store=store,
        context=agent_context(
            CRITIC_IDENTITY,
            capabilities={"shape.evaluation.submit", "shape.comparison.read"},
        ),
    )["evaluation"]
    requested = request_promotion(
        cand["candidate_id"],
        evaluation["evaluation_id"],
        "ready",
        refs,
        store=store,
        context=agent_context(EVALUATOR_IDENTITY, capabilities={"shape.promotion.request"}),
        idempotency_key="term-prom",
    )
    request_id = requested["request"]["request_id"]
    record_human_decision(
        request_id,
        store=store,
        approval_identity=HUMAN_APPROVER_ROLE,
        approval_reason="not ready",
        decision="rejected",
        context=human_context(HUMAN_APPROVER_ROLE, capabilities={"shape.promotion.approve"}),
    )
    with pytest.raises(ForbiddenTransitionError):
        record_human_decision(
            request_id,
            store=store,
            approval_identity=HUMAN_APPROVER_ROLE,
            approval_reason="flip flop",
            decision="approved",
            context=human_context(HUMAN_APPROVER_ROLE, capabilities={"shape.promotion.approve"}),
        )
    with pytest.raises(Exception):
        apply_promotion(
            request_id,
            store=store,
            approval_identity=HUMAN_APPROVER_ROLE,
            context=human_context(
                "shape.canonical_authority",
                capabilities={"shape.promotion.apply", "shape.promotion.approve"},
            ),
        )
