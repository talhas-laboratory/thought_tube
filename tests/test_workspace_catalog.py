from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pytest

from conversation_os.workspace_catalog import audit_workspace_catalogs, migrate_workspace, workspace_catalog, workspace_snapshot
from conversation_os.workspace_client import WorkspaceClient, WorkspaceClientError
from conversation_os.workspace_service import serve_workspace_service
from conversation_os.workspace_store import FileWorkspaceStore, SQLiteWorkspaceStore


def _seed_file_workspace(root: Path, workspace_id: str = "sol-context-frames") -> FileWorkspaceStore:
    store = FileWorkspaceStore(root)
    store.write_json(
        store.manifest_path(workspace_id),
        {
            "workspace_id": workspace_id,
            "label": "Context frames",
            "status": "active",
            "maturation_stage": "developing",
            "objectives": ["Keep work resumable."],
        },
    )
    store.append_jsonl(
        store.work_item_events_path(workspace_id),
        {
            "event_id": "work-1",
            "workspace_id": workspace_id,
            "work_item_id": "CAW-001",
            "operation": "create",
            "timestamp": "2026-07-11T10:00:00+00:00",
            "actor": "codex",
            "payload": {"title": "Normalize status", "status": "completed"},
        },
    )
    store.append_jsonl(
        store.test_runs_path(workspace_id),
        {
            "run_id": "run-1",
            "workspace_id": workspace_id,
            "test_id": "CAW-001:normalization",
            "timestamp": "2026-07-11T10:05:00+00:00",
            "actor": "codex",
            "result": "passed",
            "evidence_ref": "pytest",
        },
    )
    return store


def test_catalog_migration_normalizes_records_and_is_idempotent(tmp_path: Path) -> None:
    source = _seed_file_workspace(tmp_path / "source")
    target = SQLiteWorkspaceStore(tmp_path / "target", database_path=tmp_path / "target" / "state" / "workspace.db")

    audit = audit_workspace_catalogs(source, target)
    assert audit["counts"]["source_only"] == 1
    planned = migrate_workspace(source, target, "sol-context-frames", dry_run=True)
    assert planned["status"] == "planned"
    assert target.workspace_ids() == []

    migrated = migrate_workspace(source, target, "sol-context-frames")
    assert migrated["status"] == "migrated"
    work_event = target.read_jsonl(target.work_item_events_path("sol-context-frames"))[0]
    test_run = target.read_jsonl(target.test_runs_path("sol-context-frames"))[0]
    assert work_event["payload"]["status"] == "done"
    assert test_run["result"] == "passing"
    assert audit_workspace_catalogs(source, target)["counts"]["in_sync"] == 1
    assert migrate_workspace(source, target, "sol-context-frames")["status"] == "already_migrated"


def test_catalog_migration_refuses_divergent_target(tmp_path: Path) -> None:
    source = _seed_file_workspace(tmp_path / "source")
    target = SQLiteWorkspaceStore(tmp_path / "target", database_path=tmp_path / "target" / "state" / "workspace.db")
    target.write_json(
        target.manifest_path("sol-context-frames"),
        {"workspace_id": "sol-context-frames", "label": "Different workspace"},
    )

    audit = audit_workspace_catalogs(source, target)
    assert audit["counts"]["conflict"] == 1
    with pytest.raises(ValueError, match="will not be overwritten"):
        migrate_workspace(source, target, "sol-context-frames")


def test_workspace_catalog_service_endpoint_reports_store_revisions(tmp_path: Path) -> None:
    store = _seed_file_workspace(tmp_path)
    server = serve_workspace_service(root=tmp_path, host="127.0.0.1", port=0, store=store)
    try:
        url = f"http://127.0.0.1:{server.server_address[1]}/api/workspaces"
        with urllib.request.urlopen(url, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["workspace_count"] == 1
        assert payload["workspaces"][0]["workspace_id"] == "sol-context-frames"
        assert len(payload["workspaces"][0]["revision"]) == 64
        assert workspace_catalog(store)["workspaces"] == payload["workspaces"]
    finally:
        server.shutdown()
        server.server_close()


def test_workspace_service_manages_create_import_and_archive_without_overwrite(tmp_path: Path) -> None:
    source = _seed_file_workspace(tmp_path / "source")
    target = SQLiteWorkspaceStore(tmp_path / "target", database_path=tmp_path / "target" / "state" / "workspace.db")
    server = serve_workspace_service(root=tmp_path / "target", host="127.0.0.1", port=0, store=target)
    try:
        client = WorkspaceClient(f"http://127.0.0.1:{server.server_address[1]}/api")
        created = client.create_workspace({"workspace_id": "created", "label": "Created workspace"})
        assert created["status"] == "created"
        assert client.catalog()["workspace_count"] == 1

        snapshot = workspace_snapshot(source, "sol-context-frames")
        preview = client.import_workspace(snapshot, dry_run=True)
        assert preview["status"] == "planned"
        imported = client.import_workspace(snapshot)
        assert imported["status"] == "imported"
        assert imported["target_backup"]
        assert Path(imported["target_backup"]).is_file()
        assert client.import_workspace(snapshot)["status"] == "already_imported"

        archived = client.archive_workspace("created", reason="Superseded by imported workspace")
        assert archived["status"] == "archived"
        assert next(row for row in client.catalog()["workspaces"] if row["workspace_id"] == "created")["status"] == "archived"

        with pytest.raises(WorkspaceClientError, match="already exists"):
            client.create_workspace({"workspace_id": "created"})
    finally:
        server.shutdown()
        server.server_close()
