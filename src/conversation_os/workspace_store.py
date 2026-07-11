from __future__ import annotations

import json
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Protocol

from .storage import (
    append_jsonl,
    read_json,
    read_jsonl,
    workspace_activity_events_path,
    workspace_blockers_path,
    workspace_claims_path,
    workspace_decisions_path,
    workspace_manifest_path,
    workspace_dir,
    workspace_ids,
    workspace_test_cases_path,
    workspace_test_runs_path,
    workspace_work_item_events_path,
)


MODULE_ID = "kernel.workspace.workspace_store"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "WorkspaceStore",
    "FileWorkspaceStore",
    "SQLiteWorkspaceStore",
)
__all__ = list(PUBLIC_API)


class WorkspaceStore(Protocol):
    root: Path

    def manifest_path(self, workspace_id: str) -> Path: ...
    def activity_events_path(self, workspace_id: str) -> Path: ...
    def blockers_path(self, workspace_id: str) -> Path: ...
    def claims_path(self, workspace_id: str) -> Path: ...
    def decisions_path(self, workspace_id: str) -> Path: ...
    def work_item_events_path(self, workspace_id: str) -> Path: ...
    def test_cases_path(self, workspace_id: str) -> Path: ...
    def test_runs_path(self, workspace_id: str) -> Path: ...
    def repository_snapshots_path(self, workspace_id: str) -> Path: ...
    def read_json(self, path: Path, default: Any = None) -> Any: ...
    def write_json(self, path: Path, payload: Any) -> None: ...
    def read_jsonl(self, path: Path) -> List[Dict[str, Any]]: ...
    def append_jsonl(self, path: Path, payload: Dict[str, Any]) -> None: ...
    def readiness(self) -> Dict[str, Any]: ...
    def workspace_ids(self) -> List[str]: ...
    def record_paths(self, workspace_id: str) -> List[Path]: ...


@dataclass(frozen=True)
class FileWorkspaceStore:
    root: Path

    def manifest_path(self, workspace_id: str) -> Path:
        return workspace_manifest_path(self.root, workspace_id)

    def activity_events_path(self, workspace_id: str) -> Path:
        return workspace_activity_events_path(self.root, workspace_id)

    def blockers_path(self, workspace_id: str) -> Path:
        return workspace_blockers_path(self.root, workspace_id)

    def claims_path(self, workspace_id: str) -> Path:
        return workspace_claims_path(self.root, workspace_id)

    def decisions_path(self, workspace_id: str) -> Path:
        return workspace_decisions_path(self.root, workspace_id)

    def work_item_events_path(self, workspace_id: str) -> Path:
        return workspace_work_item_events_path(self.root, workspace_id)

    def test_cases_path(self, workspace_id: str) -> Path:
        return workspace_test_cases_path(self.root, workspace_id)

    def test_runs_path(self, workspace_id: str) -> Path:
        return workspace_test_runs_path(self.root, workspace_id)

    def repository_snapshots_path(self, workspace_id: str) -> Path:
        return workspace_manifest_path(self.root, workspace_id).parent / "repository_snapshots.jsonl"

    def read_json(self, path: Path, default: Any = None) -> Any:
        return read_json(path, default=default)

    def write_json(self, path: Path, payload: Any) -> None:
        from .storage import write_json

        write_json(path, payload)

    def read_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        return read_jsonl(path)

    def append_jsonl(self, path: Path, payload: Dict[str, Any]) -> None:
        append_jsonl(path, payload)

    def readiness(self) -> Dict[str, Any]:
        probe_dir = self.root / "state"
        probe_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=probe_dir, prefix="workspace-ready-", delete=True):
            pass
        return {"status": "ready", "store": type(self).__name__}

    def workspace_ids(self) -> List[str]:
        return workspace_ids(self.root)

    def record_paths(self, workspace_id: str) -> List[Path]:
        directory = workspace_dir(self.root, workspace_id)
        if not directory.is_dir():
            return []
        return sorted(
            path
            for path in directory.iterdir()
            if path.is_file() and path.suffix in {".json", ".jsonl"}
        )


@dataclass(frozen=True)
class SQLiteWorkspaceStore:
    root: Path
    database_path: Path

    def __post_init__(self) -> None:
        self._initialize()

    def manifest_path(self, workspace_id: str) -> Path:
        return workspace_manifest_path(self.root, workspace_id)

    def activity_events_path(self, workspace_id: str) -> Path:
        return workspace_activity_events_path(self.root, workspace_id)

    def blockers_path(self, workspace_id: str) -> Path:
        return workspace_blockers_path(self.root, workspace_id)

    def claims_path(self, workspace_id: str) -> Path:
        return workspace_claims_path(self.root, workspace_id)

    def decisions_path(self, workspace_id: str) -> Path:
        return workspace_decisions_path(self.root, workspace_id)

    def work_item_events_path(self, workspace_id: str) -> Path:
        return workspace_work_item_events_path(self.root, workspace_id)

    def test_cases_path(self, workspace_id: str) -> Path:
        return workspace_test_cases_path(self.root, workspace_id)

    def test_runs_path(self, workspace_id: str) -> Path:
        return workspace_test_runs_path(self.root, workspace_id)

    def repository_snapshots_path(self, workspace_id: str) -> Path:
        return workspace_manifest_path(self.root, workspace_id).parent / "repository_snapshots.jsonl"

    def read_json(self, path: Path, default: Any = None) -> Any:
        row = self._fetch_one(path, kind="json")
        if row is None:
            return default
        return json.loads(row)

    def write_json(self, path: Path, payload: Any) -> None:
        self._execute(
            """
            INSERT INTO workspace_records (workspace_id, record_key, kind, seq, payload_json)
            VALUES (?, ?, 'json', 0, ?)
            ON CONFLICT(workspace_id, record_key, kind, seq) DO UPDATE SET payload_json = excluded.payload_json
            """,
            (self._workspace_id_from_path(path), path.name, json.dumps(payload, ensure_ascii=False)),
        )

    def read_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        rows = self._fetch_all(path, kind="jsonl")
        return [json.loads(item) for item in rows]

    def append_jsonl(self, path: Path, payload: Dict[str, Any]) -> None:
        self._execute(
            """
            INSERT INTO workspace_records (workspace_id, record_key, kind, seq, payload_json)
            VALUES (
                ?, ?, 'jsonl',
                COALESCE(
                    (SELECT MAX(seq) + 1 FROM workspace_records WHERE workspace_id = ? AND record_key = ? AND kind = 'jsonl'),
                    1
                ),
                ?
            )
            """,
            (
                self._workspace_id_from_path(path),
                path.name,
                self._workspace_id_from_path(path),
                path.name,
                json.dumps(payload, ensure_ascii=False),
            ),
        )

    def readiness(self) -> Dict[str, Any]:
        with self._connect() as connection:
            integrity = str(connection.execute("PRAGMA quick_check").fetchone()[0])
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("CREATE TEMP TABLE IF NOT EXISTS workspace_readiness_probe (value INTEGER)")
            connection.execute("INSERT INTO workspace_readiness_probe (value) VALUES (1)")
            connection.rollback()
        if integrity != "ok":
            raise RuntimeError(f"workspace store integrity check failed: {integrity}")
        return {"status": "ready", "store": type(self).__name__, "integrity": integrity}

    def workspace_ids(self) -> List[str]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT DISTINCT workspace_id FROM workspace_records ORDER BY workspace_id ASC"
            ).fetchall()
        return [str(row["workspace_id"]) for row in rows]

    def record_paths(self, workspace_id: str) -> List[Path]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT record_key
                FROM workspace_records
                WHERE workspace_id = ?
                ORDER BY record_key ASC
                """,
                (workspace_id,),
            ).fetchall()
        return [workspace_dir(self.root, workspace_id) / str(row["record_key"]) for row in rows]

    def _initialize(self) -> None:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS workspace_records (
                    workspace_id TEXT NOT NULL,
                    record_key TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (workspace_id, record_key, kind, seq)
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.database_path))
        connection.row_factory = sqlite3.Row
        return connection

    def _execute(self, sql: str, params: tuple[Any, ...]) -> None:
        with self._connect() as connection:
            connection.execute(sql, params)
            connection.commit()

    def _fetch_one(self, path: Path, *, kind: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT payload_json
                FROM workspace_records
                WHERE workspace_id = ? AND record_key = ? AND kind = ? AND seq = 0
                """,
                (self._workspace_id_from_path(path), path.name, kind),
            ).fetchone()
        if row is None:
            return None
        return str(row["payload_json"])

    def _fetch_all(self, path: Path, *, kind: str) -> List[str]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT payload_json
                FROM workspace_records
                WHERE workspace_id = ? AND record_key = ? AND kind = ?
                ORDER BY seq ASC
                """,
                (self._workspace_id_from_path(path), path.name, kind),
            ).fetchall()
        return [str(row["payload_json"]) for row in rows]

    def _workspace_id_from_path(self, path: Path) -> str:
        return path.parent.name
