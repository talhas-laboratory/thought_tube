from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import os
import subprocess
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "tools" / "run_workspace_service.py"
sys.path.append(str(SCRIPT_PATH.parent))
SPEC = importlib.util.spec_from_file_location("run_workspace_service", SCRIPT_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_main_prints_sqlite_configuration(tmp_path: Path, capsys) -> None:
    argv = [
        "--root",
        str(tmp_path),
        "--host",
        "127.0.0.1",
        "--port",
        "9988",
        "--store",
        "sqlite",
        "--sqlite-path",
        str(tmp_path / "state" / "workspace.db"),
        "--print-config",
    ]

    assert runner.main(argv) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["store"] == "sqlite"
    assert payload["port"] == 9988


def test_main_starts_service_with_selected_store(tmp_path: Path) -> None:
    argv = [
        "--root",
        str(tmp_path),
        "--store",
        "sqlite",
        "--sqlite-path",
        str(tmp_path / "state" / "workspace.db"),
    ]
    server = mock.Mock()
    with mock.patch.object(runner, "serve_workspace_service", return_value=server) as serve:
        assert runner.main(argv) == 0

    serve.assert_called_once()
    _, kwargs = serve.call_args
    assert kwargs["port"] == 8765
    assert kwargs["start"] is False
    assert kwargs["store"].database_path == tmp_path / "state" / "workspace.db"
    server.serve_forever.assert_called_once_with()


def test_runner_prioritizes_src_when_pythonpath_is_preconfigured(tmp_path: Path) -> None:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--root",
            str(tmp_path),
            "--print-config",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["root"] == str(tmp_path)
