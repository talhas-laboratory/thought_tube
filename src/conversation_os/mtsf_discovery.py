from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence, Set

from .storage import ensure_dir, read_json, session_dir, utc_now, write_json

MODULE_ID = "kernel.mtsf.discovery"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "cross_session_shapes_path",
    "materialize_cross_session_shapes",
)
__all__ = list(PUBLIC_API)


def cross_session_shapes_path(root: Path) -> Path:
    return root / "memory" / "mtsf" / "cross_session_shapes.json"


def _shape_tokens(shape_id: str) -> Set[str]:
    slug = shape_id.lower().replace("cand-", "").replace("shape-", "")
    return {token for token in slug.split("-") if len(token) >= 4}


def materialize_cross_session_shapes(
    root: Path,
    *,
    session_ids: Sequence[str],
) -> Dict[str, Any]:
    by_shape_id: Dict[str, List[str]] = {}
    fragment_index: Dict[str, Set[str]] = defaultdict(set)

    for session_id in session_ids:
        draft_path = session_dir(root, session_id) / "mtsf" / "extraction_draft.json"
        if not draft_path.exists():
            continue
        draft = read_json(draft_path, default={})
        for shape in draft.get("candidate_shapes", []):
            proposed_id = str(shape.get("proposed_id", ""))
            if not proposed_id:
                continue
            sessions = by_shape_id.setdefault(proposed_id, [])
            if session_id not in sessions:
                sessions.append(session_id)
            for token in _shape_tokens(proposed_id):
                fragment_index[token].add(proposed_id)

    cross_session_refs: List[Dict[str, Any]] = []
    seen_exact: Set[tuple[str, tuple[str, ...]]] = set()
    seen_fragments: Set[str] = set()

    for shape_id, sessions in sorted(by_shape_id.items()):
        if len(sessions) < 2:
            continue
        key = (shape_id, tuple(sorted(sessions)))
        if key in seen_exact:
            continue
        seen_exact.add(key)
        cross_session_refs.append(
            {
                "candidate_shape_id": shape_id,
                "session_ids": sorted(sessions),
                "match_kind": "exact_id",
            }
        )

    for fragment, shape_ids in sorted(fragment_index.items()):
        involved_sessions: Set[str] = set()
        shape_refs: List[Dict[str, Any]] = []
        for shape_id in sorted(shape_ids):
            sessions = by_shape_id.get(shape_id, [])
            if not sessions:
                continue
            involved_sessions.update(sessions)
            shape_refs.append(
                {
                    "candidate_shape_id": shape_id,
                    "session_ids": sorted(sessions),
                }
            )
        if len(involved_sessions) < 2 or fragment in seen_fragments:
            continue
        seen_fragments.add(fragment)
        cross_session_refs.append(
            {
                "shared_fragment": fragment,
                "session_ids": sorted(involved_sessions),
                "match_kind": "shared_fragment",
                "shape_refs": shape_refs,
            }
        )

    payload = {
        "version": "1.0.0",
        "session_ids": list(session_ids),
        "cross_session_refs": cross_session_refs,
        "generated_at": utc_now(),
    }
    artifact_path = cross_session_shapes_path(root)
    ensure_dir(artifact_path.parent)
    write_json(artifact_path, payload)
    return {
        "cross_session_ref_count": len(cross_session_refs),
        "artifact_refs": {"mtsf_cross_session_shapes": str(artifact_path)},
    }
