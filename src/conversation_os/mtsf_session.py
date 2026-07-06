from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .mtsf_kernel import (
    ActivationContext,
    EntityActivationRecord,
    activate,
    build_activation_snapshot,
    load_seed_conditions,
)
from .storage import ensure_dir, make_id, read_json, read_jsonl, session_dir, session_events_path, write_json

MODULE_ID = "kernel.mtsf.session"
CONTRACT_VERSION = "1.1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "SessionActivationSignals",
    "default_entity_catalog_path",
    "load_entity_catalog",
    "infer_session_signals",
    "build_entity_context",
    "materialize_session_mtsf",
    "mtsf_framework_available",
)
__all__ = list(PUBLIC_API)

ANCHOR_TERMS = (
    "topology",
    "latent",
    "symmetry",
    "isomorph",
    "context",
    "manifold",
    "structural",
    "graph",
    "embedding",
    "transformer",
    "subconscious",
    "hardening",
)
ORTHOGONAL_TERMS = (
    "unrelated prior context",
    "unrelated context",
    "different domain",
    "orthogonal",
    "polluted",
    "semantic drift",
)
COLD_START_TERMS = (
    "without any prior context",
    "no prior context",
    "cold start",
    "cold-start",
)
FORMALIZING_TERMS = (
    "formalize",
    "formalizing",
    "schema",
    "skeleton",
    "decompose",
    "decomposition",
    "definition",
    "machine-readable",
)
SYMMETRY_TERMS = (
    "symmetric",
    "isomorph",
    "blueprint",
    "structural twin",
    "structural match",
)
INVERSION_TERMS = (
    "inversion",
    "antisymmetric",
    "inverse",
    "via negativa",
    "shadow",
    "guardrail",
)
NEGATIVE_INFERENCE_TERMS = (
    "negative inference",
    "bounding box",
    "failure mode",
    "via negativa",
)
EXPLICIT_LENS_PATTERN = re.compile(r"structural[\s_-]?isomorph", re.IGNORECASE)


@dataclass
class SessionActivationSignals:
    context_absent: bool = False
    context_domain_overlap: float = 0.0
    context_domain_orthogonal: float = 0.0
    formation_phase: Optional[str] = None
    meta_shape_id: Optional[str] = None
    meta_move_id: Optional[str] = None
    explicit_lens: Optional[str] = None
    problem_signal: bool = False
    quality_intensities: Dict[str, float] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.quality_intensities is None:
            self.quality_intensities = {}


def default_entity_catalog_path(root: Path) -> Path:
    return (
        root
        / "docs"
        / "frameworks"
        / "metaphysical-thought-space"
        / "seed"
        / "entity-activation-catalog.json"
    )


def mtsf_framework_available(root: Path) -> bool:
    return default_entity_catalog_path(root).exists()


def load_entity_catalog(root: Path) -> List[EntityActivationRecord]:
    path = default_entity_catalog_path(root)
    payload = json.loads(path.read_text(encoding="utf-8"))
    records: List[EntityActivationRecord] = []
    for row in payload.get("entities", []):
        records.append(
            EntityActivationRecord(
                id=str(row["id"]),
                shape_state_ids=[str(shape_id) for shape_id in row.get("shape_state_ids", [])],
                default_shape_id=row.get("default_shape_id"),
            )
        )
    return records


def _user_text(events: Sequence[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for event in events:
        actor = str(event.get("actor", "")).lower()
        if actor not in {"user", "importer"}:
            continue
        content = str(event.get("content", "")).strip()
        if content:
            lines.append(content)
    return "\n".join(lines).lower()


def _term_hits(text: str, terms: Sequence[str]) -> int:
    return sum(1 for term in terms if term in text)


def _normalized_hits(text: str, terms: Sequence[str]) -> float:
    if not terms:
        return 0.0
    return min(_term_hits(text, terms) / max(len(terms) * 0.25, 1.0), 1.0)


def infer_session_signals(
    events: Sequence[Dict[str, Any]],
    *,
    domains: Optional[Sequence[str]] = None,
    tags: Optional[Sequence[str]] = None,
) -> SessionActivationSignals:
    text = _user_text(events)
    user_turn_count = sum(
        1 for event in events if str(event.get("actor", "")).lower() in {"user", "importer"}
    )
    domain_text = " ".join(domains or []).lower()
    tag_text = " ".join(tags or []).lower()

    cold_hits = _term_hits(text, COLD_START_TERMS)
    anchor_score = _normalized_hits(text, ANCHOR_TERMS)
    orthogonal_score = max(
        _normalized_hits(text, ORTHOGONAL_TERMS),
        0.75 if "unrelated prior context" in text else 0.0,
    )
    domain_anchor_boost = 0.2 if domain_text and any(term in text for term in domain_text.split()) else 0.0
    overlap_score = min(anchor_score + domain_anchor_boost, 1.0)

    context_absent = bool(cold_hits) or (user_turn_count <= 1 and anchor_score < 0.2)
    if "without any prior context" in text or "no prior context" in text:
        context_absent = True

    # Triangulation pattern: if both overlap and orthogonal cues appear, prefer the stronger signal.
    if orthogonal_score >= 0.6:
        overlap_score = min(overlap_score, 0.4)
        context_absent = False
    elif overlap_score >= 0.6:
        context_absent = False
        orthogonal_score = min(orthogonal_score, 0.4)

    formalizing_score = _normalized_hits(text, FORMALIZING_TERMS)
    symmetry_score = _normalized_hits(text, SYMMETRY_TERMS)
    inversion_score = _normalized_hits(text, INVERSION_TERMS)
    negative_inference_score = _normalized_hits(text, NEGATIVE_INFERENCE_TERMS)

    meta_shape_id: Optional[str] = None
    if formalizing_score >= 0.35 or "meta-shape-formalizing" in tag_text:
        meta_shape_id = "meta-shape-formalizing"

    meta_move_id: Optional[str] = None
    if negative_inference_score >= 0.35:
        meta_move_id = "move-negative-inference"
    if inversion_score >= 0.35:
        meta_move_id = "move-inversion"
    if symmetry_score >= 0.35:
        meta_move_id = "move-symmetry-extension"

    explicit_lens: Optional[str] = None
    if EXPLICIT_LENS_PATTERN.search(text):
        explicit_lens = "structural_isomorph"

    formation_phase: Optional[str] = None
    if "product_vision" in tag_text or "product vision" in text:
        formation_phase = "product_vision_crystallization"
    elif meta_shape_id:
        formation_phase = "artifact_formation"
    elif user_turn_count >= 3:
        formation_phase = "partial_population"

    problem_signal = any(
        phrase in text
        for phrase in ("roadblock", "stuck", "blocked", "cannot", "missing implementation")
    )

    return SessionActivationSignals(
        context_absent=context_absent and overlap_score < 0.6 and orthogonal_score < 0.6,
        context_domain_overlap=overlap_score,
        context_domain_orthogonal=orthogonal_score,
        formation_phase=formation_phase,
        meta_shape_id=meta_shape_id,
        meta_move_id=meta_move_id,
        explicit_lens=explicit_lens,
        problem_signal=problem_signal,
        quality_intensities={
            "structural": symmetry_score,
            "antisymmetric": inversion_score,
            "hardening": _normalized_hits(text, ("hardening", "harden", "concrete")),
        },
    )


def build_entity_context(
    entity: EntityActivationRecord,
    signals: SessionActivationSignals,
    *,
    session_id: Optional[str],
    subgraph_id: Optional[str],
) -> ActivationContext:
    return ActivationContext(
        entity_id=entity.id,
        context_domain_overlap=signals.context_domain_overlap,
        context_domain_orthogonal=signals.context_domain_orthogonal,
        context_absent=signals.context_absent,
        formation_phase=signals.formation_phase,
        meta_move_id=signals.meta_move_id,
        meta_shape_id=signals.meta_shape_id,
        explicit_lens=signals.explicit_lens,
        problem_signal=signals.problem_signal,
        subgraph_id=subgraph_id,
        session_id=session_id,
        quality_intensities=dict(signals.quality_intensities),
    )


def _collect_tags(events: Sequence[Dict[str, Any]]) -> List[str]:
    tags: List[str] = []
    for event in events:
        tags.extend(str(tag) for tag in event.get("tags", []) if tag)
    return tags


def _build_session_graph(
    *,
    session_id: str,
    subgraph_id: str,
    entities: Sequence[EntityActivationRecord],
    results: Sequence[Any],
    signals: SessionActivationSignals,
    snapshot_path: Path,
) -> Dict[str, Any]:
    result_by_entity = {result.entity_id: result for result in results}
    graph_entities: List[Dict[str, Any]] = []
    for entity in entities:
        result = result_by_entity.get(entity.id)
        graph_entities.append(
            {
                "id": entity.id,
                "shape_state_ids": list(entity.shape_state_ids),
                "default_shape_id": entity.default_shape_id,
                "activation": result.to_dict() if result else None,
            }
        )
    return {
        "session_id": session_id,
        "subgraph_id": subgraph_id,
        "formation_phase": signals.formation_phase,
        "meta_shape_id": signals.meta_shape_id,
        "meta_move_id": signals.meta_move_id,
        "entities": graph_entities,
        "activation_snapshot_ref": str(snapshot_path),
    }


def materialize_session_mtsf(root: Path, session_id: str) -> Dict[str, str]:
    events = read_jsonl(session_events_path(root, session_id))
    manifest = read_json(session_dir(root, session_id) / "manifest.json", default={})
    domains = manifest.get("domains", [])
    tags = _collect_tags(events)

    signals = infer_session_signals(events, domains=domains, tags=tags)
    entities = load_entity_catalog(root)
    conditions = load_seed_conditions(root)
    subgraph_id = f"session-{session_id}"

    contexts = [
        build_entity_context(entity, signals, session_id=session_id, subgraph_id=subgraph_id)
        for entity in entities
    ]
    results = [activate(entity, ctx, conditions) for entity, ctx in zip(entities, contexts)]

    snapshot_id = make_id("mtsf-snap")
    snapshot = build_activation_snapshot(
        snapshot_id=snapshot_id,
        session_id=session_id,
        subgraph_id=subgraph_id,
        formation_phase=signals.formation_phase,
        meta_shape_id=signals.meta_shape_id,
        results=results,
    )
    snapshot["inference"] = {
        "context_absent": signals.context_absent,
        "context_domain_overlap": signals.context_domain_overlap,
        "context_domain_orthogonal": signals.context_domain_orthogonal,
        "meta_move_id": signals.meta_move_id,
        "explicit_lens": signals.explicit_lens,
        "problem_signal": signals.problem_signal,
        "user_turn_count": sum(
            1 for event in events if str(event.get("actor", "")).lower() in {"user", "importer"}
        ),
    }

    artifact_dir = session_dir(root, session_id) / "mtsf"
    ensure_dir(artifact_dir)
    snapshot_path = artifact_dir / "activation_snapshot.json"
    graph_path = artifact_dir / "graph.json"
    write_json(snapshot_path, snapshot)
    write_json(
        graph_path,
        _build_session_graph(
            session_id=session_id,
            subgraph_id=subgraph_id,
            entities=entities,
            results=results,
            signals=signals,
            snapshot_path=snapshot_path,
        ),
    )
    return {
        "mtsf_activation_snapshot": str(snapshot_path),
        "mtsf_graph": str(graph_path),
    }
