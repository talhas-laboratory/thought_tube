from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from unittest import mock

from conversation_os.builder_behavior import compose_builder_packet_input
from conversation_os.self_improvement import build_self_improvement_chat_response
from conversation_os.self_improvement_agent import draft_self_improvement_packet
from conversation_os.storage import ensure_dir
from conversation_os.workspace_service import serve_workspace_service
from conversation_os.workspace_store import SQLiteWorkspaceStore
from conversation_os.workspace_coordination import record_workspace_blocker, record_workspace_test_run

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "tools" / "run_telegram_meta_agent.py"
sys.path.append(str(SCRIPT_PATH.parent))
SPEC = importlib.util.spec_from_file_location("run_telegram_meta_agent", SCRIPT_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_poll_once_processes_updates_and_advances_offset(tmp_path: Path) -> None:
    updates = [{"update_id": 10, "message": {"message_id": 1}}]
    extracted = {
        "text": "/status",
        "chat_id": "11",
        "update_id": "10",
        "user_id": "42",
        "message_id": "1",
    }
    with (
        mock.patch.object(runner, "_telegram_get_updates", return_value=updates),
        mock.patch.object(runner, "extract_telegram_message", return_value=extracted),
        mock.patch.object(runner, "_handle_meta_command", return_value=(0, "ok")) as handle,
        mock.patch.object(runner, "_telegram_send_message") as send,
    ):
        code = runner._poll_once(
            bot_token="token",
            allowed_user_ids={42},
            workspace_root=tmp_path,
            api_base="http://127.0.0.1:8422/api",
        )

    assert code == 0
    handle.assert_called_once()
    send.assert_called_once_with("token", chat_id="11", text="ok")
    assert runner.read_telegram_offset(tmp_path) == 11


def test_main_requires_token_for_poll_forever() -> None:
    argv = ["run_telegram_meta_agent.py", "--poll-forever"]
    with mock.patch.object(sys, "argv", argv):
        assert runner.main() == 1


def test_handle_meta_command_supports_workspace_selection_and_task_listing(tmp_path: Path) -> None:
    workspace_id = "sol-frontend"
    workspace_dir = tmp_path / "memory" / "workspaces" / workspace_id
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "manifest.json").write_text(
        json.dumps(
            {
                "workspace_id": workspace_id,
                "artifact_roots": ["product/thought_capture_pwa/"],
                "objectives": ["Ship the PWA."],
            }
        ),
        encoding="utf-8",
    )
    (workspace_dir / "work_item_events.jsonl").write_text(
        json.dumps(
            {
                "event_id": "work-item-event-1",
                "workspace_id": workspace_id,
                "work_item_id": "MTC-001",
                "operation": "create",
                "timestamp": "2026-06-30T12:00:00+00:00",
                "actor": "agent",
                "payload": {
                    "title": "Capture shell",
                    "kind": "task",
                    "status": "ready",
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
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with mock.patch.object(runner, "repo_root_from", return_value=tmp_path):
        code, reply = runner._handle_meta_command(
            text="/workspace sol-frontend",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
        )
        assert code == 0
        assert "Workspace: sol-frontend" in reply

        code, reply = runner._handle_meta_command(
            text="/tasks",
            chat_id="11",
            update_id="11",
            user_id="42",
            message_id="2",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
        )
        assert code == 0
        assert "MTC-001" in reply
        assert "Capture shell" in reply


def test_handle_meta_command_uses_openclaw_for_plain_conversation(tmp_path: Path) -> None:
    runtime_root = tmp_path / "meta-runtime"
    with mock.patch.object(runner, "_request_meta_openclaw_reply", return_value="Here is my read on the current UI.") as openclaw:
        code, reply = runner._handle_meta_command(
            text="what do you think about the current ui",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
        )

    assert code == 0
    assert reply == "Here is my read on the current UI."
    openclaw.assert_called_once()
    builder_state = runner.read_builder_session_state(runtime_root, "telegram:11")
    assert "UI" in builder_state["candidate_objective"]
    assert builder_state["conversation_view"]["needs_analysis"] is True


def test_handle_meta_command_persists_builder_conversation_state(tmp_path: Path) -> None:
    workspace_id = "inner-world"
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path(workspace_id),
        {"workspace_id": workspace_id, "artifact_roots": ["product/thought_capture_pwa/"]},
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    base_url = f"http://127.0.0.1:{server.server_address[1]}/api"
    runtime_root = tmp_path / "meta-runtime"
    try:
        assert runner._handle_meta_command(
            text="/workspace inner-world",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )[0] == 0

        original_post_json = runner._post_json

        def fake_post_json(url: str, payload: dict) -> dict:
            if url.endswith("/self-improvement/chat"):
                response = build_self_improvement_chat_response(
                    str(payload.get("text") or ""),
                    requested_mode=str(payload.get("surface_mode") or ""),
                    requested_meta_state=str(payload.get("meta_state") or ""),
                    builder_state=payload.get("builder_state"),
                    workspace_context=payload.get("workspace_context"),
                )
                if response["interpretation"]["should_create_packet"]:
                    response["packet"] = draft_self_improvement_packet(
                        compose_builder_packet_input(
                            str(payload.get("text") or ""),
                            response.get("builder_state", {}) or {},
                            response.get("builder_scope", {}) or {},
                        ),
                        str(payload.get("session_id") or ""),
                        str(payload.get("turn_id") or ""),
                    )
                return response
            return original_post_json(url, payload)

        with mock.patch.object(runner, "_post_json", side_effect=fake_post_json):
            code, reply = runner._handle_meta_command(
                text="/change make the notes app reply less verbose",
                chat_id="11",
                update_id="11",
                user_id="42",
                message_id="2",
                workspace_root=runtime_root,
                api_base="http://127.0.0.1:8422/api",
                workspace_api_base=base_url,
            )
            assert code == 0
            assert "I think you're trying to" in reply

            code, reply = runner._handle_meta_command(
                text="yes",
                chat_id="11",
                update_id="12",
                user_id="42",
                message_id="3",
                workspace_root=runtime_root,
                api_base="http://127.0.0.1:8422/api",
                workspace_api_base=base_url,
            )
            assert code == 0
            assert "What should count as done" in reply

            code, reply = runner._handle_meta_command(
                text="Keep replies short while preserving action items.",
                chat_id="11",
                update_id="13",
                user_id="42",
                message_id="4",
                workspace_root=runtime_root,
                api_base="http://127.0.0.1:8422/api",
                workspace_api_base=base_url,
            )
            assert code == 0
            assert "Scope:" in reply
            assert "Packet: sip-" in reply
            assert "Workspace task: SIP-" in reply

            builder_state = runner.read_builder_session_state(runtime_root, "telegram:11")
            assert builder_state["workspace_task_id"].startswith("SIP-")
            assert builder_state["claim_status"] in {"active", "not_claimed"}
            assert builder_state["last_decision_id"].startswith("decision-")

            context = runner._get_json(
                runner._workspace_service_url(
                    base_url,
                    "inner-world",
                    "context",
                    query={
                        "task_id": builder_state["workspace_task_id"],
                        "agent_id": "codex",
                        "surface": "codex",
                        "session_id": "s-1",
                    },
                )
            )
            assert context["focus"]["task"]["task_id"] == builder_state["workspace_task_id"]
            assert "make the notes app reply less verbose" in context["focus"]["task"]["title"]
            assert context["orientation"]["decisions"][0]["decision_id"] == builder_state["last_decision_id"]
    finally:
        server.shutdown()
        server.server_close()


def test_builder_follow_up_updates_task_records_verification_and_completes(tmp_path: Path) -> None:
    workspace_id = "inner-world"
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path(workspace_id),
        {"workspace_id": workspace_id, "artifact_roots": ["src/", "tools/"], "objectives": ["Coordinate work."]},
    )
    create_payload = {
        "task_id": "SIP-200",
        "agent_id": "telegram:42",
        "surface": "telegram",
        "session_id": "telegram:11",
        "title": "Shorten notes replies",
        "reasoning": "Builder-scoped work.",
        "status": "ready",
        "priority": "high",
        "owner": "",
        "acceptance_criteria": ["Keep replies short while preserving action items."],
        "constraints": [],
        "depends_on": [],
        "linked_artifacts": [],
        "source_refs": ["telegram:message:4"],
    }
    runner.create_workspace_task(tmp_path, workspace_id, store=store, **create_payload)
    run = runner.begin_workspace_run(
        tmp_path,
        workspace_id,
        task_id="SIP-200",
        agent_id="telegram:42",
        device_id="telegram-chat:11",
        surface="telegram",
        session_id="telegram:11",
        intent="Builder session is coordinating this task.",
        store=store,
    )
    runner.save_builder_session_state(
        tmp_path / "meta-runtime",
        "telegram:11",
        {
            "phase": "scoping",
            "candidate_objective": "make the notes app reply less verbose",
            "confirmed_objective": "make the notes app reply less verbose",
            "objective_confirmed": True,
            "pending_question": "",
            "acceptance_criteria": "Keep replies short while preserving action items.",
            "target_meta_state": "operate",
            "workspace_task_id": "SIP-200",
            "workspace_run_id": run["run_id"],
            "claim_status": "not_claimed",
        },
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    base_url = f"http://127.0.0.1:{server.server_address[1]}/api"
    runtime_root = tmp_path / "meta-runtime"
    try:
        assert runner._handle_meta_command(
            text="/workspace inner-world",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )[0] == 0

        code, reply = runner._handle_meta_command(
            text="start implementation",
            chat_id="11",
            update_id="11",
            user_id="42",
            message_id="2",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0
        assert "Task SIP-200 is now in-progress" in reply

        code, reply = runner._handle_meta_command(
            text="tests passed after pytest tests/test_conversation_os.py -q",
            chat_id="11",
            update_id="12",
            user_id="42",
            message_id="3",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0
        assert "Verification recorded for SIP-200" in reply
        builder_state = runner.read_builder_session_state(runtime_root, "telegram:11")
        assert builder_state["claim_status"] == "released"
        assert builder_state["workspace_run_id"] == ""

        code, reply = runner._handle_meta_command(
            text=(
                "complete: Shorter notes replies shipped :: Verification passed and behavior stayed bounded :: "
                "src/conversation_os/miniapp.py,tools/run_telegram_meta_agent.py :: "
                "pytest tests/test_conversation_os.py -q ;; python3 -m py_compile tools/run_telegram_meta_agent.py :: none known"
            ),
            chat_id="11",
            update_id="13",
            user_id="42",
            message_id="4",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0
        assert "Completed SIP-200" in reply
        context = runner._get_json(
            runner._workspace_service_url(
                base_url,
                "inner-world",
                "context",
                query={
                    "task_id": "SIP-200",
                    "agent_id": "codex",
                    "surface": "codex",
                    "session_id": "s-1",
                },
            )
        )
        assert any(row["summary"] == "Execution started" for row in context["orientation"]["decisions"])
        assert any(
            any("Review completion evidence" in ref for ref in row.get("handoff_refs", []))
            for row in context["orientation"]["recent_activity"]
        )
        assert context["orientation"]["recent_runs"][0]["run_id"] == run["run_id"]
        assert context["orientation"]["recent_runs"][0]["status"] == "handed_off"
    finally:
        server.shutdown()
        server.server_close()


def test_builder_follow_up_collects_completion_evidence_conversationally(tmp_path: Path) -> None:
    workspace_id = "inner-world"
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path(workspace_id),
        {"workspace_id": workspace_id, "artifact_roots": ["src/", "tools/"], "objectives": ["Coordinate work."]},
    )
    create_payload = {
        "task_id": "SIP-201",
        "agent_id": "telegram:42",
        "surface": "telegram",
        "session_id": "telegram:11",
        "title": "Shorten notes replies",
        "reasoning": "Builder-scoped work.",
        "status": "in-progress",
        "priority": "high",
        "owner": "telegram:42",
        "acceptance_criteria": ["Keep replies short while preserving action items."],
        "constraints": [],
        "depends_on": [],
        "linked_artifacts": [],
        "source_refs": ["telegram:message:4"],
    }
    runner.create_workspace_task(tmp_path, workspace_id, store=store, **create_payload)
    record_workspace_test_run(
        tmp_path,
        workspace_id,
        task_id="SIP-201",
        agent_id="telegram:42",
        surface="telegram",
        session_id="telegram:11",
        test_name="builder-follow-up",
        result="passing",
        evidence_ref="telegram:message:3",
        notes="tests passed",
        store=store,
    )
    runner.save_builder_session_state(
        tmp_path / "meta-runtime",
        "telegram:11",
        {
            "phase": "verification",
            "candidate_objective": "make the notes app reply less verbose",
            "confirmed_objective": "make the notes app reply less verbose",
            "objective_confirmed": True,
            "pending_question": "",
            "acceptance_criteria": "Keep replies short while preserving action items.",
            "target_meta_state": "operate",
            "workspace_task_id": "SIP-201",
            "claim_status": "released",
        },
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    base_url = f"http://127.0.0.1:{server.server_address[1]}/api"
    runtime_root = tmp_path / "meta-runtime"
    try:
        assert runner._handle_meta_command(
            text="/workspace inner-world",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )[0] == 0

        prompts = [
            ("done", "What short summary should I record for completion?"),
            ("Shorter notes replies shipped.", "What reasoning should I record"),
            ("Verification passed and behavior stayed bounded.", "Which files changed?"),
            ("src/conversation_os/miniapp.py,tools/run_telegram_meta_agent.py", "Which verification commands did you run?"),
            ("pytest tests/test_conversation_os.py -q ;; python3 -m py_compile tools/run_telegram_meta_agent.py", "What residual risks remain?"),
        ]
        for update_id, (text, expected) in enumerate(prompts, start=11):
            code, reply = runner._handle_meta_command(
                text=text,
                chat_id="11",
                update_id=str(update_id),
                user_id="42",
                message_id=str(update_id),
                workspace_root=runtime_root,
                api_base="http://127.0.0.1:8422/api",
                workspace_api_base=base_url,
            )
            assert code == 0
            assert expected in reply

        code, reply = runner._handle_meta_command(
            text="none known",
            chat_id="11",
            update_id="16",
            user_id="42",
            message_id="16",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0
        assert "Completed SIP-201" in reply
    finally:
        server.shutdown()
        server.server_close()


def test_builder_resume_reports_next_gap_from_canonical_context(tmp_path: Path) -> None:
    workspace_id = "inner-world"
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path(workspace_id),
        {"workspace_id": workspace_id, "artifact_roots": ["src/", "tools/"], "objectives": ["Coordinate work."]},
    )
    runner.create_workspace_task(
        tmp_path,
        workspace_id,
        store=store,
        task_id="SIP-300",
        agent_id="telegram:42",
        surface="telegram",
        session_id="telegram:11",
        title="Shorten notes replies",
        reasoning="Builder-scoped work.",
        status="in-progress",
        priority="high",
        owner="telegram:42",
        acceptance_criteria=["Keep replies short while preserving action items."],
        constraints=[],
        depends_on=[],
        linked_artifacts=[],
        source_refs=["telegram:message:4"],
    )
    runner.save_builder_session_state(
        tmp_path / "meta-runtime",
        "telegram:11",
        {
            "phase": "execution",
            "candidate_objective": "make the notes app reply less verbose",
            "confirmed_objective": "make the notes app reply less verbose",
            "objective_confirmed": True,
            "pending_question": "",
            "acceptance_criteria": "Keep replies short while preserving action items.",
            "target_meta_state": "operate",
            "workspace_task_id": "SIP-300",
            "claim_status": "active",
        },
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    base_url = f"http://127.0.0.1:{server.server_address[1]}/api"
    runtime_root = tmp_path / "meta-runtime"
    try:
        assert runner._handle_meta_command(
            text="/workspace inner-world",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )[0] == 0

        code, reply = runner._handle_meta_command(
            text="continue",
            chat_id="11",
            update_id="11",
            user_id="42",
            message_id="2",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0
        assert "SIP-300 is currently in-progress." in reply
        assert "Next gap: record passing verification" in reply
    finally:
        server.shutdown()
        server.server_close()


def test_builder_resume_can_include_gitnexus_enrichment_hints(tmp_path: Path) -> None:
    workspace_id = "inner-world"
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path(workspace_id),
        {
            "workspace_id": workspace_id,
            "artifact_roots": ["src/", "tools/"],
            "objectives": ["Coordinate work."],
        },
    )
    runner.create_workspace_task(
        tmp_path,
        workspace_id,
        store=store,
        task_id="SIP-301",
        agent_id="telegram:42",
        surface="telegram",
        session_id="telegram:11",
        title="Shorten notes replies",
        reasoning="Builder-scoped work.",
        status="in-progress",
        priority="high",
        owner="telegram:42",
        acceptance_criteria=["Keep replies short while preserving action items."],
        constraints=[],
        depends_on=[],
        linked_artifacts=[],
        source_refs=["telegram:message:4"],
    )
    ensure_dir(tmp_path / "context" / "workspaces" / workspace_id)
    ((tmp_path / "context" / "workspaces" / workspace_id) / "atlas.json").write_text(
        json.dumps(
            {
                "git_changes": {
                    "summary": {"risk_level": "medium", "changed_count": 3, "affected_count": 1, "changed_files": 3},
                    "changed_symbols": [{"filePath": "src/conversation_os/builder_behavior/engine.py"}],
                    "affected_processes": [{"name": "Meta agent follow-up flow"}],
                }
            }
        ),
        encoding="utf-8",
    )
    runner.save_builder_session_state(
        tmp_path / "meta-runtime",
        "telegram:11",
        {
            "phase": "execution",
            "candidate_objective": "make the notes app reply less verbose",
            "confirmed_objective": "make the notes app reply less verbose",
            "objective_confirmed": True,
            "pending_question": "",
            "acceptance_criteria": "Keep replies short while preserving action items.",
            "target_meta_state": "operate",
            "workspace_task_id": "SIP-301",
            "claim_status": "active",
        },
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    base_url = f"http://127.0.0.1:{server.server_address[1]}/api"
    runtime_root = tmp_path / "meta-runtime"
    try:
        assert runner._handle_meta_command(
            text="/workspace inner-world",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )[0] == 0
        code, reply = runner._handle_meta_command(
            text="continue",
            chat_id="11",
            update_id="11",
            user_id="42",
            message_id="2",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0
        assert "Suggested adjacent surfaces" in reply
        assert "src/conversation_os/builder_behavior/engine.py" in reply
        builder_state = runner.read_builder_session_state(runtime_root, "telegram:11")
        assert builder_state["inspection"]["gitnexus_used"] is True
    finally:
        server.shutdown()
        server.server_close()


def test_handle_meta_command_uses_workspace_service_for_tasks(tmp_path: Path) -> None:
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    workspace_id = "sol-frontend"
    store.write_json(
        store.manifest_path(workspace_id),
        {
            "workspace_id": workspace_id,
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    store.append_jsonl(
        store.work_item_events_path(workspace_id),
        {
            "event_id": "work-item-event-1",
            "workspace_id": workspace_id,
            "work_item_id": "MTC-001",
            "operation": "create",
            "timestamp": "2026-06-30T12:00:00+00:00",
            "actor": "agent",
            "payload": {
                "title": "Capture shell",
                "kind": "task",
                "status": "ready",
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
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    base_url = f"http://127.0.0.1:{server.server_address[1]}/api"
    try:
        code, reply = runner._handle_meta_command(
            text="/workspace sol-frontend",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0

        with mock.patch.object(runner, "render_workspace_tasks", side_effect=AssertionError("local path should not be used")):
            code, reply = runner._handle_meta_command(
                text="/tasks",
                chat_id="11",
                update_id="11",
                user_id="42",
                message_id="2",
                workspace_root=tmp_path / "meta-runtime",
                api_base="http://127.0.0.1:8422/api",
                workspace_api_base=base_url,
            )
        assert code == 0
        assert "MTC-001" in reply
    finally:
        server.shutdown()
        server.server_close()


def test_handle_meta_command_uses_workspace_service_for_claim_and_gate(tmp_path: Path) -> None:
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    workspace_id = "sol-frontend"
    store.write_json(
        store.manifest_path(workspace_id),
        {
            "workspace_id": workspace_id,
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    base_url = f"http://127.0.0.1:{server.server_address[1]}/api"
    try:
        code, reply = runner._handle_meta_command(
            text="/workspace sol-frontend",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0
        with mock.patch.object(runner, "claim_workspace_task", side_effect=AssertionError("local path should not be used")):
            code, reply = runner._handle_meta_command(
                text="/claim MTC-001 :: Harden the shell :: product/thought_capture_pwa/",
                chat_id="11",
                update_id="11",
                user_id="42",
                message_id="2",
                workspace_root=tmp_path / "meta-runtime",
                api_base="http://127.0.0.1:8422/api",
                workspace_api_base=base_url,
            )
        assert code == 0
        assert "Claimed MTC-001" in reply

        with mock.patch.object(runner, "evaluate_workspace_release_gate", side_effect=AssertionError("local path should not be used")):
            code, reply = runner._handle_meta_command(
                text="/gate",
                chat_id="11",
                update_id="12",
                user_id="42",
                message_id="3",
                workspace_root=tmp_path / "meta-runtime",
                api_base="http://127.0.0.1:8422/api",
                workspace_api_base=base_url,
            )
        assert code == 0
        assert "Release gate: blocked" in reply
        assert "active_claims" in reply
    finally:
        server.shutdown()
        server.server_close()


def test_handle_meta_command_completes_task_through_workspace_service(tmp_path: Path) -> None:
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    workspace_id = "sol-frontend"
    store.write_json(
        store.manifest_path(workspace_id),
        {"workspace_id": workspace_id, "artifact_roots": ["product/thought_capture_pwa/"]},
    )
    store.append_jsonl(
        store.work_item_events_path(workspace_id),
        {
            "event_id": "create-1",
            "workspace_id": workspace_id,
            "work_item_id": "MTC-001",
            "operation": "create",
            "timestamp": "2026-06-30T10:00:00+00:00",
            "actor": "agent",
            "payload": {"title": "Capture shell", "status": "in-progress"},
            "source_refs": [],
        },
    )
    record_workspace_test_run(
        tmp_path,
        workspace_id,
        task_id="MTC-001",
        agent_id="telegram:42",
        surface="telegram",
        session_id="telegram:11",
        test_name="mobile-smoke",
        result="passing",
        evidence_ref="artifacts/mobile-smoke.txt",
        store=store,
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    base_url = f"http://127.0.0.1:{server.server_address[1]}/api"
    try:
        code, _reply = runner._handle_meta_command(
            text="/workspace sol-frontend",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0

        code, reply = runner._handle_meta_command(
            text=(
                "/complete MTC-001 :: Capture shell shipped :: Mobile smoke evidence passes :: "
                "product/thought_capture_pwa/app.js :: pytest tests/mobile-smoke -q :: none known"
            ),
            chat_id="11",
            update_id="11",
            user_id="42",
            message_id="2",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0
        assert "Completed MTC-001" in reply
        assert "Evidence accepted" in reply
    finally:
        server.shutdown()
        server.server_close()


def test_telegram_task_lifecycle_is_immediately_visible_in_canonical_context(tmp_path: Path) -> None:
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {"workspace_id": "inner-world", "artifact_roots": ["src/"]},
    )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    base_url = f"http://127.0.0.1:{server.server_address[1]}/api"
    runtime_root = tmp_path / "meta-runtime"
    try:
        assert runner._handle_meta_command(
            text="/workspace inner-world",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )[0] == 0

        code, reply = runner._handle_meta_command(
            text=(
                "/task CTX-TG :: Telegram-created task :: Codex sees this task, provenance survives :: "
                "Capture work in canonical state"
            ),
            chat_id="11",
            update_id="11",
            user_id="42",
            message_id="2",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0
        assert "Created CTX-TG" in reply

        code, reply = runner._handle_meta_command(
            text="/context CTX-TG",
            chat_id="11",
            update_id="12",
            user_id="42",
            message_id="3",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0
        assert "Telegram-created task" in reply

        code, reply = runner._handle_meta_command(
            text="/task-update CTX-TG :: in-progress :: Codex has started work",
            chat_id="11",
            update_id="13",
            user_id="42",
            message_id="4",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0
        assert "in-progress" in reply

        blocker = record_workspace_blocker(
            tmp_path,
            "inner-world",
            task_id="CTX-TG",
            agent_id="codex",
            surface="codex",
            session_id="s-1",
            reason="Need Telegram clarification.",
            store=store,
        )
        code, reply = runner._handle_meta_command(
            text=f"/resolve {blocker['blocker_id']} :: Clarification supplied",
            chat_id="11",
            update_id="14",
            user_id="42",
            message_id="5",
            workspace_root=runtime_root,
            api_base="http://127.0.0.1:8422/api",
            workspace_api_base=base_url,
        )
        assert code == 0
        assert f"Resolved {blocker['blocker_id']}" in reply
    finally:
        server.shutdown()
        server.server_close()


def test_handle_meta_command_supports_claim_and_handoff(tmp_path: Path) -> None:
    workspace_id = "sol-frontend"
    workspace_dir = tmp_path / "memory" / "workspaces" / workspace_id
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "manifest.json").write_text(
        json.dumps(
            {
                "workspace_id": workspace_id,
                "artifact_roots": ["product/thought_capture_pwa/"],
                "objectives": ["Ship the PWA."],
            }
        ),
        encoding="utf-8",
    )

    with mock.patch.object(runner, "repo_root_from", return_value=tmp_path):
        code, reply = runner._handle_meta_command(
            text="/workspace sol-frontend",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
        )
        assert code == 0
        assert "Workspace: sol-frontend" in reply

        code, reply = runner._handle_meta_command(
            text="/claim MTC-001 :: Harden the shell :: product/thought_capture_pwa/",
            chat_id="11",
            update_id="11",
            user_id="42",
            message_id="2",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
        )
        assert code == 0
        assert "Claimed MTC-001" in reply
        assert "product/thought_capture_pwa/" in reply

        code, reply = runner._handle_meta_command(
            text="/handoff MTC-001 :: Implementation complete :: Ready for verification :: Run smoke suite",
            chat_id="11",
            update_id="12",
            user_id="42",
            message_id="3",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
        )
        assert code == 0
        assert "Handed off MTC-001" in reply
        assert "Run smoke suite" in reply


def test_handle_meta_command_supports_decision_and_verify(tmp_path: Path) -> None:
    workspace_id = "sol-frontend"
    workspace_dir = tmp_path / "memory" / "workspaces" / workspace_id
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "manifest.json").write_text(
        json.dumps(
            {
                "workspace_id": workspace_id,
                "artifact_roots": ["product/thought_capture_pwa/"],
                "objectives": ["Ship the PWA."],
            }
        ),
        encoding="utf-8",
    )

    with mock.patch.object(runner, "repo_root_from", return_value=tmp_path):
        code, reply = runner._handle_meta_command(
            text="/workspace sol-frontend",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
        )
        assert code == 0

        code, reply = runner._handle_meta_command(
            text="/decision MTC-001 :: Keep note/meta toggle in current shell language. :: Preserves continuity and avoids extra UI churn.",
            chat_id="11",
            update_id="11",
            user_id="42",
            message_id="2",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
        )
        assert code == 0
        assert "Decision recorded for MTC-001" in reply

        code, reply = runner._handle_meta_command(
            text="/verify MTC-001 :: mobile-smoke :: passing :: artifacts/mobile-smoke.txt :: Shell loads and toggle responds.",
            chat_id="11",
            update_id="12",
            user_id="42",
            message_id="3",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
        )
        assert code == 0
        assert "Verification recorded for MTC-001" in reply
        assert "mobile-smoke" in reply


def test_handle_meta_command_supports_blocker_and_gate(tmp_path: Path) -> None:
    workspace_id = "sol-frontend"
    workspace_dir = tmp_path / "memory" / "workspaces" / workspace_id
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "manifest.json").write_text(
        json.dumps(
            {
                "workspace_id": workspace_id,
                "artifact_roots": ["product/thought_capture_pwa/"],
                "objectives": ["Ship the PWA."],
            }
        ),
        encoding="utf-8",
    )
    (workspace_dir / "work_item_events.jsonl").write_text(
        json.dumps(
            {
                "event_id": "work-item-event-1",
                "workspace_id": workspace_id,
                "work_item_id": "MTC-001",
                "operation": "create",
                "timestamp": "2026-06-30T12:00:00+00:00",
                "actor": "agent",
                "payload": {
                    "title": "Capture shell",
                    "kind": "task",
                    "status": "done",
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
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with mock.patch.object(runner, "repo_root_from", return_value=tmp_path):
        code, _reply = runner._handle_meta_command(
            text="/workspace sol-frontend",
            chat_id="11",
            update_id="10",
            user_id="42",
            message_id="1",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
        )
        assert code == 0

        code, reply = runner._handle_meta_command(
            text="/blocker MTC-001 :: Mobile shell collapses on Safari reload. :: Inspect hydration path.",
            chat_id="11",
            update_id="11",
            user_id="42",
            message_id="2",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
        )
        assert code == 0
        assert "Blocker recorded for MTC-001" in reply

        code, reply = runner._handle_meta_command(
            text="/gate",
            chat_id="11",
            update_id="12",
            user_id="42",
            message_id="3",
            workspace_root=tmp_path / "meta-runtime",
            api_base="http://127.0.0.1:8422/api",
        )
        assert code == 0
        assert "Release gate: blocked" in reply
        assert "active_blockers" in reply


def test_handle_meta_command_deploy_reports_workspace_gate_block(tmp_path: Path) -> None:
    workspace_root = tmp_path / "meta-runtime"
    paths = runner.create_workspace_paths(workspace_root)
    paths["approval_state"].parent.mkdir(parents=True, exist_ok=True)
    paths["approval_state"].write_text(
        json.dumps(
            {
                "packet_id": "sip-123",
                "release_id": "inner-world-test",
                "actor": "telegram:42",
                "decision": "approved",
            }
        ),
        encoding="utf-8",
    )

    with (
        mock.patch.object(runner, "repo_root_from", return_value=tmp_path),
        mock.patch.object(
            runner,
            "evaluate_release_readiness",
            return_value={
                "release_id": "inner-world-test",
                "status": "blocked",
                "missing": ["workspace_gate"],
                "workspace_id": "sol-frontend",
                "workspace_gate": {"status": "blocked", "reasons": ["active_blockers"]},
            },
        ),
    ):
        code, reply = runner._handle_meta_command(
            text="/deploy inner-world-test",
            chat_id="11",
            update_id="12",
            user_id="42",
            message_id="3",
            workspace_root=workspace_root,
            api_base="http://127.0.0.1:8422/api",
        )

    assert code == 1
    assert "Release inner-world-test is blocked." in reply
    assert "workspace_gate" in reply
