from __future__ import annotations

import subprocess
from pathlib import Path

from conversation_os.workspace_client import WorkspaceClient
from conversation_os.workspace_observer import observe_workspace
from conversation_os.workspace_service import serve_workspace_service
from conversation_os.workspace_store import SQLiteWorkspaceStore


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_cross_agent_workspace_lifecycle_reaches_release_ready(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "agent@example.test")
    _git(tmp_path, "config", "user.name", "Agent")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "feature.py").write_text("ready = True\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")

    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {
            "workspace_id": "inner-world",
            "purpose": "Coordinate cross-agent product work.",
            "artifact_roots": ["src/"],
            "objectives": ["Reach evidence-backed release readiness."],
        },
    )
    observe_workspace(tmp_path, "inner-world", store=store)
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        client = WorkspaceClient(f"http://127.0.0.1:{server.server_address[1]}/api")
        created = client.create_task(
            "inner-world",
            task_id="E2E-001",
            agent_id="telegram:42",
            surface="telegram",
            session_id="telegram:11",
            title="Cross-agent release",
            reasoning="The meta agent captured approved work.",
            status="ready",
            priority="high",
            owner="",
            acceptance_criteria=["canonical gate becomes ready"],
            constraints=["completion evidence is mandatory"],
            depends_on=[],
            linked_artifacts=["src/feature.py"],
            source_refs=["telegram:message:2"],
        )
        assert created["task_id"] == "E2E-001"
        assert client.context("inner-world", task_id="E2E-001", agent_id="codex")["focus"]["task"]["title"] == "Cross-agent release"

        client.update_task(
            "inner-world",
            task_id="E2E-001",
            agent_id="codex",
            surface="codex",
            session_id="codex:1",
            reasoning="Codex accepted implementation.",
            status="in-progress",
            owner="codex",
        )
        claim = client.claim(
            "inner-world",
            task_id="E2E-001",
            agent_id="codex",
            surface="codex",
            session_id="codex:1",
            intent="Implement and verify release behavior.",
            claimed_paths=["src/feature.py"],
        )
        client.decision(
            "inner-world",
            task_id="E2E-001",
            agent_id="codex",
            surface="codex",
            session_id="codex:1",
            summary="Keep one canonical service.",
            reasoning="Both agents must observe identical state.",
        )
        client.verify(
            "inner-world",
            task_id="E2E-001",
            agent_id="codex",
            surface="codex",
            session_id="codex:1",
            test_name="cross-agent-e2e",
            result="passing",
            evidence_ref="pytest:test_workspace_end_to_end",
            command_or_protocol="pytest tests/test_workspace_end_to_end.py -q",
        )
        completed = client.complete(
            "inner-world",
            task_id="E2E-001",
            agent_id="codex",
            surface="codex",
            session_id="codex:1",
            summary="Cross-agent lifecycle verified.",
            reasoning="Canonical context, ownership, provenance, and gates agree.",
            files_touched=["src/feature.py"],
            commands_run=["pytest tests/test_workspace_end_to_end.py -q"],
            residual_risks=["none known"],
        )

        assert completed["released_claim_ids"] == [claim["claim_id"]]
        gate = client.gate("inner-world")
        assert gate["status"] == "ready"
        assert gate["reasons"] == []
        assert gate["source_revision"]
        packet = client.context("inner-world", task_id="E2E-001", agent_id="telegram:42")
        assert packet["focus"]["task"]["status"] == "done"
        assert any(row["event_type"] == "completed" for row in packet["orientation"]["recent_activity"])
    finally:
        server.shutdown()
        server.server_close()
