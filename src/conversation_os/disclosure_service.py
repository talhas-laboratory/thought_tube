"""Shared disclosure service orchestration boundary (CAE-005A)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Dict, Mapping

from .disclosure_ports import DisclosurePorts, build_inner_world_ports
from .storage import read_json


MODULE_ID = "kernel.disclosure.disclosure_service"
CONTRACT_VERSION = "1.0"

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "DisclosureService",
    "disclosure_service_enabled",
    "load_disclosure_service_config",
    "build_default_disclosure_service",
)
__all__ = list(PUBLIC_API)

BridgeBundleAssembler = Callable[..., Dict[str, Any]]


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def load_disclosure_service_config(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    bridge = runtime.get("bridge", {}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    return {
        "disclosure_service_v1": bool(
            bridge.get(
                "disclosure_service_v1",
                disclosure.get("disclosure_service_v1", False),
            )
        ),
    }


def disclosure_service_enabled(root: Path) -> bool:
    from .disclosure_rollout import resolve_surface_rollout_mode

    return resolve_surface_rollout_mode(root, "bridge") != "legacy"


class DisclosureService:
    """Orchestrates disclosure through storage-independent ports (ADR-002)."""

    def __init__(
        self,
        ports: DisclosurePorts,
        *,
        assemble_bridge_bundle: BridgeBundleAssembler,
    ) -> None:
        self.ports = ports
        self.assemble_bridge_bundle = assemble_bridge_bundle

    def disclose_for_bridge(
        self,
        root: Path,
        context_state: Mapping[str, Any],
        *,
        budget: Mapping[str, Any] | None = None,
        corpus_id: str = "local_runtime",
    ) -> Dict[str, Any]:
        started = time.perf_counter()
        catalog = self.ports.catalog.build_corpus_catalog(root, corpus_id=corpus_id)
        readiness = str(catalog.get("readiness_state", "") or "")
        request_id = str(context_state.get("request_id", "") or "")
        if readiness in {"interrupted", "unsupported"}:
            abstained_grant = {
                "grant_id": "",
                "request_id": request_id,
                "envelope": "bounded",
                "effective_layers": [],
                "effective_refs": [],
                "dimensions": [],
                "shape_maturity": "candidate",
                "cross_ocean": False,
                "token_budget": 0,
                "persistence_mode": "gated",
                "explicit_pins": [],
                "narrowing_reasons": [],
                "deny_precedence_applied": False,
                "requested_grant_ref": "",
            }
            receipt = self.ports.receipt_sink.record_disclosure_receipt(
                root,
                request_id=request_id,
                result_status="abstained_dependency_not_ready",
                effective_grant=abstained_grant,
                corpus_catalog=catalog,
                frame_audit={},
                frame_bundle={"included_blocks": [], "assembly_status": "empty"},
                metrics={"corpus_readiness_state": readiness},
                surface="bridge",
            )
            return {
                "context_state": dict(context_state),
                "result_status": "abstained_dependency_not_ready",
                "disclosure_service_v1": True,
                "corpus_catalog": catalog,
                "frame_bundle": {"assembly_status": "empty", "included_blocks": []},
                "frame_audit": {},
                "budget": dict(budget or {}),
                "global_fallback": {"count": 0},
                "disclosure_receipt": receipt,
            }

        bundle = dict(
            self.assemble_bridge_bundle(
                root,
                dict(context_state),
                budget=dict(budget) if budget else None,
                candidate_search=self.ports.candidate_search,
            )
        )
        request_id = str(
            bundle.get("context_state", {}).get("request_id", "")
            or context_state.get("request_id", "")
            or ""
        )
        effective_grant = dict(bundle.get("effective_grant", {}) or {})
        frame_audit = dict(bundle.get("frame_audit", {}) or {})
        result_status = str(bundle.get("result_status", "") or "disclosed")
        latency_ms = round((time.perf_counter() - started) * 1000.0, 3)

        shape_summary = self.ports.shape_reader.read_shape_projections(root, include_legacy=True)
        included_blocks = list(bundle.get("frame_bundle", {}).get("included_blocks", []) or [])
        resolution = self.ports.evidence_resolver.resolve_frame_blocks(
            root,
            included_blocks=included_blocks,
            effective_grant=effective_grant,
        )
        resolved_blocks = list(resolution.get("resolved_blocks", []) or [])
        resolution_audit = dict(resolution.get("resolution_audit", {}) or {})
        if resolution_audit:
            frame_audit = dict(frame_audit)
            frame_audit["evidence_resolution"] = resolution_audit
            for row in list(resolution_audit.get("omitted", []) or []):
                frame_audit.setdefault("omitted_blocks", [])
                frame_audit["omitted_blocks"].append(
                    {
                        "block_id": row.get("block_id", ""),
                        "reason_code": row.get("reason_code", "evidence_resolution_omitted"),
                        "reason": row.get("reason", ""),
                    }
                )
        receipt = self.ports.receipt_sink.record_disclosure_receipt(
            root,
            request_id=request_id,
            result_status=result_status,
            effective_grant=effective_grant,
            budget_ledger=dict(
                frame_audit.get("budget_ledger", {})
                or bundle.get("budget_audit", {}).get("budget_ledger", {})
                or {}
            ),
            frame_audit=frame_audit,
            metrics={
                "latency_ms": latency_ms,
                "resolved_block_count": len(resolved_blocks),
                "corpus_readiness_state": readiness,
                "bytes_resolved": int(resolution_audit.get("bytes_resolved", 0) or 0),
                "evidence_lookup_count": int(resolution_audit.get("lookup_count", 0) or 0),
                "included_span_ids": [
                    str(row.get("fragment_id", "") or "")
                    for row in list(resolution_audit.get("included_spans", []) or [])
                    if str(row.get("fragment_id", "") or "").strip()
                ],
            },
            frame_bundle=dict(bundle.get("frame_bundle", {}) or {}),
            corpus_catalog=catalog,
            retrieval_bundle=dict(bundle.get("global_fallback", {}) or {}),
            surface="bridge",
            workspace_id=str(bundle.get("context_state", {}).get("active_workspace_id", "") or ""),
        )

        bundle["disclosure_service_v1"] = True
        bundle["corpus_catalog"] = catalog
        legacy_shape = dict(shape_summary.get("legacy", {}) or {})
        bundle["shape_projection_summary"] = {
            "readiness_state": shape_summary.get("readiness_state", ""),
            "projection_count": len(legacy_shape.get("candidate_projections", []) or [])
            + len(legacy_shape.get("anti_match_projections", []) or []),
            "legacy_adapter_version": str(legacy_shape.get("adapter_version", "") or ""),
        }
        bundle["disclosure_receipt"] = receipt
        bundle["service_metrics"] = {
            "latency_ms": latency_ms,
            "resolved_block_count": len(resolved_blocks),
        }
        if not bundle.get("result_status"):
            bundle["result_status"] = result_status
        return bundle


def build_default_disclosure_service(
    *,
    assemble_bridge_bundle: BridgeBundleAssembler,
    ports: DisclosurePorts | None = None,
) -> DisclosureService:
    return DisclosureService(
        ports=ports or build_inner_world_ports(),
        assemble_bridge_bundle=assemble_bridge_bundle,
    )
