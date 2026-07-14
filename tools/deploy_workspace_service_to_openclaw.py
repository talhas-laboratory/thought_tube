#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REMOTE = "talha@192.168.0.102"
DEFAULT_REPO_PATH = "/home/talha/.openclaw/workspace/containers/inner-world"
DEFAULT_WORKSPACE_API_BASE = "http://127.0.0.1:8765/api"


def workspace_sync_paths() -> list[str]:
    paths = [
        "src/conversation_os/holodeck.py",
        "src/conversation_os/meta_telegram_agent.py",
        "src/conversation_os/storage.py",
        "src/conversation_os/workspace_atlas.py",
        "src/conversation_os/workspace_catalog.py",
        "src/conversation_os/workspace_client.py",
        "src/conversation_os/workspace_context_packet.py",
        "src/conversation_os/workspace_continuity.py",
        "src/conversation_os/workspace_health.py",
        "src/conversation_os/workspace_coordination.py",
        "src/conversation_os/workspace_observer.py",
        "src/conversation_os/workspace_progress.py",
        "src/conversation_os/workspace_recovery.py",
        "src/conversation_os/workspace_reasoning.py",
        "src/conversation_os/workspace_runs.py",
        "src/conversation_os/workspace_service.py",
        "src/conversation_os/workspace_store.py",
        "src/conversation_os/workspace_work_adapter.py",
        "tools/backup_workspace_store.py",
        "tools/deploy_workspace_service_to_openclaw.py",
        "tools/initialize_workspace_store.py",
        "tools/observe_workspace.py",
        "tools/restore_workspace_store.py",
        "tools/run_telegram_meta_agent.py",
        "tools/run_workspace_service.py",
        "tools/workspace_coordination.py",
        "tools/workspace_catalog.py",
        "tools/workspace_work.py",
        "tools/workspace_continuity.py",
        "ops/systemd/inner-space-meta-telegram.service.sample",
        "ops/systemd/inner-space-workspace-observer.service.sample",
        "ops/systemd/inner-space-workspace.service.sample",
        "product/inner_world_v1/config/workspace.json",
        "docs/workspaces/unified-framework-synthesis/CONTINUITY.md",
        "docs/guides/deployment-guide.md",
        "docs/implementation/workspace-coordination/README.md",
        "docs/superpowers/plans/2026-06-30-agent-context-repository-gap-plan.md",
    ]
    board_root = ROOT / "docs" / "workboards" / "inner-space-agent-ops"
    paths.extend(str(path.relative_to(ROOT)) for path in sorted(board_root.rglob("*")) if path.is_file())
    return paths


def render_unit(path: Path, repo_path: str) -> str:
    return path.read_text(encoding="utf-8").replace(DEFAULT_REPO_PATH, repo_path)


def _read_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key] = value
    return values


def render_meta_env(path: Path, repo_path: str, *, workspace_api_base: str) -> str:
    values = _read_env(path)
    if not values.get("TELEGRAM_BOT_TOKEN") or not values.get("TELEGRAM_ALLOWED_USER_IDS"):
        raise ValueError("Meta agent environment requires TELEGRAM_BOT_TOKEN and TELEGRAM_ALLOWED_USER_IDS")
    values["INNER_SPACE_META_WORKSPACE_ROOT"] = f"{repo_path}/product/inner_world_v1/meta_agent/state/runtime"
    values["PYTHONPATH"] = f"{repo_path}/src"
    values["INNER_WORLD_API_BASE"] = values.get("INNER_WORLD_API_BASE", "http://127.0.0.1:8422/api")
    values["INNER_WORLD_WORKSPACE_API_BASE"] = workspace_api_base
    values["INNER_SPACE_META_POLL_INTERVAL_SECONDS"] = values.get("INNER_SPACE_META_POLL_INTERVAL_SECONDS", "2.0")
    ordered_keys = [
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ALLOWED_USER_IDS",
        "INNER_SPACE_META_WORKSPACE_ROOT",
        "INNER_WORLD_API_BASE",
        "INNER_WORLD_WORKSPACE_API_BASE",
        "INNER_SPACE_META_POLL_INTERVAL_SECONDS",
        "PYTHONPATH",
    ]
    return "\n".join(f"{key}={values[key]}" for key in ordered_keys) + "\n"


def run(command: list[str], *, input_text: str | None = None) -> None:
    subprocess.run(command, input=input_text, text=input_text is not None, check=True)


def source_revision() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _remote_command(remote: str, command: str) -> None:
    run(["ssh", remote, command])


def _sync_files(remote: str, repo_path: str) -> None:
    parents = sorted({str(Path(repo_path) / Path(relative).parent) for relative in workspace_sync_paths()})
    _remote_command(remote, "mkdir -p " + " ".join(shlex.quote(path) for path in parents))
    for relative in workspace_sync_paths():
        run(["rsync", "-az", str(ROOT / relative), f"{remote}:{repo_path}/{relative}"])


def _install_user_file(remote: str, target: str, content: str, *, mode: str = "0600") -> None:
    command = f"install -m {mode} /dev/stdin {shlex.quote(target)}"
    run(["ssh", remote, command], input_text=content)


def deploy(args: argparse.Namespace) -> dict[str, object]:
    repo_path = args.repo_path.rstrip("/")
    database_path = f"{repo_path}/state/workspace.db"
    _sync_files(args.remote, repo_path)
    _remote_command(
        args.remote,
        "mkdir -p ~/.config/systemd/user ~/.config "
        f"{shlex.quote(repo_path + '/state')} {shlex.quote(repo_path + '/backups')}",
    )
    backup_command = (
        f"if test -f {shlex.quote(database_path)}; then "
        f"cd {shlex.quote(repo_path)} && python3 tools/backup_workspace_store.py "
        f"--source {shlex.quote(database_path)} "
        f"--output {shlex.quote(repo_path + '/backups/workspace-pre-deploy.db')}; fi"
    )
    _remote_command(args.remote, backup_command)
    _remote_command(
        args.remote,
        f"cd {shlex.quote(repo_path)} && python3 tools/initialize_workspace_store.py "
        f"--root {shlex.quote(repo_path)} --sqlite-path {shlex.quote(database_path)} "
        "--manifest product/inner_world_v1/config/workspace.json",
    )

    workspace_env = (
        "PYTHONUNBUFFERED=1\n"
        f"INNER_WORLD_WORKSPACE_API_BASE={args.workspace_api_base}\n"
        f"INNER_SPACE_REPOSITORY_SOURCE_REVISION={source_revision()}\n"
    )
    _install_user_file(args.remote, "/home/talha/.config/inner-space-workspace.env", workspace_env)
    for unit_name in ("inner-space-workspace", "inner-space-workspace-observer"):
        unit = render_unit(ROOT / f"ops/systemd/{unit_name}.service.sample", repo_path)
        _install_user_file(
            args.remote,
            f"/home/talha/.config/systemd/user/{unit_name}.service",
            unit,
            mode="0644",
        )

    meta_installed = False
    if not args.skip_meta:
        meta_env = render_meta_env(Path(args.meta_env).expanduser(), repo_path, workspace_api_base=args.workspace_api_base)
        _install_user_file(args.remote, "/home/talha/.config/inner-space-meta.env", meta_env)
        meta_unit = render_unit(ROOT / "ops/systemd/inner-space-meta-telegram.service.sample", repo_path)
        _install_user_file(
            args.remote,
            "/home/talha/.config/systemd/user/inner-space-meta-telegram.service",
            meta_unit,
            mode="0644",
        )
        meta_installed = True

    services = ["inner-space-workspace.service", "inner-space-workspace-observer.service"]
    if meta_installed:
        services.append("inner-space-meta-telegram.service")
    _remote_command(
        args.remote,
        "systemctl --user daemon-reload && systemctl --user enable --now " + " ".join(services),
    )
    _remote_command(
        args.remote,
        "python3 - <<'PY'\n"
        "import json, urllib.request\n"
        "for path in ('/health', '/ready', '/api/workspaces/inner-world/context?agent_id=deploy&surface=server'):\n"
        "    with urllib.request.urlopen('http://127.0.0.1:8765' + path, timeout=10) as response:\n"
        "        payload = json.loads(response.read().decode('utf-8'))\n"
        "        assert response.status == 200, payload\n"
        "print('workspace-service-verified')\n"
        "PY",
    )
    return {"status": "deployed", "remote": args.remote, "repo_path": repo_path, "services": services}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Deploy the canonical workspace and Telegram agent services to OpenClaw.")
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--repo-path", default=DEFAULT_REPO_PATH)
    parser.add_argument("--workspace-api-base", default=DEFAULT_WORKSPACE_API_BASE)
    parser.add_argument("--meta-env", default=str(Path.home() / ".config" / "inner-space-meta.env"))
    parser.add_argument("--skip-meta", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.dry_run:
        print(json.dumps({"status": "dry-run", "remote": args.remote, "repo_path": args.repo_path, "sync_paths": workspace_sync_paths()}))
        return 0
    print(json.dumps(deploy(args), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
