from __future__ import annotations

import re
from typing import Dict, List

from .vault_ingest import shorten, tokenize


MODULE_ID = "kernel.reasoning.operators"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "DIMENSION_RULES",
    "PATTERN_RULES",
    "TENSION_RULES",
    "POLARITY_RULES",
    "GENERIC_PHRASES",
    "_detect_patterns",
    "normalize_capture",
    "infer_capture_context",
    "clarify_core_meaning",
    "separate_layers",
    "detect_shared_primitive",
    "build_why_it_matters",
    "clarify_connection_context",
    "detect_connection_primitive",
    "detect_connection_tension",
    "build_connection_why_it_matters",
    "build_connection_candidate",
    "fidelity_check",
    "genericity_filter",
    "confidence_calibration",
    "relevance_check",
    "review_gate",
    "OPERATOR_REGISTRY",
)
__all__ = list(PUBLIC_API)


DIMENSION_RULES = {
    "tension": {"but", "however", "versus", "tradeoff", "tension", "conflict"},
    "question": {"why", "how", "what", "question", "?"},
    "pattern": {"pattern", "recurring", "again", "keeps", "repeats"},
    "direction": {"should", "must", "need", "build", "prefer", "choose", "let"},
    "review": {"review", "uncertain", "provisional", "contradiction", "maybe"},
}

PATTERN_RULES = [
    {
        "label": "ambiguity_then_structure",
        "family": "heuristics",
        "keywords": {"ambiguity", "decompress", "structure", "attune", "unpack", "emerge"},
        "summary": "Preserve ambiguity early, then crystallize structure later.",
        "transfer_targets": ["writing", "journaling", "research_synthesis"],
    },
    {
        "label": "cognitive_fidelity",
        "family": "motivating_tensions",
        "keywords": {"fidelity", "nuance", "generic", "sludge", "flatten", "signal"},
        "summary": "Protect nuance and underlying signal from generic flattening.",
        "transfer_targets": ["product_design", "knowledge_work", "research"],
    },
    {
        "label": "review_before_commit",
        "family": "review_governance_preferences",
        "keywords": {"review", "commit", "approve", "persist", "gate"},
        "summary": "Require review before durable memory promotion.",
        "transfer_targets": ["memory_governance", "product_safety"],
    },
    {
        "label": "private_cognitive_layer",
        "family": "axioms",
        "keywords": {"private", "cognitive", "layer", "local", "sovereignty"},
        "summary": "The system is a private cognitive layer, not generic SaaS.",
        "transfer_targets": ["trust_architecture", "product_positioning"],
    },
    {
        "label": "progressive_disclosure",
        "family": "communication_storytelling_preferences",
        "keywords": {"progressive", "expand", "small", "deeper", "surface", "article"},
        "summary": "Show the smallest useful thought first, then unfold more depth.",
        "transfer_targets": ["interface_design", "editorial_systems"],
    },
]

TENSION_RULES = [
    ("ambiguity", "structure", "preserve ambiguity without losing structure"),
    ("privacy", "scale", "local sovereignty versus scale"),
    ("signal", "summary", "signal preservation versus summary collapse"),
    ("autonomy", "review", "autonomy versus review"),
    ("capture", "organization", "raw capture versus later organization"),
]

POLARITY_RULES = {
    "expansive": {"expand", "explore", "autonomous", "broader", "multimodal", "shared"},
    "protective": {"review", "bounded", "local", "private", "manual", "quiet", "defer", "preserve"},
}

GENERIC_PHRASES = {
    "this insight suggests",
    "in today's fast-paced",
    "unlock value",
    "leverage synergy",
    "drive innovation",
}

LOW_SIGNAL_EMERGENT_TERMS = {
    "answer",
    "because",
    "chatgpt",
    "continue",
    "does",
    "example",
    "examples",
    "exposes",
    "file",
    "files",
    "idea",
    "interprets",
    "lets",
    "meaning",
    "most",
    "more",
    "one",
    "our",
    "proposes",
    "question",
    "questions",
    "reason",
    "same",
    "said",
    "think",
    "thought",
    "title",
    "uploaded",
    "yes",
    "you",
}


def _first_sentence(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    for sentence in sentences:
        cleaned = sentence.strip()
        if cleaned:
            return cleaned
    return text.strip()


def _top_terms(text: str, limit: int = 5) -> List[str]:
    ordered: List[str] = []
    for token in tokenize(text):
        if token not in ordered:
            ordered.append(token)
    return ordered[:limit]


def _meaningful_emergent_terms(text: str, limit: int = 5) -> List[str]:
    ordered: List[str] = []
    for token in tokenize(text):
        if token in LOW_SIGNAL_EMERGENT_TERMS:
            continue
        if token not in ordered:
            ordered.append(token)
    return ordered[:limit]


def _clean_phrase(text: str, limit: int = 120) -> str:
    cleaned = re.sub(r"[*_`>#]+", " ", text or "")
    cleaned = cleaned.replace("–", " ").replace("—", " ").replace("/", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;-/")
    cleaned = re.sub(r"^(function|summary|because|why this matters)\s*:\s*", "", cleaned, flags=re.I)
    cleaned = re.sub(r"^\W+", "", cleaned)
    sentence = _first_sentence(cleaned)
    return shorten(sentence, limit).rstrip(" .")


def _is_natural_clause(text: str) -> bool:
    tokens = tokenize(text)
    if not tokens or len(tokens) > 18:
        return False
    markers = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "because",
        "before",
        "between",
        "but",
        "can",
        "could",
        "for",
        "if",
        "in",
        "is",
        "it",
        "keep",
        "keeps",
        "let",
        "lets",
        "mean",
        "means",
        "must",
        "need",
        "needs",
        "not",
        "of",
        "or",
        "should",
        "stay",
        "stays",
        "through",
        "to",
        "want",
        "wants",
        "with",
        "without",
    }
    return any(token in markers for token in tokens)


def _sentence_case(text: str) -> str:
    text = text.strip()
    if not text:
        return ""
    return text[0].upper() + text[1:]


def _natural_connection_phrase(left: Dict, right: Dict) -> str:
    candidates = []
    for raw in [
        right.get("label", ""),
        left.get("label", ""),
        right.get("summary", ""),
        left.get("summary", ""),
    ]:
        clause = _clean_phrase(raw, 100)
        if clause:
            candidates.append(clause)
    for clause in candidates:
        if _is_natural_clause(clause):
            return _sentence_case(clause)
    return ""


def _soft_title(left: Dict, right: Dict, primitive: str, shared_terms: List[str]) -> str:
    natural = _natural_connection_phrase(left, right)
    if natural:
        return shorten(natural, 72).rstrip(".")
    readable_terms = [term.replace("-", " ") for term in shared_terms if len(term) > 3][:2]
    if len(readable_terms) == 2:
        return _sentence_case(f"{readable_terms[0]} keeps leaning toward {readable_terms[1]}")
    if readable_terms:
        return _sentence_case(f"{readable_terms[0]} keeps returning")
    return _sentence_case(f"Something in {primitive.lower()} keeps asking for room")


def _extract_questions(text: str) -> List[str]:
    questions = []
    for sentence in re.split(r"(?<=[.!?])\s+", text.strip()):
        cleaned = sentence.strip()
        if not cleaned:
            continue
        if cleaned.endswith("?") or re.match(r"^(why|how|what|which)\b", cleaned.lower()):
            questions.append(cleaned.rstrip("."))
    return questions[:4]


def _looks_like_procedural_scaffold(text: str) -> bool:
    action_heads = {
        "builds",
        "creates",
        "decides",
        "detects",
        "exposes",
        "generates",
        "identifies",
        "interprets",
        "maps",
        "proposes",
        "routes",
        "stores",
        "surfaces",
    }
    clauses = [
        tokenize(part)
        for part in re.split(r"(?<=[.!?])\s+|\n+", text.strip())
        if part.strip()
    ]
    short_action_clauses = 0
    for clause in clauses[:4]:
        if len(clause) <= 4 and clause and clause[0] in action_heads:
            short_action_clauses += 1
    return short_action_clauses >= 2


def _detect_dimensions(text: str) -> List[str]:
    lowered = text.lower()
    dimensions = []
    for label, keywords in DIMENSION_RULES.items():
        if any(keyword in lowered for keyword in keywords):
            dimensions.append(label)
    return dimensions or ["pattern"]


def _detect_tensions(text: str) -> List[Dict]:
    lowered = text.lower()
    tensions = []
    for left, right, description in TENSION_RULES:
        if left in lowered or right in lowered:
            tensions.append(
                {
                    "marker": f"{left}_vs_{right}",
                    "description": description,
                }
            )
    if ("but" in lowered or "however" in lowered) and not tensions:
        tensions.append(
            {
                "marker": "internal_friction",
                "description": "The material contains an unresolved internal friction.",
            }
        )
    return tensions[:4]


def _detect_patterns(text: str, plugin_primitives: List[Dict] | None = None) -> List[Dict]:
    lowered = text.lower()
    matches = []
    for rule in PATTERN_RULES:
        hits = sum(1 for keyword in rule["keywords"] if keyword in lowered)
        if hits >= 2:
            matches.append(
                {
                    "primitive_key": rule["label"],
                    "label": rule["label"].replace("_", " ").title(),
                    "family": rule["family"],
                    "evidence": [_first_sentence(text)],
                    "adjacent_concepts": _top_terms(text, 6),
                    "transfer_targets": rule["transfer_targets"],
                    "confidence": round(min(0.95, 0.5 + hits * 0.12), 2),
                    "summary": rule["summary"],
                }
            )
    for primitive in plugin_primitives or []:
        label = primitive.get("label", primitive.get("id", "primitive"))
        keywords = set(tokenize(" ".join(primitive.get("keywords", []))))
        hits = sum(1 for keyword in keywords if keyword in lowered)
        if hits >= 2:
            matches.append(
                {
                    "primitive_key": primitive["id"],
                    "label": label,
                    "family": "plugin_primitive",
                    "evidence": [_first_sentence(text)],
                    "adjacent_concepts": _top_terms(text, 6),
                    "transfer_targets": primitive.get("keywords", [])[:3],
                    "confidence": round(min(0.94, 0.48 + hits * 0.11), 2),
                    "summary": primitive.get("description", label),
                }
            )
    if not matches:
        if _looks_like_procedural_scaffold(text):
            return []
        top_terms = _meaningful_emergent_terms(text, 3)
        if len(top_terms) >= 3:
            matches.append(
                {
                    "primitive_key": "_".join(top_terms),
                    "label": " ".join(term.title() for term in top_terms),
                    "family": "emergent_pattern",
                    "evidence": [_first_sentence(text)],
                    "adjacent_concepts": top_terms,
                    "transfer_targets": ["knowledge_work"],
                    "confidence": 0.56,
                    "summary": "Emergent pattern derived from repeated high-signal terms.",
                }
            )
    return matches[:4]


def _polarity(text: str) -> str | None:
    lowered = text.lower()
    scores = {
        label: sum(1 for keyword in keywords if keyword in lowered)
        for label, keywords in POLARITY_RULES.items()
    }
    best = max(scores.items(), key=lambda item: item[1])
    return best[0] if best[1] else None


def normalize_capture(packet: Dict, _: Dict) -> Dict:
    raw_text = packet["stimulus"]["raw_text"]
    normalized = re.sub(r"\s+", " ", raw_text).strip()
    atomic_units = [unit.strip() for unit in re.split(r"[.;!?]\s*", normalized) if unit.strip()]
    return {
        "stimulus": {"normalized_text": normalized},
        "subconscious_processing": {"atomic_units": atomic_units},
    }


def infer_capture_context(packet: Dict, _: Dict) -> Dict:
    text = packet["stimulus"].get("normalized_text") or packet["stimulus"]["raw_text"]
    dimensions = _detect_dimensions(text)
    if "question" in dimensions:
        note_kind = "questioning"
    elif "direction" in dimensions:
        note_kind = "directional"
    elif "tension" in dimensions:
        note_kind = "tension_note"
    else:
        note_kind = "idea_fragment"
    return {
        "stimulus": {
            "inferred_context": {
                "note_kind": note_kind,
                "likely_pipeline": "vault_decomposition_v1",
                "user_intent_hint": dimensions[0],
            }
        },
        "subconscious_processing": {"active_dimensions": dimensions},
    }


def clarify_core_meaning(packet: Dict, _: Dict) -> Dict:
    text = packet["stimulus"]["normalized_text"]
    dimensions = packet["subconscious_processing"].get("active_dimensions", [])
    core_statement = _first_sentence(text)
    generic_structure = " -> ".join(["raw_signal", *dimensions[:2], "reviewable_shape"])
    interpretations = [
        {
            "label": "surface_reading",
            "reading": core_statement,
            "status": "provisional",
            "confidence": 0.74,
        }
    ]
    if len(dimensions) > 1:
        interpretations.append(
            {
                "label": "process_reading",
                "reading": f"The note is really about the process move from {dimensions[0]} to {dimensions[1]}.",
                "status": "provisional",
                "confidence": 0.69,
            }
        )
    if "direction" in dimensions or "review" in dimensions:
        interpretations.append(
            {
                "label": "contextual_reading",
                "reading": "The note implies a product or governance choice, not just an observation.",
                "status": "speculative",
                "confidence": 0.63,
            }
        )
    return {
        "subconscious_processing": {
            "active_signal_frame": {
                "core_statement": core_statement,
                "generic_structure": generic_structure,
                "transformation_goal": "move from raw signal to structured thought",
                "domain_tokens": _top_terms(text, 6),
                "source_units": packet["subconscious_processing"].get("atomic_units", [])[:4],
            },
            "parallel_interpretations": interpretations,
            "open_questions": _extract_questions(text),
        }
    }


def separate_layers(packet: Dict, _: Dict) -> Dict:
    text = packet["stimulus"]["normalized_text"]
    tensions = _detect_tensions(text)
    questions = packet["subconscious_processing"].get("open_questions", [])
    atomic_units = packet["subconscious_processing"].get("atomic_units", [])
    hidden_requirements = []
    lowered = text.lower()
    if "review" in lowered or "approve" in lowered:
        hidden_requirements.append("keep promotion reviewable")
    if "private" in lowered or "local" in lowered:
        hidden_requirements.append("preserve local sovereignty")
    if "generic" in lowered or "flatten" in lowered:
        hidden_requirements.append("avoid generic flattening")
    constraints = []
    if "not" in lowered or "avoid" in lowered:
        constraints.append("respect explicit anti-goals in the material")
    transformation_path = [step for step in ["capture", "decompress", "connect", "judge", "surface"] if step in lowered]
    if not transformation_path:
        transformation_path = ["capture", "decompress", "surface"]
    return {
        "emergent_structure": {
            "layer_separation": {
                "surface_observations": atomic_units[:3],
                "hidden_requirements": hidden_requirements,
                "questions": questions,
                "constraints": constraints,
                "tensions": [item["description"] for item in tensions],
                "transformation_path": transformation_path,
            }
        },
        "subconscious_processing": {"active_tensions": tensions},
    }


def detect_shared_primitive(packet: Dict, context: Dict) -> Dict:
    text = packet["stimulus"]["normalized_text"]
    primitives = _detect_patterns(text, context.get("plugin_primitives", []))
    adjacent = []
    transfers = []
    for primitive in primitives:
        for concept in primitive.get("adjacent_concepts", []):
            adjacent.append({"concept": concept, "linked_to": primitive["primitive_key"]})
        for target in primitive.get("transfer_targets", []):
            transfers.append({"target": target, "linked_to": primitive["primitive_key"]})
    return {
        "emergent_structure": {
            "shared_primitives": primitives,
            "adjacent_concepts": adjacent[:8],
            "transfer_targets": transfers[:8],
        }
    }


def build_why_it_matters(packet: Dict, _: Dict) -> Dict:
    primitives = packet["emergent_structure"].get("shared_primitives", [])
    tensions = packet["subconscious_processing"].get("active_tensions", [])
    frames = []
    for primitive in primitives:
        frame = (
            f"{primitive['label']} keeps mattering because it changes what deserves attention next "
            f"without flattening the original texture."
        )
        frames.append(
            {
                "primitive_key": primitive["primitive_key"],
                "frame": frame,
                "tension_count": len(tensions),
                "transfer_count": len(primitive.get("transfer_targets", [])),
            }
        )
    if not frames:
        frames.append(
            {
                "primitive_key": "why_it_matters",
                "frame": "There is a quiet shift here that could change how the rest of the vault is read.",
                "tension_count": len(tensions),
                "transfer_count": 0,
            }
        )
    return {"emergent_structure": {"why_it_matters_frames": frames}}


def clarify_connection_context(packet: Dict, _: Dict) -> Dict:
    left = packet["connection"]["left"]
    right = packet["connection"]["right"]
    left_label = _clean_phrase(left.get("label") or left.get("summary") or left.get("title") or "", 80)
    right_label = _clean_phrase(right.get("label") or right.get("summary") or right.get("title") or "", 80)
    if left_label and right_label:
        context_summary = f"{_sentence_case(left_label)} keeps brushing against {right_label.lower()}."
    else:
        context_summary = "Two parts of the vault keep circling the same pressure point."
    return {
        "connection": {
            "context_summary": context_summary,
            "shared_terms": sorted(set(left.get("attributes", {}).get("tokens", [])) & set(right.get("attributes", {}).get("tokens", [])))[:6],
        }
    }


def detect_connection_primitive(packet: Dict, _: Dict) -> Dict:
    left = packet["connection"]["left"]
    right = packet["connection"]["right"]
    left_family = left.get("attributes", {}).get("family")
    right_family = right.get("attributes", {}).get("family")
    shared_terms = packet["connection"].get("shared_terms", [])
    if left_family and left_family == right_family:
        label = left_family.replace("_", " ")
    elif shared_terms:
        label = " ".join(shared_terms[:3])
    else:
        label = f"{left['kind']} to {right['kind']}"
    return {
        "connection": {
            "shared_primitive": {
                "label": label.title(),
                "family": left_family or right_family or "cross_pollination",
            }
        }
    }


def detect_connection_tension(packet: Dict, _: Dict) -> Dict:
    left = packet["connection"]["left"]
    right = packet["connection"]["right"]
    tension = None
    if left["kind"] == "contradiction" or right["kind"] == "contradiction":
        tension = "explicit contradiction"
    elif left.get("attributes", {}).get("polarity") and right.get("attributes", {}).get("polarity"):
        if left["attributes"]["polarity"] != right["attributes"]["polarity"]:
            tension = f"{left['attributes']['polarity']} versus {right['attributes']['polarity']}"
    if not tension:
        tension = "complementary perspective shift"
    return {"connection": {"tension_summary": tension}}


def build_connection_why_it_matters(packet: Dict, _: Dict) -> Dict:
    primitive = packet["connection"]["shared_primitive"]["label"]
    tension = packet["connection"]["tension_summary"]
    if "contradiction" in tension:
        why = "The interesting part is not agreement. One side keeps interrupting the other, which is usually where the real signal hides."
    elif "versus" in tension:
        why = (
            f"The pull here has not settled. {tension.capitalize()} is still shaping the direction of the thought."
        )
    else:
        why = (
            f"The same undercurrent keeps showing up from two directions. {primitive} is less a conclusion than a shift in where attention wants to rest."
        )
    return {
        "connection": {
            "why_it_matters": why
        }
    }


def build_connection_candidate(packet: Dict, _: Dict) -> Dict:
    left = packet["connection"]["left"]
    right = packet["connection"]["right"]
    primitive = packet["connection"]["shared_primitive"]["label"]
    shared_terms = packet["connection"].get("shared_terms", [])
    title = _soft_title(left, right, primitive, shared_terms)
    opening = _natural_connection_phrase(left, right) or f"Something in {primitive.lower()} keeps returning"
    why_it_matters = _clean_phrase(packet["connection"]["why_it_matters"], 120)
    if why_it_matters:
        why_it_matters = re.sub(r"^This matters because\s*", "", why_it_matters, flags=re.I)
        short_text = shorten(f"{opening.rstrip('.')}. {why_it_matters.rstrip('.')}.", 220)
    else:
        short_text = shorten(f"{opening.rstrip('.')}.", 220)
    article_outline = [
        packet["connection"]["context_summary"],
        packet["connection"]["why_it_matters"],
        "The question is whether this deserves to become a durable thought or remain an unfinished pressure point.",
    ]
    return {
        "conscious_articulation": {
            "concept_candidates": [
                {
                    "title": title,
                    "short_text": short_text,
                    "article_outline": article_outline,
                }
            ]
        }
    }


def fidelity_check(packet: Dict, _: Dict) -> Dict:
    candidate = packet["conscious_articulation"]["concept_candidates"][0]
    source_text = " ".join(packet["connection"].get("evidence_texts", []))
    overlap = len(set(tokenize(candidate["short_text"])) & set(tokenize(source_text)))
    ratio = overlap / max(1, len(set(tokenize(candidate["short_text"]))))
    status = "pass" if ratio >= 0.18 else "fail"
    return {
        "conscious_articulation": {
            "evaluation_reports": {
                "fidelity_report": {
                    "status": status,
                    "overlap_ratio": round(ratio, 2),
                }
            }
        }
    }


def genericity_filter(packet: Dict, _: Dict) -> Dict:
    candidate = packet["conscious_articulation"]["concept_candidates"][0]
    lowered = candidate["short_text"].lower()
    status = "pass"
    if any(phrase in lowered for phrase in GENERIC_PHRASES):
        status = "fail"
    if len(tokenize(candidate["short_text"])) < 6:
        status = "fail"
    return {
        "conscious_articulation": {
            "evaluation_reports": {
                "genericity_report": {
                    "status": status,
                }
            }
        }
    }


def confidence_calibration(packet: Dict, _: Dict) -> Dict:
    shared_terms = packet["connection"].get("shared_terms", [])
    left = packet["connection"]["left"]
    right = packet["connection"]["right"]
    base = 0.48 + min(0.24, len(shared_terms) * 0.08)
    if left.get("kind") != right.get("kind"):
        base += 0.08
    if left.get("attributes", {}).get("source_ref") != right.get("attributes", {}).get("source_ref"):
        base += 0.08
    if packet["conscious_articulation"]["evaluation_reports"]["fidelity_report"]["status"] == "fail":
        base -= 0.18
    if packet["conscious_articulation"]["evaluation_reports"]["genericity_report"]["status"] == "fail":
        base -= 0.22
    confidence = max(0.12, min(0.96, round(base, 2)))
    status = "high_confidence" if confidence >= 0.72 else "medium_confidence" if confidence >= 0.56 else "low_confidence"
    return {
        "conscious_articulation": {
            "evaluation_reports": {
                "confidence_report": {
                    "status": status,
                    "confidence": confidence,
                }
            }
        }
    }


def relevance_check(packet: Dict, _: Dict) -> Dict:
    shared_terms = packet["connection"].get("shared_terms", [])
    left = packet["connection"]["left"]
    right = packet["connection"]["right"]
    novelty = 0.46 + (0.16 if left["kind"] != right["kind"] else 0.06)
    novelty += min(0.22, len(shared_terms) * 0.04)
    novelty = round(min(0.95, novelty), 2)
    relevance = 0.5 + min(0.18, len(shared_terms) * 0.03)
    if "direction" in {left["kind"], right["kind"]} or "decision" in {left["kind"], right["kind"]}:
        relevance += 0.12
    relevance = round(min(0.96, relevance), 2)
    return {
        "conscious_articulation": {
            "evaluation_reports": {
                "relevance_report": {
                    "status": "pass" if relevance >= 0.58 else "needs_review",
                    "novelty": novelty,
                    "relevance": relevance,
                }
            }
        }
    }


def review_gate(packet: Dict, _: Dict) -> Dict:
    fidelity = packet["conscious_articulation"]["evaluation_reports"]["fidelity_report"]["status"]
    genericity = packet["conscious_articulation"]["evaluation_reports"]["genericity_report"]["status"]
    confidence_report = packet["conscious_articulation"]["evaluation_reports"]["confidence_report"]
    relevance_report = packet["conscious_articulation"]["evaluation_reports"]["relevance_report"]

    if fidelity == "fail" or genericity == "fail":
        review_status = "insufficient_quality"
        next_action = "revise_or_dismiss"
    elif confidence_report["status"] == "low_confidence" or relevance_report["status"] != "pass":
        review_status = "ready_for_review"
        next_action = "human_review_then_persist"
    else:
        review_status = "approved_for_surface"
        next_action = "materialize_thought"

    return {
        "memory_commit": {
            "review_status": review_status,
            "next_action": next_action,
            "graph_update_plan": {
                "status": review_status,
                "connection_kinds": [
                    packet["connection"]["left"]["kind"],
                    packet["connection"]["right"]["kind"],
                ],
            },
        }
    }


OPERATOR_REGISTRY = {
    "normalize_capture": normalize_capture,
    "infer_capture_context": infer_capture_context,
    "clarify_core_meaning": clarify_core_meaning,
    "separate_layers": separate_layers,
    "detect_shared_primitive": detect_shared_primitive,
    "build_why_it_matters": build_why_it_matters,
    "clarify_connection_context": clarify_connection_context,
    "detect_connection_primitive": detect_connection_primitive,
    "detect_connection_tension": detect_connection_tension,
    "build_connection_why_it_matters": build_connection_why_it_matters,
    "build_connection_candidate": build_connection_candidate,
    "fidelity_check": fidelity_check,
    "genericity_filter": genericity_filter,
    "confidence_calibration": confidence_calibration,
    "relevance_check": relevance_check,
    "review_gate": review_gate,
}
