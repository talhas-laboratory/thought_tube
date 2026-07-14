#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.storage import repo_root_from
from conversation_os.workspace_projection_sync import (  # noqa: E402
    check_workspace_projections,
    sync_workspace_projections,
)


def _default_workspace_api_base() -> str:
    configured = str(os.environ.get("INNER_WORLD_WORKSPACE_API_BASE", "") or "").strip()
    if configured:
        return configured
    config_path = Path(os.path.expanduser("~/.config/inner-space-workspace.env"))
    if not config_path.is_file():
        return ""
    for line in config_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("INNER_WORLD_WORKSPACE_API_BASE="):
            return stripped.split("=", 1)[1].strip()
    return ""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Publish git-tracked workspace projections from live coordination state."
    )
    parser.add_argument("command", choices=("publish", "check"))
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--root", default="")
    parser.add_argument("--workspace-api-base", default="")
    parser.add_argument("--agent-id", default="projection-sync")
    parser.add_argument("--surface", default="cursor")
    parser.add_argument("--session-id", default="projection-sync")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Use the local workspace store instead of the live API.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).expanduser().resolve() if args.root else repo_root_from(Path(__file__).resolve()).resolve()
    api_base = ""
    if not args.offline:
        api_base = args.workspace_api_base or _default_workspace_api_base()
    if args.command == "check":
        result = check_workspace_projections(
            root,
            args.workspace_id,
            api_base=api_base,
            agent_id=args.agent_id,
            surface=args.surface,
            session_id=args.session_id,
        )
    else:
        result = sync_workspace_projections(
            root,
            args.workspace_id,
            api_base=api_base,
            agent_id=args.agent_id,
            surface=args.surface,
            session_id=args.session_id,
            dry_run=args.dry_run,
        )
    print(json.dumps(result, indent=2))
    if args.command == "check" and not result.get("fresh"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
