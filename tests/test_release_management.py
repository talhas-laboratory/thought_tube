from __future__ import annotations

from pathlib import Path

from conversation_os.release_management import (
    DEFAULT_WAVE0_RELEASE_CHECKS,
    build_release_manifest,
    build_rollback_plan,
    evaluate_codebase_freshness_gate,
    validate_release_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


def test_build_release_manifest_contains_expected_artifacts() -> None:
    manifest = build_release_manifest(ROOT, release_id="test-release")
    assert manifest["release_id"] == "test-release"
    assert "runtime_config" in manifest["artifacts"]
    assert "agent_configs" in manifest["artifacts"]
    assert "shape_population" in manifest["artifacts"]
    assert "reconciliation_matrix" in manifest["artifacts"]
    assert manifest["gates"]["status"] == "blocked"
    assert "schema_revision" in manifest["versions"]
    assert "benchmark_revision" in manifest["versions"]
    assert manifest["source"]["integration_spine"].startswith("origin/cursor/shape-intelligence-remediation-pass")
    assert manifest["source"]["population_import"].startswith(
        "origin/codex/shape-population-production-hardening"
    )


def test_release_manifest_validation_requires_rollback_plan() -> None:
    manifest = build_release_manifest(ROOT, release_id="test-release")
    manifest["rollback"]["plan_path"] = ""
    errors = validate_release_manifest(manifest)
    assert "rollback plan path is required" in errors


def test_release_manifest_validation_requires_version_slots_and_integration_refs() -> None:
    manifest = build_release_manifest(ROOT, release_id="test-release")
    assert validate_release_manifest(manifest) == []
    del manifest["versions"]["corpus_revision"]
    manifest["source"]["integration_spine"] = ""
    errors = validate_release_manifest(manifest)
    assert "versions.corpus_revision is required" in errors
    assert "source.integration_spine is required" in errors


def test_build_rollback_plan_targets_previous_release() -> None:
    plan = build_rollback_plan(
        current_release_id="inner-world-new",
        previous_release_id="inner-world-old",
    )
    assert plan["current_release_id"] == "inner-world-new"
    assert plan["target_release_id"] == "inner-world-old"
    assert plan["status"] == "dry_run"
    assert "restore_manifest" in plan["steps"]


def test_evaluate_codebase_freshness_gate_passes_on_current_checkout() -> None:
    report = evaluate_codebase_freshness_gate(ROOT)
    assert report["status"] == "passed"
    assert report["fresh"] is True
    assert report["missing_manifest_count"] == 0
    assert report["shape_profile_deprecation_recorded"] is True
    assert "repo_overview_fresh" in DEFAULT_WAVE0_RELEASE_CHECKS
    assert report["recommended_hermetic_command"] == 'pytest -m "not live"'
