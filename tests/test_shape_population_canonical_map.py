from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.shape_population.canonical_port import (
    FailClosedCanonicalPort,
    FoundationCanonicalPort,
    map_population_candidate_to_proposal,
)
from conversation_os.shape_population.contracts import (
    CANONICAL_SHAPE_PROPOSAL_VERSION,
    IdempotencyConflictError,
    PopulationCandidate,
)
from conversation_os.shape_population.execution_context import (
    CAP_PROMOTION_APPLY,
    CAP_PROMOTION_ROLLBACK,
    service_context,
)
from conversation_os.shape_projection_reader import CANONICAL_SHAPE_PROFILE_ID


def _base_records(**candidate_extra):
    request = {
        "request_id": "prom-map-1",
        "candidate_id": "cand-map-1",
        "evaluation_id": "eval-map-1",
        "branch_id": "branch:map",
        "scope_id": "scope:map",
    }
    candidate = {
        "candidate_id": "cand-map-1",
        "title": "Route Confusion",
        "statement": "A receiver is delayed before reaching a goal.",
        "boundary": "Interpretation under bounded aperture",
        "mechanism": "Blocked transition delays the receiver",
        "dimensions": ["structural", "temporal"],
        "relations": [
            {
                "relation_id": "relation:receiver-goal",
                "relation_type": "delayed_before",
                "participant_refs": ["referent:receiver", "referent:goal"],
            },
            "label-only-neighbor",
        ],
        "evidence_refs": [{"packet_id": "pkt-1", "block_id": "blk-1"}],
        "counter_hypotheses": ["Maybe the delay is intentional pacing"],
        "uncertainty": "medium",
        "content_fingerprint": "cfp-map",
        "feedback": [{"loop_id": "fb-1", "polarity": "balancing"}],
        "composition": [{"part_ref": "referent:receiver", "host_ref": "referent:system"}],
        **candidate_extra,
    }
    evaluation = {
        "evaluation_id": "eval-map-1",
        "content_fingerprint": "efp-map",
        "anti_match_refs": [{"candidate_meta_id": "meta-maze-1", "penalty": 0.5}],
        "negative_evidence": [{"packet_id": "pkt-neg", "block_id": "blk-neg"}],
    }
    approval = {
        "approval_id": "appr-map-1",
        "decision": "approved",
        "human_principal_id": "human",
        "reason": "ok",
    }
    return request, candidate, evaluation, approval


def test_population_candidate_contract_round_trip():
    _, candidate, _, _ = _base_records()
    parsed = PopulationCandidate.from_mapping(candidate)
    assert parsed.candidate_id == "cand-map-1"
    assert parsed.schema_version
    assert "structural" in parsed.dimensions


def test_mapping_separates_facets_and_keeps_label_only_unresolved():
    request, candidate, evaluation, approval = _base_records()
    proposal = map_population_candidate_to_proposal(request, candidate, evaluation, approval)

    assert proposal.schema_version == CANONICAL_SHAPE_PROPOSAL_VERSION
    assert proposal.profile_id == CANONICAL_SHAPE_PROFILE_ID
    assert proposal.observed_referents
    assert any(item.get("merge_forbidden") for item in proposal.unresolved_referents)
    assert "label_only_relations_not_merged_into_shape_core" in proposal.semantic_loss_warnings
    assert "relation:receiver-goal" in proposal.closed_relation_refs
    assert "label-only-neighbor" not in proposal.closed_relation_refs
    assert proposal.shape_core["closed_complete"] is True
    assert proposal.shape_core["record_type"] == "shape_core"
    assert proposal.shape_view["record_type"] == "shape_view"
    assert proposal.shape_view["projection"]["nodes"]
    assert proposal.feedback
    assert proposal.composition
    assert proposal.anti_match_refs
    assert proposal.counter_hypotheses


def test_competing_view_stays_separate_flag():
    request, candidate, evaluation, approval = _base_records()
    evaluation = {**evaluation, "competing_view": True, "perspective": "critic"}
    proposal = map_population_candidate_to_proposal(request, candidate, evaluation, approval)
    assert proposal.competing_view is True
    assert proposal.perspective == "critic"
    assert "critic" in proposal.shape_view["id"]


def test_nested_quality_and_multidimensional_fixture():
    request, candidate, evaluation, approval = _base_records(
        dimensions=["structural", "valence", "scale"],
        scale="local_interaction",
        temporal_scope="episode",
    )
    proposal = map_population_candidate_to_proposal(request, candidate, evaluation, approval)
    assert proposal.dimensions == ["structural", "valence", "scale"]
    assert len(proposal.qualities) == 3
    assert proposal.scale == "local_interaction"
    assert proposal.temporal_scope == "episode"


def test_incomplete_closed_refs_reject_foundation_validate(tmp_path: Path):
    request, candidate, evaluation, approval = _base_records()
    candidate = {**candidate, "evidence_refs": [{"note": "missing ids"}], "relations": ["only-label"]}
    ctx = service_context("canonical.service", capabilities=(CAP_PROMOTION_APPLY,))
    port = FoundationCanonicalPort(tmp_path)
    projection = port.prepare(request, candidate, evaluation, approval, context=ctx)
    validation = port.validate(projection, context=ctx)
    assert validation["valid"] is False
    assert "shape_core requires closed validated relation/evidence refs" in validation["errors"]


def test_foundation_port_applies_with_owner_receipt_and_replay(tmp_path: Path):
    request, candidate, evaluation, approval = _base_records()
    apply_ctx = service_context("canonical.service", capabilities=(CAP_PROMOTION_APPLY,))
    rollback_ctx = service_context("canonical.service", capabilities=(CAP_PROMOTION_ROLLBACK,))
    port = FoundationCanonicalPort(tmp_path)

    projection = port.prepare(request, candidate, evaluation, approval, context=apply_ctx)
    assert projection["profile_status"]["available"] is True
    assert projection["profile_id"] == CANONICAL_SHAPE_PROFILE_ID
    validation = port.validate(projection, context=apply_ctx)
    assert validation["valid"] is True

    first = port.apply(projection, idempotency_key="map-idem-1", context=apply_ctx)
    second = port.apply(projection, idempotency_key="map-idem-1", context=apply_ctx)
    assert first["applied"] is True
    assert first["owner"] == "FoundationCanonicalPort"
    assert first["owner_version"] == 1
    assert second["replayed"] is True
    assert first["shape_core_id"] == projection["shape_core"]["id"]

    read = port.read_back(first["canonical_id"], context=apply_ctx)
    assert read["status"] == "available"
    assert read["projection"]["candidate_id"] == "cand-map-1"

    with pytest.raises(IdempotencyConflictError):
        port.apply({**projection, "title": "Changed"}, idempotency_key="map-idem-1", context=apply_ctx)

    rollback = port.rollback(
        first["canonical_id"],
        reason="source withdrawn",
        idempotency_key="map-rb-1",
        context=rollback_ctx,
    )
    replay = port.rollback(
        first["canonical_id"],
        reason="source withdrawn",
        idempotency_key="map-rb-1",
        context=rollback_ctx,
    )
    assert rollback["rolled_back"] is True
    assert rollback["stale"] is True
    assert replay["replayed"] is True
    stale = port.read_back(first["canonical_id"], context=apply_ctx)
    assert stale["status"] == "stale"


def test_fail_closed_still_blocks_apply(tmp_path: Path):
    request, candidate, evaluation, approval = _base_records()
    ctx = service_context("canonical.service", capabilities=(CAP_PROMOTION_APPLY,))
    port = FailClosedCanonicalPort(tmp_path)
    projection = port.prepare(request, candidate, evaluation, approval, context=ctx)
    validation = port.validate(projection, context=ctx)
    receipt = port.apply(projection, idempotency_key="fail-1", context=ctx)
    assert validation["valid"] is False
    assert receipt["applied"] is False
    assert receipt["status"] == "canonical_profile_unavailable"


def test_post_ingest_hook_and_operator_controls(tmp_path: Path):
    from conversation_os.shape_population.orchestrator import build_post_ingest_hook
    from conversation_os.shape_population.storage import ShapePopulationStore
    from conversation_os.vault_ingest import ingest_text_content

    store = ShapePopulationStore(tmp_path)
    hook = build_post_ingest_hook(tmp_path, store=store)
    result = ingest_text_content(
        tmp_path,
        title="Live hook source",
        content="A mechanism appears when boundary B holds.\n",
        source_ref="manual://live-hook-1",
        post_ingest_hooks=[hook],
    )
    assert result["source_id"]
    assert result["post_ingest"]["receipts"][0]["ok"] is True
    job = result["post_ingest"]["receipts"][0]["result"]
    assert job["state"] == "queued"

    store.pause_worker(reason="test_pause")
    assert store.claim_job(lease_owner="worker-a") is None
    store.resume_worker(reason="test_resume")
    claimed = store.claim_job(lease_owner="worker-a")
    assert claimed is not None
    assert claimed["job_id"] == job["job_id"]
    cancelled = store.cancel_job(claimed["job_id"], reason="test_cancel")
    assert cancelled["state"] == "cancelled"
    retried = store.retry_job(claimed["job_id"], reason="test_retry")
    assert retried["state"] == "queued"


def test_apply_approved_promotion_live_produces_owner_receipt(tmp_path: Path):
    from conversation_os.shape_population.candidate_submission import submit_candidate
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
    from conversation_os.shape_population.orchestrator import apply_approved_promotion_live
    from conversation_os.shape_population.promotion import record_human_decision, request_promotion
    from conversation_os.shape_population.storage import ShapePopulationStore

    store = ShapePopulationStore(tmp_path)
    normalized = normalize_source(
        {"content": "A mechanism appears when boundary B holds.\n", "modality": "plain_text"},
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
            "title": "Boundary mechanism",
            "statement": "A mechanism appears when boundary B holds.",
            "boundary": "boundary B",
            "mechanism": "appearance under B",
            "dimensions": ["causality"],
            "relations": [
                {
                    "relation_id": "relation:mechanism-boundary",
                    "relation_type": "appears_when",
                    "participant_refs": ["referent:mechanism", "referent:boundary"],
                }
            ],
            "evidence_refs": refs,
            "counter_hypotheses": ["coincidence"],
            "uncertainty": "low",
            "recommended_disposition": "proposed",
            "idempotency_key": "live-cand-1",
        },
        store=store,
        context=agent_context(
            PROPOSER_IDENTITY,
            capabilities={"shape.candidate.submit"},
            run_id="live-1",
            model_id="m",
            prompt_version="p",
        ),
    )["candidate"]
    evaluation = submit_evaluation(
        {
            "candidate_id": cand["candidate_id"],
            "disposition": "recommended",
            "critique": "ok",
            "evidence_refs": refs,
            "uncertainty": "low",
            "relationship_findings": [],
            "idempotency_key": "live-eval-1",
        },
        store=store,
        context=agent_context(
            CRITIC_IDENTITY,
            capabilities={"shape.evaluation.submit", "shape.comparison.read"},
            run_id="live-2",
            model_id="m",
            prompt_version="p",
        ),
    )["evaluation"]
    requested = request_promotion(
        cand["candidate_id"],
        evaluation["evaluation_id"],
        "ready for live apply",
        refs,
        store=store,
        context=agent_context(
            EVALUATOR_IDENTITY,
            capabilities={"shape.promotion.request"},
            run_id="live-3",
            model_id="m",
            prompt_version="p",
        ),
        idempotency_key="live-prom-1",
    )
    request_id = requested["request"]["request_id"]
    record_human_decision(
        request_id,
        store=store,
        approval_reason="approved for live foundation apply",
        decision="approved",
        context=human_context(HUMAN_APPROVER_ROLE, capabilities={"shape.promotion.approve"}),
    )
    applied = apply_approved_promotion_live(
        request_id,
        store=store,
        context=human_context(
            "shape.canonical_authority",
            capabilities={"shape.promotion.apply", "shape.promotion.approve"},
        ),
        idempotency_key="live-apply-1",
    )
    assert applied["candidate"]["status"] == "canonical"
    assert applied["canonical_receipt"]["applied"] is True
    assert applied["canonical_receipt"]["owner"] == "FoundationCanonicalPort"
    assert applied["projection"]["shape_core"]["closed_complete"] is True
