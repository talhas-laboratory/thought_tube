from __future__ import annotations

from pathlib import Path

from conversation_os.workspace_client import WorkspaceClient
from conversation_os.workspace_coordination import create_workspace_task, list_workspace_claims
from conversation_os.workspace_runs import begin_workspace_run, list_workspace_runs, recover_stale_workspace_runs
from conversation_os.workspace_service import serve_workspace_service
from conversation_os.workspace_store import SQLiteWorkspaceStore


def _seed_workspace(root: Path) -> SQLiteWorkspaceStore:
    store = SQLiteWorkspaceStore(root, database_path=root / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {"workspace_id": "inner-world", "artifact_roots": ["src/"], "objectives": ["Coordinate durable work."]},
    )
    create_workspace_task(
        root,
        "inner-world",
        task_id="RUN-001",
        agent_id="codex",
        surface="codex",
        session_id="session-1",
        title="Track active work",
        reasoning="A task needs a durable active agent record.",
        acceptance_criteria=["Run state is visible."],
        store=store,
    )
    return store


def test_workspace_run_lifecycle_is_visible_in_service_and_context_packet(tmp_path: Path) -> None:
    store = _seed_workspace(tmp_path)
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        client = WorkspaceClient(f"http://127.0.0.1:{server.server_address[1]}/api")
        run = client.begin_run(
            "inner-world",
            task_id="RUN-001",
            agent_id="codex",
            device_id="test-mac",
            surface="codex",
            session_id="session-1",
            intent="Implement durable run tracking.",
            source_revision="abc123",
            heartbeat_ttl_seconds=300,
            claimed_paths=["src/workspace_runs.py"],
            _idempotency_key="run-begin-1",
        )
        assert run["status"] == "active"
        assert len(run["claim_ids"]) == 1
        assert list_workspace_claims(tmp_path, "inner-world", store=store)[0]["run_id"] == run["run_id"]
        assert client.begin_run(
            "inner-world",
            task_id="RUN-001",
            agent_id="codex",
            device_id="test-mac",
            surface="codex",
            session_id="session-1",
            intent="Implement durable run tracking.",
            source_revision="abc123",
            heartbeat_ttl_seconds=300,
            claimed_paths=["src/workspace_runs.py"],
            _idempotency_key="run-begin-1",
        ) == run
        assert client.runs("inner-world", task_id="RUN-001")["runs"][0]["run_id"] == run["run_id"]
        assert client.runs("inner-world", task_id="RUN-001")["runs"][0]["claimed_paths"] == ["src/workspace_runs.py"]
        packet = client.context("inner-world", task_id="RUN-001", agent_id="telegram:42")
        assert packet["orientation"]["active_runs"][0]["actor"]["device_id"] == "test-mac"

        heartbeat = client.heartbeat_run(
            "inner-world", run_id=run["run_id"], agent_id="codex", _idempotency_key="run-heartbeat-1"
        )
        assert heartbeat["status"] == "active"
        assert list_workspace_claims(tmp_path, "inner-world", store=store)[0]["run_id"] == run["run_id"]
        ended = client.end_run(
            "inner-world",
            run_id=run["run_id"],
            agent_id="codex",
            status="handed_off",
            reason="Another agent will continue from the context packet.",
            _idempotency_key="run-end-1",
        )
        assert ended["status"] == "handed_off"
        assert ended["released_claim_ids"] == run["claim_ids"]
        assert list_workspace_claims(tmp_path, "inner-world", store=store) == []
        assert client.context("inner-world", task_id="RUN-001")["orientation"]["active_runs"] == []
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_run_becomes_stale_after_its_heartbeat_lease(tmp_path: Path) -> None:
    store = _seed_workspace(tmp_path)
    run = begin_workspace_run(
        tmp_path,
        "inner-world",
        task_id="RUN-001",
        agent_id="codex",
        device_id="test-mac",
        surface="codex",
        session_id="session-1",
        intent="Test stale detection.",
        heartbeat_ttl_seconds=60,
        store=store,
    )
    store.append_jsonl(
        store.manifest_path("inner-world").parent / "agent_runs.jsonl",
        {**run, "last_heartbeat_at": "2020-01-01T00:00:00+00:00"},
    )

    stale = list_workspace_runs(tmp_path, "inner-world", store=store)[0]
    assert stale["status"] == "stale"
    assert list_workspace_runs(tmp_path, "inner-world", active_only=True, store=store) == []
    recovered = recover_stale_workspace_runs(tmp_path, "inner-world", store=store)
    assert recovered[0]["recovered_from_stale"] is True
    assert list_workspace_claims(tmp_path, "inner-world", store=store) == []
