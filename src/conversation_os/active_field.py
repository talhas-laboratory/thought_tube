from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .models import ActiveFieldState
from .reasoning_bridge import classify_turn, get_context_bundle
from .thread_context import build_thread_packet


MODULE_ID = "kernel.reasoning.active_field"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "build_active_field",
)
__all__ = list(PUBLIC_API)


def _fragment_role(request: Dict[str, Any]) -> str:
    text = request.get("raw_text", "").lower()
    if any(token in text for token in ("feel like", "maybe", "fragment", "thought")):
        return "idea_fragment"
    if any(token in text for token in ("build", "implement", "make", "mvp")):
        return "implementation_request"
    if any(token in text for token in ("is this", "evaluate", "novel", "feasible", "risk")):
        return "candidate_evaluation"
    if text.endswith("?") or any(token in text for token in ("what", "how", "why", "explain")):
        return "question"
    return "request"


def _candidate_parent_ideas(
    request: Dict[str, Any],
    context_state: Dict[str, Any],
    retrieval_bundle: Dict[str, Any],
) -> List[Dict[str, Any]]:
    caller_hints = request.get("caller_hints", {}) or {}
    hinted = caller_hints.get("candidate_parent_ideas")
    if isinstance(hinted, list) and hinted:
        return hinted

    ideas: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for capsule in retrieval_bundle.get("seed_capsules", []) + retrieval_bundle.get("related_capsules", []):
        object_id = f"{capsule.get('ref_type', 'capsule')}:{capsule.get('ref_id', capsule.get('capsule_id', ''))}"
        if object_id in seen:
            continue
        seen.add(object_id)
        ideas.append(
            {
                "object_id": object_id,
                "label": capsule.get("label", ""),
                "score": round(float(capsule.get("confidence", 0.0)), 2),
                "capsule_type": capsule.get("capsule_type", ""),
            }
        )
    if ideas:
        return ideas[:4]
    return [
        {
            "object_id": context_state.get("object_id", ""),
            "label": context_state.get("active_topic", ""),
            "score": round(float(context_state.get("confidence", 0.0)), 2),
            "capsule_type": "context",
        }
    ]


def _active_dimensions(request: Dict[str, Any], retrieval_bundle: Dict[str, Any]) -> List[str]:
    dimensions: List[str] = []
    for value in request.get("domain_hints", []) or []:
        text = str(value).strip()
        if text and text not in dimensions:
            dimensions.append(text)
    for capsule in retrieval_bundle.get("seed_capsules", []):
        capsule_type = str(capsule.get("capsule_type", "")).strip()
        if capsule_type and capsule_type not in dimensions:
            dimensions.append(capsule_type)
    text = request.get("raw_text", "").lower()
    for token in ("architecture", "product", "research", "design", "implementation"):
        if token in text and token not in dimensions:
            dimensions.append(token)
    return dimensions[:6]


def _ambiguity_level(request: Dict[str, Any], parent_ideas: List[Dict[str, Any]]) -> float:
    text = request.get("raw_text", "").lower()
    value = 0.22
    if any(token in text for token in ("maybe", "somehow", "not sure", "feel like", "unclear")):
        value += 0.3
    if "?" in text:
        value += 0.12
    if len(parent_ideas) > 1:
        value += 0.18
    if not parent_ideas:
        value += 0.2
    return round(min(0.95, value), 2)


def _fixation_risk(request: Dict[str, Any], parent_ideas: List[Dict[str, Any]]) -> float:
    text = request.get("raw_text", "").lower()
    value = 0.12
    if any(token in text for token in ("obvious", "stuck", "same thing", "can't get past")):
        value += 0.4
    if len(parent_ideas) == 1 and parent_ideas[0].get("score", 0.0) > 0.8:
        value += 0.15
    return round(min(0.95, value), 2)


def _novelty_confidence(request: Dict[str, Any], retrieval_bundle: Dict[str, Any]) -> float:
    value = 0.45
    if retrieval_bundle.get("alias_hits"):
        value -= 0.08
    if len(request.get("domain_hints", []) or []) > 1:
        value += 0.1
    if any(token in request.get("raw_text", "").lower() for token in ("new", "novel", "different")):
        value += 0.08
    return round(max(0.1, min(0.95, value)), 2)


def _suggested_reasoning_family(
    fragment_role: str,
    ambiguity_level: float,
    parent_ideas: List[Dict[str, Any]],
    bridge_behaviors: List[Dict[str, Any]],
) -> str:
    for behavior in sorted(bridge_behaviors, key=lambda item: (-int(item.get("priority", 0)), str(item.get("behavior_id", "")))):
        preferred_pipeline = str(behavior.get("preferred_pipeline", "")).strip()
        if preferred_pipeline and str(behavior.get("routing_mode", "")).strip() == "override":
            return preferred_pipeline
    substantive_parent_count = sum(
        1 for idea in parent_ideas if idea.get("capsule_type") not in {"context", ""} or float(idea.get("score", 0.0)) >= 0.75
    )
    if fragment_role == "candidate_evaluation":
        return "candidate_evaluation_v1"
    if ambiguity_level >= 0.5 and substantive_parent_count <= 1:
        return "problem_reframing_v1"
    return "idea_embedding_v1"


def build_active_field(
    root: Path,
    request: Dict[str, Any],
    *,
    include_cross_pond: bool = False,
    context_state: Dict[str, Any] | None = None,
    context_bundle: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    if context_state is None:
        context_state = classify_turn(root, request)
    if context_bundle is None:
        context_bundle = get_context_bundle(root, context_state)
    retrieval_bundle = dict(context_bundle.get("global_fallback", {}))
    if include_cross_pond:
        retrieval_bundle["include_cross_pond"] = True

    parent_ideas = _candidate_parent_ideas(request, context_state, retrieval_bundle)
    fragment_role = _fragment_role(request)
    ambiguity_level = _ambiguity_level(request, parent_ideas)
    fixation_risk = _fixation_risk(request, parent_ideas)
    novelty_confidence = _novelty_confidence(request, retrieval_bundle)

    constraints = list((request.get("caller_hints", {}) or {}).get("constraints", []) or [])
    if not constraints:
        constraints = ["bounded_context", "inspectable_state"]

    perturbation_markers: List[str] = []
    caller_hints = request.get("caller_hints", {}) or {}
    bridge_behaviors = list(context_state.get("bridge_behaviors", []) or [])
    if caller_hints.get("thought_id"):
        try:
            thread_packet = build_thread_packet(root, str(caller_hints["thought_id"]))
            perturbation_markers.append("thread_packet")
            context_bundle["workspace_local"]["thread_packet"] = thread_packet
        except KeyError:
            pass
    if caller_hints.get("imported_conversation"):
        perturbation_markers.append("imported_conversation")
    if caller_hints.get("artifact_ref"):
        perturbation_markers.append("artifact")

    active_tensions = []
    if context_state.get("current_tension"):
        active_tensions.append(context_state["current_tension"])

    field = ActiveFieldState(
        field_id=f"field:{context_state['context_id']}",
        request_id=str(request.get("request_id", "")),
        context_id=context_state["context_id"],
        fragment_role=fragment_role,
        candidate_parent_ideas=parent_ideas,
        active_dimensions=_active_dimensions(request, retrieval_bundle),
        active_tensions=active_tensions,
        constraints=constraints,
        ambiguity_level=ambiguity_level,
        fixation_risk=fixation_risk,
        novelty_confidence=novelty_confidence,
        fit_targets=[idea.get("object_id", "") for idea in parent_ideas if idea.get("object_id")],
        suggested_reasoning_family=_suggested_reasoning_family(fragment_role, ambiguity_level, parent_ideas, bridge_behaviors),
        source_refs=list(
            dict.fromkeys(
                list(request.get("source_refs", []) or []) + list(retrieval_bundle.get("source_refs", []) or [])
            )
        ),
        retrieval_bundle_summary={
            "seed_count": len(retrieval_bundle.get("seed_capsules", []) or []),
            "related_count": len(retrieval_bundle.get("related_capsules", []) or []),
            "anchor_pond": retrieval_bundle.get("anchor_pond", ""),
            "alias_hit_count": len(retrieval_bundle.get("alias_hits", []) or []),
        },
        bridge_behaviors=bridge_behaviors,
        perturbation_markers=perturbation_markers,
        state_update_scope=str(
            context_state.get("attributes", {}).get("pending_switch_event", {}).get("switch_kind", "local_adjustment")
        ),
        attributes={
            "context_bundle": context_bundle,
            "context_state": context_state,
            "reasoning_posture": context_state.get("reasoning_posture", ""),
            "factual_anchor_level": context_state.get("factual_anchor_level", ""),
        },
    )
    return field.to_dict()
