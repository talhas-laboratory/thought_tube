#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(SRC))
sys.path[:] = [entry for entry in sys.path if entry != str(TOOLS)]

from conversation_os.bridge_session_tracking import (  # noqa: E402
    end_bridge_session,
    get_bridge_session,
    get_bridge_session_trace,
    list_bridge_sessions,
    start_bridge_session,
)
from conversation_os.storage import repo_root_from  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage Thought Tube bridge tracking sessions.")
    sub = parser.add_subparsers(dest="command", required=True)

    start = sub.add_parser("start", help="Start tracking a bridge session.")
    start.add_argument("--session-id", required=True)
    start.add_argument("--title", default="")
    start.add_argument("--surface", default="cursor")
    start.add_argument("--workspace-id", default="")
    start.add_argument("--element-key", default="")
    start.add_argument("--holodeck-id", default="")
    start.add_argument("--topology-mode", default="", choices=["", "spine", "sidecar", "parallel"])
    start.add_argument("--auto-promote-review", action="store_true")
    start.add_argument("--restart", action="store_true")

    end = sub.add_parser("end", help="End a tracked bridge session.")
    end.add_argument("--session-id", required=True)
    end.add_argument("--reason", default="")

    get = sub.add_parser("get", help="Get one tracked session.")
    get.add_argument("--session-id", required=True)

    trace = sub.add_parser("trace", help="Get full session trace for analysis.")
    trace.add_argument("--session-id", required=True)

    listing = sub.add_parser("list", help="List tracked sessions.")
    listing.add_argument("--status", default="", choices=["", "active", "ended"])
    listing.add_argument("--limit", type=int, default=20)

    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = repo_root_from(ROOT)

    try:
        if args.command == "start":
            payload = start_bridge_session(
                root,
                session_id=args.session_id,
                title=args.title,
                surface=args.surface,
                workspace_id=args.workspace_id,
                restart=args.restart,
                element_key=args.element_key,
                holodeck_id=args.holodeck_id,
                topology_mode=args.topology_mode,
                auto_promote_review=args.auto_promote_review,
            )
        elif args.command == "end":
            payload = end_bridge_session(root, args.session_id, reason=args.reason)
        elif args.command == "get":
            payload = get_bridge_session(root, args.session_id)
        elif args.command == "trace":
            payload = get_bridge_session_trace(root, args.session_id)
        else:
            payload = list_bridge_sessions(root, status=args.status, limit=args.limit)
    except (ValueError, FileNotFoundError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2

    if args.json or not sys.stdout.isatty():
        print(json.dumps({"ok": True, "result": payload}, indent=2))
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
