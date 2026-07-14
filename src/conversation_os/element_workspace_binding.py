from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .runtime_layout import product_config_dir
from .storage import read_json
from .workspace_coordination import load_workspace_manifest


def _product_elements_path(root: Path) -> Path:
    return product_config_dir(root, "inner_world_v1") / "product_elements.json"


def _workspace_subprojects_path(root: Path) -> Path:
    return product_config_dir(root, "inner_world_v1") / "workspace_subprojects.json"


def load_element_registry_entry(root: Path, element_key: str) -> Dict[str, Any]:
    key = str(element_key or "").strip()
    if not key:
        return {}
    payload = read_json(_product_elements_path(root), default={})
    for entry in list(payload.get("elements", []) or []):
        if str(entry.get("element_key", "") or "").strip() == key:
            return dict(entry)
    return {}


def load_holodeck_binding(root: Path, holodeck_id: str) -> Dict[str, Any]:
    workspace_id = str(holodeck_id or "").strip()
    if not workspace_id:
        return {}
    try:
        manifest = load_workspace_manifest(root, workspace_id)
    except FileNotFoundError:
        return {}
    return dict(manifest)


def workspace_steering_constraints(
    *,
    element: Dict[str, Any],
    holodeck: Dict[str, Any],
    subproject: Dict[str, Any] | None = None,
) -> List[str]:
    primary = str(
        (subproject or {}).get("primary_artifact_root", "")
        or holodeck.get("primary_artifact_root", "")
        or ""
    ).strip()
    constraints = [
        "honor workspace artifact_roots and objectives; treat scope_out as non-goals unless user explicitly overrides",
        "map every implementation change to pillar(s) from pillars_ref",
    ]
    if primary:
        constraints.append(f"primary artifact root is {primary}; do not implement capture work outside it")
    sub = subproject or {}
    for doc_key in ("scroll_ref", "motion_ref", "contracts_ref"):
        ref = str(sub.get(doc_key, "") or "").strip()
        if ref:
            label = doc_key.replace("_ref", "").upper()
            constraints.append(f"read {label} ({ref}) before scroll, motion, or contract-touched edits")
    workboard = str(holodeck.get("workboard_ref", "") or element.get("workboard_ref", "") or "").strip()
    if workboard:
        constraints.append(f"coordinate via workboard {workboard}")
    return constraints


def build_workspace_binding_bundle(
    root: Path,
    *,
    element_key: str,
    holodeck_id: str = "",
    subproject_id: str = "",
) -> Dict[str, Any]:
    key = str(element_key or "").strip()
    if not key:
        return {}

    element = load_element_registry_entry(root, key)
    holodeck = load_holodeck_binding(root, holodeck_id or str(element.get("holodeck_id", "") or ""))

    subproject_cfg = _resolve_subproject_config(root, holodeck, subproject_id)
    artifact_roots = _dedupe(
        list(element.get("artifact_roots", []) or [])
        + list(holodeck.get("artifact_roots", []) or [])
    )
    primary_root = str(subproject_cfg.get("primary_artifact_root", "") or "").strip()
    if primary_root and primary_root not in artifact_roots:
        artifact_roots.insert(0, primary_root)

    constraints = workspace_steering_constraints(
        element=element,
        holodeck=holodeck,
        subproject=subproject_cfg,
    )
    markdown = _render_workspace_binding_markdown(
        element_key=key,
        element=element,
        holodeck=holodeck,
        subproject=subproject_cfg,
        artifact_roots=artifact_roots,
        constraints=constraints,
    )
    return {
        "element_key": key,
        "holodeck_id": str(holodeck.get("workspace_id", "") or holodeck_id or ""),
        "subproject_id": str(subproject_cfg.get("subproject_id", "") or ""),
        "artifact_roots": artifact_roots,
        "primary_artifact_root": primary_root,
        "scope_out": list(holodeck.get("scope_out", []) or []),
        "workspace_steering_constraints": constraints,
        "workspace_binding_markdown": markdown,
    }


def merge_workspace_binding_into_preview(
    preview: Dict[str, Any],
    binding_bundle: Dict[str, Any],
) -> Dict[str, Any]:
    if not binding_bundle:
        return dict(preview or {})
    enriched = dict(preview or {})
    existing = [str(value) for value in list(enriched.get("steering_constraints", []) or []) if str(value).strip()]
    for constraint in list(binding_bundle.get("workspace_steering_constraints", []) or []):
        if constraint not in existing:
            existing.append(constraint)
    enriched["steering_constraints"] = existing
    enriched["workspace_binding"] = {
        "holodeck_id": binding_bundle.get("holodeck_id", ""),
        "subproject_id": binding_bundle.get("subproject_id", ""),
        "primary_artifact_root": binding_bundle.get("primary_artifact_root", ""),
        "artifact_roots": list(binding_bundle.get("artifact_roots", []) or []),
    }
    if binding_bundle.get("primary_artifact_root"):
        enriched["active_workspace_id"] = binding_bundle.get("holodeck_id", "") or enriched.get(
            "active_workspace_id", ""
        )
    return enriched


def _resolve_subproject_config(
    root: Path,
    holodeck: Dict[str, Any],
    subproject_id: str,
) -> Dict[str, Any]:
    cfg_path = _workspace_subprojects_path(root)
    payload = read_json(cfg_path, default={})
    projects = dict(payload.get("subprojects", {}) or {})
    project_id = (
        str(subproject_id or "").strip()
        or str(holodeck.get("active_subproject_id", "") or "").strip()
    )
    if not project_id:
        return {}
    entry = dict(projects.get(project_id, {}) or {})
    if entry:
        entry.setdefault("subproject_id", project_id)
    return entry


def _render_workspace_binding_markdown(
    *,
    element_key: str,
    element: Dict[str, Any],
    holodeck: Dict[str, Any],
    subproject: Dict[str, Any],
    artifact_roots: List[str],
    constraints: List[str],
) -> str:
    lines = [
        "## Workspace binding",
        f"- element: `{element_key}`",
        f"- holodeck: `{holodeck.get('workspace_id', '')}`",
        f"- goal: {holodeck.get('goal', '')}",
    ]
    if subproject.get("subproject_id"):
        lines.append(f"- active_subproject: `{subproject.get('subproject_id', '')}`")
    if subproject.get("primary_artifact_root"):
        lines.append(f"- primary_artifact_root: `{subproject.get('primary_artifact_root', '')}`")
    pillars = str(holodeck.get("pillars_ref", "") or element.get("pillars_ref", "") or "").strip()
    if pillars:
        lines.append(f"- pillars_ref: `{pillars}`")
    workboard = str(holodeck.get("workboard_ref", "") or element.get("workboard_ref", "") or "").strip()
    if workboard:
        lines.append(f"- workboard_ref: `{workboard}`")
    sub_ref = str(subproject.get("workboard_ref", "") or holodeck.get("subproject_ref", "") or "").strip()
    if sub_ref:
        lines.append(f"- subproject_workboard: `{sub_ref}`")
    for label, key in (
        ("scroll", "scroll_ref"),
        ("motion", "motion_ref"),
        ("contracts", "contracts_ref"),
        ("pwa_source", "pwa_source_ref"),
    ):
        ref = str(subproject.get(key, "") or element.get(key, "") or "").strip()
        if ref:
            lines.append(f"- {label}: `{ref}`")
    if artifact_roots:
        lines.extend(["", "### Artifact roots"])
        lines.extend(f"- `{path}`" for path in artifact_roots[:12])
    objectives = [str(item).strip() for item in list(holodeck.get("objectives", []) or []) if str(item).strip()]
    if objectives:
        lines.extend(["", "### Objectives"])
        lines.extend(f"- {item}" for item in objectives[:8])
    scope_out = list(holodeck.get("scope_out", []) or [])
    if scope_out:
        lines.extend(["", "### Scope out"])
        lines.extend(f"- {item}" for item in scope_out[:8])
    if constraints:
        lines.extend(["", "### Workspace constraints"])
        lines.extend(f"- {item}" for item in constraints)
    lines.extend(
        [
            "",
            "### Agent scope rule",
            "Stay inside workspace binding for this session. PWA capture work goes in "
            f"`{subproject.get('primary_artifact_root', 'product/thought_capture_pwa/')}` unless "
            "user explicitly redirects or a DECISIONS.md entry expands scope.",
        ]
    )
    return "\n".join(lines)


def _dedupe(values: List[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for raw in values:
        value = str(raw or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered
