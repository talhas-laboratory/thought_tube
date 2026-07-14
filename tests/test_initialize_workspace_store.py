from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from conversation_os.workspace_store import SQLiteWorkspaceStore


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "initialize_workspace_store.py"
SPEC = importlib.util.spec_from_file_location("initialize_workspace_store", SCRIPT)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_initializer_seeds_manifest_without_overwriting_existing_state(tmp_path: Path, capsys) -> None:
    manifest_path = tmp_path / "workspace.json"
    manifest_path.write_text(
        json.dumps({"workspace_id": "inner-world", "purpose": "Canonical server context.", "artifact_roots": ["src/"]}),
        encoding="utf-8",
    )
    database_path = tmp_path / "state" / "workspace.db"

    assert runner.main(["--root", str(tmp_path), "--sqlite-path", str(database_path), "--manifest", str(manifest_path)]) == 0
    first = json.loads(capsys.readouterr().out)
    assert first["status"] == "initialized"

    store = SQLiteWorkspaceStore(tmp_path, database_path=database_path)
    existing = store.read_json(store.manifest_path("inner-world"))
    existing["purpose"] = "Preserve live edits."
    store.write_json(store.manifest_path("inner-world"), existing)

    assert runner.main(["--root", str(tmp_path), "--sqlite-path", str(database_path), "--manifest", str(manifest_path)]) == 0
    second = json.loads(capsys.readouterr().out)
    assert second["status"] == "existing"
    assert store.read_json(store.manifest_path("inner-world"))["purpose"] == "Preserve live edits."
