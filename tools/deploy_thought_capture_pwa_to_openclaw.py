#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PWA_ROOT = ROOT / "product" / "thought_capture_pwa"
TOOLS = ROOT / "tools"

SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import deploy_inner_world_to_openclaw as deploy_common  # noqa: E402

DEFAULT_CAPTURE_HOSTNAME = "notes.talhaslaboratory.xyz"
DEFAULT_CAPTURE_USERNAME = "capture"
DEFAULT_SERVICE_URL = f"http://127.0.0.1:{deploy_common.DEFAULT_PORT}"
INNER_WORLD_ENV_PATH = "~/.config/inner-world.env"
INNER_WORLD_ENV_SYSTEMD_PATH = "%h/.config/inner-world.env"

SYNC_ITEMS = [
    "pyproject.toml",
    "src",
    "tools",
    "ops",
    "product/inner_world_v1/config/runtime.json",
    "product/thought_capture_pwa",
]


def build_pwa() -> None:
    if not (PWA_ROOT / "package.json").exists():
        raise FileNotFoundError(f"PWA package missing: {PWA_ROOT}")
    subprocess.run(["npm", "ci"], cwd=PWA_ROOT, check=True)
    subprocess.run(["npm", "run", "build"], cwd=PWA_ROOT, check=True)
    if not (PWA_ROOT / "dist" / "index.html").exists():
        raise RuntimeError("PWA build did not produce dist/index.html")


def rsync_capture_bundle(remote: str, remote_repo_path: str) -> None:
    for item in SYNC_ITEMS:
        source = ROOT / item
        if not source.exists():
            continue
        remote_target = f"{remote_repo_path}/{item}"
        if source.is_dir():
            deploy_common.run(["ssh", remote, f"mkdir -p {remote_target}"])
            deploy_common.run(["rsync", "-az", "--delete", f"{source}/", f"{remote}:{remote_target}/"])
            continue
        deploy_common.run(["ssh", remote, f"mkdir -p {Path(remote_target).parent}"])
        deploy_common.run(["rsync", "-az", str(source), f"{remote}:{remote_target}"])


def read_remote_env_var(remote: str, var_name: str) -> str:
    command = rf"""python3 - <<'PY'
from pathlib import Path

path = Path({INNER_WORLD_ENV_PATH!r}).expanduser()
if not path.exists():
    raise SystemExit(0)
for line in path.read_text(encoding="utf-8").splitlines():
    if line.startswith({var_name!r} + "="):
        print(line.split("=", 1)[1])
        break
PY"""
    proc = subprocess.run(
        ["ssh", remote, command],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def write_inner_world_env(
    remote: str,
    *,
    capture_hostname: str,
    capture_username: str,
    capture_password: str,
    mobile_hostname: str = "",
    mobile_password: str = "",
) -> None:
    lines: list[str] = []
    if mobile_hostname:
        lines.append(f"INNER_WORLD_MOBILE_HOSTNAME={mobile_hostname}")
    if mobile_password:
        lines.append(f"INNER_WORLD_MOBILE_PASSWORD={mobile_password}")
    lines.extend(
        [
            f"INNER_WORLD_CAPTURE_HOSTNAME={capture_hostname}",
            f"INNER_WORLD_CAPTURE_USERNAME={capture_username}",
            f"INNER_WORLD_CAPTURE_PASSWORD={capture_password}",
            "INNER_WORLD_CHAT_BACKEND=openclaw_gateway",
            "INNER_WORLD_OPENCLAW_AGENT=thought_tube_router",
            "INNER_WORLD_BRIDGE_ENABLED=true",
            "INNER_WORLD_BRIDGE_EXECUTION_MODE=agent",
            "INNER_WORLD_BRIDGE_AGENT=thought_tube_router",
        ]
    )
    payload = "\n".join(lines) + "\n"
    deploy_common.run(
        ["ssh", remote, f"mkdir -p ~/.config && cat > {INNER_WORLD_ENV_PATH}"],
        input_text=payload,
    )


def merge_inner_world_env(
    remote: str,
    *,
    capture_hostname: str,
    capture_password: str = "",
) -> tuple[str, str]:
    mobile_hostname = read_remote_env_var(remote, "INNER_WORLD_MOBILE_HOSTNAME")
    mobile_password = read_remote_env_var(remote, "INNER_WORLD_MOBILE_PASSWORD")
    capture_username = (
        read_remote_env_var(remote, "INNER_WORLD_CAPTURE_USERNAME") or DEFAULT_CAPTURE_USERNAME
    )
    resolved_capture_password = (
        capture_password.strip()
        or read_remote_env_var(remote, "INNER_WORLD_CAPTURE_PASSWORD")
        or secrets.token_urlsafe(24)
    )
    write_inner_world_env(
        remote,
        capture_hostname=capture_hostname,
        capture_username=capture_username,
        capture_password=resolved_capture_password,
        mobile_hostname=mobile_hostname,
        mobile_password=mobile_password,
    )
    return capture_username, resolved_capture_password


def patch_service_env_file(remote: str, remote_repo_path: str) -> None:
    unit = (ROOT / "ops" / "systemd" / "inner-world.service.sample").read_text(encoding="utf-8")
    unit = unit.replace("/home/talha/.openclaw/workspace/containers/inner-world", remote_repo_path)
    env_marker = "Environment=PYTHONPATH="
    env_file_line = f"EnvironmentFile=-{INNER_WORLD_ENV_SYSTEMD_PATH}\n"
    if env_file_line not in unit and env_marker in unit:
        unit = unit.replace(env_marker, env_file_line + env_marker, 1)
    deploy_common.run(
        ["ssh", remote, "mkdir -p ~/.config/systemd/user && cat > ~/.config/systemd/user/inner-world.service"],
        input_text=unit,
    )


def provision_bridge_agent(remote: str, remote_repo_path: str) -> None:
    deploy_common.run(
        [
            "ssh",
            remote,
            f"cd {remote_repo_path} && python3 tools/provision_bridge_openclaw_agent.py --json",
        ]
    )


def verify(remote: str, capture_hostname: str) -> None:
    port = deploy_common.DEFAULT_PORT
    checks = [
        "set -a; . $HOME/.config/inner-world.env; set +a",
        "systemctl --user is-active inner-world.service",
        f"unauthenticated_status=$(curl -sS -o /dev/null -w '%{{http_code}}' "
        f"-H 'Host: {capture_hostname}' http://127.0.0.1:{port}/capture)",
        'test "$unauthenticated_status" = "401"',
        f"curl -fsS -u \"$INNER_WORLD_CAPTURE_USERNAME:$INNER_WORLD_CAPTURE_PASSWORD\" "
        f"-H 'Host: {capture_hostname}' http://127.0.0.1:{port}/capture | grep -q 'Thought Capture'",
        f"curl -fsS -u \"$INNER_WORLD_CAPTURE_USERNAME:$INNER_WORLD_CAPTURE_PASSWORD\" "
        f"-H 'Host: {capture_hostname}' http://127.0.0.1:{port}/api/mobile/capture/session "
        "-X POST -H 'Content-Type: application/json' -d '{}' | grep -q session_id",
        f"curl -fsS --retry 5 --retry-delay 2 --retry-all-errors "
        f"-u \"$INNER_WORLD_CAPTURE_USERNAME:$INNER_WORLD_CAPTURE_PASSWORD\" "
        f"https://{capture_hostname}/ | grep -q 'Thought Capture'",
    ]
    deploy_common.run(["ssh", remote, " && ".join(checks)])


def assert_release_gate(args: argparse.Namespace) -> None:
    if getattr(args, "allow_ungated_deploy", False):
        return
    report_path = getattr(args, "release_gate_report", "")
    if not report_path:
        raise SystemExit("--release-gate-report is required unless --allow-ungated-deploy is set")
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    if report.get("status") != "passed":
        raise SystemExit(f"release gates blocked deploy: {report.get('missing_checks', [])}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deploy Thought Capture PWA to OpenClaw + cloudflared.")
    parser.add_argument("--remote", default=deploy_common.DEFAULT_REMOTE)
    parser.add_argument("--repo-path", default=deploy_common.DEFAULT_REPO_PATH)
    parser.add_argument("--capture-hostname", default=DEFAULT_CAPTURE_HOSTNAME)
    parser.add_argument(
        "--capture-password",
        default="",
        help="Capture password. Reuses the deployed value or generates one when omitted.",
    )
    parser.add_argument("--service-url", default=DEFAULT_SERVICE_URL)
    parser.add_argument("--cloudflared-config", default=deploy_common.DEFAULT_GPT_CLOUDFLARED_CONFIG)
    parser.add_argument("--cloudflared-tunnel-name", default=deploy_common.DEFAULT_GPT_CLOUDFLARED_TUNNEL)
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--release-gate-report", default="")
    parser.add_argument("--allow-ungated-deploy", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    assert_release_gate(args)
    if not args.skip_build:
        build_pwa()
    deploy_common.run(["ssh", args.remote, f"mkdir -p {args.repo_path}"])
    rsync_capture_bundle(args.remote, args.repo_path)
    capture_username, capture_password = merge_inner_world_env(
        args.remote,
        capture_hostname=args.capture_hostname,
        capture_password=args.capture_password,
    )
    patch_service_env_file(args.remote, args.repo_path)
    provision_bridge_agent(args.remote, args.repo_path)
    deploy_common.patch_cloudflared_config(
        args.remote,
        args.cloudflared_config,
        args.capture_hostname,
        args.service_url,
    )
    deploy_common.ensure_cloudflared_dns(args.remote, args.cloudflared_tunnel_name, args.capture_hostname)
    deploy_common.restart_services(args.remote)
    deploy_common.restart_cloudflared(args.remote, args.cloudflared_config, args.cloudflared_tunnel_name)
    verify(args.remote, args.capture_hostname)
    print(f"Deployed Thought Capture PWA to https://{args.capture_hostname}/capture")
    print(f"Remote repo: {args.remote}:{args.repo_path}")
    print(f"Capture username: {capture_username}")
    print(f"Capture password: {capture_password}")
    print("Mobile API: same origin /api/mobile (protected by capture authentication)")


if __name__ == "__main__":
    main()
