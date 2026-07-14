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

from conversation_os.element_capture import list_element_captures, list_promoted_element_records  # noqa: E402
from conversation_os.element_ingest import ingest_to_element_space  # noqa: E402
from conversation_os.storage import repo_root_from  # noqa: E402


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ingest content into product element semantic space.")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="Route raw text into an element provisional capture.")
    ingest.add_argument("--text", required=True)
    ingest.add_argument("--source-kind", default="cli_ingest")
    ingest.add_argument("--source-ref", default="")
    ingest.add_argument("--session-id", default="")
    ingest.add_argument("--element-key", default="")
    ingest.add_argument("--surface-hint", action="append", default=[])

    list_cmd = sub.add_parser("list", help="List element captures.")
    list_cmd.add_argument("--element-key", required=True)
    list_cmd.add_argument("--status", default="provisional")
    list_cmd.add_argument("--limit", type=int, default=20)

    promoted = sub.add_parser("promoted", help="List promoted element records.")
    promoted.add_argument("--element-key", required=True)
    promoted.add_argument("--limit", type=int, default=20)

    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = repo_root_from(ROOT)

    try:
        if args.command == "ingest":
            payload = ingest_to_element_space(
                root,
                raw_text=args.text,
                source_kind=args.source_kind,
                source_ref=args.source_ref,
                session_id=args.session_id,
                surface_hints=list(args.surface_hint or []),
                element_key=args.element_key,
            )
        elif args.command == "list":
            payload = list_element_captures(
                root,
                args.element_key,
                status=args.status,
                limit=args.limit,
            )
        else:
            payload = list_promoted_element_records(root, args.element_key, limit=args.limit)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        return 2

    if args.json or not sys.stdout.isatty():
        print(json.dumps({"ok": True, "result": payload}, indent=2))
    else:
        print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
