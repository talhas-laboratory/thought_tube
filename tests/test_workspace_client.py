from __future__ import annotations

import json
from pathlib import Path

import pytest

from conversation_os.workspace_client import WorkspaceClient, WorkspaceClientError
from conversation_os.workspace_coordination import list_workspace_decisions
from conversation_os.workspace_service import serve_workspace_service
from conversation_os.workspace_store import SQLiteWorkspaceStore


def _workspace_store(root: Path) -> SQLiteWorkspaceStore:
    store = SQLiteWorkspaceStore(root, database_path=root / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {
            "workspace_id": "inner-world",
            "artifact_roots": ["src/conversation_os/"],
            "objectives": ["Coordinate agent work."],
        },
    )
    store.append_jsonl(
        store.work_item_events_path("inner-world"),
        {
            "event_id": "create-ctx-001",
            "workspace_id": "inner-world",
            "work_item_id": "CTX-001",
            "operation": "create",
            "timestamp": "2026-06-30T10:00:00+00:00",
            "actor": "codex",
            "payload": {
                "title": "Canonical client",
                "kind": "task",
                "status": "in-progress",
                "priority": "high",
                "owner": "codex",
                "parent_id": "",
                "depends_on": [],
                "linked_artifacts": [],
                "linked_tests": [],
                "guard_status": "not_required",
                "guard_request": "",
                "guard_purpose": "",
                "guard_paths": [],
                "acceptance_criteria": ["all verbs work"],
                "constraints": [],
            },
            "source_refs": [],
        },
    )
    return store


def test_workspace_client_exercises_coordination_contract(tmp_path: Path) -> None:
    store = _workspace_store(tmp_path)
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        client = WorkspaceClient(f"http://127.0.0.1:{server.server_address[1]}")

        assert client.status("inner-world")["workspace_id"] == "inner-world"
        assert client.catalog()["workspace_count"] == 1
        assert client.tasks("inner-world")["workspace_id"] == "inner-world"
        assert client.prepare("inner-world", task_id="CTX-001", agent_id="codex")["workspace"]["workspace_id"] == "inner-world"

        parent = client.create_task(
            "inner-world", task_id="CTX-010", agent_id="codex", surface="codex", session_id="s-1",
            title="Group client work", reasoning="A parent groups independently tracked child work.",
            acceptance_criteria=["Children are visible."],
        )
        child = client.create_task(
            "inner-world", task_id="CTX-011", agent_id="codex", surface="codex", session_id="s-1",
            title="Exercise hierarchy", reasoning="The child is an independently verifiable task.",
            acceptance_criteria=["Parent is retained."], parent_task_id="CTX-010",
        )
        assert child["parent_id"] == parent["task_id"]
        tasks = client.prepare("inner-world", task_id="CTX-010", agent_id="codex")["tasks"]
        assert next(task for task in tasks if task["task_id"] == "CTX-010")["child_ids"] == ["CTX-011"]

        claim = client.claim(
            "inner-world",
            task_id="CTX-001",
            agent_id="codex",
            surface="codex",
            session_id="s-1",
            intent="Implement canonical client",
            claimed_paths=["src/conversation_os/workspace_client.py"],
        )
        assert claim["status"] == "active"

        decision = client.decision(
            "inner-world",
            task_id="CTX-001",
            agent_id="codex",
            surface="codex",
            session_id="s-1",
            summary="Use explicit service mode.",
            reasoning="Silent fallback can split canonical state.",
        )
        assert decision["status"] == "accepted"

        verification = client.verify(
            "inner-world",
            task_id="CTX-001",
            agent_id="codex",
            surface="codex",
            session_id="s-1",
            test_name="client-contract",
            result="passing",
            evidence_ref="pytest",
            command_or_protocol="pytest tests/test_workspace_client.py -q",
        )
        assert verification["result"] == "passing"

        blocker = client.blocker(
            "inner-world",
            task_id="CTX-002",
            agent_id="codex",
            surface="codex",
            session_id="s-1",
            reason="Waiting for client contract.",
            next_action="Complete CTX-001.",
        )
        assert blocker["status"] == "active"
        assert client.gate("inner-world")["status"] == "blocked"

        handoff = client.handoff(
            "inner-world",
            task_id="CTX-001",
            agent_id="codex",
            surface="codex",
            session_id="s-1",
            summary="Client contract implemented.",
            reasoning="All service verbs are represented.",
            next_action="Build context packet.",
        )
        assert handoff["released_claim_ids"] == [claim["claim_id"]]

        completion = client.complete(
            "inner-world",
            task_id="CTX-001",
            agent_id="codex",
            surface="codex",
            session_id="s-1",
            summary="Canonical client complete.",
            reasoning="The full HTTP coordination contract is represented.",
            files_touched=["src/conversation_os/workspace_client.py"],
            commands_run=["pytest tests/test_workspace_client.py -q"],
            residual_risks=["none known"],
        )
        assert completion["status"] == "done"
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_client_surfaces_http_failure_without_fallback(tmp_path: Path) -> None:
    store = _workspace_store(tmp_path)
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        client = WorkspaceClient(f"http://127.0.0.1:{server.server_address[1]}")
        with pytest.raises(WorkspaceClientError, match="Claimed path outside workspace artifact roots") as error:
            client.claim(
                "inner-world",
                task_id="CTX-001",
                agent_id="codex",
                surface="codex",
                session_id="s-1",
                intent="Invalid claim",
                claimed_paths=["product/"],
            )
        assert error.value.status_code == 400
        assert json.loads(error.value.response_body)["error"].startswith("Claimed path outside")
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_client_accepts_shared_api_base_format(tmp_path: Path) -> None:
    store = _workspace_store(tmp_path)
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        client = WorkspaceClient(f"http://127.0.0.1:{server.server_address[1]}/api")
        assert client.status("inner-world")["workspace_id"] == "inner-world"
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_client_idempotency_replays_one_mutation_and_rejects_key_reuse(tmp_path: Path) -> None:
    store = _workspace_store(tmp_path)
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        client = WorkspaceClient(f"http://127.0.0.1:{server.server_address[1]}/api")
        payload = {
            "task_id": "CTX-001",
            "agent_id": "codex",
            "surface": "codex",
            "session_id": "s-1",
            "summary": "Use a canonical service.",
            "reasoning": "Retries must not duplicate the decision ledger.",
            "_idempotency_key": "decision-request-1",
        }
        first = client.decision("inner-world", **payload)
        replay = client.decision("inner-world", **payload)
        assert replay == first
        assert len(list_workspace_decisions(tmp_path, "inner-world", task_id="CTX-001", store=store)) == 1

        with pytest.raises(WorkspaceClientError, match="Idempotency-Key") as error:
            client.decision("inner-world", **{**payload, "summary": "Different decision"})
        assert error.value.status_code == 409
    finally:
        server.shutdown()
        server.server_close()
