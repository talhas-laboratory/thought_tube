#!/usr/bin/env python3
import argparse
import json
import re
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


DISCLAIMER_LINE = "KI-Antworten können Fehler enthalten."
UI_NOISE_PATTERNS = [
    re.compile(r"^\s*KI-Modus\b", re.IGNORECASE),
    re.compile(r"^\s*Alle simulieren\b", re.IGNORECASE),
    re.compile(r"^\s*Verknüpfungen Bilder Videos News\b", re.IGNORECASE),
    re.compile(r"^\s*kann,\s*nutzt Produkte\b", re.IGNORECASE),
    re.compile(r"^\s*Produkte\b", re.IGNORECASE),
    re.compile(r"^\s*Frage stellen\b", re.IGNORECASE),
]


FRAME_LIBRARY = [
    {
        "key": "inner-world-ontology",
        "label": "Inner world ontology",
        "description": "Defines what the inner world is, what is shared across people, and how subconscious or creative cognition behaves.",
        "keywords": [
            "inner world",
            "mental landscape",
            "creative world",
            "subconscious",
            "dmn",
            "default mode network",
            "narrative structure",
            "mental time travel",
            "inner story",
        ],
    },
    {
        "key": "cognitive-automation-thesis",
        "label": "Cognitive automation thesis",
        "description": "Tests whether subconscious or creative reasoning can be automated or assisted by AI.",
        "keywords": [
            "automated using ai",
            "automating subconscious",
            "cognitive tool",
            "cognitive work",
            "personal agi",
            "cognitive prosthetic",
            "external latent space",
            "cognitive automation",
        ],
    },
    {
        "key": "reasoning-architecture",
        "label": "Reasoning architecture",
        "description": "Explores system structure, reasoning primitives, orchestration, graphs, routing, and storage.",
        "keywords": [
            "reasoning primitive",
            "graph",
            "routing",
            "orchestrated reasoning",
            "openclaw",
            "vault",
            "embed",
            "workspace",
            "database",
            "multimodal ingestion",
            "latent space",
        ],
    },
    {
        "key": "learning-adaptation",
        "label": "Learning and adaptation",
        "description": "Covers feedback loops, path strengthening, recommendation tuning, and reward modeling.",
        "keywords": [
            "feedback",
            "verification",
            "strengthen",
            "weaken",
            "implicit feedback",
            "contextual reinforcement learning",
            "reward model",
            "adaptation engine",
            "rlhf",
        ],
    },
    {
        "key": "bayesian-surprise",
        "label": "Bayesian surprise",
        "description": "Uses Bayesian surprise as the relevance and update metric for surfaced insights.",
        "keywords": [
            "bayesian surprise",
            "kl divergence",
            "prior",
            "posterior",
            "surprise engine",
            "latent warp",
            "cognitive surprise",
        ],
    },
    {
        "key": "product-validation",
        "label": "Product validation",
        "description": "Evaluates market fit, target users, competition, and business viability.",
        "keywords": [
            "product idea",
            "judge ideas",
            "survives scrutiny",
            "benefit",
            "killer app",
            "market",
            "moat",
            "time-to-value",
            "venture-ready",
            "8.5/10",
        ],
    },
    {
        "key": "interface-and-experience",
        "label": "Interface and experience",
        "description": "Shapes how users encounter surfaced insights and how the system should feel in use.",
        "keywords": [
            "interface",
            "twitter/substack",
            "insight stream",
            "progressive disclosure",
            "nudges",
            "confronted",
            "user feedback",
            "ambient",
            "ui",
        ],
    },
    {
        "key": "fractal-and-multimodal",
        "label": "Fractal and multimodal expansion",
        "description": "Explores fractal context access and multimodal or synesthetic linking.",
        "keywords": [
            "fractal",
            "context bottleneck",
            "multimodal",
            "synesthesia",
            "digital synesthesia",
            "audio",
            "images",
            "sensor",
        ],
    },
    {
        "key": "distribution-and-installation",
        "label": "Distribution and installation",
        "description": "Covers workspace integration, install shape, and operational packaging.",
        "keywords": [
            "one-click",
            "one-command",
            "install",
            "workspace",
            "agent",
            "distribution",
            "skill system",
            "existing workspace",
        ],
    },
]


TENSION_LIBRARY = [
    {
        "key": "automation-vs-human-judgment",
        "label": "Automation vs human judgment",
        "pole_a": "autonomous insight generation",
        "pole_b": "human verification and editorial control",
        "keywords": ["automated", "feedback", "verification", "hallucination", "user as the instant verification layer"],
    },
    {
        "key": "signal-vs-noise",
        "label": "Insight signal vs notification noise",
        "pole_a": "high-value sparse insights",
        "pole_b": "spammy or low-value suggestion streams",
        "keywords": ["nudge", "spam", "frequency", "tempo", "noise", "boring", "thousands", "filter"],
    },
    {
        "key": "personalization-vs-generality",
        "label": "Personal reasoning mimicry vs generic AI behavior",
        "pole_a": "user-specific cognitive DNA",
        "pole_b": "generic summarization or generic recommendations",
        "keywords": ["cognitive dna", "reasoning primitive", "generic", "mimicry", "specific intuition", "user taste"],
    },
    {
        "key": "local-sovereignty-vs-convenience",
        "label": "Local sovereignty vs operational convenience",
        "pole_a": "local-first control and workspace continuity",
        "pole_b": "simpler cloud-like or greenfield setup paths",
        "keywords": ["local-first", "workspace", "one-click", "existing workspace", "trust", "install"],
    },
    {
        "key": "depth-vs-clarity",
        "label": "Cognitive depth vs usable product clarity",
        "pole_a": "rich hidden reasoning and deep context",
        "pole_b": "simple product framing and immediate user comprehension",
        "keywords": ["product idea", "value proposition", "benefit", "who would", "interface", "progressive disclosure"],
    },
]


GUARDRAIL_LIBRARY = [
    {
        "key": "not-generic-note-app",
        "statement": "Must not collapse into a generic note storage or retrieval product.",
        "keywords": ["smarter note-taking app", "vault", "store data", "digital filing cabinets"],
    },
    {
        "key": "not-unverified-black-box",
        "statement": "Must not surface opaque or low-precision insights without a verification loop.",
        "keywords": ["black box", "hallucination", "feedback loop", "verification", "90% error"],
    },
    {
        "key": "not-intrusive",
        "statement": "Must not become noisy, intrusive, or require constant active prompting from the user.",
        "keywords": ["chatbox trap", "spam", "constant", "ambient", "notification", "confronted"],
    },
    {
        "key": "not-weight-finetuning-dependent",
        "statement": "Must not depend on expensive model retraining when orchestration and graph adaptation can carry the learning.",
        "keywords": ["finetuning", "model training", "orchestrated reasoning", "graph and the search primitives"],
    },
    {
        "key": "not-greenfield-only",
        "statement": "Must not require a brand-new environment if it can live inside an existing OpenClaw workspace.",
        "keywords": ["existing workspace", "new workspace", "one-click", "install"],
    },
]


DECISION_LIBRARY = [
    {
        "family_key": "manual-vault-as-input-layer",
        "label": "Use a manually fed digital vault as the base input layer",
        "keywords": ["digital vault", "feed manually", "input notes", "existing graph network"],
        "statement": "Use a manually fed digital vault that embeds user inputs into an evolving graph network.",
        "relation_type": "IMPLEMENTS",
    },
    {
        "family_key": "reasoning-primitives-meta-layer",
        "label": "Use reasoning-primitives meta-analysis",
        "keywords": ["meta analytical layer", "reasoning primitives", "logic dna", "atomic moves"],
        "statement": "Analyze conversations through reusable reasoning primitives rather than only topic labels.",
        "relation_type": "DEFINES",
    },
    {
        "family_key": "user-feedback-verification-loop",
        "label": "Use user feedback as the verification layer",
        "keywords": ["user as the instant verification layer", "feedback loop", "instant feedback", "verify it faster"],
        "statement": "Use user feedback as the primary verification and path-strengthening loop for surfaced insights.",
        "relation_type": "TRAINS",
    },
    {
        "family_key": "orchestration-over-finetuning",
        "label": "Prefer orchestration over finetuning",
        "keywords": ["orchestrated reasoning system", "apply perfectly", "more effective there than in standard model training", "fine-tuning the map"],
        "statement": "Prefer orchestrated reasoning and adaptive graph logic over heavyweight model finetuning.",
        "relation_type": "IMPLEMENTS",
    },
    {
        "family_key": "openclaw-as-substrate",
        "label": "Use OpenClaw as the routing substrate",
        "keywords": ["openclaw", "routing system", "intelligence backbone", "wrapper", "orchestrated intelligence system"],
        "statement": "Use OpenClaw as the routing and integration substrate while the product owns the cognitive layer.",
        "relation_type": "IMPLEMENTS",
    },
    {
        "family_key": "progressive-disclosure-ui",
        "label": "Use progressive disclosure for the interface",
        "keywords": ["twitter/substack", "insight stream", "progressive disclosure", "tweet", "article", "expandable thought"],
        "statement": "Use a progressive-disclosure interface with lightweight nudges that expand into deeper thought structures.",
        "relation_type": "SHAPES",
    },
    {
        "family_key": "fractal-context-management",
        "label": "Use fractal context management",
        "keywords": ["fractal algorithms", "context bottleneck", "self-similar organization", "necessary context fields"],
        "statement": "Use fractal context management so each thought fragment can expose only the necessary context slice while still belonging to the whole.",
        "relation_type": "ORGANIZES",
    },
    {
        "family_key": "multimodal-synesthesia-expansion",
        "label": "Expand toward multimodal synesthetic linking",
        "keywords": ["digital synesthesia", "multimodal connections", "multimodal latent space", "audio files", "images"],
        "statement": "Expand the system toward multimodal linking so cross-sensory connections can be surfaced and traced.",
        "relation_type": "EXTENDS",
    },
    {
        "family_key": "existing-workspace-installation",
        "label": "Install into existing OpenClaw workspaces",
        "keywords": ["existing workspace", "new workspace", "one-click install", "one-command integration"],
        "statement": "Install the product into an existing OpenClaw workspace instead of forcing a separate global environment.",
        "relation_type": "DEPLOYS_IN",
    },
    {
        "family_key": "bayesian-surprise-as-relevance-filter",
        "label": "Use Bayesian surprise as the relevance filter",
        "keywords": ["bayesian surprise", "filter for relevance", "aha metric", "surprise engine", "latent warp"],
        "statement": "Use Bayesian surprise as the filter that distinguishes truly mind-changing connections from merely valid but obvious ones.",
        "relation_type": "SCORES",
    },
]


DOCUMENT_LIBRARY = [
    ("DMN", ["dmn", "default mode network"]),
    ("CEN", ["central executive network", "cen"]),
    ("Salience Network", ["salience network"]),
    ("RLHF", ["rlhf"]),
    ("Contextual Reinforcement Learning", ["contextual reinforcement learning", "reward model"]),
    ("Bayesian Surprise", ["bayesian surprise", "kl divergence"]),
    ("OpenClaw", ["openclaw"]),
    ("Graph-RAG", ["graph-rag"]),
    ("Digital Synesthesia", ["digital synesthesia", "artificial synesthesia"]),
    ("Fractal Context Model", ["fractal", "self-similar"]),
]


@dataclass
class Turn:
    turn_id: str
    timestamp: str
    user_query: str
    response: str
    website_count: Optional[int]
    source_markers: List[str]
    frames: List[str]
    tensions: List[str]
    guardrails: List[str]
    decisions: List[str]
    documents: List[str]


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "item"


def normalize_space(value: str) -> str:
    value = value.replace("\f", "\n")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    return value.strip()


def clean_response_text(value: str) -> str:
    kept = []
    for line in value.splitlines():
        stripped = line.strip()
        if DISCLAIMER_LINE in stripped or "Weitere Informationen" in stripped:
            continue
        if "Verknüpfungen Bilder Videos News" in stripped or "nutzt Produkte" in stripped:
            continue
        if any(pattern.match(stripped) for pattern in UI_NOISE_PATTERNS):
            continue
        kept.append(line)
    return normalize_space("\n".join(kept))


def keyword_present(text: str, keyword: str) -> bool:
    normalized_text = text.lower()
    normalized_keyword = keyword.lower().strip()
    if not normalized_keyword:
        return False
    if re.fullmatch(r"[a-z0-9-]+", normalized_keyword):
        pattern = r"(?<![a-z0-9])" + re.escape(normalized_keyword) + r"(?![a-z0-9])"
        return re.search(pattern, normalized_text) is not None
    return normalized_keyword in normalized_text


def extract_pdf_text(pdf_path: Path) -> str:
    return subprocess.check_output(["pdftotext", "-layout", str(pdf_path), "-"], text=True)


def split_markers(response: str) -> Tuple[str, List[str]]:
    markers = []
    for name, keywords in DOCUMENT_LIBRARY:
        lowered = response.lower()
        if any(keyword in lowered for keyword in keywords):
            markers.append(name)
    source_markers = re.findall(r"([A-Z][A-Za-z0-9 .&/-]*\+\d+|[A-Z][A-Za-z][A-Za-z .()/-]{1,40})", response)
    cleaned = []
    for marker in source_markers:
        marker = marker.strip()
        if marker in cleaned:
            continue
        if len(marker) < 3:
            continue
        if marker.endswith("Websites"):
            continue
        cleaned.append(marker)
    return response, markers + cleaned[:8]


def score_labels(text: str, library: List[Dict]) -> List[str]:
    scored = []
    for item in library:
        hits = sum(1 for keyword in item["keywords"] if keyword_present(text, keyword))
        if hits:
            scored.append((hits, item["label"]))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [label for _, label in scored[:3]]


def score_guardrails(text: str) -> List[str]:
    scored = []
    for item in GUARDRAIL_LIBRARY:
        hits = sum(1 for keyword in item["keywords"] if keyword_present(text, keyword))
        if hits:
            scored.append((hits, item["statement"]))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [statement for _, statement in scored[:4]]


def score_decisions(text: str) -> List[str]:
    scored = []
    for item in DECISION_LIBRARY:
        hits = sum(1 for keyword in item["keywords"] if keyword_present(text, keyword))
        if hits:
            scored.append((hits, item["label"]))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [label for _, label in scored[:3]]


def detect_documents(text: str) -> List[str]:
    found = []
    for name, keywords in DOCUMENT_LIBRARY:
        if any(keyword_present(text, keyword) for keyword in keywords):
            found.append(name)
    return found


def parse_turns(raw_text: str) -> List[Turn]:
    lines = raw_text.splitlines()
    timestamp_re = re.compile(r"^\s*(\d{1,2}:\d{2})\s*$")
    timestamp_indexes = [index for index, line in enumerate(lines) if timestamp_re.fullmatch(line)]
    turns: List[Turn] = []
    final_cursor = 0

    for turn_index, ts_index in enumerate(timestamp_indexes):
        timestamp = timestamp_re.fullmatch(lines[ts_index]).group(1)

        query_lines: List[str] = []
        cursor = ts_index - 1
        while cursor >= 0:
            candidate = lines[cursor].replace("\f", "").rstrip()
            if not candidate.strip():
                if query_lines:
                    break
                cursor -= 1
                continue
            if DISCLAIMER_LINE in candidate or "Weitere Informationen" in candidate:
                break
            query_lines.append(candidate.strip())
            cursor -= 1
        query_lines.reverse()
        user_query = normalize_space("\n".join(query_lines))

        next_ts_index = timestamp_indexes[turn_index + 1] if turn_index + 1 < len(timestamp_indexes) else len(lines)
        cursor = ts_index + 1
        website_count = None
        while cursor < next_ts_index and not lines[cursor].strip():
            cursor += 1
        if cursor < next_ts_index:
            match = re.fullmatch(r"\s*(\d+)\s+Websites\s*", lines[cursor])
            if match:
                website_count = int(match.group(1))
                cursor += 1
        response_lines: List[str] = []
        while cursor < next_ts_index:
            line = lines[cursor].replace("\f", "").rstrip()
            if DISCLAIMER_LINE in line:
                final_cursor = cursor + 1
                break
            if "Zur Beratung in rechtlichen Fragen" in line:
                final_cursor = cursor + 1
                break
            response_lines.append(line)
            cursor += 1
        final_cursor = max(final_cursor, cursor)
        response = clean_response_text("\n".join(response_lines))
        response, source_markers = split_markers(response)

        joined = f"{user_query}\n{response}"
        turn = Turn(
            turn_id=f"turn-{turn_index + 1:03d}",
            timestamp=timestamp,
            user_query=user_query,
            response=response,
            website_count=website_count,
            source_markers=source_markers,
            frames=score_labels(joined, FRAME_LIBRARY),
            tensions=score_labels(joined, TENSION_LIBRARY),
            guardrails=score_guardrails(joined),
            decisions=score_decisions(joined),
            documents=detect_documents(joined),
        )
        turns.append(turn)

    tail_lines = lines[final_cursor:]
    tail_cursor = 0
    while tail_cursor < len(tail_lines):
        candidate = tail_lines[tail_cursor].replace("\f", "").strip()
        if candidate and DISCLAIMER_LINE not in candidate and "Weitere Informationen" not in candidate:
            break
        tail_cursor += 1
    tail_lines = tail_lines[tail_cursor:]

    if tail_lines:
        query_lines: List[str] = []
        cursor = 0
        while cursor < len(tail_lines):
            line = tail_lines[cursor].replace("\f", "").rstrip()
            if not line.strip():
                if query_lines:
                    cursor += 1
                    break
                cursor += 1
                continue
            query_lines.append(line.strip())
            cursor += 1
        while cursor < len(tail_lines) and not tail_lines[cursor].strip():
            cursor += 1
        response = clean_response_text("\n".join(line.replace("\f", "").rstrip() for line in tail_lines[cursor:]))
        user_query = normalize_space("\n".join(query_lines))
        if user_query and response:
            response, source_markers = split_markers(response)
            joined = f"{user_query}\n{response}"
            turns.append(
                Turn(
                    turn_id=f"turn-{len(turns) + 1:03d}",
                    timestamp="undated-tail",
                    user_query=user_query,
                    response=response,
                    website_count=None,
                    source_markers=source_markers,
                    frames=score_labels(joined, FRAME_LIBRARY),
                    tensions=score_labels(joined, TENSION_LIBRARY),
                    guardrails=score_guardrails(joined),
                    decisions=score_decisions(joined),
                    documents=detect_documents(joined),
                )
            )

    return turns


def top_counter(items: List[str], limit: int = 8) -> List[Tuple[str, int]]:
    counter = Counter(item for item in items if item)
    return counter.most_common(limit)


def build_session_packet(session_id: str, pdf_path: Path, raw_text: str, turns: List[Turn]) -> Dict:
    all_frames = [frame for turn in turns for frame in turn.frames]
    all_decisions = [decision for turn in turns for decision in turn.decisions]
    all_docs = [document for turn in turns for document in turn.documents]
    summary = (
        "The conversation moves from an inquiry into the inner world and subconscious creativity "
        "toward a product architecture for an AI-assisted cognitive system that uses reasoning "
        "primitives, feedback loops, Bayesian surprise, OpenClaw orchestration, fractal context "
        "management, and multimodal expansion."
    )
    return {
        "schema_version": "session_packet_v1",
        "session_id": session_id,
        "source": {
            "classification": "candidate",
            "status": "parsed_from_pdf",
            "type": "pdf-conversation-export",
            "ref": str(pdf_path),
        },
        "summary": {
            "one_paragraph": summary,
            "core_problem": "How to externalize and augment subconscious or creative cognition without collapsing into generic note-taking, noisy automation, or opaque black-box outputs.",
            "core_motion": "Shift from cognitive theory into a concrete product architecture and validation path for an inner-world intelligence system.",
        },
        "segment_stats": {
            "turn_count": len(turns),
            "average_query_words": round(sum(len(turn.user_query.split()) for turn in turns) / max(1, len(turns)), 2),
            "average_response_words": round(sum(len(turn.response.split()) for turn in turns) / max(1, len(turns)), 2),
            "questions_with_sources": sum(1 for turn in turns if turn.website_count is not None),
            "frames": dict(top_counter(all_frames, 12)),
            "decisions": dict(top_counter(all_decisions, 12)),
            "documents": dict(top_counter(all_docs, 12)),
        },
        "top_concept_candidates": [
            {"label": label, "count": count}
            for label, count in top_counter(all_frames + all_decisions + all_docs, 10)
        ],
    }


def build_structure_map(turns: List[Turn]) -> Dict:
    windows = []
    for index, turn in enumerate(turns, start=1):
        windows.append(
            {
                "window_id": f"window-{index:03d}",
                "turn_id": turn.turn_id,
                "timestamp": turn.timestamp,
                "dominant_frames": turn.frames,
                "decisions": turn.decisions,
                "guardrails": turn.guardrails,
                "documents": turn.documents,
            }
        )
    repeated = top_counter([frame for turn in turns for frame in turn.frames], 10)
    shifts = []
    for prev, cur in zip(turns, turns[1:]):
        prev_frames = set(prev.frames)
        cur_frames = set(cur.frames)
        if prev_frames != cur_frames:
            shifts.append(
                {
                    "from_turn": prev.turn_id,
                    "to_turn": cur.turn_id,
                    "from_frames": prev.frames,
                    "to_frames": cur.frames,
                }
            )
    return {
        "schema_version": "structure_map_v1",
        "turn_windows": windows,
        "repeated_anchors": [{"label": label, "frequency": count} for label, count in repeated],
        "topic_shift_points": shifts,
    }


def build_fragment_observations(turns: List[Turn]) -> Dict:
    observations = []
    for turn in turns:
        observations.append(
            {
                "turn_id": turn.turn_id,
                "timestamp": turn.timestamp,
                "query": turn.user_query,
                "frames": turn.frames,
                "tensions": turn.tensions,
                "decisions": turn.decisions,
                "documents": turn.documents,
            }
        )
    return {
        "observation_count": len(observations),
        "observations": observations,
        "top_labels": [label for label, _ in top_counter([frame for turn in turns for frame in turn.frames], 8)],
    }


def infer_session_aim(turns: List[Turn]) -> str:
    return (
        "Determine whether an AI-assisted system can model, preserve, and productize the inner world "
        "as a structured cognitive environment rather than a passive note archive."
    )


def infer_central_thread(turns: List[Turn]) -> str:
    return (
        "The conversation progressively turns inner-world psychology into a product thesis, then pressure-tests "
        "that thesis through architecture, learning loops, interface design, deployment, and business scrutiny."
    )


def infer_latent_question(turns: List[Turn]) -> str:
    return (
        "How can a system augment subconscious reasoning, surface meaningful latent connections, and stay "
        "useful, trustworthy, and installable enough to become a real product?"
    )


def build_stream_arc(turns: List[Turn]) -> Dict:
    frame_sequence = []
    for index, turn in enumerate(turns, start=1):
        phase = "opening" if index <= 4 else "closing" if index > len(turns) - 4 else "middle"
        frame_sequence.append(
            {
                "phase": phase,
                "window": f"window-{index:03d}",
                "frame": turn.frames[0] if turn.frames else "Unclassified",
            }
        )
    tensions = [label for label, _ in top_counter([t for turn in turns for t in turn.tensions], 5)]
    guardrails = [label for label, _ in top_counter([g for turn in turns for g in turn.guardrails], 5)]
    return {
        "session_aim": infer_session_aim(turns),
        "central_thread": infer_central_thread(turns),
        "latent_question": infer_latent_question(turns),
        "movement_pattern": "progressive concretization from cognitive theory into system design",
        "governing_tensions": tensions,
        "frame_sequence": frame_sequence,
        "guardrails": guardrails,
        "movement_arc": [
            "Opening: the conversation starts by mapping what the inner world and subconscious creativity are.",
            "Expansion: it then asks whether these processes can be automated or augmented by AI.",
            "Concretization: the stream hardens into product architecture choices around vaults, graphs, reasoning primitives, feedback loops, Bayesian surprise, and OpenClaw.",
            "Validation: later turns test interface patterns, market viability, installation shape, and unresolved product decisions.",
            "Closure: the conversation ends by reaffirming Bayesian surprise as the relevance filter inside the broader architecture.",
        ],
    }


def build_session_synthesis(turns: List[Turn], stream_arc: Dict) -> Dict:
    resolved = []
    for family in DECISION_LIBRARY:
        for turn in turns:
            lowered = f"{turn.user_query}\n{turn.response}".lower()
            if any(keyword.lower() in lowered for keyword in family["keywords"]):
                resolved.append(
                    {
                        "label": family["label"],
                        "statement": family["statement"],
                        "first_seen_in": turn.turn_id,
                    }
                )
                break
    stable_findings = [
        {"kind": "session-aim", "value": stream_arc["session_aim"]},
        {"kind": "central-thread", "value": stream_arc["central_thread"]},
        {"kind": "latent-question", "value": stream_arc["latent_question"]},
        {"kind": "movement-pattern", "value": stream_arc["movement_pattern"]},
    ]
    return {
        "synthesis_headline": (
            "The chat defines an 'inner world' product as a cognitive augmentation system that uses "
            "personal reasoning patterns, feedback loops, Bayesian surprise, and graph/orchestration infrastructure "
            "to surface non-obvious insights."
        ),
        "stable_findings": stable_findings,
        "resolved_positions": resolved,
        "top_frames": [label for label, _ in top_counter([frame for turn in turns for frame in turn.frames], 8)],
        "top_documents": [label for label, _ in top_counter([doc for turn in turns for doc in turn.documents], 8)],
        "top_guardrails": [label for label, _ in top_counter([g for turn in turns for g in turn.guardrails], 8)],
    }


def build_decision_attachments(turns: List[Turn]) -> Dict:
    attachments = []
    for family in DECISION_LIBRARY:
        first_turn = None
        for turn in turns:
            lowered = f"{turn.user_query}\n{turn.response}".lower()
            if any(keyword.lower() in lowered for keyword in family["keywords"]):
                first_turn = turn
                break
        if not first_turn:
            continue
        attachments.append(
            {
                "family_key": family["family_key"],
                "label": family["label"],
                "statement": family["statement"],
                "relation_type": family["relation_type"],
                "turn_id": first_turn.turn_id,
                "frames": first_turn.frames,
                "guardrails": first_turn.guardrails,
            }
        )
    return {"resolutions": attachments}


def build_graph_update_plan(session_id: str, attachments: Dict) -> Dict:
    nodes = []
    edges = []
    session_node = {"type": "Session", "id": f"session:{session_id}"}
    nodes.append(session_node)
    for item in attachments["resolutions"]:
        resolution_id = f"decision-resolution:{session_id}-{item['family_key']}"
        nodes.append({"type": "DecisionResolution", "id": resolution_id, "label": item["label"]})
        edges.append({"type": "RESOLVED_IN_SESSION", "source": resolution_id, "target": session_node["id"]})
        for frame in item["frames"]:
            frame_id = f"frame:{slugify(frame)}"
            nodes.append({"type": "Frame", "id": frame_id, "label": frame})
            edges.append({"type": "OPERATES_IN", "source": resolution_id, "target": frame_id})
        for guardrail in item["guardrails"]:
            guardrail_id = f"guardrail:{slugify(guardrail)}"
            nodes.append({"type": "Guardrail", "id": guardrail_id, "label": guardrail})
            edges.append({"type": "PROTECTS", "source": resolution_id, "target": guardrail_id})
    unique_nodes = {node["id"]: node for node in nodes}
    return {"nodes": list(unique_nodes.values()), "edges": edges}


def render_markdown(title: str, sections: List[Tuple[str, List[str]]]) -> str:
    lines = [f"# {title}", ""]
    for heading, body in sections:
        lines.append(f"## {heading}")
        lines.append("")
        lines.extend(body or ["- n/a"])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, payload: Dict) -> None:
    write(path, json.dumps(payload, indent=2, ensure_ascii=False) + "\n")


def ordered_conversation_markdown(turns: List[Turn]) -> str:
    blocks = ["# Ordered Conversation", ""]
    for turn in turns:
        blocks.append(f"## {turn.turn_id} — {turn.timestamp}")
        blocks.append("")
        blocks.append("**User**")
        blocks.append("")
        blocks.append(turn.user_query or "_empty_")
        blocks.append("")
        blocks.append("**Assistant / Search Answer**")
        blocks.append("")
        blocks.append(turn.response or "_empty_")
        blocks.append("")
        meta = []
        if turn.website_count is not None:
            meta.append(f"website_count={turn.website_count}")
        if turn.frames:
            meta.append("frames=" + ", ".join(turn.frames))
        if turn.decisions:
            meta.append("decisions=" + ", ".join(turn.decisions))
        if turn.documents:
            meta.append("documents=" + ", ".join(turn.documents))
        blocks.append("**Meta tags**")
        blocks.append("")
        blocks.extend(f"- {item}" for item in meta or ["none"])
        blocks.append("")
    return "\n".join(blocks).rstrip() + "\n"


def document_artifacts_markdown(turns: List[Turn]) -> str:
    doc_to_turns: Dict[str, List[str]] = defaultdict(list)
    for turn in turns:
        for document in turn.documents:
            doc_to_turns[document].append(turn.turn_id)
    lines = ["# Document And Artifact Capture", ""]
    lines.append("## Referenced Concepts And Frameworks")
    lines.append("")
    for document, turn_ids in sorted(doc_to_turns.items()):
        lines.append(f"- {document}: mentioned in {', '.join(turn_ids)}")
    lines.append("")
    lines.append("## Output Artifacts")
    lines.append("")
    lines.extend(
        [
            "- raw_extraction.txt: verbatim `pdftotext -layout` output from the PDF",
            "- turns.json: normalized ordered turn structure",
            "- ordered_conversation.md: human-readable turn-by-turn reconstruction",
            "- session_packet / structure_map / fragment_observations / stream_arc / session_synthesis / decision_attachments / graph_update_plan_v1: OpenClaw-style meta bundle",
        ]
    )
    lines.append("")
    return "\n".join(lines)


def turns_json(turns: List[Turn]) -> List[Dict]:
    return [
        {
            "turn_id": turn.turn_id,
            "timestamp": turn.timestamp,
            "user_query": turn.user_query,
            "response": turn.response,
            "website_count": turn.website_count,
            "source_markers": turn.source_markers,
            "frames": turn.frames,
            "tensions": turn.tensions,
            "guardrails": turn.guardrails,
            "decisions": turn.decisions,
            "documents": turn.documents,
        }
        for turn in turns
    ]


def index_markdown(bundle_dir: Path, session_id: str) -> str:
    files = [
        "raw_extraction.txt",
        "turns.json",
        "ordered_conversation.md",
        "document_artifacts.md",
        "session_packet.md",
        "structure_map.md",
        "fragment_observations.md",
        "stream_arc.md",
        "session_synthesis.md",
        "decision_attachments.md",
        "graph_update_plan_v1.md",
        "manifest.json",
    ]
    lines = [f"# Meta Observatory Review — {session_id}", "", "## Artifacts", ""]
    for file_name in files:
        lines.append(f"- [{file_name}]({file_name})")
    lines.append("")
    return "\n".join(lines)


def build_markdown_outputs(bundle_dir: Path, session_id: str, turns: List[Turn], packet: Dict, structure_map: Dict, fragment_obs: Dict, stream_arc: Dict, synthesis: Dict, decision_attachments: Dict, graph_update_plan: Dict) -> None:
    write(bundle_dir / "ordered_conversation.md", ordered_conversation_markdown(turns))
    write(bundle_dir / "document_artifacts.md", document_artifacts_markdown(turns))

    packet_md = render_markdown(
        f"Session Packet — {session_id}",
        [
            ("Source", [f"- classification: {packet['source']['classification']}", f"- status: {packet['source']['status']}", f"- type: {packet['source']['type']}", f"- ref: {packet['source']['ref']}"]),
            ("Summary", [f"- One paragraph: {packet['summary']['one_paragraph']}", f"- Core problem: {packet['summary']['core_problem']}", f"- Core motion: {packet['summary']['core_motion']}"]),
            ("Stats", [f"- turn_count: {packet['segment_stats']['turn_count']}", f"- average_query_words: {packet['segment_stats']['average_query_words']}", f"- average_response_words: {packet['segment_stats']['average_response_words']}", f"- questions_with_sources: {packet['segment_stats']['questions_with_sources']}"]),
            ("Top Concept Candidates", [f"- {item['label']} ({item['count']})" for item in packet["top_concept_candidates"]]),
        ],
    )
    write(bundle_dir / "session_packet.md", packet_md)

    structure_md = render_markdown(
        f"Structure Map — {session_id}",
        [
            ("Repeated Anchors", [f"- {item['label']} (windows: {item['frequency']})" for item in structure_map["repeated_anchors"]]),
            ("Topic Shift Points", [f"- {item['from_turn']} -> {item['to_turn']}: {', '.join(item['to_frames']) or 'Unclassified'}" for item in structure_map["topic_shift_points"]]),
        ],
    )
    write(bundle_dir / "structure_map.md", structure_md)

    obs_md = render_markdown(
        f"Fragment Observations — {session_id}",
        [
            (
                "Top Observation Labels",
                [f"- {label}" for label in fragment_obs["top_labels"]],
            ),
            (
                "Turn Observations",
                [
                    f"- {item['turn_id']} ({item['timestamp']}): {item['query']} -> frames: {', '.join(item['frames']) or 'none'}; decisions: {', '.join(item['decisions']) or 'none'}"
                    for item in fragment_obs["observations"]
                ],
            ),
        ],
    )
    write(bundle_dir / "fragment_observations.md", obs_md)

    stream_md = render_markdown(
        f"Stream Arc — {session_id}",
        [
            ("Session Aim", [stream_arc["session_aim"]]),
            ("Central Thread", [stream_arc["central_thread"]]),
            ("Latent Question", [stream_arc["latent_question"]]),
            ("Movement Pattern", [stream_arc["movement_pattern"]]),
            ("Governing Tensions", [f"- {item}" for item in stream_arc["governing_tensions"]]),
            ("Frame Sequence", [f"- {item['phase']}: {item['frame']} ({item['window']})" for item in stream_arc["frame_sequence"]]),
            ("Guardrails", [f"- {item}" for item in stream_arc["guardrails"]]),
            ("Movement Arc", [f"- {item}" for item in stream_arc["movement_arc"]]),
        ],
    )
    write(bundle_dir / "stream_arc.md", stream_md)

    synthesis_md = render_markdown(
        f"Session Synthesis — {session_id}",
        [
            ("Synthesis Headline", [synthesis["synthesis_headline"]]),
            ("Stable Findings", [f"- {item['kind']}: {item['value']}" for item in synthesis["stable_findings"]]),
            ("Resolved Positions", [f"- {item['label']}: {item['statement']} (first seen in {item['first_seen_in']})" for item in synthesis["resolved_positions"]]),
            ("Top Frames", [f"- {item}" for item in synthesis["top_frames"]]),
            ("Top Documents", [f"- {item}" for item in synthesis["top_documents"]]),
            ("Top Guardrails", [f"- {item}" for item in synthesis["top_guardrails"]]),
        ],
    )
    write(bundle_dir / "session_synthesis.md", synthesis_md)

    decisions_md = render_markdown(
        f"Decision Attachments — {session_id}",
        [
            (
                "Likely Resolved Positions",
                [
                    f"- {item['label']}: {item['statement']} -> turn:{item['turn_id']}, frames:{', '.join(item['frames']) or 'none'}, guardrails:{' | '.join(item['guardrails']) or 'none'}"
                    for item in decision_attachments["resolutions"]
                ],
            )
        ],
    )
    write(bundle_dir / "decision_attachments.md", decisions_md)

    graph_md = render_markdown(
        f"Graph Update Plan — {session_id}",
        [
            ("Nodes", [f"- {item['type']}: {item['id']}" for item in graph_update_plan["nodes"]]),
            ("Edges", [f"- {item['type']}: {item['source']} -> {item['target']}" for item in graph_update_plan["edges"]]),
        ],
    )
    write(bundle_dir / "graph_update_plan_v1.md", graph_md)

    write(bundle_dir / "INDEX.md", index_markdown(bundle_dir, session_id))


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OpenClaw-style meta-observatory artifacts from a PDF conversation export.")
    parser.add_argument("--pdf", required=True, help="Absolute path to the PDF file.")
    parser.add_argument("--output-dir", required=True, help="Directory where artifacts should be written.")
    args = parser.parse_args()

    pdf_path = Path(args.pdf).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    date_prefix = datetime.now().strftime("%Y-%m-%d")
    session_stem = slugify(pdf_path.stem)[:80]
    session_id = f"pdf-{date_prefix}-{session_stem}"
    bundle_dir = output_dir / session_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    raw_text = extract_pdf_text(pdf_path)
    turns = parse_turns(raw_text)

    packet = build_session_packet(session_id, pdf_path, raw_text, turns)
    structure_map = build_structure_map(turns)
    fragment_obs = build_fragment_observations(turns)
    stream_arc = build_stream_arc(turns)
    synthesis = build_session_synthesis(turns, stream_arc)
    decision_attachments = build_decision_attachments(turns)
    graph_update_plan = build_graph_update_plan(session_id, decision_attachments)

    write(bundle_dir / "raw_extraction.txt", raw_text)
    write_json(bundle_dir / "turns.json", {"session_id": session_id, "turn_count": len(turns), "turns": turns_json(turns)})
    write_json(bundle_dir / "session_packet.json", packet)
    write_json(bundle_dir / "structure_map.json", structure_map)
    write_json(bundle_dir / "fragment_observations.json", fragment_obs)
    write_json(bundle_dir / "stream_arc.json", stream_arc)
    write_json(bundle_dir / "session_synthesis.json", synthesis)
    write_json(bundle_dir / "decision_attachments.json", decision_attachments)
    write_json(bundle_dir / "graph_update_plan_v1.json", graph_update_plan)

    build_markdown_outputs(
        bundle_dir,
        session_id,
        turns,
        packet,
        structure_map,
        fragment_obs,
        stream_arc,
        synthesis,
        decision_attachments,
        graph_update_plan,
    )

    manifest = {
        "session_id": session_id,
        "pdf_path": str(pdf_path),
        "generated_at": datetime.now().isoformat(),
        "turn_count": len(turns),
        "bundle_dir": str(bundle_dir),
        "files": sorted(path.name for path in bundle_dir.iterdir()),
    }
    write_json(bundle_dir / "manifest.json", manifest)
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
