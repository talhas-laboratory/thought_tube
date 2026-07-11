from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .workspace_coordination import (
    list_workspace_activity_events,
    list_workspace_blockers,
    list_workspace_claims,
    list_workspace_tasks,
    list_workspace_tests,
)
from .workspace_runs import list_workspace_runs
from .workspace_store import WorkspaceStore


MODULE_ID = "kernel.workspace.workspace_progress"
CONTRACT_VERSION = "1.0"
PUBLIC_API = ("MODULE_ID", "CONTRACT_VERSION", "derive_workspace_task_progress")
__all__ = list(PUBLIC_API)


def derive_workspace_task_progress(
    root: Path,
    workspace_id: str,
    *,
    task_id: str,
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    tasks = list_workspace_tasks(root, workspace_id, limit=1000, store=store)
    task = next((row for row in tasks if str(row.get("task_id", row.get("work_item_id", "")) or "") == task_id), None)
    if task is None:
        raise FileNotFoundError(f"Task not found: {task_id}")
    child_ids = list(task.get("child_ids", []) or [])
    children = [row for row in tasks if str(row.get("task_id", "") or "") in child_ids]
    open_children = [row for row in children if str(row.get("status", "") or "") not in {"done", "cancelled"}]
    blockers = list_workspace_blockers(root, workspace_id, task_id=task_id, limit=100, store=store)
    claims = [row for row in list_workspace_claims(root, workspace_id, store=store) if str(row.get("task_id", "") or "") == task_id]
    runs = list_workspace_runs(root, workspace_id, task_id=task_id, active_only=True, store=store)
    tests = list_workspace_tests(root, workspace_id, task_id=task_id, limit=100, store=store)
    passing_tests = [row for row in tests if str(row.get("latest_result", "") or "") == "passing"]
    recent_activity = list_workspace_activity_events(root, workspace_id, task_id=task_id, limit=1, store=store)
    status = str(task.get("status", "") or "")

    if status == "done":
        state, next_action = "complete", "No action required; the task is complete."
    elif blockers:
        state, next_action = "blocked", f"Resolve blocker: {blockers[0].get('reason', 'unspecified blocker')}"
    elif runs:
        state, next_action = "active", f"Continue active run {runs[0].get('run_id', '')}."
    elif open_children:
        state, next_action = "waiting_on_subtasks", f"Complete, hand off, or cancel {len(open_children)} open subtask(s)."
    elif status in {"backlog", "ready"}:
        state, next_action = "ready_to_start", "Begin an agent run and claim the paths needed for this task."
    elif not passing_tests:
        state, next_action = "awaiting_verification", "Record passing verification evidence for this task."
    else:
        state, next_action = "ready_for_completion", "Review residual risk, then complete or hand off the task."

    return {
        "workspace_id": workspace_id,
        "task_id": task_id,
        "state": state,
        "task_status": status,
        "children": {"total": len(children), "open": len(open_children), "completed": len(children) - len(open_children)},
        "active_claim_count": len(claims),
        "active_run_count": len(runs),
        "active_blocker_count": len(blockers),
        "passing_test_count": len(passing_tests),
        "last_activity": recent_activity[0] if recent_activity else {},
        "recommended_next_action": next_action,
    }
