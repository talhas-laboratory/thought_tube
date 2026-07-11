from __future__ import annotations

from pathlib import Path

from conversation_os.release_management import (
    build_release_manifest,
    build_rollback_plan,
    validate_release_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


def test_build_release_manifest_contains_expected_artifacts() -> None:
    manifest = build_release_manifest(ROOT, release_id="test-release")
    assert manifest["release_id"] == "test-release"
    assert "runtime_config" in manifest["artifacts"]
    assert "agent_configs" in manifest["artifacts"]
    assert manifest["gates"]["status"] == "blocked"


def test_release_manifest_validation_requires_rollback_plan() -> None:
    manifest = build_release_manifest(ROOT, release_id="test-release")
    manifest["rollback"]["plan_path"] = ""
    errors = validate_release_manifest(manifest)
    assert "rollback plan path is required" in errors


def test_build_rollback_plan_targets_previous_release() -> None:
    plan = build_rollback_plan(
        current_release_id="inner-world-new",
        previous_release_id="inner-world-old",
    )
    assert plan["current_release_id"] == "inner-world-new"
    assert plan["target_release_id"] == "inner-world-old"
    assert plan["status"] == "dry_run"
    assert "restore_manifest" in plan["steps"]
