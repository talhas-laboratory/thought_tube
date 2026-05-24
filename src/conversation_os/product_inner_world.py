from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .analysis import update_manifest
from .chat_backends import request_openclaw_reply, resolve_chat_backend
from .conversation_synthesis import (
    load_concept_edges,
    load_concept_nodes,
    load_concept_review_queue,
    load_synthesis_packets,
    load_touch_operations,
    rebuild_conversation_concepts,
    search_concepts,
)
from .cost_tracker import get_cost_summary, list_cost_events
from .analysis_units import build_analysis_units, load_analysis_units as _load_analysis_units
from .conversation_deltas import build_conversation_deltas, load_conversation_deltas, load_user_expectations
from .judgment import classify_run
from .context_bubbles import (
    build_context_bubbles,
    get_context_bubble,
    list_context_bubbles,
    load_bubble_edges as _load_bubble_edges,
    load_bubble_memberships as _load_bubble_memberships,
    load_bubble_transitions as _load_bubble_transitions,
    load_context_bubbles as _load_context_bubbles,
)
from .conversation_threads import (
    build_conversation_threads,
    load_conversation_threads as _load_conversation_threads,
    load_thread_links as _load_thread_links,
)
from .library_tracker import (
    _ensure_runtime_graph,
    _materialize_connections as _materialize_connections_admin,
    _merged_pond_router_config,
    _merged_runtime_model_roles,
    _runtime_config_path,
    _runtime_config_payload,
    apply_pond_router_preset as apply_pond_router_preset_admin,
    clear_pending_governance_rederive,
    classify_assisted_dimension as classify_assisted_dimension_admin,
    classify_assisted_pond_route as classify_assisted_pond_route_admin,
    get_chunk_pond_detail as get_chunk_pond_detail_admin,
    get_chunk_pond_routing_state,
    get_dimension_model_role_status as get_dimension_model_role_status_admin,
    get_library_status as get_library_tracker_status,
    get_pond_router_status as get_pond_router_status_admin,
    load_chunk_dimension_profiles,
    load_dimension_registry,
    load_library_governance,
    load_pond_routing_feedback as load_pond_routing_feedback_admin,
    match_chunk_dimension_profiles,
    override_chunk_pond_routing,
    record_pond_routing_feedback as record_pond_routing_feedback_admin,
    resolve_governed_chunk_rows,
    resolve_governed_source_rows,
    scan_library_sources as scan_library_tracker_sources,
    sync_library_sources as sync_library_tracker_sources,
    derive_graph as derive_graph_admin,
    update_chunk_pond_detail as update_chunk_pond_detail_admin,
    update_dimension_model_role_binding as update_dimension_model_role_binding_admin,
    update_pond_router_config as update_pond_router_config_admin,
    update_family_governance,
    update_source_governance,
    ensure_runtime_model_roles,
)
from .knowledge_layer import (
    add_alias_resolution,
    build_knowledge_layer,
    build_retrieval_bundle,
    govern_context_link,
    load_context_links as _load_context_links,
    load_link_governance,
    load_knowledge_edges as _load_knowledge_edges,
    load_knowledge_nodes as _load_knowledge_nodes,
    load_semantic_capsules as _load_semantic_capsules,
    select_candidate_pairs,
)
from .meta_layer import extract_meta_layer, load_meta_records as _load_meta_records, meta_layer_dir
from .meta_objects import META_LAYER_FILES
from .pipelines import ensure_pipeline_specs
from .pipeline_runner import run_pipeline
from .plugins import load_plugins
from .policy_engine import load_policy_snapshot, update_policy_snapshot
from .review_queue import (
    load_promotion_packets as _load_promotion_packets,
    load_review_queue as _load_review_queue,
    write_review_state,
)
from .runtime_pipeline import (
    ensure_runtime_pipeline_config,
    execute_runtime_pipeline,
    get_runtime_pipeline_status,
    load_runtime_pipeline_config,
    update_runtime_pipeline_component as update_runtime_pipeline_component_config,
)
from .models import ConversationEvent, SessionManifest
from .storage import ensure_dir, make_id, read_json, read_jsonl, utc_now, write_json, write_jsonl, write_markdown
from .storage import append_jsonl, session_dir, session_events_path
from .thought_factory import (
    build_archive_rows,
    build_feed_rows,
    build_thought_packets,
    load_thought_packets as _load_thought_packets,
)
from .thread_context import build_thread_packet
from .thread_abstractions import (
    build_thread_abstractions,
    load_project_lenses as _load_project_lenses,
    load_thread_abstraction_links as _load_thread_abstraction_links,
    load_thread_abstractions as _load_thread_abstractions,
)
from .vault_ingest import (
    _runtime_chunk_view,
    bootstrap_legacy_source_items,
    ingest_source_file,
    ingest_text_content,
    load_chunk_index,
    load_chunk_index_raw,
    load_source_registry,
    load_source_registry_raw,
    shorten,
    tokenize,
)


MODULE_ID = "surface.inner_world.product_inner_world"
CONTRACT_VERSION = "1.0"
_ASSEMBLY_HOOKS = (
    "ensure_surface_recipe",
    "load_surface_recipe",
)
_SURFACE_EXPERIENCE_API = (
    "get_retrieval_bundle",
    "get_linking_overview",
    "get_link_governance_state",
    "update_link_governance",
    "create_link_alias_resolution",
    "generate_daily_batch",
    "build_thought_feed",
    "build_thought_archive",
    "list_bubbles",
    "get_bubble_detail",
    "filter_knowledge_components",
    "get_thought_detail",
    "get_source_item_detail",
    "get_thread_detail",
    "chat_with_thought",
    "save_thread",
    "delete_thread",
    "record_feedback",
    "ensure_mobile_capture_session",
    "append_mobile_capture",
    "reply_in_mobile_session",
    "build_mobile_feed",
    "save_mobile_feed_item",
    "build_mobile_library",
    "export_state",
    "get_runtime_overview",
)
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    *_ASSEMBLY_HOOKS,
    *_SURFACE_EXPERIENCE_API,
)
__all__ = list(PUBLIC_API)


def _data_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data"


def _exports_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "exports"


def _threads_dir(root: Path) -> Path:
    return _data_dir(root) / "threads"


def _thought_feed_path(root: Path) -> Path:
    return _data_dir(root) / "thought_feed.json"


def _feed_learning_events_path(root: Path) -> Path:
    return _data_dir(root) / "feed_learning_events.jsonl"


def _feed_taste_profile_path(root: Path) -> Path:
    return _data_dir(root) / "feed_taste_profile.json"


def _context_bubbles_progress_path(root: Path) -> Path:
    return _data_dir(root) / "context_bubbles_progress.json"


def _surface_recipe_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "surface_recipe.v1.json"


def _default_surface_recipe(root: Path) -> Dict[str, Any]:
    return {
        "recipe_id": "recipe.inner_world.v1",
        "surface_id": "surface.inner_world",
        "name": "Inner World v1 Reference Surface",
        "status": "transitional",
        "version": "0.1.0",
        "target_layer": "surface",
        "purpose": (
            "Present evidence-backed thoughts as a feed, archive, article expansion, "
            "and scoped chat surface over the conversation substrate."
        ),
        "module_refs": [
            {
                "module_id": "kernel.foundation.storage",
                "version_range": ">=0.1.0",
                "required": True,
                "notes": "Shared storage boundary used by the reference surface.",
            },
            {
                "module_id": "kernel.foundation.models",
                "version_range": ">=0.1.0",
                "required": True,
                "notes": "Shared record shapes used by runtime and surface payloads.",
            },
            {
                "module_id": "kernel.analysis.analysis_units",
                "version_range": ">=0.1.0",
                "required": True,
                "notes": "Provides canonical analysis units for downstream shaping.",
            },
            {
                "module_id": "kernel.meta.meta_objects",
                "version_range": ">=0.1.0",
                "required": True,
                "notes": "Provides canonical meta-layer vocabulary.",
            },
            {
                "module_id": "kernel.runtime.cost_tracker",
                "version_range": ">=0.1.0",
                "required": False,
                "notes": "Tracks runtime and equivalent LLM cost events.",
            },
            {
                "module_id": "kernel.reasoning.judgment",
                "version_range": ">=0.1.0",
                "required": False,
                "notes": "Classifies thought-surfacing runs for review and evidence state.",
            },
        ],
        "adapter_refs": [
            {
                "adapter_id": "surface.inner_world.runtime_payloads",
                "repo_paths": ["src/conversation_os/product_inner_world.py"],
                "purpose": "Shape runtime state into feed, archive, detail, and chat payloads.",
                "depends_on": [
                    "kernel.analysis.analysis_units",
                    "kernel.runtime.cost_tracker",
                    "kernel.reasoning.judgment",
                ],
            },
            {
                "adapter_id": "surface.inner_world.browser_surface",
                "repo_paths": [
                    "src/conversation_os/miniapp.py",
                    "product/inner_world_v1/miniapp",
                ],
                "purpose": "Serve the browser-facing Inner World and World Studio interface.",
                "depends_on": ["surface.inner_world.runtime_payloads"],
            },
        ],
        "policy_defaults": {
            "source_visibility": "governed",
            "contradiction_review": "required",
            "chat_backend": "heuristic",
        },
        "runtime_dependencies": [
            "product/inner_world_v1/config/runtime.json",
            "product/inner_world_v1/config/runtime_pipeline.json",
            "product/inner_world_v1/pipelines/*.json",
        ],
        "state_dependencies": [
            "memory/events",
            "memory/sessions",
            "product/inner_world_v1/data",
        ],
        "entrypoints": [
            "python3 tools/run_inner_world_miniapp.py",
            "python3 tools/run_inner_world_backend.py",
            "python3 tools/conversation_os.py inner-world serve --domains research,art,entrepreneurship",
        ],
        "config_path": str(_surface_recipe_path(root)),
    }


def ensure_surface_recipe(root: Path) -> Path:
    path = _surface_recipe_path(root)
    if not path.exists():
        write_json(path, _default_surface_recipe(root))
    return path


def load_surface_recipe(root: Path) -> Dict[str, Any]:
    path = ensure_surface_recipe(root)
    payload = read_json(path, default={}) or {}
    default_payload = _default_surface_recipe(root)
    recipe = dict(default_payload)
    recipe.update(payload)
    recipe["config_path"] = str(path)
    return recipe


def _runtime_source_visibility(root: Path) -> Dict[str, bool]:
    return {
        str(row.get("source_ref", "")).strip(): bool(row.get("include_in_runtime", True))
        for row in resolve_governed_source_rows(root, load_source_registry_raw(root))
        if str(row.get("source_ref", "")).strip()
    }


def _refs_from_fields(row: Dict[str, Any], fields: Iterable[str]) -> List[str]:
    refs: List[str] = []
    for field in fields:
        value = row.get(field)
        if isinstance(value, list):
            refs.extend(str(item).strip() for item in value if str(item).strip())
        elif isinstance(value, str):
            ref = value.strip()
            if ref:
                refs.append(ref)
    return refs


def _row_visible_by_sources(
    row: Dict[str, Any],
    source_visibility: Dict[str, bool],
    *,
    fields: Iterable[str],
) -> bool:
    refs = _refs_from_fields(row, fields)
    if not refs:
        return True
    return all(source_visibility.get(ref, True) for ref in refs)


def _filter_rows_by_runtime_sources(
    root: Path,
    rows: List[Dict[str, Any]],
    *,
    fields: Iterable[str],
) -> List[Dict[str, Any]]:
    source_visibility = _runtime_source_visibility(root)
    return [
        row
        for row in rows
        if _row_visible_by_sources(row, source_visibility, fields=fields)
    ]


def _filter_thought_surface_payload(root: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    thoughts = _filter_rows_by_runtime_sources(root, payload.get("thoughts", []), fields=("source_ref", "source_refs"))
    return {
        **payload,
        "count": len(thoughts),
        "thoughts": thoughts,
    }


def load_analysis_units(root: Path) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    return [
        row
        for row in _load_analysis_units(root)
        if _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs"))
    ]


def load_meta_records(root: Path, kinds: List[str] | None = None) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    return [
        row
        for row in _load_meta_records(root, kinds)
        if _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs"))
    ]


def _iter_jsonl_rows(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            yield json.loads(line)


def _targeted_meta_lookup(root: Path, meta_ids: Iterable[str]) -> Dict[str, Dict]:
    requested_ids = {str(meta_id).strip() for meta_id in meta_ids if str(meta_id).strip()}
    if not requested_ids:
        return {}
    source_visibility = _runtime_source_visibility(root)
    grouped_ids: Dict[str, set[str]] = {}
    unknown_ids: set[str] = set()
    for meta_id in requested_ids:
        kind = meta_id.split("-", 1)[0]
        if kind in META_LAYER_FILES:
            grouped_ids.setdefault(kind, set()).add(meta_id)
        else:
            unknown_ids.add(meta_id)
    if unknown_ids:
        for kind in META_LAYER_FILES:
            grouped_ids.setdefault(kind, set()).update(unknown_ids)
    lookup: Dict[str, Dict] = {}
    for kind, ids_for_kind in grouped_ids.items():
        remaining_ids = set(ids_for_kind) - set(lookup)
        if not remaining_ids:
            continue
        path = meta_layer_dir(root) / META_LAYER_FILES[kind]
        for row in _iter_jsonl_rows(path):
            meta_id = str(row.get("meta_id", "")).strip()
            if meta_id not in remaining_ids:
                continue
            if not _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs")):
                continue
            lookup[meta_id] = row
            remaining_ids.discard(meta_id)
            if not remaining_ids:
                break
    return lookup


def _targeted_chunk_lookup(root: Path, source_item_ids: Iterable[str]) -> Dict[str, Dict]:
    requested_ids = {str(item_id).strip() for item_id in source_item_ids if str(item_id).strip()}
    if not requested_ids:
        return {}
    matched_rows: List[Dict[str, Any]] = []
    remaining_ids = set(requested_ids)
    chunk_index_path = _data_dir(root) / "chunk_index.jsonl"
    for row in _iter_jsonl_rows(chunk_index_path):
        row_ids = {
            str(row.get("source_item_id", "")).strip(),
            str(row.get("chunk_id", "")).strip(),
        }
        row_ids.discard("")
        if not remaining_ids.intersection(row_ids):
            continue
        matched_rows.append(row)
        remaining_ids.difference_update(row_ids)
        if not remaining_ids:
            break
    if not matched_rows:
        return {}
    governed_rows = resolve_governed_chunk_rows(
        root,
        chunk_rows=matched_rows,
        governance=load_library_governance(root),
    )
    lookup: Dict[str, Dict] = {}
    for row in governed_rows:
        if not row.get("include_in_runtime", True):
            continue
        normalized = _runtime_chunk_view(row)
        if not str(normalized.get("content", "")).strip():
            continue
        row_id = str(normalized.get("source_item_id", "")).strip() or str(normalized.get("chunk_id", "")).strip()
        if row_id:
            lookup[row_id] = normalized
    return lookup


def load_conversation_threads(root: Path) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    return [
        row
        for row in _load_conversation_threads(root)
        if _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs"))
    ]


def load_thread_links(root: Path) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    visible_thread_ids = {row["thread_id"] for row in load_conversation_threads(root)}
    return [
        row
        for row in _load_thread_links(root)
        if row.get("from_thread_id") in visible_thread_ids
        and row.get("to_thread_id") in visible_thread_ids
        and _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs"))
    ]


def load_thread_abstractions(root: Path) -> List[Dict]:
    visible_thread_ids = {row["thread_id"] for row in load_conversation_threads(root)}
    rows: List[Dict] = []
    for row in _load_thread_abstractions(root):
        child_thread_ids = [thread_id for thread_id in row.get("child_thread_ids", []) if thread_id in visible_thread_ids]
        if not child_thread_ids:
            continue
        rows.append({**row, "child_thread_ids": child_thread_ids})
    return rows


def load_thread_abstraction_links(root: Path) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    visible_thread_ids = {row["thread_id"] for row in load_conversation_threads(root)}
    visible_abstraction_ids = {row["abstract_thread_id"] for row in load_thread_abstractions(root)}
    rows = []
    for row in _load_thread_abstraction_links(root):
        from_id = row.get("from_id", "")
        to_id = row.get("to_id", "")
        if from_id not in visible_thread_ids and from_id not in visible_abstraction_ids:
            continue
        if to_id not in visible_thread_ids and to_id not in visible_abstraction_ids:
            continue
        if not _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs", "evidence_refs")):
            continue
        rows.append(row)
    return rows


def load_project_lenses(root: Path) -> List[Dict]:
    visible_abstraction_ids = {row["abstract_thread_id"] for row in load_thread_abstractions(root)}
    rows = []
    for row in _load_project_lenses(root):
        linked_ids = [
            abstraction_id
            for abstraction_id in row.get("abstract_thread_ids", [])
            if abstraction_id in visible_abstraction_ids
        ]
        if row.get("abstract_thread_ids") and not linked_ids:
            continue
        if linked_ids:
            rows.append({**row, "abstract_thread_ids": linked_ids})
        else:
            rows.append(row)
    return rows


def load_context_bubbles(root: Path) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    return [
        row
        for row in _load_context_bubbles(root)
        if _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs"))
    ]


def load_bubble_memberships(root: Path) -> List[Dict]:
    visible_bubble_ids = {row["bubble_id"] for row in load_context_bubbles(root)}
    return [row for row in _load_bubble_memberships(root) if row.get("bubble_id") in visible_bubble_ids]


def load_bubble_edges(root: Path) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    visible_bubble_ids = {row["bubble_id"] for row in load_context_bubbles(root)}
    return [
        row
        for row in _load_bubble_edges(root)
        if row.get("from_bubble_id") in visible_bubble_ids
        and row.get("to_bubble_id") in visible_bubble_ids
        and _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs", "evidence_refs"))
    ]


def load_bubble_transitions(root: Path) -> List[Dict]:
    visible_bubble_ids = {row["bubble_id"] for row in load_context_bubbles(root)}
    rows = []
    for row in _load_bubble_transitions(root):
        bubble_id = row.get("bubble_id")
        related_bubble_id = row.get("related_bubble_id")
        if bubble_id not in visible_bubble_ids:
            continue
        if related_bubble_id and related_bubble_id not in visible_bubble_ids:
            continue
        rows.append(row)
    return rows


def load_knowledge_nodes(root: Path) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    return [
        row
        for row in _load_knowledge_nodes(root)
        if _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs", "evidence_refs"))
    ]


def load_knowledge_edges(root: Path) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    visible_node_ids = {row["node_id"] for row in load_knowledge_nodes(root)}
    return [
        row
        for row in _load_knowledge_edges(root)
        if row.get("from_id") in visible_node_ids
        and row.get("to_id") in visible_node_ids
        and _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs", "evidence_refs"))
    ]


def load_semantic_capsules(root: Path) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    visible_bubble_ids = {row["bubble_id"] for row in load_context_bubbles(root)}
    rows = []
    for row in _load_semantic_capsules(root):
        if not _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs", "evidence_refs")):
            continue
        if row.get("ref_type") == "bubble" and row.get("ref_id") not in visible_bubble_ids:
            continue
        rows.append(row)
    return rows


def load_context_links(root: Path) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    visible_bubble_ids = {row["bubble_id"] for row in load_context_bubbles(root)}
    visible_meta_ids = {row["meta_id"] for row in load_bubble_memberships(root)}
    rows = []
    for row in _load_context_links(root):
        if not _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs", "evidence_refs")):
            continue
        if row.get("from_ref_type") == "bubble" and row.get("from_ref_id") not in visible_bubble_ids:
            continue
        if row.get("to_ref_type") == "bubble" and row.get("to_ref_id") not in visible_bubble_ids:
            continue
        if row.get("from_ref_type") == "meta" and row.get("to_ref_type") == "bubble" and row.get("from_ref_id") not in visible_meta_ids:
            continue
        if row.get("to_ref_type") == "meta" and row.get("from_ref_type") == "bubble" and row.get("to_ref_id") not in visible_meta_ids:
            continue
        rows.append(row)
    return rows


def load_review_queue(root: Path) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    return [
        row
        for row in _load_review_queue(root)
        if _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs"))
    ]


def load_promotion_packets(root: Path) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    return [
        row
        for row in _load_promotion_packets(root)
        if _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs"))
    ]


def load_thought_packets(root: Path) -> List[Dict]:
    source_visibility = _runtime_source_visibility(root)
    return [
        row
        for row in _load_thought_packets(root)
        if _row_visible_by_sources(row, source_visibility, fields=("source_ref", "source_refs"))
    ]


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _thought_runtime_guard(root: Path) -> Dict | None:
    pipeline_status = get_runtime_pipeline_status(root)
    pipeline_summary = pipeline_status.get("summary") or {}
    runtime_counts = {
        "context_bubbles": _count_jsonl_rows(_data_dir(root) / "context_bubbles.jsonl"),
        "knowledge_nodes": _count_jsonl_rows(_data_dir(root) / "knowledge_nodes.jsonl"),
        "knowledge_edges": _count_jsonl_rows(_data_dir(root) / "knowledge_edges.jsonl"),
    }
    if pipeline_summary.get("run_status") == "running":
        return {
            "status": "rebuilding",
            "pipeline_summary": pipeline_summary,
            "runtime_counts": runtime_counts,
            "context_bubbles_progress": read_json(_context_bubbles_progress_path(root), default={}) or {},
        }
    if not all(runtime_counts.values()):
        return {
            "status": "runtime_not_ready",
            "pipeline_summary": pipeline_summary,
            "runtime_counts": runtime_counts,
            "context_bubbles_progress": read_json(_context_bubbles_progress_path(root), default={}) or {},
        }
    return None


def _empty_thought_surface(root: Path, *, surface: str, guard: Dict) -> Dict:
    payload = {
        "generated_at": utc_now(),
        "status": guard["status"],
        "pipeline_summary": guard.get("pipeline_summary"),
        "runtime_counts": guard.get("runtime_counts", {}),
        "context_bubbles_progress": guard.get("context_bubbles_progress", {}),
    }
    if surface == "feed":
        return payload | {"count": 0, "thoughts": []}
    if surface == "archive":
        return payload | {"count": 0, "thoughts": [], "filters": {"evidence_status": [], "feedback_state": [], "reasoning_primitive": []}}
    return payload | {"thought": None, "source_snippets": [], "threads": [], "active_thread": None}


def _batch_runtime_guard(root: Path, summary: Dict) -> Dict | None:
    pipeline_state = summary.get("runtime_pipeline", {})
    last_run = pipeline_state.get("last_run") or {}
    run_status = last_run.get("run_status")
    if pipeline_state.get("lock_contended") or run_status == "running":
        runtime_guard = _thought_runtime_guard(root)
        if runtime_guard is not None:
            return runtime_guard
        return {
            "status": "rebuilding",
            "pipeline_summary": get_runtime_pipeline_status(root).get("summary"),
            "runtime_counts": {
                "context_bubbles": _count_jsonl_rows(_data_dir(root) / "context_bubbles.jsonl"),
                "knowledge_nodes": _count_jsonl_rows(_data_dir(root) / "knowledge_nodes.jsonl"),
                "knowledge_edges": _count_jsonl_rows(_data_dir(root) / "knowledge_edges.jsonl"),
            },
            "context_bubbles_progress": read_json(_context_bubbles_progress_path(root), default={}) or {},
        }
    return None


def _load_feedback_events(root: Path) -> List[Dict]:
    return read_jsonl(_data_dir(root) / "feedback_events.jsonl")


def _load_feed_learning_events(root: Path) -> List[Dict]:
    return read_jsonl(_feed_learning_events_path(root))


def _thought_by_insight_lookup(root: Path) -> Dict[str, Dict]:
    return {row["insight_id"]: row for row in load_thought_packets(root)}


def _feed_learning_weight(event: Dict) -> float:
    event_type = event.get("event_type", "")
    if event_type == "detail_open":
        return 1.0
    if event_type == "thought_chat":
        return 1.6
    if event_type == "thread_saved":
        return 2.2
    if event_type == "explicit_feedback":
        return {
            "accepted": 3.0,
            "relevant": 2.0,
            "saved": 3.0,
            "revisit_later": 1.0,
            "dismiss": -2.0,
        }.get(event.get("feedback_state", ""), 0.0)
    return 0.0


def _rebuild_feed_taste_profile(root: Path) -> Dict:
    events = _load_feed_learning_events(root)
    signal_counts = Counter(row.get("event_type", "") for row in events if row.get("event_type"))
    format_scores: Dict[str, float] = {}
    format_counts = Counter()

    for event in events:
        post_format = event.get("post_format", "")
        if not post_format:
            continue
        format_counts[post_format] += 1
        format_scores[post_format] = round(format_scores.get(post_format, 0.0) + _feed_learning_weight(event), 2)

    preferred_formats = [
        key
        for key, _score in sorted(
            format_scores.items(),
            key=lambda item: (-item[1], -format_counts[item[0]], item[0]),
        )
        if _score > 0
    ]

    profile = {
        "updated_at": utc_now(),
        "event_count": len(events),
        "signal_counts": dict(signal_counts),
        "format_counts": dict(format_counts),
        "format_scores": format_scores,
        "preferred_formats": preferred_formats,
    }
    write_json(_feed_taste_profile_path(root), profile)
    return profile


def _load_feed_taste_profile(root: Path) -> Dict:
    profile = read_json(_feed_taste_profile_path(root), default=None)
    if profile is not None:
        return profile
    return _rebuild_feed_taste_profile(root)


def _record_feed_learning_event(
    root: Path,
    *,
    thought: Dict | None,
    event_type: str,
    feedback_state: str = "",
    thread_id: str = "",
) -> Dict:
    event = {
        "event_id": make_id("feed-learning"),
        "created_at": utc_now(),
        "event_type": event_type,
        "thread_id": thread_id,
        "feedback_state": feedback_state,
    }
    if thought is not None:
        feed_post = _build_feed_post(root, thought)
        event |= {
            "thought_id": thought["thought_id"],
            "insight_id": thought["insight_id"],
            "post_format": feed_post["post_format"],
            "format_reason": feed_post["format_reason"],
            "primary_bubble_id": thought.get("primary_bubble_id", ""),
            "source_ref": _primary_source_ref(thought),
        }
    rows = _load_feed_learning_events(root)
    rows.append(event)
    write_jsonl(_feed_learning_events_path(root), rows)
    profile = _rebuild_feed_taste_profile(root)
    return {"event": event, "taste_profile": profile}


def _load_thread(root: Path, thread_id: str) -> Dict:
    path = _threads_dir(root) / f"{thread_id}.json"
    payload = read_json(path)
    if payload is None:
        raise FileNotFoundError(thread_id)
    return payload


def _write_thread(root: Path, thread: Dict) -> Path:
    path = _threads_dir(root) / f"{thread['thread_id']}.json"
    write_json(path, thread)
    return path


def _session_manifest_path(root: Path, session_id: str) -> Path:
    return session_dir(root, session_id) / "manifest.json"


def _load_session_manifest(root: Path, session_id: str) -> Dict[str, Any] | None:
    payload = read_json(_session_manifest_path(root, session_id), default=None)
    return payload if isinstance(payload, dict) else None


def _write_session_manifest(root: Path, manifest: SessionManifest) -> None:
    ensure_dir(session_dir(root, manifest.session_id))
    ensure_dir(session_events_path(root, manifest.session_id).parent)
    session_events_path(root, manifest.session_id).touch(exist_ok=True)
    update_manifest(root, manifest)


def _append_session_event(
    root: Path,
    *,
    session_id: str,
    actor: str,
    kind: str,
    content: str,
    tags: List[str] | None = None,
) -> Dict[str, Any]:
    event = ConversationEvent(
        event_id=make_id("event"),
        session_id=session_id,
        timestamp=utc_now(),
        actor=actor,
        kind=kind,
        content=content,
        attachments=[],
        tags=list(tags or []),
        source_ref=None,
    )
    append_jsonl(session_events_path(root, session_id), event.to_dict())
    return event.to_dict()


def _mobile_session_manifests(root: Path) -> List[Dict[str, Any]]:
    sessions_root = root / "memory" / "sessions"
    if not sessions_root.exists():
        return []
    manifests: List[Dict[str, Any]] = []
    for path in sorted(sessions_root.glob("*/manifest.json")):
        payload = read_json(path, default={}) or {}
        if payload.get("source_type") == "mobile_surface":
            manifests.append(payload)
    return manifests


def _mobile_reply_context(session_manifest: Dict[str, Any], events: List[Dict[str, Any]]) -> Dict[str, Any]:
    source_snippets = [
        {
            "title": "Mobile capture",
            "source_ref": f"mobile://{session_manifest['session_id']}/{event['event_id']}",
            "excerpt": shorten(event.get("content", ""), 220),
        }
        for event in events
        if event.get("actor") == "user"
    ][-4:]
    return {
        "character": "Grounded Inner World companion",
        "system_prompt": (
            "Stay concise and grounded in the user's own session captures and recent messages. "
            "Do not invent outside evidence. End with one concrete next move."
        ),
        "source_snippets": source_snippets,
        "session_title": session_manifest.get("title", ""),
    }


def _generate_mobile_session_reply(context: Dict[str, Any], user_message: str, events: List[Dict[str, Any]]) -> str:
    captures = [event.get("content", "").strip() for event in events if event.get("kind") == "capture" and event.get("content", "").strip()]
    latest_capture = captures[-1] if captures else user_message
    return " ".join(
        [
            f"What feels most live is {shorten(latest_capture, 180).rstrip('.')}.",
            f"Your next question is really about {shorten(user_message, 140).rstrip('.')}.",
            "Next move: name the concrete pressure or contradiction in one sentence.",
        ]
    )


def _request_mobile_session_reply(
    root: Path,
    *,
    session_manifest: Dict[str, Any],
    user_message: str,
    events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    context = _mobile_reply_context(session_manifest, events)
    thread = {
        "thread_id": session_manifest["session_id"],
        "messages": [
            {"role": event["actor"], "content": event["content"]}
            for event in events
            if event.get("actor") in {"user", "assistant"} and event.get("content")
        ],
    }
    backend = resolve_chat_backend(root)
    if backend["id"] == "heuristic":
        return {
            "content": _generate_mobile_session_reply(context, user_message, events),
            "backend_id": "heuristic",
        }
    return request_openclaw_reply(root, context, user_message, thread, backend)


def _list_threads(root: Path, thought_id: str | None = None, include_deleted: bool = False) -> List[Dict]:
    directory = _threads_dir(root)
    if not directory.exists():
        return []
    threads = []
    for path in sorted(directory.glob("*.json")):
        payload = read_json(path, default={})
        if thought_id and payload.get("thought_id") != thought_id:
            continue
        if not include_deleted and payload.get("status") == "deleted":
            continue
        threads.append(payload)
    return sorted(threads, key=lambda item: (item.get("updated_at", ""), item.get("thread_id", "")), reverse=True)


def get_thread_detail(root: Path, thread_id: str) -> Dict:
    return _load_thread(root, thread_id)


def _feedback_bonus(feedback_state: str, policy_snapshot: Dict) -> float:
    base = {
        "accepted": 0.3,
        "relevant": 0.22,
        "saved": 0.16,
        "revisit_later": 0.08,
        "dismiss": -0.18,
    }.get(feedback_state, 0.0)
    base += policy_snapshot.get("relevance_bias", 0.0) * (1 if feedback_state == "relevant" else 0)
    base -= policy_snapshot.get("dismiss_bias", 0.0) * (1 if feedback_state == "dismiss" else 0)
    return base


def _ensure_runtime(
    root: Path,
    domain_overlays: List[str] | None = None,
    *,
    resume: bool = False,
    from_stage: str | None = None,
    only_stage: str | None = None,
    force: bool = False,
    profile: bool = False,
) -> Dict:
    return _ensure_runtime_graph(
        root,
        domain_overlays,
        resume=resume,
        from_stage=from_stage,
        only_stage=only_stage,
        force=force,
        profile=profile,
    )


def _materialize_connections(root: Path) -> Dict:
    return _materialize_connections_admin(root)


def get_runtime_pipeline(root: Path) -> Dict:
    return get_runtime_pipeline_status(root)


def update_runtime_pipeline_component(
    root: Path,
    component_id: str,
    *,
    enabled: bool | None = None,
    order: int | None = None,
    weight: float | None = None,
) -> Dict:
    return update_runtime_pipeline_component_config(
        root,
        component_id,
        enabled=enabled,
        order=order,
        weight=weight,
    )


def seed_sources(root: Path, source_path: Path, source_type: str = "manual_import") -> Dict:
    return ingest_source_file(root, source_path, source_type)


def scan_library(root: Path) -> Dict:
    return scan_library_tracker_sources(root)


def sync_library(
    root: Path,
    domain_overlays: List[str] | None = None,
    *,
    max_items: int | None = None,
    portion: float | None = None,
) -> Dict:
    del domain_overlays
    result = sync_library_tracker_sources(root, max_items=max_items, portion=portion)
    result["rebuild_required"] = bool(result["ingested_item_count"] or result["purged_item_count"])
    result["runtime"] = None
    return result


def get_library_status(root: Path) -> Dict:
    return get_library_tracker_status(root)


def get_dimension_model_role_status(root: Path) -> Dict:
    return get_dimension_model_role_status_admin(root)


def get_pond_router_status(root: Path) -> Dict:
    return get_pond_router_status_admin(root)


def get_chunk_pond_detail(root: Path, chunk_id: str, domain_overlays: List[str] | None = None) -> Dict:
    return get_chunk_pond_detail_admin(root, chunk_id, domain_overlays)


def update_pond_router_config(
    root: Path,
    *,
    enabled: bool | None = None,
    mode: str | None = None,
    assisted_on_ambiguity: bool | None = None,
    allow_manual_override: bool | None = None,
    ambiguity_threshold: float | None = None,
    local_role_id: str | None = None,
    judge_role_id: str | None = None,
    router_version: str | None = None,
) -> Dict:
    return update_pond_router_config_admin(
        root,
        enabled=enabled,
        mode=mode,
        assisted_on_ambiguity=assisted_on_ambiguity,
        allow_manual_override=allow_manual_override,
        ambiguity_threshold=ambiguity_threshold,
        local_role_id=local_role_id,
        judge_role_id=judge_role_id,
        router_version=router_version,
    )


def apply_pond_router_preset(root: Path, preset: str) -> Dict:
    return apply_pond_router_preset_admin(root, preset)


def update_chunk_pond_detail(
    root: Path,
    chunk_id: str,
    *,
    primary_pond: str | None = None,
    pond_layers: List[str] | None = None,
    clear_override: bool = False,
    notes: str | None = None,
    domain_overlays: List[str] | None = None,
) -> Dict:
    return update_chunk_pond_detail_admin(
        root,
        chunk_id,
        primary_pond=primary_pond,
        pond_layers=pond_layers,
        clear_override=clear_override,
        notes=notes,
        domain_overlays=domain_overlays,
    )


def update_dimension_model_role_binding(
    root: Path,
    *,
    role_id: str,
    backend: str | None = None,
    model_id: str | None = None,
    enabled: bool | None = None,
    fallback_role_id: str | None = None,
    endpoint: str | None = None,
    attributes: Dict | None = None,
) -> Dict:
    return update_dimension_model_role_binding_admin(
        root,
        role_id=role_id,
        backend=backend,
        model_id=model_id,
        enabled=enabled,
        fallback_role_id=fallback_role_id,
        endpoint=endpoint,
        attributes=attributes,
    )


def load_pond_routing_feedback(root: Path) -> List[Dict]:
    return load_pond_routing_feedback_admin(root)


def record_pond_routing_feedback(
    root: Path,
    *,
    event_type: str,
    chunk_id: str = "",
    source_ref: str = "",
    previous_primary_pond: str = "",
    new_primary_pond: str = "",
    previous_pond_layers: List[str] | None = None,
    new_pond_layers: List[str] | None = None,
    actor: str = "operator",
    routing_method: str = "",
    note: str = "",
) -> Dict:
    return record_pond_routing_feedback_admin(
        root,
        event_type=event_type,
        chunk_id=chunk_id,
        source_ref=source_ref,
        previous_primary_pond=previous_primary_pond,
        new_primary_pond=new_primary_pond,
        previous_pond_layers=previous_pond_layers,
        new_pond_layers=new_pond_layers,
        actor=actor,
        routing_method=routing_method,
        note=note,
    )


def classify_assisted_dimension(
    root: Path,
    *,
    dimension_id: str,
    row: Dict,
    preferred_role: str,
    allowed_values: List[str] | None = None,
) -> Dict | None:
    return classify_assisted_dimension_admin(
        root,
        dimension_id=dimension_id,
        row=row,
        preferred_role=preferred_role,
        allowed_values=allowed_values,
    )


def classify_assisted_pond_route(
    root: Path,
    *,
    row: Dict,
    pond_matrix: Dict,
    preferred_role: str,
) -> Dict | None:
    return classify_assisted_pond_route_admin(
        root,
        row=row,
        pond_matrix=pond_matrix,
        preferred_role=preferred_role,
    )


def _library_chunk_preview(root: Path) -> Dict[str, List[Dict]]:
    grouped: Dict[str, List[Dict]] = {}
    for row in load_chunk_index(root):
        grouped.setdefault(row["source_ref"], []).append(row)
    for source_ref, rows in grouped.items():
        grouped[source_ref] = sorted(rows, key=lambda item: (item.get("chunk_index", 0), item["chunk_id"]))
    return grouped


def filter_library_sources(
    root: Path,
    *,
    query: str = "",
    statuses: List[str] | None = None,
    source_families: List[str] | None = None,
    semantic_roles: List[str] | None = None,
    source_ref: str | None = None,
    include_in_runtime: bool | None = None,
    include_in_bubbles: bool | None = None,
    include_in_concepts: bool | None = None,
    limit: int = 20,
) -> Dict:
    governance = load_library_governance(root)
    governed_rows = resolve_governed_source_rows(root, load_source_registry_raw(root), governance=governance)
    chunk_preview = _library_chunk_preview(root)
    query_tokens = set(tokenize(query))
    status_filter = set(statuses or [])
    family_filter = set(source_families or [])
    role_filter = set(semantic_roles or [])
    results = []
    for row in governed_rows:
        if source_ref and row.get("source_ref") != source_ref:
            continue
        if status_filter and row.get("governance_status") not in status_filter:
            continue
        if family_filter and row.get("source_family") not in family_filter:
            continue
        if role_filter and row.get("semantic_role") not in role_filter:
            continue
        if include_in_runtime is not None and bool(row.get("include_in_runtime")) != include_in_runtime:
            continue
        if include_in_bubbles is not None and bool(row.get("include_in_bubbles")) != include_in_bubbles:
            continue
        if include_in_concepts is not None and bool(row.get("include_in_concepts")) != include_in_concepts:
            continue
        source_chunks = chunk_preview.get(row["source_ref"], [])
        preview_text = " ".join(chunk.get("content", "")[:240] for chunk in source_chunks[:3])
        haystack = " ".join(
            [
                row.get("title", ""),
                row.get("source_ref", ""),
                row.get("source_type", ""),
                row.get("source_family", ""),
                row.get("semantic_role", ""),
                row.get("governance_status", ""),
                row.get("governance_notes", ""),
                " ".join(row.get("collection_tags", [])),
                json.dumps(row.get("metadata", {}), ensure_ascii=False),
                preview_text,
            ]
        )
        score = _filter_text_score(haystack, query_tokens)
        if query and score <= 0:
            continue
        results.append(
            {
                "source_ref": row["source_ref"],
                "title": row.get("title", ""),
                "source_type": row.get("source_type", ""),
                "source_family": row.get("source_family", ""),
                "semantic_role": row.get("semantic_role", ""),
                "governance_status": row.get("governance_status", "active"),
                "normalization_profile": row.get("normalization_profile", "default"),
                "include_in_runtime": bool(row.get("include_in_runtime", True)),
                "include_in_bubbles": bool(row.get("include_in_bubbles", True)),
                "include_in_concepts": bool(row.get("include_in_concepts", True)),
                "include_in_long_form": bool(row.get("include_in_long_form", True)),
                "collection_tags": row.get("collection_tags", []),
                "governance_notes": row.get("governance_notes", ""),
                "chunk_count": row.get("chunk_count", len(source_chunks)),
                "policy_origin": row.get("governance_origin", "default"),
                "match_score": score or 0.0,
                "preview_excerpt": shorten(preview_text, 220) if preview_text else "",
            }
        )
    results.sort(
        key=lambda item: (
            -float(item.get("match_score", 0.0)),
            item.get("governance_status", ""),
            item.get("source_family", ""),
            item.get("title", ""),
        )
    )
    return {
        "count": len(results),
        "results": results[:limit],
        "filters": {
            "query": query,
            "statuses": sorted(status_filter),
            "source_families": sorted(family_filter),
            "semantic_roles": sorted(role_filter),
            "source_ref": source_ref or "",
            "include_in_runtime": include_in_runtime,
            "include_in_bubbles": include_in_bubbles,
            "include_in_concepts": include_in_concepts,
            "limit": limit,
        },
    }


def search_library_dimensions(
    root: Path,
    *,
    query: str = "",
    dimensions: List[str] | None = None,
    dimension_filters: Dict[str, List[str]] | None = None,
    dimension_weights: Dict[str, float] | None = None,
    primary_pond: str | None = None,
    include_cross_pond: bool = False,
    statuses: List[str] | None = None,
    source_ref: str | None = None,
    include_in_runtime: bool | None = None,
    limit: int = 20,
) -> Dict:
    registry = load_dimension_registry(root)
    registry_map = registry.get("dimension_map", {})
    selected_dimensions = [
        dimension_id
        for dimension_id in (
            dimensions
            or list((dimension_weights or {}).keys())
            or [
                row["dimension_id"]
                for row in registry.get("dimensions", [])
                if row.get("enabled", True)
            ]
        )
        if dimension_id in registry_map
    ]
    selected_set = set(selected_dimensions)
    normalized_dimension_filters = {
        key: [str(item).strip() for item in values if str(item).strip()]
        for key, values in (dimension_filters or {}).items()
        if key in registry_map
    }
    requested_pond = str(primary_pond or "").strip()
    if not requested_pond:
        pond_filter_values = normalized_dimension_filters.get("primary_pond", [])
        if len(pond_filter_values) == 1:
            requested_pond = pond_filter_values[0]
    weight_overrides = {
        key: float(value)
        for key, value in (dimension_weights or {}).items()
        if key in registry_map
    }
    query_tokens = set(tokenize(query))
    status_filter = set(statuses or [])
    governance = load_library_governance(root)
    profile_matches = match_chunk_dimension_profiles(
        root,
        query=query,
        dimensions=selected_dimensions,
        dimension_filters=normalized_dimension_filters or None,
        dimension_weights=weight_overrides or None,
    )
    profile_match_map = {
        row["chunk_id"]: row
        for row in profile_matches.get("matches", [])
    }
    if profile_match_map:
        raw_chunk_rows = load_chunk_index_raw(root)
        matched_raw_rows = [row for row in raw_chunk_rows if row.get("chunk_id") in profile_match_map]
        chunks = resolve_governed_chunk_rows(root, chunk_rows=matched_raw_rows, governance=governance)
    else:
        chunks = resolve_governed_chunk_rows(root, governance=governance)
    results: List[Dict] = []
    for row in chunks:
        if source_ref and row.get("source_ref") != source_ref:
            continue
        if status_filter and row.get("governance_status") not in status_filter:
            continue
        if include_in_runtime is not None and bool(row.get("include_in_runtime", True)) != include_in_runtime:
            continue
        profile_match = profile_match_map.get(row["chunk_id"])
        if selected_set and profile_match_map and not profile_match:
            continue

        text_score = _filter_text_score(
            " ".join(
                [
                    row.get("title", ""),
                    row.get("content", ""),
                    row.get("source_ref", ""),
                    " ".join(row.get("collection_tags", [])),
                ]
            ),
            query_tokens,
        )
        dimensional_score = float(profile_match.get("dimensional_score", 0.0)) if profile_match else 0.0
        matched_dimensions: List[Dict] = list(profile_match.get("matched_dimensions", [])) if profile_match else []
        score = text_score + dimensional_score
        if query and score <= 0:
            continue
        if not query and not normalized_dimension_filters and not matched_dimensions:
            continue
        results.append(
            {
                "chunk_id": row["chunk_id"],
                "source_ref": row.get("source_ref", ""),
                "title": row.get("title", ""),
                "chunk_index": row.get("chunk_index", 0),
                "content_kind": row.get("content_kind", ""),
                "governance_status": row.get("governance_status", "active"),
                "include_in_runtime": bool(row.get("include_in_runtime", True)),
                "semantic_role": row.get("semantic_role", ""),
                "normalization_profile": row.get("normalization_profile", "default"),
                "primary_pond": row.get("primary_pond", ""),
                "secondary_ponds": row.get("secondary_ponds", []),
                "pond_layers": row.get("pond_layers", []),
                "pond_confidence": float(row.get("pond_confidence", 0.0) or 0.0),
                "collection_tags": row.get("collection_tags", []),
                "matched_dimensions": matched_dimensions,
                "text_score": text_score,
                "dimensional_score": dimensional_score,
                "score": score,
                "preview_excerpt": shorten(row.get("content", ""), 220),
            }
        )
    resolved_pond = requested_pond
    if not resolved_pond and not include_cross_pond and results:
        pond_scores: Dict[str, float] = {}
        for row in results:
            pond_id = str(row.get("primary_pond", "")).strip()
            if not pond_id:
                continue
            pond_scores[pond_id] = pond_scores.get(pond_id, 0.0) + float(row.get("score", 0.0))
        ranked_ponds = sorted(pond_scores.items(), key=lambda item: (-item[1], item[0]))
        if ranked_ponds:
            top_pond, top_score = ranked_ponds[0]
            next_score = ranked_ponds[1][1] if len(ranked_ponds) > 1 else 0.0
            if top_score > 0 and (next_score <= 0 or top_score >= next_score * 1.15):
                resolved_pond = top_pond
    if resolved_pond:
        pond_bounded: List[Dict] = []
        for row in results:
            row_pond = str(row.get("primary_pond", "")).strip()
            cross_pond = bool(row_pond and row_pond != resolved_pond)
            row["cross_pond"] = cross_pond
            if include_cross_pond:
                if cross_pond:
                    row["score"] = round(float(row.get("score", 0.0)) * 0.65, 4)
                pond_bounded.append(row)
            elif not row_pond or row_pond == resolved_pond:
                pond_bounded.append(row)
        results = pond_bounded
    else:
        for row in results:
            row["cross_pond"] = False
    results.sort(
        key=lambda row: (
            -float(row.get("score", 0.0)),
            -float(row.get("dimensional_score", 0.0)),
            row.get("source_ref", ""),
            int(row.get("chunk_index", 0)),
        )
    )
    return {
        "count": len(results),
        "results": results[:limit],
        "filters": {
            "query": query,
            "dimensions": selected_dimensions,
            "dimension_filters": normalized_dimension_filters,
            "dimension_weights": {
                dimension_id: weight_overrides.get(
                    dimension_id,
                    float(registry_map.get(dimension_id, {}).get("search_weight_default", 1.0)),
                )
                for dimension_id in selected_dimensions
            },
            "requested_primary_pond": requested_pond,
            "resolved_primary_pond": resolved_pond,
            "include_cross_pond": include_cross_pond,
            "statuses": sorted(status_filter),
            "source_ref": source_ref or "",
            "include_in_runtime": include_in_runtime,
            "limit": limit,
        },
    }


def govern_library_source(
    root: Path,
    *,
    source_ref: str,
    governance_status: str | None = None,
    semantic_role: str | None = None,
    normalization_profile: str | None = None,
    include_in_runtime: bool | None = None,
    include_in_bubbles: bool | None = None,
    include_in_concepts: bool | None = None,
    include_in_long_form: bool | None = None,
    collection_tags: List[str] | None = None,
    notes: str | None = None,
) -> Dict:
    result = update_source_governance(
        root,
        source_ref,
        governance_status=governance_status,
        semantic_role=semantic_role,
        normalization_profile=normalization_profile,
        include_in_runtime=include_in_runtime,
        include_in_bubbles=include_in_bubbles,
        include_in_concepts=include_in_concepts,
        include_in_long_form=include_in_long_form,
        collection_tags=collection_tags,
        notes=notes,
    )
    resolved = filter_library_sources(root, source_ref=source_ref, limit=1)
    return result | {"resolved_source": resolved["results"][0] if resolved["results"] else None}


def govern_library_family(
    root: Path,
    *,
    source_family: str,
    governance_status: str | None = None,
    semantic_role: str | None = None,
    normalization_profile: str | None = None,
    include_in_runtime: bool | None = None,
    include_in_bubbles: bool | None = None,
    include_in_concepts: bool | None = None,
    include_in_long_form: bool | None = None,
    collection_tags: List[str] | None = None,
    notes: str | None = None,
) -> Dict:
    result = update_family_governance(
        root,
        source_family,
        governance_status=governance_status,
        semantic_role=semantic_role,
        normalization_profile=normalization_profile,
        include_in_runtime=include_in_runtime,
        include_in_bubbles=include_in_bubbles,
        include_in_concepts=include_in_concepts,
        include_in_long_form=include_in_long_form,
        collection_tags=collection_tags,
        notes=notes,
    )
    filtered = filter_library_sources(root, source_families=[source_family], limit=5)
    return result | {"sample_sources": filtered["results"]}


def rederive_library(
    root: Path,
    *,
    affected_only: bool = True,
    dry_run: bool = False,
    profile: bool = False,
) -> Dict:
    governance = load_library_governance(root)
    pending = governance.get("pending_rederive") or {}
    if affected_only and not pending:
        return {
            "status": "no_pending_changes",
            "pending_rederive": None,
        }
    if affected_only:
        plan = dict(pending)
    else:
        configured = [
            row["component_id"]
            for row in load_runtime_pipeline_config(root).get("components", [])
            if row.get("enabled", True)
        ]
        plan = {
            "affected_stages": configured,
            "from_stage": configured[0] if configured else None,
            "post_actions": [],
            "reasons": ["Explicit full library rederive requested."],
            "targets": [],
        }
    configured_set = {
        row["component_id"]
        for row in load_runtime_pipeline_config(root).get("components", [])
        if row.get("enabled", True)
    }
    ordered_stages = [
        stage
        for stage in plan.get("affected_stages", [])
        if stage in configured_set
    ]
    plan["affected_stages"] = ordered_stages
    plan["from_stage"] = ordered_stages[0] if ordered_stages else plan.get("from_stage")
    if dry_run or not plan.get("affected_stages"):
        return {
            "status": "planned",
            "rederive_plan": plan,
        }
    runtime = derive_graph(
        root,
        [],
        from_stage=plan.get("from_stage"),
        force=True,
        profile=profile,
    )
    clear_pending_governance_rederive(root, applied_plan=plan)
    return {
        "status": "completed",
        "rederive_plan": plan,
        "runtime": runtime,
    }


def get_cost_report(root: Path) -> Dict:
    return get_cost_summary(root)


def get_cost_events(root: Path, limit: int = 50) -> Dict:
    events = list_cost_events(root, limit=limit)
    return {
        "count": len(events),
        "events": events,
    }


def derive_graph(
    root: Path,
    domain_overlays: List[str] | None = None,
    *,
    resume: bool = False,
    from_stage: str | None = None,
    only_stage: str | None = None,
    force: bool = False,
    profile: bool = False,
) -> Dict:
    return derive_graph_admin(
        root,
        domain_overlays,
        resume=resume,
        from_stage=from_stage,
        only_stage=only_stage,
        force=force,
        profile=profile,
    )


def get_runtime_status(root: Path) -> Dict:
    overview = get_runtime_overview(root)
    pipeline = overview["runtime_pipeline"]
    return {
        "generated_at": overview["generated_at"],
        "counts": overview["counts"],
        "pipeline_summary": pipeline.get("summary"),
        "last_run": pipeline.get("last_run"),
        "context_bubbles_progress": overview.get("context_bubbles_progress", {}),
    }


def _status_priority(status: str) -> int:
    return {
        "active": 5,
        "approved": 4,
        "provisional": 3,
        "needs_review": 2,
        "review": 2,
        "archived": 1,
        "dismissed": 0,
    }.get(status, 1)


def _top_concepts_for_overview(root: Path, limit: int = 6) -> List[Dict]:
    nodes = sorted(
        load_concept_nodes(root),
        key=lambda row: (
            -_status_priority(row.get("status", "provisional")),
            -float(row.get("confidence", 0.0)),
            -len(row.get("source_refs", [])),
            row.get("label", ""),
        ),
    )
    return [
        {
            "concept_id": row["concept_id"],
            "label": row["label"],
            "status": row.get("status", "provisional"),
            "confidence": row.get("confidence", 0.0),
            "source_ref_count": len(row.get("source_refs", [])),
            "alias_count": len(row.get("aliases", [])),
            "abstract_pattern": row.get("abstract_pattern", ""),
            "transfer_shape": row.get("transfer_shape", ""),
        }
        for row in nodes[:limit]
    ]


def _top_bubbles_for_overview(root: Path, limit: int = 6) -> List[Dict]:
    bubbles = sorted(
        load_context_bubbles(root),
        key=lambda row: (
            -_status_priority(row.get("status", "active")),
            -float(row.get("confidence", 0.0)),
            -int(row.get("support_count", 0)),
            row.get("label", ""),
        ),
    )
    return [
        {
            "bubble_id": row["bubble_id"],
            "label": row["label"],
            "status": row.get("status", "active"),
            "confidence": row.get("confidence", 0.0),
            "support_count": row.get("support_count", 0),
            "dominant_primitives": row.get("dominant_primitives", [])[:4],
            "active_tension_count": len(row.get("active_tensions", [])),
            "open_question_count": len(row.get("open_questions", [])),
            "concept_count": len(row.get("concept_ids", [])),
            "source_ref_count": len(row.get("source_refs", [])),
        }
        for row in bubbles[:limit]
    ]


def _connections_payload(root: Path) -> Dict:
    return read_json(
        _data_dir(root) / "connections.json",
        default={
            "generated_at": None,
            "total_connection_count": 0,
            "included_connection_count": 0,
            "max_connections": 0,
            "truncated": False,
            "connections": [],
        },
    )


def _top_connections_for_overview(root: Path, limit: int = 6) -> List[Dict]:
    payload = _connections_payload(root)
    return [
        {
            "connection_id": row["connection_id"],
            "kind": row.get("kind", "relates_to"),
            "left_source_ref": row["left_source_ref"],
            "right_source_ref": row["right_source_ref"],
            "strength": row.get("strength", 0.0),
            "shared_concepts": row.get("shared_concepts", [])[:4],
        }
        for row in payload.get("connections", [])[:limit]
    ]


def _top_context_links_for_overview(root: Path, limit: int = 6) -> List[Dict]:
    links = sorted(
        load_context_links(root),
        key=lambda row: (
            row.get("status") != "stable",
            row.get("layer", ""),
            -float(row.get("confidence", 0.0)),
            row.get("kind", ""),
            row.get("link_id", ""),
        ),
    )
    return [
        {
            "link_id": row["link_id"],
            "layer": row.get("layer", ""),
            "kind": row.get("kind", ""),
            "status": row.get("status", "provisional"),
            "confidence": row.get("confidence", 0.0),
            "from_ref": f"{row.get('from_ref_type', '')}:{row.get('from_ref_id', '')}",
            "to_ref": f"{row.get('to_ref_type', '')}:{row.get('to_ref_id', '')}",
            "evidence_ref_count": len(row.get("evidence_refs", [])),
        }
        for row in links[:limit]
    ]


def _top_semantic_capsules_for_overview(root: Path, limit: int = 6) -> List[Dict]:
    capsules = sorted(
        load_semantic_capsules(root),
        key=lambda row: (
            -_status_priority(row.get("status", "provisional")),
            -float(row.get("confidence", 0.0)),
            row.get("capsule_type", ""),
            row.get("label", ""),
        ),
    )
    return [
        {
            "capsule_id": row["capsule_id"],
            "capsule_type": row.get("capsule_type", ""),
            "label": row.get("label", ""),
            "status": row.get("status", "provisional"),
            "confidence": row.get("confidence", 0.0),
            "source_ref_count": len(row.get("source_refs", [])),
            "linked_ref_count": len(row.get("linked_ref_ids", [])),
        }
        for row in capsules[:limit]
    ]


def get_retrieval_bundle(
    root: Path,
    *,
    query: str,
    limit: int = 10,
    neighbor_limit: int = 6,
    include_cross_pond: bool = False,
    domain_overlays: List[str] | None = None,
) -> Dict:
    _ensure_runtime(root, domain_overlays)
    return build_retrieval_bundle(
        root,
        query,
        limit=limit,
        neighbor_limit=neighbor_limit,
        include_cross_pond=include_cross_pond,
    )


def get_linking_overview(
    root: Path,
    *,
    query: str = "",
    limit: int = 12,
    neighbor_limit: int = 6,
    domain_overlays: List[str] | None = None,
) -> Dict:
    _ensure_runtime(root, domain_overlays)
    links = load_context_links(root)
    capsules = load_semantic_capsules(root)
    bundle = get_retrieval_bundle(
        root,
        query=query,
        limit=limit,
        neighbor_limit=neighbor_limit,
        domain_overlays=domain_overlays,
    )
    return {
        "generated_at": utc_now(),
        "query": query,
        "counts": {
            "context_links": len(links),
            "semantic_capsules": len(capsules),
            "bundle_capsules": bundle.get("count", 0),
            "bundle_links": len(bundle.get("included_links", [])),
        },
        "governance": get_link_governance_state(root),
        "top_context_links": _top_context_links_for_overview(root, limit=min(limit, 12)),
        "top_semantic_capsules": _top_semantic_capsules_for_overview(root, limit=min(limit, 12)),
        "retrieval_bundle": bundle,
        "ocean_map": _ocean_map_from_bundle(bundle, query=query),
    }


def get_link_governance_state(root: Path) -> Dict:
    governance = load_link_governance(root)
    link_rows = load_context_links(root)
    status_counts: Dict[str, int] = {}
    for row in governance.get("link_policies", []):
        status = row.get("governance_status", "active")
        status_counts[status] = status_counts.get(status, 0) + 1
    alias_rows = [
        row for row in governance.get("alias_resolutions", [])
        if row.get("status", "active") not in {"rejected", "archived"}
    ]
    recent_policies = sorted(
        governance.get("link_policies", []),
        key=lambda row: (row.get("updated_at") or "", row.get("link_id", "")),
        reverse=True,
    )[:12]
    recent_aliases = sorted(
        governance.get("alias_resolutions", []),
        key=lambda row: (row.get("updated_at") or "", row.get("alias_text", "")),
        reverse=True,
    )[:12]
    return {
        "updated_at": governance.get("updated_at"),
        "governance_path": governance.get("governance_path"),
        "counts": {
            "link_policy_count": len(governance.get("link_policies", [])),
            "active_alias_count": len(alias_rows),
            "total_alias_count": len(governance.get("alias_resolutions", [])),
            "governed_context_links": len([row for row in link_rows if row.get("governance")]),
        },
        "status_counts": status_counts,
        "recent_link_policies": recent_policies,
        "recent_alias_resolutions": recent_aliases,
    }


def _ocean_map_from_bundle(bundle: Dict, *, query: str) -> Dict:
    seeds = bundle.get("seed_capsules", [])
    related = bundle.get("related_capsules", [])
    included_links = bundle.get("included_links", [])
    nodes_by_ref: Dict[str, Dict] = {}

    def _register_capsule(row: Dict, *, role: str) -> None:
        ref_key = f"{row.get('ref_type', '')}:{row.get('ref_id', '')}"
        if not ref_key.strip(":"):
            return
        if ref_key in nodes_by_ref:
            if role == "seed":
                nodes_by_ref[ref_key]["role"] = "seed"
            return
        nodes_by_ref[ref_key] = {
            "node_id": row.get("capsule_id", ref_key),
            "ref_key": ref_key,
            "label": row.get("label", ""),
            "kind": row.get("capsule_type", ""),
            "status": row.get("status", "provisional"),
            "confidence": row.get("confidence", 0.0),
            "role": role,
            "source_ref_count": len(row.get("source_refs", [])),
            "linked_ref_count": len(row.get("linked_ref_ids", [])),
        }

    for row in seeds:
        _register_capsule(row, role="seed")
    for row in related:
        _register_capsule(row, role="related")

    edges = []
    seen_edges = set()
    for row in included_links:
        from_key = f"{row.get('from_ref_type', '')}:{row.get('from_ref_id', '')}"
        to_key = f"{row.get('to_ref_type', '')}:{row.get('to_ref_id', '')}"
        if from_key not in nodes_by_ref or to_key not in nodes_by_ref:
            continue
        edge_id = row.get("link_id", f"{from_key}->{to_key}")
        if edge_id in seen_edges:
            continue
        seen_edges.add(edge_id)
        edges.append(
            {
                "edge_id": edge_id,
                "from_ref": from_key,
                "to_ref": to_key,
                "kind": row.get("kind", ""),
                "layer": row.get("layer", ""),
                "status": row.get("status", "provisional"),
                "confidence": row.get("confidence", 0.0),
            }
        )

    ordered_nodes = sorted(
        nodes_by_ref.values(),
        key=lambda item: (
            item.get("role") != "seed",
            -_status_priority(item.get("status", "provisional")),
            -float(item.get("confidence", 0.0)),
            item.get("kind", ""),
            item.get("label", ""),
        ),
    )

    return {
        "query": query,
        "mode": "focused" if query else "ambient",
        "node_count": len(ordered_nodes),
        "edge_count": len(edges),
        "seed_count": len(seeds),
        "source_ref_count": len(bundle.get("source_refs", [])),
        "alias_hits": bundle.get("alias_hits", []),
        "nodes": ordered_nodes,
        "edges": edges,
    }


def update_link_governance(
    root: Path,
    *,
    link_id: str,
    governance_status: str,
    confidence_override: float | None = None,
    confidence_delta: float | None = None,
    notes: str | None = None,
    domain_overlays: List[str] | None = None,
) -> Dict:
    _ensure_runtime(root, domain_overlays)
    result = govern_context_link(
        root,
        link_id,
        governance_status=governance_status,
        confidence_override=confidence_override,
        confidence_delta=confidence_delta,
        notes=notes,
    )
    return result | {"governance": get_link_governance_state(root)}


def create_link_alias_resolution(
    root: Path,
    *,
    alias_text: str,
    ref_type: str,
    ref_id: str,
    status: str = "active",
    notes: str | None = None,
    domain_overlays: List[str] | None = None,
) -> Dict:
    _ensure_runtime(root, domain_overlays)
    result = add_alias_resolution(
        root,
        alias_text,
        ref_type=ref_type,
        ref_id=ref_id,
        status=status,
        notes=notes,
    )
    return result | {"governance": get_link_governance_state(root)}


def _pipeline_frontend_snapshot(root: Path) -> Dict:
    status = get_runtime_pipeline_status(root)
    last_run = status.get("last_run") or {}
    stages = []
    for component in last_run.get("components", []):
        stages.append(
            {
                "component_id": component.get("component_id"),
                "label": component.get("label") or component.get("component_id", "").replace("_", " ").title(),
                "status": component.get("status", "unknown"),
                "duration_seconds": component.get("duration_seconds"),
            }
        )
    return {
        "summary": status.get("summary"),
        "stages": stages,
    }


PAIR_PRIORITY = [
    ("tension", "direction"),
    ("question", "shared_primitive"),
    ("signal_frame", "shared_primitive"),
    ("contradiction", "why_it_matters"),
]


def _bubble_context_payload(primary: Dict, related_bubble_ids: List[str] | None = None) -> Dict:
    return {
        "bubble_id": primary["bubble_id"],
        "label": primary["label"],
        "thesis": primary["thesis"],
        "dominant_primitives": primary.get("dominant_primitives", []),
        "active_tensions": primary.get("active_tensions", []),
        "open_questions": primary.get("open_questions", []),
        "related_bubble_ids": related_bubble_ids or [],
    }


def _bubble_membership_maps(root: Path) -> tuple[Dict[str, List[str]], Dict[str, Dict]]:
    meta_to_bubbles: Dict[str, List[str]] = {}
    for membership in load_bubble_memberships(root):
        meta_to_bubbles.setdefault(membership["meta_id"], []).append(membership["bubble_id"])
    bubbles = {row["bubble_id"]: row for row in load_context_bubbles(root)}
    return meta_to_bubbles, bubbles


def _bubble_candidate_pairs(root: Path, limit: int = 36) -> List[Dict]:
    meta_lookup = {row["meta_id"]: row for row in load_meta_records(root)}
    bubbles = {row["bubble_id"]: row for row in load_context_bubbles(root)}
    memberships_by_bubble: Dict[str, List[Dict]] = {}
    for membership in load_bubble_memberships(root):
        row = meta_lookup.get(membership["meta_id"])
        if row is None:
            continue
        memberships_by_bubble.setdefault(membership["bubble_id"], []).append(membership | {"meta": row})

    candidates: List[Dict] = []
    seen = set()
    for bubble in sorted(bubbles.values(), key=lambda item: (item["status"] != "active", -item["confidence"], item["label"])):
        memberships = memberships_by_bubble.get(bubble["bubble_id"], [])
        by_kind: Dict[str, List[Dict]] = {}
        for membership in memberships:
            by_kind.setdefault(membership["meta"]["kind"], []).append(membership)
        for priority_index, (left_kind, right_kind) in enumerate(PAIR_PRIORITY):
            left_rows = sorted(by_kind.get(left_kind, []), key=lambda item: (-item["meta"]["confidence"], item["meta"]["meta_id"]))[:3]
            right_rows = sorted(by_kind.get(right_kind, []), key=lambda item: (-item["meta"]["confidence"], item["meta"]["meta_id"]))[:3]
            for left in left_rows:
                for right in right_rows:
                    pair_key = tuple(sorted([left["meta"]["meta_id"], right["meta"]["meta_id"]]))
                    if left["meta"]["meta_id"] == right["meta"]["meta_id"] or pair_key in seen:
                        continue
                    seen.add(pair_key)
                    shared_tokens = sorted(
                        set(left["meta"].get("attributes", {}).get("tokens", []))
                        & set(right["meta"].get("attributes", {}).get("tokens", []))
                    )[:8]
                    score = min(
                        0.99,
                        round(
                            0.56
                            + bubble["confidence"] * 0.24
                            + ((left["meta"]["confidence"] + right["meta"]["confidence"]) / 2) * 0.16
                            + max(0.0, 0.08 - priority_index * 0.02),
                            3,
                        ),
                    )
                    candidates.append(
                        {
                            "left": left["meta"],
                            "right": right["meta"],
                            "edge_kind": "bubble_within",
                            "score": score,
                            "shared_tokens": shared_tokens,
                            "evidence_refs": sorted(set(left["meta"]["source_refs"] + right["meta"]["source_refs"])),
                            "bubble_context": _bubble_context_payload(bubble),
                        }
                    )

    memberships_by_id = {row["bubble_id"]: row for row in load_bubble_memberships(root) if row["role"] == "anchor"}
    bubble_edges = sorted(load_bubble_edges(root), key=lambda item: (-item["confidence"], item["kind"], item["edge_id"]))
    for edge in bubble_edges:
        if edge["kind"] not in {"bridge", "contradicts"}:
            continue
        left_anchor = memberships_by_id.get(edge["from_bubble_id"])
        right_anchor = memberships_by_id.get(edge["to_bubble_id"])
        left = meta_lookup.get(left_anchor["meta_id"]) if left_anchor else None
        right = meta_lookup.get(right_anchor["meta_id"]) if right_anchor else None
        if left is None or right is None:
            continue
        pair_key = tuple(sorted([left["meta_id"], right["meta_id"]]))
        if pair_key in seen:
            continue
        seen.add(pair_key)
        left_bubble = bubbles[edge["from_bubble_id"]]
        right_bubble = bubbles[edge["to_bubble_id"]]
        primary, related = (
            (left_bubble, [right_bubble["bubble_id"]])
            if left_bubble["confidence"] >= right_bubble["confidence"]
            else (right_bubble, [left_bubble["bubble_id"]])
        )
        candidates.append(
            {
                "left": left,
                "right": right,
                "edge_kind": edge["kind"],
                "score": round(min(0.99, 0.60 + edge["confidence"] * 0.32 + (0.08 if edge["kind"] == "contradicts" else 0.04)), 3),
                "shared_tokens": edge.get("shared_terms", [])[:8],
                "evidence_refs": edge.get("evidence_refs", []),
                "bubble_context": _bubble_context_payload(primary, related_bubble_ids=related),
            }
        )
    candidates.sort(key=lambda item: (-item["score"], item["edge_kind"], item["left"]["label"]))
    return candidates[:limit]


def _select_contextual_candidate_pairs(root: Path, limit: int = 36) -> List[Dict]:
    contextual = _bubble_candidate_pairs(root, limit=limit)
    meta_to_bubbles, bubbles = _bubble_membership_maps(root)
    seen = {
        tuple(sorted([row["left"]["meta_id"], row["right"]["meta_id"]]))
        for row in contextual
    }
    for row in select_candidate_pairs(root, limit=max(limit * 2, 24)):
        pair_key = tuple(sorted([row["left"]["meta_id"], row["right"]["meta_id"]]))
        if pair_key in seen:
            continue
        seen.add(pair_key)
        left_bubbles = meta_to_bubbles.get(row["left"]["meta_id"], [])
        right_bubbles = meta_to_bubbles.get(row["right"]["meta_id"], [])
        shared_bubbles = [bubble_id for bubble_id in left_bubbles if bubble_id in right_bubbles]
        if shared_bubbles:
            primary = bubbles[shared_bubbles[0]]
            row["bubble_context"] = _bubble_context_payload(primary)
        elif left_bubbles or right_bubbles:
            left_bubble = bubbles.get(left_bubbles[0]) if left_bubbles else None
            right_bubble = bubbles.get(right_bubbles[0]) if right_bubbles else None
            if left_bubble and right_bubble:
                primary, related = (
                    (left_bubble, [right_bubble["bubble_id"]])
                    if left_bubble["confidence"] >= right_bubble["confidence"]
                    else (right_bubble, [left_bubble["bubble_id"]])
                )
                row["bubble_context"] = _bubble_context_payload(primary, related_bubble_ids=related)
            elif left_bubble:
                row["bubble_context"] = _bubble_context_payload(left_bubble)
            elif right_bubble:
                row["bubble_context"] = _bubble_context_payload(right_bubble)
        contextual.append(row)
    contextual.sort(key=lambda item: (-item["score"], item["edge_kind"], item["left"]["label"]))
    return contextual[:limit]


def _candidate_packet(pair: Dict) -> Dict:
    left = pair["left"]
    right = pair["right"]
    source_item_ids = sorted(set(left.get("chunk_ids", []) + right.get("chunk_ids", [])))
    source_refs = sorted(set(left.get("source_refs", []) + right.get("source_refs", [])))
    evidence_texts = list(dict.fromkeys(left.get("evidence", []) + right.get("evidence", [])))
    return {
        "stimulus": {},
        "subconscious_processing": {},
        "emergent_structure": {},
        "conscious_articulation": {"evaluation_reports": {}},
        "memory_commit": {},
        "connection": {
            "left": left,
            "right": right,
            "edge_kind": pair["edge_kind"],
            "source_item_ids": source_item_ids,
            "source_refs": source_refs,
            "meta_refs": [left["meta_id"], right["meta_id"]],
            "evidence_texts": evidence_texts,
            "shared_terms": pair.get("shared_tokens", []),
            "bubble_context": pair.get("bubble_context"),
        },
    }


def _infer_shared_primitive(packet: Dict) -> Dict:
    primitive = packet["connection"]["shared_primitive"]
    shared_terms = packet["connection"].get("shared_terms", [])
    signal_tokens = set(
        tokenize(
            " ".join(
                [
                    primitive.get("label", ""),
                    packet["connection"]["left"].get("label", ""),
                    packet["connection"]["right"].get("label", ""),
                    packet["connection"].get("context_summary", ""),
                    packet["connection"].get("why_it_matters", ""),
                    " ".join(shared_terms),
                ]
            )
        )
    )
    if {"morning", "batch"} <= signal_tokens:
        return {"key": "morning_batch", "label": "Morning Batch"}
    if {"private", "cognitive", "layer"} <= signal_tokens:
        return {"key": "private_cognitive_layer", "label": "Private Cognitive Layer"}
    if "review" in signal_tokens and signal_tokens & {"commit", "persist", "approve", "gate"}:
        return {"key": "review_before_commit", "label": "Review Before Commit"}
    if signal_tokens & {"progressive", "disclosure"} or ({"small", "thought"} <= signal_tokens):
        return {"key": "progressive_disclosure", "label": "Progressive Disclosure"}
    if signal_tokens & {"ambiguity", "structure"}:
        return {"key": "ambiguity_then_structure", "label": "Ambiguity Then Structure"}
    if signal_tokens & {"fidelity", "signal"} or signal_tokens & {"generic", "flatten"}:
        return {"key": "cognitive_fidelity", "label": "Cognitive Fidelity"}
    default_key = "_".join(tokenize(primitive["label"])[:4]) or "connection"
    return {"key": default_key, "label": primitive["label"]}


def _promotion_row(packet: Dict, judgment: Dict) -> Dict:
    left = packet["connection"]["left"]
    right = packet["connection"]["right"]
    candidate = packet["conscious_articulation"]["concept_candidates"][0]
    primitive = _infer_shared_primitive(packet)
    shared_terms = packet["connection"].get("shared_terms", [])
    stable_key = "|".join(
        [
            primitive["key"],
            *sorted(packet["connection"]["meta_refs"]),
            *sorted(packet["connection"]["source_item_ids"]),
        ]
    )
    packet_id = f"promotion-{hashlib.sha256(stable_key.encode('utf-8')).hexdigest()[:12]}"
    insight_id = f"insight-{hashlib.sha256(packet_id.encode('utf-8')).hexdigest()[:12]}"
    unresolved_questions = []
    for row in [left, right]:
        if row["kind"] == "question":
            unresolved_questions.append(row["summary"])
    if not unresolved_questions:
        unresolved_questions.append("What part of this connection still needs explicit review?")
    what_changed = packet["connection"]["context_summary"]
    why_it_matters_now = packet["connection"]["why_it_matters"]
    bubble_context = packet["connection"].get("bubble_context") or {}
    if judgment["review_status"] == "approved_for_surface":
        next_action = "Stay with the expansion for a minute, check it against the source material, and see whether it quietly changes the direction."
    elif judgment["review_status"] == "ready_for_review":
        next_action = "Hold the two sides together a little longer before letting this settle into a surfaced thought."
    else:
        next_action = "Leave this out of the feed for now and wait until it either sharpens or fades."
    return {
        "packet_id": packet_id,
        "insight_id": insight_id,
        "left_label": left["label"],
        "right_label": right["label"],
        "shared_terms": shared_terms,
        "shared_primitive_key": primitive["key"],
        "shared_primitive_label": primitive["label"],
        "source_refs": packet["connection"]["source_refs"],
        "source_item_ids": packet["connection"]["source_item_ids"],
        "meta_refs": packet["connection"]["meta_refs"],
        "review_status": judgment["review_status"],
        "evidence_status": judgment["evidence_status"],
        "confidence_score": judgment["confidence_score"],
        "novelty_score": judgment["novelty_score"],
        "relevance_score": judgment["relevance_score"],
        "what_changed": what_changed,
        "why_it_matters_now": why_it_matters_now,
        "next_action": next_action,
        "reasoning_pipeline": "cross_pollination_v1+thought_surfacing_v1",
        "unresolved_questions": unresolved_questions[:4],
        "candidate_title": candidate["title"],
        "candidate_short_text": candidate["short_text"],
        "primary_bubble_id": bubble_context.get("bubble_id", ""),
        "primary_bubble_label": bubble_context.get("label", ""),
        "related_bubble_ids": bubble_context.get("related_bubble_ids", []),
    }


def _write_batch_exports(root: Path, surfaced: List[Dict]) -> None:
    payload = {"generated_at": utc_now(), "count": len(surfaced), "insights": surfaced}
    write_json(_data_dir(root) / "surfaced_insights.json", payload)
    write_json(_exports_dir(root) / "latest_batch.json", payload)
    md = ["# Morning Batch", "", f"- generated_at: {payload['generated_at']}", f"- count: {payload['count']}", ""]
    for item in surfaced:
        md.extend(
            [
                f"## {item['title']}",
                "",
                f"- what_changed: {item['what_changed']}",
                f"- source_refs: {', '.join(item['source_refs'])}",
                f"- reasoning_primitive: {item['reasoning_primitive']}",
                f"- surprise_score: {item['surprise_score']}",
                f"- confidence_score: {item['confidence_score']}",
                f"- evidence_status: {item['evidence_status']}",
                f"- why_it_matters_now: {item['why_it_matters_now']}",
                f"- next_action: {item['next_action']}",
                f"- feedback_state: {item['feedback_state']}",
                "",
            ]
        )
    write_markdown(_exports_dir(root) / "latest_batch.md", "\n".join(md))


def generate_daily_batch(
    root: Path,
    limit: int = 5,
    domain_overlays: List[str] | None = None,
    write_feed: bool = True,
) -> Dict:
    runtime_summary = _ensure_runtime(root, domain_overlays)
    runtime_guard = _batch_runtime_guard(root, runtime_summary)
    if runtime_guard is not None:
        return {
            "count": 0,
            "insights": [],
            "status": runtime_guard["status"],
            "pipeline_summary": runtime_guard.get("pipeline_summary"),
            "runtime_counts": runtime_guard.get("runtime_counts", {}),
            "context_bubbles_progress": runtime_guard.get("context_bubbles_progress", {}),
        }
    policy_snapshot = load_policy_snapshot(root)
    candidate_pairs = _select_contextual_candidate_pairs(root, limit=max(limit * 8, 24))
    promotion_rows = []
    review_rows = []
    for pair in candidate_pairs:
        packet = _candidate_packet(pair)
        packet = run_pipeline(root, "cross_pollination_v1", packet, {})
        packet = run_pipeline(root, "thought_surfacing_v1", {**packet, "run_meta": {}}, {})
        judgment = classify_run(packet)
        row = _promotion_row(packet, judgment)
        promotion_rows.append(row)
        if row["review_status"] != "approved_for_surface":
            review_rows.append(row)
    write_review_state(root, review_rows, promotion_rows)
    write_json(
        _data_dir(root) / "insight_candidates.json",
        [
            {
                "insight_id": row["insight_id"],
                "title": row["candidate_title"],
                "summary": row["what_changed"],
                "source_refs": row["source_refs"],
                "source_item_ids": row["source_item_ids"],
                "reasoning_primitive": row["shared_primitive_key"],
                "surprise_score": row["novelty_score"],
                "confidence_score": row["confidence_score"],
                "evidence_status": row["evidence_status"],
                "action_hint": row["next_action"],
                "feedback_state": "pending",
                "selection_score": row["confidence_score"] + row["relevance_score"] + row["novelty_score"],
                "primary_bubble_id": row.get("primary_bubble_id", ""),
                "primary_bubble_label": row.get("primary_bubble_label", ""),
                "related_bubble_ids": row.get("related_bubble_ids", []),
            }
            for row in promotion_rows
        ],
    )
    feedback_by_insight = {row["insight_id"]: row["feedback_state"] for row in _load_feedback_events(root) if row.get("insight_id")}
    thought_packets = build_thought_packets(root, promotion_rows, feedback_by_insight)
    surfaced = []
    for thought in sorted(
        thought_packets,
        key=lambda item: (
            item["evidence_status"] != "grounded",
            -(
                item["confidence_score"]
                + item["relevance_score"]
                + item["novelty_score"]
                + (0.06 if item.get("primary_bubble_id") else 0.0)
                + _feedback_bonus(item["feedback_state"], policy_snapshot)
            ),
            item["title"],
        ),
    )[:limit]:
        surfaced.append(
            {
                "insight_id": thought["insight_id"],
                "title": thought["title"],
                "what_changed": thought["what_changed"],
                "source_refs": thought["source_refs"],
                "source_item_ids": thought["source_item_ids"],
                "reasoning_primitive": thought["shared_primitive_key"] if "shared_primitive_key" in thought else thought["reasoning_pipeline"],
                "surprise_score": thought["novelty_score"],
                "confidence_score": thought["confidence_score"],
                "evidence_status": thought["evidence_status"],
                "why_it_matters_now": thought["why_it_matters_now"],
                "next_action": thought["next_action"],
                "feedback_state": thought["feedback_state"],
                "feedback_controls": thought.get("feedback_controls", ["relevant", "dismiss", "revisit_later"]),
                "primary_bubble_id": thought.get("primary_bubble_id", ""),
                "primary_bubble_label": thought.get("primary_bubble_label", ""),
                "related_bubble_ids": thought.get("related_bubble_ids", []),
            }
        )
    _write_batch_exports(root, surfaced)
    if write_feed:
        build_thought_feed(root, limit=max(limit, 8), domain_overlays=domain_overlays, regenerate_batch=False)
    return {"count": len(surfaced), "insights": surfaced}


def _feed_rows_with_threads(root: Path, thoughts: List[Dict], taste_profile: Dict | None = None) -> List[Dict]:
    rows = []
    for thought in thoughts:
        thread_summaries = [
            {
                "thread_id": thread["thread_id"],
                "status": thread["status"],
                "updated_at": thread["updated_at"],
                "message_count": len(thread.get("messages", [])),
                "backend_id": thread.get("backend_id", "heuristic"),
            }
            for thread in _list_threads(root, thought["thought_id"])
        ]
        feed_post = thought.get("_feed_post") or _build_feed_post(root, thought, taste_profile)
        rows.append(
            thought
            | {
                "reasoning_primitive": thought.get("shared_primitive_label", thought.get("reasoning_pipeline")),
                "thread_count": len(thread_summaries),
                "saved_thread_count": sum(1 for thread in thread_summaries if thread["status"] == "saved"),
            }
            | feed_post
        )
    return rows


def _classify_post_format(thought: Dict, post_context: Dict) -> tuple[str, str]:
    evidence_status = thought.get("evidence_status", "")
    source_snippets = post_context.get("source_snippets", [])
    unresolved_questions = post_context.get("unresolved_questions", [])
    tensions = post_context.get("tensions", [])
    contradictions = post_context.get("contradictions", [])
    article_sections = thought.get("article_sections", [])

    if source_snippets and evidence_status in {"grounded", "supported", "evidence_backed"}:
        return "source_backed_card", "grounded_evidence"
    if unresolved_questions:
        return "discussion_prompt", "open_question"
    if tensions or contradictions:
        return "discussion_prompt", "live_tension"
    if len(article_sections) >= 2:
        return "mini_essay", "article_structure"
    return "sharp_post", "default_sharp_post"


def _supporting_meta_rows(packet: Dict) -> List[Dict]:
    rows = []
    for meta in packet.get("linked_meta", []):
        rows.append(
            {
                "meta_id": meta.get("meta_id", ""),
                "kind": meta.get("kind", ""),
                "label": meta.get("label", ""),
                "summary": meta.get("summary", ""),
            }
        )
    return rows


def _build_post_context_from_lookups(thought: Dict, meta_lookup: Dict[str, Dict], chunk_lookup: Dict[str, Dict]) -> Dict:
    source_snippets = []
    for item_id in thought.get("source_item_ids", [])[:6]:
        row = chunk_lookup.get(item_id)
        if not row:
            continue
        source_snippets.append(
            {
                "source_item_id": item_id,
                "title": row["title"],
                "source_ref": row["source_ref"],
                "excerpt": shorten(row["content"], 220),
            }
        )
    linked_meta = [meta_lookup[meta_id] for meta_id in thought.get("meta_refs", []) if meta_id in meta_lookup]
    tensions = [row for row in linked_meta if row["kind"] == "tension"]
    contradictions = [row for row in linked_meta if row["kind"] == "contradiction"]
    questions = [row for row in linked_meta if row["kind"] == "question"]
    return {
        "thought_id": thought["thought_id"],
        "reach_mode": "strict",
        "context_summary": thought.get("why_it_matters_now", ""),
        "primary_bubble_id": thought.get("primary_bubble_id", ""),
        "primary_bubble_label": thought.get("primary_bubble_label", ""),
        "related_bubble_ids": thought.get("related_bubble_ids", [])[:1],
        "source_snippets": source_snippets[:4],
        "supporting_meta": _supporting_meta_rows({"linked_meta": linked_meta})[:3],
        "tensions": [row.get("summary", "") for row in tensions[:2] if row.get("summary")],
        "contradictions": [row.get("summary", "") for row in contradictions[:2] if row.get("summary")],
        "unresolved_questions": [row["summary"] for row in questions[:2] if row.get("summary")],
    }


def _build_post_context(
    root: Path,
    thought: Dict,
    *,
    meta_lookup: Dict[str, Dict] | None = None,
    chunk_lookup: Dict[str, Dict] | None = None,
) -> Dict:
    if meta_lookup is not None or chunk_lookup is not None:
        return _build_post_context_from_lookups(thought, meta_lookup or {}, chunk_lookup or {})
    packet = build_thread_packet(root, thought["thought_id"])
    supporting_meta = _supporting_meta_rows(packet)
    return {
        "thought_id": thought["thought_id"],
        "reach_mode": "strict",
        "context_summary": packet.get("context_summary", thought.get("why_it_matters_now", "")),
        "primary_bubble_id": thought.get("primary_bubble_id", ""),
        "primary_bubble_label": thought.get("primary_bubble_label", ""),
        "related_bubble_ids": thought.get("related_bubble_ids", [])[:1],
        "source_snippets": packet.get("source_snippets", [])[:4],
        "supporting_meta": supporting_meta[:3],
        "tensions": [row.get("summary", "") for row in packet.get("tensions", [])[:2] if row.get("summary")],
        "contradictions": [row.get("summary", "") for row in packet.get("contradictions", [])[:2] if row.get("summary")],
        "unresolved_questions": packet.get("unresolved_questions", [])[:2],
    }


def _taste_interaction_bias(taste_profile: Dict) -> str:
    signal_counts = taste_profile.get("signal_counts", {})
    detail_open = int(signal_counts.get("detail_open", 0))
    thought_chat = int(signal_counts.get("thought_chat", 0))
    thread_saved = int(signal_counts.get("thread_saved", 0))
    if thought_chat >= max(thread_saved, detail_open) and thought_chat > 0:
        return "thought_chat"
    if thread_saved > max(thought_chat, detail_open):
        return "save_thread"
    return "deep_read"


def _taste_compactness(taste_profile: Dict) -> str:
    signal_counts = taste_profile.get("signal_counts", {})
    detail_open = int(signal_counts.get("detail_open", 0))
    thought_chat = int(signal_counts.get("thought_chat", 0))
    thread_saved = int(signal_counts.get("thread_saved", 0))
    explicit_feedback = int(signal_counts.get("explicit_feedback", 0))
    if detail_open >= max(2, thought_chat + thread_saved + explicit_feedback):
        return "compact"
    if thought_chat + thread_saved > detail_open + explicit_feedback:
        return "depth"
    return "balanced"


def _derive_taste_shape(post_format: str, post_context: Dict, taste_profile: Dict) -> Dict:
    preferred_format = ""
    preferred_formats = taste_profile.get("preferred_formats", [])
    if preferred_formats:
        preferred_format = preferred_formats[0]
    if preferred_format == "source_backed_card" and post_context.get("source_snippets", []):
        lead_mode = "evidence"
    elif preferred_format == "discussion_prompt" and post_context.get("unresolved_questions", []):
        lead_mode = "question"
    elif preferred_format == "mini_essay":
        lead_mode = "synthesis"
    elif post_format == "source_backed_card" and post_context.get("source_snippets", []):
        lead_mode = "evidence"
    elif post_format == "discussion_prompt" and post_context.get("unresolved_questions", []):
        lead_mode = "question"
    elif post_format == "mini_essay":
        lead_mode = "synthesis"
    else:
        lead_mode = "summary"
    return {
        "preferred_format": preferred_format,
        "lead_mode": lead_mode,
        "interaction_bias": _taste_interaction_bias(taste_profile),
        "compactness": _taste_compactness(taste_profile),
    }


def _taste_diagnostics(post_format: str, post_context: Dict, taste_profile: Dict, taste_shape: Dict) -> Dict:
    preferred_format = taste_shape.get("preferred_format", "")
    source_snippets = post_context.get("source_snippets", [])
    unresolved_questions = post_context.get("unresolved_questions", [])
    signal_counts = taste_profile.get("signal_counts", {})
    detail_open = int(signal_counts.get("detail_open", 0))
    thought_chat = int(signal_counts.get("thought_chat", 0))
    thread_saved = int(signal_counts.get("thread_saved", 0))
    explicit_feedback = int(signal_counts.get("explicit_feedback", 0))

    if taste_shape["lead_mode"] == "evidence" and preferred_format == "source_backed_card" and source_snippets:
        lead_rule = "preferred_format_evidence"
    elif taste_shape["lead_mode"] == "question" and preferred_format == "discussion_prompt" and unresolved_questions:
        lead_rule = "preferred_format_question"
    elif taste_shape["lead_mode"] == "synthesis" and preferred_format == "mini_essay":
        lead_rule = "preferred_format_synthesis"
    elif taste_shape["lead_mode"] == "evidence":
        lead_rule = "post_format_evidence"
    elif taste_shape["lead_mode"] == "question":
        lead_rule = "post_format_question"
    elif taste_shape["lead_mode"] == "synthesis":
        lead_rule = "post_format_synthesis"
    else:
        lead_rule = "summary_fallback"

    if taste_shape["interaction_bias"] == "thought_chat":
        interaction_rule = "thought_chat_dominant"
    elif taste_shape["interaction_bias"] == "save_thread":
        interaction_rule = "thread_saved_dominant"
    else:
        interaction_rule = "detail_open_default"

    if taste_shape["compactness"] == "depth":
        compactness_rule = "depth_from_chat_and_save"
    elif taste_shape["compactness"] == "compact":
        compactness_rule = "compact_from_detail_open"
    else:
        compactness_rule = "balanced_from_mixed_signals"

    return {
        "preferred_format": preferred_format,
        "post_format": post_format,
        "format_preference_match": bool(preferred_format) and preferred_format == post_format,
        "lead_rule": lead_rule,
        "interaction_rule": interaction_rule,
        "compactness_rule": compactness_rule,
        "signal_counts": {
            "detail_open": detail_open,
            "thought_chat": thought_chat,
            "thread_saved": thread_saved,
            "explicit_feedback": explicit_feedback,
        },
    }


def _taste_lead_text(thought: Dict, post_context: Dict, taste_shape: Dict) -> str:
    if taste_shape["lead_mode"] == "evidence":
        snippets = post_context.get("source_snippets", [])
        if snippets:
            return snippets[0].get("excerpt", "")
    if taste_shape["lead_mode"] == "question":
        questions = post_context.get("unresolved_questions", [])
        if questions:
            return questions[0]
    if taste_shape["lead_mode"] == "synthesis":
        return thought.get("what_changed", "") or thought.get("why_it_matters_now", "") or thought["short_text"]
    return thought["short_text"]


def _taste_cta_label(taste_shape: Dict) -> str:
    if taste_shape["lead_mode"] == "evidence" and taste_shape["interaction_bias"] == "thought_chat":
        return "Discuss evidence"
    if taste_shape["lead_mode"] == "evidence":
        return "See evidence"
    if taste_shape["lead_mode"] == "question":
        return "Open question"
    if taste_shape["interaction_bias"] == "thought_chat":
        return "Continue thinking"
    if taste_shape["compactness"] == "depth":
        return "Read deeper"
    return "Expand thought"


def _build_preview_payload(thought: Dict, post_format: str, post_context: Dict, taste_shape: Dict) -> Dict:
    lead_text = _taste_lead_text(thought, post_context, taste_shape)
    return {
        "kind": "preview",
        "format": post_format,
        "title": thought["title"],
        "short_text": thought["short_text"],
        "why_it_matters_now": thought.get("why_it_matters_now", ""),
        "lead_mode": taste_shape["lead_mode"],
        "lead_text": lead_text,
        "cta_label": _taste_cta_label(taste_shape),
        "taste_shape": taste_shape,
    }


def _build_expand_payload(thought: Dict, post_format: str, post_context: Dict, taste_shape: Dict) -> Dict:
    section_budget = 2 if taste_shape["compactness"] == "compact" else 3
    opening_focus = taste_shape["lead_mode"] if taste_shape["lead_mode"] != "summary" else "synthesis"
    opening_text = _taste_lead_text(thought, post_context, taste_shape)
    return {
        "kind": "expand",
        "format": post_format,
        "thought_id": thought["thought_id"],
        "title": thought.get("article_title") or thought["title"],
        "subtitle": thought["short_text"],
        "what_changed": thought.get("what_changed", ""),
        "why_it_matters_now": thought.get("why_it_matters_now", ""),
        "next_action": thought.get("next_action", ""),
        "article_sections": thought.get("article_sections", [])[:section_budget],
        "source_snippets": post_context.get("source_snippets", []),
        "supporting_meta": post_context.get("supporting_meta", [])[: (3 if taste_shape["compactness"] == "depth" else 2)],
        "opening_focus": opening_focus,
        "opening_text": opening_text,
        "recommended_interaction": taste_shape["interaction_bias"],
        "taste_shape": taste_shape,
    }


def _build_feed_post(
    root: Path,
    thought: Dict,
    taste_profile: Dict | None = None,
    *,
    meta_lookup: Dict[str, Dict] | None = None,
    chunk_lookup: Dict[str, Dict] | None = None,
) -> Dict:
    post_context = _build_post_context(root, thought, meta_lookup=meta_lookup, chunk_lookup=chunk_lookup)
    post_format, format_reason = _classify_post_format(thought, post_context)
    effective_taste_profile = taste_profile or _load_feed_taste_profile(root)
    taste_shape = _derive_taste_shape(post_format, post_context, effective_taste_profile)
    taste_diagnostics = _taste_diagnostics(post_format, post_context, effective_taste_profile, taste_shape)
    return {
        "post_id": thought["thought_id"],
        "post_format": post_format,
        "format_reason": format_reason,
        "reach_mode": post_context["reach_mode"],
        "preview_payload": _build_preview_payload(thought, post_format, post_context, taste_shape),
        "expand_payload": _build_expand_payload(thought, post_format, post_context, taste_shape),
        "deep_read_ref": {
            "surface": "thought_detail",
            "thought_id": thought["thought_id"],
            "path": f"/thought/{thought['thought_id']}",
        },
        "post_context": post_context,
        "taste_shape": taste_shape,
        "taste_diagnostics": taste_diagnostics,
    }


def _taste_preference_boost(post_format: str, taste_profile: Dict) -> float:
    format_scores = taste_profile.get("format_scores", {})
    preferred_formats = taste_profile.get("preferred_formats", [])
    base = float(format_scores.get(post_format, 0.0))
    if preferred_formats and preferred_formats[0] == post_format:
        base += 0.5
    return round(base, 2)


def _primary_source_ref(thought: Dict) -> str:
    refs = thought.get("source_refs", [])
    return refs[0] if refs else ""


def _diversity_band(thought: Dict, seen_sources: set[str], seen_bubbles: set[str]) -> int:
    source_ref = _primary_source_ref(thought)
    bubble_id = thought.get("primary_bubble_id", "")
    unseen_source = bool(source_ref) and source_ref not in seen_sources
    unseen_bubble = bool(bubble_id) and bubble_id not in seen_bubbles
    if unseen_source and unseen_bubble:
        return 0
    if unseen_source or unseen_bubble:
        return 1
    return 2


def _build_feed_context_lookups(root: Path, thoughts: List[Dict]) -> Dict[str, Dict[str, Dict]]:
    requested_meta_ids = {
        str(meta_id).strip()
        for thought in thoughts
        for meta_id in thought.get("meta_refs", [])
        if str(meta_id).strip()
    }
    requested_chunk_ids = {
        str(item_id).strip()
        for thought in thoughts
        for item_id in thought.get("source_item_ids", [])
        if str(item_id).strip()
    }
    return {
        "meta_lookup": _targeted_meta_lookup(root, requested_meta_ids),
        "chunk_lookup": _targeted_chunk_lookup(root, requested_chunk_ids),
    }


def _prepare_feed_candidates(
    root: Path,
    thoughts: List[Dict],
    taste_profile: Dict,
    *,
    meta_lookup: Dict[str, Dict] | None = None,
    chunk_lookup: Dict[str, Dict] | None = None,
) -> List[Dict]:
    prepared: List[Dict] = []
    for thought in thoughts:
        feed_post = _build_feed_post(
            root,
            thought,
            taste_profile,
            meta_lookup=meta_lookup,
            chunk_lookup=chunk_lookup,
        )
        prepared.append(
            thought
            | {
                "_feed_post": feed_post,
                "_taste_score": _taste_preference_boost(feed_post["post_format"], taste_profile),
            }
        )
    return prepared


def _select_feed_rows(thoughts: List[Dict], limit: int, taste_profile: Dict) -> tuple[List[Dict], Dict]:
    remaining = list(thoughts)
    selected: List[Dict] = []
    seen_sources: set[str] = set()
    seen_bubbles: set[str] = set()
    taste_adjusted_thought_ids: List[str] = []

    while remaining and len(selected) < limit:
        raw_best_index = 0
        raw_best_band = _diversity_band(remaining[0], seen_sources, seen_bubbles)
        for index, thought in enumerate(remaining[1:], start=1):
            band = _diversity_band(thought, seen_sources, seen_bubbles)
            if band < raw_best_band:
                raw_best_index = index
                raw_best_band = band
                if band == 0:
                    break

        best_index = raw_best_index
        best_band = raw_best_band
        best_taste_score = float(remaining[raw_best_index].get("_taste_score", 0.0))
        for index, thought in enumerate(remaining):
            band = _diversity_band(thought, seen_sources, seen_bubbles)
            taste_score = float(thought.get("_taste_score", 0.0))
            if band < best_band or (band == best_band and taste_score > best_taste_score):
                best_index = index
                best_band = band
                best_taste_score = taste_score
        chosen = remaining.pop(best_index)
        raw_best_taste_score = float(remaining[raw_best_index].get("_taste_score", 0.0)) if best_index != raw_best_index and raw_best_index < len(remaining) else 0.0
        if best_index != raw_best_index and float(chosen.get("_taste_score", 0.0)) > raw_best_taste_score:
            taste_adjusted_thought_ids.append(chosen["thought_id"])
        selected.append(chosen)
        source_ref = _primary_source_ref(chosen)
        bubble_id = chosen.get("primary_bubble_id", "")
        if source_ref:
            seen_sources.add(source_ref)
        if bubble_id:
            seen_bubbles.add(bubble_id)

    selected_source_refs = {_primary_source_ref(row) for row in selected if _primary_source_ref(row)}
    selected_bubble_ids = {row.get("primary_bubble_id", "") for row in selected if row.get("primary_bubble_id", "")}
    return selected, {
        "candidate_pool_count": len(thoughts),
        "selected_count": len(selected),
        "unique_primary_source_count": len(selected_source_refs),
        "unique_primary_bubble_count": len(selected_bubble_ids),
        "selected_thought_ids": [row["thought_id"] for row in selected],
        "applied_preferred_formats": list(taste_profile.get("preferred_formats", [])),
        "taste_adjusted_thought_ids": taste_adjusted_thought_ids,
    }


def _format_diagnostics(thoughts: List[Dict]) -> Dict:
    counts = Counter(row.get("post_format", "unknown") for row in thoughts)
    return {
        "counts": dict(counts),
    }


def _taste_post_diagnostics(thoughts: List[Dict]) -> Dict:
    return {
        row["thought_id"]: row.get("taste_diagnostics", {})
        for row in thoughts
        if row.get("thought_id")
    }


def build_thought_feed(
    root: Path,
    limit: int = 12,
    domain_overlays: List[str] | None = None,
    regenerate_batch: bool = True,
) -> Dict:
    if regenerate_batch and not load_thought_packets(root):
        guard = _thought_runtime_guard(root)
        if guard is not None:
            result = _empty_thought_surface(root, surface="feed", guard=guard)
            write_json(_thought_feed_path(root), result)
            write_json(_exports_dir(root) / "latest_feed.json", result)
            return result
        batch_result = generate_daily_batch(root, limit=max(limit, 5), domain_overlays=domain_overlays, write_feed=False)
        if batch_result.get("status") in {"rebuilding", "runtime_not_ready"} and not load_thought_packets(root):
            guard = {
                "status": batch_result["status"],
                "pipeline_summary": batch_result.get("pipeline_summary"),
                "runtime_counts": batch_result.get("runtime_counts", {}),
                "context_bubbles_progress": batch_result.get("context_bubbles_progress", {}),
            }
            result = _empty_thought_surface(root, surface="feed", guard=guard)
            write_json(_thought_feed_path(root), result)
            write_json(_exports_dir(root) / "latest_feed.json", result)
            return result
    candidate_limit = max(limit, limit * 4, limit + 6)
    taste_profile = _load_feed_taste_profile(root)
    candidate_rows = build_feed_rows(root, candidate_limit)
    feed_context_lookups = _build_feed_context_lookups(root, candidate_rows)
    prepared_candidates = _prepare_feed_candidates(
        root,
        candidate_rows,
        taste_profile,
        meta_lookup=feed_context_lookups["meta_lookup"],
        chunk_lookup=feed_context_lookups["chunk_lookup"],
    )
    selected_rows, selection_diagnostics = _select_feed_rows(prepared_candidates, limit, taste_profile)
    thoughts = _feed_rows_with_threads(root, selected_rows, taste_profile)
    thoughts = _filter_rows_by_runtime_sources(root, thoughts, fields=("source_ref", "source_refs"))
    result = {
        "generated_at": utc_now(),
        "count": len(thoughts),
        "thoughts": thoughts,
        "diagnostics": {
            "selection": selection_diagnostics,
            "formats": _format_diagnostics(thoughts),
            "taste_profile": taste_profile,
            "taste_posts": _taste_post_diagnostics(thoughts),
        },
    }
    write_json(_thought_feed_path(root), result)
    write_json(_exports_dir(root) / "latest_feed.json", result)
    md = ["# Thought Feed", "", f"- generated_at: {result['generated_at']}", f"- count: {result['count']}", ""]
    diagnostics = result["diagnostics"]["selection"]
    format_diagnostics = result["diagnostics"]["formats"]["counts"]
    taste_profile = result["diagnostics"]["taste_profile"]
    md.extend(
        [
            "## Feed Diagnostics",
            "",
            f"- candidate_pool_count: {diagnostics['candidate_pool_count']}",
            f"- selected_count: {diagnostics['selected_count']}",
            f"- unique_primary_source_count: {diagnostics['unique_primary_source_count']}",
            f"- unique_primary_bubble_count: {diagnostics['unique_primary_bubble_count']}",
            f"- format_counts: {json.dumps(format_diagnostics, ensure_ascii=False, sort_keys=True)}",
            f"- preferred_formats: {', '.join(taste_profile.get('preferred_formats', [])) or 'none'}",
            "",
        ]
    )
    for thought in thoughts:
        md.extend(
            [
                f"## {thought['title']}",
                "",
                thought["short_text"],
                "",
                f"- evidence_status: {thought['evidence_status']}",
                f"- reasoning_primitive: {thought['shared_primitive_label']}",
                f"- source_refs: {', '.join(thought['source_refs'])}",
                f"- thread_count: {thought['thread_count']}",
                "",
            ]
        )
    write_markdown(_exports_dir(root) / "latest_feed.md", "\n".join(md))
    return result


def build_thought_archive(root: Path, domain_overlays: List[str] | None = None) -> Dict:
    if not load_thought_packets(root):
        guard = _thought_runtime_guard(root)
        if guard is not None:
            result = _empty_thought_surface(root, surface="archive", guard=guard)
            write_json(_exports_dir(root) / "latest_archive.json", result)
            return result
        batch_result = generate_daily_batch(root, limit=8, domain_overlays=domain_overlays, write_feed=False)
        if batch_result.get("status") in {"rebuilding", "runtime_not_ready"} and not load_thought_packets(root):
            result = _empty_thought_surface(
                root,
                surface="archive",
                guard={
                    "status": batch_result["status"],
                    "pipeline_summary": batch_result.get("pipeline_summary"),
                    "runtime_counts": batch_result.get("runtime_counts", {}),
                    "context_bubbles_progress": batch_result.get("context_bubbles_progress", {}),
                },
            )
            write_json(_exports_dir(root) / "latest_archive.json", result)
            return result
    thoughts = _feed_rows_with_threads(root, build_archive_rows(root))
    thoughts = _filter_rows_by_runtime_sources(root, thoughts, fields=("source_ref", "source_refs"))
    result = {
        "generated_at": utc_now(),
        "count": len(thoughts),
        "thoughts": thoughts,
        "filters": {
            "evidence_status": sorted({thought["evidence_status"] for thought in thoughts}),
            "feedback_state": sorted({thought["feedback_state"] for thought in thoughts}),
            "reasoning_primitive": sorted({thought["shared_primitive_label"] for thought in thoughts}),
        },
    }
    write_json(_exports_dir(root) / "latest_archive.json", result)
    md = ["# Thought Archive", "", f"- generated_at: {result['generated_at']}", f"- count: {result['count']}", ""]
    for thought in thoughts:
        md.extend(
            [
                f"## {thought['title']}",
                "",
                thought["short_text"],
                "",
                f"- evidence_status: {thought['evidence_status']}",
                f"- feedback_state: {thought['feedback_state']}",
                "",
            ]
        )
    write_markdown(_exports_dir(root) / "latest_archive.md", "\n".join(md))
    return result


def _thought_lookup(root: Path) -> Dict[str, Dict]:
    return {row["thought_id"]: row for row in load_thought_packets(root)}


def _chunk_lookup(root: Path) -> Dict[str, Dict]:
    return {row["source_item_id"]: row for row in load_chunk_index(root)}


def list_bubbles(root: Path, limit: int = 12, domain_overlays: List[str] | None = None) -> Dict:
    _ensure_runtime(root, domain_overlays)
    return list_context_bubbles(root, limit)


def get_bubble_detail(root: Path, bubble_id: str, domain_overlays: List[str] | None = None) -> Dict:
    _ensure_runtime(root, domain_overlays)
    return get_context_bubble(root, bubble_id)


def _filter_text_score(text: str, query_tokens: set[str]) -> float:
    if not query_tokens:
        return 0.0
    lowered = text.lower()
    return float(sum(1 for token in query_tokens if token in lowered))


def filter_knowledge_components(
    root: Path,
    *,
    query: str = "",
    component_types: List[str] | None = None,
    statuses: List[str] | None = None,
    source_ref: str | None = None,
    bubble_id: str | None = None,
    concept_id: str | None = None,
    limit: int = 20,
    domain_overlays: List[str] | None = None,
) -> Dict:
    _ensure_runtime(root, domain_overlays)
    selected_types = set(component_types or ["concept", "bubble", "meta", "thought"])
    status_filter = set(statuses or [])
    query_tokens = set(tokenize(query))
    results: List[Dict] = []

    concept_lookup = {row["concept_id"]: row for row in load_concept_nodes(root)}
    bubble_lookup = {row["bubble_id"]: row for row in load_context_bubbles(root)}
    bubble_memberships = load_bubble_memberships(root)
    bubble_meta_map: Dict[str, set[str]] = {}
    for membership in bubble_memberships:
        bubble_meta_map.setdefault(membership["bubble_id"], set()).add(membership["meta_id"])

    if "concept" in selected_types:
        for row in search_concepts(root, query or " ".join(filter(None, [concept_id, bubble_id])) or "concept", limit=max(limit, 8)):
            if status_filter and row.get("status") not in status_filter:
                continue
            if source_ref and source_ref not in row.get("source_refs", []):
                continue
            if concept_id and row.get("concept_id") != concept_id:
                continue
            if bubble_id and concept_id is None and row.get("concept_id") not in bubble_lookup.get(bubble_id, {}).get("concept_ids", []):
                continue
            results.append(
                {
                    "component_type": "concept",
                    "id": row["concept_id"],
                    "label": row["label"],
                    "status": row.get("status", "provisional"),
                    "confidence": row.get("confidence", 0.0),
                    "source_refs": row.get("source_refs", []),
                    "score": row.get("_score", row.get("confidence", 0.0)),
                    "reasons": row.get("_reasons", []),
                }
            )

    if "bubble" in selected_types:
        for row in load_context_bubbles(root):
            if status_filter and row.get("status") not in status_filter:
                continue
            if source_ref and source_ref not in row.get("source_refs", []):
                continue
            if bubble_id and row.get("bubble_id") != bubble_id:
                continue
            if concept_id and concept_id not in row.get("concept_ids", []):
                continue
            score = _filter_text_score(" ".join([row.get("label", ""), row.get("thesis", ""), " ".join(row.get("domain_lenses", []))]), query_tokens)
            if concept_id and concept_id in row.get("concept_ids", []):
                score += 4.0
            if bubble_id and row.get("bubble_id") == bubble_id:
                score += 4.0
            if query and score <= 0:
                continue
            results.append(
                {
                    "component_type": "bubble",
                    "id": row["bubble_id"],
                    "label": row["label"],
                    "status": row.get("status", "active"),
                    "confidence": row.get("confidence", 0.0),
                    "source_refs": row.get("source_refs", []),
                    "score": score or row.get("confidence", 0.0),
                    "reasons": ["concept"] if concept_id and concept_id in row.get("concept_ids", []) else ["query"] if query else ["confidence"],
                }
            )

    if "meta" in selected_types:
        target_meta_ids = bubble_meta_map.get(bubble_id, set()) if bubble_id else set()
        for row in load_meta_records(root):
            if status_filter and row.get("status") not in status_filter:
                continue
            if source_ref and source_ref not in row.get("source_refs", []):
                continue
            if bubble_id and row.get("meta_id") not in target_meta_ids:
                continue
            score = _filter_text_score(" ".join([row.get("label", ""), row.get("summary", "")]), query_tokens)
            if concept_id:
                concept = concept_lookup.get(concept_id, {})
                score += _filter_text_score(" ".join(concept.get("aliases", []) + [concept.get("label", "")]), set(tokenize(row.get("label", "")))) * 0.5
            if query and score <= 0 and not bubble_id:
                continue
            results.append(
                {
                    "component_type": "meta",
                    "id": row["meta_id"],
                    "label": row["label"],
                    "status": row.get("status", "provisional"),
                    "confidence": row.get("confidence", 0.0),
                    "source_refs": row.get("source_refs", []),
                    "score": score or row.get("confidence", 0.0),
                    "reasons": ["bubble"] if bubble_id else ["query"] if query else ["confidence"],
                }
            )

    if "thought" in selected_types:
        for row in load_thought_packets(root):
            if status_filter and row.get("status") not in status_filter and row.get("review_status") not in status_filter:
                continue
            if source_ref and source_ref not in row.get("source_refs", []):
                continue
            if bubble_id and bubble_id not in [row.get("primary_bubble_id", "")] + row.get("related_bubble_ids", []):
                continue
            score = _filter_text_score(" ".join([row.get("title", ""), row.get("short_text", ""), row.get("why_it_matters_now", "")]), query_tokens)
            if query and score <= 0 and not bubble_id:
                continue
            results.append(
                {
                    "component_type": "thought",
                    "id": row["thought_id"],
                    "label": row["title"],
                    "status": row.get("review_status", row.get("status", "pending")),
                    "confidence": row.get("confidence_score", 0.0),
                    "source_refs": row.get("source_refs", []),
                    "score": score or row.get("confidence_score", 0.0),
                    "reasons": ["bubble"] if bubble_id else ["query"] if query else ["confidence"],
                }
            )

    if "capsule" in selected_types:
        for row in load_semantic_capsules(root):
            if status_filter and row.get("status") not in status_filter:
                continue
            if source_ref and source_ref not in row.get("source_refs", []):
                continue
            if bubble_id and f"bubble:{bubble_id}" not in row.get("linked_ref_ids", []) and not (
                row.get("ref_type") == "bubble" and row.get("ref_id") == bubble_id
            ):
                continue
            if concept_id and f"concept:{concept_id}" not in row.get("linked_ref_ids", []) and not (
                row.get("ref_type") == "concept" and row.get("ref_id") == concept_id
            ):
                continue
            haystack = " ".join(
                [
                    row.get("label", ""),
                    row.get("summary", ""),
                    row.get("capsule_type", ""),
                    json.dumps(row.get("attributes", {}), ensure_ascii=False),
                ]
            )
            score = _filter_text_score(haystack, query_tokens)
            if bubble_id and (row.get("ref_type") == "bubble" and row.get("ref_id") == bubble_id):
                score += 4.0
            if concept_id and (row.get("ref_type") == "concept" and row.get("ref_id") == concept_id):
                score += 4.0
            if query and score <= 0 and not bubble_id and not concept_id:
                continue
            results.append(
                {
                    "component_type": "capsule",
                    "id": row["capsule_id"],
                    "label": row.get("label", ""),
                    "status": row.get("status", "provisional"),
                    "confidence": row.get("confidence", 0.0),
                    "source_refs": row.get("source_refs", []),
                    "score": score or row.get("confidence", 0.0),
                    "reasons": ["bubble"] if bubble_id else ["concept"] if concept_id else ["query"] if query else ["confidence"],
                }
            )

    if "link" in selected_types:
        for row in load_context_links(root):
            if status_filter and row.get("status") not in status_filter:
                continue
            if source_ref and source_ref not in row.get("evidence_refs", []):
                continue
            if bubble_id and bubble_id not in {row.get("from_ref_id", ""), row.get("to_ref_id", "")}:
                continue
            if concept_id and concept_id not in {row.get("from_ref_id", ""), row.get("to_ref_id", "")}:
                continue
            haystack = " ".join(
                [
                    row.get("layer", ""),
                    row.get("kind", ""),
                    row.get("from_ref_type", ""),
                    row.get("from_ref_id", ""),
                    row.get("to_ref_type", ""),
                    row.get("to_ref_id", ""),
                    json.dumps(row.get("attributes", {}), ensure_ascii=False),
                ]
            )
            score = _filter_text_score(haystack, query_tokens)
            if bubble_id and bubble_id in {row.get("from_ref_id", ""), row.get("to_ref_id", "")}:
                score += 4.0
            if concept_id and concept_id in {row.get("from_ref_id", ""), row.get("to_ref_id", "")}:
                score += 4.0
            if query and score <= 0 and not bubble_id and not concept_id:
                continue
            results.append(
                {
                    "component_type": "link",
                    "id": row["link_id"],
                    "label": f"{row.get('kind', '')}: {row.get('from_ref_type', '')}:{row.get('from_ref_id', '')} -> {row.get('to_ref_type', '')}:{row.get('to_ref_id', '')}",
                    "status": row.get("status", "provisional"),
                    "confidence": row.get("confidence", 0.0),
                    "source_refs": row.get("evidence_refs", []),
                    "score": score or row.get("confidence", 0.0),
                    "reasons": ["bubble"] if bubble_id else ["concept"] if concept_id else ["query"] if query else ["confidence"],
                }
            )

    results.sort(key=lambda item: (-float(item.get("score", 0.0)), -float(item.get("confidence", 0.0)), item["component_type"], item["label"]))
    return {
        "count": len(results),
        "results": results[:limit],
        "filters": {
            "query": query,
            "component_types": sorted(selected_types),
            "statuses": sorted(status_filter),
            "source_ref": source_ref or "",
            "bubble_id": bubble_id or "",
            "concept_id": concept_id or "",
            "limit": limit,
        },
    }


def get_thought_detail(root: Path, thought_id: str, domain_overlays: List[str] | None = None) -> Dict:
    if not load_thought_packets(root):
        guard = _thought_runtime_guard(root)
        if guard is not None:
            return _empty_thought_surface(root, surface="detail", guard=guard) | {"thought_id": thought_id}
    thought = _thought_lookup(root).get(thought_id)
    if thought is None:
        raise KeyError(thought_id)
    chunks = _chunk_lookup(root)
    source_snippets = []
    for item_id in thought.get("source_item_ids", [])[:6]:
        row = chunks.get(item_id)
        if not row:
            continue
        source_snippets.append(
            {
                "source_item_id": item_id,
                "title": row["title"],
                "source_type": row["source_type"],
                "source_ref": row["source_ref"],
                "excerpt": shorten(row["content"], 220),
            }
        )
    threads = _list_threads(root, thought_id)
    active_thread = next((thread for thread in threads if thread["status"] == "saved"), None) or (threads[0] if threads else None)
    feed_post = _build_feed_post(root, thought, _load_feed_taste_profile(root))
    _record_feed_learning_event(root, thought=thought, event_type="detail_open")
    return {
        "thought": thought,
        "feed_post": feed_post,
        "primitive": {
            "label": thought.get("shared_primitive_label", "Thought Packet"),
            "plugin_id": thought.get("reasoning_pipeline", "thought_pipeline"),
        },
        "source_snippets": source_snippets,
        "threads": threads,
        "active_thread": active_thread,
    }


def get_source_item_detail(root: Path, source_item_id: str, domain_overlays: List[str] | None = None) -> Dict:
    row = _chunk_lookup(root).get(source_item_id)
    if row is None:
        raise KeyError(source_item_id)
    siblings = [
        sibling
        for sibling in load_chunk_index(root)
        if sibling["source_id"] == row["source_id"] and sibling["source_item_id"] != source_item_id
    ][:6]
    related_thoughts = [
        thought
        for thought in build_archive_rows(root)
        if source_item_id in thought.get("source_item_ids", [])
    ][:6]
    meta_rows = [
        record
        for record in load_meta_records(root)
        if source_item_id in record.get("chunk_ids", [])
    ]
    return {
        "source_item": row | {"path_name": Path(row["source_ref"]).name},
        "sibling_items": [
            {
                "source_item_id": item["source_item_id"],
                "title": item["title"],
                "source_type": item["source_type"],
                "excerpt": shorten(item["content"], 180),
            }
            for item in siblings
        ],
        "related_thoughts": related_thoughts,
        "meta_layer": meta_rows[:12],
    }


def build_thought_context(root: Path, thought_id: str, domain_overlays: List[str] | None = None) -> Dict:
    return build_thread_packet(root, thought_id)


def _create_thread(root: Path, thought_id: str, domain_overlays: List[str] | None = None) -> Dict:
    context = build_thought_context(root, thought_id, domain_overlays)
    now = utc_now()
    thread = {
        "thread_id": make_id("thread"),
        "thought_id": thought_id,
        "title": context["thought"]["title"],
        "status": "draft",
        "created_at": now,
        "updated_at": now,
        "character": context["character"],
        "system_prompt": context["system_prompt"],
        "context_summary": context["context_summary"],
        "source_refs": context["thought"]["source_refs"],
        "reasoning_primitive": context["thought"]["reasoning_pipeline"],
        "backend_id": "heuristic",
        "messages": [],
        "embedded_source_item_ids": [],
    }
    _write_thread(root, thread)
    return thread


def _generate_assistant_reply(context: Dict, user_message: str, thread: Dict) -> str:
    tensions = context.get("tensions", [])
    contradictions = context.get("contradictions", [])
    open_questions = context.get("unresolved_questions", [])
    source_snippets = context.get("source_snippets", [])
    evidence = source_snippets[:2]
    evidence_clause = " ".join(snippet["excerpt"] for snippet in evidence) if evidence else context["context_summary"]
    response_parts = [f"It seems to keep circling this: {context['context_summary'].rstrip('.')}."]
    response_parts.append(f"The part with the most weight right now is {shorten(evidence_clause, 220).rstrip('.')}.")
    if tensions:
        response_parts.append(f"The friction in it feels like {tensions[0]['summary'].rstrip('.')}.")
    if contradictions:
        response_parts.append(f"There is also a sharper break in the background: {contradictions[0]['summary'].rstrip('.')}.")
    if open_questions:
        response_parts.append(f"What still refuses to settle is {open_questions[0].rstrip('.')}.")
    response_parts.append(f"If you follow it a little further, the next move is {context['thought']['next_action'].rstrip('.')}.")
    return " ".join(response_parts)


def chat_with_thought(
    root: Path,
    thought_id: str,
    user_message: str,
    thread_id: str | None = None,
    domain_overlays: List[str] | None = None,
) -> Dict:
    thought_lookup = _thought_lookup(root)
    if thought_id not in thought_lookup:
        raise KeyError(thought_id)
    thread = _load_thread(root, thread_id) if thread_id else _create_thread(root, thought_id, domain_overlays)
    context = build_thought_context(root, thought_id, domain_overlays)
    backend = resolve_chat_backend(root)
    user_entry = {"message_id": make_id("message"), "role": "user", "content": user_message, "created_at": utc_now()}
    thread["messages"].append(user_entry)
    if backend["id"] == "heuristic":
        assistant_content = _generate_assistant_reply(context, user_message, thread)
        backend_id = "heuristic"
    else:
        reply = request_openclaw_reply(root, context, user_message, thread, backend)
        assistant_content = reply["content"]
        backend_id = reply["backend_id"]
    assistant_entry = {"message_id": make_id("message"), "role": "assistant", "content": assistant_content, "created_at": utc_now()}
    thread["messages"].append(assistant_entry)
    thread["updated_at"] = utc_now()
    thread["backend_id"] = backend_id
    _write_thread(root, thread)
    _record_feed_learning_event(root, thought=thought_lookup[thought_id], event_type="thought_chat", thread_id=thread["thread_id"])
    return {
        "thread": thread,
        "assistant_message": assistant_entry,
        "thought": thought_lookup[thought_id],
        "context": context,
    }


def _append_thread_to_library(root: Path, thread: Dict) -> List[str]:
    transcript_lines = [f"# Thread: {thread['title']}", "", thread["context_summary"], ""]
    for message in thread.get("messages", []):
        transcript_lines.append(f"## {message['role'].title()}")
        transcript_lines.append(message["content"])
        transcript_lines.append("")
    result = ingest_text_content(
        root,
        title=f"thread {thread['thread_id']}",
        content="\n".join(transcript_lines).strip(),
        source_ref=f"inner-world://thread/{thread['thread_id']}",
        source_type="thread_embedding",
        source_family="thread_derivations",
        sensitivity_tier="tier_work_product",
        metadata={"thread_id": thread["thread_id"]},
    )
    chunk_rows = [row for row in load_chunk_index(root) if row["source_id"] == result["source_id"]]
    return [row["source_item_id"] for row in chunk_rows]


def save_thread(root: Path, thread_id: str, domain_overlays: List[str] | None = None) -> Dict:
    thread = _load_thread(root, thread_id)
    thread["status"] = "saved"
    thread["updated_at"] = utc_now()
    thread["embedded_source_item_ids"] = _append_thread_to_library(root, thread)
    _write_thread(root, thread)
    _ensure_runtime(root, domain_overlays)
    thought = _thought_lookup(root).get(thread["thought_id"])
    if thought is not None:
        _record_feed_learning_event(root, thought=thought, event_type="thread_saved", thread_id=thread_id)
    return {"thread_id": thread_id, "status": thread["status"], "embedded_source_item_ids": thread["embedded_source_item_ids"]}


def delete_thread(root: Path, thread_id: str) -> Dict:
    thread = _load_thread(root, thread_id)
    thread["status"] = "deleted"
    thread["updated_at"] = utc_now()
    _write_thread(root, thread)
    return {"thread_id": thread_id, "status": thread["status"]}


def record_feedback(root: Path, insight_id: str, feedback_state: str) -> Dict:
    path = _data_dir(root) / "feedback_events.jsonl"
    rows = _load_feedback_events(root)
    rows.append({"event_id": make_id("feedback"), "insight_id": insight_id, "feedback_state": feedback_state, "created_at": utc_now()})
    from .storage import write_jsonl

    write_jsonl(path, rows)
    snapshot = update_policy_snapshot(root, rows)
    thought = _thought_by_insight_lookup(root).get(insight_id)
    taste_profile = _load_feed_taste_profile(root)
    if thought is not None:
        taste_profile = _record_feed_learning_event(
            root,
            thought=thought,
            event_type="explicit_feedback",
            feedback_state=feedback_state,
        )["taste_profile"]
    return {"insight_id": insight_id, "feedback_state": feedback_state, "policy_snapshot": snapshot, "taste_profile": taste_profile}


def ensure_mobile_capture_session(root: Path, session_id: str | None = None) -> Dict[str, Any]:
    resolved_session_id = session_id or make_id("session")
    existing = _load_session_manifest(root, resolved_session_id)
    if existing is not None:
        if existing.get("source_type") != "mobile_surface":
            raise ValueError(f"Session {resolved_session_id} is not a mobile_surface session")
        return existing

    manifest = SessionManifest(
        session_id=resolved_session_id,
        title="Mobile Capture Session",
        started_at=utc_now(),
        ended_at=None,
        participants=["user", "assistant"],
        source_type="mobile_surface",
        status="active",
        artifact_refs={},
        domains=[],
    )
    _write_session_manifest(root, manifest)
    return manifest.to_dict()


def append_mobile_capture(root: Path, *, content: str, session_id: str | None = None) -> Dict[str, Any]:
    manifest = ensure_mobile_capture_session(root, session_id=session_id)
    capture_event = _append_session_event(
        root,
        session_id=manifest["session_id"],
        actor="user",
        kind="capture",
        content=content,
        tags=["mobile_surface", "capture"],
    )
    return {
        "capture_id": capture_event["event_id"],
        "session_id": manifest["session_id"],
        "created_at": capture_event["timestamp"],
        "continue_conversation_available": True,
    }


def reply_in_mobile_session(root: Path, *, session_id: str, user_message: str) -> Dict[str, Any]:
    manifest = ensure_mobile_capture_session(root, session_id=session_id)
    user_event = _append_session_event(
        root,
        session_id=manifest["session_id"],
        actor="user",
        kind="message",
        content=user_message,
        tags=["mobile_surface", "conversation"],
    )
    events = read_jsonl(session_events_path(root, manifest["session_id"]))
    reply = _request_mobile_session_reply(
        root,
        session_manifest=manifest,
        user_message=user_message,
        events=events,
    )
    assistant_event = _append_session_event(
        root,
        session_id=manifest["session_id"],
        actor="assistant",
        kind="reply",
        content=reply["content"],
        tags=["mobile_surface", "conversation"],
    )
    return {
        "session_id": manifest["session_id"],
        "user_message": user_event,
        "assistant_message": {
            "event_id": assistant_event["event_id"],
            "content": assistant_event["content"],
            "created_at": assistant_event["timestamp"],
        },
        "backend_id": reply.get("backend_id", ""),
    }


def build_mobile_feed(root: Path, *, domain_overlays: List[str] | None = None, limit: int = 12) -> Dict[str, Any]:
    feed = build_thought_feed(root, limit=limit, domain_overlays=domain_overlays)
    items = [
        {
            "thought_id": thought["thought_id"],
            "insight_id": thought["insight_id"],
            "title": thought["title"],
            "summary": thought["short_text"],
            "feedback_state": thought.get("feedback_state", "pending"),
            "post_format": thought.get("post_format", ""),
            "thread_count": thought.get("thread_count", 0),
            "source_refs": list(thought.get("source_refs", [])),
        }
        for thought in feed.get("thoughts", [])
    ]
    return {
        "generated_at": feed.get("generated_at", utc_now()),
        "count": len(items),
        "items": items,
    }


def save_mobile_feed_item(root: Path, *, insight_id: str) -> Dict[str, Any]:
    return record_feedback(root, insight_id, "saved")


def build_mobile_library(root: Path) -> Dict[str, Any]:
    captures: List[Dict[str, Any]] = []
    conversations: List[Dict[str, Any]] = []
    for manifest in _mobile_session_manifests(root):
        events = read_jsonl(session_events_path(root, manifest["session_id"]))
        capture_events = [event for event in events if event.get("kind") == "capture"]
        captures.extend(
            {
                "capture_id": event["event_id"],
                "session_id": manifest["session_id"],
                "content": event["content"],
                "created_at": event["timestamp"],
            }
            for event in capture_events
        )
        assistant_events = [event for event in events if event.get("actor") == "assistant" and event.get("content")]
        if assistant_events:
            conversations.append(
                {
                    "conversation_type": "mobile_session",
                    "session_id": manifest["session_id"],
                    "title": manifest.get("title", ""),
                    "updated_at": assistant_events[-1]["timestamp"],
                    "message_count": len([event for event in events if event.get("actor") in {"user", "assistant"}]),
                    "preview": assistant_events[-1]["content"],
                }
            )

    for thread in _list_threads(root):
        if thread.get("status") != "saved":
            continue
        preview = ""
        for message in reversed(thread.get("messages", [])):
            content = message.get("content", "").strip()
            if content:
                preview = content
                break
        conversations.append(
            {
                "conversation_type": "saved_thread",
                "thread_id": thread["thread_id"],
                "thought_id": thread.get("thought_id", ""),
                "title": thread.get("title", ""),
                "updated_at": thread.get("updated_at", ""),
                "message_count": len(thread.get("messages", [])),
                "preview": preview,
            }
        )

    saved_feedback_states = {"saved", "relevant", "revisit_later"}
    archive = build_thought_archive(root)
    saved_items = [
        {
            "insight_id": thought["insight_id"],
            "title": thought["title"],
            "summary": thought.get("short_text", ""),
            "feedback_state": thought.get("feedback_state", ""),
        }
        for thought in archive.get("thoughts", [])
        if thought.get("feedback_state") in saved_feedback_states
    ]

    captures.sort(key=lambda item: (item["created_at"], item["capture_id"]), reverse=True)
    conversations.sort(key=lambda item: (item.get("updated_at", ""), item.get("title", "")), reverse=True)
    saved_items.sort(key=lambda item: (item["feedback_state"], item["title"], item["insight_id"]))
    return {
        "captures": captures,
        "conversations": conversations,
        "saved_items": saved_items,
    }


def export_state(root: Path) -> Dict:
    runtime_summary = _ensure_runtime(root, None)
    batch = generate_daily_batch(root, limit=5, domain_overlays=None, write_feed=False)
    batch = _filter_thought_surface_payload(root, batch)
    thought_feed = build_thought_feed(root, limit=12, domain_overlays=None, regenerate_batch=False)
    build_thought_archive(root, domain_overlays=None)
    insight_candidates = _filter_rows_by_runtime_sources(
        root,
        read_json(_data_dir(root) / "insight_candidates.json", default=[]),
        fields=("source_ref", "source_refs"),
    )
    payload = {
        "runtime_pipeline": get_runtime_pipeline_status(root),
        "source_registry": load_source_registry(root),
        "chunk_index": load_chunk_index(root),
        "analysis_units": load_analysis_units(root),
        "conversation_threads": load_conversation_threads(root),
        "conversation_thread_links": load_thread_links(root),
        "thread_abstractions": load_thread_abstractions(root),
        "thread_abstraction_links": load_thread_abstraction_links(root),
        "project_lenses": load_project_lenses(root),
        "meta_layer": {kind: len(load_meta_records(root, [kind])) for kind in ["theme", "shared_primitive", "tension", "contradiction", "review_item"]},
        "context_bubbles": load_context_bubbles(root),
        "bubble_memberships": load_bubble_memberships(root),
        "bubble_edges": load_bubble_edges(root),
        "bubble_transitions": load_bubble_transitions(root),
        "knowledge_nodes": load_knowledge_nodes(root),
        "knowledge_edges": load_knowledge_edges(root),
        "context_links": load_context_links(root),
        "semantic_capsules": load_semantic_capsules(root),
        "concept_graph": {
            "concept_nodes": load_concept_nodes(root),
            "concept_edges": load_concept_edges(root),
            "synthesis_packets": load_synthesis_packets(root),
            "touch_operations": load_touch_operations(root),
            "review_queue": load_concept_review_queue(root),
        },
        "insight_candidates": insight_candidates,
        "surfaced_insights": batch,
        "review_queue": load_review_queue(root),
        "promotion_packets": load_promotion_packets(root),
        "thought_packets": load_thought_packets(root),
        "thought_feed": thought_feed,
        "library_tracker": get_library_tracker_status(root),
        "llm_costs": get_cost_summary(root),
        "runtime_summary": runtime_summary,
    }
    write_json(_exports_dir(root) / "state_export.json", payload)
    md = [
        "# State Export",
        "",
        f"- source_count: {len(payload['source_registry'])}",
        f"- chunk_count: {len(payload['chunk_index'])}",
        f"- analysis_unit_count: {len(payload['analysis_units'])}",
        f"- conversation_threads: {len(payload['conversation_threads'])}",
        f"- thread_abstractions: {len(payload['thread_abstractions'])}",
        f"- project_lenses: {len(payload['project_lenses'])}",
        f"- meta_records: {sum(payload['meta_layer'].values())}",
        f"- context_bubbles: {len(payload['context_bubbles'])}",
        f"- knowledge_nodes: {len(payload['knowledge_nodes'])}",
        f"- knowledge_edges: {len(payload['knowledge_edges'])}",
        f"- context_links: {len(payload['context_links'])}",
        f"- semantic_capsules: {len(payload['semantic_capsules'])}",
        f"- concept_nodes: {len(payload['concept_graph']['concept_nodes'])}",
        f"- concept_edges: {len(payload['concept_graph']['concept_edges'])}",
        f"- concept_reviews: {len(payload['concept_graph']['review_queue'])}",
        f"- review_queue: {len(payload['review_queue'])}",
        f"- promotion_packets: {len(payload['promotion_packets'])}",
        f"- thought_packets: {len(payload['thought_packets'])}",
        f"- library_tracked_items: {payload['library_tracker']['tracked_item_count']}",
        f"- actual_llm_usd: {payload['llm_costs']['totals']['actual_usd_total']}",
        f"- equivalent_llm_usd: {payload['llm_costs']['totals']['equivalent_usd_total']}",
    ]
    write_markdown(_exports_dir(root) / "state_export.md", "\n".join(md))
    return payload


def get_runtime_overview(root: Path) -> Dict:
    source_rows = load_source_registry(root)
    thought_packets = load_thought_packets(root)
    review_rows = load_review_queue(root)
    analysis_units = load_analysis_units(root)
    conversation_threads = load_conversation_threads(root)
    thread_abstractions = load_thread_abstractions(root)
    project_lenses = load_project_lenses(root)
    context_bubbles = load_context_bubbles(root)
    knowledge_nodes = load_knowledge_nodes(root)
    knowledge_edges = load_knowledge_edges(root)
    context_links = load_context_links(root)
    semantic_capsules = load_semantic_capsules(root)
    concept_nodes = load_concept_nodes(root)
    concept_edges = load_concept_edges(root)
    concept_reviews = load_concept_review_queue(root)
    pipeline_status = get_runtime_pipeline_status(root)
    family_counts: Dict[str, int] = {}
    type_counts: Dict[str, int] = {}
    for row in source_rows:
        family = row.get("source_family", "unknown")
        source_type = row.get("source_type", "unknown")
        family_counts[family] = family_counts.get(family, 0) + 1
        type_counts[source_type] = type_counts.get(source_type, 0) + 1
    tracker_status = get_library_tracker_status(root)
    dimension_model_roles = get_dimension_model_role_status(root)
    pond_router = get_pond_router_status(root)
    cost_summary = get_cost_summary(root)
    connections_payload = _connections_payload(root)
    return {
        "generated_at": utc_now(),
        "runtime_pipeline": pipeline_status,
        "pipeline": _pipeline_frontend_snapshot(root),
        "context_bubbles_progress": read_json(_context_bubbles_progress_path(root), default={}) or {},
        "counts": {
            "sources": len(source_rows),
            "chunks": len(load_chunk_index(root)),
            "analysis_units": len(analysis_units),
            "conversation_threads": len(conversation_threads),
            "thread_abstractions": len(thread_abstractions),
            "project_lenses": len(project_lenses),
            "context_bubbles": len(context_bubbles),
            "library_tracked_items": tracker_status["tracked_item_count"],
            "llm_cost_events": cost_summary["totals"]["event_count"],
            "thought_packets": len(thought_packets),
            "review_queue": len(review_rows),
            "insight_candidates": len(
                _filter_rows_by_runtime_sources(
                    root,
                    read_json(_data_dir(root) / "insight_candidates.json", default=[]),
                    fields=("source_ref", "source_refs"),
                )
            ),
            "knowledge_nodes": len(knowledge_nodes),
            "knowledge_edges": len(knowledge_edges),
            "context_links": len(context_links),
            "semantic_capsules": len(semantic_capsules),
            "concept_nodes": len(concept_nodes),
            "concept_edges": len(concept_edges),
            "concept_reviews": len(concept_reviews),
            "connections": int(connections_payload.get("total_connection_count", 0)),
            "connection_surface": int(connections_payload.get("included_connection_count", 0)),
        },
        "source_families": [{"label": key, "count": family_counts[key]} for key in sorted(family_counts)],
        "source_types": [{"label": key, "count": type_counts[key]} for key in sorted(type_counts)],
        "meta_layer": [
            {"label": key.replace("_", " "), "count": len(load_meta_records(root, [key]))}
            for key in ["theme", "shared_primitive", "tension", "contradiction", "review_item"]
        ],
        "library_tracker": tracker_status,
        "dimension_model_roles": dimension_model_roles,
        "pond_router": pond_router,
        "llm_costs": cost_summary,
        "feed": _filter_thought_surface_payload(
            root,
            read_json(_thought_feed_path(root), default={"count": 0, "thoughts": []}),
        ),
        "top_concepts": _top_concepts_for_overview(root),
        "top_bubbles": _top_bubbles_for_overview(root),
        "top_context_links": _top_context_links_for_overview(root),
        "top_semantic_capsules": _top_semantic_capsules_for_overview(root),
        "connection_summary": {
            "total_connection_count": int(connections_payload.get("total_connection_count", 0)),
            "included_connection_count": int(connections_payload.get("included_connection_count", 0)),
            "max_connections": int(connections_payload.get("max_connections", 0)),
            "truncated": bool(connections_payload.get("truncated", False)),
        },
        "top_connections": _top_connections_for_overview(root),
    }
