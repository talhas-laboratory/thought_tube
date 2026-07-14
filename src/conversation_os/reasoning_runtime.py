from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .active_field import build_active_field
from .bridge_controller import load_bridge_config
from .chat_backends import request_bridge_execution_reply, resolve_chat_backend, trim_context_bundle
from .models import ReasoningLearningEvent, ReasoningRequest, ReasoningResult
from .note_agent_state import infer_note_agent_state
from .pipeline_runner import run_pipeline
from .reasoning_bridge import (
    _context_states_path,
    _runtime_dir,
    classify_turn,
    get_context_bundle,
    is_incognito_context,
    load_context_states,
    load_control_packets,
    persist_control_packet,
    record_context_switch,
)
from .reasoning_evaluator import evaluate_reasoning_packet
from .reasoning_learning import persist_bridge_behavior_preferences, record_learning_event
from .reasoning_router import route_reasoning
from .storage import append_jsonl, ensure_dir, make_id, read_jsonl, utc_now


MODULE_ID = "kernel.reasoning.reasoning_runtime"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "run_reasoning",
    "inspect_reasoning_request",
)
__all__ = list(PUBLIC_API)


def _active_fields_path(root: Path) -> Path:
    return _runtime_dir(root) / "active_fields.jsonl"


def _results_path(root: Path) -> Path:
    return _runtime_dir(root) / "reasoning_results.jsonl"


def _evaluations_path(root: Path) -> Path:
    return _runtime_dir(root) / "reasoning_evaluations.jsonl"


def inspect_reasoning_request(root: Path, request_id: str) -> Dict[str, Any]:
    contexts = [row for row in load_context_states(root) if str(row.get("request_id", "")) == request_id]
    if not contexts:
        raise FileNotFoundError(f"No reasoning context found for request_id={request_id}")

    context_state = contexts[-1]
    attributes = context_state.get("attributes", {}) or {}
    control_packets = [
        row
        for row in load_control_packets(root)
        if str((row.get("packet") or {}).get("request_id", "")) == request_id
    ]
    active_fields = [
        row for row in read_jsonl(_active_fields_path(root)) if str(row.get("request_id", "")) == request_id
    ]
    results = [
        row for row in read_jsonl(_results_path(root)) if str(row.get("request_id", "")) == request_id
    ]
    evaluations = [
        row for row in read_jsonl(_evaluations_path(root)) if str(row.get("request_id", "")) == request_id
    ]
    active_field = active_fields[-1] if active_fields else {}
    retrieval_summary = dict(active_field.get("retrieval_bundle_summary", {}) or {})
    context_bundle = get_context_bundle(root, context_state)
    bundle_layers = list(context_state.get("bundle_layers", []) or [])
    if not bundle_layers:
        bundle_layers = list(context_bundle.get("context_state", {}).get("bundle_layers", []) or [])

    return {
        "request_id": request_id,
        "routing_source": attributes.get("routing_source", "heuristic"),
        "context_state": context_state,
        "context_policy": dict(attributes.get("context_policy", {}) or {}),
        "bundle_layers": bundle_layers,
        "session_envelope": dict(context_bundle.get("session_envelope", {}) or {}),
        "frame_spec": dict(context_bundle.get("frame_spec", {}) or {}),
        "frame_bundle": dict(context_bundle.get("frame_bundle", {}) or {}),
        "control_packets": control_packets,
        "active_field": active_field,
        "retrieval_summary": retrieval_summary,
        "result": results[-1] if results else {},
        "evaluation": evaluations[-1] if evaluations else {},
    }


def _execution_control_packet(context_state: Dict[str, Any]) -> Dict[str, Any]:
    attributes = context_state.get("attributes", {}) or {}
    return {
        "packet_id": attributes.get("control_packet_id", ""),
        "request_id": context_state.get("request_id", ""),
        "active_topic": context_state.get("active_topic", ""),
        "user_goal": context_state.get("user_goal", ""),
        "reasoning_posture": context_state.get("reasoning_posture", ""),
        "pipeline_id": attributes.get("pipeline_id", ""),
        "bridge_behaviors": list(attributes.get("bridge_behavior_ids", []) or []),
        "steering_constraints": list(attributes.get("steering_constraints", []) or []),
        "context_policy": dict(attributes.get("context_policy", {}) or {}),
    }


def _execute_reasoning_packet(
    root: Path,
    *,
    request_payload: Dict[str, Any],
    context_bundle: Dict[str, Any],
    active_field: Dict[str, Any],
    route: Dict[str, Any],
) -> Dict[str, Any]:
    bridge_config = load_bridge_config(root)
    packet = {
        "reasoning_request": request_payload,
        "context_state": context_bundle["context_state"],
        "active_field": active_field,
        "reasoning": {
            "route": route,
        },
        "user_response": {},
        "operator_trace": [],
    }
    if str(bridge_config.get("execution_mode", "operators")).strip().lower() != "agent":
        return run_pipeline(root, route["pipeline_id"], packet, context={"route": route})

    policy = context_bundle.get("context_policy") or (
        (context_bundle.get("context_state", {}) or {}).get("attributes", {}) or {}
    ).get("context_policy", {})
    trimmed_bundle = trim_context_bundle(context_bundle, policy if isinstance(policy, dict) else None)
    control_packet = _execution_control_packet(context_bundle["context_state"])
    field_constraints = [
        str(value).strip()
        for value in active_field.get("constraints", []) or []
        if str(value).strip()
    ]
    control_packet["steering_constraints"] = list(
        dict.fromkeys([*control_packet["steering_constraints"], *field_constraints])
    )
    if not control_packet.get("pipeline_id"):
        control_packet["pipeline_id"] = route.get("pipeline_id", "")

    backend = resolve_chat_backend(root)
    session_id = str((context_bundle.get("context_state", {}).get("attributes", {}) or {}).get("session_id", ""))
    reply = request_bridge_execution_reply(
        root,
        control_packet,
        trimmed_bundle,
        str(request_payload.get("raw_text", "")),
        backend=backend,
        bridge_config=bridge_config,
        session_id=session_id,
    )
    packet["user_response"] = {"text": reply["content"]}
    packet["operator_trace"] = [
        {
            "step": "bridge_execution_agent",
            "agent": reply.get("agent", ""),
            "backend_id": reply.get("backend_id", ""),
        }
    ]
    return packet


def _allows_durable_learning_side_effects(
    context_bundle: Dict[str, Any],
    request_payload: Dict[str, Any],
) -> bool:
    envelope = dict(context_bundle.get("session_envelope", {}) or {})
    learning_mode = str(envelope.get("learning_mode", "allowed") or "allowed")
    persistence_mode = str(envelope.get("persistence_mode", "gated") or "gated")
    if learning_mode == "disabled" or persistence_mode == "disabled":
        return False
    if persistence_mode == "manual":
        hints = dict(request_payload.get("caller_hints", {}) or {})
        return bool(hints.get("allow_persistence") or hints.get("allow_learning_persistence"))
    return True


def run_reasoning(root: Path, request: ReasoningRequest | Dict[str, Any]) -> Dict[str, Any]:
    ensure_dir(_runtime_dir(root))
    request_payload = request.to_dict() if isinstance(request, ReasoningRequest) else dict(request)
    context_state = classify_turn(root, request_payload)
    note_agent_state = infer_note_agent_state(request_payload)
    if note_agent_state:
        context_state.setdefault("attributes", {})["note_agent"] = note_agent_state
    append_jsonl(_context_states_path(root), context_state)
    attributes = context_state.get("attributes", {}) or {}
    if attributes.get("routing_source") in {"agent", "hybrid"} and attributes.get("control_packet_id"):
        metadata = dict(attributes.get("control_packet_metadata", {}) or {})
        metadata.setdefault("routing_source", attributes.get("routing_source"))
        metadata.setdefault("fallback_reason", "")
        persist_control_packet(
            root,
            {
                "packet_id": attributes.get("control_packet_id"),
                "request_id": context_state.get("request_id", ""),
                "context_policy": attributes.get("context_policy", {}),
                "routing_source": attributes.get("routing_source"),
            },
            metadata=metadata,
        )
    context_bundle = get_context_bundle(root, context_state)
    pending_switch_event = context_bundle.get("context_state", {}).get("attributes", {}).get("pending_switch_event")
    if pending_switch_event:
        record_context_switch(root, pending_switch_event)

    active_field = build_active_field(
        root,
        request_payload,
        context_state=context_bundle["context_state"],
        context_bundle=context_bundle,
    )
    append_jsonl(_active_fields_path(root), active_field)

    route = route_reasoning(active_field)
    packet = _execute_reasoning_packet(
        root,
        request_payload=request_payload,
        context_bundle=context_bundle,
        active_field=active_field,
        route=route,
    )
    evaluation = evaluate_reasoning_packet(packet)
    append_jsonl(_evaluations_path(root), evaluation)

    result = ReasoningResult(
        result_id=make_id("reasoning-result"),
        request_id=str(request_payload.get("request_id", "")),
        field_id=str(active_field.get("field_id", "")),
        pipeline_id=route["pipeline_id"],
        response_text=str(packet.get("user_response", {}).get("text", "")),
        integration_verdict=str(evaluation["integration_verdict"]),
        fit_score=float(evaluation["fit_score"]),
        novelty_score=float(evaluation["novelty_score"]),
        confidence=float(evaluation["confidence"]),
        recommended_next_action=str(evaluation["recommended_next_action"]),
        operator_trace=[entry.get("step", "") for entry in packet.get("operator_trace", [])],
        attributes={
            "routing_factors": route.get("routing_factors", {}),
            "tension_preservation_score": evaluation.get("tension_preservation_score", 0.0),
            "generic_flattening_risk": evaluation.get("generic_flattening_risk", 0.0),
        },
    )

    feedback_kind = str((request_payload.get("caller_hints", {}) or {}).get("feedback_kind", "")).strip()
    learning_event = None
    if feedback_kind and _allows_durable_learning_side_effects(context_bundle, request_payload):
        learning_event = ReasoningLearningEvent(
            learning_event_id=make_id("reasoning-learning"),
            request_id=result.request_id,
            result_id=result.result_id,
            feedback_kind=feedback_kind,
            accepted_framing=str((request_payload.get("caller_hints", {}) or {}).get("accepted_framing", "")),
            rejected_framing=str((request_payload.get("caller_hints", {}) or {}).get("rejected_framing", "")),
            reframing_text=str((request_payload.get("caller_hints", {}) or {}).get("reframing_text", "")),
            preferred_abstraction_shift=str((request_payload.get("caller_hints", {}) or {}).get("preferred_abstraction_shift", "")),
            evidence_refs=list(request_payload.get("source_refs", []) or []),
            sequence_signature=[str(active_field.get("fragment_role", "")), feedback_kind],
            timestamp=utc_now(),
        )
        record_learning_event(root, learning_event.to_dict())
        persisted_patterns = persist_bridge_behavior_preferences(
            root,
            learning_event.to_dict(),
            context_state=context_bundle["context_state"],
            result=result.to_dict(),
        )
        if persisted_patterns:
            result.attributes["persisted_bridge_behavior_patterns"] = persisted_patterns

    append_jsonl(_results_path(root), result.to_dict())

    return {
        "context_state": context_bundle["context_state"],
        "session_envelope": dict(context_bundle.get("session_envelope", {}) or {}),
        "frame_spec": dict(context_bundle.get("frame_spec", {}) or {}),
        "frame_bundle": dict(context_bundle.get("frame_bundle", {}) or {}),
        "active_field": active_field,
        "route": route,
        "packet": packet,
        "evaluation": evaluation,
        "result": result.to_dict(),
        "learning_event": learning_event.to_dict() if learning_event else None,
    }
