from __future__ import annotations

import json
from pathlib import Path

from conversation_os.storage import append_jsonl, ensure_dir
from conversation_os.workspace_coordination import record_workspace_test_run, update_workspace_task
from conversation_os.workspace_projection_sync import (
    check_workspace_projections,
    load_repo_workspace_manifest,
    resolve_projection_paths,
    sync_workspace_projections,
)
from conversation_os.workspace_continuity import render_workspace_continuity_markdown


def _write_workspace_manifest(root: Path, workspace_id: str, payload: dict) -> None:
    workspace_dir = root / "docs" / "workspaces" / workspace_id
    ensure_dir(workspace_dir)
    (workspace_dir / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_workboard(root: Path) -> None:
    board_dir = root / "docs" / "workboards" / "unified-metaphysical-foundation"
    ensure_dir(board_dir / "tasks")
    ensure_dir(board_dir / "lanes" / "blocked")
    ensure_dir(board_dir / "lanes" / "review")
    (board_dir / "TASKS.md").write_text(
        "\n".join(
            [
                "# Tasks",
                "",
                "| id | status | owner | title | gate |",
                "|---|---|---|---|---|",
                "| `TASK-001-lock-kernel-contracts-and-lifecycles` | blocked | cursor-cloud-agent | Lock kernel contracts and lifecycles | verification |",
                "",
                "Stale summary.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (board_dir / "tasks" / "TASK-001-lock-kernel-contracts-and-lifecycles.md").write_text(
        "\n".join(
            [
                "# TASK-001-lock-kernel-contracts-and-lifecycles: Lock kernel contracts and lifecycles",
                "",
                "Status: blocked",
                "Owner: cursor-cloud-agent",
                "Current gate: implementation",
                "",
                "## Problem",
                "",
                "Example task packet.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (board_dir / "lanes" / "blocked" / "TASK-001-lock-kernel-contracts-and-lifecycles.md").write_text(
        (board_dir / "tasks" / "TASK-001-lock-kernel-contracts-and-lifecycles.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    append_jsonl(
        board_dir / "UPDATES.jsonl",
        {
            "timestamp": "2026-07-12T14:18:38+00:00",
            "actor": "board-bootstrap",
            "event": "board_created",
            "board_id": "unified-metaphysical-foundation",
        },
    )


def _seed_workspace(root: Path) -> None:
    workspace_id = "unified-framework-synthesis"
    _write_workspace_manifest(
        root,
        workspace_id,
        {
            "workspace_id": workspace_id,
            "label": "Unified Metaphysical Framework Foundation",
            "workboard": "docs/workboards/unified-metaphysical-foundation/README.md",
            "continuity_projection": "docs/workspaces/unified-framework-synthesis/CONTINUITY.md",
        },
    )
    _write_workboard(root)
    memory_dir = root / "memory" / "workspaces" / workspace_id
    ensure_dir(memory_dir)
    (memory_dir / "manifest.json").write_text(
        json.dumps(
            {
                "workspace_id": workspace_id,
                "label": "Unified Metaphysical Framework Foundation",
                "workboard_ref": "docs/workboards/unified-metaphysical-foundation/README.md",
            }
        ),
        encoding="utf-8",
    )
    append_jsonl(
        memory_dir / "work_item_events.jsonl",
        {
            "event_id": "work-item-event-task-001",
            "workspace_id": workspace_id,
            "work_item_id": "TASK-001-lock-kernel-contracts-and-lifecycles",
            "operation": "create",
            "timestamp": "2026-07-12T14:44:37+00:00",
            "actor": "agent",
            "payload": {
                "title": "Lock kernel contracts and lifecycles",
                "kind": "task",
                "status": "review",
                "priority": "high",
                "owner": "cursor-cloud-agent",
                "parent_id": "",
                "depends_on": [],
                "linked_artifacts": [],
                "linked_tests": [],
                "guard_status": "verification",
                "guard_request": "",
                "guard_purpose": "",
                "guard_paths": [],
                "acceptance_criteria": ["Valid fixtures pass."],
                "constraints": [],
            },
            "source_refs": [],
        },
    )
    update_workspace_task(
        root,
        workspace_id,
        task_id="TASK-001-lock-kernel-contracts-and-lifecycles",
        agent_id="cursor-cloud-agent",
        surface="cursor",
        session_id="sync-test",
        status="review",
        reasoning="Ready for review.",
    )
    record_workspace_test_run(
        root,
        workspace_id,
        task_id="TASK-001-lock-kernel-contracts-and-lifecycles",
        agent_id="cursor-cloud-agent",
        surface="cursor",
        session_id="sync-test",
        test_name="foundation_phase1_review",
        result="pass",
        evidence_ref="abc123",
        command_or_protocol="python3 tools/conversation_os.py foundation review",
    )


def test_sync_workspace_projections_updates_task_files_and_index(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    manifest = load_repo_workspace_manifest(tmp_path, "unified-framework-synthesis")
    paths = resolve_projection_paths(tmp_path, manifest)

    result = sync_workspace_projections(tmp_path, "unified-framework-synthesis", api_base="")

    task_text = paths["tasks_dir"].joinpath("TASK-001-lock-kernel-contracts-and-lifecycles.md").read_text(encoding="utf-8")
    tasks_index = paths["tasks_index"].read_text(encoding="utf-8")
    continuity = paths["continuity_path"].read_text(encoding="utf-8")

    assert result["mode"] == "offline"
    assert "Status: review" in task_text
    assert "TASK-001-lock-kernel-contracts-and-lifecycles` | review |" in tasks_index
    assert "No open blockers" in tasks_index
    assert "canonical_revision:" in continuity
    assert paths["lanes_dir"].joinpath("review", "TASK-001-lock-kernel-contracts-and-lifecycles.md").is_file()
    assert not paths["lanes_dir"].joinpath("blocked", "TASK-001-lock-kernel-contracts-and-lifecycles.md").exists()
    assert "projections_synced" in paths["updates_log"].read_text(encoding="utf-8")
    assert result["changed"]


def test_check_workspace_projections_reports_fresh_after_publish(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    sync_workspace_projections(tmp_path, "unified-framework-synthesis", api_base="")
    result = check_workspace_projections(tmp_path, "unified-framework-synthesis", api_base="")
    assert result["fresh"] is True
    assert result["changed"] == []


def test_sync_workspace_projections_materializes_missing_task_packet(tmp_path: Path) -> None:
    _seed_workspace(tmp_path)
    manifest = load_repo_workspace_manifest(tmp_path, "unified-framework-synthesis")
    paths = resolve_projection_paths(tmp_path, manifest)
    task_path = paths["tasks_dir"] / "TASK-001-lock-kernel-contracts-and-lifecycles.md"
    task_path.unlink()

    sync_workspace_projections(tmp_path, "unified-framework-synthesis", api_base="")

    task_text = task_path.read_text(encoding="utf-8")
    assert "Status: review" in task_text
    assert "Live task created before its Git task packet was materialized." in task_text
    assert paths["lanes_dir"].joinpath("review", task_path.name).is_file()


def test_workspace_continuity_uses_placeholder_for_empty_focus_title() -> None:
    rendered = render_workspace_continuity_markdown({"workspace_id": "example", "focus": {"task": {}}})
    assert "- title: _none_" in rendered
    assert "- title: \n" not in rendered
