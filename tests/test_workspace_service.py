from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from conversation_os.workspace_service import serve_workspace_service
from conversation_os.workspace_store import SQLiteWorkspaceStore


def _request_json(url: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=body, method=method)
    request.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.getcode(), json.loads(response.read().decode("utf-8"))


def _git(root: Path, *args: str) -> str:
    import subprocess

    result = subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def test_workspace_service_serves_prepare_and_claim_flow(tmp_path: Path) -> None:
    root = tmp_path
    store = SQLiteWorkspaceStore(root, database_path=root / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("sol-frontend"),
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    store.append_jsonl(
        store.work_item_events_path("sol-frontend"),
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

    server = serve_workspace_service(root=root, host="127.0.0.1", port=0, store=store)
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}/api/workspaces/sol-frontend"

        code, payload = _request_json(f"{base_url}/prepare?task_id=MTC-001&agent_id=codex&surface=codex&session_id=s-1")
        assert code == 200
        assert payload["task"]["task_id"] == "MTC-001"

        code, payload = _request_json(
            f"{base_url}/claim",
            method="POST",
            payload={
                "task_id": "MTC-001",
                "agent_id": "codex",
                "surface": "codex",
                "session_id": "s-1",
                "intent": "Harden the shell",
                "claimed_paths": ["product/thought_capture_pwa/"],
            },
        )
        assert code == 200
        assert payload["status"] == "active"

        code, payload = _request_json(f"{base_url}/gate")
        assert code == 200
        assert payload["status"] == "blocked"
        assert "active_claims" in payload["reasons"]
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_service_rejects_invalid_claim_request(tmp_path: Path) -> None:
    root = tmp_path
    store = SQLiteWorkspaceStore(root, database_path=root / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("sol-frontend"),
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    server = serve_workspace_service(root=root, host="127.0.0.1", port=0, store=store)
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}/api/workspaces/sol-frontend"
        request = urllib.request.Request(
            f"{base_url}/claim",
            data=json.dumps(
                {
                    "task_id": "MTC-001",
                    "agent_id": "codex",
                    "surface": "codex",
                    "session_id": "s-1",
                    "intent": "Reach outside scope",
                    "claimed_paths": ["src/"],
                }
            ).encode("utf-8"),
            method="POST",
        )
        request.add_header("Content-Type", "application/json")

        try:
            urllib.request.urlopen(request, timeout=5)
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            payload = json.loads(exc.read().decode("utf-8"))
            assert payload["error"] == "Claimed path outside workspace artifact roots: src/"
        else:
            raise AssertionError("expected HTTP 400")
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_service_exposes_agent_context_packet(tmp_path: Path) -> None:
    root = tmp_path
    store = SQLiteWorkspaceStore(root, database_path=root / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {
            "workspace_id": "inner-world",
            "purpose": "Give agents shared orientation.",
            "artifact_roots": ["src/"],
            "objectives": ["Assemble context."],
        },
    )
    server = serve_workspace_service(root=root, host="127.0.0.1", port=0, store=store)
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}/api/workspaces/inner-world"
        code, payload = _request_json(
            f"{base_url}/context?task_id=CTX-002&agent_id=openclaw&surface=telegram&session_id=t-1"
        )
        assert code == 200
        assert payload["workspace"]["purpose"] == "Give agents shared orientation."
        assert payload["agent"]["agent_id"] == "openclaw"
        assert payload["agent"]["surface"] == "telegram"
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_service_refreshes_repository_revision_before_context(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "agent@example.test")
    _git(tmp_path, "config", "user.name", "Agent")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "tracked.py").write_text("value = 1\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    store = SQLiteWorkspaceStore(root=tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {"workspace_id": "inner-world", "artifact_roots": ["src/"]},
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}/api/workspaces/inner-world"
        code, payload = _request_json(f"{base_url}/context")
        assert code == 200
        assert payload["repository"]["source_revision"] == _git(tmp_path, "rev-parse", "HEAD")
        assert payload["repository"]["freshness_status"] == "observed"
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_service_uses_published_revision_for_rsync_projection(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("INNER_SPACE_REPOSITORY_SOURCE_REVISION", "published-commit-1")
    store = SQLiteWorkspaceStore(root=tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {"workspace_id": "inner-world", "artifact_roots": ["src/"]},
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}/api/workspaces/inner-world"
        code, payload = _request_json(f"{base_url}/context")
        assert code == 200
        assert payload["repository"]["source_revision"] == "published-commit-1"
        assert payload["repository"]["freshness_status"] == "observed"
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_service_returns_structured_completion_gate_failure(tmp_path: Path) -> None:
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {"workspace_id": "inner-world", "artifact_roots": ["src/"]},
    )
    store.append_jsonl(
        store.work_item_events_path("inner-world"),
        {
            "event_id": "create-1",
            "workspace_id": "inner-world",
            "work_item_id": "CTX-004",
            "operation": "create",
            "timestamp": "2026-06-30T10:00:00+00:00",
            "actor": "codex",
            "payload": {"title": "Completion", "status": "in-progress"},
            "source_refs": [],
        },
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}/api/workspaces/inner-world"
        request = urllib.request.Request(
            f"{base_url}/complete",
            data=json.dumps(
                {
                    "task_id": "CTX-004",
                    "agent_id": "codex",
                    "surface": "codex",
                    "session_id": "s-1",
                    "summary": "",
                    "reasoning": "",
                    "files_touched": [],
                    "commands_run": [],
                    "residual_risks": [],
                }
            ).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=5)
        assert error.value.code == 400
        payload = json.loads(error.value.read().decode("utf-8"))
        assert payload["error"] == "completion_gate_failed"
        assert payload["missing"] == [
            "summary",
            "reasoning",
            "files_touched",
            "commands_run",
            "residual_risks",
            "passing_verification",
        ]
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_service_exposes_health_readiness_and_restart_continuity(tmp_path: Path) -> None:
    database_path = tmp_path / "state" / "workspace.db"
    store = SQLiteWorkspaceStore(tmp_path, database_path=database_path)
    store.write_json(
        store.manifest_path("inner-world"),
        {"workspace_id": "inner-world", "purpose": "Persist across restart.", "artifact_roots": ["src/"]},
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        assert _request_json(f"{base}/health") == (200, {"status": "ok"})
        ready_code, ready = _request_json(f"{base}/ready")
        assert ready_code == 200
        assert ready["status"] == "ready"
        before = _request_json(f"{base}/api/workspaces/inner-world/context")[1]
    finally:
        server.shutdown()
        server.server_close()

    restarted_store = SQLiteWorkspaceStore(tmp_path, database_path=database_path)
    restarted = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=restarted_store)
    try:
        after = _request_json(
            f"http://127.0.0.1:{restarted.server_address[1]}/api/workspaces/inner-world/context"
        )[1]
    finally:
        restarted.shutdown()
        restarted.server_close()

    before.pop("assembled_at")
    after.pop("assembled_at")
    assert before == after
