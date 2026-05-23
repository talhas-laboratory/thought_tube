from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path
from typing import Dict, List

from .conversation_learning import analyze_conversation_turns
from .models import MemoryCard, SessionManifest
from .storage import (
    cards_dir,
    indexes_dir,
    read_json,
    read_jsonl,
    session_dir,
    session_events_path,
    sorted_files,
    utc_now,
    write_json,
    write_markdown,
)


MODULE_ID = "kernel.analysis.session_analysis"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "materialize_transcript",
    "analyze_session",
    "materialize_cards",
    "refresh_indexes",
    "update_manifest",
)
__all__ = list(PUBLIC_API)


DECISION_HINTS = {
    "default_output": "Morning Batch is the default delivery mode.",
    "storage_shape": "Markdown and JSONL are canonical source of truth.",
    "trust_mode": "Default trust mode is conservative, grounded, and inspectable.",
    "scope_boundary": "Domain specialization happens through plugins instead of core branching.",
}


OPEN_QUESTION_HINTS = [
    "How should attention budget thresholds change by task type?",
    "Which plugin heuristics should become product-default versus optional overlays?",
    "What is the minimum evidence threshold for a grounded insight candidate?",
]


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _event_lines(events: List[Dict]) -> List[str]:
    lines: List[str] = []
    for event in events:
        lines.append(f"### {event['actor']} · {event['kind']} · {event['timestamp']}")
        lines.append("")
        lines.append(event["content"].strip())
        lines.append("")
    return lines


def _role_for_event(event: Dict) -> str:
    actor = str(event.get("actor", "")).lower()
    if actor in {"user", "assistant", "system"}:
        return actor
    return ""


def _conversation_turns(events: List[Dict]) -> List[Dict[str, str]]:
    turns: List[Dict[str, str]] = []
    for event in events:
        role = _role_for_event(event)
        if role and event.get("content", "").strip():
            turns.append({"role": role, "content": event["content"].strip()})
    return turns


def _session_summary(domains: List[str], turns: List[Dict[str, str]], conversation_analysis: Dict[str, object] | None) -> str:
    if not turns:
        return (
            "Conversation OS session covering "
            + (", ".join(domains) if domains else "general project work")
            + " with append-only events and derived artifacts."
        )
    user_turn_count = sum(1 for turn in turns if turn["role"] == "user")
    assistant_turn_count = sum(1 for turn in turns if turn["role"] == "assistant")
    summary = (
        "Conversation OS session covering "
        + (", ".join(domains) if domains else "general project work")
        + f" with {user_turn_count} user turns and {assistant_turn_count} assistant turns."
    )
    if conversation_analysis and conversation_analysis.get("question_path_types"):
        question_paths = ", ".join(conversation_analysis["question_path_types"][:3])
        summary += f" Dominant question paths: {question_paths}."
    if conversation_analysis and conversation_analysis.get("concept_translation_signal") in {"medium", "high"}:
        summary += (
            " The imported conversation shows "
            + str(conversation_analysis["concept_translation_signal"])
            + " concept-to-technical translation pressure."
        )
    return summary


def materialize_transcript(root: Path, session_id: str) -> Dict[str, str]:
    events = read_jsonl(session_events_path(root, session_id))
    transcript = ["# Ordered Transcript", "", f"- session_id: {session_id}", ""]
    transcript.extend(_event_lines(events))
    transcript_path = session_dir(root, session_id) / "ordered_transcript.md"
    write_markdown(transcript_path, "\n".join(transcript))
    return {"ordered_transcript": str(transcript_path)}


def analyze_session(root: Path, session_id: str) -> Dict[str, str]:
    events = read_jsonl(session_events_path(root, session_id))
    manifest = read_json(session_dir(root, session_id) / "manifest.json", default={})
    domains = manifest.get("domains", [])
    actors = sorted({event["actor"] for event in events})
    kinds = Counter(event["kind"] for event in events)
    turns = _conversation_turns(events)
    conversation_analysis = analyze_conversation_turns(turns) if turns else None

    packet = {
        "session_id": session_id,
        "event_count": len(events),
        "actors": actors,
        "kinds": dict(kinds),
        "domains": domains,
        "summary": _session_summary(domains, turns, conversation_analysis),
    }
    if conversation_analysis:
        packet["conversation_analysis"] = conversation_analysis
    structure_map = {
        "session_id": session_id,
        "event_windows": [
            {
                "index": idx + 1,
                "actor": event["actor"],
                "kind": event["kind"],
                "digest": event["content"][:180],
            }
            for idx, event in enumerate(events)
        ],
    }

    decision_attachments = {
        "session_id": session_id,
        "decisions": [
            {"decision_id": key, "statement": statement, "source_ref": f"session:{session_id}"}
            for key, statement in DECISION_HINTS.items()
        ],
    }
    synthesis = {
        "session_id": session_id,
        "headline": manifest.get("title", session_id),
        "summary": packet["summary"],
        "top_domains": domains,
        "top_requests": [
            event["content"][:140]
            for event in events
            if event["kind"] == "request"
        ][:5],
    }
    if not synthesis["top_requests"] and turns:
        synthesis["top_requests"] = [turn["content"][:140] for turn in turns if turn["role"] == "user"][:5]
    if conversation_analysis:
        synthesis["conversation_analysis"] = conversation_analysis
    artifact_dir = session_dir(root, session_id) / "analysis"
    write_json(artifact_dir / "session_packet.json", packet)
    write_json(artifact_dir / "structure_map.json", structure_map)
    write_json(artifact_dir / "decision_attachments.json", decision_attachments)
    write_json(artifact_dir / "session_synthesis.json", synthesis)

    write_markdown(
        artifact_dir / "session_packet.md",
        "\n".join(
            [
                f"# Session Packet — {session_id}",
                "",
                f"- events: {len(events)}",
                f"- actors: {', '.join(actors)}",
                f"- domains: {', '.join(domains) if domains else 'none'}",
                f"- summary: {packet['summary']}",
            ]
        ),
    )
    write_markdown(
        artifact_dir / "structure_map.md",
        "\n".join(
            [f"# Structure Map — {session_id}", ""]
            + [f"- {window['index']}: {window['actor']} / {window['kind']} — {window['digest']}" for window in structure_map["event_windows"]]
        ),
    )
    write_markdown(
        artifact_dir / "decision_attachments.md",
        "\n".join(
            [f"# Decision Attachments — {session_id}", ""]
            + [f"- {item['decision_id']}: {item['statement']}" for item in decision_attachments["decisions"]]
        ),
    )
    write_markdown(
        artifact_dir / "session_synthesis.md",
        "\n".join(
            [
                f"# Session Synthesis — {session_id}",
                "",
                f"- headline: {synthesis['headline']}",
                f"- summary: {synthesis['summary']}",
                f"- top_domains: {', '.join(domains) if domains else 'none'}",
            ]
        ),
    )
    return {
        "artifact_dir": str(artifact_dir),
        "session_packet": str(artifact_dir / "session_packet.json"),
        "structure_map": str(artifact_dir / "structure_map.json"),
        "decision_attachments": str(artifact_dir / "decision_attachments.json"),
        "session_synthesis": str(artifact_dir / "session_synthesis.json"),
    }


def materialize_cards(root: Path, session_id: str) -> List[Dict]:
    manifest = read_json(session_dir(root, session_id) / "manifest.json", default={})
    domains = manifest.get("domains", [])
    title = manifest.get("title", session_id)
    cards: List[MemoryCard] = []
    for key, statement in DECISION_HINTS.items():
        cards.append(
            MemoryCard(
                card_id=f"decision-{session_id}-{key}",
                card_type="decision",
                title=statement,
                summary=statement,
                source_refs=[f"session:{session_id}"],
                domains=domains,
                status="accepted",
                tags=["decision"],
            )
        )
    cards.append(
        MemoryCard(
            card_id=f"state-{session_id}-{_hash_text(title)}",
            card_type="state",
            title=f"Session state: {title}",
            summary=f"Closed session {session_id} captured with domains: {', '.join(domains) if domains else 'none'}.",
            source_refs=[f"session:{session_id}"],
            domains=domains,
            status="active",
            tags=["state"],
        )
    )
    for idx, question in enumerate(OPEN_QUESTION_HINTS, start=1):
        cards.append(
            MemoryCard(
                card_id=f"question-{session_id}-{idx}",
                card_type="open_question",
                title=question,
                summary=question,
                source_refs=[f"session:{session_id}"],
                domains=domains,
                status="open",
                tags=["question"],
            )
        )
    for card in cards:
        write_json(cards_dir(root) / f"{card.card_id}.json", card.to_dict())
    return [card.to_dict() for card in cards]


def refresh_indexes(root: Path) -> None:
    card_files = list(sorted_files(cards_dir(root), "*.json"))
    cards = [read_json(path) for path in card_files]
    decisions = [card for card in cards if card.get("card_type") == "decision"]
    questions = [card for card in cards if card.get("card_type") == "open_question"]
    states = [card for card in cards if card.get("card_type") == "state"]

    current_lines = ["# Current State", ""]
    if states:
        seen_states = set()
        for card in states[-10:]:
            if card["title"] in seen_states:
                continue
            seen_states.add(card["title"])
            current_lines.append(f"- {card['title']}: {card['summary']}")
    else:
        current_lines.append("- No closed sessions have been materialized yet.")
    write_markdown(indexes_dir(root) / "current_state.md", "\n".join(current_lines))

    question_lines = ["# Open Questions", ""]
    if questions:
        seen_questions = set()
        for card in questions:
            if card["title"] in seen_questions:
                continue
            seen_questions.add(card["title"])
            question_lines.append(f"- {card['title']}")
    else:
        question_lines.append("- No open questions have been materialized yet.")
    write_markdown(indexes_dir(root) / "open_questions.md", "\n".join(question_lines))

    decision_lines = ["# Decision Register", ""]
    if decisions:
        seen_decisions = set()
        for card in decisions:
            if card["title"] in seen_decisions:
                continue
            seen_decisions.add(card["title"])
            decision_lines.append(f"- {card['title']}")
    else:
        decision_lines.append("- No decisions have been materialized yet.")
    write_markdown(indexes_dir(root) / "decision_register.md", "\n".join(decision_lines))

    domains: Dict[str, Dict[str, int | str]] = {}
    for card in cards:
        for domain in card.get("domains", []) or ["general"]:
            bucket = domains.setdefault(domain, {"card_count": 0, "decision_count": 0})
            bucket["card_count"] += 1
            if card.get("card_type") == "decision":
                bucket["decision_count"] += 1
    write_json(indexes_dir(root) / "domain_map.json", {"domains": domains, "updated_at": utc_now()})


def update_manifest(root: Path, manifest: SessionManifest) -> None:
    write_json(session_dir(root, manifest.session_id) / "manifest.json", manifest.to_dict())
