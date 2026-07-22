"""Disclosure shared-service rollout modes for primary surfaces (R-004)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Mapping

from .storage import append_jsonl, read_json, utc_now


MODULE_ID = "kernel.disclosure.disclosure_rollout"
CONTRACT_VERSION = "1.0"
ROLLOUT_MODES = ("legacy", "shadow", "canary", "enforced")
PRIMARY_SURFACES = ("bridge", "holodeck")

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "ROLLOUT_MODES",
    "PRIMARY_SURFACES",
    "load_rollout_settings",
    "resolve_surface_rollout_mode",
    "resolve_execution_path",
    "shared_path_active",
    "in_canary_cohort",
    "compare_bridge_rollout_bundles",
    "compare_holodeck_knowledge_subsets",
    "record_rollout_shadow_receipt",
)
__all__ = list(PUBLIC_API)


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def _rollout_shadow_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "disclosure_rollout_shadow.jsonl"


def load_rollout_settings(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    rollout = disclosure.get("rollout", {}) or {}
    return {
        "canary_percent": max(0, min(100, int(rollout.get("canary_percent", 0) or 0))),
        "canary_salt": str(rollout.get("canary_salt", "cae-disclosure-v1") or "cae-disclosure-v1"),
    }


def _legacy_boolean_for_surface(runtime: Mapping[str, Any], surface: str) -> bool:
    disclosure = runtime.get("disclosure", {}) or {}
    surface_cfg = dict(runtime.get(surface, {}) or {})
    if surface == "bridge":
        return bool(
            surface_cfg.get(
                "disclosure_service_v1",
                disclosure.get("disclosure_service_v1", False),
            )
        )
    if surface == "holodeck":
        return bool(
            surface_cfg.get(
                "disclosure_service_v1",
                disclosure.get("holodeck_disclosure_service_v1", False),
            )
        )
    return False


def resolve_surface_rollout_mode(root: Path, surface: str) -> str:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    rollout = disclosure.get("rollout", {}) or {}
    surface_cfg = dict(runtime.get(surface, {}) or {})

    mode = str(
        surface_cfg.get("disclosure_rollout_v1", "")
        or rollout.get(surface, "")
        or ""
    ).strip().lower()
    if not mode:
        mode = "enforced" if _legacy_boolean_for_surface(runtime, surface) else "legacy"
    if mode not in ROLLOUT_MODES:
        return "legacy"
    return mode


def in_canary_cohort(cohort_key: str, *, percent: int, salt: str) -> bool:
    if percent <= 0:
        return False
    if percent >= 100:
        return True
    key = str(cohort_key or "").strip() or "default"
    digest = hashlib.sha256(f"{salt}:{key}".encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) % 100
    return bucket < percent


def resolve_execution_path(root: Path, surface: str, *, cohort_key: str = "") -> str:
    mode = resolve_surface_rollout_mode(root, surface)
    if mode == "legacy":
        return "legacy"
    if mode == "enforced":
        return "shared"
    if mode == "shadow":
        return "shadow"
    if mode == "canary":
        settings = load_rollout_settings(root)
        if in_canary_cohort(
            cohort_key,
            percent=int(settings["canary_percent"]),
            salt=str(settings["canary_salt"]),
        ):
            return "shared"
        return "legacy"
    return "legacy"


def shared_path_active(root: Path, surface: str, *, cohort_key: str = "") -> bool:
    return resolve_execution_path(root, surface, cohort_key=cohort_key) == "shared"


def _global_retrieval_subset(bundle: Mapping[str, Any]) -> Dict[str, Any]:
    global_fallback = dict(bundle.get("global_fallback", {}) or {})
    capsule_ids = sorted(
        {
            str(row.get("capsule_id", "") or "").strip()
            for row in list(global_fallback.get("seed_capsules", []) or [])
            + list(global_fallback.get("related_capsules", []) or [])
            if str(row.get("capsule_id", "") or "").strip()
        }
    )
    return {
        "count": int(global_fallback.get("count", 0) or 0),
        "result_status": str(bundle.get("result_status", "") or global_fallback.get("result_status", "") or ""),
        "capsule_ids": capsule_ids,
    }


def compare_bridge_rollout_bundles(legacy: Mapping[str, Any], shared: Mapping[str, Any]) -> Dict[str, Any]:
    legacy_subset = _global_retrieval_subset(legacy)
    shared_subset = _global_retrieval_subset(shared)
    return {
        "parity_match": legacy_subset == shared_subset,
        "legacy_subset": legacy_subset,
        "shared_subset": shared_subset,
    }


def compare_holodeck_knowledge_subsets(
    legacy_candidates: list[dict],
    shared_candidates: list[dict],
) -> Dict[str, Any]:
    def subset(rows: list[dict]) -> Dict[str, Any]:
        knowledge = [row for row in rows if row.get("candidate_kind") == "knowledge"]
        return {
            "count": len(knowledge),
            "source_layers": sorted(
                {
                    str(row.get("source_layer", "") or "").strip()
                    for row in knowledge
                    if str(row.get("source_layer", "") or "").strip()
                }
            ),
            "capsule_ids": sorted(
                {
                    str(row.get("capsule_id", "") or "").strip()
                    for row in knowledge
                    if str(row.get("capsule_id", "") or "").strip()
                }
            ),
        }

    legacy_subset = subset(legacy_candidates)
    shared_subset = subset(shared_candidates)
    return {
        "parity_match": legacy_subset == shared_subset,
        "legacy_subset": legacy_subset,
        "shared_subset": shared_subset,
    }


def record_rollout_shadow_receipt(
    root: Path,
    comparison: Mapping[str, Any],
    *,
    surface: str,
    cohort_key: str = "",
) -> Dict[str, Any]:
    row = {
        "recorded_at": utc_now(),
        "surface": surface,
        "cohort_key": str(cohort_key or ""),
        "mode": "shadow",
        "comparison": dict(comparison),
    }
    append_jsonl(_rollout_shadow_path(root), row)
    return row
