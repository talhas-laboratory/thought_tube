"""Proposer-facing submit_candidate tool."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from conversation_os.shape_population.contracts import AuthorizationError
from conversation_os.shape_population.governance import atomic_submit_candidate
from conversation_os.shape_population.execution_context import CAP_CANDIDATE_SUBMIT, ExecutionContext
from conversation_os.shape_population.identities import PROPOSER_IDENTITY, assert_tool_allowed, population_tool_surface
from conversation_os.shape_population.storage import PopulationStore

MODULE_ID = "kernel.shape_population.candidate_submission"
CONTRACT_VERSION = "1.1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "submit_candidate",
    "proposer_tool_surface",
)
__all__ = list(PUBLIC_API)

_TRUSTED_PAYLOAD_FIELDS = frozenset(
    {
        "agent_identity",
        "model_version",
        "prompt_version",
        "tool_contract_version",
        "run_id",
        "principal_id",
        "authenticated_by",
        "capabilities",
    }
)


def proposer_tool_surface() -> Mapping[str, Any]:
    surface = dict(population_tool_surface(PROPOSER_IDENTITY))
    # Only submit_candidate is exposed to the proposer.
    surface["tools"] = ["submit_candidate"]
    return surface


def submit_candidate(
    payload: Mapping[str, Any],
    *,
    store: PopulationStore,
    context: ExecutionContext,
    timing_ms: int = 0,
    retry_count: int = 0,
    cost_units: float = 0.0,
) -> Dict[str, Any]:
    """Agent tool: submit an evidence-grounded provisional interpretation."""
    if context is None:
        raise AuthorizationError("authenticated ExecutionContext is required for submit_candidate")
    context.require_capability(CAP_CANDIDATE_SUBMIT)
    identity = context.principal_id
    assert_tool_allowed(identity, "submit_candidate")
    body = {key: value for key, value in dict(payload).items() if key not in _TRUSTED_PAYLOAD_FIELDS}
    body["agent_identity"] = identity
    body["model_version"] = context.model_id
    body["prompt_version"] = context.prompt_version
    body["tool_contract_version"] = context.tool_contract_version
    body["run_id"] = context.run_id
    return atomic_submit_candidate(
        store,
        body,
        timing_ms=timing_ms,
        retry_count=retry_count,
        cost_units=cost_units,
    )
