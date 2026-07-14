from __future__ import annotations

from pathlib import Path

import pytest

from conversation_os.workspace_coordination import (
    WorkspaceCompletionError,
    claim_workspace_task,
    complete_workspace_task,
    create_workspace_task,
    list_workspace_activity_events,
    list_workspace_claims,
    list_workspace_tasks,
    record_workspace_blocker,
    record_workspace_test_run,
)
from conversation_os.workspace_store import SQLiteWorkspaceStore


def _seed_task(root: Path) -> SQLiteWorkspaceStore:
    store = SQLiteWorkspaceStore(root, database_path=root / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {"workspace_id": "inner-world", "artifact_roots": ["src/"], "objectives": ["Finish reliably."]},
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
            "payload": {
                "title": "Completion gates",
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
                "acceptance_criteria": ["reject incomplete evidence"],
                "constraints": [],
            },
            "source_refs": [],
        },
    )
    return store


def _completion_kwargs() -> dict:
    return {
        "task_id": "CTX-004",
        "agent_id": "codex",
        "surface": "codex",
        "session_id": "session-1",
        "summary": "Completion contract implemented.",
        "reasoning": "Evidence-backed completion keeps the shared board trustworthy.",
        "files_touched": ["src/conversation_os/workspace_coordination.py"],
        "commands_run": ["pytest tests/test_workspace_completion_gates.py -q"],
        "residual_risks": ["none known"],
    }


def _record_passing_verification(root: Path, store: SQLiteWorkspaceStore, *, evidence_ref: str = "pytest:passing") -> None:
    record_workspace_test_run(
        root,
        "inner-world",
        task_id="CTX-004",
        agent_id="codex",
        surface="codex",
        session_id="session-1",
        test_name="completion-contract",
        result="passing",
        evidence_ref=evidence_ref,
        command_or_protocol="pytest tests/test_workspace_completion_gates.py -q",
        store=store,
    )


@pytest.mark.parametrize(
    ("field", "value", "missing"),
    [
        ("summary", "", "summary"),
        ("reasoning", "", "reasoning"),
        ("files_touched", [], "files_touched"),
        ("commands_run", [], "commands_run"),
        ("residual_risks", [], "residual_risks"),
    ],
)
def test_completion_rejects_each_missing_evidence_field(
    tmp_path: Path,
    field: str,
    value: object,
    missing: str,
) -> None:
    store = _seed_task(tmp_path)
    kwargs = _completion_kwargs()
    kwargs[field] = value

    with pytest.raises(WorkspaceCompletionError) as error:
        complete_workspace_task(tmp_path, "inner-world", store=store, **kwargs)

    assert missing in error.value.missing
    assert list_workspace_tasks(tmp_path, "inner-world", store=store)[0]["status"] == "in-progress"


def test_completion_requires_passing_verification_with_evidence(tmp_path: Path) -> None:
    store = _seed_task(tmp_path)
    _record_passing_verification(tmp_path, store, evidence_ref="")

    with pytest.raises(WorkspaceCompletionError) as error:
        complete_workspace_task(tmp_path, "inner-world", store=store, **_completion_kwargs())

    assert error.value.missing == ["verification_evidence"]


def test_completion_rejects_active_task_blocker(tmp_path: Path) -> None:
    store = _seed_task(tmp_path)
    _record_passing_verification(tmp_path, store)
    record_workspace_blocker(
        tmp_path,
        "inner-world",
        task_id="CTX-004",
        agent_id="codex",
        surface="codex",
        session_id="session-1",
        reason="A real blocker remains.",
        store=store,
    )

    with pytest.raises(WorkspaceCompletionError) as error:
        complete_workspace_task(tmp_path, "inner-world", store=store, **_completion_kwargs())

    assert error.value.missing == ["active_blockers"]


def test_completion_rejects_parent_with_open_subtasks(tmp_path: Path) -> None:
    store = _seed_task(tmp_path)
    create_workspace_task(
        tmp_path,
        "inner-world",
        task_id="CTX-005",
        agent_id="codex",
        surface="codex",
        session_id="session-1",
        title="Finish child evidence",
        reasoning="The parent must not close before this independently tracked work does.",
        acceptance_criteria=["Child work is finished."],
        parent_task_id="CTX-004",
        store=store,
    )
    _record_passing_verification(tmp_path, store)

    with pytest.raises(WorkspaceCompletionError) as error:
        complete_workspace_task(tmp_path, "inner-world", store=store, **_completion_kwargs())

    assert "open_subtasks:CTX-005" in error.value.missing


def test_completion_marks_done_releases_claim_and_is_idempotent(tmp_path: Path) -> None:
    store = _seed_task(tmp_path)
    claim = claim_workspace_task(
        tmp_path,
        "inner-world",
        task_id="CTX-004",
        agent_id="codex",
        surface="codex",
        session_id="session-1",
        intent="Implement completion contract.",
        claimed_paths=["src/conversation_os/workspace_coordination.py"],
        store=store,
    )
    _record_passing_verification(tmp_path, store)

    completed = complete_workspace_task(tmp_path, "inner-world", store=store, **_completion_kwargs())
    retried = complete_workspace_task(tmp_path, "inner-world", store=store, **_completion_kwargs())

    assert completed["status"] == "done"
    assert completed["released_claim_ids"] == [claim["claim_id"]]
    assert retried["already_completed"] is True
    assert list_workspace_tasks(tmp_path, "inner-world", store=store)[0]["status"] == "done"
    assert list_workspace_claims(tmp_path, "inner-world", store=store) == []
    completion_events = [
        row
        for row in list_workspace_activity_events(tmp_path, "inner-world", task_id="CTX-004", limit=50, store=store)
        if row["event_type"] == "completed"
    ]
    assert len(completion_events) == 1
    assert completion_events[0]["files_touched"] == _completion_kwargs()["files_touched"]
    assert completion_events[0]["commands_run"] == _completion_kwargs()["commands_run"]
    assert completion_events[0]["metadata"]["residual_risks"] == ["none known"]
