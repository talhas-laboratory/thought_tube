from __future__ import annotations

from pathlib import Path

from conversation_os.workspace_context_packet import assemble_workspace_context_packet
from conversation_os.workspace_runs import begin_workspace_run, end_workspace_run
from conversation_os.workspace_store import SQLiteWorkspaceStore


def _seed_workspace(root: Path) -> SQLiteWorkspaceStore:
    store = SQLiteWorkspaceStore(root, database_path=root / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {
            "workspace_id": "inner-world",
            "label": "Inner World",
            "goal": "Create a durable agent context repository.",
            "purpose": "Coordinate agents without losing reasoning.",
            "artifact_roots": ["src/conversation_os/", "docs/workboards/"],
            "objectives": ["Keep context current."],
            "scope_out": ["Silent local divergence."],
        },
    )
    for index in range(30):
        store.append_jsonl(
            store.work_item_events_path("inner-world"),
            {
                "event_id": f"event-{index}",
                "workspace_id": "inner-world",
                "work_item_id": f"CTX-{index:03d}",
                "operation": "create",
                "timestamp": f"2026-06-30T12:{index:02d}:00+00:00",
                "actor": "codex",
                "payload": {
                    "title": f"Context task {index}",
                    "kind": "task",
                    "status": "in-progress" if index == 2 else "backlog",
                    "priority": "high" if index == 2 else "medium",
                    "owner": "codex" if index == 2 else "",
                    "parent_id": "",
                    "depends_on": [],
                    "linked_artifacts": ["docs/source.md"],
                    "linked_tests": [],
                    "guard_status": "not_required",
                    "guard_request": "",
                    "guard_purpose": "",
                    "guard_paths": [],
                    "acceptance_criteria": ["packet is bounded", "sources remain visible"],
                    "constraints": ["no silent fallback"],
                },
                "source_refs": ["docs/source.md"],
            },
        )
    return store


def test_context_packet_is_task_first_bounded_and_provenanced(tmp_path: Path) -> None:
    store = _seed_workspace(tmp_path)

    packet = assemble_workspace_context_packet(
        tmp_path,
        "inner-world",
        task_id="CTX-002",
        agent_id="codex",
        surface="codex",
        session_id="session-1",
        store=store,
        repository_snapshot={
            "source_revision": "abc123",
            "changed_files": ["src/conversation_os/workspace_context_packet.py"],
            "fingerprint": "snapshot-1",
        },
    )

    assert packet["schema_version"] == "1.0"
    assert packet["workspace"]["purpose"] == "Coordinate agents without losing reasoning."
    assert packet["focus"]["task"]["task_id"] == "CTX-002"
    assert packet["focus"]["acceptance_criteria"] == ["packet is bounded", "sources remain visible"]
    assert packet["agent"] == {"agent_id": "codex", "surface": "codex", "session_id": "session-1"}
    assert packet["repository"]["source_revision"] == "abc123"
    assert packet["repository"]["changed_files"] == ["src/conversation_os/workspace_context_packet.py"]
    assert len(packet["orientation"]["nearby_tasks"]) <= 12
    assert any(item["task_id"] == "CTX-002" for item in packet["orientation"]["open_threads"])
    assert "docs/source.md" in packet["provenance"]["source_refs"]
    assert packet["assembled_at"]


def test_context_packet_marks_unobserved_repository_state(tmp_path: Path) -> None:
    store = _seed_workspace(tmp_path)
    packet = assemble_workspace_context_packet(tmp_path, "inner-world", task_id="CTX-002", store=store)
    assert packet["repository"]["freshness_status"] == "unobserved"
    assert packet["repository"]["source_revision"] == ""


def test_context_packet_keeps_bounded_closed_run_handoff_provenance(tmp_path: Path) -> None:
    store = _seed_workspace(tmp_path)
    run = begin_workspace_run(
        tmp_path,
        "inner-world",
        task_id="CTX-002",
        agent_id="codex",
        device_id="laptop",
        surface="codex",
        session_id="packet-test",
        intent="Establish a handoff trail.",
        store=store,
    )
    end_workspace_run(
        tmp_path,
        "inner-world",
        run_id=run["run_id"],
        agent_id="codex",
        status="handed_off",
        reason="A second surface should resume from this packet.",
        store=store,
    )

    packet = assemble_workspace_context_packet(tmp_path, "inner-world", task_id="CTX-002", store=store)

    assert packet["orientation"]["active_runs"] == []
    assert [item["run_id"] for item in packet["orientation"]["recent_runs"]] == [run["run_id"]]
    assert packet["orientation"]["recent_runs"][0]["status"] == "handed_off"
    assert packet["orientation"]["recent_runs"][0]["end_reason"] == "A second surface should resume from this packet."
