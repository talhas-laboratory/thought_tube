"""Feed surface adapter for the shared disclosure service (CAE-009)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from .disclosure_ports import build_inner_world_ports
from .storage import make_id, read_json
from .vault_ingest import tokenize


MODULE_ID = "kernel.disclosure.feed_adapter"
CONTRACT_VERSION = "1.0"

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "load_feed_disclosure_config",
    "feed_disclosure_service_enabled",
    "build_feed_evidence_query",
    "build_feed_effective_grant",
    "feed_evidence_decision_subset",
    "map_retrieval_bundle_to_feed_pairs",
    "collect_feed_evidence_pairs",
    "record_feed_disclosure_receipt",
)
__all__ = list(PUBLIC_API)


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def load_feed_disclosure_config(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    feed = runtime.get("feed", {}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    return {
        "disclosure_service_v1": bool(
            feed.get(
                "disclosure_service_v1",
                disclosure.get("feed_disclosure_service_v1", False),
            )
        ),
        "retrieval_limit": int(feed.get("evidence_retrieval_limit", 8) or 8),
        "neighbor_limit": int(feed.get("evidence_neighbor_limit", 4) or 4),
    }


def feed_disclosure_service_enabled(root: Path) -> bool:
    return bool(load_feed_disclosure_config(root)["disclosure_service_v1"])


def build_feed_evidence_query(domain_overlays: Sequence[str] | None = None) -> str:
    overlays = [str(value).strip() for value in (domain_overlays or []) if str(value).strip()]
    if overlays:
        return " ".join(overlays)
    return "context insight connection evidence"


def build_feed_effective_grant(root: Path, domain_overlays: Sequence[str] | None = None):
    from .disclosure_contracts import RequestedGrant, normalize_effective_grant

    _ = root
    requested = RequestedGrant(
        grant_id=make_id("grant"),
        request_id=make_id("feed-req"),
        envelope="bounded",
        requested_layers=["session", "workspace", "governed_global"],
        requested_refs=[],
        dimensions=[str(value) for value in (domain_overlays or []) if str(value).strip()],
        shape_maturity="candidate",
        token_budget=0,
        persistence_mode="gated",
        explicit_pins=[],
        explicit_denials=[],
        cross_ocean=False,
    )
    return normalize_effective_grant(
        requested,
        workspace_layers=["session", "workspace", "user", "governed_global"],
    )


def feed_evidence_decision_subset(retrieval_bundle: Mapping[str, Any]) -> Dict[str, Any]:
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


def _capsule_as_meta(row: Mapping[str, Any]) -> Dict[str, Any]:
    source_refs = [str(value).strip() for value in row.get("source_refs", []) or [] if str(value).strip()]
    capsule_id = str(row.get("capsule_id", "") or "").strip()
    return {
        "meta_id": f"disclosure-{capsule_id or make_id('capsule')}",
        "kind": "concept",
        "label": str(row.get("label", "") or capsule_id or "Disclosure candidate"),
        "summary": str(row.get("summary", "") or ""),
        "source_refs": source_refs,
        "chunk_ids": [],
        "evidence": [str(row.get("summary", "") or "")],
        "confidence": float(row.get("confidence", 0.0) or 0.0),
        "attributes": {
            "disclosure_capsule_id": capsule_id,
            "disclosure_result_status": str(row.get("disclosure_result_status", "") or ""),
        },
    }


def _companion_meta(primary: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "meta_id": f"{primary['meta_id']}-context",
        "kind": "shared_primitive",
        "label": "Feed evidence context",
        "summary": "Bounded feed evidence context for admitted disclosure candidates.",
        "source_refs": list(primary.get("source_refs", []) or []),
        "chunk_ids": [],
        "evidence": [],
        "confidence": max(0.45, float(primary.get("confidence", 0.0) or 0.0) - 0.1),
        "attributes": {"disclosure_companion": True},
    }


def _shared_tokens(left: Mapping[str, Any], right: Mapping[str, Any]) -> List[str]:
    left_terms = set(tokenize(" ".join([str(left.get("label", "")), str(left.get("summary", ""))])))
    right_terms = set(tokenize(" ".join([str(right.get("label", "")), str(right.get("summary", ""))])))
    return sorted(left_terms & right_terms)[:8]


def map_retrieval_bundle_to_feed_pairs(
    retrieval_bundle: Mapping[str, Any],
    *,
    effective_grant: Mapping[str, Any] | Any,
) -> List[Dict[str, Any]]:
    capsules = list(retrieval_bundle.get("seed_capsules", []) or []) + list(
        retrieval_bundle.get("related_capsules", []) or []
    )
    grant_dict = effective_grant.to_dict() if hasattr(effective_grant, "to_dict") else dict(effective_grant or {})
    source_refs = sorted(
        {
            str(source_ref).strip()
            for row in capsules
            for source_ref in row.get("source_refs", []) or []
            if str(source_ref).strip()
        }
    )
    provenance = {
        "surface": "feed",
        "result_status": str(retrieval_bundle.get("result_status", "") or ""),
        "capsule_ids": sorted(
            str(row.get("capsule_id", "") or "").strip()
            for row in capsules
            if str(row.get("capsule_id", "") or "").strip()
        ),
        "source_refs": source_refs,
        "grant_id": str(grant_dict.get("grant_id", "") or ""),
        "envelope": str(grant_dict.get("envelope", "bounded") or "bounded"),
    }
    meta_rows = [_capsule_as_meta(row) for row in capsules]
    if not meta_rows:
        return []

    pairs: List[Dict[str, Any]] = []
    if len(meta_rows) == 1:
        left = meta_rows[0]
        right = _companion_meta(left)
        pair_rows = [(left, right)]
    else:
        pair_rows = [(meta_rows[index], meta_rows[index + 1]) for index in range(len(meta_rows) - 1)]

    for left, right in pair_rows:
        pairs.append(
            {
                "left": left,
                "right": right,
                "edge_kind": "disclosure_semantic",
                "score": round(
                    min(
                        0.99,
                        0.55 + ((float(left.get("confidence", 0.0)) + float(right.get("confidence", 0.0))) / 2) * 0.35,
                    ),
                    3,
                ),
                "shared_tokens": _shared_tokens(left, right),
                "evidence_refs": sorted(set(list(left.get("source_refs", []) or []) + list(right.get("source_refs", []) or []))),
                "disclosure_provenance": dict(provenance),
                "disclosure_grant": dict(grant_dict),
            }
        )
    pairs.sort(key=lambda item: (-item["score"], item["left"]["label"]))
    return pairs


def collect_feed_evidence_pairs(
    root: Path,
    *,
    limit: int,
    domain_overlays: Sequence[str] | None = None,
) -> tuple[List[Dict[str, Any]], Dict[str, Any], List[str]]:
    query = build_feed_evidence_query(domain_overlays)
    config = load_feed_disclosure_config(root)
    effective_grant = build_feed_effective_grant(root, domain_overlays)
    ports = build_inner_world_ports()
    retrieval_bundle = ports.candidate_search.build_retrieval_bundle(
        root,
        query,
        limit=max(1, int(config["retrieval_limit"])),
        neighbor_limit=max(0, int(config["neighbor_limit"])),
        include_cross_pond=False,
    )
    pairs = map_retrieval_bundle_to_feed_pairs(retrieval_bundle, effective_grant=effective_grant)
    consulted_layers = ["disclosure_service"]
    if int(retrieval_bundle.get("count", 0) or 0) > 0:
        consulted_layers.append("semantic_retrieval")
    return pairs[:limit], retrieval_bundle, consulted_layers


def record_feed_disclosure_receipt(
    root: Path,
    *,
    retrieval_bundle: Mapping[str, Any],
    effective_grant: Mapping[str, Any] | Any,
    pair_count: int,
) -> Dict[str, Any] | None:
    from .disclosure_receipts import persistent_receipts_enabled, record_disclosure_receipt

    if not persistent_receipts_enabled(root):
        return None
    grant_dict = effective_grant.to_dict() if hasattr(effective_grant, "to_dict") else dict(effective_grant or {})
    subset = feed_evidence_decision_subset(retrieval_bundle)
    return record_disclosure_receipt(
        root,
        request_id=str(grant_dict.get("request_id", "") or make_id("feed-req")),
        surface="feed",
        effective_grant=grant_dict,
        retrieval_bundle=retrieval_bundle,
        result_status=str(retrieval_bundle.get("result_status", "") or "empty_no_positive_match"),
        metrics={
            "pair_count": int(pair_count),
            "candidate_count": int(subset.get("count", 0) or 0),
        },
    )
