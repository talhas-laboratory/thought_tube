"""Staged ActiveState continuity rollout tied to receipt readiness (R-012)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .disclosure_rollout import ROLLOUT_MODES, in_canary_cohort, load_rollout_settings
from .storage import read_json


MODULE_ID = "kernel.disclosure.active_state_continuity_rollout"
CONTRACT_VERSION = "1.0"
CONTINUITY_SURFACES = ("bridge", "holodeck")

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "CONTINUITY_SURFACES",
    "load_continuity_rollout_settings",
    "resolve_surface_continuity_rollout_mode",
    "continuity_rollout_ready",
    "active_state_continuity_active",
)
__all__ = list(PUBLIC_API)


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def load_continuity_rollout_settings(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    active_state = disclosure.get("active_state", {}) or {}
    rollout = active_state.get("rollout", {}) or {}
    return {
        "bridge": str(rollout.get("bridge", "legacy") or "legacy").strip().lower(),
        "holodeck": str(rollout.get("holodeck", "legacy") or "legacy").strip().lower(),
    }


def resolve_surface_continuity_rollout_mode(root: Path, surface: str) -> str:
    normalized = str(surface or "bridge").strip().lower() or "bridge"
    settings = load_continuity_rollout_settings(root)
    mode = str(settings.get(normalized, "legacy") or "legacy").strip().lower()
    if mode not in ROLLOUT_MODES:
        return "legacy"
    return mode


def continuity_rollout_ready(root: Path) -> bool:
    from .disclosure_receipt_rollout import persistent_receipts_enabled_for_surface

    return persistent_receipts_enabled_for_surface(root, "bridge")


def active_state_continuity_active(
    root: Path,
    surface: str = "bridge",
    *,
    cohort_key: str = "",
) -> bool:
    from .active_state_continuity import load_active_state_config

    if not bool(load_active_state_config(root)["active_state_continuity_v1"]):
        return False
    if not continuity_rollout_ready(root):
        return False
    mode = resolve_surface_continuity_rollout_mode(root, surface)
    if mode == "legacy":
        return False
    if mode in {"enforced", "shadow"}:
        return True
    if mode == "canary":
        settings = load_rollout_settings(root)
        return in_canary_cohort(
            cohort_key or surface,
            percent=int(settings["canary_percent"]),
            salt=str(settings["canary_salt"]),
        )
    return False
