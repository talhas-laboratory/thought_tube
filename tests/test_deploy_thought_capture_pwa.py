from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "tools" / "deploy_thought_capture_pwa_to_openclaw.py"
sys.path.append(str(SCRIPT_PATH.parent))
SPEC = importlib.util.spec_from_file_location("deploy_thought_capture_pwa", SCRIPT_PATH)
assert SPEC and SPEC.loader
deploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy)


def test_sync_items_include_bridge_runtime_config() -> None:
    assert "product/inner_world_v1/config/runtime.json" in deploy.SYNC_ITEMS


def test_merge_inner_world_env_generates_capture_credential() -> None:
    values = {
        "INNER_WORLD_MOBILE_HOSTNAME": "mobile.example.test",
        "INNER_WORLD_MOBILE_PASSWORD": "mobile-pass",
        "INNER_WORLD_CAPTURE_USERNAME": "",
        "INNER_WORLD_CAPTURE_PASSWORD": "",
    }

    with (
        mock.patch.object(deploy, "read_remote_env_var", side_effect=lambda _remote, name: values[name]),
        mock.patch.object(deploy.secrets, "token_urlsafe", return_value="generated-capture-pass"),
        mock.patch.object(deploy, "write_inner_world_env") as write_env,
    ):
        username, password = deploy.merge_inner_world_env(
            "openclaw",
            capture_hostname="notes.example.test",
        )

    assert username == "capture"
    assert password == "generated-capture-pass"
    write_env.assert_called_once_with(
        "openclaw",
        capture_hostname="notes.example.test",
        capture_username="capture",
        capture_password="generated-capture-pass",
        mobile_hostname="mobile.example.test",
        mobile_password="mobile-pass",
    )


def test_write_inner_world_env_includes_capture_auth() -> None:
    with mock.patch.object(deploy.deploy_common, "run") as run:
        deploy.write_inner_world_env(
            "openclaw",
            capture_hostname="notes.example.test",
            capture_username="capture",
            capture_password="capture-pass",
        )

    payload = run.call_args.kwargs["input_text"]
    assert "INNER_WORLD_CAPTURE_HOSTNAME=notes.example.test" in payload
    assert "INNER_WORLD_CAPTURE_USERNAME=capture" in payload
    assert "INNER_WORLD_CAPTURE_PASSWORD=capture-pass" in payload
    assert "INNER_WORLD_CHAT_BACKEND=openclaw_gateway" in payload
    assert "INNER_WORLD_BRIDGE_ENABLED=true" in payload
    assert "INNER_WORLD_BRIDGE_EXECUTION_MODE=agent" in payload
    assert "INNER_WORLD_BRIDGE_AGENT=thought_tube_router" in payload


def test_provision_bridge_agent_runs_remote_tool() -> None:
    with mock.patch.object(deploy.deploy_common, "run") as run:
        deploy.provision_bridge_agent("openclaw", "/srv/inner-space")

    command = run.call_args.args[0]
    assert command[:2] == ["ssh", "openclaw"]
    assert "tools/provision_bridge_openclaw_agent.py --json" in command[-1]


def test_verify_checks_rejection_and_authenticated_routes() -> None:
    with mock.patch.object(deploy.deploy_common, "run") as run:
        deploy.verify("openclaw", "notes.example.test")

    command = run.call_args.args[0][-1]
    assert "unauthenticated_status" in command
    assert '"$INNER_WORLD_CAPTURE_USERNAME:$INNER_WORLD_CAPTURE_PASSWORD"' in command
    assert "https://notes.example.test/" in command
    assert "/api/mobile/capture/session" in command
    assert "-d '{}'" in command
    assert "--retry 5" in command
    assert "--retry-all-errors" in command
