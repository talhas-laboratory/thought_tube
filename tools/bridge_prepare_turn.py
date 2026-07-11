#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.bridge_prepare import prepare_turn  # noqa: E402
from conversation_os.storage import repo_root_from  # noqa: E402


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare Thought Tube bridge steering for the current user turn.",
    )
    parser.add_argument("--text", required=True, help="User message for this turn.")
    parser.add_argument("--session-id", default="", help="Stable session id across turns.")
    parser.add_argument("--workspace-id", default="", help="Workspace identifier.")
    parser.add_argument(
        "--surface",
        default="cli",
        help="Host surface label (cursor, codex, claude_code, mcp, hook, cli).",
    )
    parser.add_argument("--domain-hints", default="", help="Comma-separated domain hints.")
    parser.add_argument(
        "--caller-hints-json",
        default="",
        help="Optional JSON object merged into caller_hints.",
    )
    parser.add_argument(
        "--no-steering-file",
        action="store_true",
        help="Do not write .thought-tube/latest-steering.md",
    )
    parser.add_argument(
        "--steering-only",
        action="store_true",
        help="Print steering_markdown to stdout instead of JSON.",
    )
    parser.add_argument("--json", action="store_true", help="Print full JSON payload.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    root = repo_root_from(ROOT)
    caller_hints: Dict[str, Any] = {}
    if args.caller_hints_json.strip():
        caller_hints = json.loads(args.caller_hints_json)
        if not isinstance(caller_hints, dict):
            raise SystemExit("caller_hints_json must decode to an object")

    try:
        payload = prepare_turn(
            root,
            raw_text=args.text,
            session_id=args.session_id,
            workspace_id=args.workspace_id,
            surface=args.surface,
            domain_hints=_parse_csv(args.domain_hints),
            caller_hints=caller_hints,
            write_steering_file=not args.no_steering_file,
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": "invalid_request", "message": str(exc)}), file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            json.dumps({"ok": False, "error": "prepare_turn_failed", "message": str(exc) or exc.__class__.__name__}),
            file=sys.stderr,
        )
        return 1

    if args.steering_only:
        print(payload["steering_markdown"])
        return 0
    if args.json or not sys.stdout.isatty():
        print(json.dumps(payload, indent=2))
        return 0
    print(payload["steering_markdown"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
