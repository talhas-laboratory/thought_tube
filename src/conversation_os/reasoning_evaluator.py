from __future__ import annotations

from typing import Any, Dict


MODULE_ID = "kernel.reasoning.reasoning_evaluator"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "evaluate_reasoning_packet",
)
__all__ = list(PUBLIC_API)


def evaluate_reasoning_packet(packet: Dict[str, Any]) -> Dict[str, Any]:
    active_field = packet.get("active_field", {})
    reasoning = packet.get("reasoning", {})
    response_text = str(packet.get("user_response", {}).get("text", "")).strip()
    ambiguity = float(active_field.get("ambiguity_level", 0.0) or 0.0)
    fixation_risk = float(active_field.get("fixation_risk", 0.0) or 0.0)
    novelty = float(active_field.get("novelty_confidence", 0.0) or 0.0)

    chosen = reasoning.get("selected_transformation", {}) or {}
    fit_score = float(chosen.get("fit_score", 0.0) or 0.0)
    generic_flattening_risk = 0.0 if response_text and len(response_text.split()) >= 6 else 0.35
    tension_preservation_score = 0.72 if active_field.get("active_tensions") else 0.48

    if ambiguity >= 0.7 and not chosen.get("integrate"):
        verdict = "needs_more_probe"
        next_action = "probe"
    elif fit_score >= 0.72 and generic_flattening_risk <= 0.2:
        verdict = "integrate"
        next_action = "persist"
    elif ambiguity >= 0.5 and active_field.get("active_tensions"):
        verdict = "preserve_tension"
        next_action = "preserve_tension"
    elif fit_score < 0.35 and fixation_risk >= 0.4:
        verdict = "reject"
        next_action = "reframe"
    else:
        verdict = "suspend"
        next_action = "review"

    confidence = max(0.12, min(0.95, round((fit_score + novelty + (1.0 - min(fixation_risk, 1.0))) / 3.0, 2)))
    return {
        "integration_verdict": verdict,
        "recommended_next_action": next_action,
        "fit_score": round(fit_score, 2),
        "novelty_score": round(novelty, 2),
        "tension_preservation_score": round(tension_preservation_score, 2),
        "generic_flattening_risk": round(generic_flattening_risk, 2),
        "confidence": confidence,
    }
