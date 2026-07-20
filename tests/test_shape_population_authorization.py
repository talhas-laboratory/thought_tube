from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.shape_population.candidate_submission import submit_candidate
from conversation_os.shape_population.canonical_port import LocalRecordingCanonicalPort
from conversation_os.shape_population.contracts import AuthorizationError, ForbiddenTransitionError
from conversation_os.shape_population.critique import find_comparison_candidates, submit_evaluation
from conversation_os.shape_population.evidence import build_evidence_packet
from conversation_os.shape_population.execution_context import (
    CAP_CANDIDATE_SUBMIT,
    CAP_EVALUATION_SUBMIT,
    CAP_EVIDENCE_INQUIRE,
    CAP_PROMOTION_APPLY,
    CAP_PROMOTION_APPROVE,
    CAP_PROMOTION_REQUEST,
    ExecutionContext,
    agent_context,
    human_context,
    service_context,
)
from conversation_os.shape_population.identities import CRITIC_IDENTITY, EVALUATOR_IDENTITY, PROPOSER_IDENTITY
from conversation_os.shape_population.normalization import normalize_source
from conversation_os.shape_population.promotion import apply_promotion, record_human_decision, request_promotion
from conversation_os.shape_population.storage import PopulationStore


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


def _candidate_and_eval(store: PopulationStore, key: str = "auth") -> tuple[dict, dict]:
    prop_ctx = agent_context(
        PROPOSER_IDENTITY,
        capabilities=(CAP_EVIDENCE_INQUIRE, CAP_CANDIDATE_SUBMIT),
        run_id=f"{key}-proposer",
        model_id="stub",
        prompt_version="prop",
    )
    normalized = normalize_source({"content": "Grounded promotion evidence.\n", "modality": "plain_text"}, store=store)
    packet = build_evidence_packet(
        {
            "segment_ids": [segment.segment_id for segment in normalized.segments],
            "evidence_inquiry": {"question": "shape?"},
        },
        store=store,
        context=prop_ctx,
    )
    candidate = submit_candidate(
        {
            "packet_id": packet.packet_id,
            "title": "Grounded",
            "statement": "Grounded evidence supports the claim.",
            "boundary": "bounded",
            "mechanism": "mechanism",
            "dimensions": ["d"],
            "evidence_refs": _refs(packet),
            "counter_hypotheses": ["alt"],
            "uncertainty": "low",
            "recommended_disposition": "proposed",
            "idempotency_key": f"{key}-candidate",
        },
        store=store,
        context=prop_ctx,
    )["candidate"]
    critic_ctx = agent_context(
        CRITIC_IDENTITY,
        capabilities=(CAP_EVALUATION_SUBMIT,),
        run_id=f"{key}-critic",
        model_id="stub",
        prompt_version="crit",
    )
    evaluation = submit_evaluation(
        {
            "candidate_id": candidate["candidate_id"],
            "disposition": "recommended",
            "critique": "Ready.",
            "evidence_refs": candidate["evidence_refs"],
            "uncertainty": "low",
            "idempotency_key": f"{key}-evaluation",
        },
        store=store,
        context=critic_ctx,
    )["evaluation"]
    return store.get_candidate(candidate["candidate_id"]), evaluation


@pytest.fixture()
def store(tmp_path: Path) -> PopulationStore:
    return PopulationStore(tmp_path)


def test_context_overrides_model_selected_identity(store: PopulationStore) -> None:
    ctx = agent_context(
        PROPOSER_IDENTITY,
        capabilities=(CAP_EVIDENCE_INQUIRE, CAP_CANDIDATE_SUBMIT),
        run_id="trusted-run",
        model_id="trusted-model",
        prompt_version="trusted-prompt",
    )
    normalized = normalize_source({"content": "Payload tries to spoof identity.\n", "modality": "plain_text"}, store=store)
    packet = build_evidence_packet(
        {
            "segment_ids": [segment.segment_id for segment in normalized.segments],
            "evidence_inquiry": {"question": "shape?"},
        },
        store=store,
        context=ctx,
    )
    candidate = submit_candidate(
        {
            "packet_id": packet.packet_id,
            "title": "Trusted",
            "statement": "Trusted context wins.",
            "boundary": "bounded",
            "mechanism": "mechanism",
            "dimensions": ["d"],
            "evidence_refs": _refs(packet),
            "counter_hypotheses": [],
            "uncertainty": "medium",
            "recommended_disposition": "proposed",
            "agent_identity": CRITIC_IDENTITY,
            "model_version": "untrusted-model",
            "prompt_version": "untrusted-prompt",
            "tool_contract_version": "evil",
            "run_id": "evil-run",
            "idempotency_key": "spoof-candidate",
        },
        store=store,
        context=ctx,
    )["candidate"]

    assert candidate["agent_identity"] == PROPOSER_IDENTITY
    assert candidate["model_version"] == "trusted-model"
    assert candidate["prompt_version"] == "trusted-prompt"
    assert candidate["run_id"] == "trusted-run"


def test_untrusted_context_cannot_call_privileged_operations(store: PopulationStore) -> None:
    candidate, evaluation = _candidate_and_eval(store, "priv")
    weak_ctx = ExecutionContext(
        principal_id="weak.agent",
        principal_kind="agent",
        authenticated_by="unit-test",
        capabilities=(),
    )
    with pytest.raises(AuthorizationError):
        find_comparison_candidates(candidate["candidate_id"], store=store, context=weak_ctx)
    with pytest.raises(AuthorizationError):
        request_promotion(
            candidate["candidate_id"],
            evaluation["evaluation_id"],
            "Ready",
            candidate["evidence_refs"],
            store=store,
            context=weak_ctx,
        )

    request_ctx = agent_context(EVALUATOR_IDENTITY, capabilities=(CAP_PROMOTION_REQUEST,), model_id="stub", prompt_version="eval")
    request = request_promotion(
        candidate["candidate_id"],
        evaluation["evaluation_id"],
        "Ready",
        candidate["evidence_refs"],
        store=store,
        context=request_ctx,
    )["request"]
    decision_ctx = human_context("human.good", capabilities=(CAP_PROMOTION_APPROVE,))
    record_human_decision(
        request["request_id"],
        store=store,
        approval_identity="ignored",
        approval_reason="ok",
        context=decision_ctx,
    )
    with pytest.raises(AuthorizationError):
        apply_promotion(
            request["request_id"],
            store=store,
            approval_identity="ignored",
            context=weak_ctx,
            canonical_port=LocalRecordingCanonicalPort(),
        )


def test_rejected_then_approved_fails(store: PopulationStore) -> None:
    candidate, evaluation = _candidate_and_eval(store, "reject")
    request_ctx = agent_context(EVALUATOR_IDENTITY, capabilities=(CAP_PROMOTION_REQUEST,), model_id="stub", prompt_version="eval")
    request = request_promotion(
        candidate["candidate_id"],
        evaluation["evaluation_id"],
        "Ready",
        candidate["evidence_refs"],
        store=store,
        context=request_ctx,
    )["request"]
    reject_ctx = human_context("human.good", capabilities=(CAP_PROMOTION_APPROVE,))
    record_human_decision(
        request["request_id"],
        store=store,
        approval_identity="ignored",
        approval_reason="not enough",
        decision="rejected",
        context=reject_ctx,
    )
    with pytest.raises(ForbiddenTransitionError):
        record_human_decision(
            request["request_id"],
            store=store,
            approval_identity="ignored",
            approval_reason="changed mind",
            decision="approved",
            context=reject_ctx,
        )
    apply_ctx = service_context("canonical.service", capabilities=(CAP_PROMOTION_APPLY,))
    with pytest.raises(ForbiddenTransitionError):
        apply_promotion(
            request["request_id"],
            store=store,
            approval_identity="ignored",
            context=apply_ctx,
            canonical_port=LocalRecordingCanonicalPort(),
        )
