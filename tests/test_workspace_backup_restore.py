from __future__ import annotations

from pathlib import Path

from conversation_os.workspace_context_packet import assemble_workspace_context_packet
from conversation_os.workspace_recovery import backup_workspace_database, restore_workspace_database
from conversation_os.workspace_store import SQLiteWorkspaceStore


def _seed_database(root: Path, database_path: Path) -> SQLiteWorkspaceStore:
    store = SQLiteWorkspaceStore(root, database_path=database_path)
    store.write_json(
        store.manifest_path("inner-world"),
        {
            "workspace_id": "inner-world",
            "purpose": "Recover canonical context.",
            "artifact_roots": ["src/"],
            "objectives": ["Survive restart and restore."],
        },
    )
    store.append_jsonl(
        store.work_item_events_path("inner-world"),
        {
            "event_id": "create-1",
            "workspace_id": "inner-world",
            "work_item_id": "CTX-005",
            "operation": "create",
            "timestamp": "2026-06-30T10:00:00+00:00",
            "actor": "codex",
            "payload": {"title": "Recovery", "status": "in-progress"},
            "source_refs": ["docs/recovery.md"],
        },
    )
    store.append_jsonl(
        store.decisions_path("inner-world"),
        {
            "decision_id": "decision-1",
            "workspace_id": "inner-world",
            "task_id": "CTX-005",
            "summary": "Use SQLite backup API.",
            "reasoning": "It produces a consistent live backup.",
            "status": "accepted",
            "created_at": "2026-06-30T10:05:00+00:00",
        },
    )
    store.append_jsonl(
        store.repository_snapshots_path("inner-world"),
        {
            "schema_version": "1.0",
            "source_revision": "abc123",
            "changes": [{"status": "modified", "path": "src/recovery.py"}],
            "changed_files": ["src/recovery.py"],
            "fingerprint": "snapshot-1",
            "observed_at": "2026-06-30T10:06:00+00:00",
        },
    )
    return store


def _stable_packet(packet: dict) -> dict:
    normalized = dict(packet)
    normalized.pop("assembled_at", None)
    return normalized


def test_backup_restore_reproduces_canonical_context_packet(tmp_path: Path) -> None:
    source_path = tmp_path / "state" / "workspace.db"
    source_store = _seed_database(tmp_path, source_path)
    expected = _stable_packet(
        assemble_workspace_context_packet(
            tmp_path,
            "inner-world",
            task_id="CTX-005",
            agent_id="codex",
            surface="codex",
            session_id="s-1",
            store=source_store,
        )
    )
    backup_path = tmp_path / "backups" / "workspace.db"
    restored_path = tmp_path / "restored" / "workspace.db"

    backup = backup_workspace_database(source_path, backup_path)
    restore = restore_workspace_database(backup_path, restored_path)
    restored_store = SQLiteWorkspaceStore(tmp_path, database_path=restored_path)
    actual = _stable_packet(
        assemble_workspace_context_packet(
            tmp_path,
            "inner-world",
            task_id="CTX-005",
            agent_id="codex",
            surface="codex",
            session_id="s-1",
            store=restored_store,
        )
    )

    assert backup["status"] == "backed_up"
    assert restore["status"] == "restored"
    assert expected == actual


def test_restore_preserves_pre_restore_database(tmp_path: Path) -> None:
    backup_source = tmp_path / "source" / "workspace.db"
    _seed_database(tmp_path, backup_source)
    backup_path = tmp_path / "backups" / "source.db"
    backup_workspace_database(backup_source, backup_path)

    target_path = tmp_path / "target" / "workspace.db"
    target_store = SQLiteWorkspaceStore(tmp_path, database_path=target_path)
    target_store.write_json(target_store.manifest_path("old"), {"workspace_id": "old"})

    result = restore_workspace_database(backup_path, target_path)

    assert result["pre_restore_backup"]
    preserved = Path(result["pre_restore_backup"])
    assert preserved.exists()
    preserved_store = SQLiteWorkspaceStore(tmp_path, database_path=preserved)
    assert preserved_store.read_json(preserved_store.manifest_path("old"))["workspace_id"] == "old"
