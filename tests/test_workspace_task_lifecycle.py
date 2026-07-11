from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.workspace_context_packet import assemble_workspace_context_packet
from conversation_os.workspace_client import WorkspaceClient
from conversation_os.workspace_coordination import (
    create_workspace_task,
    list_workspace_activity_events,
    list_workspace_blockers,
    list_workspace_tasks,
    record_workspace_blocker,
    resolve_workspace_blocker,
    update_workspace_task,
)
from conversation_os.workspace_store import SQLiteWorkspaceStore
from conversation_os.workspace_service import serve_workspace_service


def _store(root: Path) -> SQLiteWorkspaceStore:
    store = SQLiteWorkspaceStore(root, database_path=root / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {"workspace_id": "inner-world", "artifact_roots": ["src/"], "objectives": ["Coordinate work."]},
    )
    return store


def _create(root: Path, store: SQLiteWorkspaceStore, *, title: str = "Canonical lifecycle") -> dict:
    return create_workspace_task(
        root,
        "inner-world",
        task_id="CTX-006",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        title=title,
        reasoning="The server needs an operable task lifecycle.",
        status="ready",
        priority="high",
        owner="codex",
        acceptance_criteria=["agents share canonical task state"],
        constraints=["done requires governed completion"],
        depends_on=["CTX-005"],
        linked_artifacts=["docs/lifecycle.md"],
        source_refs=["docs/source-spec.md"],
        store=store,
    )


def test_create_task_is_idempotent_and_context_preserves_sources(tmp_path: Path) -> None:
    store = _store(tmp_path)

    created = _create(tmp_path, store)
    retried = _create(tmp_path, store)
    packet = assemble_workspace_context_packet(tmp_path, "inner-world", task_id="CTX-006", store=store)

    assert created["status"] == "ready"
    assert retried["already_exists"] is True
    assert len(list_workspace_tasks(tmp_path, "inner-world", store=store)) == 1
    assert packet["focus"]["task"]["source_refs"] == ["docs/source-spec.md"]
    assert "docs/source-spec.md" in packet["provenance"]["source_refs"]


def test_create_task_rejects_conflicting_retry(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _create(tmp_path, store)

    with pytest.raises(ValueError, match="already exists with different task data"):
        _create(tmp_path, store, title="Conflicting title")


def test_update_task_uses_allowed_transitions_and_reserves_done(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _create(tmp_path, store)

    updated = update_workspace_task(
        tmp_path,
        "inner-world",
        task_id="CTX-006",
        agent_id="openclaw",
        surface="telegram",
        session_id="telegram:11",
        reasoning="Implementation has started.",
        status="in-progress",
        owner="openclaw",
        store=store,
    )

    assert updated["status"] == "in-progress"
    assert updated["owner"] == "openclaw"
    with pytest.raises(ValueError, match="complete_workspace_task"):
        update_workspace_task(
            tmp_path,
            "inner-world",
            task_id="CTX-006",
            agent_id="openclaw",
            surface="telegram",
            session_id="telegram:11",
            reasoning="Attempt to bypass completion gates.",
            status="done",
            store=store,
        )


def test_resolve_blocker_preserves_history_and_unblocks_task(tmp_path: Path) -> None:
    store = _store(tmp_path)
    _create(tmp_path, store)
    blocker = record_workspace_blocker(
        tmp_path,
        "inner-world",
        task_id="CTX-006",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        reason="Need lifecycle contract.",
        store=store,
    )

    resolved = resolve_workspace_blocker(
        tmp_path,
        "inner-world",
        blocker_id=blocker["blocker_id"],
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        reasoning="Lifecycle contract is implemented and tested.",
        store=store,
    )

    assert resolved["status"] == "resolved"
    assert list_workspace_blockers(tmp_path, "inner-world", store=store) == []
    history = store.read_jsonl(store.blockers_path("inner-world"))
    assert [row["status"] for row in history] == ["active", "resolved"]
    assert any(
        row["event_type"] == "blocker_resolved"
        for row in list_workspace_activity_events(tmp_path, "inner-world", task_id="CTX-006", limit=20, store=store)
    )


def test_http_client_operates_task_lifecycle_against_canonical_store(tmp_path: Path) -> None:
    store = _store(tmp_path)
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        client = WorkspaceClient(f"http://127.0.0.1:{server.server_address[1]}/api")
        created = client.create_task(
            "inner-world",
            task_id="CTX-HTTP",
            agent_id="telegram:42",
            surface="telegram",
            session_id="telegram:11",
            title="Task from Telegram",
            reasoning="Capture work in canonical state.",
            status="ready",
            priority="high",
            owner="telegram:42",
            acceptance_criteria=["Codex sees the task"],
            constraints=[],
            depends_on=[],
            linked_artifacts=[],
            source_refs=["telegram:message:11"],
        )
        assert created["task_id"] == "CTX-HTTP"
        assert client.context("inner-world", task_id="CTX-HTTP", agent_id="codex")["focus"]["task"]["title"] == "Task from Telegram"

        updated = client.update_task(
            "inner-world",
            task_id="CTX-HTTP",
            agent_id="codex",
            surface="codex",
            session_id="s-2",
            reasoning="Codex has started implementation.",
            status="in-progress",
            owner="codex",
        )
        assert updated["status"] == "in-progress"
        blocker = record_workspace_blocker(
            tmp_path,
            "inner-world",
            task_id="CTX-HTTP",
            agent_id="codex",
            surface="codex",
            session_id="s-2",
            reason="Need source clarification.",
            store=store,
        )
        resolved = client.resolve_blocker(
            "inner-world",
            blocker_id=blocker["blocker_id"],
            agent_id="telegram:42",
            surface="telegram",
            session_id="telegram:11",
            reasoning="Source clarification supplied.",
        )
        assert resolved["status"] == "resolved"
    finally:
        server.shutdown()
        server.server_close()
