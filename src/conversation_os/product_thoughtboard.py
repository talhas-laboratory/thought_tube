"""Thoughtboard Surface Adapter.

This module provides the surface adapter for the Thoughtboard product, managing
thoughtboard cards, pasted chatbot conversations, and rendering feeds.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .conversation_learning import parse_conversation_transcript
from .storage import ensure_dir, make_id, read_json, read_jsonl, utc_now, write_json, append_jsonl
from .models import SessionManifest

MODULE_ID = "surface.thoughtboard.product_thoughtboard"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "load_surface_recipe",
    "ensure_thoughtboard_runtime",
    "save_thoughtboard_card",
    "load_thoughtboard_cards",
    "delete_thoughtboard_card",
    "ingest_pasted_conversation",
    "build_thoughtboard_feed",
)
__all__ = list(PUBLIC_API)


def _product_dir(root: Path) -> Path:
    return root / "product" / "thoughtboard_v1"


def _data_dir(root: Path) -> Path:
    return _product_dir(root) / "data"


def _cards_dir(root: Path) -> Path:
    return _data_dir(root) / "cards"


def _surface_recipe_path(root: Path) -> Path:
    return _product_dir(root) / "config" / "surface_recipe.v1.json"


def load_surface_recipe(root: Path) -> Dict[str, Any]:
    path = _surface_recipe_path(root)
    if not path.exists():
        raise RuntimeError(f"Surface recipe not found: {path}")
    return read_json(path, default={}) or {}


def ensure_thoughtboard_runtime(root: Path) -> None:
    ensure_dir(_data_dir(root))
    ensure_dir(_cards_dir(root))


def save_thoughtboard_card(root: Path, card: Dict[str, Any]) -> Dict[str, Any]:
    ensure_thoughtboard_runtime(root)
    card_id = card.get("card_id") or make_id("card")
    now = utc_now()
    
    payload = {
        "card_id": card_id,
        "title": card.get("title") or "Untitled Thought",
        "summary": card.get("summary") or "",
        "created_at": card.get("created_at") or now,
        "updated_at": now,
        "source_ref": card.get("source_ref") or "",
        "media_refs": list(card.get("media_refs") or []),
        "relations": list(card.get("relations") or []),
        "tags": list(card.get("tags") or []),
        "status": card.get("status") or "active",
    }
    
    write_json(_cards_dir(root) / f"{card_id}.json", payload)
    return payload


def load_thoughtboard_cards(root: Path) -> List[Dict[str, Any]]:
    ensure_thoughtboard_runtime(root)
    cards = []
    for path in _cards_dir(root).glob("*.json"):
        payload = read_json(path)
        if payload and payload.get("status") != "deleted":
            cards.append(payload)
    # Sort by created_at descending
    cards.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return cards


def delete_thoughtboard_card(root: Path, card_id: str) -> bool:
    path = _cards_dir(root) / f"{card_id}.json"
    if not path.exists():
        return False
    card = read_json(path)
    if card:
        card["status"] = "deleted"
        card["updated_at"] = utc_now()
        write_json(path, card)
        return True
    return False


def ingest_pasted_conversation(root: Path, title: str, transcript_text: str) -> Dict[str, Any]:
    ensure_thoughtboard_runtime(root)
    turns = parse_conversation_transcript(transcript_text)
    session_id = make_id("import-thoughtboard")
    now = utc_now()
    
    # Create session directory and manifest
    session_root = root / "memory" / "sessions" / session_id
    ensure_dir(session_root)
    
    manifest = SessionManifest(
        session_id=session_id,
        title=title,
        started_at=now,
        ended_at=now,
        participants=list(dict.fromkeys(turn["role"] for turn in turns)) or ["user", "assistant"],
        source_type="pasted_transcript",
        status="closed",
        artifact_refs={},
        domains=["thoughtboard"],
    )
    
    write_json(session_root / "manifest.json", manifest.to_dict())
    
    # Save the raw events to memory/events
    events_path = root / "memory" / "events" / f"{session_id}.jsonl"
    ensure_dir(events_path.parent)
    
    for turn in turns:
        event = {
            "event_id": make_id("event"),
            "session_id": session_id,
            "timestamp": now,
            "actor": turn["role"],
            "kind": "request" if turn["role"] == "user" else "response",
            "content": turn["content"],
            "attachments": [],
            "tags": [],
            "source_ref": "",
        }
        append_jsonl(events_path, event)
    
    # Core heuristic synthesis (Crystallize pasted transcript into a Thoughtboard Card)
    # Extract the user's main point and the assistant's counterpoint or synthesis
    user_turns = [turn["content"] for turn in turns if turn["role"] == "user"]
    assistant_turns = [turn["content"] for turn in turns if turn["role"] != "user"]
    
    summary_lines = []
    if user_turns:
        summary_lines.append(f"Discussing: {user_turns[0][:150]}...")
    if assistant_turns:
        summary_lines.append(f"Synthesis: {assistant_turns[0][:200]}...")
    
    summary = "\n\n".join(summary_lines) or "Empty discussion."
    
    card = save_thoughtboard_card(root, {
        "title": title,
        "summary": summary,
        "source_ref": f"session:{session_id}",
        "tags": ["chatbot-discussion"],
    })

    from .element_ingest import ingest_to_element_space

    ingest_text = "\n".join(part for part in [title, summary, transcript_text] if part)
    element_ingest = ingest_to_element_space(
        root,
        raw_text=ingest_text,
        source_kind="thoughtboard_paste",
        source_ref=f"session:{session_id}",
        session_id=session_id,
        surface_hints=["thoughtboard", "pasted_transcript"],
    )
    
    return {
        "session_id": session_id,
        "card_id": card["card_id"],
        "card": card,
        "element_ingest": element_ingest,
    }


def build_thoughtboard_feed(root: Path) -> Dict[str, Any]:
    cards = load_thoughtboard_cards(root)
    
    # Construct nodes and edges for relational layout
    nodes = []
    edges = []
    
    for card in cards:
        nodes.append({
            "id": card["card_id"],
            "label": card["title"],
            "type": "thought",
            "summary": card["summary"],
            "media_refs": card["media_refs"],
            "tags": card["tags"],
        })
        
        for rel_id in card["relations"]:
            edges.append({
                "from": card["card_id"],
                "to": rel_id,
                "type": "related",
            })
            
    return {
        "generated_at": utc_now(),
        "cards": cards,
        "graph": {
            "nodes": nodes,
            "edges": edges,
        }
    }
