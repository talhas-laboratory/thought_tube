#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.self_improvement import validate_system_improvement_packet  # noqa: E402
from conversation_os.self_improvement_agent import draft_self_improvement_packet  # noqa: E402
from conversation_os.storage import ensure_dir  # noqa: E402


def _cmd_create(args: argparse.Namespace) -> int:
    packet = draft_self_improvement_packet(
        args.text,
        args.session_id,
        args.turn_id,
        use_agent=args.use_agent,
    )
    if args.dry_run:
        print(json.dumps(packet, indent=2, sort_keys=True))
        return 0
    out_dir = ROOT / "docs" / "workboards" / "inner-space-agent-ops" / "inbox"
    ensure_dir(out_dir)
    out_path = out_dir / f"{packet['packet_id']}.json"
    out_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    packet = json.loads(Path(args.path).read_text(encoding="utf-8"))
    errors = validate_system_improvement_packet(packet)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("ok")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Create or validate self-improvement packets.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    create = sub.add_parser("create")
    create.add_argument("--text", required=True)
    create.add_argument("--session-id", required=True)
    create.add_argument("--turn-id", required=True)
    create.add_argument("--use-agent", action="store_true")
    create.add_argument("--dry-run", action="store_true")
    create.set_defaults(func=_cmd_create)

    validate = sub.add_parser("validate")
    validate.add_argument("path")
    validate.set_defaults(func=_cmd_validate)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
