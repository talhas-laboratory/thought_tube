"""Staged receipt persistence rollout for disclosure surfaces (R-011)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping

from .disclosure_rollout import ROLLOUT_MODES, in_canary_cohort, load_rollout_settings
from .storage import read_json, utc_now, write_json


MODULE_ID = "kernel.disclosure.receipt_rollout"
CONTRACT_VERSION = "1.0"
RECEIPT_SURFACES = ("bridge", "holodeck", "feed", "task_pack")
# T10-08: Bridge receipt shadow activates even when release config still says legacy.
T10_08_BRIDGE_RECEIPT_SHADOW_ACTIVATION = True

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "RECEIPT_SURFACES",
    "T10_08_BRIDGE_RECEIPT_SHADOW_ACTIVATION",
    "load_receipt_rollout_settings",
    "resolve_surface_receipt_rollout_mode",
    "persistent_receipts_enabled_for_surface",
    "retention_limit_for_mode",
    "record_receipt_health_issue",
    "inspect_receipt_store_health",
)
__all__ = list(PUBLIC_API)

_RETENTION_LIMITS = {
    "normal_policy": 1.0,
    "minimal": 0.5,
    "hashes_metrics_only": 0.25,
}


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def _receipt_health_path(root: Path) -> Path:
    return (
        root
        / "product"
        / "inner_world_v1"
        / "data"
        / "reasoning_runtime"
        / "disclosure_receipt_health.json"
    )


def load_receipt_rollout_settings(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    receipts = disclosure.get("receipts", {}) or {}
    rollout = receipts.get("rollout", {}) or {}
    bridge_default = "shadow" if T10_08_BRIDGE_RECEIPT_SHADOW_ACTIVATION else "enforced"
    return {
        "bridge": str(rollout.get("bridge", bridge_default) or bridge_default).strip().lower(),
        "holodeck": str(rollout.get("holodeck", "legacy") or "legacy").strip().lower(),
        "feed": str(rollout.get("feed", "legacy") or "legacy").strip().lower(),
        "task_pack": str(rollout.get("task_pack", "legacy") or "legacy").strip().lower(),
        "bridge_force_legacy": bool(rollout.get("bridge_force_legacy", False)),
    }


def resolve_surface_receipt_rollout_mode(root: Path, surface: str) -> str:
    normalized = str(surface or "bridge").strip().lower() or "bridge"
    settings = load_receipt_rollout_settings(root)
    mode = str(settings.get(normalized, "legacy") or "legacy").strip().lower()
    if mode not in ROLLOUT_MODES:
        return "legacy"
    if (
        T10_08_BRIDGE_RECEIPT_SHADOW_ACTIVATION
        and normalized == "bridge"
        and mode == "legacy"
        and not bool(settings.get("bridge_force_legacy", False))
    ):
        return "shadow"
    return mode


def persistent_receipts_enabled_for_surface(
    root: Path,
    surface: str,
    *,
    cohort_key: str = "",
) -> bool:
    from .disclosure_receipts import load_receipt_config

    mode = resolve_surface_receipt_rollout_mode(root, surface)
    if mode == "legacy":
        return False
    # T10-08 Bridge shadow: enable surface persistence without requiring global flag.
    normalized = str(surface or "bridge").strip().lower() or "bridge"
    if T10_08_BRIDGE_RECEIPT_SHADOW_ACTIVATION and normalized == "bridge" and mode == "shadow":
        return True
    if not bool(load_receipt_config(root)["persistent_receipts_v1"]):
        return False
    if mode == "enforced":
        return True
    if mode == "shadow":
        return True
    if mode == "canary":
        settings = load_rollout_settings(root)
        return in_canary_cohort(
            cohort_key or surface,
            percent=int(settings["canary_percent"]),
            salt=str(settings["canary_salt"]),
        )
    return False


def retention_limit_for_mode(retention_mode: str, *, max_entries: int) -> int:
    factor = _RETENTION_LIMITS.get(str(retention_mode or "normal_policy"), 1.0)
    return max(1, int(max_entries * factor))


def record_receipt_health_issue(
    root: Path,
    *,
    issue_code: str,
    detail: str = "",
    surface: str = "",
) -> Dict[str, Any]:
    path = _receipt_health_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = read_json(path, default={}) or {}
    issues = list(payload.get("issues", []) or [])
    issues.append(
        {
            "recorded_at": utc_now(),
            "issue_code": str(issue_code or "unknown"),
            "detail": str(detail or ""),
            "surface": str(surface or ""),
        }
    )
    payload = {
        "updated_at": utc_now(),
        "issues": issues[-50:],
        "last_issue_code": str(issue_code or "unknown"),
    }
    write_json(path, payload)
    return payload


def inspect_receipt_store_health(root: Path) -> Dict[str, Any]:
    from .disclosure_receipts import disclosure_receipts_path, load_receipt_rows

    path = disclosure_receipts_path(root)
    health = read_json(_receipt_health_path(root), default={}) or {}
    rows, corrupt = load_receipt_rows(root, repair=True)
    lag = 0
    if rows:
        lag = max(0, len(rows))
    return {
        "store_path": str(path),
        "row_count": len(rows),
        "corrupt_row_count": len(corrupt),
        "retention_lag_rows": lag,
        "last_issue_code": str(health.get("last_issue_code", "") or ""),
        "recent_issues": list(health.get("issues", []) or [])[-5:],
        "healthy": not corrupt and not str(health.get("last_issue_code", "") or "").strip(),
    }
