"""Append-only file-backed store for metaphysical kernel records."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Optional

from conversation_os.storage import append_jsonl, ensure_dir, make_id, read_jsonl, utc_now

MODULE_ID = "kernel.metaphysical.store"
CONTRACT_VERSION = "1.1.0"

RECORD_COLLECTION_KEYS = (
    "source_fragments",
    "referents",
    "scopes",
    "model_branches",
    "branch_memberships",
    "claims",
    "states",
    "state_commitments",
    "relation_instances",
    "provenances",
    "profile_definitions",
    "profile_conformance_results",
)

RECORD_KIND_TO_KEY = {
    "source_fragment": "source_fragments",
    "referent": "referents",
    "scope": "scopes",
    "model_branch": "model_branches",
    "branch_membership": "branch_memberships",
    "claim": "claims",
    "state": "states",
    "state_commitment": "state_commitments",
    "relation_instance": "relation_instances",
    "provenance": "provenances",
    "profile_definition": "profile_definitions",
    "profile_conformance_result": "profile_conformance_results",
}


def foundation_dir(root: Path) -> Path:
    return root / "memory" / "foundation"


def foundation_events_path(root: Path) -> Path:
    return foundation_dir(root) / "kernel_events.jsonl"


class FoundationStore:
    """Append-only kernel event log with folded read model."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.events_path = foundation_events_path(root)
        ensure_dir(self.events_path.parent)

    def append_event(
        self,
        operation: str,
        *,
        actor: str,
        record_kind: str = "",
        record: Optional[Mapping[str, Any]] = None,
        target_record_id: str = "",
        reason: str = "",
    ) -> Dict[str, Any]:
        event = {
            "event_id": make_id("kevt"),
            "timestamp": utc_now(),
            "operation": operation,
            "actor": actor,
            "record_kind": record_kind,
            "record": dict(record) if record is not None else None,
            "target_record_id": target_record_id,
            "reason": reason,
        }
        append_jsonl(self.events_path, event)
        return event

    def append_records(self, records: List[Mapping[str, Any]], *, actor: str) -> Dict[str, Any]:
        """Append a validated record batch as one durable event.

        Folding only applies the batch after the whole event has been read, so
        a State adoption never exposes its commitment, State, or memberships
        independently.
        """
        event = {
            "event_id": make_id("kevt"),
            "timestamp": utc_now(),
            "operation": "append_records",
            "actor": actor,
            "records": [dict(record) for record in records],
        }
        append_jsonl(self.events_path, event)
        return event

    def read_events(self) -> List[Dict[str, Any]]:
        return read_jsonl(self.events_path)

    def fold(self) -> Dict[str, Any]:
        """Apply append-only events to produce the current active record index."""
        bundle = {key: [] for key in RECORD_COLLECTION_KEYS}
        active: Dict[str, Dict[str, Any]] = {}
        retracted: set[str] = set()

        def add_record(record: Any, record_kind_hint: str = "") -> None:
            if not isinstance(record, dict):
                return
            envelope = record.get("envelope", {})
            if not isinstance(envelope, dict):
                return
            record_id = str(envelope.get("id", ""))
            record_kind = str(envelope.get("record_kind", record_kind_hint))
            if not record_id or not record_kind:
                return
            active[record_id] = {"record_kind": record_kind, "record": record}

        for event in self.read_events():
            operation = str(event.get("operation", ""))
            if operation == "append_record":
                add_record(event.get("record"), str(event.get("record_kind", "")))
            elif operation == "append_records":
                records = event.get("records", [])
                if isinstance(records, list):
                    for record in records:
                        add_record(record)
            elif operation == "retract_record":
                target_id = str(event.get("target_record_id", ""))
                if target_id:
                    retracted.add(target_id)

        for record_id, payload in active.items():
            if record_id in retracted:
                record = dict(payload["record"])
                envelope = dict(record.get("envelope", {}))
                envelope["epistemic_status"] = "retracted"
                record["envelope"] = envelope
                record["_retracted"] = True
            else:
                record = payload["record"]
            collection = RECORD_KIND_TO_KEY.get(str(payload["record_kind"]), "")
            if collection:
                bundle[collection].append(record)

        bundle["_retracted_ids"] = sorted(retracted)
        return bundle

    def get_record(self, record_id: str) -> Optional[Dict[str, Any]]:
        folded = self.fold()
        for key in RECORD_COLLECTION_KEYS:
            for record in folded.get(key, []):
                envelope = record.get("envelope", {})
                if isinstance(envelope, dict) and envelope.get("id") == record_id:
                    return record
        return None

    def list_record_ids(self, record_kind: Optional[str] = None) -> List[str]:
        folded = self.fold()
        ids: List[str] = []
        keys = (
            [RECORD_KIND_TO_KEY[record_kind]]
            if record_kind in RECORD_KIND_TO_KEY
            else list(RECORD_COLLECTION_KEYS)
        )
        for key in keys:
            for record in folded.get(key, []):
                envelope = record.get("envelope", {})
                if isinstance(envelope, dict) and envelope.get("id"):
                    ids.append(str(envelope["id"]))
        return ids


__all__ = [
    "MODULE_ID",
    "CONTRACT_VERSION",
    "RECORD_COLLECTION_KEYS",
    "RECORD_KIND_TO_KEY",
    "foundation_dir",
    "foundation_events_path",
    "FoundationStore",
]
