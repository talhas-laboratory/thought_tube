from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from .models import ReasoningRequest
from .product_inner_world import (
    _append_session_event,
    _load_session_manifest,
)
from .reasoning_runtime import run_reasoning
from .storage import make_id, utc_now

MODULE_ID = "surface.mobile_capture.compose"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "compose_mobile_capture_insertion",
    "build_mobile_capture_reasoning_request",
    "project_insertion_text_direct",
)
__all__ = list(PUBLIC_API)

ComposeIntent = Literal["nudge", "shape"]
CompositionPhase = Literal["capture", "develop"]

_VALID_INTENTS = {"nudge", "shape"}
_VALID_PHASES = {"capture", "develop"}


def _default_capture_mode_state(intent: ComposeIntent) -> Dict[str, Any]:
    if intent == "shape":
        return {
            "mode": "development",
            "response_contract": "structural_extraction",
            "ai_presence": 3,
            "goal_state": "build_artifact",
            "confidence": 1.0,
        }
    return {
        "mode": "exploration",
        "response_contract": "continuation_cue",
        "ai_presence": 2,
        "goal_state": "preserve_flow",
        "confidence": 0.7,
    }


def _require_mobile_session(root: Path, session_id: str) -> Dict[str, Any]:
    manifest = _load_session_manifest(root, session_id)
    if manifest is None:
        raise FileNotFoundError(f"Mobile session not found: {session_id}")
    if manifest.get("source_type") != "mobile_surface":
        raise ValueError(f"Session {session_id} is not a mobile_surface session")
    return manifest


def build_mobile_capture_reasoning_request(
    *,
    deposit_body: str,
    local_deposit_id: str,
    session_id: str,
    provenance: Dict[str, Any] | None,
    capture_mode_state: Dict[str, Any],
    intent: ComposeIntent,
    composition_phase: CompositionPhase,
) -> ReasoningRequest:
    body = deposit_body.strip()
    if not body:
        raise ValueError("deposit body must not be blank")
    if not local_deposit_id.strip():
        raise ValueError("local_deposit_id is required")
    if not session_id.strip():
        raise ValueError("session_id is required")

    provenance_payload = dict(provenance or {})
    return ReasoningRequest(
        request_id=make_id("mobile-capture-compose"),
        session_id=session_id.strip(),
        surface="mobile_capture",
        raw_text=body,
        source_refs=[],
        timestamp=utc_now(),
        domain_hints=[],
        caller_hints={
            "local_deposit_id": local_deposit_id.strip(),
            "surface_id": "mobile_capture",
            "holodeck_id": provenance_payload.get("holodeck_id", "sol-frontend"),
            "element_key": provenance_payload.get("element_key", "frontend"),
            "composition_phase": composition_phase,
            "response_contract": str(capture_mode_state.get("response_contract", "")),
            "intent": intent,
            "query_override": body,
            "capture_mode_state": dict(capture_mode_state),
            "classify_mode": "heuristic",
            "context_mode": "session_only",
            "depth_mode": "focused",
            "constraints": [
                "Respond as the connected assistant in an ongoing conversation.",
                "Answer the current input directly using disclosed session context.",
                "Do not mention bridge internals, routing, scores, or context assembly.",
            ],
        },
    )


def _contract_to_utterance(response_contract: str, composition_phase: CompositionPhase) -> str:
    if composition_phase == "develop" and response_contract in {
        "structural_extraction",
        "option_generation",
        "deeper_reasoning",
    }:
        return "block_cluster"
    mapping = {
        "acknowledgment_only": "ack",
        "continuation_cue": "cue",
        "emotional_mirroring": "mirror",
        "clarification": "sharpen",
        "summary": "sharpen",
        "conversion": "sharpen",
    }
    return mapping.get(response_contract, "cue")


def _shape_blocks(text: str) -> List[str]:
    trimmed = text.strip()
    if not trimmed:
        return []

    on_dash = [segment.strip() for segment in re.split(r"\s*[—–]\s*", trimmed) if segment.strip()]
    if 2 <= len(on_dash) <= 4:
        return on_dash

    sentences = [segment.strip() for segment in re.split(r"(?<=[.!?])\s+", trimmed) if segment.strip()]
    if 2 <= len(sentences) <= 4:
        return sentences

    on_comma = [segment.strip() for segment in trimmed.split(",") if len(segment.strip()) > 6]
    if 2 <= len(on_comma) <= 4:
        return on_comma

    lines = [line.strip() for line in trimmed.splitlines() if line.strip()]
    if 2 <= len(lines) <= 6:
        return lines[:4]

    return [trimmed]


def _cap_body(text: str, *, max_lines: int) -> str:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return text.strip()
    return "\n".join(lines[:max_lines]).strip()


def project_insertion_text_direct(
    *,
    response_text: str,
    capture_mode_state: Dict[str, Any],
    composition_phase: CompositionPhase,
    intent: ComposeIntent,
    deposit_body: str,
) -> Optional[Dict[str, Any]]:
    contract = str(capture_mode_state.get("response_contract", "")).strip()
    ai_presence = int(capture_mode_state.get("ai_presence", 0) or 0)
    if contract == "no_response" or ai_presence <= 0:
        return None

    text = response_text.strip()
    if not text and contract != "structural_extraction":
        return None

    utterance_type = _contract_to_utterance(contract, composition_phase)
    mode_state = dict(capture_mode_state)

    if utterance_type == "block_cluster":
        blocks = _shape_blocks(text or deposit_body)
        if not blocks:
            return None
        return {
            "utterance_type": utterance_type,
            "body": "",
            "blocks": blocks,
            "composition_phase": composition_phase,
            "mode_state": mode_state,
        }

    if composition_phase == "capture":
        body = _cap_body(text, max_lines=4)
    elif utterance_type in {"cue", "mirror"}:
        body = _cap_body(text, max_lines=3)
    else:
        body = text.splitlines()[0].strip() if text else ""

    if not body:
        return None

    return {
        "utterance_type": utterance_type,
        "body": body,
        "blocks": None,
        "composition_phase": composition_phase,
        "mode_state": mode_state,
    }


def _provenance_refs_from_result(result: Dict[str, Any]) -> List[str]:
    refs: List[str] = []
    frame_bundle = dict(result.get("frame_bundle", {}) or {})
    for ref in frame_bundle.get("source_refs", []) or []:
        value = str(ref).strip()
        if value and value not in refs:
            refs.append(value)
    request_refs = list((result.get("context_state", {}) or {}).get("source_refs", []) or [])
    for ref in request_refs:
        value = str(ref).strip()
        if value and value not in refs:
            refs.append(value)
    return refs[:12]


def _reasoning_summary(result: Dict[str, Any]) -> Dict[str, Any]:
    context_state = dict(result.get("context_state", {}) or {})
    attributes = dict(context_state.get("attributes", {}) or {})
    run_result = dict(result.get("result", {}) or {})
    route = dict(result.get("route", {}) or {})
    return {
        "request_id": context_state.get("request_id", ""),
        "routing_source": attributes.get("routing_source", "heuristic"),
        "pipeline_id": route.get("pipeline_id", ""),
        "bridge_behavior_ids": list(attributes.get("bridge_behavior_ids", []) or []),
        "integration_verdict": run_result.get("integration_verdict", ""),
    }


def _assistant_mode_state(capture_mode_state: Dict[str, Any]) -> Dict[str, Any]:
    state = dict(capture_mode_state)
    if str(state.get("response_contract", "")).strip() == "no_response":
        state["response_contract"] = "continuation_cue"
    state["ai_presence"] = max(1, int(state.get("ai_presence", 0) or 0))
    return state


def compose_mobile_capture_insertion(
    root: Path,
    *,
    deposit_body: str,
    local_deposit_id: str,
    session_id: str,
    provenance: Dict[str, Any] | None = None,
    capture_mode_state: Dict[str, Any] | None = None,
    intent: ComposeIntent,
    composition_phase: CompositionPhase | None = None,
) -> Dict[str, Any]:
    if intent not in _VALID_INTENTS:
        raise ValueError(f"intent must be one of {sorted(_VALID_INTENTS)}")
    resolved_phase: CompositionPhase = composition_phase or ("develop" if intent == "shape" else "capture")
    if resolved_phase not in _VALID_PHASES:
        raise ValueError(f"composition_phase must be one of {sorted(_VALID_PHASES)}")

    _require_mobile_session(root, session_id)
    mode_state = _assistant_mode_state(capture_mode_state or _default_capture_mode_state(intent))
    if resolved_phase == "capture":
        mode_state["ai_presence"] = min(int(mode_state.get("ai_presence", 2) or 2), 2)

    try:
        reasoning_request = build_mobile_capture_reasoning_request(
            deposit_body=deposit_body,
            local_deposit_id=local_deposit_id,
            session_id=session_id,
            provenance=provenance,
            capture_mode_state=mode_state,
            intent=intent,
            composition_phase=resolved_phase,
        )
        reasoning_result = run_reasoning(root, reasoning_request)
    except Exception as exc:
        return {
            "insertion": None,
            "fallback": True,
            "error": str(exc) or exc.__class__.__name__,
            "composed_at": utc_now(),
        }

    response_text = str((reasoning_result.get("result", {}) or {}).get("response_text", "")).strip()
    reasoning = _reasoning_summary(reasoning_result)
    provenance_refs = _provenance_refs_from_result(reasoning_result)
    insertion = project_insertion_text_direct(
        response_text=response_text,
        capture_mode_state=mode_state,
        composition_phase=resolved_phase,
        intent=intent,
        deposit_body=deposit_body,
    )
    if insertion is None:
        return {
            "insertion": None,
            "fallback": True,
            "error": "empty_insertion",
            "reasoning": reasoning,
            "provenance_refs": provenance_refs,
            "composed_at": utc_now(),
        }

    insertion_content = insertion.get("body") or "\n".join(insertion.get("blocks") or [])
    _append_session_event(
        root,
        session_id=session_id,
        actor="assistant",
        kind="insertion",
        content=insertion_content,
        tags=["mobile_capture", "coupled_insertion", intent],
        attributes={
            "local_deposit_id": local_deposit_id,
            "utterance_type": insertion["utterance_type"],
            "composition_phase": resolved_phase,
            "provenance": dict(provenance or {}),
            "reasoning_request_id": reasoning.get("request_id", ""),
            "pipeline_id": reasoning.get("pipeline_id", ""),
        },
    )

    return {
        "insertion": insertion,
        "fallback": False,
        "reasoning": reasoning,
        "provenance_refs": provenance_refs,
        "composed_at": utc_now(),
    }
