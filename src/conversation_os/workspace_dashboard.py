"""Git-projection workspace dashboard snapshot for Workspace OS UI."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MODULE_ID = "kernel.workspace.workspace_dashboard"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = ("MODULE_ID", "CONTRACT_VERSION", "build_workspace_dashboard_snapshot")
__all__ = list(PUBLIC_API)

_TASK_ROW = re.compile(
    r"^\|\s*`([^`]+)`\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$"
)
_CONTINUITY_META = re.compile(r"<!--\s*(\w+):\s*(.*?)\s*-->")


def _git_head(root: Path) -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, stderr=subprocess.DEVNULL)
            .decode("utf-8")
            .strip()
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _read_continuity_meta(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    meta: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines()[:12]:
        match = _CONTINUITY_META.match(line.strip())
        if match:
            meta[match.group(1)] = match.group(2)
    return meta


def parse_tasks_markdown(text: str) -> list[dict[str, str]]:
    tasks: list[dict[str, str]] = []
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        match = _TASK_ROW.match(line.strip())
        if not match:
            continue
        task_id, status, owner, title, gate = match.groups()
        tasks.append(
            {
                "task_id": task_id.strip(),
                "status": status.strip(),
                "owner": owner.strip(),
                "title": title.strip(),
                "gate": gate.strip(),
            }
        )
    return tasks


def _workboard_dir(manifest: dict[str, Any], workspace_id: str) -> Path | None:
    workboard = str(manifest.get("workboard", "") or "").strip()
    if workboard:
        return Path(workboard).parent
    workboard_ref = str(manifest.get("workboard_ref", "") or "").strip()
    if workboard_ref:
        return Path(workboard_ref).parent
    candidate = Path("docs/workboards") / workspace_id
    return candidate if (candidate / "TASKS.md").is_file() else None


def _tasks_summary_line(tasks_md: Path) -> str:
    if not tasks_md.is_file():
        return ""
    for line in tasks_md.read_text(encoding="utf-8").splitlines():
        if line.startswith("Live workspace"):
            return line.strip()
    return ""


def _release_contract(workspace_dir: Path) -> dict[str, str]:
    derived = workspace_dir / "derived"
    for pattern in ("*RELEASE_DEPENDENCY_CONTRACT.json", "KERNEL_RELEASE_DEPENDENCY_CONTRACT.json"):
        matches = sorted(derived.glob(pattern))
        if matches:
            try:
                payload = json.loads(matches[0].read_text(encoding="utf-8"))
                return {
                    "path": str(matches[0].as_posix()),
                    "provider_contract_version": str(payload.get("provider_contract_version", "") or ""),
                    "release_git_revision": str(payload.get("release_git_revision", "") or ""),
                }
            except json.JSONDecodeError:
                break
    return {}


def _load_git_manifest(root: Path, workspace_id: str) -> dict[str, Any]:
    path = root / "docs/workspaces" / workspace_id / "manifest.json"
    if not path.is_file():
        return {"workspace_id": workspace_id}
    return json.loads(path.read_text(encoding="utf-8"))


def build_workspace_entry(root: Path, workspace_id: str) -> dict[str, Any]:
    manifest = _load_git_manifest(root, workspace_id)
    workspace_dir = root / "docs/workspaces" / workspace_id
    workboard_dir = _workboard_dir(manifest, workspace_id)
    tasks_md = (workboard_dir / "TASKS.md") if workboard_dir else None
    tasks = parse_tasks_markdown(tasks_md.read_text(encoding="utf-8")) if tasks_md and tasks_md.is_file() else []
    continuity_path = workspace_dir / "CONTINUITY.md"
    continuity_meta = _read_continuity_meta(continuity_path)
    status_counts: dict[str, int] = {}
    for task in tasks:
        status = task["status"]
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "workspace_id": workspace_id,
        "label": str(manifest.get("label", workspace_id) or workspace_id),
        "status": str(manifest.get("status", "") or ""),
        "maturation_stage": str(manifest.get("maturation_stage", "") or ""),
        "parent_workspace_id": str(manifest.get("parent_workspace_id", "") or ""),
        "program_task_id": str(manifest.get("program_task_id", "") or ""),
        "goal": str(manifest.get("goal", "") or "")[:280],
        "workboard_path": str(tasks_md) if tasks_md else "",
        "continuity_path": str(continuity_path.relative_to(root)) if continuity_path.is_file() else "",
        "continuity_meta": continuity_meta,
        "tasks_summary": _tasks_summary_line(tasks_md) if tasks_md else "",
        "tasks": tasks,
        "status_counts": status_counts,
        "release": _release_contract(workspace_dir),
        "readme_path": f"docs/workspaces/{workspace_id}/README.md",
    }


def build_workspace_dashboard_snapshot(root: Path) -> dict[str, Any]:
    workspaces_root = root / "docs/workspaces"
    workspace_ids: list[str] = []
    for manifest_path in sorted(workspaces_root.glob("*/manifest.json")):
        workspace_ids.append(manifest_path.parent.name)

    entries = {workspace_id: build_workspace_entry(root, workspace_id) for workspace_id in workspace_ids}

    parent_links: list[dict[str, str]] = []
    for workspace_id, entry in entries.items():
        manifest = _load_git_manifest(root, workspace_id)
        for child in list(manifest.get("child_workspaces", []) or []):
            child_id = str(child.get("workspace_id", "") or "").strip()
            if child_id:
                parent_links.append(
                    {
                        "parent": workspace_id,
                        "child": child_id,
                        "program_task_id": str(child.get("program_task_id", "") or ""),
                        "status": str(child.get("status", "") or ""),
                    }
                )

    lanes = ("backlog", "ready", "in-progress", "review", "blocked", "done")
    program_rollups: dict[str, dict[str, int]] = {}
    for entry in entries.values():
        program_rollups[entry["workspace_id"]] = {lane: entry["status_counts"].get(lane, 0) for lane in lanes}

    return {
        "schema": "workspace_dashboard_snapshot_v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repository_revision": _git_head(root),
        "source": "git_projections",
        "workspace_count": len(entries),
        "workspaces": entries,
        "hierarchy_links": parent_links,
        "lane_order": list(lanes),
    }
