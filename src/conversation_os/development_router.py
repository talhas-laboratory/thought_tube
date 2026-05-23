from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .codebase_overview import lookup_codebase
from .development_intake import get_development_idea, translate_development_idea


MODULE_ID = "assembly.development.development_router"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "rank_module_targets",
    "route_development_idea",
)
__all__ = list(PUBLIC_API)


_SURFACE_FILTER_MAP = {
    "worldbuilding": "worldbuilding_studio",
    "worldbuilding_studio": "worldbuilding_studio",
    "higgsfield": "worldbuilding_studio",
    "personal": "personal_interface_v1",
    "personal_interface": "personal_interface_v1",
    "rewrite": "personal_interface_v1",
    "calibration": "personal_interface_v1",
    "inner_world": "inner_world_v1",
    "feed": "inner_world_v1",
    "thought": "inner_world_v1",
}

_SURFACE_MODULE_MAP = {
    "worldbuilding_studio": "surface.worldbuilding.worldbuilding_studio",
    "personal_interface_v1": "surface.personal.personal_interface",
    "inner_world_v1": "surface.inner_world.product_inner_world",
}


def _normalize_string_list(values: List[str] | None) -> List[str]:
    normalized: List[str] = []
    for value in values or []:
        text = str(value or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _coerce_idea_payload(root: Path, payload: Dict[str, Any] | str) -> Dict[str, Any]:
    if isinstance(payload, str):
        idea = get_development_idea(root, payload)
        if idea is None:
            raise FileNotFoundError(f"Development idea not found: {payload}")
        return idea
    return dict(payload)


def _surface_filters(idea: Dict[str, Any]) -> List[str]:
    filters: List[str] = []
    for hint in _normalize_string_list(idea.get("surface_hints", [])):
        mapped = _SURFACE_FILTER_MAP.get(hint.lower())
        if mapped and mapped not in filters:
            filters.append(mapped)

    idea_text = " ".join(
        [
            str(idea.get("raw_idea", "")),
            str(idea.get("desired_effect", "")),
            " ".join(str(value) for value in idea.get("translated_framing", {}).get("context_notes", [])),
        ]
    ).lower()
    for token, mapped in _SURFACE_FILTER_MAP.items():
        if token in idea_text and mapped not in filters:
            filters.append(mapped)
    return filters


def _atlas_query(idea: Dict[str, Any]) -> str:
    translated = idea.get("translated_framing", {})
    signals = idea.get("development_signals", {})

    tokens = [
        str(idea.get("raw_idea", "")),
        str(idea.get("desired_effect", "")),
        " ".join(translated.get("target_artifacts", [])),
        " ".join(signals.get("query_tokens", [])),
    ]
    for surface in _surface_filters(idea):
        tokens.append(f"surface:{surface}")
    return " ".join(token for token in tokens if token).strip()


def _entry_reason(entry: Dict[str, Any], active_surfaces: List[str]) -> str:
    manifest = entry.get("module_manifest") or {}
    module_id = str(manifest.get("module_id", ""))
    surfaces = [str(value) for value in manifest.get("surfaces_using", [])]
    if any(surface in surfaces for surface in active_surfaces):
        return "surface_family_match"
    if module_id in _SURFACE_MODULE_MAP.values():
        return "surface_owner_match"
    if manifest.get("layer") == "kernel":
        return "kernel_owner_match"
    return "atlas_match"


def rank_module_targets(root: Path, idea_record: Dict[str, Any] | str, limit: int = 8) -> List[Dict[str, Any]]:
    idea = _coerce_idea_payload(root, idea_record)
    surfaces = _surface_filters(idea)
    query = _atlas_query(idea)
    rows = lookup_codebase(root, query, limit=max(limit * 2, 8))

    ranked: List[Dict[str, Any]] = []
    for row in rows:
        manifest = dict(row.get("module_manifest") or {})
        module_id = str(manifest.get("module_id", "")).strip()
        if not module_id:
            continue
        ranked.append(
            {
                "module_id": module_id,
                "path": row["path"],
                "layer": manifest.get("layer", ""),
                "owner": manifest.get("owner", ""),
                "purpose": manifest.get("purpose", ""),
                "score": row.get("score", 0),
                "matched_tokens": list(row.get("matched_tokens", [])),
                "surfaces_using": list(manifest.get("surfaces_using", [])),
                "reason": _entry_reason(row, surfaces),
            }
        )
    return ranked[: max(1, int(limit))]


def _route_kind(idea: Dict[str, Any], targets: List[Dict[str, Any]]) -> str:
    lowered = " ".join(
        [
            str(idea.get("raw_idea", "")).lower(),
            str(idea.get("desired_effect", "")).lower(),
            str(idea.get("intent_kind", "")).lower(),
        ]
    )
    if any(token in lowered for token in ("recipe", "compose", "composition", "mix and match")):
        return "update_recipe"
    if any(token in lowered for token in ("variant", "version", "lens-specific", "use case", "use-case")):
        return "create_variant"
    if any(token in lowered for token in ("new module", "new owner", "new subsystem")):
        return "create_new_module"
    if not targets or targets[0]["score"] < 4:
        return "create_new_module"
    if idea.get("intent_kind") == "lens_composition":
        return "update_recipe"
    if idea.get("intent_kind") == "module_variant":
        return "create_variant"
    if idea.get("intent_kind") == "new_module":
        return "create_new_module"
    return "extend_existing"


def _target_surface_family(idea: Dict[str, Any], targets: List[Dict[str, Any]]) -> str:
    surfaces = _surface_filters(idea)
    if surfaces:
        return surfaces[0]
    if targets and targets[0]["surfaces_using"]:
        return str(targets[0]["surfaces_using"][0])
    return ""


def _route_rationale(idea: Dict[str, Any], targets: List[Dict[str, Any]], route_kind: str) -> List[str]:
    lines = [f"Intent classified as `{idea.get('intent_kind', 'development_idea')}`."]
    if targets:
        top = targets[0]
        lines.append(
            f"Top owner match is `{top['module_id']}` because it scored `{top['score']}` and matched `{top['reason']}`."
        )
    else:
        lines.append("No strong atlas match was found, so the route defaults away from existing owners.")
    if route_kind == "update_recipe":
        lines.append("The idea emphasizes composition or lens-mixing, so the smallest change is a recipe-level update.")
    elif route_kind == "create_variant":
        lines.append("The idea suggests a lens-specific divergence, so a variant is safer than mutating the base owner.")
    elif route_kind == "create_new_module":
        lines.append("The current owner map does not provide a strong enough home for the idea.")
    else:
        lines.append("The current owner map is strong enough to extend an existing module directly.")
    return lines


def route_development_idea(root: Path, idea_record: Dict[str, Any] | str, limit: int = 6) -> Dict[str, Any]:
    idea = _coerce_idea_payload(root, idea_record)
    if "translated_framing" not in idea or "development_signals" not in idea:
        translated = translate_development_idea(
            root,
            str(idea.get("raw_idea", "")),
            desired_effect=str(idea.get("desired_effect", "")),
            surface_hints=_normalize_string_list(idea.get("surface_hints", [])),
        )
        idea["translated_framing"] = translated["translated_framing"]
        idea["development_signals"] = translated["development_signals"]

    targets = rank_module_targets(root, idea, limit=limit)
    route_kind = _route_kind(idea, targets)
    target_surface_family = _target_surface_family(idea, targets)
    confidence = 0.32
    if targets:
        confidence = min(0.95, 0.38 + float(targets[0]["score"]) * 0.06)
    if route_kind == "create_new_module":
        confidence = min(confidence, 0.58)

    return {
        "idea_id": idea.get("idea_id", ""),
        "route_kind": route_kind,
        "target_surface_family": target_surface_family,
        "candidate_targets": targets,
        "query": _atlas_query(idea),
        "rationale": _route_rationale(idea, targets, route_kind),
        "confidence": round(confidence, 2),
    }
