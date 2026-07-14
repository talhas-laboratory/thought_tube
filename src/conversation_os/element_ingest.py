from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .element_capture import append_element_capture, element_context_config, should_capture_turn
from .element_routing import resolve_element_binding


MODULE_ID = "surface.bridge.element_ingest"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "DEV_DIMENSION_TO_ELEMENT",
    "SURFACE_ELEMENT_HINTS",
    "ingest_to_element_space",
    "element_key_from_development_dimensions",
    "element_key_from_surface_hints",
)
__all__ = list(PUBLIC_API)

DEV_DIMENSION_TO_ELEMENT = {
    "mobile_execution": "frontend",
    "workflow_routing": "backend",
    "bridge_orchestration": "backend",
    "conversation_analysis": "backend",
    "expert_tool_orchestration": "backend",
}

SURFACE_ELEMENT_HINTS = {
    "mobile": "frontend",
    "mobile_surface": "frontend",
    "frontend": "frontend",
    "ui": "frontend",
    "miniapp": "frontend",
    "thoughtboard": "",
    "development_layer": "",
    "pasted_transcript": "",
    "marketing": "marketing",
    "gtm": "marketing",
    "monetization": "monetization",
    "pricing": "monetization",
    "backend": "backend",
    "bridge": "backend",
    "mcp": "backend",
}


def element_key_from_development_dimensions(dimensions: List[str]) -> str:
    for dimension in dimensions:
        key = DEV_DIMENSION_TO_ELEMENT.get(str(dimension or "").strip())
        if key:
            return key
    return ""


def element_key_from_surface_hints(surface_hints: List[str] | None) -> str:
    for hint in surface_hints or []:
        mapped = SURFACE_ELEMENT_HINTS.get(str(hint or "").strip().lower(), None)
        if mapped:
            return mapped
    return ""


def _merge_ingest_hints(
    *,
    caller_hints: Dict[str, Any] | None,
    surface_hints: List[str] | None,
    element_key: str,
    development_dimensions: List[str] | None,
) -> Dict[str, Any]:
    hints = dict(caller_hints or {})
    if element_key.strip():
        hints["element_key"] = element_key.strip()
    elif not hints.get("element_key"):
        from_surface = element_key_from_surface_hints(surface_hints)
        if from_surface:
            hints["element_key"] = from_surface
    if not hints.get("element_key") and development_dimensions:
        from_dimensions = element_key_from_development_dimensions(development_dimensions)
        if from_dimensions:
            hints["element_key"] = from_dimensions
    return hints


def ingest_to_element_space(
    root: Path,
    *,
    raw_text: str,
    source_kind: str,
    source_ref: str = "",
    session_id: str = "",
    surface_hints: List[str] | None = None,
    caller_hints: Dict[str, Any] | None = None,
    element_key: str = "",
    development_dimensions: List[str] | None = None,
    force_capture: bool = True,
    capture_trigger: str = "external_ingest",
) -> Dict[str, Any]:
    text = str(raw_text or "").strip()
    if not text:
        raise ValueError("raw_text is required")

    hints = _merge_ingest_hints(
        caller_hints=caller_hints,
        surface_hints=surface_hints,
        element_key=element_key,
        development_dimensions=development_dimensions,
    )
    binding = resolve_element_binding(
        root,
        session={},
        caller_hints=hints,
        raw_text=text,
    )
    if binding.get("element_method") == "explicit" and not hints.get("element_key"):
        binding["element_method"] = "ingest"

    capture = None
    preview = {
        "element_key": binding.get("element_key", ""),
        "element_confidence": binding.get("element_confidence", 0.0),
        "user_goal": "capture",
    }
    cfg = element_context_config(root)
    should_capture, trigger, confidence = should_capture_turn(
        raw_text=text,
        preview=preview,
        binding={**binding, "request_ingest": force_capture},
        config=cfg,
    )
    if force_capture and binding.get("element_key"):
        should_capture = True
        trigger = capture_trigger
        confidence = max(float(binding.get("element_confidence", 0.0) or 0.0), 0.72)

    if should_capture and binding.get("element_key"):
        capture = append_element_capture(
            root,
            element_key=str(binding["element_key"]),
            raw_text=text,
            session_id=session_id,
            source_kind=source_kind,
            source_ref=source_ref,
            element_keys_secondary=list(binding.get("element_keys_secondary", []) or []),
            confidence=confidence,
            method=str(binding.get("element_method", "") or "ingest"),
            capture_trigger=trigger,
            topology_mode=str(binding.get("topology_mode", "spine") or "spine"),
            holodeck_id=str(binding.get("holodeck_id", "") or ""),
        )

    return {
        "element_binding": binding,
        "element_capture": capture,
        "captured": capture is not None,
    }
