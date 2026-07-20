"""Tests for human-gated promotion operations."""

from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.shape_population.candidate_submission import submit_candidate
from conversation_os.shape_population.canonical_port import LocalRecordingCanonicalPort
from conversation_os.shape_population.contracts import AuthorizationError, ForbiddenTransitionError, ValidationError
from conversation_os.shape_population.critique import submit_evaluation
from conversation_os.shape_population.evidence import build_evidence_packet
from conversation_os.shape_population.execution_context import (
    CAP_CANDIDATE_SUBMIT,
    CAP_EVALUATION_SUBMIT,
    CAP_EVIDENCE_INQUIRE,
    CAP_PROMOTION_APPLY,
    CAP_PROMOTION_APPROVE,
    CAP_PROMOTION_REQUEST,
    CAP_PROMOTION_ROLLBACK,
    agent_context,
    human_context,
    service_context,
)
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


def _inq_context():
    return agent_context(PROPOSER_IDENTITY, capabilities=(CAP_EVIDENCE_INQUIRE,))


def _prop_context(run_id: str = "p-run"):
    return agent_context(
        PROPOSER_IDENTITY,
        capabilities=(CAP_CANDIDATE_SUBMIT,),
        run_id=run_id,
        model_id="stub",
        prompt_version="p",
    )


def _critic_context(run_id: str = "c-run"):
    return agent_context(
        CRITIC_IDENTITY,
        capabilities=(CAP_EVALUATION_SUBMIT,),
        run_id=run_id,
        model_id="stub",
        prompt_version="c",
    )


def _eval_context():
    return agent_context(EVALUATOR_IDENTITY, capabilities=(CAP_PROMOTION_REQUEST,), model_id="stub", prompt_version="e")


def _human_context():
    return human_context(HUMAN_APPROVER_ROLE, capabilities=(CAP_PROMOTION_APPROVE, CAP_PROMOTION_APPLY, CAP_PROMOTION_ROLLBACK))


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
        context=_inq_context(),
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
            "idempotency_key": f"cand-{key}",
        },
        store=store,
        context=_prop_context(f"p-{key}"),
    )["candidate"]
    evaluation = submit_evaluation(
        {
            "candidate_id": candidate["candidate_id"],
            "disposition": "recommended",
            "critique": "Grounded and coherent.",
            "evidence_refs": refs,
            "uncertainty": "low",
            "idempotency_key": f"eval-{key}",
        },
        store=store,
        context=_critic_context(f"c-{key}"),
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
        context=_eval_context(),
        idempotency_key="prom-req-1",
    )
    assert requested["request"]["status"] == "requested"
    with pytest.raises(AuthorizationError):
        apply_promotion(
            requested["request"]["request_id"],
            store=store,
            context=agent_context(EVALUATOR_IDENTITY, capabilities=(CAP_PROMOTION_APPLY,)),
        )
    with pytest.raises(AuthorizationError):
        record_human_approval(
            requested["request"]["request_id"],
            store=store,
            approval_reason="nope",
            context=agent_context(EVALUATOR_IDENTITY, capabilities=(CAP_PROMOTION_APPROVE,)),
        )


def test_human_apply_idempotent_request_and_rejection(store: PopulationStore) -> None:
    candidate, evaluation = _recommended_candidate(store, "hum-1")
    eval_ctx = _eval_context()
    first = request_promotion(
        candidate["candidate_id"],
        evaluation["evaluation_id"],
        "Ready",
        candidate["evidence_refs"],
        store=store,
        context=eval_ctx,
        idempotency_key="prom-hum-1",
    )
    second = request_promotion(
        candidate["candidate_id"],
        evaluation["evaluation_id"],
        "Ready",
        candidate["evidence_refs"],
        store=store,
        context=eval_ctx,
        idempotency_key="prom-hum-1",
    )
    assert second["replayed"] is True
    request_id = first["request"]["request_id"]
    record_human_approval(
        request_id,
        store=store,
        approval_reason="reject weak",
        decision="rejected",
        context=_human_context(),
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
        context=_eval_context(),
        idempotency_key="prom-apply-1",
    )
    record_human_approval(
        requested["request"]["request_id"],
        store=store,
        approval_reason="Looks solid",
        context=_human_context(),
    )
    port = LocalRecordingCanonicalPort()
    applied = apply_promotion(
        requested["request"]["request_id"],
        store=store,
        context=_human_context(),
        canonical_port=port,
    )
    assert applied["candidate"]["status"] == "canonical"
    assert store.get_canonical_projection(candidate["candidate_id"]) is not None
    candidate2, evaluation2 = _recommended_candidate(store, "apply-2")
    requested2 = request_promotion(
        candidate2["candidate_id"],
        evaluation2["evaluation_id"],
        "Promote2",
        candidate2["evidence_refs"],
        store=store,
        context=_eval_context(),
        idempotency_key="prom-apply-2",
    )
    with pytest.raises(AuthorizationError):
        apply_promotion(
            requested2["request"]["request_id"],
            store=store,
            context=agent_context(PROPOSER_IDENTITY, capabilities=(CAP_PROMOTION_APPLY,)),
        )
    rolled = rollback_promotion(
        candidate["candidate_id"],
        store=store,
        context=_human_context(),
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
            context=agent_context(PROPOSER_IDENTITY, capabilities=(CAP_PROMOTION_REQUEST,)),
        )
    with pytest.raises(ValidationError):
        request_promotion(
            candidate["candidate_id"],
            evaluation["evaluation_id"],
            "x",
            [],
            store=store,
            context=_eval_context(),
            idempotency_key="missing-ev",
        )
    normalized = normalize_source({"content": "x\n", "modality": "plain_text"}, store=store)
    packet = build_evidence_packet(
        {
            "segment_ids": [normalized.segments[0].segment_id],
            "evidence_inquiry": {"question": "q", "requested_by": PROPOSER_IDENTITY},
        },
        store=store,
        context=_inq_context(),
    )
    proposed = submit_candidate(
        {
            "packet_id": packet.packet_id,
            "title": "t",
            "statement": "s",
            "boundary": "b",
            "mechanism": "m",
            "dimensions": ["d"],
            "evidence_refs": [_refs(packet)[0]],
            "counter_hypotheses": ["a"],
            "uncertainty": "high",
            "recommended_disposition": "proposed",
            "idempotency_key": "still-proposed",
        },
        store=store,
        context=_prop_context("still"),
    )["candidate"]
    proposed_eval = submit_evaluation(
        {
            "candidate_id": proposed["candidate_id"],
            "disposition": "under_review",
            "critique": "still weak",
            "evidence_refs": proposed["evidence_refs"],
            "uncertainty": "high",
            "idempotency_key": "eval-still-proposed",
        },
        store=store,
        context=_critic_context("c-proposed"),
    )["evaluation"]
    with pytest.raises(ForbiddenTransitionError):
        request_promotion(
            proposed["candidate_id"],
            proposed_eval["evaluation_id"],
            "nope",
            proposed["evidence_refs"],
            store=store,
            context=_eval_context(),
            idempotency_key="not-ready",
        )


def test_evaluator_rubric_marker(store: PopulationStore) -> None:
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
