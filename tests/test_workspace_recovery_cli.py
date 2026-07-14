from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from conversation_os.workspace_store import SQLiteWorkspaceStore


ROOT = Path(__file__).resolve().parents[1]


def _load_tool(name: str):
    path = ROOT / "tools" / name
    spec = importlib.util.spec_from_file_location(name.replace(".py", ""), path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_backup_and_restore_cli_round_trip(tmp_path: Path, capsys) -> None:
    source = tmp_path / "state" / "workspace.db"
    store = SQLiteWorkspaceStore(tmp_path, database_path=source)
    store.write_json(store.manifest_path("inner-world"), {"workspace_id": "inner-world"})
    backup = tmp_path / "backups" / "workspace.db"
    restored = tmp_path / "restored" / "workspace.db"

    backup_tool = _load_tool("backup_workspace_store.py")
    assert backup_tool.main(["--source", str(source), "--output", str(backup)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "backed_up"

    restore_tool = _load_tool("restore_workspace_store.py")
    assert restore_tool.main(["--backup", str(backup), "--target", str(restored)]) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "restored"
    restored_store = SQLiteWorkspaceStore(tmp_path, database_path=restored)
    assert restored_store.read_json(restored_store.manifest_path("inner-world"))["workspace_id"] == "inner-world"


def test_systemd_samples_enforce_safe_workspace_operation() -> None:
    service = (ROOT / "ops" / "systemd" / "inner-space-workspace.service.sample").read_text(encoding="utf-8")
    observer = (ROOT / "ops" / "systemd" / "inner-space-workspace-observer.service.sample").read_text(encoding="utf-8")

    assert "User=" not in service
    assert "--host 127.0.0.1" in service
    assert "EnvironmentFile=%h/.config/inner-space-workspace.env" in service
    assert "Restart=on-failure" in service
    assert "NoNewPrivileges=true" in service
    assert "ExecStartPre=" in service and "/ready" not in service

    assert "User=" not in observer
    assert "Requires=inner-space-workspace.service" in observer
    assert "After=inner-space-workspace.service" in observer
    assert "--store sqlite" in observer
    assert "Restart=on-failure" in observer
    assert "WantedBy=default.target" in service
    assert "WantedBy=default.target" in observer


def test_launchd_tunnel_sample_keeps_workspace_service_private() -> None:
    plist = (ROOT / "ops" / "launchd" / "com.inner-space.workspace-tunnel.plist.sample").read_text(encoding="utf-8")
    assert "127.0.0.1:18765:127.0.0.1:8765" in plist
    assert "talha@192.168.0.102" in plist
    assert "ExitOnForwardFailure=yes" in plist
    assert "ServerAliveInterval=30" in plist
    assert "<key>KeepAlive</key>" in plist
