#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

from conversation_os.workspace_recovery import restore_workspace_database


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Restore a validated workspace SQLite backup.")
    parser.add_argument("--backup", required=True)
    parser.add_argument("--target", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = restore_workspace_database(Path(args.backup), Path(args.target))
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
