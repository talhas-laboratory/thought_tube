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

from conversation_os.release_management import (  # noqa: E402
    build_release_manifest,
    build_rollback_plan,
    validate_release_manifest,
    write_release_manifest,
)


def _cmd_candidate(args: argparse.Namespace) -> int:
    manifest = build_release_manifest(ROOT, release_id=args.release_id)
    errors = validate_release_manifest(manifest)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    if args.dry_run:
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    print(write_release_manifest(ROOT, manifest))
    return 0


def _cmd_rollback_plan(args: argparse.Namespace) -> int:
    plan = build_rollback_plan(args.current_release_id, args.previous_release_id)
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Manage Inner World release manifests.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    candidate = sub.add_parser("candidate")
    candidate.add_argument("--release-id")
    candidate.add_argument("--dry-run", action="store_true")
    candidate.set_defaults(func=_cmd_candidate)

    rollback = sub.add_parser("rollback-plan")
    rollback.add_argument("--current-release-id", required=True)
    rollback.add_argument("--previous-release-id", required=True)
    rollback.set_defaults(func=_cmd_rollback_plan)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
