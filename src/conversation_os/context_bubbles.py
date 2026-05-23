from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import defaultdict
from time import perf_counter
from pathlib import Path
from typing import Any, Callable, Dict, List, Tuple

from .conversation_synthesis import canonicalize_concept_identity, load_concept_nodes
from .library_tracker import get_governed_source_lookup
from .meta_layer import load_meta_records
from .models import BubbleEdge, BubbleMembership, BubbleTransition, ContextBubble
from .storage import ensure_dir, read_json, read_jsonl, slugify, utc_now, write_json, write_jsonl
from .thread_abstractions import build_thread_abstractions, load_thread_abstractions
from .vault_ingest import load_chunk_index, load_source_registry, shorten, tokenize


MODULE_ID = "kernel.analysis.context_bubbles"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "load_context_bubbles",
    "load_bubble_memberships",
    "load_bubble_edges",
    "load_bubble_transitions",
    "load_context_bubble_progress",
    "build_context_bubbles",
    "list_context_bubbles",
    "get_context_bubble",
)
__all__ = list(PUBLIC_API)


SEED_KIND_PRIORITY = {
    "shared_primitive": 0,
    "signal_frame": 1,
    "theme": 2,
}

ROLE_DIRECT_MAP = {
    "tension": "tension",
    "question": "question",
    "direction": "direction",
    "guardrail": "guardrail",
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "before",
    "but",
    "by",
    "for",
    "from",
    "how",
    "if",
    "in",
    "into",
    "is",
    "it",
    "local",
    "not",
    "of",
    "on",
    "or",
    "private",
    "should",
    "stay",
    "that",
    "the",
    "their",
    "there",
    "this",
    "to",
    "we",
    "what",
    "with",
    "without",
}

LOW_SIGNAL_LABEL_TOKENS = {
    "assistant",
    "answer",
    "because",
    "chat",
    "chatgpt",
    "continue",
    "does",
    "file",
    "idea",
    "let",
    "lets",
    "meaning",
    "model",
    "most",
    "more",
    "one",
    "our",
    "question",
    "reason",
    "said",
    "same",
    "source",
    "text",
    "think",
    "thought",
    "time",
    "title",
    "uploaded",
    "user",
    "label",
    "image",
    "refresh",
    "url",
    "yes",
    "you",
}

LOW_SIGNAL_LABEL_PHRASES = {
    "assistant",
    "current url",
    "label",
    "refresh",
    "source",
    "text",
    "uploaded image",
    "user",
    "you said",
}

LOW_SIGNAL_PRIMITIVE_PREFIXES = (
    "title-",
    "title_",
    "uploaded-file",
    "uploaded_file",
    "you-said",
    "you_said",
)


def _data_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data"


def _bubbles_path(root: Path) -> Path:
    return _data_dir(root) / "context_bubbles.jsonl"


def _memberships_path(root: Path) -> Path:
    return _data_dir(root) / "bubble_memberships.jsonl"


def _edges_path(root: Path) -> Path:
    return _data_dir(root) / "bubble_edges.jsonl"


def _transitions_path(root: Path) -> Path:
    return _data_dir(root) / "bubble_transitions.jsonl"


def _progress_path(root: Path) -> Path:
    return _data_dir(root) / "context_bubbles_progress.json"


def _runtime_config(root: Path) -> Dict[str, Any]:
    return (
        read_json(
            root / "product" / "inner_world_v1" / "config" / "runtime.json",
            default={},
        )
        or {}
    )


def _bubble_title_cache_path(root: Path) -> Path:
    return _data_dir(root) / "semantic_bubble_titles.json"


def _load_bubble_title_cache(root: Path) -> Dict[str, Dict[str, Any]]:
    return read_json(_bubble_title_cache_path(root), default={}) or {}


def _write_bubble_title_cache(root: Path, payload: Dict[str, Dict[str, Any]]) -> None:
    write_json(_bubble_title_cache_path(root), payload)


def _bubble_assist_config(root: Path) -> Dict[str, Any]:
    runtime = _runtime_config(root)
    backend_id = runtime.get("chat_backend", "heuristic")
    openclaw = runtime.get("openclaw", {})
    assist = runtime.get("semantic_assist", {})
    enabled = assist.get("enabled")
    if enabled is None:
        enabled = backend_id in {"openclaw_gateway", "openclaw_local"}
    if not enabled or backend_id not in {"openclaw_gateway", "openclaw_local"}:
        return {"enabled": False}
    return {
        "enabled": True,
        "backend_id": backend_id,
        "agent": assist.get("agent") or openclaw.get("agent") or "main",
        "thinking": assist.get("thinking") or openclaw.get("thinking") or "minimal",
        "timeout_seconds": int(assist.get("timeout_seconds") or openclaw.get("timeout_seconds") or 25),
        "label_limit": max(0, int(assist.get("bubble_label_limit", 4) or 0)),
        "snippet_limit": max(1, int(assist.get("snippet_limit", 3) or 3)),
        "snippet_chars": max(80, int(assist.get("snippet_chars", 180) or 180)),
    }


def load_context_bubbles(root: Path) -> List[Dict]:
    return read_jsonl(_bubbles_path(root))


def load_bubble_memberships(root: Path) -> List[Dict]:
    return read_jsonl(_memberships_path(root))


def load_bubble_edges(root: Path) -> List[Dict]:
    return read_jsonl(_edges_path(root))


def load_bubble_transitions(root: Path) -> List[Dict]:
    return read_jsonl(_transitions_path(root))


def load_context_bubble_progress(root: Path) -> Dict:
    return read_json(_progress_path(root), default={}) or {}


def _digest(prefix: str, *parts: str) -> str:
    payload = "::".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:12]}"


def _extract_assist_json(stdout: str) -> Dict[str, Any] | None:
    text = stdout.strip()
    if not text:
        return None
    candidates: List[Any] = []
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        candidates.append(payload)
        for key in ("reply", "text", "content", "message"):
            if payload.get(key):
                candidates.append(payload[key])
        result = payload.get("result")
        if isinstance(result, dict):
            candidates.append(result)
            for key in ("reply", "text", "content", "message"):
                if result.get(key):
                    candidates.append(result[key])
    else:
        candidates.append(text)
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get("label"):
            return candidate
        if isinstance(candidate, str):
            candidate = candidate.strip()
            if not candidate:
                continue
            try:
                nested = json.loads(candidate)
            except json.JSONDecodeError:
                nested = None
            if isinstance(nested, dict) and nested.get("label"):
                return nested
            match = re.search(r"\{.*\}", candidate, re.S)
            if match:
                try:
                    nested = json.loads(match.group(0))
                except json.JSONDecodeError:
                    nested = None
                if isinstance(nested, dict) and nested.get("label"):
                    return nested
    return None


def _normalized_label_surface(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", normalized)


def _is_low_signal_label_text(value: str) -> bool:
    normalized = _normalized_label_surface(value)
    if not normalized:
        return True
    if normalized in LOW_SIGNAL_LABEL_PHRASES:
        return True
    return any(
        normalized.startswith(f"{phrase} ")
        for phrase in ("uploaded image", "you said", "current url")
    )


def _generic_bubble_thesis(value: str) -> bool:
    normalized = " ".join((value or "").lower().split())
    return normalized.startswith("there is a quiet shift here")


def _summary_label_candidate(row: Dict) -> str:
    summary = " ".join(str(row.get("summary", "")).split())
    if not summary:
        return ""
    if _is_low_signal_label_text(summary):
        return ""
    if len(tokenize(summary)) < 2:
        return ""
    return shorten(summary, 120)


def _record_tokens(row: Dict) -> set[str]:
    tokens = set(row.get("attributes", {}).get("tokens", []))
    label = row.get("label", "")
    if not _is_low_signal_label_text(label):
        tokens.update(tokenize(label))
    tokens.update(tokenize(row.get("summary", "")))
    return {token for token in tokens if token and token not in STOPWORDS}


def _meaningful_tokens(values: List[str]) -> set[str]:
    return {
        value
        for value in values
        if value
        and value not in STOPWORDS
        and value not in LOW_SIGNAL_LABEL_TOKENS
    }


def _label_tokens(row: Dict) -> set[str]:
    label = row.get("label", "")
    if _is_low_signal_label_text(label):
        return set()
    return _meaningful_tokens(tokenize(label))


def _is_low_signal_seed(row: Dict) -> bool:
    if row["kind"] not in {"shared_primitive", "signal_frame", "theme"}:
        return False
    attributes = row.get("attributes", {})
    primitive_key = attributes.get("primitive_key", "")
    if primitive_key.startswith(LOW_SIGNAL_PRIMITIVE_PREFIXES):
        return True
    label_tokens = _label_tokens(row)
    attribute_tokens = _meaningful_tokens(attributes.get("tokens", []))
    if label_tokens:
        return False
    if row["kind"] == "shared_primitive" and attributes.get("family") == "emergent_pattern" and len(attribute_tokens) < 2:
        return True
    return len(attribute_tokens) == 0


def _primitive_keys(row: Dict) -> List[str]:
    attributes = row.get("attributes", {})
    if row["kind"] == "shared_primitive":
        key = attributes.get("primitive_key")
        if key:
            return [key]
        return [slugify(row["label"])]
    return []


def _primitive_families(row: Dict) -> List[str]:
    family = row.get("attributes", {}).get("family")
    return [family] if family else []


def _domain_lenses(row: Dict) -> List[str]:
    attributes = row.get("attributes", {})
    values = list(attributes.get("transfer_targets", []))
    linked_to = attributes.get("linked_to")
    if row["kind"] == "transfer_target":
        values.append(slugify(row["label"]))
    if linked_to:
        values.append(linked_to)
    return sorted({value for value in values if value})


def _tension_terms(row: Dict) -> List[str]:
    if row["kind"] != "tension":
        return []
    return [row["summary"]]


def _question_terms(row: Dict) -> List[str]:
    if row["kind"] != "question":
        return []
    return [row["summary"]]


def _state_raw_label(state: Dict) -> str:
    rows = list(state["_member_rows"].values())
    shared = [row for row in rows if row["kind"] == "shared_primitive" and not _is_low_signal_label_text(row["label"])]
    if shared:
        return max(shared, key=lambda item: (item["confidence"], item["label"]))["label"]
    themes = [row for row in rows if row["kind"] == "theme" and not _is_low_signal_label_text(row["label"])]
    if themes:
        return max(themes, key=lambda item: (item["confidence"], item["label"]))["label"]
    signals = [row for row in rows if row["kind"] == "signal_frame" and not _is_low_signal_label_text(row["label"])]
    if signals:
        return max(signals, key=lambda item: (item["confidence"], item["label"]))["label"]
    meaningful = [row for row in rows if not _is_low_signal_label_text(row["label"])]
    if meaningful:
        return max(meaningful, key=lambda item: (item["confidence"], item["label"]))["label"]
    summary_labels = [(row["confidence"], _summary_label_candidate(row)) for row in rows]
    summary_labels = [(confidence, label) for confidence, label in summary_labels if label]
    if summary_labels:
        return max(summary_labels, key=lambda item: (item[0], item[1]))[1]
    anchors = [row for row in rows if state["_member_roles"].get(row["meta_id"]) == "anchor"]
    return (anchors[0]["label"] if anchors else rows[0]["label"])[:120]


def _seed_candidates(meta_rows: List[Dict]) -> List[Dict]:
    grouped: Dict[tuple[str, ...], List[Dict]] = defaultdict(list)
    for row in meta_rows:
        if _is_low_signal_seed(row):
            continue
        if row.get("attributes", {}).get("semantic_role") == "approved_context":
            continue
        if row["kind"] == "shared_primitive" and row["confidence"] >= 0.60:
            grouped[tuple(sorted(row.get("chunk_ids", [])))].append(row)
        elif row["kind"] in {"signal_frame", "theme"}:
            grouped[tuple(sorted(row.get("chunk_ids", [])))].append(row)
    winners = []
    for rows in grouped.values():
        winner = min(
            rows,
            key=lambda item: (
                SEED_KIND_PRIORITY[item["kind"]],
                -item["confidence"],
                item["label"],
                item["meta_id"],
            ),
        )
        winners.append(winner)
    return sorted(
        winners,
        key=lambda item: (
            SEED_KIND_PRIORITY[item["kind"]],
            -item["confidence"],
            item["label"],
            item["meta_id"],
        ),
    )


def _new_state(anchor: Dict, now: str) -> Dict:
    bubble_id = _digest("bubble", anchor["meta_id"], anchor["label"])
    return {
        "bubble_id": bubble_id,
        "created_at": now,
        "last_reinforced_at": now,
        "_member_ids": set(),
        "_member_rows": {},
        "_member_roles": {},
        "_source_refs": set(),
        "_chunk_ids": set(),
        "_tokens": set(),
        "_primitive_keys": set(),
        "_primitive_families": set(),
        "_domain_lenses": set(),
        "_active_tensions": [],
        "_open_questions": [],
        "_polarities": set(),
        "_primary_concept_id": "",
        "_concept_ids": set(),
    }


def _store_member(state: Dict, row: Dict, role: str) -> None:
    meta_id = row["meta_id"]
    if meta_id in state["_member_ids"]:
        existing = state["_member_roles"][meta_id]
        if existing != "anchor" and role == "anchor":
            state["_member_roles"][meta_id] = "anchor"
        return
    state["_member_ids"].add(meta_id)
    state["_member_rows"][meta_id] = row
    state["_member_roles"][meta_id] = role
    state["_source_refs"].update(row.get("source_refs", []))
    state["_chunk_ids"].update(row.get("chunk_ids", []))
    state["_tokens"].update(_record_tokens(row))
    state["_primitive_keys"].update(_primitive_keys(row))
    state["_primitive_families"].update(_primitive_families(row))
    state["_domain_lenses"].update(_domain_lenses(row))
    state["_active_tensions"].extend(_tension_terms(row))
    state["_open_questions"].extend(_question_terms(row))
    polarity = row.get("attributes", {}).get("polarity")
    if polarity:
        state["_polarities"].add(polarity)


def _row_profile(row: Dict) -> Dict:
    return {
        "meta_id": row["meta_id"],
        "tokens": _record_tokens(row),
        "primitives": set(_primitive_keys(row)),
        "families": set(_primitive_families(row)),
        "lenses": set(_domain_lenses(row)),
        "source_refs": set(row.get("source_refs", [])),
        "chunk_ids": set(row.get("chunk_ids", [])),
        "tension_tokens": set(tokenize(" ".join(_tension_terms(row)))),
        "question_tokens": set(tokenize(" ".join(_question_terms(row)))),
    }


def _state_indexes() -> Dict[str, Dict[str, set[str]]]:
    return {
        "primitive_keys": defaultdict(set),
        "primitive_families": defaultdict(set),
        "domain_lenses": defaultdict(set),
        "tokens": defaultdict(set),
        "source_refs": defaultdict(set),
        "chunk_ids": defaultdict(set),
        "states_by_id": {},
    }


def _register_state(indexes: Dict[str, Dict[str, set[str]]], state: Dict) -> None:
    indexes["states_by_id"][state["bubble_id"]] = state


def _index_state_row(indexes: Dict[str, Dict[str, set[str]]], state: Dict, row: Dict) -> None:
    bubble_id = state["bubble_id"]
    for key in _primitive_keys(row):
        indexes["primitive_keys"][key].add(bubble_id)
    for family in _primitive_families(row):
        indexes["primitive_families"][family].add(bubble_id)
    for lens in _domain_lenses(row):
        indexes["domain_lenses"][lens].add(bubble_id)
    for token in _record_tokens(row):
        indexes["tokens"][token].add(bubble_id)
    for source_ref in row.get("source_refs", []):
        indexes["source_refs"][source_ref].add(bubble_id)
    for chunk_id in row.get("chunk_ids", []):
        indexes["chunk_ids"][chunk_id].add(bubble_id)


def _index_state(indexes: Dict[str, Dict[str, set[str]]], state: Dict) -> None:
    _register_state(indexes, state)
    for row in state["_member_rows"].values():
        _index_state_row(indexes, state, row)


def _ranked_state_ids(
    profile: Dict,
    indexes: Dict[str, Dict[str, set[str]]],
    *,
    limit: int = 96,
) -> List[str]:
    structural_scores: Dict[str, float] = defaultdict(float)
    token_scores: Dict[str, float] = defaultdict(float)

    def _bump(bucket: Dict[str, float], index_name: str, keys: set[str], weight: float) -> None:
        for key in keys:
            for bubble_id in indexes[index_name].get(key, set()):
                bucket[bubble_id] += weight

    _bump(structural_scores, "chunk_ids", profile["chunk_ids"], 4.5)
    _bump(structural_scores, "source_refs", profile["source_refs"], 3.0)
    for key in profile["primitives"]:
        _bump(structural_scores, "primitive_keys", {key}, 5.0)
    for family in profile["families"]:
        _bump(structural_scores, "primitive_families", {family}, 3.5)
    for lens in profile["lenses"]:
        _bump(structural_scores, "domain_lenses", {lens}, 2.5)

    token_keys = _meaningful_tokens(list(profile["tokens"] | profile["tension_tokens"] | profile["question_tokens"]))
    if structural_scores:
        for token in token_keys:
            for bubble_id in indexes["tokens"].get(token, set()):
                if bubble_id in structural_scores:
                    structural_scores[bubble_id] += 0.35
        ranked = sorted(structural_scores.items(), key=lambda item: (-item[1], item[0]))
        return [bubble_id for bubble_id, _ in ranked[:limit]]

    for token in token_keys:
        for bubble_id in indexes["tokens"].get(token, set()):
            token_scores[bubble_id] += 1.0
    ranked = sorted(
        (
            (bubble_id, score)
            for bubble_id, score in token_scores.items()
            if score >= 2.0
        ),
        key=lambda item: (-item[1], item[0]),
    )
    if not ranked:
        return []
    return [bubble_id for bubble_id, _ in ranked[:limit]]


def _candidate_states(profile: Dict, indexes: Dict[str, Dict[str, set[str]]]) -> List[Dict]:
    states_by_id = indexes["states_by_id"]
    return [states_by_id[bubble_id] for bubble_id in _ranked_state_ids(profile, indexes) if bubble_id in states_by_id]


def _seed_attachment_score(profile: Dict, state: Dict) -> float:
    score = 0.0
    if profile["primitives"] & state["_primitive_keys"] or profile["families"] & state["_primitive_families"]:
        score += 0.35
    if profile["lenses"] & state["_domain_lenses"]:
        score += 0.20
    if profile["tokens"] & state["_tokens"]:
        score += 0.15
    if profile["source_refs"] and state["_source_refs"] and not profile["source_refs"] <= state["_source_refs"]:
        score += 0.10
    if profile["tension_tokens"] & state["_tokens"]:
        score += 0.10
    if profile["question_tokens"] & state["_tokens"]:
        score += 0.10
    return round(min(0.99, score), 2)


def _best_seed_bubble(profile: Dict, states: List[Dict]) -> Tuple[Dict | None, float, int]:
    best_state = None
    best_score = 0.0
    for state in states:
        score = _seed_attachment_score(profile, state)
        if score > best_score:
            best_state = state
            best_score = score
    return best_state, best_score, len(states)


def _role_for_record(row: Dict) -> str:
    return ROLE_DIRECT_MAP.get(row["kind"], "support")


def _attach_related_records(
    meta_rows: List[Dict],
    indexes: Dict[str, Dict[str, set[str]]],
    row_profiles: Dict[str, Dict],
    progress_callback=None,
) -> Dict[str, int]:
    assigned = {
        meta_id
        for state in indexes["states_by_id"].values()
        for meta_id in state["_member_ids"]
    }
    attachment_checks = 0
    attached_count = 0
    total = len(meta_rows)
    for index, row in enumerate(meta_rows, start=1):
        if row["meta_id"] in assigned:
            if progress_callback and (index == total or index % 2000 == 0):
                progress_callback(index, attachment_checks, attached_count)
            continue
        profile = row_profiles[row["meta_id"]]
        best_state = None
        best_score = 0.0
        candidate_states = _candidate_states(profile, indexes)
        attachment_checks += len(candidate_states)
        for state in candidate_states:
            chunk_overlap = len(profile["chunk_ids"] & state["_chunk_ids"])
            if chunk_overlap:
                score = 0.70 + min(0.20, chunk_overlap * 0.06)
            else:
                source_overlap = 0.12 if profile["source_refs"] & state["_source_refs"] else 0.0
                token_overlap = 0.06 if profile["tokens"] & state["_tokens"] else 0.0
                score = _seed_attachment_score(profile, state) + source_overlap + token_overlap
            if score > best_score:
                best_state = state
                best_score = score
        if best_state and best_score >= 0.40:
            _store_member(best_state, row, _role_for_record(row))
            _index_state_row(indexes, best_state, row)
            assigned.add(row["meta_id"])
            attached_count += 1
        if progress_callback and (index == total or index % 2000 == 0):
            progress_callback(index, attachment_checks, attached_count)
    return {
        "attachment_checks": attachment_checks,
        "attached_count": attached_count,
    }


def _write_progress(
    root: Path,
    *,
    status: str,
    phase: str,
    meta_row_count: int,
    seed_count: int,
    states_count: int,
    processed_count: int,
    total_count: int,
    seed_checks: int = 0,
    attachment_checks: int = 0,
    attached_count: int = 0,
    edge_pair_checks: int = 0,
    edge_count: int = 0,
    profiling: Dict | None = None,
) -> None:
    write_json(
        _progress_path(root),
        {
            "generated_at": utc_now(),
            "status": status,
            "phase": phase,
            "meta_row_count": meta_row_count,
            "seed_count": seed_count,
            "states_count": states_count,
            "processed_count": processed_count,
            "total_count": total_count,
            "seed_checks": seed_checks,
            "attachment_checks": attachment_checks,
            "attached_count": attached_count,
            "edge_pair_checks": edge_pair_checks,
            "edge_count": edge_count,
            "profiling": profiling or {},
        },
    )


def _bubble_label(state: Dict) -> str:
    return state.get("_canonical_label") or _state_raw_label(state)


def _bubble_thesis(state: Dict) -> str:
    rows = list(state["_member_rows"].values())
    why_rows = [row for row in rows if row["kind"] == "why_it_matters"]
    if why_rows:
        return max(why_rows, key=lambda item: (item["confidence"], item["summary"]))["summary"]
    signal_rows = [row for row in rows if row["kind"] == "signal_frame"]
    if signal_rows:
        return max(signal_rows, key=lambda item: (item["confidence"], item["summary"]))["summary"]
    return rows[0]["summary"]


def _bubble_confidence(state: Dict) -> float:
    total = 0.0
    weight = 0.0
    for meta_id, row in state["_member_rows"].items():
        member_weight = 2.0 if state["_member_roles"].get(meta_id) == "anchor" else 1.0
        total += row["confidence"] * member_weight
        weight += member_weight
    base = total / max(1.0, weight)
    recurrence_bonus = min(0.08, max(0, len(state["_source_refs"]) - 1) * 0.04)
    return round(min(0.96, base + recurrence_bonus), 2)


def _needs_semantic_bubble_assist(row: Dict) -> bool:
    label_tokens = tokenize(row.get("label", ""))
    return (
        not row.get("primary_concept_id")
        and row.get("support_count", 0) >= 2
        and (
            _is_low_signal_label_text(row.get("label", ""))
            or len(label_tokens) <= 3
            or _generic_bubble_thesis(row.get("thesis", ""))
        )
    )


def _bubble_assist_fingerprint(row: Dict, chunk_lookup: Dict[str, Dict[str, Any]]) -> str:
    snippet_payload = []
    for chunk_id in row.get("chunk_ids", [])[:3]:
        chunk = chunk_lookup.get(chunk_id)
        if chunk:
            snippet_payload.append(chunk.get("content", "")[:220])
    payload = {
        "label": row.get("label", ""),
        "thesis": row.get("thesis", ""),
        "dominant_primitives": row.get("dominant_primitives", []),
        "support_count": row.get("support_count", 0),
        "chunk_snippets": snippet_payload,
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _bubble_assist_prompt(row: Dict, snippets: List[Dict[str, Any]]) -> str:
    evidence_block = "\n".join(
        f"- {snippet['title']}: {snippet['excerpt']}"
        for snippet in snippets
    ) or "- No direct source snippets."
    return "\n".join(
        [
            "You are relabeling a context bubble for Inner World.",
            "Return JSON only with this shape:",
            '{"label":"...","confidence":"high|medium|low","reason":"..."}',
            "",
            "Rules:",
            "- Produce a short human-readable label grounded in the evidence.",
            "- Prefer 2 to 6 words.",
            "- Avoid transcript residue, UI labels, placeholders, or generic phrases.",
            "- Do not invent concepts not present in the evidence.",
            "",
            f"Current label: {row.get('label', '')}",
            f"Thesis: {row.get('thesis', '')}",
            f"Dominant primitives: {', '.join(row.get('dominant_primitives', [])[:4])}",
            "",
            "Evidence snippets:",
            evidence_block,
        ]
    )


def _run_bubble_assist(
    root: Path,
    config: Dict[str, Any],
    row: Dict,
    snippets: List[Dict[str, Any]],
) -> Dict[str, Any] | None:
    command = [
        "openclaw",
        "agent",
        "--agent",
        config["agent"],
        "--thinking",
        config["thinking"],
        "--message",
        _bubble_assist_prompt(row, snippets),
        "--json",
    ]
    if config["backend_id"] == "openclaw_local":
        command.append("--local")
    completed = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        timeout=config["timeout_seconds"],
        check=False,
    )
    if completed.returncode != 0:
        return None
    payload = _extract_assist_json(completed.stdout)
    if not payload:
        return None
    label = shorten(str(payload.get("label", "")).strip(), 80).rstrip(" .")
    if not label or _is_low_signal_label_text(label):
        return None
    if len(tokenize(label)) > 7:
        return None
    return {
        "label": label,
        "confidence": str(payload.get("confidence", "")).strip().lower(),
        "reason": shorten(str(payload.get("reason", "")).strip(), 220).rstrip(),
    }


def _semantic_bubble_snippets(
    row: Dict,
    chunk_lookup: Dict[str, Dict[str, Any]],
    limit: int,
    char_limit: int,
) -> List[Dict[str, Any]]:
    snippets: List[Dict[str, Any]] = []
    for chunk_id in row.get("chunk_ids", [])[:limit]:
        chunk = chunk_lookup.get(chunk_id)
        if not chunk:
            continue
        snippets.append(
            {
                "chunk_id": chunk_id,
                "title": chunk.get("semantic_title") or chunk.get("title", ""),
                "excerpt": shorten(chunk.get("semantic_content") or chunk.get("content", ""), char_limit),
            }
        )
    return snippets


def _apply_semantic_bubble_titles(root: Path, bubbles: List[Dict]) -> tuple[List[Dict], Dict[str, Any]]:
    config = _bubble_assist_config(root)
    if not config.get("enabled") or not bubbles:
        return bubbles, {"attempted": 0, "applied": 0, "cached": 0}
    candidates = [
        row
        for row in sorted(
            bubbles,
            key=lambda item: (
                item.get("status") != "active",
                -float(item.get("confidence", 0.0)),
                -int(item.get("support_count", 0)),
                item.get("label", ""),
            ),
        )
        if _needs_semantic_bubble_assist(row)
    ][: config["label_limit"]]
    if not candidates:
        return bubbles, {"attempted": 0, "applied": 0, "cached": 0}
    chunk_lookup = {row["chunk_id"]: row for row in load_chunk_index(root)}
    cache = _load_bubble_title_cache(root)
    updated = False
    applied = 0
    cached_hits = 0
    bubble_lookup = {row["bubble_id"]: row for row in bubbles}
    for row in candidates:
        fingerprint = _bubble_assist_fingerprint(row, chunk_lookup)
        cached = cache.get(row["bubble_id"])
        payload = None
        if cached and cached.get("fingerprint") == fingerprint:
            payload = cached.get("payload")
            cached_hits += 1
        else:
            snippets = _semantic_bubble_snippets(row, chunk_lookup, config["snippet_limit"], config["snippet_chars"])
            payload = _run_bubble_assist(root, config, row, snippets)
            if payload:
                cache[row["bubble_id"]] = {
                    "fingerprint": fingerprint,
                    "payload": payload,
                    "updated_at": utc_now(),
                }
                updated = True
        if not payload or not payload.get("label"):
            continue
        bubble = bubble_lookup[row["bubble_id"]]
        bubble["raw_label"] = bubble.get("raw_label") or bubble.get("label", "")
        bubble["semantic_label"] = payload["label"]
        bubble["semantic_assist"] = payload
        bubble["label"] = payload["label"]
        applied += 1
    if updated:
        _write_bubble_title_cache(root, cache)
    return list(bubble_lookup.values()), {"attempted": len(candidates), "applied": applied, "cached": cached_hits}


def _merge_state_into(primary: Dict, secondary: Dict) -> None:
    for meta_id, row in secondary["_member_rows"].items():
        _store_member(primary, row, secondary["_member_roles"].get(meta_id, "support"))
    primary["created_at"] = min(primary["created_at"], secondary["created_at"])
    primary["last_reinforced_at"] = max(primary["last_reinforced_at"], secondary["last_reinforced_at"])
    primary["_concept_ids"].update(secondary.get("_concept_ids", set()))
    if not primary.get("_primary_concept_id"):
        primary["_primary_concept_id"] = secondary.get("_primary_concept_id", "")


def _align_state_concepts(
    root: Path,
    states: List[Dict],
    concepts: List[Dict],
    governed_lookup: Dict[str, Dict[str, Any]] | None = None,
) -> None:
    for state in states:
        alias_payload = canonicalize_concept_identity(
            root,
            _state_raw_label(state),
            aliases=[row["label"] for row in state["_member_rows"].values()],
            transfer_terms=sorted(state["_domain_lenses"] | state["_primitive_keys"]),
        )
        state["_canonical_label"] = alias_payload["canonical_label"]
        state_tokens = _meaningful_tokens(list(state["_tokens"])) | set(tokenize(alias_payload["canonical_label"]))
        state["_meaningful_tokens"] = state_tokens
        concept_eligible = True
        if governed_lookup is not None:
            concept_eligible = any(
                governed_lookup.get(source_ref, {}).get("include_in_concepts", True)
                for source_ref in state["_source_refs"]
            )
        if not concept_eligible:
            state["_concept_ids"] = set()
            state["_primary_concept_id"] = ""
            state["_label_slug"] = slugify(alias_payload["canonical_label"])
            continue
        state_transfers = set(alias_payload["transfer_terms"]) | set(state["_domain_lenses"]) | set(state["_primitive_keys"])
        matches = []
        for concept in concepts:
            label_tokens = set(tokenize(concept.get("label", ""))) | {
                token
                for alias in concept.get("aliases", [])
                for token in tokenize(alias)
            }
            transfer_tokens = set(concept.get("attributes", {}).get("transfer_terms", []))
            source_overlap = len(set(concept.get("source_refs", [])) & state["_source_refs"])
            label_overlap = len(state_tokens & label_tokens)
            transfer_overlap = len(state_transfers & transfer_tokens)
            score = label_overlap * 0.22 + transfer_overlap * 0.18 + source_overlap * 0.12
            if alias_payload["canonical_label"].lower() == concept.get("label", "").lower():
                score += 0.36
            if score >= 0.34:
                matches.append((score, concept))
        matches.sort(key=lambda item: (-item[0], -item[1].get("confidence", 0.0), item[1]["concept_id"]))
        state["_concept_ids"] = {concept["concept_id"] for _, concept in matches[:4]}
        state["_primary_concept_id"] = matches[0][1]["concept_id"] if matches else ""
        state["_label_slug"] = slugify(alias_payload["canonical_label"])


def _merge_duplicate_label_states(
    root: Path,
    states: List[Dict],
    concepts: List[Dict],
    governed_lookup: Dict[str, Dict[str, Any]] | None = None,
    progress_callback=None,
) -> List[Dict]:
    _align_state_concepts(root, states, concepts, governed_lookup=governed_lookup)
    merged: List[Dict] = []
    merged_by_concept: Dict[str, Dict] = {}
    merged_by_slug: Dict[str, List[Dict]] = defaultdict(list)
    ordered_states = sorted(states, key=lambda item: (-len(item["_member_ids"]), item["bubble_id"]))
    total = len(ordered_states)
    for index, state in enumerate(ordered_states, start=1):
        label_slug = state.get("_label_slug") or slugify(_bubble_label(state))
        shared_tokens = state.get("_meaningful_tokens") or _meaningful_tokens(list(state["_tokens"]))
        target = None
        primary_concept_id = state.get("_primary_concept_id")
        if primary_concept_id:
            target = merged_by_concept.get(primary_concept_id)
        if target is None:
            for existing in merged_by_slug.get(label_slug, []):
                existing_tokens = existing.get("_meaningful_tokens") or _meaningful_tokens(list(existing["_tokens"]))
                if len(shared_tokens & existing_tokens) >= 2:
                    target = existing
                    break
                if state["_primitive_families"] & existing["_primitive_families"]:
                    target = existing
                    break
                if state["_domain_lenses"] & existing["_domain_lenses"]:
                    target = existing
                    break
        if target is None:
            merged.append(state)
            merged_by_slug[label_slug].append(state)
            if primary_concept_id:
                merged_by_concept[primary_concept_id] = state
            if progress_callback and (index == total or index % 250 == 0):
                progress_callback(index, len(merged))
            continue
        _merge_state_into(target, state)
        target["_meaningful_tokens"] = _meaningful_tokens(list(target["_tokens"]))
        if primary_concept_id:
            merged_by_concept[primary_concept_id] = target
        if progress_callback and (index == total or index % 250 == 0):
            progress_callback(index, len(merged))
    return merged


def _has_structural_support(state: Dict) -> bool:
    structural_kinds = {
        "shared_primitive",
        "direction",
        "tension",
        "question",
        "guardrail",
        "why_it_matters",
        "contradiction",
    }
    return any(row["kind"] in structural_kinds for row in state["_member_rows"].values())


def _prune_low_signal_states(states: List[Dict]) -> List[Dict]:
    kept: List[Dict] = []
    for state in states:
        semantic_tokens = state.get("_meaningful_tokens") or _meaningful_tokens(list(state["_tokens"]))
        member_rows = list(state["_member_rows"].values())
        if (
            member_rows
            and all(_is_low_signal_label_text(row.get("label", "")) for row in member_rows)
            and len(semantic_tokens) < 2
            and not state.get("_concept_ids")
        ):
            continue
        if len(state["_source_refs"]) >= 2:
            kept.append(state)
            continue
        if _has_structural_support(state):
            kept.append(state)
            continue
        if len(state["_member_ids"]) >= 6:
            kept.append(state)
            continue
        if state["_active_tensions"] or state["_open_questions"] or state["_domain_lenses"]:
            kept.append(state)
            continue
    return kept


def _finalize_bubbles(states: List[Dict]) -> List[Dict]:
    rows = []
    for state in states:
        label = _bubble_label(state)
        confidence = _bubble_confidence(state)
        bubble = ContextBubble(
            bubble_id=state["bubble_id"],
            label=label,
            thesis=_bubble_thesis(state),
            status="needs_review" if confidence < 0.58 else "active",
            confidence=confidence,
            support_count=len(state["_member_ids"]),
            source_refs=sorted(state["_source_refs"]),
            chunk_ids=sorted(state["_chunk_ids"]),
            meta_ids=sorted(state["_member_ids"]),
            dominant_primitives=sorted(state["_primitive_keys"]) or [slugify(label)],
            active_tensions=sorted(set(state["_active_tensions"]))[:6],
            open_questions=sorted(set(state["_open_questions"]))[:6],
            domain_lenses=sorted(state["_domain_lenses"])[:8],
            primary_abstract_thread_id="",
            supporting_thread_ids=[],
            project_lens_keys=[],
            primary_concept_id=state.get("_primary_concept_id", ""),
            concept_ids=sorted(state.get("_concept_ids", set())),
            related_bubble_ids=[],
            created_at=state["created_at"],
            last_reinforced_at=state["last_reinforced_at"],
        ).to_dict()
        rows.append(bubble)
    return sorted(rows, key=lambda item: (item["status"] != "active", -item["confidence"], item["label"], item["bubble_id"]))


def _enrich_bubbles_with_thread_abstractions(bubbles: List[Dict], abstractions: List[Dict]) -> None:
    if not bubbles or not abstractions:
        return
    for bubble in bubbles:
        bubble_meta_ids = set(bubble.get("meta_ids", []))
        bubble_sources = set(bubble.get("source_refs", []))
        matches = []
        for abstraction in abstractions:
            semantic_overlap = len(bubble_meta_ids & set(abstraction.get("semantic_line_meta_ids", [])))
            context_overlap = len(bubble_meta_ids & set(abstraction.get("approved_context_meta_ids", [])))
            source_overlap = len(bubble_sources & set(abstraction.get("source_refs", [])))
            if semantic_overlap == 0 and context_overlap == 0 and source_overlap == 0:
                continue
            score = semantic_overlap * 3 + context_overlap + source_overlap
            matches.append((score, semantic_overlap, abstraction))
        if not matches:
            continue
        matches.sort(key=lambda item: (-item[0], -item[1], -item[2]["confidence"], item[2]["abstract_thread_id"]))
        primary = matches[0][2]
        bubble["primary_abstract_thread_id"] = primary["abstract_thread_id"]
        bubble["supporting_thread_ids"] = sorted(
            {
                thread_id
                for _, _, abstraction in matches
                for thread_id in abstraction.get("child_thread_ids", [])
            }
        )
        bubble["project_lens_keys"] = sorted(
            {
                key
                for _, _, abstraction in matches
                for key in abstraction.get("project_lens_keys", [abstraction.get("primary_lens_key", "")])
                if key
            }
        )
        if not bubble.get("domain_lenses"):
            bubble["domain_lenses"] = bubble["project_lens_keys"][:8]


def _build_memberships(states: List[Dict], now: str) -> List[Dict]:
    rows = []
    for state in states:
        for meta_id, role in sorted(state["_member_roles"].items(), key=lambda item: item[0]):
            row = state["_member_rows"][meta_id]
            rows.append(
                BubbleMembership(
                    membership_id=_digest("membership", state["bubble_id"], meta_id),
                    bubble_id=state["bubble_id"],
                    meta_id=meta_id,
                    role=role,
                    confidence=row["confidence"],
                    created_at=now,
                ).to_dict()
            )
    return rows


def _edge_token_sets(states: List[Dict]) -> Dict[str, set[str]]:
    ordered = sorted(states, key=lambda item: item["bubble_id"])
    max_common_token_frequency = max(3, len(ordered) // 20)
    document_frequency: Dict[str, int] = defaultdict(int)
    raw_token_sets: Dict[str, set[str]] = {}
    for state in ordered:
        tokens = set(state.get("_meaningful_tokens") or _meaningful_tokens(list(state["_tokens"])))
        raw_token_sets[state["bubble_id"]] = tokens
        for token in tokens:
            document_frequency[token] += 1
    filtered_sets: Dict[str, set[str]] = {}
    for bubble_id, tokens in raw_token_sets.items():
        filtered = {
            token
            for token in tokens
            if document_frequency[token] <= max_common_token_frequency
        }
        filtered_sets[bubble_id] = filtered or tokens
    return filtered_sets


def _build_edges(
    states: List[Dict],
    now: str,
    progress_callback: Callable[[int, int, int, int], None] | None = None,
) -> tuple[List[Dict], List[Dict], Dict[str, List[str]], int]:
    edges: List[Dict] = []
    transitions: List[Dict] = []
    related_ids: Dict[str, set[str]] = defaultdict(set)
    ordered = sorted(states, key=lambda item: item["bubble_id"])
    token_sets = _edge_token_sets(ordered)
    total_states = len(ordered)
    pair_checks = 0
    for index, left in enumerate(ordered):
        left_tokens = token_sets[left["bubble_id"]]
        for right in ordered[index + 1 :]:
            pair_checks += 1
            right_tokens = token_sets[right["bubble_id"]]
            shared_primitives = left["_primitive_keys"] & right["_primitive_keys"]
            shared_domains = left["_domain_lenses"] & right["_domain_lenses"]
            token_overlap = left_tokens & right_tokens
            token_overlap_count = len(token_overlap)
            member_overlap: int | None = None
            opposite_polarity = (
                ("protective" in left["_polarities"] and "expansive" in right["_polarities"])
                or ("expansive" in left["_polarities"] and "protective" in right["_polarities"])
            )
            kind = None
            if opposite_polarity and (token_overlap_count or shared_domains):
                if not shared_primitives:
                    kind = "contradicts"
                else:
                    member_overlap = len(left["_member_ids"] & right["_member_ids"])
                    if member_overlap <= 1:
                        kind = "contradicts"
            shared_concepts = left.get("_concept_ids", set()) & right.get("_concept_ids", set())
            if kind is None and shared_primitives:
                kind = "overlaps"
            if kind is None and token_overlap_count >= 2 and (shared_domains or shared_concepts):
                kind = "overlaps"
            if kind is None and token_overlap_count >= 3:
                kind = "overlaps"
            if kind is None and shared_concepts and token_overlap_count:
                kind = "bridge"
            if kind is None:
                if member_overlap is None:
                    member_overlap = len(left["_member_ids"] & right["_member_ids"])
                if member_overlap:
                    kind = "overlaps"
            if kind is None and shared_domains and token_overlap_count >= 2:
                kind = "bridge"
            if not kind:
                continue
            shared_terms = sorted(token_overlap)[:6]
            confidence = 0.42 + min(0.18, len(shared_terms) * 0.04) + min(0.12, len(shared_domains) * 0.04)
            if kind == "contradicts":
                confidence += 0.14
            elif kind == "overlaps":
                confidence += 0.10
            else:
                confidence += 0.08
            edge = BubbleEdge(
                edge_id=_digest("bubble-edge", kind, left["bubble_id"], right["bubble_id"]),
                kind=kind,
                from_bubble_id=left["bubble_id"],
                to_bubble_id=right["bubble_id"],
                confidence=round(min(0.92, confidence), 2),
                shared_terms=shared_terms,
                evidence_refs=sorted(left["_source_refs"] | right["_source_refs"]),
                created_at=now,
            ).to_dict()
            edges.append(edge)
            related_ids[left["bubble_id"]].add(right["bubble_id"])
            related_ids[right["bubble_id"]].add(left["bubble_id"])
            if kind in {"bridge", "contradicts"}:
                transitions.append(
                    BubbleTransition(
                        transition_id=_digest("bubble-transition", kind, left["bubble_id"], right["bubble_id"]),
                        bubble_id=left["bubble_id"],
                        action="bridge" if kind == "bridge" else "contradict",
                        meta_id=None,
                        related_bubble_id=right["bubble_id"],
                        reason=f"{kind} edge derived from shared pressure between bubbles.",
                        created_at=now,
                    ).to_dict()
                )
        if progress_callback and (index + 1 == total_states or (index + 1) % 50 == 0):
            progress_callback(index + 1, total_states, pair_checks, len(edges))
    related_lists = {bubble_id: sorted(values) for bubble_id, values in related_ids.items()}
    return (
        sorted(edges, key=lambda item: (-item["confidence"], item["kind"], item["edge_id"])),
        transitions,
        related_lists,
        pair_checks,
    )


def build_context_bubbles(
    root: Path,
    domain_overlays: List[str] | None = None,
    ensure_dependencies: bool = True,
    profile: bool = False,
) -> Dict:
    ensure_dir(_data_dir(root))
    if ensure_dependencies:
        build_thread_abstractions(root, domain_overlays)
    governed_lookup = get_governed_source_lookup(root)
    meta_rows = [
        row
        for row in load_meta_records(root)
        if any(
            governed_lookup.get(source_ref, {}).get("include_in_bubbles", True)
            for source_ref in row.get("source_refs", [])
        )
    ]
    _write_progress(
        root,
        status="running",
        phase="precompute_profiles",
        meta_row_count=len(meta_rows),
        seed_count=0,
        states_count=0,
        processed_count=0,
        total_count=len(meta_rows),
    )
    row_profiles = {row["meta_id"]: _row_profile(row) for row in meta_rows}
    seeds = _seed_candidates(meta_rows)
    states: List[Dict] = []
    indexes = _state_indexes()
    transitions: List[Dict] = []
    now = utc_now()
    seed_checks = 0
    seed_stage_started = perf_counter()
    _write_progress(
        root,
        status="running",
        phase="seed_selection",
        meta_row_count=len(meta_rows),
        seed_count=len(seeds),
        states_count=0,
        processed_count=0,
        total_count=len(seeds),
    )

    for index, row in enumerate(seeds, start=1):
        profile_row = row_profiles[row["meta_id"]]
        candidate_states = _candidate_states(profile_row, indexes)
        best_state, score, checks = _best_seed_bubble(profile_row, candidate_states)
        seed_checks += checks
        if best_state and score >= 0.58:
            source_before = set(best_state["_source_refs"])
            _store_member(best_state, row, "support")
            _index_state_row(indexes, best_state, row)
            transitions.append(
                BubbleTransition(
                    transition_id=_digest("bubble-transition", "attach", best_state["bubble_id"], row["meta_id"]),
                    bubble_id=best_state["bubble_id"],
                    action="attach",
                    meta_id=row["meta_id"],
                    related_bubble_id=None,
                    reason=f"Attached seed candidate with score {score:.2f}.",
                    created_at=now,
                ).to_dict()
            )
            if not set(row.get("source_refs", [])) <= source_before:
                best_state["last_reinforced_at"] = now
                transitions.append(
                    BubbleTransition(
                        transition_id=_digest("bubble-transition", "reinforce", best_state["bubble_id"], row["meta_id"]),
                        bubble_id=best_state["bubble_id"],
                        action="reinforce",
                        meta_id=row["meta_id"],
                        related_bubble_id=None,
                        reason="A new source reinforced an existing pressure point.",
                        created_at=now,
                ).to_dict()
            )
        else:
            state = _new_state(row, now)
            _store_member(state, row, "anchor")
            states.append(state)
            _register_state(indexes, state)
            _index_state_row(indexes, state, row)
            transitions.append(
                BubbleTransition(
                    transition_id=_digest("bubble-transition", "attach", state["bubble_id"], row["meta_id"]),
                    bubble_id=state["bubble_id"],
                    action="attach",
                    meta_id=row["meta_id"],
                    related_bubble_id=None,
                    reason="Created a new context bubble from a seed candidate.",
                    created_at=now,
                ).to_dict()
            )
        if index == len(seeds) or index % 250 == 0:
            _write_progress(
                root,
                status="running",
                phase="seed_selection",
                meta_row_count=len(meta_rows),
                seed_count=len(seeds),
                states_count=len(states),
                processed_count=index,
                total_count=len(seeds),
                seed_checks=seed_checks,
            )

    seed_stage_seconds = round(perf_counter() - seed_stage_started, 3)
    related_stage_started = perf_counter()
    _write_progress(
        root,
        status="running",
        phase="related_attachment",
        meta_row_count=len(meta_rows),
        seed_count=len(seeds),
        states_count=len(states),
        processed_count=0,
        total_count=len(meta_rows),
        seed_checks=seed_checks,
    )
    attachment_stats = _attach_related_records(
        meta_rows,
        indexes,
        row_profiles,
        progress_callback=lambda processed, attachment_checks, attached_count: _write_progress(
            root,
            status="running",
            phase="related_attachment",
            meta_row_count=len(meta_rows),
            seed_count=len(seeds),
            states_count=len(states),
            processed_count=processed,
            total_count=len(meta_rows),
            seed_checks=seed_checks,
            attachment_checks=attachment_checks,
            attached_count=attached_count,
        ),
    )
    related_stage_seconds = round(perf_counter() - related_stage_started, 3)
    merge_states_before = len(states)
    merge_stage_started = perf_counter()
    _write_progress(
        root,
        status="running",
        phase="merge_duplicate_labels",
        meta_row_count=len(meta_rows),
        seed_count=len(seeds),
        states_count=len(states),
        processed_count=len(meta_rows),
        total_count=len(meta_rows),
        seed_checks=seed_checks,
        attachment_checks=attachment_stats["attachment_checks"],
        attached_count=attachment_stats["attached_count"],
    )
    states = _merge_duplicate_label_states(
        root,
        states,
        load_concept_nodes(root),
        governed_lookup=governed_lookup,
        progress_callback=lambda processed, merged_count: _write_progress(
            root,
            status="running",
            phase="merge_duplicate_labels",
            meta_row_count=len(meta_rows),
            seed_count=len(seeds),
            states_count=merged_count,
            processed_count=processed,
            total_count=merge_states_before,
            seed_checks=seed_checks,
            attachment_checks=attachment_stats["attachment_checks"],
            attached_count=attachment_stats["attached_count"],
        ),
    )
    merge_stage_seconds = round(perf_counter() - merge_stage_started, 3)
    merge_states_after = len(states)
    pruned_before = len(states)
    prune_stage_started = perf_counter()
    states = _prune_low_signal_states(states)
    prune_stage_seconds = round(perf_counter() - prune_stage_started, 3)
    bubbles = _finalize_bubbles(states)
    _enrich_bubbles_with_thread_abstractions(bubbles, load_thread_abstractions(root))
    edge_stage_started = perf_counter()
    _write_progress(
        root,
        status="running",
        phase="edge_building",
        meta_row_count=len(meta_rows),
        seed_count=len(seeds),
        states_count=len(states),
        processed_count=0,
        total_count=len(states),
        seed_checks=seed_checks,
        attachment_checks=attachment_stats["attachment_checks"],
        attached_count=attachment_stats["attached_count"],
    )
    edges, edge_transitions, related_bubble_ids, edge_pair_checks = _build_edges(
        states,
        now,
        progress_callback=lambda processed, total, pair_checks, edge_count: _write_progress(
            root,
            status="running",
            phase="edge_building",
            meta_row_count=len(meta_rows),
            seed_count=len(seeds),
            states_count=len(states),
            processed_count=processed,
            total_count=total,
            seed_checks=seed_checks,
            attachment_checks=attachment_stats["attachment_checks"],
            attached_count=attachment_stats["attached_count"],
            edge_pair_checks=pair_checks,
            edge_count=edge_count,
        ),
    )
    memberships = _build_memberships(states, now)
    edge_stage_seconds = round(perf_counter() - edge_stage_started, 3)
    transitions.extend(edge_transitions)

    bubble_lookup = {row["bubble_id"]: row for row in bubbles}
    for bubble_id, related in related_bubble_ids.items():
        bubble_lookup[bubble_id]["related_bubble_ids"] = related
    assisted_bubbles, assist_summary = _apply_semantic_bubble_titles(root, list(bubble_lookup.values()))
    bubble_lookup = {row["bubble_id"]: row for row in assisted_bubbles}

    profiling_summary = {
        "enabled": profile,
        "seed_checks": seed_checks,
        "seed_stage_seconds": seed_stage_seconds,
        "related_record_checks": attachment_stats["attachment_checks"],
        "related_records_attached": attachment_stats["attached_count"],
        "related_stage_seconds": related_stage_seconds,
        "merge_stage_seconds": merge_stage_seconds,
        "states_before_merge": merge_states_before,
        "states_after_merge": merge_states_after,
        "prune_stage_seconds": prune_stage_seconds,
        "edge_stage_seconds": edge_stage_seconds,
        "edge_pair_checks": edge_pair_checks,
        "states_before_prune": pruned_before,
        "states_after_prune": len(states),
        "semantic_bubble_assist": assist_summary,
    }
    write_jsonl(_bubbles_path(root), list(bubble_lookup.values()))
    write_jsonl(_memberships_path(root), memberships)
    write_jsonl(_edges_path(root), edges)
    write_jsonl(_transitions_path(root), sorted(transitions, key=lambda item: (item["bubble_id"], item["action"], item["transition_id"])))
    _write_progress(
        root,
        status="completed",
        phase="completed",
        meta_row_count=len(meta_rows),
        seed_count=len(seeds),
        states_count=len(states),
        processed_count=len(meta_rows),
        total_count=len(meta_rows),
        seed_checks=seed_checks,
        attachment_checks=attachment_stats["attachment_checks"],
        attached_count=attachment_stats["attached_count"],
        profiling=profiling_summary,
    )
    return {
        "seed_count": len(seeds),
        "bubble_count": len(bubble_lookup),
        "membership_count": len(memberships),
        "edge_count": len(edges),
        "transition_count": len(transitions),
        "profiling": profiling_summary,
    }


def list_context_bubbles(root: Path, limit: int = 12) -> Dict:
    bubbles = load_context_bubbles(root)
    rows = [
        {
            "bubble_id": row["bubble_id"],
            "label": row["label"],
            "status": row["status"],
            "confidence": row["confidence"],
            "support_count": row["support_count"],
            "dominant_primitives": row.get("dominant_primitives", []),
            "active_tension_count": len(row.get("active_tensions", [])),
            "open_question_count": len(row.get("open_questions", [])),
        }
        for row in bubbles[:limit]
    ]
    return {"count": len(bubbles), "bubbles": rows}


def get_context_bubble(root: Path, bubble_id: str) -> Dict:
    bubbles = {row["bubble_id"]: row for row in load_context_bubbles(root)}
    bubble = bubbles.get(bubble_id)
    if bubble is None:
        raise KeyError(bubble_id)
    meta_lookup = {row["meta_id"]: row for row in load_meta_records(root)}
    memberships = [row for row in load_bubble_memberships(root) if row["bubble_id"] == bubble_id]
    edges = [
        row
        for row in load_bubble_edges(root)
        if row["from_bubble_id"] == bubble_id or row["to_bubble_id"] == bubble_id
    ]
    transitions = [row for row in load_bubble_transitions(root) if row["bubble_id"] == bubble_id]
    supporting_thoughts = []
    for row in read_jsonl(_data_dir(root) / "thought_packets.jsonl"):
        if row.get("primary_bubble_id") == bubble_id or bubble_id in row.get("related_bubble_ids", []):
            supporting_thoughts.append(
                {
                    "thought_id": row["thought_id"],
                    "title": row["title"],
                    "confidence_score": row["confidence_score"],
                }
            )
    chunk_lookup = {row["chunk_id"]: row for row in load_chunk_index(root)}
    source_lookup = {row["source_ref"]: row for row in load_source_registry(root)}
    chunk_rows = []
    for membership in memberships:
        meta = meta_lookup.get(membership["meta_id"]) or {}
        for chunk_id in meta.get("chunk_ids", []):
            row = chunk_lookup.get(chunk_id)
            if row and row not in chunk_rows:
                chunk_rows.append(row)
    source_packets = []
    grouped_sources: Dict[str, List[Dict]] = defaultdict(list)
    for row in chunk_rows:
        grouped_sources[row["source_ref"]].append(row)
    for source_ref in sorted(grouped_sources):
        source_rows = sorted(grouped_sources[source_ref], key=lambda item: (item.get("chunk_index", 0), item["chunk_id"]))
        source_entry = source_lookup.get(source_ref, {})
        source_packets.append(
            {
                "source_ref": source_ref,
                "title": source_entry.get("title", Path(source_ref).name),
                "source_type": source_entry.get("source_type", source_rows[0].get("source_type", "unknown")),
                "source_family": source_entry.get("source_family", source_rows[0].get("source_family", "unknown")),
                "chunk_count": len(source_rows),
                "chunk_excerpts": [
                    {
                        "chunk_id": row["chunk_id"],
                        "title": row["title"],
                        "content_kind": row.get("content_kind", ""),
                        "excerpt": shorten(row["content"], 220),
                    }
                    for row in source_rows[:8]
                ],
            }
        )
    related_concepts = []
    concept_lookup = {row["concept_id"]: row for row in load_concept_nodes(root)}
    for concept_id in bubble.get("concept_ids", []):
        if concept_id in concept_lookup:
            related_concepts.append(concept_lookup[concept_id])
    return {
        "bubble": bubble,
        "memberships": [
            membership | {"meta": meta_lookup.get(membership["meta_id"])}
            for membership in memberships
        ],
        "edges": edges,
        "transitions": transitions,
        "supporting_thoughts": supporting_thoughts[:12],
        "provenance": {
            "source_count": len(source_packets),
            "chunk_count": len(chunk_rows),
            "source_packets": source_packets,
            "related_concepts": related_concepts,
        },
    }
