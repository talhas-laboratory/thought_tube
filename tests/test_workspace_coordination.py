from __future__ import annotations

import json
from pathlib import Path

import pytest

import conversation_os.workspace_coordination as workspace_coordination
from conversation_os.storage import append_jsonl, ensure_dir, read_jsonl
from conversation_os.workspace_coordination import (
    append_workspace_activity_event,
    claim_workspace_task,
    create_workspace_task,
    evaluate_workspace_release_gate,
    list_workspace_activity_events,
    list_workspace_blockers,
    list_workspace_claims,
    load_workspace_manifest,
    prepare_workspace_task,
    record_workspace_blocker,
    record_workspace_decision,
    record_workspace_test_run,
    release_workspace_task_claims,
    render_workspace_tasks,
)


def _write_workspace_manifest(root: Path, workspace_id: str, payload: dict) -> None:
    workspace_dir = root / "memory" / "workspaces" / workspace_id
    ensure_dir(workspace_dir)
    (workspace_dir / "manifest.json").write_text(json.dumps(payload), encoding="utf-8")


def _append_work_item(root: Path, workspace_id: str, *, work_item_id: str, title: str, status: str) -> None:
    append_jsonl(
        root / "memory" / "workspaces" / workspace_id / "work_item_events.jsonl",
        {
            "event_id": f"work-item-event-{work_item_id}",
            "workspace_id": workspace_id,
            "work_item_id": work_item_id,
            "operation": "create",
            "timestamp": "2026-06-30T12:00:00+00:00",
            "actor": "agent",
            "payload": {
                "title": title,
                "kind": "task",
                "status": status,
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


def test_load_workspace_manifest_migrates_scope_in_into_paths_and_objectives(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-context-frames",
        {
            "workspace_id": "sol-context-frames",
            "scope_in": [
                "src/conversation_os/",
                "Fix bridge retrieval candidate timing.",
            ],
            "scope_out": ["No deploy"],
            "domain_overlays": ["bridge", "knowledge"],
        },
    )

    payload = load_workspace_manifest(tmp_path, "sol-context-frames")

    assert payload["artifact_roots"] == ["src/conversation_os/"]
    assert payload["objectives"] == ["Fix bridge retrieval candidate timing."]
    assert payload["domains"] == ["bridge", "knowledge"]
    assert payload["activity_ref"].endswith("memory/workspaces/sol-context-frames/activity_events.jsonl")


def test_load_workspace_manifest_uses_workspace_store_adapter(tmp_path: Path, monkeypatch) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-context-frames",
        {
            "workspace_id": "sol-context-frames",
            "artifact_roots": ["src/conversation_os/"],
            "objectives": ["Keep coordination durable."],
        },
    )

    class RecordingStore:
        def __init__(self, root: Path) -> None:
            self.root = root
            self.calls: list[tuple[str, str]] = []

        def manifest_path(self, workspace_id: str) -> Path:
            self.calls.append(("manifest_path", workspace_id))
            return self.root / "memory" / "workspaces" / workspace_id / "manifest.json"

        def activity_events_path(self, workspace_id: str) -> Path:
            self.calls.append(("activity_events_path", workspace_id))
            return self.root / "memory" / "workspaces" / workspace_id / "activity_events.jsonl"

        def read_json(self, path: Path, default=None):
            self.calls.append(("read_json", path.name))
            return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default

    store = RecordingStore(tmp_path)
    monkeypatch.setattr(workspace_coordination, "_workspace_store", lambda root: store)

    payload = load_workspace_manifest(tmp_path, "sol-context-frames")

    assert payload["workspace_id"] == "sol-context-frames"
    assert store.calls[:3] == [
        ("manifest_path", "sol-context-frames"),
        ("read_json", "manifest.json"),
        ("activity_events_path", "sol-context-frames"),
    ]


def test_workspace_claims_block_overlapping_paths_from_other_actors(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )

    first = claim_workspace_task(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        intent="Harden the shell",
        claimed_paths=["product/thought_capture_pwa/"],
    )
    assert first["status"] == "active"

    try:
        claim_workspace_task(
            tmp_path,
            "sol-frontend",
            task_id="MTC-002",
            agent_id="telegram-meta",
            surface="telegram",
            session_id="s-2",
            intent="Change the same area",
            claimed_paths=["product/thought_capture_pwa/src/"],
        )
    except ValueError as exc:
        assert "overlaps" in str(exc)
    else:
        raise AssertionError("expected overlap error")


def test_workspace_tasks_support_one_level_subtasks_and_render_them(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {"workspace_id": "sol-frontend", "objectives": ["Ship the PWA."]},
    )
    parent = create_workspace_task(
        tmp_path, "sol-frontend", task_id="MTC-001", agent_id="codex", surface="codex", session_id="s-1",
        title="Ship capture", reasoning="The parent groups independently verifiable work.", acceptance_criteria=["Capture ships."],
    )
    child = create_workspace_task(
        tmp_path, "sol-frontend", task_id="MTC-002", agent_id="codex", surface="codex", session_id="s-1",
        title="Add capture test", reasoning="This work can be verified independently.", acceptance_criteria=["Test passes."], parent_task_id="MTC-001",
    )

    assert child["parent_id"] == parent["task_id"]
    tasks = workspace_coordination.list_workspace_tasks(tmp_path, "sol-frontend", limit=10)
    parent_task = next(task for task in tasks if task["task_id"] == "MTC-001")
    assert parent_task["child_ids"] == ["MTC-002"]
    assert parent_task["open_subtask_count"] == 1
    assert "  - MTC-002 [backlog] Add capture test" in render_workspace_tasks(tmp_path, "sol-frontend")

    with pytest.raises(ValueError, match="one subtask level"):
        create_workspace_task(
            tmp_path, "sol-frontend", task_id="MTC-003", agent_id="codex", surface="codex", session_id="s-1",
            title="Nested task", reasoning="This would exceed the supported depth.", acceptance_criteria=["Never created."], parent_task_id="MTC-002",
        )


def test_prepare_workspace_task_includes_recent_activity_claims_and_tasks(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
            "scope_out": ["backend"],
            "domains": ["frontend"],
        },
    )
    _append_work_item(tmp_path, "sol-frontend", work_item_id="MTC-001", title="Capture shell", status="ready")
    append_workspace_activity_event(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        event_type="edited",
        summary="Adjusted capture shell spacing.",
        reasoning="Needed tighter spacing on mobile.",
        files_touched=["product/thought_capture_pwa/src/shell/app-shell.tsx"],
    )
    claim_workspace_task(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        intent="Finish capture shell",
        claimed_paths=["product/thought_capture_pwa/"],
    )

    packet = prepare_workspace_task(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
    )

    assert packet["workspace"]["artifact_roots"] == ["product/thought_capture_pwa/"]
    assert packet["task"]["task_id"] == "MTC-001"
    assert packet["active_claims"][0]["task_id"] == "MTC-001"
    assert packet["recent_activity"][0]["event_type"] == "edited"


def test_release_workspace_task_claims_marks_claim_released_and_logs_handoff(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    claim = claim_workspace_task(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        intent="Finish capture shell",
        claimed_paths=["product/thought_capture_pwa/"],
    )

    result = release_workspace_task_claims(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        summary="Handed off remaining verification.",
        reasoning="Implementation is done, verification still pending.",
        next_action="Run the PWA verification suite.",
    )

    assert claim["claim_id"] in result["released_claim_ids"]
    active_claims = list_workspace_claims(tmp_path, "sol-frontend")
    assert active_claims == []
    activity = list_workspace_activity_events(tmp_path, "sol-frontend")
    assert activity[0]["event_type"] == "handoff"
    claim_rows = read_jsonl(tmp_path / "memory" / "workspaces" / "sol-frontend" / "claims.jsonl")
    assert claim_rows[-1]["status"] == "released"


def test_record_workspace_decision_persists_ledger_and_prepare_packet(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    _append_work_item(tmp_path, "sol-frontend", work_item_id="MTC-001", title="Capture shell", status="ready")

    decision = record_workspace_decision(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        summary="Keep note/meta toggle in the existing shell language.",
        reasoning="It preserves continuity and reduces UI surface churn.",
    )

    packet = prepare_workspace_task(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
    )

    assert decision["task_id"] == "MTC-001"
    assert packet["decisions"][0]["decision_id"] == decision["decision_id"]
    assert packet["recent_activity"][0]["event_type"] == "decided"


def test_record_workspace_test_run_creates_case_and_prepare_packet_includes_verification(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    _append_work_item(tmp_path, "sol-frontend", work_item_id="MTC-001", title="Capture shell", status="ready")

    run = record_workspace_test_run(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        test_name="mobile-smoke",
        result="passing",
        evidence_ref="artifacts/mobile-smoke.txt",
        notes="Shell loads and toggle responds on iPhone Safari.",
        command_or_protocol="pnpm test:e2e mobile-smoke",
    )

    packet = prepare_workspace_task(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
    )

    assert run["result"] == "passing"
    assert packet["tests"][0]["latest_result"] == "passing"
    assert packet["tests"][0]["latest_evidence_ref"] == "artifacts/mobile-smoke.txt"
    assert packet["recent_activity"][0]["event_type"] == "tested"


def test_record_workspace_blocker_persists_and_prepare_packet_includes_blockers(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    _append_work_item(tmp_path, "sol-frontend", work_item_id="MTC-001", title="Capture shell", status="blocked")

    blocker = record_workspace_blocker(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        reason="Mobile shell collapses on Safari reload.",
        next_action="Inspect hydration path on iPhone Safari.",
    )

    packet = prepare_workspace_task(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
    )

    assert blocker["status"] == "active"
    assert list_workspace_blockers(tmp_path, "sol-frontend")[0]["blocker_id"] == blocker["blocker_id"]
    assert packet["blockers"][0]["reason"] == "Mobile shell collapses on Safari reload."
    assert packet["recent_activity"][0]["event_type"] == "blocked"


def test_evaluate_workspace_release_gate_blocks_active_blockers(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    _append_work_item(tmp_path, "sol-frontend", work_item_id="MTC-001", title="Capture shell", status="done")
    record_workspace_test_run(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        test_name="mobile-smoke",
        result="passing",
        evidence_ref="artifacts/mobile-smoke.txt",
    )
    record_workspace_blocker(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        reason="Post-reload shell regression remains unresolved.",
        next_action="Fix reload path.",
    )

    gate = evaluate_workspace_release_gate(tmp_path, "sol-frontend")

    assert gate["status"] == "blocked"
    assert "active_blockers" in gate["reasons"]


def test_evaluate_workspace_release_gate_blocks_active_claims(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    _append_work_item(tmp_path, "sol-frontend", work_item_id="MTC-001", title="Capture shell", status="done")
    record_workspace_test_run(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        test_name="mobile-smoke",
        result="passing",
        evidence_ref="artifacts/mobile-smoke.txt",
    )
    claim_workspace_task(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        intent="Final polish",
        claimed_paths=["product/thought_capture_pwa/"],
    )

    gate = evaluate_workspace_release_gate(tmp_path, "sol-frontend")

    assert gate["status"] == "blocked"
    assert "active_claims" in gate["reasons"]


def test_evaluate_workspace_release_gate_blocks_missing_verification(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    _append_work_item(tmp_path, "sol-frontend", work_item_id="MTC-001", title="Capture shell", status="done")

    gate = evaluate_workspace_release_gate(tmp_path, "sol-frontend")

    assert gate["status"] == "blocked"
    assert "missing_verification" in gate["reasons"]


def test_evaluate_workspace_release_gate_passes_with_no_claims_blockers_and_passing_verification(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    _append_work_item(tmp_path, "sol-frontend", work_item_id="MTC-001", title="Capture shell", status="done")
    record_workspace_test_run(
        tmp_path,
        "sol-frontend",
        task_id="MTC-001",
        agent_id="codex",
        surface="codex",
        session_id="s-1",
        test_name="mobile-smoke",
        result="passing",
        evidence_ref="artifacts/mobile-smoke.txt",
    )
    append_jsonl(
        tmp_path / "memory" / "workspaces" / "sol-frontend" / "repository_snapshots.jsonl",
        {
            "schema_version": "1.0",
            "source_revision": "abc123",
            "changes": [],
            "changed_files": [],
            "fingerprint": "snapshot-1",
            "observed_at": "2026-06-30T12:10:00+00:00",
        },
    )

    gate = evaluate_workspace_release_gate(tmp_path, "sol-frontend")

    assert gate["status"] == "ready"
    assert gate["reasons"] == []


def test_evaluate_workspace_release_gate_requires_evidence_and_blocks_active_work(tmp_path: Path) -> None:
    _write_workspace_manifest(
        tmp_path,
        "sol-frontend",
        {"workspace_id": "sol-frontend", "artifact_roots": ["src/"]},
    )

    empty_gate = evaluate_workspace_release_gate(tmp_path, "sol-frontend")
    assert empty_gate["status"] == "blocked"
    assert "missing_verification" in empty_gate["reasons"]
    assert "missing_repository_snapshot" in empty_gate["reasons"]

    _append_work_item(
        tmp_path,
        "sol-frontend",
        work_item_id="CTX-ACTIVE",
        title="Active work",
        status="in-progress",
    )
    active_gate = evaluate_workspace_release_gate(tmp_path, "sol-frontend")
    assert active_gate["status"] == "blocked"
    assert "active_tasks" in active_gate["reasons"]
