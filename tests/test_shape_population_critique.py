"""Tests for critique comparison and evaluation tools."""

from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.shape_population.candidate_submission import submit_candidate
from conversation_os.shape_population.contracts import AuthorizationError, ValidationError
from conversation_os.shape_population.critique import critic_tool_surface, find_comparison_candidates, submit_evaluation
from conversation_os.shape_population.evidence import build_evidence_packet
from conversation_os.shape_population.identities import CRITIC_IDENTITY, PROPOSER_IDENTITY, SYNTHESIZER_IDENTITY
from conversation_os.shape_population.normalization import normalize_source
from conversation_os.shape_population.promotion import apply_promotion
from conversation_os.shape_population.storage import PopulationStore

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "shape_population" / "critique"


def _submit(store: PopulationStore, text: str, key: str, title: str) -> dict:
    normalized = normalize_source({"content": text, "modality": "plain_text"}, store=store)
    packet = build_evidence_packet(
        {
            "segment_ids": [seg.segment_id for seg in normalized.segments],
            "evidence_inquiry": {"question": "shape?", "requested_by": PROPOSER_IDENTITY},
        },
        store=store,
    )
    refs = [
        {
            "source_id": seg.source_id,
            "segment_id": seg.segment_id,
            "char_start": seg.char_start,
            "char_end": seg.char_end,
            "text_sha256": seg.text_sha256,
        }
        for seg in normalized.segments
    ]
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
            "agent_identity": PROPOSER_IDENTITY,
            "model_version": "stub",
            "prompt_version": "p1",
            "tool_contract_version": "1.0.0",
            "run_id": f"run-{key}",
            "idempotency_key": key,
        },
        store=store,
    )["candidate"]


@pytest.fixture()
def store(tmp_path: Path) -> PopulationStore:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    return PopulationStore(tmp_path)


def test_comparison_precondition_and_vocabulary(store: PopulationStore) -> None:
    with pytest.raises(ValidationError):
        find_comparison_candidates("missing", store=store)
    a = _submit(store, "Feedback loop amplifies signal.\n", "a", "Feedback loop")
    b = _submit(store, "Feedback loop amplifies noise.\n", "b", "Feedback loop noise")
    _submit(store, "Completely unrelated astronomy claim.\n", "c", "Astronomy")
    result = find_comparison_candidates(a["candidate_id"], store=store, limit=5)
    assert result["authoritative_equivalence"] is False
    assert len(result["neighbors"]) >= 1
    for neighbor in result["neighbors"]:
        assert neighbor["relation_hint"] in {
            "possible_same",
            "possibly_adjacent",
            "possibly_conflicting",
            "possibly_distinct",
        }
        assert neighbor["authoritative_equivalence"] is False


def test_distinct_identity_and_no_canonical_tool(store: PopulationStore) -> None:
    surface = critic_tool_surface()
    assert set(surface["tools"]) == {"find_comparison_candidates", "submit_evaluation"}
    assert surface["forbidden"]["promotion"] is True
    candidate = _submit(store, "Claim with evidence.\n", "crit-1", "Claim")
    with pytest.raises(AuthorizationError):
        apply_promotion("nope", store=store, approval_identity=CRITIC_IDENTITY, approval_reason="no")
    result = submit_evaluation(
        {
            "candidate_id": candidate["candidate_id"],
            "disposition": "under_review",
            "critique": "Needs tighter boundary.",
            "evidence_refs": candidate["evidence_refs"],
            "uncertainty": "medium",
            "agent_identity": CRITIC_IDENTITY,
            "model_version": "stub",
            "prompt_version": "c1",
            "tool_contract_version": "1.0.0",
            "run_id": "critic-run-1",
            "relationship_findings": [{"relation": "possibly_adjacent", "other_candidate_id": "x"}],
            "idempotency_key": "eval-1",
        },
        store=store,
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
            "agent_identity": CRITIC_IDENTITY,
            "model_version": "stub",
            "prompt_version": "c1",
            "tool_contract_version": "1.0.0",
            "run_id": "critic-run-2",
            "idempotency_key": "eval-cont-1",
        },
        store=store,
    )
    assert store.get_candidate(candidate["candidate_id"])["boundary"] == boundary
    submit_evaluation(
        {
            "candidate_id": candidate["candidate_id"],
            "disposition": "needs_evidence",
            "critique": "Narrow the boundary.",
            "evidence_refs": candidate["evidence_refs"],
            "uncertainty": "high",
            "agent_identity": SYNTHESIZER_IDENTITY,
            "model_version": "stub",
            "prompt_version": "s1",
            "tool_contract_version": "1.0.0",
            "run_id": "synth-run-1",
            "revisions": ["boundary: revised explicit boundary"],
            "idempotency_key": "eval-cont-2",
        },
        store=store,
    )
    assert store.get_candidate(candidate["candidate_id"])["boundary"] == "revised explicit boundary"


def test_false_merge_split_safe_ambiguous(store: PopulationStore) -> None:
    left = _submit(store, "Market pull drives adoption.\n", "fm-1", "Market pull")
    right = _submit(store, "Market pull is coincidental with adoption.\n", "fm-2", "Market coincidence")
    comparison = find_comparison_candidates(left["candidate_id"], store=store)
    # Even if similar, evaluation may keep them distinct — similarity never merges.
    submit_evaluation(
        {
            "candidate_id": left["candidate_id"],
            "disposition": "under_review",
            "critique": "Possibly adjacent, not the same; avoid false merge.",
            "evidence_refs": left["evidence_refs"],
            "uncertainty": "high",
            "agent_identity": CRITIC_IDENTITY,
            "model_version": "stub",
            "prompt_version": "c1",
            "tool_contract_version": "1.0.0",
            "run_id": "critic-run-fm",
            "relationship_findings": [
                {"relation": "possibly_adjacent", "other_candidate_id": right["candidate_id"]}
            ],
            "idempotency_key": "eval-fm",
        },
        store=store,
    )
    assert store.get_candidate(left["candidate_id"])["candidate_id"] != right["candidate_id"]
    assert comparison["authoritative_equivalence"] is False
