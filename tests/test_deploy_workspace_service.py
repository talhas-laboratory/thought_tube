from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools" / "deploy_workspace_service_to_openclaw.py"
SPEC = importlib.util.spec_from_file_location("deploy_workspace_service", SCRIPT)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


def test_deployment_scope_contains_only_workspace_runtime_dependencies() -> None:
    paths = set(runner.workspace_sync_paths())
    assert "src/conversation_os/workspace_service.py" in paths
    assert "src/conversation_os/workspace_coordination.py" in paths
    assert "src/conversation_os/holodeck.py" in paths
    assert "src/conversation_os/storage.py" in paths
    assert "tools/run_workspace_service.py" in paths
    assert "tools/run_telegram_meta_agent.py" in paths
    assert "product/inner_world_v1/config/workspace.json" in paths
    assert "product/inner_world_v1/miniapp" not in paths
    assert "product/mobile_surface_v1" not in paths


def test_rendered_units_and_meta_env_use_remote_paths_and_shared_api(tmp_path: Path) -> None:
    repo_path = "/srv/inner-world"
    unit = runner.render_unit(ROOT / "ops/systemd/inner-space-workspace.service.sample", repo_path)
    assert "/srv/inner-world/tools/run_workspace_service.py" in unit
    assert "/home/talha/.openclaw/workspace/containers/inner-world" not in unit

    local_env = tmp_path / "meta.env"
    local_env.write_text(
        "TELEGRAM_BOT_TOKEN=secret\n"
        "TELEGRAM_ALLOWED_USER_IDS=42\n"
        "INNER_SPACE_META_WORKSPACE_ROOT=/local/runtime\n"
        "PYTHONPATH=/local/src\n",
        encoding="utf-8",
    )
    rendered = runner.render_meta_env(local_env, repo_path, workspace_api_base="http://127.0.0.1:8765/api")
    assert "TELEGRAM_BOT_TOKEN=secret" in rendered
    assert "INNER_SPACE_META_WORKSPACE_ROOT=/srv/inner-world/product/inner_world_v1/meta_agent/state/runtime" in rendered
    assert "PYTHONPATH=/srv/inner-world/src" in rendered
    assert "INNER_WORLD_WORKSPACE_API_BASE=http://127.0.0.1:8765/api" in rendered


def test_source_revision_reads_published_git_head() -> None:
    assert len(runner.source_revision()) == 40
