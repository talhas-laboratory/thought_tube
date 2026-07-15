from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .storage import append_jsonl, utc_now
from .workspace_client import WorkspaceClient, WorkspaceClientError
from .workspace_continuity import render_workspace_continuity_markdown
from .workspace_coordination import (
    list_workspace_blockers,
    list_workspace_tasks,
    load_workspace_manifest,
)
from .workspace_store import WorkspaceStore


MODULE_ID = "kernel.workspace.workspace_projection_sync"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "load_repo_workspace_manifest",
    "resolve_projection_paths",
    "sync_workspace_projections",
    "check_workspace_projections",
)
__all__ = list(PUBLIC_API)

_STATUS_LINE = re.compile(r"^Status:\s*.+$", re.MULTILINE)
_OWNER_LINE = re.compile(r"^Owner:\s*.+$", re.MULTILINE)
_TASKS_TABLE_ROW = re.compile(
    r"^\|\s*`(?P<id>[^`]+)`\s*\|\s*(?P<status>[^|]+)\s*\|\s*(?P<owner>[^|]+)\s*\|\s*(?P<title>[^|]+)\s*\|\s*(?P<gate>[^|]+)\s*\|$"
)
_CONTINUITY_REVISION = re.compile(r"canonical_revision:\s*([^\n ]+)")


def load_repo_workspace_manifest(root: Path, workspace_id: str) -> dict[str, Any]:
    docs_manifest = root / "docs" / "workspaces" / workspace_id / "manifest.json"
    if docs_manifest.is_file():
        payload = json.loads(docs_manifest.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    return load_workspace_manifest(root, workspace_id)


def resolve_projection_paths(root: Path, manifest: dict[str, Any]) -> dict[str, Path]:
    workspace_id = str(manifest.get("workspace_id", "") or "").strip()
    workboard_ref = str(manifest.get("workboard", "") or manifest.get("workboard_ref", "") or "").strip()
    if workboard_ref:
        workboard_dir = (root / workboard_ref).resolve().parent
    else:
        workboard_dir = (root / "docs" / "workboards" / workspace_id).resolve()
    continuity_ref = str(manifest.get("continuity_projection", "") or "").strip()
    if continuity_ref:
        continuity_path = (root / continuity_ref).resolve()
    else:
        continuity_path = (root / "docs" / "workspaces" / workspace_id / "CONTINUITY.md").resolve()
    return {
        "workboard_dir": workboard_dir,
        "tasks_index": workboard_dir / "TASKS.md",
        "tasks_dir": workboard_dir / "tasks",
        "lanes_dir": workboard_dir / "lanes",
        "updates_log": workboard_dir / "UPDATES.jsonl",
        "continuity_path": continuity_path,
    }


def _normalize_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for row in tasks:
        task_id = str(row.get("task_id", "") or row.get("work_item_id", "") or "").strip()
        if not task_id:
            continue
        normalized.append(
            {
                "task_id": task_id,
                "status": str(row.get("status", "backlog") or "backlog").strip(),
                "owner": str(row.get("owner", "") or "").strip() or "unassigned",
                "title": str(row.get("title", "") or task_id).strip(),
                "gate": str(row.get("guard_status", "") or "verification").strip() or "verification",
            }
        )
    normalized.sort(key=lambda item: item["task_id"])
    return normalized


def _fetch_live_snapshot(
    client: WorkspaceClient,
    workspace_id: str,
    *,
    agent_id: str,
    surface: str,
    session_id: str,
) -> dict[str, Any]:
    prepared = client.prepare(
        workspace_id,
        agent_id=agent_id,
        surface=surface,
        session_id=session_id,
    )
    continuity = client.continuity(workspace_id)
    return {
        "tasks": _normalize_tasks(list(prepared.get("tasks", []) or [])),
        "blockers": list(prepared.get("blockers", []) or []),
        "continuity": continuity,
        "canonical_revision": str(continuity.get("canonical_revision", "") or ""),
    }


def _fetch_offline_snapshot(root: Path, workspace_id: str, *, store: WorkspaceStore | None = None) -> dict[str, Any]:
    from .workspace_continuity import assemble_workspace_continuity_export

    tasks = _normalize_tasks(list_workspace_tasks(root, workspace_id, limit=200, store=store))
    blockers = list_workspace_blockers(root, workspace_id, limit=100, store=store)
    continuity = assemble_workspace_continuity_export(root, workspace_id, store=store)
    return {
        "tasks": tasks,
        "blockers": blockers,
        "continuity": continuity,
        "canonical_revision": str(continuity.get("canonical_revision", "") or ""),
    }


def _patch_task_packet(text: str, *, status: str, owner: str) -> str:
    updated = _STATUS_LINE.sub(f"Status: {status}", text, count=1)
    if updated == text and "Status:" not in text:
        updated = f"Status: {status}\n" + text
    if owner and owner != "unassigned":
        if _OWNER_LINE.search(updated):
            updated = _OWNER_LINE.sub(f"Owner: {owner}", updated, count=1)
        else:
            updated = updated.replace(f"Status: {status}\n", f"Status: {status}\nOwner: {owner}\n", 1)
    return updated


def _render_task_packet(task: dict[str, Any]) -> str:
    """Render the minimum resumable packet for a live task lacking a Git projection.

    Status and owner remain a projection of the live workspace. The packet gives
    a future agent a stable place to add scope, verification, and handoff detail
    without inventing a second coordination record.
    """
    task_id = task["task_id"]
    title = task["title"]
    return "\n".join(
        [
            f"# {task_id}: {title}",
            "",
            f"Status: {task['status']}",
            f"Owner: {task['owner']}",
            f"Current gate: {task['gate']}",
            "",
            "## Scope",
            "",
            "Live task created before its Git task packet was materialized.",
            "Refine scope, constraints, verification, and handoff notes here; update coordination state through the live workspace API.",
            "",
            "## Verification Evidence",
            "",
            "- Not recorded in this projection yet.",
            "",
            "## Handoff Notes",
            "",
            "- Read the live workspace context before claiming this task.",
            "",
        ]
    )


def _render_tasks_index(tasks: list[dict[str, Any]], *, blockers: list[dict[str, Any]]) -> str:
    lines = [
        "# Tasks",
        "",
        "| id | status | owner | title | gate |",
        "|---|---|---|---|---|",
    ]
    for task in tasks:
        lines.append(
            f"| `{task['task_id']}` | {task['status']} | {task['owner']} | {task['title']} | {task['gate']} |"
        )
    lines.extend(
        [
            "",
            "Status values: `backlog`, `ready`, `in-progress`, `review`, `blocked`, `done`.",
            "A task may enter `done` only when every required gate in `GATES.md` has evidence.",
            "",
            _render_tasks_summary(tasks, blockers),
            "",
            "**Local agent start:** [`LOCAL-AGENT-BOOT.md`](./LOCAL-AGENT-BOOT.md)",
            "",
        ]
    )
    return "\n".join(lines)


def _render_tasks_summary(tasks: list[dict[str, Any]], blockers: list[dict[str, Any]]) -> str:
    if not tasks:
        return "No live tasks are currently registered for this workboard."
    statuses = {str(task["status"]) for task in tasks}
    if len(statuses) == 1:
        status = next(iter(statuses))
        summary = f"Live workspace tasks are synchronized at `{status}`."
    else:
        parts = ", ".join(f"`{task['task_id']}`={task['status']}" for task in tasks)
        summary = f"Live workspace task statuses: {parts}."
    open_blockers = [
        item
        for item in blockers
        if str(item.get("status", "open") or "open").strip().lower() not in {"resolved", "closed"}
    ]
    if open_blockers:
        summary += f" {len(open_blockers)} open blocker(s) remain in the live workspace."
    else:
        summary += " No open blockers in the live workspace."
    summary += " Git projections were refreshed from live coordination state."
    return summary


def _sync_lane_entries(lanes_dir: Path, tasks: list[dict[str, Any]], tasks_dir: Path) -> list[str]:
    changed: list[str] = []
    for status in ("backlog", "ready", "in-progress", "verification", "review", "blocked", "done", "cancelled"):
        (lanes_dir / status).mkdir(parents=True, exist_ok=True)
    for task in tasks:
        task_id = task["task_id"]
        status = task["status"]
        source = tasks_dir / f"{task_id}.md"
        if not source.is_file():
            continue
        for lane_dir in lanes_dir.iterdir():
            if not lane_dir.is_dir():
                continue
            lane_file = lane_dir / f"{task_id}.md"
            if lane_dir.name == status:
                if not lane_file.exists() or lane_file.read_text(encoding="utf-8") != source.read_text(encoding="utf-8"):
                    lane_file.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
                    changed.append(str(lane_file))
            elif lane_file.exists():
                lane_file.unlink()
                changed.append(str(lane_file))
    return changed


def _continuity_revision(path: Path) -> str:
    if not path.is_file():
        return ""
    match = _CONTINUITY_REVISION.search(path.read_text(encoding="utf-8"))
    return match.group(1) if match else ""


def _relative(root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(root.resolve()))
    except ValueError:
        return str(path)


def sync_workspace_projections(
    root: Path,
    workspace_id: str,
    *,
    api_base: str = "",
    agent_id: str = "projection-sync",
    surface: str = "cursor",
    session_id: str = "projection-sync",
    dry_run: bool = False,
    store: WorkspaceStore | None = None,
) -> dict[str, Any]:
    manifest = load_repo_workspace_manifest(root, workspace_id)
    paths = resolve_projection_paths(root, manifest)
    mode = "connected" if api_base else "offline"
    api_reachable = False
    error = ""
    try:
        if api_base:
            client = WorkspaceClient(api_base)
            snapshot = _fetch_live_snapshot(
                client,
                workspace_id,
                agent_id=agent_id,
                surface=surface,
                session_id=session_id,
            )
            api_reachable = True
        else:
            snapshot = _fetch_offline_snapshot(root, workspace_id, store=store)
    except WorkspaceClientError as exc:
        error = str(exc)
        snapshot = _fetch_offline_snapshot(root, workspace_id, store=store)
        mode = "offline_fallback"

    tasks = list(snapshot["tasks"])
    blockers = list(snapshot["blockers"])
    continuity = dict(snapshot["continuity"])
    changes: list[str] = []

    continuity_text = render_workspace_continuity_markdown(continuity)
    continuity_path = paths["continuity_path"]
    live_revision = str(snapshot.get("canonical_revision", "") or "")
    on_disk_revision = _continuity_revision(continuity_path)
    if on_disk_revision != live_revision:
        changes.append(_relative(root, continuity_path))

    tasks_index_text = _render_tasks_index(tasks, blockers=blockers)
    tasks_index_path = paths["tasks_index"]
    if not tasks_index_path.exists() or tasks_index_path.read_text(encoding="utf-8") != tasks_index_text:
        changes.append(_relative(root, tasks_index_path))

    task_file_changes: list[str] = []
    paths["tasks_dir"].mkdir(parents=True, exist_ok=True)
    for task in tasks:
        task_path = paths["tasks_dir"] / f"{task['task_id']}.md"
        if not task_path.is_file():
            task_file_changes.append(_relative(root, task_path))
            if not dry_run:
                task_path.write_text(_render_task_packet(task), encoding="utf-8")
            continue
        current = task_path.read_text(encoding="utf-8")
        updated = _patch_task_packet(current, status=task["status"], owner=task["owner"])
        if updated != current:
            task_file_changes.append(_relative(root, task_path))
            if not dry_run:
                task_path.write_text(updated, encoding="utf-8")

    lane_changes = _sync_lane_entries(paths["lanes_dir"], tasks, paths["tasks_dir"]) if not dry_run else []
    if dry_run:
        lane_changes = []

    changes.extend(task_file_changes)
    changes.extend(_relative(root, Path(item)) for item in lane_changes if item not in changes)

    if not dry_run:
        if _relative(root, continuity_path) in changes or not continuity_path.exists():
            continuity_path.parent.mkdir(parents=True, exist_ok=True)
            continuity_path.write_text(continuity_text, encoding="utf-8")
        if _relative(root, tasks_index_path) in changes or not tasks_index_path.exists():
            tasks_index_path.parent.mkdir(parents=True, exist_ok=True)
            tasks_index_path.write_text(tasks_index_text, encoding="utf-8")
        if changes and paths["updates_log"].parent.exists():
            append_jsonl(
                paths["updates_log"],
                {
                    "timestamp": utc_now(),
                    "actor": agent_id,
                    "event": "projections_synced",
                    "workspace_id": workspace_id,
                    "canonical_revision": snapshot.get("canonical_revision", ""),
                    "mode": mode,
                    "changes": changes,
                },
            )
            changes.append(_relative(root, paths["updates_log"]))

    return {
        "workspace_id": workspace_id,
        "mode": mode,
        "api_reachable": api_reachable,
        "dry_run": dry_run,
        "error": error,
        "canonical_revision": snapshot.get("canonical_revision", ""),
        "task_count": len(tasks),
        "open_blocker_count": len(
            [
                item
                for item in blockers
                if str(item.get("status", "open") or "open").strip().lower() not in {"resolved", "closed"}
            ]
        ),
        "changed": changes,
        "paths": {key: _relative(root, value) for key, value in paths.items()},
    }


def check_workspace_projections(
    root: Path,
    workspace_id: str,
    *,
    api_base: str = "",
    agent_id: str = "projection-sync",
    surface: str = "cursor",
    session_id: str = "projection-sync",
    store: WorkspaceStore | None = None,
) -> dict[str, Any]:
    result = sync_workspace_projections(
        root,
        workspace_id,
        api_base=api_base,
        agent_id=agent_id,
        surface=surface,
        session_id=session_id,
        dry_run=True,
        store=store,
    )
    paths = resolve_projection_paths(root, load_repo_workspace_manifest(root, workspace_id))
    continuity_fresh = _continuity_revision(paths["continuity_path"]) == str(result.get("canonical_revision", "") or "")
    result["fresh"] = continuity_fresh and not result["changed"]
    result["continuity_fresh"] = continuity_fresh
    return result
