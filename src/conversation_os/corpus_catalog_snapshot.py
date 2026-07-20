"""Materialized CorpusCatalog snapshots for O(1) request-path readiness (R-006)."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .library_tracker import CORPUS_CATALOG_CONTRACT_VERSION
from .runtime_layout import product_runtime_dir
from .storage import read_json, utc_now


MODULE_ID = "kernel.disclosure.corpus_catalog_snapshot"
CONTRACT_VERSION = "1.0"
SNAPSHOT_SCHEMA_VERSION = "1.0"

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "SNAPSHOT_SCHEMA_VERSION",
    "corpus_catalog_snapshot_path",
    "compute_generation_marker",
    "publish_corpus_catalog_snapshot",
    "load_corpus_catalog_for_request",
    "invalidate_corpus_catalog_cache",
)
__all__ = list(PUBLIC_API)

_PROCESS_CACHE: dict[str, dict[str, Any]] = {}


def _data_dir(root: Path) -> Path:
    return product_runtime_dir(root, "inner_world_v1", "data")


def _snapshot_dir(root: Path) -> Path:
    return _data_dir(root) / "corpus_catalog_snapshots"


def corpus_catalog_snapshot_path(root: Path, *, corpus_id: str = "local_runtime") -> Path:
    normalized = str(corpus_id or "local_runtime").strip() or "local_runtime"
    return _snapshot_dir(root) / f"{normalized}.json"


def _watched_index_paths(root: Path) -> list[Path]:
    from .meta_layer import shape_graph_edges_path, shape_graph_nodes_path, shape_signatures_path
    from .runtime_pipeline import _last_run_path
    from .vault_ingest import _chunk_index_path, _source_registry_path

    data_dir = _data_dir(root)
    return [
        _source_registry_path(root),
        _chunk_index_path(root),
        data_dir / "library_governance.json",
        _last_run_path(root),
        data_dir / "knowledge_nodes.jsonl",
        data_dir / "semantic_capsules.jsonl",
        shape_signatures_path(root),
        shape_graph_nodes_path(root),
        shape_graph_edges_path(root),
    ]


def _path_watermark(path: Path) -> str:
    if not path.exists():
        return f"missing:{path.name}"
    stat = path.stat()
    return f"{path.name}:{stat.st_mtime_ns}:{stat.st_size}"


def compute_generation_marker(root: Path) -> str:
    """Cheap revision marker from source-index watermarks (no corpus load)."""
    parts = [_path_watermark(path) for path in _watched_index_paths(root)]
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:32]


def _cache_key(root: Path, corpus_id: str) -> str:
    return f"{root.resolve()}::{corpus_id}"


def invalidate_corpus_catalog_cache(root: Path | None = None) -> None:
    if root is None:
        _PROCESS_CACHE.clear()
        return
    prefix = f"{root.resolve()}::"
    for key in list(_PROCESS_CACHE):
        if key.startswith(prefix):
            del _PROCESS_CACHE[key]


def _write_snapshot_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.parent / f".{path.name}.{uuid.uuid4().hex}.tmp"
    try:
        temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _abstained_catalog(
    *,
    corpus_id: str,
    abstention_reason: str,
    generation_marker: str = "",
) -> Dict[str, Any]:
    return {
        "schema_version": CORPUS_CATALOG_CONTRACT_VERSION,
        "contract_id": "CorpusCatalog",
        "corpus_id": corpus_id,
        "corpus_revision": "",
        "readiness_state": "stale",
        "retrieval_allowed": False,
        "quality_claims_allowed": False,
        "abstention_reason": abstention_reason,
        "counts": {
            "source_count": 0,
            "fragment_count": 0,
            "indexed_record_count": 0,
        },
        "coverage": {
            "provenance_coverage": 0.0,
            "fragment_provenance_coverage": 0.0,
            "branch_coverage": 0.0,
            "scope_coverage": 0.0,
            "shape_coverage": 0.0,
            "fragment_branch_coverage": 0.0,
            "fragment_scope_coverage": 0.0,
        },
        "shape_artifacts": {
            "signature_count": 0,
            "graph_node_count": 0,
            "graph_edge_count": 0,
        },
        "capabilities": {
            "supported": [],
            "available": {},
            "required": [],
            "unsupported_required": [],
        },
        "pipeline": {"pipeline_present": False},
        "staleness": {
            "pending_rederive": False,
            "seed_mismatch": False,
            "interrupted": False,
            "snapshot_missing": abstention_reason == "corpus_catalog_snapshot_missing",
            "snapshot_stale": abstention_reason == "corpus_catalog_snapshot_stale",
        },
        "snapshot": {
            "generation_marker": generation_marker,
            "served_from_snapshot": False,
        },
        "generated_at": utc_now(),
    }


def publish_corpus_catalog_snapshot(
    root: Path,
    *,
    corpus_id: str = "local_runtime",
    required_capabilities: Iterable[str] | None = None,
) -> Dict[str, Any]:
    """Rebuild and persist a CorpusCatalog snapshot (pipeline / ingestion only)."""
    from .library_tracker import build_corpus_catalog

    normalized = str(corpus_id or "local_runtime").strip() or "local_runtime"
    catalog = build_corpus_catalog(
        root,
        corpus_id=normalized,
        required_capabilities=required_capabilities,
    )
    generation_marker = compute_generation_marker(root)
    snapshot = {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "contract_id": "CorpusCatalogSnapshot",
        "corpus_id": normalized,
        "generation_marker": generation_marker,
        "published_at": utc_now(),
        "catalog": catalog,
    }
    path = corpus_catalog_snapshot_path(root, corpus_id=normalized)
    _write_snapshot_atomic(path, snapshot)
    invalidate_corpus_catalog_cache(root)
    _PROCESS_CACHE[_cache_key(root, normalized)] = {
        "generation_marker": generation_marker,
        "catalog": dict(catalog),
    }
    return snapshot


def _read_snapshot_file(root: Path, *, corpus_id: str) -> Dict[str, Any] | None:
    path = corpus_catalog_snapshot_path(root, corpus_id=corpus_id)
    payload = read_json(path, default=None)
    if not isinstance(payload, dict):
        return None
    catalog = payload.get("catalog")
    if not isinstance(catalog, dict):
        return None
    return payload


def load_corpus_catalog_for_request(
    root: Path,
    *,
    corpus_id: str = "local_runtime",
) -> Dict[str, Any]:
    """Request-path catalog load: snapshot read + marker check only (never rebuild)."""
    normalized = str(corpus_id or "local_runtime").strip() or "local_runtime"
    generation_marker = compute_generation_marker(root)
    cache_key = _cache_key(root, normalized)
    cached = _PROCESS_CACHE.get(cache_key)
    if cached and cached.get("generation_marker") == generation_marker:
        catalog = dict(cached["catalog"])
        catalog["snapshot"] = {
            "generation_marker": generation_marker,
            "served_from_snapshot": True,
        }
        return catalog

    snapshot = _read_snapshot_file(root, corpus_id=normalized)
    if snapshot is None:
        return _abstained_catalog(
            corpus_id=normalized,
            abstention_reason="corpus_catalog_snapshot_missing",
            generation_marker=generation_marker,
        )

    snapshot_marker = str(snapshot.get("generation_marker", "") or "")
    if snapshot_marker != generation_marker:
        return _abstained_catalog(
            corpus_id=normalized,
            abstention_reason="corpus_catalog_snapshot_stale",
            generation_marker=generation_marker,
        )

    catalog = dict(snapshot.get("catalog", {}) or {})
    catalog["snapshot"] = {
        "generation_marker": generation_marker,
        "served_from_snapshot": True,
    }
    _PROCESS_CACHE[cache_key] = {
        "generation_marker": generation_marker,
        "catalog": dict(catalog),
    }
    return catalog
