from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from .mtsf_extraction import (
    DEEP_STAGES,
    SKILL_ID,
    SKILL_VERSION,
    default_skill_path,
    validate_extraction_draft,
)
from .storage import ensure_dir, make_id, utc_now, write_json

MODULE_ID = "kernel.mtsf.extraction_skill"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "build_skill_input_envelope",
    "build_deep_extraction_draft_heuristic",
    "resolve_deep_extraction_draft",
    "materialize_skill_input",
    "parse_extraction_draft_from_text",
    "request_llm_deep_extraction",
)
__all__ = list(PUBLIC_API)

SKILL_SYSTEM_PROMPT = """You are the MTSF semantic-shape-extraction skill.
Read the skill input envelope and emit ONE ExtractionDraft JSON object only.
Rules:
- capture_mode must match the envelope (deep)
- provenance.skill_id = semantic-shape-extraction
- provenance.skill_version = 1.0.0
- Every entity, quality, relation, and shape cites evidence.spans from raw_content
- Stencil drafts use role_types, not domain nouns
- Pattern-match seed stencils before inventing topology
- Silence is valid: empty stencil_drafts with uncertainties beats forced structure
- Output JSON only, no markdown fences or commentary"""


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def build_skill_input_envelope(
    *,
    session_id: str,
    events: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
    raw_content: str,
    capture_mode: str = "deep",
) -> Dict[str, Any]:
    domains = manifest.get("domains", [])
    tags: List[str] = []
    for event in events:
        tags.extend(str(tag) for tag in event.get("tags", []) if tag)
    subgraph_id = domains[0] if domains else f"session-{session_id}"
    source_type = manifest.get("source_type")
    input_type = "import" if source_type == "imported_transcript" else "text"
    return {
        "input_id": f"session:{session_id}",
        "input_type": input_type,
        "raw_content": raw_content[:12000],
        "capture_mode": capture_mode,
        "session_id": session_id,
        "subgraph_id": subgraph_id,
        "context": {
            "user_goal": manifest.get("title"),
            "project": manifest.get("title"),
            "domain": ", ".join(domains) if domains else None,
            "tags": tags,
            "source_type": source_type,
        },
        "skill_refs": {
            "skill_path": "docs/frameworks/metaphysical-thought-space/skills/semantic-shape-extraction/SKILL.md",
            "rubric_path": "docs/frameworks/metaphysical-thought-space/skills/semantic-shape-extraction/rubrics/stages.md",
            "schema": "mtsf://schemas/extraction-draft",
        },
        "ontology_refs": {
            "governing_roles": "mtsf://ontologies/governing-roles@1.0.0",
            "relation_primitives": "mtsf://ontologies/relation-primitives@1.1.0",
            "stencil_role_types": "mtsf://ontologies/stencil-role-types@1.0.0",
        },
        "prepared_at": utc_now(),
    }


def materialize_skill_input(
    root: Path,
    session_id: str,
    envelope: Dict[str, Any],
) -> Dict[str, str]:
    from .storage import session_dir

    path = session_dir(root, session_id) / "mtsf" / "skill_input.json"
    ensure_dir(path.parent)
    write_json(path, envelope)
    return {"mtsf_skill_input": str(path)}


def parse_extraction_draft_from_text(
    root: Path,
    text: str,
    *,
    session_id: str,
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    payload = _extract_json_object(text)
    if not payload:
        raise ValueError("no_json_object_in_response")
    draft = dict(payload)
    draft.setdefault("draft_id", make_id("mtsf-draft"))
    draft.setdefault("input_id", envelope.get("input_id", f"session:{session_id}"))
    draft.setdefault("input_type", envelope.get("input_type", "text"))
    draft.setdefault("capture_mode", envelope.get("capture_mode", "deep"))
    draft["session_id"] = session_id
    draft.setdefault("subgraph_id", envelope.get("subgraph_id", f"session-{session_id}"))
    draft.setdefault("scope", "session")
    draft.setdefault("raw_content", envelope.get("raw_content", ""))
    draft.setdefault("context", envelope.get("context", {}))
    draft.setdefault("ontology_refs", envelope.get("ontology_refs", {}))
    provenance = dict(draft.get("provenance", {}))
    provenance.setdefault("skill_id", SKILL_ID)
    provenance.setdefault("skill_version", SKILL_VERSION)
    provenance.setdefault("extracted_at", utc_now())
    provenance.setdefault("stages_completed", sorted(DEEP_STAGES))
    draft["provenance"] = provenance
    draft.setdefault("entities", [])
    draft.setdefault("sub_entities", [])
    draft.setdefault("qualities", [])
    draft.setdefault("quality_roles", [])
    draft.setdefault("relations", [])
    draft.setdefault("candidate_shapes", [])
    draft.setdefault("stencil_drafts", [])
    draft.setdefault("uncertainties", [])
    draft.setdefault("user_questions", [])
    draft.setdefault("confidence", 0.5)
    draft.setdefault("status", "proposed")
    report = validate_extraction_draft(root, draft)
    if not report.ok:
        raise ValueError("; ".join(report.errors[:5]))
    return draft


def request_llm_deep_extraction(
    root: Path,
    *,
    session_id: str,
    envelope: Dict[str, Any],
) -> Dict[str, Any]:
    from .chat_backends import request_openclaw_reply, resolve_chat_backend

    backend = resolve_chat_backend(root)
    if backend["id"] not in {"openclaw_local", "openclaw_gateway"}:
        raise RuntimeError("llm_backend_unavailable")

    skill_excerpt = ""
    skill_path = default_skill_path(root)
    if skill_path.exists():
        skill_excerpt = skill_path.read_text(encoding="utf-8")[:4000]

    context = {
        "character": "MTSF Semantic Shape Extractor",
        "system_prompt": "\n".join(
            [
                SKILL_SYSTEM_PROMPT,
                "",
                "Skill reference excerpt:",
                skill_excerpt,
            ]
        ),
        "source_snippets": [
            {
                "title": envelope.get("context", {}).get("project") or f"session:{session_id}",
                "source_ref": envelope.get("input_id", f"session:{session_id}"),
                "excerpt": str(envelope.get("raw_content", ""))[:2000],
            }
        ],
    }
    thread = {
        "thread_id": f"mtsf-deep-{session_id}",
        "title": "MTSF deep extraction",
        "messages": [],
    }
    user_message = (
        "Emit an ExtractionDraft JSON object for this skill input envelope:\n"
        f"{json.dumps(envelope, indent=2, ensure_ascii=False)}"
    )
    reply = request_openclaw_reply(root, context, user_message, thread, backend)
    draft = parse_extraction_draft_from_text(
        root,
        reply.get("content", ""),
        session_id=session_id,
        envelope=envelope,
    )
    draft["provenance"]["model_id"] = f"openclaw:{backend['id']}"
    return {
        "draft": draft,
        "source": "llm",
        "backend_id": backend["id"],
    }


def _build_quality_roles(
    qualities: Sequence[Dict[str, Any]],
    entities: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    roles: List[Dict[str, Any]] = []
    entity_ref = entities[0]["proposed_id"] if entities else None
    role_map = {
        "quality-domain-overlap": "stabilizing",
        "quality-domain-orthogonal": "contrasting",
        "quality-formalizing": "generating",
        "quality-cold-start": "contrasting",
        "quality-anchored": "stabilizing",
        "quality-orthogonal": "contrasting",
    }
    for quality in qualities:
        quality_id = str(quality.get("quality_id", ""))
        role = role_map.get(quality_id, "amplifying")
        roles.append(
            {
                "quality_ref": quality_id,
                "entity_ref": quality.get("entity_ref") or entity_ref,
                "role": role,
                "confidence": float(quality.get("confidence", 0.7)),
                "evidence": quality.get("evidence", {"spans": ["derived from quality signal"]}),
            }
        )
    return roles


def _build_deep_relations(
    entities: Sequence[Dict[str, Any]],
    qualities: Sequence[Dict[str, Any]],
    text: str,
) -> List[Dict[str, Any]]:
    from .mtsf_ingest import TRIANGULATION_PHRASES, _evidence_span

    relations: List[Dict[str, Any]] = []
    entity_by_id = {row["proposed_id"]: row for row in entities}
    context_entity = entity_by_id.get("entity-context-field")
    path_entity = entity_by_id.get("entity-latent-manifold") or entity_by_id.get("entity-effective-topology")
    if not path_entity and entities:
        path_entity = entities[0]

    if context_entity and path_entity:
        relations.append(
            {
                "source_ref": context_entity["proposed_id"],
                "target_ref": path_entity["proposed_id"],
                "level": "entity_entity",
                "relation_type": "steers",
                "primitive": "modulates",
                "domain_expression": "context field modulates inference path or topology",
                "weight": 0.88,
                "confidence": 0.84,
                "evidence": {
                    "spans": [_evidence_span(text, ("context", "topology", "modulates", "prior context"))]
                },
            }
        )

    for quality in qualities:
        entity_ref = quality.get("entity_ref") or (entities[0]["proposed_id"] if entities else None)
        if not entity_ref:
            continue
        relations.append(
            {
                "source_ref": quality["quality_id"],
                "target_ref": entity_ref,
                "level": "quality_entity",
                "relation_type": "conditions",
                "primitive": "modulates",
                "domain_expression": f"{quality.get('quality_id')} conditions {entity_ref}",
                "weight": float(quality.get("intensity", 0.7)),
                "confidence": float(quality.get("confidence", 0.75)),
                "evidence": quality.get("evidence", {"spans": [_evidence_span(text, TRIANGULATION_PHRASES)]}),
            }
        )

    cold = next((row for row in qualities if "cold" in str(row.get("quality_id", ""))), None)
    anchored = next((row for row in qualities if "anchored" in str(row.get("quality_id", "")) or "overlap" in str(row.get("quality_id", ""))), None)
    orthogonal = next((row for row in qualities if "orthogonal" in str(row.get("quality_id", ""))), None)
    if cold and anchored:
        relations.append(
            {
                "source_ref": cold["quality_id"],
                "target_ref": anchored["quality_id"],
                "level": "quality_quality",
                "relation_type": "contrasts_with",
                "primitive": "intensifies",
                "domain_expression": "cold start contrasts anchored context",
                "weight": 0.8,
                "confidence": 0.78,
                "evidence": cold.get("evidence", {"spans": [_evidence_span(text, TRIANGULATION_PHRASES)]}),
            }
        )
    if anchored and orthogonal:
        relations.append(
            {
                "source_ref": orthogonal["quality_id"],
                "target_ref": anchored["quality_id"],
                "level": "quality_quality",
                "relation_type": "pollutes",
                "primitive": "modulates",
                "domain_expression": "orthogonal context disrupts anchored conditioning",
                "weight": 0.82,
                "confidence": 0.8,
                "evidence": orthogonal.get("evidence", {"spans": [_evidence_span(text, TRIANGULATION_PHRASES)]}),
            }
        )
    return relations


def build_deep_extraction_draft_heuristic(
    *,
    session_id: str,
    events: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
    raw_content: Optional[str] = None,
) -> Dict[str, Any]:
    from .mtsf_ingest import build_fast_extraction_draft

    draft = build_fast_extraction_draft(
        session_id=session_id,
        events=events,
        manifest=manifest,
        raw_content=raw_content,
    )
    text = draft.get("raw_content", "")
    entities = draft.get("entities", [])
    qualities = draft.get("qualities", [])
    candidate_shapes = draft.get("candidate_shapes", [])
    stencil_drafts = list(draft.get("stencil_drafts", []))

    if candidate_shapes and not stencil_drafts:
        from .mtsf_ingest import _detect_stencil_drafts
        from .mtsf_session import infer_session_signals

        domains = manifest.get("domains", [])
        tags = draft.get("context", {}).get("tags", [])
        signals = infer_session_signals(events, domains=domains, tags=tags)
        stencil_drafts = _detect_stencil_drafts(text, signals)

    quality_roles = _build_quality_roles(qualities, entities)
    relations = _build_deep_relations(entities, qualities, text)

    confidence = float(draft.get("confidence", 0.62))
    if relations:
        confidence += 0.05
    if quality_roles:
        confidence += 0.03
    if stencil_drafts:
        confidence += 0.05
    confidence = min(confidence, 0.93)

    uncertainties = [
        "Deep heuristic extraction from session events; LLM skill pass may refine relations and stencil topology."
    ]
    if candidate_shapes and not stencil_drafts:
        uncertainties.append("Candidate shapes present but no confident stencil topology; review before promotion.")

    draft.update(
        {
            "capture_mode": "deep",
            "quality_roles": quality_roles,
            "relations": relations,
            "stencil_drafts": stencil_drafts,
            "confidence": confidence,
            "uncertainties": uncertainties,
            "provenance": {
                **draft.get("provenance", {}),
                "model_id": "mtsf_ingest.deep_heuristic",
                "stages_completed": sorted(DEEP_STAGES),
            },
        }
    )
    return draft


def resolve_deep_extraction_draft(
    root: Path,
    *,
    session_id: str,
    events: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
    raw_content: Optional[str] = None,
    llm_preference: str = "agent",
) -> Dict[str, Any]:
    from .mtsf_ingest import _conversation_text

    text = raw_content or _conversation_text(events)
    envelope = build_skill_input_envelope(
        session_id=session_id,
        events=events,
        manifest=manifest,
        raw_content=text,
        capture_mode="deep",
    )
    skill_refs = materialize_skill_input(root, session_id, envelope)
    fallback_reason: Optional[str] = None

    if llm_preference in {"auto", "force"}:
        try:
            llm_result = request_llm_deep_extraction(root, session_id=session_id, envelope=envelope)
            return {
                "draft": llm_result["draft"],
                "source": llm_result["source"],
                "backend_id": llm_result.get("backend_id"),
                "artifact_refs": skill_refs,
            }
        except Exception as exc:
            if llm_preference == "force":
                raise
            fallback_reason = str(exc)

    if llm_preference in {"auto", "agent"}:
        from .mtsf_agent_extractor import build_agent_skill_extraction_draft

        draft = build_agent_skill_extraction_draft(
            session_id=session_id,
            events=events,
            manifest=manifest,
            raw_content=text,
        )
        return {
            "draft": draft,
            "source": "agent_skill",
            "fallback_reason": fallback_reason,
            "artifact_refs": skill_refs,
        }

    draft = build_deep_extraction_draft_heuristic(
        session_id=session_id,
        events=events,
        manifest=manifest,
        raw_content=text,
    )
    return {
        "draft": draft,
        "source": "deep_heuristic",
        "fallback_reason": fallback_reason,
        "artifact_refs": skill_refs,
    }
