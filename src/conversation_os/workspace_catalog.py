from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from .storage import utc_now, workspace_manifest_path
from .workspace_store import WorkspaceStore


MODULE_ID = "kernel.workspace.workspace_catalog"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "audit_workspace_catalogs",
    "archive_workspace",
    "create_workspace",
    "import_workspace_snapshot",
    "migrate_workspace",
    "normalize_workspace_snapshot",
    "workspace_catalog",
    "workspace_snapshot",
)
__all__ = list(PUBLIC_API)


TASK_STATUS_ALIASES = {
    "completed": "done",
    "in_progress": "in-progress",
    "implementing": "in-progress",
}
TEST_RESULT_ALIASES = {
    "pass": "passing",
    "passed": "passing",
    "fail": "failing",
    "failed": "failing",
}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _snapshot_fingerprint(snapshot: Dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(snapshot).encode("utf-8")).hexdigest()


def _normalize_task_status(value: Any) -> Any:
    normalized = str(value or "").strip().lower()
    return TASK_STATUS_ALIASES.get(normalized, value)


def _normalize_test_result(value: Any) -> Any:
    normalized = str(value or "").strip().lower()
    return TEST_RESULT_ALIASES.get(normalized, value)


def _normalize_row(path: Path, row: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(row)
    if path.name == "work_item_events.jsonl":
        payload = dict(normalized.get("payload", {}) or {})
        if "status" in payload:
            payload["status"] = _normalize_task_status(payload["status"])
        normalized["payload"] = payload
    elif path.name == "test_runs.jsonl" and "result" in normalized:
        normalized["result"] = _normalize_test_result(normalized["result"])
    elif path.name == "test_cases.jsonl" and "expected_signal" in normalized:
        normalized["expected_signal"] = _normalize_test_result(normalized["expected_signal"])
    return normalized


def workspace_snapshot(store: WorkspaceStore, workspace_id: str) -> Dict[str, Any]:
    records: Dict[str, Any] = {}
    for path in store.record_paths(workspace_id):
        if path.suffix == ".json":
            records[path.name] = store.read_json(path, default=None)
        elif path.suffix == ".jsonl":
            records[path.name] = store.read_jsonl(path)
    manifest = records.get("manifest.json")
    if not isinstance(manifest, dict):
        raise FileNotFoundError(f"Workspace manifest missing: {workspace_id}")
    return {"workspace_id": workspace_id, "records": records}


def normalize_workspace_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    records: Dict[str, Any] = {}
    for name, payload in dict(snapshot.get("records", {}) or {}).items():
        path = Path(name)
        if path.suffix == ".jsonl":
            rows = [_normalize_row(path, dict(row)) for row in list(payload or [])]
            # SQLite has no record key for an empty append-only ledger; treat it
            # as equivalent to an empty file-backed ledger when fingerprinting.
            if rows:
                records[name] = rows
        elif isinstance(payload, dict):
            records[name] = _normalize_row(path, payload)
        else:
            records[name] = payload
    return {"workspace_id": str(snapshot.get("workspace_id", "") or ""), "records": records}


def workspace_catalog(store: WorkspaceStore) -> Dict[str, Any]:
    workspaces: List[Dict[str, Any]] = []
    for workspace_id in store.workspace_ids():
        snapshot = normalize_workspace_snapshot(workspace_snapshot(store, workspace_id))
        manifest = dict(snapshot["records"].get("manifest.json", {}) or {})
        workspaces.append(
            {
                "workspace_id": workspace_id,
                "label": str(manifest.get("label", workspace_id) or workspace_id),
                "status": str(manifest.get("status", "active") or "active"),
                "maturation_stage": str(manifest.get("maturation_stage", "raw") or "raw"),
                "record_count": len(snapshot["records"]),
                "revision": _snapshot_fingerprint(snapshot),
            }
        )
    return {
        "schema_version": CONTRACT_VERSION,
        "store": type(store).__name__,
        "workspace_count": len(workspaces),
        "workspaces": workspaces,
    }


def audit_workspace_catalogs(source: WorkspaceStore, target: WorkspaceStore) -> Dict[str, Any]:
    source_catalog = workspace_catalog(source)
    target_catalog = workspace_catalog(target)
    source_by_id = {row["workspace_id"]: row for row in source_catalog["workspaces"]}
    target_by_id = {row["workspace_id"]: row for row in target_catalog["workspaces"]}
    rows: List[Dict[str, Any]] = []
    for workspace_id in sorted(set(source_by_id) | set(target_by_id)):
        source_row = source_by_id.get(workspace_id)
        target_row = target_by_id.get(workspace_id)
        if source_row is None:
            status = "target_only"
        elif target_row is None:
            status = "source_only"
        elif source_row["revision"] == target_row["revision"]:
            status = "in_sync"
        else:
            status = "conflict"
        rows.append(
            {
                "workspace_id": workspace_id,
                "status": status,
                "source_revision": source_row.get("revision", "") if source_row else "",
                "target_revision": target_row.get("revision", "") if target_row else "",
            }
        )
    return {
        "schema_version": CONTRACT_VERSION,
        "source_store": source_catalog["store"],
        "target_store": target_catalog["store"],
        "workspaces": rows,
        "counts": {status: sum(1 for row in rows if row["status"] == status) for status in ("source_only", "target_only", "in_sync", "conflict")},
    }


def migrate_workspace(
    source: WorkspaceStore,
    target: WorkspaceStore,
    workspace_id: str,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    source_snapshot = normalize_workspace_snapshot(workspace_snapshot(source, workspace_id))
    result = import_workspace_snapshot(target, source_snapshot, dry_run=dry_run, imported_from=type(source).__name__)
    if result["status"] == "imported":
        result["status"] = "migrated"
    elif result["status"] == "already_imported":
        result["status"] = "already_migrated"
    return result


def _validated_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    normalized = normalize_workspace_snapshot(snapshot)
    workspace_id = str(normalized.get("workspace_id", "") or "").strip()
    records = dict(normalized.get("records", {}) or {})
    manifest = records.get("manifest.json")
    if not workspace_id or not isinstance(manifest, dict):
        raise ValueError("Snapshot requires workspace_id and manifest.json")
    if str(manifest.get("workspace_id", "") or "").strip() != workspace_id:
        raise ValueError("Snapshot manifest workspace_id must match snapshot workspace_id")
    for name, payload in records.items():
        path = Path(name)
        if path.name != name or path.suffix not in {".json", ".jsonl"}:
            raise ValueError(f"Invalid workspace record name: {name}")
        if path.suffix == ".json" and not isinstance(payload, dict):
            raise ValueError(f"JSON workspace record must be an object: {name}")
        if path.suffix == ".jsonl" and not isinstance(payload, list):
            raise ValueError(f"JSONL workspace record must be a list: {name}")
    return {"workspace_id": workspace_id, "records": records}


def import_workspace_snapshot(
    target: WorkspaceStore,
    snapshot: Dict[str, Any],
    *,
    dry_run: bool = False,
    imported_from: str = "snapshot",
) -> Dict[str, Any]:
    source_snapshot = _validated_snapshot(snapshot)
    workspace_id = source_snapshot["workspace_id"]
    source_revision = _snapshot_fingerprint(source_snapshot)
    target_path = workspace_manifest_path(target.root, workspace_id)
    if target.read_json(target_path, default=None) is not None:
        target_snapshot = normalize_workspace_snapshot(workspace_snapshot(target, workspace_id))
        target_revision = _snapshot_fingerprint(target_snapshot)
        if target_revision == source_revision:
            return {
                "workspace_id": workspace_id,
                "status": "already_imported",
                "source_revision": source_revision,
                "target_revision": target_revision,
                "records_written": 0,
            }
        raise ValueError(f"Target workspace differs and will not be overwritten: {workspace_id}")

    records = dict(source_snapshot["records"])
    result = {
        "workspace_id": workspace_id,
        "status": "planned" if dry_run else "imported",
        "source_revision": source_revision,
        "target_revision": source_revision,
        "records_written": len(records),
        "normalized": True,
        "imported_from": imported_from,
    }
    if dry_run:
        return result
    for name, payload in records.items():
        path = workspace_manifest_path(target.root, workspace_id).parent / name
        if path.suffix == ".json":
            target.write_json(path, payload)
        elif path.suffix == ".jsonl":
            for row in list(payload or []):
                target.append_jsonl(path, dict(row))
    return result


def create_workspace(target: WorkspaceStore, manifest: Dict[str, Any]) -> Dict[str, Any]:
    workspace_id = str(manifest.get("workspace_id", "") or "").strip()
    if not workspace_id:
        raise ValueError("workspace_id is required")
    path = workspace_manifest_path(target.root, workspace_id)
    if target.read_json(path, default=None) is not None:
        raise ValueError(f"Workspace already exists: {workspace_id}")
    payload = dict(manifest)
    payload["workspace_id"] = workspace_id
    payload.setdefault("status", "active")
    payload.setdefault("maturation_stage", "raw")
    payload.setdefault("created_at", utc_now())
    payload.setdefault("updated_at", payload["created_at"])
    target.write_json(path, payload)
    return {
        "workspace_id": workspace_id,
        "status": "created",
        "revision": _snapshot_fingerprint(normalize_workspace_snapshot(workspace_snapshot(target, workspace_id))),
    }


def archive_workspace(target: WorkspaceStore, workspace_id: str, *, reason: str = "") -> Dict[str, Any]:
    path = workspace_manifest_path(target.root, workspace_id)
    manifest = target.read_json(path, default=None)
    if not isinstance(manifest, dict):
        raise FileNotFoundError(f"Workspace not found: {workspace_id}")
    payload = dict(manifest)
    payload["status"] = "archived"
    payload["status_reason"] = str(reason or "").strip()
    payload["closed_at"] = utc_now()
    payload["updated_at"] = payload["closed_at"]
    target.write_json(path, payload)
    return {
        "workspace_id": workspace_id,
        "status": "archived",
        "revision": _snapshot_fingerprint(normalize_workspace_snapshot(workspace_snapshot(target, workspace_id))),
    }
