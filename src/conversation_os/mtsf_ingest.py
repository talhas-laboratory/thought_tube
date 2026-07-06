from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from .mtsf_extraction import SKILL_ID, SKILL_VERSION, materialize_extraction_draft
from .mtsf_session import SessionActivationSignals, infer_session_signals
from .storage import make_id, read_json, read_jsonl, session_dir, session_events_path, utc_now

MODULE_ID = "kernel.mtsf.ingest"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "MIN_USER_TEXT_CHARS",
    "ENTITY_HINTS",
    "should_run_mtsf_ingest",
    "build_fast_extraction_draft",
    "materialize_session_mtsf_ingest",
)
__all__ = list(PUBLIC_API)

MIN_USER_TEXT_CHARS = 40

ENTITY_HINTS = (
    {
        "keywords": ("context", "prior context", "kv cache", "context field"),
        "proposed_id": "entity-context-field",
        "name": "context field",
        "stable_identity": ["contextual conditioning on inference"],
    },
    {
        "keywords": ("latent", "manifold", "embedding", "transformer"),
        "proposed_id": "entity-latent-manifold",
        "name": "latent manifold",
        "stable_identity": ["learned semantic geometry"],
    },
    {
        "keywords": ("topology", "effective topology", "geodesic"),
        "proposed_id": "entity-effective-topology",
        "name": "effective topology",
        "stable_identity": ["context-warped accessible landscape"],
    },
    {
        "keywords": ("symmetry", "isomorph", "blueprint", "structural twin"),
        "proposed_id": "entity-symmetry-engine",
        "name": "symmetry engine",
        "stable_identity": ["structural matching operator"],
    },
    {
        "keywords": ("thought ocean", "note library", "personal library", "notes"),
        "proposed_id": "entity-thought-ocean",
        "name": "thought ocean",
        "stable_identity": ["personal knowledge library"],
    },
    {
        "keywords": ("subconscious", "incubation", "spreading activation"),
        "proposed_id": "entity-synthetic-subconscious",
        "name": "synthetic subconscious",
        "stable_identity": ["background cross-domain matcher"],
    },
)

TRIANGULATION_PHRASES = (
    "without any prior context",
    "no prior context",
    "relevant prior context",
    "unrelated prior context",
)


def _collect_tags(events: Sequence[Dict[str, Any]]) -> List[str]:
    tags: List[str] = []
    for event in events:
        tags.extend(str(tag) for tag in event.get("tags", []) if tag)
    return tags


def _conversation_text(events: Sequence[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for event in events:
        content = str(event.get("content", "")).strip()
        if content:
            lines.append(content)
    return "\n".join(lines)


def _user_text(events: Sequence[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for event in events:
        actor = str(event.get("actor", "")).lower()
        if actor in {"user", "importer"}:
            content = str(event.get("content", "")).strip()
            if content:
                lines.append(content)
    return "\n".join(lines)


def _evidence_span(text: str, keywords: Sequence[str]) -> str:
    lowered = text.lower()
    for keyword in keywords:
        index = lowered.find(keyword.lower())
        if index >= 0:
            start = max(0, index - 40)
            end = min(len(text), index + len(keyword) + 60)
            return text[start:end].strip()
    snippet = text.strip().split("\n")[0]
    return snippet[:180] if snippet else text[:180]


def should_run_mtsf_ingest(
    mode: str,
    events: Sequence[Dict[str, Any]],
    *,
    source_type: Optional[str] = None,
) -> bool:
    if mode == "off":
        return False
    user_text = _user_text(events)
    if source_type == "imported_transcript" and user_text.strip():
        return True
    return len(user_text.strip()) >= MIN_USER_TEXT_CHARS


def _detect_entities(text: str) -> List[Dict[str, Any]]:
    lowered = text.lower()
    entities: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for hint in ENTITY_HINTS:
        if not any(keyword in lowered for keyword in hint["keywords"]):
            continue
        proposed_id = str(hint["proposed_id"])
        if proposed_id in seen:
            continue
        seen.add(proposed_id)
        span = _evidence_span(text, hint["keywords"])
        entities.append(
            {
                "proposed_id": proposed_id,
                "name": hint["name"],
                "type": "composite",
                "stable_identity": list(hint["stable_identity"]),
                "confidence": 0.72,
                "evidence": {"spans": [span]},
            }
        )
    return entities


def _detect_qualities(
    text: str,
    signals: SessionActivationSignals,
    entities: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    qualities: List[Dict[str, Any]] = []
    entity_ref = entities[0]["proposed_id"] if entities else None
    if signals.context_domain_overlap >= 0.5:
        qualities.append(
            {
                "quality_id": "quality-domain-overlap",
                "quality_type": "meta_state",
                "intensity": signals.context_domain_overlap,
                "kind": "contextual",
                "entity_ref": entity_ref,
                "labels": ["anchored", "domain_overlap"],
                "confidence": 0.75,
                "evidence": {"spans": [_evidence_span(text, ("context", "topology", "relevant"))]},
            }
        )
    if signals.context_domain_orthogonal >= 0.5:
        qualities.append(
            {
                "quality_id": "quality-domain-orthogonal",
                "quality_type": "meta_state",
                "intensity": signals.context_domain_orthogonal,
                "kind": "contextual",
                "entity_ref": entity_ref,
                "labels": ["orthogonal", "polluted"],
                "confidence": 0.75,
                "evidence": {"spans": [_evidence_span(text, TRIANGULATION_PHRASES)]},
            }
        )
    if signals.meta_shape_id:
        qualities.append(
            {
                "quality_id": "quality-formalizing",
                "quality_type": "meta_state",
                "intensity": 0.8,
                "kind": "emergent",
                "entity_ref": entity_ref,
                "labels": ["formalizing"],
                "confidence": 0.78,
                "evidence": {"spans": [_evidence_span(text, ("formal", "schema", "structure"))]},
            }
        )
    return qualities


def _detect_candidate_shapes(
    text: str,
    signals: SessionActivationSignals,
    entities: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    shapes: List[Dict[str, Any]] = []
    entity_refs = [row["proposed_id"] for row in entities]
    lowered = text.lower()

    if any(phrase in lowered for phrase in TRIANGULATION_PHRASES):
        shapes.append(
            {
                "proposed_id": "cand-context-triangulation",
                "possible_names": ["context triangulation", "three-case context contrast"],
                "relational_configuration": "cold vs anchored vs orthogonal context",
                "entity_refs": entity_refs[:3],
                "confidence": 0.8,
                "evidence": {"spans": [_evidence_span(text, TRIANGULATION_PHRASES)]},
            }
        )
    if signals.meta_shape_id:
        shapes.append(
            {
                "proposed_id": "cand-formalizing-pass",
                "possible_names": ["formalizing pass", "structural skeleton formation"],
                "relational_configuration": "prose → structural abstraction",
                "entity_refs": entity_refs[:2],
                "confidence": 0.76,
                "evidence": {"spans": [_evidence_span(text, ("formal", "schema", "structure"))]},
            }
        )
    if signals.meta_move_id == "move-symmetry-extension":
        shapes.append(
            {
                "proposed_id": "cand-symmetry-match",
                "possible_names": ["symmetric blueprint", "structural twin search"],
                "relational_configuration": "seed → isomorph template",
                "entity_refs": entity_refs[:2],
                "confidence": 0.74,
                "evidence": {"spans": [_evidence_span(text, ("symmetry", "isomorph", "blueprint"))]},
            }
        )
    if not shapes and entities:
        shapes.append(
            {
                "proposed_id": "cand-session-motif",
                "possible_names": ["session motif"],
                "relational_configuration": " + ".join(row["name"] for row in entities[:3]),
                "entity_refs": entity_refs[:3],
                "confidence": 0.62,
                "evidence": {"spans": [text.strip()[:180]]},
            }
        )
    return shapes


def _detect_stencil_drafts(text: str, signals: SessionActivationSignals) -> List[Dict[str, Any]]:
    lowered = text.lower()
    drafts: List[Dict[str, Any]] = []

    triangulation = any(phrase in lowered for phrase in TRIANGULATION_PHRASES)
    topology_anchor = any(term in lowered for term in ("topology", "latent", "context", "manifold"))
    if triangulation and topology_anchor:
        drafts.append(
            {
                "proposed_name": "context field modulates probe path",
                "role_entities": [
                    {"role_type": "field"},
                    {"role_type": "probe"},
                    {"role_type": "landscape"},
                ],
                "relation_topology": [
                    {
                        "source_role_ref": "field",
                        "target_role_ref": "probe",
                        "primitive": "modulates",
                        "relation_type": "steers",
                    },
                    {
                        "source_role_ref": "field",
                        "target_role_ref": "landscape",
                        "primitive": "modulates",
                        "relation_type": "warps",
                    },
                ],
                "dynamics_class": "gradient",
                "symmetry_profile": "asymmetric",
                "facet_completeness": {"causal_geometry": True},
                "confidence": 0.82,
                "evidence": {
                    "spans": [_evidence_span(text, TRIANGULATION_PHRASES)],
                    "source_refs": ["seed:stencil-context-warps-topology", "ingest:fast"],
                },
            }
        )
    elif signals.meta_move_id == "move-symmetry-extension":
        drafts.append(
            {
                "proposed_name": "symmetric blueprint match",
                "role_entities": [
                    {"role_type": "mediator"},
                    {"role_type": "source"},
                    {"role_type": "template"},
                ],
                "relation_topology": [
                    {
                        "source_role_ref": "mediator",
                        "target_role_ref": "source",
                        "primitive": "resembles",
                    },
                    {
                        "source_role_ref": "mediator",
                        "target_role_ref": "template",
                        "primitive": "instantiates",
                    },
                ],
                "dynamics_class": "star_topology",
                "symmetry_profile": "symmetric",
                "facet_completeness": {"causal_geometry": True},
                "confidence": 0.78,
                "evidence": {
                    "spans": [_evidence_span(text, ("symmetry", "isomorph"))],
                    "source_refs": ["seed:stencil-symmetric-blueprint", "ingest:fast"],
                },
            }
        )
    return drafts


def build_fast_extraction_draft(
    *,
    session_id: str,
    events: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
    raw_content: Optional[str] = None,
) -> Dict[str, Any]:
    text = raw_content or _conversation_text(events)
    user_text = _user_text(events)
    domains = manifest.get("domains", [])
    tags = _collect_tags(events)
    signals = infer_session_signals(events, domains=domains, tags=tags)
    entities = _detect_entities(text)
    qualities = _detect_qualities(text, signals, entities)
    candidate_shapes = _detect_candidate_shapes(text, signals, entities)
    stencil_drafts = _detect_stencil_drafts(text, signals)

    subgraph_id = domains[0] if domains else f"session-{session_id}"
    confidence = 0.62
    if entities:
        confidence += 0.08
    if stencil_drafts:
        confidence += 0.1
    if signals.meta_shape_id or any(phrase in user_text.lower() for phrase in TRIANGULATION_PHRASES):
        confidence += 0.08
    confidence = min(confidence, 0.9)

    dominant_entity_refs = [row["proposed_id"] for row in entities[:2]]
    active_quality_refs = [row["quality_id"] for row in qualities[:3]]

    return {
        "draft_id": make_id("mtsf-draft"),
        "input_id": f"session:{session_id}",
        "input_type": "import" if manifest.get("source_type") == "imported_transcript" else "text",
        "capture_mode": "fast",
        "session_id": session_id,
        "subgraph_id": subgraph_id,
        "scope": "session",
        "raw_content": text[:12000],
        "context": {
            "project": manifest.get("title"),
            "domain": ", ".join(domains) if domains else None,
            "tags": tags,
        },
        "ontology_refs": {
            "governing_roles": "mtsf://ontologies/governing-roles@1.0.0",
            "relation_primitives": "mtsf://ontologies/relation-primitives@1.1.0",
            "stencil_role_types": "mtsf://ontologies/stencil-role-types@1.0.0",
        },
        "provenance": {
            "skill_id": SKILL_ID,
            "skill_version": SKILL_VERSION,
            "model_id": "mtsf_ingest.fast",
            "extracted_at": utc_now(),
            "stages_completed": [
                "capture",
                "surface",
                "entities",
                "qualities",
                "candidate_shapes",
                *(["stencil_drafts"] if stencil_drafts else []),
                "activation_hint",
            ],
        },
        "entities": entities,
        "sub_entities": [],
        "qualities": qualities,
        "quality_roles": [],
        "relations": [],
        "candidate_shapes": candidate_shapes,
        "stencil_drafts": stencil_drafts,
        "activation_snapshot_hint": {
            "formation_phase": signals.formation_phase,
            "meta_shape_id": signals.meta_shape_id,
            "meta_move_id": signals.meta_move_id,
            "dominant_entity_refs": dominant_entity_refs,
            "active_quality_refs": active_quality_refs,
        },
        "artifact_pathways": [],
        "uncertainties": [
            "Fast ingest heuristic extraction; deep skill pass may refine structure."
        ],
        "user_questions": [],
        "confidence": confidence,
        "status": "proposed",
    }


def materialize_session_mtsf_ingest(
    root: Path,
    session_id: str,
    mode: str = "fast",
) -> Dict[str, Any]:
    events = read_jsonl(session_events_path(root, session_id))
    manifest = read_json(session_dir(root, session_id) / "manifest.json", default={})
    if not should_run_mtsf_ingest(mode, events, source_type=manifest.get("source_type")):
        return {
            "session_id": session_id,
            "mtsf_ingest": "skipped",
            "reason": "mode_off_or_insufficient_content",
            "artifact_refs": {},
        }

    draft = build_fast_extraction_draft(session_id=session_id, events=events, manifest=manifest)
    result = materialize_extraction_draft(root, session_id, draft)
    return {
        "session_id": session_id,
        "mtsf_ingest": "completed",
        "draft_id": draft["draft_id"],
        "capture_mode": draft["capture_mode"],
        "entity_count": len(draft.get("entities", [])),
        "stencil_draft_count": len(draft.get("stencil_drafts", [])),
        "artifact_refs": result.get("artifact_refs", {}),
        "validation_ok": result.get("validation_ok"),
        "quarantine": result.get("quarantine"),
        "projection": result.get("projection"),
    }
