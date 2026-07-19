"""Storage-independent ports for the disclosure service (CAE-005A / ADR-002)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Mapping, Protocol, runtime_checkable


MODULE_ID = "kernel.disclosure.ports"
CONTRACT_VERSION = "1.0"

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "CorpusCatalogPort",
    "CandidateSearchPort",
    "ShapeProjectionReaderPort",
    "EvidenceResolverPort",
    "ReceiptSinkPort",
    "DisclosurePorts",
    "InnerWorldDisclosurePorts",
    "build_inner_world_ports",
)
__all__ = list(PUBLIC_API)


@runtime_checkable
class CorpusCatalogPort(Protocol):
    def build_corpus_catalog(self, root: Path, *, corpus_id: str = "local_runtime") -> Dict[str, Any]: ...


@runtime_checkable
class CandidateSearchPort(Protocol):
    def build_retrieval_bundle(
        self,
        root: Path,
        query: str,
        *,
        limit: int = 10,
        neighbor_limit: int = 6,
        include_cross_pond: bool = False,
        envelope_mode: str = "open",
        explicit_pins: list[str] | None = None,
    ) -> Dict[str, Any]: ...


@runtime_checkable
class ShapeProjectionReaderPort(Protocol):
    def read_shape_projections(
        self,
        root: Path,
        *,
        branch_id: str = "",
        scope_id: str = "",
        source_refs: list[str] | None = None,
        include_legacy: bool = True,
        include_anti_match: bool = True,
    ) -> Dict[str, Any]: ...


@runtime_checkable
class EvidenceResolverPort(Protocol):
    def resolve_frame_blocks(
        self,
        root: Path,
        *,
        included_blocks: list[Dict[str, Any]],
        effective_grant: Mapping[str, Any],
    ) -> list[Dict[str, Any]]: ...


@runtime_checkable
class ReceiptSinkPort(Protocol):
    def record_disclosure_receipt(
        self,
        root: Path,
        *,
        request_id: str,
        result_status: str,
        effective_grant: Mapping[str, Any],
        budget_ledger: Mapping[str, Any] | None = None,
        frame_audit: Mapping[str, Any] | None = None,
        metrics: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]: ...


@dataclass(frozen=True)
class DisclosurePorts:
    catalog: CorpusCatalogPort
    candidate_search: CandidateSearchPort
    shape_reader: ShapeProjectionReaderPort
    evidence_resolver: EvidenceResolverPort
    receipt_sink: ReceiptSinkPort


class _InnerWorldCorpusCatalog:
    def build_corpus_catalog(self, root: Path, *, corpus_id: str = "local_runtime") -> Dict[str, Any]:
        from .library_tracker import build_corpus_catalog

        return build_corpus_catalog(root, corpus_id=corpus_id)


class _InnerWorldCandidateSearch:
    def build_retrieval_bundle(
        self,
        root: Path,
        query: str,
        *,
        limit: int = 10,
        neighbor_limit: int = 6,
        include_cross_pond: bool = False,
        envelope_mode: str = "open",
        explicit_pins: list[str] | None = None,
    ) -> Dict[str, Any]:
        from .knowledge_layer import build_retrieval_bundle

        return build_retrieval_bundle(
            root,
            query,
            limit=limit,
            neighbor_limit=neighbor_limit,
            include_cross_pond=include_cross_pond,
            envelope_mode=envelope_mode,
            explicit_pins=explicit_pins,
        )


class _InnerWorldShapeReader:
    def read_shape_projections(
        self,
        root: Path,
        *,
        branch_id: str = "",
        scope_id: str = "",
        source_refs: list[str] | None = None,
        include_legacy: bool = True,
        include_anti_match: bool = True,
    ) -> Dict[str, Any]:
        from .shape_projection_reader import read_shape_projections

        return read_shape_projections(
            root,
            branch_id=branch_id,
            scope_id=scope_id,
            source_refs=source_refs,
            include_legacy=include_legacy,
            include_anti_match=include_anti_match,
        )


class _InnerWorldEvidenceResolver:
    def resolve_frame_blocks(
        self,
        root: Path,
        *,
        included_blocks: list[Dict[str, Any]],
        effective_grant: Mapping[str, Any],
    ) -> list[Dict[str, Any]]:
        _ = root, effective_grant
        return [dict(row) for row in included_blocks]


class _InMemoryReceiptSink:
    def __init__(self) -> None:
        self.records: list[Dict[str, Any]] = []

    def record_disclosure_receipt(
        self,
        root: Path,
        *,
        request_id: str,
        result_status: str,
        effective_grant: Mapping[str, Any],
        budget_ledger: Mapping[str, Any] | None = None,
        frame_audit: Mapping[str, Any] | None = None,
        metrics: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        _ = root
        record = {
            "request_id": request_id,
            "result_status": result_status,
            "effective_grant": dict(effective_grant),
            "budget_ledger": dict(budget_ledger or {}),
            "frame_audit_id": str((frame_audit or {}).get("audit_id", "") or ""),
            "metrics": dict(metrics or {}),
        }
        self.records.append(record)
        return record


def build_inner_world_ports(*, receipt_sink: ReceiptSinkPort | None = None) -> DisclosurePorts:
    return DisclosurePorts(
        catalog=_InnerWorldCorpusCatalog(),
        candidate_search=_InnerWorldCandidateSearch(),
        shape_reader=_InnerWorldShapeReader(),
        evidence_resolver=_InnerWorldEvidenceResolver(),
        receipt_sink=receipt_sink or _InMemoryReceiptSink(),
    )


InnerWorldDisclosurePorts = build_inner_world_ports
