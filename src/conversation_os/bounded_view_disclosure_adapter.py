"""Optional kernel bounded-view epistemic backend for disclosure (CAE-011)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from .storage import read_json


MODULE_ID = "kernel.disclosure.bounded_view_adapter"
CONTRACT_VERSION = "1.0"
DEFAULT_MAX_NODES = 8
KERNEL_REF_PREFIX = "kernel:"

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "DEFAULT_MAX_NODES",
    "KERNEL_REF_PREFIX",
    "load_bounded_view_disclosure_config",
    "bounded_view_epistemic_backend_enabled",
    "extract_bounded_view_grant_context",
    "map_bounded_view_to_evidence_blocks",
    "collect_bounded_view_evidence",
)
__all__ = list(PUBLIC_API)


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def load_bounded_view_disclosure_config(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    bounded_view = runtime.get("disclosure", {}).get("bounded_view", {}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    return {
        "epistemic_backend_v1": bool(
            bounded_view.get(
                "epistemic_backend_v1",
                disclosure.get("bounded_view_epistemic_backend_v1", False),
            )
        ),
        "max_nodes": max(1, int(bounded_view.get("max_nodes", DEFAULT_MAX_NODES) or DEFAULT_MAX_NODES)),
        "max_depth": max(0, int(bounded_view.get("max_depth", 3) or 3)),
    }


def bounded_view_epistemic_backend_enabled(root: Path) -> bool:
    return bool(load_bounded_view_disclosure_config(root)["epistemic_backend_v1"])


def _kernel_record_id(ref: str) -> str:
    value = str(ref or "").strip()
    if value.startswith(KERNEL_REF_PREFIX):
        return value[len(KERNEL_REF_PREFIX) :]
    return value


def extract_bounded_view_grant_context(
    effective_grant: Mapping[str, Any],
    *,
    root_record_ids: Sequence[str] | None = None,
) -> Dict[str, Any]:
    provenance = dict(effective_grant.get("provenance", {}) or {})
    branch_id = str(provenance.get("branch_id", "") or "").strip()
    scope_id = str(provenance.get("scope_id", "") or "").strip()

    roots: List[str] = []
    for ref in list(root_record_ids or []) + list(effective_grant.get("explicit_pins", []) or []):
        record_id = _kernel_record_id(str(ref))
        if record_id and record_id not in roots:
            roots.append(record_id)
    for ref in list(effective_grant.get("effective_refs", []) or []):
        record_id = _kernel_record_id(str(ref))
        if record_id and record_id not in roots:
            roots.append(record_id)

    return {
        "branch_id": branch_id,
        "scope_id": scope_id,
        "root_record_ids": roots,
    }


def map_bounded_view_to_evidence_blocks(
    view: Mapping[str, Any],
    *,
    branch_id: str,
    scope_id: str,
    max_nodes: int,
) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    for node in list(view.get("nodes", []) or []):
        record_id = str(node.get("record_id", "") or "").strip()
        if not record_id:
            continue
        node_branch = str(node.get("branch_id", "") or "").strip()
        if branch_id and node_branch and node_branch != branch_id:
            continue
        blocks.append(
            {
                "block_id": record_id,
                "source_ref": f"{KERNEL_REF_PREFIX}{record_id}",
                "label": str(node.get("record_kind", "") or "record"),
                "summary": str(node.get("epistemic_status", "") or "")[:240],
                "branch_id": node_branch or branch_id,
                "scope_id": scope_id,
                "depth": int(node.get("depth", 0) or 0),
                "provenance": {
                    "surface": "bounded_view",
                    "reference_only": True,
                    "record_kind": str(node.get("record_kind", "") or ""),
                    "epistemic_status": str(node.get("epistemic_status", "") or ""),
                },
            }
        )
        if len(blocks) >= max(1, int(max_nodes)):
            break
    return blocks


def _foundation_store_available(root: Path) -> bool:
    from .metaphysical_kernel_store import foundation_events_path

    return foundation_events_path(root).exists()


def collect_bounded_view_evidence(
    root: Path,
    effective_grant: Mapping[str, Any],
    *,
    root_record_ids: Sequence[str] | None = None,
) -> Dict[str, Any]:
    if not bounded_view_epistemic_backend_enabled(root):
        return {"count": 0, "result_status": "disabled", "blocks": []}

    config = load_bounded_view_disclosure_config(root)
    grant_context = extract_bounded_view_grant_context(
        effective_grant,
        root_record_ids=root_record_ids,
    )
    branch_id = grant_context["branch_id"]
    scope_id = grant_context["scope_id"]
    roots = grant_context["root_record_ids"]

    if not branch_id or not scope_id:
        return {
            "count": 0,
            "result_status": "abstained_missing_branch_scope",
            "blocks": [],
            "grant_context": grant_context,
        }
    if not roots:
        return {
            "count": 0,
            "result_status": "abstained_missing_root_records",
            "blocks": [],
            "grant_context": grant_context,
        }
    if not _foundation_store_available(root):
        return {
            "count": 0,
            "result_status": "abstained_dependency_not_ready",
            "blocks": [],
            "grant_context": grant_context,
        }

    from .metaphysical_kernel_runtime import BoundedViewQuery, FoundationRuntime

    runtime = FoundationRuntime(root)
    view = runtime.query_bounded_view(
        BoundedViewQuery(
            branch_id=branch_id,
            scope_id=scope_id,
            root_record_ids=roots,
            max_depth=int(config["max_depth"]),
            include_retracted=False,
        )
    )
    blocks = map_bounded_view_to_evidence_blocks(
        view.to_dict(),
        branch_id=branch_id,
        scope_id=scope_id,
        max_nodes=int(config["max_nodes"]),
    )
    if not blocks:
        return {
            "count": 0,
            "result_status": "empty_no_positive_match",
            "blocks": [],
            "grant_context": grant_context,
            "bounded_view": {
                "truncated": bool(view.truncated),
                "excluded_retracted": int(view.excluded_retracted),
            },
        }

    return {
        "count": len(blocks),
        "result_status": "disclosed",
        "blocks": blocks,
        "grant_context": grant_context,
        "bounded_view": {
            "truncated": bool(view.truncated),
            "excluded_retracted": int(view.excluded_retracted),
        },
        "provenance": {
            "surface": "bounded_view",
            "adapter_version": CONTRACT_VERSION,
            "reference_only": True,
        },
    }
