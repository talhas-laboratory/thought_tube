"""Critique tools: find_comparison_candidates and submit_evaluation."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping

from conversation_os.shape_population.contracts import (
    COMPARISON_RELATIONS,
    ComparisonNeighbor,
    ValidationError,
)
from conversation_os.shape_population.governance import atomic_submit_evaluation
from conversation_os.shape_population.identities import CRITIC_IDENTITY, assert_tool_allowed, population_tool_surface
from conversation_os.shape_population.storage import PopulationStore

MODULE_ID = "kernel.shape_population.critique"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "find_comparison_candidates",
    "submit_evaluation",
    "critic_tool_surface",
)
__all__ = list(PUBLIC_API)


def critic_tool_surface(identity_id: str = CRITIC_IDENTITY) -> Mapping[str, Any]:
    surface = dict(population_tool_surface(identity_id))
    surface["tools"] = sorted(
        tool for tool in surface["tools"] if tool in {"find_comparison_candidates", "submit_evaluation"}
    )
    return surface


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", text.lower()) if len(token) > 2}


def _relation_hint(candidate: Mapping[str, Any], other: Mapping[str, Any]) -> str:
    """Lexical overlap supplies comparison material only — never equivalence."""
    left = _tokenize(f"{candidate.get('title','')} {candidate.get('statement','')} {candidate.get('boundary','')}")
    right = _tokenize(f"{other.get('title','')} {other.get('statement','')} {other.get('boundary','')}")
    if not left or not right:
        return "possibly_distinct"
    overlap = len(left & right) / max(1, len(left | right))
    conflict_markers = {"not", "unlike", "opposite", "conflict", "versus"}
    if overlap >= 0.5:
        return "possible_same"
    if left & conflict_markers or right & conflict_markers:
        return "possibly_conflicting"
    if overlap >= 0.2:
        return "possibly_adjacent"
    return "possibly_distinct"


def find_comparison_candidates(
    candidate_id: str,
    *,
    store: PopulationStore,
    limit: int = 5,
    policy_version: str = "1.0.0",
    agent_identity: str = CRITIC_IDENTITY,
) -> Dict[str, Any]:
    """Agent tool: retrieve possible related candidates after provisional formation."""
    assert_tool_allowed(agent_identity, "find_comparison_candidates")
    if limit < 1:
        raise ValidationError("limit must be >= 1")
    if not policy_version:
        raise ValidationError("policy_version required")
    candidate = store.get_candidate(candidate_id)
    if candidate is None:
        raise ValidationError("comparison unavailable before provisional candidate acceptance")
    neighbors: List[ComparisonNeighbor] = []
    for other in store.list_candidates():
        if other["candidate_id"] == candidate_id:
            continue
        hint = _relation_hint(candidate, other)
        if hint not in COMPARISON_RELATIONS:
            hint = "possibly_distinct"
        neighbors.append(
            ComparisonNeighbor(
                candidate_id=other["candidate_id"],
                relation_hint=hint,
                title=str(other.get("title") or ""),
                statement=str(other.get("statement") or ""),
                boundary=str(other.get("boundary") or ""),
                evidence_refs=[dict(item) for item in (other.get("evidence_refs") or [])],
                status=str(other.get("status") or ""),
            )
        )
        if len(neighbors) >= limit:
            break
    return {
        "candidate_id": candidate_id,
        "policy_version": policy_version,
        "neighbors": [item.to_dict() for item in neighbors],
        "authoritative_equivalence": False,
        "note": "Similarity supplies comparison material; intelligence decides relationship.",
    }


def submit_evaluation(
    payload: Mapping[str, Any],
    *,
    store: PopulationStore,
    timing_ms: int = 0,
    retry_count: int = 0,
    cost_units: float = 0.0,
) -> Dict[str, Any]:
    """Agent tool: submit critique/disposition/relationship findings."""
    identity = str(payload.get("agent_identity") or CRITIC_IDENTITY)
    assert_tool_allowed(identity, "submit_evaluation")
    body = dict(payload)
    body["agent_identity"] = identity
    return atomic_submit_evaluation(
        store,
        body,
        timing_ms=timing_ms,
        retry_count=retry_count,
        cost_units=cost_units,
    )
