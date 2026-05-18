#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.miniapp import build_miniapp_ui_enhancement_assets, inject_miniapp_ui_enhancement  # noqa: E402
from conversation_os.openclaw_miniapp import build_openclaw_bundle  # noqa: E402


DEFAULT_REMOTE = "talha@192.168.0.102"
DEFAULT_APPS_ROOT = "/home/talha/.openclaw/workspace/apps/miniapps"
DEFAULT_APP_ID = "inner-world"
DEFAULT_API_BASE = "/apps/api/inner-world"
WATCH_ITEMS = [
    ROOT / "product" / "inner_world_v1" / "miniapp",
    ROOT / "src" / "conversation_os" / "openclaw_miniapp.py",
    ROOT / "src" / "conversation_os" / "miniapp.py",
]


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def _write_enhanced_bundle_assets(bundle_dir: Path) -> None:
    assets = build_miniapp_ui_enhancement_assets()
    index_path = bundle_dir / "index.html"
    if index_path.exists():
        index_path.write_text(inject_miniapp_ui_enhancement(index_path.read_text(encoding="utf-8")), encoding="utf-8")
    for filename, content in assets.items():
        (bundle_dir / filename).write_text(content, encoding="utf-8")


def build_temp_bundle(api_base_url: str, app_id: str) -> Path:
    temp_root = Path(tempfile.mkdtemp(prefix="inner-world-ui-sync-"))
    bundle_dir = temp_root / app_id
    build_openclaw_bundle(ROOT, output_dir=bundle_dir, app_id=app_id, api_base_url=api_base_url)
    _write_enhanced_bundle_assets(bundle_dir)
    return bundle_dir


def push_bundle(bundle_dir: Path, remote: str, apps_root: str, app_id: str, *, restart_miniapps: bool) -> None:
    remote_target = f"{apps_root.rstrip('/')}/{app_id}"
    run(["ssh", remote, f"mkdir -p {remote_target}"])
    run(["rsync", "-az", "--delete", f"{bundle_dir}/", f"{remote}:{remote_target}/"])
    if restart_miniapps:
        run(["ssh", remote, "systemctl --user restart openclaw-miniapps.service"])


def snapshot_state(paths: list[Path]) -> tuple[tuple[str, int, int], ...]:
    rows: list[tuple[str, int, int]] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_file():
            stat = path.stat()
            rows.append((str(path), stat.st_mtime_ns, stat.st_size))
            continue
        for child in sorted(path.rglob("*")):
            if child.name.startswith(".") or not child.is_file():
                continue
            stat = child.stat()
            rows.append((str(child), stat.st_mtime_ns, stat.st_size))
    return tuple(rows)


def remote_host(remote: str) -> str:
    return remote.split("@", 1)[-1]


def print_sync_banner(remote: str, apps_root: str, app_id: str) -> None:
    print(f"Synced miniapp bundle to {remote}:{apps_root.rstrip('/')}/{app_id}")
    print(f"Open from this machine: http://{remote_host(remote)}:3010/apps/{app_id}/")


def sync_once(args: argparse.Namespace) -> None:
    bundle_dir = build_temp_bundle(args.api_base_url, args.app_id)
    try:
        push_bundle(bundle_dir, args.remote, args.apps_root, args.app_id, restart_miniapps=args.restart_miniapps)
        print_sync_banner(args.remote, args.apps_root, args.app_id)
    finally:
        shutil.rmtree(bundle_dir.parent, ignore_errors=True)


def watch_and_sync(args: argparse.Namespace) -> None:
    paths = WATCH_ITEMS
    previous = snapshot_state(paths)
    print("Watching Inner World UI sources for changes...")
    sync_once(args)
    while True:
        time.sleep(args.interval)
        current = snapshot_state(paths)
        if current == previous:
            continue
        previous = current
        sync_once(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync only the Inner World miniapp bundle to the OpenClaw server.")
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--apps-root", default=DEFAULT_APPS_ROOT)
    parser.add_argument("--app-id", default=DEFAULT_APP_ID)
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE)
    parser.add_argument("--watch", action="store_true")
    parser.add_argument("--interval", type=float, default=0.8)
    parser.add_argument("--restart-miniapps", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.watch:
        watch_and_sync(args)
        return
    sync_once(args)


if __name__ == "__main__":
    main()
