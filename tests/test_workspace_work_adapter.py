from __future__ import annotations

from conversation_os.workspace_client import WorkspaceClient
from conversation_os.workspace_coordination import create_workspace_task, list_workspace_activity_events, list_workspace_claims
from conversation_os.workspace_service import serve_workspace_service
from conversation_os.workspace_store import SQLiteWorkspaceStore
from conversation_os.workspace_work_adapter import WorkspaceWorkAdapter


def test_workspace_work_adapter_runs_the_connected_lifecycle(tmp_path) -> None:
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(store.manifest_path("inner-world"), {"workspace_id": "inner-world", "artifact_roots": ["src/"]})
    create_workspace_task(tmp_path, "inner-world", task_id="ADAPT-001", agent_id="codex", surface="codex", session_id="s-1", title="Use adapter", reasoning="Surface integration needs one contract.", acceptance_criteria=["Lifecycle is coherent."], store=store)
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        adapter = WorkspaceWorkAdapter(WorkspaceClient(f"http://127.0.0.1:{server.server_address[1]}/api"), "inner-world", "codex", "test-device", "codex", "s-1")
        run = adapter.begin(task_id="ADAPT-001", intent="Implement adapter integration.", claimed_paths=["src/adapter.py"], next_action="Add adapter test.", idempotency_key="adapter-begin")
        adapter.heartbeat(run_id=run["run_id"], update="Adapter test is running.", idempotency_key="adapter-heartbeat")
        ended = adapter.handoff(run_id=run["run_id"], next_action="Review the adapter contract.", rationale="Implementation and evidence are ready for review.", idempotency_key="adapter-handoff")
        assert ended["status"] == "handed_off"
        assert list_workspace_claims(tmp_path, "inner-world", store=store) == []
        handoff = next(row for row in list_workspace_activity_events(tmp_path, "inner-world", task_id="ADAPT-001", limit=20, store=store) if row["event_type"] == "handoff")
        assert handoff["metadata"]["run_id"] == run["run_id"]
        packet = adapter.client.context("inner-world", task_id="ADAPT-001")
        assert any(row["summary"] == "Review the adapter contract." for row in packet["orientation"]["reasoning"])
    finally:
        server.shutdown()
        server.server_close()
