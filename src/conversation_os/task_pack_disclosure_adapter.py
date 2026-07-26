"""Task-pack evidence adapter for the shared disclosure service (CAE-010)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from .disclosure_ports import build_inner_world_ports
from .storage import read_json
from .vault_ingest import tokenize


MODULE_ID = "kernel.disclosure.task_pack_adapter"
CONTRACT_VERSION = "1.0"
DEFAULT_MAX_EVIDENCE_BLOCKS = 4

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "load_task_pack_disclosure_config",
    "task_pack_disclosure_service_enabled",
    "build_task_pack_evidence_query",
    "map_retrieval_bundle_to_evidence_blocks",
    "collect_task_pack_evidence",
    "enrich_task_pack_with_bounded_evidence",
)
__all__ = list(PUBLIC_API)


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def load_task_pack_disclosure_config(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    task_pack = runtime.get("task_pack", {}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    return {
        "disclosure_service_v1": bool(
            task_pack.get(
                "disclosure_service_v1",
                disclosure.get("task_pack_disclosure_service_v1", False),
            )
        ),
        "max_evidence_blocks": max(
            1,
            int(task_pack.get("max_evidence_blocks", DEFAULT_MAX_EVIDENCE_BLOCKS) or DEFAULT_MAX_EVIDENCE_BLOCKS),
        ),
        "retrieval_limit": int(task_pack.get("evidence_retrieval_limit", 6) or 6),
        "neighbor_limit": int(task_pack.get("evidence_neighbor_limit", 4) or 4),
    }


def task_pack_disclosure_service_enabled(root: Path) -> bool:
    return bool(load_task_pack_disclosure_config(root)["disclosure_service_v1"])


def build_task_pack_evidence_query(request: str, domain_overlays: Sequence[str] | None = None) -> str:
    parts = [str(value).strip() for value in [request, *(domain_overlays or [])] if str(value).strip()]
    return " ".join(parts)


def _query_tokens(query: str) -> set[str]:
    return {token.lower() for token in tokenize(query) if token.strip()}


def map_retrieval_bundle_to_evidence_blocks(
    retrieval_bundle: Mapping[str, Any],
    *,
    query: str,
    max_blocks: int,
) -> List[Dict[str, Any]]:
    query_tokens = _query_tokens(query)
    blocks: List[Dict[str, Any]] = []
    seen_refs: set[str] = set()
    for row in list(retrieval_bundle.get("seed_capsules", []) or []) + list(
        retrieval_bundle.get("related_capsules", []) or []
    ):
        source_refs = [str(value).strip() for value in row.get("source_refs", []) or [] if str(value).strip()]
        source_ref = source_refs[0] if source_refs else str(row.get("capsule_id", "") or "")
        if not source_ref or source_ref in seen_refs:
            continue
        text = " ".join([str(row.get("label", "")), str(row.get("summary", ""))])
        matched_terms = sorted(_query_tokens(text) & query_tokens)
        if not matched_terms:
            continue
        seen_refs.add(source_ref)
        blocks.append(
            {
                "block_id": str(row.get("capsule_id", "") or source_ref),
                "source_ref": source_ref,
                "label": str(row.get("label", "") or source_ref),
                "summary": str(row.get("summary", ""))[:480],
                "matched_terms": matched_terms,
                "confidence": float(row.get("confidence", 0.0) or 0.0),
                "provenance": {
                    "surface": "task_pack",
                    "disclosure_result_status": str(retrieval_bundle.get("result_status", "") or ""),
                    "source_refs": source_refs,
                },
            }
        )
        if len(blocks) >= max(1, int(max_blocks)):
            break
    return blocks


def collect_task_pack_evidence(
    root: Path,
    request: str,
    *,
    domain_overlays: Sequence[str] | None = None,
) -> Dict[str, Any]:
    config = load_task_pack_disclosure_config(root)
    query = build_task_pack_evidence_query(request, domain_overlays)
    if not query.strip():
        return {"count": 0, "result_status": "empty_no_positive_match", "blocks": []}

    ports = build_inner_world_ports()
    retrieval_bundle = ports.candidate_search.build_retrieval_bundle(
        root,
        query,
        limit=max(1, int(config["retrieval_limit"])),
        neighbor_limit=max(0, int(config["neighbor_limit"])),
        include_cross_pond=False,
    )
    blocks = map_retrieval_bundle_to_evidence_blocks(
        retrieval_bundle,
        query=query,
        max_blocks=int(config["max_evidence_blocks"]),
    )
    result_status = str(retrieval_bundle.get("result_status", "") or "")
    if not blocks:
        return {
            "count": 0,
            "result_status": result_status or "empty_no_positive_match",
            "blocks": [],
            "query": query,
        }
    return {
        "count": len(blocks),
        "result_status": result_status or "disclosed",
        "query": query,
        "blocks": blocks,
        "provenance": {
            "surface": "task_pack",
            "adapter_version": CONTRACT_VERSION,
            "reference_only": True,
        },
    }


def enrich_task_pack_with_bounded_evidence(
    root: Path,
    pack: Mapping[str, Any],
    *,
    request: str,
    domain_overlays: Sequence[str] | None = None,
) -> Dict[str, Any]:
    payload = dict(pack)
    if not task_pack_disclosure_service_enabled(root):
        return payload
    evidence = collect_task_pack_evidence(root, request, domain_overlays=domain_overlays)
    if int(evidence.get("count", 0) or 0) > 0:
        payload["bounded_evidence"] = evidence
    return payload
