from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.shape_population.canonical_port import FailClosedCanonicalPort, LocalRecordingCanonicalPort
from conversation_os.shape_population.contracts import IdempotencyConflictError
from conversation_os.shape_population.execution_context import CAP_PROMOTION_APPLY, CAP_PROMOTION_ROLLBACK, service_context
from conversation_os.shape_projection_reader import CANONICAL_SHAPE_PROFILE_ID


def _records() -> tuple[dict, dict, dict, dict]:
    request = {"request_id": "prom-1", "candidate_id": "cand-1", "evaluation_id": "eval-1"}
    candidate = {
        "candidate_id": "cand-1",
        "title": "Shape",
        "statement": "Claim",
        "boundary": "Boundary",
        "mechanism": "Mechanism",
        "dimensions": ["d"],
        "relations": [],
        "evidence_refs": [{"packet_id": "pkt-1", "block_id": "blk-1"}],
        "uncertainty": "low",
        "content_fingerprint": "cfp",
    }
    evaluation = {"evaluation_id": "eval-1", "content_fingerprint": "efp"}
    approval = {"approval_id": "appr-1", "decision": "approved", "human_principal_id": "human", "reason": "ok"}
    return request, candidate, evaluation, approval


def test_fail_closed_port_reports_missing_profile(tmp_path: Path) -> None:
    ctx = service_context("canonical.service", capabilities=(CAP_PROMOTION_APPLY,))
    port = FailClosedCanonicalPort(tmp_path)
    projection = port.prepare(*_records(), context=ctx)
    validation = port.validate(projection, context=ctx)
    receipt = port.apply(projection, idempotency_key="canon-1", context=ctx)

    assert projection["profile_id"] == CANONICAL_SHAPE_PROFILE_ID
    assert validation["valid"] is False
    assert receipt["applied"] is False
    assert receipt["status"] == "canonical_profile_unavailable"
    assert receipt["dependency_receipt"]["dependency"] == CANONICAL_SHAPE_PROFILE_ID


def test_local_recording_port_applies_once_and_rolls_back() -> None:
    apply_ctx = service_context("canonical.service", capabilities=(CAP_PROMOTION_APPLY,))
    rollback_ctx = service_context("canonical.service", capabilities=(CAP_PROMOTION_ROLLBACK,))
    port = LocalRecordingCanonicalPort()
    projection = port.prepare(*_records(), context=apply_ctx)
    assert port.validate(projection, context=apply_ctx)["valid"] is True

    first = port.apply(projection, idempotency_key="idem-1", context=apply_ctx)
    second = port.apply(projection, idempotency_key="idem-1", context=apply_ctx)

    assert first["applied"] is True
    assert second["replayed"] is True
    assert len(port.applies) == 1
    assert port.read_back(first["canonical_id"], context=apply_ctx)["projection"]["candidate_id"] == "cand-1"
    with pytest.raises(IdempotencyConflictError):
        port.apply({**projection, "title": "Changed"}, idempotency_key="idem-1", context=apply_ctx)

    rollback = port.rollback(
        first["canonical_id"],
        reason="audit rollback",
        idempotency_key="rb-1",
        context=rollback_ctx,
    )
    replay = port.rollback(
        first["canonical_id"],
        reason="audit rollback",
        idempotency_key="rb-1",
        context=rollback_ctx,
    )
    assert rollback["rolled_back"] is True
    assert replay["replayed"] is True
    assert port.read_back(first["canonical_id"], context=apply_ctx)["projection"]["rolled_back"] is True
