from __future__ import annotations

from pathlib import Path
from typing import Any

from .storage import utc_now
from .workspace_coordination import prepare_workspace_task
from .workspace_runs import list_workspace_runs
from .workspace_reasoning import list_workspace_reasoning
from .workspace_progress import derive_workspace_task_progress
from .workspace_store import WorkspaceStore


MODULE_ID = "kernel.workspace.workspace_context_packet"
CONTRACT_VERSION = "1.0"
PUBLIC_API = ("MODULE_ID", "CONTRACT_VERSION", "assemble_workspace_context_packet")
__all__ = list(PUBLIC_API)


def _source_refs(*collections: list[dict[str, Any]]) -> list[str]:
    refs: list[str] = []
    for rows in collections:
        for row in rows:
            candidates = list(row.get("source_refs", []) or [])
            candidates.extend(list(row.get("linked_artifacts", []) or []))
            evidence_ref = str(row.get("evidence_ref", "") or "").strip()
            if evidence_ref:
                candidates.append(evidence_ref)
            for candidate in candidates:
                value = str(candidate or "").strip()
                if value and value not in refs:
                    refs.append(value)
    return refs[:50]


def assemble_workspace_context_packet(
    root: Path,
    workspace_id: str,
    *,
    task_id: str = "",
    agent_id: str = "",
    surface: str = "",
    session_id: str = "",
    store: WorkspaceStore | None = None,
    repository_snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    prepared = prepare_workspace_task(
        root,
        workspace_id,
        task_id=task_id,
        agent_id=agent_id,
        surface=surface,
        session_id=session_id,
        store=store,
    )
    selected_task = dict(prepared.get("task", {}) or {})
    tasks = list(prepared.get("tasks", []) or [])
    nearby_tasks = sorted(
        tasks,
        key=lambda row: (
            0 if str(row.get("task_id", row.get("work_item_id", "")) or "") == task_id else 1,
            str(row.get("status", "") or "") == "done",
            str(row.get("task_id", row.get("work_item_id", "")) or ""),
        ),
    )[:12]
    open_threads = [
        {
            "task_id": str(row.get("task_id", row.get("work_item_id", "")) or ""),
            "title": str(row.get("title", "") or ""),
            "status": str(row.get("status", "") or ""),
            "owner": str(row.get("owner", "") or ""),
            "parent_task_id": str(row.get("parent_id", "") or ""),
            "child_ids": list(row.get("child_ids", []) or []),
            "open_subtask_count": int(row.get("open_subtask_count", 0) or 0),
        }
        for row in nearby_tasks
        if str(row.get("status", "") or "") not in {"done", "cancelled"}
    ]
    decisions = list(prepared.get("decisions", []) or [])[:12]
    tests = list(prepared.get("tests", []) or [])[:12]
    activity = list(prepared.get("recent_activity", []) or [])[:20]
    active_runs = list_workspace_runs(root, workspace_id, task_id=task_id, active_only=True, store=store)[:20]
    # Active runs answer "who owns work now". A small, task-scoped closed-run
    # trail answers "how did this work arrive here" after a handoff releases
    # its claim. Full audit history remains available from the runs endpoint.
    recent_runs = [
        run
        for run in list_workspace_runs(root, workspace_id, task_id=task_id, store=store)
        if str(run.get("status", "") or "") != "active"
    ][:12]
    reasoning = list_workspace_reasoning(root, workspace_id, task_id=task_id, limit=12, store=store)
    if repository_snapshot is None:
        from .workspace_observer import latest_workspace_snapshot

        repository_snapshot = latest_workspace_snapshot(root, workspace_id, store=store)
    snapshot = dict(repository_snapshot or {})
    progress = derive_workspace_task_progress(root, workspace_id, task_id=task_id, store=store) if task_id and selected_task else {}
    return {
        "schema_version": "1.0",
        "workspace": prepared["workspace"],
        "focus": {
            "task": selected_task,
            "acceptance_criteria": list(selected_task.get("acceptance_criteria", []) or []),
            "constraints": list(selected_task.get("constraints", []) or []),
            "progress": progress,
            "recommended_next_action": progress.get("recommended_next_action", "") if progress else "Select a task to receive a recommended next action.",
        },
        "orientation": {
            "nearby_tasks": nearby_tasks,
            "open_threads": open_threads,
            "active_claims": list(prepared.get("active_claims", []) or [])[:20],
            "blockers": list(prepared.get("blockers", []) or [])[:20],
            "decisions": decisions,
            "tests": tests,
            "recent_activity": activity,
            "active_runs": active_runs,
            "recent_runs": recent_runs,
            "reasoning": reasoning,
        },
        "repository": {
            "source_revision": str(snapshot.get("source_revision", "") or ""),
            "changed_files": list(snapshot.get("changed_files", []) or [])[:100],
            "fingerprint": str(snapshot.get("fingerprint", "") or ""),
            "observed_at": str(snapshot.get("observed_at", "") or ""),
            "freshness_status": "observed" if str(snapshot.get("source_revision", "") or "").strip() else "unobserved",
        },
        "provenance": {
            "source_refs": _source_refs([selected_task], decisions, tests, activity, reasoning),
            "canonical_store": type(store).__name__ if store is not None else "FileWorkspaceStore",
        },
        "agent": {
            "agent_id": agent_id,
            "surface": surface,
            "session_id": session_id,
        },
        "assembled_at": utc_now(),
    }
