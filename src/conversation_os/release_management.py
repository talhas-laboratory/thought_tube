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
    "build_rollback_plan",
)
__all__ = list(PUBLIC_API)


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


def build_release_manifest(root: Path, release_id: str | None = None) -> Dict[str, Any]:
    resolved_release_id = release_id or "inner-world-" + utc_now().replace(":", "").replace("-", "")
    artifact_paths = {
        "backend": ["src/conversation_os", "tools"],
        "runtime_config": ["product/inner_world_v1/config/runtime.json"],
        "agent_configs": ["product/inner_world_v1/config/agent_configs"],
        "bridge_behaviors": ["product/inner_world_v1/config/bridge_behaviors"],
        "pipelines": ["product/inner_world_v1/pipelines"],
        "pwa_bundle": ["product/thought_capture_pwa/dist"],
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
        },
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
