from __future__ import annotations

from conversation_os.workspace_client import WorkspaceClient
from conversation_os.workspace_coordination import create_workspace_task, record_workspace_test_run
from conversation_os.workspace_service import serve_workspace_service
from conversation_os.workspace_store import SQLiteWorkspaceStore


def test_workspace_progress_derives_state_and_next_action_from_evidence(tmp_path) -> None:
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(store.manifest_path("inner-world"), {"workspace_id": "inner-world", "objectives": ["Make progress trustworthy."]})
    create_workspace_task(
        tmp_path, "inner-world", task_id="PROG-001", agent_id="codex", surface="codex", session_id="s-1",
        title="Derive progress", reasoning="Progress must come from evidence.", acceptance_criteria=["Packet has a next action."], store=store,
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        client = WorkspaceClient(f"http://127.0.0.1:{server.server_address[1]}/api")
        initial = client.progress("inner-world", task_id="PROG-001")
        assert initial["state"] == "ready_to_start"
        assert "Begin an agent run" in initial["recommended_next_action"]

        run = client.begin_run(
            "inner-world", task_id="PROG-001", agent_id="codex", device_id="test", surface="codex",
            session_id="s-1", intent="Work the task.",
        )
        assert client.progress("inner-world", task_id="PROG-001")["state"] == "active"
        client.update_task(
            "inner-world", task_id="PROG-001", agent_id="codex", surface="codex", session_id="s-1",
            reasoning="Implementation is complete; verification remains.", status="in-progress",
        )
        client.end_run("inner-world", run_id=run["run_id"], agent_id="codex", status="released", reason="Ready for verification.")
        assert client.progress("inner-world", task_id="PROG-001")["state"] == "awaiting_verification"

        record_workspace_test_run(
            tmp_path, "inner-world", task_id="PROG-001", agent_id="codex", surface="codex", session_id="s-1",
            test_name="progress", result="passing", evidence_ref="pytest", store=store,
        )
        progress = client.progress("inner-world", task_id="PROG-001")
        assert progress["state"] == "ready_for_completion"
        packet = client.context("inner-world", task_id="PROG-001")
        assert packet["focus"]["progress"]["state"] == "ready_for_completion"
        assert packet["focus"]["recommended_next_action"] == progress["recommended_next_action"]
    finally:
        server.shutdown()
        server.server_close()
