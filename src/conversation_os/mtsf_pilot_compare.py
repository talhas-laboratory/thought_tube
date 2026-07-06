from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .storage import ensure_dir, read_json, session_dir, utc_now, write_json

MODULE_ID = "kernel.mtsf.pilot_compare"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "default_pilot_002_paths",
    "snapshot_baseline",
    "summarize_baseline_third_space",
    "summarize_pipeline_session",
    "compare_extractions",
    "run_pipeline_replay",
    "run_pilot_002_comparison",
    "write_comparison_markdown",
)
__all__ = list(PUBLIC_API)


def default_pilot_002_paths(root: Path) -> Dict[str, Path]:
    sandbox = root / "sandbox" / "2026-07-05-metaphysical-thought-space"
    sources_manifest = read_json(sandbox / "sources" / "manifest.json", default={"sources": []})
    source_row = next(
        (row for row in sources_manifest.get("sources", []) if row.get("id") == "source-gemini-2026-05-07"),
        {},
    )
    source_path = Path(str(source_row.get("original_upload", "")))
    if not source_path.exists():
        uploads = Path("/home/ubuntu/.cursor/projects/workspace/uploads/2026-05-07_you-said_ca8c.md")
        if uploads.exists():
            source_path = uploads
    experiment_dir = sandbox / "experiments" / "pilot-002-pipeline-replay"
    return {
        "sandbox": sandbox,
        "baseline_third_space": sandbox
        / "experiments"
        / "pilot-002-latent-topology-cognitive-system"
        / "third-space.json",
        "source_path": source_path,
        "legacy_session_id": str(source_row.get("import_session_id", "import-69ea1f64f744")),
        "experiment_dir": experiment_dir,
    }


def snapshot_baseline(root: Path, *, experiment_dir: Optional[Path] = None) -> Dict[str, Any]:
    paths = default_pilot_002_paths(root)
    baseline_path = paths["baseline_third_space"]
    if not baseline_path.exists():
        raise FileNotFoundError(f"baseline not found: {baseline_path}")

    out_dir = (experiment_dir or paths["experiment_dir"]) / "baseline_snapshot"
    ensure_dir(out_dir)
    snapshot_path = out_dir / "third-space.json"
    shutil.copy2(baseline_path, snapshot_path)
    manifest = {
        "snapshot_id": "pilot-002-baseline",
        "snapshot_at": utc_now(),
        "source_artifact": str(baseline_path),
        "snapshot_path": str(snapshot_path),
        "method": "manual Formation Agent pass (Pilot 002)",
        "import_session_id": paths["legacy_session_id"],
        "title": "You said — Latent Space Topology and Cognitive System",
    }
    write_json(out_dir / "snapshot_manifest.json", manifest)
    return {
        "snapshot_dir": str(out_dir),
        "snapshot_path": str(snapshot_path),
        "manifest_path": str(out_dir / "snapshot_manifest.json"),
        "summary": summarize_baseline_third_space(read_json(snapshot_path)),
    }


def summarize_baseline_third_space(payload: Dict[str, Any]) -> Dict[str, Any]:
    entities = payload.get("entities", [])
    relations = payload.get("relations", [])
    snapshots = payload.get("activation_snapshots", [])
    pattern = payload.get("candidate_pattern", {})
    return {
        "artifact_type": "third_space",
        "entity_ids": [str(row.get("id", "")) for row in entities],
        "entity_names": [str(row.get("name", "")) for row in entities],
        "entity_count": len(entities),
        "relation_count": len(relations),
        "relation_signatures": [
            _relation_signature(
                str(row.get("source", "")),
                str(row.get("target", "")),
                str(row.get("primitive", "")),
            )
            for row in relations
        ],
        "activation_snapshot_count": len(snapshots),
        "candidate_pattern_id": pattern.get("id"),
        "candidate_pattern_names": pattern.get("possible_names", []),
        "dominant_tension": payload.get("intake_assessment", {}).get("dominant_tension"),
        "confidence": pattern.get("confidence_score") or payload.get("intake_assessment", {}).get("confidence"),
        "stencil_count": 0,
        "stencil_ids": [],
    }


def _relation_signature(source: str, target: str, primitive: str) -> str:
    return f"{source}|{primitive}|{target}"


def summarize_pipeline_session(root: Path, session_id: str) -> Dict[str, Any]:
    base = session_dir(root, session_id)
    draft_path = base / "mtsf" / "extraction_draft.json"
    shape_index_path = base / "mtsf" / "shape_index.json"
    activation_path = base / "mtsf" / "activation_snapshot.json"
    projection_path = base / "mtsf" / "stencil_projection.json"

    draft = read_json(draft_path, default={}) if draft_path.exists() else {}
    shape_index = read_json(shape_index_path, default={}) if shape_index_path.exists() else {}
    activation = read_json(activation_path, default={}) if activation_path.exists() else {}
    projection = read_json(projection_path, default={}) if projection_path.exists() else {}

    entities = draft.get("entities", [])
    relations = draft.get("relations", [])
    candidate_shapes = draft.get("candidate_shapes", [])
    stencil_drafts = draft.get("stencil_drafts", [])
    active_stencil_ids = projection.get("active_stencil_ids") or shape_index.get("stencils", {}).keys()

    return {
        "artifact_type": "mtsf_pipeline",
        "session_id": session_id,
        "capture_mode": draft.get("capture_mode"),
        "extraction_source": draft.get("provenance", {}).get("model_id"),
        "entity_ids": [str(row.get("proposed_id", "")) for row in entities],
        "entity_names": [str(row.get("name", "")) for row in entities],
        "entity_count": len(entities),
        "relation_count": len(relations),
        "relation_signatures": [
            _relation_signature(
                str(row.get("source_ref", "")),
                str(row.get("target_ref", "")),
                str(row.get("primitive", "")),
            )
            for row in relations
        ],
        "quality_count": len(draft.get("qualities", [])),
        "quality_role_count": len(draft.get("quality_roles", [])),
        "candidate_shape_ids": [str(row.get("proposed_id", "")) for row in candidate_shapes],
        "candidate_shape_names": [
            str((row.get("possible_names") or [""])[0]) for row in candidate_shapes
        ],
        "stencil_draft_count": len(stencil_drafts),
        "stencil_draft_names": [str(row.get("proposed_name", "")) for row in stencil_drafts],
        "active_stencil_ids": sorted(str(value) for value in active_stencil_ids),
        "stencil_count": len(shape_index.get("stencils", {})),
        "shape_instance_count": len(shape_index.get("instances", [])),
        "activation_entity_count": len(activation.get("active_entities", [])),
        "confidence": draft.get("confidence"),
        "promotion_ready": draft.get("quarantine", {}).get("promotion_ready"),
        "validation_ok": draft.get("validation", {}).get("ok"),
        "artifact_paths": {
            "extraction_draft": str(draft_path) if draft_path.exists() else None,
            "shape_index": str(shape_index_path) if shape_index_path.exists() else None,
            "activation_snapshot": str(activation_path) if activation_path.exists() else None,
            "stencil_projection": str(projection_path) if projection_path.exists() else None,
        },
    }


def _name_slug(value: str) -> str:
    return value.strip().lower().replace(" ", "-")


def compare_extractions(baseline: Dict[str, Any], pipeline: Dict[str, Any]) -> Dict[str, Any]:
    baseline_entity_ids = set(baseline.get("entity_ids", []))
    pipeline_entity_ids = set(pipeline.get("entity_ids", []))
    entity_id_overlap = sorted(baseline_entity_ids & pipeline_entity_ids)
    entity_id_missing = sorted(baseline_entity_ids - pipeline_entity_ids)
    entity_id_novel = sorted(pipeline_entity_ids - baseline_entity_ids)

    baseline_names = {_name_slug(name) for name in baseline.get("entity_names", []) if name}
    pipeline_names = {_name_slug(name) for name in pipeline.get("entity_names", []) if name}
    entity_name_overlap = sorted(baseline_names & pipeline_names)

    baseline_rel = set(baseline.get("relation_signatures", []))
    pipeline_rel = set(pipeline.get("relation_signatures", []))
    relation_overlap = sorted(baseline_rel & pipeline_rel)
    relation_missing = sorted(baseline_rel - pipeline_rel)
    relation_novel = sorted(pipeline_rel - baseline_rel)

    return {
        "baseline_artifact": baseline.get("artifact_type"),
        "pipeline_artifact": pipeline.get("artifact_type"),
        "pipeline_mode": pipeline.get("capture_mode"),
        "pipeline_source": pipeline.get("extraction_source"),
        "counts": {
            "baseline_entities": baseline.get("entity_count", 0),
            "pipeline_entities": pipeline.get("entity_count", 0),
            "baseline_relations": baseline.get("relation_count", 0),
            "pipeline_relations": pipeline.get("relation_count", 0),
            "pipeline_qualities": pipeline.get("quality_count", 0),
            "pipeline_quality_roles": pipeline.get("quality_role_count", 0),
            "pipeline_stencil_drafts": pipeline.get("stencil_draft_count", 0),
            "pipeline_active_stencils": len(pipeline.get("active_stencil_ids", [])),
            "baseline_activation_snapshots": baseline.get("activation_snapshot_count", 0),
            "pipeline_shape_instances": pipeline.get("shape_instance_count", 0),
        },
        "entities": {
            "id_overlap": entity_id_overlap,
            "id_overlap_count": len(entity_id_overlap),
            "id_missing_from_pipeline": entity_id_missing,
            "id_novel_in_pipeline": entity_id_novel,
            "name_overlap": entity_name_overlap,
            "name_overlap_count": len(entity_name_overlap),
            "recall_by_id": _safe_ratio(len(entity_id_overlap), len(baseline_entity_ids)),
            "precision_by_id": _safe_ratio(len(entity_id_overlap), len(pipeline_entity_ids)),
        },
        "relations": {
            "overlap": relation_overlap,
            "overlap_count": len(relation_overlap),
            "missing_from_pipeline": relation_missing,
            "novel_in_pipeline": relation_novel,
            "recall": _safe_ratio(len(relation_overlap), len(baseline_rel)),
        },
        "patterns": {
            "baseline_candidate_pattern_id": baseline.get("candidate_pattern_id"),
            "baseline_candidate_names": baseline.get("candidate_pattern_names", []),
            "pipeline_candidate_shape_ids": pipeline.get("candidate_shape_ids", []),
            "pipeline_candidate_shape_names": pipeline.get("candidate_shape_names", []),
            "pipeline_active_stencil_ids": pipeline.get("active_stencil_ids", []),
            "baseline_had_stencils": baseline.get("stencil_count", 0) > 0,
            "pipeline_has_stencils": pipeline.get("stencil_count", 0) > 0,
        },
        "confidence": {
            "baseline": baseline.get("confidence"),
            "pipeline": pipeline.get("confidence"),
            "pipeline_promotion_ready": pipeline.get("promotion_ready"),
            "pipeline_validation_ok": pipeline.get("validation_ok"),
        },
        "gaps_closed": _gaps_closed(baseline, pipeline),
    }


def _safe_ratio(numerator: int, denominator: int) -> Optional[float]:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 4)


def _gaps_closed(baseline: Dict[str, Any], pipeline: Dict[str, Any]) -> List[str]:
    closed: List[str] = []
    if baseline.get("stencil_count", 0) == 0 and pipeline.get("stencil_count", 0) > 0:
        closed.append("machine_readable_stencil_schema")
    if pipeline.get("relation_count", 0) > 0:
        closed.append("typed_relation_edges_in_pipeline")
    if pipeline.get("active_stencil_ids"):
        closed.append("seed_stencil_projection")
    if pipeline.get("shape_instance_count", 0) > 0:
        closed.append("shape_instance_bindings")
    return closed


def run_pipeline_replay(
    root: Path,
    *,
    source_path: Path,
    session_id: str,
    title: str,
    mode: str = "deep",
    llm_preference: str = "off",
    domains: str = "research,topology",
) -> Dict[str, Any]:
    from .cli import session_import

    if not source_path.exists():
        raise FileNotFoundError(f"source transcript not found: {source_path}")

    result = session_import(
        root,
        type(
            "Args",
            (),
            {
                "source_path": str(source_path),
                "title": title,
                "session_id": session_id,
                "participants": "importer",
                "source_type": "imported_transcript",
                "domains": domains,
                "tags": "pilot-002,pipeline-replay",
                "task_id": None,
                "request": title,
                "task_type": "pilot_compare",
                "mtsf_mode": mode,
                "mtsf_llm": llm_preference,
            },
        )(),
    )
    return {
        "session_id": session_id,
        "mode": mode,
        "llm_preference": llm_preference,
        "import_result": result,
        "summary": summarize_pipeline_session(root, session_id),
    }


def write_comparison_markdown(comparison_payload: Dict[str, Any]) -> str:
    lines = [
        "# Pilot 002 — Baseline vs MTSF Pipeline Comparison",
        "",
        f"Generated: {comparison_payload.get('generated_at', '')}",
        "",
        "## Baseline",
        "",
        f"- Artifact: Pilot 002 `third-space.json` (manual Formation Agent pass)",
        f"- Entities: {comparison_payload['baseline']['entity_count']}",
        f"- Relations: {comparison_payload['baseline']['relation_count']}",
        f"- Activation snapshots: {comparison_payload['baseline'].get('activation_snapshot_count', 0)}",
        f"- Candidate pattern: `{comparison_payload['baseline'].get('candidate_pattern_id', '')}`",
        "",
    ]
    for mode, block in comparison_payload.get("pipeline_runs", {}).items():
        cmp = block["comparison"]
        counts = cmp["counts"]
        lines.extend(
            [
                f"## Pipeline replay — `{mode}`",
                "",
                f"- Session: `{block['session_id']}`",
                f"- Extraction source: `{block['summary'].get('extraction_source', '')}`",
                f"- Entities: {counts['pipeline_entities']} (baseline recall by id: {cmp['entities']['recall_by_id']})",
                f"- Relations: {counts['pipeline_relations']} (baseline recall: {cmp['relations']['recall']})",
                f"- Active stencils: {', '.join(block['summary'].get('active_stencil_ids', [])) or 'none'}",
                f"- Promotion ready: {cmp['confidence'].get('pipeline_promotion_ready')}",
                "",
                "### Entity overlap (ids)",
                "",
            ]
        )
        overlap = cmp["entities"]["id_overlap"]
        lines.append(", ".join(f"`{item}`" for item in overlap) if overlap else "_none_")
        lines.extend(["", "### Entities in baseline but not pipeline", ""])
        missing = cmp["entities"]["id_missing_from_pipeline"]
        lines.append(", ".join(f"`{item}`" for item in missing) if missing else "_none_")
        lines.extend(["", "### Novel entities in pipeline", ""])
        novel = cmp["entities"]["id_novel_in_pipeline"]
        lines.append(", ".join(f"`{item}`" for item in novel) if novel else "_none_")
        lines.extend(["", "### Gaps closed by pipeline", ""])
        gaps = cmp.get("gaps_closed", [])
        lines.append("\n".join(f"- {gap}" for gap in gaps) if gaps else "_none identified_")
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def run_pilot_002_comparison(
    root: Path,
    *,
    modes: Optional[Sequence[Tuple[str, str]]] = None,
    llm_preference: str = "off",
    rerun: bool = True,
) -> Dict[str, Any]:
    paths = default_pilot_002_paths(root)
    experiment_dir = paths["experiment_dir"]
    ensure_dir(experiment_dir)

    snapshot = snapshot_baseline(root, experiment_dir=experiment_dir)
    baseline_summary = snapshot["summary"]

    selected_modes = list(modes or (("fast", "off"), ("deep", "off")))
    pipeline_runs: Dict[str, Any] = {}

    for mode, mode_llm in selected_modes:
        session_id = f"pilot-002-replay-{mode}"
        replay_dir = experiment_dir / f"replay-{mode}"
        ensure_dir(replay_dir)

        if rerun or not (session_dir(root, session_id) / "mtsf" / "extraction_draft.json").exists():
            replay = run_pipeline_replay(
                root,
                source_path=paths["source_path"],
                session_id=session_id,
                title=f"Pilot 002 replay ({mode})",
                mode=mode,
                llm_preference=mode_llm or llm_preference,
            )
        else:
            replay = {
                "session_id": session_id,
                "mode": mode,
                "llm_preference": mode_llm or llm_preference,
                "summary": summarize_pipeline_session(root, session_id),
            }

        pipeline_summary = replay["summary"]
        comparison = compare_extractions(baseline_summary, pipeline_summary)

        run_payload = {
            "session_id": session_id,
            "mode": mode,
            "summary": pipeline_summary,
            "comparison": comparison,
        }
        write_json(replay_dir / "pipeline_summary.json", pipeline_summary)
        write_json(replay_dir / "comparison.json", comparison)
        pipeline_runs[mode] = run_payload

        session_base = session_dir(root, session_id) / "mtsf"
        if session_base.exists():
            for artifact in session_base.glob("*.json"):
                shutil.copy2(artifact, replay_dir / artifact.name)

    payload = {
        "experiment_id": "pilot-002-pipeline-replay",
        "generated_at": utc_now(),
        "baseline_snapshot": snapshot,
        "baseline": baseline_summary,
        "source_path": str(paths["source_path"]),
        "legacy_session_id": paths["legacy_session_id"],
        "pipeline_runs": pipeline_runs,
    }
    write_json(experiment_dir / "comparison.json", payload)
    markdown = write_comparison_markdown(payload)
    (experiment_dir / "comparison.md").write_text(markdown, encoding="utf-8")
    payload["comparison_markdown_path"] = str(experiment_dir / "comparison.md")
    payload["comparison_json_path"] = str(experiment_dir / "comparison.json")
    return payload
