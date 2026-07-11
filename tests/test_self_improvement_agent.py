from __future__ import annotations

from unittest.mock import Mock

from conversation_os.self_improvement_agent import draft_self_improvement_packet


def test_agent_packet_accepts_valid_json(monkeypatch) -> None:
    completed = Mock()
    completed.returncode = 0
    completed.stdout = '{"schema_version":"1.0","packet_id":"sip-agent","status":"proposed","source":{"session_id":"s","turn_id":"t","raw_user_signal":"x","provenance_refs":[]},"classification":{"domain":"ui_ux","risk":"medium","affected_layers":[],"change_type":"system_feedback"},"problem":{"observed":"x","expected":"","evidence":[]},"proposal":{"summary":"","files_or_configs":[],"runtime_effect":"","alternatives_considered":[]},"gates":{"required_tests":["pwa_tests"],"required_smokes":[],"required_reviews":[],"rollback_required":false},"release":{"version_bump":"patch","deploy_allowed":false,"approval_required":true,"rollback_plan":""}}'
    completed.stderr = ""
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: completed)

    packet = draft_self_improvement_packet("ui is jumpy", "s", "t", use_agent=True)

    assert packet["packet_id"] == "sip-agent"
    assert packet["classification"]["domain"] == "ui_ux"


def test_agent_packet_falls_back_on_invalid_json(monkeypatch) -> None:
    completed = Mock()
    completed.returncode = 0
    completed.stdout = "I think you should improve the bridge."
    completed.stderr = ""
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: completed)

    packet = draft_self_improvement_packet("bridge leaked context", "s", "t", use_agent=True)

    assert packet["packet_id"].startswith("sip-")
    assert packet["classification"]["domain"] == "bridge_work"
    assert packet["attributes"]["fallback_reason"] == "invalid_agent_packet"
