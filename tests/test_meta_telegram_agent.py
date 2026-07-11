from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

from conversation_os.meta_telegram_agent import (
    apply_packet_decision,
    build_meta_chat_payload,
    build_meta_telegram_reply,
    classify_meta_command,
    execute_release_deploy,
    extract_telegram_message,
    create_workspace_paths,
    evaluate_release_readiness,
    parse_release_approval,
    parse_workspace_complete,
    parse_workspace_task_create,
    parse_workspace_task_update,
    parse_workspace_blocker_resolution,
    persist_meta_packet,
    read_telegram_offset,
    render_rollback_status_reply,
    render_meta_status_reply,
    release_is_approved,
    save_telegram_offset,
    triage_packet_to_workboard,
)
from conversation_os.workspace_service import serve_workspace_service
from conversation_os.workspace_store import SQLiteWorkspaceStore


ROOT = Path(__file__).resolve().parents[1]


def test_inner_space_meta_agent_config_is_proposal_only() -> None:
    path = ROOT / "product" / "inner_world_v1" / "config" / "agent_configs" / "inner_space_meta.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["agent_id"] == "inner_space_meta"
    assert payload["default_authority"] == "propose"
    assert payload["production_deploy_authority"] == "blocked_by_default"
    assert payload["requires_release_gate"] is True
    assert payload["requires_rollback_plan"] is True


def test_classify_meta_command_routes_discuss_and_operate_modes() -> None:
    discuss = classify_meta_command("/meta should we tighten the bridge context policy?")
    assert discuss.command == "meta"
    assert discuss.meta_state == "discuss"
    assert discuss.text == "should we tighten the bridge context policy?"

    operate = classify_meta_command("/change shorten capture replies and add tests")
    assert operate.command == "change"
    assert operate.meta_state == "operate"
    assert operate.text == "shorten capture replies and add tests"

    complete = classify_meta_command("/complete CTX-004 :: summary")
    assert complete.command == "complete"
    assert complete.meta_state == "operate"


def test_parse_workspace_complete_preserves_required_evidence_lists() -> None:
    packet = parse_workspace_complete(
        "CTX-004 :: Contract complete :: Gates prevent false completion :: "
        "src/a.py, tests/test_a.py :: pytest tests/test_a.py -q ;; python3 -m py_compile src/a.py :: none known"
    )

    assert packet == {
        "task_id": "CTX-004",
        "summary": "Contract complete",
        "reasoning": "Gates prevent false completion",
        "files_touched": ["src/a.py", "tests/test_a.py"],
        "commands_run": ["pytest tests/test_a.py -q", "python3 -m py_compile src/a.py"],
        "residual_risks": ["none known"],
    }


def test_parse_workspace_task_lifecycle_commands() -> None:
    assert parse_workspace_task_create(
        "CTX-007 :: Cross-agent context :: Telegram task is visible, sources are preserved :: Coordinate shared state"
    ) == {
        "task_id": "CTX-007",
        "title": "Cross-agent context",
        "acceptance_criteria": ["Telegram task is visible", "sources are preserved"],
        "reasoning": "Coordinate shared state",
        "parent_task_id": "",
    }
    assert parse_workspace_task_create(
        "CTX-008 :: Child context :: Child is independently visible :: Keep the parent open :: CTX-007"
    )["parent_task_id"] == "CTX-007"
    assert parse_workspace_task_update("CTX-007 :: in-progress :: Work has started") == {
        "task_id": "CTX-007",
        "status": "in-progress",
        "reasoning": "Work has started",
    }
    assert parse_workspace_blocker_resolution("blocker-1 :: Clarification supplied") == {
        "blocker_id": "blocker-1",
        "reasoning": "Clarification supplied",
    }


def test_build_meta_chat_payload_uses_telegram_ids() -> None:
    payload = build_meta_chat_payload(
        text="fix the iPhone layout",
        meta_state="operate",
        chat_id="12345",
        update_id="67890",
        user_id="42",
        message_id="55",
    )
    assert payload["surface_mode"] == "meta"
    assert payload["meta_state"] == "operate"
    assert payload["session_id"] == "telegram:12345"
    assert payload["turn_id"] == "telegram:67890"
    assert payload["source"]["channel"] == "telegram"


def test_build_meta_telegram_reply_keeps_status_compact() -> None:
    reply = build_meta_telegram_reply(
        {
            "assistant_text": "This is ready to move into governed change work.",
            "interpretation": {
                "meta_state": "operate",
                "domain": "ui_ux",
                "risk": "medium",
                "should_create_packet": True,
            },
            "packet": {"packet_id": "sip-123"},
        }
    )
    assert "This is ready to move into governed change work." in reply
    assert "Mode: operate" in reply
    assert "Domain: ui_ux" in reply
    assert "Risk: medium" in reply
    assert "Packet: sip-123" in reply


def test_build_meta_telegram_reply_uses_conversational_builder_format() -> None:
    reply = build_meta_telegram_reply(
        {
            "assistant_text": "I think the objective is: shorten the notes replies. Is that right?",
            "interpretation": {
                "builder_phase": "objective_confirmation",
                "meta_state": "operate",
                "domain": "agent_behavior",
                "risk": "high",
            },
            "packet": {},
        }
    )
    assert reply == "I think the objective is: shorten the notes replies. Is that right?"


def test_persist_meta_packet_updates_active_status(tmp_path: Path) -> None:
    packet = {
        "packet_id": "sip-123",
        "classification": {"domain": "ui_ux", "risk": "medium"},
        "proposal": {"summary": "Shorten capture replies."},
    }
    paths = create_workspace_paths(tmp_path)
    persist_meta_packet(tmp_path, packet, status="proposed")
    saved = json.loads((paths["packets_proposed"] / "sip-123.json").read_text(encoding="utf-8"))
    active = json.loads(paths["active_packets"].read_text(encoding="utf-8"))
    assert saved["status"] == "proposed"
    assert active["packets"][0]["packet_id"] == "sip-123"
    assert active["packets"][0]["status"] == "proposed"


def test_apply_packet_decision_moves_packet_and_records_actor(tmp_path: Path) -> None:
    packet = {
        "packet_id": "sip-123",
        "classification": {"domain": "ui_ux", "risk": "medium"},
        "proposal": {"summary": "Shorten capture replies."},
    }
    paths = create_workspace_paths(tmp_path)
    persist_meta_packet(tmp_path, packet, status="proposed")
    updated = apply_packet_decision(tmp_path, "sip-123", decision="approved", actor="telegram:42")
    assert updated["status"] == "approved"
    assert updated["approval"]["actor"] == "telegram:42"
    assert not (paths["packets_proposed"] / "sip-123.json").exists()
    assert (paths["packets_approved"] / "sip-123.json").exists()


def test_render_meta_status_reply_lists_active_packets(tmp_path: Path) -> None:
    persist_meta_packet(
        tmp_path,
        {
            "packet_id": "sip-123",
            "classification": {"domain": "ui_ux", "risk": "medium"},
            "proposal": {"summary": "Shorten capture replies."},
        },
        status="proposed",
    )
    status = render_meta_status_reply(tmp_path)
    assert "1 active packet" in status
    assert "sip-123" in status
    assert "ui_ux" in status


def test_triage_packet_to_workboard_creates_inbox_copy_and_task(tmp_path: Path) -> None:
    packet = {
        "packet_id": "sip-123",
        "classification": {"domain": "ui_ux", "risk": "medium"},
        "problem": {"observed": "Replies are too long."},
        "proposal": {"summary": "Shorten capture replies."},
        "gates": {"required_tests": ["pwa_tests", "build"]},
    }
    task = triage_packet_to_workboard(tmp_path, packet, actor="telegram:42")
    inbox_copy = tmp_path / "docs" / "workboards" / "inner-space-agent-ops" / "inbox" / "sip-123.json"
    task_file = tmp_path / "docs" / "workboards" / "inner-space-agent-ops" / "tasks" / "SIP-123.md"
    updates_file = tmp_path / "docs" / "workboards" / "inner-space-agent-ops" / "UPDATES.jsonl"
    assert task["task_id"] == "SIP-123"
    assert inbox_copy.exists()
    assert task_file.exists()
    assert updates_file.exists()
    assert "Shorten capture replies." in task_file.read_text(encoding="utf-8")


def test_evaluate_release_readiness_blocks_missing_gate_artifacts(tmp_path: Path) -> None:
    report = evaluate_release_readiness(tmp_path, "inner-world-test")
    assert report["status"] == "blocked"
    assert "gate_report" in report["missing"]
    assert "rollback_plan" in report["missing"]


def test_evaluate_release_readiness_includes_workspace_gate_status(tmp_path: Path) -> None:
    release_dir = tmp_path / "product" / "inner_world_v1" / "releases" / "inner-world-test"
    release_dir.mkdir(parents=True)
    (release_dir / "manifest.json").write_text(
        json.dumps({"workspace_id": "sol-frontend"}),
        encoding="utf-8",
    )
    (release_dir / "gate_report.json").write_text('{"status":"passed","missing_checks":[]}\n', encoding="utf-8")
    (release_dir / "rollback_plan.json").write_text('{"target_release_id":"inner-world-prev","steps":["restore_manifest"]}\n', encoding="utf-8")

    with mock.patch("conversation_os.meta_telegram_agent.evaluate_workspace_release_gate", return_value={"status": "blocked", "reasons": ["active_blockers"]}):
        report = evaluate_release_readiness(tmp_path, "inner-world-test")

    assert report["status"] == "blocked"
    assert report["workspace_id"] == "sol-frontend"
    assert report["workspace_gate"]["status"] == "blocked"
    assert "workspace_gate" in report["missing"]


def test_evaluate_release_readiness_can_use_workspace_service(tmp_path: Path) -> None:
    release_dir = tmp_path / "product" / "inner_world_v1" / "releases" / "inner-world-test"
    release_dir.mkdir(parents=True)
    (release_dir / "manifest.json").write_text(
        json.dumps({"workspace_id": "sol-frontend"}),
        encoding="utf-8",
    )
    (release_dir / "gate_report.json").write_text('{"status":"passed","missing_checks":[]}\n', encoding="utf-8")
    (release_dir / "rollback_plan.json").write_text('{"target_release_id":"inner-world-prev","steps":["restore_manifest"]}\n', encoding="utf-8")

    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("sol-frontend"),
        {
            "workspace_id": "sol-frontend",
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )
    store.append_jsonl(
        store.claims_path("sol-frontend"),
        {
            "claim_id": "claim-1",
            "workspace_id": "sol-frontend",
            "task_id": "MTC-001",
            "actor": {"agent_id": "telegram:42", "surface": "telegram", "session_id": "telegram:11"},
            "intent": "Harden shell",
            "claimed_paths": ["product/thought_capture_pwa/"],
                "status": "active",
                "created_at": "2026-06-30T12:00:00+00:00",
                "updated_at": "2026-06-30T12:00:00+00:00",
                "expires_at": "2026-08-01T12:00:00+00:00",
            },
        )
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        base_url = f"http://127.0.0.1:{server.server_address[1]}/api"
        with mock.patch("conversation_os.meta_telegram_agent.evaluate_workspace_release_gate", side_effect=AssertionError("local gate should not be used")):
            report = evaluate_release_readiness(tmp_path, "inner-world-test", workspace_api_base=base_url)
    finally:
        server.shutdown()
        server.server_close()

    assert report["status"] == "blocked"
    assert report["workspace_gate"]["status"] == "blocked"
    assert "active_claims" in report["workspace_gate"]["reasons"]


def test_execute_release_deploy_blocks_when_workspace_gate_is_not_ready(tmp_path: Path) -> None:
    release_dir = tmp_path / "product" / "inner_world_v1" / "releases" / "inner-world-test"
    release_dir.mkdir(parents=True)
    (release_dir / "manifest.json").write_text(
        json.dumps({"workspace_id": "sol-frontend"}),
        encoding="utf-8",
    )
    (release_dir / "gate_report.json").write_text('{"status":"passed","missing_checks":[]}\n', encoding="utf-8")
    (release_dir / "rollback_plan.json").write_text('{"target_release_id":"inner-world-prev","steps":["restore_manifest"]}\n', encoding="utf-8")

    with mock.patch("conversation_os.meta_telegram_agent.evaluate_workspace_release_gate", return_value={"status": "blocked", "reasons": ["missing_verification"]}):
        result = execute_release_deploy(tmp_path, tmp_path / "workspace", "inner-world-test")

    assert result["status"] == "blocked"
    assert result["reason"] == "workspace_gate_blocked"
    assert result["workspace_id"] == "sol-frontend"


def test_execute_release_deploy_runs_gated_runtime_and_capture_deploys(tmp_path: Path) -> None:
    release_dir = tmp_path / "product" / "inner_world_v1" / "releases" / "inner-world-test"
    release_dir.mkdir(parents=True)
    workspace_dir = tmp_path / "memory" / "workspaces" / "sol-frontend"
    workspace_dir.mkdir(parents=True)
    (workspace_dir / "manifest.json").write_text(
        json.dumps(
            {
                "workspace_id": "sol-frontend",
                "label": "SOL Frontend",
                "artifact_roots": ["product/thought_capture_pwa/"],
                "objectives": ["Ship the PWA."],
                "workboard_ref": "docs/workboards/sol-frontend/README.md",
            }
        ),
        encoding="utf-8",
    )
    (release_dir / "manifest.json").write_text(json.dumps({"workspace_id": "sol-frontend"}), encoding="utf-8")
    (release_dir / "gate_report.json").write_text('{"status":"passed","missing_checks":[]}\n', encoding="utf-8")
    (release_dir / "rollback_plan.json").write_text('{"target_release_id":"inner-world-prev","steps":["restore_manifest"]}\n', encoding="utf-8")

    completed = mock.Mock(returncode=0, stdout="ok", stderr="")
    with (
        mock.patch("conversation_os.meta_telegram_agent.subprocess.run", return_value=completed) as run,
        mock.patch("conversation_os.meta_telegram_agent.evaluate_workspace_release_gate", return_value={"status": "ready", "reasons": []}),
    ):
        result = execute_release_deploy(tmp_path, tmp_path / "workspace", "inner-world-test")

    assert result["status"] == "deployed"
    assert run.call_count == 2
    commands = [call.args[0] for call in run.call_args_list]
    assert commands[0][:2] == ["python3", "tools/deploy_inner_world_to_openclaw.py"]
    assert commands[1][:2] == ["python3", "tools/deploy_thought_capture_pwa_to_openclaw.py"]
    smoke = json.loads((release_dir / "post_deploy_smoke.json").read_text(encoding="utf-8"))
    assert smoke["status"] == "passed"
    state = json.loads((tmp_path / "workspace" / "state" / "deployment_state.json").read_text(encoding="utf-8"))
    assert state["status"] == "deployed"
    activity_path = workspace_dir / "activity_events.jsonl"
    assert activity_path.exists()
    activity_rows = [json.loads(line) for line in activity_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert activity_rows[-1]["event_type"] == "deployed"
    assert activity_rows[-1]["metadata"]["release_id"] == "inner-world-test"
    releases_projection = tmp_path / "docs" / "workboards" / "sol-frontend" / "RELEASES.generated.md"
    assert releases_projection.exists()
    assert "inner-world-test" in releases_projection.read_text(encoding="utf-8")


def test_execute_release_deploy_records_failure_state(tmp_path: Path) -> None:
    release_dir = tmp_path / "product" / "inner_world_v1" / "releases" / "inner-world-test"
    release_dir.mkdir(parents=True)
    (release_dir / "manifest.json").write_text("{}", encoding="utf-8")
    (release_dir / "gate_report.json").write_text('{"status":"passed","missing_checks":[]}\n', encoding="utf-8")
    (release_dir / "rollback_plan.json").write_text('{"target_release_id":"inner-world-prev","steps":["restore_manifest"]}\n', encoding="utf-8")

    responses = [
        mock.Mock(returncode=0, stdout="runtime ok", stderr=""),
        mock.Mock(returncode=1, stdout="", stderr="capture failed"),
    ]
    with mock.patch("conversation_os.meta_telegram_agent.subprocess.run", side_effect=responses):
        result = execute_release_deploy(tmp_path, tmp_path / "workspace", "inner-world-test")

    assert result["status"] == "failed"
    assert result["reason"] == "deploy_command_failed"
    state = json.loads((tmp_path / "workspace" / "state" / "deployment_state.json").read_text(encoding="utf-8"))
    assert state["status"] == "failed"


def test_render_rollback_status_reply_reports_dry_run_plan(tmp_path: Path) -> None:
    release_dir = tmp_path / "product" / "inner_world_v1" / "releases" / "inner-world-test"
    release_dir.mkdir(parents=True)
    (release_dir / "manifest.json").write_text(
        json.dumps({"rollback": {"previous_release_id": "inner-world-prev"}}),
        encoding="utf-8",
    )
    (release_dir / "rollback_plan.json").write_text(
        json.dumps({"target_release_id": "inner-world-prev", "steps": ["restore_manifest", "restart_inner_world_service"]}),
        encoding="utf-8",
    )

    reply = render_rollback_status_reply(tmp_path, "inner-world-test")
    assert "Rollback plan for inner-world-test is ready as a dry run." in reply
    assert "Target: inner-world-prev" in reply
    assert "Execution: rollback executor not wired yet" in reply


def test_parse_release_approval_extracts_packet_and_release() -> None:
    approval = parse_release_approval("sip-123 for release inner-world-20260630")
    assert approval == {"packet_id": "sip-123", "release_id": "inner-world-20260630"}


def test_release_is_approved_requires_matching_release_id(tmp_path: Path) -> None:
    paths = create_workspace_paths(tmp_path)
    paths["approval_state"].parent.mkdir(parents=True, exist_ok=True)
    paths["approval_state"].write_text(
        json.dumps(
            {
                "packet_id": "sip-123",
                "release_id": "inner-world-20260630",
                "actor": "telegram:42",
                "decision": "approved",
            }
        ),
        encoding="utf-8",
    )
    assert release_is_approved(tmp_path, "inner-world-20260630") is True
    assert release_is_approved(tmp_path, "inner-world-20260701") is False


def test_telegram_offset_roundtrip(tmp_path: Path) -> None:
    assert read_telegram_offset(tmp_path) == 0
    save_telegram_offset(tmp_path, 123)
    assert read_telegram_offset(tmp_path) == 123


def test_extract_telegram_message_filters_to_allowlisted_text_messages() -> None:
    update = {
        "update_id": 77,
        "message": {
            "message_id": 9,
            "text": "/meta tighten the bridge",
            "chat": {"id": 11},
            "from": {"id": 42},
        },
    }
    extracted = extract_telegram_message(update, allowed_user_ids={42})
    assert extracted is not None
    assert extracted["text"] == "/meta tighten the bridge"
    assert extracted["chat_id"] == "11"
    assert extracted["user_id"] == "42"

    assert extract_telegram_message(update, allowed_user_ids={7}) is None
