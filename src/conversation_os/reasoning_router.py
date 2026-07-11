from __future__ import annotations

from typing import Any, Dict


MODULE_ID = "kernel.reasoning.reasoning_router"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "route_reasoning",
)
__all__ = list(PUBLIC_API)


def route_reasoning(active_field: Dict[str, Any]) -> Dict[str, Any]:
    suggested = str(active_field.get("suggested_reasoning_family", "")).strip() or "idea_embedding_v1"
    fragment_role = str(active_field.get("fragment_role", "")).strip()
    ambiguity = float(active_field.get("ambiguity_level", 0.0) or 0.0)
    parent_count = len(active_field.get("candidate_parent_ideas", []) or [])
    bridge_behaviors = list(active_field.get("bridge_behaviors", []) or [])

    pipeline_id = suggested
    if bridge_behaviors:
        override = sorted(
            bridge_behaviors,
            key=lambda item: (-int(item.get("priority", 0)), str(item.get("behavior_id", ""))),
        )[0]
        preferred_pipeline = str(override.get("preferred_pipeline", "")).strip()
        if preferred_pipeline and str(override.get("routing_mode", "")).strip() == "override":
            pipeline_id = preferred_pipeline
        elif fragment_role == "candidate_evaluation":
            pipeline_id = "candidate_evaluation_v1"
        elif ambiguity >= 0.7 and parent_count <= 1:
            pipeline_id = "problem_reframing_v1"
    elif fragment_role == "candidate_evaluation":
        pipeline_id = "candidate_evaluation_v1"
    elif ambiguity >= 0.7 and parent_count <= 1:
        pipeline_id = "problem_reframing_v1"

    return {
        "pipeline_id": pipeline_id,
        "operator_overrides": {},
        "routing_factors": {
            "fragment_role": fragment_role,
            "ambiguity_level": round(ambiguity, 2),
            "candidate_parent_count": parent_count,
            "suggested_reasoning_family": suggested,
            "bridge_behavior_ids": [behavior.get("behavior_id", "") for behavior in bridge_behaviors],
        },
    }
