from __future__ import annotations

from pathlib import Path

from .storage import ensure_dir, read_json, write_json


MODULE_ID = "assembly.runtime.pipelines"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "DEFAULT_PIPELINES",
    "pipeline_dir",
    "ensure_pipeline_specs",
    "load_pipeline_spec",
)
__all__ = list(PUBLIC_API)


DEFAULT_PIPELINES = {
    "idea_embedding_v1": {
        "pipeline_id": "idea_embedding_v1",
        "description": "Take a live fragment and place it into the most plausible larger idea structure.",
        "steps": [
            "classify_fragment_role",
            "identify_parent_ideas",
            "activate_dimensions",
            "generate_candidate_transformations",
            "score_candidate_transformations",
            "choose_probe_or_integration",
            "build_user_response",
        ],
    },
    "problem_reframing_v1": {
        "pipeline_id": "problem_reframing_v1",
        "description": "Handle high-ambiguity fragments by probing framing before premature integration.",
        "steps": [
            "classify_fragment_role",
            "identify_parent_ideas",
            "activate_dimensions",
            "generate_candidate_transformations",
            "score_candidate_transformations",
            "choose_probe_or_integration",
            "build_user_response",
        ],
    },
    "candidate_evaluation_v1": {
        "pipeline_id": "candidate_evaluation_v1",
        "description": "Judge an existing candidate direction for fit, novelty, and next action.",
        "steps": [
            "classify_fragment_role",
            "identify_parent_ideas",
            "activate_dimensions",
            "generate_candidate_transformations",
            "score_candidate_transformations",
            "choose_probe_or_integration",
            "build_user_response",
        ],
    },
    "intuition_expansion_v1": {
        "pipeline_id": "intuition_expansion_v1",
        "description": "Expand an intuitive or interpretive fragment into adjacent meanings without collapsing the spark too early.",
        "steps": [
            "classify_fragment_role",
            "identify_parent_ideas",
            "activate_dimensions",
            "generate_candidate_transformations",
            "score_candidate_transformations",
            "choose_probe_or_integration",
            "build_user_response",
        ],
    },
    "symbolic_interpretation_v1": {
        "pipeline_id": "symbolic_interpretation_v1",
        "description": "Interpret a symbolic fragment by mapping latent meanings and adjacent associations without forcing a single literal reading.",
        "steps": [
            "classify_fragment_role",
            "identify_parent_ideas",
            "activate_dimensions",
            "generate_candidate_transformations",
            "score_candidate_transformations",
            "choose_probe_or_integration",
            "build_user_response",
        ],
    },
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
