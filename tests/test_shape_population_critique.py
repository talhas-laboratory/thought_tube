"""Tests for critique comparison and evaluation tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.shape_population.candidate_submission import submit_candidate
from conversation_os.shape_population.contracts import AuthorizationError, ValidationError
from conversation_os.shape_population.critique import critic_tool_surface, find_comparison_candidates, submit_evaluation
from conversation_os.shape_population.evidence import build_evidence_packet
from conversation_os.shape_population.execution_context import (
    CAP_CANDIDATE_SUBMIT,
    CAP_COMPARISON_READ,
    CAP_EVALUATION_SUBMIT,
    CAP_EVIDENCE_INQUIRE,
    agent_context,
    human_context,
)
from conversation_os.shape_population.identities import CRITIC_IDENTITY, PROPOSER_IDENTITY, SYNTHESIZER_IDENTITY
from conversation_os.shape_population.normalization import normalize_source
from conversation_os.shape_population.promotion import apply_promotion
from conversation_os.shape_population.storage import PopulationStore

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "shape_population" / "critique"


def _inq_context():
    return agent_context(PROPOSER_IDENTITY, capabilities=(CAP_EVIDENCE_INQUIRE,))


def _prop_context(run_id: str):
    return agent_context(
        PROPOSER_IDENTITY,
        capabilities=(CAP_CANDIDATE_SUBMIT,),
        run_id=run_id,
        model_id="stub",
        prompt_version="p1",
    )


def _critic_context(run_id: str, identity: str = CRITIC_IDENTITY):
    return agent_context(
        identity,
        capabilities=(CAP_EVALUATION_SUBMIT, CAP_COMPARISON_READ),
        run_id=run_id,
        model_id="stub",
        prompt_version="c1",
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


def _submit(store: PopulationStore, text: str, key: str, title: str) -> dict:
    normalized = normalize_source({"content": text, "modality": "plain_text"}, store=store)
    packet = build_evidence_packet(
        {
            "segment_ids": [seg.segment_id for seg in normalized.segments],
            "evidence_inquiry": {"question": "shape?", "requested_by": PROPOSER_IDENTITY},
        },
        store=store,
        context=_inq_context(),
    )
    refs = _refs(packet)
    return submit_candidate(
        {
            "packet_id": packet.packet_id,
            "title": title,
            "statement": text.strip(),
            "boundary": "scoped boundary",
            "mechanism": "m",
            "dimensions": ["d"],
            "evidence_refs": refs,
            "counter_hypotheses": ["alt"],
            "uncertainty": "low",
            "recommended_disposition": "proposed",
            "idempotency_key": key,
        },
        store=store,
        context=_prop_context(f"run-{key}"),
    )["candidate"]


@pytest.fixture()
def store(tmp_path: Path) -> PopulationStore:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    return PopulationStore(tmp_path)


def test_missing_candidate_fails(store: PopulationStore) -> None:
    with pytest.raises(ValidationError):
        find_comparison_candidates(
            "missing",
            store=store,
            context=agent_context(CRITIC_IDENTITY, capabilities=(CAP_COMPARISON_READ,)),
        )


def test_comparison_neighbors(store: PopulationStore) -> None:
    a = _submit(store, "Feedback loop amplifies signal.\n", "a", "Feedback loop")
    b = _submit(store, "Feedback loop amplifies noise.\n", "b", "Feedback loop noise")
    _submit(store, "Completely unrelated astronomy claim.\n", "c", "Astronomy")
    result = find_comparison_candidates(
        a["candidate_id"],
        store=store,
        limit=5,
        context=agent_context(CRITIC_IDENTITY, capabilities=(CAP_COMPARISON_READ,)),
    )
    assert "authoritative_equivalence" not in result
    assert len(result["neighbors"]) >= 1
    assert store.get_comparison_set(result["comparison_set_version"]) is not None
    for neighbor in result["neighbors"]:
        assert neighbor["relation_hint"] in {
            "possible_same",
            "possibly_adjacent",
            "possibly_conflicting",
            "possibly_distinct",
        }
        assert "authoritative_equivalence" not in neighbor


def test_distinct_identity_and_no_canonical_tool(store: PopulationStore) -> None:
    surface = critic_tool_surface()
    assert set(surface["tools"]) == {"find_comparison_candidates", "submit_evaluation"}
    assert surface["forbidden"]["promotion"] is True
    candidate = _submit(store, "Claim with evidence.\n", "crit-1", "Claim")
    with pytest.raises((AuthorizationError, TypeError)):
        apply_promotion(
            "nope",
            store=store,
            context=agent_context(CRITIC_IDENTITY, capabilities=()),
        )
    result = submit_evaluation(
        {
            "candidate_id": candidate["candidate_id"],
            "disposition": "under_review",
            "critique": "Needs tighter boundary.",
            "evidence_refs": candidate["evidence_refs"],
            "uncertainty": "medium",
            "relationship_findings": [{"relation": "possibly_adjacent", "other_candidate_id": "x"}],
            "idempotency_key": "eval-1",
        },
        store=store,
        context=_critic_context("critic-run-1"),
    )
    assert result["evaluation"]["evaluation_id"].startswith("eval-")
    assert result["candidate"]["status"] == "under_review"


def test_continuity_boundary_survives_unless_revised(store: PopulationStore) -> None:
    candidate = _submit(store, "Stable boundary text.\n", "cont-1", "Stable")
    boundary = candidate["boundary"]
    submit_evaluation(
        {
            "candidate_id": candidate["candidate_id"],
            "disposition": "under_review",
            "critique": "No boundary change.",
            "evidence_refs": candidate["evidence_refs"],
            "uncertainty": "low",
            "idempotency_key": "eval-cont-1",
        },
        store=store,
        context=_critic_context("critic-run-2"),
    )
    assert store.get_candidate(candidate["candidate_id"])["boundary"] == boundary
    submit_evaluation(
        {
            "candidate_id": candidate["candidate_id"],
            "disposition": "needs_evidence",
            "critique": "Narrow the boundary.",
            "evidence_refs": candidate["evidence_refs"],
            "uncertainty": "high",
            "revisions": ["boundary: revised explicit boundary"],
            "idempotency_key": "eval-cont-2",
        },
        store=store,
        context=_critic_context("synth-run-1", identity=SYNTHESIZER_IDENTITY),
    )
    assert store.get_candidate(candidate["candidate_id"])["boundary"] == "revised explicit boundary"


def test_false_merge_split_safe_ambiguous(store: PopulationStore) -> None:
    left = _submit(store, "Market pull drives adoption.\n", "fm-1", "Market pull")
    right = _submit(store, "Market pull is coincidental with adoption.\n", "fm-2", "Market coincidence")
    comparison = find_comparison_candidates(
        left["candidate_id"],
        store=store,
        context=agent_context(CRITIC_IDENTITY, capabilities=(CAP_COMPARISON_READ,)),
    )
    submit_evaluation(
        {
            "candidate_id": left["candidate_id"],
            "disposition": "under_review",
            "critique": "Possibly adjacent, not the same; avoid false merge.",
            "evidence_refs": left["evidence_refs"],
            "uncertainty": "high",
            "relationship_findings": [
                {"relation": "possibly_adjacent", "other_candidate_id": right["candidate_id"]}
            ],
            "idempotency_key": "eval-fm",
        },
        store=store,
        context=_critic_context("critic-run-fm"),
    )
    assert store.get_candidate(left["candidate_id"])["candidate_id"] != right["candidate_id"]
    assert "authoritative_equivalence" not in comparison
