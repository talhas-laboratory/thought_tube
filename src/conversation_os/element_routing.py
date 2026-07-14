from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from .runtime_layout import product_config_dir
from .storage import read_json


MODULE_ID = "surface.bridge.element_routing"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "ELEMENT_KEYS",
    "TOPOLOGY_MODES",
    "TURN_FLAG_TAGS",
    "product_elements_config_path",
    "load_product_elements",
    "element_registry_by_key",
    "parse_turn_hashtags",
    "resolve_element_binding",
    "enrich_preview_with_element",
    "sync_session_element_binding",
)
__all__ = list(PUBLIC_API)

ELEMENT_KEYS = frozenset({"frontend", "backend", "marketing", "monetization"})
TOPOLOGY_MODES = frozenset({"spine", "sidecar", "parallel"})
TURN_FLAG_TAGS = frozenset({"promote", "ingest", "deep"})
_HASHTAG_RE = re.compile(r"#([a-z][a-z0-9_-]*)", re.IGNORECASE)


def product_elements_config_path(root: Path) -> Path:
    return product_config_dir(root, "inner_world_v1") / "product_elements.json"


def load_product_elements(root: Path) -> Dict[str, Any]:
    payload = read_json(product_elements_config_path(root), default=None)
    if not isinstance(payload, dict):
        return {"version": 1, "elements": []}
    elements = payload.get("elements")
    if not isinstance(elements, list):
        payload["elements"] = []
    return payload


def element_registry_by_key(root: Path) -> Dict[str, Dict[str, Any]]:
    registry: Dict[str, Dict[str, Any]] = {}
    for element in load_product_elements(root).get("elements", []):
        if not isinstance(element, dict):
            continue
        key = str(element.get("element_key", "") or "").strip()
        if key:
            registry[key] = element
    return registry


def _dedupe_preserve_order(values: List[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for value in values:
        clean = str(value or "").strip()
        if not clean or clean in seen:
            continue
        seen.add(clean)
        ordered.append(clean)
    return ordered


def parse_turn_hashtags(raw_text: str) -> Dict[str, Any]:
    tags = [match.group(1).lower() for match in _HASHTAG_RE.finditer(str(raw_text or ""))]
    element_keys = [tag for tag in tags if tag in ELEMENT_KEYS]
    topology_mode = "spine"
    if "sidecar" in tags:
        topology_mode = "sidecar"
    elif "parallel" in tags:
        topology_mode = "parallel"
    return {
        "element_key": element_keys[0] if element_keys else "",
        "element_keys_secondary": element_keys[1:],
        "topology_mode": topology_mode,
        "flags": [tag for tag in tags if tag in TURN_FLAG_TAGS],
        "request_promote": "promote" in tags,
        "request_ingest": "ingest" in tags,
        "request_deep": "deep" in tags,
    }


def _heuristic_element_key(raw_text: str, registry: Dict[str, Dict[str, Any]]) -> tuple[str, float]:
    tokens = set(re.findall(r"[a-z0-9_]+", str(raw_text or "").lower()))
    if not tokens:
        return "", 0.0

    best_key = ""
    best_score = 0.0
    for key, element in registry.items():
        keywords = {str(value).lower() for value in element.get("keywords", []) or [] if str(value).strip()}
        if not keywords:
            continue
        overlap = len(tokens & keywords)
        if overlap <= 0:
            continue
        score = overlap / max(len(keywords), 1)
        if score > best_score:
            best_score = score
            best_key = key
    if best_score < 0.08:
        return "", 0.0
    return best_key, round(min(0.85, 0.45 + best_score), 2)


def resolve_element_binding(
    root: Path,
    *,
    session: Dict[str, Any] | None,
    caller_hints: Dict[str, Any] | None,
    raw_text: str,
) -> Dict[str, Any]:
    registry = element_registry_by_key(root)
    parsed = parse_turn_hashtags(raw_text)
    hints = dict(caller_hints or {})
    session_row = dict(session or {})

    element_key = ""
    method = "none"
    confidence = 0.0

    if parsed["element_key"]:
        element_key = parsed["element_key"]
        method = "hashtag"
        confidence = 1.0
    else:
        hint_key = str(hints.get("element_key", "") or "").strip()
        if hint_key:
            element_key = hint_key
            method = "explicit"
            confidence = 1.0
        else:
            session_key = str(session_row.get("element_key", "") or "").strip()
            if session_key:
                element_key = session_key
                method = "session"
                confidence = 1.0
            else:
                holodeck_id = str(hints.get("holodeck_id") or hints.get("active_workspace_id") or "").strip()
                if not holodeck_id:
                    holodeck_id = str(session_row.get("holodeck_id", "") or "").strip()
                if holodeck_id:
                    for key, element in registry.items():
                        if str(element.get("holodeck_id", "") or "").strip() == holodeck_id:
                            element_key = key
                            method = "holodeck"
                            confidence = 1.0
                            break
                if not element_key:
                    guessed_key, guessed_confidence = _heuristic_element_key(raw_text, registry)
                    if guessed_key:
                        element_key = guessed_key
                        method = "heuristic"
                        confidence = guessed_confidence

    element = registry.get(element_key, {})
    holodeck_id = (
        str(hints.get("holodeck_id", "") or "").strip()
        or str(session_row.get("holodeck_id", "") or "").strip()
        or str(element.get("holodeck_id", "") or "").strip()
    )

    topology_mode = parsed["topology_mode"]
    if topology_mode == "spine":
        topology_mode = str(session_row.get("topology_mode", "") or "").strip() or str(
            element.get("topology_default", "spine") or "spine"
        )
    if topology_mode not in TOPOLOGY_MODES:
        topology_mode = "spine"

    secondary = _dedupe_preserve_order(
        list(parsed.get("element_keys_secondary", []) or [])
        + list(session_row.get("element_keys_secondary", []) or [])
        + [str(value) for value in hints.get("element_keys_secondary", []) or [] if str(value).strip()]
    )
    if element_key in secondary:
        secondary = [value for value in secondary if value != element_key]

    return {
        "element_key": element_key,
        "element_keys_secondary": secondary,
        "topology_mode": topology_mode,
        "holodeck_id": holodeck_id,
        "element_method": method,
        "element_confidence": confidence,
        "flags": list(parsed.get("flags", []) or []),
        "request_promote": bool(parsed.get("request_promote")),
        "request_ingest": bool(parsed.get("request_ingest")),
        "request_deep": bool(parsed.get("request_deep")),
        "element_label": str(element.get("label", "") or ""),
        "artifact_roots": list(element.get("artifact_roots", []) or []),
        "bound_systems": list(element.get("bound_systems", []) or []),
    }


def enrich_preview_with_element(preview: Dict[str, Any], binding: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(preview or {})
    for field in (
        "element_key",
        "element_keys_secondary",
        "topology_mode",
        "holodeck_id",
        "element_method",
        "element_confidence",
        "element_label",
    ):
        if field in binding:
            enriched[field] = binding[field]
    if binding.get("flags"):
        enriched["element_flags"] = list(binding.get("flags", []) or [])
    if binding.get("request_promote"):
        enriched["request_promote"] = True
    if binding.get("request_ingest"):
        enriched["request_ingest"] = True
    if binding.get("request_deep"):
        enriched["request_deep"] = True
    return enriched


def sync_session_element_binding(
    root: Path,
    session_id: str,
    binding: Dict[str, Any],
) -> Dict[str, Any] | None:
    from .bridge_session_tracking import update_bridge_session_element

    session_key = str(session_id or "").strip()
    if not session_key:
        return None
    method = str(binding.get("element_method", "") or "").strip()
    should_sync = method in {"hashtag", "explicit", "holodeck"} or bool(binding.get("request_promote"))
    if not should_sync:
        return None
    try:
        return update_bridge_session_element(
            root,
            session_key,
            element_key=str(binding.get("element_key", "") or ""),
            element_keys_secondary=list(binding.get("element_keys_secondary", []) or []),
            topology_mode=str(binding.get("topology_mode", "spine") or "spine"),
            holodeck_id=str(binding.get("holodeck_id", "") or ""),
            auto_promote_review=bool(binding.get("request_promote")),
            source=method or "binding",
        )
    except ValueError:
        return None


def element_defaults_for_key(root: Path, element_key: str) -> Dict[str, Any]:
    element = element_registry_by_key(root).get(str(element_key or "").strip(), {})
    if not element:
        return {}
    return {
        "element_key": str(element.get("element_key", "") or ""),
        "holodeck_id": str(element.get("holodeck_id", "") or ""),
        "topology_mode": str(element.get("topology_default", "spine") or "spine"),
        "element_label": str(element.get("label", "") or ""),
        "artifact_roots": list(element.get("artifact_roots", []) or []),
        "bound_systems": list(element.get("bound_systems", []) or []),
    }
