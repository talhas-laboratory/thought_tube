from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from .long_form import build_long_form_article
from .models import ThoughtPacket
from .storage import read_json, read_jsonl, utc_now, write_json, write_jsonl
from .vault_ingest import load_chunk_index, shorten, tokenize


MODULE_ID = "kernel.surface.thought_factory"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "thought_packets_path",
    "load_thought_packets",
    "build_thought_packets",
    "build_feed_rows",
    "build_archive_rows",
)
__all__ = list(PUBLIC_API)


THOUGHT_STYLE_MAP = {
    "morning_batch": {
        "title": "Morning Batch Is The Native Surface",
        "short_text": "A calm daily batch is easier to trust than a feed that keeps tugging at the sleeve. The day probably wants one clear arrival, not a constant drip.",
    },
    "ambiguity_then_structure": {
        "title": "Let The Thought Stay Messy First",
        "short_text": "Some things lose their shape the moment you rush to explain them. Better to let them stay a little loose until the center becomes obvious.",
    },
    "cognitive_fidelity": {
        "title": "Protect The Signal Before You Explain It",
        "short_text": "There is usually a live wire inside the raw material. Once it gets polished too early, the voltage disappears.",
    },
    "review_before_commit": {
        "title": "Nothing Durable Without Review",
        "short_text": "Not everything deserves to become memory on first contact. Some thoughts need to sit in the light a little longer before they harden.",
    },
    "private_cognitive_layer": {
        "title": "This Is Not A Note App",
        "short_text": "This private cognitive layer wants to feel closer to inner weather than storage. The point is not collecting notes, but letting your own material speak back with some weight.",
    },
    "progressive_disclosure": {
        "title": "Small Thought, Deep Expansion",
        "short_text": "A thought should arrive lightly. Depth can wait until curiosity actually asks for it.",
    },
}


STALE_SYSTEM_PHRASES = (
    "a deeper connection surfaced",
    "random overlap",
    "this connection matters because",
    "reveals a reusable move in the vault",
    "productive tension",
)

GENERIC_THOUGHT_PREFIXES = (
    "something in ",
)

GENERIC_THOUGHT_CONTAINS = (
    " keeps leaning toward ",
    " keeps returning",
)


def thought_packets_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "thought_packets.jsonl"


def load_thought_packets(root: Path) -> List[Dict]:
    return read_jsonl(thought_packets_path(root))


def _runtime_config(root: Path) -> Dict[str, Any]:
    return (
        read_json(
            root / "product" / "inner_world_v1" / "config" / "runtime.json",
            default={},
        )
        or {}
    )


def _thought_assist_cache_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "semantic_thought_assists.json"


def _thought_assist_cache(root: Path) -> Dict[str, Dict[str, Any]]:
    return read_json(_thought_assist_cache_path(root), default={}) or {}


def _write_thought_assist_cache(root: Path, payload: Dict[str, Dict[str, Any]]) -> None:
    write_json(_thought_assist_cache_path(root), payload)


def _thought_assist_config(root: Path) -> Dict[str, Any]:
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
        "candidate_limit": max(0, int(assist.get("thought_candidate_limit", 4) or 0)),
        "snippet_limit": max(1, int(assist.get("snippet_limit", 3) or 3)),
        "snippet_chars": max(80, int(assist.get("snippet_chars", 180) or 180)),
    }


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
        if isinstance(candidate, dict) and candidate.get("decision"):
            return candidate
        if isinstance(candidate, str):
            candidate = candidate.strip()
            if not candidate:
                continue
            try:
                nested = json.loads(candidate)
            except json.JSONDecodeError:
                nested = None
            if isinstance(nested, dict) and nested.get("decision"):
                return nested
            match = re.search(r"\{.*\}", candidate, re.S)
            if match:
                try:
                    nested = json.loads(match.group(0))
                except json.JSONDecodeError:
                    nested = None
                if isinstance(nested, dict) and nested.get("decision"):
                    return nested
    return None


def _looks_generic_thought_text(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    if not normalized:
        return True
    if any(normalized.startswith(prefix) for prefix in GENERIC_THOUGHT_PREFIXES):
        return True
    return any(fragment in normalized for fragment in GENERIC_THOUGHT_CONTAINS)


def _thought_assist_fingerprint(row: Dict, snippets: List[Dict]) -> str:
    payload = {
        "candidate_title": row.get("candidate_title", ""),
        "candidate_short_text": row.get("candidate_short_text", ""),
        "what_changed": row.get("what_changed", ""),
        "why_it_matters_now": row.get("why_it_matters_now", ""),
        "review_status": row.get("review_status", ""),
        "evidence_status": row.get("evidence_status", ""),
        "confidence_score": row.get("confidence_score", 0.0),
        "relevance_score": row.get("relevance_score", 0.0),
        "novelty_score": row.get("novelty_score", 0.0),
        "primary_bubble_label": row.get("primary_bubble_label", ""),
        "source_snippets": [snippet.get("excerpt", "") for snippet in snippets[:3]],
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _thought_assist_prompt(row: Dict, snippets: List[Dict]) -> str:
    evidence_lines = []
    for snippet in snippets[:3]:
        evidence_lines.append(
            f"- {snippet['full_title'] or snippet['title']}: {shorten(snippet['excerpt'], 180)}"
        )
    evidence_block = "\n".join(evidence_lines) if evidence_lines else "- No direct source snippets."
    return "\n".join(
        [
            "You are improving a surfaced thought candidate for Inner World.",
            "Return JSON only with this shape:",
            '{"decision":"promote|review|reject","title":"...","short_text":"...","confidence":"high|medium|low","reason":"..."}',
            "",
            "Rules:",
            "- Use reject if the candidate is generic, procedural, or not clearly meaningful enough to surface.",
            "- Use review if it is interesting but still too weak or vague to surface cleanly.",
            "- Use promote only if the title and short_text can be made concrete, human-readable, and grounded in the evidence.",
            "- Keep title under 8 words.",
            "- Keep short_text under 220 characters.",
            "- Avoid generic phrasing like 'Something in X' or 'keeps leaning toward'.",
            "- Do not invent facts beyond the evidence.",
            "",
            f"Primitive: {row.get('shared_primitive_label', '')}",
            f"Candidate title: {row.get('candidate_title', '')}",
            f"Candidate short text: {row.get('candidate_short_text', '')}",
            f"What changed: {row.get('what_changed', '')}",
            f"Why it matters now: {row.get('why_it_matters_now', '')}",
            f"Review status: {row.get('review_status', '')}",
            f"Evidence status: {row.get('evidence_status', '')}",
            f"Primary bubble: {row.get('primary_bubble_label', '')}",
            "",
            "Evidence snippets:",
            evidence_block,
        ]
    )


def _run_thought_assist(root: Path, config: Dict[str, Any], row: Dict, snippets: List[Dict]) -> Dict[str, Any] | None:
    command = [
        "openclaw",
        "agent",
        "--agent",
        config["agent"],
        "--thinking",
        config["thinking"],
        "--message",
        _thought_assist_prompt(row, snippets),
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
    decision = str(payload.get("decision", "")).strip().lower()
    if decision not in {"promote", "review", "reject"}:
        return None
    return {
        "decision": decision,
        "title": shorten(str(payload.get("title", "")).strip(), 72).rstrip(" ."),
        "short_text": shorten(str(payload.get("short_text", "")).strip(), 220).rstrip(),
        "confidence": str(payload.get("confidence", "")).strip().lower(),
        "reason": shorten(str(payload.get("reason", "")).strip(), 220).rstrip(),
    }


def _select_thought_assist_candidates(
    rows: List[Dict],
    feedback_by_insight: Dict[str, str],
    limit: int,
) -> List[Dict]:
    selected: List[Dict] = []
    for row in sorted(rows, key=lambda item: _packet_rank(item, feedback_by_insight)):
        if _packet_style(row):
            continue
        if row.get("review_status") != "approved_for_surface":
            selected.append(row)
        elif _looks_generic_thought_text(row.get("candidate_title", "")) or _looks_generic_thought_text(row.get("candidate_short_text", "")):
            selected.append(row)
        elif row.get("confidence_score", 0.0) < 0.72:
            selected.append(row)
        if len(selected) >= limit:
            break
    return selected


def _semantic_thought_assists(
    root: Path,
    rows: List[Dict],
    feedback_by_insight: Dict[str, str],
) -> Dict[str, Dict[str, Any]]:
    config = _thought_assist_config(root)
    if not config.get("enabled"):
        return {}
    candidate_limit = config.get("candidate_limit", 0)
    if candidate_limit <= 0:
        return {}
    cache = _thought_assist_cache(root)
    updated = False
    assists: Dict[str, Dict[str, Any]] = {}
    for row in _select_thought_assist_candidates(rows, feedback_by_insight, candidate_limit):
        snippets = _source_snippets(root, row["source_item_ids"])[: config["snippet_limit"]]
        fingerprint = _thought_assist_fingerprint(row, snippets)
        cached = cache.get(row["packet_id"])
        if cached and cached.get("fingerprint") == fingerprint:
            assists[row["packet_id"]] = cached["payload"]
            continue
        payload = _run_thought_assist(root, config, row, snippets)
        if not payload:
            continue
        cache[row["packet_id"]] = {
            "fingerprint": fingerprint,
            "payload": payload,
            "updated_at": utc_now(),
        }
        assists[row["packet_id"]] = payload
        updated = True
    if updated:
        _write_thought_assist_cache(root, cache)
    return assists


def _packet_style(packet: Dict) -> Dict | None:
    primitive_key = packet.get("shared_primitive_key") or ""
    if primitive_key in THOUGHT_STYLE_MAP:
        return THOUGHT_STYLE_MAP[primitive_key]
    signal_text = " ".join(
        [
            primitive_key,
            packet.get("shared_primitive_label", ""),
            packet.get("what_changed", ""),
            packet.get("why_it_matters_now", ""),
            " ".join(packet.get("shared_terms", [])),
            packet.get("candidate_title", ""),
            packet.get("candidate_short_text", ""),
        ]
    ).lower()
    if "morning" in signal_text and "batch" in signal_text:
        return THOUGHT_STYLE_MAP["morning_batch"]
    if "private" in signal_text and "cognitive" in signal_text and "layer" in signal_text:
        return THOUGHT_STYLE_MAP["private_cognitive_layer"]
    if "review" in signal_text and any(term in signal_text for term in ["commit", "persist", "approve", "gate"]):
        return THOUGHT_STYLE_MAP["review_before_commit"]
    if any(term in signal_text for term in ["progressive disclosure", "small thought", "deep expansion"]):
        return THOUGHT_STYLE_MAP["progressive_disclosure"]
    return None


def _clean_source_line(text: str, limit: int = 120) -> str:
    cleaned = re.sub(r"[*_`>#]+", " ", text or "")
    cleaned = cleaned.replace("–", " ").replace("—", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;-/")
    cleaned = re.sub(r"^(function|summary|why this matters)\s*:\s*", "", cleaned, flags=re.I)
    return shorten(cleaned, limit).rstrip(" .")


def _source_display_title(row: Dict) -> str:
    content = (row.get("content") or "").strip()
    if not content:
        return row.get("title", "")
    first_line = content.splitlines()[0].strip()
    first_line = re.sub(r"^[-*]\s+|^\d+\.\s+", "", first_line)
    return first_line or row.get("title", "")


def _human_line(text: str) -> bool:
    tokens = tokenize(text)
    if not tokens:
        return False
    markers = {"the", "a", "an", "is", "are", "keep", "keeps", "should", "because", "before", "not", "with", "without", "can", "must", "need", "needs"}
    return any(token in markers for token in tokens)


def _source_voice(snippets: List[Dict], limit: int = 120) -> str:
    for snippet in snippets:
        line = _clean_source_line(snippet.get("excerpt", ""), limit)
        if line and _human_line(line):
            return line
    return ""


def _surface_worthy(packet: Dict, style: Dict | None, title: str, short_text: str, snippets: List[Dict]) -> bool:
    if style:
        return True
    lowered_title = title.lower()
    lowered_short = short_text.lower()
    if " keeps leaning toward " in lowered_title or lowered_title.startswith("something in "):
        return False
    if lowered_short.startswith("something in "):
        return False
    if packet.get("evidence_status") == "grounded" and packet.get("confidence_score", 0.0) >= 0.72:
        return True
    source_line = _source_voice(snippets, 120)
    if source_line:
        return True
    if _human_line(title) and _human_line(short_text) and packet.get("confidence_score", 0.0) >= 0.62:
        return True
    return False


def _fallback_title(packet: Dict, snippets: List[Dict]) -> str:
    candidate_title = (packet.get("candidate_title") or "").strip()
    if candidate_title and not _looks_generic_thought_text(candidate_title) and any(token in tokenize(candidate_title) for token in ["the", "a", "an", "is", "are", "keep", "keeps", "should", "before", "because"]):
        return candidate_title
    for field in [packet.get("candidate_short_text", ""), packet.get("what_changed", ""), packet.get("why_it_matters_now", "")]:
        text = shorten(field.strip(), 72).rstrip(" .") if field else ""
        tokens = tokenize(text)
        if text and not _looks_generic_thought_text(text) and any(token in tokens for token in ["the", "a", "an", "is", "are", "keep", "keeps", "should", "before", "because"]):
            return text
    source_line = _source_voice(snippets, 72)
    if source_line:
        return source_line
    primitive_label = shorten((packet.get("shared_primitive_label") or "").strip(), 72).rstrip(" .")
    if primitive_label and not _looks_generic_thought_text(primitive_label) and len(tokenize(primitive_label)) >= 2:
        return primitive_label
    terms = packet.get("shared_terms", [])[:3]
    if terms:
        readable = [term.replace("-", " ") for term in terms if len(term) > 3]
        if len(readable) >= 2:
            return f"{readable[0].capitalize()} keeps leaning toward {readable[1]}"
        if readable:
            return f"{readable[0].capitalize()} keeps returning"
    primitive = packet.get("shared_primitive_label") or "Interesting Connection"
    return f"Something in {primitive.lower()} keeps asking for room"


def _fallback_short_text(packet: Dict, snippets: List[Dict]) -> str:
    candidate_short_text = (packet.get("candidate_short_text") or "").strip()
    lowered = candidate_short_text.lower()
    if candidate_short_text and not _looks_generic_thought_text(candidate_short_text) and not any(phrase in lowered for phrase in STALE_SYSTEM_PHRASES):
        return shorten(candidate_short_text, 220)
    source_line = _source_voice(snippets, 160)
    if source_line:
        return shorten(f"{source_line.rstrip('.')}. {_soften_surface_text(packet['why_it_matters_now']).rstrip('.')}.", 220)
    return shorten(
        f"{_soften_surface_text(packet['what_changed']).rstrip('.')} {_soften_surface_text(packet['why_it_matters_now']).rstrip('.')}",
        220,
    )


def _soften_surface_text(text: str) -> str:
    softened = (text or "").strip()
    softened = softened.replace("productive tension", "living friction")
    softened = softened.replace("reveals a reusable move in the vault", "keeps shifting where attention wants to land")
    softened = softened.replace("The same undercurrent keeps showing up from two directions.", "The same undercurrent keeps arriving from two directions.")
    if softened.lower().startswith("this connection matters because "):
        softened = softened[len("This connection matters because ") :]
    return softened


def _normalized_title(title: str) -> str:
    return " ".join(tokenize(title)) or title.strip().lower()


def _packet_rank(row: Dict, feedback_by_insight: Dict[str, str]) -> tuple:
    feedback_state = feedback_by_insight.get(row["insight_id"], "pending")
    feedback_bonus = {
        "accepted": 0.30,
        "relevant": 0.22,
        "saved": 0.16,
        "revisit_later": 0.08,
        "dismiss": -0.18,
    }.get(feedback_state, 0.0)
    return (
        row.get("evidence_status") != "grounded",
        -(row.get("confidence_score", 0.0) + row.get("relevance_score", 0.0) + row.get("novelty_score", 0.0) + feedback_bonus),
        row.get("candidate_title", row.get("left_label", "")),
        row.get("packet_id", ""),
    )


def _source_snippets(root: Path, source_item_ids: List[str]) -> List[Dict]:
    rows = {row["source_item_id"]: row for row in load_chunk_index(root)}
    snippets = []
    for item_id in source_item_ids[:6]:
        row = rows.get(item_id)
        if not row:
            continue
        snippets.append(
            {
                "source_item_id": item_id,
                "title": row["title"],
                "full_title": _source_display_title(row),
                "source_type": row["source_type"],
                "source_ref": row["source_ref"],
                "excerpt": shorten(row["content"], 220),
                "content": row["content"],
            }
        )
    return snippets


def _build_article_payload(root: Path, packet: Dict, snippets: List[Dict], title: str, short_text: str) -> Dict:
    return build_long_form_article(root, packet, snippets, title, short_text)


def build_thought_packets(root: Path, promotion_rows: List[Dict], feedback_by_insight: Dict[str, str] | None = None) -> List[Dict]:
    feedback_by_insight = feedback_by_insight or {}
    packets: List[Dict] = []
    seen_titles = set()
    sorted_rows = sorted(promotion_rows, key=lambda item: _packet_rank(item, feedback_by_insight))
    approved_rows = [row for row in sorted_rows if row.get("review_status") == "approved_for_surface"]
    eligible_rows = approved_rows or [
        row
        for row in sorted_rows
        if row.get("review_status") == "ready_for_review"
        and (row.get("evidence_status") == "grounded" or row.get("confidence_score", 0.0) >= 0.56)
    ]
    semantic_assists = _semantic_thought_assists(root, eligible_rows, feedback_by_insight)
    for row in eligible_rows:
        snippets = _source_snippets(root, row["source_item_ids"])
        semantic_assist = semantic_assists.get(row["packet_id"])
        style = _packet_style(row)
        title = style["title"] if style else _fallback_title(row, snippets)
        short_text = style["short_text"] if style else _fallback_short_text(row, snippets)
        if semantic_assist and semantic_assist.get("decision") == "reject":
            continue
        if semantic_assist:
            assisted_title = semantic_assist.get("title", "")
            assisted_short_text = semantic_assist.get("short_text", "")
            if assisted_title and not _looks_generic_thought_text(assisted_title):
                title = assisted_title
            if assisted_short_text and not _looks_generic_thought_text(assisted_short_text):
                short_text = assisted_short_text
        if not (semantic_assist and semantic_assist.get("decision") == "promote") and not _surface_worthy(row, style, title, short_text, snippets):
            continue
        title_key = _normalized_title(title)
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        thought_id = f"thought-{hashlib.sha256(row['packet_id'].encode('utf-8')).hexdigest()[:12]}"
        insight_id = row["insight_id"]
        article_payload = _build_article_payload(root, row, snippets, title, short_text)
        packet = ThoughtPacket(
                packet_id=row["packet_id"],
                thought_id=thought_id,
                insight_id=insight_id,
                title=title,
                short_text=short_text,
                article_title=title,
                article_markdown=article_payload["markdown"],
                status="active",
                review_status=row["review_status"],
                evidence_status=row["evidence_status"],
                confidence_score=row["confidence_score"],
                relevance_score=row["relevance_score"],
                novelty_score=row["novelty_score"],
                source_refs=row["source_refs"],
                source_item_ids=row["source_item_ids"],
                meta_refs=row["meta_refs"],
                shared_primitive_key=row["shared_primitive_key"],
                shared_primitive_label=row["shared_primitive_label"],
                what_changed=row["what_changed"],
                why_it_matters_now=row["why_it_matters_now"],
                next_action=row["next_action"],
                reasoning_pipeline=row["reasoning_pipeline"],
                primary_bubble_id=row.get("primary_bubble_id", ""),
                primary_bubble_label=row.get("primary_bubble_label", ""),
                related_bubble_ids=row.get("related_bubble_ids", []),
                feedback_state=feedback_by_insight.get(insight_id, "pending"),
                article_sections=article_payload["sections"],
                article_profile=article_payload["profile"],
                article_module_order=article_payload["module_order"],
                article_config_snapshot=article_payload["config_snapshot"],
            ).to_dict()
        if semantic_assist:
            packet["semantic_assist"] = semantic_assist
        packets.append(packet)
    write_jsonl(thought_packets_path(root), packets)
    return packets


def build_feed_rows(root: Path, limit: int = 12) -> List[Dict]:
    packets = load_thought_packets(root)
    rows = sorted(
        packets,
        key=lambda item: (
            item["evidence_status"] != "grounded",
            -item["confidence_score"],
            -item["relevance_score"],
            -item["novelty_score"],
            item["title"],
        ),
    )
    deduped = []
    seen_titles = set()
    for row in rows:
        title_key = _normalized_title(row["title"])
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        deduped.append(row)
        if len(deduped) >= limit:
            break
    return deduped


def build_archive_rows(root: Path) -> List[Dict]:
    rows = sorted(
        load_thought_packets(root),
        key=lambda item: (
            item["evidence_status"] != "grounded",
            -item["confidence_score"],
            -item["relevance_score"],
            item["title"],
        ),
    )
    deduped = []
    seen_titles = set()
    for row in rows:
        title_key = _normalized_title(row["title"])
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        deduped.append(row)
    return deduped
