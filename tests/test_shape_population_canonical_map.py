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
