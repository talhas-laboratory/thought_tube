from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from .holodeck import _reduce_tests, _reduce_work_items
from .storage import (
    make_id,
    slugify,
    utc_now,
)
from .workspace_store import FileWorkspaceStore, WorkspaceStore


MODULE_ID = "kernel.workspace.workspace_coordination"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "append_workspace_activity_event",
    "claim_workspace_task",
    "complete_workspace_task",
    "create_workspace_task",
    "evaluate_workspace_release_gate",
    "list_workspace_activity_events",
    "list_workspace_blockers",
    "list_workspace_claims",
    "list_workspace_decisions",
    "list_workspace_tasks",
    "list_workspace_tests",
    "load_workspace_manifest",
    "prepare_workspace_task",
    "record_workspace_blocker",
    "record_workspace_decision",
    "record_workspace_test_run",
    "resolve_workspace_blocker",
    "release_workspace_task_claims",
    "render_workspace_status",
    "render_workspace_tasks",
    "update_workspace_task",
    "WorkspaceCompletionError",
)
__all__ = list(PUBLIC_API)


class WorkspaceCompletionError(ValueError):
    def __init__(self, missing: List[str]) -> None:
        self.missing = list(missing)
        super().__init__(f"Completion requirements missing: {', '.join(self.missing)}")


def _workspace_store(root: Path) -> WorkspaceStore:
    return FileWorkspaceStore(root)


def _resolve_store(root: Path, store: WorkspaceStore | None) -> WorkspaceStore:
    return store or _workspace_store(root)


def _parse_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _refresh_workspace_atlas(root: Path, workspace_id: str, *, store: WorkspaceStore | None = None) -> None:
    from .workspace_atlas import materialize_workspace_atlas

    materialize_workspace_atlas(root, workspace_id, store=store)


def _looks_like_repo_path(root: Path, value: str) -> bool:
    candidate = str(value or "").strip()
    if not candidate:
        return False
    prefixes = ("src/", "product/", "docs/", "tools/", "tests/", "ops/", "memory/", "context/")
    if candidate.startswith(prefixes) or candidate.endswith("/"):
        return True
    return (root / candidate).exists()


def load_workspace_manifest(root: Path, workspace_id: str, *, store: WorkspaceStore | None = None) -> Dict[str, Any]:
    store = _resolve_store(root, store)
    path = store.manifest_path(workspace_id)
    payload = store.read_json(path, default=None)
    if not isinstance(payload, dict):
        raise FileNotFoundError(f"Workspace not found: {workspace_id}")

    artifact_roots = [str(item).strip() for item in list(payload.get("artifact_roots", []) or []) if str(item).strip()]
    objectives = [str(item).strip() for item in list(payload.get("objectives", []) or []) if str(item).strip()]
    for raw in list(payload.get("scope_in", []) or []):
        value = str(raw or "").strip()
        if not value:
            continue
        if _looks_like_repo_path(root, value):
            if value not in artifact_roots:
                artifact_roots.append(value)
        elif value not in objectives:
            objectives.append(value)

    domains = [str(item).strip() for item in list(payload.get("domains", []) or payload.get("domain_overlays", []) or []) if str(item).strip()]
    active_subprojects = [str(item).strip() for item in list(payload.get("active_subprojects", []) or []) if str(item).strip()]
    active_subproject_id = str(payload.get("active_subproject_id", "") or "").strip()
    if active_subproject_id and active_subproject_id not in active_subprojects:
        active_subprojects.append(active_subproject_id)

    normalized = dict(payload)
    normalized["artifact_roots"] = artifact_roots
    normalized["objectives"] = objectives
    normalized["domains"] = domains
    normalized["active_subprojects"] = active_subprojects
    normalized["activity_ref"] = str(store.activity_events_path(workspace_id).relative_to(root))
    normalized.setdefault("scope_out", [])
    return normalized


def append_workspace_activity_event(
    root: Path,
    workspace_id: str,
    *,
    task_id: str,
    agent_id: str,
    surface: str,
    session_id: str,
    event_type: str,
    summary: str,
    reasoning: str = "",
    files_touched: List[str] | None = None,
    commands_run: List[str] | None = None,
    verification: List[str] | None = None,
    blockers: List[str] | None = None,
    decision_refs: List[str] | None = None,
    handoff_refs: List[str] | None = None,
    metadata: Dict[str, Any] | None = None,
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    store = _resolve_store(root, store)
    load_workspace_manifest(root, workspace_id, store=store)
    event = {
        "event_id": make_id("evt"),
        "schema_version": "1.0",
        "created_at": utc_now(),
        "workspace_id": workspace_id,
        "task_id": task_id,
        "actor": {
            "agent_id": agent_id,
            "surface": surface,
            "session_id": session_id,
        },
        "event_type": event_type,
        "summary": summary,
        "reasoning": reasoning,
        "files_touched": list(files_touched or []),
        "commands_run": list(commands_run or []),
        "verification": list(verification or []),
        "blockers": list(blockers or []),
        "decision_refs": list(decision_refs or []),
        "handoff_refs": list(handoff_refs or []),
        "metadata": dict(metadata or {}),
    }
    store.append_jsonl(store.activity_events_path(workspace_id), event)
    return event


def list_workspace_activity_events(
    root: Path,
    workspace_id: str,
    *,
    task_id: str = "",
    limit: int = 20,
    store: WorkspaceStore | None = None,
) -> List[Dict[str, Any]]:
    store = _resolve_store(root, store)
    load_workspace_manifest(root, workspace_id, store=store)
    rows = store.read_jsonl(store.activity_events_path(workspace_id))
    if task_id:
        rows = [row for row in rows if row.get("task_id", "") == task_id]
    rows = list(reversed(rows))
    return rows[:limit]


def _path_overlaps(left: str, right: str) -> bool:
    l = str(left or "").strip().rstrip("/")
    r = str(right or "").strip().rstrip("/")
    if not l or not r:
        return False
    return l == r or l.startswith(r + "/") or r.startswith(l + "/")


def _reduce_claims(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    now = datetime.now(timezone.utc)
    for row in sorted(rows, key=lambda item: (item.get("updated_at", item.get("created_at", "")), item.get("claim_id", ""))):
        payload = dict(row)
        expires_at = str(payload.get("expires_at", "") or "")
        if payload.get("status") == "active" and expires_at:
            try:
                if _parse_iso(expires_at) <= now:
                    payload["status"] = "expired"
            except ValueError:
                payload["status"] = "expired"
        latest[str(payload.get("claim_id", ""))] = payload
    return [claim for claim in latest.values() if claim.get("claim_id")]


def list_workspace_claims(
    root: Path,
    workspace_id: str,
    *,
    include_inactive: bool = False,
    store: WorkspaceStore | None = None,
) -> List[Dict[str, Any]]:
    store = _resolve_store(root, store)
    load_workspace_manifest(root, workspace_id, store=store)
    claims = _reduce_claims(store.read_jsonl(store.claims_path(workspace_id)))
    if not include_inactive:
        claims = [claim for claim in claims if claim.get("status") == "active"]
    claims.sort(key=lambda row: (row.get("updated_at", row.get("created_at", "")), row.get("claim_id", "")), reverse=True)
    return claims


def list_workspace_tasks(root: Path, workspace_id: str, *, limit: int = 20, store: WorkspaceStore | None = None) -> List[Dict[str, Any]]:
    store = _resolve_store(root, store)
    load_workspace_manifest(root, workspace_id, store=store)
    rows = store.read_jsonl(store.work_item_events_path(workspace_id))
    source_refs_by_task: Dict[str, List[str]] = {}
    for row in rows:
        row_task_id = str(row.get("work_item_id", "") or "")
        refs = source_refs_by_task.setdefault(row_task_id, [])
        for raw in list(row.get("source_refs", []) or []):
            value = str(raw or "").strip()
            if value and value not in refs:
                refs.append(value)
    tasks = []
    for task in _reduce_work_items(rows):
        normalized = dict(task)
        normalized.setdefault("task_id", str(task.get("work_item_id", "") or ""))
        normalized["source_refs"] = source_refs_by_task.get(str(task.get("work_item_id", "") or ""), [])
        tasks.append(normalized)
    children_by_parent: Dict[str, List[str]] = {}
    for task in tasks:
        parent_id = str(task.get("parent_id", "") or "")
        if parent_id:
            children_by_parent.setdefault(parent_id, []).append(str(task["task_id"]))
    for task in tasks:
        child_ids = children_by_parent.get(str(task["task_id"]), [])
        task["child_ids"] = child_ids
        task["subtask_count"] = len(child_ids)
        task["open_subtask_count"] = sum(
            1
            for child_id in child_ids
            if next((row for row in tasks if row["task_id"] == child_id), {}).get("status") not in {"done", "cancelled"}
        )
    return tasks[:limit]


_TASK_STATUSES = {"backlog", "ready", "in-progress", "review", "verification", "blocked", "done", "cancelled"}
_TASK_TRANSITIONS = {
    "backlog": {"ready", "in-progress", "cancelled"},
    "ready": {"backlog", "in-progress", "blocked", "cancelled"},
    "in-progress": {"review", "verification", "blocked", "cancelled"},
    "review": {"in-progress", "verification", "blocked", "cancelled"},
    "verification": {"in-progress", "review", "blocked", "cancelled"},
    "blocked": {"backlog", "ready", "in-progress", "cancelled"},
    "cancelled": {"backlog"},
    "done": set(),
}


def _validate_parent_task(
    tasks: List[Dict[str, Any]],
    *,
    task_id: str,
    parent_task_id: str,
) -> None:
    if not parent_task_id:
        return
    if parent_task_id == task_id:
        raise ValueError("A task cannot be its own parent")
    by_id = {str(task.get("task_id", task.get("work_item_id", "")) or ""): task for task in tasks}
    parent = by_id.get(parent_task_id)
    if parent is None:
        raise ValueError(f"Parent task not found: {parent_task_id}")
    if str(parent.get("parent_id", "") or ""):
        raise ValueError("Task hierarchy supports one subtask level; parent tasks cannot themselves be subtasks")
    current_parent_id = str(parent.get("parent_id", "") or "")
    while current_parent_id:
        if current_parent_id == task_id:
            raise ValueError(f"Parent relationship would create a cycle through {parent_task_id}")
        current_parent_id = str(by_id.get(current_parent_id, {}).get("parent_id", "") or "")


def create_workspace_task(
    root: Path,
    workspace_id: str,
    *,
    task_id: str,
    agent_id: str,
    surface: str,
    session_id: str,
    title: str,
    reasoning: str,
    status: str = "backlog",
    priority: str = "medium",
    owner: str = "",
    acceptance_criteria: List[str] | None = None,
    constraints: List[str] | None = None,
    depends_on: List[str] | None = None,
    linked_artifacts: List[str] | None = None,
    source_refs: List[str] | None = None,
    parent_task_id: str = "",
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    store = _resolve_store(root, store)
    load_workspace_manifest(root, workspace_id, store=store)
    task_id = str(task_id or "").strip()
    title = str(title or "").strip()
    reasoning = str(reasoning or "").strip()
    criteria = [str(item).strip() for item in list(acceptance_criteria or []) if str(item).strip()]
    parent_task_id = str(parent_task_id or "").strip()
    if not task_id or not title or not reasoning or not criteria:
        raise ValueError("task_id, title, reasoning, and acceptance_criteria are required")
    if status not in _TASK_STATUSES or status == "done":
        raise ValueError("New task status must be backlog, ready, in-progress, review, verification, blocked, or cancelled")
    expected = {
        "title": title,
        "status": status,
        "priority": str(priority or "medium"),
        "owner": str(owner or ""),
        "depends_on": [str(item).strip() for item in list(depends_on or []) if str(item).strip()],
        "linked_artifacts": [str(item).strip() for item in list(linked_artifacts or []) if str(item).strip()],
        "acceptance_criteria": criteria,
        "constraints": [str(item).strip() for item in list(constraints or []) if str(item).strip()],
        "parent_id": parent_task_id,
    }
    tasks = list_workspace_tasks(root, workspace_id, limit=1000, store=store)
    existing = next((row for row in tasks if row.get("task_id") == task_id), None)
    if existing is not None:
        if all(existing.get(key) == value for key, value in expected.items()):
            return {**existing, "already_exists": True}
        raise ValueError(f"Task {task_id} already exists with different task data")
    _validate_parent_task(tasks, task_id=task_id, parent_task_id=parent_task_id)
    event = {
        "event_id": make_id("work-item-event"),
        "workspace_id": workspace_id,
        "work_item_id": task_id,
        "operation": "create",
        "timestamp": utc_now(),
        "actor": agent_id,
        "payload": {
            **expected,
            "kind": "task",
            "parent_id": parent_task_id,
            "linked_tests": [],
            "guard_status": "not_required",
            "guard_request": "",
            "guard_purpose": "",
            "guard_paths": [],
        },
        "source_refs": [str(item).strip() for item in list(source_refs or []) if str(item).strip()],
    }
    store.append_jsonl(store.work_item_events_path(workspace_id), event)
    append_workspace_activity_event(
        root,
        workspace_id,
        task_id=task_id,
        agent_id=agent_id,
        surface=surface,
        session_id=session_id,
        event_type="task_created",
        summary=title,
        reasoning=reasoning,
        metadata={"source_refs": event["source_refs"]},
        store=store,
    )
    _refresh_workspace_atlas(root, workspace_id, store=store)
    return next(row for row in list_workspace_tasks(root, workspace_id, limit=1000, store=store) if row.get("task_id") == task_id)


def update_workspace_task(
    root: Path,
    workspace_id: str,
    *,
    task_id: str,
    agent_id: str,
    surface: str,
    session_id: str,
    reasoning: str,
    status: str | None = None,
    owner: str | None = None,
    priority: str | None = None,
    acceptance_criteria: List[str] | None = None,
    constraints: List[str] | None = None,
    depends_on: List[str] | None = None,
    linked_artifacts: List[str] | None = None,
    source_refs: List[str] | None = None,
    parent_task_id: str | None = None,
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    store = _resolve_store(root, store)
    current = next((row for row in list_workspace_tasks(root, workspace_id, limit=1000, store=store) if row.get("task_id") == task_id), None)
    if current is None:
        raise FileNotFoundError(f"Task not found: {task_id}")
    if not str(reasoning or "").strip():
        raise ValueError("reasoning is required")
    if status == "done":
        raise ValueError("Use complete_workspace_task to mark a task done")
    if status is not None and status != current.get("status"):
        if status not in _TASK_TRANSITIONS.get(str(current.get("status", "")), set()):
            raise ValueError(f"Invalid task transition: {current.get('status', '')} -> {status}")
    if parent_task_id is not None:
        parent_task_id = str(parent_task_id or "").strip()
        _validate_parent_task(tasks=list_workspace_tasks(root, workspace_id, limit=1000, store=store), task_id=task_id, parent_task_id=parent_task_id)
    updates = [
        ("set_status", "status", status),
        ("set_owner", "owner", owner),
        ("set_priority", "priority", priority),
        ("set_acceptance", "acceptance_criteria", acceptance_criteria),
        ("set_constraints", "constraints", constraints),
        ("set_dependencies", "depends_on", depends_on),
        ("set_linked_artifacts", "linked_artifacts", linked_artifacts),
        ("set_parent", "parent_id", parent_task_id),
    ]
    changed_fields: List[str] = []
    timestamp = utc_now()
    refs = [str(item).strip() for item in list(source_refs or []) if str(item).strip()]
    for operation, field, value in updates:
        if value is None:
            continue
        normalized: Any = value
        if isinstance(value, list):
            normalized = [str(item).strip() for item in value if str(item).strip()]
        if current.get(field) == normalized:
            continue
        store.append_jsonl(
            store.work_item_events_path(workspace_id),
            {
                "event_id": make_id("work-item-event"),
                "workspace_id": workspace_id,
                "work_item_id": task_id,
                "operation": operation,
                "timestamp": timestamp,
                "actor": agent_id,
                "payload": {field: normalized},
                "source_refs": refs,
            },
        )
        changed_fields.append(field)
    if not changed_fields:
        return {**current, "unchanged": True}
    append_workspace_activity_event(
        root,
        workspace_id,
        task_id=task_id,
        agent_id=agent_id,
        surface=surface,
        session_id=session_id,
        event_type="task_updated",
        summary=f"Updated task {task_id}: {', '.join(changed_fields)}",
        reasoning=str(reasoning).strip(),
        metadata={"changed_fields": changed_fields, "source_refs": refs},
        store=store,
    )
    _refresh_workspace_atlas(root, workspace_id, store=store)
    return next(row for row in list_workspace_tasks(root, workspace_id, limit=1000, store=store) if row.get("task_id") == task_id)


def _reduce_blockers(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    latest: Dict[str, Dict[str, Any]] = {}
    for row in sorted(rows, key=lambda item: (item.get("updated_at", item.get("created_at", "")), item.get("blocker_id", ""))):
        payload = dict(row)
        latest[str(payload.get("blocker_id", ""))] = payload
    return [row for row in latest.values() if row.get("blocker_id")]


def record_workspace_blocker(
    root: Path,
    workspace_id: str,
    *,
    task_id: str,
    agent_id: str,
    surface: str,
    session_id: str,
    reason: str,
    next_action: str = "",
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    store = _resolve_store(root, store)
    load_workspace_manifest(root, workspace_id, store=store)
    blocker = {
        "blocker_id": make_id("blocker"),
        "schema_version": "1.0",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "workspace_id": workspace_id,
        "task_id": task_id,
        "actor": {
            "agent_id": agent_id,
            "surface": surface,
            "session_id": session_id,
        },
        "reason": reason,
        "next_action": next_action,
        "status": "active",
    }
    store.append_jsonl(store.blockers_path(workspace_id), blocker)
    append_workspace_activity_event(
        root,
        workspace_id,
        task_id=task_id,
        agent_id=agent_id,
        surface=surface,
        session_id=session_id,
        event_type="blocked",
        summary=reason,
        reasoning=next_action,
        blockers=[reason],
        handoff_refs=[next_action] if next_action else [],
        metadata={"blocker_id": blocker["blocker_id"]},
        store=store,
    )
    _refresh_workspace_atlas(root, workspace_id, store=store)
    return blocker


def list_workspace_blockers(
    root: Path,
    workspace_id: str,
    *,
    task_id: str = "",
    include_inactive: bool = False,
    limit: int = 20,
    store: WorkspaceStore | None = None,
) -> List[Dict[str, Any]]:
    store = _resolve_store(root, store)
    load_workspace_manifest(root, workspace_id, store=store)
    rows = _reduce_blockers(store.read_jsonl(store.blockers_path(workspace_id)))
    if task_id:
        rows = [row for row in rows if row.get("task_id", "") == task_id]
    if not include_inactive:
        rows = [row for row in rows if row.get("status") == "active"]
    rows.sort(key=lambda row: (row.get("updated_at", row.get("created_at", "")), row.get("blocker_id", "")), reverse=True)
    return rows[:limit]


def resolve_workspace_blocker(
    root: Path,
    workspace_id: str,
    *,
    blocker_id: str,
    agent_id: str,
    surface: str,
    session_id: str,
    reasoning: str,
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    store = _resolve_store(root, store)
    blockers = list_workspace_blockers(root, workspace_id, include_inactive=True, limit=1000, store=store)
    blocker = next((row for row in blockers if row.get("blocker_id") == blocker_id), None)
    if blocker is None:
        raise FileNotFoundError(f"Blocker not found: {blocker_id}")
    if blocker.get("status") == "resolved":
        return {**blocker, "already_resolved": True}
    if not str(reasoning or "").strip():
        raise ValueError("reasoning is required")
    resolved = {
        **blocker,
        "updated_at": utc_now(),
        "status": "resolved",
        "resolution": str(reasoning).strip(),
        "resolved_by": {"agent_id": agent_id, "surface": surface, "session_id": session_id},
    }
    store.append_jsonl(store.blockers_path(workspace_id), resolved)
    append_workspace_activity_event(
        root,
        workspace_id,
        task_id=str(blocker.get("task_id", "") or ""),
        agent_id=agent_id,
        surface=surface,
        session_id=session_id,
        event_type="blocker_resolved",
        summary=f"Resolved blocker {blocker_id}",
        reasoning=str(reasoning).strip(),
        metadata={"blocker_id": blocker_id},
        store=store,
    )
    _refresh_workspace_atlas(root, workspace_id, store=store)
    return resolved


def record_workspace_decision(
    root: Path,
    workspace_id: str,
    *,
    task_id: str,
    agent_id: str,
    surface: str,
    session_id: str,
    summary: str,
    reasoning: str,
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    store = _resolve_store(root, store)
    load_workspace_manifest(root, workspace_id, store=store)
    decision = {
        "decision_id": make_id("decision"),
        "schema_version": "1.0",
        "created_at": utc_now(),
        "workspace_id": workspace_id,
        "task_id": task_id,
        "actor": {
            "agent_id": agent_id,
            "surface": surface,
            "session_id": session_id,
        },
        "summary": summary,
        "reasoning": reasoning,
        "status": "accepted",
    }
    store.append_jsonl(store.decisions_path(workspace_id), decision)
    append_workspace_activity_event(
        root,
        workspace_id,
        task_id=task_id,
        agent_id=agent_id,
        surface=surface,
        session_id=session_id,
        event_type="decided",
        summary=summary,
        reasoning=reasoning,
        decision_refs=[decision["decision_id"]],
        store=store,
    )
    _refresh_workspace_atlas(root, workspace_id, store=store)
    return decision


def list_workspace_decisions(
    root: Path,
    workspace_id: str,
    *,
    task_id: str = "",
    limit: int = 20,
    store: WorkspaceStore | None = None,
) -> List[Dict[str, Any]]:
    store = _resolve_store(root, store)
    load_workspace_manifest(root, workspace_id, store=store)
    rows = store.read_jsonl(store.decisions_path(workspace_id))
    if task_id:
        rows = [row for row in rows if row.get("task_id", "") == task_id]
    rows = list(reversed(rows))
    return rows[:limit]


def record_workspace_test_run(
    root: Path,
    workspace_id: str,
    *,
    task_id: str,
    agent_id: str,
    surface: str,
    session_id: str,
    test_name: str,
    result: str,
    evidence_ref: str = "",
    notes: str = "",
    command_or_protocol: str = "",
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    store = _resolve_store(root, store)
    load_workspace_manifest(root, workspace_id, store=store)
    test_name = str(test_name or "").strip()
    if not test_name:
        raise ValueError("test_name is required")
    test_id = f"{task_id}:{slugify(test_name)}"
    cases_path = store.test_cases_path(workspace_id)
    runs_path = store.test_runs_path(workspace_id)
    existing_cases = {row.get("test_id", ""): row for row in store.read_jsonl(cases_path)}
    if test_id not in existing_cases:
        store.append_jsonl(
            cases_path,
            {
                "test_id": test_id,
                "workspace_id": workspace_id,
                "work_item_id": task_id,
                "test_kind": "verification",
                "intent": test_name,
                "command_or_protocol": command_or_protocol,
                "expected_signal": result,
                "risk_level": "medium",
                "status": "planned",
                "created_at": utc_now(),
            },
        )
    run = {
        "run_id": make_id("test-run"),
        "workspace_id": workspace_id,
        "test_id": test_id,
        "timestamp": utc_now(),
        "actor": agent_id,
        "result": result,
        "evidence_ref": evidence_ref,
        "notes": notes,
        "command_or_protocol": command_or_protocol,
    }
    store.append_jsonl(runs_path, run)
    append_workspace_activity_event(
        root,
        workspace_id,
        task_id=task_id,
        agent_id=agent_id,
        surface=surface,
        session_id=session_id,
        event_type="tested",
        summary=f"Recorded verification {test_name}",
        reasoning=notes or command_or_protocol,
        verification=[evidence_ref] if evidence_ref else [result],
        metadata={"test_id": test_id, "result": result},
        store=store,
    )
    _refresh_workspace_atlas(root, workspace_id, store=store)
    return {**run, "test_name": test_name}


def list_workspace_tests(
    root: Path,
    workspace_id: str,
    *,
    task_id: str = "",
    limit: int = 20,
    store: WorkspaceStore | None = None,
) -> List[Dict[str, Any]]:
    store = _resolve_store(root, store)
    load_workspace_manifest(root, workspace_id, store=store)
    tests = _reduce_tests(
        store.read_jsonl(store.test_cases_path(workspace_id)),
        store.read_jsonl(store.test_runs_path(workspace_id)),
    )
    if task_id:
        tests = [row for row in tests if row.get("work_item_id", "") == task_id]
    tests.sort(key=lambda row: (row.get("latest_run_at", ""), row.get("created_at", ""), row.get("test_id", "")), reverse=True)
    return tests[:limit]


def evaluate_workspace_release_gate(root: Path, workspace_id: str, *, store: WorkspaceStore | None = None) -> Dict[str, Any]:
    store = _resolve_store(root, store)
    manifest = load_workspace_manifest(root, workspace_id, store=store)
    tasks = list_workspace_tasks(root, workspace_id, limit=200, store=store)
    claims = list_workspace_claims(root, workspace_id, store=store)
    blockers = list_workspace_blockers(root, workspace_id, store=store)
    tests = list_workspace_tests(root, workspace_id, limit=200, store=store)
    repository_snapshots = store.read_jsonl(store.repository_snapshots_path(workspace_id))
    repository_snapshot = dict(repository_snapshots[-1]) if repository_snapshots else {}
    tests_by_task: Dict[str, List[Dict[str, Any]]] = {}
    for row in tests:
        tests_by_task.setdefault(str(row.get("work_item_id", "") or ""), []).append(row)

    reasons: List[str] = []
    if claims:
        reasons.append("active_claims")
    if blockers:
        reasons.append("active_blockers")
    if not str(repository_snapshot.get("source_revision", "") or "").strip():
        reasons.append("missing_repository_snapshot")

    active_task_statuses = {"in-progress", "in_progress", "implementing", "blocked"}
    if any(str(task.get("status", "") or "") in active_task_statuses for task in tasks):
        reasons.append("active_tasks")

    target_statuses = {"done", "review", "verification"}
    for task in tasks:
        task_id = str(task.get("task_id", "") or task.get("work_item_id", "") or "")
        if str(task.get("status", "") or "") not in target_statuses:
            continue
        task_tests = tests_by_task.get(task_id, [])
        if not any(str(row.get("latest_result", "") or "") == "passing" for row in task_tests):
            reasons.append("missing_verification")
            break

    verified_task_count = sum(
        1
        for task in tasks
        if any(
            str(row.get("latest_result", "") or "") == "passing"
            for row in tests_by_task.get(str(task.get("task_id", "") or task.get("work_item_id", "") or ""), [])
        )
    )
    if verified_task_count == 0 and "missing_verification" not in reasons:
        reasons.append("missing_verification")

    return {
        "workspace_id": workspace_id,
        "status": "ready" if not reasons else "blocked",
        "reasons": reasons,
        "task_count": len(tasks),
        "active_claim_count": len(claims),
        "active_blocker_count": len(blockers),
        "verified_task_count": verified_task_count,
        "artifact_roots": list(manifest.get("artifact_roots", [])),
        "source_revision": str(repository_snapshot.get("source_revision", "") or ""),
        "repository_observed_at": str(repository_snapshot.get("observed_at", "") or ""),
    }


def claim_workspace_task(
    root: Path,
    workspace_id: str,
    *,
    task_id: str,
    agent_id: str,
    surface: str,
    session_id: str,
    intent: str,
    claimed_paths: List[str],
    ttl_seconds: int = 3600,
    override: bool = False,
    run_id: str = "",
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    store = _resolve_store(root, store)
    manifest = load_workspace_manifest(root, workspace_id, store=store)
    resolved_paths = [str(path).strip() for path in claimed_paths if str(path).strip()]
    active_claims = list_workspace_claims(root, workspace_id, store=store)
    if not override:
        for claim in active_claims:
            other_actor = dict(claim.get("actor", {}))
            if other_actor.get("agent_id") == agent_id and claim.get("task_id") == task_id:
                continue
            if any(_path_overlaps(left, right) for left in resolved_paths for right in list(claim.get("claimed_paths", []) or [])):
                raise ValueError(
                    f"Claim overlaps active claim {claim.get('claim_id', '')} held by {other_actor.get('agent_id', 'unknown')}"
                )
    for path in resolved_paths:
        if manifest["artifact_roots"] and not any(_path_overlaps(path, root_path) for root_path in manifest["artifact_roots"]):
            raise ValueError(f"Claimed path outside workspace artifact roots: {path}")

    claim = {
        "claim_id": make_id("claim"),
        "schema_version": "1.0",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=max(ttl_seconds, 60))).replace(microsecond=0).isoformat(),
        "workspace_id": workspace_id,
        "task_id": task_id,
        "actor": {
            "agent_id": agent_id,
            "surface": surface,
            "session_id": session_id,
        },
        "intent": intent,
        "claimed_paths": resolved_paths,
        "status": "active",
        "run_id": str(run_id or "").strip(),
    }
    store.append_jsonl(store.claims_path(workspace_id), claim)
    append_workspace_activity_event(
        root,
        workspace_id,
        task_id=task_id,
        agent_id=agent_id,
        surface=surface,
        session_id=session_id,
        event_type="claimed",
        summary=f"Claimed task {task_id}",
        reasoning=intent,
        files_touched=resolved_paths,
        metadata={"claim_id": claim["claim_id"]},
        store=store,
    )
    _refresh_workspace_atlas(root, workspace_id, store=store)
    return claim


def release_workspace_task_claims(
    root: Path,
    workspace_id: str,
    *,
    task_id: str,
    agent_id: str,
    surface: str,
    session_id: str,
    summary: str,
    reasoning: str,
    next_action: str = "",
    run_id: str = "",
    source_revision: str = "",
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    store = _resolve_store(root, store)
    load_workspace_manifest(root, workspace_id, store=store)
    active_claims = list_workspace_claims(root, workspace_id, store=store)
    released: List[str] = []
    timestamp = utc_now()
    for claim in active_claims:
        actor = dict(claim.get("actor", {}))
        if claim.get("task_id") != task_id or actor.get("agent_id") != agent_id:
            continue
        released.append(str(claim.get("claim_id", "")))
        store.append_jsonl(
            store.claims_path(workspace_id),
            {
                **claim,
                "updated_at": timestamp,
                "status": "released",
            },
        )
    append_workspace_activity_event(
        root,
        workspace_id,
        task_id=task_id,
        agent_id=agent_id,
        surface=surface,
        session_id=session_id,
        event_type="handoff",
        summary=summary,
        reasoning=reasoning,
        handoff_refs=[next_action] if next_action else [],
        metadata={"released_claim_ids": released, "next_action": next_action, "run_id": run_id, "source_revision": source_revision},
        store=store,
    )
    _refresh_workspace_atlas(root, workspace_id, store=store)
    return {"released_claim_ids": released}


def complete_workspace_task(
    root: Path,
    workspace_id: str,
    *,
    task_id: str,
    agent_id: str,
    surface: str,
    session_id: str,
    summary: str,
    reasoning: str,
    files_touched: List[str],
    commands_run: List[str],
    residual_risks: List[str],
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    store = _resolve_store(root, store)
    manifest = load_workspace_manifest(root, workspace_id, store=store)
    previous_completions = [
        row
        for row in list_workspace_activity_events(root, workspace_id, task_id=task_id, limit=200, store=store)
        if row.get("event_type") == "completed"
    ]
    if previous_completions:
        previous = previous_completions[0]
        return {
            "workspace_id": workspace_id,
            "task_id": task_id,
            "status": "done",
            "already_completed": True,
            "completion_event_id": previous.get("event_id", ""),
            "released_claim_ids": list(previous.get("metadata", {}).get("released_claim_ids", []) or []),
        }

    tasks = list_workspace_tasks(root, workspace_id, limit=500, store=store)
    task = next((row for row in tasks if row.get("task_id") == task_id or row.get("work_item_id") == task_id), None)
    if task is None:
        raise FileNotFoundError(f"Task not found: {task_id}")

    normalized_files = [str(item).strip() for item in files_touched if str(item).strip()]
    normalized_commands = [str(item).strip() for item in commands_run if str(item).strip()]
    normalized_risks = [str(item).strip() for item in residual_risks if str(item).strip()]
    missing: List[str] = []
    if not str(summary or "").strip():
        missing.append("summary")
    if not str(reasoning or "").strip():
        missing.append("reasoning")
    if not normalized_files:
        missing.append("files_touched")
    if not normalized_commands:
        missing.append("commands_run")
    if not normalized_risks:
        missing.append("residual_risks")
    for path in normalized_files:
        if manifest["artifact_roots"] and not any(_path_overlaps(path, root_path) for root_path in manifest["artifact_roots"]):
            raise ValueError(f"Completed file outside workspace artifact roots: {path}")

    blockers = list_workspace_blockers(root, workspace_id, task_id=task_id, limit=200, store=store)
    if blockers:
        missing.append("active_blockers")
    open_child_ids = [
        str(child.get("task_id", child.get("work_item_id", "")) or "")
        for child in tasks
        if str(child.get("parent_id", "") or "") == task_id and str(child.get("status", "") or "") not in {"done", "cancelled"}
    ]
    if open_child_ids:
        missing.append(f"open_subtasks:{','.join(open_child_ids)}")
    tests = list_workspace_tests(root, workspace_id, task_id=task_id, limit=200, store=store)
    passing = [row for row in tests if str(row.get("latest_result", "") or "") == "passing"]
    if not passing:
        missing.append("passing_verification")
    elif not any(str(row.get("latest_evidence_ref", "") or "").strip() for row in passing):
        missing.append("verification_evidence")
    if missing:
        raise WorkspaceCompletionError(missing)

    timestamp = utc_now()
    store.append_jsonl(
        store.work_item_events_path(workspace_id),
        {
            "event_id": make_id("work-item-event"),
            "workspace_id": workspace_id,
            "work_item_id": task_id,
            "operation": "set_status",
            "timestamp": timestamp,
            "actor": agent_id,
            "payload": {"status": "done"},
            "source_refs": [str(row.get("latest_evidence_ref", "") or "") for row in passing if row.get("latest_evidence_ref")],
        },
    )
    released: List[str] = []
    for claim in list_workspace_claims(root, workspace_id, store=store):
        actor = dict(claim.get("actor", {}) or {})
        if claim.get("task_id") != task_id or actor.get("agent_id") != agent_id:
            continue
        released.append(str(claim.get("claim_id", "") or ""))
        store.append_jsonl(store.claims_path(workspace_id), {**claim, "updated_at": timestamp, "status": "released"})
    event = append_workspace_activity_event(
        root,
        workspace_id,
        task_id=task_id,
        agent_id=agent_id,
        surface=surface,
        session_id=session_id,
        event_type="completed",
        summary=str(summary).strip(),
        reasoning=str(reasoning).strip(),
        files_touched=normalized_files,
        commands_run=normalized_commands,
        verification=[str(row.get("latest_evidence_ref", "") or "") for row in passing],
        metadata={
            "residual_risks": normalized_risks,
            "released_claim_ids": released,
            "previous_status": task.get("status", ""),
        },
        store=store,
    )
    _refresh_workspace_atlas(root, workspace_id, store=store)
    return {
        "workspace_id": workspace_id,
        "task_id": task_id,
        "status": "done",
        "already_completed": False,
        "completion_event_id": event["event_id"],
        "released_claim_ids": released,
    }


def prepare_workspace_task(
    root: Path,
    workspace_id: str,
    *,
    task_id: str = "",
    agent_id: str = "",
    surface: str = "",
    session_id: str = "",
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    store = _resolve_store(root, store)
    manifest = load_workspace_manifest(root, workspace_id, store=store)
    tasks = list_workspace_tasks(root, workspace_id, limit=50, store=store)
    active_claims = list_workspace_claims(root, workspace_id, store=store)
    blockers = list_workspace_blockers(root, workspace_id, task_id=task_id, limit=20, store=store)
    decisions = list_workspace_decisions(root, workspace_id, task_id=task_id, limit=20, store=store)
    tests = list_workspace_tests(root, workspace_id, task_id=task_id, limit=20, store=store)
    recent_activity = list_workspace_activity_events(root, workspace_id, task_id=task_id, limit=50, store=store)
    substantive_activity = [row for row in recent_activity if row.get("event_type") != "claimed"]
    if substantive_activity:
        recent_activity = substantive_activity[:20]
    else:
        recent_activity = recent_activity[:20]
    selected_task = (
        next(
            (
                task
                for task in tasks
                if task.get("task_id") == task_id or task.get("work_item_id") == task_id
            ),
            None,
        )
        if task_id
        else None
    )
    return {
        "workspace": manifest,
        "task": selected_task or {},
        "tasks": tasks,
        "active_claims": active_claims,
        "blockers": blockers,
        "decisions": decisions,
        "tests": tests,
        "recent_activity": recent_activity,
        "agent": {
            "agent_id": agent_id,
            "surface": surface,
            "session_id": session_id,
        },
    }


def render_workspace_tasks(root: Path, workspace_id: str, *, store: WorkspaceStore | None = None) -> str:
    tasks = list_workspace_tasks(root, workspace_id, store=store)
    if not tasks:
        return f"Workspace {workspace_id} has no tracked tasks."
    lines = [f"Workspace {workspace_id} tasks:"]
    task_ids = {str(task.get("task_id", "") or "") for task in tasks}
    top_level = [
        task
        for task in tasks
        if not str(task.get("parent_id", "") or "") or str(task.get("parent_id", "") or "") not in task_ids
    ]
    for task in top_level[:12]:
        lines.append(
            f"- {task.get('work_item_id', 'unknown')} [{task.get('status', 'unknown')}] {task.get('title', '')}"
        )
        for child in [item for item in tasks if str(item.get("parent_id", "") or "") == str(task.get("task_id", "") or "")]:
            lines.append(
                f"  - {child.get('work_item_id', 'unknown')} [{child.get('status', 'unknown')}] {child.get('title', '')}"
            )
    return "\n".join(lines)


def render_workspace_status(root: Path, workspace_id: str, *, store: WorkspaceStore | None = None) -> str:
    manifest = load_workspace_manifest(root, workspace_id, store=store)
    tasks = list_workspace_tasks(root, workspace_id, store=store)
    active_claims = list_workspace_claims(root, workspace_id, store=store)
    blockers = list_workspace_blockers(root, workspace_id, limit=6, store=store)
    decisions = list_workspace_decisions(root, workspace_id, limit=3, store=store)
    tests = list_workspace_tests(root, workspace_id, limit=6, store=store)
    recent = list_workspace_activity_events(root, workspace_id, limit=3, store=store)
    lines = [
        f"Workspace: {workspace_id}",
        f"Status: {manifest.get('status', 'active')}",
        f"Goals: {manifest.get('goal', '') or 'none'}",
        f"Artifact roots: {', '.join(manifest.get('artifact_roots', [])) or 'none'}",
        f"Objectives: {', '.join(manifest.get('objectives', [])) or 'none'}",
        f"Tasks: {len(tasks)}",
        f"Active claims: {len(active_claims)}",
        f"Active blockers: {len(blockers)}",
        f"Decisions: {len(decisions)}",
        f"Tests tracked: {len(tests)}",
    ]
    if recent:
        lines.append("Recent activity:")
        for row in recent:
            lines.append(
                f"- {row.get('event_type', 'event')} {row.get('task_id', '')}: {row.get('summary', '')}"
            )
    return "\n".join(lines)
