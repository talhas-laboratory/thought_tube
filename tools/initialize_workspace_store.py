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

from conversation_os.workspace_store import SQLiteWorkspaceStore


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Initialize a canonical workspace SQLite store from a manifest.")
    parser.add_argument("--root", required=True)
    parser.add_argument("--sqlite-path", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--force", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.root).expanduser().resolve()
    database_path = Path(args.sqlite_path).expanduser().resolve()
    manifest_path = Path(args.manifest).expanduser().resolve()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    workspace_id = str(manifest.get("workspace_id", "") or "").strip()
    if not workspace_id:
        raise ValueError("workspace manifest requires workspace_id")
    store = SQLiteWorkspaceStore(root, database_path=database_path)
    path = store.manifest_path(workspace_id)
    existing = store.read_json(path, default=None)
    if isinstance(existing, dict) and not args.force:
        status = "existing"
    else:
        store.write_json(path, manifest)
        status = "initialized" if existing is None else "replaced"
    print(
        json.dumps(
            {
                "status": status,
                "workspace_id": workspace_id,
                "database_path": str(database_path),
                "manifest_path": str(manifest_path),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
