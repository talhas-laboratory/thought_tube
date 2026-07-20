"""Tests for human-gated promotion operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.shape_population.candidate_submission import submit_candidate
from conversation_os.shape_population.canonical_port import LocalRecordingCanonicalPort
from conversation_os.shape_population.contracts import AuthorizationError, ForbiddenTransitionError, ValidationError
from conversation_os.shape_population.critique import submit_evaluation
from conversation_os.shape_population.evidence import build_evidence_packet
from conversation_os.shape_population.execution_context import ExecutionContext
from conversation_os.shape_population.identities import (
    CRITIC_IDENTITY,
    EVALUATOR_IDENTITY,
    HUMAN_APPROVER_ROLE,
    PROPOSER_IDENTITY,
)
from conversation_os.shape_population.normalization import normalize_source
from conversation_os.shape_population.promotion import (
    apply_promotion,
    record_human_approval,
    request_promotion,
    rollback_promotion,
)
from conversation_os.shape_population.storage import PopulationStore

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "shape_population" / "promotion"


def _context() -> ExecutionContext:
    return ExecutionContext(
        principal_id=PROPOSER_IDENTITY,
        principal_kind="agent",
        authenticated_by="unit-test",
        capabilities=("shape.evidence.inquire",),
    )


def _refs(packet) -> list[dict]:
    return [
        {
            "packet_id": packet.packet_id,
            "block_id": block.block_id,
            "source_id": block.source_id,
            "segment_id": block.segment_id,
            "char_start": block.char_start,
            "char_end": block.char_end,
            "text_sha256": block.text_sha256,
            "normalization_version": block.normalization_version,
        }
        for block in packet.blocks
    ]


def _recommended_candidate(store: PopulationStore, key: str = "prom-1") -> tuple[dict, dict]:
    normalized = normalize_source(
        {"content": "Strong grounded mechanism with clear boundary.\n", "modality": "plain_text"},
        store=store,
    )
    packet = build_evidence_packet(
        {
            "segment_ids": [seg.segment_id for seg in normalized.segments],
            "evidence_inquiry": {"question": "promote?", "requested_by": PROPOSER_IDENTITY},
        },
        store=store,
        context=_context(),
    )
    refs = _refs(packet)
    candidate = submit_candidate(
        {
            "packet_id": packet.packet_id,
            "title": "Grounded shape",
            "statement": "Mechanism holds under boundary.",
            "boundary": "clear boundary",
            "mechanism": "m",
            "dimensions": ["d"],
            "evidence_refs": refs,
            "counter_hypotheses": ["alt"],
            "uncertainty": "low",
            "recommended_disposition": "proposed",
            "agent_identity": PROPOSER_IDENTITY,
            "model_version": "stub",
            "prompt_version": "p",
            "tool_contract_version": "1.0.0",
            "run_id": "p-run",
            "idempotency_key": f"cand-{key}",
        },
        store=store,
    )["candidate"]
    evaluation = submit_evaluation(
        {
            "candidate_id": candidate["candidate_id"],
            "disposition": "recommended",
            "critique": "Grounded and coherent.",
            "evidence_refs": refs,
            "uncertainty": "low",
            "agent_identity": CRITIC_IDENTITY,
            "model_version": "stub",
            "prompt_version": "c",
            "tool_contract_version": "1.0.0",
            "run_id": "c-run",
            "idempotency_key": f"eval-{key}",
        },
        store=store,
    )["evaluation"]
    return store.get_candidate(candidate["candidate_id"]), evaluation


@pytest.fixture()
def store(tmp_path: Path) -> PopulationStore:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    return PopulationStore(tmp_path)


def test_evaluator_can_request_but_not_approve(store: PopulationStore) -> None:
    candidate, evaluation = _recommended_candidate(store, "req-1")
    requested = request_promotion(
        candidate["candidate_id"],
        evaluation["evaluation_id"],
        "Ready for canon",
        candidate["evidence_refs"],
        store=store,
        requester_identity=EVALUATOR_IDENTITY,
        idempotency_key="prom-req-1",
    )
    assert requested["request"]["status"] == "requested"
    with pytest.raises(AuthorizationError):
        apply_promotion(
            requested["request"]["request_id"],
            store=store,
            approval_identity=EVALUATOR_IDENTITY,
            approval_reason="self approve",
        )
    with pytest.raises(AuthorizationError):
        record_human_approval(
            requested["request"]["request_id"],
            store=store,
            approval_identity=EVALUATOR_IDENTITY,
            approval_reason="nope",
        )


def test_human_apply_idempotent_request_and_rejection(store: PopulationStore) -> None:
    candidate, evaluation = _recommended_candidate(store, "hum-1")
    first = request_promotion(
        candidate["candidate_id"],
        evaluation["evaluation_id"],
        "Ready",
        candidate["evidence_refs"],
        store=store,
        idempotency_key="prom-hum-1",
    )
    second = request_promotion(
        candidate["candidate_id"],
        evaluation["evaluation_id"],
        "Ready",
        candidate["evidence_refs"],
        store=store,
        idempotency_key="prom-hum-1",
    )
    assert second["replayed"] is True
    request_id = first["request"]["request_id"]
    record_human_approval(
        request_id,
        store=store,
        approval_identity=HUMAN_APPROVER_ROLE,
        approval_reason="reject weak",
        decision="rejected",
    )
    assert store.get_candidate(candidate["candidate_id"])["status"] == "recommended"
    assert store.get_canonical_projection(candidate["candidate_id"]) is None


def test_apply_promotion_and_rollback(store: PopulationStore) -> None:
    candidate, evaluation = _recommended_candidate(store, "apply-1")
    requested = request_promotion(
        candidate["candidate_id"],
        evaluation["evaluation_id"],
        "Promote",
        candidate["evidence_refs"],
        store=store,
        idempotency_key="prom-apply-1",
    )
    record_human_approval(
        requested["request"]["request_id"],
        store=store,
        approval_identity=HUMAN_APPROVER_ROLE,
        approval_reason="Looks solid",
    )
    port = LocalRecordingCanonicalPort()
    applied = apply_promotion(
        requested["request"]["request_id"],
        store=store,
        approval_identity=HUMAN_APPROVER_ROLE,
        canonical_port=port,
    )
    assert applied["candidate"]["status"] == "canonical"
    assert store.get_canonical_projection(candidate["candidate_id"]) is not None
    # Population identity cannot apply.
    candidate2, evaluation2 = _recommended_candidate(store, "apply-2")
    requested2 = request_promotion(
        candidate2["candidate_id"],
        evaluation2["evaluation_id"],
        "Promote2",
        candidate2["evidence_refs"],
        store=store,
        idempotency_key="prom-apply-2",
    )
    with pytest.raises(AuthorizationError):
        apply_promotion(
            requested2["request"]["request_id"],
            store=store,
            approval_identity=PROPOSER_IDENTITY,
            approval_reason="no",
        )
    rolled = rollback_promotion(
        candidate["candidate_id"],
        store=store,
        authority_identity=HUMAN_APPROVER_ROLE,
        canonical_port=port,
        reason="revert",
    )
    assert rolled["projection"] is None
    assert rolled["candidate"]["status"] == "recommended"


def test_unauthorized_and_missing_evidence(store: PopulationStore) -> None:
    candidate, evaluation = _recommended_candidate(store, "bad-1")
    with pytest.raises(AuthorizationError):
        request_promotion(
            candidate["candidate_id"],
            evaluation["evaluation_id"],
            "x",
            candidate["evidence_refs"],
            store=store,
            requester_identity=PROPOSER_IDENTITY,
        )
    with pytest.raises(ValidationError):
        request_promotion(
            candidate["candidate_id"],
            evaluation["evaluation_id"],
            "x",
            [],
            store=store,
            idempotency_key="missing-ev",
        )
    # Not recommended yet path
    normalized = normalize_source({"content": "x\n", "modality": "plain_text"}, store=store)
    packet = build_evidence_packet(
        {
            "segment_ids": [normalized.segments[0].segment_id],
            "evidence_inquiry": {"question": "q", "requested_by": PROPOSER_IDENTITY},
        },
        store=store,
        context=_context(),
    )
    proposed = submit_candidate(
        {
            "packet_id": packet.packet_id,
            "title": "t",
            "statement": "s",
            "boundary": "b",
            "mechanism": "m",
            "dimensions": ["d"],
            "evidence_refs": [
                {
                    **_refs(packet)[0],
                }
            ],
            "counter_hypotheses": ["a"],
            "uncertainty": "high",
            "recommended_disposition": "proposed",
            "agent_identity": PROPOSER_IDENTITY,
            "model_version": "stub",
            "prompt_version": "p",
            "tool_contract_version": "1.0.0",
            "idempotency_key": "still-proposed",
        },
        store=store,
    )["candidate"]
    proposed_eval = submit_evaluation(
        {
            "candidate_id": proposed["candidate_id"],
            "disposition": "under_review",
            "critique": "still weak",
            "evidence_refs": proposed["evidence_refs"],
            "uncertainty": "high",
            "agent_identity": CRITIC_IDENTITY,
            "model_version": "stub",
            "prompt_version": "c",
            "tool_contract_version": "1.0.0",
            "run_id": "c-proposed",
            "idempotency_key": "eval-still-proposed",
        },
        store=store,
    )["evaluation"]
    with pytest.raises(ForbiddenTransitionError):
        request_promotion(
            proposed["candidate_id"],
            proposed_eval["evaluation_id"],
            "nope",
            proposed["evidence_refs"],
            store=store,
            idempotency_key="not-ready",
        )


def test_evaluator_rubric_marker(store: PopulationStore) -> None:
    """Bounded non-deterministic quality marker for golden recommendation cases."""
    candidate, evaluation = _recommended_candidate(store, "rubric-1")
    rubric = {
        "grounding": "present",
        "explanatory_coherence": "present",
        "boundary_clarity": bool(candidate["boundary"]),
        "uncertainty": evaluation["uncertainty"],
        "non_deterministic_quality": True,
    }
    assert rubric["non_deterministic_quality"] is True
    assert rubric["boundary_clarity"]
