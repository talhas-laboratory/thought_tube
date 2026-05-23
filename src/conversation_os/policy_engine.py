from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .storage import read_json, write_json


MODULE_ID = "kernel.policy.policy_engine"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "policy_snapshot_path",
    "update_policy_snapshot",
    "load_policy_snapshot",
)
__all__ = list(PUBLIC_API)


def policy_snapshot_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "policy_snapshot.json"


def update_policy_snapshot(root: Path, feedback_events: List[Dict]) -> Dict:
    snapshot = {
        "feedback_count": len(feedback_events),
        "dismiss_count": sum(1 for row in feedback_events if row.get("feedback_state") == "dismiss"),
        "relevant_count": sum(1 for row in feedback_events if row.get("feedback_state") == "relevant"),
        "revisit_count": sum(1 for row in feedback_events if row.get("feedback_state") == "revisit_later"),
        "save_count": sum(1 for row in feedback_events if row.get("feedback_state") == "saved"),
    }
    snapshot["dismiss_bias"] = round(min(0.35, snapshot["dismiss_count"] * 0.04), 2)
    snapshot["relevance_bias"] = round(min(0.35, snapshot["relevant_count"] * 0.04), 2)
    write_json(policy_snapshot_path(root), snapshot)
    return snapshot


def load_policy_snapshot(root: Path) -> Dict:
    return read_json(policy_snapshot_path(root), default={})
