from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.workspace_dashboard import build_workspace_dashboard_snapshot, parse_tasks_markdown


SAMPLE_TASKS = """# Tasks

| id | status | owner | title | gate |
|---|---|---|---|---|
| `KERNEL-001-atomic` | done | agent | Lock contracts | not_required |
| `KERNEL-002-fixtures` | backlog | unassigned | Build fixtures | not_required |
"""


def test_parse_tasks_markdown_extracts_rows() -> None:
    rows = parse_tasks_markdown(SAMPLE_TASKS)
    assert len(rows) == 2
    assert rows[0]["task_id"] == "KERNEL-001-atomic"
    assert rows[0]["status"] == "done"
    assert rows[1]["status"] == "backlog"


def test_build_workspace_dashboard_snapshot_includes_umf_programs() -> None:
    root = Path(__file__).resolve().parents[1]
    snapshot = build_workspace_dashboard_snapshot(root)
    workspaces = snapshot["workspaces"]
    assert "metaphysical-kernel-ontology" in workspaces
    assert "metaphysical-branch-reasoning" in workspaces
    assert "metaphysical-vocabulary-governance" in workspaces
    kernel = workspaces["metaphysical-kernel-ontology"]
    assert kernel["status_counts"].get("done", 0) >= 5
    assert snapshot["workspace_count"] >= 5
