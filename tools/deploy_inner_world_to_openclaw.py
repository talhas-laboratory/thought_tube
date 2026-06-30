#!/usr/bin/env python3
from __future__ import annotations

import argparse
import secrets
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.openclaw_miniapp import build_openclaw_bundle  # noqa: E402
from conversation_os.codebase_overview import refresh_codebase_overview  # noqa: E402


DEFAULT_REMOTE = "talha@192.168.0.102"
DEFAULT_WORKSPACE = "/home/talha/.openclaw/workspace"
DEFAULT_REPO_PATH = f"{DEFAULT_WORKSPACE}/containers/inner-world"
DEFAULT_APPS_ROOT = f"{DEFAULT_WORKSPACE}/apps/miniapps"
DEFAULT_APP_ID = "inner-world"
DEFAULT_PORT = 8422
DEFAULT_GPT_BRIDGE_PORT = 8093
DEFAULT_GPT_BRIDGE_HOSTNAME = "inner-world-gpt.talhaslaboratory.xyz"
DEFAULT_GPT_CLOUDFLARED_CONFIG = "/home/talha/.cloudflared/config.yml"
DEFAULT_GPT_CLOUDFLARED_TUNNEL = "klarorder-gpt"

SYNC_ITEMS = [
    "AGENTS.md",
    "CONTEXT_ROUTING.md",
    "PRODUCT_THESIS.md",
    "README.md",
    "SESSION_PROTOCOL.md",
    "TENETS.md",
    "context",
    "pyproject.toml",
    "docs",
    "ops",
    "pipelines",
    "plugins",
    "src",
    "tests",
    "tools",
]

PRODUCT_SYNC_ITEMS = [
    "product/inner_world_v1/CONTRACT.md",
    "product/inner_world_v1/FEEDBACK_MODEL.md",
    "product/inner_world_v1/README.md",
    "product/inner_world_v1/config",
    "product/inner_world_v1/data",
    "product/inner_world_v1/exports",
    "product/inner_world_v1/miniapp",
    "product/inner_world_v1/pipelines",
    "product/inner_world_v1/portable",
]


def run(cmd: list[str], *, input_text: str | None = None) -> None:
    subprocess.run(cmd, input=input_text, text=input_text is not None, check=True)


def build_bundle(api_base_url: str) -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="inner-world-openclaw-bundle-"))
    build_openclaw_bundle(
        ROOT,
        output_dir=temp_root / DEFAULT_APP_ID,
        app_id=DEFAULT_APP_ID,
        api_base_url=api_base_url,
    )
    return temp_root / DEFAULT_APP_ID


def refresh_generated_agent_docs() -> None:
    refresh_codebase_overview(ROOT)


def rsync_repo(remote: str, remote_repo_path: str) -> None:
    for item in SYNC_ITEMS:
        source = ROOT / item
        if not source.exists():
            continue
        if source.is_dir():
            run(["rsync", "-az", "--delete", f"{source}/", f"{remote}:{remote_repo_path}/{item}/"])
            continue
        run(["rsync", "-az", str(source), f"{remote}:{remote_repo_path}/"])

    for item in PRODUCT_SYNC_ITEMS:
        source = ROOT / item
        if not source.exists():
            continue
        remote_target = f"{remote_repo_path}/{item}"
        if source.is_dir():
            run(["ssh", remote, f"mkdir -p {remote_target}"])
            run(["rsync", "-az", "--delete", f"{source}/", f"{remote}:{remote_target}/"])
            continue
        run(["ssh", remote, f"mkdir -p {Path(remote_target).parent}"])
        run(["rsync", "-az", str(source), f"{remote}:{remote_target}"])


def rsync_bundle(bundle_dir: Path, remote: str, remote_apps_root: str, app_id: str) -> None:
    run(["ssh", remote, f"mkdir -p {remote_apps_root}/{app_id}"])
    run(["rsync", "-az", "--delete", f"{bundle_dir}/", f"{remote}:{remote_apps_root}/{app_id}/"])


def install_service_with_stdin(remote: str, remote_repo_path: str) -> None:
    unit = (ROOT / "ops" / "systemd" / "inner-world.service.sample").read_text(encoding="utf-8")
    unit = unit.replace("/home/talha/.openclaw/workspace/containers/inner-world", remote_repo_path)
    run(
        ["ssh", remote, "mkdir -p ~/.config/systemd/user && cat > ~/.config/systemd/user/inner-world.service"],
        input_text=unit,
    )


def install_gpt_bridge_service(remote: str, remote_repo_path: str, bridge_port: int) -> None:
    unit = f"""[Unit]
Description=Inner World GPT bridge for ChatGPT mobile collaboration
After=network-online.target

[Service]
Type=simple
WorkingDirectory={remote_repo_path}
EnvironmentFile=%h/.config/inner-world-gpt-bridge.env
Environment=PYTHONPATH={remote_repo_path}/src
ExecStart=/usr/bin/env python3 {remote_repo_path}/tools/run_inner_world_backend.py --mode gpt_bridge --host 127.0.0.1 --port {bridge_port} --domains research,art,entrepreneurship
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
"""
    run(
        ["ssh", remote, "mkdir -p ~/.config/systemd/user && cat > ~/.config/systemd/user/inner-world-gpt-bridge.service"],
        input_text=unit,
    )


def install_gpt_bridge_env(
    remote: str,
    *,
    action_key: str,
    legacy_action_keys: list[str] | None,
    public_base_url: str,
    artifact_root: str,
) -> None:
    lines = [
        f"INNER_WORLD_GPT_ACTION_KEY={action_key}",
        f"INNER_WORLD_GPT_PUBLIC_BASE_URL={public_base_url}",
        f"INNER_WORLD_GPT_ARTIFACT_ROOT={artifact_root}",
    ]
    if legacy_action_keys:
        lines.append(f"INNER_WORLD_GPT_LEGACY_ACTION_KEYS={','.join(legacy_action_keys)}")
    lines.append("")
    payload = "\n".join(lines)
    run(
        ["ssh", remote, "mkdir -p ~/.config && cat > ~/.config/inner-world-gpt-bridge.env"],
        input_text=payload,
    )


def read_existing_gpt_bridge_env_var(remote: str, var_name: str) -> str:
    command = rf"""python3 - <<'PY'
from pathlib import Path

path = Path.home() / ".config" / "inner-world-gpt-bridge.env"
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


def patch_remote_host(remote: str) -> None:
    patch_script = r'''
from pathlib import Path
path = Path('/home/talha/.openclaw/workspace/apps/miniapps/_host/server.js')
text = path.read_text(encoding='utf-8')
if 'BEGIN INNER WORLD PROXY' in text:
    print('proxy patch already present')
    raise SystemExit(0)
marker = "function redirect(res, location) {\n  res.writeHead(302, { Location: location });\n  res.end();\n}\n"
insert = """
const INNER_WORLD_PROXY_PREFIX = `${URL_PREFIX}/api/inner-world`;
const INNER_WORLD_PROXY_HOST = process.env.INNER_WORLD_PROXY_HOST || "127.0.0.1";
const INNER_WORLD_PROXY_PORT = Number.parseInt(process.env.INNER_WORLD_PROXY_PORT || "8422", 10);

function proxyInnerWorld(req, res, pathname, search) {
  const upstreamSuffix = pathname.slice(INNER_WORLD_PROXY_PREFIX.length) || "/";
  const upstreamPath = `/api${upstreamSuffix}`;
  const proxyReq = http.request(
    {
      hostname: INNER_WORLD_PROXY_HOST,
      port: INNER_WORLD_PROXY_PORT,
      path: `${upstreamPath}${search || ""}`,
      method: req.method,
      headers: {
        ...req.headers,
        host: `${INNER_WORLD_PROXY_HOST}:${INNER_WORLD_PROXY_PORT}`,
      },
    },
    (proxyRes) => {
      res.writeHead(proxyRes.statusCode || 502, proxyRes.headers);
      proxyRes.pipe(res);
    }
  );
  proxyReq.on("error", (err) => json(res, 502, { ok: false, error: `inner_world_proxy_error: ${err.message}` }));
  if (req.method === "GET" || req.method === "HEAD") {
    proxyReq.end();
    return;
  }
  req.pipe(proxyReq);
}
// BEGIN INNER WORLD PROXY
"""
route_marker = "// API (under /apps/api/* so it stays inside the tailnet-exposed prefix)\n"
route_block = """
  if (pathname === INNER_WORLD_PROXY_PREFIX || pathname.startsWith(`${INNER_WORLD_PROXY_PREFIX}/`)) {
    return proxyInnerWorld(req, res, pathname, u.search);
  }

"""
if marker not in text or route_marker not in text:
    raise SystemExit('expected host markers not found')
text = text.replace(marker, marker + insert)
text = text.replace(route_marker, route_block + route_marker, 1)
backup = path.with_name(f"{path.name}.bak.inner-world")
backup.write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
path.write_text(text, encoding='utf-8')
print(f'patched {path}')
'''
    run(["ssh", remote, "python3 -"], input_text=patch_script)


def patch_cloudflared_config(remote: str, config_path: str, hostname: str, port: int) -> None:
    patch_script = f"""
from pathlib import Path

path = Path({config_path!r})
text = path.read_text(encoding='utf-8')
block = "  - hostname: {hostname}\\n    service: http://127.0.0.1:{port}\\n"
if f"hostname: {hostname}" in text:
    print("cloudflared hostname already present")
    raise SystemExit(0)
marker = "  - service: http_status:404\\n"
if marker not in text:
    raise SystemExit("cloudflared fallback marker not found")
text = text.replace(marker, block + marker, 1)
path.write_text(text, encoding='utf-8')
print(f"patched {{path}}")
"""
    run(["ssh", remote, "python3 -"], input_text=patch_script)


def ensure_cloudflared_dns(remote: str, tunnel_name: str, hostname: str) -> None:
    command = (
        f"if [ -x \"$HOME/.local/bin/cloudflared\" ]; then "
        f"\"$HOME/.local/bin/cloudflared\" tunnel route dns {tunnel_name} {hostname} || true; "
        "fi"
    )
    run(["ssh", remote, command])


def restart_cloudflared(remote: str, config_path: str, tunnel_name: str) -> None:
    script = f"""
set -e
BIN="$HOME/.local/bin/cloudflared"
CONFIG={config_path!r}
TUNNEL={tunnel_name!r}
LOG="$HOME/.cloudflared/cloudflared.log"
pkill -f "cloudflared tunnel --config $CONFIG run" >/dev/null 2>&1 || true
nohup "$BIN" tunnel --config "$CONFIG" run "$TUNNEL" >"$LOG" 2>&1 &
sleep 2
pgrep -af "cloudflared tunnel --config $CONFIG run"
"""
    run(["ssh", remote, script])


def restart_services(remote: str, *, with_gpt_bridge: bool = False) -> None:
    units = [
        "systemctl --user daemon-reload",
        "systemctl --user enable --now inner-world.service",
        "systemctl --user restart openclaw-miniapps.service",
    ]
    if with_gpt_bridge:
        units.append("systemctl --user enable inner-world-gpt-bridge.service")
        units.append("systemctl --user restart inner-world-gpt-bridge.service")
    run(["ssh", remote, " && ".join(units)])


def verify(remote: str, app_id: str) -> None:
    checks = [
        "systemctl --user is-active inner-world.service",
        "systemctl --user is-active openclaw-miniapps.service",
        f"curl -fsS http://127.0.0.1:{DEFAULT_PORT}/api/feed > /dev/null",
        "curl -fsS http://127.0.0.1:3010/apps/api/inner-world/feed > /dev/null",
        f"curl -fsS http://127.0.0.1:3010/apps/{app_id}/ > /dev/null",
    ]
    run(["ssh", remote, " && ".join(checks)])


def verify_gpt_bridge(remote: str, bridge_port: int) -> None:
    checks = [
        "systemctl --user is-active inner-world-gpt-bridge.service",
        f"curl -fsS http://127.0.0.1:{bridge_port}/health > /dev/null",
        "source ~/.config/inner-world-gpt-bridge.env",
        f"curl -fsS -H \"X-Inner-World-Action-Key: $INNER_WORLD_GPT_ACTION_KEY\" http://127.0.0.1:{bridge_port}/context/status-bundle > /dev/null",
        f"curl -fsS -H \"X-Inner-World-Action-Key: $INNER_WORLD_GPT_ACTION_KEY\" http://127.0.0.1:{bridge_port}/sync/local-status > /dev/null",
    ]
    run(["ssh", remote, " && ".join(checks)])


def fix_telegram_bindings_remote(remote: str, remote_repo_path: str) -> None:
    script = f"""
import json
import sys
from pathlib import Path

sys.path.insert(0, {remote_repo_path!r} + "/src")
from conversation_os.chat_backends import diagnose_openclaw_telegram_config, migrate_openclaw_telegram_bindings

root = Path({remote_repo_path!r})
diagnosis = diagnose_openclaw_telegram_config(root)
print(json.dumps({{"phase": "diagnose", **diagnosis}}, indent=2))
if diagnosis.get("ok"):
    raise SystemExit(0)
result = migrate_openclaw_telegram_bindings(root, apply=True)
print(json.dumps({{"phase": "migrate", **result}}, indent=2))
if not result.get("diagnosis", {{}}).get("ok"):
    raise SystemExit("telegram binding fix incomplete")
"""
    run(["ssh", remote, "python3 -"], input_text=script)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deploy Inner World into the live OpenClaw workspace.")
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE)
    parser.add_argument("--repo-path", default=DEFAULT_REPO_PATH)
    parser.add_argument("--apps-root", default=DEFAULT_APPS_ROOT)
    parser.add_argument("--app-id", default=DEFAULT_APP_ID)
    parser.add_argument("--api-base-url", default="/apps/api/inner-world")
    parser.add_argument("--with-gpt-bridge", action="store_true")
    parser.add_argument("--gpt-bridge-port", type=int, default=DEFAULT_GPT_BRIDGE_PORT)
    parser.add_argument("--gpt-bridge-hostname", default=DEFAULT_GPT_BRIDGE_HOSTNAME)
    parser.add_argument("--gpt-bridge-action-key", default="")
    parser.add_argument("--gpt-bridge-legacy-action-keys", default="")
    parser.add_argument("--gpt-bridge-artifact-root", default="")
    parser.add_argument("--cloudflared-config", default=DEFAULT_GPT_CLOUDFLARED_CONFIG)
    parser.add_argument("--cloudflared-tunnel-name", default=DEFAULT_GPT_CLOUDFLARED_TUNNEL)
    parser.add_argument("--fix-telegram-bindings", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    refresh_generated_agent_docs()
    run(["ssh", args.remote, f"mkdir -p {args.repo_path} {args.apps_root}/{args.app_id}"])
    bundle_dir = build_bundle(args.api_base_url)
    action_key = args.gpt_bridge_action_key.strip()
    if args.with_gpt_bridge and not action_key:
        action_key = read_existing_gpt_bridge_env_var(args.remote, "INNER_WORLD_GPT_ACTION_KEY")
    if not action_key:
        action_key = secrets.token_urlsafe(32)
    legacy_action_keys = [item.strip() for item in args.gpt_bridge_legacy_action_keys.split(",") if item.strip()]
    if args.with_gpt_bridge and not legacy_action_keys:
        existing_legacy = read_existing_gpt_bridge_env_var(args.remote, "INNER_WORLD_GPT_LEGACY_ACTION_KEYS")
        legacy_action_keys = [item.strip() for item in existing_legacy.split(",") if item.strip()]
    artifact_root = args.gpt_bridge_artifact_root.strip() or f"{args.repo_path}/mobile_artifacts"
    public_base_url = f"https://{args.gpt_bridge_hostname}"
    try:
        rsync_repo(args.remote, args.repo_path)
        rsync_bundle(bundle_dir, args.remote, args.apps_root, args.app_id)
        install_service_with_stdin(args.remote, args.repo_path)
        patch_remote_host(args.remote)
        if args.with_gpt_bridge:
            install_gpt_bridge_env(
                args.remote,
                action_key=action_key,
                legacy_action_keys=legacy_action_keys,
                public_base_url=public_base_url,
                artifact_root=artifact_root,
            )
            install_gpt_bridge_service(args.remote, args.repo_path, args.gpt_bridge_port)
            patch_cloudflared_config(args.remote, args.cloudflared_config, args.gpt_bridge_hostname, args.gpt_bridge_port)
            ensure_cloudflared_dns(args.remote, args.cloudflared_tunnel_name, args.gpt_bridge_hostname)
        restart_services(args.remote, with_gpt_bridge=args.with_gpt_bridge)
        if args.with_gpt_bridge:
            restart_cloudflared(args.remote, args.cloudflared_config, args.cloudflared_tunnel_name)
        verify(args.remote, args.app_id)
        if args.with_gpt_bridge:
            verify_gpt_bridge(args.remote, args.gpt_bridge_port)
        if args.fix_telegram_bindings:
            fix_telegram_bindings_remote(args.remote, args.repo_path)
            run(["ssh", args.remote, "openclaw gateway restart && openclaw gateway health"])
        print(f"Deployed Inner World to {args.remote}:{args.repo_path}")
        print(f"Miniapp URL path: /apps/{args.app_id}/")
        print("GPT repo visibility for the private app: inherited from the existing OpenClaw GPT context service.")
        if args.with_gpt_bridge:
            print(f"Inner World GPT bridge URL: {public_base_url}")
            print(f"Inner World GPT bridge local port: {args.gpt_bridge_port}")
            print(f"Inner World GPT bridge artifact root: {artifact_root}")
            print(f"Inner World GPT bridge action key: {action_key}")
    finally:
        shutil.rmtree(bundle_dir.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
