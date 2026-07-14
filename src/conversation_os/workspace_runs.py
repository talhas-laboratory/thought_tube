from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from .storage import make_id, utc_now
from .workspace_coordination import claim_workspace_task, list_workspace_claims, list_workspace_tasks, load_workspace_manifest
from .workspace_store import WorkspaceStore


MODULE_ID = "kernel.workspace.workspace_runs"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "begin_workspace_run",
    "end_workspace_run",
    "heartbeat_workspace_run",
    "list_workspace_runs",
    "recover_stale_workspace_runs",
)
__all__ = list(PUBLIC_API)


_END_STATUSES = {"released", "handed_off", "completed", "cancelled"}


def _runs_path(store: WorkspaceStore, workspace_id: str) -> Path:
    return store.manifest_path(workspace_id).parent / "agent_runs.jsonl"


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _reduced_runs(store: WorkspaceStore, workspace_id: str) -> Dict[str, Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for row in store.read_jsonl(_runs_path(store, workspace_id)):
        run_id = str(row.get("run_id", "") or "")
        if run_id:
            latest[run_id] = dict(row)
    return latest


def _linked_claims(root: Path, workspace_id: str, run: Dict[str, Any], store: WorkspaceStore) -> List[Dict[str, Any]]:
    claim_ids = {str(item or "") for item in list(run.get("claim_ids", []) or [])}
    return [
        claim
        for claim in list_workspace_claims(root, workspace_id, store=store)
        if str(claim.get("claim_id", "") or "") in claim_ids
    ]


def _append_claim_update(store: WorkspaceStore, workspace_id: str, claim: Dict[str, Any]) -> None:
    store.append_jsonl(store.claims_path(workspace_id), claim)


def list_workspace_runs(
    root: Path,
    workspace_id: str,
    *,
    task_id: str = "",
    active_only: bool = False,
    store: WorkspaceStore | None = None,
) -> List[Dict[str, Any]]:
    if store is None:
        from .workspace_store import FileWorkspaceStore

        store = FileWorkspaceStore(root)
    load_workspace_manifest(root, workspace_id, store=store)
    now = datetime.now(timezone.utc)
    runs: List[Dict[str, Any]] = []
    for run in _reduced_runs(store, workspace_id).values():
        item = dict(run)
        linked_claims = _linked_claims(root, workspace_id, item, store)
        item["claimed_paths"] = [
            path
            for claim in linked_claims
            for path in list(claim.get("claimed_paths", []) or [])
        ]
        if item.get("status") == "active":
            try:
                deadline = _parse_iso(str(item.get("last_heartbeat_at", item.get("started_at", "")) or "")) + timedelta(
                    seconds=max(int(item.get("heartbeat_ttl_seconds", 900) or 900), 60)
                )
                if deadline <= now:
                    item["status"] = "stale"
                    item["stale_since"] = deadline.replace(microsecond=0).isoformat()
            except (TypeError, ValueError):
                item["status"] = "stale"
        if task_id and str(item.get("task_id", "") or "") != task_id:
            continue
        if active_only and item.get("status") != "active":
            continue
        runs.append(item)
    runs.sort(key=lambda row: (str(row.get("last_heartbeat_at", "") or ""), str(row.get("run_id", "") or "")), reverse=True)
    return runs


def begin_workspace_run(
    root: Path,
    workspace_id: str,
    *,
    task_id: str,
    agent_id: str,
    device_id: str,
    surface: str,
    session_id: str,
    intent: str,
    source_revision: str = "",
    heartbeat_ttl_seconds: int = 900,
    run_id: str = "",
    claimed_paths: List[str] | None = None,
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    if store is None:
        from .workspace_store import FileWorkspaceStore

        store = FileWorkspaceStore(root)
    load_workspace_manifest(root, workspace_id, store=store)
    if not task_id or not agent_id or not surface or not session_id or not intent:
        raise ValueError("task_id, agent_id, surface, session_id, and intent are required")
    tasks = list_workspace_tasks(root, workspace_id, limit=1000, store=store)
    if not any(str(row.get("task_id", row.get("work_item_id", "")) or "") == task_id for row in tasks):
        raise FileNotFoundError(f"Task not found: {task_id}")
    run_id = str(run_id or make_id("agent-run")).strip()
    existing = _reduced_runs(store, workspace_id).get(run_id)
    if existing is not None:
        if existing.get("status") == "active":
            return {**existing, "already_exists": True}
        raise ValueError(f"Run id is already closed: {run_id}")
    active_claims = [
        claim
        for claim in list_workspace_claims(root, workspace_id, store=store)
        if str(claim.get("task_id", "") or "") == task_id
        and str(claim.get("actor", {}).get("agent_id", "") or "") == agent_id
    ]
    if claimed_paths:
        active_claims.append(
            claim_workspace_task(
                root,
                workspace_id,
                task_id=task_id,
                agent_id=agent_id,
                surface=surface,
                session_id=session_id,
                intent=intent,
                claimed_paths=claimed_paths,
                ttl_seconds=heartbeat_ttl_seconds,
                run_id=run_id,
                store=store,
            )
        )
    claim_ids: List[str] = []
    for claim in active_claims:
        claim_id = str(claim.get("claim_id", "") or "")
        if not claim_id or claim_id in claim_ids:
            continue
        claim_ids.append(claim_id)
        if str(claim.get("run_id", "") or "") != run_id:
            _append_claim_update(store, workspace_id, {**claim, "run_id": run_id, "updated_at": utc_now()})
    now = utc_now()
    run = {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "task_id": task_id,
        "actor": {
            "agent_id": agent_id,
            "device_id": str(device_id or "").strip(),
            "surface": surface,
            "session_id": session_id,
        },
        "status": "active",
        "intent": intent,
        "source_revision": str(source_revision or "").strip(),
        "heartbeat_ttl_seconds": max(int(heartbeat_ttl_seconds or 900), 60),
        "claim_ids": claim_ids,
        "claimed_paths": [path for claim in active_claims for path in list(claim.get("claimed_paths", []) or [])],
        "started_at": now,
        "last_heartbeat_at": now,
        "ended_at": None,
        "end_reason": "",
    }
    store.append_jsonl(_runs_path(store, workspace_id), run)
    return run


def heartbeat_workspace_run(
    root: Path,
    workspace_id: str,
    *,
    run_id: str,
    agent_id: str,
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    if store is None:
        from .workspace_store import FileWorkspaceStore

        store = FileWorkspaceStore(root)
    current = _reduced_runs(store, workspace_id).get(run_id)
    if current is None:
        raise FileNotFoundError(f"Run not found: {run_id}")
    if current.get("status") != "active":
        raise ValueError(f"Run is not active: {run_id}")
    if str(current.get("actor", {}).get("agent_id", "") or "") != agent_id:
        raise ValueError("Only the run owner can heartbeat the run")
    now = utc_now()
    for claim in _linked_claims(root, workspace_id, current, store):
        _append_claim_update(
            store,
            workspace_id,
            {
                **claim,
                "run_id": run_id,
                "updated_at": now,
                "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=max(int(current.get("heartbeat_ttl_seconds", 900) or 900), 60))).replace(microsecond=0).isoformat(),
            },
        )
    updated = {**current, "last_heartbeat_at": now}
    store.append_jsonl(_runs_path(store, workspace_id), updated)
    return updated


def end_workspace_run(
    root: Path,
    workspace_id: str,
    *,
    run_id: str,
    agent_id: str,
    status: str,
    reason: str,
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    if store is None:
        from .workspace_store import FileWorkspaceStore

        store = FileWorkspaceStore(root)
    current = _reduced_runs(store, workspace_id).get(run_id)
    if current is None:
        raise FileNotFoundError(f"Run not found: {run_id}")
    if current.get("status") != "active":
        raise ValueError(f"Run is not active: {run_id}")
    if str(current.get("actor", {}).get("agent_id", "") or "") != agent_id:
        raise ValueError("Only the run owner can end the run")
    if status not in _END_STATUSES:
        raise ValueError(f"Invalid run end status: {status}")
    if not str(reason or "").strip():
        raise ValueError("reason is required")
    now = utc_now()
    released_claim_ids: List[str] = []
    for claim in _linked_claims(root, workspace_id, current, store):
        released_claim_ids.append(str(claim.get("claim_id", "") or ""))
        _append_claim_update(store, workspace_id, {**claim, "updated_at": now, "status": "released", "run_id": run_id})
    updated = {
        **current,
        "status": status,
        "ended_at": now,
        "end_reason": str(reason).strip(),
        "released_claim_ids": released_claim_ids,
    }
    store.append_jsonl(_runs_path(store, workspace_id), updated)
    return updated


def recover_stale_workspace_runs(root: Path, workspace_id: str, *, store: WorkspaceStore | None = None) -> List[Dict[str, Any]]:
    if store is None:
        from .workspace_store import FileWorkspaceStore

        store = FileWorkspaceStore(root)
    stale_runs = [row for row in list_workspace_runs(root, workspace_id, store=store) if row.get("status") == "stale"]
    recovered: List[Dict[str, Any]] = []
    for stale in stale_runs:
        current = _reduced_runs(store, workspace_id).get(str(stale.get("run_id", "") or ""))
        if current is None or current.get("status") != "active":
            continue
        now = utc_now()
        released_claim_ids: List[str] = []
        for claim in _linked_claims(root, workspace_id, current, store):
            released_claim_ids.append(str(claim.get("claim_id", "") or ""))
            _append_claim_update(store, workspace_id, {**claim, "updated_at": now, "status": "released"})
        updated = {
            **current,
            "status": "released",
            "ended_at": now,
            "end_reason": "Recovered after heartbeat lease expired.",
            "released_claim_ids": released_claim_ids,
            "recovered_from_stale": True,
        }
        store.append_jsonl(_runs_path(store, workspace_id), updated)
        recovered.append(updated)
    return recovered
