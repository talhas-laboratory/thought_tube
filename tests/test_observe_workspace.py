from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

from conversation_os.workspace_store import SQLiteWorkspaceStore


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "observe_workspace.py"
SPEC = importlib.util.spec_from_file_location("observe_workspace_tool", SCRIPT)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_observer_runner_records_one_shot_sqlite_snapshot(tmp_path: Path, capsys) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "agent@example.test")
    _git(tmp_path, "config", "user.name", "Agent")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("before\n", encoding="utf-8")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "initial")
    database = tmp_path / "state" / "workspace.db"
    store = SQLiteWorkspaceStore(tmp_path, database_path=database)
    store.write_json(
        store.manifest_path("inner-world"),
        {"workspace_id": "inner-world", "artifact_roots": ["src/"]},
    )
    (tmp_path / "src" / "app.py").write_text("after\n", encoding="utf-8")

    code = runner.main(
        [
            "--root",
            str(tmp_path),
            "--workspace-id",
            "inner-world",
            "--store",
            "sqlite",
            "--sqlite-path",
            str(database),
            "--once",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["recorded"] is True
    assert payload["snapshot"]["changed_files"] == ["src/app.py"]
