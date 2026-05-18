from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import subprocess
import textwrap
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .models import ChunkDimensionProfile, DimensionRun, DimensionSpec
from .storage import make_id, read_json, read_jsonl, repo_root_from, utc_now, write_json, write_jsonl


DEFAULT_TEXT_GLOBS = ["*.md", "*.markdown", "*.txt", "*.json"]
TEXT_COLUMN_HINTS = {
    "title",
    "name",
    "content",
    "text",
    "body",
    "message",
    "messages",
    "summary",
    "transcript",
    "note",
    "notes",
    "knowledge",
    "payload",
    "json",
    "context",
    "conversation",
    "history",
}
SQLITE_TABLE_EXCLUDES = ("sqlite_", "embedding", "vector", "fts", "cache")
RAW_ITEM_KEY = "_raw_items"
GOVERNANCE_STATUSES = {
    "active",
    "background",
    "downweighted",
    "exclude_from_bubbles",
    "exclude_from_concepts",
    "exclude_from_runtime",
    "archived",
}
GOVERNANCE_FLAG_FIELDS = (
    "include_in_runtime",
    "include_in_bubbles",
    "include_in_concepts",
    "include_in_long_form",
)
GOVERNANCE_TEXT_FIELDS = (
    "governance_status",
    "semantic_role",
    "normalization_profile",
    "notes",
)
CHUNK_GOVERNANCE_EXTRA_FIELDS = ("dimension_overlays",)
LOW_SIGNAL_LABELS = {
    "you said",
    "label",
    "source",
    "text",
    "uploaded image",
    "refresh",
    "current url",
}
TRANSCRIPT_MARKERS = (
    "user:",
    "assistant:",
    "system:",
    "you said",
    "assistant said",
    "user said",
    "<heartbeat>",
    "# in app browser",
)
METADATA_MARKERS = (
    "source_ref",
    "source_type",
    "source_family",
    "remote_host",
    "relative_path",
    "row_id",
    "db_path",
    "path_name",
    "session_id",
    "automation_id",
    "artifact_refs",
    "current_time_iso",
)
PROFILE_MARKERS = (
    "preference",
    "preferences",
    "likes",
    "dislikes",
    "taste",
    "profile",
    "user model",
    "talha",
)
CURATION_CLASS_ORDER = [
    "transcript_residue",
    "ui_label_residue",
    "metadata_residue",
    "scaffolding_residue",
    "profile_residue",
    "boilerplate_residue",
]
RUNTIME_STAGE_SEQUENCE = [
    "analysis_units",
    "conversation_deltas",
    "meta_layer",
    "conversation_threads",
    "thread_abstractions",
    "conversation_concepts",
    "concept_nodes",
    "context_bubbles",
    "knowledge_layer",
    "connections",
]


def _config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "library_sources.json"


def _state_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "library_tracker_state.json"


def _governance_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "library_governance.json"


def _dimension_registry_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "dimensions.json"


def _pond_matrix_path(root: Path) -> Path:
    return root / "memory" / "indexes" / "pond_matrix.json"


def _chunk_dimension_profiles_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "dimensions" / "chunk_dimension_profiles.jsonl"


def _dimension_runs_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "dimensions" / "dimension_runs.json"


def _default_library_sources() -> Dict[str, Any]:
    home = Path.home()
    workspace = home / ".openclaw" / "workspace"
    return {
        "version": 1,
        "sources": [
            {
                "source_id": "chat_converter_saved_conversations",
                "kind": "filesystem",
                "enabled": True,
                "remote_host": "talha@192.168.0.102",
                "source_type": "chat_converter_conversation",
                "source_family": "chat_converter",
                "roots": ["/home/talha/apps/chat_converter/output"],
                "include_globs": ["*.md", "*.markdown", "*.txt"],
            },
            {
                "source_id": "openclaw_workspace_histories",
                "kind": "filesystem",
                "enabled": True,
                "remote_host": "talha@192.168.0.102",
                "source_type": "openclaw_conversation",
                "source_family": "openclaw_conversations",
                "roots": [
                    "/home/talha/.openclaw/workspace/transcripts",
                    "/home/talha/.openclaw/workspace/casts",
                    "/home/talha/.openclaw/workspace/brain-vomits/entries",
                    "/home/talha/.openclaw/workspace/brain-vomits/inputs/raw-transcripts",
                    "/home/talha/.openclaw/workspace/brain-vomits/discovery/transcripts",
                    "/home/talha/.openclaw/workspace/meta-observatory/artifacts/session_packets",
                    "/home/talha/.openclaw/workspace/meta-observatory/artifacts/decision_attachments",
                    "/home/talha/.openclaw/workspace/meta-observatory/artifacts/session_syntheses",
                    "/home/talha/.openclaw/workspace/meta-observatory/artifacts/fragment_observations",
                    "/home/talha/.openclaw/workspace/containers/thought-tube/knowledge",
                ],
                "include_globs": DEFAULT_TEXT_GLOBS,
            },
            {
                "source_id": "openclaw_memory_db",
                "kind": "sqlite",
                "enabled": True,
                "remote_host": "talha@192.168.0.102",
                "source_type": "openclaw_memory_record",
                "source_family": "openclaw_memory",
                "db_paths": [
                    "/home/talha/.openclaw/memory/main.sqlite",
                ],
                "exclude_tables": ["embeddings", "vectors", "cache"],
            },
            {
                "source_id": "server_content",
                "kind": "filesystem",
                "enabled": True,
                "remote_host": "talha@192.168.0.102",
                "source_type": "server_content",
                "source_family": "server_content",
                "roots": [
                    "/home/talha/.openclaw/workspace/.thought-tube/seeds/active",
                    "/home/talha/.openclaw/workspace/.thought-tube/seeds/archive",
                    "/home/talha/.openclaw/workspace/.thought-tube/backend/sessions",
                    "/home/talha/.openclaw/workspace/containers/thought-tube/legacy_sources",
                    "/home/talha/.openclaw/workspace/containers/thought-tube/session_context",
                ],
                "include_globs": DEFAULT_TEXT_GLOBS,
                "notes": "Add any extra server roots here.",
            },
        ],
    }


def ensure_library_tracker_bootstrap(root: Path) -> Path:
    path = _config_path(root)
    if not path.exists():
        write_json(path, _default_library_sources())
    return path


def load_library_tracker_config(root: Path) -> Dict[str, Any]:
    ensure_library_tracker_bootstrap(root)
    return read_json(_config_path(root), default=_default_library_sources())


def _default_state() -> Dict[str, Any]:
    return {
        "updated_at": None,
        "tracked_items": [],
        "last_scan": None,
        "last_sync": None,
    }


def _default_governance() -> Dict[str, Any]:
    return {
        "version": 1,
        "updated_at": None,
        "source_policies": [],
        "family_policies": [],
        "chunk_policies": [],
        "chunk_links": [],
        "prune_actions": [],
        "pending_rederive": None,
        "last_applied_rederive": None,
    }


def _default_dimension_specs() -> List[DimensionSpec]:
    return [
        DimensionSpec(
            dimension_id="primary_pond",
            label="Primary Pond",
            description="Dominant bounded project or domain basin that should contain the chunk.",
            applies_to=["chunk", "source"],
            derive_mode="heuristic",
            comparison_strategy="exact",
            search_weight_default=1.1,
            attributes={"kind": "boundary", "owner": "library_tracker"},
        ),
        DimensionSpec(
            dimension_id="pond_layer",
            label="Pond Layer",
            description="Specific layer(s) inside the routed pond that the chunk materially touches.",
            applies_to=["chunk"],
            derive_mode="heuristic",
            comparison_strategy="overlap",
            search_weight_default=0.95,
            attributes={"kind": "boundary", "owner": "library_tracker"},
        ),
        DimensionSpec(
            dimension_id="source_family",
            label="Source Family",
            description="Library source family for structural provenance and filtering.",
            applies_to=["chunk", "source"],
            derive_mode="deterministic",
            comparison_strategy="exact",
            search_weight_default=0.35,
            attributes={"kind": "structural", "owner": "library_tracker"},
        ),
        DimensionSpec(
            dimension_id="source_type",
            label="Source Type",
            description="Normalized source type describing the substrate origin.",
            applies_to=["chunk", "source"],
            derive_mode="deterministic",
            comparison_strategy="exact",
            search_weight_default=0.3,
            attributes={"kind": "structural", "owner": "library_tracker"},
        ),
        DimensionSpec(
            dimension_id="semantic_role",
            label="Semantic Role",
            description="High-level role of the source or chunk within the knowledge ocean.",
            applies_to=["chunk", "source"],
            derive_mode="heuristic",
            comparison_strategy="exact",
            search_weight_default=0.75,
            allowed_values=["conversation", "memory", "reference", "scaffolding", "source"],
            attributes={"kind": "semantic", "owner": "library_tracker"},
        ),
        DimensionSpec(
            dimension_id="normalization_profile",
            label="Normalization Profile",
            description="Cleaning mode applied to the runtime chunk view before reasoning.",
            applies_to=["chunk", "source"],
            derive_mode="deterministic",
            comparison_strategy="exact",
            search_weight_default=0.25,
            allowed_values=["default", "raw", "strict", "aggressive", "off", "verbatim"],
            attributes={"kind": "runtime", "owner": "library_tracker"},
        ),
        DimensionSpec(
            dimension_id="section_path",
            label="Section Path",
            description="Document or conversation section ancestry for local structural linking.",
            applies_to=["chunk"],
            derive_mode="deterministic",
            comparison_strategy="path_overlap",
            search_weight_default=0.4,
            attributes={"kind": "structural", "owner": "library_tracker"},
        ),
        DimensionSpec(
            dimension_id="collection_tags",
            label="Collection Tags",
            description="Operator-assigned collection tags used for curation and bundle shaping.",
            applies_to=["chunk", "source"],
            derive_mode="manual",
            comparison_strategy="overlap",
            search_weight_default=0.6,
            attributes={"kind": "governance", "owner": "library_tracker"},
        ),
        DimensionSpec(
            dimension_id="intent_family",
            label="Intent Family",
            description="Primary intent cluster expressed by a chunk after semantic enrichment.",
            applies_to=["chunk"],
            derive_mode="assisted",
            requires_model=True,
            preferred_role="dimension_local_semantic",
            fallback_mode="heuristic",
            comparison_strategy="semantic_overlap",
            search_weight_default=0.95,
            attributes={"kind": "semantic", "owner": "dimension_engine"},
        ),
        DimensionSpec(
            dimension_id="tension_family",
            label="Tension Family",
            description="Dominant tension or unresolved pressure carried by a chunk.",
            applies_to=["chunk"],
            derive_mode="assisted",
            requires_model=True,
            preferred_role="dimension_local_semantic",
            fallback_mode="heuristic",
            comparison_strategy="semantic_overlap",
            search_weight_default=0.9,
            attributes={"kind": "semantic", "owner": "dimension_engine"},
        ),
        DimensionSpec(
            dimension_id="project_lens",
            label="Project Lens",
            description="Project or build lens through which a chunk should be interpreted.",
            applies_to=["chunk"],
            derive_mode="assisted",
            requires_model=True,
            preferred_role="dimension_local_semantic",
            fallback_mode="heuristic",
            comparison_strategy="semantic_overlap",
            search_weight_default=0.8,
            attributes={"kind": "semantic", "owner": "dimension_engine"},
        ),
        DimensionSpec(
            dimension_id="evidence_posture",
            label="Evidence Posture",
            description="Whether a chunk is presenting direct evidence, synthesis, speculation, or scaffolding.",
            applies_to=["chunk"],
            derive_mode="assisted",
            requires_model=True,
            preferred_role="dimension_local_fast",
            fallback_mode="heuristic",
            comparison_strategy="exact",
            search_weight_default=0.7,
            allowed_values=["evidence", "synthesis", "speculation", "instruction", "scaffolding"],
            attributes={"kind": "semantic", "owner": "dimension_engine"},
        ),
    ]


def _default_dimension_registry() -> Dict[str, Any]:
    return {
        "version": 1,
        "updated_at": None,
        "dimensions": [spec.to_dict() for spec in _default_dimension_specs()],
    }


def _coerce_dimension_spec(row: Dict[str, Any] | None) -> DimensionSpec | None:
    payload = dict(row or {})
    dimension_id = str(payload.get("dimension_id", "")).strip()
    label = str(payload.get("label", "")).strip()
    description = str(payload.get("description", "")).strip()
    applies_to = [str(value).strip() for value in payload.get("applies_to", []) if str(value).strip()]
    if not dimension_id or not label or not description or not applies_to:
        return None
    return DimensionSpec(
        dimension_id=dimension_id,
        label=label,
        description=description,
        applies_to=applies_to,
        derive_mode=str(payload.get("derive_mode", "deterministic")).strip() or "deterministic",
        enabled=bool(payload.get("enabled", True)),
        requires_model=bool(payload.get("requires_model", False)),
        preferred_role=str(payload.get("preferred_role", "")).strip(),
        fallback_mode=str(payload.get("fallback_mode", "deterministic")).strip() or "deterministic",
        comparison_strategy=str(payload.get("comparison_strategy", "overlap")).strip() or "overlap",
        search_weight_default=float(payload.get("search_weight_default", 1.0)),
        cache_version=str(payload.get("cache_version", "v1")).strip() or "v1",
        allowed_values=[
            str(value).strip()
            for value in payload.get("allowed_values", [])
            if str(value).strip()
        ],
        attributes=dict(payload.get("attributes", {})),
    )


def ensure_dimension_registry_bootstrap(root: Path) -> Path:
    path = _dimension_registry_path(root)
    if not path.exists():
        write_json(path, _default_dimension_registry())
    return path


def load_dimension_registry(root: Path) -> Dict[str, Any]:
    path = ensure_dimension_registry_bootstrap(root)
    payload = read_json(path, default=_default_dimension_registry()) or {}
    merged_specs: Dict[str, Dict[str, Any]] = {
        spec.dimension_id: spec.to_dict()
        for spec in _default_dimension_specs()
    }
    order = list(merged_specs.keys())
    for row in payload.get("dimensions", []):
        spec = _coerce_dimension_spec(row)
        if spec is None:
            continue
        base = merged_specs.get(spec.dimension_id, {})
        merged_specs[spec.dimension_id] = {**base, **spec.to_dict()}
        if spec.dimension_id not in order:
            order.append(spec.dimension_id)
    dimensions = [merged_specs[dimension_id] for dimension_id in order]
    return {
        "version": int(payload.get("version", 1)),
        "updated_at": payload.get("updated_at"),
        "registry_path": str(path),
        "dimension_ids": order,
        "dimensions": dimensions,
        "dimension_map": {
            row["dimension_id"]: row
            for row in dimensions
        },
    }


def _profile_id_for(chunk_id: str, dimension_id: str) -> str:
    return f"chunk-dimension-{_content_hash(f'{chunk_id}:{dimension_id}')[:12]}"


POND_STOPWORDS = {
    "a",
    "an",
    "and",
    "anti",
    "as",
    "by",
    "core",
    "cognitive",
    "domain",
    "first",
    "for",
    "general",
    "how",
    "in",
    "into",
    "is",
    "layer",
    "layers",
    "local",
    "of",
    "on",
    "or",
    "overall",
    "private",
    "project",
    "reason",
    "research",
    "the",
    "to",
    "v1",
    "within",
}


def _pond_tokens(value: Any) -> List[str]:
    text = str(value or "").lower()
    text = text.replace("/", " ").replace("-", " ").replace("_", " ")
    return [
        token
        for token in re.findall(r"[a-z0-9]+", text)
        if len(token) > 2 and token not in POND_STOPWORDS
    ]


def _load_pond_matrix(root: Path) -> Dict[str, Any]:
    path = _pond_matrix_path(root)
    if not path.exists():
        fallback = repo_root_from(Path(__file__)) / "memory" / "indexes" / "pond_matrix.json"
        if fallback.exists():
            path = fallback
    return read_json(path, default={"ponds": {}, "metadata": {}}) or {"ponds": {}, "metadata": {}}


def _pond_routing_payload(root: Path, row: Dict[str, Any]) -> Dict[str, Any]:
    matrix = _load_pond_matrix(root)
    pond_rows = matrix.get("ponds", {}) or {}
    if not pond_rows:
        return {}
    try:
        from .product_inner_world import classify_assisted_pond_route, get_pond_router_status
    except Exception:
        classify_assisted_pond_route = None
        get_pond_router_status = None
    router_status = get_pond_router_status(root) if get_pond_router_status is not None else {
        "enabled": True,
        "mode": "heuristic",
        "assisted_on_ambiguity": True,
        "ambiguity_threshold": 0.72,
        "router_version": "v1",
        "local_role_id": "pond_router_local",
        "judge_role_id": "pond_router_judge",
    }
    mode = str(router_status.get("mode", "heuristic")).strip().lower() or "heuristic"
    if not bool(router_status.get("enabled", True)) or mode in {"off", "manual_only"}:
        return {}
    text_parts = [
        row.get("title", ""),
        row.get("content", ""),
        row.get("source_ref", ""),
        row.get("source_type", ""),
        row.get("source_family", ""),
        row.get("semantic_role", ""),
        " ".join(row.get("section_path", []) or []),
        " ".join(row.get("collection_tags", []) or []),
        " ".join(str(value) for value in row.get("metadata_dimensions", {}).values() if value),
    ]
    source_text = " ".join(part for part in text_parts if part).strip()
    if not source_text:
        return {}
    token_counts = Counter(_pond_tokens(source_text))
    if not token_counts:
        return {}

    pond_scores: Dict[str, float] = {}
    pond_matches: Dict[str, Dict[str, Any]] = {}
    for pond_id, pond in pond_rows.items():
        anchor_tokens = set(
            _pond_tokens(pond_id)
            + _pond_tokens(pond_id.removeprefix("project_"))
            + _pond_tokens(pond_id.removeprefix("domain_"))
        )
        description_tokens = set(_pond_tokens(pond.get("description", "")))
        layer_scores: Dict[str, float] = {}
        matched_tokens: set[str] = set()
        score = 0.0
        for token in anchor_tokens:
            if token_counts.get(token):
                score += 6.0
                matched_tokens.add(token)
        for token in description_tokens:
            if token_counts.get(token):
                score += 1.5
                matched_tokens.add(token)
        for layer in pond.get("layers", []) or []:
            layer_token_overlap = sorted({token for token in _pond_tokens(layer) if token_counts.get(token)})
            if layer_token_overlap:
                layer_score = 3.0 * len(layer_token_overlap)
                layer_scores[str(layer)] = round(layer_score, 3)
                score += layer_score
                matched_tokens.update(layer_token_overlap)
        if score <= 0:
            continue
        pond_scores[pond_id] = round(score, 3)
        pond_matches[pond_id] = {
            "matched_tokens": sorted(matched_tokens),
            "layer_scores": layer_scores,
        }

    if not pond_scores:
        if mode in {"assisted", "hybrid"} and classify_assisted_pond_route is not None:
            assisted = classify_assisted_pond_route(
                root,
                row=row,
                pond_matrix=matrix,
                preferred_role=str(router_status.get("local_role_id", "pond_router_local")).strip() or "pond_router_local",
            )
            if assisted:
                return {
                    "primary_pond": assisted["primary_pond"],
                    "secondary_ponds": [],
                    "touched_layers": assisted.get("touched_layers", []),
                    "touch_confidence_score": round(float(assisted.get("confidence", 0.65)), 3),
                    "routing_justification": assisted.get("justification", ""),
                    "routing_method": "assisted",
                    "router_version": str(router_status.get("router_version", "v1")).strip() or "v1",
                    "model_role": str(assisted.get("model_role", "")).strip(),
                    "model_signature": str(assisted.get("model_signature", "")).strip(),
                }
        return {}
    primary_pond = max(
        pond_scores,
        key=lambda pond_id: (
            pond_scores[pond_id],
            len(pond_matches.get(pond_id, {}).get("layer_scores", {})),
            pond_id,
        ),
    )
    primary_score = pond_scores[primary_pond]
    if primary_score < 6.0:
        if mode in {"assisted", "hybrid"} and classify_assisted_pond_route is not None:
            assisted = classify_assisted_pond_route(
                root,
                row=row,
                pond_matrix=matrix,
                preferred_role=str(router_status.get("judge_role_id", "")).strip()
                or str(router_status.get("local_role_id", "pond_router_local")).strip()
                or "pond_router_local",
            )
            if assisted:
                return {
                    "primary_pond": assisted["primary_pond"],
                    "secondary_ponds": [],
                    "touched_layers": assisted.get("touched_layers", []),
                    "touch_confidence_score": round(float(assisted.get("confidence", 0.65)), 3),
                    "routing_justification": assisted.get("justification", ""),
                    "routing_method": "assisted",
                    "router_version": str(router_status.get("router_version", "v1")).strip() or "v1",
                    "model_role": str(assisted.get("model_role", "")).strip(),
                    "model_signature": str(assisted.get("model_signature", "")).strip(),
                }
        return {}
    secondary_ponds = [
        pond_id
        for pond_id, score in sorted(
            pond_scores.items(),
            key=lambda item: (-item[1], item[0]),
        )
        if pond_id != primary_pond and score >= max(6.0, primary_score * 0.65)
    ]
    touched_layers = [
        layer
        for layer, _ in sorted(
            pond_matches[primary_pond]["layer_scores"].items(),
            key=lambda item: (-item[1], item[0]),
        )
    ]
    route = {
        "primary_pond": primary_pond,
        "secondary_ponds": secondary_ponds,
        "touched_layers": touched_layers,
        "touch_confidence_score": round(min(0.99, 0.45 + (primary_score / 24.0)), 3),
        "routing_justification": (
            f"Matched pond {primary_pond} via tokens "
            f"{', '.join(pond_matches[primary_pond]['matched_tokens'][:8])}"
            + (
                f"; touched layers: {', '.join(touched_layers[:4])}"
                if touched_layers else ""
            )
        ),
    }
    route["routing_method"] = "heuristic"
    route["router_version"] = str(router_status.get("router_version", "v1")).strip() or "v1"
    route["model_role"] = ""
    route["model_signature"] = ""
    ambiguity_threshold = float(router_status.get("ambiguity_threshold", 0.72) or 0.72)
    ambiguous = (
        bool(secondary_ponds)
        or not touched_layers
        or float(route["touch_confidence_score"]) < ambiguity_threshold
    )
    should_assist = (
        mode == "assisted"
        or (mode == "hybrid" and bool(router_status.get("assisted_on_ambiguity", True)) and ambiguous)
    )
    if should_assist and classify_assisted_pond_route is not None:
        preferred_role = (
            str(router_status.get("judge_role_id" if ambiguous else "local_role_id", "")).strip()
            or str(router_status.get("local_role_id", "pond_router_local")).strip()
            or "pond_router_local"
        )
        assisted = classify_assisted_pond_route(
            root,
            row=row,
            pond_matrix=matrix,
            preferred_role=preferred_role,
        )
        if assisted:
            return {
                "primary_pond": assisted["primary_pond"],
                "secondary_ponds": [] if assisted["primary_pond"] == route["primary_pond"] else secondary_ponds,
                "touched_layers": assisted.get("touched_layers", []),
                "touch_confidence_score": round(float(assisted.get("confidence", route["touch_confidence_score"])), 3),
                "routing_justification": assisted.get("justification", "") or route["routing_justification"],
                "routing_method": "assisted",
                "router_version": route["router_version"],
                "model_role": str(assisted.get("model_role", "")).strip(),
                "model_signature": str(assisted.get("model_signature", "")).strip(),
            }
    return route


def _load_library_tracker_state(root: Path) -> Dict[str, Any]:
    return read_json(_state_path(root), default=_default_state())


def _save_library_tracker_state(root: Path, payload: Dict[str, Any]) -> None:
    write_json(_state_path(root), payload)


def ensure_library_governance_bootstrap(root: Path) -> Path:
    path = _governance_path(root)
    if not path.exists():
        write_json(path, _default_governance())
    return path


def load_library_governance(root: Path) -> Dict[str, Any]:
    path = ensure_library_governance_bootstrap(root)
    payload = read_json(path, default=_default_governance()) or {}
    merged = _default_governance()
    merged["version"] = int(payload.get("version", merged["version"]))
    merged["updated_at"] = payload.get("updated_at")
    merged["source_policies"] = list(payload.get("source_policies", []))
    merged["family_policies"] = list(payload.get("family_policies", []))
    merged["chunk_policies"] = list(payload.get("chunk_policies", []))
    merged["chunk_links"] = list(payload.get("chunk_links", []))
    merged["prune_actions"] = list(payload.get("prune_actions", []))
    merged["pending_rederive"] = payload.get("pending_rederive")
    merged["last_applied_rederive"] = payload.get("last_applied_rederive")
    merged["governance_path"] = str(path)
    return merged


def _save_library_governance(root: Path, payload: Dict[str, Any]) -> None:
    path = ensure_library_governance_bootstrap(root)
    write_json(path, payload)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_title(value: str) -> str:
    return value.replace("-", " ").replace("_", " ").strip() or "Untitled source"


def _item_summary(item: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source_ref": item["source_ref"],
        "title": item["title"],
        "fingerprint": item["fingerprint"],
        "adapter_id": item["adapter_id"],
        "source_type": item["source_type"],
        "source_family": item["source_family"],
        "metadata": item.get("metadata", {}),
    }


def _state_item(item: Dict[str, Any], seen_at: str) -> Dict[str, Any]:
    payload = _item_summary(item)
    payload["last_seen_at"] = seen_at
    return payload


def _normalize_collection_tags(values: Iterable[str] | None) -> List[str]:
    tags = []
    for value in values or []:
        text = str(value).strip()
        if text:
            tags.append(text)
    return sorted(set(tags))


def _policy_defaults_for_status(status: str) -> Dict[str, bool]:
    if status == "background":
        return {
            "include_in_runtime": True,
            "include_in_bubbles": False,
            "include_in_concepts": False,
            "include_in_long_form": False,
        }
    if status == "exclude_from_bubbles":
        return {
            "include_in_runtime": True,
            "include_in_bubbles": False,
            "include_in_concepts": True,
            "include_in_long_form": True,
        }
    if status == "exclude_from_concepts":
        return {
            "include_in_runtime": True,
            "include_in_bubbles": True,
            "include_in_concepts": False,
            "include_in_long_form": True,
        }
    if status == "exclude_from_runtime" or status == "archived":
        return {
            "include_in_runtime": False,
            "include_in_bubbles": False,
            "include_in_concepts": False,
            "include_in_long_form": False,
        }
    return {
        "include_in_runtime": True,
        "include_in_bubbles": True,
        "include_in_concepts": True,
        "include_in_long_form": True,
    }


def _infer_semantic_role(source_row: Dict[str, Any]) -> str:
    metadata = source_row.get("metadata", {})
    explicit = str(metadata.get("semantic_role", "")).strip()
    if explicit:
        return explicit
    hay = " ".join(
        [
            str(source_row.get("source_type", "")),
            str(source_row.get("source_family", "")),
            str(source_row.get("source_ref", "")),
            str(metadata.get("root", "")),
        ]
    ).lower()
    if "meta-observatory" in hay or "session_packet" in hay or "session_synthes" in hay:
        return "scaffolding"
    if "conversation" in hay or "transcript" in hay or "chat_converter" in hay:
        return "conversation"
    if "memory" in hay:
        return "memory"
    if "knowledge" in hay or "seed" in hay or "legacy_sources" in hay:
        return "reference"
    return "source"


def _governance_patch(record: Dict[str, Any] | None) -> Dict[str, Any]:
    if not record:
        return {}
    patch: Dict[str, Any] = {}
    for key in GOVERNANCE_TEXT_FIELDS:
        value = record.get(key)
        if value not in (None, ""):
            patch[key] = value
    for key in GOVERNANCE_FLAG_FIELDS:
        if key in record and record.get(key) is not None:
            patch[key] = bool(record[key])
    if record.get("collection_tags"):
        patch["collection_tags"] = _normalize_collection_tags(record.get("collection_tags", []))
    return patch


def _family_policy_map(governance: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        row["source_family"]: row
        for row in governance.get("family_policies", [])
        if row.get("source_family")
    }


def _source_policy_map(governance: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        row["source_ref"]: row
        for row in governance.get("source_policies", [])
        if row.get("source_ref")
    }


def _chunk_policy_map(governance: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        row["chunk_id"]: row
        for row in governance.get("chunk_policies", [])
        if row.get("chunk_id")
    }


def _canonical_chunk_pair(chunk_id: str, other_chunk_id: str) -> tuple[str, str]:
    return tuple(sorted([chunk_id, other_chunk_id]))


def _normalize_dimension_overlays(values: Dict[str, Any] | None) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    for raw_key, raw_value in (values or {}).items():
        key = str(raw_key).strip()
        if not key:
            continue
        if isinstance(raw_value, (list, tuple, set)):
            items = [str(item).strip() for item in raw_value if str(item).strip()]
            if items:
                normalized[key] = sorted(dict.fromkeys(items))
            continue
        text = str(raw_value).strip()
        if text:
            normalized[key] = text
    return normalized


def _chunk_governance_patch(record: Dict[str, Any] | None) -> Dict[str, Any]:
    patch = _governance_patch(record)
    if record and record.get("dimension_overlays"):
        patch["dimension_overlays"] = _normalize_dimension_overlays(record.get("dimension_overlays"))
    return patch


def _manual_chunk_link_map(governance: Dict[str, Any]) -> Dict[str, set[str]]:
    links: Dict[str, set[str]] = {}
    for row in governance.get("chunk_links", []):
        left = str(row.get("chunk_id", "")).strip()
        right = str(row.get("other_chunk_id", "")).strip()
        if not left or not right or left == right:
            continue
        links.setdefault(left, set()).add(right)
        links.setdefault(right, set()).add(left)
    return links


def _dimension_values(value: Any) -> List[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip() if value not in (None, "") else ""
    return [text] if text else []


def _project_lens_values(row: Dict[str, Any]) -> List[str]:
    metadata_dimensions = row.get("metadata_dimensions", {})
    direct = metadata_dimensions.get("project_lens")
    if direct not in (None, "", [], {}):
        return _dimension_values(direct)
    for key in ("project_lens_keys", "project_lenses", "lens_keys"):
        values = _dimension_values(metadata_dimensions.get(key))
        if values:
            return values
    return []


def _intent_family_values(row: Dict[str, Any]) -> List[str]:
    try:
        from .operators import _detect_dimensions
    except Exception:
        return []
    text = " ".join(
        [
            str(row.get("title", "")),
            str(row.get("content", "")),
            " ".join(str(value) for value in row.get("collection_tags", [])),
        ]
    )
    dimensions = [str(value).strip() for value in _detect_dimensions(text) if str(value).strip()]
    return dimensions[:3]


def _tension_family_values(row: Dict[str, Any]) -> List[str]:
    try:
        from .operators import _detect_tensions
    except Exception:
        return []
    text = " ".join(
        [
            str(row.get("title", "")),
            str(row.get("content", "")),
        ]
    )
    tensions = _detect_tensions(text)
    markers = [str(item.get("marker", "")).strip() for item in tensions if str(item.get("marker", "")).strip()]
    return markers[:4]


def _project_lens_heuristic_values(root: Path, row: Dict[str, Any]) -> List[str]:
    current = _project_lens_values(row)
    if current:
        return current
    try:
        from .thread_abstractions import load_project_lenses
    except Exception:
        return []
    text = " ".join(
        [
            str(row.get("title", "")),
            str(row.get("content", "")),
            " ".join(str(value) for value in row.get("collection_tags", [])),
        ]
    ).lower()
    scored: List[tuple[int, str]] = []
    for lens in load_project_lenses(root):
        keywords = [str(value).strip().lower() for value in lens.get("keywords", []) if str(value).strip()]
        if not keywords:
            continue
        hits = sum(1 for keyword in keywords if keyword in text)
        if hits:
            scored.append((hits, str(lens.get("lens_key", "")).strip()))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [lens_key for _, lens_key in scored[:3] if lens_key]


def _evidence_posture_values(row: Dict[str, Any]) -> List[str]:
    metadata_dimensions = row.get("metadata_dimensions", {})
    direct = _dimension_values(metadata_dimensions.get("evidence_posture"))
    if direct:
        return direct
    semantic_role = str(row.get("semantic_role", "")).strip().lower()
    content_kind = str(row.get("content_kind", "")).strip().lower()
    curation_classes = set(row.get("curation_classes", []))
    if "scaffolding_residue" in curation_classes or semantic_role == "scaffolding":
        return ["scaffolding"]
    if content_kind in {"quote", "citation", "reference"} or semantic_role == "reference":
        return ["evidence"]
    if content_kind in {"summary", "article", "note"} or semantic_role == "memory":
        return ["synthesis"]
    if content_kind in {"instruction", "task", "todo"}:
        return ["instruction"]
    if content_kind in {"message", "line", "bullet"} or semantic_role == "conversation":
        return ["speculation"]
    return []


def _dimension_profile_payload(
    root: Path,
    row: Dict[str, Any],
    spec: Dict[str, Any],
) -> Dict[str, Any] | None:
    dimension_id = spec["dimension_id"]
    metadata_dimensions = row.get("metadata_dimensions", {})
    values: List[str] = []
    method = str(spec.get("derive_mode", "deterministic")).strip() or "deterministic"
    evidence = [f"dimension:{dimension_id}"]
    assisted_payload: Dict[str, Any] | None = None

    if dimension_id == "source_family":
        values = _dimension_values(row.get("source_family", metadata_dimensions.get("source_family")))
    elif dimension_id == "source_type":
        values = _dimension_values(row.get("source_type", metadata_dimensions.get("source_type")))
    elif dimension_id == "semantic_role":
        values = _dimension_values(row.get("semantic_role", metadata_dimensions.get("semantic_role")))
        method = "heuristic"
    elif dimension_id == "normalization_profile":
        values = _dimension_values(row.get("normalization_profile", metadata_dimensions.get("normalization_profile")))
    elif dimension_id == "section_path":
        values = _dimension_values(metadata_dimensions.get("section_path", row.get("section_path", [])))
    elif dimension_id == "collection_tags":
        values = _dimension_values(row.get("collection_tags", metadata_dimensions.get("collection_tags", [])))
        method = "manual"
    elif dimension_id == "project_lens":
        values = _project_lens_heuristic_values(root, row)
        if values:
            method = "heuristic"
    elif dimension_id == "intent_family":
        values = _intent_family_values(row)
        if values:
            method = "heuristic"
    elif dimension_id == "tension_family":
        values = _tension_family_values(row)
        if values:
            method = "heuristic"
    elif dimension_id == "evidence_posture":
        if spec.get("requires_model", False):
            try:
                from .product_inner_world import classify_assisted_dimension
            except Exception:
                classify_assisted_dimension = None
            if classify_assisted_dimension is not None:
                assisted_payload = classify_assisted_dimension(
                    root,
                    dimension_id=dimension_id,
                    row=row,
                    preferred_role=str(spec.get("preferred_role", "")).strip(),
                    allowed_values=list(spec.get("allowed_values", [])),
                )
            if assisted_payload:
                values = _dimension_values(assisted_payload.get("value"))
                method = "assisted"
                evidence.append(f"assisted:{assisted_payload.get('model_role', '')}")
        if method != "assisted":
            values = _evidence_posture_values(row)
            if values:
                method = "heuristic"
    else:
        values = _dimension_values(metadata_dimensions.get(dimension_id))
        if values and method == "assisted":
            method = "manual" if row.get("dimension_overlays", {}).get(dimension_id) else "heuristic"

    values = [value for value in values if value]
    if not values:
        return None
    unique_values = sorted(dict.fromkeys(values))
    return ChunkDimensionProfile(
        profile_id=_profile_id_for(row["chunk_id"], dimension_id),
        chunk_id=row["chunk_id"],
        source_ref=row.get("source_ref", ""),
        dimension_id=dimension_id,
        primary_value=unique_values[0],
        normalized_values=unique_values,
        confidence=(
            float(assisted_payload.get("confidence", 0.6))
            if assisted_payload and method == "assisted"
            else 0.95 if method == "deterministic"
            else 0.75 if method == "heuristic"
            else 1.0 if method == "manual"
            else 0.6
        ),
        method=method,
        version=str(spec.get("cache_version", "v1")),
        updated_at=utc_now(),
        evidence=evidence,
        model_role=str(assisted_payload.get("model_role", "")).strip() if assisted_payload and method == "assisted" else "",
        model_signature=str(assisted_payload.get("model_signature", "")).strip() if assisted_payload and method == "assisted" else "",
        attributes={
            "label": spec.get("label", dimension_id),
            "comparison_strategy": spec.get("comparison_strategy", "overlap"),
            "requires_model": bool(spec.get("requires_model", False)),
            "assisted_rationale": str(assisted_payload.get("rationale", "")).strip() if assisted_payload and method == "assisted" else "",
        },
    ).to_dict()


def derive_chunk_dimension_profiles(
    root: Path,
    chunk_rows: List[Dict[str, Any]] | None = None,
    *,
    governance: Dict[str, Any] | None = None,
    registry: Dict[str, Any] | None = None,
    persist: bool = True,
) -> Dict[str, Any]:
    if chunk_rows is None:
        chunk_rows = resolve_governed_chunk_rows(root, governance=governance)
    registry = registry or load_dimension_registry(root)
    enabled_specs = [
        row for row in registry.get("dimensions", [])
        if row.get("enabled", True)
    ]
    profiles: List[Dict[str, Any]] = []
    per_dimension_counts = Counter()
    covered_chunks: set[str] = set()
    for row in chunk_rows:
        for spec in enabled_specs:
            profile = _dimension_profile_payload(root, row, spec)
            if profile is None:
                continue
            profiles.append(profile)
            per_dimension_counts[profile["dimension_id"]] += 1
            covered_chunks.add(profile["chunk_id"])
    profiles.sort(
        key=lambda row: (
            row.get("chunk_id", ""),
            row.get("dimension_id", ""),
            row.get("primary_value", ""),
        )
    )
    path = _chunk_dimension_profiles_path(root)
    method_counts = Counter(row.get("method", "") for row in profiles if row.get("method"))
    model_roles = sorted(
        {
            row.get("model_role", "")
            for row in profiles
            if row.get("method") == "assisted" and row.get("model_role")
        }
    )
    run = DimensionRun(
        run_id=make_id("dimension-run"),
        dimension_id="all",
        status="completed",
        started_at=utc_now(),
        completed_at=utc_now(),
        chunk_count=len(chunk_rows),
        processed_count=len(profiles),
        skipped_count=0,
        cache_hit_count=0,
        model_roles=model_roles,
        method_counts=dict(method_counts),
        attributes={
            "enabled_dimensions": [row["dimension_id"] for row in enabled_specs],
            "covered_chunk_count": len(covered_chunks),
            "profile_path": str(path),
        },
    ).to_dict()
    if persist:
        write_jsonl(path, profiles)
        write_json(
            _dimension_runs_path(root),
            {
                "last_run": run,
                "history": [run],
            },
        )
    return {
        "profile_path": str(path),
        "profile_count": len(profiles),
        "covered_chunk_count": len(covered_chunks),
        "profiles": profiles,
        "per_dimension_counts": dict(per_dimension_counts),
        "last_run": run,
    }


def load_chunk_dimension_profiles(root: Path, *, refresh: bool = True) -> Dict[str, Any]:
    path = _chunk_dimension_profiles_path(root)
    if refresh or not path.exists():
        return derive_chunk_dimension_profiles(root, persist=True)
    rows = read_jsonl(path)
    run_payload = read_json(_dimension_runs_path(root), default={}) or {}
    per_dimension_counts = Counter(row.get("dimension_id", "") for row in rows if row.get("dimension_id"))
    covered_chunks = {row.get("chunk_id", "") for row in rows if row.get("chunk_id")}
    return {
        "profile_path": str(path),
        "profile_count": len(rows),
        "covered_chunk_count": len(covered_chunks),
        "profiles": rows,
        "per_dimension_counts": dict(per_dimension_counts),
        "last_run": run_payload.get("last_run"),
    }


def match_chunk_dimension_profiles(
    root: Path,
    *,
    query: str = "",
    dimensions: List[str] | None = None,
    dimension_filters: Dict[str, List[str]] | None = None,
    dimension_weights: Dict[str, float] | None = None,
    limit: int | None = None,
) -> Dict[str, Any]:
    from .vault_ingest import tokenize

    registry = load_dimension_registry(root)
    registry_map = registry.get("dimension_map", {})
    selected_dimensions = [
        dimension_id
        for dimension_id in (
            dimensions
            or list((dimension_weights or {}).keys())
            or list((dimension_filters or {}).keys())
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
    weight_overrides = {
        key: float(value)
        for key, value in (dimension_weights or {}).items()
        if key in registry_map
    }
    query_tokens = set(tokenize(query))
    profiles_payload = load_chunk_dimension_profiles(root, refresh=False)
    chunk_profiles: Dict[str, Dict[str, List[Dict]]] = {}
    for row in profiles_payload.get("profiles", []):
        dimension_id = row.get("dimension_id")
        if selected_set and dimension_id not in selected_set:
            continue
        chunk_profiles.setdefault(row.get("chunk_id", ""), {}).setdefault(dimension_id, []).append(row)

    matches: List[Dict[str, Any]] = []
    for chunk_id, profile_map in chunk_profiles.items():
        dimensional_score = 0.0
        matched_dimensions: List[Dict[str, Any]] = []
        filter_hits = 0
        for dimension_id in selected_dimensions:
            profiles = profile_map.get(dimension_id, [])
            if not profiles:
                continue
            configured_weight = weight_overrides.get(
                dimension_id,
                float(registry_map.get(dimension_id, {}).get("search_weight_default", 1.0)),
            )
            query_match_score = 0.0
            filter_match = False
            matched_values: List[str] = []
            expected_values = {
                str(value).strip().lower()
                for value in normalized_dimension_filters.get(dimension_id, [])
                if str(value).strip()
            }
            for profile in profiles:
                values = [str(value).strip() for value in profile.get("normalized_values", []) if str(value).strip()]
                value_text = " ".join(values).lower()
                if query_tokens:
                    query_match_score = max(query_match_score, float(sum(1 for token in query_tokens if token in value_text)))
                lowered_values = {value.lower() for value in values}
                if expected_values and lowered_values.intersection(expected_values):
                    filter_match = True
                if query_match_score > 0 or filter_match:
                    matched_values.extend(values)
            if expected_values and not filter_match:
                continue
            if filter_match:
                filter_hits += 1
            if query and query_match_score <= 0 and not filter_match:
                continue
            dimension_score = configured_weight * query_match_score
            if filter_match:
                dimension_score += configured_weight * 2.0
            dimensional_score += dimension_score
            matched_dimensions.append(
                {
                    "dimension_id": dimension_id,
                    "label": registry_map.get(dimension_id, {}).get("label", dimension_id),
                    "weight": configured_weight,
                    "query_match_score": query_match_score,
                    "filter_match": filter_match,
                    "values": sorted(dict.fromkeys(matched_values))[:12],
                }
            )

        if normalized_dimension_filters and filter_hits < len(normalized_dimension_filters):
            continue
        if query and dimensional_score <= 0:
            continue
        if not query and not normalized_dimension_filters and not matched_dimensions:
            continue
        matches.append(
            {
                "chunk_id": chunk_id,
                "dimensional_score": dimensional_score,
                "matched_dimensions": matched_dimensions,
            }
        )

    matches.sort(
        key=lambda row: (
            -float(row.get("dimensional_score", 0.0)),
            row.get("chunk_id", ""),
        )
    )
    if limit is not None:
        matches = matches[:limit]
    return {
        "count": len(matches),
        "matches": matches,
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
        },
    }


def _semantic_text(row: Dict[str, Any]) -> str:
    return " ".join(
        [
            str(row.get("title", "")),
            str(row.get("content", "")),
            str(row.get("source_ref", "")),
            json.dumps(row.get("metadata", {}), ensure_ascii=False),
        ]
    )


def _chunk_curation_profile(row: Dict[str, Any]) -> Dict[str, Any]:
    text = _semantic_text(row)
    lowered = text.lower()
    title = str(row.get("title", "")).strip().lower()
    content = str(row.get("content", "")).strip()
    content_lower = content.lower()
    title_and_content = " ".join([title, content_lower]).strip()
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{1,}", title_and_content)
    metadata = row.get("metadata", {})
    semantic_role = str(row.get("semantic_role", metadata.get("semantic_role", ""))).strip().lower()
    content_kind = str(row.get("content_kind", "")).strip().lower()
    matches: Dict[str, List[str]] = {}

    transcript_hits = [marker for marker in TRANSCRIPT_MARKERS if marker in title_and_content]
    if transcript_hits:
        matches["transcript_residue"] = transcript_hits

    ui_hits = []
    short_surface = len(content) <= 96 or len(title) <= 48
    for label in LOW_SIGNAL_LABELS:
        if title == label or content_lower == label:
            ui_hits.append(label)
            continue
        if short_surface and (title.startswith(label) or content_lower.startswith(label)):
            ui_hits.append(label)
    if ui_hits:
        matches["ui_label_residue"] = ui_hits

    metadata_hits = [marker for marker in METADATA_MARKERS if marker in title_and_content]
    if metadata_hits and (len(metadata_hits) >= 2 or semantic_role == "scaffolding"):
        matches["metadata_residue"] = metadata_hits

    if semantic_role == "scaffolding" or "meta-observatory" in lowered or "session_packet" in lowered or "session_synthesis" in lowered:
        matches["scaffolding_residue"] = [semantic_role or "scaffolding"]

    profile_hits = [marker for marker in PROFILE_MARKERS if marker in title_and_content]
    strong_profile_hits = [marker for marker in profile_hits if marker != "talha"]
    if strong_profile_hits or ("talha" in profile_hits and len(profile_hits) >= 2):
        matches["profile_residue"] = profile_hits

    is_short = len(content) <= 80
    low_signal_ratio = (sum(1 for token in tokens if token in {"label", "source", "text", "image", "url", "user", "assistant"}) / len(tokens)) if tokens else 0.0
    if is_short and (title in LOW_SIGNAL_LABELS or low_signal_ratio >= 0.35 or (content_kind in {"line", "bullet"} and len(tokens) <= 12)):
        matches["boilerplate_residue"] = [content_kind or "short_text"]

    classes = [name for name in CURATION_CLASS_ORDER if name in matches]
    return {
        "classes": classes,
        "signals": {key: sorted(set(values))[:6] for key, values in matches.items()},
    }


def _source_curation_profile(source_row: Dict[str, Any], chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    class_counter: Counter[str] = Counter()
    class_sources: Dict[str, List[str]] = {}
    for chunk in chunks:
        for name in chunk.get("curation_classes", []):
            class_counter[name] += 1
            for signal in chunk.get("curation_signals", {}).get(name, []):
                class_sources.setdefault(name, [])
                if signal not in class_sources[name]:
                    class_sources[name].append(signal)
    selected: List[str] = []
    threshold = max(1, math.ceil(len(chunks) * 0.3))
    for name in CURATION_CLASS_ORDER:
        if class_counter.get(name, 0) >= threshold:
            selected.append(name)
    if source_row.get("semantic_role") == "scaffolding" and "scaffolding_residue" not in selected:
        selected.append("scaffolding_residue")
    return {
        "classes": selected,
        "signals": {key: values[:6] for key, values in class_sources.items() if key in selected},
        "counts": dict(class_counter),
    }


def _chunk_field_value(field: str, row: Dict[str, Any]) -> Any:
    if field in row:
        return row.get(field)
    if field == "section_path":
        return row.get("section_path", [])
    return row.get("metadata", {}).get(field)


def resolve_governed_chunk_rows(
    root: Path,
    chunk_rows: List[Dict[str, Any]] | None = None,
    *,
    governance: Dict[str, Any] | None = None,
    source_lookup: Dict[str, Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    if chunk_rows is None:
        from .vault_ingest import load_chunk_index_raw, speaker_role_weight

        chunk_rows = load_chunk_index_raw(root)
    else:
        from .vault_ingest import speaker_role_weight
    governance = governance or load_library_governance(root)
    if source_lookup is None:
        source_lookup = get_governed_source_lookup(root, governance=governance)
    chunk_policy_map = _chunk_policy_map(governance)
    manual_link_map = _manual_chunk_link_map(governance)

    normalized_chunk_rows: List[Dict[str, Any]] = []
    for index, row in enumerate(chunk_rows):
        normalized = dict(row)
        normalized.setdefault("chunk_id", row.get("source_item_id") or f"chunk-{index + 1}")
        normalized.setdefault("source_id", row.get("source_ref", ""))
        normalized.setdefault("chunk_index", index)
        normalized_chunk_rows.append(normalized)

    source_neighbors: Dict[str, List[str]] = {}
    section_neighbors: Dict[str, List[str]] = {}
    grouped_by_source: Dict[str, List[Dict[str, Any]]] = {}
    ordered_rows = sorted(normalized_chunk_rows, key=lambda row: (row.get("source_id", ""), int(row.get("chunk_index", 0)), row.get("chunk_id", "")))
    effective_section_paths: Dict[str, List[str]] = {}
    for row in ordered_rows:
        chunk_patch = _chunk_governance_patch(chunk_policy_map.get(row.get("chunk_id", "")))
        section_value = chunk_patch.get("dimension_overlays", {}).get("section_path", row.get("section_path") or [])
        if isinstance(section_value, list):
            effective_section_paths[row["chunk_id"]] = [str(item).strip() for item in section_value if str(item).strip()]
        else:
            text = str(section_value).strip()
            effective_section_paths[row["chunk_id"]] = [text] if text else []
    for row in ordered_rows:
        grouped_by_source.setdefault(row.get("source_id", ""), []).append(row)
    for rows in grouped_by_source.values():
        for index, row in enumerate(rows):
            neighbors: List[str] = []
            if index > 0:
                neighbors.append(rows[index - 1]["chunk_id"])
            if index + 1 < len(rows):
                neighbors.append(rows[index + 1]["chunk_id"])
            source_neighbors[row["chunk_id"]] = neighbors
        section_groups: Dict[tuple[str, ...], List[Dict[str, Any]]] = {}
        for row in rows:
            section_key = tuple(effective_section_paths.get(row["chunk_id"], []))
            if section_key:
                section_groups.setdefault(section_key, []).append(row)
        for peers in section_groups.values():
            for index, row in enumerate(peers):
                neighbors = []
                if index > 0:
                    neighbors.append(peers[index - 1]["chunk_id"])
                if index + 1 < len(peers):
                    neighbors.append(peers[index + 1]["chunk_id"])
                if neighbors:
                    section_neighbors[row["chunk_id"]] = neighbors

    resolved_rows: List[Dict[str, Any]] = []
    for row in ordered_rows:
        source_row = source_lookup.get(row.get("source_ref", ""), {})
        chunk_policy = chunk_policy_map.get(row.get("chunk_id", ""))
        chunk_patch = _chunk_governance_patch(chunk_policy)
        inherited_status = source_row.get("governance_status", "active")
        inherited_flags = {
            key: bool(source_row.get(key, True))
            for key in GOVERNANCE_FLAG_FIELDS
        }
        status = chunk_patch.get("governance_status", inherited_status)
        local_flags = _policy_defaults_for_status(status)
        for key in GOVERNANCE_FLAG_FIELDS:
            if key in chunk_patch:
                local_flags[key] = bool(chunk_patch[key])
        resolved_flags = {
            key: bool(inherited_flags.get(key, True)) and bool(local_flags.get(key, True))
            for key in GOVERNANCE_FLAG_FIELDS
        }
        raw_metadata = dict(row.get("metadata", {}))
        collection_tags = _normalize_collection_tags(
            list(source_row.get("collection_tags", [])) + list(chunk_patch.get("collection_tags", []))
        )
        section_path = row.get("section_path") or []
        semantic_role = chunk_patch.get("semantic_role", source_row.get("semantic_role", _infer_semantic_role(source_row or row)))
        normalization_profile = chunk_patch.get("normalization_profile", source_row.get("normalization_profile", "default"))
        metadata_dimensions: Dict[str, Any] = {
            "source_type": row.get("source_type", ""),
            "source_family": row.get("source_family", ""),
            "content_kind": row.get("content_kind", ""),
            "sensitivity_tier": row.get("sensitivity_tier", ""),
            "path_name": raw_metadata.get("path_name", ""),
            "speaker_role": raw_metadata.get("speaker_role", ""),
            "semantic_role": semantic_role,
            "normalization_profile": normalization_profile,
            "governance_status": status,
        }
        pond_route = _pond_routing_payload(root, {**row, "semantic_role": semantic_role, "collection_tags": collection_tags})
        if pond_route.get("primary_pond"):
            metadata_dimensions["primary_pond"] = pond_route["primary_pond"]
        if pond_route.get("secondary_ponds"):
            metadata_dimensions["secondary_ponds"] = list(pond_route["secondary_ponds"])
        if pond_route.get("touched_layers"):
            metadata_dimensions["pond_layer"] = list(pond_route["touched_layers"])
        if pond_route.get("touch_confidence_score"):
            metadata_dimensions["pond_confidence"] = float(pond_route["touch_confidence_score"])
        if pond_route.get("routing_justification"):
            metadata_dimensions["pond_routing_justification"] = pond_route["routing_justification"]
        if pond_route.get("routing_method"):
            metadata_dimensions["pond_routing_method"] = str(pond_route["routing_method"]).strip()
        if pond_route.get("router_version"):
            metadata_dimensions["pond_router_version"] = str(pond_route["router_version"]).strip()
        if pond_route.get("model_role"):
            metadata_dimensions["pond_model_role"] = str(pond_route["model_role"]).strip()
        if pond_route.get("model_signature"):
            metadata_dimensions["pond_model_signature"] = str(pond_route["model_signature"]).strip()
        if section_path:
            metadata_dimensions["section_path"] = list(section_path)
            metadata_dimensions["section_label"] = " / ".join(section_path)
        if collection_tags:
            metadata_dimensions["collection_tags"] = collection_tags
        for key, value in raw_metadata.items():
            if key in {"speaker_weight"}:
                continue
            if value in (None, "", [], {}):
                continue
            metadata_dimensions.setdefault(key, value)
        metadata_dimensions.update(chunk_patch.get("dimension_overlays", {}))
        if "section_path" in metadata_dimensions:
            section_value = metadata_dimensions["section_path"]
            if isinstance(section_value, list):
                section_path = section_value
            else:
                section_path = [str(section_value).strip()] if str(section_value).strip() else []
            metadata_dimensions["section_path"] = list(section_path)
            if section_path:
                metadata_dimensions["section_label"] = " / ".join(section_path)
            else:
                metadata_dimensions.pop("section_label", None)
        resolved_metadata = dict(raw_metadata)
        for key, value in metadata_dimensions.items():
            if key in {"section_label", "collection_tags", "semantic_role", "normalization_profile", "governance_status"}:
                continue
            resolved_metadata[key] = value
        speaker_role_value = metadata_dimensions.get("speaker_role", resolved_metadata.get("speaker_role", ""))
        if isinstance(speaker_role_value, list):
            speaker_role = speaker_role_value[0] if speaker_role_value else ""
        else:
            speaker_role = str(speaker_role_value).strip()
        resolved_metadata["speaker_role"] = speaker_role
        resolved_metadata["speaker_weight"] = speaker_role_weight(speaker_role)
        related_ids = sorted(
            {
                *source_neighbors.get(row["chunk_id"], []),
                *section_neighbors.get(row["chunk_id"], []),
                *manual_link_map.get(row["chunk_id"], set()),
            }
        )
        resolved = dict(row)
        resolved.update(resolved_flags)
        resolved["governance_status"] = status
        resolved["normalization_profile"] = normalization_profile
        resolved["semantic_role"] = semantic_role
        resolved["collection_tags"] = collection_tags
        resolved["governance_notes"] = chunk_patch.get("notes", "")
        resolved["metadata"] = resolved_metadata
        resolved["metadata_dimensions"] = metadata_dimensions
        resolved["primary_pond"] = str(metadata_dimensions.get("primary_pond", "")).strip()
        resolved["secondary_ponds"] = list(metadata_dimensions.get("secondary_ponds", [])) if isinstance(metadata_dimensions.get("secondary_ponds"), list) else []
        resolved["pond_layers"] = list(metadata_dimensions.get("pond_layer", [])) if isinstance(metadata_dimensions.get("pond_layer"), list) else _dimension_values(metadata_dimensions.get("pond_layer"))
        resolved["pond_confidence"] = float(metadata_dimensions.get("pond_confidence", 0.0) or 0.0)
        resolved["pond_routing_justification"] = str(metadata_dimensions.get("pond_routing_justification", "")).strip()
        resolved["pond_routing_method"] = str(metadata_dimensions.get("pond_routing_method", "")).strip()
        resolved["pond_router_version"] = str(metadata_dimensions.get("pond_router_version", "")).strip()
        resolved["pond_model_role"] = str(metadata_dimensions.get("pond_model_role", "")).strip()
        resolved["pond_model_signature"] = str(metadata_dimensions.get("pond_model_signature", "")).strip()
        resolved["section_path"] = list(section_path)
        resolved["source_neighbor_chunk_ids"] = source_neighbors.get(row["chunk_id"], [])
        resolved["section_neighbor_chunk_ids"] = section_neighbors.get(row["chunk_id"], [])
        resolved["manual_linked_chunk_ids"] = sorted(manual_link_map.get(row["chunk_id"], set()))
        resolved["related_chunk_ids"] = related_ids
        resolved["governance_origin"] = "chunk" if chunk_policy else source_row.get("governance_origin", "default")
        resolved["source_policy_applied"] = bool(source_row and source_row.get("source_policy_applied"))
        resolved["family_policy_applied"] = bool(source_row and source_row.get("family_policy_applied"))
        resolved["chunk_policy_applied"] = bool(chunk_policy)
        resolved["dimension_overlays"] = chunk_patch.get("dimension_overlays", {})
        curation_profile = _chunk_curation_profile(resolved)
        resolved["curation_classes"] = curation_profile["classes"]
        resolved["curation_signals"] = curation_profile["signals"]
        resolved_rows.append(resolved)
    return resolved_rows


def _chunk_rederive_plan_for_fields(changed_fields: set[str], chunk_id: str) -> Dict[str, Any]:
    affected: set[str] = set()
    reasons: List[str] = []
    if {"governance_status", "include_in_runtime", "normalization_profile", "dimension_overlays", "collection_tags"} & changed_fields:
        affected.update(
            [
                "analysis_units",
                "conversation_deltas",
                "meta_layer",
                "conversation_threads",
                "thread_abstractions",
                "context_bubbles",
                "knowledge_layer",
                "connections",
            ]
        )
        reasons.append(f"Chunk {chunk_id} changed runtime chunk substrate.")
    if {"include_in_bubbles"} & changed_fields:
        affected.update(["context_bubbles", "knowledge_layer", "connections"])
        reasons.append(f"Chunk {chunk_id} changed bubble eligibility.")
    if {"include_in_concepts", "semantic_role"} & changed_fields:
        affected.update(["context_bubbles", "knowledge_layer", "connections"])
        reasons.append(f"Chunk {chunk_id} changed concept alignment eligibility.")
    ordered = _ordered_stages(affected)
    return {
        "affected_stages": ordered,
        "from_stage": ordered[0] if ordered else None,
        "post_actions": [],
        "reasons": reasons,
        "targets": [chunk_id],
    }


def resolve_governed_source_rows(
    root: Path,
    source_rows: List[Dict[str, Any]] | None = None,
    *,
    governance: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    if source_rows is None:
        from .vault_ingest import load_source_registry_raw

        source_rows = load_source_registry_raw(root)
    governance = governance or load_library_governance(root)
    family_map = _family_policy_map(governance)
    source_map = _source_policy_map(governance)
    resolved_rows: List[Dict[str, Any]] = []
    for source in source_rows:
        family_policy = family_map.get(source.get("source_family", ""))
        source_policy = source_map.get(source.get("source_ref", ""))
        merged_patch = {}
        merged_patch.update(_governance_patch(family_policy))
        merged_patch.update(_governance_patch(source_policy))
        status = merged_patch.get("governance_status", "active")
        include_flags = _policy_defaults_for_status(status)
        for key in GOVERNANCE_FLAG_FIELDS:
            if key in merged_patch:
                include_flags[key] = bool(merged_patch[key])
        collection_tags = []
        if family_policy:
            collection_tags.extend(family_policy.get("collection_tags", []))
        if source_policy:
            collection_tags.extend(source_policy.get("collection_tags", []))
        resolved = dict(source)
        resolved.update(include_flags)
        resolved["governance_status"] = status
        resolved["semantic_role"] = merged_patch.get("semantic_role", _infer_semantic_role(source))
        resolved["normalization_profile"] = merged_patch.get("normalization_profile", "default")
        resolved["collection_tags"] = _normalize_collection_tags(collection_tags)
        resolved["governance_notes"] = merged_patch.get("notes", "")
        resolved["governance_origin"] = (
            "source"
            if source_policy
            else "family"
            if family_policy
            else "default"
        )
        resolved["family_policy_applied"] = bool(family_policy)
        resolved["source_policy_applied"] = bool(source_policy)
        resolved_rows.append(resolved)
    return resolved_rows


def get_governed_source_lookup(
    root: Path,
    source_rows: List[Dict[str, Any]] | None = None,
    *,
    governance: Dict[str, Any] | None = None,
) -> Dict[str, Dict[str, Any]]:
    return {
        row["source_ref"]: row
        for row in resolve_governed_source_rows(root, source_rows, governance=governance)
    }


def _ordered_stages(stages: Iterable[str]) -> List[str]:
    unique = set(stages)
    return [stage for stage in RUNTIME_STAGE_SEQUENCE if stage in unique]


def _rederive_plan_for_fields(changed_fields: set[str], target_label: str) -> Dict[str, Any]:
    affected: set[str] = set()
    reasons: List[str] = []
    post_actions: List[str] = []
    if {"governance_status", "include_in_runtime", "normalization_profile"} & changed_fields:
        affected.update(
            [
                "analysis_units",
                "conversation_deltas",
                "meta_layer",
                "conversation_threads",
                "thread_abstractions",
                "context_bubbles",
                "knowledge_layer",
                "connections",
            ]
        )
        reasons.append(f"{target_label} changed runtime eligibility.")
    if {"include_in_bubbles"} & changed_fields:
        affected.update(["context_bubbles", "knowledge_layer", "connections"])
        reasons.append(f"{target_label} changed bubble eligibility.")
    if {"include_in_concepts", "semantic_role"} & changed_fields:
        affected.update(["context_bubbles", "knowledge_layer", "connections"])
        reasons.append(f"{target_label} changed concept alignment eligibility.")
    if "include_in_long_form" in changed_fields:
        post_actions.append("inner-world batch --limit 5")
    ordered = _ordered_stages(affected)
    return {
        "affected_stages": ordered,
        "from_stage": ordered[0] if ordered else None,
        "post_actions": sorted(set(post_actions)),
        "reasons": reasons,
    }


def _merge_rederive_plans(existing: Dict[str, Any] | None, update: Dict[str, Any]) -> Dict[str, Any]:
    affected = _ordered_stages(list(existing.get("affected_stages", [])) + list(update.get("affected_stages", []))) if existing else update.get("affected_stages", [])
    post_actions = sorted(set((existing or {}).get("post_actions", []) + update.get("post_actions", [])))
    reasons = list(dict.fromkeys((existing or {}).get("reasons", []) + update.get("reasons", [])))
    targets = list(dict.fromkeys((existing or {}).get("targets", []) + update.get("targets", [])))
    merged = {
        "updated_at": utc_now(),
        "affected_stages": affected,
        "from_stage": affected[0] if affected else None,
        "post_actions": post_actions,
        "reasons": reasons,
        "targets": targets,
    }
    return merged


def _upsert_policy(rows: List[Dict[str, Any]], key: str, value: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    target = next((row for row in rows if row.get(key) == value), None)
    if target is None:
        target = {key: value}
        rows.append(target)
    target.update(patch)
    target["updated_at"] = utc_now()
    return target


def _changed_governance_fields(before: Dict[str, Any] | None, after: Dict[str, Any] | None) -> set[str]:
    fields = set(GOVERNANCE_TEXT_FIELDS) | set(GOVERNANCE_FLAG_FIELDS) | {"collection_tags"}
    changed = set()
    before = before or {}
    after = after or {}
    for field in fields:
        if before.get(field) != after.get(field):
            changed.add(field)
    return changed


def update_source_governance(
    root: Path,
    source_ref: str,
    *,
    governance_status: str | None = None,
    semantic_role: str | None = None,
    normalization_profile: str | None = None,
    include_in_runtime: bool | None = None,
    include_in_bubbles: bool | None = None,
    include_in_concepts: bool | None = None,
    include_in_long_form: bool | None = None,
    collection_tags: Iterable[str] | None = None,
    notes: str | None = None,
) -> Dict[str, Any]:
    governance = load_library_governance(root)
    previous = dict(_source_policy_map(governance).get(source_ref, {}))
    patch: Dict[str, Any] = {}
    if governance_status:
        patch["governance_status"] = governance_status
    if semantic_role:
        patch["semantic_role"] = semantic_role
    if normalization_profile:
        patch["normalization_profile"] = normalization_profile
    for key, value in {
        "include_in_runtime": include_in_runtime,
        "include_in_bubbles": include_in_bubbles,
        "include_in_concepts": include_in_concepts,
        "include_in_long_form": include_in_long_form,
    }.items():
        if value is not None:
            patch[key] = bool(value)
    if collection_tags is not None:
        patch["collection_tags"] = _normalize_collection_tags(collection_tags)
    if notes is not None:
        patch["notes"] = notes
    record = _upsert_policy(governance["source_policies"], "source_ref", source_ref, patch)
    changed_fields = _changed_governance_fields(previous, record)
    plan = _rederive_plan_for_fields(changed_fields, f"Source {source_ref}")
    plan["targets"] = [source_ref]
    governance["updated_at"] = utc_now()
    governance["pending_rederive"] = _merge_rederive_plans(governance.get("pending_rederive"), plan)
    _save_library_governance(root, governance)
    return {
        "governance_path": governance["governance_path"],
        "policy_record": record,
        "changed_fields": sorted(changed_fields),
        "pending_rederive": governance.get("pending_rederive"),
    }


def update_family_governance(
    root: Path,
    source_family: str,
    *,
    governance_status: str | None = None,
    semantic_role: str | None = None,
    normalization_profile: str | None = None,
    include_in_runtime: bool | None = None,
    include_in_bubbles: bool | None = None,
    include_in_concepts: bool | None = None,
    include_in_long_form: bool | None = None,
    collection_tags: Iterable[str] | None = None,
    notes: str | None = None,
) -> Dict[str, Any]:
    governance = load_library_governance(root)
    previous = dict(_family_policy_map(governance).get(source_family, {}))
    patch: Dict[str, Any] = {}
    if governance_status:
        patch["governance_status"] = governance_status
    if semantic_role:
        patch["semantic_role"] = semantic_role
    if normalization_profile:
        patch["normalization_profile"] = normalization_profile
    for key, value in {
        "include_in_runtime": include_in_runtime,
        "include_in_bubbles": include_in_bubbles,
        "include_in_concepts": include_in_concepts,
        "include_in_long_form": include_in_long_form,
    }.items():
        if value is not None:
            patch[key] = bool(value)
    if collection_tags is not None:
        patch["collection_tags"] = _normalize_collection_tags(collection_tags)
    if notes is not None:
        patch["notes"] = notes
    record = _upsert_policy(governance["family_policies"], "source_family", source_family, patch)
    changed_fields = _changed_governance_fields(previous, record)
    plan = _rederive_plan_for_fields(changed_fields, f"Family {source_family}")
    plan["targets"] = [source_family]
    governance["updated_at"] = utc_now()
    governance["pending_rederive"] = _merge_rederive_plans(governance.get("pending_rederive"), plan)
    _save_library_governance(root, governance)
    return {
        "governance_path": governance["governance_path"],
        "policy_record": record,
        "changed_fields": sorted(changed_fields),
        "pending_rederive": governance.get("pending_rederive"),
    }


def _changed_chunk_governance_fields(before: Dict[str, Any] | None, after: Dict[str, Any] | None) -> set[str]:
    fields = set(GOVERNANCE_TEXT_FIELDS) | set(GOVERNANCE_FLAG_FIELDS) | {"collection_tags", "dimension_overlays"}
    changed = set()
    before = before or {}
    after = after or {}
    for field in fields:
        left = before.get(field)
        right = after.get(field)
        if field == "dimension_overlays":
            left = _normalize_dimension_overlays(left)
            right = _normalize_dimension_overlays(right)
        if left != right:
            changed.add(field)
    return changed


def update_chunk_governance(
    root: Path,
    chunk_id: str,
    *,
    governance_status: str | None = None,
    semantic_role: str | None = None,
    normalization_profile: str | None = None,
    include_in_runtime: bool | None = None,
    include_in_bubbles: bool | None = None,
    include_in_concepts: bool | None = None,
    include_in_long_form: bool | None = None,
    collection_tags: Iterable[str] | None = None,
    dimension_overlays: Dict[str, Any] | None = None,
    clear_dimension_overlays: bool = False,
    notes: str | None = None,
) -> Dict[str, Any]:
    governance = load_library_governance(root)
    previous_resolved = next((row for row in resolve_governed_chunk_rows(root, governance=governance) if row["chunk_id"] == chunk_id), None)
    previous = dict(_chunk_policy_map(governance).get(chunk_id, {}))
    patch: Dict[str, Any] = {}
    if governance_status:
        patch["governance_status"] = governance_status
    if semantic_role:
        patch["semantic_role"] = semantic_role
    if normalization_profile:
        patch["normalization_profile"] = normalization_profile
    for key, value in {
        "include_in_runtime": include_in_runtime,
        "include_in_bubbles": include_in_bubbles,
        "include_in_concepts": include_in_concepts,
        "include_in_long_form": include_in_long_form,
    }.items():
        if value is not None:
            patch[key] = bool(value)
    if collection_tags is not None:
        patch["collection_tags"] = _normalize_collection_tags(collection_tags)
    if clear_dimension_overlays:
        patch["dimension_overlays"] = {}
    elif dimension_overlays is not None:
        patch["dimension_overlays"] = _normalize_dimension_overlays(dimension_overlays)
    if notes is not None:
        patch["notes"] = notes
    record = _upsert_policy(governance["chunk_policies"], "chunk_id", chunk_id, patch)
    changed_fields = _changed_chunk_governance_fields(previous, record)
    plan = _chunk_rederive_plan_for_fields(changed_fields, chunk_id)
    governance["updated_at"] = utc_now()
    governance["pending_rederive"] = _merge_rederive_plans(governance.get("pending_rederive"), plan)
    _save_library_governance(root, governance)
    resolved = next((row for row in resolve_governed_chunk_rows(root, governance=governance) if row["chunk_id"] == chunk_id), None)
    if "dimension_overlays" in changed_fields and previous_resolved and resolved:
        previous_pond = str(previous_resolved.get("primary_pond", "")).strip()
        resolved_pond = str(resolved.get("primary_pond", "")).strip()
        previous_layers = [str(value).strip() for value in previous_resolved.get("pond_layers", []) if str(value).strip()]
        resolved_layers = [str(value).strip() for value in resolved.get("pond_layers", []) if str(value).strip()]
        if previous_pond != resolved_pond or previous_layers != resolved_layers:
            try:
                from .product_inner_world import record_pond_routing_feedback
            except Exception:
                record_pond_routing_feedback = None
            if record_pond_routing_feedback is not None:
                record_pond_routing_feedback(
                    root,
                    event_type="manual_pond_override" if previous_pond != resolved_pond else "manual_pond_layer_override",
                    chunk_id=chunk_id,
                    source_ref=str(resolved.get("source_ref", "")).strip(),
                    previous_primary_pond=previous_pond,
                    new_primary_pond=resolved_pond,
                    previous_pond_layers=previous_layers,
                    new_pond_layers=resolved_layers,
                    actor="operator",
                    routing_method="manual",
                    note=str(notes or "").strip(),
                )
    return {
        "governance_path": governance["governance_path"],
        "policy_record": record,
        "changed_fields": sorted(changed_fields),
        "resolved_chunk": resolved,
        "pending_rederive": governance.get("pending_rederive"),
    }


def get_chunk_pond_routing_state(root: Path, chunk_id: str) -> Dict[str, Any]:
    governance = load_library_governance(root)
    resolved = next((row for row in resolve_governed_chunk_rows(root, governance=governance) if row["chunk_id"] == chunk_id), None)
    if resolved is None:
        raise ValueError(f"Unknown chunk_id: {chunk_id}")
    chunk_policy = _chunk_policy_map(governance).get(chunk_id, {})
    dimension_overlays = _normalize_dimension_overlays(chunk_policy.get("dimension_overlays"))
    manual_override_primary_pond = str(dimension_overlays.get("primary_pond", "")).strip()
    manual_override_pond_layers = _dimension_values(dimension_overlays.get("pond_layer"))
    pond_rows = (_load_pond_matrix(root).get("ponds", {}) or {})
    available_ponds = [
        {
            "pond_id": pond_id,
            "description": str(pond.get("description", "")).strip(),
            "layers": [str(value).strip() for value in pond.get("layers", []) if str(value).strip()],
            "selected": pond_id == resolved.get("primary_pond", ""),
        }
        for pond_id, pond in sorted(pond_rows.items(), key=lambda item: item[0])
    ]
    allowed_layers = []
    selected_pond = manual_override_primary_pond or str(resolved.get("primary_pond", "")).strip()
    if selected_pond and selected_pond in pond_rows:
        allowed_layers = [str(value).strip() for value in pond_rows[selected_pond].get("layers", []) if str(value).strip()]
    return {
        "chunk_id": resolved["chunk_id"],
        "source_ref": str(resolved.get("source_ref", "")).strip(),
        "title": str(resolved.get("title", "")).strip(),
        "chunk_index": int(resolved.get("chunk_index", 0) or 0),
        "primary_pond": str(resolved.get("primary_pond", "")).strip(),
        "secondary_ponds": [str(value).strip() for value in resolved.get("secondary_ponds", []) if str(value).strip()],
        "pond_layers": [str(value).strip() for value in resolved.get("pond_layers", []) if str(value).strip()],
        "pond_confidence": float(resolved.get("pond_confidence", 0.0) or 0.0),
        "pond_routing_justification": str(resolved.get("pond_routing_justification", "")).strip(),
        "pond_routing_method": str(resolved.get("pond_routing_method", "")).strip(),
        "pond_router_version": str(resolved.get("pond_router_version", "")).strip(),
        "pond_model_role": str(resolved.get("pond_model_role", "")).strip(),
        "pond_model_signature": str(resolved.get("pond_model_signature", "")).strip(),
        "manual_override": bool(manual_override_primary_pond or manual_override_pond_layers),
        "manual_override_primary_pond": manual_override_primary_pond,
        "manual_override_pond_layers": manual_override_pond_layers,
        "allowed_layers": allowed_layers,
        "available_ponds": available_ponds,
    }


def override_chunk_pond_routing(
    root: Path,
    chunk_id: str,
    *,
    primary_pond: str | None = None,
    pond_layers: Iterable[str] | None = None,
    clear_override: bool = False,
    notes: str | None = None,
) -> Dict[str, Any]:
    state = get_chunk_pond_routing_state(root, chunk_id)
    governance = load_library_governance(root)
    chunk_policy = _chunk_policy_map(governance).get(chunk_id, {})
    overlays = _normalize_dimension_overlays(chunk_policy.get("dimension_overlays"))
    for key in [
        "primary_pond",
        "pond_layer",
        "pond_confidence",
        "pond_routing_justification",
        "pond_routing_method",
        "pond_router_version",
        "pond_model_role",
        "pond_model_signature",
    ]:
        overlays.pop(key, None)
    if clear_override:
        result = update_chunk_governance(
            root,
            chunk_id,
            dimension_overlays=overlays,
            notes=notes,
        )
        return {
            **result,
            "action": "cleared",
            "pond_state": get_chunk_pond_routing_state(root, chunk_id),
        }

    pond_rows = (_load_pond_matrix(root).get("ponds", {}) or {})
    target_primary_pond = str(primary_pond or state.get("manual_override_primary_pond") or state.get("primary_pond") or "").strip()
    if not target_primary_pond:
        raise ValueError(f"Chunk {chunk_id} has no available pond to override.")
    if target_primary_pond not in pond_rows:
        raise ValueError(f"Unknown pond_id: {target_primary_pond}")
    target_layers = (
        _dimension_values(pond_layers)
        if pond_layers is not None
        else (
            state.get("manual_override_pond_layers", [])
            if state.get("manual_override_primary_pond") == target_primary_pond and state.get("manual_override")
            else state.get("pond_layers", [])
        )
    )
    allowed_layers = {str(value).strip() for value in pond_rows[target_primary_pond].get("layers", []) if str(value).strip()}
    invalid_layers = [value for value in target_layers if value not in allowed_layers]
    if invalid_layers:
        raise ValueError(
            f"Invalid pond layers for {target_primary_pond}: {', '.join(sorted(dict.fromkeys(invalid_layers)))}"
        )

    overlays["primary_pond"] = target_primary_pond
    if target_layers:
        overlays["pond_layer"] = sorted(dict.fromkeys(target_layers))
    overlays["pond_confidence"] = "1.0"
    overlays["pond_routing_method"] = "manual"
    if notes is not None:
        justification = notes.strip()
    else:
        justification = (
            f"Manual override to {target_primary_pond}"
            + (f" with layers {', '.join(target_layers)}" if target_layers else "")
        )
    overlays["pond_routing_justification"] = justification

    result = update_chunk_governance(
        root,
        chunk_id,
        dimension_overlays=overlays,
        notes=notes,
    )
    return {
        **result,
        "action": "updated",
        "pond_state": get_chunk_pond_routing_state(root, chunk_id),
    }


def update_chunk_link(
    root: Path,
    chunk_id: str,
    other_chunk_id: str,
    *,
    kind: str = "manual",
    notes: str | None = None,
    remove: bool = False,
) -> Dict[str, Any]:
    left, right = _canonical_chunk_pair(chunk_id, other_chunk_id)
    governance = load_library_governance(root)
    links = governance.setdefault("chunk_links", [])
    existing = next(
        (
            row
            for row in links
            if row.get("chunk_id") == left and row.get("other_chunk_id") == right and row.get("kind", "manual") == kind
        ),
        None,
    )
    if remove:
        links[:] = [
            row
            for row in links
            if not (
                row.get("chunk_id") == left
                and row.get("other_chunk_id") == right
                and row.get("kind", "manual") == kind
            )
        ]
        action = "removed"
        record = None
    else:
        record = existing or {"chunk_id": left, "other_chunk_id": right, "kind": kind}
        if notes is not None:
            record["notes"] = notes
        record["updated_at"] = utc_now()
        if existing is None:
            links.append(record)
        action = "upserted"
    governance["updated_at"] = utc_now()
    plan = {
        "affected_stages": ["analysis_units", "conversation_deltas", "meta_layer", "conversation_threads", "thread_abstractions", "context_bubbles", "knowledge_layer", "connections"],
        "from_stage": "analysis_units",
        "post_actions": [],
        "reasons": [f"Chunk link {action} for {left} and {right}."],
        "targets": [left, right],
    }
    governance["pending_rederive"] = _merge_rederive_plans(governance.get("pending_rederive"), plan)
    _save_library_governance(root, governance)
    return {
        "governance_path": governance["governance_path"],
        "action": action,
        "chunk_link": record,
        "pending_rederive": governance.get("pending_rederive"),
    }


def clear_pending_governance_rederive(root: Path, *, applied_plan: Dict[str, Any] | None = None) -> Dict[str, Any]:
    governance = load_library_governance(root)
    governance["pending_rederive"] = None
    governance["last_applied_rederive"] = {
        **(applied_plan or {}),
        "applied_at": utc_now(),
    } if applied_plan else None
    governance["updated_at"] = utc_now()
    _save_library_governance(root, governance)
    return governance


def _iter_files(roots: Iterable[str], include_globs: Iterable[str]) -> List[Path]:
    include_globs = list(include_globs) or list(DEFAULT_TEXT_GLOBS)
    discovered: dict[str, Path] = {}
    for raw_root in roots:
        root = Path(raw_root).expanduser()
        if not root.exists():
            continue
        if root.is_file():
            discovered[str(root.resolve())] = root.resolve()
            continue
        for pattern in include_globs:
            for path in root.rglob(pattern):
                if path.is_file():
                    discovered[str(path.resolve())] = path.resolve()
    return [discovered[key] for key in sorted(discovered)]


def _is_remote_host(host: str | None) -> bool:
    return bool(host and host not in {"local", "localhost", "127.0.0.1"})


def _run_host_python(host: str | None, script: str) -> Any:
    if _is_remote_host(host):
        cmd = ["ssh", host, "python3", "-"]
    else:
        cmd = ["python3", "-"]
    result = subprocess.run(
        cmd,
        input=script,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def _remote_source_ref(host: str | None, path: str) -> str:
    if _is_remote_host(host):
        return f"ssh://{host}{path}"
    return str(Path(path).resolve())


def _scan_remote_filesystem_source(source: Dict[str, Any]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    roots = source.get("roots", [])
    include_globs = source.get("include_globs", DEFAULT_TEXT_GLOBS)
    host = source.get("remote_host")
    script = textwrap.dedent(
        f"""
        import fnmatch
        import hashlib
        import json
        from pathlib import Path

        roots = {json.dumps(roots)}
        include_globs = {json.dumps(include_globs)}
        discovered = {{}}
        for raw_root in roots:
            root = Path(raw_root).expanduser()
            if not root.exists():
                continue
            if root.is_file():
                discovered[str(root)] = root
                continue
            for pattern in include_globs:
                for path in root.rglob("*"):
                    if path.is_file() and fnmatch.fnmatch(path.name, pattern):
                        discovered[str(path)] = path

        items = []
        for key in sorted(discovered):
            path = discovered[key]
            content = path.read_text(encoding="utf-8", errors="ignore").strip()
            if not content:
                continue
            root_match = ""
            for raw_root in roots:
                if key.startswith(raw_root):
                    root_match = raw_root
                    break
            relative_path = key[len(root_match):].lstrip("/") if root_match and key.startswith(root_match) else path.name
            items.append({{
                "path": key,
                "title": path.stem.replace("-", " ").replace("_", " ").strip() or "Untitled source",
                "content": content,
                "fingerprint": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "metadata": {{
                    "path_name": path.name,
                    "root": root_match,
                    "relative_path": relative_path,
                }},
            }})
        print(json.dumps({{"items": items, "existing_roots": [raw for raw in roots if Path(raw).expanduser().exists()]}}))
        """
    )
    payload = _run_host_python(host, script)
    items: List[Dict[str, Any]] = []
    for row in payload["items"]:
        items.append(
            {
                "source_ref": _remote_source_ref(host, row["path"]),
                "title": row["title"],
                "content": row["content"],
                "fingerprint": row["fingerprint"],
                "adapter_id": source["source_id"],
                "source_type": source.get("source_type", "manual_import"),
                "source_family": source.get("source_family", "manual_imports"),
                "sensitivity_tier": source.get("sensitivity_tier", "tier_work_product"),
                "metadata": {
                    **row.get("metadata", {}),
                    "remote_host": host,
                    "remote_path": row["path"],
                },
            }
        )
    return items, {
        "source_id": source["source_id"],
        "kind": "filesystem",
        "enabled": source.get("enabled", True),
        "remote_host": host,
        "configured_roots": roots,
        "existing_roots": payload.get("existing_roots", []),
        "discovered_item_count": len(items),
    }


def _scan_filesystem_source(source: Dict[str, Any]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if source.get("remote_host"):
        return _scan_remote_filesystem_source(source)
    roots = source.get("roots", [])
    files = _iter_files(roots, source.get("include_globs", DEFAULT_TEXT_GLOBS))
    items: List[Dict[str, Any]] = []
    for path in files:
        content = path.read_text(encoding="utf-8", errors="ignore").strip()
        if not content:
            continue
        items.append(
            {
                "source_ref": str(path.resolve()),
                "title": _normalize_title(path.stem),
                "content": content,
                "fingerprint": _content_hash(content),
                "adapter_id": source["source_id"],
                "source_type": source.get("source_type", "manual_import"),
                "source_family": source.get("source_family", "manual_imports"),
                "sensitivity_tier": source.get("sensitivity_tier", "tier_work_product"),
                "metadata": {
                    "path_name": path.name,
                    "root": next((raw for raw in roots if str(path).startswith(str(Path(raw).expanduser()))), ""),
                    "relative_path": path.name,
                },
            }
        )
    existing_roots = [str(Path(raw).expanduser()) for raw in roots if Path(raw).expanduser().exists()]
    return items, {
        "source_id": source["source_id"],
        "kind": "filesystem",
        "enabled": source.get("enabled", True),
        "configured_roots": roots,
        "existing_roots": existing_roots,
        "discovered_item_count": len(items),
    }


def _declared_type(column: sqlite3.Row) -> str:
    return str(column["type"] or "").lower()


def _choose_primary_key(columns: List[sqlite3.Row]) -> str:
    primary_keys = sorted((column for column in columns if int(column["pk"] or 0) > 0), key=lambda item: int(item["pk"]))
    if primary_keys:
        return primary_keys[0]["name"]
    for preferred in ("id", "rowid"):
        if any(column["name"] == preferred for column in columns):
            return preferred
    return "rowid"


def _choose_text_columns(columns: List[sqlite3.Row], configured: List[str] | None = None) -> List[str]:
    if configured:
        return [column["name"] for column in columns if column["name"] in configured]
    selected: List[str] = []
    for column in columns:
        name = column["name"]
        column_type = _declared_type(column)
        if any(marker in name.lower() for marker in TEXT_COLUMN_HINTS):
            selected.append(name)
            continue
        if any(marker in column_type for marker in ("char", "text", "clob", "json")):
            selected.append(name)
    return selected[:6]


def _format_sqlite_value(column: str, value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if column.lower() in {"content", "text", "body", "message", "summary", "transcript", "notes", "knowledge"}:
        return text
    return f"{column}: {text}"


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _scan_sqlite_source(source: Dict[str, Any]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if source.get("remote_host"):
        return _scan_remote_sqlite_source(source)
    db_paths = source.get("db_paths") or ([source["db_path"]] if source.get("db_path") else [])
    items: List[Dict[str, Any]] = []
    existing_paths = [Path(raw).expanduser().resolve() for raw in db_paths if Path(raw).expanduser().exists()]
    include_tables = set(source.get("include_tables", []))
    exclude_tables = {name.lower() for name in source.get("exclude_tables", [])}
    configured_text_columns = source.get("text_columns", [])
    for db_path in sorted(existing_paths):
        connection = sqlite3.connect(str(db_path))
        connection.row_factory = sqlite3.Row
        tables = [
            row["name"]
            for row in connection.execute("select name from sqlite_master where type = 'table' and name not like 'sqlite_%' order by name")
        ]
        for table in tables:
            lowered = table.lower()
            if include_tables and table not in include_tables:
                continue
            if lowered in exclude_tables or any(marker in lowered for marker in SQLITE_TABLE_EXCLUDES):
                continue
            try:
                columns = list(connection.execute(f"pragma table_info({_quote_identifier(table)})"))
            except sqlite3.Error:
                continue
            if not columns:
                continue
            primary_key = _choose_primary_key(columns)
            text_columns = _choose_text_columns(columns, configured_text_columns)
            if not text_columns:
                continue
            select_parts: List[str] = []
            if primary_key == "rowid":
                select_parts.append('rowid as "__tracker_rowid__"')
            else:
                select_parts.append(_quote_identifier(primary_key))
            for column in text_columns:
                if column != primary_key:
                    select_parts.append(_quote_identifier(column))
            query = f"select {', '.join(select_parts)} from {_quote_identifier(table)}"
            try:
                rows = connection.execute(query)
            except sqlite3.Error:
                continue
            for row in rows:
                row_id = row["__tracker_rowid__"] if primary_key == "rowid" else row[primary_key]
                formatted_parts = []
                title_value = ""
                for column in text_columns:
                    value = row[column] if column in row.keys() else None
                    if column.lower() == "title" and value:
                        title_value = str(value).strip()
                    formatted = _format_sqlite_value(column, value)
                    if formatted:
                        formatted_parts.append(formatted)
                content = "\n\n".join(formatted_parts).strip()
                if not content:
                    continue
                items.append(
                    {
                        "source_ref": f"sqlite://{db_path}#{table}/{row_id}",
                        "title": title_value or _normalize_title(f"{table} {row_id}"),
                        "content": content,
                        "fingerprint": _content_hash(content),
                        "adapter_id": source["source_id"],
                        "source_type": source.get("source_type", "sqlite_record"),
                        "source_family": source.get("source_family", "sqlite_records"),
                        "sensitivity_tier": source.get("sensitivity_tier", "tier_work_product"),
                        "metadata": {
                            "db_path": str(db_path),
                            "table": table,
                            "row_id": str(row_id),
                            "text_columns": text_columns,
                        },
                    }
                )
        connection.close()
    return items, {
        "source_id": source["source_id"],
        "kind": "sqlite",
        "enabled": source.get("enabled", True),
        "configured_db_paths": db_paths,
        "existing_db_paths": [str(path) for path in existing_paths],
        "discovered_item_count": len(items),
    }


def _scan_remote_sqlite_source(source: Dict[str, Any]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    host = source.get("remote_host")
    db_paths = source.get("db_paths") or ([source["db_path"]] if source.get("db_path") else [])
    include_tables = source.get("include_tables", [])
    exclude_tables = source.get("exclude_tables", [])
    configured_text_columns = source.get("text_columns", [])
    script = textwrap.dedent(
        f"""
        import json
        import hashlib
        import sqlite3
        from pathlib import Path

        db_paths = {json.dumps(db_paths)}
        include_tables = set({json.dumps(include_tables)})
        exclude_tables = {{name.lower() for name in {json.dumps(exclude_tables)}}}
        configured_text_columns = {json.dumps(configured_text_columns)}
        text_column_hints = {json.dumps(sorted(TEXT_COLUMN_HINTS))}
        sqlite_table_excludes = {json.dumps(list(SQLITE_TABLE_EXCLUDES))}

        def declared_type(column):
            return str(column["type"] or "").lower()

        def choose_primary_key(columns):
            primary_keys = sorted((column for column in columns if int(column["pk"] or 0) > 0), key=lambda item: int(item["pk"]))
            if primary_keys:
                return primary_keys[0]["name"]
            for preferred in ("id", "rowid"):
                if any(column["name"] == preferred for column in columns):
                    return preferred
            return "rowid"

        def choose_text_columns(columns):
            if configured_text_columns:
                return [column["name"] for column in columns if column["name"] in configured_text_columns]
            selected = []
            for column in columns:
                name = column["name"]
                column_type = declared_type(column)
                if any(marker in name.lower() for marker in text_column_hints):
                    selected.append(name)
                    continue
                if any(marker in column_type for marker in ("char", "text", "clob", "json")):
                    selected.append(name)
            return selected[:6]

        def format_value(column, value):
            if value is None:
                return ""
            text = str(value).strip()
            if not text:
                return ""
            if column.lower() in {{"content", "text", "body", "message", "summary", "transcript", "notes", "knowledge"}}:
                return text
            return f"{{column}}: {{text}}"

        def quote_identifier(value):
            return '"' + value.replace('"', '""') + '"'

        items = []
        existing_db_paths = []
        for raw_path in db_paths:
            db_path = Path(raw_path).expanduser()
            if not db_path.exists():
                continue
            existing_db_paths.append(str(db_path))
            connection = sqlite3.connect(str(db_path))
            connection.row_factory = sqlite3.Row
            tables = [
                row["name"]
                for row in connection.execute("select name from sqlite_master where type = 'table' and name not like 'sqlite_%' order by name")
            ]
            for table in tables:
                lowered = table.lower()
                if include_tables and table not in include_tables:
                    continue
                if lowered in exclude_tables or any(marker in lowered for marker in sqlite_table_excludes):
                    continue
                try:
                    columns = list(connection.execute(f"pragma table_info({{quote_identifier(table)}})"))
                except sqlite3.Error:
                    continue
                if not columns:
                    continue
                primary_key = choose_primary_key(columns)
                text_columns = choose_text_columns(columns)
                if not text_columns:
                    continue
                select_parts = []
                if primary_key == "rowid":
                    select_parts.append('rowid as "__tracker_rowid__"')
                else:
                    select_parts.append(quote_identifier(primary_key))
                for column in text_columns:
                    if column != primary_key:
                        select_parts.append(quote_identifier(column))
                query = f"select {{', '.join(select_parts)}} from {{quote_identifier(table)}}"
                try:
                    rows = connection.execute(query)
                except sqlite3.Error:
                    continue
                for row in rows:
                    row_id = row["__tracker_rowid__"] if primary_key == "rowid" else row[primary_key]
                    title_value = ""
                    formatted_parts = []
                    for column in text_columns:
                        value = row[column] if column in row.keys() else None
                        if column.lower() == "title" and value:
                            title_value = str(value).strip()
                        formatted = format_value(column, value)
                        if formatted:
                            formatted_parts.append(formatted)
                    content = "\\n\\n".join(formatted_parts).strip()
                    if not content:
                        continue
                    items.append({{
                        "db_path": str(db_path),
                        "table": table,
                        "row_id": str(row_id),
                        "title": title_value or (f"{{table}} {{row_id}}".replace("-", " ").replace("_", " ").strip() or "Untitled source"),
                        "content": content,
                        "fingerprint": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        "metadata": {{
                            "db_path": str(db_path),
                            "table": table,
                            "row_id": str(row_id),
                            "text_columns": text_columns,
                        }},
                    }})
            connection.close()

        print(json.dumps({{"items": items, "existing_db_paths": existing_db_paths}}))
        """
    )
    payload = _run_host_python(host, script)
    items: List[Dict[str, Any]] = []
    for row in payload["items"]:
        source_ref = (
            f"sqlite+ssh://{host}{row['db_path']}#{row['table']}/{row['row_id']}"
            if _is_remote_host(host)
            else f"sqlite://{Path(row['db_path']).resolve()}#{row['table']}/{row['row_id']}"
        )
        items.append(
            {
                "source_ref": source_ref,
                "title": row["title"],
                "content": row["content"],
                "fingerprint": row["fingerprint"],
                "adapter_id": source["source_id"],
                "source_type": source.get("source_type", "sqlite_record"),
                "source_family": source.get("source_family", "sqlite_records"),
                "sensitivity_tier": source.get("sensitivity_tier", "tier_work_product"),
                "metadata": {
                    **row.get("metadata", {}),
                    "remote_host": host,
                },
            }
        )
    return items, {
        "source_id": source["source_id"],
        "kind": "sqlite",
        "enabled": source.get("enabled", True),
        "remote_host": host,
        "configured_db_paths": db_paths,
        "existing_db_paths": payload.get("existing_db_paths", []),
        "discovered_item_count": len(items),
    }


def _collect_library_items(root: Path) -> Dict[str, Any]:
    config = load_library_tracker_config(root)
    state = _load_library_tracker_state(root)
    previous_items = {item["source_ref"]: item for item in state.get("tracked_items", [])}
    current_items: List[Dict[str, Any]] = []
    source_summaries: List[Dict[str, Any]] = []
    enabled_sources = 0
    for source in config.get("sources", []):
        if not source.get("enabled", True):
            source_summaries.append(
                {
                    "source_id": source["source_id"],
                    "kind": source["kind"],
                    "enabled": False,
                    "discovered_item_count": 0,
                }
            )
            continue
        enabled_sources += 1
        if source["kind"] == "filesystem":
            items, summary = _scan_filesystem_source(source)
        elif source["kind"] == "sqlite":
            items, summary = _scan_sqlite_source(source)
        else:
            items, summary = [], {
                "source_id": source["source_id"],
                "kind": source["kind"],
                "enabled": True,
                "discovered_item_count": 0,
                "error": f"Unsupported source kind: {source['kind']}",
            }
        current_items.extend(items)
        source_summaries.append(summary)

    current_items.sort(key=lambda item: (item["adapter_id"], item["source_ref"]))
    current_by_ref = {item["source_ref"]: item for item in current_items}
    new_items = [item for ref, item in current_by_ref.items() if ref not in previous_items]
    changed_items = [
        item
        for ref, item in current_by_ref.items()
        if ref in previous_items and previous_items[ref].get("fingerprint") != item["fingerprint"]
    ]
    unchanged_items = [
        item
        for ref, item in current_by_ref.items()
        if ref in previous_items and previous_items[ref].get("fingerprint") == item["fingerprint"]
    ]
    deleted_items = [item for ref, item in previous_items.items() if ref not in current_by_ref]
    scanned_at = utc_now()
    payload = {
        "scanned_at": scanned_at,
        "config_path": str(_config_path(root)),
        "state_path": str(_state_path(root)),
        "counts": {
            "configured_sources": len(config.get("sources", [])),
            "enabled_sources": enabled_sources,
            "tracked": len(current_items),
            "new": len(new_items),
            "changed": len(changed_items),
            "unchanged": len(unchanged_items),
            "deleted": len(deleted_items),
        },
        "sources": source_summaries,
        "items": {
            "new": [_item_summary(item) for item in new_items],
            "changed": [_item_summary(item) for item in changed_items],
            "unchanged": [_item_summary(item) for item in unchanged_items],
            "deleted": list(deleted_items),
        },
        RAW_ITEM_KEY: {
            "current": current_items,
            "new": new_items,
            "changed": changed_items,
            "unchanged": unchanged_items,
            "deleted": deleted_items,
        },
    }
    return payload


def scan_library_sources(root: Path) -> Dict[str, Any]:
    payload = _collect_library_items(root)
    public = dict(payload)
    public.pop(RAW_ITEM_KEY, None)
    return public


def _bounded_pending_count(item_count: int, max_items: int | None = None, portion: float | None = None) -> int:
    if item_count <= 0:
        return 0
    limit = item_count
    if portion is not None:
        normalized = max(0.0, min(portion, 1.0))
        limit = 0 if normalized <= 0 else max(1, math.ceil(item_count * normalized))
    if max_items is not None:
        limit = min(limit, max(0, max_items))
    return min(limit, item_count)


def sync_library_sources(root: Path, *, max_items: int | None = None, portion: float | None = None) -> Dict[str, Any]:
    from .vault_ingest import ingest_text_items_batch, remove_source_by_ref

    state = _load_library_tracker_state(root)
    previous_items = {item["source_ref"]: item for item in state.get("tracked_items", [])}
    collected = _collect_library_items(root)
    raw = collected.pop(RAW_ITEM_KEY)
    ingested_refs: List[str] = []
    purged_refs: List[str] = []
    for item in raw["deleted"]:
        remove_source_by_ref(root, item["source_ref"])
        purged_refs.append(item["source_ref"])
    pending_items = raw["new"] + raw["changed"]
    selected_count = _bounded_pending_count(len(pending_items), max_items=max_items, portion=portion)
    selected_items = pending_items[:selected_count]
    selected_refs = {item["source_ref"] for item in selected_items}
    ingest_items = [
        {
            "title": item["title"],
            "content": item["content"],
            "source_ref": item["source_ref"],
            "source_type": item["source_type"],
            "source_family": item["source_family"],
            "sensitivity_tier": item.get("sensitivity_tier", "tier_work_product"),
            "metadata": item.get("metadata", {}),
        }
        for item in selected_items
    ]
    if ingest_items:
        ingest_text_items_batch(root, ingest_items)
        ingested_refs = [item["source_ref"] for item in ingest_items]
    scanned_at = collected["scanned_at"]
    tracked_items = []
    unchanged_refs = {item["source_ref"] for item in raw["unchanged"]}
    for item in raw["current"]:
        source_ref = item["source_ref"]
        if source_ref in unchanged_refs or source_ref in selected_refs:
            tracked_items.append(_state_item(item, scanned_at))
            continue
        previous = previous_items.get(source_ref)
        if previous:
            tracked_items.append({**previous, "last_seen_at": scanned_at})
    synced_at = utc_now()
    _save_library_tracker_state(
        root,
        {
            "updated_at": synced_at,
            "tracked_items": tracked_items,
            "last_scan": collected,
            "last_sync": {
                "synced_at": synced_at,
                "counts": collected["counts"],
                "ingested_item_count": len(ingested_refs),
                "purged_item_count": len(purged_refs),
                "deferred_item_count": len(pending_items) - len(ingested_refs),
                "ingested_source_refs": ingested_refs,
                "purged_source_refs": purged_refs,
            },
        },
    )
    return {
        **collected,
        "synced_at": synced_at,
        "ingested_item_count": len(ingested_refs),
        "purged_item_count": len(purged_refs),
        "deferred_item_count": len(pending_items) - len(ingested_refs),
        "requested_max_items": max_items,
        "requested_portion": portion,
        "ingested_source_refs": ingested_refs,
        "purged_source_refs": purged_refs,
    }


def _filter_text_score(text: str, query_tokens: set[str]) -> float:
    if not query_tokens:
        return 0.0
    from .vault_ingest import tokenize

    haystack = set(tokenize(text))
    if not haystack:
        return 0.0
    return sum(1 for token in query_tokens if token in haystack) / len(query_tokens)


def get_chunk_status(root: Path) -> Dict[str, Any]:
    governance = load_library_governance(root)
    from .vault_ingest import load_chunk_index_raw

    raw_chunks = load_chunk_index_raw(root)
    governed_chunks = resolve_governed_chunk_rows(root, raw_chunks, governance=governance)
    chunk_status_counts = Counter(row["governance_status"] for row in governed_chunks)
    content_kind_counts = Counter(row.get("content_kind", "unknown") for row in governed_chunks)
    curation_class_counts = Counter()
    dimension_key_counts = Counter()
    connected_chunk_count = 0
    for row in governed_chunks:
        if row.get("related_chunk_ids"):
            connected_chunk_count += 1
        for key in row.get("curation_classes", []):
            curation_class_counts[key] += 1
        for key in row.get("metadata_dimensions", {}):
            dimension_key_counts[key] += 1
    return {
        "governance_path": governance["governance_path"],
        "raw_chunk_count": len(raw_chunks),
        "governed_chunk_count": len(governed_chunks),
        "runtime_chunk_count": sum(1 for row in governed_chunks if row.get("include_in_runtime", True)),
        "connected_chunk_count": connected_chunk_count,
        "chunk_policy_count": len(governance.get("chunk_policies", [])),
        "manual_chunk_link_count": len(governance.get("chunk_links", [])),
        "chunk_status_counts": dict(chunk_status_counts),
        "content_kind_counts": dict(content_kind_counts),
        "curation_class_counts": dict(curation_class_counts),
        "dimension_key_counts": dict(dimension_key_counts.most_common(20)),
        "pending_rederive": governance.get("pending_rederive"),
    }


def _match_governed_chunks(
    root: Path,
    *,
    query: str = "",
    regex: str = "",
    statuses: Iterable[str] | None = None,
    source_families: Iterable[str] | None = None,
    source_ref: str | None = None,
    content_kinds: Iterable[str] | None = None,
    speaker_roles: Iterable[str] | None = None,
    semantic_classes: Iterable[str] | None = None,
    dimension_filters: Dict[str, List[str]] | None = None,
    include_in_runtime: bool | None = None,
) -> Dict[str, Any]:
    from .vault_ingest import tokenize

    governance = load_library_governance(root)
    chunks = resolve_governed_chunk_rows(root, governance=governance)
    query_tokens = set(tokenize(query))
    regex_pattern = re.compile(regex, re.IGNORECASE) if regex else None
    status_filter = set(statuses or [])
    family_filter = set(source_families or [])
    content_kind_filter = set(content_kinds or [])
    speaker_role_filter = set(speaker_roles or [])
    semantic_class_filter = set(semantic_classes or [])
    normalized_dimension_filters = {
        key: [item for item in _dimension_values(values)]
        for key, values in (dimension_filters or {}).items()
        if _dimension_values(values)
    }

    matches: List[Dict[str, Any]] = []
    for row in chunks:
        if source_ref and row.get("source_ref") != source_ref:
            continue
        if status_filter and row.get("governance_status") not in status_filter:
            continue
        if family_filter and row.get("source_family") not in family_filter:
            continue
        if content_kind_filter and row.get("content_kind") not in content_kind_filter:
            continue
        if speaker_role_filter and row.get("metadata", {}).get("speaker_role", "") not in speaker_role_filter:
            continue
        if semantic_class_filter and not semantic_class_filter.intersection(row.get("curation_classes", [])):
            continue
        if include_in_runtime is not None and bool(row.get("include_in_runtime", True)) != include_in_runtime:
            continue
        dimensions = row.get("metadata_dimensions", {})
        dimension_match = True
        for key, expected_values in normalized_dimension_filters.items():
            actual_values = set(_dimension_values(dimensions.get(key)))
            if not actual_values.intersection(expected_values):
                dimension_match = False
                break
        if not dimension_match:
            continue
        haystack = _semantic_text(row)
        score = _filter_text_score(haystack, query_tokens)
        regex_hit = bool(regex_pattern.search(haystack)) if regex_pattern else False
        if regex and not regex_hit:
            continue
        if query and score <= 0:
            continue
        matches.append(
            {
                **row,
                "_match_score": (score or 0.0) + (1.0 if regex_hit else 0.0),
            }
        )
    matches.sort(
        key=lambda row: (
            -float(row.get("_match_score", 0.0)),
            row.get("governance_status", ""),
            row.get("source_ref", ""),
            int(row.get("chunk_index", 0)),
        )
    )
    return {
        "matches": matches,
        "filters": {
            "query": query,
            "regex": regex,
            "statuses": sorted(status_filter),
            "source_families": sorted(family_filter),
            "source_ref": source_ref or "",
            "content_kinds": sorted(content_kind_filter),
            "speaker_roles": sorted(speaker_role_filter),
            "semantic_classes": sorted(semantic_class_filter),
            "dimension_filters": normalized_dimension_filters,
            "include_in_runtime": include_in_runtime,
        },
    }


def filter_governed_chunks(
    root: Path,
    *,
    query: str = "",
    regex: str = "",
    statuses: Iterable[str] | None = None,
    source_families: Iterable[str] | None = None,
    source_ref: str | None = None,
    content_kinds: Iterable[str] | None = None,
    speaker_roles: Iterable[str] | None = None,
    semantic_classes: Iterable[str] | None = None,
    dimension_filters: Dict[str, List[str]] | None = None,
    include_in_runtime: bool | None = None,
    limit: int = 20,
) -> Dict[str, Any]:
    from .vault_ingest import shorten, tokenize

    del tokenize
    match_payload = _match_governed_chunks(
        root,
        query=query,
        regex=regex,
        statuses=statuses,
        source_families=source_families,
        source_ref=source_ref,
        content_kinds=content_kinds,
        speaker_roles=speaker_roles,
        semantic_classes=semantic_classes,
        dimension_filters=dimension_filters,
        include_in_runtime=include_in_runtime,
    )
    results = []
    for row in match_payload["matches"]:
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
                "curation_classes": row.get("curation_classes", []),
                "curation_signals": row.get("curation_signals", {}),
                "metadata_dimensions": row.get("metadata_dimensions", {}),
                "related_chunk_ids": row.get("related_chunk_ids", []),
                "preview_excerpt": shorten(row.get("content", ""), 220),
                "match_score": row.get("_match_score", 0.0),
            }
        )
    return {
        "count": len(results),
        "results": results[:limit],
        "filters": match_payload["filters"] | {"limit": limit},
    }


def _matched_prune_targets(
    root: Path,
    *,
    scope: str,
    query: str = "",
    regex: str = "",
    statuses: Iterable[str] | None = None,
    source_families: Iterable[str] | None = None,
    source_ref: str | None = None,
    content_kinds: Iterable[str] | None = None,
    speaker_roles: Iterable[str] | None = None,
    semantic_classes: Iterable[str] | None = None,
    dimension_filters: Dict[str, List[str]] | None = None,
    include_in_runtime: bool | None = None,
) -> Dict[str, Any]:
    match_payload = _match_governed_chunks(
        root,
        query=query,
        regex=regex,
        statuses=statuses,
        source_families=source_families,
        source_ref=source_ref,
        content_kinds=content_kinds,
        speaker_roles=speaker_roles,
        semantic_classes=semantic_classes,
        dimension_filters=dimension_filters,
        include_in_runtime=include_in_runtime,
    )
    matched_chunks = match_payload["matches"]
    source_refs = sorted({row["source_ref"] for row in matched_chunks})
    source_lookup = get_governed_source_lookup(root)
    source_chunks: Dict[str, List[Dict[str, Any]]] = {}
    for row in resolve_governed_chunk_rows(root):
        source_chunks.setdefault(row["source_ref"], []).append(row)
    matched_sources = []
    for ref in source_refs:
        source_row = source_lookup.get(ref, {})
        profile = _source_curation_profile(source_row, source_chunks.get(ref, []))
        matched_sources.append(
            {
                "source_ref": ref,
                "title": source_row.get("title", ""),
                "source_family": source_row.get("source_family", ""),
                "semantic_role": source_row.get("semantic_role", ""),
                "governance_status": source_row.get("governance_status", "active"),
                "chunk_count": len(source_chunks.get(ref, [])),
                "curation_classes": profile["classes"],
                "curation_signals": profile["signals"],
            }
        )
    affected_chunk_rows = matched_chunks
    if scope == "source":
        affected_chunk_rows = []
        for ref in source_refs:
            affected_chunk_rows.extend(source_chunks.get(ref, []))
    return {
        "scope": scope,
        "filters": match_payload["filters"],
        "matched_chunks": matched_chunks,
        "matched_sources": matched_sources,
        "affected_chunks": affected_chunk_rows,
        "affected_source_refs": source_refs,
    }


def _prune_impact_preview(root: Path, *, affected_chunks: List[Dict[str, Any]], affected_source_refs: List[str]) -> Dict[str, Any]:
    affected_chunk_ids = {row["chunk_id"] for row in affected_chunks}
    affected_source_refs_set = set(affected_source_refs)
    from .context_bubbles import load_context_bubbles
    from .conversation_synthesis import load_concept_nodes
    from .knowledge_layer import load_knowledge_edges
    from .meta_layer import load_meta_records
    from .thought_factory import load_thought_packets

    meta_rows = [
        row
        for row in load_meta_records(root)
        if affected_chunk_ids.intersection(row.get("chunk_ids", [])) or affected_source_refs_set.intersection(row.get("source_refs", []))
    ]
    bubbles = [
        row
        for row in load_context_bubbles(root)
        if affected_chunk_ids.intersection(row.get("chunk_ids", [])) or affected_source_refs_set.intersection(row.get("source_refs", []))
    ]
    knowledge_edges = [
        row
        for row in load_knowledge_edges(root)
        if affected_source_refs_set.intersection(row.get("evidence_refs", []))
    ]
    thoughts = [
        row
        for row in load_thought_packets(root)
        if affected_source_refs_set.intersection(row.get("source_refs", [])) or affected_chunk_ids.intersection(row.get("source_item_ids", []))
    ]
    concepts = [
        row
        for row in load_concept_nodes(root)
        if affected_source_refs_set.intersection(row.get("source_refs", []))
    ]
    return {
        "source_count": len(affected_source_refs_set),
        "chunk_count": len(affected_chunk_ids),
        "meta_record_count": len(meta_rows),
        "bubble_count": len(bubbles),
        "knowledge_edge_count": len(knowledge_edges),
        "thought_count": len(thoughts),
        "concept_count": len(concepts),
        "sample_meta_ids": [row["meta_id"] for row in meta_rows[:8]],
        "sample_bubble_ids": [row["bubble_id"] for row in bubbles[:8]],
        "sample_thought_ids": [row["thought_id"] for row in thoughts[:8]],
    }


def _prune_rederive_plan(scope: str, target_status: str, targets: List[str]) -> Dict[str, Any]:
    if scope == "source":
        plan = _rederive_plan_for_fields({"governance_status"}, f"Prune {target_status}")
    else:
        plan = _chunk_rederive_plan_for_fields({"governance_status"}, f"{scope}:{target_status}")
    plan["targets"] = list(targets)
    return plan


def preview_prune_candidates(
    root: Path,
    *,
    scope: str = "chunk",
    query: str = "",
    regex: str = "",
    statuses: Iterable[str] | None = None,
    source_families: Iterable[str] | None = None,
    source_ref: str | None = None,
    content_kinds: Iterable[str] | None = None,
    speaker_roles: Iterable[str] | None = None,
    semantic_classes: Iterable[str] | None = None,
    dimension_filters: Dict[str, List[str]] | None = None,
    include_in_runtime: bool | None = None,
    target_status: str | None = None,
    limit: int = 20,
) -> Dict[str, Any]:
    matched = _matched_prune_targets(
        root,
        scope=scope,
        query=query,
        regex=regex,
        statuses=statuses,
        source_families=source_families,
        source_ref=source_ref,
        content_kinds=content_kinds,
        speaker_roles=speaker_roles,
        semantic_classes=semantic_classes,
        dimension_filters=dimension_filters,
        include_in_runtime=include_in_runtime,
    )
    affected_chunks = matched["affected_chunks"]
    affected_source_refs = matched["affected_source_refs"]
    targets = [row["chunk_id"] for row in matched["matched_chunks"]] if scope == "chunk" else affected_source_refs
    return {
        "scope": scope,
        "match_count": len(targets),
        "matched_source_count": len(affected_source_refs),
        "preview": {
            "chunks": [
                {
                    "chunk_id": row["chunk_id"],
                    "source_ref": row["source_ref"],
                    "title": row.get("title", ""),
                    "governance_status": row.get("governance_status", "active"),
                    "curation_classes": row.get("curation_classes", []),
                    "curation_signals": row.get("curation_signals", {}),
                }
                for row in matched["matched_chunks"][:limit]
            ],
            "sources": matched["matched_sources"][:limit],
        },
        "impact": _prune_impact_preview(root, affected_chunks=affected_chunks, affected_source_refs=affected_source_refs),
        "rederive_plan": _prune_rederive_plan(scope, target_status, targets) if target_status else None,
        "filters": matched["filters"] | {"scope": scope, "limit": limit, "target_status": target_status or ""},
    }


def apply_prune_candidates(
    root: Path,
    *,
    scope: str = "chunk",
    target_status: str,
    query: str = "",
    regex: str = "",
    statuses: Iterable[str] | None = None,
    source_families: Iterable[str] | None = None,
    source_ref: str | None = None,
    content_kinds: Iterable[str] | None = None,
    speaker_roles: Iterable[str] | None = None,
    semantic_classes: Iterable[str] | None = None,
    dimension_filters: Dict[str, List[str]] | None = None,
    include_in_runtime: bool | None = None,
    notes: str | None = None,
    limit: int = 20,
) -> Dict[str, Any]:
    matched = _matched_prune_targets(
        root,
        scope=scope,
        query=query,
        regex=regex,
        statuses=statuses,
        source_families=source_families,
        source_ref=source_ref,
        content_kinds=content_kinds,
        speaker_roles=speaker_roles,
        semantic_classes=semantic_classes,
        dimension_filters=dimension_filters,
        include_in_runtime=include_in_runtime,
    )
    governance = load_library_governance(root)
    applied_targets: List[str] = []
    if scope == "source":
        for source_item in matched["matched_sources"]:
            patch = {"governance_status": target_status}
            if notes is not None:
                patch["notes"] = notes
            _upsert_policy(governance["source_policies"], "source_ref", source_item["source_ref"], patch)
            applied_targets.append(source_item["source_ref"])
    else:
        for row in matched["matched_chunks"]:
            patch = {"governance_status": target_status}
            if notes is not None:
                patch["notes"] = notes
            _upsert_policy(governance["chunk_policies"], "chunk_id", row["chunk_id"], patch)
            applied_targets.append(row["chunk_id"])
    plan = _prune_rederive_plan(scope, target_status, applied_targets)
    governance["pending_rederive"] = _merge_rederive_plans(governance.get("pending_rederive"), plan)
    governance["updated_at"] = utc_now()
    governance.setdefault("prune_actions", []).append(
        {
            "applied_at": utc_now(),
            "scope": scope,
            "target_status": target_status,
            "target_count": len(applied_targets),
            "filters": matched["filters"],
            "targets": applied_targets[:200],
            "notes": notes or "",
        }
    )
    _save_library_governance(root, governance)
    return {
        "status": "applied",
        "scope": scope,
        "target_status": target_status,
        "applied_count": len(applied_targets),
        "applied_targets": applied_targets[:limit],
        "impact": _prune_impact_preview(
            root,
            affected_chunks=matched["affected_chunks"],
            affected_source_refs=matched["affected_source_refs"],
        ),
        "pending_rederive": governance.get("pending_rederive"),
        "filters": matched["filters"] | {"scope": scope, "limit": limit},
    }


def get_library_status(root: Path) -> Dict[str, Any]:
    config = load_library_tracker_config(root)
    state = _load_library_tracker_state(root)
    governance = load_library_governance(root)
    dimension_registry = load_dimension_registry(root)
    from .vault_ingest import load_chunk_index_raw, load_source_registry_raw

    raw_sources = load_source_registry_raw(root)
    governed_sources = resolve_governed_source_rows(root, raw_sources, governance=governance)
    raw_chunks = load_chunk_index_raw(root)
    governed_chunks = resolve_governed_chunk_rows(root, raw_chunks, governance=governance)
    dimension_profiles = load_chunk_dimension_profiles(root, refresh=False)
    status_counts = Counter(row["governance_status"] for row in governed_sources)
    semantic_role_counts = Counter(row["semantic_role"] for row in governed_sources)
    chunk_status_counts = Counter(row["governance_status"] for row in governed_chunks)
    curation_class_counts = Counter()
    source_chunks: Dict[str, List[Dict[str, Any]]] = {}
    source_curation_counts = Counter()
    dimension_key_counts = Counter()
    connected_chunk_count = 0
    for row in governed_chunks:
        if row.get("related_chunk_ids"):
            connected_chunk_count += 1
        source_chunks.setdefault(row.get("source_ref", ""), []).append(row)
        for key in row.get("curation_classes", []):
            curation_class_counts[key] += 1
        for key in row.get("metadata_dimensions", {}):
            dimension_key_counts[key] += 1
    for source in governed_sources:
        profile = _source_curation_profile(source, source_chunks.get(source.get("source_ref", ""), []))
        for key in profile["classes"]:
            source_curation_counts[key] += 1
    return {
        "config_path": str(_config_path(root)),
        "state_path": str(_state_path(root)),
        "governance_path": governance["governance_path"],
        "dimension_registry_path": dimension_registry["registry_path"],
        "configured_sources": len(config.get("sources", [])),
        "enabled_sources": sum(1 for source in config.get("sources", []) if source.get("enabled", True)),
        "tracked_item_count": len(state.get("tracked_items", [])),
        "source_registry_count": len(raw_sources),
        "governed_source_count": len(governed_sources),
        "policy_counts": {
            "family_policies": len(governance.get("family_policies", [])),
            "source_policies": len(governance.get("source_policies", [])),
            "chunk_policies": len(governance.get("chunk_policies", [])),
            "chunk_links": len(governance.get("chunk_links", [])),
            "prune_actions": len(governance.get("prune_actions", [])),
        },
        "status_counts": dict(status_counts),
        "semantic_role_counts": dict(semantic_role_counts),
        "dimension_registry": {
            "dimension_count": len(dimension_registry.get("dimensions", [])),
            "enabled_dimension_count": sum(
                1
                for row in dimension_registry.get("dimensions", [])
                if row.get("enabled", True)
            ),
            "model_assisted_dimension_count": sum(
                1
                for row in dimension_registry.get("dimensions", [])
                if row.get("requires_model", False)
            ),
            "dimension_ids": dimension_registry.get("dimension_ids", [])[:16],
        },
        "chunk_dimension_profiles": {
            "profile_count": dimension_profiles["profile_count"],
            "covered_chunk_count": dimension_profiles["covered_chunk_count"],
            "profile_path": dimension_profiles["profile_path"],
            "per_dimension_counts": dict(
                Counter(dimension_profiles["per_dimension_counts"]).most_common(16)
            ),
        },
        "chunk_counts": {
            "raw_chunk_count": len(raw_chunks),
            "governed_chunk_count": len(governed_chunks),
            "runtime_chunk_count": sum(1 for row in governed_chunks if row.get("include_in_runtime", True)),
            "connected_chunk_count": connected_chunk_count,
        },
        "chunk_status_counts": dict(chunk_status_counts),
        "chunk_curation_class_counts": dict(curation_class_counts),
        "source_curation_class_counts": dict(source_curation_counts),
        "chunk_dimension_key_counts": dict(dimension_key_counts.most_common(16)),
        "pending_rederive": governance.get("pending_rederive"),
        "last_applied_rederive": governance.get("last_applied_rederive"),
        "sources": [
            {
                "source_id": source["source_id"],
                "kind": source["kind"],
                "enabled": source.get("enabled", True),
            }
            for source in config.get("sources", [])
        ],
        "last_scan": state.get("last_scan"),
        "last_sync": state.get("last_sync"),
    }
