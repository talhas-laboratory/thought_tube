#!/usr/bin/env python3
"""Re-extract upload sessions using semantic intelligence (OpenRouter or agent-authored drafts).

Never falls back to open_evidence heuristics.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
TOOLS = ROOT / "tools"
sys.path = [str(SRC)] + [p for p in sys.path if p not in {str(SRC), str(TOOLS), ""}]

from conversation_os.mtsf_extraction import DEEP_STAGES, SKILL_ID, SKILL_VERSION  # noqa: E402
from conversation_os.mtsf_graph import rebuild_global_content_graph  # noqa: E402
from conversation_os.mtsf_ingest import _conversation_text  # noqa: E402
from conversation_os.storage import (  # noqa: E402
    make_id,
    read_json,
    read_jsonl,
    session_dir,
    session_events_path,
    utc_now,
)

DraftBuilder = Callable[[str, Sequence[Dict[str, Any]], Dict[str, Any], str], Dict[str, Any]]


def _slug_session_id(path: Path) -> str:
    stem = path.stem
    date_match = re.match(r"^(\d{4}-\d{2}-\d{2})", stem)
    if date_match:
        topic = re.sub(r"^\d{4}-\d{2}-\d{2}_?", "", stem)
        topic = re.sub(r"^chatgpt---", "", topic, flags=re.IGNORECASE)
        topic = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:40]
        base = f"brainwalk-{date_match.group(1)}"
        return f"{base}-{topic}" if topic and topic not in base else base
    slug = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return slug[:64] or "import-batch"


def _draft_shell(
    session_id: str,
    manifest: Dict[str, Any],
    raw_content: str,
    *,
    model_id: str,
) -> Dict[str, Any]:
    domains = manifest.get("domains", [])
    subgraph_id = domains[0] if domains else f"session-{session_id}"
    return {
        "draft_id": make_id("mtsf-draft"),
        "input_id": f"session:{session_id}",
        "input_type": "import",
        "capture_mode": "deep",
        "session_id": session_id,
        "subgraph_id": subgraph_id,
        "scope": "session",
        "raw_content": raw_content[:12000],
        "context": {
            "user_goal": manifest.get("title"),
            "project": manifest.get("title"),
            "domain": ", ".join(domains) if domains else None,
        },
        "ontology_refs": {
            "governing_roles": "mtsf://ontologies/governing-roles@1.0.0",
            "relation_primitives": "mtsf://ontologies/relation-primitives@1.1.0",
            "stencil_role_types": "mtsf://ontologies/stencil-role-types@1.0.0",
        },
        "provenance": {
            "skill_id": SKILL_ID,
            "skill_version": SKILL_VERSION,
            "model_id": model_id,
            "extracted_at": utc_now(),
            "stages_completed": sorted(DEEP_STAGES),
        },
        "entities": [],
        "sub_entities": [],
        "qualities": [],
        "quality_roles": [],
        "relations": [],
        "candidate_shapes": [],
        "stencil_drafts": [],
        "uncertainties": [],
        "user_questions": [],
        "confidence": 0.88,
        "status": "proposed",
    }


def _openrouter_draft(
    root: Path,
    session_id: str,
    events: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
    raw_content: str,
) -> Dict[str, Any]:
    from conversation_os.mtsf_extraction_skill import (
        build_skill_input_envelope,
        request_llm_deep_extraction,
    )

    envelope = build_skill_input_envelope(
        session_id=session_id,
        events=events,
        manifest=manifest,
        raw_content=raw_content,
        capture_mode="deep",
    )
    result = request_llm_deep_extraction(
        root,
        session_id=session_id,
        envelope=envelope,
        llm_preference="api",
    )
    draft = result["draft"]
    draft["session_id"] = session_id
    return draft


def _backrooms_draft(
    session_id: str,
    manifest: Dict[str, Any],
    raw_content: str,
) -> Dict[str, Any]:
    draft = _draft_shell(session_id, manifest, raw_content, model_id="cursor_agent:semantic-shape-extraction")
    draft["entities"] = [
        {
            "proposed_id": "entity-liminal-horror-register",
            "name": "liminal horror register",
            "type": "composite",
            "stable_identity": ["spatial psychological horror where architecture behaves like subconscious maze"],
            "confidence": 0.93,
            "evidence": {"spans": ["liminal/spatial/psychological horror where architecture behaves like a subconscious maze"]},
        },
        {
            "proposed_id": "entity-thought-tube",
            "name": "thought tube",
            "type": "composite",
            "stable_identity": ["curated experiential channel needing reference clusters for spots"],
            "confidence": 0.9,
            "evidence": {"spans": ["For your Thought Tube spot, the strongest reference cluster is:"]},
        },
        {
            "proposed_id": "entity-metaphysical-zone",
            "name": "metaphysical zone",
            "type": "composite",
            "stable_identity": ["forbidden space testing inner desire, faith, and meaning"],
            "confidence": 0.92,
            "evidence": {"spans": ['A guide leads two men into "the Zone," a forbidden space where normal logic breaks down']},
        },
        {
            "proposed_id": "entity-memory-materialization",
            "name": "memory materialization",
            "type": "composite",
            "stable_identity": ["inner memory becoming physically present in space"],
            "confidence": 0.91,
            "evidence": {"spans": ["a place where memory materializes. The planet creates physical"]},
        },
        {
            "proposed_id": "entity-synthetic-no-exit-space",
            "name": "synthetic no-exit space",
            "type": "composite",
            "stable_identity": ["wrong-familiar repetitive architecture with no clean exit"],
            "confidence": 0.9,
            "evidence": {"spans": ['Very strong "wrong familiar space" feeling. Same repetitive, synthetic, no-exit architecture as Backrooms']},
        },
        {
            "proposed_id": "entity-institutional-corridor",
            "name": "institutional corridor",
            "type": "composite",
            "stable_identity": ["fluorescent looping corridor requiring anomaly detection"],
            "confidence": 0.88,
            "evidence": {"spans": ["looped through the same fluorescent corridor and has to notice anomalies"]},
        },
        {
            "proposed_id": "entity-inner-world-made-physical",
            "name": "inner world made physical",
            "type": "composite",
            "stable_identity": ["constructed inner world swallowing outer life"],
            "confidence": 0.87,
            "evidence": {"spans": ["life-sized replica of New York inside a warehouse until the constructed world swallows his real life"]},
        },
        {
            "proposed_id": "entity-reference-stack",
            "name": "curated reference stack",
            "type": "composite",
            "stable_identity": ["cross-cultural film cluster serving a creative brief"],
            "confidence": 0.89,
            "evidence": {"spans": ["Stalker + The Hourglass Sanatorium + Pulse + Vivarium + Hausu"]},
        },
    ]
    draft["qualities"] = [
        {
            "quality_id": "quality-wrong-familiar",
            "quality_type": "emergent",
            "intensity": 0.86,
            "kind": "emergent",
            "entity_ref": "entity-synthetic-no-exit-space",
            "labels": ["wrong_familiar", "uncanny"],
            "confidence": 0.88,
            "evidence": {"spans": ['"wrong familiar space" feeling']},
        },
        {
            "quality_id": "quality-dream-collapse",
            "quality_type": "emergent",
            "intensity": 0.84,
            "kind": "emergent",
            "entity_ref": "entity-memory-materialization",
            "labels": ["dream_logic", "identity_collapse"],
            "confidence": 0.86,
            "evidence": {"spans": ["Reality, memory, identity, and space slowly collapse into dream logic"]},
        },
    ]
    draft["quality_roles"] = [
        {
            "quality_ref": "quality-wrong-familiar",
            "entity_ref": "entity-synthetic-no-exit-space",
            "role": "defining",
            "confidence": 0.88,
            "evidence": {"spans": ['"wrong familiar space" feeling']},
        },
        {
            "quality_ref": "quality-dream-collapse",
            "entity_ref": "entity-memory-materialization",
            "role": "amplifying",
            "confidence": 0.86,
            "evidence": {"spans": ["collapse into dream logic"]},
        },
    ]
    draft["relations"] = [
        {
            "source_ref": "entity-liminal-horror-register",
            "target_ref": "entity-synthetic-no-exit-space",
            "level": "entity_entity",
            "relation_type": "exemplifies",
            "primitive": "resembles",
            "domain_expression": "Backrooms register exemplified by synthetic no-exit architecture",
            "weight": 0.9,
            "confidence": 0.88,
            "evidence": {"spans": ["Closest to Backrooms / liminal-space horror"]},
        },
        {
            "source_ref": "entity-metaphysical-zone",
            "target_ref": "entity-liminal-horror-register",
            "level": "entity_entity",
            "relation_type": "tests",
            "primitive": "modulates",
            "domain_expression": "Zone tests inner desire inside horror register",
            "weight": 0.91,
            "confidence": 0.9,
            "evidence": {"spans": ["space that seems to test inner desire, faith, fear, and meaning"]},
        },
        {
            "source_ref": "entity-reference-stack",
            "target_ref": "entity-thought-tube",
            "level": "entity_entity",
            "relation_type": "serves",
            "primitive": "enables",
            "domain_expression": "curated film stack serves Thought Tube spot brief",
            "weight": 0.92,
            "confidence": 0.9,
            "evidence": {"spans": ["For your Thought Tube spot, the strongest reference cluster is:"]},
        },
        {
            "source_ref": "entity-memory-materialization",
            "target_ref": "entity-inner-world-made-physical",
            "level": "entity_entity",
            "relation_type": "parallels",
            "primitive": "resembles",
            "domain_expression": "Solaris memory-guests parallel Synecdoche constructed world",
            "weight": 0.85,
            "confidence": 0.84,
            "evidence": {"spans": ["inner world becomes architecture", "memory materializes"]},
        },
    ]
    draft["candidate_shapes"] = [
        {
            "proposed_id": "cand-thought-tube-reference-synthesis",
            "possible_names": ["genre register to product reference stack"],
            "relational_configuration": "horror register → clustered film references → Thought Tube spot synthesis",
            "entity_refs": [
                "entity-liminal-horror-register",
                "entity-reference-stack",
                "entity-thought-tube",
            ],
            "quality_refs": ["quality-wrong-familiar"],
            "confidence": 0.91,
            "evidence": {"spans": ["For your Thought Tube spot", "strongest reference cluster"]},
        },
        {
            "proposed_id": "cand-subconscious-architecture",
            "possible_names": ["architecture as subconscious test"],
            "relational_configuration": "metaphysical zone + memory materialization + trap space",
            "entity_refs": [
                "entity-metaphysical-zone",
                "entity-memory-materialization",
                "entity-synthetic-no-exit-space",
            ],
            "quality_refs": ["quality-dream-collapse"],
            "confidence": 0.9,
            "evidence": {"spans": ["space as subconscious test", "subconscious spatial cinema"]},
        },
    ]
    draft["stencil_drafts"] = [
        {
            "proposed_name": "genre register filters reference cluster for product spot",
            "role_entities": [
                {"role_type": "controller"},
                {"role_type": "reservoir"},
                {"role_type": "mediator"},
            ],
            "relation_topology": [
                {
                    "source_role_ref": "controller",
                    "target_role_ref": "reservoir",
                    "primitive": "modulates",
                    "relation_type": "filters",
                },
                {
                    "source_role_ref": "reservoir",
                    "target_role_ref": "mediator",
                    "primitive": "enables",
                    "relation_type": "serves",
                },
            ],
            "dynamics_class": "gradient",
            "symmetry_profile": "asymmetric",
            "facet_completeness": {"causal_geometry": True},
            "confidence": 0.89,
            "evidence": {
                "spans": ["grouped by the specific feeling", "For your Thought Tube spot"],
                "source_refs": ["seed:stencil-context-warps-topology"],
            },
        }
    ]
    draft["activation_snapshot_hint"] = {
        "formation_phase": "partial_population",
        "dominant_entity_refs": ["entity-liminal-horror-register", "entity-thought-tube"],
        "active_quality_refs": ["quality-wrong-familiar"],
    }
    draft["confidence"] = 0.91
    return draft


def _latent_space_draft(session_id: str, manifest: Dict[str, Any], raw_content: str) -> Dict[str, Any]:
    draft = _draft_shell(session_id, manifest, raw_content, model_id="cursor_agent:semantic-shape-extraction")
    draft["entities"] = [
        {
            "proposed_id": "entity-metaphysical-space",
            "name": "metaphysical space",
            "type": "composite",
            "stable_identity": ["pre-material world of ideas, associations, moods, archetypes"],
            "confidence": 0.94,
            "evidence": {"spans": ["pre-material world of ideas: associations, symbols, moods"]},
        },
        {
            "proposed_id": "entity-actual-space",
            "name": "actual space",
            "type": "composite",
            "stable_identity": ["produced world of artifacts and material outputs"],
            "confidence": 0.93,
            "evidence": {"spans": ["Actual space means the produced world: text, images, video"]},
        },
        {
            "proposed_id": "entity-latent-space",
            "name": "latent space",
            "type": "composite",
            "stable_identity": ["computational geometry of semantic possibility"],
            "confidence": 0.95,
            "evidence": {"spans": ["gives vague meaning a **computational geometry**"]},
        },
        {
            "proposed_id": "entity-transformer-bridge",
            "name": "transformer bridge",
            "type": "composite",
            "stable_identity": ["context-sensitive translation layer from semantic object to output form"],
            "confidence": 0.92,
            "evidence": {"spans": ["translation layer between the invisible semantic object and a concrete output form"]},
        },
        {
            "proposed_id": "entity-thought-tube",
            "name": "thought tube",
            "type": "composite",
            "stable_identity": ["actualization engine for pre-material thought objects"],
            "confidence": 0.93,
            "evidence": {"spans": ["actualization engine for pre-material thought objects"]},
        },
        {
            "proposed_id": "entity-constraint-binding",
            "name": "constraint binding",
            "type": "composite",
            "stable_identity": ["turning vague possibility into specific form"],
            "confidence": 0.9,
            "evidence": {"spans": ["constraint-binding: turning vague possibility into specific form"]},
        },
    ]
    draft["qualities"] = [
        {
            "quality_id": "quality-scalable-bridge",
            "quality_type": "meta_state",
            "intensity": 0.9,
            "kind": "contextual",
            "entity_ref": "entity-latent-space",
            "labels": ["machine_operational", "scalable"],
            "confidence": 0.92,
            "evidence": {"spans": ["first scalable, machine-operational bridge between metaphysical space and actual space"]},
        }
    ]
    draft["quality_roles"] = [
        {
            "quality_ref": "quality-scalable-bridge",
            "entity_ref": "entity-latent-space",
            "role": "defining",
            "confidence": 0.92,
            "evidence": {"spans": ["machine-operational bridge"]},
        }
    ]
    draft["relations"] = [
        {
            "source_ref": "entity-latent-space",
            "target_ref": "entity-metaphysical-space",
            "level": "entity_entity",
            "relation_type": "approximates",
            "primitive": "resembles",
            "domain_expression": "latent space approximates metaphysical semantic field",
            "weight": 0.88,
            "confidence": 0.87,
            "evidence": {"spans": ["Latent space is not metaphysical space itself", "technical approximation of semantic possibility"]},
        },
        {
            "source_ref": "entity-transformer-bridge",
            "target_ref": "entity-actual-space",
            "level": "entity_entity",
            "relation_type": "materializes",
            "primitive": "enables",
            "domain_expression": "transformers enable materialization into actual artifacts",
            "weight": 0.91,
            "confidence": 0.9,
            "evidence": {"spans": ["externalize, navigate, recombine, and materialize"]},
        },
        {
            "source_ref": "entity-thought-tube",
            "target_ref": "entity-constraint-binding",
            "level": "entity_entity",
            "relation_type": "performs",
            "primitive": "modulates",
            "domain_expression": "Thought Tube performs constraint-binding actualization",
            "weight": 0.92,
            "confidence": 0.91,
            "evidence": {"spans": ["progressively bind that thought into actual artifacts"]},
        },
    ]
    draft["candidate_shapes"] = [
        {
            "proposed_id": "cand-metaphysical-actual-bridge",
            "possible_names": ["metaphysical to actual bridge"],
            "relational_configuration": "inner intuition → semantic representation → latent manipulation → artifact → feedback",
            "entity_refs": [
                "entity-metaphysical-space",
                "entity-latent-space",
                "entity-transformer-bridge",
                "entity-actual-space",
                "entity-thought-tube",
            ],
            "quality_refs": ["quality-scalable-bridge"],
            "confidence": 0.93,
            "evidence": {"spans": ["inner intuition → semantic representation → latent manipulation → generated artifact → feedback"]},
        }
    ]
    draft["stencil_drafts"] = [
        {
            "proposed_name": "semantic field warps through latent geometry into artifact",
            "role_entities": [
                {"role_type": "field"},
                {"role_type": "landscape"},
                {"role_type": "probe"},
                {"role_type": "sink"},
            ],
            "relation_topology": [
                {"source_role_ref": "field", "target_role_ref": "landscape", "primitive": "modulates", "relation_type": "warps"},
                {"source_role_ref": "probe", "target_role_ref": "landscape", "primitive": "modulates", "relation_type": "steers"},
                {"source_role_ref": "landscape", "target_role_ref": "sink", "primitive": "enables", "relation_type": "materializes"},
            ],
            "dynamics_class": "gradient",
            "symmetry_profile": "asymmetric",
            "facet_completeness": {"causal_geometry": True},
            "confidence": 0.9,
            "evidence": {"spans": ["computational geometry", "constraint-binding"], "source_refs": ["seed:stencil-context-warps-topology"]},
        }
    ]
    draft["activation_snapshot_hint"] = {
        "formation_phase": "partial_population",
        "dominant_entity_refs": ["entity-latent-space", "entity-thought-tube"],
        "active_quality_refs": ["quality-scalable-bridge"],
    }
    draft["confidence"] = 0.93
    return draft


def _external_thoughts_draft(session_id: str, manifest: Dict[str, Any], raw_content: str) -> Dict[str, Any]:
    draft = _draft_shell(session_id, manifest, raw_content, model_id="cursor_agent:semantic-shape-extraction")
    draft["entities"] = [
        {
            "proposed_id": "entity-external-thought",
            "name": "external thought",
            "type": "composite",
            "stable_identity": ["thought encountered outside the mind as fragment or artifact"],
            "confidence": 0.9,
            "evidence": {"spans": ["interact with external thoughts"]},
        },
        {
            "proposed_id": "entity-associative-space",
            "name": "associative space",
            "type": "composite",
            "stable_identity": ["spatial field where ideas are placed, clustered, and revisited"],
            "confidence": 0.92,
            "evidence": {"spans": ["an associative space that can be conversationally explored"]},
        },
        {
            "proposed_id": "entity-thought-tube",
            "name": "thought tube",
            "type": "composite",
            "stable_identity": ["product surface for glance-resonate-connect-transform loop"],
            "confidence": 0.9,
            "evidence": {"spans": ["For Thought Tube specifically", "glance → resonate → open → connect → transform → re-encounter"]},
        },
        {
            "proposed_id": "entity-taste-formation",
            "name": "taste formation",
            "type": "composite",
            "stable_identity": ["tool for formulating taste rather than storing notes"],
            "confidence": 0.88,
            "evidence": {"spans": ["lens around thought tube that focusses on taste formation"]},
        },
    ]
    draft["relations"] = [
        {
            "source_ref": "entity-external-thought",
            "target_ref": "entity-associative-space",
            "level": "entity_entity",
            "relation_type": "inhabits",
            "primitive": "modulates",
            "domain_expression": "external thoughts live in associative space not rigid filing",
            "weight": 0.9,
            "confidence": 0.88,
            "evidence": {"spans": ["encounter, relate, refine, return"]},
        },
        {
            "source_ref": "entity-thought-tube",
            "target_ref": "entity-taste-formation",
            "level": "entity_entity",
            "relation_type": "cultivates",
            "primitive": "enables",
            "domain_expression": "Thought Tube cultivates taste formation",
            "weight": 0.87,
            "confidence": 0.86,
            "evidence": {"spans": ["tool to help formulate taste"]},
        },
    ]
    draft["candidate_shapes"] = [
        {
            "proposed_id": "cand-encounter-revisit-loop",
            "possible_names": ["recognition resonance revisitation loop"],
            "relational_configuration": "fragment → resonance → revisitation → transformation",
            "entity_refs": ["entity-external-thought", "entity-associative-space", "entity-thought-tube"],
            "quality_refs": [],
            "confidence": 0.9,
            "evidence": {"spans": ["recognition, resonance, and revisitation", "glance → resonate → open → connect"]},
        }
    ]
    draft["stencil_drafts"] = [
        {
            "proposed_name": "fragment resonates in associative field",
            "role_entities": [{"role_type": "probe"}, {"role_type": "field"}, {"role_type": "mediator"}],
            "relation_topology": [
                {"source_role_ref": "probe", "target_role_ref": "field", "primitive": "modulates", "relation_type": "resonates"},
                {"source_role_ref": "field", "target_role_ref": "mediator", "primitive": "enables", "relation_type": "feeds"},
            ],
            "dynamics_class": "oscillatory",
            "symmetry_profile": "asymmetric",
            "facet_completeness": {"causal_geometry": True},
            "confidence": 0.87,
            "evidence": {"spans": ["association + spatiality + dialogue + revisitation"], "source_refs": ["seed:stencil-context-warps-topology"]},
        }
    ]
    draft["confidence"] = 0.9
    return draft


def _latent_path_draft(session_id: str, manifest: Dict[str, Any], raw_content: str) -> Dict[str, Any]:
    draft = _draft_shell(session_id, manifest, raw_content, model_id="cursor_agent:semantic-shape-extraction")
    draft["entities"] = [
        {
            "proposed_id": "entity-latent-manifold",
            "name": "latent manifold",
            "type": "composite",
            "stable_identity": ["pre-defined high-dimensional manifold navigated at inference"],
            "confidence": 0.93,
            "evidence": {"spans": ["pre-defined, high-dimensional manifold"]},
        },
        {
            "proposed_id": "entity-inference-path",
            "name": "inference path",
            "type": "composite",
            "stable_identity": ["trajectory of hidden states across layers"],
            "confidence": 0.92,
            "evidence": {"spans": ['"Movement" in latent space happens', "trajectory from a broad concept toward a specific prediction"]},
        },
        {
            "proposed_id": "entity-context-field",
            "name": "context field",
            "type": "composite",
            "stable_identity": ["prior tokens conditioning starting position and steering"],
            "confidence": 0.91,
            "evidence": {"spans": ["starting position of a word like \"bank\" will be different if the surrounding tokens"]},
        },
        {
            "proposed_id": "entity-attention-steering",
            "name": "attention steering",
            "type": "composite",
            "stable_identity": ["dynamic weighting that shifts path toward relevant clusters"],
            "confidence": 0.9,
            "evidence": {"spans": ["Attention Mechanism is the steering wheel"]},
        },
    ]
    draft["relations"] = [
        {
            "source_ref": "entity-context-field",
            "target_ref": "entity-inference-path",
            "level": "entity_entity",
            "relation_type": "anchors",
            "primitive": "modulates",
            "domain_expression": "context anchors and steers inference path",
            "weight": 0.91,
            "confidence": 0.9,
            "evidence": {"spans": ["initial placement sets the entire", "steer the hidden states"]},
        },
        {
            "source_ref": "entity-attention-steering",
            "target_ref": "entity-inference-path",
            "level": "entity_entity",
            "relation_type": "steers",
            "primitive": "modulates",
            "domain_expression": "attention steers path through latent manifold",
            "weight": 0.9,
            "confidence": 0.89,
            "evidence": {"spans": ["path shifts toward specific clusters"]},
        },
    ]
    draft["candidate_shapes"] = [
        {
            "proposed_id": "cand-context-steered-path",
            "possible_names": ["context-anchored inference trajectory"],
            "relational_configuration": "context field + attention → path on static manifold",
            "entity_refs": ["entity-context-field", "entity-attention-steering", "entity-inference-path", "entity-latent-manifold"],
            "quality_refs": [],
            "confidence": 0.91,
            "evidence": {"spans": ["path an agent takes through its latent space is not a random walk"]},
        }
    ]
    draft["stencil_drafts"] = [
        {
            "proposed_name": "context field modulates probe path",
            "role_entities": [{"role_type": "field"}, {"role_type": "probe"}, {"role_type": "landscape"}],
            "relation_topology": [
                {"source_role_ref": "field", "target_role_ref": "probe", "primitive": "modulates", "relation_type": "steers"},
                {"source_role_ref": "field", "target_role_ref": "landscape", "primitive": "modulates", "relation_type": "warps"},
            ],
            "dynamics_class": "gradient",
            "symmetry_profile": "asymmetric",
            "facet_completeness": {"causal_geometry": True},
            "confidence": 0.9,
            "evidence": {"spans": ["contextual Encoding", "steer the hidden states"], "source_refs": ["seed:stencil-context-warps-topology"]},
        }
    ]
    draft["confidence"] = 0.91
    return draft


def _cognitive_scaffolding_draft(session_id: str, manifest: Dict[str, Any], raw_content: str) -> Dict[str, Any]:
    draft = _draft_shell(session_id, manifest, raw_content, model_id="cursor_agent:semantic-shape-extraction")
    draft["entities"] = [
        {
            "proposed_id": "entity-session-purpose",
            "name": "session purpose",
            "type": "composite",
            "stable_identity": ["evolving anchor that preserves why the conversation exists"],
            "confidence": 0.91,
            "evidence": {"spans": ["preserving the purpose of the session, evolving it over time"]},
        },
        {
            "proposed_id": "entity-thought-tube",
            "name": "thought tube",
            "type": "composite",
            "stable_identity": ["cognitive scaffolding for sustained deep thinking"],
            "confidence": 0.93,
            "evidence": {"spans": ["Thought Tube is cognitive scaffolding for sustained deep thinking"]},
        },
        {
            "proposed_id": "entity-cascading-associations",
            "name": "cascading associations",
            "type": "composite",
            "stable_identity": ["weighted associations revealed in depth when relevant"],
            "confidence": 0.9,
            "evidence": {"spans": ["revealing weighted associations in cascading depth"]},
        },
    ]
    draft["relations"] = [
        {
            "source_ref": "entity-thought-tube",
            "target_ref": "entity-session-purpose",
            "level": "entity_entity",
            "relation_type": "anchors",
            "primitive": "stabilizes",
            "domain_expression": "Thought Tube anchors session to evolving purpose",
            "weight": 0.92,
            "confidence": 0.9,
            "evidence": {"spans": ["anchoring each session to an evolving purpose"]},
        },
        {
            "source_ref": "entity-cascading-associations",
            "target_ref": "entity-thought-tube",
            "level": "entity_entity",
            "relation_type": "feeds",
            "primitive": "enables",
            "domain_expression": "cascading associations feed scaffolding without dumping everything",
            "weight": 0.88,
            "confidence": 0.87,
            "evidence": {"spans": ["revealing weighted associations in cascading depth based on the user’s current cognitive state"]},
        },
    ]
    draft["candidate_shapes"] = [
        {
            "proposed_id": "cand-cognitive-scaffolding",
            "possible_names": ["purpose-anchored cascading depth"],
            "relational_configuration": "session purpose → scaffolding → timed association reveal",
            "entity_refs": ["entity-session-purpose", "entity-thought-tube", "entity-cascading-associations"],
            "quality_refs": [],
            "confidence": 0.9,
            "evidence": {"spans": ["stay inside a meaningful thought process", "cascading depth"]},
        }
    ]
    draft["confidence"] = 0.9
    return draft


def _expressive_roles_draft(session_id: str, manifest: Dict[str, Any], raw_content: str) -> Dict[str, Any]:
    draft = _draft_shell(session_id, manifest, raw_content, model_id="cursor_agent:semantic-shape-extraction")
    draft["entities"] = [
        {
            "proposed_id": "entity-domain-object",
            "name": "domain object",
            "type": "atomic",
            "stable_identity": ["concrete object inside a medium-specific expressive system"],
            "confidence": 0.9,
            "evidence": {"spans": ["concrete objects are domain-specific"]},
        },
        {
            "proposed_id": "entity-expressive-role",
            "name": "expressive role",
            "type": "composite",
            "stable_identity": ["functional role object plays inside expressive system"],
            "confidence": 0.92,
            "evidence": {"spans": ["what role does this object play inside the expressive system?"]},
        },
        {
            "proposed_id": "entity-thought-tube",
            "name": "thought tube",
            "type": "composite",
            "stable_identity": ["cross-domain abstraction layer for creative work"],
            "confidence": 0.85,
            "evidence": {"spans": ["abstraction layer above them"]},
        },
    ]
    draft["relations"] = [
        {
            "source_ref": "entity-domain-object",
            "target_ref": "entity-expressive-role",
            "level": "entity_entity",
            "relation_type": "abstracts_to",
            "primitive": "resembles",
            "domain_expression": "domain objects map to universal expressive roles",
            "weight": 0.9,
            "confidence": 0.88,
            "evidence": {"spans": ["every domain object can be abstracted by function/role"]},
        }
    ]
    draft["candidate_shapes"] = [
        {
            "proposed_id": "cand-cross-domain-role-lift",
            "possible_names": ["domain object to expressive role lift"],
            "relational_configuration": "note/shot/fabric/wall → anchor/accent/boundary roles",
            "entity_refs": ["entity-domain-object", "entity-expressive-role"],
            "quality_refs": [],
            "confidence": 0.89,
            "evidence": {"spans": ["Universal expressive roles", "Anchor"]},
        }
    ]
    draft["confidence"] = 0.88
    return draft


def _marketing_copy_draft(session_id: str, manifest: Dict[str, Any], raw_content: str) -> Dict[str, Any]:
    draft = _draft_shell(session_id, manifest, raw_content, model_id="cursor_agent:semantic-shape-extraction")
    draft["entities"] = [
        {
            "proposed_id": "entity-audience-state",
            "name": "audience state",
            "type": "composite",
            "stable_identity": ["current psychological/commercial state of audience"],
            "confidence": 0.9,
            "evidence": {"spans": ["What state are they currently in?"]},
        },
        {
            "proposed_id": "entity-desired-movement",
            "name": "desired movement",
            "type": "composite",
            "stable_identity": ["target state transition copy must produce"],
            "confidence": 0.9,
            "evidence": {"spans": ["What state do we want them to move into?"]},
        },
        {
            "proposed_id": "entity-product-truth",
            "name": "product truth",
            "type": "composite",
            "stable_identity": ["non-negotiable reality copy must anchor in"],
            "confidence": 0.89,
            "evidence": {"spans": ["What is the product truth?"]},
        },
        {
            "proposed_id": "entity-visible-copy",
            "name": "visible copy",
            "type": "composite",
            "stable_identity": ["surface wording layer generated last"],
            "confidence": 0.88,
            "evidence": {"spans": ["invisible strategy before visible wording"]},
        },
    ]
    draft["relations"] = [
        {
            "source_ref": "entity-audience-state",
            "target_ref": "entity-desired-movement",
            "level": "entity_entity",
            "relation_type": "precedes",
            "primitive": "enables",
            "domain_expression": "copy diagnoses current state before defining movement",
            "weight": 0.9,
            "confidence": 0.88,
            "evidence": {"spans": ["Define audience state transition"]},
        },
        {
            "source_ref": "entity-product-truth",
            "target_ref": "entity-visible-copy",
            "level": "entity_entity",
            "relation_type": "anchors",
            "primitive": "stabilizes",
            "domain_expression": "product truth anchors visible copy",
            "weight": 0.89,
            "confidence": 0.87,
            "evidence": {"spans": ["Anchor in product truth", "Generate visible copy"]},
        },
    ]
    draft["candidate_shapes"] = [
        {
            "proposed_id": "cand-copy-operating-system",
            "possible_names": ["copy operating system pipeline"],
            "relational_configuration": "diagnose → state transition → strategy → visible copy → evaluate",
            "entity_refs": ["entity-audience-state", "entity-desired-movement", "entity-product-truth", "entity-visible-copy"],
            "quality_refs": [],
            "confidence": 0.9,
            "evidence": {"spans": ["operating system for copy", "Diagnose context"]},
        }
    ]
    draft["confidence"] = 0.89
    return draft


def _mj_spatial_draft(session_id: str, manifest: Dict[str, Any], raw_content: str) -> Dict[str, Any]:
    draft = _draft_shell(session_id, manifest, raw_content, model_id="cursor_agent:semantic-shape-extraction")
    draft["entities"] = [
        {
            "proposed_id": "entity-spatial-intuition",
            "name": "spatial intuition",
            "type": "composite",
            "stable_identity": ["talent for moving through space as expressive medium"],
            "confidence": 0.9,
            "evidence": {"spans": ["talent or intuition of moving through space"]},
        },
        {
            "proposed_id": "entity-chameleon-adapter",
            "name": "chameleon adapter",
            "type": "composite",
            "stable_identity": ["rapid situational code-switching protecting core identity"],
            "confidence": 0.89,
            "evidence": {"spans": ["chameleon-like ability to navigate the disparate worlds"]},
        },
        {
            "proposed_id": "entity-product-space",
            "name": "product space",
            "type": "composite",
            "stable_identity": ["designed experiential field expanded to subconscious needs"],
            "confidence": 0.86,
            "evidence": {"spans": ["expanding the Product Space to include the user’s subconscious needs"]},
        },
    ]
    draft["relations"] = [
        {
            "source_ref": "entity-chameleon-adapter",
            "target_ref": "entity-spatial-intuition",
            "level": "entity_entity",
            "relation_type": "protects",
            "primitive": "modulates",
            "domain_expression": "adapter navigates worlds to protect unicorn core",
            "weight": 0.87,
            "confidence": 0.85,
            "evidence": {"spans": ["navigate a world that wasn't built for someone of his specific nature"]},
        }
    ]
    draft["candidate_shapes"] = [
        {
            "proposed_id": "cand-unicorn-chameleon",
            "possible_names": ["unicorn core with chameleon surface"],
            "relational_configuration": "outlier identity + adaptive navigation across contexts",
            "entity_refs": ["entity-spatial-intuition", "entity-chameleon-adapter"],
            "quality_refs": [],
            "confidence": 0.88,
            "evidence": {"spans": ["complete unicorn but could adapt to his surroundings really fast"]},
        }
    ]
    draft["confidence"] = 0.88
    return draft


def _cybernetics_draft(session_id: str, manifest: Dict[str, Any], raw_content: str) -> Dict[str, Any]:
    draft = _draft_shell(session_id, manifest, raw_content, model_id="cursor_agent:semantic-shape-extraction")
    if "cybernetic" not in raw_content.lower() and "feedback" not in raw_content.lower():
        draft["uncertainties"] = ["Cybernetics themes inferred from session title; transcript may emphasize other threads."]
    draft["entities"] = [
        {
            "proposed_id": "entity-feedback-loop",
            "name": "feedback loop",
            "type": "composite",
            "stable_identity": ["recursive system where outputs reshape future inputs"],
            "confidence": 0.85,
            "evidence": {"spans": ["That is exactly the right direction for Thought Tube"]},
        },
        {
            "proposed_id": "entity-thought-tube",
            "name": "thought tube",
            "type": "composite",
            "stable_identity": ["system evolving thought through feedback not one-shot answers"],
            "confidence": 0.88,
            "evidence": {"spans": ["For Thought Tube, this is especially valuable because your system is not just trying to answer questions"]},
        },
    ]
    draft["relations"] = [
        {
            "source_ref": "entity-feedback-loop",
            "target_ref": "entity-thought-tube",
            "level": "entity_entity",
            "relation_type": "governs",
            "primitive": "modulates",
            "domain_expression": "cybernetic feedback governs thought evolution in product",
            "weight": 0.86,
            "confidence": 0.84,
            "evidence": {"spans": ["not just trying to answer questions"]},
        }
    ]
    draft["confidence"] = 0.85
    return draft


def _fragment_article_chat_draft(session_id: str, manifest: Dict[str, Any], raw_content: str) -> Dict[str, Any]:
    draft = _draft_shell(session_id, manifest, raw_content, model_id="cursor_agent:semantic-shape-extraction")
    draft["entities"] = [
        {
            "proposed_id": "entity-fragment",
            "name": "fragment",
            "type": "atomic",
            "stable_identity": ["compressed entry-point thought"],
            "confidence": 0.91,
            "evidence": {"spans": ["Fragment → Article → Chat"]},
        },
        {
            "proposed_id": "entity-article-layer",
            "name": "article layer",
            "type": "composite",
            "stable_identity": ["clarification mini-essay generated on demand"],
            "confidence": 0.9,
            "evidence": {"spans": ["Article (mini-essay)= clarification layer"]},
        },
        {
            "proposed_id": "entity-chat-layer",
            "name": "chat layer",
            "type": "composite",
            "stable_identity": ["reasoning and expansion surface"],
            "confidence": 0.9,
            "evidence": {"spans": ["Chat= reasoning / expansion layer"]},
        },
        {
            "proposed_id": "entity-thought-tube",
            "name": "thought tube",
            "type": "composite",
            "stable_identity": ["associative evolving thinking environment"],
            "confidence": 0.92,
            "evidence": {"spans": ["product concept (Thought Tube)", "associative, evolving thinking environment"]},
        },
    ]
    draft["relations"] = [
        {
            "source_ref": "entity-fragment",
            "target_ref": "entity-article-layer",
            "level": "entity_entity",
            "relation_type": "expands_to",
            "primitive": "enables",
            "domain_expression": "fragments lazy-expand into articles",
            "weight": 0.9,
            "confidence": 0.89,
            "evidence": {"spans": ["depth ison-demand (lazy generation)"]},
        },
        {
            "source_ref": "entity-article-layer",
            "target_ref": "entity-chat-layer",
            "level": "entity_entity",
            "relation_type": "opens_into",
            "primitive": "enables",
            "domain_expression": "articles open into chat reasoning",
            "weight": 0.88,
            "confidence": 0.87,
            "evidence": {"spans": ["Fragment → Article → Chat"]},
        },
    ]
    draft["candidate_shapes"] = [
        {
            "proposed_id": "cand-fragment-article-chat",
            "possible_names": ["fragment article chat stack"],
            "relational_configuration": "fragment → article → chat with lazy depth",
            "entity_refs": ["entity-fragment", "entity-article-layer", "entity-chat-layer", "entity-thought-tube"],
            "quality_refs": [],
            "confidence": 0.91,
            "evidence": {"spans": ["Fragment → Article → Chat", "lazy generation"]},
        }
    ]
    draft["confidence"] = 0.9
    return draft


SESSION_BUILDERS: Dict[str, DraftBuilder] = {
    "brainwalk-2026-06-26-backrooms-as-subconscious-metaphor-0f4d": _backrooms_draft,
    "brainwalk-2026-07-05-05-07-latent-space-and-transformers-1-97": _latent_space_draft,
    "brainwalk-2026-04-10-brainwalk-1004-0039-5bf1": _external_thoughts_draft,
    "brainwalk-2026-05-07-you-said-ca8c": _latent_path_draft,
    "brainwalk-2026-05-27-brainwalk-265-0dd7": _cognitive_scaffolding_draft,
    "brainwalk-2026-06-26-braintrip-0706-1469": _expressive_roles_draft,
    "brainwalk-2026-06-26-use-marketing-copy-structure-dcfb": _marketing_copy_draft,
    "brainwalk-2026-04-25-brainwalk-michael-jackson-and-space-expl": _mj_spatial_draft,
    "brainwalk-2026-04-20-brainwalk-cybernetics-c2e2": _cybernetics_draft,
    "brainwalk-2026-04-11-brainwalk-1104-1800-cf73": _fragment_article_chat_draft,
}


def resolve_draft(
    root: Path,
    session_id: str,
    events: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
    raw_content: str,
    *,
    prefer_openrouter: bool,
) -> Dict[str, Any]:
    if prefer_openrouter:
        from conversation_os.mtsf_llm_backend import resolve_mtsf_llm_settings

        if resolve_mtsf_llm_settings(root)["openrouter_enabled"]:
            return _openrouter_draft(root, session_id, events, manifest, raw_content)

    builder = SESSION_BUILDERS.get(session_id)
    if builder is None:
        raise ValueError(f"no_intelligent_builder_for_session:{session_id}")
    return builder(session_id, manifest, raw_content)


def materialize_intelligent_session(
    root: Path,
    session_id: str,
    *,
    prefer_openrouter: bool,
) -> Dict[str, Any]:
    from conversation_os.mtsf_embeddings import materialize_entity_embeddings
    from conversation_os.mtsf_extraction import materialize_extraction_draft
    from conversation_os.mtsf_graph import apply_substrate_refs_to_draft

    events = read_jsonl(session_events_path(root, session_id))
    manifest = read_json(session_dir(root, session_id) / "manifest.json", default={})
    raw_content = _conversation_text(events)
    draft = resolve_draft(
        root,
        session_id,
        events,
        manifest,
        raw_content,
        prefer_openrouter=prefer_openrouter,
    )
    apply_substrate_refs_to_draft(root, session_id, events, draft)
    result = materialize_extraction_draft(root, session_id, draft)
    embedding_result = materialize_entity_embeddings(root, session_id, draft)
    result.setdefault("artifact_refs", {}).update(embedding_result.get("artifact_refs", {}))
    result["extraction_source"] = "llm" if draft["provenance"]["model_id"].startswith("openrouter:") else "agent_intelligence"
    result["entity_count"] = len(draft.get("entities", []))
    result["relation_count"] = len(draft.get("relations", []))
    result["stencil_draft_count"] = len(draft.get("stencil_drafts", []))
    result["model_id"] = draft["provenance"]["model_id"]
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Intelligent semantic re-extract (no heuristic fallback)")
    parser.add_argument("paths", nargs="*", help="Markdown uploads; default all uploads")
    parser.add_argument("--prefer-openrouter", action="store_true", help="Use OpenRouter when API key is configured")
    parser.add_argument("--no-rebuild-global", action="store_true")
    args = parser.parse_args()

    candidates: List[Path] = []
    if args.paths:
        for raw in args.paths:
            path = Path(raw)
            if path.is_dir():
                candidates.extend(sorted(path.glob("*.md")))
            elif path.is_file():
                candidates.append(path)
    else:
        uploads = Path("/home/ubuntu/.cursor/projects/workspace/uploads")
        candidates = sorted(uploads.glob("*.md"))

    runs: List[Dict[str, Any]] = []
    session_ids: List[str] = []
    for path in candidates:
        session_id = _slug_session_id(path)
        manifest_path = ROOT / "memory" / "sessions" / session_id / "manifest.json"
        if not manifest_path.exists():
            runs.append({"session_id": session_id, "status": "failed", "error": "session_not_found"})
            continue
        try:
            result = materialize_intelligent_session(ROOT, session_id, prefer_openrouter=args.prefer_openrouter)
            runs.append(
                {
                    "session_id": session_id,
                    "title": read_json(manifest_path, default={}).get("title"),
                    "status": "reextracted",
                    "extraction_source": result.get("extraction_source"),
                    "model_id": result.get("model_id"),
                    "entity_count": result.get("entity_count"),
                    "relation_count": result.get("relation_count"),
                    "stencil_draft_count": result.get("stencil_draft_count"),
                    "validation_ok": result.get("validation_ok"),
                }
            )
            session_ids.append(session_id)
        except Exception as exc:  # noqa: BLE001
            runs.append({"session_id": session_id, "status": "failed", "error": str(exc)})

    rebuild: Dict[str, Any] = {}
    if not args.no_rebuild_global and session_ids:
        rebuild = rebuild_global_content_graph(ROOT, session_ids=session_ids)

    payload = {
        "batch_id": f"intelligent-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "prefer_openrouter": args.prefer_openrouter,
        "runs": runs,
        "session_ids": session_ids,
        "rebuild": rebuild,
    }
    out_path = ROOT / "memory" / "mtsf" / "batch_intelligent_reextract.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 1 if any(row.get("status") == "failed" for row in runs) else 0


if __name__ == "__main__":
    raise SystemExit(main())
