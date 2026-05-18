from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from .storage import read_jsonl, write_jsonl
from .vault_ingest import load_chunk_index, tokenize


STOPWORDS = {
    "about",
    "again",
    "answer",
    "assistant",
    "because",
    "build",
    "clear",
    "good",
    "just",
    "like",
    "need",
    "please",
    "reply",
    "should",
    "system",
    "that",
    "then",
    "this",
    "user",
    "want",
    "with",
}

CORRECTION_MARKERS = {"no", "wrong", "missed", "instead", "literal", "directly"}
INSTRUCTION_MARKERS = {"answer", "speak", "use", "short", "shorter", "precise", "specific", "literal", "directly", "concise"}
VALIDATION_MARKERS = {"yes", "good", "correct", "right", "exactly", "closer", "okay"}
DEEPER_MARKERS = {"how", "apply", "practice", "connect", "example", "deeper", "specifically", "what"}
CLARIFICATION_MARKERS = {"clarify", "mean", "exactly", "sense", "define"}
REFERENTIAL_MARKERS = {"they", "them", "that", "those", "these", "it"}


def _normalize_token(token: str) -> str:
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed"):
        return token[:-2]
    if len(token) > 4 and token.endswith("es"):
        return token[:-2]
    if len(token) > 4 and token.endswith("s"):
        return token[:-1]
    if len(token) > 5 and token.endswith("e"):
        return token[:-1]
    return token


def _data_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data"


def _deltas_path(root: Path) -> Path:
    return _data_dir(root) / "conversation_deltas.jsonl"


def _expectations_path(root: Path) -> Path:
    return _data_dir(root) / "user_expectations.jsonl"


def load_conversation_deltas(root: Path) -> List[Dict]:
    return read_jsonl(_deltas_path(root))


def load_user_expectations(root: Path) -> List[Dict]:
    return read_jsonl(_expectations_path(root))


def _speaker_role(row: Dict) -> str:
    return row.get("speaker_role") or row.get("metadata", {}).get("speaker_role") or ""


def _meaningful_tokens(text: str) -> List[str]:
    tokens = []
    for token in tokenize(text):
        normalized = _normalize_token(token)
        if normalized in STOPWORDS:
            continue
        tokens.append(normalized)
    return tokens


def _intent_tokens(row: Dict) -> List[str]:
    return _meaningful_tokens(row.get("content", ""))[:12]


def _assistant_tokens(row: Dict) -> List[str]:
    return _meaningful_tokens(row.get("content", ""))[:16]


def _intent_overlap(left: Dict, right: Dict) -> List[str]:
    return sorted(set(_intent_tokens(left)) & set(_intent_tokens(right)))


def _intent_key(source_ref: str, overlap_tokens: List[str]) -> str:
    seed = "::".join([source_ref, "|".join(overlap_tokens[:6])]).encode("utf-8")
    return f"intent-{hashlib.sha256(seed).hexdigest()[:12]}"


def _delta_id(source_ref: str, initial_id: str, repeated_id: str) -> str:
    seed = "::".join([source_ref, initial_id, repeated_id]).encode("utf-8")
    return f"delta-{hashlib.sha256(seed).hexdigest()[:12]}"


def _next_user_after(rows: List[Dict], chunk_index: int) -> Dict | None:
    return next(
        (row for row in rows if row["chunk_index"] > chunk_index and _speaker_role(row) == "user"),
        None,
    )


def _focus_label(question_overlap: int, answer_overlap: int, follow_up_tokens: set[str], text: str) -> str:
    lower = text.lower()
    if question_overlap == 0 and answer_overlap == 0:
        if (
            (VALIDATION_MARKERS & follow_up_tokens)
            or (REFERENTIAL_MARKERS & follow_up_tokens)
            or any(phrase in lower for phrase in ["how do they", "how does it", "how would that", "in practice", "good. how", "yes. how"])
        ) and ("?" in text or DEEPER_MARKERS & follow_up_tokens or any(phrase in lower for phrase in ["in practice", "how do", "how does", "how would"])):
            return "answer_line"
        return "new_branch"
    if answer_overlap > question_overlap:
        return "answer_line"
    if question_overlap > answer_overlap:
        return "question_line"
    if answer_overlap and ("?" in text or {"good", "yes", "okay"} & follow_up_tokens or DEEPER_MARKERS & follow_up_tokens):
        return "answer_line"
    if question_overlap and CORRECTION_MARKERS & follow_up_tokens:
        return "question_line"
    if "?" in lower and answer_overlap:
        return "answer_line"
    return "mixed"


def _follow_up_kind(focus: str, follow_up_tokens: set[str], text: str) -> str:
    lower = text.lower()
    if focus == "new_branch":
        return "branch_switch"
    if CORRECTION_MARKERS & follow_up_tokens or lower.startswith("no"):
        return "correction"
    if INSTRUCTION_MARKERS & follow_up_tokens and focus in {"question_line", "mixed"}:
        return "instruction_shift"
    if {"good", "yes", "okay", "closer"} & follow_up_tokens and "?" not in text:
        return "validation"
    if "?" in text:
        if DEEPER_MARKERS & follow_up_tokens or any(phrase in lower for phrase in ["in practice", "what would", "how do"]):
            return "deeper_specificity"
        if CLARIFICATION_MARKERS & follow_up_tokens:
            return "clarification"
        if focus == "answer_line":
            return "clarification"
    if {"good", "yes", "okay", "closer"} & follow_up_tokens:
        return "validation"
    if focus == "answer_line":
        return "deeper_specificity"
    return "instruction_shift"


def _relevance_score(kind: str, focus: str) -> float:
    base = {
        "correction": 0.18,
        "instruction_shift": 0.28,
        "branch_switch": 0.45,
        "clarification": 0.72,
        "validation": 0.82,
        "deeper_specificity": 0.84,
    }.get(kind, 0.5)
    base += {
        "answer_line": 0.04,
        "mixed": 0.0,
        "question_line": -0.04,
        "new_branch": 0.0,
    }.get(focus, 0.0)
    return round(max(0.05, min(0.95, base)), 2)


def _relevance_label(score: float) -> str:
    if score >= 0.72:
        return "high"
    if score >= 0.45:
        return "partial"
    return "low"


def _analyze_follow_up(previous_user: Dict, assistant: Dict, next_user: Dict | None) -> Dict:
    if next_user is None:
        return {
            "follow_up_user_chunk_id": "",
            "follow_up_focus": "terminal",
            "follow_up_kind": "terminal",
            "relevance_score": 0.6,
            "relevance_label": "partial",
        }
    question_tokens = set(_intent_tokens(previous_user))
    answer_tokens = set(_assistant_tokens(assistant))
    follow_up_tokens = set(_intent_tokens(next_user))
    question_overlap = len(follow_up_tokens & question_tokens)
    answer_overlap = len(follow_up_tokens & answer_tokens)
    text = next_user.get("content", "")
    focus = _focus_label(question_overlap, answer_overlap, follow_up_tokens, text)
    kind = _follow_up_kind(focus, follow_up_tokens, text)
    score = _relevance_score(kind, focus)
    return {
        "follow_up_user_chunk_id": next_user["chunk_id"],
        "follow_up_focus": focus,
        "follow_up_kind": kind,
        "relevance_score": score,
        "relevance_label": _relevance_label(score),
    }


def build_conversation_deltas(root: Path) -> Dict:
    chunks = sorted(
        [row for row in load_chunk_index(root) if _speaker_role(row)],
        key=lambda row: (row["source_ref"], row["chunk_index"]),
    )
    by_source: Dict[str, List[Dict]] = defaultdict(list)
    for row in chunks:
        by_source[row["source_ref"]].append(row)

    deltas: List[Dict] = []
    expectations: Dict[str, Dict] = {}
    seen_pairs: set[tuple[str, str, str]] = set()

    for source_ref, rows in by_source.items():
        user_rows = [row for row in rows if _speaker_role(row) == "user"]
        for index, initial in enumerate(user_rows):
            for repeated in user_rows[index + 1 : index + 4]:
                overlap_tokens = _intent_overlap(initial, repeated)
                if len(overlap_tokens) < 2:
                    continue
                pair_key = (source_ref, initial["chunk_id"], repeated["chunk_id"])
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)
                between = [
                    row for row in rows
                    if initial["chunk_index"] < row["chunk_index"] < repeated["chunk_index"]
                ]
                unsatisfying = [row for row in between if _speaker_role(row) == "assistant"]
                if not unsatisfying:
                    continue
                after = [row for row in rows if row["chunk_index"] > repeated["chunk_index"]]
                resolved = next((row for row in after if _speaker_role(row) == "assistant"), None)
                last_unsatisfying = unsatisfying[-1]
                unsatisfying_follow_up = _analyze_follow_up(initial, last_unsatisfying, repeated)
                resolved_follow_up = _analyze_follow_up(repeated, resolved, _next_user_after(rows, resolved["chunk_index"])) if resolved else {
                    "follow_up_user_chunk_id": "",
                    "follow_up_focus": "open",
                    "follow_up_kind": "open",
                    "relevance_score": 0.5,
                    "relevance_label": "partial",
                }
                delta = {
                    "delta_id": _delta_id(source_ref, initial["chunk_id"], repeated["chunk_id"]),
                    "source_ref": source_ref,
                    "intent_key": _intent_key(source_ref, overlap_tokens),
                    "initial_user_chunk_id": initial["chunk_id"],
                    "repeated_user_chunk_id": repeated["chunk_id"],
                    "unsatisfying_assistant_chunk_ids": [row["chunk_id"] for row in unsatisfying],
                    "resolved_assistant_chunk_id": resolved["chunk_id"] if resolved else "",
                    "overlap_tokens": overlap_tokens,
                    "user_priority_tokens": sorted(set(_intent_tokens(repeated) + [token for token in _intent_tokens(repeated) if token not in _intent_tokens(initial)]))[:12],
                    "unsatisfying_follow_up_user_chunk_id": unsatisfying_follow_up["follow_up_user_chunk_id"],
                    "unsatisfying_follow_up_focus": unsatisfying_follow_up["follow_up_focus"],
                    "unsatisfying_follow_up_kind": unsatisfying_follow_up["follow_up_kind"],
                    "unsatisfying_relevance_score": unsatisfying_follow_up["relevance_score"],
                    "unsatisfying_relevance_label": unsatisfying_follow_up["relevance_label"],
                    "resolved_follow_up_user_chunk_id": resolved_follow_up["follow_up_user_chunk_id"],
                    "resolved_follow_up_focus": resolved_follow_up["follow_up_focus"],
                    "resolved_follow_up_kind": resolved_follow_up["follow_up_kind"],
                    "resolved_relevance_score": resolved_follow_up["relevance_score"],
                    "resolved_relevance_label": resolved_follow_up["relevance_label"],
                    "status": "resolved" if resolved else "open",
                }
                deltas.append(delta)
                expectation = expectations.setdefault(
                    delta["intent_key"],
                    {
                        "expectation_id": delta["intent_key"].replace("intent", "expectation", 1),
                        "source_ref": source_ref,
                        "intent_key": delta["intent_key"],
                        "user_priority_tokens": [],
                        "rejected_answer_tokens": [],
                        "preferred_answer_tokens": [],
                        "rejected_follow_up_kinds": [],
                        "preferred_follow_up_kinds": [],
                        "rejected_follow_up_focuses": [],
                        "preferred_follow_up_focuses": [],
                        "conversation_dynamics": {},
                        "delta_ids": [],
                    },
                )
                expectation["user_priority_tokens"] = sorted(
                    set(expectation["user_priority_tokens"]) | set(delta["user_priority_tokens"])
                )[:16]
                rejected_tokens = set()
                for row in unsatisfying:
                    rejected_tokens.update(_assistant_tokens(row))
                preferred_tokens = set(_assistant_tokens(resolved)) if resolved else set()
                expectation["rejected_answer_tokens"] = sorted(
                    set(expectation["rejected_answer_tokens"]) | rejected_tokens
                )[:20]
                expectation["preferred_answer_tokens"] = sorted(
                    set(expectation["preferred_answer_tokens"]) | preferred_tokens
                )[:20]
                expectation["rejected_follow_up_kinds"] = sorted(
                    set(expectation["rejected_follow_up_kinds"]) | {delta["unsatisfying_follow_up_kind"]}
                )
                expectation["preferred_follow_up_kinds"] = sorted(
                    set(expectation["preferred_follow_up_kinds"]) | ({delta["resolved_follow_up_kind"]} if resolved else set())
                )
                expectation["rejected_follow_up_focuses"] = sorted(
                    set(expectation["rejected_follow_up_focuses"]) | {delta["unsatisfying_follow_up_focus"]}
                )
                expectation["preferred_follow_up_focuses"] = sorted(
                    set(expectation["preferred_follow_up_focuses"]) | ({delta["resolved_follow_up_focus"]} if resolved else set())
                )
                dynamics = dict(expectation["conversation_dynamics"])
                dynamics[delta["unsatisfying_follow_up_kind"]] = dynamics.get(delta["unsatisfying_follow_up_kind"], 0) + 1
                if resolved:
                    dynamics[delta["resolved_follow_up_kind"]] = dynamics.get(delta["resolved_follow_up_kind"], 0) + 1
                expectation["conversation_dynamics"] = dynamics
                expectation["delta_ids"].append(delta["delta_id"])

    ordered_deltas = sorted(deltas, key=lambda item: (item["source_ref"], item["delta_id"]))
    ordered_expectations = sorted(expectations.values(), key=lambda item: (item["source_ref"], item["intent_key"]))
    write_jsonl(_deltas_path(root), ordered_deltas)
    write_jsonl(_expectations_path(root), ordered_expectations)
    return {
        "source_count": len(by_source),
        "delta_count": len(ordered_deltas),
        "expectation_count": len(ordered_expectations),
    }
