from __future__ import annotations

import pytest

from conversation_os.workspace_client import WorkspaceClient, WorkspaceClientError
from conversation_os.workspace_coordination import create_workspace_task
from conversation_os.workspace_service import serve_workspace_service
from conversation_os.workspace_store import SQLiteWorkspaceStore


def _seed_workspace(root):
    store = SQLiteWorkspaceStore(root, database_path=root / "state" / "workspace.db")
    store.write_json(store.manifest_path("inner-world"), {"workspace_id": "inner-world", "objectives": ["Keep work explainable."]})
    create_workspace_task(
        root, "inner-world", task_id="RUN-001", agent_id="codex", surface="codex", session_id="session-1",
        title="Explain work", reasoning="Reasoning records need a task.", acceptance_criteria=["Records are visible."], store=store,
    )
    return store


def test_reasoning_records_are_bounded_provenanced_and_visible_in_context(tmp_path) -> None:
    store = _seed_workspace(tmp_path)
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        client = WorkspaceClient(f"http://127.0.0.1:{server.server_address[1]}/api")
        record = client.record_reasoning(
            "inner-world",
            task_id="RUN-001",
            agent_id="codex",
            surface="codex",
            session_id="session-1",
            kind="decision",
            summary="Keep agent runs separate from task status.",
            rationale="A work attempt may end without completing its task.",
            source_refs=["docs/plans/2026-07-11-reliable-cross-agent-holodeck-work-system-design.md"],
            confidence=0.9,
            _idempotency_key="reasoning-1",
        )
        assert client.record_reasoning(
            "inner-world",
            task_id="RUN-001",
            agent_id="codex",
            surface="codex",
            session_id="session-1",
            kind="decision",
            summary="Keep agent runs separate from task status.",
            rationale="A work attempt may end without completing its task.",
            source_refs=["docs/plans/2026-07-11-reliable-cross-agent-holodeck-work-system-design.md"],
            confidence=0.9,
            _idempotency_key="reasoning-1",
        )["reasoning_id"] == record["reasoning_id"]
        # Repeating the exact request does not append a second reasoning record.
        context = client.context("inner-world", task_id="RUN-001")
        assert context["orientation"]["reasoning"][0]["summary"] == record["summary"]
        assert record["source_refs"][0] in context["provenance"]["source_refs"]

        with pytest.raises(WorkspaceClientError, match="Unsupported reasoning kind"):
            client.record_reasoning(
                "inner-world",
                task_id="RUN-001",
                agent_id="codex",
                surface="codex",
                session_id="session-1",
                kind="raw_chain_of_thought",
                summary="This must not be stored.",
                rationale="Only compact work-relevant records are supported.",
            )
    finally:
        server.shutdown()
        server.server_close()
