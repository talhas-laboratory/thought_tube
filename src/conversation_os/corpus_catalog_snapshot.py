"""Materialized CorpusCatalog snapshots for O(1) request-path readiness (R-006).

T10-04 ocean readiness: published snapshots carry family inventory digests,
ambiguous-placement review reasons (never invent branch/scope), legacy
signature candidate-only markers, dependency indexes for withdrawal/staleness,
seed-pilot status, and reproducible rebuild metadata.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping

from .library_tracker import (
    CHAT_CONVERTER_SEED_CORPUS_ID,
    CHAT_CONVERTER_SEED_FRAGMENT_COUNT,
    CHAT_CONVERTER_SEED_SOURCE_COUNT,
    CORPUS_CATALOG_CONTRACT_VERSION,
)
from .runtime_layout import product_runtime_dir
from .storage import read_json, utc_now


MODULE_ID = "kernel.disclosure.corpus_catalog_snapshot"
CONTRACT_VERSION = "1.0"
SNAPSHOT_SCHEMA_VERSION = "1.1"
OCEAN_READINESS_CONTRACT_VERSION = "1.0"
# Gap-program legacy deterministic signature inventory (candidate-only evidence).
LEGACY_DETERMINISTIC_SIGNATURE_TARGET = 454

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "SNAPSHOT_SCHEMA_VERSION",
    "OCEAN_READINESS_CONTRACT_VERSION",
    "LEGACY_DETERMINISTIC_SIGNATURE_TARGET",
    "corpus_catalog_snapshot_path",
    "compute_generation_marker",
    "publish_corpus_catalog_snapshot",
    "load_corpus_catalog_for_request",
    "invalidate_corpus_catalog_cache",
    "enrich_catalog_ocean_readiness",
)
__all__ = list(PUBLIC_API)

_PROCESS_CACHE: dict[str, dict[str, Any]] = {}

_FAMILY_IDS = (
    "sources",
    "fragments",
    "library_governance",
    "pipeline_last_run",
    "knowledge_nodes",
    "semantic_capsules",
    "shape_signatures",
    "shape_graph_nodes",
    "shape_graph_edges",
)


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


def _file_content_digest(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 64)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _family_inventory(root: Path) -> Dict[str, Any]:
    paths = _watched_index_paths(root)
    families: Dict[str, Any] = {}
    for family_id, path in zip(_FAMILY_IDS, paths, strict=True):
        exists = path.exists()
        size = int(path.stat().st_size) if exists and path.is_file() else 0
        families[family_id] = {
            "family_id": family_id,
            "path_name": path.name,
            "present": exists,
            "byte_size": size,
            "watermark": _path_watermark(path),
            "content_digest": _file_content_digest(path) if exists and path.is_file() else "",
            "schema_hint": path.suffix.lstrip(".") or "unknown",
        }
    inventory_digest = hashlib.sha256(
        json.dumps(
            {key: families[key]["content_digest"] or families[key]["watermark"] for key in _FAMILY_IDS},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "families": families,
        "inventory_digest": inventory_digest,
        "family_count": len(families),
        "present_count": sum(1 for row in families.values() if row["present"]),
    }


def _coverage_float(coverage: Mapping[str, Any], key: str) -> float:
    try:
        return float(coverage.get(key, 0.0) or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _ambiguous_placement_review(catalog: Mapping[str, Any]) -> Dict[str, Any]:
    """Surface incomplete branch/scope as review — never invent placement."""
    counts = catalog.get("counts") if isinstance(catalog.get("counts"), Mapping) else {}
    coverage = catalog.get("coverage") if isinstance(catalog.get("coverage"), Mapping) else {}
    source_count = int(counts.get("source_count", 0) or 0)
    fragment_count = int(counts.get("fragment_count", 0) or 0)
    reasons: list[str] = []
    if source_count > 0 and _coverage_float(coverage, "branch_coverage") < 1.0:
        reasons.append("ambiguous_source_branch")
    if source_count > 0 and _coverage_float(coverage, "scope_coverage") < 1.0:
        reasons.append("ambiguous_source_scope")
    if fragment_count > 0 and _coverage_float(coverage, "fragment_branch_coverage") < 1.0:
        reasons.append("ambiguous_fragment_branch")
    if fragment_count > 0 and _coverage_float(coverage, "fragment_scope_coverage") < 1.0:
        reasons.append("ambiguous_fragment_scope")
    return {
        "review_required": bool(reasons),
        "reasons": reasons,
        "policy": "do_not_invent_branch_or_scope",
        "routing": "review_queue" if reasons else "none",
    }


def _seed_pilot_status(catalog: Mapping[str, Any]) -> Dict[str, Any]:
    corpus_id = str(catalog.get("corpus_id", "") or "")
    counts = catalog.get("counts") if isinstance(catalog.get("counts"), Mapping) else {}
    source_count = int(counts.get("source_count", 0) or 0)
    fragment_count = int(counts.get("fragment_count", 0) or 0)
    if corpus_id != CHAT_CONVERTER_SEED_CORPUS_ID:
        return {
            "pilot_id": "chat_converter_seed_v1",
            "status": "not_applicable",
            "expected_source_count": CHAT_CONVERTER_SEED_SOURCE_COUNT,
            "expected_fragment_count": CHAT_CONVERTER_SEED_FRAGMENT_COUNT,
            "observed_source_count": source_count,
            "observed_fragment_count": fragment_count,
            "matched": False,
        }
    matched = (
        source_count == CHAT_CONVERTER_SEED_SOURCE_COUNT
        and fragment_count == CHAT_CONVERTER_SEED_FRAGMENT_COUNT
    )
    return {
        "pilot_id": "chat_converter_seed_v1",
        "status": "matched" if matched else ("mismatch" if source_count > 0 else "not_started"),
        "expected_source_count": CHAT_CONVERTER_SEED_SOURCE_COUNT,
        "expected_fragment_count": CHAT_CONVERTER_SEED_FRAGMENT_COUNT,
        "observed_source_count": source_count,
        "observed_fragment_count": fragment_count,
        "matched": matched,
    }


def _legacy_signature_policy(catalog: Mapping[str, Any]) -> Dict[str, Any]:
    shape = catalog.get("shape_artifacts") if isinstance(catalog.get("shape_artifacts"), Mapping) else {}
    signature_count = int(shape.get("signature_count", 0) or 0)
    return {
        "candidate_only": True,
        "promotion_forbidden": True,
        "comparison_evidence_only": True,
        "target_inventory_count": LEGACY_DETERMINISTIC_SIGNATURE_TARGET,
        "observed_signature_count": signature_count,
        "capability_id": "structural_shape_legacy",
        "notes": (
            "Deterministic legacy signatures are retained only as candidate/comparison "
            "evidence; they must not merge or promote into canonical Shape authority."
        ),
    }


def _dependency_indexes(root: Path, *, generation_marker: str, inventory: Mapping[str, Any]) -> Dict[str, Any]:
    families = inventory.get("families") if isinstance(inventory.get("families"), Mapping) else {}
    # Withdrawal of sources/fragments stales downstream derived families only.
    withdrawal_edges = [
        {"from": "sources", "to": "fragments", "effect": "stale"},
        {"from": "sources", "to": "knowledge_nodes", "effect": "stale"},
        {"from": "sources", "to": "semantic_capsules", "effect": "stale"},
        {"from": "sources", "to": "shape_signatures", "effect": "stale"},
        {"from": "sources", "to": "shape_graph_nodes", "effect": "stale"},
        {"from": "sources", "to": "shape_graph_edges", "effect": "stale"},
        {"from": "fragments", "to": "knowledge_nodes", "effect": "stale"},
        {"from": "fragments", "to": "semantic_capsules", "effect": "stale"},
        {"from": "library_governance", "to": "fragments", "effect": "permission_or_correction_stale"},
    ]
    return {
        "indexed": True,
        "generation_marker": generation_marker,
        "watched_family_ids": list(_FAMILY_IDS),
        "withdrawal": {
            "edges": withdrawal_edges,
            "policy": "source_removal_stales_all_and_only_dependent_projections",
        },
        "staleness": {
            "marker_kind": "watched_index_watermarks",
            "generation_marker": generation_marker,
            "inventory_digest": str(inventory.get("inventory_digest", "") or ""),
        },
        "permission_change": {
            "trigger_families": ["library_governance"],
            "propagates_to": ["fragments", "knowledge_nodes", "semantic_capsules"],
        },
        "family_presence": {
            family_id: bool((families.get(family_id) or {}).get("present"))
            for family_id in _FAMILY_IDS
        },
    }


def _rebuild_metadata(
    *,
    generation_marker: str,
    catalog: Mapping[str, Any],
    inventory: Mapping[str, Any],
) -> Dict[str, Any]:
    manifest = {
        "builder": "library_tracker.build_corpus_catalog",
        "enricher": "corpus_catalog_snapshot.enrich_catalog_ocean_readiness",
        "snapshot_schema_version": SNAPSHOT_SCHEMA_VERSION,
        "ocean_readiness_contract_version": OCEAN_READINESS_CONTRACT_VERSION,
        "corpus_id": str(catalog.get("corpus_id", "") or ""),
        "corpus_revision": str(catalog.get("corpus_revision", "") or ""),
        "generation_marker": generation_marker,
        "inventory_digest": str(inventory.get("inventory_digest", "") or ""),
    }
    content_digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "reproducible": True,
        "transformation_manifest": manifest,
        "content_digest": content_digest,
        "notes": "Deterministic rebuild from sources plus transformation manifests; no silent defaults.",
    }


def enrich_catalog_ocean_readiness(
    root: Path,
    catalog: Mapping[str, Any],
    *,
    generation_marker: str | None = None,
) -> Dict[str, Any]:
    """Attach T10-04 ocean readiness fields; demote readiness on ambiguous placement."""
    enriched = dict(catalog)
    marker = generation_marker or compute_generation_marker(root)
    inventory = _family_inventory(root)
    ambiguous = _ambiguous_placement_review(enriched)
    seed_pilot = _seed_pilot_status(enriched)
    legacy = _legacy_signature_policy(enriched)
    dependency_indexes = _dependency_indexes(root, generation_marker=marker, inventory=inventory)
    rebuild = _rebuild_metadata(generation_marker=marker, catalog=enriched, inventory=inventory)

    ocean = {
        "contract_version": OCEAN_READINESS_CONTRACT_VERSION,
        "complete": True,
        "family_inventory": inventory,
        "ambiguous_placement": ambiguous,
        "legacy_signatures": legacy,
        "dependency_indexes": dependency_indexes,
        "seed_pilot": seed_pilot,
        "rebuild": rebuild,
    }
    enriched["ocean_readiness"] = ocean

    # Fail closed: incomplete branch/scope never invents placement and is not retrieval-ready.
    if ambiguous["review_required"] and enriched.get("readiness_state") == "ready":
        enriched["readiness_state"] = "stale"
        enriched["retrieval_allowed"] = False
        enriched["quality_claims_allowed"] = False
        enriched["abstention_reason"] = "corpus_ocean_ambiguous_placement"
        staleness = dict(enriched.get("staleness") or {})
        staleness["ambiguous_placement"] = True
        enriched["staleness"] = staleness
    return enriched


def _empty_ocean_readiness(*, generation_marker: str = "", complete: bool = False) -> Dict[str, Any]:
    return {
        "contract_version": OCEAN_READINESS_CONTRACT_VERSION,
        "complete": complete,
        "family_inventory": {
            "families": {},
            "inventory_digest": "",
            "family_count": 0,
            "present_count": 0,
        },
        "ambiguous_placement": {
            "review_required": False,
            "reasons": [],
            "policy": "do_not_invent_branch_or_scope",
            "routing": "none",
        },
        "legacy_signatures": {
            "candidate_only": True,
            "promotion_forbidden": True,
            "comparison_evidence_only": True,
            "target_inventory_count": LEGACY_DETERMINISTIC_SIGNATURE_TARGET,
            "observed_signature_count": 0,
            "capability_id": "structural_shape_legacy",
            "notes": "Deterministic legacy signatures are candidate/comparison evidence only.",
        },
        "dependency_indexes": {
            "indexed": False,
            "generation_marker": generation_marker,
            "watched_family_ids": list(_FAMILY_IDS),
            "withdrawal": {"edges": [], "policy": "source_removal_stales_all_and_only_dependent_projections"},
            "staleness": {
                "marker_kind": "watched_index_watermarks",
                "generation_marker": generation_marker,
                "inventory_digest": "",
            },
            "permission_change": {
                "trigger_families": ["library_governance"],
                "propagates_to": ["fragments", "knowledge_nodes", "semantic_capsules"],
            },
            "family_presence": {},
        },
        "seed_pilot": {
            "pilot_id": "chat_converter_seed_v1",
            "status": "not_applicable",
            "expected_source_count": CHAT_CONVERTER_SEED_SOURCE_COUNT,
            "expected_fragment_count": CHAT_CONVERTER_SEED_FRAGMENT_COUNT,
            "observed_source_count": 0,
            "observed_fragment_count": 0,
            "matched": False,
        },
        "rebuild": {
            "reproducible": False,
            "transformation_manifest": {},
            "content_digest": "",
            "notes": "Snapshot absent or incomplete; rebuild required.",
        },
    }


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
            "ocean_incomplete": abstention_reason == "corpus_ocean_not_ready",
        },
        "ocean_readiness": _empty_ocean_readiness(generation_marker=generation_marker, complete=False),
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
    catalog = enrich_catalog_ocean_readiness(
        root,
        catalog,
        generation_marker=generation_marker,
    )
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


def _ocean_readiness_complete(catalog: Mapping[str, Any]) -> bool:
    ocean = catalog.get("ocean_readiness")
    if not isinstance(ocean, Mapping):
        return False
    if not bool(ocean.get("complete")):
        return False
    inventory = ocean.get("family_inventory")
    legacy = ocean.get("legacy_signatures")
    deps = ocean.get("dependency_indexes")
    rebuild = ocean.get("rebuild")
    if not isinstance(inventory, Mapping) or not inventory.get("inventory_digest"):
        return False
    if not isinstance(legacy, Mapping) or not bool(legacy.get("candidate_only")):
        return False
    if not isinstance(deps, Mapping) or not bool(deps.get("indexed")):
        return False
    if not isinstance(rebuild, Mapping) or not bool(rebuild.get("reproducible")):
        return False
    return True


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
        if not _ocean_readiness_complete(catalog):
            return _abstained_catalog(
                corpus_id=normalized,
                abstention_reason="corpus_ocean_not_ready",
                generation_marker=generation_marker,
            )
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
    if not _ocean_readiness_complete(catalog):
        return _abstained_catalog(
            corpus_id=normalized,
            abstention_reason="corpus_ocean_not_ready",
            generation_marker=generation_marker,
        )

    catalog["snapshot"] = {
        "generation_marker": generation_marker,
        "served_from_snapshot": True,
    }
    _PROCESS_CACHE[cache_key] = {
        "generation_marker": generation_marker,
        "catalog": dict(catalog),
    }
    return catalog
