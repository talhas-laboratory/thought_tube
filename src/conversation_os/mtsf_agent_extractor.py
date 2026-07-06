from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .mtsf_extraction import DEEP_STAGES, SKILL_ID, SKILL_VERSION
from .mtsf_ingest import (
    TRIANGULATION_PHRASES,
    _collect_tags,
    _conversation_text,
    _detect_stencil_drafts,
    _evidence_span,
    _user_text,
)
from .mtsf_session import SessionActivationSignals, infer_session_signals
from .storage import make_id, utc_now

MODULE_ID = "kernel.mtsf.agent_extractor"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "AGENT_ENTITY_HINTS",
    "AGENT_RELATION_TEMPLATES",
    "build_agent_skill_extraction_draft",
)
__all__ = list(PUBLIC_API)

AGENT_ENTITY_HINTS = (
    {
        "keywords": ("latent space", "latent manifold", "high-dimensional manifold", "semantic geometry"),
        "proposed_id": "entity-latent-manifold",
        "name": "latent manifold",
        "type": "composite",
        "stable_identity": ["fixed mathematical library of learned relationships"],
    },
    {
        "keywords": ("inference path", "hidden states", "trajectory", "path\" is a trajectory", "successive layers"),
        "proposed_id": "entity-agent-path",
        "name": "inference path",
        "type": "composite",
        "stable_identity": ["sequence of hidden-state movements during processing"],
    },
    {
        "keywords": ("context", "prior context", "kv cache", "context field", "coordinate shift"),
        "proposed_id": "entity-context-field",
        "name": "context field",
        "type": "composite",
        "stable_identity": ["prior runs as gravitational weather on the manifold"],
    },
    {
        "keywords": ("effective topology", "topological landscape", "conditional manifold", "context warps"),
        "proposed_id": "entity-effective-topology",
        "name": "effective topology",
        "type": "composite",
        "stable_identity": ["accessible landscape sculpted by context without changing weights"],
    },
    {
        "keywords": ("bundle of fibers", "dimensional fiber", "sub-dimension", "meaning dimension"),
        "proposed_id": "entity-dimensional-fiber",
        "name": "dimensional fiber",
        "type": "atomic",
        "stable_identity": ["independent meaning dimension within a concept vector"],
    },
    {
        "keywords": ("thought ocean", "ocean of thoughts", "users thoughts and ideas", "well organized ocean"),
        "proposed_id": "entity-thought-ocean",
        "name": "thought ocean",
        "type": "composite",
        "stable_identity": ["personal library of notes organized by geometry not folders"],
    },
    {
        "keywords": ("relational stencil", "directed relational topology", "structural shape", "verbs of force"),
        "proposed_id": "entity-structural-shape",
        "name": "structural shape",
        "type": "composite",
        "stable_identity": ["directed relational topology abstracted from prose"],
    },
    {
        "keywords": ("dynamic state-space", "entities interact through relationships", "entity-relationship-state", "e-r-s"),
        "proposed_id": "entity-entity-relationship-state",
        "name": "entity-relationship-state model",
        "type": "composite",
        "stable_identity": ["thought as nodes, edges, and evolving state"],
    },
    {
        "keywords": ("synthetic subconscious", "spreading activation", "background cross-pollination"),
        "proposed_id": "entity-synthetic-subconscious",
        "name": "synthetic subconscious",
        "type": "composite",
        "stable_identity": ["AI layer performing background spreading activation across personal library"],
    },
    {
        "keywords": ("symmetry engine", "structural isomorph", "symmetric match", "isomorph"),
        "proposed_id": "entity-symmetry-engine",
        "name": "symmetry engine",
        "type": "composite",
        "stable_identity": ["matcher finding symmetric twins and antisymmetric inverses"],
    },
    {
        "keywords": ("eureka", "aha!", "aha moment", "topological bridge"),
        "proposed_id": "entity-eureka-moment",
        "name": "eureka moment",
        "type": "composite",
        "stable_identity": ["conscious reveal of a latent topological bridge"],
    },
    {
        "keywords": ("hardened idea", "hardens the idea", "harden\" the idea", "more complex, \"hardened\""),
        "proposed_id": "entity-hardened-idea",
        "name": "hardened idea",
        "type": "composite",
        "stable_identity": ["soft creative seed made concrete through structural mapping"],
    },
)

AGENT_RELATION_TEMPLATES: Tuple[Dict[str, Any], ...] = (
    {
        "source": "entity-context-field",
        "target": "entity-effective-topology",
        "relation_type": "warps",
        "primitive": "modulates",
        "domain_expression": "context warps accessible topology",
    },
    {
        "source": "entity-context-field",
        "target": "entity-agent-path",
        "relation_type": "steers",
        "primitive": "modulates",
        "domain_expression": "context steers inference path",
    },
    {
        "source": "entity-agent-path",
        "target": "entity-latent-manifold",
        "relation_type": "traverses",
        "primitive": "contains",
        "domain_expression": "inference path traverses latent manifold",
    },
    {
        "source": "entity-dimensional-fiber",
        "target": "entity-effective-topology",
        "relation_type": "enables",
        "primitive": "combines-with",
        "domain_expression": "fibers enable path-splicing across topology",
        "level": "quality_quality",
    },
    {
        "source": "entity-thought-ocean",
        "target": "entity-structural-shape",
        "relation_type": "contains",
        "primitive": "contains",
        "domain_expression": "ocean stores structural shapes",
    },
    {
        "source": "entity-structural-shape",
        "target": "entity-entity-relationship-state",
        "relation_type": "materializes-as",
        "primitive": "defines",
        "domain_expression": "shape decomposes into E-R-S model",
    },
    {
        "source": "entity-synthetic-subconscious",
        "target": "entity-thought-ocean",
        "relation_type": "scans",
        "primitive": "enables",
        "domain_expression": "subconscious scans thought ocean",
    },
    {
        "source": "entity-symmetry-engine",
        "target": "entity-structural-shape",
        "relation_type": "matches",
        "primitive": "resembles",
        "domain_expression": "symmetry engine matches structural shapes",
    },
    {
        "source": "entity-synthetic-subconscious",
        "target": "entity-eureka-moment",
        "relation_type": "triggers",
        "primitive": "enables",
        "domain_expression": "background matching triggers eureka",
    },
    {
        "source": "entity-eureka-moment",
        "target": "entity-hardened-idea",
        "relation_type": "enables",
        "primitive": "transforms-into",
        "domain_expression": "eureka enables idea hardening",
    },
    {
        "source": "entity-symmetry-engine",
        "target": "entity-hardened-idea",
        "relation_type": "sculpts",
        "primitive": "defines",
        "domain_expression": "negative inference sculpts hardened idea",
    },
)


def _detect_agent_entities(text: str) -> List[Dict[str, Any]]:
    lowered = text.lower()
    entities: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for hint in AGENT_ENTITY_HINTS:
        if not any(keyword.lower() in lowered for keyword in hint["keywords"]):
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
                "type": hint.get("type", "composite"),
                "stable_identity": list(hint.get("stable_identity", [])),
                "confidence": 0.84,
                "evidence": {"spans": [span]},
            }
        )
    return entities


def _detect_agent_qualities(
    text: str,
    entities: Sequence[Dict[str, Any]],
    signals: SessionActivationSignals,
) -> List[Dict[str, Any]]:
    from .mtsf_ingest import _detect_qualities

    qualities = _detect_qualities(text, signals, entities)
    lowered = text.lower()
    entity_by_id = {row["proposed_id"]: row for row in entities}
    extra: List[Dict[str, Any]] = []

    def add_quality(
        quality_id: str,
        labels: Sequence[str],
        entity_ref: Optional[str],
        *,
        quality_type: str = "meta_state",
        kind: str = "emergent",
        keywords: Sequence[str],
        confidence: float = 0.85,
    ) -> None:
        if not any(keyword.lower() in lowered for keyword in keywords):
            return
        if any(row.get("quality_id") == quality_id for row in qualities + extra):
            return
        extra.append(
            {
                "quality_id": quality_id,
                "quality_type": quality_type,
                "intensity": 0.85,
                "kind": kind,
                "entity_ref": entity_ref,
                "labels": list(labels),
                "confidence": confidence,
                "evidence": {"spans": [_evidence_span(text, keywords)]},
            }
        )

    add_quality(
        "quality-static-weights",
        ["static", "frozen"],
        entity_by_id.get("entity-latent-manifold", {}).get("proposed_id"),
        quality_type="ontological",
        kind="intrinsic",
        keywords=("static after training", "latent space itself is static"),
    )
    add_quality(
        "quality-symmetric-match",
        ["symmetric", "isomorph"],
        entity_by_id.get("entity-symmetry-engine", {}).get("proposed_id"),
        quality_type="formal",
        kind="relational",
        keywords=("structural isomorph", "symmetric match", "symmetry engine"),
    )
    add_quality(
        "quality-antisymmetric-shadow",
        ["antisymmetric", "inversion"],
        entity_by_id.get("entity-symmetry-engine", {}).get("proposed_id"),
        quality_type="formal",
        kind="relational",
        keywords=("antisymmetric", "shadow", "opposite direction"),
    )
    add_quality(
        "quality-via-negativa",
        ["bounding_box", "negative_inference"],
        entity_by_id.get("entity-hardened-idea", {}).get("proposed_id"),
        keywords=("via negativa", "negative inference", "what it is not"),
    )
    if any(phrase in lowered for phrase in TRIANGULATION_PHRASES):
        add_quality(
            "quality-cold-start",
            ["no prior context"],
            entity_by_id.get("entity-context-field", {}).get("proposed_id"),
            keywords=TRIANGULATION_PHRASES[:2],
        )
    return qualities + extra


def _detect_agent_relations(
    text: str,
    entities: Sequence[Dict[str, Any]],
    qualities: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    from .mtsf_extraction_skill import _build_deep_relations

    entity_ids = {row["proposed_id"] for row in entities}
    relations: List[Dict[str, Any]] = []

    for template in AGENT_RELATION_TEMPLATES:
        source = str(template["source"])
        target = str(template["target"])
        if source not in entity_ids or target not in entity_ids:
            continue
        level = str(template.get("level", "entity_entity"))
        relations.append(
            {
                "source_ref": source,
                "target_ref": target,
                "level": level,
                "relation_type": template["relation_type"],
                "primitive": template["primitive"],
                "domain_expression": template["domain_expression"],
                "weight": 0.86,
                "confidence": 0.84,
                "evidence": {
                    "spans": [
                        _evidence_span(
                            text,
                            (
                                template["domain_expression"],
                                template["relation_type"],
                                template["primitive"],
                            ),
                        )
                    ]
                },
            }
        )

    for row in _build_deep_relations(list(entities), list(qualities), text):
        signature = (row["source_ref"], row["target_ref"], row.get("primitive", ""))
        if not any(
            (existing["source_ref"], existing["target_ref"], existing.get("primitive", "")) == signature
            for existing in relations
        ):
            relations.append(row)
    return relations


def _detect_agent_candidate_shapes(
    text: str,
    entities: Sequence[Dict[str, Any]],
    signals: SessionActivationSignals,
) -> List[Dict[str, Any]]:
    from .mtsf_ingest import _detect_candidate_shapes

    shapes = _detect_candidate_shapes(text, signals, entities)
    lowered = text.lower()
    entity_refs = [row["proposed_id"] for row in entities]

    if any(term in lowered for term in ("synthetic subconscious", "hardened idea", "spreading activation")):
        shapes.append(
            {
                "proposed_id": "cand-synthetic-subconscious",
                "possible_names": [
                    "synthetic subconscious hardening loop",
                    "isomorphic hardening loop",
                ],
                "relational_configuration": (
                    "context_momentum + structural_abstraction + isomorphic_matching + "
                    "negative_inference → synthetic_subconscious → hardened_idea"
                ),
                "entity_refs": [
                    ref
                    for ref in (
                        "entity-synthetic-subconscious",
                        "entity-symmetry-engine",
                        "entity-hardened-idea",
                        "entity-thought-ocean",
                    )
                    if ref in entity_refs
                ],
                "confidence": 0.88,
                "evidence": {
                    "spans": [
                        _evidence_span(
                            text,
                            ("synthetic subconscious", "hardened", "spreading activation", "symmetry engine"),
                        )
                    ]
                },
            }
        )
    return shapes


def _detect_agent_stencil_drafts(text: str, signals: SessionActivationSignals) -> List[Dict[str, Any]]:
    drafts = list(_detect_stencil_drafts(text, signals))
    lowered = text.lower()
    seen_names = {str(row.get("proposed_name", "")) for row in drafts}

    def add_draft(draft: Dict[str, Any]) -> None:
        name = str(draft.get("proposed_name", ""))
        if name and name not in seen_names:
            drafts.append(draft)
            seen_names.add(name)

    if any(term in lowered for term in ("symmetry engine", "structural isomorph", "symmetric match")):
        add_draft(
            {
                "proposed_name": "symmetric blueprint",
                "role_entities": [
                    {"role_type": "mediator"},
                    {"role_type": "source"},
                    {"role_type": "template"},
                ],
                "relation_topology": [
                    {"source_role_ref": "mediator", "target_role_ref": "source", "primitive": "resembles"},
                    {"source_role_ref": "mediator", "target_role_ref": "template", "primitive": "instantiates"},
                ],
                "dynamics_class": "star_topology",
                "symmetry_profile": "symmetric",
                "facet_completeness": {"causal_geometry": True},
                "confidence": 0.86,
                "evidence": {
                    "spans": [_evidence_span(text, ("symmetry", "isomorph", "symmetric match"))],
                    "source_refs": ["seed:stencil-symmetric-blueprint", "ingest:agent"],
                },
            }
        )
    if any(term in lowered for term in ("antisymmetric", "shadow", "opposite direction", "via negativa")):
        add_draft(
            {
                "proposed_name": "antisymmetric guardrail",
                "role_entities": [
                    {"role_type": "mediator"},
                    {"role_type": "source"},
                    {"role_type": "sink"},
                ],
                "relation_topology": [
                    {"source_role_ref": "mediator", "target_role_ref": "source", "primitive": "contrasts"},
                    {"source_role_ref": "mediator", "target_role_ref": "sink", "primitive": "blocks"},
                ],
                "dynamics_class": "tight_coupling",
                "symmetry_profile": "antisymmetric",
                "facet_completeness": {"causal_geometry": True},
                "confidence": 0.82,
                "evidence": {
                    "spans": [_evidence_span(text, ("antisymmetric", "shadow", "via negativa"))],
                    "source_refs": ["seed:stencil-antisymmetric-guardrail", "ingest:agent"],
                },
            }
        )
    if any(term in lowered for term in ("eureka", "aha moment", "topological bridge", "incubation")):
        add_draft(
            {
                "proposed_name": "phase transition bridge",
                "role_entities": [
                    {"role_type": "buffer"},
                    {"role_type": "mediator"},
                    {"role_type": "sink"},
                ],
                "relation_topology": [
                    {"source_role_ref": "buffer", "target_role_ref": "mediator", "primitive": "enables"},
                    {"source_role_ref": "mediator", "target_role_ref": "sink", "primitive": "transforms-into"},
                ],
                "dynamics_class": "phase",
                "symmetry_profile": "mixed",
                "facet_completeness": {"causal_geometry": True},
                "confidence": 0.8,
                "evidence": {
                    "spans": [_evidence_span(text, ("eureka", "aha", "bridge", "incubation"))],
                    "source_refs": ["seed:stencil-phase-transition-bridge", "ingest:agent"],
                },
            }
        )
    if any(term in lowered for term in ("hardened idea", "hardens the idea", "negative inference")):
        add_draft(
            {
                "proposed_name": "hardening loop",
                "role_entities": [
                    {"role_type": "controller"},
                    {"role_type": "buffer"},
                    {"role_type": "sink"},
                ],
                "relation_topology": [
                    {"source_role_ref": "controller", "target_role_ref": "buffer", "primitive": "modulates"},
                    {"source_role_ref": "buffer", "target_role_ref": "sink", "primitive": "transforms-into"},
                ],
                "dynamics_class": "feedback_reinforcing",
                "symmetry_profile": "asymmetric",
                "facet_completeness": {"causal_geometry": True},
                "confidence": 0.81,
                "evidence": {
                    "spans": [_evidence_span(text, ("hardened", "negative inference", "hardens"))],
                    "source_refs": ["seed:stencil-hardening-loop", "ingest:agent"],
                },
            }
        )
    return drafts


def _build_quality_roles(
    qualities: Sequence[Dict[str, Any]],
    entities: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    from .mtsf_extraction_skill import _build_quality_roles

    return _build_quality_roles(qualities, entities)


def build_agent_skill_extraction_draft(
    *,
    session_id: str,
    events: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
    raw_content: Optional[str] = None,
) -> Dict[str, Any]:
    text = raw_content or _conversation_text(events)
    domains = manifest.get("domains", [])
    tags = _collect_tags(events)
    signals = infer_session_signals(events, domains=domains, tags=tags)

    entities = _detect_agent_entities(text)
    qualities = _detect_agent_qualities(text, entities, signals)
    relations = _detect_agent_relations(text, entities, qualities)
    candidate_shapes = _detect_agent_candidate_shapes(text, entities, signals)
    stencil_drafts = _detect_agent_stencil_drafts(text, signals)
    quality_roles = _build_quality_roles(qualities, entities)

    subgraph_id = domains[0] if domains else f"session-{session_id}"
    confidence = 0.7
    if entities:
        confidence += min(0.12, 0.01 * len(entities))
    if relations:
        confidence += min(0.08, 0.01 * len(relations))
    if stencil_drafts:
        confidence += 0.05
    confidence = min(confidence, 0.93)

    dominant_entity_refs = [row["proposed_id"] for row in entities[:3]]
    active_quality_refs = [row["quality_id"] for row in qualities[:5]]

    return {
        "draft_id": make_id("mtsf-draft"),
        "input_id": f"session:{session_id}",
        "input_type": "import" if manifest.get("source_type") == "imported_transcript" else "text",
        "capture_mode": "deep",
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
            "model_id": "mtsf_ingest.agent_skill",
            "extracted_at": utc_now(),
            "stages_completed": sorted(DEEP_STAGES),
        },
        "entities": entities,
        "sub_entities": [],
        "qualities": qualities,
        "quality_roles": quality_roles,
        "relations": relations,
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
            "Agent-skill extraction uses full-text phrase analysis (no external LLM). OpenClaw or human review may refine relations and stencil topology."
        ],
        "user_questions": [],
        "confidence": confidence,
        "status": "proposed",
    }
