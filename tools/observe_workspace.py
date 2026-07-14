from __future__ import annotations

import argparse
import json
import signal
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

from conversation_os.workspace_observer import observe_workspace
from conversation_os.workspace_store import FileWorkspaceStore, SQLiteWorkspaceStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Observe workspace-scoped git changes.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--store", choices=("file", "sqlite"), default="sqlite")
    parser.add_argument("--sqlite-path", default="")
    parser.add_argument("--interval", type=float, default=5.0)
    parser.add_argument("--once", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    if args.store == "sqlite":
        database_path = Path(args.sqlite_path).expanduser().resolve() if args.sqlite_path else root / "state" / "workspace.db"
        store = SQLiteWorkspaceStore(root, database_path=database_path)
    else:
        store = FileWorkspaceStore(root)

    stopping = False

    def stop(_signum: int, _frame: object) -> None:
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    interval = max(float(args.interval), 1.0)
    while not stopping:
        result = observe_workspace(root, args.workspace_id, store=store)
        if args.once or result["recorded"]:
            print(json.dumps(result, ensure_ascii=False))
        if args.once:
            return 0
        time.sleep(interval)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
