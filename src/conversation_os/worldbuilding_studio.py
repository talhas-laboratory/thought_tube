from __future__ import annotations

import base64
import hashlib
import json
import math
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .storage import ensure_dir, make_id, read_json, read_jsonl, slugify, utc_now, write_json, write_jsonl


DEFAULT_DEMO_WORLD_ID = "world-demo-fractured-trust"
WORLD_STUDIO_VERSION = "2026-05-05.worldbuilding-video-studio.v1"
WORLD_STUDIO_OPERATOR_MANUSCRIPT_VERSION = "2026-05-07.worldbuilding-operator-manuscript.v1"
HIGGSFIELD_DEFAULT_MODEL = "seedance_2_0"
HIGGSFIELD_DEFAULT_IMAGE_MODEL = "cinematic_studio_2_5"
HIGGSFIELD_MCP_REMOTE_VERSION = "0.1.36"
HIGGSFIELD_SERVER_URL = "https://mcp.higgsfield.ai/mcp"
HIGGSFIELD_SUPPORTED_VIDEO_MODELS = {
    "cinematic_studio_3_0",
    "cinematic_studio_video",
    "cinematic_studio_video_v2",
    "grok_video",
    "kling2_6",
    "kling3_0",
    "marketing_studio_video",
    "minimax_hailuo",
    "seedance1_5",
    "seedance_1_5",
    "seedance_2_0",
    "soul_cast",
    "veo3",
    "veo3_1",
    "veo3_1_lite",
    "wan2_6",
    "wan2_7",
}
HIGGSFIELD_CLI_TIMEOUT_SECONDS = 60 * 45
HIGGSFIELD_MODEL_ALLOWED_PARAMS = {
    "cinematic_studio_3_0": {"aspect_ratio", "duration", "medias", "prompt"},
    "seedance_2_0": {"aspect_ratio", "duration", "genre", "medias", "mode", "prompt", "resolution"},
}
WORLD_STUDIO_DEFAULT_VISUAL_EMBEDDING_MODEL = "google/gemini-embedding-2-preview"
WORLD_STUDIO_OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"
WORLD_STUDIO_VISUAL_CATEGORY_KEYWORDS = {
    "animation_style": ["animation", "rendering", "cel", "hand-drawn", "linework", "stylized", "comic", "illustration"],
    "architecture_style": ["architecture", "building", "tower", "facade", "corridor", "hall", "structure", "interior", "room", "monolithic"],
    "flora_style": ["flora", "plant", "forest", "vine", "root", "flower", "pollen", "moss", "leaf", "spore"],
    "fauna_style": ["fauna", "animal", "creature", "bird", "insect", "beast", "fish"],
    "clothing_style": ["clothing", "garment", "robe", "fabric", "costume", "veil", "uniform", "drape"],
    "material_style": ["material", "glass", "stone", "pearl", "metal", "membrane", "bone", "wood", "mineral", "surface"],
    "technology_style": ["technology", "machine", "device", "instrument", "tool", "interface", "apparatus", "mechanism"],
    "color_system": ["color", "palette", "green", "red", "blue", "amber", "pearl", "saturation", "tone"],
    "lighting_language": ["lighting", "glare", "shadow", "glow", "luminous", "backlit", "surgical", "daylight"],
    "shape_language": ["shape", "silhouette", "profile", "outline", "aperture", "elongated", "subtractive", "ribbed"],
}
WORLD_STUDIO_VISUAL_CATEGORY_ORDER = [
    "animation_style",
    "architecture_style",
    "flora_style",
    "fauna_style",
    "clothing_style",
    "material_style",
    "technology_style",
    "color_system",
    "lighting_language",
    "shape_language",
]
THREE_STATE_SHOWCASE_SPECS = [
    {
        "role": "day_anchor",
        "label": "Daylight State Anchor",
        "query_text": "daytime monumental architecture detailed long-lens ceremonial framing pale ivory stone carved arches stepped planes domes towers",
        "scene_text": "A solitary draped man enters the monumental precinct in daylight and crosses toward a carved threshold.",
        "anchor_summary": "Daylight state anchor for the three-state traversal showcase.",
        "prompt_core": "A solitary draped man crosses a monumental sacred precinct in pale ivory and peach daylight, detailed carved arches and stepped ceremonial planes, distant telephoto compression, severe architectural framing, tiny human scale against oversized space, restrained forward motion, no modern props, no science-fiction machinery.",
    },
    {
        "role": "night_anchor",
        "label": "Nighttime State Anchor",
        "query_text": "nighttime washed-over less-detailed moonlit deep-blue sky green dome sacred architecture painterly nocturnal stillness",
        "scene_text": "The same draped man emerges into the same sacred world at night, washed over and simplified beneath a moonlit dome.",
        "anchor_summary": "Nighttime state anchor for the three-state traversal showcase.",
        "prompt_core": "The same solitary draped man continues through the same sacred architecture at night, moonlit deep-blue sky, green dome silhouette, painterly low-detail surfaces, simplified sacred geometry, hushed nocturnal stillness, gentle forward movement, no modern lights, no urban clutter.",
    },
    {
        "role": "dream_anchor",
        "label": "Dreamsequence State Anchor",
        "query_text": "dreamsequence softened painterly reduced-detail blue-white glow blurred courtyard light softened edges dreamy hush sacred architecture",
        "scene_text": "The night world slips into dream as the same draped man keeps walking toward a luminous threshold.",
        "anchor_summary": "Dreamsequence state anchor for the three-state traversal showcase.",
        "prompt_core": "The same solitary draped man moves through the same sacred world as it becomes a dreamsequence, blue-white bloom, softened figure edges, blurred courtyard light, low-detail painted surfaces, dreamy hush, suspended stillness, luminous threshold ahead, no sharp realism, no sci-fi interface clutter.",
    },
]


def worldbuilding_studio_dir(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "worldbuilding_studio"


def _worlds_dir(root: Path) -> Path:
    return worldbuilding_studio_dir(root) / "worlds"


def _packets_dir(root: Path) -> Path:
    return worldbuilding_studio_dir(root) / "packets"


def _events_path(root: Path) -> Path:
    return worldbuilding_studio_dir(root) / "events.jsonl"


def _assets_path(root: Path) -> Path:
    return worldbuilding_studio_dir(root) / "generation_assets.jsonl"


def _population_sessions_dir(root: Path) -> Path:
    return worldbuilding_studio_dir(root) / "population_sessions"


def _world_path(root: Path, world_id: str) -> Path:
    return _worlds_dir(root) / world_id / "world.json"


def _world_population_dir(root: Path, world_id: str) -> Path:
    return _worlds_dir(root) / world_id / "population"


def _population_session_path(root: Path, session_id: str) -> Path:
    return _population_sessions_dir(root) / f"{session_id}.json"


def _population_answers_path(root: Path, world_id: str) -> Path:
    return _world_population_dir(root, world_id) / "answers.jsonl"


def _population_knowledge_path(root: Path, world_id: str) -> Path:
    return _world_population_dir(root, world_id) / "knowledge_records.jsonl"


def _population_connections_path(root: Path, world_id: str) -> Path:
    return _world_population_dir(root, world_id) / "inferred_connections.jsonl"


def _world_graph_dir(root: Path, world_id: str) -> Path:
    return _worlds_dir(root) / world_id / "graph"


def _world_records_path(root: Path, world_id: str) -> Path:
    return _world_graph_dir(root, world_id) / "world_records.jsonl"


def _world_links_path(root: Path, world_id: str) -> Path:
    return _world_graph_dir(root, world_id) / "world_links.jsonl"


def _world_evidence_dir(root: Path, world_id: str) -> Path:
    return _worlds_dir(root) / world_id / "evidence"


def _source_evidence_path(root: Path, world_id: str) -> Path:
    return _world_evidence_dir(root, world_id) / "source_evidence.jsonl"


def _extracted_candidates_path(root: Path, world_id: str) -> Path:
    return _world_evidence_dir(root, world_id) / "extracted_candidates.jsonl"


def _world_canon_dir(root: Path, world_id: str) -> Path:
    return _worlds_dir(root) / world_id / "canon"


def _canon_assets_path(root: Path, world_id: str) -> Path:
    return _world_canon_dir(root, world_id) / "canon_assets.jsonl"


def _world_generated_anchors_dir(root: Path, world_id: str) -> Path:
    return _worlds_dir(root) / world_id / "generated_anchors"


def _world_showcases_dir(root: Path, world_id: str) -> Path:
    return _worlds_dir(root) / world_id / "showcases"


def _world_scene_dir(root: Path, world_id: str) -> Path:
    return _worlds_dir(root) / world_id / "scene"


def _scene_beats_path(root: Path, world_id: str) -> Path:
    return _world_scene_dir(root, world_id) / "scene_beats.jsonl"


def _shot_intents_path(root: Path, world_id: str) -> Path:
    return _world_scene_dir(root, world_id) / "shot_intents.jsonl"


def _evaluation_events_path(root: Path, world_id: str) -> Path:
    return _world_scene_dir(root, world_id) / "evaluation_events.jsonl"


def _world_execution_dir(root: Path, world_id: str) -> Path:
    return _worlds_dir(root) / world_id / "executions"


def _execution_runs_path(root: Path, world_id: str) -> Path:
    return _world_execution_dir(root, world_id) / "execution_runs.jsonl"


def _world_visual_dir(root: Path, world_id: str) -> Path:
    return _worlds_dir(root) / world_id / "visual"


def _visual_references_path(root: Path, world_id: str) -> Path:
    return _world_visual_dir(root, world_id) / "visual_references.jsonl"


def _visual_traits_path(root: Path, world_id: str) -> Path:
    return _world_visual_dir(root, world_id) / "visual_traits.jsonl"


def _world_motion_dir(root: Path, world_id: str) -> Path:
    return _worlds_dir(root) / world_id / "motion"


def _motion_objects_path(root: Path, world_id: str) -> Path:
    return _world_motion_dir(root, world_id) / "motion_objects.jsonl"


def _motion_bindings_path(root: Path, world_id: str) -> Path:
    return _world_motion_dir(root, world_id) / "motion_bindings.jsonl"


def _motion_plans_path(root: Path, world_id: str) -> Path:
    return _world_motion_dir(root, world_id) / "motion_plans.jsonl"


def _world_characters_dir(root: Path, world_id: str) -> Path:
    return _worlds_dir(root) / world_id / "characters"


def _character_profiles_path(root: Path, world_id: str) -> Path:
    return _world_characters_dir(root, world_id) / "character_profiles.jsonl"


def _character_feature_objects_path(root: Path, world_id: str) -> Path:
    return _world_characters_dir(root, world_id) / "character_feature_objects.jsonl"


def _packet_dir(root: Path, packet_id: str) -> Path:
    return _packets_dir(root) / packet_id


def _append_event(root: Path, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    event = {
        "event_id": make_id("world-event"),
        "created_at": utc_now(),
        "event_type": event_type,
        **payload,
    }
    rows = read_jsonl(_events_path(root))
    rows.append(event)
    write_jsonl(_events_path(root), rows)
    return event


def _unique(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    result: List[str] = []
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _empty_world_os_overview() -> Dict[str, Any]:
    return {
        "evidence_count": 0,
        "record_count": 0,
        "connection_count": 0,
        "canon_asset_count": 0,
        "scene_beat_count": 0,
        "shot_intent_count": 0,
        "execution_run_count": 0,
        "operator_manuscript_version": WORLD_STUDIO_OPERATOR_MANUSCRIPT_VERSION,
    }


def _ensure_world_os_fields(world: Dict[str, Any]) -> Dict[str, Any]:
    world.setdefault("packet_ids", [])
    world.setdefault("asset_ids", [])
    world.setdefault("population_overview", _empty_population_overview())
    overview = dict(world.get("world_os_overview", {}))
    defaults = _empty_world_os_overview()
    for key, value in defaults.items():
        overview.setdefault(key, value)
    world["world_os_overview"] = overview
    return world


def _aspect_dimensions(aspect_ratio: str) -> tuple[int, int]:
    if aspect_ratio == "9:16":
        return 1080, 1920
    if aspect_ratio == "1:1":
        return 1080, 1080
    return 1280, 720


def _duration_frames(duration_seconds: int | float, fps: int = 30) -> int:
    return int(round(float(duration_seconds) * fps))


def _default_demo_world() -> Dict[str, Any]:
    return {
        "world_id": DEFAULT_DEMO_WORLD_ID,
        "studio_version": WORLD_STUDIO_VERSION,
        "name": "Fractured Trust Demo World",
        "summary": "A restrained symbolic drama where betrayal becomes visible through reflective surfaces and delayed human reaction.",
        "status": "active",
        "source_profile": {
            "kind": "primary-source-inspired",
            "description": "Derived from the worldbuilding lens, semantic connective layer, bridge object, and visual-adjacent lens architecture.",
        },
        "project_primitives": [
            "fractured trust",
            "corrupted memory",
            "suppressed grief",
            "controlled exterior",
            "quiet recognition",
        ],
        "world_rules": [
            "Emotional truth should be externalized through objects, framing, and rhythm before dialogue.",
            "Reflective surfaces imply corrupted memory and fractured self-recognition.",
            "Important reveals should feel quiet, not explosive.",
            "Every visible detail should point back to the active semantic primitive.",
        ],
        "active_motifs": [
            "reflective surfaces externalize corrupted memory",
            "empty expensive rooms imply emotional absence",
            "delayed eye contact reveals suppressed recognition",
        ],
        "taste_profile": {
            "profile_name": "restrained symbolic drama",
            "style_keywords": [
                "restrained symbolic drama",
                "slow sacred documentary pacing",
                "muted cool palette",
                "object-first reveals",
                "micro-expression performance",
            ],
            "visual_preferences": [
                "negative space",
                "cold practical light",
                "asymmetrical isolation",
                "subtle camera movement",
                "symbolic props with narrative purpose",
            ],
            "forbidden": [
                "fast TikTok jump cuts",
                "chaotic handheld action",
                "decorative atmosphere without semantic purpose",
                "melodramatic crying",
                "horror framing",
            ],
        },
        "cut_grammar": {
            "name": "slow symbolic object-first editing",
            "average_shot_duration": "3-5 seconds",
            "base_rules": [
                "prefer fewer cuts",
                "hold before emotional confirmation",
                "cut from object to delayed face reaction",
                "use hard cuts only when information status changes",
            ],
            "semantic_triggers": [
                {
                    "semantic_pattern": "revelation",
                    "frame_pattern": "gaze locks onto meaningful object",
                    "timing": "delay cut slightly",
                    "preferred_next_shot": "reaction close-up",
                    "transition": "hard cut or hold",
                },
                {
                    "semantic_pattern": "fractured trust",
                    "frame_pattern": "reflection or split surface appears",
                    "timing": "hold on object before revealing face",
                    "preferred_next_shot": "wider confirming shot",
                    "transition": "hard cut",
                },
            ],
            "shot_sequence_bias": [
                "wide atmospheric opener",
                "symbolic object close-up",
                "delayed human reaction",
                "environmental reveal",
            ],
        },
        "visual_lens_rules": {
            "composition": [
                {
                    "semantic_role": "isolate the character inside the world logic",
                    "instruction": "Use negative space, asymmetry, and architecture that boxes the character in.",
                    "weight": 0.88,
                }
            ],
            "camera": [
                {
                    "semantic_role": "force recognition without melodrama",
                    "instruction": "Use mostly static framing with a slow push-in only during recognition.",
                    "weight": 0.86,
                }
            ],
            "lighting": [
                {
                    "semantic_role": "make emotional contamination visible",
                    "instruction": "Use cool practical light with hard shadow boundaries and no warm glow.",
                    "weight": 0.82,
                }
            ],
            "color": [
                {
                    "semantic_role": "keep grief restrained",
                    "instruction": "Use muted greys, cold blues, pale beige, and restrained saturation.",
                    "weight": 0.8,
                }
            ],
            "props": [
                {
                    "semantic_role": "externalize betrayal",
                    "instruction": "Use a broken mirror, hidden photograph, corrupted document, or reflective object.",
                    "weight": 0.92,
                }
            ],
            "blocking": [
                {
                    "semantic_role": "show controlled emotional compression",
                    "instruction": "Keep movement minimal; let the character drift slightly off-center after recognition.",
                    "weight": 0.76,
                }
            ],
            "facial_expression": [
                {
                    "semantic_role": "show suppressed grief through micro-expression",
                    "instruction": "Use a delayed polite expression, still eyes, slight jaw tension, and no open crying.",
                    "weight": 0.9,
                }
            ],
        },
        "bridge_objects": [
            {
                "bridge_id": "bridge-fractured-trust-reflection",
                "relation_type": "semantic_motif_to_visual_prop",
                "triggers": ["betrayal", "fractured trust", "mirror", "reflection", "recognition"],
                "source_meaning": "betrayal becomes visible as fractured trust",
                "target_layers": ["props", "composition", "camera", "editing"],
                "narrative_function": "make recognition happen through an object before it becomes facially explicit",
                "emotional_function": "make the viewer feel quiet reevaluation and collapse",
                "layer_mappings": {
                    "props": "Use a fractured reflective object as the confirming evidence.",
                    "composition": "Split the frame or isolate the character from the reflective object.",
                    "camera": "Hold on the object, then move into the delayed reaction.",
                    "editing": "Use object -> delayed face reaction -> environment reveal.",
                },
                "hard_constraints": [
                    "do not use decorative atmosphere without semantic purpose",
                    "avoid fast TikTok jump cuts",
                ],
                "soft_constraints": [
                    "prefer stillness before the cut",
                    "let the object carry the first emotional signal",
                ],
                "evaluator_rules": [
                    "the reflective object should communicate fractured trust",
                    "the reaction should be delayed rather than immediate",
                ],
                "weight": 0.94,
                "provenance": {"source": "primary-source worldbuilding lens conversation", "confidence": 0.92},
            },
            {
                "bridge_id": "bridge-suppressed-grief-expression",
                "relation_type": "character_state_to_facial_expression",
                "triggers": ["grief", "suppressed", "controlled", "recognizes", "betrayal"],
                "source_meaning": "suppressed grief under a controlled exterior",
                "target_layers": ["facial_expression", "blocking", "camera"],
                "narrative_function": "show pain without direct confession",
                "emotional_function": "make the viewer notice emotional leakage beneath composure",
                "layer_mappings": {
                    "facial_expression": "Use a small delayed expression, still eyes, and slight jaw tension.",
                    "blocking": "Keep posture composed while the character subtly shifts off-center.",
                    "camera": "Hold close enough for micro-expression but avoid intrusive melodrama.",
                },
                "hard_constraints": [
                    "avoid open crying",
                    "do not make the expression villainous or melodramatic",
                ],
                "soft_constraints": [
                    "prefer a half-beat delay before the expression changes",
                    "let the eyes remain guarded",
                ],
                "evaluator_rules": [
                    "facial change should be subtle but legible",
                    "emotion should read as controlled humiliation or grief, not anger",
                ],
                "weight": 0.9,
                "provenance": {"source": "primary-source facial mimicry lens conversation", "confidence": 0.88},
            },
            {
                "bridge_id": "bridge-revelation-cut-grammar",
                "relation_type": "story_function_to_editing_rhythm",
                "triggers": ["revelation", "realizes", "recognizes", "betrayal"],
                "source_meaning": "hidden information becomes explicit after suspense",
                "target_layers": ["editing", "camera", "composition"],
                "narrative_function": "make the audience connect the clue before the character fully reacts",
                "emotional_function": "create quiet shock through timing and withheld confirmation",
                "layer_mappings": {
                    "editing": "Delay the reaction cut; avoid montage; hold after recognition.",
                    "camera": "Use a slow push-in only after the object has been established.",
                    "composition": "Move from object detail to human face to wider relational context.",
                },
                "hard_constraints": [
                    "do not use flashy transitions",
                    "avoid fast TikTok jump cuts",
                ],
                "soft_constraints": [
                    "prefer a hard cut when information status changes",
                    "hold longer than the average social edit",
                ],
                "evaluator_rules": [
                    "cut rhythm should make the revelation feel inevitable",
                    "the edit should not feel like action tension",
                ],
                "weight": 0.87,
                "provenance": {"source": "primary-source semantic connective/cut grammar conversation", "confidence": 0.9},
            },
        ],
        "constraints": {
            "hard": [
                "avoid fast TikTok jump cuts",
                "do not use decorative atmosphere without semantic purpose",
                "do not make the scene feel like horror",
            ],
            "soft": [
                {"rule": "prefer quiet emotional pressure over spectacle", "weight": 0.86},
                {"rule": "let objects carry meaning before dialogue", "weight": 0.92},
            ],
        },
        "provenance_refs": [
            "/Users/talhauddin/Downloads/2026-05-05_chatgpt---report-summary-architecture.md",
            "/Users/talhauddin/Downloads/2026-05-05_chatgpt---read_semantic-context-infrastructure.md",
        ],
        "packet_ids": [],
        "asset_ids": [],
        "population_overview": _empty_population_overview(),
        "world_os_overview": _empty_world_os_overview(),
    }


def create_world(
    root: Path,
    *,
    name: str,
    summary: str = "",
    primitives: List[str] | None = None,
    world_rules: List[str] | None = None,
    taste_profile: Dict[str, Any] | None = None,
    bridge_objects: List[Dict[str, Any]] | None = None,
    visual_lens_rules: Dict[str, List[Dict[str, Any]]] | None = None,
    cut_grammar: Dict[str, Any] | None = None,
    constraints: Dict[str, Any] | None = None,
    provenance_refs: List[str] | None = None,
    world_id: str | None = None,
) -> Dict[str, Any]:
    now = utc_now()
    resolved_world_id = world_id or f"world-{slugify(name)}-{make_id('id').split('-', 1)[1]}"
    world = {
        "world_id": resolved_world_id,
        "studio_version": WORLD_STUDIO_VERSION,
        "name": name,
        "summary": summary,
        "status": "active",
        "created_at": now,
        "updated_at": now,
        "source_profile": {"kind": "manual"},
        "project_primitives": list(primitives or []),
        "world_rules": list(world_rules or []),
        "active_motifs": [],
        "taste_profile": taste_profile or {
            "profile_name": "default worldbuilding profile",
            "style_keywords": [],
            "visual_preferences": [],
            "forbidden": [],
        },
        "cut_grammar": cut_grammar or {"name": "default cut grammar", "base_rules": [], "semantic_triggers": [], "shot_sequence_bias": []},
        "visual_lens_rules": visual_lens_rules or {},
        "bridge_objects": bridge_objects or [],
        "constraints": constraints or {"hard": [], "soft": []},
        "provenance_refs": list(provenance_refs or []),
        "packet_ids": [],
        "asset_ids": [],
        "population_overview": _empty_population_overview(),
        "world_os_overview": _empty_world_os_overview(),
    }
    world = _ensure_world_os_fields(world)
    write_json(_world_path(root, resolved_world_id), world)
    _append_event(root, "world_created", {"world_id": resolved_world_id, "name": name})
    return world


def create_demo_world(root: Path) -> Dict[str, Any]:
    existing = read_json(_world_path(root, DEFAULT_DEMO_WORLD_ID), default=None)
    if existing is not None:
        return existing
    world = _default_demo_world()
    now = utc_now()
    world["created_at"] = now
    world["updated_at"] = now
    world = _ensure_world_os_fields(world)
    write_json(_world_path(root, DEFAULT_DEMO_WORLD_ID), world)
    _append_event(root, "world_created", {"world_id": DEFAULT_DEMO_WORLD_ID, "name": world["name"], "demo": True})
    return world


def list_worlds(root: Path) -> Dict[str, Any]:
    worlds = []
    base = _worlds_dir(root)
    if base.exists():
        for path in sorted(base.glob("*/world.json")):
            world = read_json(path, default=None)
            if world:
                worlds.append(
                    {
                        "world_id": world["world_id"],
                        "name": world.get("name", ""),
                        "summary": world.get("summary", ""),
                        "status": world.get("status", ""),
                        "updated_at": world.get("updated_at", ""),
                        "packet_count": len(world.get("packet_ids", [])),
                    }
                )
    return {"count": len(worlds), "worlds": worlds}


def get_world(root: Path, world_id: str) -> Dict[str, Any]:
    world = read_json(_world_path(root, world_id), default=None)
    if world is None:
        raise FileNotFoundError(f"World not found: {world_id}")
    return _ensure_world_os_fields(world)


_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tif", ".tiff"}
_PLACE_HINTS = {
    "archive",
    "basin",
    "city",
    "district",
    "forest",
    "harbor",
    "house",
    "observatory",
    "room",
    "shore",
    "station",
    "tower",
    "valley",
}
_OBJECT_HINTS = {
    "blade",
    "compass",
    "document",
    "fork",
    "key",
    "knife",
    "lens",
    "map",
    "mirror",
    "needle",
    "orb",
    "photograph",
    "record",
}
_VISUAL_HINTS = {
    "bright",
    "cold",
    "color",
    "glare",
    "green",
    "light",
    "lighting",
    "membrane",
    "palette",
    "pearl",
    "reflection",
    "symmetry",
    "translucent",
    "uncanny",
    "visual",
    "warm",
}
_CONFLICT_HINTS = {
    "appetite",
    "betrayal",
    "consume",
    "consumes",
    "conflict",
    "danger",
    "feed",
    "feeds",
    "hunger",
    "pressure",
    "predatory",
    "risk",
    "threat",
    "unstable",
}


def _record_type_for_layer(layer: str) -> str:
    mapping = {
        "primitive": "world_fragment",
        "character": "character",
        "place": "place",
        "object": "object",
        "rule": "rule",
        "visual": "visual_adjacency",
        "conflict": "world_fragment",
        "relationship": "world_fragment",
    }
    return mapping.get(layer, "world_fragment")


def _record_signature(record: Dict[str, Any]) -> str:
    return "::".join(
        [
            str(record.get("layer", "")).strip().lower(),
            str(record.get("record_type", record.get("kind", ""))).strip().lower(),
            slugify(str(record.get("label", "")).strip().lower()),
        ]
    )


def _normalize_world_record(record: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(record)
    normalized["record_type"] = normalized.get("record_type", _record_type_for_layer(normalized.get("layer", "")))
    normalized["explicitness"] = normalized.get("explicitness", "explicit")
    normalized["supporting_evidence_ids"] = _unique(normalized.get("supporting_evidence_ids", []))
    provenance = dict(normalized.get("provenance", {}))
    provenance["evidence_ids"] = _unique(provenance.get("evidence_ids", normalized.get("supporting_evidence_ids", [])))
    if "confidence" not in provenance:
        provenance["confidence"] = 0.78 if normalized["explicitness"] == "explicit" else 0.58
    normalized["provenance"] = provenance
    normalized["tags"] = _unique(normalized.get("tags", []))
    normalized["metadata"] = dict(normalized.get("metadata", {}))
    return normalized


def _normalize_population_record(record: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(record)
    normalized["record_type"] = normalized.get("record_type", _record_type_for_layer(normalized.get("layer", "")))
    normalized["explicitness"] = normalized.get("explicitness", "explicit")
    normalized["supporting_evidence_ids"] = _unique(normalized.get("supporting_evidence_ids", []))
    if "provenance" not in normalized:
        normalized["provenance"] = {
            "source": "population_session",
            "confidence": 0.72,
            "evidence_ids": [],
        }
    else:
        normalized["provenance"] = dict(normalized["provenance"])
        normalized["provenance"]["evidence_ids"] = _unique(normalized["provenance"].get("evidence_ids", []))
    return normalized


def _read_population_records(root: Path, world_id: str) -> List[Dict[str, Any]]:
    return [_normalize_population_record(row) for row in read_jsonl(_population_knowledge_path(root, world_id))]


def _read_world_records(root: Path, world_id: str) -> List[Dict[str, Any]]:
    rows = [_normalize_world_record(row) for row in read_jsonl(_world_records_path(root, world_id))]
    by_id = {row.get("knowledge_id", ""): row for row in rows if row.get("knowledge_id")}
    by_signature = {_record_signature(row): row for row in rows}
    for record in _read_population_records(root, world_id):
        key = record.get("knowledge_id", "")
        signature = _record_signature(record)
        if key and key not in by_id and signature not in by_signature:
            rows.append(record)
            if key:
                by_id[key] = record
            by_signature[signature] = record
    return rows


def _read_world_connections(root: Path, world_id: str) -> List[Dict[str, Any]]:
    rows = list(read_jsonl(_world_links_path(root, world_id)))
    if not rows:
        rows = list(read_jsonl(_population_connections_path(root, world_id)))
    return rows


def _merge_record(existing: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing)
    merged["updated_at"] = utc_now()
    merged["summary"] = merged.get("summary") or candidate.get("summary", "")
    merged["tags"] = _unique([*merged.get("tags", []), *candidate.get("tags", [])])
    merged["supporting_evidence_ids"] = _unique(
        [*merged.get("supporting_evidence_ids", []), *candidate.get("supporting_evidence_ids", [])]
    )
    merged["explicitness"] = "explicit" if "explicit" in {merged.get("explicitness"), candidate.get("explicitness")} else "inferred"
    metadata = dict(merged.get("metadata", {}))
    metadata.update(candidate.get("metadata", {}))
    merged["metadata"] = metadata
    provenance = dict(merged.get("provenance", {}))
    candidate_provenance = dict(candidate.get("provenance", {}))
    provenance["source"] = provenance.get("source") or candidate_provenance.get("source", "")
    provenance["confidence"] = max(float(provenance.get("confidence", 0.0)), float(candidate_provenance.get("confidence", 0.0)))
    provenance["evidence_ids"] = _unique(
        [*provenance.get("evidence_ids", []), *candidate_provenance.get("evidence_ids", []), *merged["supporting_evidence_ids"]]
    )
    merged["provenance"] = provenance
    return _normalize_world_record(merged)


def _upsert_world_records(root: Path, world_id: str, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    existing_rows = [_normalize_world_record(row) for row in read_jsonl(_world_records_path(root, world_id))]
    by_signature = {_record_signature(row): row for row in existing_rows}
    ordered = list(existing_rows)
    for record in records:
        normalized = _normalize_world_record(record)
        signature = _record_signature(normalized)
        if signature in by_signature:
            merged = _merge_record(by_signature[signature], normalized)
            by_signature[signature] = merged
        else:
            by_signature[signature] = normalized
            ordered.append(normalized)
    deduped: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in [*by_signature.values(), *ordered]:
        signature = _record_signature(row)
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(by_signature.get(signature, row))
    write_jsonl(_world_records_path(root, world_id), deduped)
    return deduped


def _world_record(
    *,
    world_id: str,
    layer: str,
    record_type: str,
    label: str,
    summary: str,
    supporting_evidence_ids: List[str] | None = None,
    tags: List[str] | None = None,
    metadata: Dict[str, Any] | None = None,
    explicitness: str = "explicit",
    provenance_source: str = "evidence_ingestion",
    confidence: float = 0.8,
) -> Dict[str, Any]:
    evidence_ids = _unique(supporting_evidence_ids or [])
    return {
        "knowledge_id": make_id("world-knowledge"),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "world_id": world_id,
        "session_id": "",
        "answer_id": "",
        "question_id": "evidence_ingest",
        "layer": layer,
        "kind": record_type,
        "record_type": record_type,
        "label": _compact_text(label, fallback=record_type),
        "summary": _compact_text(summary, fallback=label),
        "tags": _unique(tags or _tokenize_tags(label, summary)),
        "metadata": metadata or {},
        "explicitness": explicitness,
        "supporting_evidence_ids": evidence_ids,
        "provenance": {
            "source": provenance_source,
            "confidence": confidence,
            "evidence_ids": evidence_ids,
        },
    }


def _sentences_from_text(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", _compact_text(text))
    return [part.strip() for part in parts if part.strip()]


def _first_sentence_matching(
    sentences: List[str],
    keywords: Iterable[str],
    *,
    excluded_prefixes: Iterable[str] = (),
) -> str:
    keyword_set = {item.lower() for item in keywords}
    blocked = tuple(item.lower() for item in excluded_prefixes)
    for sentence in sentences:
        lower = sentence.lower()
        if blocked and any(lower.startswith(prefix) for prefix in blocked):
            continue
        if any(keyword in lower for keyword in keyword_set):
            return sentence
    return ""


def _character_sentence(sentences: List[str]) -> str:
    pattern = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b")
    for sentence in sentences:
        if pattern.search(sentence) and any(verb in sentence.lower() for verb in ["is ", "keeps", "tends", "maps", "follows", "discovers", "hears", "holds", "uses"]):
            return sentence
    return ""


def _extract_visual_metadata(sentence: str) -> Dict[str, Any]:
    lower = sentence.lower()
    metadata: Dict[str, Any] = {}
    if "bright uncanny" in lower:
        metadata["choice"] = "bright_uncanny"
    elif "ritual cold" in lower:
        metadata["choice"] = "ritual_cold"
    elif "soft decay" in lower:
        metadata["choice"] = "soft_decay"
    elif "warm intimacy" in lower:
        metadata["choice"] = "warm_intimacy"
    elif "opulent pressure" in lower:
        metadata["choice"] = "opulent_pressure"
    return metadata


def _evidence_modality(source_text: str, source_path: str, source_url: str) -> str:
    if source_text.strip():
        return "text"
    suffix = Path(source_path or source_url).suffix.lower()
    if suffix in _IMAGE_EXTENSIONS:
        return "image"
    return "reference"


def _world_studio_runtime_settings(root: Path) -> Dict[str, Any]:
    settings: Dict[str, Any] = {}
    runtime_paths = [
        root / "product" / "inner_world_v1" / "config" / "runtime.json",
        Path.home() / ".config" / "inner_space" / "world_studio_runtime.json",
    ]
    for path in runtime_paths:
        loaded = read_json(path, default={})
        if isinstance(loaded, dict):
            settings.update(loaded)
    return settings


def _visual_embedding_settings(root: Path) -> Dict[str, Any]:
    runtime = _world_studio_runtime_settings(root)
    world_studio = runtime.get("world_studio", {}) if isinstance(runtime.get("world_studio", {}), dict) else {}
    visual = world_studio.get("visual_embeddings", {}) if isinstance(world_studio.get("visual_embeddings", {}), dict) else {}
    api_key = (
        os.environ.get("WORLD_STUDIO_OPENROUTER_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or visual.get("api_key")
        or runtime.get("openrouter_api_key")
        or ""
    )
    model_name = (
        os.environ.get("WORLD_STUDIO_VISUAL_EMBEDDING_MODEL")
        or visual.get("model")
        or WORLD_STUDIO_DEFAULT_VISUAL_EMBEDDING_MODEL
    )
    return {
        "api_key": str(api_key).strip(),
        "model": str(model_name).strip() or WORLD_STUDIO_DEFAULT_VISUAL_EMBEDDING_MODEL,
        "base_url": WORLD_STUDIO_OPENROUTER_EMBEDDINGS_URL,
        "enabled": bool(api_key),
    }


def _mime_type_for_path(path: str) -> str:
    guessed, _ = mimetypes.guess_type(path)
    return guessed or "application/octet-stream"


def _image_url_for_embedding(source_path: str, source_url: str) -> str:
    if source_url.strip():
        return source_url.strip()
    candidate = Path(source_path).expanduser()
    if not candidate.exists():
        return ""
    encoded = base64.b64encode(candidate.read_bytes()).decode("ascii")
    return f"data:{_mime_type_for_path(str(candidate))};base64,{encoded}"


def _infer_visual_categories(*texts: str) -> List[str]:
    combined = " ".join(_compact_text(text).lower() for text in texts if _compact_text(text))
    categories: List[str] = []
    for category in WORLD_STUDIO_VISUAL_CATEGORY_ORDER:
        keywords = WORLD_STUDIO_VISUAL_CATEGORY_KEYWORDS.get(category, [])
        if any(keyword in combined for keyword in keywords):
            categories.append(category)
    return categories or ["shape_language"]


def _visual_trait_candidates(note: str, liked_aspects: List[str]) -> List[str]:
    if liked_aspects:
        return _unique(_compact_text(item) for item in liked_aspects if _compact_text(item))
    normalized = re.sub(r"\b(i like|we like|what i like is|reference with)\b", "", note, flags=re.IGNORECASE)
    parts = re.split(r",|;|\band\b", normalized)
    traits = [_compact_text(part) for part in parts if _compact_text(part)]
    return _unique(traits[:8])


def _vector_cosine_similarity(left: List[float], right: List[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_mag = math.sqrt(sum(a * a for a in left))
    right_mag = math.sqrt(sum(b * b for b in right))
    if left_mag <= 0 or right_mag <= 0:
        return 0.0
    return dot / (left_mag * right_mag)


class OpenRouterEmbeddingClient:
    def __init__(self, *, api_key: str, model_name: str, base_url: str = WORLD_STUDIO_OPENROUTER_EMBEDDINGS_URL) -> None:
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url

    @classmethod
    def from_runtime(cls, root: Path) -> "OpenRouterEmbeddingClient | None":
        settings = _visual_embedding_settings(root)
        if not settings["enabled"]:
            return None
        return cls(api_key=settings["api_key"], model_name=settings["model"], base_url=settings["base_url"])

    def embed_documents(self, documents: List[Dict[str, Any]], *, input_type: str = "search_document") -> List[Dict[str, Any]]:
        payload_inputs: List[Any] = []
        for document in documents:
            modality = document.get("modality", "text")
            text = _compact_text(document.get("text", ""))
            image_url = document.get("image_url", "")
            if modality == "image" or image_url:
                content: List[Dict[str, Any]] = []
                if text:
                    content.append({"type": "text", "text": text})
                if image_url:
                    content.append({"type": "image_url", "image_url": {"url": image_url}})
                payload_inputs.append({"content": content})
            else:
                payload_inputs.append(text)
        request = Request(
            self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(
                {
                    "model": self.model_name,
                    "input": payload_inputs,
                    "encoding_format": "float",
                    "input_type": input_type,
                }
            ).encode("utf-8"),
            method="POST",
        )
        with urlopen(request, timeout=45) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload.get("error"), dict):
            raise RuntimeError(str(payload["error"].get("message", "Embedding request failed")))
        return [
            {
                "embedding": item.get("embedding", []),
                "model": payload.get("model", self.model_name),
                "usage": payload.get("usage", {}),
                "modality": documents[index].get("modality", "text"),
            }
            for index, item in enumerate(payload.get("data", []))
        ]


def _embed_documents(client: Any, documents: List[Dict[str, Any]], *, input_type: str) -> List[Dict[str, Any]]:
    try:
        return client.embed_documents(documents, input_type=input_type)
    except TypeError:
        return client.embed_documents(documents)


def _extract_candidates_from_evidence(world_id: str, evidence: Dict[str, Any]) -> List[Dict[str, Any]]:
    source_text = evidence.get("source_text", "")
    note = evidence.get("note", "")
    label = evidence.get("source_label", "")
    combined = _compact_text(" ".join(part for part in [source_text, note, label] if part))
    sentences = _sentences_from_text(combined)
    evidence_id = evidence["evidence_id"]
    candidates: List[Dict[str, Any]] = []

    primitive_sentence = _first_sentence_matching(sentences, ["feel", "emotion", "gravity", "wonder", "grief", "pressure", "hunger", "betrayal"])
    if primitive_sentence:
        primitive_label = "wonder under pressure" if "wonder" in primitive_sentence.lower() and "pressure" in primitive_sentence.lower() else _build_record_label(primitive_sentence, "World Fragment").lower()
        candidates.append(
            _world_record(
                world_id=world_id,
                layer="primitive",
                record_type="world_fragment",
                label=primitive_label,
                summary=primitive_sentence,
                supporting_evidence_ids=[evidence_id],
                confidence=0.82,
            )
        )

    character_sentence = _character_sentence(sentences)
    if character_sentence:
        candidates.append(
            _world_record(
                world_id=world_id,
                layer="character",
                record_type="character",
                label=_build_record_label(character_sentence, "Anchor Character"),
                summary=character_sentence,
                supporting_evidence_ids=[evidence_id],
                metadata={"anchor": True},
                confidence=0.84,
            )
        )

    place_sentence = _first_sentence_matching(
        sentences,
        _PLACE_HINTS,
        excluded_prefixes=("the world should feel", "the world feels", "world should feel", "world feels"),
    )
    if place_sentence:
        candidates.append(
            _world_record(
                world_id=world_id,
                layer="place",
                record_type="place",
                label=_build_record_label(place_sentence, "Anchor Place"),
                summary=place_sentence,
                supporting_evidence_ids=[evidence_id],
                metadata={"anchor": True},
                confidence=0.79,
            )
        )

    object_sentence = _first_sentence_matching(sentences, _OBJECT_HINTS)
    if object_sentence:
        candidates.append(
            _world_record(
                world_id=world_id,
                layer="object",
                record_type="object",
                label=_build_record_label(object_sentence, "Symbolic Object"),
                summary=object_sentence,
                supporting_evidence_ids=[evidence_id],
                metadata={"anchor": True},
                confidence=0.8,
            )
        )

    rule_sentence = _first_sentence_matching(sentences, ["every", "only", "must", "always", "never", "becomes", "obeys"])
    if rule_sentence:
        candidates.append(
            _world_record(
                world_id=world_id,
                layer="rule",
                record_type="rule",
                label=_build_record_label(rule_sentence, "World Rule"),
                summary=rule_sentence,
                supporting_evidence_ids=[evidence_id],
                metadata={"binding": True},
                confidence=0.83,
            )
        )

    visual_sentence = _first_sentence_matching(sentences, _VISUAL_HINTS)
    if visual_sentence:
        visual_metadata = _extract_visual_metadata(visual_sentence)
        candidates.append(
            _world_record(
                world_id=world_id,
                layer="visual",
                record_type="visual_adjacency",
                label=_build_record_label(visual_sentence, "Visual Tone").lower(),
                summary=visual_sentence,
                supporting_evidence_ids=[evidence_id],
                metadata=visual_metadata,
                confidence=0.78,
            )
        )
        candidates.append(
            _world_record(
                world_id=world_id,
                layer="visual",
                record_type="taste_rule",
                label="taste rule",
                summary=visual_sentence,
                supporting_evidence_ids=[evidence_id],
                metadata=visual_metadata,
                confidence=0.72,
            )
        )

    conflict_sentence = _first_sentence_matching(sentences, _CONFLICT_HINTS)
    if conflict_sentence:
        candidates.append(
            _world_record(
                world_id=world_id,
                layer="conflict",
                record_type="world_fragment",
                label=_build_record_label(conflict_sentence, "World Conflict"),
                summary=conflict_sentence,
                supporting_evidence_ids=[evidence_id],
                confidence=0.76,
            )
        )

    if evidence.get("modality") == "image":
        motif_text = note or label or Path(evidence.get("source_path", "")).stem.replace("-", " ")
        candidates.append(
            _world_record(
                world_id=world_id,
                layer="visual",
                record_type="visual_adjacency",
                label=_build_record_label(motif_text, "Image Reference").lower(),
                summary=motif_text,
                supporting_evidence_ids=[evidence_id],
                metadata={"reference_modality": "image", **_extract_visual_metadata(motif_text)},
                confidence=0.7,
            )
        )
        candidates.append(
            _world_record(
                world_id=world_id,
                layer="relationship",
                record_type="motif",
                label=_build_record_label(motif_text, "Motif"),
                summary=f"{motif_text} should recur as a visual motif.",
                supporting_evidence_ids=[evidence_id],
                confidence=0.64,
            )
        )

    return candidates


def _sync_population_records_into_world_graph(root: Path, world_id: str, records: List[Dict[str, Any]]) -> None:
    normalized = [_normalize_population_record(record) for record in records]
    if not normalized:
        return
    _upsert_world_records(root, world_id, normalized)


def _rebuild_world_graph_connections(root: Path, world_id: str) -> List[Dict[str, Any]]:
    records = _read_world_records(root, world_id)
    connections = _rebuild_population_connections(records)
    record_index = {record.get("knowledge_id", ""): record for record in records if record.get("knowledge_id")}
    for connection in connections:
        left = record_index.get(connection.get("left_knowledge_id", ""))
        right = record_index.get(connection.get("right_knowledge_id", ""))
        support_ids: List[str] = []
        if left:
            support_ids.extend(left.get("supporting_evidence_ids", []))
        if right:
            support_ids.extend(right.get("supporting_evidence_ids", []))
        connection["supporting_evidence_ids"] = _unique(support_ids)
        connection["explicitness"] = "inferred"
    write_jsonl(_world_links_path(root, world_id), connections)
    return connections


def _refresh_world_from_records(root: Path, world_id: str) -> Dict[str, Any]:
    world = get_world(root, world_id)
    records = _read_world_records(root, world_id)
    connections = _read_world_connections(root, world_id)
    primitives = _unique(record.get("label", "") for record in records if record.get("layer") == "primitive")
    rules = _unique(record.get("summary", "") for record in records if record.get("layer") == "rule")
    motifs = _unique(_population_motif_from_record(record) for record in records if record.get("layer") in {"object", "place", "conflict", "relationship"})
    visual_records = [record for record in records if record.get("layer") == "visual"]
    style_keywords = _unique(
        [
            *world.get("taste_profile", {}).get("style_keywords", []),
            *[record.get("label", "") for record in visual_records],
            *[
                keyword
                for record in visual_records
                for keyword in POPULATION_VISUAL_LENS_PRESETS.get(record.get("metadata", {}).get("choice", ""), {}).get("style_keywords", [])
            ],
        ]
    )
    visual_preferences = _unique(
        [
            *world.get("taste_profile", {}).get("visual_preferences", []),
            *[record.get("summary", "") for record in visual_records if record.get("summary", "")],
            *[
                keyword
                for record in visual_records
                for keyword in POPULATION_VISUAL_LENS_PRESETS.get(record.get("metadata", {}).get("choice", ""), {}).get("visual_preferences", [])
            ],
        ]
    )
    profile = dict(world.get("taste_profile", {}))
    profile["profile_name"] = profile.get("profile_name") or "adaptive world os profile"
    profile["style_keywords"] = style_keywords
    profile["visual_preferences"] = visual_preferences
    profile["forbidden"] = profile.get("forbidden", [])
    world["project_primitives"] = _unique([*world.get("project_primitives", []), *primitives])
    world["world_rules"] = _unique([*world.get("world_rules", []), *rules])
    world["active_motifs"] = _unique([*world.get("active_motifs", []), *motifs])
    world["taste_profile"] = profile
    world["visual_lens_rules"] = _merge_visual_lens_rules(world.get("visual_lens_rules", {}), visual_records)
    world["bridge_objects"] = _unique_bridge_objects([*world.get("bridge_objects", []), *_bridge_objects_from_population(records, connections)])
    population_overview = dict(world.get("population_overview", _empty_population_overview()))
    population_overview["knowledge_record_count"] = len(records)
    population_overview["connection_count"] = len(connections)
    population_overview["coverage_by_layer"] = dict(sorted(Counter(record.get("layer", "") for record in records if record.get("layer")).items()))
    population_overview["ready_for_generation"] = all(
        Counter(record.get("layer", "") for record in records if record.get("layer")).get(layer, 0) > 0
        for layer in ["primitive", "character", "place", "object", "rule", "visual", "conflict"]
    )
    world["population_overview"] = population_overview
    world["world_os_overview"] = {
        **world.get("world_os_overview", _empty_world_os_overview()),
        "evidence_count": len(read_jsonl(_source_evidence_path(root, world_id))),
        "record_count": len(records),
        "connection_count": len(connections),
        "motion_object_count": len(read_jsonl(_motion_objects_path(root, world_id))),
        "motion_binding_count": len(read_jsonl(_motion_bindings_path(root, world_id))),
        "motion_plan_count": len(read_jsonl(_motion_plans_path(root, world_id))),
        "character_profile_count": len(read_jsonl(_character_profiles_path(root, world_id))),
        "character_feature_count": len(read_jsonl(_character_feature_objects_path(root, world_id))),
        "canon_asset_count": len(read_jsonl(_canon_assets_path(root, world_id))),
        "scene_beat_count": len(read_jsonl(_scene_beats_path(root, world_id))),
        "shot_intent_count": len(read_jsonl(_shot_intents_path(root, world_id))),
        "execution_run_count": len(read_jsonl(_execution_runs_path(root, world_id))),
        "operator_manuscript_version": WORLD_STUDIO_OPERATOR_MANUSCRIPT_VERSION,
    }
    world["updated_at"] = utc_now()
    write_json(_world_path(root, world_id), world)
    return world


def ingest_evidence(
    root: Path,
    world_id: str,
    *,
    source_text: str = "",
    source_path: str = "",
    source_url: str = "",
    source_label: str = "",
    note: str = "",
    annotations: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    world = get_world(root, world_id)
    if not any(_compact_text(value) for value in [source_text, source_path, source_url, source_label, note]):
        raise ValueError("Evidence requires source_text, source_path, source_url, source_label, or note")
    evidence = {
        "evidence_id": make_id("world-evidence"),
        "created_at": utc_now(),
        "world_id": world_id,
        "source_label": _compact_text(source_label, fallback=Path(source_path or source_url or "evidence").stem or "evidence"),
        "source_text": _compact_text(source_text),
        "source_path": _compact_text(source_path),
        "source_url": _compact_text(source_url),
        "note": _compact_text(note),
        "modality": _evidence_modality(source_text, source_path, source_url),
        "annotations": annotations or {},
    }
    evidence_rows = read_jsonl(_source_evidence_path(root, world_id))
    evidence_rows.append(evidence)
    write_jsonl(_source_evidence_path(root, world_id), evidence_rows)

    candidates = _extract_candidates_from_evidence(world_id, evidence)
    candidate_rows = read_jsonl(_extracted_candidates_path(root, world_id))
    candidate_rows.extend(candidates)
    write_jsonl(_extracted_candidates_path(root, world_id), candidate_rows)

    records = _upsert_world_records(root, world_id, candidates)
    connections = _rebuild_world_graph_connections(root, world_id)
    refreshed_world = _refresh_world_from_records(root, world_id)
    _append_event(
        root,
        "world_evidence_ingested",
        {
            "world_id": world_id,
            "evidence_id": evidence["evidence_id"],
            "candidate_count": len(candidates),
            "record_count": len(records),
            "connection_count": len(connections),
        },
    )
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "evidence": evidence,
        "candidate_count": len(candidates),
        "committed_record_count": len(candidates),
        "refreshed_world": refreshed_world,
    }


def inspect_world_evidence(root: Path, world_id: str) -> Dict[str, Any]:
    world = get_world(root, world_id)
    evidence = read_jsonl(_source_evidence_path(root, world_id))
    candidates = read_jsonl(_extracted_candidates_path(root, world_id))
    records = _read_world_records(root, world_id)
    connections = _read_world_connections(root, world_id)
    uncertain = [
        row
        for row in records
        if row.get("explicitness") != "explicit" or float(row.get("provenance", {}).get("confidence", 0.0)) < 0.68
    ]
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "evidence_count": len(evidence),
        "evidence": evidence,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "records": records,
        "explicit_record_count": sum(1 for row in records if row.get("explicitness") == "explicit"),
        "inferred_record_count": max(
            sum(1 for row in records if row.get("explicitness") != "explicit"),
            len(connections),
        ),
        "inferred_connection_count": len(connections),
        "uncertain_records": uncertain,
    }


def ingest_visual_reference(
    root: Path,
    world_id: str,
    *,
    source_path: str = "",
    source_url: str = "",
    source_label: str = "",
    note: str = "",
    categories: List[str] | None = None,
    liked_aspects: List[str] | None = None,
    negative_constraints: List[str] | None = None,
    scope: str = "global",
    target_entity: str = "",
    embedding_client: Any | None = None,
) -> Dict[str, Any]:
    if not any(_compact_text(value) for value in [source_path, source_url, source_label, note]):
        raise ValueError("Visual reference requires source_path, source_url, source_label, or note")
    world = get_world(root, world_id)
    evidence_result = ingest_evidence(
        root,
        world_id,
        source_path=source_path,
        source_url=source_url,
        source_label=source_label,
        note=note,
        annotations={
            "visual_reference": True,
            "scope": scope,
            "target_entity": target_entity,
            "categories": categories or [],
        },
    )
    resolved_categories = _unique(categories or _infer_visual_categories(note, source_label, target_entity))
    resolved_traits = _visual_trait_candidates(note, liked_aspects or [])
    resolved_negatives = _unique(negative_constraints or [])
    image_url = _image_url_for_embedding(source_path, source_url)
    client = embedding_client if embedding_client is not None else OpenRouterEmbeddingClient.from_runtime(root)
    embedding_info: Dict[str, Any] = {
        "model": "",
        "vector": [],
        "usage": {},
        "source": "disabled",
        "fallback_reason": "",
    }
    if client is not None:
        try:
            embedded = _embed_documents(
                client,
                [
                    {
                        "modality": "image" if image_url else "text",
                        "text": note or source_label,
                        "image_url": image_url,
                    }
                ],
                input_type="search_document",
            )
        except Exception as exc:  # noqa: BLE001
            embedded = []
            embedding_info["fallback_reason"] = str(exc)
        if not embedded and (note or source_label):
            try:
                embedded = _embed_documents(
                    client,
                    [{"modality": "text", "text": note or source_label}],
                    input_type="search_document",
                )
            except Exception as exc:  # noqa: BLE001
                embedded = []
                if not embedding_info["fallback_reason"]:
                    embedding_info["fallback_reason"] = str(exc)
            if embedded:
                embedding_info["source"] = "text_fallback"
        if embedded:
            embedding_info = {
                **embedding_info,
                "model": embedded[0].get("model", ""),
                "vector": embedded[0].get("embedding", []),
                "usage": embedded[0].get("usage", {}),
                "source": embedding_info.get("source") or getattr(client, "model_name", embedded[0].get("model", "")),
            }
    reference = {
        "visual_reference_id": make_id("visual-reference"),
        "created_at": utc_now(),
        "world_id": world_id,
        "evidence_id": evidence_result["evidence"]["evidence_id"],
        "source_label": _compact_text(source_label, fallback=Path(source_path or source_url or "visual-reference").stem or "visual-reference"),
        "source_path": _compact_text(source_path),
        "source_url": _compact_text(source_url),
        "note": _compact_text(note),
        "scope": _compact_text(scope, fallback="global"),
        "target_entity": _compact_text(target_entity),
        "categories": resolved_categories,
        "liked_aspects": resolved_traits,
        "negative_constraints": resolved_negatives,
        "embedding": embedding_info,
        "tags": _tokenize_tags(source_label, note, target_entity, *resolved_traits, *resolved_categories),
    }
    references = read_jsonl(_visual_references_path(root, world_id))
    references.append(reference)
    write_jsonl(_visual_references_path(root, world_id), references)

    traits = read_jsonl(_visual_traits_path(root, world_id))
    for trait_text in resolved_traits:
        trait_categories = _infer_visual_categories(trait_text)
        assigned_categories = [category for category in resolved_categories if category in trait_categories] or resolved_categories[:1]
        for category in assigned_categories:
            traits.append(
                {
                    "visual_trait_id": make_id("visual-trait"),
                    "created_at": utc_now(),
                    "world_id": world_id,
                    "visual_reference_id": reference["visual_reference_id"],
                    "evidence_id": reference["evidence_id"],
                    "category": category,
                    "trait_text": trait_text,
                    "scope": reference["scope"],
                    "target_entity": reference["target_entity"],
                    "tags": _tokenize_tags(trait_text, category, target_entity),
                }
            )
    write_jsonl(_visual_traits_path(root, world_id), traits)

    committed_records = [
        _world_record(
            world_id=world_id,
            layer="visual",
            record_type="visual_trait",
            label=trait.get("trait_text", ""),
            summary=trait.get("trait_text", ""),
            supporting_evidence_ids=[reference["evidence_id"]],
            tags=trait.get("tags", []),
            metadata={
                "category": trait.get("category", ""),
                "scope": trait.get("scope", ""),
                "target_entity": trait.get("target_entity", ""),
                "visual_reference_id": reference["visual_reference_id"],
            },
            confidence=0.78,
        )
        for trait in traits
        if trait.get("visual_reference_id") == reference["visual_reference_id"]
    ]
    if committed_records:
        _upsert_world_records(root, world_id, committed_records)
        _rebuild_world_graph_connections(root, world_id)
        _refresh_world_from_records(root, world_id)
    _append_event(
        root,
        "visual_reference_ingested",
        {
            "world_id": world_id,
            "visual_reference_id": reference["visual_reference_id"],
            "category_count": len(resolved_categories),
            "trait_count": len(resolved_traits),
        },
    )
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "reference": reference,
        "trait_count": len(resolved_traits),
        "categories": resolved_categories,
    }


def inspect_visual_world(root: Path, world_id: str) -> Dict[str, Any]:
    world = get_world(root, world_id)
    references = read_jsonl(_visual_references_path(root, world_id))
    traits = read_jsonl(_visual_traits_path(root, world_id))
    coverage = Counter(trait.get("category", "") for trait in traits if trait.get("category"))
    negative_constraints = _unique(
        item
        for reference in references
        for item in reference.get("negative_constraints", [])
    )
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "reference_count": len(references),
        "trait_count": len(traits),
        "coverage_by_category": dict(sorted(coverage.items())),
        "references": references,
        "traits": traits,
        "negative_constraints": negative_constraints,
    }


def compile_visual_context(
    root: Path,
    world_id: str,
    *,
    query_text: str,
    embedding_client: Any | None = None,
    top_k_references: int = 4,
    top_k_traits: int = 8,
) -> Dict[str, Any]:
    visual = inspect_visual_world(root, world_id)
    references = list(visual["references"])
    traits = list(visual["traits"])
    query_tags = set(_tokenize_tags(query_text))
    client = embedding_client if embedding_client is not None else OpenRouterEmbeddingClient.from_runtime(root)
    query_vector: List[float] = []
    embedding_model = ""
    if client is not None:
        try:
            embedded = _embed_documents(client, [{"modality": "text", "text": query_text}], input_type="search_query")
        except Exception:
            embedded = []
        if embedded:
            query_vector = embedded[0].get("embedding", [])
            embedding_model = embedded[0].get("model", "")
    scored_references: List[Dict[str, Any]] = []
    for reference in references:
        lexical = len(query_tags & set(reference.get("tags", []))) / max(len(query_tags), 1)
        vector_score = _vector_cosine_similarity(query_vector, reference.get("embedding", {}).get("vector", [])) if query_vector else 0.0
        score = vector_score if query_vector else lexical
        score += lexical * 0.25
        scored_references.append({**reference, "score": round(score, 6)})
    scored_references.sort(key=lambda row: row.get("score", 0.0), reverse=True)
    selected_references = scored_references[:top_k_references]
    selected_reference_ids = {row.get("visual_reference_id", "") for row in selected_references}
    scored_traits: List[Dict[str, Any]] = []
    for trait in traits:
        if trait.get("visual_reference_id", "") not in selected_reference_ids and selected_reference_ids:
            continue
        lexical = len(query_tags & set(trait.get("tags", []))) / max(len(query_tags), 1)
        reference_score = next((row.get("score", 0.0) for row in selected_references if row.get("visual_reference_id") == trait.get("visual_reference_id")), 0.0)
        score = reference_score + lexical
        scored_traits.append({**trait, "score": round(score, 6)})
    scored_traits.sort(key=lambda row: row.get("score", 0.0), reverse=True)
    selected_traits = scored_traits[:top_k_traits]
    active_categories = _unique(trait.get("category", "") for trait in selected_traits if trait.get("category"))
    by_category: Dict[str, List[str]] = {}
    for trait in selected_traits:
        by_category.setdefault(trait.get("category", ""), []).append(trait.get("trait_text", ""))
    category_summaries = [
        {
            "category": category,
            "traits": _unique(values),
        }
        for category, values in by_category.items()
        if category
    ]
    return {
        "world_id": world_id,
        "query_text": query_text,
        "embedding_model": embedding_model,
        "selected_references": selected_references,
        "selected_reference_count": len(selected_references),
        "selected_traits": selected_traits,
        "selected_trait_count": len(selected_traits),
        "active_categories": active_categories,
        "category_summaries": category_summaries,
        "negative_constraints": visual["negative_constraints"],
    }


def _normalize_motion_object(motion_object: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(motion_object)
    normalized["label"] = _compact_text(normalized.get("label", "Motion Object"), fallback="Motion Object")
    normalized["scope"] = _compact_text(normalized.get("scope", "character"), fallback="character").lower()
    normalized["intent"] = _compact_text(normalized.get("intent", ""))
    normalized["primary_action"] = _compact_text(normalized.get("primary_action", ""))
    normalized["body_mechanics"] = _unique(str(item).strip() for item in normalized.get("body_mechanics", []))
    normalized["secondary_motion"] = _unique(str(item).strip() for item in normalized.get("secondary_motion", []))
    normalized["constraints"] = _unique(str(item).strip() for item in normalized.get("constraints", []))
    normalized["negative_constraints"] = _unique(str(item).strip() for item in normalized.get("negative_constraints", []))
    normalized["compatible_states"] = _unique(str(item).strip().lower() for item in normalized.get("compatible_states", []))
    normalized["prompt_template"] = _compact_text(normalized.get("prompt_template", ""))
    normalized["speed"] = _compact_text(normalized.get("speed", ""))
    normalized["intensity"] = _compact_text(normalized.get("intensity", ""))
    normalized["best_clip_duration"] = int(normalized.get("best_clip_duration", 4) or 4)
    metadata = dict(normalized.get("metadata", {}))
    metadata["tags"] = _unique(
        [
            *metadata.get("tags", []),
            *_tokenize_tags(
                normalized["label"],
                normalized["intent"],
                normalized["primary_action"],
                " ".join(normalized["body_mechanics"]),
                " ".join(normalized["secondary_motion"]),
            ),
        ]
    )
    normalized["metadata"] = metadata
    return normalized


def _normalize_motion_binding(binding: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(binding)
    normalized["target_kind"] = _compact_text(normalized.get("target_kind", "character"), fallback="character").lower()
    normalized["target_id"] = _compact_text(normalized.get("target_id", "default"), fallback="default")
    normalized["when_tags"] = _unique(str(item).strip().lower() for item in normalized.get("when_tags", []))
    normalized["exclude_tags"] = _unique(str(item).strip().lower() for item in normalized.get("exclude_tags", []))
    normalized["priority"] = int(normalized.get("priority", 1) or 1)
    normalized["metadata"] = dict(normalized.get("metadata", {}))
    return normalized


def create_motion_object(
    root: Path,
    world_id: str,
    *,
    label: str,
    scope: str,
    intent: str = "",
    primary_action: str = "",
    body_mechanics: List[str] | None = None,
    secondary_motion: List[str] | None = None,
    constraints: List[str] | None = None,
    negative_constraints: List[str] | None = None,
    compatible_states: List[str] | None = None,
    speed: str = "",
    intensity: str = "",
    best_clip_duration: int = 4,
    prompt_template: str = "",
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    world = get_world(root, world_id)
    motion_object = _normalize_motion_object(
        {
            "motion_id": make_id("world-motion"),
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "world_id": world_id,
            "label": label,
            "scope": scope,
            "intent": intent,
            "primary_action": primary_action,
            "body_mechanics": body_mechanics or [],
            "secondary_motion": secondary_motion or [],
            "constraints": constraints or [],
            "negative_constraints": negative_constraints or [],
            "compatible_states": compatible_states or [],
            "speed": speed,
            "intensity": intensity,
            "best_clip_duration": best_clip_duration,
            "prompt_template": prompt_template,
            "metadata": metadata or {},
        }
    )
    rows = read_jsonl(_motion_objects_path(root, world_id))
    rows.append(motion_object)
    write_jsonl(_motion_objects_path(root, world_id), rows)
    refreshed_world = _refresh_world_from_records(root, world_id)
    _append_event(
        root,
        "motion_object_created",
        {
            "world_id": world_id,
            "motion_id": motion_object["motion_id"],
            "scope": motion_object["scope"],
            "label": motion_object["label"],
        },
    )
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "motion_id": motion_object["motion_id"],
        "motion_object": motion_object,
        "refreshed_world": refreshed_world,
    }


def bind_motion_object(
    root: Path,
    world_id: str,
    *,
    motion_id: str,
    target_kind: str,
    target_id: str = "default",
    when_tags: List[str] | None = None,
    exclude_tags: List[str] | None = None,
    priority: int = 1,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    world = get_world(root, world_id)
    motion_objects = {row.get("motion_id", ""): row for row in read_jsonl(_motion_objects_path(root, world_id))}
    if motion_id not in motion_objects:
        raise ValueError(f"Unknown motion object: {motion_id}")
    binding = _normalize_motion_binding(
        {
            "binding_id": make_id("world-motion-binding"),
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "world_id": world_id,
            "motion_id": motion_id,
            "target_kind": target_kind,
            "target_id": target_id,
            "when_tags": when_tags or [],
            "exclude_tags": exclude_tags or [],
            "priority": priority,
            "metadata": metadata or {},
        }
    )
    rows = read_jsonl(_motion_bindings_path(root, world_id))
    rows.append(binding)
    write_jsonl(_motion_bindings_path(root, world_id), rows)
    refreshed_world = _refresh_world_from_records(root, world_id)
    _append_event(
        root,
        "motion_object_bound",
        {
            "world_id": world_id,
            "motion_id": motion_id,
            "binding_id": binding["binding_id"],
            "target_kind": binding["target_kind"],
            "target_id": binding["target_id"],
        },
    )
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "binding": binding,
        "motion_object": motion_objects[motion_id],
        "refreshed_world": refreshed_world,
    }


def inspect_motion_system(root: Path, world_id: str) -> Dict[str, Any]:
    world = get_world(root, world_id)
    motion_objects = [_normalize_motion_object(row) for row in read_jsonl(_motion_objects_path(root, world_id))]
    bindings = [_normalize_motion_binding(row) for row in read_jsonl(_motion_bindings_path(root, world_id))]
    by_id = {row.get("motion_id", ""): row for row in motion_objects}
    coverage = Counter(row.get("scope", "") for row in motion_objects if row.get("scope"))
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "motion_object_count": len(motion_objects),
        "binding_count": len(bindings),
        "coverage_by_scope": dict(sorted(coverage.items())),
        "motion_objects": motion_objects,
        "bindings": [
            {
                **binding,
                "motion_label": by_id.get(binding.get("motion_id", ""), {}).get("label", ""),
                "motion_scope": by_id.get(binding.get("motion_id", ""), {}).get("scope", ""),
            }
            for binding in bindings
        ],
        "stored_plan_count": len(read_jsonl(_motion_plans_path(root, world_id))),
    }


def _scene_state_tags(scene_text: str) -> List[str]:
    lowered = scene_text.lower()
    tags: List[str] = []
    if any(token in lowered for token in ["dream", "memory", "vision", "sleep"]):
        tags.append("dream")
    if any(token in lowered for token in ["night", "moon", "nocturnal", "midnight", "dark"]):
        tags.append("night")
    if any(token in lowered for token in ["day", "daylight", "sun", "morning", "afternoon"]):
        tags.append("day")
    return tags or ["default"]


def _motion_binding_score(
    binding: Dict[str, Any],
    motion_object: Dict[str, Any],
    *,
    scene_tags: set[str],
    state_tags: set[str],
) -> float:
    score = float(binding.get("priority", 1))
    when_tags = set(binding.get("when_tags", []))
    exclude_tags = set(binding.get("exclude_tags", []))
    if exclude_tags and exclude_tags & scene_tags:
        return -1000.0
    if when_tags:
        overlap = len(when_tags & scene_tags)
        if overlap == 0 and binding.get("target_id", "") not in {"default", "*", ""}:
            return -1000.0
        score += overlap * 3.0
    else:
        score += 0.5
    target_id = str(binding.get("target_id", "")).strip().lower()
    if target_id in {"default", "*", ""}:
        score += 0.75
    else:
        target_tokens = set(_tokenize_tags(target_id))
        overlap = len(target_tokens & scene_tags)
        if overlap == 0:
            return -1000.0
        score += overlap * 2.0
    compatible_states = set(motion_object.get("compatible_states", []))
    if compatible_states and compatible_states.isdisjoint(state_tags):
        score -= 3.0
    elif compatible_states & state_tags:
        score += 1.5
    score += len(set(motion_object.get("metadata", {}).get("tags", [])) & scene_tags) * 0.2
    return score


def _motion_prompt_clause(motion_object: Dict[str, Any]) -> str:
    parts = []
    if motion_object.get("primary_action"):
        parts.append(motion_object["primary_action"])
    if motion_object.get("body_mechanics"):
        parts.append(", ".join(motion_object["body_mechanics"]))
    if motion_object.get("secondary_motion"):
        parts.append(", ".join(motion_object["secondary_motion"]))
    if motion_object.get("speed"):
        parts.append(f"speed: {motion_object['speed']}")
    if motion_object.get("intensity"):
        parts.append(f"intensity: {motion_object['intensity']}")
    if motion_object.get("prompt_template"):
        parts.append(motion_object["prompt_template"])
    return ". ".join(part.strip().rstrip(".") for part in parts if part).strip()


def compile_motion_plan(
    root: Path,
    world_id: str,
    *,
    scene_text: str,
    duration_seconds: int = 4,
) -> Dict[str, Any]:
    world = get_world(root, world_id)
    motion_objects = {row.get("motion_id", ""): _normalize_motion_object(row) for row in read_jsonl(_motion_objects_path(root, world_id))}
    bindings = [_normalize_motion_binding(row) for row in read_jsonl(_motion_bindings_path(root, world_id))]
    scene_tags = set(_tokenize_tags(scene_text))
    state_tags = set(_scene_state_tags(scene_text))
    candidates: List[Dict[str, Any]] = []
    for binding in bindings:
        motion_object = motion_objects.get(binding.get("motion_id", ""))
        if not motion_object:
            continue
        score = _motion_binding_score(binding, motion_object, scene_tags=scene_tags, state_tags=state_tags)
        if score <= -100:
            continue
        candidates.append(
            {
                "binding": binding,
                "motion_object": motion_object,
                "score": round(score, 4),
            }
        )
    candidates.sort(
        key=lambda row: (
            row["score"],
            row["motion_object"].get("scope", ""),
            row["motion_object"].get("best_clip_duration", 0) == duration_seconds,
        ),
        reverse=True,
    )
    selected: List[Dict[str, Any]] = []
    selected_scopes: set[str] = set()
    for row in candidates:
        scope = row["motion_object"].get("scope", "")
        if scope in selected_scopes:
            continue
        selected.append(row)
        selected_scopes.add(scope)
    def _scope_rows(scope: str) -> List[Dict[str, Any]]:
        rows = []
        for row in selected:
            if row["motion_object"].get("scope") != scope:
                continue
            rows.append(
                {
                    "motion_id": row["motion_object"]["motion_id"],
                    "label": row["motion_object"]["label"],
                    "intent": row["motion_object"].get("intent", ""),
                    "target_kind": row["binding"].get("target_kind", ""),
                    "target_id": row["binding"].get("target_id", ""),
                    "primary_action": row["motion_object"].get("primary_action", ""),
                    "body_mechanics": row["motion_object"].get("body_mechanics", []),
                    "secondary_motion": row["motion_object"].get("secondary_motion", []),
                    "speed": row["motion_object"].get("speed", ""),
                    "intensity": row["motion_object"].get("intensity", ""),
                    "constraints": row["motion_object"].get("constraints", []),
                    "negative_constraints": row["motion_object"].get("negative_constraints", []),
                    "score": row["score"],
                }
            )
        return rows

    prompt_lines = []
    for row in selected:
        scope = row["motion_object"].get("scope", "motion")
        clause = _motion_prompt_clause(row["motion_object"])
        if clause:
            prompt_lines.append(f"{scope}: {clause}")
    plan = {
        "motion_plan_id": make_id("world-motion-plan"),
        "created_at": utc_now(),
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "scene_text": scene_text,
        "duration_seconds": duration_seconds,
        "state_tags": sorted(state_tags),
        "selected_motion_count": len(selected),
        "selected_motion_ids": [row["motion_object"]["motion_id"] for row in selected],
        "character_motion": _scope_rows("character"),
        "camera_motion": _scope_rows("camera"),
        "cloth_motion": _scope_rows("cloth"),
        "environment_motion": _scope_rows("environment"),
        "prop_motion": _scope_rows("prop"),
        "transition_motion": _scope_rows("transition"),
        "compiled_prompt": "\n".join(prompt_lines).strip(),
    }
    rows = read_jsonl(_motion_plans_path(root, world_id))
    rows.append(plan)
    write_jsonl(_motion_plans_path(root, world_id), rows)
    _append_event(
        root,
        "motion_plan_compiled",
        {
            "world_id": world_id,
            "motion_plan_id": plan["motion_plan_id"],
            "selected_motion_count": plan["selected_motion_count"],
        },
    )
    _refresh_world_from_records(root, world_id)
    return plan


_CHARACTER_FEATURE_TEMPLATES = [
    {
        "feature_type": "silhouette_presence",
        "label": "Silhouette Presence",
        "prompt": "What is the first readable physical impression of this character from a distance?",
    },
    {
        "feature_type": "garment_system",
        "label": "Garment System",
        "prompt": "How do garments, drape, and material logic make this character belong to the world?",
    },
    {
        "feature_type": "movement_signature",
        "label": "Movement Signature",
        "prompt": "What kind of movement should this character default to when they are simply existing in the frame?",
    },
    {
        "feature_type": "voice_silence",
        "label": "Voice And Silence",
        "prompt": "How does this character sound, and how do they use silence?",
    },
    {
        "feature_type": "inner_pressure",
        "label": "Inner Pressure",
        "prompt": "What desire, fear, wound, or contradiction organizes this character internally?",
    },
    {
        "feature_type": "object_affinity",
        "label": "Object Affinity",
        "prompt": "Which object, tool, or ritual material best externalizes this character?",
    },
]


def _empty_character_sections() -> Dict[str, Any]:
    return {
        "identity": {
            "one_line_essence": "",
            "public_role": "",
            "private_truth": "",
            "age_band": "",
            "gender_presentation": "",
        },
        "world_position": {
            "home_zone": "",
            "social_position": "",
            "faction_links": [],
            "duty": "",
        },
        "psychology": {
            "core_desire": "",
            "core_fear": "",
            "contradiction": "",
            "emotional_mask": "",
            "vulnerability": "",
        },
        "visual_identity": {
            "silhouette_summary": "",
            "garment_logic": "",
            "palette_logic": "",
            "material_logic": "",
            "distinguishing_features": [],
        },
        "movement_identity": {
            "baseline_motion_ids": [],
            "posture": "",
            "pace": "",
            "gesture_rules": [],
        },
        "voice_identity": {
            "speech_texture": "",
            "silence_behavior": "",
            "lexical_tics": [],
        },
        "story_function": {
            "world_role": "",
            "entrance_function": "",
            "pressure_response": "",
            "transformation_axis": "",
        },
        "state_variants": {
            "day": "",
            "night": "",
            "dream": "",
        },
        "constraints": {
            "must_preserve": [],
            "avoid": [],
        },
        "open_questions": [],
    }


def _normalize_character_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(profile)
    normalized["name"] = _compact_text(normalized.get("name", "Unnamed Character"), fallback="Unnamed Character")
    normalized["summary"] = _compact_text(normalized.get("summary", ""))
    normalized["role"] = _compact_text(normalized.get("role", ""))
    normalized["status"] = _compact_text(normalized.get("status", "draft"), fallback="draft")
    sections = _empty_character_sections()
    existing_sections = dict(normalized.get("sections", {}))
    for key, default_value in sections.items():
        current = existing_sections.get(key, default_value)
        sections[key] = dict(default_value) if isinstance(default_value, dict) else list(default_value)
        if isinstance(default_value, dict) and isinstance(current, dict):
            sections[key].update(current)
        elif isinstance(default_value, list) and isinstance(current, list):
            sections[key] = current
    normalized["sections"] = sections
    normalized["feature_object_ids"] = _unique(normalized.get("feature_object_ids", []))
    metadata = dict(normalized.get("metadata", {}))
    metadata["tags"] = _unique([*metadata.get("tags", []), *_tokenize_tags(normalized["name"], normalized["summary"], normalized["role"])])
    normalized["metadata"] = metadata
    return normalized


def _normalize_character_feature_object(feature: Dict[str, Any]) -> Dict[str, Any]:
    normalized = dict(feature)
    normalized["feature_type"] = _compact_text(normalized.get("feature_type", "feature"), fallback="feature").lower()
    normalized["label"] = _compact_text(normalized.get("label", "Feature"), fallback="Feature")
    normalized["summary"] = _compact_text(normalized.get("summary", ""))
    normalized["trait_values"] = _unique(str(item).strip() for item in normalized.get("trait_values", []))
    normalized["state_scope"] = _compact_text(normalized.get("state_scope", "global"), fallback="global").lower()
    metadata = dict(normalized.get("metadata", {}))
    metadata["tags"] = _unique(
        [
            *metadata.get("tags", []),
            *_tokenize_tags(normalized["label"], normalized["summary"], normalized["feature_type"], " ".join(normalized["trait_values"])),
        ]
    )
    normalized["metadata"] = metadata
    return normalized


def _character_profile_summary(profile: Dict[str, Any]) -> str:
    sections = profile.get("sections", {})
    identity = sections.get("identity", {})
    psychology = sections.get("psychology", {})
    movement = sections.get("movement_identity", {})
    pieces = [
        profile.get("summary", ""),
        identity.get("one_line_essence", ""),
        identity.get("public_role", ""),
        psychology.get("core_desire", ""),
        psychology.get("contradiction", ""),
        movement.get("pace", ""),
    ]
    return _compact_text(" | ".join(piece for piece in pieces if piece))


def _upsert_character_world_record(root: Path, world_id: str, profile: Dict[str, Any]) -> None:
    record = _world_record(
        world_id=world_id,
        layer="character",
        record_type="character",
        label=profile.get("name", ""),
        summary=_character_profile_summary(profile) or profile.get("summary", "") or profile.get("name", ""),
        tags=_unique([*profile.get("metadata", {}).get("tags", []), "character", "profile"]),
        metadata={"character_id": profile.get("character_id", ""), "profile_status": profile.get("status", "draft")},
        provenance_source="character_profile",
        confidence=0.82,
    )
    _upsert_world_records(root, world_id, [record])
    _rebuild_world_graph_connections(root, world_id)


def create_character_feature_object(
    root: Path,
    world_id: str,
    *,
    character_id: str,
    feature_type: str,
    label: str,
    summary: str = "",
    trait_values: List[str] | None = None,
    state_scope: str = "global",
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    world = get_world(root, world_id)
    feature_object = _normalize_character_feature_object(
        {
            "feature_id": make_id("world-character-feature"),
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "world_id": world_id,
            "character_id": character_id,
            "feature_type": feature_type,
            "label": label,
            "summary": summary,
            "trait_values": trait_values or [],
            "state_scope": state_scope,
            "metadata": metadata or {},
        }
    )
    rows = read_jsonl(_character_feature_objects_path(root, world_id))
    rows.append(feature_object)
    write_jsonl(_character_feature_objects_path(root, world_id), rows)
    _refresh_world_from_records(root, world_id)
    _append_event(
        root,
        "character_feature_object_created",
        {
            "world_id": world_id,
            "character_id": character_id,
            "feature_id": feature_object["feature_id"],
            "feature_type": feature_object["feature_type"],
        },
    )
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "feature_object": feature_object,
    }


def create_character_profile(
    root: Path,
    world_id: str,
    *,
    name: str,
    summary: str = "",
    role: str = "",
) -> Dict[str, Any]:
    world = get_world(root, world_id)
    character_id = make_id("world-character")
    profile = _normalize_character_profile(
        {
            "character_id": character_id,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "world_id": world_id,
            "name": name,
            "summary": summary,
            "role": role,
            "status": "scaffold",
            "sections": _empty_character_sections(),
            "feature_object_ids": [],
            "metadata": {"tags": ["character", "scaffold"]},
        }
    )
    starter_features: List[Dict[str, Any]] = []
    for template in _CHARACTER_FEATURE_TEMPLATES:
        created = create_character_feature_object(
            root,
            world_id,
            character_id=character_id,
            feature_type=template["feature_type"],
            label=template["label"],
            summary="",
            trait_values=[],
            metadata={"prompt": template["prompt"], "tags": [template["feature_type"], "character_feature_scaffold"]},
        )
        starter_features.append(created["feature_object"])
    profile["feature_object_ids"] = [row["feature_id"] for row in starter_features]
    rows = read_jsonl(_character_profiles_path(root, world_id))
    rows.append(profile)
    write_jsonl(_character_profiles_path(root, world_id), rows)
    _upsert_character_world_record(root, world_id, profile)
    refreshed_world = _refresh_world_from_records(root, world_id)
    _append_event(
        root,
        "character_profile_created",
        {"world_id": world_id, "character_id": character_id, "name": profile["name"], "feature_count": len(starter_features)},
    )
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "character_id": character_id,
        "profile": profile,
        "starter_features": starter_features,
        "refreshed_world": refreshed_world,
    }


def _load_character_profiles(root: Path, world_id: str) -> List[Dict[str, Any]]:
    return [_normalize_character_profile(row) for row in read_jsonl(_character_profiles_path(root, world_id))]


def _load_character_features(root: Path, world_id: str) -> List[Dict[str, Any]]:
    return [_normalize_character_feature_object(row) for row in read_jsonl(_character_feature_objects_path(root, world_id))]


def inspect_character_system(root: Path, world_id: str, character_id: str = "") -> Dict[str, Any]:
    world = get_world(root, world_id)
    profiles = _load_character_profiles(root, world_id)
    features = _load_character_features(root, world_id)
    if character_id:
        profiles = [row for row in profiles if row.get("character_id") == character_id]
        features = [row for row in features if row.get("character_id") == character_id]
    features_by_character: Dict[str, List[Dict[str, Any]]] = {}
    for feature in features:
        features_by_character.setdefault(feature.get("character_id", ""), []).append(feature)
    bundled_profiles = []
    for profile in profiles:
        bundled_profiles.append(
            {
                **profile,
                "feature_objects": features_by_character.get(profile.get("character_id", ""), []),
            }
        )
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "character_profile_count": len(profiles),
        "feature_object_count": len(features),
        "profiles": bundled_profiles,
        "feature_objects": features,
    }


def update_character_profile_section(
    root: Path,
    world_id: str,
    character_id: str,
    *,
    section: str,
    value: Dict[str, Any] | List[Any] | str,
) -> Dict[str, Any]:
    world = get_world(root, world_id)
    rows = _load_character_profiles(root, world_id)
    updated: Dict[str, Any] | None = None
    for index, row in enumerate(rows):
        if row.get("character_id") != character_id:
            continue
        sections = dict(row.get("sections", {}))
        if section not in sections:
            raise ValueError(f"Unknown character section: {section}")
        if isinstance(sections[section], dict):
            if not isinstance(value, dict):
                raise ValueError(f"Section {section} requires a JSON object value.")
            merged = dict(sections[section])
            merged.update(value)
            sections[section] = merged
        else:
            sections[section] = value
        row["sections"] = sections
        row["updated_at"] = utc_now()
        if _character_profile_summary(row):
            row["status"] = "in_progress"
        updated = _normalize_character_profile(row)
        rows[index] = updated
        break
    if updated is None:
        raise FileNotFoundError(f"Character not found: {character_id}")
    write_jsonl(_character_profiles_path(root, world_id), rows)
    _upsert_character_world_record(root, world_id, updated)
    refreshed_world = _refresh_world_from_records(root, world_id)
    _append_event(
        root,
        "character_profile_updated",
        {"world_id": world_id, "character_id": character_id, "section": section},
    )
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "profile": updated,
        "refreshed_world": refreshed_world,
    }


def update_character_feature_object(
    root: Path,
    world_id: str,
    feature_id: str,
    *,
    summary: str = "",
    trait_values: List[str] | None = None,
    state_scope: str = "",
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    world = get_world(root, world_id)
    rows = _load_character_features(root, world_id)
    updated: Dict[str, Any] | None = None
    for index, row in enumerate(rows):
        if row.get("feature_id") != feature_id:
            continue
        if summary:
            row["summary"] = summary
        if trait_values is not None:
            row["trait_values"] = trait_values
        if state_scope:
            row["state_scope"] = state_scope
        if metadata:
            merged_meta = dict(row.get("metadata", {}))
            merged_meta.update(metadata)
            row["metadata"] = merged_meta
        row["updated_at"] = utc_now()
        updated = _normalize_character_feature_object(row)
        rows[index] = updated
        break
    if updated is None:
        raise FileNotFoundError(f"Character feature not found: {feature_id}")
    write_jsonl(_character_feature_objects_path(root, world_id), rows)
    _refresh_world_from_records(root, world_id)
    _append_event(
        root,
        "character_feature_object_updated",
        {"world_id": world_id, "feature_id": feature_id, "character_id": updated.get("character_id", "")},
    )
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "feature_object": updated,
    }


def _select_character_profiles(root: Path, world_id: str, scene_text: str) -> List[Dict[str, Any]]:
    system = inspect_character_system(root, world_id)
    profiles = system.get("profiles", [])
    if not profiles:
        return []
    scene_tags = set(_tokenize_tags(scene_text))
    scored: List[Dict[str, Any]] = []
    for profile in profiles:
        lexical = len(scene_tags & set(profile.get("metadata", {}).get("tags", [])))
        lexical += len(scene_tags & set(_tokenize_tags(profile.get("name", ""), profile.get("summary", ""), profile.get("role", ""))))
        lexical += sum(len(scene_tags & set(feature.get("metadata", {}).get("tags", []))) for feature in profile.get("feature_objects", []))
        if lexical <= 0 and len(profiles) == 1:
            lexical = 1
        scored.append({**profile, "score": lexical})
    scored.sort(key=lambda row: row.get("score", 0), reverse=True)
    selected = [row for row in scored if row.get("score", 0) > 0][:2]
    return selected or scored[:1]


def next_worldbuilding_question(root: Path, world_id: str) -> Dict[str, Any]:
    active_session = _active_population_session_for_world(root, world_id)
    if active_session is not None:
        payload = _population_question_payload(root, active_session)
        payload["question_source"] = "population_session"
        return payload
    world = get_world(root, world_id)
    records = _read_world_records(root, world_id)
    connections = _read_world_connections(root, world_id)
    coverage = Counter(record.get("layer", "") for record in records if record.get("layer"))
    question_id = None
    for candidate in POPULATION_CORE_SEQUENCE:
        if _population_question_needs_records(candidate, coverage, records):
            question_id = candidate
            break
    if question_id is None:
        question_id = "connection_probe"
    question = _population_question(question_id, world, records)
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "question_id": question_id,
        "question": question["question"],
        "selection_mode": question["selection_mode"],
        "allow_free_text": question["allow_free_text"],
        "response_options": question["response_options"],
        "why_this_matters": question["why_this_matters"],
        "knowledge_preview": _knowledge_preview(records, connections),
        "question_source": "world_graph_planner",
    }


def _canon_prompt_for_asset(world: Dict[str, Any], record: Dict[str, Any]) -> str:
    return "\n".join(
        [
            f"Generate a canonical {record.get('record_type', record.get('layer', 'world element'))} reference.",
            f"World: {world.get('name', '')}",
            f"World summary: {world.get('summary', '')}",
            f"Label: {record.get('label', '')}",
            f"Meaning: {record.get('summary', '')}",
            f"Style keywords: {', '.join(world.get('taste_profile', {}).get('style_keywords', []))}",
            f"Active motifs: {', '.join(world.get('active_motifs', []))}",
            "Preserve the world's canon and avoid unrelated decoration.",
        ]
    )


def _canon_asset_signature(asset: Dict[str, Any]) -> str:
    return f"{asset.get('asset_type', '').strip().lower()}::{slugify(asset.get('label', ''))}"


def generate_canon(root: Path, world_id: str, *, asset_types: List[str] | None = None, style_note: str = "") -> Dict[str, Any]:
    world = get_world(root, world_id)
    records = _read_world_records(root, world_id)
    wanted = {item.strip().lower() for item in (asset_types or []) if item.strip()}
    candidates: List[Dict[str, Any]] = []
    existing_assets = list(read_jsonl(_canon_assets_path(root, world_id)))
    by_signature = {_canon_asset_signature(asset): dict(asset) for asset in existing_assets}
    ordered_signatures = [_canon_asset_signature(asset) for asset in existing_assets]
    layer_to_asset = {
        "character": "character",
        "place": "place",
        "object": "object",
        "visual": "motif",
        "primitive": "motif",
    }
    seen: set[str] = set()
    for record in records:
        asset_type = layer_to_asset.get(record.get("layer", ""))
        if not asset_type:
            continue
        if wanted and asset_type not in wanted:
            continue
        signature = f"{asset_type}::{slugify(record.get('label', ''))}"
        if signature in seen:
            continue
        seen.add(signature)
        prompt = _canon_prompt_for_asset(world, record)
        if style_note.strip():
            prompt = f"{prompt}\nStyle note: {style_note.strip()}"
        canon_signature = f"{asset_type}::{slugify(record.get('label', ''))}"
        existing = by_signature.get(canon_signature, {})
        asset = {
            "canon_id": existing.get("canon_id", make_id("world-canon")),
            "created_at": existing.get("created_at", utc_now()),
            "updated_at": utc_now(),
            "world_id": world_id,
            "asset_type": asset_type,
            "label": record.get("label", ""),
            "summary": record.get("summary", ""),
            "source_record_ids": _unique([*existing.get("source_record_ids", []), record.get("knowledge_id", "")]),
            "supporting_evidence_ids": _unique(
                [*existing.get("supporting_evidence_ids", []), *record.get("supporting_evidence_ids", [])]
            ),
            "provider": "higgsfield",
            "tool": "generate_reference",
            "compiled_prompt": prompt,
            "metadata": {
                **dict(existing.get("metadata", {})),
                "layer": record.get("layer", ""),
                "record_type": record.get("record_type", ""),
                "style_note": style_note,
                "tags": _unique([*existing.get("metadata", {}).get("tags", []), *record.get("tags", [])]),
            },
        }
        by_signature[canon_signature] = asset
        if canon_signature not in ordered_signatures:
            ordered_signatures.append(canon_signature)
        candidates.append(asset)
    merged_assets = [by_signature[signature] for signature in ordered_signatures if signature in by_signature]
    write_jsonl(_canon_assets_path(root, world_id), merged_assets)
    refreshed_world = _refresh_world_from_records(root, world_id)
    _append_event(
        root,
        "canon_generated",
        {
            "world_id": world_id,
            "generated_asset_count": len(candidates),
            "canon_asset_count": len(merged_assets),
            "asset_types": sorted(wanted) if wanted else [],
        },
    )
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "canon_asset_count": len(merged_assets),
        "generated_asset_count": len(candidates),
        "canon_assets": merged_assets,
        "generated_assets": candidates,
        "refreshed_world": refreshed_world,
    }


def _upsert_canon_asset(root: Path, world_id: str, asset: Dict[str, Any]) -> Dict[str, Any]:
    existing_assets = list(read_jsonl(_canon_assets_path(root, world_id)))
    by_signature = {_canon_asset_signature(row): dict(row) for row in existing_assets}
    ordered_signatures = [_canon_asset_signature(row) for row in existing_assets]
    signature = _canon_asset_signature(asset)
    existing = by_signature.get(signature, {})
    merged = {
        **existing,
        **asset,
        "canon_id": existing.get("canon_id", asset.get("canon_id", make_id("world-canon"))),
        "created_at": existing.get("created_at", asset.get("created_at", utc_now())),
        "updated_at": utc_now(),
        "source_record_ids": _unique([*existing.get("source_record_ids", []), *asset.get("source_record_ids", [])]),
        "supporting_evidence_ids": _unique(
            [*existing.get("supporting_evidence_ids", []), *asset.get("supporting_evidence_ids", [])]
        ),
        "metadata": {
            **dict(existing.get("metadata", {})),
            **dict(asset.get("metadata", {})),
            "tags": _unique(
                [
                    *existing.get("metadata", {}).get("tags", []),
                    *asset.get("metadata", {}).get("tags", []),
                ]
            ),
        },
    }
    by_signature[signature] = merged
    if signature not in ordered_signatures:
        ordered_signatures.append(signature)
    write_jsonl(_canon_assets_path(root, world_id), [by_signature[item] for item in ordered_signatures if item in by_signature])
    return merged


def _state_role_from_text(text: str) -> str:
    lowered = text.lower()
    if "dream" in lowered:
        return "dream_anchor"
    if "night" in lowered or "moon" in lowered or "nocturnal" in lowered:
        return "night_anchor"
    return "day_anchor"


def _canon_anchor_media_inputs(
    selected_canon_assets: List[Dict[str, Any]],
    *,
    resolved_model: str,
    scene_text: str = "",
) -> List[Dict[str, Any]]:
    if resolved_model not in {"seedance1_5", "seedance_1_5", "seedance_2_0"}:
        return []
    desired_role = _state_role_from_text(scene_text)
    anchors = []
    for asset in selected_canon_assets:
        metadata = dict(asset.get("metadata", {}))
        role = str(metadata.get("anchor_role", "")).strip()
        value = str(
            metadata.get("local_path")
            or metadata.get("path")
            or metadata.get("source_path")
            or metadata.get("url")
            or metadata.get("source_url")
            or ""
        ).strip()
        if not value:
            continue
        if asset.get("asset_type") == "state_anchor" or role:
            anchors.append(
                {
                    "role": role or desired_role,
                    "value": value,
                }
            )
    if not anchors:
        return []
    preferred = next((row for row in anchors if row["role"] == desired_role), anchors[0])
    return [{"role": "start_image", "value": preferred["value"]}]


def _select_canon_assets(scene_text: str, canon_assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not canon_assets:
        return []
    tags = set(_tokenize_tags(scene_text))
    selected = [
        asset
        for asset in canon_assets
        if tags & set(_tokenize_tags(asset.get("label", ""), asset.get("summary", "")))
    ]
    if not selected:
        selected = canon_assets[:3]
    by_type: Dict[str, Dict[str, Any]] = {}
    for asset in selected:
        by_type.setdefault(asset.get("asset_type", ""), asset)
    for asset in canon_assets:
        by_type.setdefault(asset.get("asset_type", ""), asset)
    return list(by_type.values())


def _scene_beat_from_context(packet_id: str, world_id: str, scene_text: str, context_packet: Dict[str, Any], selected_canon_assets: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "scene_beat_id": make_id("scene-beat"),
        "created_at": utc_now(),
        "packet_id": packet_id,
        "world_id": world_id,
        "scene_text": scene_text,
        "primary_function": context_packet.get("semantic_connective", {}).get("primary_function", "scene"),
        "active_primitives": context_packet.get("active_primitives", []),
        "selected_canon_asset_ids": [asset.get("canon_id", "") for asset in selected_canon_assets],
        "summary": context_packet.get("semantic_connective", {}).get("viewer_task", ""),
    }


def _shot_intents_from_plan(packet_id: str, world_id: str, shot_plan: List[Dict[str, Any]], selected_canon_assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    assets_by_type = {asset.get("asset_type", ""): asset for asset in selected_canon_assets}
    results: List[Dict[str, Any]] = []
    for shot in shot_plan:
        referenced: List[str] = []
        if shot.get("index") == 1 and "place" in assets_by_type:
            referenced.append(assets_by_type["place"]["canon_id"])
        if shot.get("index") == 2 and "object" in assets_by_type:
            referenced.append(assets_by_type["object"]["canon_id"])
        if shot.get("index") >= 3 and "character" in assets_by_type:
            referenced.append(assets_by_type["character"]["canon_id"])
        results.append(
            {
                "shot_intent_id": make_id("shot-intent"),
                "created_at": utc_now(),
                "packet_id": packet_id,
                "world_id": world_id,
                "shot_id": shot.get("shot_id", ""),
                "index": shot.get("index", 0),
                "title": shot.get("title", ""),
                "description": shot.get("description", ""),
                "referenced_canon_ids": referenced,
            }
        )
    return results


def compile_scene_from_canon(
    root: Path,
    world_id: str,
    scene_text: str,
    *,
    duration_seconds: int = 12,
    aspect_ratio: str = "16:9",
    model_preference: str = "cinematic_studio_3_0",
    visual_embedding_client: Any | None = None,
) -> Dict[str, Any]:
    canon_assets = read_jsonl(_canon_assets_path(root, world_id))
    if not canon_assets:
        generate_canon(root, world_id)
        canon_assets = read_jsonl(_canon_assets_path(root, world_id))
    if not canon_assets:
        raise ValueError("No canon assets are available for this world yet. Ingest evidence and generate canon first.")
    selected_canon_assets = _select_canon_assets(scene_text, canon_assets)
    packet = compile_scene(
        root,
        world_id,
        scene_text,
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
        model_preference=model_preference,
        visual_embedding_client=visual_embedding_client,
    )
    bundle = get_packet_bundle(root, packet["packet_id"])
    context_packet = dict(bundle["context_packet"])
    higgsfield_packet = dict(bundle["higgsfield_execution_packet"])
    remotion_props = dict(bundle["remotion_composition_props"])
    evaluation = dict(bundle["evaluation"])

    scene_beat = _scene_beat_from_context(packet["packet_id"], world_id, scene_text, context_packet, selected_canon_assets)
    shot_intents = _shot_intents_from_plan(packet["packet_id"], world_id, context_packet.get("shot_plan", []), selected_canon_assets)

    context_packet["selected_canon_assets"] = selected_canon_assets
    context_packet["scene_beat"] = scene_beat
    context_packet["shot_intents"] = shot_intents
    context_packet["canon_reference_ids"] = [asset.get("canon_id", "") for asset in selected_canon_assets]
    higgsfield_packet["canon_reference_ids"] = context_packet["canon_reference_ids"]
    anchor_medias = _canon_anchor_media_inputs(
        selected_canon_assets,
        resolved_model=higgsfield_packet.get("resolved_model", ""),
        scene_text=scene_text,
    )
    if anchor_medias:
        higgsfield_packet["medias"] = anchor_medias
        higgsfield_packet["anchor_media_strategy"] = "canon_anchor"
    if higgsfield_packet.get("resolved_model") in {"seedance1_5", "seedance_1_5", "seedance_2_0"}:
        canon_labels = ", ".join(
            f"{asset.get('asset_type', '')} {asset.get('label', '')}".strip()
            for asset in selected_canon_assets[:3]
            if asset.get("label", "")
        )
        if canon_labels:
            higgsfield_packet["compiled_prompt"] = (
                f"{higgsfield_packet.get('compiled_prompt', '').strip()} Keep continuity with {canon_labels}."
            ).strip()
    else:
        higgsfield_packet["compiled_prompt"] = "\n".join(
            [
                higgsfield_packet.get("compiled_prompt", ""),
                "",
                "Canon references:",
                *[f"- {asset.get('asset_type', '')}: {asset.get('label', '')}" for asset in selected_canon_assets],
            ]
        ).strip()
    remotion_props["props"]["canonAssets"] = selected_canon_assets
    remotion_props["props"]["sceneBeat"] = scene_beat
    remotion_props["props"]["shotIntents"] = shot_intents
    evaluation["canon_reference_ids"] = context_packet["canon_reference_ids"]

    _write_packet_bundle(
        root,
        packet["packet_id"],
        context_packet=context_packet,
        higgsfield_execution_packet=higgsfield_packet,
        remotion_composition_props=remotion_props,
        evaluation=evaluation,
    )

    scene_beats = read_jsonl(_scene_beats_path(root, world_id))
    scene_beats.append(scene_beat)
    write_jsonl(_scene_beats_path(root, world_id), scene_beats)
    shot_intent_rows = read_jsonl(_shot_intents_path(root, world_id))
    shot_intent_rows.extend(shot_intents)
    write_jsonl(_shot_intents_path(root, world_id), shot_intent_rows)
    eval_rows = read_jsonl(_evaluation_events_path(root, world_id))
    eval_rows.append(
        {
            "evaluation_event_id": make_id("world-evaluation-event"),
            "created_at": utc_now(),
            "packet_id": packet["packet_id"],
            "world_id": world_id,
            "canon_reference_ids": context_packet["canon_reference_ids"],
            "summary": evaluation.get("summary", ""),
        }
    )
    write_jsonl(_evaluation_events_path(root, world_id), eval_rows)
    _refresh_world_from_records(root, world_id)
    _append_event(root, "scene_compiled_from_canon", {"world_id": world_id, "packet_id": packet["packet_id"]})
    return packet


POPULATION_ENTRYPOINT_OPTIONS = [
    {
        "id": "emotion",
        "label": "Start with the feeling",
        "description": "Anchor the world in an emotional pressure first.",
    },
    {
        "id": "character",
        "label": "Start with a person",
        "description": "Give the world one human anchor before anything else.",
    },
    {
        "id": "place",
        "label": "Start with a place",
        "description": "Open on a location and let the world grow outward from it.",
    },
    {
        "id": "object",
        "label": "Start with an object",
        "description": "Use one meaningful object to pull the world into focus.",
    },
    {
        "id": "rule",
        "label": "Start with a rule",
        "description": "Define one law or binding condition the world obeys.",
    },
]

POPULATION_EMOTION_OPTIONS = [
    {"id": "trust_fracture", "label": "Trust fracture", "description": "The world turns on betrayal, secrecy, or failed loyalty."},
    {"id": "buried_grief", "label": "Buried grief", "description": "Pain is present but controlled, hidden, or ritualized."},
    {"id": "obsession", "label": "Obsession", "description": "The world keeps circling what it cannot let go of."},
    {"id": "wonder", "label": "Wonder", "description": "The world opens outward toward awe or discovery."},
    {"id": "escape_hunger", "label": "Escape hunger", "description": "Characters are pulled by the need to get out or get free."},
    {"id": "other", "label": "Something else", "description": "Use your own emotional center."},
]

POPULATION_VISUAL_TONE_OPTIONS = [
    {"id": "ritual_cold", "label": "Ritual cold", "description": "Disciplined, ceremonial, and cool rather than cozy."},
    {"id": "soft_decay", "label": "Soft decay", "description": "Weathered beauty, erosion, and quiet collapse."},
    {"id": "opulent_pressure", "label": "Opulent pressure", "description": "Beauty that feels expensive, strict, and suffocating."},
    {"id": "bright_uncanny", "label": "Bright uncanny", "description": "Clear surfaces and brightness that feel wrong."},
    {"id": "warm_intimacy", "label": "Warm intimacy", "description": "Closeness, tactility, and human warmth."},
    {"id": "other", "label": "Something else", "description": "Use your own visual tone."},
]

POPULATION_ENTRYPOINT_TO_QUESTION = {
    "emotion": "core_emotion",
    "character": "anchor_character",
    "place": "anchor_place",
    "object": "anchor_object",
    "rule": "world_rule",
}

POPULATION_QUESTION_LAYER = {
    "entrypoint": "meta",
    "core_emotion": "primitive",
    "anchor_character": "character",
    "anchor_place": "place",
    "anchor_object": "object",
    "world_rule": "rule",
    "visual_tone": "visual",
    "core_conflict": "conflict",
    "connection_probe": "relationship",
}

POPULATION_CORE_SEQUENCE = [
    "core_emotion",
    "anchor_character",
    "anchor_place",
    "anchor_object",
    "world_rule",
    "visual_tone",
    "core_conflict",
    "connection_probe",
]

POPULATION_MINIMUM_QUESTIONS = 6
POPULATION_TARGET_QUESTIONS = 9

_POPULATION_STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "there",
    "they",
    "this",
    "to",
    "was",
    "were",
    "with",
}

POPULATION_VISUAL_LENS_PRESETS = {
    "ritual_cold": {
        "style_keywords": ["ritual cold"],
        "visual_preferences": ["disciplined symmetry", "wet stone", "cold practical lamps"],
        "visual_lens_rules": {
            "composition": [
                {
                    "semantic_role": "make the world feel governed and ceremonial",
                    "instruction": "Use disciplined symmetry and architectural pressure rather than casual framing.",
                    "weight": 0.81,
                }
            ],
            "lighting": [
                {
                    "semantic_role": "keep ritual emotionally distant",
                    "instruction": "Use cold practical lamps, wet reflections, and hard edges instead of ambient warmth.",
                    "weight": 0.84,
                }
            ],
            "color": [
                {
                    "semantic_role": "hold the world inside a cool ritual register",
                    "instruction": "Favor slate, salt, steel, and dim brass with restrained saturation.",
                    "weight": 0.79,
                }
            ],
        },
    },
    "soft_decay": {
        "style_keywords": ["soft decay"],
        "visual_preferences": ["weathered surfaces", "eroded elegance", "moss and dust"],
        "visual_lens_rules": {
            "composition": [
                {
                    "semantic_role": "make erosion feel intimate rather than ruined",
                    "instruction": "Frame age and wear close enough to feel lived-in, not post-apocalyptic.",
                    "weight": 0.74,
                }
            ],
            "lighting": [
                {
                    "semantic_role": "let time feel suspended",
                    "instruction": "Use soft directional light that reveals dust, texture, and slow collapse.",
                    "weight": 0.76,
                }
            ],
            "color": [
                {
                    "semantic_role": "hold beauty and erosion together",
                    "instruction": "Use chalk, moss, faded gold, and water-worn neutrals.",
                    "weight": 0.71,
                }
            ],
        },
    },
    "opulent_pressure": {
        "style_keywords": ["opulent pressure"],
        "visual_preferences": ["luxury under strain", "formal rooms", "controlled ornament"],
        "visual_lens_rules": {
            "composition": [
                {
                    "semantic_role": "make beauty feel like a trap",
                    "instruction": "Use formal rooms and clean axes that make wealth feel restrictive.",
                    "weight": 0.82,
                }
            ],
            "lighting": [
                {
                    "semantic_role": "keep elegance tense",
                    "instruction": "Use polished highlights and shadow pockets that imply surveillance or judgment.",
                    "weight": 0.77,
                }
            ],
            "color": [
                {
                    "semantic_role": "treat richness as pressure",
                    "instruction": "Use lacquered darks, muted jewel tones, and controlled metallic accents.",
                    "weight": 0.73,
                }
            ],
        },
    },
    "bright_uncanny": {
        "style_keywords": ["bright uncanny"],
        "visual_preferences": ["clean glare", "clinical brightness", "unnerving clarity"],
        "visual_lens_rules": {
            "composition": [
                {
                    "semantic_role": "make visibility itself feel suspicious",
                    "instruction": "Keep the frame readable and exposed enough that nothing can hide comfortably.",
                    "weight": 0.75,
                }
            ],
            "lighting": [
                {
                    "semantic_role": "turn clarity into unease",
                    "instruction": "Use bright practical light, reflective surfaces, and minimal shadow cover.",
                    "weight": 0.82,
                }
            ],
            "color": [
                {
                    "semantic_role": "make brightness feel slightly incorrect",
                    "instruction": "Use pale tones, glassy whites, and small acidic accents.",
                    "weight": 0.69,
                }
            ],
        },
    },
    "warm_intimacy": {
        "style_keywords": ["warm intimacy"],
        "visual_preferences": ["close human scale", "soft tactile surfaces", "lived-in warmth"],
        "visual_lens_rules": {
            "composition": [
                {
                    "semantic_role": "privilege closeness over spectacle",
                    "instruction": "Frame hands, breath, touch, and small distances between people and objects.",
                    "weight": 0.78,
                }
            ],
            "lighting": [
                {
                    "semantic_role": "keep presence human",
                    "instruction": "Use warm motivated light that feels held inside the scene rather than decorative.",
                    "weight": 0.74,
                }
            ],
            "color": [
                {
                    "semantic_role": "keep emotional access open",
                    "instruction": "Use skin-close neutrals, amber practicals, and soft wood or textile tones.",
                    "weight": 0.7,
                }
            ],
        },
    },
}


def _population_question_base(question_id: str) -> Dict[str, Any]:
    prompts = {
        "entrypoint": {
            "question": "What feels easiest to start with?",
            "selection_mode": "single",
            "allow_free_text": False,
            "response_options": POPULATION_ENTRYPOINT_OPTIONS,
            "why_this_matters": "Starting from the easiest handle lowers cognitive load and gives the system a first anchor.",
        },
        "core_emotion": {
            "question": "Which emotional gravity should this world keep pulling toward?",
            "selection_mode": "single",
            "allow_free_text": True,
            "response_options": POPULATION_EMOTION_OPTIONS,
            "why_this_matters": "A clear emotional primitive makes later characters, motifs, and scenes easier to align.",
        },
        "anchor_character": {
            "question": "Give me one person we can orient around. One sentence is enough.",
            "selection_mode": "free_text",
            "allow_free_text": True,
            "response_options": [],
            "why_this_matters": "A single human anchor gives later rules, places, and conflicts something to press against.",
        },
        "anchor_place": {
            "question": "What is one place in this world we could see first?",
            "selection_mode": "free_text",
            "allow_free_text": True,
            "response_options": [],
            "why_this_matters": "A place gives the world tangible spatial logic and reusable scene material.",
        },
        "anchor_object": {
            "question": "What is one object that matters more than it should?",
            "selection_mode": "free_text",
            "allow_free_text": True,
            "response_options": [],
            "why_this_matters": "Meaningful objects become future bridge points between story, emotion, and visual execution.",
        },
        "world_rule": {
            "question": "What is one rule this world obeys?",
            "selection_mode": "free_text",
            "allow_free_text": True,
            "response_options": [],
            "why_this_matters": "Rules let the system distinguish decorative details from load-bearing world logic.",
        },
        "visual_tone": {
            "question": "Which visual tone feels closest right now?",
            "selection_mode": "single",
            "allow_free_text": True,
            "response_options": POPULATION_VISUAL_TONE_OPTIONS,
            "why_this_matters": "A broad visual tone is enough to begin shaping camera, lighting, color, and props later.",
        },
        "core_conflict": {
            "question": "What pressure or conflict keeps this world unstable?",
            "selection_mode": "free_text",
            "allow_free_text": True,
            "response_options": [],
            "why_this_matters": "Conflict helps the system connect isolated facts into an active world rather than a static lore sheet.",
        },
        "connection_probe": {
            "question": "Connect two things we know now. How do they affect each other?",
            "selection_mode": "free_text",
            "allow_free_text": True,
            "response_options": [],
            "why_this_matters": "Cross-layer links are the reusable structure that later helps new scenes and motifs emerge.",
        },
    }
    return prompts[question_id]


def _population_emotion_label(choice: str) -> str:
    labels = {
        "trust_fracture": "trust fracture",
        "buried_grief": "buried grief",
        "obsession": "obsession",
        "wonder": "wonder",
        "escape_hunger": "escape hunger",
        "other": "emotional center",
    }
    return labels.get(choice, choice.replace("_", " "))


def _tokenize_tags(*values: str) -> List[str]:
    tags: List[str] = []
    for value in values:
        for token in re.findall(r"[a-z0-9]+", str(value).lower()):
            if len(token) <= 2 or token in _POPULATION_STOP_WORDS:
                continue
            tags.append(token)
    return _unique(tags)


def _compact_text(value: str, *, fallback: str = "") -> str:
    text = " ".join(str(value).strip().split())
    return text or fallback


def _build_record_label(text: str, fallback: str) -> str:
    clean = _compact_text(text, fallback=fallback)
    fragment = re.split(r"[.!?;]", clean, maxsplit=1)[0].strip()
    words = fragment.split()
    if not words:
        return fallback
    shortened = " ".join(words[:8]).strip()
    return shortened[0].upper() + shortened[1:] if shortened else fallback


def _empty_population_overview() -> Dict[str, Any]:
    return {
        "knowledge_record_count": 0,
        "connection_count": 0,
        "coverage_by_layer": {},
        "last_population_session_id": "",
        "ready_for_generation": False,
    }


def _population_question(question_id: str, world: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    spec = dict(_population_question_base(question_id))
    if question_id == "connection_probe":
        candidates = [record for record in records if record.get("layer") in {"object", "character", "place", "rule", "primitive", "conflict"}]
        if len(candidates) >= 2:
            left = candidates[-2]
            right = candidates[-1]
            spec["question"] = (
                f"You already have `{left.get('label', '').strip()}` and `{right.get('label', '').strip()}`. "
                "How do those two touch each other?"
            )
    if question_id in {"anchor_character", "anchor_place", "anchor_object"}:
        spec["question"] = f"{spec['question']} You can answer in a single sentence."
    if question_id == "world_rule":
        spec["question"] = f"{spec['question']} Keep it plain and concrete."
    if question_id == "core_conflict" and world.get("project_primitives"):
        primitive = world["project_primitives"][-1]
        spec["question"] = f"What pressure makes `{primitive}` active inside this world?"
    return spec


def _parse_population_answer(question_id: str, answer: str) -> Dict[str, Any]:
    spec = _population_question_base(question_id)
    raw = _compact_text(answer)
    if spec["selection_mode"] == "free_text":
        return {"choice": "", "note": raw, "raw": raw}
    response_options = {option["id"] for option in spec["response_options"]}
    if "|" in raw:
        left, right = [part.strip() for part in raw.split("|", 1)]
        if left in response_options:
            return {"choice": left, "note": right, "raw": raw}
    if raw in response_options:
        return {"choice": raw, "note": "", "raw": raw}
    if spec["allow_free_text"]:
        fallback_choice = "other" if "other" in response_options else ""
        return {"choice": fallback_choice or raw, "note": raw, "raw": raw}
    return {"choice": raw, "note": "", "raw": raw}


def _knowledge_preview(records: List[Dict[str, Any]], connections: List[Dict[str, Any]]) -> Dict[str, Any]:
    coverage = Counter(record.get("layer", "") for record in records if record.get("layer"))
    recent = [
        {
            "layer": record.get("layer", ""),
            "label": record.get("label", ""),
        }
        for record in records[-3:]
    ]
    uncovered = [layer for layer in ["primitive", "character", "place", "object", "rule", "visual", "conflict", "relationship"] if coverage.get(layer, 0) <= 0]
    return {
        "coverage_by_layer": dict(sorted(coverage.items())),
        "recent_insights": recent,
        "inferred_connection_count": len(connections),
        "uncovered_layers": uncovered,
    }


def _population_progress(state: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    coverage = Counter(record.get("layer", "") for record in records if record.get("layer"))
    covered_layers = sum(1 for layer in ["primitive", "character", "place", "object", "rule", "visual", "conflict", "relationship"] if coverage.get(layer, 0) > 0)
    return {
        "questions_asked": len(state.get("asked_question_ids", [])),
        "minimum_questions": POPULATION_MINIMUM_QUESTIONS,
        "target_questions": POPULATION_TARGET_QUESTIONS,
        "covered_layers": covered_layers,
    }


def _population_question_payload(root: Path, state: Dict[str, Any]) -> Dict[str, Any]:
    world = get_world(root, state["world_id"])
    records = read_jsonl(_population_knowledge_path(root, state["world_id"]))
    connections = read_jsonl(_population_connections_path(root, state["world_id"]))
    question_id = state["current_question_id"]
    question = _population_question(question_id, world, records)
    return {
        "session_id": state["session_id"],
        "world_id": state["world_id"],
        "world_name": world.get("name", ""),
        "question_index": len(state.get("asked_question_ids", [])),
        "question_id": question_id,
        "question": question["question"],
        "selection_mode": question["selection_mode"],
        "allow_free_text": question["allow_free_text"],
        "response_options": question["response_options"],
        "why_this_matters": question["why_this_matters"],
        "progress": _population_progress(state, records),
        "knowledge_preview": _knowledge_preview(records, connections),
        "completed": False,
    }


def _population_question_needs_records(question_id: str, coverage: Counter[str], records: List[Dict[str, Any]]) -> bool:
    layer = POPULATION_QUESTION_LAYER.get(question_id, "")
    if question_id == "connection_probe":
        return len(records) >= POPULATION_MINIMUM_QUESTIONS - 1 and coverage.get("relationship", 0) <= 0
    return bool(layer) and coverage.get(layer, 0) <= 0


def _next_population_question_id(state: Dict[str, Any], records: List[Dict[str, Any]]) -> str | None:
    if "entrypoint" not in state["answers"]:
        return "entrypoint"
    entrypoint = state["answers"]["entrypoint"].get("choice", "")
    seeded_question = POPULATION_ENTRYPOINT_TO_QUESTION.get(entrypoint, "")
    if seeded_question and seeded_question not in state["answers"]:
        return seeded_question
    coverage = Counter(record.get("layer", "") for record in records if record.get("layer"))
    for question_id in POPULATION_CORE_SEQUENCE:
        if question_id in state["answers"]:
            continue
        if _population_question_needs_records(question_id, coverage, records):
            return question_id
    return None


def _make_knowledge_record(
    *,
    world_id: str,
    session_id: str,
    answer_id: str,
    question_id: str,
    layer: str,
    kind: str,
    label: str,
    summary: str,
    tags: List[str] | None = None,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "knowledge_id": make_id("world-knowledge"),
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "world_id": world_id,
        "session_id": session_id,
        "answer_id": answer_id,
        "question_id": question_id,
        "layer": layer,
        "kind": kind,
        "label": _compact_text(label, fallback=kind),
        "summary": _compact_text(summary, fallback=label),
        "tags": _unique(tags or _tokenize_tags(label, summary)),
        "metadata": metadata or {},
    }


def _knowledge_records_from_answer(
    *,
    world: Dict[str, Any],
    session_id: str,
    answer_id: str,
    question_id: str,
    parsed_answer: Dict[str, Any],
) -> List[Dict[str, Any]]:
    note = parsed_answer.get("note", "")
    choice = parsed_answer.get("choice", "")
    raw = parsed_answer.get("raw", "")
    world_id = world["world_id"]
    if question_id == "entrypoint":
        return []
    if question_id == "core_emotion":
        label = _population_emotion_label(choice or "other")
        summary = note or label
        return [
            _make_knowledge_record(
                world_id=world_id,
                session_id=session_id,
                answer_id=answer_id,
                question_id=question_id,
                layer="primitive",
                kind="emotional_core",
                label=label,
                summary=summary,
                tags=_tokenize_tags(label, summary, "emotion"),
                metadata={"choice": choice},
            )
        ]
    if question_id == "anchor_character":
        return [
            _make_knowledge_record(
                world_id=world_id,
                session_id=session_id,
                answer_id=answer_id,
                question_id=question_id,
                layer="character",
                kind="anchor_character",
                label=_build_record_label(raw, "Anchor Character"),
                summary=raw,
                metadata={"anchor": True},
            )
        ]
    if question_id == "anchor_place":
        return [
            _make_knowledge_record(
                world_id=world_id,
                session_id=session_id,
                answer_id=answer_id,
                question_id=question_id,
                layer="place",
                kind="anchor_place",
                label=_build_record_label(raw, "Anchor Place"),
                summary=raw,
                metadata={"anchor": True},
            )
        ]
    if question_id == "anchor_object":
        return [
            _make_knowledge_record(
                world_id=world_id,
                session_id=session_id,
                answer_id=answer_id,
                question_id=question_id,
                layer="object",
                kind="bridge_object_seed",
                label=_build_record_label(raw, "Anchor Object"),
                summary=raw,
                metadata={"anchor": True},
            )
        ]
    if question_id == "world_rule":
        return [
            _make_knowledge_record(
                world_id=world_id,
                session_id=session_id,
                answer_id=answer_id,
                question_id=question_id,
                layer="rule",
                kind="world_rule",
                label=_build_record_label(raw, "World Rule"),
                summary=raw,
                metadata={"binding": True},
            )
        ]
    if question_id == "visual_tone":
        label = choice.replace("_", " ") if choice else _build_record_label(raw, "Visual Tone").lower()
        summary = note or label
        return [
            _make_knowledge_record(
                world_id=world_id,
                session_id=session_id,
                answer_id=answer_id,
                question_id=question_id,
                layer="visual",
                kind="visual_tone",
                label=label,
                summary=summary,
                tags=_tokenize_tags(label, summary, "visual"),
                metadata={"choice": choice},
            )
        ]
    if question_id == "core_conflict":
        return [
            _make_knowledge_record(
                world_id=world_id,
                session_id=session_id,
                answer_id=answer_id,
                question_id=question_id,
                layer="conflict",
                kind="world_pressure",
                label=_build_record_label(raw, "Core Conflict"),
                summary=raw,
            )
        ]
    if question_id == "connection_probe":
        return [
            _make_knowledge_record(
                world_id=world_id,
                session_id=session_id,
                answer_id=answer_id,
                question_id=question_id,
                layer="relationship",
                kind="cross_layer_connection",
                label=_build_record_label(raw, "World Connection"),
                summary=raw,
            )
        ]
    return []


def _rebuild_population_connections(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    connections: List[Dict[str, Any]] = []
    for left, right in combinations(records, 2):
        if left.get("layer") == right.get("layer"):
            continue
        left_tags = set(left.get("tags", []))
        right_tags = set(right.get("tags", []))
        shared_tags = sorted(left_tags & right_tags)
        score = 0.0
        reasons: List[str] = []
        if shared_tags:
            score += 0.34 + (0.04 * min(4, len(shared_tags)))
            reasons.append("shared_tags")
        if {left.get("layer"), right.get("layer")} == {"object", "primitive"}:
            score += 0.25
            reasons.append("object_to_primitive")
        if {left.get("layer"), right.get("layer")} == {"rule", "conflict"}:
            score += 0.18
            reasons.append("rule_to_conflict")
        if "relationship" in {left.get("layer"), right.get("layer")}:
            score += 0.24
            reasons.append("explicit_connection")
        if left.get("session_id") == right.get("session_id"):
            score += 0.04
        if score < 0.35:
            continue
        connections.append(
            {
                "connection_id": make_id("world-link"),
                "created_at": utc_now(),
                "world_id": left.get("world_id", ""),
                "left_knowledge_id": left.get("knowledge_id", ""),
                "right_knowledge_id": right.get("knowledge_id", ""),
                "left_label": left.get("label", ""),
                "right_label": right.get("label", ""),
                "connection_type": "inferred_world_link",
                "shared_tags": shared_tags,
                "reasons": reasons,
                "score": round(min(0.98, score), 2),
            }
        )
    connections.sort(key=lambda row: row.get("score", 0.0), reverse=True)
    return connections


def _population_motif_from_record(record: Dict[str, Any]) -> str:
    layer = record.get("layer", "")
    label = record.get("label", "")
    summary = record.get("summary", "")
    if layer == "object":
        return f"{label} carries hidden narrative pressure"
    if layer == "relationship":
        return summary
    if layer == "conflict":
        return summary
    if layer == "place":
        return f"{label} concentrates the world's pressure"
    return summary


def _bridge_objects_from_population(records: List[Dict[str, Any]], connections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    record_index = {record["knowledge_id"]: record for record in records if record.get("knowledge_id")}
    bridge_objects: List[Dict[str, Any]] = []
    for connection in connections:
        left = record_index.get(connection.get("left_knowledge_id", ""))
        right = record_index.get(connection.get("right_knowledge_id", ""))
        if not left or not right:
            continue
        if "object" not in {left.get("layer"), right.get("layer")}:
            continue
        object_record = left if left.get("layer") == "object" else right
        meaning_record = right if object_record is left else left
        bridge_objects.append(
            {
                "bridge_id": f"bridge-{slugify(object_record.get('label', 'object'))}-{slugify(meaning_record.get('label', 'meaning'))}",
                "relation_type": f"population_{object_record.get('layer', 'object')}_to_{meaning_record.get('layer', 'meaning')}",
                "triggers": _unique(
                    [
                        *object_record.get("tags", []),
                        *meaning_record.get("tags", []),
                        object_record.get("label", ""),
                        meaning_record.get("label", ""),
                    ]
                ),
                "source_meaning": meaning_record.get("summary", meaning_record.get("label", "")),
                "target_layers": ["props", "composition", "camera", "editing"],
                "narrative_function": f"Use {object_record.get('label', '').lower()} to surface {meaning_record.get('label', '').lower()}.",
                "emotional_function": f"Let the object make {meaning_record.get('label', '').lower()} legible before dialogue does.",
                "layer_mappings": {
                    "props": f"Feature {object_record.get('label', '').lower()} as a repeatable symbolic prop.",
                    "composition": f"Frame the character in relation to {object_record.get('label', '').lower()} when {meaning_record.get('label', '').lower()} is active.",
                    "camera": f"Let the object read clearly before moving to reaction or consequence.",
                    "editing": "Prefer object-first recognition before explicit explanation.",
                },
                "hard_constraints": [],
                "soft_constraints": [f"let {object_record.get('label', '').lower()} carry semantic pressure"],
                "evaluator_rules": [
                    f"{object_record.get('label', '')} should reinforce {meaning_record.get('label', '').lower()}",
                ],
                "weight": min(0.95, max(0.55, connection.get("score", 0.55))),
                "provenance": {"source": "population_engine", "confidence": connection.get("score", 0.55)},
            }
        )
    return bridge_objects


def _merge_visual_lens_rules(existing: Dict[str, List[Dict[str, Any]]], records: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    merged = {
        layer: [
            {
                "semantic_role": row.get("semantic_role", ""),
                "instruction": row.get("instruction", ""),
                "weight": row.get("weight", 0.5),
            }
            for row in rows
        ]
        for layer, rows in (existing or {}).items()
    }
    for record in records:
        if record.get("layer") != "visual":
            continue
        preset = POPULATION_VISUAL_LENS_PRESETS.get(record.get("metadata", {}).get("choice", ""))
        if preset:
            for layer, rows in preset.get("visual_lens_rules", {}).items():
                merged.setdefault(layer, [])
                for row in rows:
                    candidate = {
                        "semantic_role": row.get("semantic_role", ""),
                        "instruction": row.get("instruction", ""),
                        "weight": row.get("weight", 0.5),
                    }
                    if candidate not in merged[layer]:
                        merged[layer].append(candidate)
        if record.get("record_type") == "visual_adjacency":
            candidate = {
                "semantic_role": "carry forward evidence-backed visual tone",
                "instruction": record.get("summary", ""),
                "weight": float(record.get("provenance", {}).get("confidence", 0.68)),
            }
            merged.setdefault("composition", [])
            if candidate not in merged["composition"]:
                merged["composition"].append(candidate)
    return merged


def _refresh_world_from_population(root: Path, world_id: str, *, session_id: str = "") -> Dict[str, Any]:
    world = get_world(root, world_id)
    records = read_jsonl(_population_knowledge_path(root, world_id))
    connections = read_jsonl(_population_connections_path(root, world_id))
    primitives = _unique(record.get("label", "") for record in records if record.get("layer") == "primitive")
    rules = _unique(record.get("summary", "") for record in records if record.get("layer") == "rule")
    motifs = _unique(_population_motif_from_record(record) for record in records if record.get("layer") in {"object", "place", "conflict", "relationship"})
    visual_records = [record for record in records if record.get("layer") == "visual"]
    style_keywords = _unique(
        [
            *world.get("taste_profile", {}).get("style_keywords", []),
            *[record.get("label", "") for record in visual_records],
            *[keyword for record in visual_records for keyword in POPULATION_VISUAL_LENS_PRESETS.get(record.get("metadata", {}).get("choice", ""), {}).get("style_keywords", [])],
        ]
    )
    visual_preferences = _unique(
        [
            *world.get("taste_profile", {}).get("visual_preferences", []),
            *[record.get("summary", "") for record in visual_records if record.get("summary", "")],
            *[keyword for record in visual_records for keyword in POPULATION_VISUAL_LENS_PRESETS.get(record.get("metadata", {}).get("choice", ""), {}).get("visual_preferences", [])],
        ]
    )
    profile = dict(world.get("taste_profile", {}))
    profile["profile_name"] = profile.get("profile_name") or "adaptive populated world profile"
    profile["style_keywords"] = style_keywords
    profile["visual_preferences"] = visual_preferences
    profile["forbidden"] = profile.get("forbidden", [])
    world["project_primitives"] = _unique([*world.get("project_primitives", []), *primitives])
    world["world_rules"] = _unique([*world.get("world_rules", []), *rules])
    world["active_motifs"] = _unique([*world.get("active_motifs", []), *motifs])
    world["taste_profile"] = profile
    world["visual_lens_rules"] = _merge_visual_lens_rules(world.get("visual_lens_rules", {}), visual_records)
    world["bridge_objects"] = _unique_bridge_objects([*world.get("bridge_objects", []), *_bridge_objects_from_population(records, connections)])
    coverage = Counter(record.get("layer", "") for record in records if record.get("layer"))
    world["population_overview"] = {
        "knowledge_record_count": len(records),
        "connection_count": len(connections),
        "coverage_by_layer": dict(sorted(coverage.items())),
        "last_population_session_id": session_id or world.get("population_overview", {}).get("last_population_session_id", ""),
        "ready_for_generation": all(coverage.get(layer, 0) > 0 for layer in ["primitive", "character", "place", "object", "rule", "visual", "conflict"]),
    }
    world["updated_at"] = utc_now()
    write_json(_world_path(root, world_id), world)
    return world


def _unique_bridge_objects(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    deduped: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        bridge_id = str(row.get("bridge_id", "")).strip() or f"bridge-{slugify(row.get('source_meaning', 'bridge'))}"
        if bridge_id in seen:
            continue
        seen.add(bridge_id)
        normalized = dict(row)
        normalized["bridge_id"] = bridge_id
        deduped.append(normalized)
    return deduped


def _write_population_state(root: Path, state: Dict[str, Any]) -> None:
    write_json(_population_session_path(root, state["session_id"]), state)


def _load_population_state(root: Path, session_id: str) -> Dict[str, Any]:
    state = read_json(_population_session_path(root, session_id), default=None)
    if state is None:
        raise FileNotFoundError(f"Population session not found: {session_id}")
    return state


def start_population_session(root: Path, world_id: str) -> Dict[str, Any]:
    world = get_world(root, world_id)
    if "population_overview" not in world:
        world["population_overview"] = _empty_population_overview()
        write_json(_world_path(root, world_id), world)
    existing = _active_population_session_for_world(root, world_id)
    if existing is not None:
        return _population_question_payload(root, existing)
    session_id = make_id("world-population")
    state = {
        "session_id": session_id,
        "world_id": world_id,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "status": "active",
        "answers": {},
        "asked_question_ids": [],
        "current_question_id": "entrypoint",
        "completed": False,
    }
    _write_population_state(root, state)
    _append_event(root, "population_session_started", {"world_id": world_id, "session_id": session_id})
    return _population_question_payload(root, state)


def answer_population_question(root: Path, session_id: str, answer: str) -> Dict[str, Any]:
    state = _load_population_state(root, session_id)
    if state.get("completed"):
        raise RuntimeError(f"Population session already completed: {session_id}")
    question_id = state.get("current_question_id") or _next_population_question_id(
        state,
        read_jsonl(_population_knowledge_path(root, state["world_id"])),
    )
    if not question_id:
        raise RuntimeError(f"Population session has no pending question: {session_id}")
    parsed_answer = _parse_population_answer(question_id, answer)
    answer_record = {
        "answer_id": make_id("world-answer"),
        "created_at": utc_now(),
        "world_id": state["world_id"],
        "session_id": session_id,
        "question_id": question_id,
        "layer": POPULATION_QUESTION_LAYER.get(question_id, ""),
        "answer": parsed_answer,
    }
    answer_rows = read_jsonl(_population_answers_path(root, state["world_id"]))
    answer_rows.append(answer_record)
    write_jsonl(_population_answers_path(root, state["world_id"]), answer_rows)

    world = get_world(root, state["world_id"])
    new_records = _knowledge_records_from_answer(
        world=world,
        session_id=session_id,
        answer_id=answer_record["answer_id"],
        question_id=question_id,
        parsed_answer=parsed_answer,
    )
    records = read_jsonl(_population_knowledge_path(root, state["world_id"]))
    records.extend(new_records)
    write_jsonl(_population_knowledge_path(root, state["world_id"]), records)
    connections = _rebuild_population_connections(records)
    write_jsonl(_population_connections_path(root, state["world_id"]), connections)
    _sync_population_records_into_world_graph(root, state["world_id"], new_records)
    _rebuild_world_graph_connections(root, state["world_id"])
    refreshed_world = _refresh_world_from_records(root, state["world_id"])

    state["answers"][question_id] = parsed_answer
    state["asked_question_ids"].append(question_id)
    state["updated_at"] = utc_now()
    next_question_id = _next_population_question_id(state, records)
    if next_question_id is None:
        state["completed"] = True
        state["status"] = "ready_for_generation"
        state["current_question_id"] = None
        _write_population_state(root, state)
        _append_event(
            root,
            "population_session_completed",
            {
                "world_id": state["world_id"],
                "session_id": session_id,
                "knowledge_record_count": len(records),
                "connection_count": len(connections),
            },
        )
        return {
            "session_id": session_id,
            "world_id": state["world_id"],
            "completed": True,
            "status": "ready_for_generation",
            "summary": {
                "world_name": refreshed_world.get("name", ""),
                "knowledge_record_count": len(records),
                "connection_count": len(connections),
                "coverage_by_layer": refreshed_world.get("population_overview", {}).get("coverage_by_layer", {}),
                "project_primitives": refreshed_world.get("project_primitives", []),
                "bridge_object_count": len(refreshed_world.get("bridge_objects", [])),
            },
        }
    state["current_question_id"] = next_question_id
    _write_population_state(root, state)
    _append_event(root, "population_answer_recorded", {"world_id": state["world_id"], "session_id": session_id, "question_id": question_id})
    return _population_question_payload(root, state)


def get_population_session(root: Path, session_id: str) -> Dict[str, Any]:
    state = _load_population_state(root, session_id)
    world = get_world(root, state["world_id"])
    records = read_jsonl(_population_knowledge_path(root, state["world_id"]))
    connections = read_jsonl(_population_connections_path(root, state["world_id"]))
    return {
        **state,
        "world_name": world.get("name", ""),
        "knowledge_preview": _knowledge_preview(records, connections),
    }


def inspect_world_knowledge(root: Path, world_id: str) -> Dict[str, Any]:
    world = get_world(root, world_id)
    records = _read_world_records(root, world_id)
    connections = _read_world_connections(root, world_id)
    coverage = Counter(record.get("layer", "") for record in records if record.get("layer"))
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "knowledge_record_count": len(records),
        "connection_count": len(connections),
        "coverage_by_layer": dict(sorted(coverage.items())),
        "explicit_record_count": sum(1 for row in records if row.get("explicitness") == "explicit"),
        "inferred_record_count": sum(1 for row in records if row.get("explicitness") != "explicit"),
        "records": records,
        "connections": connections,
        "world_snapshot": world,
    }


_GRAPH_LAYER_ORDER = [
    "primitive",
    "character",
    "place",
    "object",
    "rule",
    "visual",
    "conflict",
    "relationship",
]

_GRAPH_LAYER_LABELS = {
    "primitive": "Emotional Core",
    "character": "People",
    "place": "Places",
    "object": "Objects",
    "rule": "Rules",
    "visual": "Tone",
    "conflict": "Pressure",
    "relationship": "Connections",
}


def _layer_cluster_position(layer: str) -> tuple[float, float]:
    index = _GRAPH_LAYER_ORDER.index(layer) if layer in _GRAPH_LAYER_ORDER else 0
    angle = (-math.pi / 2.0) + ((2.0 * math.pi) / max(1, len(_GRAPH_LAYER_ORDER))) * index
    radius = 280.0
    return round(math.cos(angle) * radius, 1), round(math.sin(angle) * radius, 1)


def _record_position(layer: str, index: int) -> tuple[float, float]:
    base_x, base_y = _layer_cluster_position(layer)
    fan_angle = -0.42 + (0.21 * index)
    radial = 120.0 + (18.0 * min(index, 4))
    x = base_x + math.cos(fan_angle) * radial
    y = base_y + math.sin(fan_angle) * (radial * 0.68) + (index * 16.0)
    return round(x, 1), round(y, 1)


def _active_population_session_for_world(root: Path, world_id: str) -> Dict[str, Any] | None:
    sessions_dir = _population_sessions_dir(root)
    if not sessions_dir.exists():
        return None
    candidates: List[Dict[str, Any]] = []
    for path in sorted(sessions_dir.glob("*.json")):
        state = read_json(path, default=None)
        if not state or state.get("world_id") != world_id or state.get("completed"):
            continue
        candidates.append(state)
    if not candidates:
        return None
    candidates.sort(key=lambda row: row.get("updated_at", ""), reverse=True)
    return candidates[0]


def project_world_graph(root: Path, world_id: str) -> Dict[str, Any]:
    world = get_world(root, world_id)
    records = _read_world_records(root, world_id)
    connections = _read_world_connections(root, world_id)
    active_session = _active_population_session_for_world(root, world_id)
    knowledge = inspect_world_knowledge(root, world_id)
    coverage = knowledge["coverage_by_layer"]

    nodes: List[Dict[str, Any]] = [
        {
            "node_id": f"world:{world_id}",
            "node_type": "world",
            "layer": "world",
            "label": world.get("name", ""),
            "summary": world.get("summary", ""),
            "layout": {"x": 0.0, "y": 0.0},
            "metadata": {
                "ready_for_generation": world.get("population_overview", {}).get("ready_for_generation", False),
                "packet_count": len(world.get("packet_ids", [])),
            },
        }
    ]
    edges: List[Dict[str, Any]] = []

    for layer in _GRAPH_LAYER_ORDER:
        count = int(coverage.get(layer, 0))
        x, y = _layer_cluster_position(layer)
        cluster_id = f"cluster:{layer}"
        nodes.append(
            {
                "node_id": cluster_id,
                "node_type": "cluster",
                "layer": layer,
                "label": _GRAPH_LAYER_LABELS[layer],
                "summary": f"{count} fragment{'s' if count != 1 else ''}",
                "layout": {"x": x, "y": y},
                "metadata": {"count": count},
            }
        )
        edges.append(
            {
                "edge_id": f"edge:world:{layer}",
                "edge_type": "contains_layer",
                "source_id": f"world:{world_id}",
                "target_id": cluster_id,
                "weight": 0.4 + (0.06 * min(count, 5)),
            }
        )

    layer_counters: Dict[str, int] = Counter()
    for record in records:
        layer = str(record.get("layer", "")).strip() or "relationship"
        index = layer_counters[layer]
        layer_counters[layer] += 1
        x, y = _record_position(layer, index)
        nodes.append(
            {
                "node_id": record.get("knowledge_id", ""),
                "node_type": "fragment",
                "layer": layer,
                "label": record.get("label", ""),
                "summary": record.get("summary", ""),
                "tags": record.get("tags", []),
                "layout": {"x": x, "y": y},
                "metadata": record.get("metadata", {}),
            }
        )
        edges.append(
            {
                "edge_id": f"edge:cluster:{layer}:{record.get('knowledge_id', '')}",
                "edge_type": "belongs_to_layer",
                "source_id": f"cluster:{layer}",
                "target_id": record.get("knowledge_id", ""),
                "weight": 0.56,
            }
        )

    for connection in connections:
        edges.append(
            {
                "edge_id": connection.get("connection_id", ""),
                "edge_type": connection.get("connection_type", "inferred_world_link"),
                "source_id": connection.get("left_knowledge_id", ""),
                "target_id": connection.get("right_knowledge_id", ""),
                "weight": connection.get("score", 0.5),
                "shared_tags": connection.get("shared_tags", []),
                "reasons": connection.get("reasons", []),
            }
        )

    focus_node_id = f"world:{world_id}"
    if active_session and active_session.get("current_question_id"):
        question_id = active_session["current_question_id"]
        question_payload = _population_question_payload(root, active_session)
        target_layer = POPULATION_QUESTION_LAYER.get(question_id, "relationship")
        nodes.append(
            {
                "node_id": f"question:{active_session['session_id']}:{question_id}",
                "node_type": "question",
                "layer": target_layer,
                "label": question_payload.get("question", ""),
                "summary": question_payload.get("why_this_matters", ""),
                "layout": {"x": 0.0, "y": -160.0},
                "metadata": {
                    "question_id": question_id,
                    "session_id": active_session["session_id"],
                    "response_options": question_payload.get("response_options", []),
                    "allow_free_text": question_payload.get("allow_free_text", False),
                    "selection_mode": question_payload.get("selection_mode", "free_text"),
                },
            }
        )
        edges.append(
            {
                "edge_id": f"edge:question:{question_id}",
                "edge_type": "asks_for",
                "source_id": f"question:{active_session['session_id']}:{question_id}",
                "target_id": f"cluster:{target_layer}",
                "weight": 0.72,
            }
        )
        focus_node_id = f"question:{active_session['session_id']}:{question_id}"

    ready_for_generation = bool(world.get("population_overview", {}).get("ready_for_generation", False))
    canon_assets = read_jsonl(_canon_assets_path(root, world_id))
    recommended_actions: List[str] = []
    if active_session:
        recommended_actions.append("continue_population")
    elif ready_for_generation:
        recommended_actions.append("generate_canon" if not canon_assets else "compile_scene_from_canon")
        recommended_actions.append("compile_scene")
    else:
        recommended_actions.append("populate_world")
    if records:
        recommended_actions.append("inspect_node_graph")
    if canon_assets:
        recommended_actions.append("inspect_canon")
    if world.get("packet_ids"):
        recommended_actions.append("inspect_packets")
        recommended_actions.append("execute_packet")

    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "ready_for_generation": ready_for_generation,
        "focus_node_id": focus_node_id,
        "coverage_by_layer": coverage,
        "nodes": nodes,
        "edges": edges,
        "recommended_actions": recommended_actions,
        "active_session_id": active_session.get("session_id", "") if active_session else "",
        "packet_count": len(world.get("packet_ids", [])),
    }


def get_world_studio_guide(root: Path) -> Dict[str, Any]:
    return {
        "title": "Worldbuilding Studio Agent Workflow",
        "summary": (
            "Use the world OS as explicit graph truth: ingest evidence, ingest visual references with categories and traits, "
            "let the system commit layered records with provenance, attach reusable motion objects to scene entities, ask the next high-value question, "
            "generate canon references, then compile scenes from canon into generation packets."
        ),
        "browser_entry": {
            "path": "/world-studio.html",
            "description": "Conversation-first spatial canvas for creating a world, answering questions, and inspecting layered knowledge.",
        },
        "docs": {
            "agent_guide_path": str(root / "docs" / "guides" / "worldbuilding-studio-agent-workflow.md"),
            "agents_file": str(root / "AGENTS.md"),
            "operator_manuscript_path": str(root / "docs" / "guides" / "worldbuilding-studio-operator-manuscript.md"),
        },
        "cli_commands": [
            "python3 tools/conversation_os.py world-studio ingest-evidence --world-id <world_id> --source-text \"...\" --source-label \"...\"",
            "python3 tools/conversation_os.py world-studio ingest-visual-reference --world-id <world_id> --source-path ./ref.png --note \"...\" --categories architecture_style,material_style",
            "python3 tools/conversation_os.py world-studio inspect-visual-world --world-id <world_id>",
            "python3 tools/conversation_os.py world-studio compile-visual-context --world-id <world_id> --query-text \"...\"",
            "python3 tools/conversation_os.py world-studio create-motion-object --world-id <world_id> --label \"Restrained Forward Walk\" --scope character --primary-action \"walks forward with three slow measured steps\"",
            "python3 tools/conversation_os.py world-studio bind-motion-object --world-id <world_id> --motion-id <motion_id> --target-kind character --target-id default --when-tags man,walk,crosses",
            "python3 tools/conversation_os.py world-studio inspect-motion-system --world-id <world_id>",
            "python3 tools/conversation_os.py world-studio compile-motion-plan --world-id <world_id> --scene-text \"...\" --duration-seconds 4",
            "python3 tools/conversation_os.py world-studio create-character-profile --world-id <world_id> --name \"The Traveler\" --summary \"...\" --role primary_traveler",
            "python3 tools/conversation_os.py world-studio inspect-character-system --world-id <world_id>",
            "python3 tools/conversation_os.py world-studio update-character-profile --world-id <world_id> --character-id <character_id> --section identity --value-json '{\"one_line_essence\": \"...\"}'",
            "python3 tools/conversation_os.py world-studio update-character-feature --world-id <world_id> --feature-id <feature_id> --summary \"...\" --trait-values \"...,...\"",
            "python3 tools/conversation_os.py world-studio next-question --world-id <world_id>",
            "python3 tools/conversation_os.py world-studio inspect-evidence --world-id <world_id>",
            "python3 tools/conversation_os.py world-studio generate-canon --world-id <world_id>",
            "python3 tools/conversation_os.py world-studio compile-scene-from-canon --world-id <world_id> --scene-text \"...\"",
            "python3 tools/conversation_os.py world-studio execute-packet --packet-id <packet_id> --mode auto",
            "python3 tools/conversation_os.py world-studio populate-start --name \"Your World\" --summary \"Optional summary\"",
            "python3 tools/conversation_os.py world-studio populate-answer --session-id <session_id> --answer \"...\"",
            "python3 tools/conversation_os.py world-studio population-session --session-id <session_id>",
            "python3 tools/conversation_os.py world-studio inspect-knowledge --world-id <world_id>",
            "python3 tools/conversation_os.py world-studio inspect-graph --world-id <world_id>",
            "python3 tools/conversation_os.py world-studio compile-scene --world-id <world_id> --scene-text \"...\"",
            "python3 tools/conversation_os.py world-studio get-packet --packet-id <packet_id>",
        ],
        "api_routes": [
            {"method": "POST", "path": "/api/world-studio/ingest-evidence"},
            {"method": "POST", "path": "/api/world-studio/ingest-visual-reference"},
            {"method": "GET", "path": "/api/world-studio/world/<world_id>/visual"},
            {"method": "POST", "path": "/api/world-studio/compile-visual-context"},
            {"method": "POST", "path": "/api/world-studio/motion-object"},
            {"method": "POST", "path": "/api/world-studio/motion-binding"},
            {"method": "GET", "path": "/api/world-studio/world/<world_id>/motion"},
            {"method": "POST", "path": "/api/world-studio/compile-motion-plan"},
            {"method": "POST", "path": "/api/world-studio/character-profile"},
            {"method": "GET", "path": "/api/world-studio/world/<world_id>/characters"},
            {"method": "POST", "path": "/api/world-studio/update-character-profile"},
            {"method": "POST", "path": "/api/world-studio/update-character-feature"},
            {"method": "GET", "path": "/api/world-studio/world/<world_id>/next-question"},
            {"method": "GET", "path": "/api/world-studio/world/<world_id>/evidence"},
            {"method": "POST", "path": "/api/world-studio/generate-canon"},
            {"method": "POST", "path": "/api/world-studio/compile-scene-from-canon"},
            {"method": "POST", "path": "/api/world-studio/execute-packet"},
            {"method": "GET", "path": "/api/world-studio/executions"},
            {"method": "POST", "path": "/api/world-studio/population/start"},
            {"method": "POST", "path": "/api/world-studio/population/answer"},
            {"method": "GET", "path": "/api/world-studio/population/session/<session_id>"},
            {"method": "GET", "path": "/api/world-studio/world/<world_id>/knowledge"},
            {"method": "GET", "path": "/api/world-studio/world/<world_id>/graph"},
            {"method": "POST", "path": "/api/world-studio/compile-scene"},
            {"method": "GET", "path": "/api/world-studio/worlds"},
        ],
        "recommended_workflow": [
            "Ingest text notes and still-image references first so the world graph starts with explicit evidence-backed records.",
            "Ingest visual references with category labels, liked aspects, and negatives so architecture, flora, clothing, materials, and technology become reusable world facts.",
            "Ask only the next returned question and let the system either fill missing layers or clarify uncertainty.",
            "Inspect evidence and graph state when you need to know what is explicit, what is inferred, and which source supports a claim.",
            "Compile visual context before generation so the active category traits, scoped references, and negatives are what the agent actually sees.",
            "Create motion objects for character, camera, cloth, prop, and environment behavior, then bind them to default or named scene entities.",
            "Compile a motion plan before generation so the packet carries explicit body mechanics and secondary motion even when no anchor image is present.",
            "Create a character profile as one semantic object, then fill separate linked feature objects for silhouette, garments, movement, voice, inner pressure, and object affinity.",
            "Generate canonical character/place/object/motif references before asking Higgsfield for full scenes.",
            "Compile scenes from canon so later shots stay consistent with the world rather than drifting per prompt.",
            "Execute prepared packets through the Higgsfield adapter or hand the prepared MCP call to another agent.",
        ],
        "handoff_prompt": (
            "Use the World Studio operator manuscript. Ingest user notes and still-image references as evidence, commit explicit "
            "world records with provenance, create and bind reusable motion objects for entity behavior, ask only the next high-value question, inspect evidence before making assumptions, "
            "generate canon references before full scenes, and compile every scene from canon-backed world state."
        ),
        "new_chat_prompt_hint": (
            "In a fresh chat, tell the agent to use the World Studio operator manuscript, ingest evidence first, ask the next "
            "returned question, and generate canon before scene compilation."
        ),
    }


def _extract_story_beat(scene_text: str, world: Dict[str, Any]) -> Dict[str, Any]:
    text = scene_text.lower()
    scene_tags = set(_tokenize_tags(scene_text))
    primary_function = "scene"
    for candidate, triggers in [
        ("revelation", ["recognizes", "realizes", "reveals", "discovers", "finds", "understands"]),
        ("pursuit", ["follows", "tracks", "chases", "searches", "navigates"]),
        ("transformation", ["opens", "awakens", "becomes", "transforms", "changes"]),
        ("encounter", ["meets", "hears", "faces", "answers", "enters"]),
    ]:
        if any(term in text for term in triggers):
            primary_function = candidate
            break
    scored_primitives: List[tuple[int, str]] = []
    for primitive in world.get("project_primitives", []):
        primitive_tags = set(_tokenize_tags(primitive))
        overlap = len(scene_tags & primitive_tags)
        if overlap:
            scored_primitives.append((overlap, primitive))
    scored_primitives.sort(key=lambda row: (-row[0], row[1]))
    active_primitives = _unique([primitive for _, primitive in scored_primitives] or world.get("project_primitives", [])[:3])
    primitive_focus = ", ".join(active_primitives[:2]) if active_primitives else "the world pressure"
    if primary_function == "revelation":
        viewer_task = f"notice how {primitive_focus} becomes legible through action, space, and material detail"
        information_status = "hidden -> explicit"
        rhythm_need = "measured holds with one decisive reveal"
    elif primary_function == "pursuit":
        viewer_task = "track how the world's rules reshape the character's path"
        information_status = "unfolding"
        rhythm_need = "forward motion with readable pauses"
    elif primary_function == "transformation":
        viewer_task = "notice what changes once the world rule is activated"
        information_status = "unstable -> newly ordered"
        rhythm_need = "clear before-and-after contrast"
    elif primary_function == "encounter":
        viewer_task = "stay oriented as the world answers back"
        information_status = "partial -> contested"
        rhythm_need = "controlled escalation"
    else:
        viewer_task = "stay oriented inside the world's logic and emotional pressure"
        information_status = "partial"
        rhythm_need = "readable progression"
    return {
        "raw_scene_text": scene_text,
        "primary_function": primary_function,
        "emotional_state": primitive_focus,
        "information_status": information_status,
        "viewer_task": viewer_task,
        "rhythm_need": rhythm_need,
        "intimacy_level": "close and readable" if world.get("project_primitives") else "observational",
        "symbolic_weight": "high" if active_primitives else "medium",
        "emphasis_targets": ["world scale", "rule-bearing detail", "character action", "environmental consequence"],
        "active_primitives": active_primitives,
    }


def _activate_bridge_objects(scene_text: str, world: Dict[str, Any], active_primitives: List[str]) -> List[Dict[str, Any]]:
    text = scene_text.lower()
    primitive_text = " ".join(active_primitives).lower()
    activated = []
    for bridge in world.get("bridge_objects", []):
        triggers = [str(item).lower() for item in bridge.get("triggers", [])]
        if any(trigger in text or trigger in primitive_text for trigger in triggers):
            activated.append(bridge)
    if not activated:
        activated = sorted(world.get("bridge_objects", []), key=lambda row: float(row.get("weight", 0)), reverse=True)[:2]
    return activated


def _compile_layer_constraints(world: Dict[str, Any], bridges: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    layers: Dict[str, List[Dict[str, Any]]] = {}
    for layer, rules in world.get("visual_lens_rules", {}).items():
        layers[layer] = [
            {
                "semantic_role": row.get("semantic_role", ""),
                "instruction": row.get("instruction", ""),
                "weight": row.get("weight", 0.5),
                "source": "world.visual_lens_rules",
            }
            for row in rules
        ]
    for bridge in bridges:
        for layer, instruction in bridge.get("layer_mappings", {}).items():
            layers.setdefault(layer, []).append(
                {
                    "semantic_role": bridge.get("source_meaning", ""),
                    "instruction": instruction,
                    "weight": bridge.get("weight", 0.5),
                    "source": bridge.get("bridge_id", ""),
                }
            )
    return layers


def _compile_constraints(world: Dict[str, Any], bridges: List[Dict[str, Any]]) -> Dict[str, Any]:
    hard = list(world.get("constraints", {}).get("hard", []))
    soft = list(world.get("constraints", {}).get("soft", []))
    for bridge in bridges:
        hard.extend(bridge.get("hard_constraints", []))
        soft.extend({"rule": rule, "weight": bridge.get("weight", 0.5)} for rule in bridge.get("soft_constraints", []))
    return {"hard": _unique(hard), "soft": soft}


def _layer_instruction(layer_constraints: Dict[str, List[Dict[str, Any]]], layer: str, fallback: str) -> str:
    rows = layer_constraints.get(layer, [])
    if not rows:
        return fallback
    return rows[0].get("instruction", fallback)


def _default_shot_sequence(primary_function: str) -> List[str]:
    if primary_function == "revelation":
        return [
            "world establishment",
            "rule-bearing detail",
            "recognition action",
            "environmental consequence",
        ]
    if primary_function == "pursuit":
        return [
            "world establishment",
            "route or signal detail",
            "movement through the rule",
            "world response",
        ]
    if primary_function == "transformation":
        return [
            "before state",
            "activation detail",
            "change in motion",
            "after state",
        ]
    return [
        "world establishment",
        "material detail",
        "character action",
        "consequence reveal",
    ]


def _shot_description(
    *,
    index: int,
    sequence_role: str,
    semantic_connective: Dict[str, Any],
    scene_text: str,
) -> str:
    viewer_task = semantic_connective.get("viewer_task", "hold the world logic together")
    emphasis = semantic_connective.get("emphasis_targets", [])
    focus = emphasis[min(index, len(emphasis) - 1)] if emphasis else "world detail"
    if index == 0:
        return f"Establish the world pressure and make the scale immediately readable through {focus}."
    if index == 1:
        return f"Focus on the object, route, or material signal that carries the rule of the scene."
    if index == 2:
        return f"Show the character acting inside the rule so the viewer can {viewer_task}."
    if "response" in sequence_role or "consequence" in sequence_role or "after state" in sequence_role:
        return "Reveal how the environment answers the action and shifts the stakes."
    compact_scene = _compact_text(scene_text)
    return compact_scene if compact_scene else f"Advance the scene through {focus}."


def _compile_shot_plan(
    *,
    duration_seconds: int,
    semantic_connective: Dict[str, Any],
    layer_constraints: Dict[str, List[Dict[str, Any]]],
    cut_grammar: Dict[str, Any],
    scene_text: str,
) -> List[Dict[str, Any]]:
    sequence = cut_grammar.get("shot_sequence_bias") or _default_shot_sequence(semantic_connective.get("primary_function", "scene"))
    titles = [
        "World Establishment",
        "Rule Signal",
        "Character Throughline",
        "World Consequence",
    ]
    shot_count = max(3, min(4, len(sequence)))
    base_duration = float(duration_seconds) / shot_count
    shots: List[Dict[str, Any]] = []
    cursor = 0.0
    for index in range(shot_count):
        shot_duration = base_duration
        start = cursor
        end = duration_seconds if index == shot_count - 1 else round(cursor + shot_duration, 2)
        cursor = end
        shots.append(
            {
                "shot_id": f"shot-{index + 1:02d}",
                "index": index + 1,
                "title": titles[index],
                "time_label": f"{start:g}-{end:g}s",
                "duration_seconds": round(end - start, 2),
                "sequence_role": sequence[index],
                "description": _shot_description(
                    index=index,
                    sequence_role=sequence[index],
                    semantic_connective=semantic_connective,
                    scene_text=scene_text,
                ),
                "semantic_function": semantic_connective["primary_function"] if index in {1, 2} else semantic_connective["viewer_task"],
                "composition": _layer_instruction(layer_constraints, "composition", "Keep the subject isolated."),
                "camera": _layer_instruction(layer_constraints, "camera", "Use restrained camera motion."),
                "lighting": _layer_instruction(layer_constraints, "lighting", "Use motivated cinematic lighting."),
                "color": _layer_instruction(layer_constraints, "color", "Use a coherent color palette."),
                "prop": _layer_instruction(layer_constraints, "props", "Use a symbolic object."),
                "facial_expression": _layer_instruction(layer_constraints, "facial_expression", "Keep expression subtle."),
                "transition": "hard cut" if semantic_connective.get("primary_function") in {"revelation", "transformation"} and index in {1, 2} else "hold",
            }
        )
    return shots


def _bridge_summaries(bridges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "bridge_id": bridge.get("bridge_id", ""),
            "relation_type": bridge.get("relation_type", ""),
            "source_meaning": bridge.get("source_meaning", ""),
            "target_layers": bridge.get("target_layers", []),
            "weight": bridge.get("weight", 0.0),
            "evaluator_rules": bridge.get("evaluator_rules", []),
        }
        for bridge in bridges
    ]


def _compile_higgsfield_prompt(
    *,
    world: Dict[str, Any],
    context_packet: Dict[str, Any],
    shot_plan: List[Dict[str, Any]],
    motion_plan: Dict[str, Any] | None = None,
    resolved_model: str = "",
) -> str:
    visual_world = context_packet.get("visual_world", {})
    motion_prompt = (motion_plan or {}).get("compiled_prompt", "").strip()
    character_profiles = context_packet.get("character_profiles", [])
    if resolved_model in {"seedance1_5", "seedance_1_5", "seedance_2_0"}:
        category_clauses = []
        for row in visual_world.get("category_summaries", [])[:5]:
            traits = ", ".join(row.get("traits", [])[:2]).strip()
            if traits:
                category_clauses.append(traits)
        canon_assets = context_packet.get("selected_canon_assets", [])
        canon_labels = ", ".join(asset.get("label", "") for asset in canon_assets[:3] if asset.get("label", ""))
        avoid = ", ".join(context_packet["constraints"]["hard"][:3])
        continuity = []
        if canon_labels:
            continuity.append(f"Keep continuity with {canon_labels}.")
        if category_clauses:
            continuity.append(f"Preserve the reference world through {', '.join(category_clauses)}.")
        if character_profiles:
            for profile in character_profiles[:2]:
                feature_traits = []
                for feature in profile.get("feature_objects", [])[:3]:
                    feature_traits.extend(feature.get("trait_values", [])[:2])
                profile_clause = ", ".join(
                    item for item in [profile.get("name", ""), profile.get("summary", ""), *feature_traits[:4]] if item
                )
                if profile_clause:
                    continuity.append(f"Character semantic pack: {profile_clause}.")
        if avoid:
            continuity.append(f"Avoid {avoid}.")
        if motion_prompt:
            continuity.append(f"Motion plan: {motion_prompt}")
        return " ".join(
            part
            for part in [
                "Reference-driven cinematic video.",
                context_packet["raw_scene_text"],
                f"Motion should feel {context_packet['semantic_connective']['rhythm_need']} with restrained camera movement.",
                f"The viewer should {context_packet['semantic_connective']['viewer_task']}.",
                " ".join(continuity),
            ]
            if part
        ).strip()
    lines = [
        f"Generate a {context_packet['duration_seconds']}-second cinematic video.",
        "",
        "Scene request:",
        context_packet["raw_scene_text"],
        "",
        "World context:",
        f"- {world.get('summary', '')}",
        f"- Active primitives: {', '.join(context_packet['active_primitives'])}",
        f"- Taste profile: {world.get('taste_profile', {}).get('profile_name', '')}",
        "",
        "Semantic connective layer:",
        f"- Function: {context_packet['semantic_connective']['primary_function']}",
        f"- Viewer task: {context_packet['semantic_connective']['viewer_task']}",
        f"- Rhythm: {context_packet['semantic_connective']['rhythm_need']}",
        "",
        "Layer constraints:",
    ]
    for layer, rules in context_packet["layer_constraints"].items():
        instructions = "; ".join(row["instruction"] for row in rules[:2] if row.get("instruction"))
        lines.append(f"- {layer}: {instructions}")
    lines.extend(["", "Shot plan:"])
    for shot in shot_plan:
        lines.append(
            f"{shot['index']}. {shot['time_label']}: {shot['sequence_role']} - {shot['description']} "
            f"Camera: {shot['camera']} Transition: {shot['transition']}"
        )
    if character_profiles:
        lines.extend(["", "Character semantic pack:"])
        for profile in character_profiles:
            lines.append(f"- {profile.get('name', '')}: {profile.get('summary', '')}")
            for feature in profile.get("feature_objects", [])[:4]:
                trait_text = "; ".join(feature.get("trait_values", [])[:3]) or feature.get("summary", "")
                if trait_text:
                    lines.append(f"  - {feature.get('label', '')}: {trait_text}")
    if motion_prompt:
        lines.extend(["", "Motion plan:"])
        for item in motion_prompt.splitlines():
            lines.append(f"- {item}")
    if visual_world.get("active_categories"):
        lines.extend(["", "Visual world categories:"])
        for row in visual_world.get("category_summaries", []):
            traits = "; ".join(row.get("traits", [])[:3])
            lines.append(f"- {row.get('category', '')}: {traits}")
    if visual_world.get("negative_constraints"):
        lines.extend(["", "Visual negatives:"])
        for rule in visual_world.get("negative_constraints", []):
            lines.append(f"- {rule}")
    lines.extend(["", "Avoid:"])
    for rule in context_packet["constraints"]["hard"]:
        lines.append(f"- {rule}")
    lines.extend(["", "Evaluator target:", context_packet["evaluator_criteria"][0]])
    return "\n".join(lines)


def _is_retryable_higgsfield_error(message: str) -> bool:
    lowered = message.lower()
    return any(
        token in lowered
        for token in [
            "http 500",
            "http 502",
            "http 503",
            "http 504",
            "cannot reach https://fnf.higgsfield.ai/agents/jobs",
            "bad gateway",
            "gateway timeout",
        ]
    )


def _phase_match_score(text: str, cues: List[str]) -> int:
    lowered = text.lower()
    return sum(1 for cue in cues if cue in lowered)


def _visual_reference_media_inputs(
    visual_world: Dict[str, Any],
    *,
    resolved_model: str,
    scene_text: str = "",
) -> List[Dict[str, Any]]:
    if resolved_model not in {"seedance1_5", "seedance_1_5", "seedance_2_0"}:
        return []
    selected = visual_world.get("selected_references", [])
    if not isinstance(selected, list):
        return []
    references: List[Dict[str, Any]] = []
    for row in selected:
        if not isinstance(row, dict):
            continue
        candidate = str(row.get("source_path") or row.get("source_url") or "").strip()
        if not candidate:
            continue
        reference_text = " ".join(
            [
                str(row.get("source_label", "")),
                str(row.get("note", "")),
                " ".join(str(item) for item in row.get("liked_aspects", [])),
                " ".join(str(item) for item in row.get("tags", [])),
            ]
        )
        references.append(
            {
                "value": candidate,
                "text": reference_text,
                "start_score": _phase_match_score(reference_text, ["daylight", "day", "warm", "courtyard", "sun", "morning"]),
                "middle_score": _phase_match_score(reference_text, ["night", "blue", "glow", "shrine", "black sky", "evening"]),
                "end_score": _phase_match_score(reference_text, ["dream", "moon", "crescent", "painterly", "celestial", "stars"]),
            }
        )
    if not references:
        return []
    if scene_text.strip():
        scene_lower = scene_text.lower()
        if "night" not in scene_lower:
            for row in references:
                row["middle_score"] = 0
        if "dream" not in scene_lower:
            for row in references:
                row["end_score"] = 0
        if "day" not in scene_lower and "daylight" not in scene_lower:
            for row in references:
                row["start_score"] = 0
    used: set[str] = set()

    def _pick(best_key: str) -> Dict[str, Any] | None:
        ordered = sorted(
            references,
            key=lambda row: (
                row.get(best_key, 0),
                row.get("middle_score", 0) + row.get("start_score", 0) + row.get("end_score", 0),
            ),
            reverse=True,
        )
        for row in ordered:
            value = str(row.get("value", ""))
            if value and value not in used:
                used.add(value)
                return row
        return None

    start = _pick("start_score") or references[0]
    if str(start.get("value", "")):
        used.add(str(start["value"]))
    end = _pick("end_score")
    middle_rows = []
    middle = _pick("middle_score")
    if middle:
        middle_rows.append(middle)
    for row in references:
        value = str(row.get("value", ""))
        if value and value not in used:
            middle_rows.append(row)
            used.add(value)
    values = [str(start.get("value", ""))]
    values.extend(str(row.get("value", "")) for row in middle_rows if str(row.get("value", "")))
    if end and str(end.get("value", "")) not in values:
        values.append(str(end.get("value", "")))
    if not end and len(values) > 1:
        end = {"value": values.pop()}
    if not values:
        return []
    if len(values) == 1:
        return [{"role": "start_image", "value": values[0]}]
    if len(values) == 2:
        return [
            {"role": "start_image", "value": values[0]},
            {"role": "end_image", "value": values[1]},
        ]
    medias: List[Dict[str, Any]] = [{"role": "start_image", "value": values[0]}]
    for value in values[1:-1]:
        medias.append({"role": "image", "value": value})
    medias.append({"role": "end_image", "value": values[-1]})
    return medias


def _build_evaluation(context_packet: Dict[str, Any]) -> Dict[str, Any]:
    primary_focus = ", ".join(context_packet.get("active_primitives", [])[:2]) or "the active world logic"
    shot_roles = " -> ".join(shot.get("sequence_role", "") for shot in context_packet.get("shot_plan", [])[:3])
    checks = [
        {
            "criterion": "bridge_alignment",
            "question": f"Do all visible layers reinforce {primary_focus} rather than generic cinematic decoration?",
            "status": "planned",
            "weight": 0.34,
        },
        {
            "criterion": "cut_grammar",
            "question": f"Does the sequence stay faithful to the intended progression ({shot_roles})?",
            "status": "planned",
            "weight": 0.28,
        },
        {
            "criterion": "taste_profile",
            "question": "Does the output stay inside the world's taste profile and material logic?",
            "status": "planned",
            "weight": 0.24,
        },
        {
            "criterion": "constraint_compliance",
            "question": "Does the output avoid violating the hard constraints while keeping the scene readable?",
            "status": "planned",
            "weight": 0.14,
        },
    ]
    return {
        "packet_id": context_packet["packet_id"],
        "world_id": context_packet["world_id"],
        "evaluation_id": make_id("world-eval"),
        "created_at": utc_now(),
        "summary": "Planned evaluation: check world alignment, scene grammar, taste fit, and hard-constraint compliance.",
        "score": 0.86,
        "checks": checks,
        "status": "planned",
    }


def _active_motifs_for_scene(scene_text: str, world: Dict[str, Any], active_primitives: List[str]) -> List[str]:
    scene_tags = set(_tokenize_tags(scene_text, *active_primitives))
    motifs = [motif for motif in world.get("active_motifs", []) if scene_tags & set(_tokenize_tags(motif))]
    return motifs or world.get("active_motifs", [])[:3]


def _write_packet_bundle(
    root: Path,
    packet_id: str,
    *,
    context_packet: Dict[str, Any],
    higgsfield_execution_packet: Dict[str, Any],
    remotion_composition_props: Dict[str, Any],
    evaluation: Dict[str, Any],
) -> Path:
    packet_dir = _packet_dir(root, packet_id)
    write_json(packet_dir / "context_packet.json", context_packet)
    write_json(packet_dir / "higgsfield_execution_packet.json", higgsfield_execution_packet)
    write_json(packet_dir / "remotion_composition_props.json", remotion_composition_props)
    write_json(packet_dir / "evaluation.json", evaluation)
    write_json(
        packet_dir / "packet_bundle.json",
        {
            "context_packet": context_packet,
            "higgsfield_execution_packet": higgsfield_execution_packet,
            "remotion_composition_props": remotion_composition_props,
            "evaluation": evaluation,
        },
    )
    return packet_dir


def compile_scene(
    root: Path,
    world_id: str,
    scene_text: str,
    *,
    duration_seconds: int = 12,
    aspect_ratio: str = "16:9",
    model_preference: str = "cinematic_studio_3_0",
    visual_embedding_client: Any | None = None,
) -> Dict[str, Any]:
    world = get_world(root, world_id)
    packet_id = make_id("world-packet")
    resolved_model = _resolved_higgsfield_model(model_preference)
    story_beat = _extract_story_beat(scene_text, world)
    bridges = _activate_bridge_objects(scene_text, world, story_beat["active_primitives"])
    layer_constraints = _compile_layer_constraints(world, bridges)
    constraints = _compile_constraints(world, bridges)
    semantic_connective = {
        "primary_function": story_beat["primary_function"],
        "emotional_state": story_beat["emotional_state"],
        "information_status": story_beat["information_status"],
        "viewer_task": story_beat["viewer_task"],
        "rhythm_need": story_beat["rhythm_need"],
        "intimacy_level": story_beat["intimacy_level"],
        "symbolic_weight": story_beat["symbolic_weight"],
        "emphasis_targets": story_beat["emphasis_targets"],
    }
    active_motifs = _active_motifs_for_scene(scene_text, world, story_beat["active_primitives"])
    visual_world = compile_visual_context(
        root,
        world_id,
        query_text=scene_text,
        embedding_client=visual_embedding_client,
    )
    character_profiles = _select_character_profiles(root, world_id, scene_text)
    motion_plan = compile_motion_plan(
        root,
        world_id,
        scene_text=scene_text,
        duration_seconds=duration_seconds,
    )
    shot_plan = _compile_shot_plan(
        duration_seconds=duration_seconds,
        semantic_connective=semantic_connective,
        layer_constraints=layer_constraints,
        cut_grammar=world.get("cut_grammar", {}),
        scene_text=scene_text,
    )
    evaluator_criteria = _unique(
        [
            f"Do all layers reinforce {', '.join(story_beat['active_primitives'][:2]) or 'the world logic'} rather than unrelated cinematic decoration?",
            f"Does the shot rhythm stay faithful to {world.get('cut_grammar', {}).get('name', 'the scene grammar')}?",
            "Do canon, world rules, and performance cues remain coherent in the same scene?",
            *[rule for bridge in bridges for rule in bridge.get("evaluator_rules", [])],
        ]
    )
    width, height = _aspect_dimensions(aspect_ratio)
    context_packet = {
        "packet_id": packet_id,
        "studio_version": WORLD_STUDIO_VERSION,
        "created_at": utc_now(),
        "status": "compiled",
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "raw_scene_text": scene_text,
        "duration_seconds": duration_seconds,
        "aspect_ratio": aspect_ratio,
        "active_primitives": story_beat["active_primitives"],
        "active_motifs": active_motifs,
        "world_rules": world.get("world_rules", []),
        "semantic_connective": semantic_connective,
        "taste_profile": world.get("taste_profile", {}),
        "activated_bridge_objects": _bridge_summaries(bridges),
        "layer_constraints": layer_constraints,
        "cut_grammar": world.get("cut_grammar", {}),
        "shot_plan": shot_plan,
        "constraints": constraints,
        "evaluator_criteria": evaluator_criteria,
        "provenance_refs": world.get("provenance_refs", []),
        "visual_world": visual_world,
        "character_profiles": character_profiles,
        "motion_plan": motion_plan,
    }
    higgsfield_packet = {
        "packet_id": packet_id,
        "world_id": world_id,
        "provider": "higgsfield",
        "tool": "generate_video",
        "model_preference": model_preference,
        "resolved_model": resolved_model,
        "status": "ready_for_execution_when_mcp_available",
        "duration_seconds": duration_seconds,
        "aspect_ratio": aspect_ratio,
        "params": {
            "duration": duration_seconds,
            "aspect_ratio": aspect_ratio,
            "resolution": "720p" if width <= 1280 else "1080p",
        },
        "medias": _visual_reference_media_inputs(
            visual_world,
            resolved_model=resolved_model,
            scene_text=scene_text,
        ),
        "compiled_prompt": _compile_higgsfield_prompt(
            world=world,
            context_packet=context_packet,
            shot_plan=shot_plan,
            motion_plan=motion_plan,
            resolved_model=resolved_model,
        ),
        "negative_constraints": constraints["hard"],
        "evaluator_refs": evaluator_criteria,
        "visual_reference_ids": [row.get("visual_reference_id", "") for row in visual_world.get("selected_references", [])],
    }
    remotion_props = {
        "kind": "composition_props",
        "composition_id": "WorldStudioStoryboard",
        "props": {
            "packetId": packet_id,
            "worldTitle": world.get("name", ""),
            "sceneTitle": semantic_connective["primary_function"].replace("_", " ").title(),
            "sceneText": scene_text,
            "theme": world.get("summary", ""),
            "styleKeywords": world.get("taste_profile", {}).get("style_keywords", []),
            "activePrimitives": context_packet["active_primitives"],
            "activeMotifs": active_motifs,
            "visualWorld": visual_world,
            "characterProfiles": character_profiles,
            "motionPlan": motion_plan,
            "semanticConnective": semantic_connective,
            "layerConstraints": layer_constraints,
            "shots": shot_plan,
            "hardConstraints": constraints["hard"],
            "softConstraints": constraints["soft"],
            "evaluatorCriteria": evaluator_criteria,
            "evaluatorSummary": "",
        },
        "metadata": {
            "aspect_ratio": aspect_ratio,
            "width": width,
            "height": height,
            "fps": 30,
            "duration_seconds": duration_seconds,
            "duration_frames": _duration_frames(duration_seconds),
            "provenance": "worldbuilding_studio",
            "generation_source": "worldbuilding_studio_packet_compiler",
            "asset_role": "composition_input",
        },
    }
    evaluation = _build_evaluation(context_packet)
    remotion_props["props"]["evaluatorSummary"] = evaluation["summary"]

    packet_dir = _write_packet_bundle(
        root,
        packet_id,
        context_packet=context_packet,
        higgsfield_execution_packet=higgsfield_packet,
        remotion_composition_props=remotion_props,
        evaluation=evaluation,
    )

    world["packet_ids"] = _unique([*world.get("packet_ids", []), packet_id])
    world["updated_at"] = utc_now()
    write_json(_world_path(root, world_id), world)
    _append_event(root, "scene_compiled", {"world_id": world_id, "packet_id": packet_id, "scene_text": scene_text})
    return {
        "status": "compiled",
        "world_id": world_id,
        "packet_id": packet_id,
        "artifacts": {
            "context_packet": str(packet_dir / "context_packet.json"),
            "higgsfield_execution_packet": str(packet_dir / "higgsfield_execution_packet.json"),
            "remotion_composition_props": str(packet_dir / "remotion_composition_props.json"),
            "evaluation": str(packet_dir / "evaluation.json"),
        },
    }


def run_demo(root: Path, *, scene_text: str | None = None, duration_seconds: int = 12, aspect_ratio: str = "16:9") -> Dict[str, Any]:
    world = create_demo_world(root)
    packet = compile_scene(
        root,
        world["world_id"],
        scene_text or "Mina finds the fractured mirror and recognizes the betrayal.",
        duration_seconds=duration_seconds,
        aspect_ratio=aspect_ratio,
    )
    return {"status": packet["status"], "world": world, "packet": packet, "bundle": get_packet_bundle(root, packet["packet_id"])}


def get_packet_bundle(root: Path, packet_id: str) -> Dict[str, Any]:
    packet_dir = _packet_dir(root, packet_id)
    bundle = {
        "context_packet": read_json(packet_dir / "context_packet.json", default=None),
        "higgsfield_execution_packet": read_json(packet_dir / "higgsfield_execution_packet.json", default=None),
        "remotion_composition_props": read_json(packet_dir / "remotion_composition_props.json", default=None),
        "evaluation": read_json(packet_dir / "evaluation.json", default=None),
    }
    if any(value is None for value in bundle.values()):
        raise FileNotFoundError(f"Packet not found: {packet_id}")
    return bundle


class HiggsfieldMcpClient:
    def __init__(self, root: Path, *, server_url: str = HIGGSFIELD_SERVER_URL) -> None:
        self.root = root
        self.server_url = server_url

    def _ensure_vendor_path(self) -> None:
        candidates = [
            self.root / ".vendor" / "mcp_py",
            Path(__file__).resolve().parents[2] / ".vendor" / "mcp_py",
        ]
        for vendor in candidates:
            if vendor.exists() and str(vendor) not in sys.path:
                sys.path.insert(0, str(vendor))

    def _normalize_result(self, result: Any) -> Dict[str, Any]:
        structured = getattr(result, "structuredContent", None)
        content = []
        for item in getattr(result, "content", []):
            text = getattr(item, "text", None)
            if text:
                content.append(text)
        return {
            "is_error": bool(getattr(result, "isError", False)),
            "structured_content": structured,
            "content": content,
        }

    def _response_message(self, payload: Dict[str, Any]) -> str:
        structured = payload.get("structured_content")
        if isinstance(structured, dict) and structured.get("error"):
            return str(structured["error"])
        for text in payload.get("content", []):
            compact = _compact_text(text)
            if compact:
                return compact
        return ""

    def _response_request_id(self, payload: Dict[str, Any]) -> str:
        structured = payload.get("structured_content")
        if isinstance(structured, dict):
            return str(structured.get("request_id", ""))
        return ""

    def _extract_job_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        structured = payload.get("structured_content")
        if isinstance(structured, dict):
            data = dict(structured)
        else:
            data = {}
        results = data.get("results") or data.get("assets") or data.get("outputs") or []
        if isinstance(results, dict):
            results = [results]
        return {
            "status": str(
                data.get("status")
                or data.get("state")
                or ("completed" if results else "submitted")
            ),
            "job_id": str(data.get("job_id") or data.get("jobId") or data.get("id") or ""),
            "results": results if isinstance(results, list) else [],
            "raw_response": data or payload,
        }

    async def _call_tool_async(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_vendor_path()
        import anyio
        from mcp import ClientSession, StdioServerParameters, stdio_client

        params = StdioServerParameters(
            command="npx",
            args=["-y", f"mcp-remote@{HIGGSFIELD_MCP_REMOTE_VERSION}", self.server_url],
        )
        async with stdio_client(params) as streams:
            async with ClientSession(*streams) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                return self._normalize_result(result)

    def _call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        import anyio

        return anyio.run(self._call_tool_async, tool_name, arguments)

    def _call_tool_with_refresh(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        first = self._call_tool(tool_name, arguments)
        if not first.get("is_error"):
            return first
        message = self._response_message(first).lower()
        if "invalid or expired token" not in message:
            return first
        refreshed = _refresh_higgsfield_oauth_tokens(self.server_url)
        if not refreshed:
            return first
        return self._call_tool(tool_name, arguments)

    def submit(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        tool_name = str(request_payload.get("tool") or "generate_video")
        arguments = dict(request_payload.get("arguments", {}))
        first = self._call_tool_with_refresh(tool_name, arguments)
        if first.get("is_error"):
            return {
                "status": "failed",
                "error": self._response_message(first) or "Higgsfield tool call failed",
                "request_id": self._response_request_id(first),
                "raw_response": first,
                "results": [],
            }
        response = self._extract_job_payload(first)
        job_id = response.get("job_id", "")
        if job_id and response.get("status") not in {"completed", "failed", "canceled", "cancelled"}:
            follow_up = self._call_tool_with_refresh("job_status", {"jobId": job_id, "sync": True})
            if not follow_up.get("is_error"):
                polled = self._extract_job_payload(follow_up)
                polled["job_id"] = polled.get("job_id") or job_id
                return polled
        return response


def _find_higgsfield_cli_binary() -> str | None:
    configured = os.environ.get("HIGGSFIELD_CLI_BIN", "").strip()
    candidates = [configured] if configured else []
    candidates.extend(
        [
            shutil.which("higgsfield") or "",
            shutil.which("hf") or "",
            shutil.which("higgs") or "",
            "/opt/homebrew/bin/higgsfield",
            "/usr/local/bin/higgsfield",
        ]
    )
    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        path = Path(candidate).expanduser()
        if path.exists() and os.access(path, os.X_OK):
            return str(path)
    return None


def _is_higgsfield_uuid(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", value.strip().lower()))


def _media_suffix_for_role(role: str) -> str:
    normalized = role.strip().lower()
    if "video" in normalized:
        return ".mp4"
    if "audio" in normalized:
        return ".wav"
    return ".png"


class HiggsfieldCliClient:
    runtime_label = "official_cli"

    def __init__(self, root: Path, binary: str) -> None:
        self.root = root
        self.binary = binary

    def _run_json(self, args: List[str], *, timeout: int = HIGGSFIELD_CLI_TIMEOUT_SECONDS) -> Dict[str, Any] | List[Any]:
        command = [self.binary, *args]
        if "--json" not in command:
            command.append("--json")
        completed = subprocess.run(
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        stdout = completed.stdout.strip()
        stderr = completed.stderr.strip()
        if completed.returncode != 0:
            raise RuntimeError(stderr or stdout or f"Higgsfield CLI failed with exit code {completed.returncode}")
        if not stdout:
            return {}
        try:
            return json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to decode Higgsfield CLI JSON output: {exc}") from exc

    def _download_media_reference(self, value: str, role: str, tempdir: Path) -> str:
        suffix = Path(value.split("?", 1)[0]).suffix or _media_suffix_for_role(role)
        target = tempdir / f"{make_id('world-studio-ref')}{suffix}"
        request = Request(value, headers={"User-Agent": "inner-space-world-studio"})
        with urlopen(request, timeout=30) as response:  # noqa: S310
            target.write_bytes(response.read())
        return str(target)

    def _materialize_media_value(self, value: str, role: str, tempdir: Path) -> str:
        candidate = Path(value).expanduser()
        if candidate.exists():
            return str(candidate)
        if value.startswith("http://") or value.startswith("https://"):
            return self._download_media_reference(value, role, tempdir)
        return value

    def _upload_media_input(self, value: str, role: str, tempdir: Path) -> str:
        materialized = self._materialize_media_value(value, role, tempdir)
        if _is_higgsfield_uuid(materialized):
            return materialized
        candidate = Path(materialized).expanduser()
        if not candidate.exists():
            return materialized
        uploaded = self._run_json(["upload", "create", str(candidate)])
        if isinstance(uploaded, dict):
            upload_id = str(uploaded.get("id") or "")
            if upload_id:
                return upload_id
        raise RuntimeError(f"Failed to upload media input for role {role}: {value}")

    def _media_flag(self, role: str) -> str:
        normalized = role.strip().replace("_", "-").lower()
        return f"--{normalized or 'image'}"

    def _normalize_response(self, payload: Dict[str, Any] | List[Any], *, media_type: str = "video") -> Dict[str, Any]:
        rows = payload if isinstance(payload, list) else [payload]
        results: List[Dict[str, Any]] = []
        job_id = ""
        status = "submitted"
        for row in rows:
            if isinstance(row, str) and _is_higgsfield_uuid(row):
                job_id = job_id or row
                continue
            if not isinstance(row, dict):
                continue
            job_id = job_id or str(row.get("id") or row.get("job_id") or "")
            status = str(row.get("status") or status)
            result_url = row.get("result_url") or row.get("url") or ""
            if result_url:
                results.append(
                    {
                        "url": result_url,
                        "media_type": media_type,
                    }
                )
        return {
            "status": status,
            "job_id": job_id,
            "results": results,
            "raw_response": payload,
        }

    def submit(self, request_payload: Dict[str, Any]) -> Dict[str, Any]:
        try:
            params = dict(request_payload.get("arguments", {}).get("params", {}))
            model = str(params.pop("model"))
            prompt = str(params.pop("prompt"))
            media_type = "video" if model in HIGGSFIELD_SUPPORTED_VIDEO_MODELS else "image"
            medias = list(params.pop("medias", []))
            submission_count = max(1, int(params.pop("count", 1) or 1))
            payloads: List[Dict[str, Any] | List[Any]] = []
            with tempfile.TemporaryDirectory(prefix="world-studio-higgsfield-") as tempdir_name:
                tempdir = Path(tempdir_name)
                upload_cache: Dict[str, str] = {}
                for _ in range(submission_count):
                    last_error = ""
                    for attempt in range(3):
                        try:
                            create_args = [
                                "generate",
                                "create",
                                model,
                                "--prompt",
                                prompt,
                            ]
                            for key, value in params.items():
                                if value in {None, ""}:
                                    continue
                                if isinstance(value, (dict, list)):
                                    continue
                                create_args.extend([f"--{key}", str(value).lower() if isinstance(value, bool) else str(value)])
                            for media in medias:
                                if not isinstance(media, dict):
                                    continue
                                value = str(media.get("value", "")).strip()
                                if not value:
                                    continue
                                role = str(media.get("role", "image")).strip() or "image"
                                if value not in upload_cache:
                                    upload_cache[value] = self._upload_media_input(value, role, tempdir)
                                create_args.extend([self._media_flag(role), upload_cache[value]])
                            created = self._run_json(create_args)
                            created_rows = created if isinstance(created, list) else [created]
                            created_row = created_rows[0] if created_rows else {}
                            job_id = ""
                            if isinstance(created_row, str) and _is_higgsfield_uuid(created_row):
                                job_id = created_row
                            elif isinstance(created_row, dict):
                                job_id = str(created_row.get("id") or created_row.get("job_id") or "")
                            if not job_id:
                                payloads.append(created)
                                break
                            waited = self._run_json(
                                [
                                    "generate",
                                    "wait",
                                    job_id,
                                    "--timeout",
                                    "45m",
                                    "--interval",
                                    "5s",
                                    "--quiet",
                                ],
                                timeout=HIGGSFIELD_CLI_TIMEOUT_SECONDS,
                            )
                            payloads.append(waited)
                            break
                        except RuntimeError as exc:
                            last_error = str(exc)
                            if attempt == 2 or not _is_retryable_higgsfield_error(last_error):
                                raise
                            time.sleep(2 * (attempt + 1))
                    if last_error and not payloads:
                        raise RuntimeError(last_error)
            if len(payloads) == 1:
                return self._normalize_response(payloads[0], media_type=media_type)
            return self._normalize_response(payloads, media_type=media_type)
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "failed",
                "error": str(exc),
                "request_id": "",
                "raw_response": {"error": str(exc)},
                "results": [],
            }


def build_live_higgsfield_client(root: Path) -> HiggsfieldCliClient | HiggsfieldMcpClient:
    backend = os.environ.get("WORLD_STUDIO_HIGGSFIELD_BACKEND", "").strip().lower()
    if backend == "mcp":
        return HiggsfieldMcpClient(root)
    cli_binary = _find_higgsfield_cli_binary()
    if cli_binary:
        return HiggsfieldCliClient(root, cli_binary)
    return HiggsfieldMcpClient(root)


def _resolved_higgsfield_model(model_preference: str) -> str:
    candidate = str(model_preference or "").strip().lower()
    if candidate in HIGGSFIELD_SUPPORTED_VIDEO_MODELS:
        return candidate
    return HIGGSFIELD_DEFAULT_MODEL


def _supported_higgsfield_param_names(model_name: str) -> set[str]:
    normalized = str(model_name or "").strip().lower()
    explicit = HIGGSFIELD_MODEL_ALLOWED_PARAMS.get(normalized)
    if explicit:
        return set(explicit)
    return {"aspect_ratio", "duration", "medias", "prompt", "resolution", "genre", "mode"}


def _higgsfield_server_url_hash(server_url: str = HIGGSFIELD_SERVER_URL) -> str:
    return hashlib.md5(server_url.encode("utf-8")).hexdigest()


def _higgsfield_auth_paths(server_url: str = HIGGSFIELD_SERVER_URL) -> Dict[str, Path]:
    base = Path.home() / ".mcp-auth" / f"mcp-remote-{HIGGSFIELD_MCP_REMOTE_VERSION}"
    server_hash = _higgsfield_server_url_hash(server_url)
    return {
        "auth_dir": base,
        "client_info": base / f"{server_hash}_client_info.json",
        "tokens": base / f"{server_hash}_tokens.json",
    }


def _refresh_higgsfield_oauth_tokens(server_url: str = HIGGSFIELD_SERVER_URL) -> Dict[str, Any] | None:
    paths = _higgsfield_auth_paths(server_url)
    client_info = read_json(paths["client_info"], default=None)
    tokens = read_json(paths["tokens"], default=None)
    if not client_info or not tokens or not tokens.get("refresh_token"):
        return None
    payload = urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": tokens["refresh_token"],
            "client_id": client_info["client_id"],
        }
    ).encode("utf-8")
    request = Request(
        url="https://mcp.higgsfield.ai/oauth2/token",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=20) as response:  # noqa: S310
        refreshed = json.loads(response.read().decode("utf-8"))
    write_json(paths["tokens"], refreshed)
    return refreshed


def _higgsfield_mcp_tool_call(packet: Dict[str, Any]) -> Dict[str, Any]:
    resolved_model = _resolved_higgsfield_model(packet.get("model_preference", ""))
    prompt = packet.get("compiled_prompt", "").strip()
    allowed_param_names = _supported_higgsfield_param_names(resolved_model)
    params = {
        "model": resolved_model,
        "prompt": prompt,
        "count": 1,
    }
    packet_params = dict(packet.get("params", {}))
    for key, value in packet_params.items():
        if key not in allowed_param_names:
            continue
        if value in {None, ""}:
            continue
        if isinstance(value, (dict, list)):
            continue
        params[key] = value
    medias = []
    for media in packet.get("medias", []):
        value = media.get("value") or media.get("url") or media.get("path")
        if not value:
            continue
        medias.append(
            {
                "value": value,
                "role": media.get("role", "reference"),
            }
        )
    if medias:
        params["medias"] = medias
    return {
        "namespace": "mcp__higgsfield__",
        "tool": packet.get("tool", "generate_video"),
        "arguments": {"params": params},
    }


def _all_execution_runs(root: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    worlds_dir = _worlds_dir(root)
    if not worlds_dir.exists():
        return rows
    for path in sorted(worlds_dir.glob("*/executions/execution_runs.jsonl")):
        rows.extend(read_jsonl(path))
    rows.sort(key=lambda row: row.get("created_at", ""))
    return rows


def _upsert_execution_run(root: Path, world_id: str, run: Dict[str, Any]) -> Dict[str, Any]:
    rows = list(read_jsonl(_execution_runs_path(root, world_id)))
    updated = False
    for index, existing in enumerate(rows):
        if existing.get("execution_id") == run.get("execution_id"):
            rows[index] = run
            updated = True
            break
    if not updated:
        rows.append(run)
    write_jsonl(_execution_runs_path(root, world_id), rows)
    return run


def list_execution_runs(root: Path, *, packet_id: str = "", world_id: str = "") -> Dict[str, Any]:
    runs = _all_execution_runs(root) if not world_id else list(read_jsonl(_execution_runs_path(root, world_id)))
    filtered = [
        run
        for run in runs
        if (not packet_id or run.get("packet_id") == packet_id) and (not world_id or run.get("world_id") == world_id)
    ]
    filtered.sort(key=lambda row: row.get("created_at", ""))
    return {
        "count": len(filtered),
        "packet_id": packet_id,
        "world_id": world_id,
        "executions": filtered,
    }


def get_execution_run(root: Path, execution_id: str) -> Dict[str, Any]:
    for run in _all_execution_runs(root):
        if run.get("execution_id") == execution_id:
            return run
    raise FileNotFoundError(f"Execution run not found: {execution_id}")


def _record_execution_assets(
    root: Path,
    packet_id: str,
    execution_id: str,
    provider_job_id: str,
    response: Dict[str, Any],
) -> List[str]:
    asset_ids: List[str] = []
    for index, result in enumerate(response.get("results", [])):
        url = result.get("url", "")
        path = result.get("path", "")
        if not url and not path:
            continue
        asset = record_generation_asset(
            root,
            packet_id,
            provider="higgsfield",
            kind="execution_output",
            url=url,
            path=path,
            media_type=result.get("media_type", "video"),
            metadata={
                "execution_id": execution_id,
                "provider_job_id": provider_job_id,
                "result_index": index,
                **{key: value for key, value in result.items() if key not in {"url", "path"}},
            },
        )
        asset_ids.append(asset["asset_id"])
    return asset_ids


def execute_higgsfield_packet(
    root: Path,
    packet_id: str,
    *,
    client: Any | None = None,
    mode: str = "prepared",
) -> Dict[str, Any]:
    bundle = get_packet_bundle(root, packet_id)
    context_packet = dict(bundle["context_packet"])
    higgsfield_packet = dict(bundle["higgsfield_execution_packet"])
    remotion_props = dict(bundle["remotion_composition_props"])
    evaluation = dict(bundle["evaluation"])
    if higgsfield_packet.get("provider") != "higgsfield":
        raise ValueError(f"Packet {packet_id} is not a Higgsfield packet")
    normalized_mode = str(mode or "prepared").strip().lower()
    if normalized_mode not in {"prepared", "live", "auto"}:
        raise ValueError(f"Unsupported execution mode: {mode}")

    world_id = context_packet["world_id"]
    mcp_tool_call = _higgsfield_mcp_tool_call(higgsfield_packet)
    resolved_model = mcp_tool_call["arguments"]["params"]["model"]
    execution_id = make_id("world-execution")
    execution = {
        "execution_id": execution_id,
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "packet_id": packet_id,
        "world_id": world_id,
        "provider": "higgsfield",
        "tool": higgsfield_packet.get("tool", "generate_video"),
        "status": "prepared",
        "mode": normalized_mode,
        "model_preference": higgsfield_packet.get("model_preference", ""),
        "resolved_model": resolved_model,
        "provider_job_id": "",
        "asset_ids": [],
        "mcp_tool_call": mcp_tool_call,
    }
    if client is None and normalized_mode in {"live", "auto"}:
        client = build_live_higgsfield_client(root)

    if client is None:
        higgsfield_packet["status"] = "prepared"
        higgsfield_packet["resolved_model"] = resolved_model
        higgsfield_packet["last_execution_id"] = execution_id
        _write_packet_bundle(
            root,
            packet_id,
            context_packet=context_packet,
            higgsfield_execution_packet=higgsfield_packet,
            remotion_composition_props=remotion_props,
            evaluation=evaluation,
        )
        _upsert_execution_run(root, world_id, execution)
        _refresh_world_from_records(root, world_id)
        _append_event(root, "higgsfield_execution_prepared", {"world_id": world_id, "packet_id": packet_id, "execution_id": execution_id})
        return execution

    execution["status"] = "submitted"
    execution["mode"] = "live"
    execution["updated_at"] = utc_now()
    higgsfield_packet["status"] = "submitted"
    higgsfield_packet["resolved_model"] = resolved_model
    higgsfield_packet["last_execution_id"] = execution_id
    _write_packet_bundle(
        root,
        packet_id,
        context_packet=context_packet,
        higgsfield_execution_packet=higgsfield_packet,
        remotion_composition_props=remotion_props,
        evaluation=evaluation,
    )
    _upsert_execution_run(root, world_id, execution)
    _refresh_world_from_records(root, world_id)
    _append_event(
        root,
        "higgsfield_execution_submitted",
        {"world_id": world_id, "packet_id": packet_id, "execution_id": execution_id, "mode": "live"},
    )
    try:
        response = client.submit(
            {
                "namespace": mcp_tool_call["namespace"],
                "tool": mcp_tool_call["tool"],
                "arguments": mcp_tool_call["arguments"],
                "packet_id": packet_id,
                "world_id": world_id,
            }
        )
    except Exception as exc:  # noqa: BLE001
        execution["status"] = "failed"
        execution["updated_at"] = utc_now()
        execution["error"] = str(exc)
        higgsfield_packet["status"] = "failed"
        higgsfield_packet["resolved_model"] = resolved_model
        higgsfield_packet["last_execution_id"] = execution_id
        higgsfield_packet["last_error"] = str(exc)
        _write_packet_bundle(
            root,
            packet_id,
            context_packet=context_packet,
            higgsfield_execution_packet=higgsfield_packet,
            remotion_composition_props=remotion_props,
            evaluation=evaluation,
        )
        _upsert_execution_run(root, world_id, execution)
        _refresh_world_from_records(root, world_id)
        _append_event(
            root,
            "higgsfield_execution_failed",
            {"world_id": world_id, "packet_id": packet_id, "execution_id": execution_id, "error": str(exc)},
        )
        return execution

    provider_job_id = response.get("job_id") or response.get("provider_job_id", "")
    asset_ids = _record_execution_assets(root, packet_id, execution_id, provider_job_id, response)
    execution["updated_at"] = utc_now()
    execution["status"] = str(response.get("status", "submitted"))
    execution["provider_job_id"] = provider_job_id
    execution["asset_ids"] = asset_ids
    execution["provider_response"] = response.get("raw_response", response)

    higgsfield_packet["status"] = execution["status"]
    higgsfield_packet["resolved_model"] = resolved_model
    higgsfield_packet["last_execution_id"] = execution_id
    higgsfield_packet["provider_job_id"] = provider_job_id
    higgsfield_packet["result_asset_ids"] = asset_ids
    _write_packet_bundle(
        root,
        packet_id,
        context_packet=context_packet,
        higgsfield_execution_packet=higgsfield_packet,
        remotion_composition_props=remotion_props,
        evaluation=evaluation,
    )
    _upsert_execution_run(root, world_id, execution)
    _refresh_world_from_records(root, world_id)
    _append_event(
        root,
        "higgsfield_execution_completed" if execution["status"] == "completed" else "higgsfield_execution_submitted",
        {
            "world_id": world_id,
            "packet_id": packet_id,
            "execution_id": execution_id,
            "provider_job_id": provider_job_id,
            "asset_count": len(asset_ids),
        },
    )
    return execution


def record_generation_asset(
    root: Path,
    packet_id: str,
    *,
    provider: str,
    kind: str,
    url: str = "",
    path: str = "",
    media_type: str = "video",
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    bundle = get_packet_bundle(root, packet_id)
    context_packet = bundle["context_packet"]
    asset = {
        "asset_id": make_id("world-asset"),
        "created_at": utc_now(),
        "packet_id": packet_id,
        "world_id": context_packet["world_id"],
        "provider": provider,
        "kind": kind,
        "url": url,
        "path": path,
        "media_type": media_type,
        "metadata": metadata or {},
    }
    rows = read_jsonl(_assets_path(root))
    rows.append(asset)
    write_jsonl(_assets_path(root), rows)
    world = get_world(root, context_packet["world_id"])
    world["asset_ids"] = _unique([*world.get("asset_ids", []), asset["asset_id"]])
    world["updated_at"] = utc_now()
    write_json(_world_path(root, world["world_id"]), world)
    _append_event(root, "asset_recorded", {"world_id": world["world_id"], "packet_id": packet_id, "asset_id": asset["asset_id"]})
    return asset


def _download_result_to_path(url: str, target_path: Path) -> str:
    request = Request(url, headers={"User-Agent": "inner-space-world-studio"})
    with urlopen(request, timeout=60) as response:  # noqa: S310
        target_path.write_bytes(response.read())
    return str(target_path)


def _asset_row_by_id(root: Path, asset_id: str) -> Dict[str, Any] | None:
    for row in read_jsonl(_assets_path(root)):
        if row.get("asset_id") == asset_id:
            return row
    return None


def _first_result_url(response: Dict[str, Any]) -> str:
    for row in response.get("results", []):
        url = str(row.get("url", "")).strip()
        if url:
            return url
    return ""


def _build_showcase_anchor_prompt(world: Dict[str, Any], spec: Dict[str, Any], visual_world: Dict[str, Any]) -> str:
    category_clauses: List[str] = []
    for row in visual_world.get("category_summaries", [])[:4]:
        traits = ", ".join(item.strip() for item in row.get("traits", [])[:2] if str(item).strip())
        if traits:
            category_clauses.append(traits)
    world_summary = str(world.get("summary", "")).strip()
    motifs = ", ".join(world.get("active_motifs", [])[:3])
    continuity = (
        "The same solitary adult man appears in every state: lean build, face mostly obscured, pale layered draped robe, "
        "moving forward through the same sacred route."
    )
    parts = [
        spec.get("prompt_core", ""),
        continuity,
        f"World summary: {world_summary}." if world_summary else "",
        f"Recurring motifs: {motifs}." if motifs else "",
        f"Reference traits: {'; '.join(category_clauses)}." if category_clauses else "",
    ]
    return " ".join(part.strip() for part in parts if part.strip())


def _generate_showcase_anchor(
    root: Path,
    world_id: str,
    *,
    spec: Dict[str, Any],
    image_model: str,
    aspect_ratio: str,
    client: Any,
    visual_embedding_client: Any | None = None,
) -> Dict[str, Any]:
    world = get_world(root, world_id)
    visual_world = compile_visual_context(
        root,
        world_id,
        query_text=spec["query_text"],
        embedding_client=visual_embedding_client,
    )
    prompt = _build_showcase_anchor_prompt(world, spec, visual_world)
    response = client.submit(
        {
            "arguments": {
                "params": {
                    "model": image_model,
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                }
            }
        }
    )
    if str(response.get("status", "")).lower() != "completed":
        raise RuntimeError(f"Anchor generation failed for {spec['role']}: {response}")
    result_url = _first_result_url(response)
    if not result_url:
        raise RuntimeError(f"Anchor generation returned no result URL for {spec['role']}: {response}")
    suffix = Path(result_url.split("?", 1)[0]).suffix or ".png"
    local_path = Path(_world_generated_anchors_dir(root, world_id)) / f"{slugify(spec['role'])}{suffix}"
    ensure_dir(local_path.parent)
    _download_result_to_path(result_url, local_path)
    asset = _upsert_canon_asset(
        root,
        world_id,
        {
            "canon_id": make_id("world-canon"),
            "created_at": utc_now(),
            "world_id": world_id,
            "asset_type": "state_anchor",
            "label": spec["label"],
            "summary": spec["anchor_summary"],
            "source_record_ids": [],
            "supporting_evidence_ids": [],
            "provider": "higgsfield",
            "tool": "generate_image",
            "compiled_prompt": prompt,
            "metadata": {
                "anchor_role": spec["role"],
                "local_path": str(local_path),
                "url": result_url,
                "image_model": image_model,
                "query_text": spec["query_text"],
                "tags": [spec["role"], "three-state-showcase", "state-anchor"],
            },
        },
    )
    _append_event(
        root,
        "showcase_anchor_generated",
        {
            "world_id": world_id,
            "canon_id": asset["canon_id"],
            "anchor_role": spec["role"],
            "image_model": image_model,
        },
    )
    return asset


def _download_execution_asset(root: Path, asset_id: str, target_path: Path) -> str:
    asset = _asset_row_by_id(root, asset_id)
    if not asset:
        raise FileNotFoundError(f"Execution asset not found: {asset_id}")
    path = str(asset.get("path", "")).strip()
    if path and Path(path).exists():
        shutil.copy2(path, target_path)
        return str(target_path)
    url = str(asset.get("url", "")).strip()
    if not url:
        raise ValueError(f"Execution asset has no local path or URL: {asset_id}")
    return _download_result_to_path(url, target_path)


def _stitch_videos_ffmpeg(clip_paths: List[str], output_path: Path) -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("ffmpeg is required to stitch showcase clips")
    ensure_dir(output_path.parent)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as handle:
        concat_list = Path(handle.name)
        for path in clip_paths:
            handle.write(f"file '{Path(path).as_posix()}'\n")
    try:
        completed = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                str(output_path),
            ],
            cwd=output_path.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or "ffmpeg concat failed")
    finally:
        concat_list.unlink(missing_ok=True)
    return str(output_path)


def orchestrate_three_state_showcase(
    root: Path,
    world_id: str,
    *,
    image_model: str = HIGGSFIELD_DEFAULT_IMAGE_MODEL,
    video_model: str = "seedance_2_0",
    aspect_ratio: str = "16:9",
    clip_duration_seconds: int = 4,
    visual_embedding_client: Any | None = None,
    client: Any | None = None,
) -> Dict[str, Any]:
    world = get_world(root, world_id)
    generate_canon(
        root,
        world_id,
        style_note=(
            "Maintain one recurring draped male figure, one sacred architectural lineage, one forward route, and let only the "
            "detail density, light, and rendering behavior change by state."
        ),
    )
    if client is None:
        client = build_live_higgsfield_client(root)

    anchor_assets = [
        _generate_showcase_anchor(
            root,
            world_id,
            spec=spec,
            image_model=image_model,
            aspect_ratio=aspect_ratio,
            client=client,
            visual_embedding_client=visual_embedding_client,
        )
        for spec in THREE_STATE_SHOWCASE_SPECS
    ]
    anchor_by_role = {
        str(asset.get("metadata", {}).get("anchor_role", "") or asset.get("label", "")).strip(): asset
        for asset in anchor_assets
        if isinstance(asset, dict)
    }
    _refresh_world_from_records(root, world_id)

    showcase_dir = Path(_world_showcases_dir(root, world_id))
    clips_dir = showcase_dir / "clips"
    ensure_dir(clips_dir)
    clip_runs: List[Dict[str, Any]] = []
    clip_paths: List[str] = []
    for index, spec in enumerate(THREE_STATE_SHOWCASE_SPECS, start=1):
        compiled = compile_scene_from_canon(
            root,
            world_id,
            spec["scene_text"],
            duration_seconds=clip_duration_seconds,
            aspect_ratio=aspect_ratio,
            model_preference=video_model,
            visual_embedding_client=visual_embedding_client,
        )
        packet_bundle = get_packet_bundle(root, compiled["packet_id"])
        higgsfield_packet = dict(packet_bundle["higgsfield_execution_packet"])
        anchor_asset = anchor_by_role.get(spec["role"])
        if anchor_asset:
            anchor_metadata = dict(anchor_asset.get("metadata", {}))
            anchor_value = str(
                anchor_metadata.get("local_path")
                or anchor_metadata.get("path")
                or anchor_metadata.get("source_path")
                or anchor_metadata.get("url")
                or anchor_metadata.get("source_url")
                or ""
            ).strip()
            if anchor_value:
                higgsfield_packet["medias"] = [{"role": "start_image", "value": anchor_value}]
                higgsfield_packet["anchor_media_strategy"] = "showcase_anchor_override"
        _write_packet_bundle(
            root,
            compiled["packet_id"],
            context_packet=packet_bundle["context_packet"],
            higgsfield_execution_packet=higgsfield_packet,
            remotion_composition_props=packet_bundle["remotion_composition_props"],
            evaluation=packet_bundle["evaluation"],
        )
        execution = execute_higgsfield_packet(root, compiled["packet_id"], client=client, mode="live")
        if execution.get("status") != "completed" or not execution.get("asset_ids"):
            raise RuntimeError(f"Showcase clip generation failed for {spec['role']}: {execution}")
        clip_path = clips_dir / f"{index:02d}-{slugify(spec['role'])}.mp4"
        downloaded = _download_execution_asset(root, execution["asset_ids"][0], clip_path)
        clip_runs.append(
            {
                "role": spec["role"],
                "packet_id": compiled["packet_id"],
                "execution_id": execution["execution_id"],
                "asset_ids": execution["asset_ids"],
                "local_path": downloaded,
            }
        )
        clip_paths.append(downloaded)

    final_path = Path(_stitch_videos_ffmpeg(clip_paths, showcase_dir / "three-state-traversal-showcase.mp4"))
    _append_event(
        root,
        "three_state_showcase_completed",
        {
            "world_id": world_id,
            "world_name": world.get("name", ""),
            "clip_packet_ids": [row["packet_id"] for row in clip_runs],
            "output_path": str(final_path),
        },
    )
    return {
        "world_id": world_id,
        "world_name": world.get("name", ""),
        "anchor_assets": anchor_assets,
        "clips": clip_runs,
        "output_path": str(final_path),
        "image_model": image_model,
        "video_model": video_model,
        "aspect_ratio": aspect_ratio,
        "clip_duration_seconds": clip_duration_seconds,
    }


def evaluate_output(root: Path, packet_id: str, *, observed_text: str) -> Dict[str, Any]:
    bundle = get_packet_bundle(root, packet_id)
    context_packet = bundle["context_packet"]
    observed = observed_text.lower()
    expected_terms = _unique(
        [
            context_packet.get("raw_scene_text", ""),
            *context_packet.get("constraints", {}).get("hard", [])[:2],
            *context_packet.get("active_primitives", [])[:2],
            *context_packet.get("active_motifs", [])[:2],
            *[rule.get("rule", "") for rule in context_packet.get("constraints", {}).get("soft", [])[:2]],
            *[shot.get("description", "") for shot in context_packet.get("shot_plan", [])[1:3]],
        ]
    )
    required_signals = _unique(
        [
        token
        for phrase in expected_terms
        for token in _tokenize_tags(phrase)
        if len(token) > 3
        ]
    )[:8]
    if not required_signals:
        required_signals = ["world", "scene", "rule"]
    matched = [signal for signal in required_signals if signal in observed]
    score = round(len(matched) / max(1, min(len(required_signals), 4)), 2)
    score = min(1.0, score)
    evaluation = {
        "evaluation_id": make_id("world-output-eval"),
        "created_at": utc_now(),
        "packet_id": packet_id,
        "world_id": context_packet["world_id"],
        "observed_text": observed_text,
        "matched_signals": matched,
        "missing_signals": [signal for signal in required_signals if signal not in matched],
        "score": score,
        "status": "pass" if score >= 0.7 else "needs_revision",
        "summary": "Output evaluation against world alignment, canon continuity, and packet constraints.",
    }
    packet_dir = _packet_dir(root, packet_id)
    write_json(packet_dir / f"{evaluation['evaluation_id']}.json", evaluation)
    _append_event(root, "output_evaluated", {"world_id": context_packet["world_id"], "packet_id": packet_id, "evaluation_id": evaluation["evaluation_id"], "score": score})
    return evaluation
