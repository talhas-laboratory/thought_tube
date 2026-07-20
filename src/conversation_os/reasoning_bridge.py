from __future__ import annotations

import copy
from dataclasses import replace
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .knowledge_layer import build_retrieval_bundle
from .models import ContextState, ControlPacket
from .personal_interface import load_bridge_state
from .runtime_layout import product_runtime_dir
from .storage import append_jsonl, ensure_dir, make_id, read_json, read_jsonl, session_events_path, utc_now


MODULE_ID = "kernel.reasoning.reasoning_bridge"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "ensure_reasoning_runtime",
    "load_context_states",
    "load_context_switch_events",
    "classify_turn",
    "bind_workspace",
    "get_context_bundle",
    "record_context_switch",
    "prepare_bridge_candidates",
    "context_state_from_control_packet",
    "persist_control_packet",
    "heuristic_classify_turn",
    "load_control_packets",
    "is_incognito_context",
    "load_bridge_behavior_specs",
    "find_latest_context_for_thought",
    "find_latest_result_for_request",
    "build_session_envelope",
    "build_frame_spec",
    "build_frame_bundle",
    "assemble_frame_bundle",
    "split_frame_assembly",
    "build_frame_audit",
    "execution_audit_isolation_enabled",
    "build_effective_grant_from_context",
    "effective_layers_to_bridge_layers",
    "effective_grant_normalization_enabled",
    "deterministic_budget_enforcement_enabled",
    "orient_first_compose_enabled",
    "disclosure_service_enabled",
    "inspect_disclosure_receipt",
    "list_disclosure_receipts",
    "inspect_aperture_operator_view",
    "active_state_continuity_enabled",
)
__all__ = list(PUBLIC_API)


def _note_agent_retrieval_mode(note_agent_state: Dict[str, Any]) -> str:
    retrieval_policy = dict(note_agent_state.get("retrieval_policy", {}) or {})
    mode = str(retrieval_policy.get("retrieval_mode", "") or "").strip().lower()
    if mode == "ocean_wide":
        return "deep_global"
    if mode == "session_plus_ocean":
        return "bounded_global"
    return "session_only"


def _apply_note_agent_overrides(
    resolved_budget: Dict[str, Any],
    attributes: Dict[str, Any],
    retrieval_mode: str,
    *,
    orient_first_enabled: bool = False,
) -> tuple[Dict[str, Any], str, Dict[str, Any] | None]:
    note_agent_state = dict(attributes.get("note_agent", {}) or {})
    if not note_agent_state:
        return resolved_budget, retrieval_mode, None

    caller_hints = dict(attributes.get("caller_hints", {}) or {})
    if str(caller_hints.get("context_mode", "") or caller_hints.get("retrieval_mode", "")).strip():
        return resolved_budget, retrieval_mode, note_agent_state

    retrieval_policy = dict(note_agent_state.get("retrieval_policy", {}) or {})
    if not retrieval_policy:
        return resolved_budget, retrieval_mode, note_agent_state

    next_budget = dict(resolved_budget)
    if "retrieval_limit" in retrieval_policy:
        next_budget["retrieval_limit"] = int(retrieval_policy.get("retrieval_limit", 0) or 0)
    if "neighbor_limit" in retrieval_policy:
        next_budget["neighbor_limit"] = int(retrieval_policy.get("neighbor_limit", 0) or 0)

    next_mode = _note_agent_retrieval_mode(note_agent_state)
    if orient_first_enabled:
        from .orient_first_compose import authorize_second_pass_widen

        authorized, reason = authorize_second_pass_widen(
            base_mode=retrieval_mode,
            proposed_mode=next_mode,
            caller_hints=caller_hints,
        )
        if not authorized:
            blocked_state = {
                **note_agent_state,
                "widen_blocked": True,
                "widen_block_reason": reason,
            }
            return resolved_budget, retrieval_mode, blocked_state

    next_budget["use_global"] = next_mode != "session_only"
    return next_budget, next_mode, note_agent_state


BRIDGE_BEHAVIOR_RULES = {
    "creative_expansion": {
        "behavior_id": "creative_expansion",
        "priority": 90,
        "preferred_pipeline": "intuition_expansion_v1",
        "routing_mode": "override",
        "reasoning_posture": "expansive",
        "response_directives": [
            "connect_adjacent_paths",
            "explain_signal_shape",
            "preserve_creative_spark",
            "avoid_unnecessary_caveats",
        ],
        "operator_biases": {
            "prefer_expansion": True,
            "prefer_connection_over_caveat": True,
            "prefer_interpretation_over_closure": True,
        },
    }
    ,
    "symbolic_interpretation": {
        "behavior_id": "symbolic_interpretation",
        "priority": 88,
        "preferred_pipeline": "symbolic_interpretation_v1",
        "routing_mode": "override",
        "reasoning_posture": "interpretive",
        "response_directives": [
            "map_symbolic_meaning",
            "name_latent_associations",
            "preserve_multiplicity",
        ],
        "operator_biases": {
            "prefer_symbolic_reading": True,
            "avoid_literal_collapse": True,
        },
    },
    "objective_evaluation": {
        "behavior_id": "objective_evaluation",
        "priority": 84,
        "preferred_pipeline": "candidate_evaluation_v1",
        "routing_mode": "override",
        "reasoning_posture": "evaluative",
        "response_directives": [
            "state_assessment_directly",
            "separate_signal_from_speculation",
            "surface_key_risks",
        ],
        "operator_biases": {
            "prefer_objective_language": True,
            "prefer_comparative_scoring": True,
        },
    },
    "implementation_scaffold": {
        "behavior_id": "implementation_scaffold",
        "priority": 82,
        "preferred_pipeline": "idea_embedding_v1",
        "routing_mode": "bias",
        "reasoning_posture": "implementation",
        "response_directives": [
            "translate_into_steps",
            "preserve_architectural_shape",
            "move_toward_execution",
        ],
        "operator_biases": {
            "prefer_actionable_structure": True,
            "prefer_scaffold_over_abstraction": True,
        },
    },
}


def _bridge_behaviors_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "bridge_behaviors"


def load_bridge_behavior_specs(root: Path) -> Dict[str, Dict[str, Any]]:
    behavior_dir = _bridge_behaviors_dir(root)
    if not behavior_dir.exists():
        return copy.deepcopy(BRIDGE_BEHAVIOR_RULES)

    specs: Dict[str, Dict[str, Any]] = {}
    for path in sorted(behavior_dir.glob("*.json")):
        payload = read_json(path, default=None)
        if not isinstance(payload, dict):
            continue
        behavior_id = str(payload.get("behavior_id", path.stem)).strip()
        if not behavior_id:
            continue
        normalized = dict(payload)
        normalized["behavior_id"] = behavior_id
        specs[behavior_id] = normalized

    if not specs:
        return copy.deepcopy(BRIDGE_BEHAVIOR_RULES)
    return specs


def find_latest_context_for_thought(root: Path, thought_id: str) -> Dict[str, Any] | None:
    if not thought_id:
        return None
    for row in reversed(load_context_states(root)):
        caller_hints = (row.get("attributes", {}) or {}).get("caller_hints", {}) or {}
        if str(caller_hints.get("thought_id", "")).strip() == thought_id:
            return row
    return None


def find_latest_result_for_request(root: Path, request_id: str) -> Dict[str, Any] | None:
    if not request_id:
        return None
    results_path = _runtime_dir(root) / "reasoning_results.jsonl"
    for row in reversed(read_jsonl(results_path)):
        if str(row.get("request_id", "")).strip() == request_id:
            return row
    return None


def _runtime_dir(root: Path) -> Path:
    return product_runtime_dir(root, "inner_world_v1", "data") / "reasoning_runtime"


def _context_states_path(root: Path) -> Path:
    return _runtime_dir(root) / "context_states.jsonl"


def _context_switch_events_path(root: Path) -> Path:
    return _runtime_dir(root) / "context_switch_events.jsonl"


def _control_packets_path(root: Path) -> Path:
    return _runtime_dir(root) / "control_packets.jsonl"


def ensure_reasoning_runtime(root: Path) -> None:
    ensure_dir(_runtime_dir(root))


def load_context_states(root: Path) -> List[Dict[str, Any]]:
    ensure_reasoning_runtime(root)
    return read_jsonl(_context_states_path(root))


def load_context_switch_events(root: Path) -> List[Dict[str, Any]]:
    ensure_reasoning_runtime(root)
    return read_jsonl(_context_switch_events_path(root))


def load_control_packets(root: Path) -> List[Dict[str, Any]]:
    ensure_reasoning_runtime(root)
    return read_jsonl(_control_packets_path(root))


def _latest_context_for_session(root: Path, session_id: str) -> Dict[str, Any] | None:
    if not session_id:
        return None
    for row in reversed(load_context_states(root)):
        if row.get("attributes", {}).get("session_id") == session_id:
            return row
    return None


def _topical_tokens(text: str) -> List[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "but",
        "for",
        "from",
        "how",
        "i",
        "in",
        "into",
        "is",
        "it",
        "my",
        "of",
        "on",
        "or",
        "so",
        "that",
        "the",
        "this",
        "to",
        "we",
        "with",
    }
    cleaned = "".join(ch.lower() if ch.isalnum() or ch.isspace() else " " for ch in text)
    tokens = [token for token in cleaned.split() if token and token not in stopwords]
    ordered: List[str] = []
    for token in tokens:
        if token not in ordered:
            ordered.append(token)
    return ordered[:8]


def _infer_active_topic(request: Dict[str, Any]) -> str:
    caller_hints = request.get("caller_hints", {}) or {}
    if caller_hints.get("active_topic"):
        return str(caller_hints["active_topic"])
    tokens = _topical_tokens(request.get("raw_text", ""))
    if not tokens:
        return "unspecified topic"
    return " ".join(tokens[:4])


def _infer_object_scope(request: Dict[str, Any]) -> str:
    caller_hints = request.get("caller_hints", {}) or {}
    explicit = str(caller_hints.get("object_scope", "")).strip()
    if explicit:
        return explicit
    text = request.get("raw_text", "").lower()
    if any(phrase in text for phrase in ("different topic", "new thread", "new main object")):
        return "new_main"
    if any(phrase in text for phrase in ("parallel", "adjacent thread", "side topic")):
        return "parallel_object"
    if any(phrase in text for phrase in ("dimension", "different angle", "sub version", "sub-object")):
        return "sub_object"
    return "same_main"


def _infer_user_goal(request: Dict[str, Any]) -> str:
    caller_hints = request.get("caller_hints", {}) or {}
    if caller_hints.get("user_goal"):
        return str(caller_hints["user_goal"])
    text = request.get("raw_text", "").lower()
    if any(token in text for token in ("build", "implement", "mvp", "scaffold")):
        return "build"
    if any(token in text for token in ("evaluate", "novel", "risk", "feasible")):
        return "evaluate"
    if any(token in text for token in ("explain", "what is", "how does", "why")):
        return "understand"
    return "explore"


def _infer_tension(request: Dict[str, Any]) -> str:
    caller_hints = request.get("caller_hints", {}) or {}
    if caller_hints.get("current_tension"):
        return str(caller_hints["current_tension"])
    text = request.get("raw_text", "")
    lowered = text.lower()
    if " vs " in lowered:
        return text
    for marker in (" but ", " however ", " while ", " although "):
        if marker in lowered:
            left, _, right = lowered.partition(marker)
            return f"{left.strip()} vs {right.strip()}".strip()
    return ""


def _infer_answer_shape(request: Dict[str, Any]) -> str:
    caller_hints = request.get("caller_hints", {}) or {}
    if caller_hints.get("answer_shape"):
        return str(caller_hints["answer_shape"])
    text = request.get("raw_text", "").lower()
    if any(token in text for token in ("build", "implement", "mvp", "scaffold", "plan")):
        return "implementation_scaffold"
    if any(token in text for token in ("evaluate", "novel", "risk", "feasible")):
        return "evaluation_summary"
    if "?" in text or any(token in text for token in ("what", "how", "why", "explain")):
        return "direct_explanation"
    return "integration_probe"


def _infer_depth_mode(request: Dict[str, Any]) -> str:
    caller_hints = request.get("caller_hints", {}) or {}
    for key in ("depth_mode", "desired_depth"):
        value = str(caller_hints.get(key, "")).strip().lower()
        if value in {"focused", "contextual", "deep", "incognito"}:
            return value
    text = request.get("raw_text", "").lower()
    if any(token in text for token in ("deep", "thorough", "holistic", "full context")):
        return "deep"
    if any(token in text for token in ("why", "how", "build", "evaluate", "system")):
        return "contextual"
    return "focused"


def _infer_factual_anchor_level(request: Dict[str, Any]) -> str:
    caller_hints = request.get("caller_hints", {}) or {}
    explicit = str(caller_hints.get("factual_anchor_level", "")).strip().lower()
    if explicit in {"low", "medium", "high"}:
        return explicit

    text = request.get("raw_text", "").lower()
    technical_markers = (
        "api",
        "bug",
        "class",
        "cli",
        "code",
        "contract",
        "dataclass",
        "error",
        "file",
        "function",
        "implement",
        "module",
        "parser",
        "schema",
        "test",
    )
    interpretive_markers = (
        "aesthetic",
        "association",
        "could this",
        "feel like",
        "intuition",
        "meaning",
        "metaphor",
        "represent",
        "subconscious",
        "symbolic",
        "vibe",
    )
    technical_hits = sum(1 for marker in technical_markers if marker in text)
    interpretive_hits = sum(1 for marker in interpretive_markers if marker in text)
    if technical_hits >= max(2, interpretive_hits + 1):
        return "high"
    if interpretive_hits >= max(1, technical_hits):
        return "low"
    return "medium"


def _infer_reasoning_posture(request: Dict[str, Any], factual_anchor_level: str, user_goal: str) -> str:
    caller_hints = request.get("caller_hints", {}) or {}
    explicit = str(caller_hints.get("reasoning_posture", "")).strip().lower()
    if explicit:
        return explicit

    routing_tags = [str(value).strip().lower() for value in caller_hints.get("routing_tags", []) or [] if str(value).strip()]
    text = request.get("raw_text", "").lower()
    if "metathought" in routing_tags or any(
        phrase in text for phrase in ("creative discussion", "expand this", "connect this", "keep the spark", "interpret this")
    ):
        return "expansive"
    if factual_anchor_level == "low" and any(
        phrase in text for phrase in ("could this", "intuition", "represent", "subconscious", "symbolic", "what does")
    ):
        return "expansive"
    if user_goal == "build":
        return "implementation"
    if user_goal == "evaluate":
        return "evaluative"
    if "?" in text:
        return "explanatory"
    return "exploratory"


def _behavior_pattern_texts(bridge_state: Dict[str, Any]) -> List[str]:
    patterns = []
    for entry in bridge_state.get("behavior_patterns", []) or []:
        if isinstance(entry, str):
            patterns.append(entry.lower())
        elif isinstance(entry, dict):
            text = " ".join(str(value) for value in entry.values() if isinstance(value, (str, int, float)))
            if text.strip():
                patterns.append(text.lower())
    return patterns


def _confirmed_bridge_behavior_ids(bridge_state: Dict[str, Any]) -> set[str]:
    confirmed: set[str] = set()
    for entry in bridge_state.get("behavior_patterns", []) or []:
        if not isinstance(entry, dict):
            continue
        pattern_key = str(entry.get("pattern_key", "")).strip().lower()
        if not pattern_key.startswith("bridge_behavior:"):
            continue
        behavior_id = pattern_key.split(":", 1)[1].strip()
        if not behavior_id:
            continue
        count = int(entry.get("count", 0) or 0)
        confidence = float(entry.get("confidence", 0.0) or 0.0)
        if count >= 1 and confidence >= 0.7:
            confirmed.add(behavior_id)
    return confirmed


def _match_bridge_behaviors(
    request: Dict[str, Any],
    bridge_state: Dict[str, Any],
    *,
    user_goal: str,
    factual_anchor_level: str,
    reasoning_posture: str,
    behavior_rules: Dict[str, Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    rules = behavior_rules or BRIDGE_BEHAVIOR_RULES
    caller_hints = request.get("caller_hints", {}) or {}
    routing_tags = {str(value).strip().lower() for value in caller_hints.get("routing_tags", []) or [] if str(value).strip()}
    text = request.get("raw_text", "").lower()
    pattern_texts = _behavior_pattern_texts(bridge_state)
    confirmed_behavior_ids = _confirmed_bridge_behavior_ids(bridge_state)
    matched: List[Dict[str, Any]] = []

    requested_behaviors = [
        str(value).strip().lower()
        for value in caller_hints.get("bridge_behaviors", []) or caller_hints.get("behavior_ids", []) or []
        if str(value).strip()
    ]
    has_explicit_symbolic_language = any(
        phrase in text for phrase in ("symbolic", "subconscious", "archetype", "deeper meaning", "represent")
    )

    creative_signals: List[str] = []
    if "metathought" in routing_tags:
        creative_signals.append("routing_tag:metathought")
    if any(phrase in text for phrase in ("could this", "intuition", "represent", "subconscious", "symbolic", "what does")):
        creative_signals.append("interpretive_language")
    if "expand" in text or "connector" in text or "explain" in text:
        creative_signals.append("expansion_request")
    if any("creative spark" in pattern or "avoid caveat" in pattern or "expand" in pattern for pattern in pattern_texts):
        creative_signals.append("bridge_state_pattern_match")
    if reasoning_posture == "expansive":
        creative_signals.append("reasoning_posture:expansive")
    if factual_anchor_level == "low":
        creative_signals.append("factual_anchor:low")

    should_apply_creative = (
        "creative_expansion" in requested_behaviors
        or "metathought" in routing_tags
        or (
            not has_explicit_symbolic_language
            and "symbolic_interpretation" not in requested_behaviors
            and reasoning_posture == "expansive"
            and factual_anchor_level == "low"
            and user_goal in {"explore", "understand"}
            and len(creative_signals) >= 2
        )
    )
    if should_apply_creative and "creative_expansion" in rules:
        behavior = dict(rules["creative_expansion"])
        behavior["matched_signals"] = creative_signals
        matched.append(behavior)

    symbolic_signals: List[str] = []
    if has_explicit_symbolic_language:
        symbolic_signals.append("symbolic_language")
    if reasoning_posture in {"expansive", "interpretive"}:
        symbolic_signals.append(f"reasoning_posture:{reasoning_posture}")
    if "symbolic_interpretation" in confirmed_behavior_ids:
        symbolic_signals.append("confirmed_behavior:symbolic_interpretation")
    if ("symbolic_interpretation" in requested_behaviors or (
        factual_anchor_level == "low" and symbolic_signals and user_goal in {"explore", "understand"}
    )) and "symbolic_interpretation" in rules:
        behavior = dict(rules["symbolic_interpretation"])
        behavior["matched_signals"] = symbolic_signals
        matched.append(behavior)

    evaluation_signals: List[str] = []
    if any(phrase in text for phrase in ("evaluate", "objectively", "risks", "novel", "feasible", "bullshit")):
        evaluation_signals.append("evaluation_language")
    if user_goal == "evaluate":
        evaluation_signals.append("user_goal:evaluate")
    if factual_anchor_level in {"medium", "high"}:
        evaluation_signals.append(f"factual_anchor:{factual_anchor_level}")
    if "objective_evaluation" in confirmed_behavior_ids:
        evaluation_signals.append("confirmed_behavior:objective_evaluation")
    if ("objective_evaluation" in requested_behaviors or (
        evaluation_signals and user_goal == "evaluate"
    )) and "objective_evaluation" in rules:
        behavior = dict(rules["objective_evaluation"])
        behavior["matched_signals"] = evaluation_signals
        matched.append(behavior)

    implementation_signals: List[str] = []
    if any(phrase in text for phrase in ("build", "implement", "mvp", "scaffold", "architecture", "plan")):
        implementation_signals.append("implementation_language")
    if user_goal == "build":
        implementation_signals.append("user_goal:build")
    if "implementation_scaffold" in confirmed_behavior_ids:
        implementation_signals.append("confirmed_behavior:implementation_scaffold")
    if ("implementation_scaffold" in requested_behaviors or (
        implementation_signals and user_goal == "build"
    )) and "implementation_scaffold" in rules:
        behavior = dict(rules["implementation_scaffold"])
        behavior["matched_signals"] = implementation_signals
        matched.append(behavior)

    matched.sort(key=lambda item: (-int(item.get("priority", 0)), str(item.get("behavior_id", ""))))
    return matched


def _context_confidence(scope: str, topic: str, tension: str) -> float:
    confidence = 0.56
    if scope != "same_main":
        confidence -= 0.04
    if topic and topic != "unspecified topic":
        confidence += 0.12
    if tension:
        confidence += 0.04
    return round(max(0.1, min(0.95, confidence)), 2)


def _switch_kind(previous: Dict[str, Any], current: ContextState) -> str | None:
    if previous.get("active_workspace_id") != current.active_workspace_id and current.active_workspace_id:
        return "workspace_shift"
    if previous.get("object_id") != current.object_id or previous.get("object_scope") != current.object_scope:
        return "object_shift"
    if previous.get("active_topic") != current.active_topic or previous.get("user_goal") != current.user_goal:
        return "field_reshape"
    if previous.get("depth_mode") != current.depth_mode or previous.get("answer_shape") != current.answer_shape:
        return "local_adjustment"
    return None


def classify_turn(root: Path, request: Dict[str, Any]) -> Dict[str, Any]:
    from .bridge_controller import classify_with_agent, load_bridge_config
    from .bridge_session_context import should_skip_agent_classify

    if should_skip_agent_classify(root, request):
        return heuristic_classify_turn(root, request)

    bridge_config = load_bridge_config(root)
    if bridge_config.get("enabled"):
        packet_result = _classify_turn_with_agent(root, request, bridge_config=bridge_config)
        if packet_result is not None:
            packet, metadata = packet_result
            context_state = context_state_from_control_packet(root, request, packet, metadata=metadata)
            return context_state
    return heuristic_classify_turn(root, request)


def prepare_bridge_candidates(root: Path, request: Dict[str, Any]) -> Dict[str, Any]:
    heuristic_preview = heuristic_classify_turn(root, request)
    active_topic = str(heuristic_preview.get("active_topic", ""))
    depth_mode = str(heuristic_preview.get("depth_mode", "contextual"))
    candidate_depth_mode = "contextual" if depth_mode == "focused" else depth_mode
    budget = _budget_for_depth(candidate_depth_mode)
    retrieval_bundle = {
        "query": active_topic,
        "seed_capsules": [],
        "related_capsules": [],
        "included_links": [],
        "source_refs": [],
        "count": 0,
        "alias_hits": [],
        "anchor_pond": "",
        "include_cross_pond": False,
    }
    if budget["use_global"] and active_topic:
        retrieval_bundle = build_retrieval_bundle(
            root,
            active_topic,
            limit=int(budget["retrieval_limit"]),
            neighbor_limit=int(budget["neighbor_limit"]),
            include_cross_pond=candidate_depth_mode == "deep",
        )
    bridge_state = load_bridge_state(root)
    return {
        "retrieval_bundle": retrieval_bundle,
        "bridge_state": bridge_state,
        "heuristic_preview": heuristic_preview,
    }


def _classify_turn_with_agent(
    root: Path,
    request: Dict[str, Any],
    *,
    bridge_config: Dict[str, Any],
) -> tuple[ControlPacket, Dict[str, Any]] | None:
    from .bridge_controller import classify_with_agent

    candidates = prepare_bridge_candidates(root, request)
    heuristic_preview = candidates["heuristic_preview"] if bridge_config.get("emit_heuristic_preview") else None
    return classify_with_agent(
        root,
        request,
        retrieval_bundle=candidates["retrieval_bundle"],
        bridge_state=candidates["bridge_state"],
        heuristic_preview=heuristic_preview,
    )


def context_state_from_control_packet(
    root: Path,
    request: Dict[str, Any],
    packet: ControlPacket,
    *,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    caller_hints = request.get("caller_hints", {}) or {}
    session_id = str(request.get("session_id", "")).strip()
    behavior_rules = load_bridge_behavior_specs(root)
    bridge_behaviors = [
        dict(behavior_rules[behavior_id])
        for behavior_id in packet.bridge_behaviors
        if behavior_id in behavior_rules
    ]
    context = ContextState(
        context_id=make_id("ctx"),
        request_id=str(request.get("request_id", packet.request_id)),
        active_topic=packet.active_topic,
        object_scope=packet.object_scope,
        object_id=packet.object_id,
        parent_object_id=packet.parent_object_id,
        dimension_axis=packet.dimension_axis,
        user_goal=packet.user_goal,
        current_tension=packet.current_tension,
        answer_shape=packet.answer_shape or _infer_answer_shape(request),
        active_workspace_id=str(caller_hints.get("active_workspace_id") or caller_hints.get("workspace_id") or ""),
        depth_mode=packet.context_policy.depth_mode,
        confidence=packet.confidence,
        bundle_layers=[],
        source_refs=list(request.get("source_refs", []) or []),
        reasoning_posture=packet.reasoning_posture,
        factual_anchor_level=packet.factual_anchor_level,
        bridge_behaviors=bridge_behaviors,
        attributes={
            "session_id": session_id,
            "domain_hints": list(request.get("domain_hints", []) or []),
            "caller_hints": caller_hints,
            "bridge_behavior_ids": list(packet.bridge_behaviors),
            "routing_source": packet.routing_source,
            "context_policy": packet.context_policy.to_dict(),
            "control_packet_id": packet.packet_id,
            "pipeline_id": packet.pipeline_id,
            "steering_constraints": list(packet.steering_constraints),
            "control_packet_metadata": dict(metadata or {}),
        },
    )
    if not context.confidence:
        context.confidence = _context_confidence(context.object_scope, context.active_topic, context.current_tension)
    previous = _latest_context_for_session(root, session_id)
    if previous is not None:
        switch_kind = _switch_kind(previous, context)
        if switch_kind:
            context.attributes["pending_switch_event"] = {
                "event_id": make_id("ctx-switch"),
                "request_id": context.request_id,
                "previous_context_id": previous.get("context_id", ""),
                "new_context_id": context.context_id,
                "trigger": "turn_classification",
                "switch_kind": switch_kind,
                "confidence": context.confidence,
                "retrieval_sources": [],
                "rollback_path": previous.get("context_id", ""),
                "timestamp": utc_now(),
                "attributes": {},
            }
    return context.to_dict()


def persist_control_packet(
    root: Path,
    packet: ControlPacket | Dict[str, Any],
    *,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    ensure_reasoning_runtime(root)
    payload = packet.to_dict() if isinstance(packet, ControlPacket) else dict(packet)
    row = {
        "packet": payload,
        "metadata": dict(metadata or {}),
        "timestamp": utc_now(),
    }
    append_jsonl(_control_packets_path(root), row)
    return row


def heuristic_classify_turn(root: Path, request: Dict[str, Any]) -> Dict[str, Any]:
    ensure_reasoning_runtime(root)
    caller_hints = request.get("caller_hints", {}) or {}
    bridge_state = load_bridge_state(root)
    session_id = str(request.get("session_id", "")).strip()
    active_topic = _infer_active_topic(request)
    object_scope = _infer_object_scope(request)
    user_goal = _infer_user_goal(request)
    factual_anchor_level = _infer_factual_anchor_level(request)
    reasoning_posture = _infer_reasoning_posture(request, factual_anchor_level, user_goal)
    bridge_behaviors = _match_bridge_behaviors(
        request,
        bridge_state,
        user_goal=user_goal,
        factual_anchor_level=factual_anchor_level,
        reasoning_posture=reasoning_posture,
        behavior_rules=load_bridge_behavior_specs(root),
    )
    object_id = str(caller_hints.get("object_id", "")).strip() or f"object:{active_topic.replace(' ', '-')}"
    context = ContextState(
        context_id=make_id("ctx"),
        request_id=str(request.get("request_id", "")),
        active_topic=active_topic,
        object_scope=object_scope,
        object_id=object_id,
        parent_object_id=caller_hints.get("parent_object_id"),
        dimension_axis=str(caller_hints.get("dimension_axis", "") or ""),
        user_goal=user_goal,
        current_tension=_infer_tension(request),
        answer_shape=_infer_answer_shape(request),
        active_workspace_id=str(caller_hints.get("active_workspace_id") or caller_hints.get("workspace_id") or ""),
        depth_mode=_infer_depth_mode(request),
        confidence=0.0,
        bundle_layers=[],
        source_refs=list(request.get("source_refs", []) or []),
        reasoning_posture=reasoning_posture,
        factual_anchor_level=factual_anchor_level,
        bridge_behaviors=bridge_behaviors,
        attributes={
            "session_id": session_id,
            "domain_hints": list(request.get("domain_hints", []) or []),
            "caller_hints": caller_hints,
            "bridge_behavior_ids": [behavior["behavior_id"] for behavior in bridge_behaviors],
        },
    )
    context.confidence = _context_confidence(context.object_scope, context.active_topic, context.current_tension)
    previous = _latest_context_for_session(root, session_id)
    if previous is not None:
        switch_kind = _switch_kind(previous, context)
        if switch_kind:
            context.attributes["pending_switch_event"] = {
                "event_id": make_id("ctx-switch"),
                "request_id": context.request_id,
                "previous_context_id": previous.get("context_id", ""),
                "new_context_id": context.context_id,
                "trigger": "turn_classification",
                "switch_kind": switch_kind,
                "confidence": context.confidence,
                "retrieval_sources": [],
                "rollback_path": previous.get("context_id", ""),
                "timestamp": utc_now(),
                "attributes": {},
            }
    return context.to_dict()


def bind_workspace(root: Path, context_state: Dict[str, Any]) -> Dict[str, Any]:
    state = dict(context_state)
    attributes = dict(state.get("attributes", {}) or {})
    caller_hints = attributes.get("caller_hints", {}) or {}
    if not state.get("active_workspace_id"):
        bridge_state = load_bridge_state(root)
        client_context = bridge_state.get("context", {}).get("client_context", {}) or {}
        state["active_workspace_id"] = str(
            caller_hints.get("workspace_id")
            or client_context.get("active_workspace_id")
            or client_context.get("workspace_id")
            or ""
        )
    return state


def _budget_for_depth(depth_mode: str, budget: Dict[str, Any] | None = None) -> Dict[str, Any]:
    defaults = {
        "focused": {"session_events": 4, "user_patterns": 2, "retrieval_limit": 4, "neighbor_limit": 2, "use_global": False},
        "contextual": {"session_events": 8, "user_patterns": 4, "retrieval_limit": 6, "neighbor_limit": 4, "use_global": True},
        "deep": {"session_events": 12, "user_patterns": 6, "retrieval_limit": 8, "neighbor_limit": 6, "use_global": True},
        "incognito": {"session_events": 0, "user_patterns": 0, "retrieval_limit": 0, "neighbor_limit": 0, "use_global": False},
    }
    resolved = dict(defaults.get(depth_mode, defaults["focused"]))
    if budget:
        resolved.update({key: value for key, value in budget.items() if key in resolved})
    return resolved


def _context_policy_from_state(state: Dict[str, Any]) -> Dict[str, Any] | None:
    attributes = state.get("attributes", {}) or {}
    policy = attributes.get("context_policy")
    return dict(policy) if isinstance(policy, dict) and policy else None


def _apply_layer_policy(layer_names: List[str], policy: Dict[str, Any] | None) -> List[str]:
    if not policy:
        return layer_names
    include_layers = [str(value) for value in policy.get("include_layers", []) or [] if str(value).strip()]
    exclude_layers = {str(value) for value in policy.get("exclude_layers", []) or [] if str(value).strip()}
    if include_layers:
        layer_names = [name for name in layer_names if name in include_layers]
    if exclude_layers:
        layer_names = [name for name in layer_names if name not in exclude_layers]
    return layer_names


def is_incognito_context(context_state: Dict[str, Any]) -> bool:
    policy = _context_policy_from_state(context_state)
    if policy and str(policy.get("depth_mode", "")).strip().lower() == "incognito":
        return True
    return str(context_state.get("depth_mode", "")).strip().lower() == "incognito"


def _canonical_layers() -> List[str]:
    return ["session", "workspace", "user", "global"]


def _default_allowed_layers_for_envelope(mode: str) -> List[str]:
    defaults = {
        "open": ["session", "workspace", "user", "global"],
        "bounded": ["session", "workspace", "user", "global"],
        "strict": ["session"],
        "incognito": ["session"],
    }
    return list(defaults.get(mode, defaults["bounded"]))


def _apply_session_envelope_to_layers(layer_names: List[str], envelope: Dict[str, Any]) -> List[str]:
    mode = str(envelope.get("mode", "bounded") or "bounded")
    allowed = [
        str(value)
        for value in (envelope.get("allowed_layers", []) or _default_allowed_layers_for_envelope(mode))
        if str(value).strip()
    ]
    allowed_set = set(allowed)
    blocked = {
        str(value)
        for value in envelope.get("default_blocked_layers", []) or []
        if str(value).strip() and str(value) not in allowed_set
    }
    explicit_excludes = {str(value) for value in envelope.get("explicit_excludes", []) or [] if str(value).strip()}
    if allowed:
        layer_names = [name for name in layer_names if name in allowed]
    if blocked:
        layer_names = [name for name in layer_names if name not in blocked]
    if explicit_excludes:
        layer_names = [name for name in layer_names if name not in explicit_excludes]
    return layer_names


def _infer_session_envelope_mode(state: Dict[str, Any], policy: Dict[str, Any] | None) -> str:
    attributes = state.get("attributes", {}) or {}
    caller_hints = attributes.get("caller_hints", {}) or {}
    explicit = str(
        caller_hints.get("envelope_mode")
        or attributes.get("session_envelope_mode")
        or (policy or {}).get("envelope_mode", "")
    ).strip().lower()
    if explicit in {"open", "bounded", "strict", "incognito"}:
        return explicit
    if is_incognito_context(state) or (policy and str(policy.get("mode", "")).strip().lower() == "none"):
        return "incognito"
    include_layers = [str(value) for value in (policy or {}).get("include_layers", []) or [] if str(value).strip()]
    exclude_layers = {str(value) for value in (policy or {}).get("exclude_layers", []) or [] if str(value).strip()}
    if exclude_layers.intersection({"workspace", "user", "global"}):
        return "strict"
    if include_layers == ["session"]:
        return "strict"
    if str(state.get("depth_mode", "")).strip().lower() == "deep":
        return "open"
    return "bounded"


def build_session_envelope(
    context_state: Dict[str, Any],
    *,
    policy: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    state = dict(context_state)
    attributes = state.get("attributes", {}) or {}
    caller_hints = attributes.get("caller_hints", {}) or {}
    session_id = str(attributes.get("session_id", "")).strip()
    mode = _infer_session_envelope_mode(state, policy)
    explicit_includes = [str(value) for value in (policy or {}).get("include_layers", []) or [] if str(value).strip()]
    explicit_excludes = [str(value) for value in (policy or {}).get("exclude_layers", []) or [] if str(value).strip()]
    allowed_layers = explicit_includes or _default_allowed_layers_for_envelope(mode)
    if explicit_excludes:
        allowed_layers = [layer for layer in allowed_layers if layer not in set(explicit_excludes)]
    default_blocked = [layer for layer in _canonical_layers() if layer not in _default_allowed_layers_for_envelope(mode)]
    learning_mode = {
        "open": "allowed",
        "bounded": "allowed",
        "strict": "session_scoped",
        "incognito": "disabled",
    }[mode]
    persistence_mode = {
        "open": "gated",
        "bounded": "gated",
        "strict": "manual",
        "incognito": "disabled",
    }[mode]
    cross_session_mode = {
        "open": "routed",
        "bounded": "limited",
        "strict": "disabled",
        "incognito": "disabled",
    }[mode]
    sidecar_mode = {
        "open": "attached",
        "bounded": "isolated_by_default",
        "strict": "isolated",
        "incognito": "isolated",
    }[mode]
    return {
        "envelope_id": make_id("envelope"),
        "session_id": session_id,
        "request_id": str(state.get("request_id", "")),
        "mode": mode,
        "allowed_layers": allowed_layers,
        "default_blocked_layers": default_blocked,
        "learning_mode": learning_mode,
        "persistence_mode": persistence_mode,
        "cross_session_mode": cross_session_mode,
        "sidecar_mode": sidecar_mode,
        "explicit_includes": explicit_includes,
        "explicit_excludes": explicit_excludes,
        "workspace_id": str(state.get("active_workspace_id", "") or caller_hints.get("workspace_id", "") or ""),
    }


_BRIDGE_LAYER_TO_GRANT = {
    "session": "session",
    "workspace": "workspace",
    "user": "user",
    "global": "governed_global",
}
_GRANT_LAYER_TO_BRIDGE = {
    "session": "session",
    "workspace": "workspace",
    "user": "user",
    "governed_global": "global",
    "explicit_pin": "session",
    "ephemeral_turn": "session",
}


def effective_grant_normalization_enabled(root: Path | None) -> bool:
    if root is None:
        return True
    try:
        from .bridge_controller import load_bridge_config

        return bool(load_bridge_config(root).get("effective_grant_normalization_v1", True))
    except Exception:
        return True


def build_effective_grant_from_context(
    context_state: Dict[str, Any],
    policy: Dict[str, Any] | None,
    session_envelope: Dict[str, Any],
):
    from .disclosure_contracts import RequestedGrant, normalize_effective_grant

    state = dict(context_state)
    policy_payload = dict(policy or {})
    mode = str(
        policy_payload.get("envelope_mode")
        or session_envelope.get("mode", "bounded")
        or "bounded"
    )
    include_layers = [str(value) for value in policy_payload.get("include_layers", []) or [] if str(value).strip()]
    exclude_layers = [str(value) for value in policy_payload.get("exclude_layers", []) or [] if str(value).strip()]
    exclude_layers.extend(
        str(value) for value in session_envelope.get("explicit_excludes", []) or [] if str(value).strip()
    )
    default_layers = _default_allowed_layers_for_envelope(mode)
    requested_layers = [_BRIDGE_LAYER_TO_GRANT.get(layer, layer) for layer in (include_layers or default_layers)]
    explicit_denials = [_BRIDGE_LAYER_TO_GRANT.get(layer, layer) for layer in exclude_layers]
    attributes = dict(state.get("attributes", {}) or {})
    policy_specified = "token_budget" in policy_payload
    depth_mode = str(state.get("depth_mode", "focused") or "focused")
    from .disclosure_budget_allocator import resolve_token_budget

    requested = RequestedGrant(
        grant_id=make_id("grant"),
        request_id=str(state.get("request_id", "")),
        envelope=mode,
        requested_layers=requested_layers,
        requested_refs=[str(value) for value in state.get("source_refs", []) or [] if str(value).strip()],
        dimensions=[],
        shape_maturity="candidate",
        token_budget=resolve_token_budget(
            int(policy_payload.get("token_budget", 0) or 0),
            depth_mode=depth_mode,
            policy_specified=policy_specified,
        ),
        persistence_mode=str(session_envelope.get("persistence_mode", "gated") or "gated"),
        explicit_pins=[str(value) for value in attributes.get("explicit_pins", []) or [] if str(value).strip()],
        explicit_denials=list(dict.fromkeys(explicit_denials)),
        cross_ocean=bool(policy_payload.get("cross_ocean")) if "cross_ocean" in policy_payload else None,
    )
    workspace_layers = ["session", "workspace", "user", "governed_global"] if state.get("active_workspace_id") else None
    grant = normalize_effective_grant(requested, workspace_layers=workspace_layers)
    grant_dict = grant.to_dict()
    grant_dict["token_budget_specified"] = policy_specified
    from .disclosure_contracts import EffectiveGrant

    return EffectiveGrant.from_dict(grant_dict)


def _grant_governed_search_allowed(
    effective_grant: Any,
    *,
    resolved_budget: Dict[str, Any],
    active_topic: str,
) -> bool:
    if not str(active_topic or "").strip():
        return False
    if not resolved_budget.get("use_global"):
        return False
    if str(getattr(effective_grant, "envelope", "") or "").strip().lower() == "incognito":
        return False
    layers = set(getattr(effective_grant, "effective_layers", []) or [])
    if "governed_global" in layers:
        return True
    if "explicit_pin" in layers and list(getattr(effective_grant, "explicit_pins", []) or []):
        return True
    return False


def _grant_governed_search_kwargs(
    effective_grant: Any,
    *,
    include_cross_pond: bool,
) -> Dict[str, Any]:
    return {
        "envelope_mode": str(getattr(effective_grant, "envelope", "") or "bounded"),
        "explicit_pins": list(getattr(effective_grant, "explicit_pins", []) or []),
        "include_cross_pond": bool(include_cross_pond),
    }


def effective_layers_to_bridge_layers(grant, available_layers: List[str]) -> List[str]:
    available = set(available_layers)
    bridge_layers: List[str] = []
    for layer in grant.effective_layers:
        bridge_layer = _GRANT_LAYER_TO_BRIDGE.get(layer, layer)
        if bridge_layer in available and bridge_layer not in bridge_layers:
            bridge_layers.append(bridge_layer)
    if "session" in available and "session" not in bridge_layers:
        bridge_layers.insert(0, "session")
    return bridge_layers


def build_frame_spec(
    context_state: Dict[str, Any],
    *,
    envelope: Dict[str, Any],
    budget: Dict[str, Any],
    session_rows: List[Dict[str, Any]],
    workspace_layer: Dict[str, Any],
    user_patterns: List[Dict[str, Any]],
    bridge_state: Dict[str, Any],
    retrieval_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    state = dict(context_state)
    attributes = state.get("attributes", {}) or {}
    caller_hints = attributes.get("caller_hints", {}) or {}
    session_id = str(attributes.get("session_id", "")).strip()
    frame_id = make_id("frame")
    selectors: List[Dict[str, Any]] = []
    if session_id and session_rows:
        selectors.append(
            {
                "selector_id": f"{frame_id}:session",
                "layer": "session",
                "match_mode": "required",
                "query": session_id,
                "filters": {"session_id": session_id, "max_events": int(budget.get("session_events", 0) or 0)},
                "reason": "Carry recent in-session continuity.",
            }
        )
    if workspace_layer:
        selectors.append(
            {
                "selector_id": f"{frame_id}:workspace",
                "layer": "workspace",
                "match_mode": "preferred",
                "query": str(workspace_layer.get("workspace_id", "") or workspace_layer.get("thought_id", "")),
                "filters": dict(workspace_layer),
                "reason": "Bind retrieval to the active workspace surface.",
            }
        )
    if user_patterns or bridge_state.get("presentation", {}).get("current_mode") or bridge_state.get("personalization"):
        selectors.append(
            {
                "selector_id": f"{frame_id}:user",
                "layer": "user",
                "match_mode": "optional",
                "query": "bridge_state",
                "filters": {"pattern_count": len(user_patterns)},
                "reason": "Allow bounded personalization and presentation continuity.",
            }
        )
    if state.get("active_topic") and retrieval_bundle.get("count"):
        selectors.append(
            {
                "selector_id": f"{frame_id}:global",
                "layer": "global",
                "match_mode": "preferred",
                "query": str(retrieval_bundle.get("query", "") or state.get("active_topic", "")),
                "filters": {
                    "retrieval_limit": int(budget.get("retrieval_limit", 0) or 0),
                    "neighbor_limit": int(budget.get("neighbor_limit", 0) or 0),
                    "include_cross_pond": bool(retrieval_bundle.get("include_cross_pond", False)),
                },
                "reason": "Allow bounded semantic retrieval around the active topic.",
            }
        )
    return {
        "frame_id": frame_id,
        "request_id": str(state.get("request_id", "")),
        "session_id": session_id,
        "workspace_id": str(state.get("active_workspace_id", "") or caller_hints.get("workspace_id", "") or ""),
        "active_topic": str(state.get("active_topic", "")),
        "object_scope": str(state.get("object_scope", "")),
        "object_id": str(state.get("object_id", "")),
        "envelope_mode": str(envelope.get("mode", "bounded")),
        "selectors": selectors,
        "pins": [str(value) for value in state.get("source_refs", []) or [] if str(value).strip()],
        "exclusions": [{"kind": "layer", "value": value} for value in envelope.get("explicit_excludes", []) or []],
        "budget_hints": {
            "max_blocks": len(selectors),
            "max_session_events": int(budget.get("session_events", 0) or 0),
            "max_capsules": int(budget.get("retrieval_limit", 0) or 0),
            "max_neighbors": int(budget.get("neighbor_limit", 0) or 0),
            "allow_cross_pond": bool(retrieval_bundle.get("include_cross_pond", False)),
            "allow_workspace_context": bool(workspace_layer),
        },
        "preview_only": True,
    }


def deterministic_budget_enforcement_enabled(root: Path) -> bool:
    try:
        from .disclosure_budget_allocator import deterministic_budget_enforcement_enabled as _enabled

        return bool(_enabled(root))
    except Exception:
        return True


def orient_first_compose_enabled(root: Path) -> bool:
    try:
        from .orient_first_compose import orient_first_compose_enabled as _enabled

        return bool(_enabled(root))
    except Exception:
        return True


def disclosure_service_enabled(root: Path) -> bool:
    from .disclosure_rollout import resolve_surface_rollout_mode

    return resolve_surface_rollout_mode(root, "bridge") != "legacy"


def execution_audit_isolation_enabled(root: Path | None) -> bool:
    if root is None:
        return True
    try:
        from .bridge_controller import load_bridge_config

        return bool(load_bridge_config(root).get("execution_audit_isolation_v1", True))
    except Exception:
        return True


def assemble_frame_bundle(
    context_state: Dict[str, Any],
    *,
    frame_spec: Dict[str, Any],
    envelope: Dict[str, Any],
    disclosed_layers: List[str],
    session_rows: List[Dict[str, Any]],
    workspace_layer: Dict[str, Any],
    user_patterns: List[Dict[str, Any]],
    bridge_state: Dict[str, Any],
    retrieval_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    state = dict(context_state)
    session_id = str((state.get("attributes", {}) or {}).get("session_id", "")).strip()
    selectors_by_layer = {row["layer"]: row for row in frame_spec.get("selectors", []) or []}
    candidate_blocks: List[Dict[str, Any]] = []

    if session_rows:
        candidate_blocks.append(
            {
                "block_id": f"{frame_spec['frame_id']}:session",
                "layer": "session",
                "source_ref": f"memory/events/{session_id}.jsonl" if session_id else "memory/events",
                "source_kind": "session_events",
                "summary": f"{len(session_rows)} session event(s)",
                "reason_included": "Recent session continuity is available.",
                "selector_ids": [selectors_by_layer["session"]["selector_id"]] if "session" in selectors_by_layer else [],
                "token_estimate": max(1, len(session_rows)) * 40,
                "freshness_state": "current",
            }
        )
    if workspace_layer:
        candidate_blocks.append(
            {
                "block_id": f"{frame_spec['frame_id']}:workspace",
                "layer": "workspace",
                "source_ref": f"workspace:{workspace_layer.get('workspace_id', '') or workspace_layer.get('thought_id', '')}",
                "source_kind": "workspace_binding",
                "summary": f"workspace binding for {workspace_layer.get('workspace_id', '') or workspace_layer.get('thought_id', '')}",
                "reason_included": "Workspace context is available for the active turn.",
                "selector_ids": [selectors_by_layer["workspace"]["selector_id"]] if "workspace" in selectors_by_layer else [],
                "token_estimate": 20,
                "freshness_state": "current",
            }
        )
    if user_patterns or bridge_state.get("presentation", {}).get("current_mode") or bridge_state.get("personalization"):
        candidate_blocks.append(
            {
                "block_id": f"{frame_spec['frame_id']}:user",
                "layer": "user",
                "source_ref": "reasoning_runtime/bridge_state.json",
                "source_kind": "bridge_state",
                "summary": f"{len(user_patterns)} user pattern(s)",
                "reason_included": "User-local continuity is available.",
                "selector_ids": [selectors_by_layer["user"]["selector_id"]] if "user" in selectors_by_layer else [],
                "token_estimate": max(1, len(user_patterns)) * 30,
                "freshness_state": "current",
            }
        )
    if retrieval_bundle.get("count"):
        candidate_blocks.append(
            {
                "block_id": f"{frame_spec['frame_id']}:global",
                "layer": "global",
                "source_ref": str((retrieval_bundle.get("source_refs", []) or [f"retrieval:{retrieval_bundle.get('query', '')}"])[0]),
                "source_kind": "semantic_retrieval",
                "summary": f"{int(retrieval_bundle.get('count', 0) or 0)} retrieval candidate(s)",
                "reason_included": "Bounded semantic retrieval found relevant context.",
                "selector_ids": [selectors_by_layer["global"]["selector_id"]] if "global" in selectors_by_layer else [],
                "token_estimate": max(1, int(retrieval_bundle.get("count", 0) or 0)) * 60,
                "freshness_state": "unknown",
            }
        )

    included_blocks: List[Dict[str, Any]] = []
    suppressed_blocks: List[Dict[str, Any]] = []
    disclosed_set = set(disclosed_layers)
    for block in candidate_blocks:
        disclosure_state = "included" if block["layer"] in disclosed_set else "suppressed"
        row = {**block, "disclosure_state": disclosure_state}
        if disclosure_state == "included":
            included_blocks.append(row)
        else:
            suppressed_blocks.append(row)

    rejected_selectors: List[Dict[str, Any]] = []
    for selector in frame_spec.get("selectors", []) or []:
        if selector["layer"] not in {block["layer"] for block in candidate_blocks}:
            rejected_selectors.append(
                {
                    "selector_id": selector["selector_id"],
                    "layer": selector["layer"],
                    "reason": "no_matches",
                }
            )

    source_refs: List[str] = []
    for row in included_blocks + suppressed_blocks:
        source_ref = str(row.get("source_ref", "")).strip()
        if source_ref and source_ref not in source_refs:
            source_refs.append(source_ref)
    for row in state.get("source_refs", []) or []:
        source_ref = str(row).strip()
        if source_ref and source_ref not in source_refs:
            source_refs.append(source_ref)

    assembly_status = "empty"
    if included_blocks:
        assembly_status = "partial" if (suppressed_blocks or rejected_selectors) else "complete"

    return {
        "bundle_id": make_id("frame-bundle"),
        "frame_id": frame_spec["frame_id"],
        "request_id": str(state.get("request_id", "")),
        "session_id": session_id,
        "workspace_id": str(state.get("active_workspace_id", "")),
        "envelope_mode": str(envelope.get("mode", "bounded")),
        "assembly_status": assembly_status,
        "included_blocks": included_blocks,
        "rejected_selectors": rejected_selectors,
        "suppressed_blocks": suppressed_blocks,
        "provenance_summary": {
            "source_refs": source_refs,
            "included_layer_count": len(included_blocks),
            "suppressed_layer_count": len(suppressed_blocks),
        },
        "assembly_metrics": {
            "session_event_count": len(session_rows),
            "workspace_block_count": 1 if workspace_layer else 0,
            "user_pattern_count": len(user_patterns),
            "global_capsule_count": int(retrieval_bundle.get("count", 0) or 0),
            "rejected_selector_count": len(rejected_selectors),
            "suppressed_block_count": len(suppressed_blocks),
            "estimated_token_cost": sum(int(row.get("token_estimate", 0) or 0) for row in included_blocks + suppressed_blocks),
        },
    }


def split_frame_assembly(assembly: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    included_blocks = []
    for row in assembly.get("included_blocks", []) or []:
        clean = {key: value for key, value in dict(row).items() if key != "disclosure_state"}
        included_blocks.append(clean)

    suppressed_blocks = [dict(row) for row in assembly.get("suppressed_blocks", []) or []]
    rejected_selectors = [dict(row) for row in assembly.get("rejected_selectors", []) or []]
    included_refs: List[str] = []
    for row in included_blocks:
        source_ref = str(row.get("source_ref", "")).strip()
        if source_ref and source_ref not in included_refs:
            included_refs.append(source_ref)

    audit_id = make_id("frame-audit")
    execution_bundle = {
        key: value
        for key, value in assembly.items()
        if key not in {"suppressed_blocks", "provenance_summary", "assembly_metrics"}
    }
    execution_bundle["included_blocks"] = included_blocks
    execution_bundle["frame_audit_id"] = audit_id
    execution_bundle["provenance_summary"] = {
        "source_refs": included_refs,
        "included_layer_count": len(included_blocks),
    }
    execution_bundle["assembly_metrics"] = {
        **dict(assembly.get("assembly_metrics", {}) or {}),
        "suppressed_block_count": 0,
        "estimated_token_cost": sum(int(row.get("token_estimate", 0) or 0) for row in included_blocks),
    }

    frame_audit = {
        "audit_id": audit_id,
        "frame_id": assembly.get("frame_id", ""),
        "request_id": assembly.get("request_id", ""),
        "session_id": assembly.get("session_id", ""),
        "workspace_id": assembly.get("workspace_id", ""),
        "envelope_mode": assembly.get("envelope_mode", ""),
        "assembly_status": assembly.get("assembly_status", ""),
        "omitted_blocks": [
            {
                "block_id": row.get("block_id", ""),
                "layer": row.get("layer", ""),
                "reason_code": "layer_not_disclosed",
                "summary": row.get("summary", ""),
                "source_ref": row.get("source_ref", ""),
                "disclosure_state": row.get("disclosure_state", "suppressed"),
            }
            for row in suppressed_blocks
        ],
        "suppressed_blocks": suppressed_blocks,
        "rejected_selectors": rejected_selectors,
        "provenance_summary": dict(assembly.get("provenance_summary", {}) or {}),
        "assembly_metrics": dict(assembly.get("assembly_metrics", {}) or {}),
    }
    return execution_bundle, frame_audit


def build_frame_audit(
    context_state: Dict[str, Any],
    *,
    frame_spec: Dict[str, Any],
    envelope: Dict[str, Any],
    disclosed_layers: List[str],
    session_rows: List[Dict[str, Any]],
    workspace_layer: Dict[str, Any],
    user_patterns: List[Dict[str, Any]],
    bridge_state: Dict[str, Any],
    retrieval_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    assembly = assemble_frame_bundle(
        context_state,
        frame_spec=frame_spec,
        envelope=envelope,
        disclosed_layers=disclosed_layers,
        session_rows=session_rows,
        workspace_layer=workspace_layer,
        user_patterns=user_patterns,
        bridge_state=bridge_state,
        retrieval_bundle=retrieval_bundle,
    )
    _, frame_audit = split_frame_assembly(assembly)
    return frame_audit


def build_frame_bundle(
    context_state: Dict[str, Any],
    *,
    frame_spec: Dict[str, Any],
    envelope: Dict[str, Any],
    disclosed_layers: List[str],
    session_rows: List[Dict[str, Any]],
    workspace_layer: Dict[str, Any],
    user_patterns: List[Dict[str, Any]],
    bridge_state: Dict[str, Any],
    retrieval_bundle: Dict[str, Any],
    root: Path | None = None,
) -> Dict[str, Any]:
    assembly = assemble_frame_bundle(
        context_state,
        frame_spec=frame_spec,
        envelope=envelope,
        disclosed_layers=disclosed_layers,
        session_rows=session_rows,
        workspace_layer=workspace_layer,
        user_patterns=user_patterns,
        bridge_state=bridge_state,
        retrieval_bundle=retrieval_bundle,
    )
    if execution_audit_isolation_enabled(root):
        execution_bundle, _ = split_frame_assembly(assembly)
        return execution_bundle
    return assembly


def _assemble_bridge_context_bundle_impl(
    root: Path,
    context_state: Dict[str, Any],
    *,
    budget: Dict[str, Any] | None = None,
    candidate_search: Any | None = None,
) -> Dict[str, Any]:
    ensure_reasoning_runtime(root)
    state = bind_workspace(root, context_state)
    policy = _context_policy_from_state(state)
    depth_mode = str(state.get("depth_mode", "focused"))
    if policy and policy.get("depth_mode"):
        depth_mode = str(policy["depth_mode"])
        state["depth_mode"] = depth_mode

    resolved_budget = _budget_for_depth(depth_mode, budget=budget)
    if policy:
        if "retrieval_limit" in policy:
            resolved_budget["retrieval_limit"] = int(policy.get("retrieval_limit", 0) or 0)
        if "neighbor_limit" in policy:
            resolved_budget["neighbor_limit"] = int(policy.get("neighbor_limit", 0) or 0)
        if depth_mode == "incognito" or str(policy.get("mode", "")).strip().lower() == "none":
            resolved_budget["use_global"] = False
            resolved_budget["session_events"] = 0
            resolved_budget["user_patterns"] = 0
        elif depth_mode in {"contextual", "deep"}:
            resolved_budget["use_global"] = True

    attributes = state.get("attributes", {}) or {}
    session_id = str(attributes.get("session_id", "")).strip()
    caller_hints = dict(attributes.get("caller_hints", {}) or {})

    from .bridge_session_context import (
        CONTEXT_MODE_DEEP_GLOBAL,
        CONTEXT_MODE_SESSION_ONLY,
        build_dynamic_session_context,
        resolve_context_retrieval_mode,
        session_rows_for_bundle,
        tracking_config,
    )

    session_context: Dict[str, Any] | None = None
    session_rows: List[Dict[str, Any]] = []
    retrieval_mode = resolve_context_retrieval_mode(
        root,
        session_id=session_id,
        depth_mode=depth_mode,
        policy=policy,
        caller_hints=caller_hints,
    )
    resolved_budget, retrieval_mode, note_agent_state = _apply_note_agent_overrides(
        resolved_budget,
        attributes,
        retrieval_mode,
        orient_first_enabled=orient_first_compose_enabled(root),
    )
    if retrieval_mode == CONTEXT_MODE_SESSION_ONLY:
        resolved_budget["use_global"] = False
    elif retrieval_mode == CONTEXT_MODE_DEEP_GLOBAL:
        resolved_budget["use_global"] = True

    if session_id and resolved_budget["session_events"] > 0:
        try:
            session_context = build_dynamic_session_context(
                root,
                session_id,
                max_turns=min(
                    max(int(resolved_budget["session_events"]), 1),
                    tracking_config(root)["max_turn_window"],
                ),
            )
            session_context["context_mode"] = retrieval_mode
            session_rows = session_rows_for_bundle(
                session_context,
                max_events=int(resolved_budget["session_events"]),
            )
        except ValueError:
            session_rows = read_jsonl(session_events_path(root, session_id))[-resolved_budget["session_events"] :]

    bridge_state = load_bridge_state(root)
    user_patterns = list(bridge_state.get("behavior_patterns", []) or [])[: resolved_budget["user_patterns"]]

    workspace_layer: Dict[str, Any] = {}
    thought_id = str(attributes.get("caller_hints", {}).get("thought_id", "")).strip()
    if state.get("active_workspace_id"):
        workspace_layer["workspace_id"] = state["active_workspace_id"]
    if thought_id:
        workspace_layer["thought_id"] = thought_id

    retrieval_bundle = {
        "query": state.get("active_topic", ""),
        "seed_capsules": [],
        "related_capsules": [],
        "included_links": [],
        "source_refs": [],
        "count": 0,
        "alias_hits": [],
        "anchor_pond": "",
        "include_cross_pond": False,
    }
    note_retrieval_policy = (
        dict((note_agent_state or {}).get("retrieval_policy", {}) or {})
        if note_agent_state
        else {}
    )
    session_envelope = build_session_envelope(state, policy=policy)
    effective_grant = build_effective_grant_from_context(state, policy, session_envelope)

    if note_retrieval_policy:
        include_cross_pond = bool(note_retrieval_policy.get("cross_ocean"))
    else:
        include_cross_pond = bool(effective_grant.cross_ocean)

    search_kwargs = _grant_governed_search_kwargs(effective_grant, include_cross_pond=include_cross_pond)
    active_topic = str(state.get("active_topic", "") or "")
    if _grant_governed_search_allowed(
        effective_grant,
        resolved_budget=resolved_budget,
        active_topic=active_topic,
    ):
        if candidate_search is not None:
            retrieval_bundle = candidate_search.build_retrieval_bundle(
                root,
                active_topic,
                limit=int(resolved_budget["retrieval_limit"]),
                neighbor_limit=int(resolved_budget["neighbor_limit"]),
                **search_kwargs,
            )
        else:
            retrieval_bundle = build_retrieval_bundle(
                root,
                active_topic,
                limit=int(resolved_budget["retrieval_limit"]),
                neighbor_limit=int(resolved_budget["neighbor_limit"]),
                **search_kwargs,
            )

    orient_first_enabled = orient_first_compose_enabled(root)
    from .library_tracker import CHAT_CONVERTER_SEED_CORPUS_REVISION
    from .orient_first_compose import build_active_state_snapshot, load_orient_first_config

    orient_config = load_orient_first_config(root)
    active_state_snapshot = build_active_state_snapshot(
        state,
        {
            "request_id": state.get("request_id", ""),
            "active_topic": state.get("active_topic", ""),
            "user_goal": state.get("user_goal", ""),
            "reasoning_posture": state.get("reasoning_posture", ""),
            "object_scope": state.get("object_scope", "same_main"),
        },
        workspace_layer=workspace_layer,
        session_envelope=session_envelope,
        corpus_revision=CHAT_CONVERTER_SEED_CORPUS_REVISION,
    )

    available_layers = ["session"]
    if workspace_layer:
        available_layers.append("workspace")
    if user_patterns or bridge_state.get("personalization") or bridge_state.get("presentation", {}).get("current_mode"):
        available_layers.append("user")
    if retrieval_bundle.get("count") and "governed_global" in set(effective_grant.effective_layers or []):
        available_layers.append("global")
    if note_retrieval_policy.get("include_layers"):
        allowed_layers = {str(value) for value in note_retrieval_policy.get("include_layers", []) or []}
        available_layers = [layer for layer in available_layers if layer in allowed_layers]
    if note_retrieval_policy.get("exclude_layers"):
        blocked_layers = {str(value) for value in note_retrieval_policy.get("exclude_layers", []) or []}
        available_layers = [layer for layer in available_layers if layer not in blocked_layers]

    active_state_transition: Dict[str, Any] = {}
    active_state_continuity_on = False
    try:
        from .active_state_continuity import active_state_continuity_enabled, apply_active_state_continuity

        active_state_continuity_on = active_state_continuity_enabled(
            root,
            cohort_key=str(state.get("request_id", "") or ""),
        )
        if active_state_continuity_on:
            active_state_snapshot, active_state_transition = apply_active_state_continuity(
                root,
                active_state_snapshot,
                effective_grant=effective_grant.to_dict(),
                session_envelope=session_envelope,
                surface="bridge",
                context_state=state,
            )
    except Exception:
        active_state_transition = {}
    if effective_grant_normalization_enabled(root):
        layer_names = effective_layers_to_bridge_layers(effective_grant, available_layers)
    else:
        layer_names = list(available_layers)
        layer_names = _apply_layer_policy(layer_names, policy)
        layer_names = _apply_session_envelope_to_layers(layer_names, session_envelope)

    widen_grant_id = str(
        (attributes.get("caller_hints", {}) or {}).get("second_pass_widen_grant_id")
        or (attributes.get("caller_hints", {}) or {}).get("widen_grant_id")
        or ""
    ).strip()
    if (
        widen_grant_id
        and note_agent_state
        and not note_agent_state.get("widen_blocked")
        and "global" in note_retrieval_policy.get("include_layers", [])
        and retrieval_bundle.get("count")
    ):
        if "global" not in layer_names and "global" in available_layers:
            layer_names.append("global")
        if "governed_global" not in effective_grant.effective_layers:
            effective_grant = replace(
                effective_grant,
                effective_layers=[*effective_grant.effective_layers, "governed_global"],
                narrowing_reasons=[
                    *list(effective_grant.narrowing_reasons),
                    {
                        "code": "second_pass_widen_grant",
                        "field": "effective_layers",
                        "requested": list(effective_grant.effective_layers),
                        "effective": [*effective_grant.effective_layers, "governed_global"],
                        "reason": f"Explicit second-pass widen grant {widen_grant_id}",
                    },
                ],
            )

    state["bundle_layers"] = layer_names
    frame_spec = build_frame_spec(
        state,
        envelope=session_envelope,
        budget=resolved_budget,
        session_rows=session_rows,
        workspace_layer=workspace_layer,
        user_patterns=user_patterns,
        bridge_state=bridge_state,
        retrieval_bundle=retrieval_bundle,
    )
    frame_assembly = assemble_frame_bundle(
        state,
        frame_spec=frame_spec,
        envelope=session_envelope,
        disclosed_layers=layer_names,
        session_rows=session_rows,
        workspace_layer=workspace_layer,
        user_patterns=user_patterns,
        bridge_state=bridge_state,
        retrieval_bundle=retrieval_bundle,
    )
    budget_audit: Dict[str, Any] = {}
    if deterministic_budget_enforcement_enabled(root):
        from .disclosure_budget_allocator import apply_frame_budget_to_assembly

        budget_audit = apply_frame_budget_to_assembly(
            frame_assembly,
            context_state=state,
            effective_grant=effective_grant.to_dict(),
            root=root,
            corpus_revision=CHAT_CONVERTER_SEED_CORPUS_REVISION,
            session_event_count=len(session_rows),
        )
    if execution_audit_isolation_enabled(root):
        frame_bundle, frame_audit = split_frame_assembly(frame_assembly)
    else:
        frame_bundle = frame_assembly
        frame_audit = {}
    if budget_audit:
        dropped_blocks = list(budget_audit.get("dropped_blocks", []) or [])
        if dropped_blocks:
            frame_audit.setdefault("omitted_blocks", [])
            frame_audit["omitted_blocks"].extend(
                {
                    "block_id": row.get("block_id", ""),
                    "layer": row.get("layer", ""),
                    "reason_code": "budget_insufficient",
                    "summary": row.get("summary", ""),
                    "source_ref": row.get("source_ref", ""),
                    "disclosure_state": "dropped",
                }
                for row in dropped_blocks
            )
        frame_audit["drop_ledger"] = list(budget_audit.get("drop_ledger", []) or [])
        frame_audit["budget_ledger"] = dict(budget_audit.get("budget_ledger", {}) or {})
        frame_audit["budget_summary"] = dict(budget_audit.get("budget_summary", {}) or {})
        frame_audit["budget_policy_hash"] = str(budget_audit.get("policy_hash", "") or "")
        frame_bundle["budget_summary"] = dict(budget_audit.get("budget_summary", {}) or {})
        frame_bundle["result_status"] = str(budget_audit.get("result_status", "") or frame_bundle.get("result_status", "disclosed"))
        if "drop_ledger" in frame_bundle:
            del frame_bundle["drop_ledger"]

    bundle = {
        "context_state": state,
        "budget": resolved_budget,
        "context_retrieval_mode": retrieval_mode,
        "session_context": session_context or {},
        "session_envelope": session_envelope,
        "frame_spec": frame_spec,
        "frame_bundle": frame_bundle,
        "frame_audit": frame_audit,
        "effective_grant": effective_grant.to_dict(),
        "session_local": session_rows if "session" in layer_names else [],
        "workspace_local": workspace_layer if "workspace" in layer_names else {},
        "user_local": {
            "behavior_patterns": user_patterns if "user" in layer_names else [],
            "presentation_mode": bridge_state.get("presentation", {}).get("current_mode", "") if "user" in layer_names else "",
            "personalization": bridge_state.get("personalization", {}) if "user" in layer_names else {},
        },
        "global_fallback": retrieval_bundle if "global" in layer_names else {
            "query": state.get("active_topic", ""),
            "seed_capsules": [],
            "related_capsules": [],
            "included_links": [],
            "source_refs": [],
            "count": 0,
            "alias_hits": [],
            "anchor_pond": "",
            "include_cross_pond": False,
        },
        "active_state_snapshot": active_state_snapshot,
        "active_state_transition": active_state_transition,
        "active_state_continuity_v1": active_state_continuity_on,
        "orient_first_compose_v1": orient_first_enabled,
        "orientation_max_chars": int(orient_config.get("orientation_max_chars", 480) or 480),
    }
    if policy:
        bundle["context_policy"] = policy
    bundle["execution_audit_isolation_v1"] = execution_audit_isolation_enabled(root)
    bundle["deterministic_budget_enforcement_v1"] = deterministic_budget_enforcement_enabled(root)
    bundle["orient_first_compose_v1"] = orient_first_enabled
    if budget_audit:
        bundle["budget_audit"] = {
            "result_status": budget_audit.get("result_status", ""),
            "budget_ledger": dict(budget_audit.get("budget_ledger", {}) or {}),
            "drop_ledger": list(budget_audit.get("drop_ledger", []) or []),
            "estimator_version": budget_audit.get("estimator_version", ""),
            "reservation_version": budget_audit.get("reservation_version", ""),
        }
        bundle["result_status"] = str(budget_audit.get("result_status", "") or "disclosed")

    pending = state.get("attributes", {}).get("pending_switch_event")
    if pending:
        pending["retrieval_sources"] = list(retrieval_bundle.get("source_refs", []))
    from .bounded_view_disclosure_adapter import merge_bounded_view_evidence_into_bundle

    merge_bounded_view_evidence_into_bundle(
        root,
        bundle,
        effective_grant.to_dict(),
        surface="bridge",
    )
    return bundle


def get_context_bundle(
    root: Path,
    context_state: Dict[str, Any],
    *,
    budget: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    from .disclosure_rollout import (
        compare_bridge_rollout_bundles,
        record_rollout_shadow_receipt,
        resolve_execution_path,
        resolve_surface_rollout_mode,
    )

    cohort_key = str(
        context_state.get("request_id", "")
        or context_state.get("context_id", "")
        or ""
    )
    execution_path = resolve_execution_path(root, "bridge", cohort_key=cohort_key)
    rollout_mode = resolve_surface_rollout_mode(root, "bridge")

    if execution_path == "shared":
        from .bridge_disclosure_adapter import disclose_for_bridge

        bundle = disclose_for_bridge(root, context_state, budget=budget)
        bundle["disclosure_rollout_mode"] = rollout_mode
        return bundle

    legacy_bundle = _assemble_bridge_context_bundle_impl(root, context_state, budget=budget)
    legacy_bundle["disclosure_receipt"] = _record_bridge_disclosure_receipt(root, legacy_bundle)
    legacy_bundle["disclosure_rollout_mode"] = rollout_mode

    if execution_path == "shadow":
        try:
            from .bridge_disclosure_adapter import disclose_for_bridge

            shared_bundle = disclose_for_bridge(root, context_state, budget=budget)
            comparison = compare_bridge_rollout_bundles(legacy_bundle, shared_bundle)
            shadow_record = {
                "surface": "bridge",
                "mode": "shadow",
                **comparison,
            }
            legacy_bundle["disclosure_rollout_shadow"] = shadow_record
            record_rollout_shadow_receipt(
                root,
                shadow_record,
                surface="bridge",
                cohort_key=cohort_key,
            )
        except Exception as exc:
            legacy_bundle["disclosure_rollout_shadow"] = {
                "surface": "bridge",
                "mode": "shadow",
                "parity_match": False,
                "shared_error": type(exc).__name__,
            }
    return legacy_bundle


def _record_bridge_disclosure_receipt(root: Path, bundle: Dict[str, Any]) -> Dict[str, Any]:
    from .disclosure_receipts import record_bridge_context_receipt

    return record_bridge_context_receipt(root, bundle)


def inspect_disclosure_receipt(root: Path, receipt_id: str) -> Dict[str, Any]:
    from .disclosure_receipts import inspect_disclosure_receipt as _inspect

    return _inspect(root, receipt_id)


def list_disclosure_receipts(
    root: Path,
    *,
    request_id: str = "",
    surface: str = "",
    workspace_id: str = "",
    limit: int = 20,
) -> List[Dict[str, Any]]:
    from .disclosure_receipts import list_disclosure_receipts as _list

    return _list(
        root,
        request_id=request_id,
        surface=surface,
        workspace_id=workspace_id,
        limit=limit,
    )


def inspect_aperture_operator_view(
    root: Path,
    *,
    surface: str = "",
    corpus_revision: str = "",
    receipt_limit: int | None = None,
) -> Dict[str, Any]:
    from .aperture_operator_metrics import inspect_operator_view

    return inspect_operator_view(
        root,
        surface=surface,
        corpus_revision=corpus_revision,
        receipt_limit=receipt_limit,
    )


def active_state_continuity_enabled(root: Path) -> bool:
    try:
        from .active_state_continuity import active_state_continuity_enabled as _enabled

        return bool(_enabled(root))
    except Exception:
        return False


def record_context_switch(root: Path, event: Dict[str, Any]) -> Dict[str, Any]:
    ensure_reasoning_runtime(root)
    append_jsonl(_context_switch_events_path(root), event)
    return event
