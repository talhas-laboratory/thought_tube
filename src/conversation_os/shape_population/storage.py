"""Transactional provisional-candidate store for Shape population."""

from __future__ import annotations

import copy
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from conversation_os.storage import ensure_dir, make_id, read_json, utc_now, write_json

MODULE_ID = "kernel.shape_population.storage"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "shape_population_dir",
    "PopulationStore",
)
__all__ = list(PUBLIC_API)

_LOCK = threading.RLock()


def shape_population_dir(root: Path) -> Path:
    return ensure_dir(root / "product" / "inner_world_v1" / "data" / "shape_population")


class PopulationStore:
    """File-backed store with all-or-nothing transactional writes."""

    def __init__(self, root: Path):
        self.root = Path(root)
        self.base = shape_population_dir(self.root)
        self.sources_path = self.base / "normalized_sources.json"
        self.segments_path = self.base / "segments.json"
        self.packets_path = self.base / "evidence_packets.json"
        self.candidates_path = self.base / "candidates.json"
        self.evaluations_path = self.base / "evaluations.json"
        self.receipts_path = self.base / "receipts.json"
        self.idempotency_path = self.base / "idempotency.json"
        self.promotions_path = self.base / "promotion_requests.json"
        self.approvals_path = self.base / "human_approvals.json"
        self.canonical_projection_path = self.base / "canonical_projection.json"
        self._ensure_files()

    def _ensure_files(self) -> None:
        for path in (
            self.sources_path,
            self.segments_path,
            self.packets_path,
            self.candidates_path,
            self.evaluations_path,
            self.receipts_path,
            self.idempotency_path,
            self.promotions_path,
            self.approvals_path,
            self.canonical_projection_path,
        ):
            if not path.exists():
                write_json(path, {})

    def _load(self, path: Path) -> Dict[str, Any]:
        payload = read_json(path, default={})
        if not isinstance(payload, dict):
            return {}
        return payload

    def snapshot(self) -> Dict[str, Dict[str, Any]]:
        with _LOCK:
            return {
                "sources": copy.deepcopy(self._load(self.sources_path)),
                "segments": copy.deepcopy(self._load(self.segments_path)),
                "packets": copy.deepcopy(self._load(self.packets_path)),
                "candidates": copy.deepcopy(self._load(self.candidates_path)),
                "evaluations": copy.deepcopy(self._load(self.evaluations_path)),
                "receipts": copy.deepcopy(self._load(self.receipts_path)),
                "idempotency": copy.deepcopy(self._load(self.idempotency_path)),
                "promotions": copy.deepcopy(self._load(self.promotions_path)),
                "approvals": copy.deepcopy(self._load(self.approvals_path)),
                "canonical_projection": copy.deepcopy(self._load(self.canonical_projection_path)),
            }

    def restore(self, snap: Dict[str, Dict[str, Any]]) -> None:
        with _LOCK:
            write_json(self.sources_path, snap.get("sources", {}))
            write_json(self.segments_path, snap.get("segments", {}))
            write_json(self.packets_path, snap.get("packets", {}))
            write_json(self.candidates_path, snap.get("candidates", {}))
            write_json(self.evaluations_path, snap.get("evaluations", {}))
            write_json(self.receipts_path, snap.get("receipts", {}))
            write_json(self.idempotency_path, snap.get("idempotency", {}))
            write_json(self.promotions_path, snap.get("promotions", {}))
            write_json(self.approvals_path, snap.get("approvals", {}))
            write_json(self.canonical_projection_path, snap.get("canonical_projection", {}))

    def transaction(self):
        store = self

        class _Txn:
            def __enter__(self_inner):
                _LOCK.acquire()
                self_inner._snap = store.snapshot()
                return store

            def __exit__(self_inner, exc_type, exc, tb):
                try:
                    if exc_type is not None:
                        store.restore(self_inner._snap)
                finally:
                    _LOCK.release()
                return False

        return _Txn()

    def put_source(self, source: Dict[str, Any]) -> None:
        sources = self._load(self.sources_path)
        sources[source["source_id"]] = source
        write_json(self.sources_path, sources)
        segments = self._load(self.segments_path)
        for segment in source.get("segments") or []:
            segments[segment["segment_id"]] = segment
        write_json(self.segments_path, segments)

    def get_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        return self._load(self.sources_path).get(source_id)

    def get_segment(self, segment_id: str) -> Optional[Dict[str, Any]]:
        return self._load(self.segments_path).get(segment_id)

    def list_segments(self) -> List[Dict[str, Any]]:
        return list(self._load(self.segments_path).values())

    def put_packet(self, packet: Dict[str, Any]) -> None:
        packets = self._load(self.packets_path)
        packets[packet["packet_id"]] = packet
        write_json(self.packets_path, packets)

    def get_packet(self, packet_id: str) -> Optional[Dict[str, Any]]:
        return self._load(self.packets_path).get(packet_id)

    def put_candidate(self, candidate: Dict[str, Any]) -> None:
        candidates = self._load(self.candidates_path)
        candidates[candidate["candidate_id"]] = candidate
        write_json(self.candidates_path, candidates)

    def get_candidate(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        return self._load(self.candidates_path).get(candidate_id)

    def list_candidates(self) -> List[Dict[str, Any]]:
        return list(self._load(self.candidates_path).values())

    def put_evaluation(self, evaluation: Dict[str, Any]) -> None:
        evaluations = self._load(self.evaluations_path)
        evaluations[evaluation["evaluation_id"]] = evaluation
        write_json(self.evaluations_path, evaluations)

    def get_evaluation(self, evaluation_id: str) -> Optional[Dict[str, Any]]:
        return self._load(self.evaluations_path).get(evaluation_id)

    def put_receipt(self, receipt: Dict[str, Any]) -> None:
        receipts = self._load(self.receipts_path)
        receipts[receipt["receipt_id"]] = receipt
        write_json(self.receipts_path, receipts)

    def get_receipt(self, receipt_id: str) -> Optional[Dict[str, Any]]:
        return self._load(self.receipts_path).get(receipt_id)

    def get_idempotency(self, key: str) -> Optional[Dict[str, Any]]:
        return self._load(self.idempotency_path).get(key)

    def put_idempotency(self, key: str, record: Dict[str, Any]) -> None:
        rows = self._load(self.idempotency_path)
        rows[key] = record
        write_json(self.idempotency_path, rows)

    def put_promotion(self, request: Dict[str, Any]) -> None:
        rows = self._load(self.promotions_path)
        rows[request["request_id"]] = request
        write_json(self.promotions_path, rows)

    def get_promotion(self, request_id: str) -> Optional[Dict[str, Any]]:
        return self._load(self.promotions_path).get(request_id)

    def list_promotions(self) -> List[Dict[str, Any]]:
        return list(self._load(self.promotions_path).values())

    def put_approval(self, approval: Dict[str, Any]) -> None:
        rows = self._load(self.approvals_path)
        rows[approval["approval_id"]] = approval
        write_json(self.approvals_path, rows)

    def get_approval_for_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        for row in self._load(self.approvals_path).values():
            if row.get("request_id") == request_id and row.get("decision") == "approved":
                return row
        return None

    def put_canonical_projection(self, candidate_id: str, projection: Dict[str, Any]) -> None:
        rows = self._load(self.canonical_projection_path)
        rows[candidate_id] = projection
        write_json(self.canonical_projection_path, rows)

    def remove_canonical_projection(self, candidate_id: str) -> None:
        rows = self._load(self.canonical_projection_path)
        rows.pop(candidate_id, None)
        write_json(self.canonical_projection_path, rows)

    def get_canonical_projection(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        return self._load(self.canonical_projection_path).get(candidate_id)

    def new_id(self, prefix: str) -> str:
        return make_id(prefix)

    def now(self) -> str:
        return utc_now()

    def dump_audit(self) -> str:
        return json.dumps(self.snapshot(), indent=2, sort_keys=True)
