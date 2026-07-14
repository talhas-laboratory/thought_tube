from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .storage import make_id, utc_now
from .workspace_coordination import list_workspace_tasks, load_workspace_manifest
from .workspace_store import WorkspaceStore


MODULE_ID = "kernel.workspace.workspace_reasoning"
CONTRACT_VERSION = "1.0"
PUBLIC_API = ("MODULE_ID", "CONTRACT_VERSION", "list_workspace_reasoning", "record_workspace_reasoning")
__all__ = list(PUBLIC_API)


ALLOWED_REASONING_KINDS = {"observation", "hypothesis", "decision", "tension", "discovery", "scope_change", "next_action"}


def _reasoning_path(store: WorkspaceStore, workspace_id: str) -> Path:
    return store.manifest_path(workspace_id).parent / "reasoning_records.jsonl"


def list_workspace_reasoning(
    root: Path,
    workspace_id: str,
    *,
    task_id: str = "",
    run_id: str = "",
    limit: int = 20,
    store: WorkspaceStore | None = None,
) -> List[Dict[str, Any]]:
    if store is None:
        from .workspace_store import FileWorkspaceStore

        store = FileWorkspaceStore(root)
    load_workspace_manifest(root, workspace_id, store=store)
    rows = store.read_jsonl(_reasoning_path(store, workspace_id))
    if task_id:
        rows = [row for row in rows if str(row.get("task_id", "") or "") == task_id]
    if run_id:
        rows = [row for row in rows if str(row.get("run_id", "") or "") == run_id]
    rows.sort(key=lambda row: (str(row.get("created_at", "") or ""), str(row.get("reasoning_id", "") or "")), reverse=True)
    return [dict(row) for row in rows[:limit]]


def record_workspace_reasoning(
    root: Path,
    workspace_id: str,
    *,
    task_id: str,
    agent_id: str,
    surface: str,
    session_id: str,
    kind: str,
    summary: str,
    rationale: str,
    run_id: str = "",
    source_refs: List[str] | None = None,
    confidence: float | None = None,
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    if store is None:
        from .workspace_store import FileWorkspaceStore

        store = FileWorkspaceStore(root)
    load_workspace_manifest(root, workspace_id, store=store)
    if kind not in ALLOWED_REASONING_KINDS:
        raise ValueError(f"Unsupported reasoning kind: {kind}")
    if not task_id or not agent_id or not surface or not session_id or not str(summary or "").strip() or not str(rationale or "").strip():
        raise ValueError("task_id, agent_id, surface, session_id, summary, and rationale are required")
    tasks = list_workspace_tasks(root, workspace_id, limit=1000, store=store)
    if not any(str(row.get("task_id", row.get("work_item_id", "")) or "") == task_id for row in tasks):
        raise FileNotFoundError(f"Task not found: {task_id}")
    if confidence is not None and not 0 <= float(confidence) <= 1:
        raise ValueError("confidence must be between 0 and 1")
    record = {
        "reasoning_id": make_id("reasoning"),
        "workspace_id": workspace_id,
        "task_id": task_id,
        "run_id": str(run_id or "").strip(),
        "kind": kind,
        "summary": str(summary).strip(),
        "rationale": str(rationale).strip(),
        "source_refs": [str(item).strip() for item in list(source_refs or []) if str(item).strip()],
        "confidence": None if confidence is None else float(confidence),
        "actor": {"agent_id": agent_id, "surface": surface, "session_id": session_id},
        "created_at": utc_now(),
    }
    store.append_jsonl(_reasoning_path(store, workspace_id), record)
    return record
