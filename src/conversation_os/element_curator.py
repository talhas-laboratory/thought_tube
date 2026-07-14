from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from .element_capture import (
    CAPTURE_STATUS_PROVISIONAL,
    element_context_config,
    list_element_captures,
    promote_element_capture,
    reject_element_capture,
)
from .bridge_session_tracking import get_bridge_session_trace


MODULE_ID = "surface.bridge.element_curator"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "review_session_for_promotion",
    "apply_curator_recommendations",
)
__all__ = list(PUBLIC_API)

_LOW_SIGNAL_RE = re.compile(
    r"^(ok|okay|thanks|thank you|yes|no|sure|done|continue|go ahead|sounds good)[\s.!]*$",
    re.IGNORECASE,
)


def _tier1_recommendation(capture: Dict[str, Any]) -> Dict[str, Any]:
    capture_id = str(capture.get("capture_id", "") or "")
    element_key = str(capture.get("element_key", "") or "")
    raw_text = str(capture.get("raw_text", "") or "").strip()
    trigger = str(capture.get("capture_trigger", "") or "")
    confidence = float(capture.get("confidence", 0.0) or 0.0)

    promote = False
    reject = False
    reason = ""

    if not raw_text or _LOW_SIGNAL_RE.match(raw_text):
        reject = True
        reason = "low_signal_text"
    elif len(raw_text) < 32:
        reject = True
        reason = "too_short"
    elif trigger in {"ingest", "promote", "external_ingest"} and confidence >= 0.65:
        promote = True
        reason = f"trigger:{trigger}"
    elif confidence >= 0.85 and any(token in raw_text.lower() for token in ("decide", "decision", "will", "should", "must")):
        promote = True
        reason = "high_confidence_decision_language"
    else:
        reject = True
        reason = "below_promotion_threshold"

    return {
        "capture_id": capture_id,
        "element_key": element_key,
        "promote": promote,
        "reject": reject,
        "reason": reason,
        "confidence": confidence,
        "thesis": capture.get("thesis", ""),
        "tier": "rules",
    }


def review_session_for_promotion(
    root: Path,
    session_id: str,
    *,
    element_key: str = "",
    auto_apply: bool = False,
) -> Dict[str, Any]:
    session_key = str(session_id or "").strip()
    if not session_key:
        raise ValueError("session_id is required")

    trace = get_bridge_session_trace(root, session_key)
    session = dict(trace.get("session", {}) or {})
    target_element = str(element_key or session.get("element_key", "") or "").strip()
    if not target_element:
        return {
            "session_id": session_key,
            "element_key": "",
            "recommendations": [],
            "applied": [],
            "skipped": "no_element_key",
        }

    captures = list_element_captures(
        root,
        target_element,
        status=CAPTURE_STATUS_PROVISIONAL,
        session_id=session_key,
        limit=50,
    ).get("captures", [])

    recommendations = [_tier1_recommendation(capture) for capture in captures]
    applied: List[Dict[str, Any]] = []
    if auto_apply:
        applied = apply_curator_recommendations(root, recommendations)

    return {
        "session_id": session_key,
        "element_key": target_element,
        "capture_count": len(captures),
        "recommendations": recommendations,
        "applied": applied,
        "auto_apply": auto_apply,
    }


def apply_curator_recommendations(
    root: Path,
    recommendations: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    applied: List[Dict[str, Any]] = []
    for row in recommendations:
        element_key = str(row.get("element_key", "") or "").strip()
        capture_id = str(row.get("capture_id", "") or "").strip()
        if not element_key or not capture_id:
            continue
        try:
            if row.get("promote"):
                result = promote_element_capture(
                    root,
                    element_key=element_key,
                    capture_id=capture_id,
                    reason=str(row.get("reason", "") or "curator_promotion"),
                    confidence=float(row.get("confidence", 0.0) or 0.0),
                )
                applied.append({"action": "promote", **result})
            elif row.get("reject"):
                result = reject_element_capture(
                    root,
                    element_key=element_key,
                    capture_id=capture_id,
                    reason=str(row.get("reason", "") or "curator_rejection"),
                )
                applied.append({"action": "reject", "capture": result})
        except ValueError:
            continue
    return applied


def review_session_on_end_if_flagged(root: Path, session: Dict[str, Any]) -> Dict[str, Any] | None:
    session_id = str(session.get("session_id", "") or "").strip()
    if not session_id:
        return None
    if not bool(session.get("auto_promote_review")):
        return None
    cfg = element_context_config(root)
    auto_apply = bool(cfg.get("auto_apply_on_session_end", False))
    return review_session_for_promotion(
        root,
        session_id,
        element_key=str(session.get("element_key", "") or ""),
        auto_apply=auto_apply,
    )
