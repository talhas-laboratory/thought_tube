from __future__ import annotations

META_LAYER_KINDS = [
    "signal_frame",
    "interpretation",
    "theme",
    "discussion",
    "direction",
    "tension",
    "question",
    "guardrail",
    "shared_primitive",
    "adjacent_concept",
    "transfer_target",
    "why_it_matters",
    "review_item",
    "contradiction",
]

META_LAYER_FILES = {
    "signal_frame": "signal_frames.jsonl",
    "interpretation": "interpretations.jsonl",
    "theme": "themes.jsonl",
    "discussion": "discussions.jsonl",
    "direction": "directions.jsonl",
    "tension": "tensions.jsonl",
    "question": "questions.jsonl",
    "guardrail": "guardrails.jsonl",
    "shared_primitive": "shared_primitives.jsonl",
    "adjacent_concept": "adjacent_concepts.jsonl",
    "transfer_target": "transfer_targets.jsonl",
    "why_it_matters": "why_it_matters_frames.jsonl",
    "review_item": "review_items.jsonl",
    "contradiction": "contradictions.jsonl",
}


REVIEW_STATUSES = [
    "ready_for_review",
    "approved_for_surface",
    "needs_human_review",
    "insufficient_quality",
    "dismissed",
]
