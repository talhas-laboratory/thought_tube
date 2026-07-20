"""Tests for proposer submit_candidate tool."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conversation_os.shape_population.candidate_submission import proposer_tool_surface, submit_candidate
from conversation_os.shape_population.contracts import AuthorizationError, ValidationError
from conversation_os.shape_population.evidence import build_evidence_packet
from conversation_os.shape_population.execution_context import ExecutionContext
from conversation_os.shape_population.identities import CRITIC_IDENTITY, PROPOSER_IDENTITY
from conversation_os.shape_population.normalization import normalize_source
from conversation_os.shape_population.storage import PopulationStore

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "shape_population" / "interpretation"


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


def _seed(store: PopulationStore, text: str = "Mechanism A causes outcome B within boundary C.\n") -> dict:
    normalized = normalize_source({"content": text, "modality": "plain_text"}, store=store)
    packet = build_evidence_packet(
        {
            "segment_ids": [seg.segment_id for seg in normalized.segments],
            "evidence_inquiry": {
                "question": "What shape is here?",
                "requested_by": PROPOSER_IDENTITY,
            },
        },
        store=store,
        context=_context(),
    )
    refs = _refs(packet)
    return {"packet": packet, "refs": refs}


def _payload(packet_id: str, refs: list, **overrides) -> dict:
    body = {
        "packet_id": packet_id,
        "title": "Causal mechanism A",
        "statement": "A produces B inside boundary C.",
        "boundary": "Applies only when C holds.",
        "mechanism": "A -> B",
        "dimensions": ["causality"],
        "evidence_refs": refs,
        "counter_hypotheses": ["B may be independent of A"],
        "uncertainty": "medium",
        "recommended_disposition": "proposed",
        "agent_identity": PROPOSER_IDENTITY,
        "model_version": "stub-1",
        "prompt_version": "prop-1",
        "tool_contract_version": "1.0.0",
        "run_id": "run-proposer-1",
        "idempotency_key": "cand-key-1",
    }
    body.update(overrides)
    return body


@pytest.fixture()
def store(tmp_path: Path) -> PopulationStore:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    return PopulationStore(tmp_path)


def test_only_submit_candidate_exposed(store: PopulationStore) -> None:
    surface = proposer_tool_surface()
    assert surface["tools"] == ["submit_candidate"]
    assert surface["forbidden"]["promotion"] is True


def test_submit_assigns_immutable_id_and_rejects_canonical(store: PopulationStore) -> None:
    seeded = _seed(store)
    result = submit_candidate(_payload(seeded["packet"].packet_id, seeded["refs"]), store=store)
    candidate = result["candidate"]
    assert candidate["candidate_id"].startswith("cand-")
    assert candidate["status"] == "proposed"
    assert result["receipt"]["operation"] == "submit_candidate"
    with pytest.raises(ValidationError):
        submit_candidate(
            _payload(seeded["packet"].packet_id, seeded["refs"], status="canonical", idempotency_key="x2"),
            store=store,
        )
    with pytest.raises(ValidationError):
        submit_candidate(
            _payload(
                seeded["packet"].packet_id,
                seeded["refs"],
                candidate_id="model-assigned",
                idempotency_key="x3",
            ),
            store=store,
        )


def test_invalid_schema_and_missing_evidence_rejected(store: PopulationStore) -> None:
    seeded = _seed(store)
    with pytest.raises(ValidationError):
        submit_candidate({"packet_id": seeded["packet"].packet_id}, store=store)
    with pytest.raises(ValidationError):
        submit_candidate(
            _payload(seeded["packet"].packet_id, [{"segment_id": "missing"}], idempotency_key="bad-ref"),
            store=store,
        )


def test_wrong_identity_forbidden(store: PopulationStore) -> None:
    seeded = _seed(store)
    with pytest.raises((AuthorizationError, ValidationError)):
        submit_candidate(
            _payload(
                seeded["packet"].packet_id,
                seeded["refs"],
                agent_identity=CRITIC_IDENTITY,
                idempotency_key="wrong-id",
            ),
            store=store,
        )


def test_idempotent_replay_and_retry_cap(store: PopulationStore) -> None:
    seeded = _seed(store)
    payload = _payload(seeded["packet"].packet_id, seeded["refs"])
    first = submit_candidate(payload, store=store)
    second = submit_candidate(payload, store=store)
    assert second["replayed"] is True
    assert second["candidate"]["candidate_id"] == first["candidate"]["candidate_id"]
    with pytest.raises(ValidationError):
        submit_candidate({**payload, "idempotency_key": "retry-cap"}, store=store, retry_count=99)


def test_golden_semantic_fields_present(store: PopulationStore) -> None:
    """Golden case: grounded packet requires evidence/counter-hypothesis/uncertainty."""
    seeded = _seed(store, "Grounded evidence about feedback loops.\n")
    (FIXTURE_DIR / "grounded.json").write_text(
        json.dumps(_payload(seeded["packet"].packet_id, seeded["refs"]), indent=2) + "\n",
        encoding="utf-8",
    )
    result = submit_candidate(_payload(seeded["packet"].packet_id, seeded["refs"], idempotency_key="golden"), store=store)
    candidate = result["candidate"]
    assert candidate["evidence_refs"]
    assert candidate["counter_hypotheses"]
    assert candidate["uncertainty"]
    # Evaluator rubric placeholder — intelligence judges support; deterministic path only checks presence.
    rubric = {
        "grounding": "fields_present",
        "uncertainty_calibration": candidate["uncertainty"],
        "non_deterministic_quality": True,
    }
    assert rubric["grounding"] == "fields_present"
