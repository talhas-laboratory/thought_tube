"""Tests for proposer submit_candidate tool."""

from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.shape_population.candidate_submission import proposer_tool_surface, submit_candidate
from conversation_os.shape_population.contracts import AuthorizationError, ValidationError
from conversation_os.shape_population.evidence import build_evidence_packet
from conversation_os.shape_population.execution_context import CAP_CANDIDATE_SUBMIT, CAP_EVIDENCE_INQUIRE, agent_context
from conversation_os.shape_population.identities import CRITIC_IDENTITY, PROPOSER_IDENTITY
from conversation_os.shape_population.normalization import normalize_source
from conversation_os.shape_population.storage import PopulationStore

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "shape_population" / "interpretation"


def _inq_context():
    return agent_context(PROPOSER_IDENTITY, capabilities=(CAP_EVIDENCE_INQUIRE,))


def _submit_context(*, run_id: str = "run-proposer-1"):
    return agent_context(
        PROPOSER_IDENTITY,
        capabilities=(CAP_CANDIDATE_SUBMIT,),
        run_id=run_id,
        model_id="stub-1",
        prompt_version="prop-1",
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
        context=_inq_context(),
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
    ctx = _submit_context()
    result = submit_candidate(_payload(seeded["packet"].packet_id, seeded["refs"]), store=store, context=ctx)
    candidate = result["candidate"]
    assert candidate["candidate_id"].startswith("cand-")
    assert candidate["status"] == "proposed"
    assert result["receipt"]["operation"] == "submit_candidate"
    with pytest.raises(ValidationError):
        submit_candidate(
            _payload(seeded["packet"].packet_id, seeded["refs"], status="canonical", idempotency_key="x2"),
            store=store,
            context=_submit_context(run_id="run-x2"),
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
            context=_submit_context(run_id="run-x3"),
        )


def test_invalid_schema_and_missing_evidence_rejected(store: PopulationStore) -> None:
    seeded = _seed(store)
    with pytest.raises(ValidationError):
        submit_candidate({"packet_id": seeded["packet"].packet_id}, store=store, context=_submit_context(run_id="bad-1"))
    with pytest.raises(ValidationError):
        submit_candidate(
            _payload(seeded["packet"].packet_id, [{"segment_id": "missing"}], idempotency_key="bad-ref"),
            store=store,
            context=_submit_context(run_id="bad-2"),
        )


def test_model_payload_cannot_select_identity(store: PopulationStore) -> None:
    seeded = _seed(store)
    # Spoofed identity in payload is ignored; authenticated context wins.
    result = submit_candidate(
        _payload(
            seeded["packet"].packet_id,
            seeded["refs"],
            agent_identity=CRITIC_IDENTITY,
            idempotency_key="wrong-id",
        ),
        store=store,
        context=_submit_context(run_id="trusted"),
    )
    assert result["candidate"]["agent_identity"] == PROPOSER_IDENTITY


def test_missing_context_rejected(store: PopulationStore) -> None:
    seeded = _seed(store)
    with pytest.raises(TypeError):
        submit_candidate(_payload(seeded["packet"].packet_id, seeded["refs"]), store=store)  # type: ignore[call-arg]


def test_idempotent_replay_and_retry_cap(store: PopulationStore) -> None:
    seeded = _seed(store)
    payload = _payload(seeded["packet"].packet_id, seeded["refs"])
    ctx = _submit_context()
    first = submit_candidate(payload, store=store, context=ctx)
    second = submit_candidate(payload, store=store, context=ctx)
    assert second["replayed"] is True
    assert second["candidate"]["candidate_id"] == first["candidate"]["candidate_id"]
    with pytest.raises(ValidationError):
        submit_candidate(
            {**payload, "idempotency_key": "retry-cap"},
            store=store,
            context=_submit_context(run_id="retry"),
            retry_count=99,
        )


def test_golden_semantic_fields_present(store: PopulationStore) -> None:
    """Golden case: grounded packet requires evidence/counter-hypothesis/uncertainty."""
    seeded = _seed(store, "Grounded evidence about feedback loops.\n")
    result = submit_candidate(
        _payload(seeded["packet"].packet_id, seeded["refs"], idempotency_key="golden"),
        store=store,
        context=_submit_context(run_id="golden"),
    )
    candidate = result["candidate"]
    assert candidate["evidence_refs"]
    assert candidate["counter_hypotheses"]
    assert candidate["uncertainty"]
