"""Proposer-facing submit_candidate tool."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from conversation_os.shape_population.governance import atomic_submit_candidate
from conversation_os.shape_population.identities import PROPOSER_IDENTITY, assert_tool_allowed, population_tool_surface
from conversation_os.shape_population.storage import PopulationStore

MODULE_ID = "kernel.shape_population.candidate_submission"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "submit_candidate",
    "proposer_tool_surface",
)
__all__ = list(PUBLIC_API)


def proposer_tool_surface() -> Mapping[str, Any]:
    surface = dict(population_tool_surface(PROPOSER_IDENTITY))
    # Only submit_candidate is exposed to the proposer.
    surface["tools"] = ["submit_candidate"]
    return surface


def submit_candidate(
    payload: Mapping[str, Any],
    *,
    store: PopulationStore,
    timing_ms: int = 0,
    retry_count: int = 0,
    cost_units: float = 0.0,
) -> Dict[str, Any]:
    """Agent tool: submit an evidence-grounded provisional interpretation."""
    identity = str(payload.get("agent_identity") or PROPOSER_IDENTITY)
    assert_tool_allowed(identity, "submit_candidate")
    body = dict(payload)
    body["agent_identity"] = identity
    return atomic_submit_candidate(
        store,
        body,
        timing_ms=timing_ms,
        retry_count=retry_count,
        cost_units=cost_units,
    )
