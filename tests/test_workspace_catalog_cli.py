from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from conversation_os.workspace_store import FileWorkspaceStore, SQLiteWorkspaceStore
from conversation_os.workspace_service import serve_workspace_service


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "tools" / "workspace_catalog.py"
SPEC = importlib.util.spec_from_file_location("workspace_catalog_tool", SCRIPT_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _seed_workspace(root: Path) -> None:
    store = FileWorkspaceStore(root)
    store.write_json(
        store.manifest_path("sol-context-frames"),
        {"workspace_id": "sol-context-frames", "label": "Context Frames"},
    )


def test_catalog_cli_audits_and_migrates_a_workspace(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    _seed_workspace(source)

    assert runner.main(["catalog", "--root", str(source), "--store", "file"]) == 0
    assert json.loads(capsys.readouterr().out)["workspace_count"] == 1

    audit_args = [
        "audit", "--root", str(source), "--store", "file", "--target-root", str(target),
        "--target-store", "sqlite", "--target-sqlite-path", str(target / "state" / "workspace.db"),
    ]
    assert runner.main(audit_args) == 0
    assert json.loads(capsys.readouterr().out)["counts"]["source_only"] == 1

    migrate_args = [
        "migrate", "--root", str(source), "--store", "file", "--target-root", str(target),
        "--target-store", "sqlite", "--target-sqlite-path", str(target / "state" / "workspace.db"),
        "--workspace-id", "sol-context-frames",
    ]
    assert runner.main(migrate_args) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "migrated"


def test_catalog_cli_requires_backup_for_nonempty_sqlite_target(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source"
    target = tmp_path / "target"
    _seed_workspace(source)
    target_store = SQLiteWorkspaceStore(target, database_path=target / "state" / "workspace.db")
    target_store.write_json(target_store.manifest_path("existing"), {"workspace_id": "existing"})

    code = runner.main(
        [
            "migrate", "--root", str(source), "--store", "file", "--target-root", str(target),
            "--target-store", "sqlite", "--target-sqlite-path", str(target / "state" / "workspace.db"),
            "--workspace-id", "sol-context-frames",
        ]
    )

    assert code == 2
    assert "--backup-path is required" in capsys.readouterr().err


def test_catalog_cli_imports_local_snapshot_to_canonical_service(tmp_path: Path, capsys) -> None:
    source = tmp_path / "source"
    _seed_workspace(source)
    target_store = SQLiteWorkspaceStore(tmp_path / "target", database_path=tmp_path / "target" / "state" / "workspace.db")
    server = serve_workspace_service(root=tmp_path / "target", host="127.0.0.1", port=0, store=target_store)
    try:
        api_base = f"http://127.0.0.1:{server.server_address[1]}/api"
        code = runner.main(
            [
                "migrate", "--root", str(source), "--store", "file", "--workspace-id", "sol-context-frames",
                "--workspace-api-base", api_base,
            ]
        )
        assert code == 0
        assert json.loads(capsys.readouterr().out)["status"] == "imported"
        assert target_store.read_json(target_store.manifest_path("sol-context-frames"))["workspace_id"] == "sol-context-frames"
    finally:
        server.shutdown()
        server.server_close()
