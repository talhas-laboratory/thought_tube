from __future__ import annotations

import json
from pathlib import Path

from conversation_os.self_improvement import (
    classify_feedback_domain,
    default_packet_for_feedback,
    interpret_self_improvement_turn,
    validate_system_improvement_packet,
)


ROOT = Path(__file__).resolve().parents[1]


def test_self_improvement_config_declares_required_domains() -> None:
    path = ROOT / "product" / "inner_world_v1" / "config" / "self_improvement.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    domains = {item["domain"] for item in payload["feedback_domains"]}
    assert domains == {
        "ui_ux",
        "agent_behavior",
        "backend_setup",
        "tool_creation",
        "thought_pipeline_config",
        "bridge_work",
        "deployment_release",
    }


def test_runtime_self_improvement_is_proposal_only_by_default() -> None:
    path = ROOT / "product" / "inner_world_v1" / "config" / "runtime.sample.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    config = payload["self_improvement"]
    assert config["enabled"] is False
    assert config["agent"] == "thought_tube_self_improve"
    assert config["default_authority"] == "propose"
    assert config["allow_production_deploy"] is False
    assert config["agent_config_path"] == "product/inner_world_v1/config/agent_configs/thought_tube_self_improve.json"


def test_self_improvement_config_stays_separate_from_telegram_meta_agent() -> None:
    runtime_path = ROOT / "product" / "inner_world_v1" / "config" / "runtime.sample.json"
    runtime_payload = json.loads(runtime_path.read_text(encoding="utf-8"))
    config = runtime_payload["self_improvement"]
    assert config["agent"] == "thought_tube_self_improve"
    assert config["enabled"] is False


def test_meta_agent_identity_config_declares_conversational_builder_profile() -> None:
    path = ROOT / "product" / "inner_world_v1" / "config" / "agent_configs" / "inner_space_meta.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    profile = payload["conversation_profile"]
    assert payload["agent_id"] == "inner_space_meta"
    assert profile["style"] == "natural_collaborative_builder"
    assert profile["goal_extraction"] == "implicit_until_scope_is_stable"
    assert profile["soft_reset_on_greeting"] is True


def test_classify_bridge_feedback() -> None:
    packet = default_packet_for_feedback(
        raw_text="The bridge pulled too much context and leaked sidecar material.",
        session_id="session-1",
        turn_id="turn-1",
    )
    assert packet["classification"]["domain"] == "bridge_work"
    assert packet["classification"]["risk"] == "high"
    assert "context_policy_tests" in packet["gates"]["required_tests"]


def test_classify_ui_feedback() -> None:
    assert classify_feedback_domain("The mobile capture UI jumps when the answer streams.") == "ui_ux"


def test_backend_feedback_requires_service_smoke_and_rollback() -> None:
    packet = default_packet_for_feedback("backend auth deploy broke the API", "s", "t")
    assert packet["classification"]["domain"] == "backend_setup"
    assert "service_smoke" in packet["gates"]["required_tests"]
    assert packet["gates"]["rollback_required"] is True


def test_agent_behavior_feedback_requires_examples_and_trace_review() -> None:
    packet = default_packet_for_feedback("the assistant tone is too verbose and ignores context", "s", "t")
    assert packet["classification"]["domain"] == "agent_behavior"
    assert "golden_conversation_examples" in packet["gates"]["required_tests"]
    assert "bridge_trace_review" in packet["gates"]["required_tests"]


def test_deployment_feedback_is_critical() -> None:
    packet = default_packet_for_feedback("we need rollback before production deploy", "s", "t")
    assert packet["classification"]["domain"] == "deployment_release"
    assert packet["classification"]["risk"] == "critical"
    assert "rollback_dry_run" in packet["gates"]["required_tests"]


def test_packet_validation_rejects_deploy_allowed_without_approval() -> None:
    packet = default_packet_for_feedback(
        raw_text="Deploy this runtime config change.",
        session_id="session-1",
        turn_id="turn-1",
    )
    packet["release"]["deploy_allowed"] = True
    packet["release"]["approval_required"] = False
    errors = validate_system_improvement_packet(packet)
    assert "deploy_allowed requires approval_required" in errors


def test_interpret_meta_discuss_turn_stays_provisional() -> None:
    interpretation = interpret_self_improvement_turn(
        "Should we change how the bridge handles sidecar context?",
        requested_mode="meta",
        requested_meta_state="discuss",
    )
    assert interpretation["surface_mode"] == "meta"
    assert interpretation["meta_state"] == "discuss"
    assert interpretation["domain"] == "bridge_work"
    assert interpretation["should_create_packet"] is False


def test_interpret_meta_operate_turn_becomes_actionable() -> None:
    interpretation = interpret_self_improvement_turn(
        "Implement rollback and gate-controlled deploy before production release.",
        requested_mode="meta",
        requested_meta_state="operate",
    )
    assert interpretation["surface_mode"] == "meta"
    assert interpretation["meta_state"] == "operate"
    assert interpretation["domain"] == "deployment_release"
    assert interpretation["should_create_packet"] is True


def test_interpret_note_mode_suppresses_self_improvement_actions() -> None:
    interpretation = interpret_self_improvement_turn(
        "I need to think through this idea without changing the product yet.",
        requested_mode="note",
        requested_meta_state="operate",
    )
    assert interpretation["surface_mode"] == "note"
    assert interpretation["meta_state"] == "discuss"
    assert interpretation["should_create_packet"] is False
