from __future__ import annotations

import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any


MODULE_ID = "service.workspace.workspace_recovery"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "backup_workspace_database",
    "restore_workspace_database",
)
__all__ = list(PUBLIC_API)


def _validate_workspace_database(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Workspace database not found: {path}")
    with sqlite3.connect(str(path)) as connection:
        integrity = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        table = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'workspace_records'"
        ).fetchone()
        count = int(connection.execute("SELECT COUNT(*) FROM workspace_records").fetchone()[0]) if table else 0
    if integrity != "ok":
        raise ValueError(f"Workspace database integrity check failed: {integrity}")
    if table is None:
        raise ValueError("Workspace database schema is missing workspace_records")
    return {"integrity": integrity, "record_count": count}


def backup_workspace_database(source_path: Path, backup_path: Path) -> dict[str, Any]:
    source = source_path.expanduser().resolve()
    destination = backup_path.expanduser().resolve()
    validation = _validate_workspace_database(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.parent / f".{destination.name}.{uuid.uuid4().hex}.tmp"
    try:
        with sqlite3.connect(str(source)) as source_connection:
            with sqlite3.connect(str(temporary)) as destination_connection:
                source_connection.backup(destination_connection)
        _validate_workspace_database(temporary)
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {
        "status": "backed_up",
        "source": str(source),
        "backup": str(destination),
        **validation,
    }


def restore_workspace_database(backup_path: Path, target_path: Path) -> dict[str, Any]:
    source = backup_path.expanduser().resolve()
    target = target_path.expanduser().resolve()
    validation = _validate_workspace_database(source)
    pre_restore_backup = ""
    if target.exists():
        preserved = target.parent / f"{target.stem}.pre-restore-{uuid.uuid4().hex}{target.suffix}"
        backup_workspace_database(target, preserved)
        pre_restore_backup = str(preserved)
    backup_workspace_database(source, target)
    return {
        "status": "restored",
        "backup": str(source),
        "target": str(target),
        "pre_restore_backup": pre_restore_backup,
        **validation,
    }
