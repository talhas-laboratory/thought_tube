from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from .mtsf_stencils import compute_structural_fingerprint, load_seed_stencils
from .storage import append_jsonl, ensure_dir, make_id, read_json, session_dir, utc_now, write_json

MODULE_ID = "kernel.mtsf.index"
CONTRACT_VERSION = "1.0.0"
INDEX_VERSION = "1.2.0"
PROMOTION_CONFIDENCE_THRESHOLD = 0.75

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "INDEX_VERSION",
    "PROMOTION_CONFIDENCE_THRESHOLD",
    "IndexValidationReport",
    "default_shape_index_path",
    "default_index_events_path",
    "session_shape_index_path",
    "empty_shape_index",
    "load_shape_index",
    "validate_shape_index",
    "merge_shape_index",
    "promote_projection_to_global",
    "promote_session_to_global",
    "rebuild_global_index",
    "append_index_event",
    "find_instances_by_stencil",
    "find_wormhole_links",
    "find_orthogonal_candidates",
    "query_shape_index",
    "bootstrap_global_from_seed",
)
__all__ = list(PUBLIC_API)


@dataclass
class IndexValidationReport:
    ok: bool
    errors: List[str]
    warnings: List[str]


def default_shape_index_path(root: Path) -> Path:
    return root / "memory" / "mtsf" / "shape_index.json"


def default_index_events_path(root: Path) -> Path:
    return root / "memory" / "mtsf" / "index_events.jsonl"


def session_shape_index_path(root: Path, session_id: str) -> Path:
    return session_dir(root, session_id) / "mtsf" / "shape_index.json"


def empty_shape_index(*, scope: str = "session") -> Dict[str, Any]:
    return {
        "version": INDEX_VERSION,
        "scope": scope,
        "stencils": {},
        "fingerprints": {},
        "instances": [],
        "provisional_stencils": [],
        "stencil_stats": {},
        "sessions_contributed": {},
    }


def load_shape_index(path: Path, *, scope: Optional[str] = None) -> Dict[str, Any]:
    if not path.exists():
        return empty_shape_index(scope=scope or "session")
    payload = read_json(path, default={})
    if not payload:
        return empty_shape_index(scope=scope or "session")
    payload.setdefault("version", INDEX_VERSION)
    payload.setdefault("scope", scope or ("global" if "mtsf/shape_index.json" in str(path) else "session"))
    payload.setdefault("stencils", {})
    payload.setdefault("fingerprints", {})
    payload.setdefault("instances", [])
    payload.setdefault("provisional_stencils", [])
    payload.setdefault("stencil_stats", {})
    payload.setdefault("sessions_contributed", {})
    return payload


def validate_shape_index(index: Dict[str, Any]) -> IndexValidationReport:
    errors: List[str] = []
    warnings: List[str] = []

    if not index.get("version"):
        errors.append("missing version")
    if index.get("scope") not in {"session", "global"}:
        errors.append("scope must be session or global")

    stencils = index.get("stencils", {})
    fingerprints = index.get("fingerprints", {})
    for fingerprint, stencil_id in fingerprints.items():
        if stencil_id not in stencils:
            warnings.append(f"fingerprint {fingerprint} points to missing stencil {stencil_id}")

    instance_ids: Set[str] = set()
    for row in index.get("instances", []):
        instance_id = str(row.get("id", ""))
        if not instance_id:
            errors.append("instance missing id")
            continue
        if instance_id in instance_ids:
            warnings.append(f"duplicate instance id: {instance_id}")
        instance_ids.add(instance_id)
        stencil_id = str(row.get("stencil_id", ""))
        if stencil_id and stencil_id not in stencils:
            warnings.append(f"instance {instance_id} references unknown stencil {stencil_id}")

    for stencil_id, stats in index.get("stencil_stats", {}).items():
        if stencil_id not in stencils:
            warnings.append(f"stencil_stats entry for unknown stencil {stencil_id}")
        if int(stats.get("recurrence_count", 0)) < 1:
            warnings.append(f"stencil_stats.{stencil_id} has non-positive recurrence_count")

    return IndexValidationReport(ok=not errors, errors=errors, warnings=warnings)


def _stencil_summary(canonical: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(canonical)
    summary.pop("views", None)
    return summary


def _update_stencil_stats(
    stats: Dict[str, Any],
    *,
    stencil_id: str,
    session_id: str,
    subgraph_ids: Sequence[str],
    now: str,
) -> None:
    row = dict(stats.get(stencil_id, {}))
    session_ids = list(row.get("session_ids", []))
    is_new_session = bool(session_id and session_id not in session_ids)
    if session_id and session_id not in session_ids:
        session_ids.append(session_id)
    merged_subgraphs = list(row.get("subgraph_ids", []))
    for subgraph_id in subgraph_ids:
        if subgraph_id and subgraph_id not in merged_subgraphs:
            merged_subgraphs.append(subgraph_id)
    if is_new_session:
        row["recurrence_count"] = int(row.get("recurrence_count", 0)) + 1
    else:
        row.setdefault("recurrence_count", 1)
    row["session_ids"] = session_ids
    row["subgraph_ids"] = merged_subgraphs
    row.setdefault("first_seen_at", now)
    row["last_seen_at"] = now
    stats[stencil_id] = row


def merge_shape_index(
    index: Dict[str, Any],
    projection: Any,
    *,
    session_id: Optional[str] = None,
    promotion_mode: Optional[str] = None,
) -> Dict[str, Any]:
    merged = json.loads(json.dumps(index))
    merged.setdefault("scope", "session")
    merged.setdefault("stencil_stats", {})
    merged.setdefault("sessions_contributed", {})

    stencils = merged.setdefault("stencils", {})
    fingerprints = merged.setdefault("fingerprints", {})
    instances = merged.setdefault("instances", [])
    provisional = merged.setdefault("provisional_stencils", [])
    stats = merged.setdefault("stencil_stats", {})

    active_session_id = session_id or str(getattr(projection, "session_id", ""))
    draft_id = str(getattr(projection, "draft_id", ""))
    now = utc_now()

    existing_instance_ids = {str(row.get("id", "")) for row in instances}
    added_instances: List[Dict[str, Any]] = []
    for row in getattr(projection, "shape_instances", []):
        if row["id"] not in existing_instance_ids:
            instances.append(row)
            added_instances.append(row)
            existing_instance_ids.add(row["id"])

    active_stencil_ids: List[str] = []
    for stencil_projection in getattr(projection, "stencil_projections", []):
        canonical = stencil_projection.canonical_stencil
        if not canonical:
            continue
        stencil_id = stencil_projection.stencil_id
        active_stencil_ids.append(stencil_id)
        fingerprints[stencil_projection.fingerprint] = stencil_id
        if stencil_projection.quarantine:
            provisional_ids = {str(row.get("id", "")) for row in provisional}
            if stencil_id not in provisional_ids:
                provisional.append(canonical)
        stencils[stencil_id] = _stencil_summary(canonical)

        if merged.get("scope") == "global":
            subgraph_ids = sorted(
                {
                    str(row.get("subgraph_id", ""))
                    for row in added_instances
                    if str(row.get("stencil_id", "")) == stencil_id
                }
            )
            _update_stencil_stats(
                stats,
                stencil_id=stencil_id,
                session_id=active_session_id,
                subgraph_ids=subgraph_ids,
                now=now,
            )

    if merged.get("scope") == "global" and active_session_id:
        sessions_contributed = merged.setdefault("sessions_contributed", {})
        sessions_contributed[active_session_id] = {
            "promoted_at": now,
            "draft_id": draft_id,
            "promotion_mode": promotion_mode or "auto",
            "stencil_ids": sorted(set(active_stencil_ids)),
            "instance_count": len(added_instances),
        }

    merged["updated_at"] = now
    merged["last_session_id"] = active_session_id
    merged["last_draft_id"] = draft_id
    return merged


def append_index_event(root: Path, event: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(event)
    payload.setdefault("event_id", make_id("mtsf-idx-ev"))
    payload.setdefault("timestamp", utc_now())
    events_path = default_index_events_path(root)
    ensure_dir(events_path.parent)
    append_jsonl(events_path, payload)
    return payload


def bootstrap_global_from_seed(root: Path) -> Dict[str, Any]:
    index = empty_shape_index(scope="global")
    for seed in load_seed_stencils(root):
        stencil_id = str(seed["id"])
        fingerprint = compute_structural_fingerprint(seed)
        index["stencils"][stencil_id] = _stencil_summary(seed)
        index["fingerprints"][fingerprint] = stencil_id
    index["updated_at"] = utc_now()
    return index


def promote_projection_to_global(
    root: Path,
    projection: Any,
    *,
    promotion_mode: str = "auto",
    validation_quarantine: bool = False,
) -> Dict[str, Any]:
    if validation_quarantine:
        return {
            "promoted": False,
            "reason": "validation_quarantine",
            "artifact_refs": {},
        }

    global_index_path = default_shape_index_path(root)
    global_index = load_shape_index(global_index_path, scope="global")
    if not global_index.get("stencils"):
        global_index = bootstrap_global_from_seed(root)

    global_index = merge_shape_index(
        global_index,
        projection,
        session_id=str(getattr(projection, "session_id", "")),
        promotion_mode=promotion_mode,
    )
    ensure_dir(global_index_path.parent)
    write_json(global_index_path, global_index)

    event = append_index_event(
        root,
        {
            "kind": "session_promoted",
            "session_id": getattr(projection, "session_id", ""),
            "draft_id": getattr(projection, "draft_id", ""),
            "promotion_mode": promotion_mode,
            "stencil_ids": sorted({row.stencil_id for row in getattr(projection, "stencil_projections", [])}),
            "instance_count": len(getattr(projection, "shape_instances", [])),
        },
    )

    return {
        "promoted": True,
        "promotion_mode": promotion_mode,
        "artifact_refs": {"mtsf_global_shape_index": str(global_index_path)},
        "event_id": event["event_id"],
        "active_stencil_ids": sorted({row.stencil_id for row in getattr(projection, "stencil_projections", [])}),
    }


def _session_promotion_ready(root: Path, session_id: str) -> tuple[bool, str]:
    draft_path = session_dir(root, session_id) / "mtsf" / "extraction_draft.json"
    if draft_path.exists():
        draft = read_json(draft_path, default={})
        quarantine = draft.get("quarantine", {})
        if quarantine.get("quarantine"):
            return False, "validation_quarantine"
        if quarantine.get("promotion_ready"):
            return True, "promotion_ready"
        confidence = float(draft.get("confidence", 0.0))
        if confidence >= PROMOTION_CONFIDENCE_THRESHOLD:
            return True, "confidence_threshold"
        return False, "confidence_below_threshold"

    projection_path = session_dir(root, session_id) / "mtsf" / "stencil_projection.json"
    if projection_path.exists():
        projection = read_json(projection_path, default={})
        if projection.get("validation_quarantine"):
            return False, "validation_quarantine"
        return True, "projection_present"

    return False, "no_session_projection"


def promote_session_to_global(
    root: Path,
    session_id: str,
    *,
    mode: str = "auto",
) -> Dict[str, Any]:
    session_index_path = session_shape_index_path(root, session_id)
    projection_path = session_dir(root, session_id) / "mtsf" / "stencil_projection.json"
    if not session_index_path.exists() or not projection_path.exists():
        return {
            "session_id": session_id,
            "promoted": False,
            "reason": "missing_session_index_or_projection",
        }

    if mode == "auto":
        ready, reason = _session_promotion_ready(root, session_id)
        if not ready:
            return {
                "session_id": session_id,
                "promoted": False,
                "reason": reason,
            }

    session_index = load_shape_index(session_index_path, scope="session")
    projection_payload = read_json(projection_path, default={})

    class _SessionPromotionProjection:
        def __init__(self) -> None:
            self.session_id = session_id
            self.draft_id = str(projection_payload.get("draft_id", ""))
            self.shape_instances = list(session_index.get("instances", []))
            self.stencil_projections = [
                type(
                    "StencilProjection",
                    (),
                    {
                        "stencil_id": row["stencil_id"],
                        "fingerprint": row["fingerprint"],
                        "quarantine": row.get("quarantine", False),
                        "canonical_stencil": session_index.get("stencils", {}).get(row["stencil_id"]),
                    },
                )()
                for row in projection_payload.get("stencil_projections", [])
            ]

    projection = _SessionPromotionProjection()
    validation_quarantine = bool(projection_payload.get("validation_quarantine"))
    result = promote_projection_to_global(
        root,
        projection,
        promotion_mode="explicit" if mode == "force" else mode,
        validation_quarantine=validation_quarantine if mode == "auto" else False,
    )
    result["session_id"] = session_id
    return result


def rebuild_global_index(root: Path, *, session_ids: Optional[Sequence[str]] = None) -> Dict[str, Any]:
    global_index = bootstrap_global_from_seed(root)
    sessions_dir = root / "memory" / "sessions"
    scanned: List[str] = []

    if session_ids is not None:
        candidates = [sessions_dir / session_id for session_id in session_ids]
    else:
        candidates = sorted(sessions_dir.glob("*/")) if sessions_dir.exists() else []

    merged_sessions = 0
    for candidate in candidates:
        session_id = candidate.name if candidate.is_dir() else str(candidate)
        session_index_path = session_shape_index_path(root, session_id)
        if not session_index_path.exists():
            continue
        session_index = load_shape_index(session_index_path, scope="session")
        if not session_index.get("instances") and not session_index.get("stencils"):
            continue

        class _RebuildProjection:
            def __init__(self, sid: str, payload: Dict[str, Any]) -> None:
                self.session_id = sid
                self.draft_id = str(payload.get("last_draft_id", ""))
                self.shape_instances = list(payload.get("instances", []))
                self.stencil_projections = [
                    type(
                        "StencilProjection",
                        (),
                        {
                            "stencil_id": stencil_id,
                            "fingerprint": next(
                                (
                                    fingerprint
                                    for fingerprint, mapped_id in payload.get("fingerprints", {}).items()
                                    if mapped_id == stencil_id
                                ),
                                "",
                            ),
                            "quarantine": any(
                                str(row.get("id", "")) == stencil_id
                                for row in payload.get("provisional_stencils", [])
                            ),
                            "canonical_stencil": payload.get("stencils", {}).get(stencil_id),
                        },
                    )()
                    for stencil_id in payload.get("stencils", {})
                ]

        global_index = merge_shape_index(
            global_index,
            _RebuildProjection(session_id, session_index),
            session_id=session_id,
            promotion_mode="rebuild",
        )
        scanned.append(session_id)
        merged_sessions += 1

    now = utc_now()
    global_index["rebuilt_at"] = now
    global_index["updated_at"] = now

    global_index_path = default_shape_index_path(root)
    ensure_dir(global_index_path.parent)
    write_json(global_index_path, global_index)

    event = append_index_event(
        root,
        {
            "kind": "global_rebuilt",
            "session_ids": scanned,
            "merged_session_count": merged_sessions,
            "stencil_count": len(global_index.get("stencils", {})),
            "instance_count": len(global_index.get("instances", [])),
        },
    )

    return {
        "rebuilt": True,
        "merged_session_count": merged_sessions,
        "session_ids": scanned,
        "artifact_refs": {"mtsf_global_shape_index": str(global_index_path)},
        "event_id": event["event_id"],
        "stencil_count": len(global_index.get("stencils", {})),
        "instance_count": len(global_index.get("instances", [])),
    }


def find_instances_by_stencil(index: Dict[str, Any], stencil_id: str) -> List[Dict[str, Any]]:
    return [
        row
        for row in index.get("instances", [])
        if str(row.get("stencil_id", "")) == stencil_id
    ]


def find_wormhole_links(
    index: Dict[str, Any],
    *,
    stencil_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    instances = index.get("instances", [])
    stencil_ids: Set[str]
    if stencil_id:
        stencil_ids = {stencil_id}
    else:
        stencil_ids = {str(row.get("stencil_id", "")) for row in instances if row.get("stencil_id")}

    links: List[Dict[str, Any]] = []
    for sid in sorted(stencil_ids):
        rows = find_instances_by_stencil(index, sid)
        subgraphs: Dict[str, List[Dict[str, Any]]] = {}
        for row in rows:
            subgraphs.setdefault(str(row.get("subgraph_id", "")), []).append(row)
        if len(subgraphs) < 2:
            continue
        subgraph_keys = sorted(subgraphs)
        pairs = []
        for left in subgraph_keys:
            for right in subgraph_keys:
                if left >= right:
                    continue
                for left_row in subgraphs[left]:
                    for right_row in subgraphs[right]:
                        pairs.append(
                            {
                                "left_subgraph_id": left,
                                "left_entity_id": left_row.get("entity_id"),
                                "left_instance_id": left_row.get("id"),
                                "right_subgraph_id": right,
                                "right_entity_id": right_row.get("entity_id"),
                                "right_instance_id": right_row.get("id"),
                            }
                        )
        links.append(
            {
                "stencil_id": sid,
                "stencil_name": index.get("stencils", {}).get(sid, {}).get("name", sid),
                "subgraph_count": len(subgraphs),
                "instance_count": len(rows),
                "pairs": pairs,
            }
        )
    return links


def _structural_similarity(left: Dict[str, Any], right: Dict[str, Any]) -> float:
    score = 0.0
    if left.get("dynamics_class") and left.get("dynamics_class") == right.get("dynamics_class"):
        score += 0.35
    if left.get("symmetry_profile") and left.get("symmetry_profile") == right.get("symmetry_profile"):
        score += 0.25
    left_roles = {str(row.get("role_type", "")) for row in left.get("role_entities", [])}
    right_roles = {str(row.get("role_type", "")) for row in right.get("role_entities", [])}
    if left_roles and right_roles:
        overlap = len(left_roles & right_roles) / max(len(left_roles | right_roles), 1)
        score += 0.25 * overlap
    left_edges = {
        (
            str(edge.get("source_role_id", "")),
            str(edge.get("primitive", "")),
            str(edge.get("target_role_id", "")),
        )
        for edge in left.get("relation_topology", [])
    }
    right_edges = {
        (
            str(edge.get("source_role_id", "")),
            str(edge.get("primitive", "")),
            str(edge.get("target_role_id", "")),
        )
        for edge in right.get("relation_topology", [])
    }
    if left_edges and right_edges:
        edge_overlap = len(left_edges & right_edges) / max(len(left_edges | right_edges), 1)
        score += 0.15 * edge_overlap
    return round(min(score, 1.0), 4)


def find_orthogonal_candidates(
    index: Dict[str, Any],
    stencil_id: str,
    *,
    min_score: float = 0.45,
    max_results: int = 5,
) -> List[Dict[str, Any]]:
    source = index.get("stencils", {}).get(stencil_id)
    if not source:
        return []

    source_fingerprint = next(
        (fingerprint for fingerprint, mapped_id in index.get("fingerprints", {}).items() if mapped_id == stencil_id),
        "",
    )
    candidates: List[Dict[str, Any]] = []
    for candidate_id, candidate in index.get("stencils", {}).items():
        if candidate_id == stencil_id:
            continue
        candidate_fingerprint = next(
            (
                fingerprint
                for fingerprint, mapped_id in index.get("fingerprints", {}).items()
                if mapped_id == candidate_id
            ),
            "",
        )
        if candidate_fingerprint and candidate_fingerprint == source_fingerprint:
            continue
        score = _structural_similarity(source, candidate)
        if score < min_score:
            continue
        candidates.append(
            {
                "stencil_id": candidate_id,
                "name": candidate.get("name", candidate_id),
                "structural_similarity": score,
                "dynamics_class": candidate.get("dynamics_class"),
                "symmetry_profile": candidate.get("symmetry_profile"),
            }
        )
    candidates.sort(key=lambda row: (-row["structural_similarity"], row["stencil_id"]))
    return candidates[:max_results]


def query_shape_index(
    root: Path,
    *,
    stencil_id: Optional[str] = None,
    subgraph_id: Optional[str] = None,
    session_id: Optional[str] = None,
    scope: str = "global",
) -> Dict[str, Any]:
    if scope == "session":
        if not session_id:
            raise ValueError("session_id is required when scope=session")
        index = load_shape_index(session_shape_index_path(root, session_id), scope="session")
    else:
        index = load_shape_index(default_shape_index_path(root), scope="global")

    instances = index.get("instances", [])
    if stencil_id:
        instances = [row for row in instances if str(row.get("stencil_id", "")) == stencil_id]
    if subgraph_id:
        instances = [row for row in instances if str(row.get("subgraph_id", "")) == subgraph_id]
    if session_id and scope == "global":
        contributed = index.get("sessions_contributed", {}).get(session_id)
        if contributed:
            allowed = set(contributed.get("stencil_ids", []))
            instances = [row for row in instances if str(row.get("stencil_id", "")) in allowed]

    report = validate_shape_index(index)
    result: Dict[str, Any] = {
        "scope": index.get("scope", scope),
        "index_path": str(
            session_shape_index_path(root, session_id)
            if scope == "session" and session_id
            else default_shape_index_path(root)
        ),
        "stencil_count": len(index.get("stencils", {})),
        "instance_count": len(instances),
        "instances": instances,
        "validation_ok": report.ok,
        "validation_errors": report.errors,
        "validation_warnings": report.warnings,
    }
    if stencil_id:
        result["wormhole_links"] = find_wormhole_links(index, stencil_id=stencil_id)
        result["orthogonal_candidates"] = find_orthogonal_candidates(index, stencil_id)
        result["stencil_stats"] = index.get("stencil_stats", {}).get(stencil_id)
    return result
