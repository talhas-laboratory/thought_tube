from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from .conversation_deltas import build_conversation_deltas, load_conversation_deltas
from .storage import read_jsonl, write_jsonl
from .vault_ingest import load_chunk_index, tokenize


MODULE_ID = "kernel.analysis.conversation_threads"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "load_conversation_threads",
    "load_thread_links",
    "build_conversation_threads",
)
__all__ = list(PUBLIC_API)


STOPWORDS = {
    "again",
    "also",
    "back",
    "earlier",
    "first",
    "idea",
    "later",
    "point",
    "returning",
    "system",
}


def _data_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data"


def _threads_path(root: Path) -> Path:
    return _data_dir(root) / "conversation_threads.jsonl"


def _links_path(root: Path) -> Path:
    return _data_dir(root) / "conversation_thread_links.jsonl"


def load_conversation_threads(root: Path) -> List[Dict]:
    return read_jsonl(_threads_path(root))


def load_thread_links(root: Path) -> List[Dict]:
    return read_jsonl(_links_path(root))


def _speaker_role(row: Dict) -> str:
    return row.get("speaker_role") or row.get("metadata", {}).get("speaker_role") or ""


def _meaningful_tokens(text: str) -> List[str]:
    return [token for token in tokenize(text) if token not in STOPWORDS][:12]


def _thread_id(anchor_chunk_id: str, signature: List[str]) -> str:
    seed = "::".join([anchor_chunk_id, "|".join(signature[:6])]).encode("utf-8")
    return f"thread-{hashlib.sha256(seed).hexdigest()[:12]}"


def _link_id(kind: str, left: str, right: str) -> str:
    seed = "::".join([kind, left, right]).encode("utf-8")
    return f"thread-link-{hashlib.sha256(seed).hexdigest()[:12]}"


def _thread_score(tokens: List[str], thread: Dict) -> int:
    overlap = set(tokens) & set(thread["topic_signature"])
    return len(overlap)


def _match_thread(tokens: List[str], active_threads: List[Dict]) -> Dict | None:
    ranked = sorted(
        (( _thread_score(tokens, thread), thread) for thread in active_threads),
        key=lambda item: (-item[0], item[1]["thread_id"]),
    )
    if not ranked or ranked[0][0] < 2:
        return None
    return ranked[0][1]


def build_conversation_threads(root: Path, ensure_dependencies: bool = True) -> Dict:
    if ensure_dependencies:
        build_conversation_deltas(root)
    delta_rows = load_conversation_deltas(root)
    delta_by_user_chunk: Dict[str, List[Dict]] = defaultdict(list)
    for row in delta_rows:
        delta_by_user_chunk[row["initial_user_chunk_id"]].append(row)
        delta_by_user_chunk[row["repeated_user_chunk_id"]].append(row)

    chunks = sorted(load_chunk_index(root), key=lambda row: (row["source_ref"], row["chunk_index"]))
    user_rows = [row for row in chunks if _speaker_role(row) == "user"]
    thread_by_id: Dict[str, Dict] = {}
    links: List[Dict] = []

    last_thread_by_source: Dict[str, str] = {}
    previous_threads_by_source: Dict[str, List[str]] = defaultdict(list)

    for row in user_rows:
        source_ref = row["source_ref"]
        tokens = _meaningful_tokens(row.get("content", ""))
        matching_pool = list(thread_by_id.values())
        thread = _match_thread(tokens, matching_pool)
        if thread is None:
            thread = {
                "thread_id": _thread_id(row["chunk_id"], tokens or [row["chunk_id"]]),
                "topic_signature": tokens[:8],
                "source_refs": [],
                "user_chunk_ids": [],
                "approved_context_chunk_ids": [],
                "turn_count": 0,
                "interruption_count": 0,
                "delta_intent_keys": [],
                "source_count": 0,
            }
            thread_by_id[thread["thread_id"]] = thread
        else:
            merged = sorted(set(thread["topic_signature"]) | set(tokens))
            thread["topic_signature"] = merged[:8]

        if thread["thread_id"] != last_thread_by_source.get(source_ref):
            if thread["thread_id"] in previous_threads_by_source[source_ref]:
                thread["interruption_count"] += 1
                prior = last_thread_by_source.get(source_ref)
                if prior:
                    links.append(
                        {
                            "link_id": _link_id("returns_to", prior, thread["thread_id"]),
                            "kind": "returns_to",
                            "from_thread_id": prior,
                            "to_thread_id": thread["thread_id"],
                            "source_refs": [source_ref],
                            "confidence": 0.74,
                        }
                    )
            previous_threads_by_source[source_ref].append(thread["thread_id"])
            last_thread_by_source[source_ref] = thread["thread_id"]

        thread["user_chunk_ids"].append(row["chunk_id"])
        thread["turn_count"] += 1
        if source_ref not in thread["source_refs"]:
            thread["source_refs"].append(source_ref)
            thread["source_count"] = len(thread["source_refs"])

        for delta in delta_by_user_chunk.get(row["chunk_id"], []):
            if delta["intent_key"] not in thread["delta_intent_keys"]:
                thread["delta_intent_keys"].append(delta["intent_key"])
            resolved = delta.get("resolved_assistant_chunk_id")
            if resolved and resolved not in thread["approved_context_chunk_ids"]:
                thread["approved_context_chunk_ids"].append(resolved)

    for thread in thread_by_id.values():
        if len(thread["source_refs"]) > 1:
            ordered_sources = sorted(thread["source_refs"])
            for left, right in zip(ordered_sources, ordered_sources[1:]):
                links.append(
                    {
                        "link_id": _link_id("continues_across_sources", thread["thread_id"], right),
                        "kind": "continues_across_sources",
                        "from_thread_id": thread["thread_id"],
                        "to_thread_id": thread["thread_id"],
                        "source_refs": [left, right],
                        "confidence": 0.8,
                    }
                )

    ordered_threads = sorted(
        (
            {
                **thread,
                "topic_signature": thread["topic_signature"][:8],
                "source_refs": sorted(thread["source_refs"]),
                "user_chunk_ids": thread["user_chunk_ids"],
                "approved_context_chunk_ids": thread["approved_context_chunk_ids"],
                "delta_intent_keys": sorted(thread["delta_intent_keys"]),
            }
            for thread in thread_by_id.values()
        ),
        key=lambda item: (-item["turn_count"], item["thread_id"]),
    )
    deduped_links = {
        link["link_id"]: link
        for link in links
    }
    ordered_links = sorted(deduped_links.values(), key=lambda item: (item["kind"], item["link_id"]))

    write_jsonl(_threads_path(root), ordered_threads)
    write_jsonl(_links_path(root), ordered_links)
    return {
        "thread_count": len(ordered_threads),
        "link_count": len(ordered_links),
        "cross_source_thread_count": sum(1 for thread in ordered_threads if thread["source_count"] > 1),
    }
