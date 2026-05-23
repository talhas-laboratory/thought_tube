from __future__ import annotations

import hashlib
from collections import defaultdict
from time import perf_counter
from pathlib import Path
from typing import Dict, List, Set

from .conversation_deltas import build_conversation_deltas, load_user_expectations
from .conversation_threads import build_conversation_threads, load_conversation_threads
from .meta_layer import load_meta_records
from .models import ProjectLens, ThreadAbstraction, ThreadAbstractionLink
from .storage import ensure_dir, read_json, read_jsonl, slugify, write_json, write_jsonl
from .vault_ingest import tokenize


MODULE_ID = "kernel.analysis.thread_abstractions"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "load_project_lenses",
    "load_thread_abstractions",
    "load_thread_abstraction_links",
    "build_thread_abstractions",
)
__all__ = list(PUBLIC_API)


DEFAULT_PROJECT_LENSES = [
    {
        "lens_key": "interaction_model",
        "label": "Interaction Model",
        "thesis_hint": "How the system should reveal, structure, and navigate thought over time.",
        "keywords": ["interface", "fragment", "article", "chat", "feed", "twitter", "substack", "entry", "depth", "surface", "interaction", "reveal"],
    },
    {
        "lens_key": "cognitive_fidelity",
        "label": "Cognitive Fidelity",
        "thesis_hint": "How the system preserves ambiguity, signal texture, and non-flattened thought.",
        "keywords": ["ambiguity", "fidelity", "preserve", "structure", "flattening", "signal", "texture", "survive", "literal", "thought"],
    },
    {
        "lens_key": "context_bubble_organization",
        "label": "Context Bubble Organization",
        "thesis_hint": "How fragments and signals should cluster into larger coherent wholes.",
        "keywords": ["bubble", "puzzle", "cluster", "organize", "context", "whole", "pressure", "group", "cohere"],
    },
    {
        "lens_key": "reasoning_routing",
        "label": "Reasoning Routing",
        "thesis_hint": "How material should route across reasoning paths, branches, or domain overlays.",
        "keywords": ["route", "routing", "pipeline", "reasoning", "domain", "worker", "branch", "mechanism", "flow"],
    },
    {
        "lens_key": "user_model_and_taste",
        "label": "User Model And Taste",
        "thesis_hint": "How the system models preference, judgment, style, and personal reasoning tendencies.",
        "keywords": ["taste", "preference", "judgment", "user", "style", "model", "pattern", "behavior", "alignment"],
    },
    {
        "lens_key": "interface_expression",
        "label": "Interface Expression",
        "thesis_hint": "How visual, compositional, and expressive design choices should feel.",
        "keywords": ["color", "palette", "composition", "visual", "illustration", "design", "layout", "typography", "expression", "style"],
    },
    {
        "lens_key": "answer_shape_governance",
        "label": "Answer Shape Governance",
        "thesis_hint": "How answers should be framed, constrained, and shaped to match user expectations.",
        "keywords": ["literal", "precise", "concise", "short", "answer", "language", "direct", "step", "true", "speak", "shape"],
    },
    {
        "lens_key": "emergent_misc",
        "label": "Emergent Misc",
        "thesis_hint": "Material that does not yet fit a stable project lens but may still matter later.",
        "keywords": [],
    },
]


def _data_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data"


def _config_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config"


def _project_lenses_path(root: Path) -> Path:
    return _config_dir(root) / "project_lenses.json"


def _thread_abstractions_path(root: Path) -> Path:
    return _data_dir(root) / "thread_abstractions.jsonl"


def _thread_abstraction_links_path(root: Path) -> Path:
    return _data_dir(root) / "thread_abstraction_links.jsonl"


def load_project_lenses(root: Path) -> List[Dict]:
    path = _project_lenses_path(root)
    payload = read_json(path)
    if payload is None:
        ensure_dir(path.parent)
        write_json(path, DEFAULT_PROJECT_LENSES)
        payload = DEFAULT_PROJECT_LENSES
    return payload


def load_thread_abstractions(root: Path) -> List[Dict]:
    return read_jsonl(_thread_abstractions_path(root))


def load_thread_abstraction_links(root: Path) -> List[Dict]:
    return read_jsonl(_thread_abstraction_links_path(root))


def _digest(prefix: str, *parts: str) -> str:
    payload = "::".join(parts).encode("utf-8")
    return f"{prefix}-{hashlib.sha256(payload).hexdigest()[:12]}"


def _doc_tokens(path: Path) -> Set[str]:
    if not path.exists():
        return set()
    return set(tokenize(path.read_text(encoding="utf-8")))  # type: ignore[arg-type]


def _answer_shape_constraints(tokens: Set[str]) -> List[str]:
    constraints = []
    if {"literal", "define", "direct"} & tokens:
        constraints.append("prefer_literal_definition")
    if {"precise", "exact", "palette", "composition", "style"} & tokens:
        constraints.append("require_operational_specificity")
    if {"short", "concise", "true", "step"} & tokens:
        constraints.append("short_concise_true")
    if {"twitter", "substack", "contrast", "interface"} & tokens:
        constraints.append("preserve_specific_contrast")
    return constraints


def _meta_by_id(root: Path) -> Dict[str, Dict]:
    return {row["meta_id"]: row for row in load_meta_records(root)}


def _collect_thread_meta(meta_rows: List[Dict], user_chunk_ids: List[str], context_chunk_ids: List[str]) -> tuple[List[Dict], List[Dict]]:
    line_meta = []
    context_meta = []
    user_chunks = set(user_chunk_ids)
    context_chunks = set(context_chunk_ids)
    for row in meta_rows:
        role = row.get("attributes", {}).get("semantic_role")
        chunk_ids = set(row.get("chunk_ids", []))
        if role == "semantic_line" and chunk_ids & user_chunks:
            line_meta.append(row)
        elif role == "approved_context" and chunk_ids & context_chunks:
            context_meta.append(row)
    return line_meta, context_meta


def _expectations_by_intent(root: Path) -> Dict[str, List[Dict]]:
    grouped: Dict[str, List[Dict]] = defaultdict(list)
    for row in load_user_expectations(root):
        grouped[row["intent_key"]].append(row)
    return grouped


def _thread_descriptor(thread: Dict, meta_rows: List[Dict], expectations_by_intent: Dict[str, List[Dict]], lenses: List[Dict], thesis_tokens: Set[str], corpus_tokens: Set[str]) -> Dict:
    line_meta, context_meta = _collect_thread_meta(meta_rows, thread.get("user_chunk_ids", []), thread.get("approved_context_chunk_ids", []))
    line_tokens = {token for row in line_meta for token in row.get("attributes", {}).get("tokens", [])}
    context_tokens = {token for row in context_meta for token in row.get("attributes", {}).get("tokens", [])}
    delta_intents = set(thread.get("delta_intent_keys", []))
    expectation_rows = [row for intent in delta_intents for row in expectations_by_intent.get(intent, [])]
    expectation_tokens = {token for row in expectation_rows for token in row.get("user_priority_tokens", [])}
    tension_terms = [
        row["summary"]
        for row in line_meta
        if row["kind"] in {"tension", "contradiction"}
    ]
    source_tokens = set(thread.get("topic_signature", [])) | line_tokens | context_tokens | expectation_tokens
    project_anchor_tokens = thesis_tokens | corpus_tokens
    lens_scores = []
    for lens in lenses:
        if lens["lens_key"] == "emergent_misc":
            continue
        lens_tokens = set(lens.get("keywords", []))
        keyword_overlap = len(source_tokens & lens_tokens)
        expectation_overlap = len(expectation_tokens & lens_tokens)
        delta_overlap = len({token for intent in delta_intents for token in tokenize(intent)} & lens_tokens)
        project_overlap = len((source_tokens & lens_tokens) & project_anchor_tokens)
        score = keyword_overlap * 2 + expectation_overlap * 2 + delta_overlap + project_overlap
        lens_scores.append((score, lens))
    lens_scores.sort(key=lambda item: (-item[0], item[1]["lens_key"]))
    primary = lens_scores[0][1] if lens_scores and lens_scores[0][0] >= 2 else next(lens for lens in lenses if lens["lens_key"] == "emergent_misc")
    secondary = [lens["lens_key"] for score, lens in lens_scores[1:3] if score >= 2]
    tokens_for_constraints = source_tokens | {token for term in tension_terms for token in tokenize(term)}
    return {
        "thread": thread,
        "line_meta": line_meta,
        "context_meta": context_meta,
        "line_meta_ids": [row["meta_id"] for row in line_meta],
        "context_meta_ids": [row["meta_id"] for row in context_meta],
        "context_meta_id_set": {row["meta_id"] for row in context_meta},
        "tokens": source_tokens,
        "expectations": expectation_rows,
        "tensions": tension_terms,
        "primary_lens": primary,
        "secondary_lens_keys": secondary,
        "answer_shape_constraints": _answer_shape_constraints(tokens_for_constraints),
        "intent_keys_set": delta_intents,
        "source_ref_set": set(thread.get("source_refs", [])),
    }


def _descriptors_should_merge(left: Dict, right: Dict) -> bool:
    if left["primary_lens"]["lens_key"] != right["primary_lens"]["lens_key"]:
        return False
    shared_intents = left["intent_keys_set"] & right["intent_keys_set"]
    shared_tokens = left["tokens"] & right["tokens"]
    shared_context = left["context_meta_id_set"] & right["context_meta_id_set"]
    shared_sources = left["source_ref_set"] & right["source_ref_set"]
    if left["tensions"] and right["tensions"] and not (set(left["tensions"]) & set(right["tensions"])) and len(shared_tokens) < 2 and not shared_intents:
        return False
    if shared_intents or len(shared_tokens) >= 3 or shared_context:
        return True
    if shared_sources and left["primary_lens"]["lens_key"] != "emergent_misc":
        # Raw thread traces are intentionally fine-grained. Collapse same-source,
        # same-lens traces upward unless they carry clearly distinct pressures.
        if not left["tensions"] and not right["tensions"]:
            return True
        if len(shared_tokens) >= 1:
            return True
    return False


def _merge_group(group: List[Dict], lenses_by_key: Dict[str, Dict]) -> Dict:
    primary = group[0]["primary_lens"]
    child_threads = [item["thread"]["thread_id"] for item in group]
    source_refs = sorted({source_ref for item in group for source_ref in item["thread"].get("source_refs", [])})
    delta_intent_keys = sorted({intent for item in group for intent in item["thread"].get("delta_intent_keys", [])})
    line_meta_ids = sorted({meta_id for item in group for meta_id in item["line_meta_ids"]})
    context_meta_ids = sorted({meta_id for item in group for meta_id in item["context_meta_ids"]})
    expectations = sorted({row["expectation_id"] for item in group for row in item["expectations"]})
    tensions = sorted({term for item in group for term in item["tensions"]})[:6]
    constraints = sorted({value for item in group for value in item["answer_shape_constraints"]})
    secondary = sorted({key for item in group for key in item["secondary_lens_keys"] if key != primary["lens_key"]})[:2]
    project_keys = [primary["lens_key"]] + [key for key in secondary if key != primary["lens_key"]]
    label = primary["label"]
    if primary["lens_key"] == "emergent_misc":
        candidate_labels = [row["label"] for item in group for row in item["line_meta"] if row["kind"] in {"theme", "shared_primitive", "signal_frame"}]
        label = candidate_labels[0] if candidate_labels else "Emergent Misc"
    thesis = primary["thesis_hint"]
    if tensions:
        thesis = f"{primary['thesis_hint']} Active pressure: {tensions[0]}"
    resolution_state = "resolved" if context_meta_ids else ("active" if delta_intent_keys else "open")
    confidence = round(min(0.95, 0.58 + len(child_threads) * 0.06 + len(delta_intent_keys) * 0.04), 2)
    return ThreadAbstraction(
        abstract_thread_id=_digest("abstract-thread", primary["lens_key"], *child_threads),
        label=label,
        primary_lens_key=primary["lens_key"],
        secondary_lens_keys=secondary,
        thesis=thesis,
        child_thread_ids=child_threads,
        source_refs=source_refs,
        delta_intent_keys=delta_intent_keys,
        dominant_tensions=tensions,
        answer_shape_constraints=constraints,
        approved_context_meta_ids=context_meta_ids,
        expectation_ids=expectations,
        resolution_state=resolution_state,
        confidence=confidence,
        semantic_line_meta_ids=line_meta_ids,
        project_lens_keys=project_keys,
    ).to_dict()


def build_thread_abstractions(
    root: Path,
    domain_overlays: List[str] | None = None,
    ensure_dependencies: bool = True,
    profile: bool = False,
) -> Dict:
    del domain_overlays
    ensure_dir(_data_dir(root))
    if ensure_dependencies:
        build_conversation_threads(root)
        build_conversation_deltas(root)

    lenses = load_project_lenses(root)
    lenses_by_key = {row["lens_key"]: row for row in lenses}
    thesis_tokens = _doc_tokens(root / "PRODUCT_THESIS.md")
    corpus_tokens = _doc_tokens(root / "docs" / "research" / "conversation-corpus-2026-04-17" / "README.md")
    threads = load_conversation_threads(root)
    meta_rows = load_meta_records(root)
    expectations_by_intent = _expectations_by_intent(root)

    descriptor_started = perf_counter()
    descriptors = [
        _thread_descriptor(thread, meta_rows, expectations_by_intent, lenses, thesis_tokens, corpus_tokens)
        for thread in threads
    ]
    descriptor_duration = round(perf_counter() - descriptor_started, 3)
    groups: List[List[Dict]] = []
    groups_by_lens: Dict[str, List[List[Dict]]] = defaultdict(list)
    merge_candidate_groups = 0
    merge_checks = 0
    grouping_started = perf_counter()
    for descriptor in descriptors:
        target = None
        lens_key = descriptor["primary_lens"]["lens_key"]
        lens_groups = groups_by_lens[lens_key]
        merge_candidate_groups += len(lens_groups)
        for group in lens_groups:
            merge_checks += len(group)
            if any(_descriptors_should_merge(descriptor, existing) for existing in group):
                target = group
                break
        if target is None:
            target = [descriptor]
            groups.append(target)
            lens_groups.append(target)
        else:
            target.append(descriptor)
    grouping_duration = round(perf_counter() - grouping_started, 3)

    abstractions = [_merge_group(group, lenses_by_key) for group in groups]
    links: List[Dict] = []
    for abstraction in abstractions:
        for thread_id in abstraction["child_thread_ids"]:
            links.append(
                ThreadAbstractionLink(
                    link_id=_digest("thread-abstraction-link", "abstracts_to", thread_id, abstraction["abstract_thread_id"]),
                    kind="abstracts_to",
                    from_id=thread_id,
                    to_id=abstraction["abstract_thread_id"],
                    confidence=abstraction["confidence"],
                    evidence_refs=abstraction["source_refs"],
                ).to_dict()
            )
        links.append(
            ThreadAbstractionLink(
                link_id=_digest("thread-abstraction-link", "aligned_to_lens", abstraction["abstract_thread_id"], abstraction["primary_lens_key"]),
                kind="aligned_to_lens",
                from_id=abstraction["abstract_thread_id"],
                to_id=abstraction["primary_lens_key"],
                confidence=abstraction["confidence"],
                evidence_refs=abstraction["source_refs"],
                attributes={"secondary_lens_keys": abstraction.get("secondary_lens_keys", [])},
            ).to_dict()
        )

    ordered_abstractions = sorted(abstractions, key=lambda item: (item["primary_lens_key"], item["label"], item["abstract_thread_id"]))
    ordered_links = sorted(links, key=lambda item: (item["kind"], item["link_id"]))
    write_jsonl(_thread_abstractions_path(root), ordered_abstractions)
    write_jsonl(_thread_abstraction_links_path(root), ordered_links)
    return {
        "raw_thread_count": len(threads),
        "descriptor_count": len(descriptors),
        "abstract_thread_count": len(ordered_abstractions),
        "link_count": len(ordered_links),
        "project_lens_count": len(lenses),
        "profiling": {
            "enabled": profile,
            "descriptor_build_seconds": descriptor_duration,
            "grouping_seconds": grouping_duration,
            "merge_candidate_groups": merge_candidate_groups,
            "merge_checks": merge_checks,
        },
    }
