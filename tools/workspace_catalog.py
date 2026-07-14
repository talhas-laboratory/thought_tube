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
from conversation_os.workspace_catalog import audit_workspace_catalogs, migrate_workspace, workspace_catalog, workspace_snapshot
from conversation_os.workspace_client import WorkspaceClient, WorkspaceClientError
from conversation_os.workspace_recovery import backup_workspace_database
from conversation_os.workspace_store import FileWorkspaceStore, SQLiteWorkspaceStore


def _store(root: Path, kind: str, sqlite_path: str):
    if kind == "file":
        return FileWorkspaceStore(root)
    database_path = Path(sqlite_path).expanduser().resolve() if sqlite_path else root / "state" / "workspace.db"
    return SQLiteWorkspaceStore(root, database_path=database_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect and safely migrate workspace catalogs.")
    parser.add_argument("command", choices=("catalog", "audit", "migrate"))
    parser.add_argument("--root", default="", help="Repository root; defaults to this repository.")
    parser.add_argument("--store", choices=("file", "sqlite"), default="file")
    parser.add_argument("--sqlite-path", default="")
    parser.add_argument("--target-root", default="")
    parser.add_argument("--target-store", choices=("file", "sqlite"), default="sqlite")
    parser.add_argument("--target-sqlite-path", default="")
    parser.add_argument("--workspace-id", default="")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--backup-path", default="", help="Required before a migration mutates a nonempty SQLite target store.")
    parser.add_argument("--workspace-api-base", default="", help="Canonical workspace service base for catalog reads or imports.")
    return parser


def _root(raw_root: str) -> Path:
    if raw_root:
        return Path(raw_root).expanduser().resolve()
    return repo_root_from(Path(__file__).resolve()).resolve()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = _root(args.root)
    source = _store(root, args.store, args.sqlite_path)
    client = WorkspaceClient(args.workspace_api_base) if args.workspace_api_base else None
    if args.command == "catalog":
        payload = client.catalog() if client else workspace_catalog(source)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    if client:
        if args.command == "audit":
            print(json.dumps({"error": "Remote audit is not implemented; use catalog revisions to compare stores."}), file=sys.stderr)
            return 2
        if not args.workspace_id:
            build_parser().error("--workspace-id is required for migrate")
        try:
            result = client.import_workspace(
                workspace_snapshot(source, args.workspace_id),
                dry_run=args.dry_run,
                imported_from=f"{args.store}:{root}",
            )
        except (FileNotFoundError, ValueError, WorkspaceClientError) as exc:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
            return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    target_root = _root(args.target_root) if args.target_root else root
    target = _store(target_root, args.target_store, args.target_sqlite_path)
    if args.command == "audit":
        print(json.dumps(audit_workspace_catalogs(source, target), ensure_ascii=False, indent=2))
        return 0
    if not args.workspace_id:
        parser = build_parser()
        parser.error("--workspace-id is required for migrate")
    try:
        preview = migrate_workspace(source, target, args.workspace_id, dry_run=True)
        if args.dry_run or preview["status"] != "planned":
            result = preview
        else:
            backup = ""
            if isinstance(target, SQLiteWorkspaceStore) and target.workspace_ids():
                if not args.backup_path:
                    raise ValueError("--backup-path is required before mutating a nonempty SQLite target store")
                backup = backup_workspace_database(target.database_path, Path(args.backup_path))["backup"]
            result = migrate_workspace(source, target, args.workspace_id)
            result["target_backup"] = backup
    except (FileNotFoundError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
