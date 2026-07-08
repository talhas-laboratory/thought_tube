from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .mtsf_extraction import assess_quarantine, validate_extraction_draft
from .mtsf_stencils import (
    compute_structural_fingerprint,
    load_seed_stencils,
    match_stencil_drafts_to_seed,
    normalize_stencil_draft,
)
from .mtsf_index import (
    default_shape_index_path,
    load_shape_index,
    merge_shape_index,
    promote_projection_to_global,
    session_shape_index_path,
)

from .storage import ensure_dir, make_id, read_json, session_dir, utc_now, write_json

MODULE_ID = "kernel.mtsf.projector"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "StencilProjection",
    "ProjectionResult",
    "default_shape_index_path",
    "session_shape_index_path",
    "load_shape_index",
    "merge_shape_index",
    "project_stencil_draft",
    "resolve_stencil_projections",
    "build_shape_instances",
    "project_extraction_draft",
    "materialize_stencil_projection",
)
__all__ = list(PUBLIC_API)

MERGE_SCORE_THRESHOLD = 0.8


@dataclass
class StencilProjection:
    draft_index: int
    proposed_name: str
    fingerprint: str
    action: str
    stencil_id: str
    structural_match_score: float
    matched_seed_id: Optional[str] = None
    canonical_stencil: Optional[Dict[str, Any]] = None
    quarantine: bool = False


@dataclass
class ProjectionResult:
    session_id: str
    draft_id: str
    subgraph_id: Optional[str]
    stencil_projections: List[StencilProjection] = field(default_factory=list)
    shape_instances: List[Dict[str, Any]] = field(default_factory=list)
    active_stencil_ids: List[str] = field(default_factory=list)
    quarantined_stencils: List[Dict[str, Any]] = field(default_factory=list)


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "stencil"


def _build_views(stencil: Dict[str, Any]) -> Dict[str, Any]:
    role_rows = stencil.get("role_entities", [])
    gist = str(stencil.get("name", stencil.get("id", "projected stencil")))
    if role_rows:
        nodes = []
        edges = []
        slot_table = []
        for row in role_rows:
            role_id = str(row.get("role_id", ""))
            role_type = str(row.get("role_type", "role"))
            node_id = role_id or role_type
            nodes.append(f'  {node_id}["{node_id}: {role_type}"]')
            slot_table.append(
                {
                    "slot_id": role_id or role_type,
                    "role_type": role_type,
                    "transfer_note": f"Slot for {role_type}",
                }
            )
        for edge in stencil.get("relation_topology", []):
            source_id = str(edge.get("source_role_id", ""))
            target_id = str(edge.get("target_role_id", ""))
            primitive = str(edge.get("primitive", "links"))
            edges.append(f"  {source_id} -->|{primitive}| {target_id}")
        mermaid = "flowchart LR\n" + "\n".join(nodes + edges)
    else:
        mermaid = "flowchart LR\n  a[projected]"
        slot_table = []
    return {
        "gist": gist,
        "mermaid_topology": mermaid,
        "slot_table": slot_table,
    }


def project_stencil_draft(
    stencil_draft: Dict[str, Any],
    *,
    draft_index: int = 0,
    source_refs: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    normalized = normalize_stencil_draft(stencil_draft)
    proposed_name = str(stencil_draft.get("proposed_name", f"projected-stencil-{draft_index}"))
    fingerprint = compute_structural_fingerprint(
        {
            "role_entities": normalized.get("role_entities", []),
            "relation_topology": normalized.get("relation_topology", []),
            "dynamics_class": stencil_draft.get("dynamics_class"),
            "symmetry_profile": stencil_draft.get("symmetry_profile"),
        }
    )
    stencil_id = f"stencil-proj-{_slug(proposed_name)}-{fingerprint[:8]}"
    refs = list(source_refs or [])
    refs.extend(stencil_draft.get("evidence", {}).get("source_refs", []))
    canonical = {
        "id": stencil_id,
        "name": proposed_name,
        "status": "provisional",
        "role_entities": normalized.get("role_entities", []),
        "relation_topology": normalized.get("relation_topology", []),
        "dynamics_class": stencil_draft.get("dynamics_class", "other"),
        "symmetry_profile": stencil_draft.get("symmetry_profile", "unknown"),
        "facet_completeness": normalized.get(
            "facet_completeness",
            {"causal_geometry": True},
        ),
        "facets_extracted_order": stencil_draft.get(
            "facets_extracted_order",
            ["causal_geometry"],
        ),
        "confidence": float(stencil_draft.get("confidence", 0.5)),
        "possible_names": stencil_draft.get("possible_names", [proposed_name]),
        "evidence": {
            "source_refs": sorted(set(refs)) or ["projection"],
            "recurrence_count": 1,
        },
    }
    canonical["views"] = _build_views(canonical)
    canonical["structural_fingerprint"] = fingerprint
    return canonical


def resolve_stencil_projections(
    root: Path,
    stencil_drafts: Sequence[Dict[str, Any]],
    *,
    source_refs: Optional[Sequence[str]] = None,
) -> List[StencilProjection]:
    matches = match_stencil_drafts_to_seed(root, stencil_drafts)
    seed_by_id = {row["id"]: row for row in load_seed_stencils(root)}
    projections: List[StencilProjection] = []

    for index, stencil_draft in enumerate(stencil_drafts):
        match = matches[index] if index < len(matches) else {}
        fingerprint = str(match.get("fingerprint", ""))
        score = float(match.get("structural_score", 0.0))
        best_seed_id = match.get("best_seed_match_id")
        declared_refs = list(match.get("declared_seed_refs", []))
        declared_seed = declared_refs[0] if declared_refs and declared_refs[0] in seed_by_id else None

        if declared_seed:
            action = "merge_declared_seed"
            stencil_id = declared_seed
            canonical = dict(seed_by_id[declared_seed])
            canonical["structural_fingerprint"] = compute_structural_fingerprint(canonical)
            quarantine = False
            score = 1.0
        elif best_seed_id and score >= MERGE_SCORE_THRESHOLD:
            action = "merge_seed_fingerprint"
            stencil_id = str(best_seed_id)
            canonical = dict(seed_by_id[stencil_id])
            canonical["structural_fingerprint"] = fingerprint
            quarantine = False
        else:
            canonical = project_stencil_draft(
                stencil_draft,
                draft_index=index,
                source_refs=source_refs,
            )
            action = "register_provisional"
            stencil_id = str(canonical["id"])
            quarantine = True

        projections.append(
            StencilProjection(
                draft_index=index,
                proposed_name=str(stencil_draft.get("proposed_name", "")),
                fingerprint=fingerprint or str(canonical.get("structural_fingerprint", "")),
                action=action,
                stencil_id=stencil_id,
                structural_match_score=score,
                matched_seed_id=best_seed_id if action.startswith("merge") else None,
                canonical_stencil=canonical,
                quarantine=quarantine,
            )
        )
    return projections


def _primary_entity_ref(extraction_draft: Dict[str, Any]) -> Optional[str]:
    hint = extraction_draft.get("activation_snapshot_hint", {})
    dominant = hint.get("dominant_entity_refs") or []
    if dominant:
        return str(dominant[0])
    for shape in extraction_draft.get("candidate_shapes", []):
        refs = shape.get("entity_refs") or []
        if refs:
            return str(refs[0])
    entities = extraction_draft.get("entities", [])
    if entities:
        return str(entities[0].get("proposed_id", ""))
    return None


def _domain_skin_summary(extraction_draft: Dict[str, Any], projection: StencilProjection) -> str:
    for shape in extraction_draft.get("candidate_shapes", []):
        names = shape.get("possible_names") or []
        if names:
            return str(names[0])
    return projection.proposed_name


def build_shape_instances(
    extraction_draft: Dict[str, Any],
    projections: Sequence[StencilProjection],
) -> List[Dict[str, Any]]:
    subgraph_id = str(extraction_draft.get("subgraph_id", f"session-{extraction_draft.get('session_id', 'unknown')}"))
    draft_id = str(extraction_draft.get("draft_id", "draft"))
    entity_ref = _primary_entity_ref(extraction_draft)
    instances: List[Dict[str, Any]] = []

    for projection in projections:
        if not entity_ref:
            continue
        instances.append(
            {
                "id": make_id("shape-inst"),
                "entity_id": entity_ref,
                "stencil_id": projection.stencil_id,
                "subgraph_id": subgraph_id,
                "status": "provisional" if projection.quarantine else "provisional",
                "structural_match_score": projection.structural_match_score,
                "domain_skin_summary": _domain_skin_summary(extraction_draft, projection),
                "outcome_class": "unknown",
                "evidence_refs": [f"draft:{draft_id}", f"projection:{projection.action}"],
                "instantiated_at": utc_now(),
            }
        )
    return instances


def project_extraction_draft(root: Path, extraction_draft: Dict[str, Any]) -> ProjectionResult:
    session_id = str(extraction_draft.get("session_id", ""))
    source_refs = [f"draft:{extraction_draft.get('draft_id', '')}"]
    if session_id:
        source_refs.append(f"session:{session_id}")

    projections = resolve_stencil_projections(
        root,
        extraction_draft.get("stencil_drafts", []),
        source_refs=source_refs,
    )
    instances = build_shape_instances(extraction_draft, projections)
    active_stencil_ids = sorted({projection.stencil_id for projection in projections})
    quarantined = [
        projection.canonical_stencil
        for projection in projections
        if projection.quarantine and projection.canonical_stencil
    ]

    return ProjectionResult(
        session_id=session_id,
        draft_id=str(extraction_draft.get("draft_id", "")),
        subgraph_id=extraction_draft.get("subgraph_id"),
        stencil_projections=projections,
        shape_instances=instances,
        active_stencil_ids=active_stencil_ids,
        quarantined_stencils=[row for row in quarantined if row],
    )


def materialize_stencil_projection(
    root: Path,
    session_id: str,
    extraction_draft: Dict[str, Any],
    *,
    update_global_index: bool = False,
) -> Dict[str, Any]:
    report = validate_extraction_draft(root, extraction_draft)
    quarantine = assess_quarantine(extraction_draft, report)
    if not report.ok:
        return {
            "session_id": session_id,
            "ok": False,
            "errors": report.errors,
            "projected": False,
        }

    payload = dict(extraction_draft)
    payload["session_id"] = session_id
    projection = project_extraction_draft(root, payload)

    session_index_path = session_shape_index_path(root, session_id)
    session_index = merge_shape_index(
        load_shape_index(session_index_path, scope="session"),
        projection,
        session_id=session_id,
    )
    session_index["scope"] = "session"
    ensure_dir(session_index_path.parent)
    write_json(session_index_path, session_index)

    projection_payload = {
        "session_id": session_id,
        "draft_id": projection.draft_id,
        "subgraph_id": projection.subgraph_id,
        "validation_quarantine": quarantine.quarantine,
        "active_stencil_ids": projection.active_stencil_ids,
        "stencil_projections": [
            {
                "draft_index": row.draft_index,
                "proposed_name": row.proposed_name,
                "fingerprint": row.fingerprint,
                "action": row.action,
                "stencil_id": row.stencil_id,
                "structural_match_score": row.structural_match_score,
                "matched_seed_id": row.matched_seed_id,
                "quarantine": row.quarantine,
            }
            for row in projection.stencil_projections
        ],
        "shape_instances": projection.shape_instances,
        "quarantined_stencil_count": len(projection.quarantined_stencils),
    }
    projection_path = session_dir(root, session_id) / "mtsf" / "stencil_projection.json"
    write_json(projection_path, projection_payload)

    refs = {
        "mtsf_shape_index": str(session_index_path),
        "mtsf_stencil_projection": str(projection_path),
    }

    global_promotion: Dict[str, Any] = {"promoted": False}
    if update_global_index:
        global_promotion = promote_projection_to_global(
            root,
            projection,
            promotion_mode="auto",
            validation_quarantine=quarantine.quarantine,
        )
        if global_promotion.get("artifact_refs"):
            refs.update(global_promotion["artifact_refs"])

    return {
        "session_id": session_id,
        "ok": True,
        "projected": True,
        "artifact_refs": refs,
        "active_stencil_ids": projection.active_stencil_ids,
        "stencil_projections": projection_payload["stencil_projections"],
        "shape_instance_count": len(projection.shape_instances),
        "validation_quarantine": quarantine.quarantine,
        "global_promotion": global_promotion,
    }
