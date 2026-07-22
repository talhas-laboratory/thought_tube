from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .storage import ensure_dir, utc_now, write_json


MODULE_ID = "kernel.release.release_management"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "build_release_manifest",
    "validate_release_manifest",
    "write_release_manifest",
    "evaluate_release_gates",
    "evaluate_codebase_freshness_gate",
    "build_rollback_plan",
    "DEFAULT_WAVE0_RELEASE_CHECKS",
)
__all__ = list(PUBLIC_API)

DEFAULT_WAVE0_RELEASE_CHECKS = (
    "repo_overview_fresh",
    "module_manifests_complete",
    "hermetic_unit_suite",
    "population_focused_suite",
    "aperture_focused_suite",
    "shape_profile_deprecation_recorded",
)


def _hash_paths(root: Path, paths: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for relative in sorted(paths):
        path = root / relative
        if not path.exists():
            digest.update(f"missing:{relative}\n".encode("utf-8"))
            continue
        if path.is_file():
            digest.update(relative.encode("utf-8"))
            digest.update(path.read_bytes())
            continue
        for child in sorted(candidate for candidate in path.rglob("*") if candidate.is_file()):
            digest.update(str(child.relative_to(root)).encode("utf-8"))
            digest.update(child.read_bytes())
    return "sha256:" + digest.hexdigest()


def _git_value(root: Path, args: List[str], default: str) -> str:
    try:
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)
    except OSError:
        return default
    if result.returncode != 0:
        return default
    return result.stdout.strip() or default


_VERSION_SLOT_KEYS = (
    "schema_revision",
    "profile_revision",
    "prompt_revision",
    "model_revision",
    "policy_revision",
    "migration_revision",
    "flag_revision",
    "corpus_revision",
    "benchmark_revision",
)


def _read_optional_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _build_version_block(root: Path) -> Dict[str, Any]:
    """Collect explicit revision slots for a truthful release claim.

    Missing slots stay empty strings. Callers/gates decide whether emptiness blocks
    release; the manifest must still expose the slots so Wave 0 baselines cannot
    silently omit them.
    """

    runtime = _read_optional_json(root / "product" / "inner_world_v1" / "config" / "runtime.json")
    disclosure = runtime.get("disclosure") if isinstance(runtime.get("disclosure"), dict) else {}
    versions = {key: "" for key in _VERSION_SLOT_KEYS}
    versions["schema_revision"] = str(
        runtime.get("schema_revision")
        or runtime.get("schema_version")
        or CONTRACT_VERSION
    )
    profile_rev = runtime.get("profile_revision")
    if not profile_rev and isinstance(runtime.get("profiles"), dict):
        profile_rev = runtime["profiles"].get("revision")
    versions["profile_revision"] = str(profile_rev or "")
    versions["prompt_revision"] = str(runtime.get("prompt_revision") or "")
    versions["model_revision"] = str(
        runtime.get("model_revision")
        or ((runtime.get("model_roles") or {}) if isinstance(runtime.get("model_roles"), dict) else {}).get("revision")
        or ""
    )
    versions["policy_revision"] = str(
        runtime.get("policy_revision")
        or disclosure.get("policy_revision")
        or disclosure.get("estimator_version")
        or ""
    )
    versions["migration_revision"] = str(runtime.get("migration_revision") or "")
    flag_rev = runtime.get("flag_revision")
    if not flag_rev and disclosure:
        flag_rev = "disclosure-rollout:" + str((disclosure.get("rollout") or {}).get("bridge") or "unset")
    versions["flag_revision"] = str(flag_rev or "")
    versions["corpus_revision"] = str(runtime.get("corpus_revision") or "")
    versions["benchmark_revision"] = str(runtime.get("benchmark_revision") or "")
    versions["slots"] = list(_VERSION_SLOT_KEYS)
    return versions


def build_release_manifest(root: Path, release_id: str | None = None) -> Dict[str, Any]:
    resolved_release_id = release_id or "inner-world-" + utc_now().replace(":", "").replace("-", "")
    artifact_paths = {
        "backend": ["src/conversation_os", "tools"],
        "runtime_config": ["product/inner_world_v1/config/runtime.json"],
        "agent_configs": ["product/inner_world_v1/config/agent_configs"],
        "bridge_behaviors": ["product/inner_world_v1/config/bridge_behaviors"],
        "pipelines": ["product/inner_world_v1/pipelines"],
        "pwa_bundle": ["product/thought_capture_pwa/dist"],
        "shape_population": ["src/conversation_os/shape_population"],
        "reconciliation_matrix": [
            "docs/workspaces/unified-framework-synthesis/derived/T10-00-RECONCILIATION-MATRIX.md"
        ],
    }
    artifacts = {
        key: {"paths": list(paths), "fingerprint": _hash_paths(root, paths)}
        for key, paths in artifact_paths.items()
    }
    dirty = _git_value(root, ["status", "--short"], "")
    return {
        "schema_version": "1.0",
        "release_id": resolved_release_id,
        "created_at": utc_now(),
        "source": {
            "git_commit": _git_value(root, ["rev-parse", "HEAD"], "unknown"),
            "branch": _git_value(root, ["branch", "--show-current"], "unknown"),
            "git_status_clean": dirty == "",
            "integration_spine": (
                "origin/cursor/shape-intelligence-remediation-pass"
                "@0c8f367a0e8d85d703f572493b9d8e9c02ae4349"
            ),
            "population_import": (
                "origin/codex/shape-population-production-hardening"
                "@82a1c3589caf9fa743dbf67ba024b1c360649bfa"
            ),
            "reconciliation_matrix": (
                "docs/workspaces/unified-framework-synthesis/derived/T10-00-RECONCILIATION-MATRIX.md"
            ),
        },
        "versions": _build_version_block(root),
        "artifacts": artifacts,
        "gates": {
            "status": "blocked",
            "report_path": f"product/inner_world_v1/releases/{resolved_release_id}/gate_report.json",
        },
        "rollback": {
            "previous_release_id": "",
            "plan_path": f"product/inner_world_v1/releases/{resolved_release_id}/rollback_plan.json",
        },
    }


def validate_release_manifest(manifest: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    if not manifest.get("release_id"):
        errors.append("release_id is required")
    if not manifest.get("rollback", {}).get("plan_path"):
        errors.append("rollback plan path is required")
    if "runtime_config" not in manifest.get("artifacts", {}):
        errors.append("runtime_config artifact is required")
    if "agent_configs" not in manifest.get("artifacts", {}):
        errors.append("agent_configs artifact is required")
    versions = manifest.get("versions")
    if not isinstance(versions, dict):
        errors.append("versions block is required")
    else:
        for key in _VERSION_SLOT_KEYS:
            if key not in versions:
                errors.append(f"versions.{key} is required")
    source = manifest.get("source")
    if not isinstance(source, dict):
        errors.append("source block is required")
    else:
        for key in ("integration_spine", "population_import", "reconciliation_matrix"):
            if not source.get(key):
                errors.append(f"source.{key} is required")
    return errors


def write_release_manifest(root: Path, manifest: Dict[str, Any]) -> Path:
    release_dir = root / "product" / "inner_world_v1" / "releases" / manifest["release_id"]
    ensure_dir(release_dir)
    path = release_dir / "manifest.json"
    write_json(path, manifest)
    return path


def evaluate_release_gates(required_checks: List[str], completed_checks: List[str]) -> Dict[str, Any]:
    completed = set(completed_checks)
    missing = [check for check in required_checks if check not in completed]
    return {
        "schema_version": "1.0",
        "status": "passed" if not missing else "blocked",
        "required_checks": list(required_checks),
        "completed_checks": list(completed_checks),
        "missing_checks": missing,
    }


def evaluate_codebase_freshness_gate(root: Path) -> Dict[str, Any]:
    """Block release claims when the codebase overview/manifest index is stale or incomplete."""

    from .codebase_overview import validate_codebase_index

    report = validate_codebase_index(root)
    missing_manifests = int(report.get("missing_manifest_count") or 0)
    error_count = int(report.get("error_count") or 0)
    warning_count = int(report.get("warning_count") or 0)
    fresh = bool(report.get("fresh"))
    blocked_reasons: List[str] = []
    if not fresh:
        blocked_reasons.extend(str(item) for item in report.get("stale_reasons") or [])
    if missing_manifests:
        blocked_reasons.append(f"missing_manifests={missing_manifests}")
    if error_count:
        blocked_reasons.append(f"manifest_errors={error_count}")
    if warning_count:
        blocked_reasons.append(f"manifest_warnings={warning_count}")
    deprecation = (
        root
        / "docs"
        / "workspaces"
        / "unified-framework-synthesis"
        / "derived"
        / "ADR-SHAPE-PROFILE-ID-DEPRECATION.md"
    )
    shape_deprecation_recorded = deprecation.is_file()
    if not shape_deprecation_recorded:
        blocked_reasons.append("shape_profile_deprecation_adr_missing")
    status = "passed" if not blocked_reasons else "blocked"
    return {
        "schema_version": "1.0",
        "status": status,
        "fresh": fresh,
        "missing_manifest_count": missing_manifests,
        "error_count": error_count,
        "warning_count": warning_count,
        "shape_profile_deprecation_recorded": shape_deprecation_recorded,
        "blocked_reasons": blocked_reasons,
        "recommended_hermetic_command": "pytest -m \"not live\"",
        "recommended_live_command": "pytest -m live",
        "default_wave0_checks": list(DEFAULT_WAVE0_RELEASE_CHECKS),
        "overview_report": {
            "module_manifest_count": report.get("module_manifest_count"),
            "newest_source_path": report.get("newest_source_path"),
            "newest_generated_path": report.get("newest_generated_path"),
        },
    }


def build_rollback_plan(current_release_id: str, previous_release_id: str) -> Dict[str, Any]:
    return {
        "schema_version": "1.0",
        "current_release_id": current_release_id,
        "target_release_id": previous_release_id,
        "status": "dry_run",
        "steps": [
            "restore_manifest",
            "restore_runtime_config",
            "restore_agent_configs",
            "restore_pwa_bundle_if_present",
            "restart_inner_world_service",
            "restart_openclaw_miniapps_if_needed",
            "run_post_rollback_smoke",
        ],
    }
