from __future__ import annotations

import json
from pathlib import Path

from conversation_os.storage import append_jsonl, ensure_dir
from conversation_os.workspace_atlas import materialize_workspace_atlas
from conversation_os.workspace_coordination import (
    record_workspace_decision,
    record_workspace_test_run,
)


def _write_workspace_manifest(root: Path, workspace_id: str, payload: dict) -> None:
    workspace_dir = root / "memory" / "workspaces" / workspace_id
    ensure_dir(workspace_dir)
    (workspace_dir / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")


def _append_work_item(root: Path, workspace_id: str, *, work_item_id: str, title: str, status: str) -> None:
    append_jsonl(
        root / "memory" / "workspaces" / workspace_id / "work_item_events.jsonl",
        {
            "event_id": f"work-item-event-{work_item_id}",
            "workspace_id": workspace_id,
            "work_item_id": work_item_id,
            "operation": "create",
            "timestamp": "2026-06-30T12:00:00+00:00",
            "actor": "agent",
            "payload": {
                "title": title,
                "kind": "task",
                "status": status,
                "priority": "medium",
                "owner": "",
                "parent_id": "",
                "depends_on": [],
                "linked_artifacts": [],
                "linked_tests": [],
                "guard_status": "not_required",
                "guard_request": "",
                "guard_purpose": "",
                "guard_paths": [],
                "acceptance_criteria": ["ship"],
                "constraints": [],
            },
            "source_refs": [],
        },
    )


def test_materialize_workspace_atlas_writes_context_and_workboard_projections(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "label": "SOL Frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
            "workboard_ref": "docs/workboards/sol-frontend/README.md",
        },
    )
    _append_work_item(tmp_path, "sol-frontend", work_item_id="MTC-001", title="Capture shell", status="ready")
    record_workspace_decision(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        summary="Keep shell language stable.",
        reasoning="Preserves continuity.",
    )
    record_workspace_test_run(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        test_name="mobile-smoke",
        result="passing",
        evidence_ref="artifacts/mobile-smoke.txt",
    )

    atlas = materialize_workspace_atlas(tmp_path, "sol-frontend")

    assert atlas["workspace"]["workspace_id"] == "sol-frontend"
    assert (tmp_path / "context" / "workspaces" / "sol-frontend" / "atlas.md").exists()
    assert (tmp_path / "docs" / "workboards" / "sol-frontend" / "AGENT_STATE.md").exists()
    assert (tmp_path / "docs" / "workboards" / "sol-frontend" / "TASKS.generated.md").exists()
    assert (tmp_path / "docs" / "workboards" / "sol-frontend" / "DECISIONS.generated.md").exists()
    assert "MTC-001" in (tmp_path / "docs" / "workboards" / "sol-frontend" / "TASKS.generated.md").read_text(
        encoding="utf-8"
    )


def test_workspace_mutations_auto_refresh_atlas_files(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "label": "SOL Frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
            "workboard_ref": "docs/workboards/sol-frontend/README.md",
        },
    )
    _append_work_item(tmp_path, "sol-frontend", work_item_id="MTC-001", title="Capture shell", status="ready")

    record_workspace_decision(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        summary="Keep shell language stable.",
        reasoning="Preserves continuity.",
    )

    decisions_projection = tmp_path / "docs" / "workboards" / "sol-frontend" / "DECISIONS.generated.md"
    assert decisions_projection.exists()
    assert "Keep shell language stable." in decisions_projection.read_text(encoding="utf-8")


def test_materialize_workspace_atlas_includes_gitnexus_change_report(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "label": "SOL Frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
            "workboard_ref": "docs/workboards/sol-frontend/README.md",
        },
    )
    _append_work_item(tmp_path, "sol-frontend", work_item_id="MTC-001", title="Capture shell", status="ready")

    atlas = materialize_workspace_atlas(
        tmp_path,
        "sol-frontend",
        git_change_report={
            "summary": {
                "changed_count": 3,
                "affected_count": 2,
                "changed_files": 2,
                "risk_level": "medium",
            },
            "changed_symbols": [
                {
                    "name": "AppShell",
                    "filePath": "product/thought_capture_pwa/src/app-shell.tsx",
                    "change_type": "modified",
                }
            ],
            "affected_processes": [
                {
                    "name": "Render capture shell",
                    "changed_steps": [{"symbol": "AppShell", "step": 1}],
                }
            ],
        },
    )

    changed = tmp_path / "docs" / "workboards" / "sol-frontend" / "CHANGED_SURFACES.md"
    assert atlas["git_changes"]["summary"]["risk_level"] == "medium"
    assert changed.exists()
    content = changed.read_text(encoding="utf-8")
    assert "AppShell" in content
    assert "Render capture shell" in content


def test_materialize_workspace_atlas_includes_release_projection(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "label": "SOL Frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
            "workboard_ref": "docs/workboards/sol-frontend/README.md",
        },
    )
    _append_work_item(tmp_path, "sol-frontend", work_item_id="MTC-001", title="Capture shell", status="done")
    append_jsonl(
        tmp_path / "memory" / "workspaces" / "sol-frontend" / "activity_events.jsonl",
        {
            "event_id": "evt-release",
            "schema_version": "1.0",
            "created_at": "2026-06-30T12:30:00+00:00",
            "workspace_id": "sol-frontend",
            "task_id": "",
            "actor": {"agent_id": "system", "surface": "deploy", "session_id": "release"},
            "event_type": "deployed",
            "summary": "Deployed release inner-world-test",
            "reasoning": "",
            "files_touched": [],
            "commands_run": [],
            "verification": ["product/inner_world_v1/releases/inner-world-test/post_deploy_smoke.json"],
            "blockers": [],
            "decision_refs": [],
            "handoff_refs": [],
            "metadata": {
                "release_id": "inner-world-test",
                "post_deploy_smoke_path": "product/inner_world_v1/releases/inner-world-test/post_deploy_smoke.json",
            },
        },
    )

    materialize_workspace_atlas(tmp_path, "sol-frontend")

    releases = tmp_path / "docs" / "workboards" / "sol-frontend" / "RELEASES.generated.md"
    assert releases.exists()
    content = releases.read_text(encoding="utf-8")
    assert "inner-world-test" in content
    assert "post_deploy_smoke.json" in content
