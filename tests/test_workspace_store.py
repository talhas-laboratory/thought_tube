from __future__ import annotations

from pathlib import Path

from conversation_os.workspace_store import SQLiteWorkspaceStore


def test_sqlite_workspace_store_roundtrips_manifest_and_activity_rows(tmp_path: Path) -> None:
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    workspace_id = "sol-frontend"

    manifest_path = store.manifest_path(workspace_id)
    store.write_json(
        manifest_path,
        {
            "workspace_id": workspace_id,
            "artifact_roots": ["product/thought_capture_pwa/"],
            "objectives": ["Ship the PWA."],
        },
    )

    store.append_jsonl(
        store.activity_events_path(workspace_id),
        {
            "event_id": "evt-1",
            "workspace_id": workspace_id,
            "task_id": "MTC-001",
            "event_type": "edited",
            "summary": "Adjusted shell spacing.",
        },
    )
    store.append_jsonl(
        store.activity_events_path(workspace_id),
        {
            "event_id": "evt-2",
            "workspace_id": workspace_id,
            "task_id": "MTC-001",
            "event_type": "tested",
            "summary": "Ran mobile smoke.",
        },
    )

    assert store.read_json(manifest_path, default=None)["workspace_id"] == workspace_id
    assert [row["event_id"] for row in store.read_jsonl(store.activity_events_path(workspace_id))] == ["evt-1", "evt-2"]
