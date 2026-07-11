from __future__ import annotations

from typing import Any, Dict, List

from .builder_behavior import build_builder_chat_response
from .self_improvement_domains import (
    DOMAIN_LAYER_HINTS,
    DOMAIN_RISK,
    DOMAIN_TESTS,
    classify_feedback_domain,
)
from .storage import make_id, utc_now


MODULE_ID = "kernel.reasoning.self_improvement"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "build_self_improvement_chat_response",
    "classify_feedback_domain",
    "default_packet_for_feedback",
    "interpret_self_improvement_turn",
    "validate_system_improvement_packet",
)
__all__ = list(PUBLIC_API)


NOTE_MODE_KEYWORDS = ("idea", "thought", "note", "capture", "reflect", "journal")
OPERATE_KEYWORDS = (
    "implement",
    "change",
    "update",
    "deploy",
    "release",
    "rollback",
    "add",
    "fix",
    "build",
    "create",
)


def default_packet_for_feedback(raw_text: str, session_id: str, turn_id: str) -> Dict[str, Any]:
    domain = classify_feedback_domain(raw_text)
    risk = DOMAIN_RISK[domain]
    return {
        "schema_version": "1.0",
        "packet_id": make_id("sip"),
        "created_at": utc_now(),
        "status": "proposed",
        "source": {
            "session_id": session_id,
            "turn_id": turn_id,
            "raw_user_signal": raw_text,
            "provenance_refs": [],
        },
        "classification": {
            "domain": domain,
            "risk": risk,
            "affected_layers": list(DOMAIN_LAYER_HINTS.get(domain, [])),
            "change_type": "system_feedback",
        },
        "problem": {
            "observed": raw_text,
            "expected": "",
            "evidence": [],
        },
        "proposal": {
            "summary": "",
            "files_or_configs": [],
            "runtime_effect": "",
            "alternatives_considered": [],
        },
        "gates": {
            "required_tests": list(DOMAIN_TESTS[domain]),
            "required_smokes": [],
            "required_reviews": ["release_gate_review"] if risk in {"high", "critical"} else [],
            "rollback_required": risk in {"high", "critical"},
        },
        "release": {
            "version_bump": "patch",
            "deploy_allowed": False,
            "approval_required": True,
            "rollback_plan": "",
        },
    }


def interpret_self_improvement_turn(
    raw_text: str,
    *,
    requested_mode: str = "",
    requested_meta_state: str = "",
) -> Dict[str, Any]:
    text = raw_text.strip()
    lower = text.lower()
    resolved_mode = requested_mode.strip().lower() or "meta"
    if resolved_mode not in {"note", "meta"}:
        resolved_mode = "meta"
    resolved_state = requested_meta_state.strip().lower() or "discuss"
    if resolved_state not in {"discuss", "operate"}:
        resolved_state = "discuss"
    if resolved_mode == "note":
        resolved_state = "discuss"
    if resolved_mode == "meta" and resolved_state == "discuss":
        if any(keyword in lower for keyword in OPERATE_KEYWORDS) and "should we" not in lower and "could we" not in lower:
            resolved_state = "operate"
    domain = classify_feedback_domain(text)
    should_create_packet = resolved_mode == "meta" and resolved_state == "operate"
    summary = (
        f"Interpreted as {resolved_mode} mode. "
        f"{'Staying in discussion space.' if not should_create_packet else 'Ready to operationalize this change.'}"
    )
    next_action = (
        "Keep discussing the idea without creating a governed change packet yet."
        if not should_create_packet
        else "Create a governed change packet, then attach tests, release gates, and rollback planning."
    )
    return {
        "surface_mode": resolved_mode,
        "meta_state": resolved_state,
        "domain": domain,
        "risk": DOMAIN_RISK[domain] if resolved_mode == "meta" else "none",
        "should_create_packet": should_create_packet,
        "summary": summary,
        "next_action": next_action,
    }


def build_self_improvement_chat_response(
    raw_text: str,
    *,
    requested_mode: str = "",
    requested_meta_state: str = "",
    builder_state: Dict[str, Any] | None = None,
    workspace_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    resolved_mode = requested_mode.strip().lower() or "meta"
    if resolved_mode == "meta":
        return build_builder_chat_response(
            raw_text,
            requested_meta_state=requested_meta_state,
            builder_state=builder_state,
            workspace_context=workspace_context,
        )

    interpretation = interpret_self_improvement_turn(
        raw_text,
        requested_mode=requested_mode,
        requested_meta_state=requested_meta_state,
    )
    if interpretation["should_create_packet"]:
        assistant_text = (
            "This is ready to move out of discussion space. "
            "I will treat it as a governed change packet candidate and attach the required tests, release gates, and rollback work."
        )
    else:
        assistant_text = (
            "This stays in discussion space for now. "
            "We can refine the idea, narrow scope, and only create a governed change packet once the change is explicit."
        )
    return {
        "interpretation": interpretation,
        "assistant_text": assistant_text,
        "packet": None,
    }


def validate_system_improvement_packet(packet: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    for key in ["schema_version", "packet_id", "source", "classification", "problem", "proposal", "gates", "release"]:
        if key not in packet:
            errors.append(f"missing {key}")
    release = packet.get("release", {}) or {}
    if release.get("deploy_allowed") and not release.get("approval_required"):
        errors.append("deploy_allowed requires approval_required")
    classification = packet.get("classification", {}) or {}
    domain = classification.get("domain", "")
    if domain not in DOMAIN_RISK:
        errors.append("unknown feedback domain")
    if classification.get("risk") == "critical" and not packet.get("gates", {}).get("rollback_required"):
        errors.append("critical risk requires rollback_required")
    return errors
