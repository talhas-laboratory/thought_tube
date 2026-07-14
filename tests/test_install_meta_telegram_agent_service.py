from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "tools" / "install_meta_telegram_agent_service.py"
sys.path.append(str(SCRIPT_PATH.parent))
SPEC = importlib.util.spec_from_file_location("install_meta_telegram_agent_service", SCRIPT_PATH)
assert SPEC and SPEC.loader
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


def test_env_lines_include_required_runtime_keys(tmp_path: Path) -> None:
    lines = installer._env_lines(
        workspace_root=tmp_path / "runtime",
        api_base="http://127.0.0.1:8422/api",
    )
    payload = "\n".join(lines)
    assert "INNER_SPACE_META_WORKSPACE_ROOT=" in payload
    assert "INNER_WORLD_API_BASE=http://127.0.0.1:8422/api" in payload
    assert "INNER_SPACE_META_POLL_INTERVAL_SECONDS=2.0" in payload
    assert "TELEGRAM_BOT_TOKEN=" in payload
    assert "TELEGRAM_ALLOWED_USER_IDS=" in payload


def test_launch_agent_plist_runs_poll_forever(tmp_path: Path) -> None:
    env_path = tmp_path / "inner-space-meta.env"
    plist = installer._launch_agent_plist(
        env_path=env_path,
        python_bin="python3",
        poll_interval_seconds=3.5,
    )
    assert "run_telegram_meta_agent_daemon.sh" in plist
    assert "<key>INNER_SPACE_META_POLL_INTERVAL_SECONDS</key>" in plist
    assert "<string>3.5</string>" in plist
    assert str(env_path) in plist


def test_env_has_required_secrets_requires_both_values(tmp_path: Path) -> None:
    env_path = tmp_path / "inner-space-meta.env"
    env_path.write_text("TELEGRAM_BOT_TOKEN=\nTELEGRAM_ALLOWED_USER_IDS=\n", encoding="utf-8")
    assert installer.env_has_required_secrets(env_path) is False

    env_path.write_text("TELEGRAM_BOT_TOKEN=abc\nTELEGRAM_ALLOWED_USER_IDS=42\n", encoding="utf-8")
    assert installer.env_has_required_secrets(env_path) is True
