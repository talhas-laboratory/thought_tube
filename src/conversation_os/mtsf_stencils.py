from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

MODULE_ID = "kernel.mtsf.stencils"
CONTRACT_VERSION = "1.1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "default_seed_stencils_path",
    "default_stencil_role_types_path",
    "load_seed_stencils",
    "load_stencil_role_types",
    "compute_structural_fingerprint",
    "validate_stencil_record",
    "validate_seed_library",
)
__all__ = list(PUBLIC_API)


def default_seed_stencils_path(root: Path) -> Path:
    return (
        root
        / "docs"
        / "frameworks"
        / "metaphysical-thought-space"
        / "seed"
        / "stencils.json"
    )


def default_stencil_role_types_path(root: Path) -> Path:
    return (
        root
        / "docs"
        / "frameworks"
        / "metaphysical-thought-space"
        / "ontologies"
        / "stencil-role-types.json"
    )


def load_stencil_role_types(root: Path) -> Set[str]:
    path = default_stencil_role_types_path(root)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(row["role_type"]) for row in payload.get("role_types", [])}


def load_seed_stencils(root: Path) -> List[Dict[str, Any]]:
    path = default_seed_stencils_path(root)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("stencils", []))


def _role_type_by_id(stencil: Dict[str, Any]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for row in stencil.get("role_entities", []):
        role_id = str(row.get("role_id", ""))
        role_type = str(row.get("role_type", ""))
        if role_id and role_type:
            mapping[role_id] = role_type
    return mapping


def compute_structural_fingerprint(stencil: Dict[str, Any]) -> str:
    role_types = _role_type_by_id(stencil)
    edge_tokens: List[str] = []
    for edge in stencil.get("relation_topology", []):
        source_id = str(edge.get("source_role_id", ""))
        target_id = str(edge.get("target_role_id", ""))
        primitive = str(edge.get("primitive", ""))
        source_type = role_types.get(source_id, source_id)
        target_type = role_types.get(target_id, target_id)
        edge_tokens.append(f"{source_type}|{primitive}|{target_type}")
    dynamics = str(stencil.get("dynamics_class", "unknown"))
    symmetry = str(stencil.get("symmetry_profile", "unknown"))
    role_signature = ",".join(sorted(role_types.values()))
    edge_signature = ",".join(sorted(edge_tokens))
    raw = f"roles:{role_signature}::edges:{edge_signature}::dyn:{dynamics}::sym:{symmetry}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def validate_stencil_record(
    stencil: Dict[str, Any],
    *,
    allowed_role_types: Optional[Set[str]] = None,
) -> List[str]:
    errors: List[str] = []
    if not stencil.get("id"):
        errors.append("missing id")
    if not stencil.get("name"):
        errors.append("missing name")

    roles = stencil.get("role_entities", [])
    if len(roles) < 2:
        errors.append("role_entities must contain at least 2 roles")
    if len(roles) > 7:
        errors.append("role_entities exceeds max of 7")

    role_ids: Set[str] = set()
    for row in roles:
        role_id = str(row.get("role_id", ""))
        role_type = str(row.get("role_type", ""))
        if not role_id:
            errors.append("role_entity missing role_id")
        elif role_id in role_ids:
            errors.append(f"duplicate role_id: {role_id}")
        else:
            role_ids.add(role_id)
        if not role_type:
            errors.append(f"role_entity {role_id or '?'} missing role_type")
        elif allowed_role_types and role_type not in allowed_role_types:
            errors.append(f"unknown role_type: {role_type}")

    edges = stencil.get("relation_topology", [])
    if not edges:
        errors.append("relation_topology must contain at least 1 edge")
    if len(edges) > 12:
        errors.append("relation_topology exceeds max of 12")

    for edge in edges:
        source_id = str(edge.get("source_role_id", ""))
        target_id = str(edge.get("target_role_id", ""))
        if source_id not in role_ids:
            errors.append(f"edge source_role_id not found: {source_id}")
        if target_id not in role_ids:
            errors.append(f"edge target_role_id not found: {target_id}")
        if not edge.get("primitive"):
            errors.append(f"edge {source_id}->{target_id} missing primitive")

    facet = stencil.get("facet_completeness", {})
    if not facet.get("causal_geometry"):
        errors.append("facet_completeness.causal_geometry must be true")

    evidence = stencil.get("evidence", {})
    if not evidence.get("source_refs"):
        errors.append("evidence.source_refs required")

    views = stencil.get("views", {})
    if not views.get("gist"):
        errors.append("views.gist required for seed stencils")
    if not views.get("mermaid_topology"):
        errors.append("views.mermaid_topology required for seed stencils")
    if not views.get("slot_table"):
        errors.append("views.slot_table required for seed stencils")

    return errors


def validate_seed_library(root: Path) -> Dict[str, Any]:
    role_types = load_stencil_role_types(root)
    stencils = load_seed_stencils(root)
    fingerprints: Dict[str, str] = {}
    rows: List[Dict[str, Any]] = []
    passed = 0

    for stencil in stencils:
        stencil_id = str(stencil.get("id", ""))
        errors = validate_stencil_record(stencil, allowed_role_types=role_types)
        fingerprint = compute_structural_fingerprint(stencil)
        duplicate_of: Optional[str] = None
        for other_id, other_fp in fingerprints.items():
            if other_fp == fingerprint:
                duplicate_of = other_id
                break
        if duplicate_of:
            errors.append(f"duplicate structural fingerprint as {duplicate_of}")
        else:
            fingerprints[stencil_id] = fingerprint

        ok = not errors
        if ok:
            passed += 1
        rows.append(
            {
                "id": stencil_id,
                "ok": ok,
                "fingerprint": fingerprint,
                "errors": errors,
                "dynamics_class": stencil.get("dynamics_class"),
                "symmetry_profile": stencil.get("symmetry_profile"),
            }
        )

    return {
        "library": "seed/stencils.json",
        "total": len(stencils),
        "passed": passed,
        "failed": len(stencils) - passed,
        "rows": rows,
    }
