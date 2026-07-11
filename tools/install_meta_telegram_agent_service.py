#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import platform
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LABEL = "com.inner-space.meta-telegram"
DEFAULT_WORKSPACE_ROOT = (
    ROOT / "product" / "inner_world_v1" / "meta_agent" / "state" / "runtime"
)


def _env_path() -> Path:
    return Path.home() / ".config" / "inner-space-meta.env"


def _launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _env_lines(*, workspace_root: Path, api_base: str) -> list[str]:
    return [
        f"INNER_SPACE_META_WORKSPACE_ROOT={workspace_root}",
        f"INNER_WORLD_API_BASE={api_base}",
        f"PYTHONPATH={ROOT / 'src'}",
        "INNER_SPACE_META_POLL_INTERVAL_SECONDS=2.0",
        "TELEGRAM_BOT_TOKEN=",
        "TELEGRAM_ALLOWED_USER_IDS=",
        "",
    ]


def ensure_env_file(*, workspace_root: Path, api_base: str, force: bool) -> Path:
    path = _env_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return path
    path.write_text("\n".join(_env_lines(workspace_root=workspace_root, api_base=api_base)), encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def _launch_agent_plist(*, env_path: Path, python_bin: str, poll_interval_seconds: float) -> str:
    daemon_script = ROOT / "tools" / "run_telegram_meta_agent_daemon.sh"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>{LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>{daemon_script}</string>
  </array>
  <key>WorkingDirectory</key>
  <string>{ROOT}</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>INNER_SPACE_META_ENV_FILE</key>
    <string>{env_path}</string>
    <key>PYTHON_BIN</key>
    <string>{python_bin}</string>
    <key>INNER_SPACE_META_POLL_INTERVAL_SECONDS</key>
    <string>{poll_interval_seconds}</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>{Path.home() / 'Library' / 'Logs' / 'inner-space-meta-telegram.log'}</string>
  <key>StandardErrorPath</key>
  <string>{Path.home() / 'Library' / 'Logs' / 'inner-space-meta-telegram.err.log'}</string>
</dict>
</plist>
"""


def install_launch_agent(*, env_path: Path, python_bin: str, poll_interval_seconds: float, force: bool) -> Path:
    path = _launch_agent_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        return path
    path.write_text(
        _launch_agent_plist(
            env_path=env_path,
            python_bin=python_bin,
            poll_interval_seconds=poll_interval_seconds,
        ),
        encoding="utf-8",
    )
    return path


def launchctl_bootstrap(path: Path) -> None:
    domain = f"gui/{os.getuid()}"
    subprocess.run(["launchctl", "bootout", domain, str(path)], check=False)
    subprocess.run(["launchctl", "bootstrap", domain, str(path)], check=True)
    subprocess.run(["launchctl", "kickstart", "-k", f"{domain}/{LABEL}"], check=True)


def env_has_required_secrets(path: Path) -> bool:
    if not path.exists():
        return False
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if "=" not in line or line.strip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return bool(values.get("TELEGRAM_BOT_TOKEN")) and bool(values.get("TELEGRAM_ALLOWED_USER_IDS"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the Inner Space Telegram meta agent as a local service.")
    parser.add_argument("--workspace-root", default=str(DEFAULT_WORKSPACE_ROOT))
    parser.add_argument("--api-base", default="http://127.0.0.1:8422/api")
    parser.add_argument("--python-bin", default="python3")
    parser.add_argument("--poll-interval-seconds", type=float, default=2.0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--start", action="store_true")
    args = parser.parse_args()

    if platform.system() != "Darwin":
        raise SystemExit("local installer currently supports macOS LaunchAgents only")

    env_path = ensure_env_file(
        workspace_root=Path(args.workspace_root).expanduser(),
        api_base=args.api_base,
        force=args.force,
    )
    agent_path = install_launch_agent(
        env_path=env_path,
        python_bin=args.python_bin,
        poll_interval_seconds=args.poll_interval_seconds,
        force=args.force,
    )

    print(f"env_file={env_path}")
    print(f"launch_agent={agent_path}")
    if args.start:
        if not env_has_required_secrets(env_path):
            print("not_started=missing TELEGRAM_BOT_TOKEN or TELEGRAM_ALLOWED_USER_IDS in env file")
            return 0
        launchctl_bootstrap(agent_path)
        print(f"started={LABEL}")
    else:
        print("started=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
