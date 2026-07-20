"""Critique tools: find_comparison_candidates and submit_evaluation."""

from __future__ import annotations

from typing import Any, Dict, Mapping

from conversation_os.shape_population.comparison import DEFAULT_POLICY_VERSION, ComparisonRetriever, find_neighbors
from conversation_os.shape_population.execution_context import (
    CAP_COMPARISON_READ,
    CAP_EVALUATION_SUBMIT,
    ExecutionContext,
    agent_context,
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


def find_comparison_candidates(
    candidate_id: str,
    *,
    store: PopulationStore,
    limit: int = 5,
    policy_version: str = DEFAULT_POLICY_VERSION,
    agent_identity: str = CRITIC_IDENTITY,
    context: ExecutionContext | None = None,
    retriever: ComparisonRetriever | None = None,
) -> Dict[str, Any]:
    """Agent tool: retrieve possible related candidates after provisional formation."""
    if context is None:
        assert_tool_allowed(agent_identity, "find_comparison_candidates")
        context = agent_context(
            agent_identity,
            capabilities=(CAP_COMPARISON_READ,),
            model_id="deterministic-comparison",
            prompt_version=CONTRACT_VERSION,
        )
    return find_neighbors(
        candidate_id,
        store=store,
        context=context,
        retriever=retriever,
        limit=limit,
        policy_version=policy_version,
    )


def submit_evaluation(
    payload: Mapping[str, Any],
    *,
    store: PopulationStore,
    context: ExecutionContext | None = None,
    timing_ms: int = 0,
    retry_count: int = 0,
    cost_units: float = 0.0,
) -> Dict[str, Any]:
    """Agent tool: submit critique/disposition/relationship findings."""
    if context is not None:
        context.require_capability(CAP_EVALUATION_SUBMIT)
        identity = context.principal_id
    else:
        identity = str(payload.get("agent_identity") or CRITIC_IDENTITY)
    assert_tool_allowed(identity, "submit_evaluation")
    body = dict(payload)
    body["agent_identity"] = identity
    if context is not None:
        body["model_version"] = context.model_id
        body["prompt_version"] = context.prompt_version
        body["tool_contract_version"] = context.tool_contract_version
        body["run_id"] = context.run_id
    return atomic_submit_evaluation(
        store,
        body,
        timing_ms=timing_ms,
        retry_count=retry_count,
        cost_units=cost_units,
    )
