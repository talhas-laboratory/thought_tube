from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Dict

from .cost_tracker import estimate_token_count, record_equivalent_cost
from .operators import OPERATOR_REGISTRY
from .pipelines import load_pipeline_spec
from .storage import ensure_dir, make_id, utc_now, write_json


MODULE_ID = "assembly.runtime.pipeline_runner"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "run_pipeline",
)
__all__ = list(PUBLIC_API)


def _merge_patch(target: Dict, patch: Dict) -> Dict:
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge_patch(target[key], value)
        else:
            target[key] = value
    return target


def _runs_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "runs"


def run_pipeline(
    root: Path,
    pipeline_id: str,
    packet: Dict,
    context: Dict | None = None,
) -> Dict:
    spec = load_pipeline_spec(root, pipeline_id)
    packet = deepcopy(packet)
    input_snapshot = deepcopy(packet)
    packet.setdefault("run_meta", {})
    packet["run_meta"].update(
        {
            "run_id": packet["run_meta"].get("run_id") or make_id("run"),
            "pipeline_id": pipeline_id,
            "started_at": packet["run_meta"].get("started_at") or utc_now(),
        }
    )
    packet.setdefault("operator_trace", [])
    context = context or {}

    trace = []
    for step in spec["steps"]:
        operator = OPERATOR_REGISTRY[step]
        patch = operator(packet, context) or {}
        _merge_patch(packet, patch)
        trace_entry = {
            "step": step,
            "timestamp": utc_now(),
            "writes": sorted(patch.keys()),
        }
        packet["operator_trace"].append(trace_entry)
        trace.append(trace_entry)

    packet["run_meta"]["completed_at"] = utc_now()
    run_dir = ensure_dir(_runs_dir(root) / packet["run_meta"]["run_id"])
    write_json(run_dir / "run_packet.json", packet)
    write_json(run_dir / "trace.json", trace)
    write_json(
        run_dir / "review.json",
        {
            "run_id": packet["run_meta"]["run_id"],
            "pipeline_id": pipeline_id,
            "review_status": packet.get("memory_commit", {}).get("review_status"),
            "next_action": packet.get("memory_commit", {}).get("next_action"),
        },
    )
    record_equivalent_cost(
        root,
        component="pipeline",
        operation=pipeline_id,
        input_tokens=estimate_token_count(input_snapshot),
        output_tokens=estimate_token_count(packet),
        metadata={
            "run_id": packet["run_meta"]["run_id"],
            "step_count": len(spec["steps"]),
        },
    )
    return packet
