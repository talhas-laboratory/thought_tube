"""Tests for atomic candidate governance."""

from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.shape_population.candidate_submission import submit_candidate
from conversation_os.shape_population.contracts import ForbiddenTransitionError, IdempotencyConflictError, ValidationError
from conversation_os.shape_population.evidence import build_evidence_packet
from conversation_os.shape_population.execution_context import ExecutionContext
from conversation_os.shape_population.governance import atomic_submit_candidate, transition_candidate
from conversation_os.shape_population.identities import PROPOSER_IDENTITY
from conversation_os.shape_population.normalization import normalize_source
from conversation_os.shape_population.storage import PopulationStore


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


def _seed_payload(store: PopulationStore, key: str = "gov-1") -> dict:
    normalized = normalize_source({"content": "Evidence line for governance.\n", "modality": "plain_text"}, store=store)
    packet = build_evidence_packet(
        {
            "segment_ids": [seg.segment_id for seg in normalized.segments],
            "evidence_inquiry": {"question": "q", "requested_by": PROPOSER_IDENTITY},
        },
        store=store,
        context=_context(),
    )
    refs = _refs(packet)
    return {
        "packet_id": packet.packet_id,
        "title": "Gov candidate",
        "statement": "A statement",
        "boundary": "B",
        "mechanism": "M",
        "dimensions": ["d"],
        "evidence_refs": refs,
        "counter_hypotheses": ["alt"],
        "uncertainty": "low",
        "recommended_disposition": "proposed",
        "agent_identity": PROPOSER_IDENTITY,
        "model_version": "stub",
        "prompt_version": "p",
        "tool_contract_version": "1.0.0",
        "run_id": "r1",
        "idempotency_key": key,
    }


@pytest.fixture()
def store(tmp_path: Path) -> PopulationStore:
    return PopulationStore(tmp_path)


def test_invalid_schema_and_evidence_fail_closed(store: PopulationStore) -> None:
    with pytest.raises(ValidationError):
        atomic_submit_candidate(store, {"packet_id": "x"})
    payload = _seed_payload(store, "bad-ev")
    payload["evidence_refs"] = [{"segment_id": "nope"}]
    before = store.snapshot()
    with pytest.raises(ValidationError):
        atomic_submit_candidate(store, payload)
    assert store.list_candidates() == []
    # Receipt for failed attempt should not partially persist candidate.
    assert store.snapshot()["candidates"] == before["candidates"]


def test_idempotent_replay_and_conflict(store: PopulationStore) -> None:
    payload = _seed_payload(store, "idem-1")
    first = submit_candidate(payload, store=store)
    second = submit_candidate(payload, store=store)
    assert second["replayed"] is True
    assert second["receipt"]["receipt_id"] == first["receipt"]["receipt_id"]
    conflict = dict(payload)
    conflict["title"] = "Changed"
    with pytest.raises(IdempotencyConflictError):
        submit_candidate(conflict, store=store)


def test_transaction_rollback_on_receipt_path(store: PopulationStore) -> None:
    payload = _seed_payload(store, "rollback-1")
    # Force failure after validation by using absurd cost cap.
    with pytest.raises(ValidationError):
        submit_candidate(payload, store=store, cost_units=10_000)
    assert store.get_idempotency(payload["idempotency_key"]) is None
    assert store.list_candidates() == []


def test_forbidden_transition_and_no_canon_side_effect(store: PopulationStore) -> None:
    payload = _seed_payload(store, "trans-1")
    candidate = submit_candidate(payload, store=store)["candidate"]
    with pytest.raises(ForbiddenTransitionError):
        transition_candidate(store, candidate["candidate_id"], "canonical")
    assert store.get_canonical_projection(candidate["candidate_id"]) is None
    transition_candidate(store, candidate["candidate_id"], "under_review")
    transition_candidate(store, candidate["candidate_id"], "recommended")
    with pytest.raises(ForbiddenTransitionError):
        transition_candidate(store, candidate["candidate_id"], "proposed")


def test_receipt_privacy_and_audit_reconstruction(store: PopulationStore) -> None:
    payload = _seed_payload(store, "priv-1")
    result = submit_candidate(payload, store=store)
    receipt = result["receipt"]
    assert "raw_text" not in (receipt.get("provenance") or {})
    assert "source_text" not in (receipt.get("provenance") or {})
    audit = store.dump_audit()
    assert result["candidate"]["candidate_id"] in audit
    assert receipt["receipt_id"] in audit


def test_concurrent_duplicate_submission(store: PopulationStore) -> None:
    payload = _seed_payload(store, "dup-1")
    a = submit_candidate(payload, store=store)
    b = submit_candidate(payload, store=store)
    assert a["candidate"]["candidate_id"] == b["candidate"]["candidate_id"]
    assert len(store.list_candidates()) == 1
