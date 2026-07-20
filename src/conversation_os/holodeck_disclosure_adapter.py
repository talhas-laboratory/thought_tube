"""Holodeck surface adapter for the shared disclosure service (CAE-005B)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping

from .disclosure_ports import build_inner_world_ports
from .storage import read_json
from .vault_ingest import tokenize


MODULE_ID = "kernel.disclosure.holodeck_adapter"
CONTRACT_VERSION = "1.0"

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "load_holodeck_disclosure_config",
    "holodeck_disclosure_service_enabled",
    "build_contextualization_query",
    "retrieval_decision_subset",
    "map_retrieval_bundle_to_candidates",
    "collect_disclosure_knowledge_candidates",
)
__all__ = list(PUBLIC_API)


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def load_holodeck_disclosure_config(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    holodeck = runtime.get("holodeck", {}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    return {
        "disclosure_service_v1": bool(
            holodeck.get(
                "disclosure_service_v1",
                disclosure.get("holodeck_disclosure_service_v1", False),
            )
        ),
        "retrieval_limit": int(holodeck.get("contextualization_retrieval_limit", 6) or 6),
        "neighbor_limit": int(holodeck.get("contextualization_neighbor_limit", 4) or 4),
    }


def holodeck_disclosure_service_enabled(root: Path) -> bool:
    from .disclosure_rollout import resolve_surface_rollout_mode

    return resolve_surface_rollout_mode(root, "holodeck") != "legacy"


def build_contextualization_query(seed_bundle: Mapping[str, Any]) -> str:
    topic_terms = list(seed_bundle.get("topic_terms", []) or [])
    if topic_terms:
        return " ".join(str(term) for term in topic_terms if str(term).strip())
    combined = list(seed_bundle.get("combined_terms", []) or [])
    return " ".join(str(term) for term in combined[:16] if str(term).strip())


def _matched_seed_terms(seed_terms: Iterable[str], text: str) -> List[str]:
    seed_set = {str(term).strip().lower() for term in seed_terms if str(term).strip()}
    if not seed_set:
        return []
    text_terms = {token.lower() for token in tokenize(text)}
    return sorted(seed_set & text_terms)


def retrieval_decision_subset(retrieval_bundle: Mapping[str, Any]) -> Dict[str, Any]:
    capsule_ids: List[str] = []
    source_refs: List[str] = []
    for row in list(retrieval_bundle.get("seed_capsules", []) or []) + list(
        retrieval_bundle.get("related_capsules", []) or []
    ):
        capsule_id = str(row.get("capsule_id", "") or "").strip()
        if capsule_id:
            capsule_ids.append(capsule_id)
        for source_ref in row.get("source_refs", []) or []:
            ref = str(source_ref).strip()
            if ref and ref not in source_refs:
                source_refs.append(ref)
    return {
        "count": int(retrieval_bundle.get("count", 0) or 0),
        "result_status": str(retrieval_bundle.get("result_status", "") or ""),
        "capsule_ids": sorted(capsule_ids),
        "source_refs": sorted(source_refs),
    }


def map_retrieval_bundle_to_candidates(
    retrieval_bundle: Mapping[str, Any],
    seed_bundle: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    seed_terms = list(seed_bundle.get("combined_terms", []) or [])
    candidates: List[Dict[str, Any]] = []
    seen_refs: set[str] = set()
    for row in list(retrieval_bundle.get("seed_capsules", []) or []) + list(
        retrieval_bundle.get("related_capsules", []) or []
    ):
        source_refs = [str(value).strip() for value in row.get("source_refs", []) or [] if str(value).strip()]
        source_ref = source_refs[0] if source_refs else str(row.get("capsule_id", "") or "")
        if not source_ref or source_ref in seen_refs:
            continue
        seen_refs.add(source_ref)
        text = " ".join([str(row.get("label", "")), str(row.get("summary", ""))])
        matched_terms = _matched_seed_terms(seed_terms, text)
        confidence = float(row.get("confidence", 0.0) or 0.0)
        score = max(int(round(confidence * 100)), len(matched_terms) * 10)
        candidates.append(
            {
                "candidate_kind": "knowledge",
                "source_layer": "disclosure_semantic",
                "source_ref": source_ref,
                "title": str(row.get("label", "") or row.get("capsule_id", "")),
                "statement": str(row.get("summary", "")),
                "matched_terms": matched_terms,
                "score": score,
                "confidence": min(0.93, confidence or 0.55),
                "capsule_id": str(row.get("capsule_id", "") or ""),
                "disclosure_result_status": str(retrieval_bundle.get("result_status", "") or ""),
            }
        )
    candidates.sort(key=lambda item: (-item.get("score", 0), -float(item.get("confidence", 0)), item.get("title", "")))
    return candidates


def collect_disclosure_knowledge_candidates(
    root: Path,
    seed_bundle: Mapping[str, Any],
    *,
    max_source_refs: int,
) -> tuple[List[Dict[str, Any]], List[str]]:
    query = build_contextualization_query(seed_bundle)
    if not query.strip():
        return [], ["disclosure_service"]

    config = load_holodeck_disclosure_config(root)
    limit = max(1, min(int(max_source_refs), int(config["retrieval_limit"])))
    neighbor_limit = max(0, min(int(max_source_refs), int(config["neighbor_limit"])))

    ports = build_inner_world_ports()
    retrieval_bundle = ports.candidate_search.build_retrieval_bundle(
        root,
        query,
        limit=limit,
        neighbor_limit=neighbor_limit,
        include_cross_pond=False,
    )
    candidates = map_retrieval_bundle_to_candidates(retrieval_bundle, seed_bundle)
    consulted_layers = ["disclosure_service"]
    if int(retrieval_bundle.get("count", 0) or 0) > 0:
        consulted_layers.append("semantic_retrieval")
    return candidates[: max_source_refs * 4], consulted_layers
