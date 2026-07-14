from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .storage import ensure_dir, utc_now, workspace_context_dir, write_json, write_markdown
from .workspace_coordination import (
    evaluate_workspace_release_gate,
    list_workspace_activity_events,
    list_workspace_blockers,
    list_workspace_claims,
    list_workspace_decisions,
    list_workspace_tasks,
    list_workspace_tests,
    load_workspace_manifest,
)
from .workspace_store import WorkspaceStore


MODULE_ID = "kernel.workspace.workspace_atlas"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "build_workspace_atlas",
    "materialize_workspace_atlas",
    "workspace_atlas_paths",
)
__all__ = list(PUBLIC_API)


def workspace_atlas_paths(
    root: Path,
    workspace_id: str,
    *,
    manifest: Dict[str, Any] | None = None,
    store: WorkspaceStore | None = None,
) -> Dict[str, Path]:
    manifest = manifest or load_workspace_manifest(root, workspace_id, store=store)
    workboard_ref = str(manifest.get("workboard_ref", "") or "").strip()
    if workboard_ref:
        workboard_dir = (root / workboard_ref).resolve().parent
    else:
        workboard_dir = root / "docs" / "workboards" / workspace_id
    context_dir = workspace_context_dir(root, workspace_id)
    return {
        "context_dir": context_dir,
        "atlas_json": context_dir / "atlas.json",
        "atlas": context_dir / "atlas.md",
        "workboard_dir": workboard_dir,
        "agent_state": workboard_dir / "AGENT_STATE.md",
        "tasks_generated": workboard_dir / "TASKS.generated.md",
        "decisions_generated": workboard_dir / "DECISIONS.generated.md",
        "handoffs_generated": workboard_dir / "HANDOFFS.generated.md",
        "releases_generated": workboard_dir / "RELEASES.generated.md",
        "changed_surfaces": workboard_dir / "CHANGED_SURFACES.md",
    }


def _normalize_git_change_report(report: Dict[str, Any] | None) -> Dict[str, Any]:
    payload = dict(report or {})
    summary = dict(payload.get("summary", {}) or {})
    return {
        "summary": {
            "changed_count": int(summary.get("changed_count", 0) or 0),
            "affected_count": int(summary.get("affected_count", 0) or 0),
            "changed_files": int(summary.get("changed_files", 0) or 0),
            "risk_level": str(summary.get("risk_level", "none") or "none"),
        },
        "changed_symbols": [
            {
                "name": str(item.get("name", "") or ""),
                "filePath": str(item.get("filePath", "") or ""),
                "change_type": str(item.get("change_type", "") or ""),
            }
            for item in list(payload.get("changed_symbols", []) or [])[:25]
        ],
        "affected_processes": [
            {
                "name": str(item.get("name", "") or ""),
                "changed_steps": list(item.get("changed_steps", []) or []),
            }
            for item in list(payload.get("affected_processes", []) or [])[:12]
        ],
    }


def build_workspace_atlas(
    root: Path,
    workspace_id: str,
    *,
    git_change_report: Dict[str, Any] | None = None,
    repository_snapshot: Dict[str, Any] | None = None,
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    manifest = load_workspace_manifest(root, workspace_id, store=store)
    tasks = list_workspace_tasks(root, workspace_id, limit=100, store=store)
    claims = list_workspace_claims(root, workspace_id, store=store)
    blockers = list_workspace_blockers(root, workspace_id, limit=100, store=store)
    decisions = list_workspace_decisions(root, workspace_id, limit=100, store=store)
    tests = list_workspace_tests(root, workspace_id, limit=100, store=store)
    recent_activity = list_workspace_activity_events(root, workspace_id, limit=30, store=store)
    release_gate = evaluate_workspace_release_gate(root, workspace_id, store=store)
    git_changes = _normalize_git_change_report(git_change_report)
    return {
        "workspace": manifest,
        "counts": {
            "tasks": len(tasks),
            "active_claims": len(claims),
            "active_blockers": len(blockers),
            "decisions": len(decisions),
            "tests": len(tests),
        },
        "release_gate": release_gate,
        "tasks": tasks,
        "active_claims": claims,
        "blockers": blockers,
        "decisions": decisions,
        "tests": tests,
        "recent_activity": recent_activity,
        "git_changes": git_changes,
        "repository_snapshot": dict(repository_snapshot or {}),
        "materialized_at": utc_now(),
    }


def materialize_workspace_atlas(
    root: Path,
    workspace_id: str,
    *,
    git_change_report: Dict[str, Any] | None = None,
    repository_snapshot: Dict[str, Any] | None = None,
    store: WorkspaceStore | None = None,
) -> Dict[str, Any]:
    atlas = build_workspace_atlas(
        root,
        workspace_id,
        git_change_report=git_change_report,
        repository_snapshot=repository_snapshot,
        store=store,
    )
    paths = workspace_atlas_paths(root, workspace_id, manifest=atlas["workspace"], store=store)
    ensure_dir(paths["context_dir"])
    ensure_dir(paths["workboard_dir"])
    write_json(paths["atlas_json"], atlas)
    write_markdown(paths["atlas"], _render_atlas_markdown(atlas))
    write_markdown(paths["agent_state"], _render_agent_state_markdown(atlas))
    write_markdown(paths["tasks_generated"], _render_tasks_markdown(atlas))
    write_markdown(paths["decisions_generated"], _render_decisions_markdown(atlas))
    write_markdown(paths["handoffs_generated"], _render_handoffs_markdown(atlas))
    write_markdown(paths["releases_generated"], _render_releases_markdown(atlas))
    write_markdown(paths["changed_surfaces"], _render_changed_surfaces_markdown(atlas))
    return atlas


def _render_atlas_markdown(atlas: Dict[str, Any]) -> str:
    workspace = atlas["workspace"]
    gate = atlas["release_gate"]
    lines = [
        f"# Workspace Atlas — {workspace.get('label', workspace.get('workspace_id', 'workspace'))}",
        "",
        f"- workspace_id: `{workspace.get('workspace_id', '')}`",
        f"- status: `{workspace.get('status', 'active')}`",
        f"- release_gate: `{gate.get('status', 'blocked')}`",
        f"- artifact_roots: {', '.join(workspace.get('artifact_roots', [])) or 'none'}",
        f"- objectives: {', '.join(workspace.get('objectives', [])) or 'none'}",
        "",
        "## Counts",
        "",
        f"- tasks: {atlas['counts']['tasks']}",
        f"- active_claims: {atlas['counts']['active_claims']}",
        f"- active_blockers: {atlas['counts']['active_blockers']}",
        f"- decisions: {atlas['counts']['decisions']}",
        f"- tests: {atlas['counts']['tests']}",
    ]
    if gate.get("reasons"):
        lines.extend(["", "## Release Gate Reasons", ""])
        lines.extend(f"- {item}" for item in gate["reasons"])
    return "\n".join(lines)


def _render_agent_state_markdown(atlas: Dict[str, Any]) -> str:
    workspace = atlas["workspace"]
    gate = atlas["release_gate"]
    lines = [
        f"# Agent State — {workspace.get('workspace_id', '')}",
        "",
        f"- release_gate: `{gate.get('status', 'blocked')}`",
        f"- reasons: {', '.join(gate.get('reasons', [])) or 'none'}",
        "",
        "## Active Claims",
        "",
    ]
    claims = atlas.get("active_claims", [])
    if claims:
        lines.extend(
            f"- {item.get('task_id', '')} :: {item.get('actor', {}).get('agent_id', 'unknown')} :: {', '.join(item.get('claimed_paths', [])) or 'no paths'}"
            for item in claims[:12]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Active Blockers", ""])
    blockers = atlas.get("blockers", [])
    if blockers:
        lines.extend(
            f"- {item.get('task_id', '')} :: {item.get('reason', '')} :: next {item.get('next_action', '') or 'unspecified'}"
            for item in blockers[:12]
        )
    else:
        lines.append("- none")
    lines.extend(["", "## Recent Activity", ""])
    recent = atlas.get("recent_activity", [])
    if recent:
        lines.extend(
            f"- {item.get('event_type', '')} {item.get('task_id', '')}: {item.get('summary', '')}"
            for item in recent[:12]
        )
    else:
        lines.append("- none")
    return "\n".join(lines)


def _render_tasks_markdown(atlas: Dict[str, Any]) -> str:
    lines = ["# Tasks", ""]
    tasks = atlas.get("tasks", [])
    if tasks:
        task_ids = {str(row.get("task_id", "") or "") for row in tasks}
        for item in [
            row
            for row in tasks
            if not str(row.get("parent_id", "") or "") or str(row.get("parent_id", "") or "") not in task_ids
        ][:50]:
            lines.append(f"- {item.get('task_id', '')} [{item.get('status', 'unknown')}] {item.get('title', '')}")
            for child in [row for row in tasks if str(row.get("parent_id", "") or "") == str(item.get("task_id", "") or "")]:
                lines.append(f"  - {child.get('task_id', '')} [{child.get('status', 'unknown')}] {child.get('title', '')}")
    else:
        lines.append("- none")
    return "\n".join(lines)


def _render_decisions_markdown(atlas: Dict[str, Any]) -> str:
    lines = ["# Decisions", ""]
    decisions = atlas.get("decisions", [])
    if decisions:
        lines.extend(
            f"- {item.get('task_id', '')} :: {item.get('summary', '')} :: {item.get('decision_id', '')}"
            for item in decisions[:50]
        )
    else:
        lines.append("- none")
    return "\n".join(lines)


def _render_handoffs_markdown(atlas: Dict[str, Any]) -> str:
    lines = ["# Handoffs", ""]
    handoffs = [item for item in atlas.get("recent_activity", []) if item.get("event_type") == "handoff"]
    if handoffs:
        lines.extend(
            f"- {item.get('task_id', '')} :: {item.get('summary', '')} :: {', '.join(item.get('handoff_refs', [])) or 'no next action'}"
            for item in handoffs[:25]
        )
    else:
        lines.append("- none")
    return "\n".join(lines)


def _render_changed_surfaces_markdown(atlas: Dict[str, Any]) -> str:
    changes = atlas.get("git_changes", {})
    summary = changes.get("summary", {})
    lines = [
        "# Changed Surfaces",
        "",
        f"- risk_level: `{summary.get('risk_level', 'none')}`",
        f"- changed_files: {summary.get('changed_files', 0)}",
        f"- changed_symbols: {summary.get('changed_count', 0)}",
        f"- affected_processes: {summary.get('affected_count', 0)}",
        "",
        "## Changed Symbols",
        "",
    ]
    symbols = changes.get("changed_symbols", [])
    if symbols:
        lines.extend(
            f"- {item.get('name', '')} :: {item.get('filePath', '')} :: {item.get('change_type', '') or 'touched'}"
            for item in symbols[:25]
        )
    else:
        lines.append("- no gitnexus change report provided")
    lines.extend(["", "## Affected Processes", ""])
    processes = changes.get("affected_processes", [])
    if processes:
        lines.extend(
            f"- {item.get('name', '')} :: "
            + ", ".join(
                f"{step.get('symbol', '')}@{step.get('step', '')}"
                for step in list(item.get("changed_steps", []) or [])[:5]
            )
            for item in processes[:12]
        )
    else:
        lines.append("- none")
    return "\n".join(lines)


def _render_releases_markdown(atlas: Dict[str, Any]) -> str:
    lines = ["# Releases", ""]
    releases = [item for item in atlas.get("recent_activity", []) if item.get("event_type") == "deployed"]
    if releases:
        lines.extend(
            f"- {item.get('metadata', {}).get('release_id', '') or item.get('summary', '')} :: "
            f"{item.get('metadata', {}).get('post_deploy_smoke_path', '') or ', '.join(item.get('verification', [])) or 'no evidence'}"
            for item in releases[:25]
        )
    else:
        lines.append("- none")
    return "\n".join(lines)
