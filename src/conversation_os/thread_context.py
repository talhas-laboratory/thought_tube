from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .meta_layer import load_meta_records
from .thought_factory import load_thought_packets
from .vault_ingest import load_chunk_index, shorten


MODULE_ID = "kernel.surface.thread_context"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "build_thread_packet",
)
__all__ = list(PUBLIC_API)


def _thought_lookup(root: Path) -> Dict[str, Dict]:
    return {row["thought_id"]: row for row in load_thought_packets(root)}


def _chunk_lookup(root: Path) -> Dict[str, Dict]:
    return {row["source_item_id"]: row for row in load_chunk_index(root)}


def build_thread_packet(root: Path, thought_id: str) -> Dict:
    thought = _thought_lookup(root).get(thought_id)
    if thought is None:
        raise KeyError(thought_id)
    meta_lookup = {row["meta_id"]: row for row in load_meta_records(root)}
    chunks = _chunk_lookup(root)
    source_snippets = []
    for item_id in thought.get("source_item_ids", [])[:6]:
        row = chunks.get(item_id)
        if not row:
            continue
        source_snippets.append(
            {
                "source_item_id": item_id,
                "title": row["title"],
                "source_ref": row["source_ref"],
                "excerpt": shorten(row["content"], 220),
            }
        )
    linked_meta = [meta_lookup[meta_id] for meta_id in thought.get("meta_refs", []) if meta_id in meta_lookup]
    tensions = [row for row in linked_meta if row["kind"] == "tension"]
    contradictions = [row for row in linked_meta if row["kind"] == "contradiction"]
    why_frames = [row for row in linked_meta if row["kind"] == "why_it_matters"]
    questions = [row for row in linked_meta if row["kind"] == "question"]
    return {
        "thought_id": thought_id,
        "character": f"The voice of '{thought['title']}'",
        "system_prompt": (
            "Speak from the bounded thought packet only. Use the attached evidence, "
            "acknowledge tensions and contradictions, and do not drift into generic advice."
        ),
        "context_summary": thought["why_it_matters_now"],
        "source_snippets": source_snippets,
        "linked_meta": linked_meta[:12],
        "tensions": tensions[:6],
        "contradictions": contradictions[:6],
        "why_it_matters_frames": why_frames[:6],
        "unresolved_questions": [row["summary"] for row in questions[:4]],
        "thought": thought,
    }
