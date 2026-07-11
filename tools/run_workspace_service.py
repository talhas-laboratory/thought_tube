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

from conversation_os.storage import repo_root_from
from conversation_os.workspace_service import serve_workspace_service
from conversation_os.workspace_store import FileWorkspaceStore, SQLiteWorkspaceStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the workspace coordination service.")
    parser.add_argument("--root", default="", help="Repo root. Defaults to current repo.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--store", choices=("file", "sqlite"), default="sqlite")
    parser.add_argument("--sqlite-path", default="", help="SQLite database path for server-native mode.")
    parser.add_argument("--print-config", action="store_true", help="Print resolved config and exit.")
    return parser


def _resolve_root(raw_root: str) -> Path:
    if raw_root:
        return Path(raw_root).expanduser().resolve()
    return repo_root_from(Path(__file__).resolve()).resolve()


def _build_store(root: Path, *, store_kind: str, sqlite_path: str):
    if store_kind == "file":
        return FileWorkspaceStore(root)
    database_path = Path(sqlite_path).expanduser().resolve() if sqlite_path else root / "state" / "workspace.db"
    return SQLiteWorkspaceStore(root, database_path=database_path)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = _resolve_root(args.root)
    store = _build_store(root, store_kind=args.store, sqlite_path=args.sqlite_path)

    if args.print_config:
        print(
            json.dumps(
                {
                    "root": str(root),
                    "host": args.host,
                    "port": args.port,
                    "store": args.store,
                    "sqlite_path": str(getattr(store, "database_path", "")),
                }
            )
        )
        return 0

    server = serve_workspace_service(
        root=root,
        host=args.host,
        port=args.port,
        store=store,
        start=False,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
