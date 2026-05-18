from __future__ import annotations

import re
from typing import Any, Dict, List


ROLE_ALIASES = {
    "human": "user",
    "agent": "assistant",
}

ROLE_PATTERN = r"(user|assistant|agent|human|system)"
TRANSLATION_KEYWORDS = {
    "architecture",
    "concept",
    "interface",
    "interfaces",
    "layer",
    "model",
    "module",
    "modules",
    "pattern",
    "policies",
    "policy",
    "product",
    "schema",
    "state",
    "system",
    "technical",
    "translate",
    "workflow",
    "workflows",
}

_REFERENCE_STOPWORDS = {
    "the",
    "and",
    "that",
    "this",
    "with",
    "from",
    "into",
    "what",
    "when",
    "does",
    "mean",
    "your",
    "have",
    "about",
    "would",
    "could",
    "should",
    "there",
    "their",
    "then",
    "them",
    "they",
    "just",
    "like",
    "because",
    "which",
    "where",
    "while",
    "after",
    "before",
    "more",
    "than",
    "over",
}


def _normalize_role(role: str) -> str:
    return ROLE_ALIASES.get(role.lower(), role.lower())


def _parse_prefixed_transcript(text: str) -> List[Dict[str, str]]:
    turns: List[Dict[str, str]] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        match = re.match(rf"^{ROLE_PATTERN}\s*:\s*(.+)$", line, flags=re.IGNORECASE)
        if match:
            turns.append({"role": _normalize_role(match.group(1)), "content": match.group(2).strip()})
            continue
        if turns:
            turns[-1]["content"] = f"{turns[-1]['content']} {line}".strip()
    return turns


def _parse_markdown_transcript(text: str) -> List[Dict[str, str]]:
    turns: List[Dict[str, str]] = []
    lines = text.splitlines()
    index = 0

    if lines and lines[0].strip() == "---":
        index = 1
        while index < len(lines) and lines[index].strip() != "---":
            index += 1
        if index < len(lines):
            index += 1

    current_role = ""
    buffer: List[str] = []

    def flush() -> None:
        nonlocal buffer
        content = "\n".join(buffer).strip()
        buffer = []
        if current_role and content:
            turns.append({"role": current_role, "content": content})

    for raw_line in lines[index:]:
        line = raw_line.strip()
        heading_match = re.match(rf"^#{{1,6}}\s*{ROLE_PATTERN}\s*$", line, flags=re.IGNORECASE)
        if heading_match:
            flush()
            current_role = _normalize_role(heading_match.group(1))
            continue
        if not current_role:
            continue
        if line == "---":
            continue
        buffer.append(raw_line.rstrip())

    flush()
    return turns


def parse_conversation_transcript(text: str) -> List[Dict[str, str]]:
    turns = _parse_markdown_transcript(text)
    if turns:
        return turns
    return _parse_prefixed_transcript(text)


def classify_user_question(question: str) -> str:
    lower = question.lower()
    if any(token in lower for token in ["example", "for instance", "concrete"]):
        return "example_request"
    if any(token in lower for token in ["how does", "how do", "becomes code", "implement", "modules", "interfaces"]):
        return "implementation_mapping"
    if any(token in lower for token in ["why", "why does"]):
        return "rationale"
    if any(token in lower for token in ["compare", "difference", "versus", "tradeoff"]):
        return "comparison"
    if any(token in lower for token in ["what", "define", "mean"]):
        return "definition"
    return "open_question"


def _derive_example_preferences(questions: List[str]) -> List[str]:
    preferences: List[str] = []
    combined = " ".join(question.lower() for question in questions)
    if "code example" in combined or ("code" in combined and "example" in combined):
        preferences.append("code_example")
    if "concrete example" in combined or "concrete" in combined or "real-world" in combined or "product example" in combined:
        preferences.append("concrete_example")
    if "analogy" in combined:
        preferences.append("analogy")
    return preferences or ["concrete_example"]


def _derive_followup_preferences(question_types: List[str]) -> List[str]:
    preferences: List[str] = []
    if "implementation_mapping" in question_types:
        preferences.append("technical_mapping")
    if "comparison" in question_types:
        preferences.append("tradeoff_framing")
    if "example_request" in question_types:
        preferences.append("example_then_explanation")
    return preferences or ["technical_mapping"]


def _derive_guiding_path(question_types: List[str]) -> str:
    if "definition" in question_types and "example_request" in question_types and "implementation_mapping" in question_types:
        return "pattern_to_example_to_implementation"
    if "example_request" in question_types and "implementation_mapping" in question_types:
        return "example_to_implementation"
    if "definition" in question_types and "comparison" in question_types:
        return "concept_to_tradeoff"
    return "pattern_to_example_to_implementation"


def _reference_terms(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z]{4,}", text.lower())
        if token not in _REFERENCE_STOPWORDS
    }


def _classify_followup_intents(user_turn: str) -> List[str]:
    lower = user_turn.lower()
    intents: List[str] = []
    if any(token in lower for token in ["do you mean", "what do you mean", "clarify", "when you say"]):
        intents.append("clarification")
    if any(token in lower for token in ["is that right", "correct", "so the idea is", "am i understanding"]):
        intents.append("validation")
    if any(token in lower for token in ["specifically", "which", "how exactly", "more about", "details"]):
        intents.append("deepen_specifics")
    if any(token in lower for token in ["instead", "different", "another way", "show me code", "use code", "give code"]):
        intents.append("different_instruction")
    if any(token in lower for token in ["going back", "my original question", "what i asked", "original question"]):
        intents.append("return_to_user_goal")
    return intents


def _analyze_followup_dynamics(turns: List[Dict[str, str]]) -> Dict[str, Any]:
    answer_reference_count = 0
    self_reference_count = 0
    intent_types: List[str] = []

    for index, turn in enumerate(turns):
        if turn["role"] != "user":
            continue
        previous_assistant = next((candidate for candidate in reversed(turns[:index]) if candidate["role"] == "assistant"), None)
        previous_user = next((candidate for candidate in reversed(turns[:index]) if candidate["role"] == "user"), None)
        if previous_assistant is None:
            continue

        user_lower = turn["content"].lower()
        assistant_terms = _reference_terms(previous_assistant["content"])
        user_terms = _reference_terms(turn["content"])
        previous_user_terms = _reference_terms(previous_user["content"]) if previous_user else set()

        answer_overlap = len(user_terms & assistant_terms)
        self_overlap = len(user_terms & previous_user_terms)

        if answer_overlap >= 2 or any(token in user_lower for token in ["you said", "when you say", "that means", "do you mean"]):
            answer_reference_count += 1
        if self_overlap >= 2 or any(token in user_lower for token in ["going back", "my original question", "what i asked", "original question"]):
            self_reference_count += 1

        intent_types.extend(_classify_followup_intents(turn["content"]))

    if answer_reference_count > 0 and self_reference_count > 0:
        answer_relevance_signal = "high"
    elif answer_reference_count > 0 or self_reference_count > 0:
        answer_relevance_signal = "medium"
    else:
        answer_relevance_signal = "low"

    return {
        "answer_reference_count": answer_reference_count,
        "self_reference_count": self_reference_count,
        "intent_types": sorted(set(intent_types)),
        "answer_relevance_signal": answer_relevance_signal,
    }


def analyze_conversation_turns(turns: List[Dict[str, str]]) -> Dict[str, Any]:
    user_turns = [turn["content"] for turn in turns if turn["role"] == "user"]
    question_turns = [
        turn
        for turn in user_turns
        if "?" in turn
        or turn.lower().startswith(("what", "how", "why", "can", "could", "show", "give", "map", "translate", "compare", "walk me through"))
        or any(token in turn.lower() for token in ["modules", "interfaces", "implementation", "becomes code"])
    ]
    question_types = [classify_user_question(question) for question in question_turns]
    followup_dynamics = _analyze_followup_dynamics(turns)
    user_combined = " ".join(user_turns).lower()
    translation_focus_terms = sorted({token for token in TRANSLATION_KEYWORDS if token in user_combined})

    concept_translation_signal = "low"
    if "implementation_mapping" in question_types or len(translation_focus_terms) >= 4:
        concept_translation_signal = "high"
    elif translation_focus_terms or "technical_mapping" in _derive_followup_preferences(question_types):
        concept_translation_signal = "medium"

    return {
        "user_question_count": len(question_turns),
        "question_path_types": question_types,
        "example_preferences": _derive_example_preferences(question_turns),
        "followup_preferences": _derive_followup_preferences(question_types),
        "guiding_path": _derive_guiding_path(question_types),
        "followup_dynamics": followup_dynamics,
        "answer_relevance_signal": followup_dynamics["answer_relevance_signal"],
        "concept_translation_signal": concept_translation_signal,
        "translation_focus_terms": translation_focus_terms[:8],
    }
