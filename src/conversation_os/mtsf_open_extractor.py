from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from .mtsf_agent_extractor import AGENT_ENTITY_HINTS, AGENT_RELATION_TEMPLATES
from .mtsf_extraction import DEEP_STAGES, SKILL_ID, SKILL_VERSION
from .mtsf_ingest import ENTITY_HINTS, TRIANGULATION_PHRASES, _collect_tags, _conversation_text, _evidence_span
from .mtsf_session import SessionActivationSignals, infer_session_signals
from .storage import make_id, utc_now

MODULE_ID = "kernel.mtsf.open_extractor"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "OPEN_ENTITY_HINTS",
    "MERGED_ENTITY_HINTS",
    "build_open_deep_extraction_draft",
)
__all__ = list(PUBLIC_API)

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
        "they",
        "them",
        "their",
        "you",
        "your",
        "we",
        "our",
        "i",
        "my",
        "he",
        "she",
        "his",
        "her",
        "not",
        "also",
        "very",
        "just",
        "more",
        "most",
        "some",
        "any",
        "all",
        "each",
        "every",
        "both",
        "few",
        "many",
        "much",
        "such",
        "no",
        "nor",
        "only",
        "own",
        "same",
        "so",
        "than",
        "too",
        "here",
        "there",
        "when",
        "where",
        "why",
        "how",
        "what",
        "which",
        "who",
        "whom",
        "yes",
        "here",
        "probably",
        "maybe",
        "actually",
        "really",
        "one",
        "two",
        "three",
        "first",
        "second",
        "third",
        "into",
        "about",
        "after",
        "before",
        "between",
        "through",
        "during",
        "without",
        "within",
        "along",
        "following",
        "across",
        "behind",
        "beyond",
        "plus",
        "film",
        "movie",
        "country",
        "fits",
        "why",
        "closest",
        "said",
        "said",
        "chatgpt",
    }
)

OPEN_ENTITY_HINTS: Tuple[Dict[str, Any], ...] = (
    {
        "keywords": ("thought tube",),
        "proposed_id": "entity-thought-tube",
        "name": "thought tube",
        "type": "composite",
        "stable_identity": ["curated experiential channel for inner-space metaphors"],
    },
    {
        "keywords": ("backrooms", "liminal-space", "liminal space", "liminal"),
        "proposed_id": "entity-liminal-space",
        "name": "liminal space",
        "type": "composite",
        "stable_identity": ["wrong-familiar architecture with no clean exit"],
    },
    {
        "keywords": (
            "subconscious maze",
            "subconscious architecture",
            "memory architecture",
            "psychological interior",
            "psychological maze",
            "inner desire",
        ),
        "proposed_id": "entity-subconscious-architecture",
        "name": "subconscious architecture",
        "type": "composite",
        "stable_identity": ["built environment that externalizes inner structure"],
    },
    {
        "keywords": ("the zone", " metaphysical zone", "forbidden space", "metaphysical space"),
        "proposed_id": "entity-metaphysical-zone",
        "name": "metaphysical zone",
        "type": "composite",
        "stable_identity": ["space that tests meaning, memory, and desire"],
    },
    {
        "keywords": ("impossible architecture", "no-exit architecture", "endless corridor", "endless suburb"),
        "proposed_id": "entity-trap-architecture",
        "name": "trap architecture",
        "type": "composite",
        "stable_identity": ["spatial configuration that encloses rather than orients"],
    },
    {
        "keywords": ("dream logic", "dream-logic", "materializes", "memory materializes"),
        "proposed_id": "entity-memory-materialization",
        "name": "memory materialization",
        "type": "composite",
        "stable_identity": ["inner memory becoming physically present in space"],
    },
    {
        "keywords": ("empty hallway", "hallway", "endless hallway", "corridor"),
        "proposed_id": "entity-hallway",
        "name": "hallway",
        "type": "composite",
        "stable_identity": ["liminal corridor with institutional stillness"],
    },
    {
        "keywords": ("fluorescent light", "cold fluorescent", "fluorescent", "harsh light"),
        "proposed_id": "entity-fluorescent-light",
        "name": "fluorescent light",
        "type": "composite",
        "stable_identity": ["cold overhead illumination that flattens space"],
    },
)


def _merge_entity_hints() -> Tuple[Dict[str, Any], ...]:
    merged: Dict[str, Dict[str, Any]] = {}
    for hint in (*ENTITY_HINTS, *AGENT_ENTITY_HINTS, *OPEN_ENTITY_HINTS):
        proposed_id = str(hint["proposed_id"])
        keywords = tuple(str(keyword) for keyword in hint.get("keywords", ()))
        if proposed_id not in merged:
            merged[proposed_id] = {
                "keywords": keywords,
                "proposed_id": proposed_id,
                "name": hint["name"],
                "type": hint.get("type", "composite"),
                "stable_identity": list(hint.get("stable_identity", [])),
            }
            continue
        existing = merged[proposed_id]
        existing_keywords = set(existing["keywords"])
        existing_keywords.update(keywords)
        existing["keywords"] = tuple(sorted(existing_keywords, key=len, reverse=True))
        if hint.get("stable_identity"):
            stable = list(existing.get("stable_identity", []))
            for item in hint.get("stable_identity", []):
                if item not in stable:
                    stable.append(str(item))
            existing["stable_identity"] = stable
    return tuple(merged.values())


MERGED_ENTITY_HINTS = _merge_entity_hints()


def _slug_entity_id(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return f"entity-{slug[:48]}" or "entity-discourse"


def _detect_seed_entities(text: str, hints: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    lowered = text.lower()
    entities: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for hint in hints:
        if not any(keyword.lower() in lowered for keyword in hint["keywords"]):
            continue
        proposed_id = str(hint["proposed_id"])
        if proposed_id in seen:
            continue
        seen.add(proposed_id)
        entities.append(
            {
                "proposed_id": proposed_id,
                "name": hint["name"],
                "type": hint.get("type", "composite"),
                "stable_identity": list(hint.get("stable_identity", [])),
                "confidence": 0.8,
                "evidence": {"spans": [_evidence_span(text, hint["keywords"])]},
            }
        )
    return entities


def _tokenize_phrase(phrase: str) -> List[str]:
    return [token for token in re.findall(r"[a-z0-9']+", phrase.lower()) if token and token not in _STOPWORDS]


def _is_noisy_phrase(name: str) -> bool:
    tokens = name.split()
    if len(tokens) < 2:
        return True
    if any(token in {"if", "want", "good", "useful", "lists", "portal", "dark", "strange", "test"} for token in tokens):
        return True
    if name.startswith("and ") or name.endswith(" behaves"):
        return True
    return False


def _detect_recurring_phrase_entities(text: str, *, max_entities: int = 4) -> List[Dict[str, Any]]:
    lowered = text.lower()
    counts: Dict[str, int] = {}
    for match in re.finditer(r"[a-z][a-z0-9'/-]{1,}(?:\s+[a-z][a-z0-9'/-]{1,}){0,3}", lowered):
        phrase = match.group(0).strip(" -")
        tokens = _tokenize_phrase(phrase)
        if len(tokens) < 2 or len(tokens) > 4:
            continue
        if any(token in _STOPWORDS for token in tokens[:1]):
            continue
        counts[phrase] = counts.get(phrase, 0) + 1

    entities: List[Dict[str, Any]] = []
    seen_names: Set[str] = set()
    for phrase, count in sorted(counts.items(), key=lambda item: (-item[1], -len(item[0]))):
        if count < 2:
            continue
        name = " ".join(_tokenize_phrase(phrase))
        if not name or name in seen_names or _is_noisy_phrase(name):
            continue
        seen_names.add(name)
        span = _evidence_span(text, (phrase,))
        entities.append(
            {
                "proposed_id": _slug_entity_id(name),
                "name": name,
                "type": "composite",
                "stable_identity": [f"recurring discourse phrase ({count} mentions)"],
                "confidence": min(0.62 + 0.04 * count, 0.84),
                "evidence": {"spans": [span]},
            }
        )
        if len(entities) >= max_entities:
            break
    return entities


def _detect_metaphor_anchor_entities(text: str, *, max_entities: int = 2) -> List[Dict[str, Any]]:
    patterns = (
        r"(?P<anchor>[A-Za-z][A-Za-z0-9' /-]{2,40}?)\s+(?:as|like)\s+(?P<target>[A-Za-z][A-Za-z0-9' /-]{2,40})",
        r"(?:behaves like|becomes|acts as)\s+(?:a\s+)?(?P<target>[A-Za-z][A-Za-z0-9' /-]{2,40})",
    )
    entities: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            for key in ("anchor", "target"):
                raw = match.groupdict().get(key)
                if not raw:
                    continue
                name = " ".join(_tokenize_phrase(raw))
                if len(name.split()) > 4 or len(name) < 4:
                    continue
                if name in seen:
                    continue
                seen.add(name)
                span = text[max(0, match.start() - 10) : min(len(text), match.end() + 20)].strip()
                entities.append(
                    {
                        "proposed_id": _slug_entity_id(name),
                        "name": name,
                        "type": "composite",
                        "stable_identity": ["metaphor anchor surfaced from prose"],
                        "confidence": 0.74,
                        "evidence": {"spans": [span]},
                    }
                )
                if len(entities) >= max_entities:
                    return entities
    return entities


def _merge_entities(*groups: Sequence[Dict[str, Any]], max_entities: int = 12) -> List[Dict[str, Any]]:
    merged: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    seen_names: Set[str] = set()
    for group in groups:
        for row in group:
            proposed_id = str(row.get("proposed_id", ""))
            name = str(row.get("name", "")).strip().lower()
            if not proposed_id or proposed_id in seen_ids or name in seen_names:
                continue
            seen_ids.add(proposed_id)
            seen_names.add(name)
            merged.append(row)
            if len(merged) >= max_entities:
                return merged
    return merged


def _detect_open_qualities(
    text: str,
    entities: Sequence[Dict[str, Any]],
    signals: SessionActivationSignals,
) -> List[Dict[str, Any]]:
    from .mtsf_ingest import _detect_qualities

    qualities = _detect_qualities(text, signals, entities)
    lowered = text.lower()
    entity_ref = entities[0]["proposed_id"] if entities else None

    def add_quality(
        quality_id: str,
        labels: Sequence[str],
        *,
        keywords: Sequence[str],
        quality_type: str = "emergent",
        confidence: float = 0.76,
    ) -> None:
        if not any(keyword.lower() in lowered for keyword in keywords):
            return
        if any(row.get("quality_id") == quality_id for row in qualities):
            return
        qualities.append(
            {
                "quality_id": quality_id,
                "quality_type": quality_type,
                "intensity": 0.78,
                "kind": "emergent",
                "entity_ref": entity_ref,
                "labels": list(labels),
                "confidence": confidence,
                "evidence": {"spans": [_evidence_span(text, keywords)]},
            }
        )

    add_quality("quality-liminal", ["liminal", "uncanny"], keywords=("liminal", "uncanny", "wrong familiar"))
    add_quality("quality-no-exit", ["trapped", "no_exit"], keywords=("no-exit", "no exit", "trapped", "endless"))
    add_quality("quality-watched", ["watched"], keywords=("watched", "surveillance"))
    add_quality("quality-empty", ["empty"], keywords=("empty",))
    add_quality("quality-dreamlike", ["dreamlike"], keywords=("dream logic", "dream-logic", "dreamlike"))
    if any(phrase in lowered for phrase in TRIANGULATION_PHRASES):
        add_quality("quality-cold-start", ["no prior context"], keywords=TRIANGULATION_PHRASES[:2])
    return qualities


def _detect_open_relations(
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
        relations.append(
            {
                "source_ref": source,
                "target_ref": target,
                "level": str(template.get("level", "entity_entity")),
                "relation_type": template["relation_type"],
                "primitive": template["primitive"],
                "domain_expression": template["domain_expression"],
                "weight": 0.82,
                "confidence": 0.78,
                "evidence": {
                    "spans": [
                        _evidence_span(
                            text,
                            (
                                template["domain_expression"],
                                template["relation_type"],
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

    if len(entities) >= 2:
        left = entities[0]
        right = entities[1]
        relations.append(
            {
                "source_ref": left["proposed_id"],
                "target_ref": right["proposed_id"],
                "level": "entity_entity",
                "relation_type": "evokes",
                "primitive": "resembles",
                "domain_expression": f"{left['name']} evokes {right['name']}",
                "weight": 0.7,
                "confidence": 0.68,
                "evidence": {"spans": [_evidence_span(text, (left["name"], right["name"]))]},
            }
        )
    return relations


def _detect_open_candidate_shapes(
    text: str,
    entities: Sequence[Dict[str, Any]],
    qualities: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    lowered = text.lower()
    shapes: List[Dict[str, Any]] = []
    entity_refs = [row["proposed_id"] for row in entities[:4]]
    quality_refs = [row["quality_id"] for row in qualities[:4]]
    if "liminal" in lowered or "backrooms" in lowered or "wrong-familiar" in lowered or "wrong familiar" in lowered:
        shapes.append(
            {
                "proposed_id": "cand-liminal-trap",
                "possible_names": ["liminal trap", "wrong-familiar enclosure"],
                "relational_configuration": "familiar surface + spatial wrongness + no clean exit",
                "entity_refs": entity_refs,
                "quality_refs": quality_refs,
                "confidence": 0.74,
                "evidence": {"spans": [_evidence_span(text, ("liminal", "backrooms", "no-exit", "endless"))]},
            }
        )
    if "subconscious" in lowered and ("architecture" in lowered or "maze" in lowered):
        shapes.append(
            {
                "proposed_id": "cand-subconscious-architecture",
                "possible_names": ["subconscious architecture", "inner space as built form"],
                "relational_configuration": "psychological interior rendered as navigable architecture",
                "entity_refs": entity_refs,
                "quality_refs": quality_refs,
                "confidence": 0.76,
                "evidence": {"spans": [_evidence_span(text, ("subconscious", "architecture", "maze"))]},
            }
        )
    if "hallway" in lowered or "fluorescent" in lowered:
        shapes.append(
            {
                "proposed_id": "cand-hallway-uncanny",
                "possible_names": ["hallway uncanny", "peaceful surveillance corridor"],
                "relational_configuration": "institutional calm + ambient light + watched stillness",
                "entity_refs": entity_refs,
                "quality_refs": quality_refs,
                "confidence": 0.73,
                "evidence": {"spans": [_evidence_span(text, ("hallway", "fluorescent", "watched", "peaceful"))]},
            }
        )
    return shapes


def build_open_deep_extraction_draft(
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

    seed_entities = _detect_seed_entities(text, MERGED_ENTITY_HINTS)
    phrase_entities = _detect_recurring_phrase_entities(text)
    metaphor_entities = _detect_metaphor_anchor_entities(text)
    entities = _merge_entities(seed_entities, phrase_entities, metaphor_entities)
    qualities = _detect_open_qualities(text, entities, signals)
    relations = _detect_open_relations(text, entities, qualities)
    keyword_shapes = _detect_open_candidate_shapes(text, entities, qualities)
    from .mtsf_embeddings import build_semantic_cluster_candidate_shapes

    candidate_shapes = build_semantic_cluster_candidate_shapes(
        root=Path("."),
        text=text,
        entities=entities,
        relations=relations,
        qualities=qualities,
        existing_shapes=keyword_shapes,
    )

    from .mtsf_extraction_skill import _build_quality_roles

    quality_roles = _build_quality_roles(qualities, entities)

    confidence = 0.66
    if entities:
        confidence += min(0.14, 0.02 * len(entities))
    if relations:
        confidence += min(0.08, 0.01 * len(relations))
    if candidate_shapes:
        confidence += 0.04
    confidence = min(confidence, 0.9)

    uncertainties = [
        "Open evidence extraction maps discourse phrases and merged seed hints; semantic LLM pass may refine topology and cross-register aliases.",
    ]
    if not entities:
        uncertainties.append(
            "No stable entities surfaced from evidence spans; review whether the source needs semantic LLM extraction or manual annotation."
        )

    subgraph_id = domains[0] if domains else f"session-{session_id}"
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
            "model_id": "mtsf_ingest.open_evidence",
            "extracted_at": utc_now(),
            "stages_completed": sorted(DEEP_STAGES),
        },
        "entities": entities,
        "sub_entities": [],
        "qualities": qualities,
        "quality_roles": quality_roles,
        "relations": relations,
        "candidate_shapes": candidate_shapes,
        "stencil_drafts": [],
        "activation_snapshot_hint": {
            "formation_phase": signals.formation_phase,
            "meta_shape_id": signals.meta_shape_id,
            "meta_move_id": signals.meta_move_id,
            "dominant_entity_refs": [row["proposed_id"] for row in entities[:3]],
            "active_quality_refs": [row["quality_id"] for row in qualities[:5]],
        },
        "artifact_pathways": [],
        "uncertainties": uncertainties,
        "user_questions": [],
        "confidence": confidence,
        "status": "proposed",
    }
