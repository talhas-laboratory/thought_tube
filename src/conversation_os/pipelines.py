from __future__ import annotations

from pathlib import Path

from .storage import ensure_dir, read_json, write_json


DEFAULT_PIPELINES = {
    "vault_decomposition_v1": {
        "pipeline_id": "vault_decomposition_v1",
        "description": "Turn one vault chunk into a reviewable meta-layer packet.",
        "steps": [
            "normalize_capture",
            "infer_capture_context",
            "clarify_core_meaning",
            "separate_layers",
            "detect_shared_primitive",
            "build_why_it_matters",
        ],
    },
    "cross_pollination_v1": {
        "pipeline_id": "cross_pollination_v1",
        "description": "Find a meaningful connection between two knowledge-layer regions.",
        "steps": [
            "clarify_connection_context",
            "detect_connection_primitive",
            "detect_connection_tension",
            "build_connection_why_it_matters",
            "build_connection_candidate",
        ],
    },
    "thought_surfacing_v1": {
        "pipeline_id": "thought_surfacing_v1",
        "description": "Judge whether a connection deserves to become a surfaced thought.",
        "steps": [
            "fidelity_check",
            "genericity_filter",
            "confidence_calibration",
            "relevance_check",
            "review_gate",
        ],
    },
}


def pipeline_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "pipelines"


def ensure_pipeline_specs(root: Path) -> dict:
    directory = pipeline_dir(root)
    ensure_dir(directory)
    for pipeline_id, payload in DEFAULT_PIPELINES.items():
        path = directory / f"{pipeline_id}.json"
        if not path.exists():
            write_json(path, payload)
    return {"path": str(directory), "count": len(DEFAULT_PIPELINES)}


def load_pipeline_spec(root: Path, pipeline_id: str) -> dict:
    ensure_pipeline_specs(root)
    path = pipeline_dir(root) / f"{pipeline_id}.json"
    payload = read_json(path)
    if payload is None:
        raise KeyError(pipeline_id)
    return payload
