from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.shape_population.candidate_submission import submit_candidate
from conversation_os.shape_population.comparison import find_neighbors
from conversation_os.shape_population.contracts import AuthorizationError
from conversation_os.shape_population.critique import find_comparison_candidates
from conversation_os.shape_population.evidence import build_evidence_packet
from conversation_os.shape_population.execution_context import CAP_CANDIDATE_SUBMIT, CAP_COMPARISON_READ, CAP_EVIDENCE_INQUIRE, agent_context
from conversation_os.shape_population.identities import CRITIC_IDENTITY, PROPOSER_IDENTITY
from conversation_os.shape_population.normalization import normalize_source
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


def _candidate(store: PopulationStore, text: str, key: str, title: str) -> dict:
    ctx = agent_context(
        PROPOSER_IDENTITY,
        capabilities=(CAP_EVIDENCE_INQUIRE, CAP_CANDIDATE_SUBMIT),
        run_id=f"run-{key}",
        model_id="stub-model",
        prompt_version="prop-test",
    )
    normalized = normalize_source({"content": text, "modality": "plain_text"}, store=store)
    packet = build_evidence_packet(
        {
            "segment_ids": [segment.segment_id for segment in normalized.segments],
            "evidence_inquiry": {"question": "shape?"},
        },
        store=store,
        context=ctx,
    )
    return submit_candidate(
        {
            "packet_id": packet.packet_id,
            "title": title,
            "statement": text.strip(),
            "boundary": "bounded",
            "mechanism": "mechanism",
            "dimensions": ["feedback"],
            "evidence_refs": _refs(packet),
            "counter_hypotheses": ["alternative"],
            "uncertainty": "medium",
            "recommended_disposition": "proposed",
            "idempotency_key": key,
        },
        store=store,
        context=ctx,
    )["candidate"]


@pytest.fixture()
def store(tmp_path: Path) -> PopulationStore:
    return PopulationStore(tmp_path)


def test_comparison_requires_capability_when_context_is_supplied(store: PopulationStore) -> None:
    candidate = _candidate(store, "Feedback amplifies signal.\n", "cmp-a", "Feedback")
    ctx = agent_context(CRITIC_IDENTITY, capabilities=(), model_id="stub", prompt_version="cmp")
    with pytest.raises(AuthorizationError):
        find_comparison_candidates(candidate["candidate_id"], store=store, context=ctx)


def test_comparison_ranks_all_neighbors_and_persists_supported_version(store: PopulationStore) -> None:
    recorded: list[dict] = []
    store.put_comparison_set = recorded.append  # type: ignore[attr-defined]
    first = _candidate(store, "Feedback amplifies signal.\n", "cmp-first", "Feedback signal")
    near = _candidate(store, "Feedback amplifies noise.\n", "cmp-near", "Feedback noise")
    _candidate(store, "Orbital mechanics describe planets.\n", "cmp-far", "Astronomy")
    ctx = agent_context(CRITIC_IDENTITY, capabilities=(CAP_COMPARISON_READ,), model_id="stub", prompt_version="cmp")

    result = find_neighbors(first["candidate_id"], store=store, context=ctx, limit=2)

    assert "authoritative_equivalence" not in result
    assert result["comparison_set_version"].startswith("cmp-")
    assert recorded and recorded[0]["comparison_set_version"] == result["comparison_set_version"]
    assert result["neighbors"][0]["candidate_id"] == near["candidate_id"]
    for neighbor in result["neighbors"]:
        assert "authoritative_equivalence" not in neighbor
        assert neighbor["relation_hint"] in {"possible_same", "possibly_adjacent", "possibly_conflicting", "possibly_distinct"}
        assert "score_components" in neighbor
        assert neighbor["provenance"]["retriever"] == "default_lexical_candidate_retriever"
