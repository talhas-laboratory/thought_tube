from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from .meta_layer import load_meta_records
from .models import ConceptEdge, ConceptNode, SynthesisPacket, ThoughtPacket, TouchOperation
from .storage import read_json, read_jsonl, session_dir, session_events_path, sorted_files, utc_now, write_json, write_jsonl
from .vault_ingest import shorten, tokenize


MODULE_ID = "kernel.synthesis.conversation_synthesis"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "FormationCandidate",
    "ShapeMatch",
    "OperatorDecision",
    "SynthesisCandidate",
    "StressTestResult",
    "load_concept_nodes",
    "load_concept_edges",
    "load_synthesis_packets",
    "load_touch_operations",
    "load_concept_review_queue",
    "ensure_concept_alias_registry",
    "load_concept_alias_registry",
    "ensure_concept_merge_policy",
    "load_concept_merge_policy",
    "canonicalize_concept_identity",
    "rebuild_conversation_concepts",
    "search_concepts",
    "derive_development_signals",
    "load_formation_synthesis_reviews",
    "retrieve_candidates",
    "match_shapes",
    "choose_operator",
    "synthesize_candidate",
    "stress_test_candidate",
    "emit_thought_packet",
    "record_formation_synthesis_review",
)
__all__ = list(PUBLIC_API)


DEFAULT_MERGE_POLICY = {
    "version": 1,
    "auto_merge_threshold": 0.78,
    "review_threshold": 0.58,
    "minimum_threshold": 0.34,
    "max_concepts_per_session": 8,
    "neighbor_boost": 0.18,
    "always_review_touch_types": ["contradicts"],
    "prefer_review_touch_types": ["reframes", "changes_priority"],
    "status_weights": {
        "active": 1.0,
        "provisional": 0.82,
        "needs_review": 0.72,
        "archived": 0.48,
    },
}

DEFAULT_ALIAS_REGISTRY = {
    "version": 1,
    "concepts": [],
}

_GENERIC_TOKENS = {
    "agent",
    "analysis",
    "answer",
    "assistant",
    "because",
    "better",
    "build",
    "building",
    "change",
    "changes",
    "chat",
    "code",
    "conversation",
    "conversations",
    "design",
    "does",
    "done",
    "example",
    "future",
    "good",
    "idea",
    "import",
    "implementation",
    "inner",
    "just",
    "kind",
    "layer",
    "need",
    "needs",
    "next",
    "okay",
    "please",
    "project",
    "really",
    "repo",
    "session",
    "sessions",
    "should",
    "something",
    "system",
    "task",
    "that",
    "them",
    "then",
    "there",
    "these",
    "they",
    "thing",
    "this",
    "those",
    "through",
    "turn",
    "user",
    "using",
    "want",
    "what",
    "when",
    "where",
    "which",
    "work",
    "world",
    "would",
    "your",
}

_MECHANISM_HINTS = {
    "abstraction",
    "agent",
    "artifact",
    "control",
    "cybernetics",
    "edge",
    "feedback",
    "governance",
    "graph",
    "knowledge",
    "memory",
    "merge",
    "module",
    "navigation",
    "node",
    "pattern",
    "pipeline",
    "policy",
    "propagation",
    "query",
    "reasoning",
    "retrieval",
    "review",
    "route",
    "routing",
    "runtime",
    "signal",
    "state",
    "structure",
    "synthesis",
    "thread",
    "touch",
    "transfer",
    "update",
}

_NEGATION_MARKERS = {"not", "instead", "rather", "versus", "wrong", "avoid"}
_PRIORITY_MARKERS = {"priority", "prioritize", "default", "first", "ranking", "threshold"}
_PATH_PATTERN = re.compile(r"(/[^`\s]+|\b[\w./-]+\.(?:py|md|json|jsonl|txt|toml)\b)")
_BACKTICK_PATTERN = re.compile(r"`([^`]{2,80})`")


@dataclass
class FormationCandidate:
    candidate_id: str
    meta_id: str
    kind: str
    label: str
    summary: str
    source_refs: List[str]
    chunk_ids: List[str]
    evidence: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)
    candidate_score: float = 0.0
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShapeMatch:
    match_id: str
    anchor_meta_id: str
    anchor_kind: str
    candidate_meta_id: str
    candidate_kind: str
    edge_kind: str
    score: float
    shared_tokens: List[str] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    operator_hints: List[str] = field(default_factory=list)
    source_refs: List[str] = field(default_factory=list)
    source_item_ids: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    anchor_label: str = ""
    candidate_label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OperatorDecision:
    operator_key: str
    confidence: float
    rationale: str
    fallback_operator_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SynthesisCandidate:
    synthesis_id: str
    anchor_meta_id: str
    candidate_meta_id: str
    operator_key: str
    title: str
    short_text: str
    summary: str
    what_changed: str
    why_it_matters_now: str
    next_action: str
    source_refs: List[str]
    source_item_ids: List[str]
    meta_refs: List[str]
    confidence_score: float
    relevance_score: float
    novelty_score: float
    evidence_status: str
    review_status: str
    shared_primitive_key: str
    shared_primitive_label: str
    reasoning_pipeline: str
    rationale: str
    shared_tokens: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StressTestResult:
    should_surface: bool
    review_status: str
    evidence_status: str
    confidence_adjustment: float
    concerns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _concept_graph_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "concept_graph"


def _concept_nodes_path(root: Path) -> Path:
    return _concept_graph_dir(root) / "concept_nodes.jsonl"


def _concept_edges_path(root: Path) -> Path:
    return _concept_graph_dir(root) / "concept_edges.jsonl"


def _synthesis_packets_path(root: Path) -> Path:
    return _concept_graph_dir(root) / "synthesis_packets.jsonl"


def _touch_operations_path(root: Path) -> Path:
    return _concept_graph_dir(root) / "touch_operations.jsonl"


def _review_queue_path(root: Path) -> Path:
    return _concept_graph_dir(root) / "review_queue.jsonl"


def _policy_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "concept_merge_policy.json"


def _alias_registry_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "concept_alias_registry.json"


def load_concept_nodes(root: Path) -> List[Dict]:
    return read_jsonl(_concept_nodes_path(root))


def load_concept_edges(root: Path) -> List[Dict]:
    return read_jsonl(_concept_edges_path(root))


def load_synthesis_packets(root: Path) -> List[Dict]:
    return read_jsonl(_synthesis_packets_path(root))


def load_touch_operations(root: Path) -> List[Dict]:
    return read_jsonl(_touch_operations_path(root))


def load_concept_review_queue(root: Path) -> List[Dict]:
    return read_jsonl(_review_queue_path(root))


def ensure_concept_alias_registry(root: Path) -> Path:
    path = _alias_registry_path(root)
    if not path.exists():
        write_json(path, DEFAULT_ALIAS_REGISTRY)
    return path


def load_concept_alias_registry(root: Path) -> Dict[str, Any]:
    path = ensure_concept_alias_registry(root)
    payload = read_json(path, default={}) or {}
    merged = dict(DEFAULT_ALIAS_REGISTRY)
    merged["version"] = int(payload.get("version", DEFAULT_ALIAS_REGISTRY["version"]))
    merged["concepts"] = list(payload.get("concepts", []))
    merged["config_path"] = str(path)
    return merged


def ensure_concept_merge_policy(root: Path) -> Path:
    path = _policy_path(root)
    if not path.exists():
        write_json(path, DEFAULT_MERGE_POLICY)
    return path


def load_concept_merge_policy(root: Path) -> Dict[str, Any]:
    path = ensure_concept_merge_policy(root)
    payload = read_json(path, default={}) or {}
    merged = dict(DEFAULT_MERGE_POLICY)
    merged.update({key: value for key, value in payload.items() if key != "status_weights"})
    merged["status_weights"] = dict(DEFAULT_MERGE_POLICY["status_weights"]) | dict(payload.get("status_weights", {}))
    merged["config_path"] = str(path)
    return merged


def _stable_id(prefix: str, *parts: str) -> str:
    seed = "::".join(part.strip().lower() for part in parts if part.strip())
    return f"{prefix}-{hashlib.sha256(seed.encode('utf-8')).hexdigest()[:12]}"


def _format_label(phrase: str) -> str:
    normalized = phrase.strip()
    if re.search(r"[/_.]", normalized):
        return normalized
    return " ".join(part.capitalize() for part in normalized.split())


def _normalize_phrase(value: str) -> str:
    return " ".join(tokenize(value))


def _alias_lookup(alias_registry: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    mapping: Dict[str, Dict[str, Any]] = {}
    for concept in alias_registry.get("concepts", []):
        variants = [concept.get("canonical_label", "")] + list(concept.get("aliases", []))
        for variant in variants:
            normalized = _normalize_phrase(variant)
            if normalized:
                mapping[normalized] = concept
    return mapping


def canonicalize_concept_identity(
    root: Path,
    label: str,
    aliases: List[str] | None = None,
    transfer_terms: List[str] | None = None,
) -> Dict[str, Any]:
    alias_registry = load_concept_alias_registry(root)
    lookup = _alias_lookup(alias_registry)
    candidates = [label] + list(aliases or [])
    match = None
    for candidate in candidates:
        normalized = _normalize_phrase(candidate)
        if normalized in lookup:
            match = lookup[normalized]
            break
    canonical_label = _format_label(label)
    combined_aliases = sorted({_format_label(value) for value in candidates if value.strip()})
    combined_transfer_terms = sorted(set(transfer_terms or []))
    if match:
        canonical_label = match.get("canonical_label", canonical_label).strip() or canonical_label
        combined_aliases = sorted(
            {_format_label(value) for value in ([canonical_label] + list(match.get("aliases", [])) + candidates) if value.strip()}
        )
        combined_transfer_terms = sorted(set(combined_transfer_terms) | set(match.get("transfer_terms", [])))
    return {
        "canonical_label": canonical_label,
        "aliases": combined_aliases,
        "transfer_terms": combined_transfer_terms,
        "matched_registry_entry": match or {},
    }


def _jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    left_set = {value for value in left if value}
    right_set = {value for value in right if value}
    if not left_set or not right_set:
        return 0.0
    return len(left_set & right_set) / len(left_set | right_set)


def _artifact_refs(text: str) -> List[str]:
    refs = set()
    for match in _PATH_PATTERN.findall(text):
        cleaned = match.strip().strip(".,)")
        if cleaned:
            refs.add(cleaned)
    return sorted(refs)


def _artifact_tokens(refs: Iterable[str]) -> List[str]:
    tokens: List[str] = []
    for ref in refs:
        tokens.extend(tokenize(Path(ref).name))
    return tokens


def _candidate_phrases(text: str, seeds: set[str]) -> List[str]:
    phrases = set()
    for raw in _BACKTICK_PATTERN.findall(text):
        value = raw.strip()
        if value and not value.startswith("/"):
            phrases.add(value)
    tokens = tokenize(text)
    for length in (3, 2):
        for index in range(0, max(0, len(tokens) - length + 1)):
            chunk = tokens[index : index + length]
            if not chunk or all(token in _GENERIC_TOKENS for token in chunk):
                continue
            if len(set(chunk)) == 1:
                continue
            phrase = " ".join(chunk)
            if len(set(chunk) & seeds) >= 1 or len(set(chunk) - _GENERIC_TOKENS) >= length:
                phrases.add(phrase)
    for token in tokens:
        if token in seeds and token not in _GENERIC_TOKENS and token not in _MECHANISM_HINTS:
            phrases.add(token)
    return sorted(phrases)


def _transfer_terms(label_tokens: set[str], support_texts: List[str], artifact_refs: List[str]) -> List[str]:
    counts: Counter[str] = Counter()
    for text in support_texts:
        for token in tokenize(text):
            if token in label_tokens or token in _GENERIC_TOKENS:
                continue
            if token in _MECHANISM_HINTS:
                counts[token] += 3
            else:
                counts[token] += 1
    for token in _artifact_tokens(artifact_refs):
        if token not in label_tokens and token not in _GENERIC_TOKENS:
            counts[token] += 2
    return [token for token, _ in counts.most_common(8)]


def _abstract_pattern(label: str, transfer_terms: List[str]) -> str:
    if transfer_terms:
        return f"{label} as a reusable mechanism for {', '.join(transfer_terms[:3])}."
    return f"{label} as a reusable concept derived from conversation synthesis."


def _transfer_shape(label: str, transfer_terms: List[str]) -> str:
    if len(transfer_terms) >= 2:
        return f"Useful when {transfer_terms[0]} and {transfer_terms[1]} need to connect across contexts."
    if transfer_terms:
        return f"Useful when work needs stronger {transfer_terms[0]} across related concepts."
    return f"Useful when {label.lower()} needs to transfer into a different context or query."


def _extract_session_candidates(root: Path, title: str, turns: List[Dict[str, str]], conversation_analysis: Dict[str, Any], policy: Dict[str, Any]) -> List[Dict[str, Any]]:
    title_tokens = set(tokenize(title))
    translation_terms = set(conversation_analysis.get("translation_focus_terms", []))
    seeds = {token for token in title_tokens | translation_terms if token not in _GENERIC_TOKENS}
    support_map: Dict[str, Dict[str, Any]] = {}

    for turn in turns:
        role = turn["role"]
        text = turn["content"]
        role_weight = 1.25 if role == "user" else 1.0 if role == "assistant" else 0.45
        phrases = _candidate_phrases(text, seeds)
        refs = _artifact_refs(text)
        for phrase in phrases:
            phrase_tokens = tokenize(phrase)
            if not phrase_tokens:
                continue
            if len(phrase_tokens) == 1 and phrase_tokens[0] not in seeds:
                continue
            canonical = canonicalize_concept_identity(root, phrase, aliases=[_format_label(phrase)])
            key = " ".join(tokenize(canonical["canonical_label"])) or " ".join(phrase_tokens)
            bucket = support_map.setdefault(
                key,
                {
                    "phrase": canonical["canonical_label"],
                    "support_texts": [],
                    "roles": set(),
                    "artifact_refs": set(),
                    "explicit_mentions": 0,
                    "score": 0.0,
                    "aliases": set(canonical["aliases"]),
                    "registry_transfer_terms": set(canonical["transfer_terms"]),
                },
            )
            bucket["support_texts"].append(text.strip())
            bucket["roles"].add(role)
            bucket["artifact_refs"].update(refs)
            bucket["aliases"].update(canonical["aliases"])
            bucket["registry_transfer_terms"].update(canonical["transfer_terms"])
            if phrase in _BACKTICK_PATTERN.findall(text):
                bucket["explicit_mentions"] += 1
            bonus = 0.0
            if set(phrase_tokens) & seeds:
                bonus += 0.12
            if set(phrase_tokens) & title_tokens:
                bonus += 0.08
            if set(phrase_tokens) & translation_terms:
                bonus += 0.1
            if refs:
                bonus += min(0.08, len(refs) * 0.02)
            bucket["score"] += role_weight + bonus

    candidates: List[Dict[str, Any]] = []
    for key, bucket in support_map.items():
        label_tokens = set(key.split())
        refs = sorted(bucket["artifact_refs"])
        transfer_terms = sorted(set(_transfer_terms(label_tokens, bucket["support_texts"], refs)) | set(bucket["registry_transfer_terms"]))
        support_count = len(bucket["support_texts"])
        role_count = len(bucket["roles"])
        confidence = 0.34
        confidence += min(0.22, support_count * 0.08)
        confidence += min(0.12, role_count * 0.05)
        confidence += min(0.1, bucket["explicit_mentions"] * 0.05)
        if label_tokens & title_tokens:
            confidence += 0.05
        if label_tokens & translation_terms:
            confidence += 0.06
        if refs:
            confidence += min(0.08, len(refs) * 0.02)
        if len(label_tokens) >= 2:
            confidence += 0.06
        canonical = canonicalize_concept_identity(root, bucket["phrase"], aliases=sorted(bucket["aliases"]), transfer_terms=transfer_terms)
        label = canonical["canonical_label"]
        candidates.append(
            {
                "candidate_id": _stable_id("candidate", label, *transfer_terms[:2]),
                "label": label,
                "summary": shorten(bucket["support_texts"][0], 180),
                "abstract_pattern": _abstract_pattern(label, transfer_terms),
                "transfer_shape": _transfer_shape(label, transfer_terms),
                "aliases": canonical["aliases"],
                "artifact_refs": refs,
                "support_texts": bucket["support_texts"][:6],
                "transfer_terms": canonical["transfer_terms"] or transfer_terms,
                "confidence": round(min(0.94, confidence), 2),
                "score": round(bucket["score"], 2),
                "roles": sorted(bucket["roles"]),
                "explicit_mentions": bucket["explicit_mentions"],
            }
        )

    candidates.sort(
        key=lambda item: (
            -item.get("explicit_mentions", 0),
            -item["score"],
            -item["confidence"],
            -len(tokenize(item["label"])),
            item["label"],
        )
    )
    selected: List[Dict[str, Any]] = []
    selected_tokens: List[set[str]] = []
    for candidate in candidates:
        candidate_tokens = set(tokenize(candidate["label"]))
        if any(
            candidate_tokens <= existing_tokens
            or _jaccard(candidate_tokens, existing_tokens) >= 0.8
            for existing_tokens in selected_tokens
        ):
            continue
        selected.append(candidate)
        selected_tokens.append(candidate_tokens)
        if len(selected) >= int(policy["max_concepts_per_session"]):
            break
    return selected


def _node_index_tokens(node: Dict[str, Any]) -> Dict[str, set[str]]:
    attributes = node.get("attributes", {})
    return {
        "label": set(tokenize(node.get("label", ""))) | {token for alias in node.get("aliases", []) for token in tokenize(alias)},
        "pattern": set(tokenize(node.get("summary", ""))) | set(tokenize(node.get("abstract_pattern", ""))),
        "transfer": set(attributes.get("transfer_terms", [])) | set(tokenize(node.get("transfer_shape", ""))),
        "artifact": set(_artifact_tokens(node.get("artifact_refs", []))),
    }


def _match_existing_concept(candidate: Dict[str, Any], nodes: List[Dict[str, Any]]) -> Tuple[Dict[str, Any] | None, float]:
    candidate_label = set(tokenize(candidate["label"]))
    candidate_aliases = {token for alias in candidate.get("aliases", []) for token in tokenize(alias)}
    candidate_transfer = set(candidate.get("transfer_terms", []))
    candidate_artifacts = set(_artifact_tokens(candidate.get("artifact_refs", [])))
    best_node = None
    best_score = 0.0
    for node in nodes:
        index = _node_index_tokens(node)
        label_overlap = _jaccard(candidate_label | candidate_aliases, index["label"])
        pattern_overlap = _jaccard(candidate_transfer | candidate_label, index["pattern"])
        transfer_overlap = _jaccard(candidate_transfer, index["transfer"])
        artifact_overlap = _jaccard(candidate_artifacts, index["artifact"])
        score = label_overlap * 0.55 + transfer_overlap * 0.25 + pattern_overlap * 0.12 + artifact_overlap * 0.08
        if candidate["label"].lower() == node.get("label", "").lower() or candidate["label"].lower() in {
            alias.lower() for alias in node.get("aliases", [])
        }:
            score += 0.2
        score = round(min(0.98, score), 2)
        if score > best_score:
            best_score = score
            best_node = node
    return best_node, best_score


def _touch_type(candidate: Dict[str, Any], node: Dict[str, Any] | None, match_score: float) -> str:
    if node is None or match_score < 0.34:
        return "spawns_new_node"
    existing_transfer = set(node.get("attributes", {}).get("transfer_terms", []))
    existing_artifacts = set(node.get("artifact_refs", []))
    new_transfer = set(candidate.get("transfer_terms", [])) - existing_transfer
    new_artifacts = set(candidate.get("artifact_refs", [])) - existing_artifacts
    support_blob = " ".join(candidate.get("support_texts", [])).lower()
    if set(tokenize(support_blob)) & _NEGATION_MARKERS:
        return "contradicts"
    if set(tokenize(support_blob)) & _PRIORITY_MARKERS:
        return "changes_priority"
    if match_score >= 0.82 and not new_transfer and not new_artifacts:
        return "reinforces"
    if match_score >= 0.7 and not new_transfer and not new_artifacts:
        return "clarifies"
    if new_transfer or new_artifacts:
        return "extends"
    return "reframes"


def _decide_touch(touch_type: str, confidence: float, policy: Dict[str, Any]) -> Tuple[str, str]:
    auto_threshold = float(policy["auto_merge_threshold"])
    review_threshold = float(policy["review_threshold"])
    minimum_threshold = float(policy["minimum_threshold"])
    always_review = set(policy.get("always_review_touch_types", []))
    prefer_review = set(policy.get("prefer_review_touch_types", []))

    if confidence < minimum_threshold:
        return "discarded", "discarded"
    if touch_type in always_review and confidence >= review_threshold:
        return "needs_review", "needs_review"
    if touch_type in prefer_review and confidence < auto_threshold + 0.08 and confidence >= review_threshold:
        return "needs_review", "needs_review"
    if confidence >= auto_threshold:
        return "auto_merged", "applied"
    if confidence >= review_threshold:
        return "needs_review", "needs_review"
    return "recorded_only", "recorded_only"


def _merge_node(existing: Dict[str, Any] | None, candidate: Dict[str, Any], session_id: str, source_refs: List[str], decision_confidence: float, decision: str) -> Dict[str, Any]:
    now = utc_now()
    if existing is None:
        concept_id = _stable_id("concept", candidate["label"], *candidate.get("transfer_terms", [])[:2])
        status = "active" if decision == "auto_merged" else "provisional"
        return ConceptNode(
            concept_id=concept_id,
            label=candidate["label"],
            summary=candidate["summary"],
            abstract_pattern=candidate["abstract_pattern"],
            transfer_shape=candidate["transfer_shape"],
            aliases=candidate.get("aliases", []),
            artifact_refs=candidate.get("artifact_refs", []),
            source_refs=sorted(set(source_refs)),
            session_ids=[session_id],
            status=status,
            confidence=decision_confidence,
            created_at=now,
            updated_at=now,
            attributes={
                "transfer_terms": candidate.get("transfer_terms", []),
                "support_snippets": candidate.get("support_texts", [])[:4],
                "touch_count": 1,
                "merge_count": 1 if decision == "auto_merged" else 0,
                "manual_overrides": {},
                "canonical_key": _normalize_phrase(candidate["label"]),
            },
        ).to_dict()

    aliases = sorted(set(existing.get("aliases", [])) | set(candidate.get("aliases", [])) | {existing["label"], candidate["label"]})
    attributes = dict(existing.get("attributes", {}))
    transfer_terms = sorted(set(attributes.get("transfer_terms", [])) | set(candidate.get("transfer_terms", [])))
    support_snippets = list(attributes.get("support_snippets", []))
    for snippet in candidate.get("support_texts", []):
        if snippet not in support_snippets:
            support_snippets.append(snippet)
    attributes["support_snippets"] = support_snippets[:8]
    attributes["transfer_terms"] = transfer_terms
    attributes["touch_count"] = int(attributes.get("touch_count", 0)) + 1
    attributes["merge_count"] = int(attributes.get("merge_count", 0)) + 1
    attributes["canonical_key"] = _normalize_phrase(existing["label"])
    existing["aliases"] = aliases
    existing["artifact_refs"] = sorted(set(existing.get("artifact_refs", [])) | set(candidate.get("artifact_refs", [])))
    existing["source_refs"] = sorted(set(existing.get("source_refs", [])) | set(source_refs))
    existing["session_ids"] = sorted(set(existing.get("session_ids", [])) | {session_id})
    existing["status"] = "active"
    existing["confidence"] = round(max(float(existing.get("confidence", 0.0)), decision_confidence), 2)
    existing["updated_at"] = utc_now()
    existing["attributes"] = attributes
    if decision_confidence >= float(existing["confidence"]) and candidate.get("summary"):
        existing["summary"] = candidate["summary"]
        existing["abstract_pattern"] = candidate["abstract_pattern"]
        existing["transfer_shape"] = candidate["transfer_shape"]
    return existing


def _synthesis_source_refs(session_id: str, events: List[Dict[str, Any]]) -> List[str]:
    refs = {f"session:{session_id}"}
    for event in events:
        if event.get("source_ref"):
            refs.add(event["source_ref"])
    return sorted(refs)


def _session_turns(events: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    turns = []
    for event in events:
        actor = str(event.get("actor", "")).lower()
        if actor not in {"user", "assistant", "system"}:
            continue
        content = str(event.get("content", "")).strip()
        if content:
            turns.append({"role": actor, "content": content})
    return turns


def _session_sort_key(manifest: Dict[str, Any]) -> Tuple[str, str]:
    return (manifest.get("ended_at") or manifest.get("started_at") or "", manifest.get("session_id", ""))


def _concept_edge_rows(nodes: List[Dict[str, Any]], packets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    node_lookup = {row["concept_id"]: row for row in nodes}
    buckets: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for packet in packets:
        concept_ids = sorted({row["concept_id"] for row in packet.get("touch_operations", []) if row.get("decision") != "discarded"})
        for index, left in enumerate(concept_ids):
            for right in concept_ids[index + 1 :]:
                key = (left, right)
                bucket = buckets.setdefault(
                    key,
                    {
                        "session_ids": set(),
                        "shared_terms": set(),
                        "confidence": 0.38,
                    },
                )
                bucket["session_ids"].add(packet["session_id"])
                left_terms = set(node_lookup.get(left, {}).get("attributes", {}).get("transfer_terms", []))
                right_terms = set(node_lookup.get(right, {}).get("attributes", {}).get("transfer_terms", []))
                bucket["shared_terms"].update(left_terms & right_terms)
                bucket["confidence"] = min(0.92, bucket["confidence"] + 0.08)
    rows = []
    for (left, right), bucket in sorted(buckets.items()):
        kind = "shares_transfer_shape" if bucket["shared_terms"] else "co_occurs_with"
        rows.append(
            ConceptEdge(
                edge_id=_stable_id("concept-edge", left, right, kind),
                kind=kind,
                from_id=left,
                to_id=right,
                status="active" if bucket["confidence"] >= 0.58 else "provisional",
                confidence=round(bucket["confidence"] + min(0.18, len(bucket["shared_terms"]) * 0.04), 2),
                shared_terms=sorted(bucket["shared_terms"])[:8],
                source_refs=[f"session:{session_id}" for session_id in sorted(bucket["session_ids"])],
                session_ids=sorted(bucket["session_ids"]),
            ).to_dict()
        )
    return rows


def _session_rows(root: Path) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]], Dict[str, Any]]]:
    rows = []
    sessions_root = root / "memory" / "sessions"
    if not sessions_root.exists():
        return rows
    for entry in sorted(sessions_root.iterdir()):
        manifest = read_json(entry / "manifest.json", default={}) or {}
        if manifest.get("status") != "closed":
            continue
        events = read_jsonl(session_events_path(root, manifest["session_id"]))
        packet = read_json(entry / "analysis" / "session_packet.json", default={}) or {}
        rows.append((manifest, events, packet))
    rows.sort(key=lambda item: _session_sort_key(item[0]))
    return rows


def rebuild_conversation_concepts(root: Path) -> Dict[str, Any]:
    policy = load_concept_merge_policy(root)
    concept_nodes: List[Dict[str, Any]] = []
    synthesis_packets: List[Dict[str, Any]] = []
    touch_rows: List[Dict[str, Any]] = []

    for manifest, events, packet in _session_rows(root):
        session_id = manifest["session_id"]
        turns = _session_turns(events)
        conversation_analysis = dict(packet.get("conversation_analysis", {}))
        candidates = _extract_session_candidates(root, manifest.get("title", session_id), turns, conversation_analysis, policy)
        source_refs = _synthesis_source_refs(session_id, events)
        packet_touch_rows: List[Dict[str, Any]] = []
        confirmed: List[str] = []
        inferred: List[str] = []
        contested: List[str] = []
        for candidate in candidates:
            matched_node, match_score = _match_existing_concept(candidate, concept_nodes)
            touch_type = _touch_type(candidate, matched_node, match_score)
            if matched_node is None:
                decision_confidence = candidate["confidence"]
            else:
                decision_confidence = round(min(0.96, candidate["confidence"] * 0.55 + match_score * 0.45), 2)
            decision, status = _decide_touch(touch_type, decision_confidence, policy)
            concept_id = matched_node["concept_id"] if matched_node else _stable_id("concept", candidate["label"], *candidate.get("transfer_terms", [])[:2])
            touch = TouchOperation(
                touch_id=_stable_id("touch", session_id, concept_id, candidate["label"], touch_type),
                synthesis_id=_stable_id("synthesis", session_id),
                session_id=session_id,
                concept_id=concept_id,
                concept_label=matched_node["label"] if matched_node else candidate["label"],
                candidate_label=candidate["label"],
                touch_type=touch_type,
                decision=decision,
                status=status,
                confidence=decision_confidence,
                source_refs=source_refs,
                artifact_refs=candidate.get("artifact_refs", []),
                evidence=candidate.get("support_texts", [])[:3],
                attributes={
                    "match_score": round(match_score, 2),
                    "transfer_terms": candidate.get("transfer_terms", []),
                    "candidate_summary": candidate.get("summary", ""),
                },
            ).to_dict()
            packet_touch_rows.append(touch)
            touch_rows.append(touch)

            if touch_type == "contradicts":
                contested.append(candidate["label"])
            elif decision == "auto_merged":
                confirmed.append(candidate["label"])
            elif decision in {"needs_review", "recorded_only"}:
                inferred.append(candidate["label"])

            if decision == "auto_merged":
                if matched_node is None:
                    concept_nodes.append(_merge_node(None, candidate, session_id, source_refs, decision_confidence, decision))
                else:
                    _merge_node(matched_node, candidate, session_id, source_refs, decision_confidence, decision)
            elif decision == "needs_review" and matched_node is None:
                concept_nodes.append(_merge_node(None, candidate, session_id, source_refs, decision_confidence, decision))

        open_questions = [
            shorten(turn["content"], 180)
            for turn in turns
            if turn["role"] == "user" and "?" in turn["content"]
        ][:5]
        summary = (
            f"Conversation synthesis for {manifest.get('title', session_id)} with "
            f"{len(candidates)} concept candidates and {len(packet_touch_rows)} touch operations."
        )
        synthesis_packet = SynthesisPacket(
            synthesis_id=_stable_id("synthesis", session_id),
            session_id=session_id,
            title=manifest.get("title", session_id),
            summary=summary,
            status="ready" if confirmed else "review" if inferred or contested else "sparse",
            confidence=round(
                min(0.94, (sum(row["confidence"] for row in packet_touch_rows) / max(1, len(packet_touch_rows)))) if packet_touch_rows else 0.0,
                2,
            ),
            source_refs=source_refs,
            confirmed=confirmed,
            inferred=inferred,
            contested=contested,
            open_questions=open_questions,
            concept_candidates=candidates,
            touch_operations=packet_touch_rows,
            conversation_analysis=conversation_analysis,
        ).to_dict()
        synthesis_packets.append(synthesis_packet)
        write_json(session_dir(root, session_id) / "analysis" / "concept_synthesis.json", synthesis_packet)

    concept_nodes.sort(key=lambda row: (-row["confidence"], row["label"], row["concept_id"]))
    concept_edges = _concept_edge_rows(concept_nodes, synthesis_packets)
    review_rows = [row for row in touch_rows if row["status"] == "needs_review"]

    write_jsonl(_concept_nodes_path(root), concept_nodes)
    write_jsonl(_concept_edges_path(root), concept_edges)
    write_jsonl(_synthesis_packets_path(root), synthesis_packets)
    write_jsonl(_touch_operations_path(root), touch_rows)
    write_jsonl(_review_queue_path(root), review_rows)

    return {
        "concept_graph_dir": str(_concept_graph_dir(root)),
        "concept_nodes": str(_concept_nodes_path(root)),
        "concept_edges": str(_concept_edges_path(root)),
        "synthesis_packets": str(_synthesis_packets_path(root)),
        "touch_operations": str(_touch_operations_path(root)),
        "review_queue": str(_review_queue_path(root)),
        "packet_count": len(synthesis_packets),
        "concept_count": len(concept_nodes),
        "touch_count": len(touch_rows),
        "review_count": len(review_rows),
        "session_refs": {
            row["session_id"]: str(session_dir(root, row["session_id"]) / "analysis" / "concept_synthesis.json")
            for row in synthesis_packets
        },
    }


def search_concepts(root: Path, query: str, limit: int = 6) -> List[Dict[str, Any]]:
    nodes = load_concept_nodes(root)
    edges = load_concept_edges(root)
    policy = load_concept_merge_policy(root)
    query_tokens = set(tokenize(query))
    if not nodes:
        return []

    base_scores: Dict[str, float] = {}
    reason_map: Dict[str, List[str]] = defaultdict(list)
    for node in nodes:
        index = _node_index_tokens(node)
        label_overlap = len(query_tokens & index["label"])
        pattern_overlap = len(query_tokens & index["pattern"])
        transfer_overlap = len(query_tokens & index["transfer"])
        artifact_overlap = len(query_tokens & index["artifact"])
        score = label_overlap * 4.0 + pattern_overlap * 2.2 + transfer_overlap * 3.0 + artifact_overlap * 1.6
        score += float(node.get("confidence", 0.0)) * 1.4
        score *= float(policy["status_weights"].get(node.get("status", "provisional"), 0.8))
        if label_overlap:
            reason_map[node["concept_id"]].append("label")
        if pattern_overlap:
            reason_map[node["concept_id"]].append("pattern")
        if transfer_overlap:
            reason_map[node["concept_id"]].append("transfer")
        if artifact_overlap:
            reason_map[node["concept_id"]].append("artifact")
        base_scores[node["concept_id"]] = round(score, 2)

    top_seed_ids = [
        node_id
        for node_id, _ in sorted(base_scores.items(), key=lambda item: (-item[1], item[0]))[:3]
        if base_scores[node_id] > 0
    ]
    neighbor_boost = float(policy.get("neighbor_boost", 0.18))
    for edge in edges:
        if edge["from_id"] not in top_seed_ids and edge["to_id"] not in top_seed_ids:
            continue
        target_id = edge["to_id"] if edge["from_id"] in top_seed_ids else edge["from_id"]
        shared_term_overlap = len(query_tokens & set(edge.get("shared_terms", [])))
        boost = float(edge.get("confidence", 0.0)) * (neighbor_boost + shared_term_overlap * 0.04)
        base_scores[target_id] = round(base_scores.get(target_id, 0.0) + boost, 2)
        reason_map[target_id].append("graph")

    ranked = sorted(
        nodes,
        key=lambda row: (
            -base_scores.get(row["concept_id"], 0.0),
            -float(row.get("confidence", 0.0)),
            row["label"],
        ),
    )
    scored = []
    for node in ranked:
        score = base_scores.get(node["concept_id"], 0.0)
        if score <= 0:
            continue
        payload = dict(node)
        payload["_score"] = round(score, 2)
        payload["_reasons"] = sorted(set(reason_map.get(node["concept_id"], [])))
        scored.append(payload)
    if not scored:
        fallback = sorted(nodes, key=lambda row: (-float(row.get("confidence", 0.0)), row["label"]))[:limit]
        return [{**row, "_score": round(float(row.get("confidence", 0.0)), 2), "_reasons": ["confidence"]} for row in fallback]
    return scored[:limit]


def derive_development_signals(root: Path, query_text: str, limit: int = 6) -> Dict[str, Any]:
    normalized_query = str(query_text or "").strip()
    if not normalized_query:
        return {
            "query_text": "",
            "query_tokens": [],
            "concept_matches": [],
            "formation_candidates": [],
            "shape_matches": [],
            "synthesis_candidates": [],
        }

    concept_matches = search_concepts(root, normalized_query, limit=limit)
    candidates = retrieve_candidates(
        root,
        {
            "query_text": normalized_query,
            "meta_refs": [],
            "source_refs": [],
        },
        limit=max(limit * 2, 8),
    )

    anchor = candidates[0] if candidates else None
    shape_matches = match_shapes(anchor, candidates[1:])[:limit] if anchor and len(candidates) > 1 else []
    synthesized = [synthesize_candidate(match, choose_operator(match)).to_dict() for match in shape_matches[: min(3, len(shape_matches))]]

    return {
        "query_text": normalized_query,
        "query_tokens": [token for token in tokenize(normalized_query) if token not in _GENERIC_TOKENS][:12],
        "concept_matches": concept_matches,
        "formation_candidates": [candidate.to_dict() for candidate in candidates[:limit]],
        "shape_matches": [match.to_dict() for match in shape_matches],
        "synthesis_candidates": synthesized,
    }


def _formation_review_queue_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "review_queue.jsonl"


def load_formation_synthesis_reviews(root: Path) -> List[Dict[str, Any]]:
    rows = read_jsonl(_formation_review_queue_path(root))
    return [row for row in rows if row.get("queue_type") == "formation_synthesis"]


def _candidate_from_meta(meta: Dict[str, Any], *, score: float, reasons: List[str]) -> FormationCandidate:
    return FormationCandidate(
        candidate_id=_stable_id("formation-candidate", str(meta.get("meta_id", ""))),
        meta_id=str(meta.get("meta_id", "")).strip(),
        kind=str(meta.get("kind", "")).strip(),
        label=str(meta.get("label", "")).strip(),
        summary=str(meta.get("summary", "")).strip(),
        source_refs=[str(value).strip() for value in meta.get("source_refs", []) if str(value).strip()],
        chunk_ids=[str(value).strip() for value in meta.get("chunk_ids", []) if str(value).strip()],
        evidence=[str(value).strip() for value in meta.get("evidence", []) if str(value).strip()],
        attributes=dict(meta.get("attributes", {})),
        candidate_score=round(score, 3),
        reasons=sorted(set(reasons)),
    )


def retrieve_candidates(root: Path, seed_packet: Dict[str, Any], limit: int = 24) -> List[FormationCandidate]:
    from .knowledge_layer import select_candidate_pairs

    pair_rows = select_candidate_pairs(root, limit=max(limit * 3, 24))
    seed_meta_refs = {str(value).strip() for value in seed_packet.get("meta_refs", []) if str(value).strip()}
    seed_source_refs = {str(value).strip() for value in seed_packet.get("source_refs", []) if str(value).strip()}
    query_tokens = set(tokenize(str(seed_packet.get("query_text", ""))))

    buckets: Dict[str, Dict[str, Any]] = {}
    for pair in pair_rows:
        for side in ("left", "right"):
            meta = pair[side]
            meta_id = str(meta.get("meta_id", "")).strip()
            if not meta_id:
                continue
            reasons: List[str] = []
            score = float(pair.get("score", 0.0))
            meta_source_refs = {str(value).strip() for value in meta.get("source_refs", []) if str(value).strip()}
            meta_tokens = set(tokenize(f"{meta.get('label', '')} {meta.get('summary', '')}"))
            if meta_id in seed_meta_refs:
                reasons.append("seed_meta")
                score += 0.45
            if seed_source_refs & meta_source_refs:
                reasons.append("seed_source")
                score += 0.18
            overlap = len(query_tokens & meta_tokens)
            if overlap:
                reasons.append("query_overlap")
                score += min(0.24, overlap * 0.06)
            if pair.get("edge_kind") == "contradicts":
                reasons.append("contradiction")
                score += 0.04
            if not reasons and query_tokens:
                continue
            existing = buckets.get(meta_id)
            if existing is None or score > existing["score"]:
                buckets[meta_id] = {
                    "meta": meta,
                    "score": score,
                    "reasons": reasons,
                }
            else:
                existing["reasons"].extend(reasons)
                existing["score"] = max(existing["score"], score)

    if not buckets:
        for meta in load_meta_records(root):
            meta_id = str(meta.get("meta_id", "")).strip()
            if not meta_id:
                continue
            reasons: List[str] = []
            score = float(meta.get("confidence", 0.0))
            meta_source_refs = {str(value).strip() for value in meta.get("source_refs", []) if str(value).strip()}
            meta_tokens = set(tokenize(f"{meta.get('label', '')} {meta.get('summary', '')}"))
            if meta_id in seed_meta_refs:
                reasons.append("seed_meta")
                score += 0.45
            if seed_source_refs & meta_source_refs:
                reasons.append("seed_source")
                score += 0.18
            overlap = len(query_tokens & meta_tokens)
            if overlap:
                reasons.append("query_overlap")
                score += min(0.24, overlap * 0.06)
            if meta.get("kind") == "contradiction":
                reasons.append("contradiction")
                score += 0.04
            if not reasons:
                continue
            buckets[meta_id] = {
                "meta": meta,
                "score": score,
                "reasons": reasons,
            }

    ranked = sorted(
        buckets.values(),
        key=lambda item: (-item["score"], item["meta"].get("label", ""), item["meta"].get("meta_id", "")),
    )
    return [
        _candidate_from_meta(row["meta"], score=row["score"], reasons=row["reasons"])
        for row in ranked[:limit]
    ]


def match_shapes(anchor: FormationCandidate, candidates: List[FormationCandidate]) -> List[ShapeMatch]:
    anchor_tokens = set(tokenize(f"{anchor.label} {anchor.summary}"))
    rows: List[ShapeMatch] = []
    for candidate in candidates:
        if candidate.meta_id == anchor.meta_id:
            continue
        candidate_tokens = set(tokenize(f"{candidate.label} {candidate.summary}"))
        shared_tokens = sorted(anchor_tokens & candidate_tokens)
        score = min(anchor.candidate_score, candidate.candidate_score) * 0.45
        reasons: List[str] = []
        if shared_tokens:
            reasons.append("shared_tokens")
            score += min(0.32, len(shared_tokens) * 0.08)
        if anchor.kind == candidate.kind:
            reasons.append("shared_kind")
            score += 0.16
        if anchor.source_refs and set(anchor.source_refs) & set(candidate.source_refs):
            reasons.append("shared_source")
            score += 0.06
        if candidate.kind == "contradiction":
            reasons.append("counterpoint")
            score += 0.04
        if not reasons:
            continue
        operator_hints: List[str] = []
        if candidate.kind == "contradiction":
            operator_hints.append("find_counterpoint")
        if anchor.kind == candidate.kind and len(shared_tokens) >= 2:
            operator_hints.append("structure_map")
        if len(shared_tokens) >= 1:
            operator_hints.append("blend")
        if candidate.kind in {"transfer_target", "shared_primitive"}:
            operator_hints.append("adapt_case")
        rows.append(
            ShapeMatch(
                match_id=_stable_id("shape-match", anchor.meta_id, candidate.meta_id),
                anchor_meta_id=anchor.meta_id,
                anchor_kind=anchor.kind,
                candidate_meta_id=candidate.meta_id,
                candidate_kind=candidate.kind,
                edge_kind="contradicts" if candidate.kind == "contradiction" else "relates_to",
                score=round(min(0.99, score), 3),
                shared_tokens=shared_tokens[:8],
                reasons=reasons,
                operator_hints=operator_hints,
                source_refs=sorted(set(anchor.source_refs + candidate.source_refs)),
                source_item_ids=sorted(set(anchor.chunk_ids + candidate.chunk_ids)),
                evidence=(anchor.evidence + candidate.evidence)[:4],
                anchor_label=anchor.label,
                candidate_label=candidate.label,
            )
        )
    rows.sort(key=lambda item: (-item.score, item.candidate_label, item.candidate_meta_id))
    return rows


def choose_operator(match: ShapeMatch) -> OperatorDecision:
    if match.edge_kind == "contradicts" or "find_counterpoint" in match.operator_hints:
        return OperatorDecision(
            operator_key="find_counterpoint",
            confidence=round(min(0.95, 0.58 + match.score * 0.32), 3),
            rationale="The candidate acts as a contradiction or opposing pressure on the anchor formation.",
            fallback_operator_key="abduce_hypothesis",
        )
    if "structure_map" in match.operator_hints:
        return OperatorDecision(
            operator_key="structure_map",
            confidence=round(min(0.95, 0.62 + match.score * 0.3), 3),
            rationale="The anchor and candidate share a strong structural pattern with aligned roles.",
            fallback_operator_key="blend",
        )
    if "adapt_case" in match.operator_hints:
        return OperatorDecision(
            operator_key="adapt_case",
            confidence=round(min(0.9, 0.54 + match.score * 0.28), 3),
            rationale="The candidate looks like a reusable pattern that can be adapted into the anchor context.",
            fallback_operator_key="structure_map",
        )
    if "blend" in match.operator_hints:
        return OperatorDecision(
            operator_key="blend",
            confidence=round(min(0.88, 0.5 + match.score * 0.26), 3),
            rationale="The candidate shares enough structure to support a combined synthesis.",
            fallback_operator_key="abduce_hypothesis",
        )
    return OperatorDecision(
        operator_key="abduce_hypothesis",
        confidence=round(min(0.82, 0.46 + match.score * 0.22), 3),
        rationale="The match is real but weaker, so the safest move is a provisional explanatory hypothesis.",
        fallback_operator_key="blend",
    )


def synthesize_candidate(match: ShapeMatch, decision: OperatorDecision) -> SynthesisCandidate:
    shared_phrase = ", ".join(match.shared_tokens[:3]) if match.shared_tokens else "the same underlying pattern"
    if decision.operator_key == "find_counterpoint":
        title = f"{match.anchor_label} Meets Resistance"
        short_text = f"{match.candidate_label} exposes where {match.anchor_label.lower()} breaks down or closes too early."
        what_changed = f"The system found a counterpoint instead of a reinforcing bridge: {match.candidate_label} pushes back against {match.anchor_label.lower()}."
        why_it_matters_now = f"The tension around {shared_phrase} shows where the formation may need review before surfacing."
        next_action = "Review the contradiction and decide whether it sharpens or invalidates the formation."
        review_status = "needs_review"
    elif decision.operator_key == "structure_map":
        title = f"{match.anchor_label} Repeats"
        short_text = f"{match.anchor_label} and {match.candidate_label.lower()} share the same shape: {shared_phrase}."
        what_changed = f"The system found a structural echo between {match.anchor_label} and {match.candidate_label}."
        why_it_matters_now = f"The shared shape around {shared_phrase} makes this formation more reusable and more legible."
        next_action = "Surface the structural bridge and watch for adjacent formations with the same shape."
        review_status = "approved_for_surface"
    elif decision.operator_key == "adapt_case":
        title = f"{match.candidate_label} Transfers"
        short_text = f"{match.candidate_label} looks reusable inside {match.anchor_label.lower()}."
        what_changed = f"The candidate now looks less like a neighbor and more like a reusable case for {match.anchor_label.lower()}."
        why_it_matters_now = f"The overlap around {shared_phrase} suggests a concrete adaptation path."
        next_action = "Adapt the reusable case into the current formation and inspect the result."
        review_status = "ready_for_review"
    elif decision.operator_key == "blend":
        title = f"{match.anchor_label} Blends Forward"
        short_text = f"{match.anchor_label} and {match.candidate_label.lower()} combine into a new line of thought around {shared_phrase}."
        what_changed = f"The system generated a blended candidate from {match.anchor_label} and {match.candidate_label}."
        why_it_matters_now = f"The blend reveals a possible new path through {shared_phrase}."
        next_action = "Inspect the blended candidate and keep only the concrete parts."
        review_status = "ready_for_review"
    else:
        title = f"{match.anchor_label} Suggests A Cause"
        short_text = f"{match.candidate_label} may explain why {match.anchor_label.lower()} keeps returning."
        what_changed = f"The system turned the match into a provisional explanatory hypothesis."
        why_it_matters_now = f"The hypothesis gives the formation a more explicit mechanism around {shared_phrase}."
        next_action = "Check the hypothesis against more evidence before promotion."
        review_status = "ready_for_review"

    evidence_status = "grounded" if match.source_refs and match.source_item_ids else "provisional"
    base_confidence = round(min(0.99, match.score * 0.62 + decision.confidence * 0.38), 3)
    return SynthesisCandidate(
        synthesis_id=_stable_id("formation-synthesis", match.anchor_meta_id, match.candidate_meta_id, decision.operator_key),
        anchor_meta_id=match.anchor_meta_id,
        candidate_meta_id=match.candidate_meta_id,
        operator_key=decision.operator_key,
        title=title,
        short_text=short_text,
        summary=short_text,
        what_changed=what_changed,
        why_it_matters_now=why_it_matters_now,
        next_action=next_action,
        source_refs=match.source_refs,
        source_item_ids=match.source_item_ids,
        meta_refs=[match.anchor_meta_id, match.candidate_meta_id],
        confidence_score=base_confidence,
        relevance_score=round(min(0.99, match.score), 3),
        novelty_score=round(min(0.99, 0.42 + len(match.shared_tokens) * 0.08), 3),
        evidence_status=evidence_status,
        review_status=review_status,
        shared_primitive_key=decision.operator_key,
        shared_primitive_label=decision.operator_key.replace("_", " "),
        reasoning_pipeline="formation_synthesis_v1",
        rationale=decision.rationale,
        shared_tokens=match.shared_tokens,
        evidence=match.evidence,
    )


def stress_test_candidate(candidate: SynthesisCandidate) -> StressTestResult:
    concerns: List[str] = []
    confidence_adjustment = 0.0
    review_status = candidate.review_status
    should_surface = candidate.review_status == "approved_for_surface"
    evidence_status = candidate.evidence_status

    if candidate.operator_key == "find_counterpoint":
        concerns.append("counterpoint_requires_review")
        should_surface = False
        review_status = "needs_review"
        confidence_adjustment -= 0.12
    if candidate.confidence_score < 0.62:
        concerns.append("low_confidence")
        should_surface = False
        review_status = "needs_review"
        confidence_adjustment -= 0.08
    if candidate.evidence_status != "grounded":
        concerns.append("weak_evidence")
        should_surface = False
        review_status = "needs_review"
        evidence_status = "provisional"
    return StressTestResult(
        should_surface=should_surface,
        review_status=review_status,
        evidence_status=evidence_status,
        confidence_adjustment=round(confidence_adjustment, 3),
        concerns=concerns,
    )


def emit_thought_packet(candidate: SynthesisCandidate, stress: StressTestResult) -> Dict[str, Any] | None:
    if not stress.should_surface:
        return None
    confidence_score = round(min(0.99, max(0.0, candidate.confidence_score + stress.confidence_adjustment)), 3)
    article_markdown = "\n".join(
        [
            f"# {candidate.title}",
            "",
            candidate.short_text,
            "",
            "## Why it matters",
            "",
            candidate.why_it_matters_now,
            "",
            "## Next action",
            "",
            candidate.next_action,
        ]
    )
    packet = ThoughtPacket(
        packet_id=f"packet-{candidate.synthesis_id}",
        thought_id=f"thought-{candidate.synthesis_id}",
        insight_id=candidate.synthesis_id,
        title=candidate.title,
        short_text=candidate.short_text,
        article_title=candidate.title,
        article_markdown=article_markdown,
        status="active",
        review_status=stress.review_status,
        evidence_status=stress.evidence_status,
        confidence_score=confidence_score,
        relevance_score=candidate.relevance_score,
        novelty_score=candidate.novelty_score,
        source_refs=candidate.source_refs,
        source_item_ids=candidate.source_item_ids,
        meta_refs=candidate.meta_refs,
        shared_primitive_key=candidate.shared_primitive_key,
        shared_primitive_label=candidate.shared_primitive_label,
        what_changed=candidate.what_changed,
        why_it_matters_now=candidate.why_it_matters_now,
        next_action=candidate.next_action,
        reasoning_pipeline=candidate.reasoning_pipeline,
    )
    return packet.to_dict()


def record_formation_synthesis_review(
    root: Path,
    seed_packet: Dict[str, Any],
    candidate: SynthesisCandidate,
    stress: StressTestResult,
) -> Dict[str, Any]:
    rows = read_jsonl(_formation_review_queue_path(root))
    review_row = {
        "review_id": _stable_id("formation-review", candidate.synthesis_id, ",".join(stress.concerns)),
        "queue_type": "formation_synthesis",
        "status": stress.review_status,
        "created_at": utc_now(),
        "seed_meta_refs": [str(value).strip() for value in seed_packet.get("meta_refs", []) if str(value).strip()],
        "seed_source_refs": [str(value).strip() for value in seed_packet.get("source_refs", []) if str(value).strip()],
        "synthesis_id": candidate.synthesis_id,
        "operator_key": candidate.operator_key,
        "title": candidate.title,
        "summary": candidate.summary,
        "concerns": stress.concerns,
        "candidate": candidate.to_dict(),
        "stress_test": stress.to_dict(),
    }
    rows.append(review_row)
    write_jsonl(_formation_review_queue_path(root), rows)
    return review_row
