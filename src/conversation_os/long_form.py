from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any, Dict, List

from .storage import read_json
from .vault_ingest import shorten, tokenize


_LONG_FORM_BLUEPRINT_PATH = Path(
    "docs/research/substack-article-structure-2026-04-16/long_form/long_form_blueprint.json"
)
_LONG_FORM_RUNTIME_CONFIG_PATH = Path("product/inner_world_v1/config/long_form.json")

_DEFAULT_RUNTIME_CONFIG = {
    "profile": "explainer_default",
    "profiles": {
        "explainer_default": {
            "modules": {
                "entry-vector": {"enabled": True, "weight": "light"},
                "object-field": {"enabled": True, "weight": "medium"},
                "evidence-ladder": {"enabled": True, "weight": "heavy"},
                "decisions-and-implications": {"enabled": True, "weight": "medium"},
                "open-questions-and-boundaries": {"enabled": True, "weight": "medium"},
            }
        },
        "narrative_leaning": {
            "modules": {
                "entry-vector": {"enabled": True, "weight": "heavy"},
                "object-field": {"enabled": True, "weight": "light"},
                "tension-and-stakes": {"enabled": True, "weight": "medium"},
                "evidence-ladder": {"enabled": True, "weight": "medium"},
                "decisions-and-implications": {"enabled": True, "weight": "light"},
                "open-questions-and-boundaries": {"enabled": True, "weight": "light"},
                "close-and-next-move": {"enabled": True, "weight": "heavy"},
            }
        },
        "research_heavy": {
            "modules": {
                "entry-vector": {"enabled": True, "weight": "light"},
                "object-field": {"enabled": True, "weight": "medium"},
                "evidence-ladder": {"enabled": True, "weight": "heavy"},
                "decisions-and-implications": {"enabled": True, "weight": "medium"},
                "open-questions-and-boundaries": {"enabled": True, "weight": "heavy"},
            }
        },
        "pattern_transfer": {
            "modules": {
                "entry-vector": {"enabled": True, "weight": "light"},
                "tension-and-stakes": {"enabled": True, "weight": "medium"},
                "pattern-and-transfer": {"enabled": True, "weight": "heavy"},
                "decisions-and-implications": {"enabled": True, "weight": "medium"},
                "open-questions-and-boundaries": {"enabled": True, "weight": "medium"},
            }
        },
    },
    "modules": {},
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _soften_surface_text(text: str) -> str:
    softened = (text or "").strip()
    softened = softened.replace("productive tension", "living friction")
    softened = softened.replace(
        "reveals a reusable move in the vault",
        "keeps shifting where attention wants to land",
    )
    softened = softened.replace(
        "The same undercurrent keeps showing up from two directions.",
        "The same undercurrent keeps arriving from two directions.",
    )
    if softened.lower().startswith("this connection matters because "):
        softened = softened[len("This connection matters because ") :]
    return softened


def _clean_source_line(text: str, limit: int | None = 160) -> str:
    cleaned = re.sub(r"[*_`>#]+", " ", text or "")
    cleaned = cleaned.replace("–", " ").replace("—", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;-/")
    if limit is None:
        return cleaned.rstrip(" .")
    return shorten(cleaned, limit).rstrip(" .")


def _source_text(snippet: Dict[str, Any], *, shorten_to: int | None = None) -> str:
    source_text = snippet.get("content") or snippet.get("excerpt", "")
    return _clean_source_line(source_text, shorten_to)


def _source_title(snippet: Dict[str, Any]) -> str:
    return (snippet.get("full_title") or snippet.get("title") or "").strip()


def _human_line(text: str) -> bool:
    tokens = tokenize(text)
    if not tokens:
        return False
    markers = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "keep",
        "keeps",
        "should",
        "because",
        "before",
        "not",
        "with",
        "without",
        "can",
        "must",
        "need",
        "needs",
    }
    return any(token in markers for token in tokens)


def _source_voice(snippets: List[Dict[str, Any]], limit: int | None = 160) -> str:
    for snippet in snippets:
        line = _source_text(snippet, shorten_to=limit)
        if line and _human_line(line):
            return line
    return ""


def _weight_value(weight: str, light: int, medium: int, heavy: int) -> int:
    return {"light": light, "medium": medium, "heavy": heavy}.get(weight, medium)


def _scope_boundary(packet: Dict[str, Any]) -> str:
    review_status = packet.get("review_status")
    if review_status == "approved_for_surface":
        return "Treat this as a grounded expansion, not a permanent rule."
    if review_status == "ready_for_review":
        return "Treat this as a live interpretation that still needs review pressure."
    return "Treat this as provisional and keep it close to the source material."


def _confidence_posture(packet: Dict[str, Any]) -> str:
    evidence_status = packet.get("evidence_status", "speculative")
    confidence = float(packet.get("confidence_score", 0.0))
    if evidence_status == "grounded" and confidence >= 0.75:
        return "The grounding is strong enough to make the claim usable, but not strong enough to treat it as settled."
    if evidence_status == "grounded":
        return "The signal is grounded, but it still benefits from explicit review before it becomes a default."
    return "The pattern is suggestive rather than settled, so the article should stay honest about that."


class LongFormConfigLoader:
    def load(self, root: Path, overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
        blueprint_path = root / _LONG_FORM_BLUEPRINT_PATH
        blueprint = read_json(blueprint_path, default={})
        runtime_config = _deep_merge(
            _DEFAULT_RUNTIME_CONFIG,
            read_json(root / _LONG_FORM_RUNTIME_CONFIG_PATH, default={}) or {},
        )
        runtime_config = _deep_merge(runtime_config, overrides or {})
        profile = runtime_config.get("profile") or blueprint.get("default_profile") or "explainer_default"
        profile_config = runtime_config.get("profiles", {}).get(profile, {})
        modules = []
        blueprint_dir = blueprint_path.parent
        for module in blueprint.get("modules", []):
            manifest_path = blueprint_dir / Path(module["manifest_path"])
            manifest = read_json(manifest_path, default={})
            module_id = module["id"]
            global_override = runtime_config.get("modules", {}).get(module_id, {})
            profile_override = profile_config.get("modules", {}).get(module_id, {})
            enabled = global_override.get(
                "enabled",
                profile_override.get(
                    "enabled",
                    module.get("required_by_default", manifest.get("required_by_default", False)),
                ),
            )
            weight = global_override.get("weight", profile_override.get("weight", "medium"))
            modules.append(
                {
                    "id": module_id,
                    "title": manifest.get("title", module_id.replace("-", " ").title()),
                    "position": global_override.get("position", module.get("default_position", 999)),
                    "required_by_default": module.get(
                        "required_by_default", manifest.get("required_by_default", False)
                    ),
                    "enabled": enabled,
                    "weight": weight,
                    "manifest": manifest,
                }
            )
        modules.sort(key=lambda item: item["position"])
        return {
            "blueprint_id": blueprint.get("id", "long-form"),
            "style_posture": blueprint.get("style_posture", "structured_explainer"),
            "profile": profile,
            "selected_algorithms": blueprint.get("selected_algorithms", []),
            "conditional_algorithms": blueprint.get("conditional_algorithms", []),
            "modules": modules,
        }


class LongFormContextBuilder:
    def build(
        self,
        packet: Dict[str, Any],
        snippets: List[Dict[str, Any]],
        title: str,
        short_text: str,
        resolved_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        source_voice = _source_voice(snippets, None)
        shared_terms = [term.replace("-", " ") for term in packet.get("shared_terms", []) if term]
        source_titles = [_source_title(snippet) for snippet in snippets if _source_title(snippet)]
        unresolved_questions = packet.get("unresolved_questions") or [
            "What part of this still needs explicit review?"
        ]
        enabled_modules = [module["id"] for module in resolved_config["modules"] if module["enabled"]]
        thesis = _soften_surface_text(packet.get("what_changed", short_text))
        why_now = _soften_surface_text(packet.get("why_it_matters_now", short_text))
        next_action = packet.get("next_action", "Stay with the expansion long enough to see whether it changes direction.")
        opening_scene = source_voice or short_text
        object_components = shared_terms[:4] or [packet.get("shared_primitive_label", "core pattern")]
        evidence_layers = [
            {
                "label": Path(snippet.get("source_ref", "source")).name,
                "title": _source_title(snippet),
                "excerpt": _source_text(snippet, shorten_to=None),
                "source_ref": snippet.get("source_ref", ""),
            }
            for snippet in snippets
            if snippet.get("excerpt")
        ]
        pattern_name = next_action.rstrip(".") if next_action else packet.get("shared_primitive_label", "Reusable pattern")
        return {
            "title": title,
            "short_text": short_text,
            "module_sequence": enabled_modules,
            "signal_frame": {
                "headline": title,
                "subtitle": short_text,
                "scope_boundary": _scope_boundary(packet),
            },
            "entry_vector": {
                "opening_scene": opening_scene,
                "hook_type": "source_voice" if source_voice else "summary",
                "entry_pressure": why_now,
            },
            "thesis_and_reader_map": {
                "thesis_statement": thesis,
                "reader_map": enabled_modules,
                "section_expectation": "Move from claim to tension, then through evidence, pattern, and next move.",
            },
            "object_field": {
                "object_map": object_components,
                "named_components": source_titles[:3],
                "relationship_overview": packet.get("shared_primitive_label", "Cross-source pattern"),
            },
            "transformation_path": {
                "steps": [thesis, why_now, next_action],
            },
            "decisions": {
                "default_position": next_action,
                "implications": [
                    "Structure should arrive after the signal survives contact with evidence.",
                    "The article should clarify the move without pretending the uncertainty is gone.",
                ],
            },
            "guardrails": {
                "scope_boundary": _scope_boundary(packet),
                "anti_goals": [
                    "Do not confuse legibility with truth.",
                    "Do not let the article collapse into generic productivity advice.",
                ],
            },
            "tensions": {
                "tension_pairs": [
                    "usable structure vs fidelity to the raw material",
                    "clarity for the reader vs premature commitment by the system",
                ],
                "stakes_statement": why_now,
                "live_pressure": thesis,
            },
            "contradictions": {
                "items": [],
            },
            "evidence_ladder": {
                "examples": evidence_layers,
                "confidence_posture": _confidence_posture(packet),
            },
            "open_questions": {
                "items": unresolved_questions[:4],
                "scope_limits": _scope_boundary(packet),
            },
            "pattern_transfer": {
                "reasoning_primitive": packet.get("shared_primitive_label", "Pattern"),
                "pattern_name": pattern_name,
                "transfer_layer": (
                    "The same move can apply anywhere a system needs to preserve weak signals long enough for the real pattern to appear."
                ),
            },
            "source_refs": packet.get("source_refs", []),
        }


def _build_promise_frame(context: Dict[str, Any], module_config: Dict[str, Any]) -> Dict[str, Any]:
    frame = context["signal_frame"]
    markdown = "\n".join(
        [
            f"# {frame['headline']}",
            "",
            frame["subtitle"],
            "",
            f"*{frame['scope_boundary']}*",
        ]
    )
    return {
        "module_id": module_config["id"],
        "title": module_config["title"],
        "enabled": True,
        "weight": module_config["weight"],
        "markdown": markdown,
        "source_refs": context["source_refs"],
        "evidence_refs": [],
        "data": frame,
    }


def _build_entry_vector(context: Dict[str, Any], module_config: Dict[str, Any]) -> Dict[str, Any]:
    entry = context["entry_vector"]
    weight = module_config["weight"]
    extra_line = ""
    if weight == "heavy":
        extra_line = "That opening pressure matters because once the system moves too quickly, the explanation becomes smoother than the thing it is trying to explain."
    markdown_lines = [
        "## Where this opens",
        "",
        entry["opening_scene"],
        "",
        entry["entry_pressure"],
    ]
    if extra_line:
        markdown_lines.extend(["", extra_line])
    return {
        "module_id": module_config["id"],
        "title": "Where this opens",
        "enabled": True,
        "weight": weight,
        "markdown": "\n".join(markdown_lines),
        "source_refs": context["source_refs"],
        "evidence_refs": [],
        "data": entry,
    }


def _build_thesis_and_reader_map(context: Dict[str, Any], module_config: Dict[str, Any]) -> Dict[str, Any]:
    thesis = context["thesis_and_reader_map"]
    module_labels = {
        "tension-and-stakes": "the central tension",
        "evidence-ladder": "what the material actually shows",
        "pattern-and-transfer": "the reusable pattern",
        "close-and-next-move": "what to do with it",
    }
    path = [module_labels[item] for item in thesis["reader_map"] if item in module_labels]
    reader_map = ""
    if path:
        if len(path) == 1:
            reader_map = f"From here, the piece moves into {path[0]}."
        else:
            reader_map = f"From here, the piece moves through {', '.join(path[:-1])}, and then {path[-1]}."
    markdown = "\n".join(
        [
            "## The core claim",
            "",
            thesis["thesis_statement"],
            "",
            reader_map or thesis["section_expectation"],
        ]
    )
    return {
        "module_id": module_config["id"],
        "title": "The core claim",
        "enabled": True,
        "weight": module_config["weight"],
        "markdown": markdown,
        "source_refs": context["source_refs"],
        "evidence_refs": [],
        "data": thesis,
    }


def _build_object_field(context: Dict[str, Any], module_config: Dict[str, Any]) -> Dict[str, Any]:
    object_field = context["object_field"]
    weight = module_config["weight"]
    term_limit = _weight_value(weight, 2, 4, 5)
    source_limit = _weight_value(weight, 1, 2, 3)
    bullets = [f"- {item}" for item in object_field["object_map"][:term_limit]]
    bullets.extend(f"- Source: {item}" for item in object_field["named_components"][:source_limit])
    markdown = "\n".join(
        [
            "## What is in the field",
            "",
            f"The live structure here is organized around {object_field['relationship_overview'].lower()}.",
            "",
            *bullets,
        ]
    )
    return {
        "module_id": module_config["id"],
        "title": "What is in the field",
        "enabled": True,
        "weight": weight,
        "markdown": markdown,
        "source_refs": context["source_refs"],
        "evidence_refs": [],
        "data": object_field,
    }


def _build_tension_and_stakes(context: Dict[str, Any], module_config: Dict[str, Any]) -> Dict[str, Any]:
    tension = context["tensions"]
    bullets = [f"- {item}" for item in tension["tension_pairs"][:2]]
    markdown = "\n".join(
        [
            "## The central tension",
            "",
            tension["live_pressure"],
            "",
            tension["stakes_statement"],
            "",
            *bullets,
        ]
    )
    return {
        "module_id": module_config["id"],
        "title": "The central tension",
        "enabled": True,
        "weight": module_config["weight"],
        "markdown": markdown,
        "source_refs": context["source_refs"],
        "evidence_refs": [],
        "data": tension,
    }


def _build_evidence_ladder(context: Dict[str, Any], module_config: Dict[str, Any]) -> Dict[str, Any]:
    evidence = context["evidence_ladder"]
    weight = module_config["weight"]
    example_limit = _weight_value(weight, 1, 2, 4)
    bullets = []
    evidence_refs = []
    for item in evidence["examples"][:example_limit]:
        bullets.append(f"- `{item['label']}`: {item['excerpt']}")
        if item["source_ref"]:
            evidence_refs.append(item["source_ref"])
    if not bullets:
        bullets.append("- No direct excerpts were attached to this thought packet yet.")
    markdown = "\n".join(
        [
            "## What the material actually shows",
            "",
            evidence["confidence_posture"],
            "",
            *bullets,
        ]
    )
    return {
        "module_id": module_config["id"],
        "title": "What the material actually shows",
        "enabled": True,
        "weight": weight,
        "markdown": markdown,
        "source_refs": context["source_refs"],
        "evidence_refs": evidence_refs,
        "data": evidence,
    }


def _build_pattern_and_transfer(context: Dict[str, Any], module_config: Dict[str, Any]) -> Dict[str, Any]:
    pattern = context["pattern_transfer"]
    weight = module_config["weight"]
    closing_line = pattern["transfer_layer"] if weight in {"medium", "heavy"} else ""
    markdown_lines = [
        "## The reusable pattern",
        "",
        f"At the article level, this is a question of {pattern['reasoning_primitive'].lower()}.",
        "",
        pattern["pattern_name"],
    ]
    if closing_line:
        markdown_lines.extend(["", closing_line])
    return {
        "module_id": module_config["id"],
        "title": "The reusable pattern",
        "enabled": True,
        "weight": weight,
        "markdown": "\n".join(markdown_lines),
        "source_refs": context["source_refs"],
        "evidence_refs": [],
        "data": pattern,
    }


def _build_decisions_and_implications(context: Dict[str, Any], module_config: Dict[str, Any]) -> Dict[str, Any]:
    decisions = context["decisions"]
    weight = module_config["weight"]
    implication_limit = _weight_value(weight, 1, 2, 3)
    markdown = "\n".join(
        [
            "## What this changes",
            "",
            decisions["default_position"],
            "",
            *[f"- {item}" for item in decisions["implications"][:implication_limit]],
        ]
    )
    return {
        "module_id": module_config["id"],
        "title": "What this changes",
        "enabled": True,
        "weight": weight,
        "markdown": markdown,
        "source_refs": context["source_refs"],
        "evidence_refs": [],
        "data": decisions,
    }


def _build_open_questions_and_boundaries(context: Dict[str, Any], module_config: Dict[str, Any]) -> Dict[str, Any]:
    open_questions = context["open_questions"]
    weight = module_config["weight"]
    question_limit = _weight_value(weight, 1, 2, 4)
    markdown = "\n".join(
        [
            "## What remains unresolved",
            "",
            open_questions["scope_limits"],
            "",
            *[f"- {item}" for item in open_questions["items"][:question_limit]],
        ]
    )
    return {
        "module_id": module_config["id"],
        "title": "What remains unresolved",
        "enabled": True,
        "weight": weight,
        "markdown": markdown,
        "source_refs": context["source_refs"],
        "evidence_refs": [],
        "data": open_questions,
    }


def _build_close_and_next_move(context: Dict[str, Any], module_config: Dict[str, Any]) -> Dict[str, Any]:
    thesis = context["thesis_and_reader_map"]["thesis_statement"].rstrip(".")
    next_move = context["decisions"]["default_position"]
    markdown = "\n".join(
        [
            "## What to do with it",
            "",
            f"If the framing is right, then the article should end by making the move explicit: {thesis}.",
            "",
            next_move,
        ]
    )
    return {
        "module_id": module_config["id"],
        "title": "What to do with it",
        "enabled": True,
        "weight": module_config["weight"],
        "markdown": markdown,
        "source_refs": context["source_refs"],
        "evidence_refs": [],
        "data": {"next_move": next_move},
    }


_MODULE_BUILDERS = {
    "promise-frame": _build_promise_frame,
    "entry-vector": _build_entry_vector,
    "thesis-and-reader-map": _build_thesis_and_reader_map,
    "object-field": _build_object_field,
    "tension-and-stakes": _build_tension_and_stakes,
    "evidence-ladder": _build_evidence_ladder,
    "pattern-and-transfer": _build_pattern_and_transfer,
    "decisions-and-implications": _build_decisions_and_implications,
    "open-questions-and-boundaries": _build_open_questions_and_boundaries,
    "close-and-next-move": _build_close_and_next_move,
}


class LongFormModuleAssembler:
    def build(self, context: Dict[str, Any], resolved_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        sections = []
        for module in resolved_config["modules"]:
            if not module["enabled"]:
                continue
            builder = _MODULE_BUILDERS.get(module["id"])
            if builder is None:
                continue
            sections.append(builder(context, module))
        return sections


class LongFormRenderer:
    def render(self, sections: List[Dict[str, Any]]) -> str:
        parts = [section["markdown"].strip() for section in sections if section.get("markdown", "").strip()]
        return "\n\n".join(parts).strip()


class LongFormOrchestrator:
    """Top-layer article orchestration that sits above context extraction and output rendering."""

    def __init__(
        self,
        config_loader: LongFormConfigLoader | None = None,
        context_builder: LongFormContextBuilder | None = None,
        module_assembler: LongFormModuleAssembler | None = None,
        renderer: LongFormRenderer | None = None,
    ) -> None:
        self.config_loader = config_loader or LongFormConfigLoader()
        self.context_builder = context_builder or LongFormContextBuilder()
        self.module_assembler = module_assembler or LongFormModuleAssembler()
        self.renderer = renderer or LongFormRenderer()

    def build_article(
        self,
        root: Path,
        packet: Dict[str, Any],
        snippets: List[Dict[str, Any]],
        title: str,
        short_text: str,
        overrides: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        resolved_config = self.config_loader.load(root, overrides=overrides)
        context = self.context_builder.build(packet, snippets, title, short_text, resolved_config)
        sections = self.module_assembler.build(context, resolved_config)
        markdown = self.renderer.render(sections)
        return {
            "markdown": markdown,
            "sections": sections,
            "profile": resolved_config["profile"],
            "module_order": [section["module_id"] for section in sections],
            "config_snapshot": {
                "blueprint_id": resolved_config["blueprint_id"],
                "style_posture": resolved_config["style_posture"],
                "profile": resolved_config["profile"],
                "modules": [
                    {
                        "id": module["id"],
                        "enabled": module["enabled"],
                        "weight": module["weight"],
                        "required_by_default": module["required_by_default"],
                    }
                    for module in resolved_config["modules"]
                ],
                "selected_algorithms": resolved_config["selected_algorithms"],
            },
        }


def build_long_form_article(
    root: Path,
    packet: Dict[str, Any],
    snippets: List[Dict[str, Any]],
    title: str,
    short_text: str,
    overrides: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    orchestrator = LongFormOrchestrator()
    return orchestrator.build_article(root, packet, snippets, title, short_text, overrides=overrides)
