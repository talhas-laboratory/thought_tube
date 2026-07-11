from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

from conversation_os.workspace_service import serve_workspace_service
from conversation_os.workspace_store import SQLiteWorkspaceStore


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "tools" / "workspace_coordination.py"
sys.path.append(str(SCRIPT_PATH.parent))
SPEC = importlib.util.spec_from_file_location("workspace_coordination_tool", SCRIPT_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _write_workspace_manifest(root: Path, workspace_id: str, payload: dict) -> None:
    workspace_dir = root / "memory" / "workspaces" / workspace_id
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_work_item(root: Path, workspace_id: str, payload: dict) -> None:
    path = root / "memory" / "workspaces" / workspace_id / "work_item_events.jsonl"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def test_workspace_coordination_cli_status_outputs_workspace_snapshot(tmp_path: Path, capsys) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    _write_work_item(
        tmp_path,
        "sol-frontend",
        {
            "event_id": "work-item-event-1",
            "workspace_id": "sol-frontend",
            "work_item_id": "MTC-001",
            "operation": "create",
            "timestamp": "2026-06-30T12:00:00+00:00",
            "actor": "agent",
            "payload": {
                "title": "Capture shell",
                "kind": "task",
                "status": "ready",
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

    code = runner.main(
        [
            "status",
            "--root",
            str(tmp_path),
            "--workspace-id",
            "sol-frontend",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert "Workspace: sol-frontend" in captured.out
    assert "Tasks: 1" in captured.out


def test_workspace_coordination_cli_uses_service_when_configured(tmp_path: Path, capsys) -> None:
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("server-workspace"),
        {
            "workspace_id": "server-workspace",
            "artifact_roots": ["src/"],
            "objectives": ["Use canonical server state."],
        },
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        code = runner.main(
            [
                "status",
                "--root",
                str(tmp_path / "empty-local-root"),
                "--workspace-id",
                "server-workspace",
                "--workspace-api-base",
                f"http://127.0.0.1:{server.server_address[1]}",
            ]
        )
    finally:
        server.shutdown()
        server.server_close()

    captured = capsys.readouterr()
    assert code == 0
    assert "Workspace: server-workspace" in captured.out


def test_workspace_coordination_cli_creates_task_and_reads_context_through_service(tmp_path: Path, capsys) -> None:
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {"workspace_id": "inner-world", "artifact_roots": ["src/"]},
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    api_base = f"http://127.0.0.1:{server.server_address[1]}/api"
    try:
        code = runner.main(
            [
                "create-task",
                "--root",
                str(tmp_path / "empty-local"),
                "--workspace-id",
                "inner-world",
                "--workspace-api-base",
                api_base,
                "--task-id",
                "CTX-CLI",
                "--title",
                "Task through canonical service",
                "--reasoning",
                "Codex must share server state.",
                "--acceptance",
                "context returns this task",
            ]
        )
        assert code == 0
        assert json.loads(capsys.readouterr().out)["task_id"] == "CTX-CLI"

        code = runner.main(
            [
                "context",
                "--root",
                str(tmp_path / "empty-local"),
                "--workspace-id",
                "inner-world",
                "--workspace-api-base",
                api_base,
                "--task-id",
                "CTX-CLI",
            ]
        )
        packet = json.loads(capsys.readouterr().out)
        assert code == 0
        assert packet["focus"]["task"]["title"] == "Task through canonical service"
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_coordination_cli_discovers_local_workspace_service_config(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(store.manifest_path("inner-world"), {"workspace_id": "inner-world", "artifact_roots": ["src/"]})
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        config_dir = tmp_path / "home" / ".config"
        config_dir.mkdir(parents=True)
        (config_dir / "inner-space-workspace.env").write_text(
            f"INNER_WORLD_WORKSPACE_API_BASE=http://127.0.0.1:{server.server_address[1]}/api\n",
            encoding="utf-8",
        )
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        monkeypatch.delenv("INNER_WORLD_WORKSPACE_API_BASE", raising=False)

        code = runner.main(
            [
                "status",
                "--workspace-id",
                "inner-world",
            ]
        )
        assert code == 0
        assert "Workspace: inner-world" in capsys.readouterr().out
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_coordination_cli_claim_outputs_json(tmp_path: Path, capsys) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )

    code = runner.main(
        [
            "claim",
            "--root",
            str(tmp_path),
            "--workspace-id",
            "sol-frontend",
            "--task-id",
            "MTC-001",
            "--agent-id",
            "codex",
            "--surface",
            "codex",
            "--session-id",
            "session-1",
            "--intent",
            "Harden the shell",
            "--claimed-path",
            "product/thought_capture_pwa/",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["task_id"] == "MTC-001"
    assert payload["claimed_paths"] == ["product/thought_capture_pwa/"]


def test_workspace_coordination_cli_complete_records_governed_completion(tmp_path: Path, capsys) -> None:
    _write_workspace_manifest(
        tmp_path,
        "inner-world",
        {"workspace_id": "inner-world", "artifact_roots": ["src/"]},
    )
    _write_work_item(
        tmp_path,
        "inner-world",
        {
            "event_id": "create-ctx-004",
            "workspace_id": "inner-world",
            "work_item_id": "CTX-004",
            "operation": "create",
            "timestamp": "2026-06-30T10:00:00+00:00",
            "actor": "codex",
            "payload": {"title": "Completion", "status": "in-progress"},
            "source_refs": [],
        },
    )
    assert runner.main(
        [
            "verify",
            "--root",
            str(tmp_path),
            "--workspace-id",
            "inner-world",
            "--task-id",
            "CTX-004",
            "--test-name",
            "completion-contract",
            "--result",
            "passing",
            "--evidence-ref",
            "pytest:passing",
        ]
    ) == 0
    capsys.readouterr()

    code = runner.main(
        [
            "complete",
            "--root",
            str(tmp_path),
            "--workspace-id",
            "inner-world",
            "--task-id",
            "CTX-004",
            "--summary",
            "Completion contract implemented.",
            "--reasoning",
            "All mandatory evidence is attached.",
            "--file-touched",
            "src/conversation_os/workspace_coordination.py",
            "--command-run",
            "pytest tests/test_workspace_completion_gates.py -q",
            "--residual-risk",
            "none known",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["status"] == "done"


def test_workspace_coordination_cli_decision_outputs_json(tmp_path: Path, capsys) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )

    code = runner.main(
        [
            "decision",
            "--root",
            str(tmp_path),
            "--workspace-id",
            "sol-frontend",
            "--task-id",
            "MTC-001",
            "--agent-id",
            "codex",
            "--surface",
            "codex",
            "--session-id",
            "session-1",
            "--summary",
            "Keep note/meta toggle in current shell language.",
            "--reasoning",
            "Preserves continuity and avoids extra UI churn.",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["task_id"] == "MTC-001"
    assert payload["status"] == "accepted"


def test_workspace_coordination_cli_verify_outputs_json(tmp_path: Path, capsys) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )

    code = runner.main(
        [
            "verify",
            "--root",
            str(tmp_path),
            "--workspace-id",
            "sol-frontend",
            "--task-id",
            "MTC-001",
            "--agent-id",
            "codex",
            "--surface",
            "codex",
            "--session-id",
            "session-1",
            "--test-name",
            "mobile-smoke",
            "--result",
            "passing",
            "--evidence-ref",
            "artifacts/mobile-smoke.txt",
            "--notes",
            "Shell loads and toggle responds.",
            "--command-or-protocol",
            "pnpm test:e2e mobile-smoke",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["result"] == "passing"
    assert payload["test_name"] == "mobile-smoke"


def test_workspace_coordination_cli_blocker_outputs_json(tmp_path: Path, capsys) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )

    code = runner.main(
        [
            "blocker",
            "--root",
            str(tmp_path),
            "--workspace-id",
            "sol-frontend",
            "--task-id",
            "MTC-001",
            "--agent-id",
            "codex",
            "--surface",
            "codex",
            "--session-id",
            "session-1",
            "--reasoning",
            "Mobile shell collapses on Safari reload.",
            "--next-action",
            "Inspect hydration path.",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["task_id"] == "MTC-001"
    assert payload["status"] == "active"


def test_workspace_coordination_cli_gate_outputs_json(tmp_path: Path, capsys) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    _write_work_item(
        tmp_path,
        "sol-frontend",
        {
            "event_id": "work-item-event-1",
            "workspace_id": "sol-frontend",
            "work_item_id": "MTC-001",
            "operation": "create",
            "timestamp": "2026-06-30T12:00:00+00:00",
            "actor": "agent",
            "payload": {
                "title": "Capture shell",
                "kind": "task",
                "status": "done",
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

    code = runner.main(
        [
            "gate",
            "--root",
            str(tmp_path),
            "--workspace-id",
            "sol-frontend",
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["status"] == "blocked"
    assert "missing_verification" in payload["reasons"]


def test_workspace_coordination_cli_atlas_writes_generated_files(tmp_path: Path, capsys) -> None:
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
    _write_work_item(
        tmp_path,
        "sol-frontend",
        {
            "event_id": "work-item-event-1",
            "workspace_id": "sol-frontend",
            "work_item_id": "MTC-001",
            "operation": "create",
            "timestamp": "2026-06-30T12:00:00+00:00",
            "actor": "agent",
            "payload": {
                "title": "Capture shell",
                "kind": "task",
                "status": "ready",
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
    changes_path = tmp_path / "changes.json"
    changes_path.write_text(
        json.dumps(
            {
                "summary": {"changed_count": 1, "affected_count": 1, "changed_files": 1, "risk_level": "low"},
                "changed_symbols": [{"name": "AppShell", "filePath": "product/thought_capture_pwa/src/app-shell.tsx"}],
                "affected_processes": [{"name": "Render capture shell", "changed_steps": [{"symbol": "AppShell", "step": 1}]}],
            }
        ),
        encoding="utf-8",
    )

    code = runner.main(
        [
            "atlas",
            "--root",
            str(tmp_path),
            "--workspace-id",
            "sol-frontend",
            "--git-changes-path",
            str(changes_path),
        ]
    )

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["workspace"]["workspace_id"] == "sol-frontend"
    assert (tmp_path / "docs" / "workboards" / "sol-frontend" / "CHANGED_SURFACES.md").exists()
