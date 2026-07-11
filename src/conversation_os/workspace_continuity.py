from __future__ import annotations

"""Read-only, git-trackable continuity projections of canonical workspace state."""

from pathlib import Path
from typing import Any

from .storage import utc_now
from .workspace_catalog import workspace_catalog
from .workspace_context_packet import assemble_workspace_context_packet
from .workspace_store import FileWorkspaceStore, WorkspaceStore


MODULE_ID = "kernel.workspace.workspace_continuity"
CONTRACT_VERSION = "1.0"
PUBLIC_API = ("MODULE_ID", "CONTRACT_VERSION", "assemble_workspace_continuity_export", "render_workspace_continuity_markdown")
__all__ = list(PUBLIC_API)


def assemble_workspace_continuity_export(
    root: Path, workspace_id: str, *, task_id: str = "", store: WorkspaceStore | None = None
) -> dict[str, Any]:
    packet = assemble_workspace_context_packet(root, workspace_id, task_id=task_id, store=store)
    catalog = workspace_catalog(store or FileWorkspaceStore(root))
    revision = next((str(row.get("revision", "") or "") for row in catalog["workspaces"] if row.get("workspace_id") == workspace_id), "")
    orientation = dict(packet.get("orientation", {}) or {})
    focus = dict(packet.get("focus", {}) or {})
    return {
        "schema_version": CONTRACT_VERSION,
        "workspace_id": workspace_id,
        "canonical_revision": revision,
        "repository_source_revision": str(packet.get("repository", {}).get("source_revision", "") or ""),
        "generated_at": utc_now(),
        "focus": focus,
        "runs": {"active": list(orientation.get("active_runs", []) or [])[:12], "recent": list(orientation.get("recent_runs", []) or [])[:12]},
        "reasoning": list(orientation.get("reasoning", []) or [])[:12],
        "tests": list(orientation.get("tests", []) or [])[:12],
        "resume_instructions": str(focus.get("recommended_next_action", "") or "Select a focused task from canonical workspace state."),
    }


def render_workspace_continuity_markdown(export: dict[str, Any]) -> str:
    focus = dict(export.get("focus", {}) or {})
    task = dict(focus.get("task", {}) or {})
    lines = [
        "<!-- generated: workspace continuity export; canonical store remains authoritative -->",
        f"<!-- workspace_id: {export.get('workspace_id', '')} -->",
        f"<!-- canonical_revision: {export.get('canonical_revision', '')} -->",
        f"<!-- repository_source_revision: {export.get('repository_source_revision', '')} -->",
        f"<!-- generated_at: {export.get('generated_at', '')} -->",
        "",
        f"# Workspace continuity: {export.get('workspace_id', '')}",
        "",
        "## Resume",
        "",
        str(export.get("resume_instructions", "") or "Select a focused task from canonical workspace state."),
        "",
        "## Focus task",
        "",
        f"- id: `{task.get('task_id', '')}`",
        f"- status: `{task.get('status', '')}`",
        f"- title: {task.get('title', '')}",
    ]
    for heading, rows in (("Recent runs", export.get("runs", {}).get("recent", [])), ("Reasoning", export.get("reasoning", [])), ("Verification", export.get("tests", []))):
        lines.extend(["", f"## {heading}", ""])
        lines.extend(f"- {row.get('summary') or row.get('end_reason') or row.get('intent') or row.get('latest_evidence_ref') or row.get('test_id') or 'recorded'}" for row in rows)
        if not rows:
            lines.append("- none")
    return "\n".join(lines).rstrip() + "\n"
