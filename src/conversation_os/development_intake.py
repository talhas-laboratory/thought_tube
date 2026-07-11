from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from .codebase_overview import refresh_codebase_overview
from .conversation_synthesis import derive_development_signals
from .models import DevelopmentIdeaRecord
from .personal_interface import translate_idea_to_technical_framing
from .runtime_layout import product_runtime_dir, product_source_dir
from .routing import build_task_pack
from .storage import append_jsonl, ensure_dir, make_id, read_jsonl, utc_now, write_jsonl


MODULE_ID = "assembly.development.development_intake"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "record_development_idea",
    "get_development_idea",
    "list_development_ideas",
    "translate_development_idea",
    "build_development_proposal",
    "get_development_proposal",
    "list_development_proposals",
    "approve_development_proposal",
    "build_proposal_task_pack",
)
__all__ = list(PUBLIC_API)


THOUGHT_GRAPH_SIZE_LENSES = [
    {
        "lens_key": "raw_drop",
        "label": "Raw Drop",
        "purpose": "Preserve the submitted wording as the source layer.",
    },
    {
        "lens_key": "micro_shift",
        "label": "Micro Shift",
        "purpose": "Track sentence-level tone, context, or intent changes.",
    },
    {
        "lens_key": "meta_commentary",
        "label": "Meta Commentary",
        "purpose": "Store derived commentary about the conversation's dynamics, implicit instructions, uncertainty, and tool-readiness.",
    },
    {
        "lens_key": "cross_conversation",
        "label": "Cross Conversation",
        "purpose": "Compare the drop against prior themes, concepts, and related conversations.",
    },
    {
        "lens_key": "macro_conversation",
        "label": "Macro Conversation",
        "purpose": "Summarize the whole drop as one durable product direction.",
    },
    {
        "lens_key": "workflow_path",
        "label": "Workflow Path",
        "purpose": "Map the drop toward owner-aware implementation steps.",
    },
    {
        "lens_key": "bridge_orchestration",
        "label": "Bridge Orchestration",
        "purpose": "Identify communication and tool-routing implications.",
    },
]

DIMENSION_KEYWORDS = {
    "mobile_execution": {"mobile", "phone", "codex", "vps", "hosted", "openclaw", "hermes", "execution"},
    "workflow_routing": {"workflow", "route", "routing", "implement", "implementation", "safe", "guard"},
    "conversation_analysis": {"conversation", "micro", "macro", "tone", "dynamic", "context", "shift", "lens"},
    "bridge_orchestration": {"bridge", "hub", "incoming", "flow", "communication", "state"},
    "expert_tool_orchestration": {"tool", "tools", "blender", "higgsfield", "excel", "statistics", "expert"},
}


def _product_dir(root: Path) -> Path:
    return product_source_dir(root, "development_layer_v1")


def _data_dir(root: Path) -> Path:
    return product_runtime_dir(root, "development_layer_v1", "data")


def _ideas_path(root: Path) -> Path:
    return _data_dir(root) / "ideas.jsonl"


def _proposals_path(root: Path) -> Path:
    return _data_dir(root) / "proposals.jsonl"


def _proposal_reviews_path(root: Path) -> Path:
    return _data_dir(root) / "proposal_reviews.jsonl"


def _normalize_string_list(values: List[str] | None) -> List[str]:
    normalized: List[str] = []
    for value in values or []:
        text = str(value or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _preview_text(value: Any, limit: int = 120) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _thought_segments(raw_idea: str, desired_effect: str) -> List[str]:
    text = "\n".join(value for value in [raw_idea, desired_effect] if value)
    candidates = [
        " ".join(part.split())
        for part in re.split(r"(?:[\n\r]+|(?<=[.!?])\s+)", text)
    ]
    return [part for part in candidates if len(part) >= 12][:8]


def _dimension_tags(text: str) -> List[str]:
    tokens = set(re.findall(r"[a-z0-9_]+", text.lower()))
    tags = [
        dimension
        for dimension, keywords in DIMENSION_KEYWORDS.items()
        if tokens & keywords
    ]
    return tags or ["emergent_misc"]


def _graph_node(graph_id: str, lens: str, index: int, label: str, summary: str, dimensions: List[str]) -> Dict[str, Any]:
    return {
        "node_id": f"{graph_id}:{lens}:{index}",
        "lens": lens,
        "label": _preview_text(label, 72),
        "summary": _preview_text(summary, 220),
        "dimensions": dimensions,
    }


def _build_meta_commentary_artifacts(
    *,
    graph_id: str,
    raw_idea: str,
    desired_effect: str,
    source_refs: List[str],
) -> List[Dict[str, Any]]:
    text = " ".join([raw_idea, desired_effect]).lower()
    artifacts: List[Dict[str, Any]] = []

    def add_artifact(
        artifact_type: str,
        summary: str,
        dimensions: List[str],
        confidence: float,
        uncertainty: List[str] | None = None,
    ) -> None:
        artifacts.append(
            {
                "artifact_id": f"{graph_id}:meta-commentary:{len(artifacts)}",
                "artifact_type": artifact_type,
                "lens": "meta_commentary",
                "summary": summary,
                "analysis_dimensions": dimensions,
                "evidence_refs": source_refs,
                "confidence": confidence,
                "uncertainty": uncertainty or [],
            }
        )

    if any(token in text for token in ("brain dump", "vision", "rough", "thought")):
        add_artifact(
            "interaction_dynamic",
            "The user is in capture mode and needs preservation before narrowing.",
            ["capture_mode", "scope_pressure"],
            0.74,
        )
    if any(token in text for token in ("micro", "macro", "lens", "dimension", "meta")):
        add_artifact(
            "abstraction_move",
            "The user is asking to analyze the conversation through multiple abstraction sizes.",
            ["abstraction_level", "analysis_dimension"],
            0.78,
        )
    if any(token in text for token in ("need", "should", "must", "workflow", "plan")):
        add_artifact(
            "implicit_instruction",
            "The thought drop contains an instruction to transform rough material into a reliable workflow.",
            ["instruction_extraction", "workflow_routing"],
            0.76,
        )
    if any(token in text for token in ("safe", "guard", "uncertain", "rough", "reliable")):
        add_artifact(
            "uncertainty_marker",
            "The drop asks for safety and reliability, so implementation should surface assumptions before execution.",
            ["uncertainty", "guardrail"],
            0.7,
            ["Heuristic marker; later versions should use turn-level evidence."],
        )
    if any(token in text for token in ("codex", "openclaw", "hermes", "tool", "tools", "execute", "execution")):
        add_artifact(
            "tool_readiness",
            "The drop references execution tools, but readiness should remain gated by approval and task packs.",
            ["tool_readiness", "execution_gate"],
            0.72,
        )

    if not artifacts:
        add_artifact(
            "interaction_dynamic",
            "The conversation needs commentary, but no strong v1 marker was detected.",
            ["low_signal"],
            0.42,
            ["Low-signal heuristic artifact."],
        )
    return artifacts


def _build_thought_graph_payload(
    *,
    raw_idea: str,
    desired_effect: str,
    intent_kind: str,
    surface_hints: List[str],
    source_session_id: str | None,
    source_refs: List[str],
    development_signals: Dict[str, Any],
) -> Dict[str, Any]:
    graph_id = make_id("thought-graph")
    segments = _thought_segments(raw_idea, desired_effect)
    all_text = "\n".join([raw_idea, desired_effect])
    dimensions = sorted(set(_dimension_tags(all_text)))
    meta_commentary_artifacts = _build_meta_commentary_artifacts(
        graph_id=graph_id,
        raw_idea=raw_idea,
        desired_effect=desired_effect,
        source_refs=source_refs,
    )
    related_context_refs = [
        {
            "meta_id": str(row.get("meta_id", "")),
            "kind": str(row.get("kind", "")),
            "label": str(row.get("label", "")),
            "source_refs": list(row.get("source_refs", [])),
            "confidence": float(row.get("confidence", 0.0)),
        }
        for row in development_signals.get("formation_candidates", [])[:5]
        if str(row.get("meta_id", "")).strip()
    ]

    nodes: List[Dict[str, Any]] = [
        _graph_node(
            graph_id,
            "raw_drop",
            0,
            "Submitted thought drop",
            raw_idea,
            dimensions,
        )
    ]
    edges: List[Dict[str, str]] = []
    raw_node_id = nodes[0]["node_id"]

    for index, segment in enumerate(segments, start=1):
        node = _graph_node(
            graph_id,
            "micro_shift",
            index,
            segment,
            segment,
            _dimension_tags(segment),
        )
        nodes.append(node)
        edges.append(
            {
                "source_node_id": raw_node_id,
                "target_node_id": node["node_id"],
                "relation": "contains",
            }
        )

    macro_node = _graph_node(
        graph_id,
        "macro_conversation",
        0,
        "Whole conversation direction",
        desired_effect or raw_idea,
        dimensions,
    )
    workflow_node = _graph_node(
        graph_id,
        "workflow_path",
        0,
        "Owner-aware implementation path",
        f"Intent `{intent_kind}` should move from capture to routing, guard assessment, and scoped execution.",
        ["workflow_routing"],
    )
    bridge_node = _graph_node(
        graph_id,
        "bridge_orchestration",
        0,
        "Communication and tool bridge",
        "Treat the drop as incoming flow that may route to communication adaptation, product building, or expert tool execution.",
        ["bridge_orchestration", "expert_tool_orchestration"],
    )
    cross_node = _graph_node(
        graph_id,
        "cross_conversation",
        0,
        "Related conversation search",
        "Use development signals, concept matches, context bubbles, and thread abstractions to compare this drop against prior material.",
        ["conversation_analysis"],
    )
    meta_node = _graph_node(
        graph_id,
        "meta_commentary",
        0,
        "Derived conversation commentary",
        "Derived artifacts describe conversation dynamics, abstraction moves, implicit instructions, uncertainty, and tool-readiness.",
        ["conversation_analysis", "bridge_orchestration"],
    )
    nodes.extend([macro_node, workflow_node, bridge_node, cross_node, meta_node])
    edges.extend(
        [
            {
                "source_node_id": raw_node_id,
                "target_node_id": macro_node["node_id"],
                "relation": "summarizes_into",
            },
            {
                "source_node_id": macro_node["node_id"],
                "target_node_id": workflow_node["node_id"],
                "relation": "implies_workflow",
            },
            {
                "source_node_id": macro_node["node_id"],
                "target_node_id": bridge_node["node_id"],
                "relation": "implies_bridge",
            },
            {
                "source_node_id": macro_node["node_id"],
                "target_node_id": cross_node["node_id"],
                "relation": "compares_against",
            },
            {
                "source_node_id": raw_node_id,
                "target_node_id": meta_node["node_id"],
                "relation": "derives_commentary",
            },
        ]
    )

    uncertainty = []
    if not source_session_id:
        uncertainty.append("No source session id was provided.")
    if not source_refs:
        uncertainty.append("No source event references were provided.")
    if len(segments) < 2:
        uncertainty.append("The thought drop is short, so micro-shift evidence is limited.")

    return {
        "graph_id": graph_id,
        "source_session_id": source_session_id or "",
        "source_refs": source_refs,
        "size_lenses": THOUGHT_GRAPH_SIZE_LENSES,
        "surface_hints": surface_hints,
        "dimensions": dimensions,
        "nodes": nodes,
        "edges": edges,
        "meta_commentary_artifacts": meta_commentary_artifacts,
        "related_context_refs": related_context_refs,
        "workflow_path": [
            {
                "step": "capture",
                "owner_module": "assembly.development.development_intake",
                "effect": "Persist the rough idea with source refs and graph payload.",
            },
            {
                "step": "route",
                "owner_module": "assembly.development.development_router",
                "effect": "Rank existing owners and choose extend, variant, recipe, or new-module path.",
            },
            {
                "step": "guard",
                "owner_module": "builder.guard.engineering_guard",
                "effect": "Block implementation until purpose and edit surface are narrow enough.",
            },
        ],
        "uncertainty": uncertainty,
    }


def _infer_intent_kind(raw_idea: str, desired_effect: str, surface_hints: List[str]) -> str:
    lowered = " ".join([raw_idea.lower(), desired_effect.lower(), " ".join(hint.lower() for hint in surface_hints)])
    if any(token in lowered for token in ("recipe", "compose", "composition", "lens", "mix and match")):
        return "lens_composition"
    if any(token in lowered for token in ("variant", "version", "use case", "use-case")):
        return "module_variant"
    if any(token in lowered for token in ("new module", "new owner", "new subsystem")):
        return "new_module"
    if any(token in lowered for token in ("improve", "extend", "update", "refine", "feature", "module", "proposal")):
        return "module_extension"
    return "development_idea"


def _build_idea_record(
    *,
    raw_idea: str,
    desired_effect: str,
    intent_kind: str,
    surface_hints: List[str],
    source_session_id: str | None,
    source_refs: List[str],
    translated_framing: Dict[str, Any],
    development_signals: Dict[str, Any],
) -> DevelopmentIdeaRecord:
    return DevelopmentIdeaRecord(
        idea_id=make_id("idea"),
        created_at=utc_now(),
        raw_idea=raw_idea,
        desired_effect=desired_effect,
        intent_kind=intent_kind,
        surface_hints=surface_hints,
        source_session_id=source_session_id,
        source_refs=source_refs,
        translated_framing=translated_framing,
        development_signals=development_signals,
        status="recorded",
    )


def translate_development_idea(
    root: Path,
    raw_idea: str,
    desired_effect: str = "",
    surface_hints: List[str] | None = None,
    caller_hints: Dict[str, Any] | None = None,
    context_notes: List[str] | None = None,
) -> Dict[str, Any]:
    normalized_surface_hints = _normalize_string_list(surface_hints)
    framing = translate_idea_to_technical_framing(
        root,
        raw_idea,
        desired_effect=desired_effect,
        caller_hints=caller_hints,
        context_notes=context_notes,
    )
    signals = derive_development_signals(root, f"{raw_idea}\n{desired_effect}".strip())
    return {
        "translated_framing": framing,
        "development_signals": signals,
        "surface_hints": normalized_surface_hints,
    }


def record_development_idea(
    root: Path,
    raw_idea: str,
    desired_effect: str = "",
    intent_kind: str = "",
    surface_hints: List[str] | None = None,
    source_session_id: str | None = None,
    source_refs: List[str] | None = None,
    caller_hints: Dict[str, Any] | None = None,
    context_notes: List[str] | None = None,
) -> Dict[str, Any]:
    normalized_raw_idea = str(raw_idea or "").strip()
    if not normalized_raw_idea:
        raise ValueError("raw_idea is required")

    normalized_surface_hints = _normalize_string_list(surface_hints)
    normalized_source_refs = _normalize_string_list(source_refs)
    translation_payload = translate_development_idea(
        root,
        normalized_raw_idea,
        desired_effect=desired_effect,
        surface_hints=normalized_surface_hints,
        caller_hints=caller_hints,
        context_notes=context_notes,
    )
    resolved_intent_kind = str(intent_kind or "").strip() or _infer_intent_kind(
        normalized_raw_idea,
        desired_effect,
        normalized_surface_hints,
    )
    record = _build_idea_record(
        raw_idea=normalized_raw_idea,
        desired_effect=str(desired_effect or "").strip(),
        intent_kind=resolved_intent_kind,
        surface_hints=normalized_surface_hints,
        source_session_id=source_session_id,
        source_refs=normalized_source_refs,
        translated_framing=translation_payload["translated_framing"],
        development_signals=translation_payload["development_signals"],
    )
    record_payload = record.to_dict()
    record_payload["thought_graph"] = _build_thought_graph_payload(
        raw_idea=record.raw_idea,
        desired_effect=record.desired_effect,
        intent_kind=record.intent_kind,
        surface_hints=record.surface_hints,
        source_session_id=record.source_session_id,
        source_refs=record.source_refs,
        development_signals=translation_payload["development_signals"],
    )
    ensure_dir(_data_dir(root))
    append_jsonl(_ideas_path(root), record_payload)

    from .element_ingest import ingest_to_element_space

    thought_graph = dict(record_payload.get("thought_graph", {}) or {})
    record_payload["element_ingest"] = ingest_to_element_space(
        root,
        raw_text="\n".join(part for part in [normalized_raw_idea, str(desired_effect or "").strip()] if part),
        source_kind="development_idea",
        source_ref=f"development_layer_v1/data/ideas.jsonl#{record_payload.get('idea_id', '')}",
        session_id=str(source_session_id or ""),
        surface_hints=normalized_surface_hints,
        caller_hints=dict(caller_hints or {}),
        development_dimensions=list(thought_graph.get("dimensions", []) or []),
    )
    return record_payload


def _coerce_idea_payload(root: Path, payload: Dict[str, Any] | str) -> Dict[str, Any]:
    if isinstance(payload, str):
        idea = get_development_idea(root, payload)
        if idea is None:
            raise FileNotFoundError(f"Development idea not found: {payload}")
        return idea
    return dict(payload)


def _route_payload(root: Path, idea: Dict[str, Any], route_payload: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if route_payload is not None:
        return dict(route_payload)
    from .development_router import route_development_idea

    return route_development_idea(root, idea)


def _summarize_development_idea(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "idea_id": str(row.get("idea_id", "")),
        "created_at": str(row.get("created_at", "")),
        "intent_kind": str(row.get("intent_kind", "")),
        "status": str(row.get("status", "")),
        "surface_hints": _normalize_string_list(row.get("surface_hints")),
        "idea_preview": _preview_text(row.get("raw_idea")),
        "desired_effect_preview": _preview_text(row.get("desired_effect")),
    }


def _summarize_development_proposal(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "proposal_id": str(row.get("proposal_id", "")),
        "idea_id": str(row.get("idea_id", "")),
        "created_at": str(row.get("created_at", "")),
        "route_kind": str(row.get("route_kind", "")),
        "approval_status": str(row.get("approval_status", "")),
        "target_surface_family": str(row.get("target_surface_family", "")),
        "target_module_ids": _normalize_string_list(row.get("target_module_ids")),
        "confidence": float(row.get("confidence", 0.0)),
    }


def _write_proposals(root: Path, rows: List[Dict[str, Any]]) -> None:
    ensure_dir(_data_dir(root))
    write_jsonl(_proposals_path(root), rows)


def _write_proposal_review(root: Path, payload: Dict[str, Any]) -> None:
    ensure_dir(_data_dir(root))
    append_jsonl(_proposal_reviews_path(root), payload)


def _thought_graph_summary(idea: Dict[str, Any]) -> Dict[str, Any]:
    thought_graph = dict(idea.get("thought_graph") or {})
    return {
        "graph_id": str(thought_graph.get("graph_id", "")),
        "dimensions": list(thought_graph.get("dimensions", [])),
        "lens_keys": [
            str(lens.get("lens_key", ""))
            for lens in thought_graph.get("size_lenses", [])
            if str(lens.get("lens_key", ""))
        ],
        "uncertainty": list(thought_graph.get("uncertainty", [])),
    }


def build_development_proposal(
    root: Path,
    idea_record: Dict[str, Any] | str,
    route_payload: Dict[str, Any] | None = None,
    open_questions: List[str] | None = None,
) -> Dict[str, Any]:
    idea = _coerce_idea_payload(root, idea_record)
    route = _route_payload(root, idea, route_payload)
    targets = list(route.get("candidate_targets", []))
    target_module_ids = [str(row.get("module_id", "")).strip() for row in targets if str(row.get("module_id", "")).strip()]
    rationale_lines = list(route.get("rationale", []))

    proposal = {
        "proposal_id": make_id("proposal"),
        "idea_id": str(idea.get("idea_id", "")).strip(),
        "created_at": utc_now(),
        "route_kind": str(route.get("route_kind", "extend_existing")),
        "target_module_ids": target_module_ids,
        "target_surface_family": str(route.get("target_surface_family", "")).strip(),
        "rationale": "\n".join(rationale_lines),
        "confidence": float(route.get("confidence", 0.0)),
        "version_plan": {
            "strategy": "variant_manifest" if route.get("route_kind") == "create_variant" else "existing_contract_update",
            "base_modules": target_module_ids[:3],
        },
        "recipe_plan": {
            "surface_family": str(route.get("target_surface_family", "")).strip(),
            "required": route.get("route_kind") == "update_recipe",
        },
        "scope_in": [row.get("module_id", "") for row in targets[:3]],
        "scope_out": [],
        "open_questions": _normalize_string_list(open_questions) or list(idea.get("translated_framing", {}).get("open_questions", []))[:4],
        "approval_status": "proposed",
        "thought_graph_summary": _thought_graph_summary(idea),
        "source_idea": {
            "raw_idea": str(idea.get("raw_idea", "")),
            "desired_effect": str(idea.get("desired_effect", "")),
            "intent_kind": str(idea.get("intent_kind", "")),
        },
        "route_snapshot": route,
    }
    ensure_dir(_data_dir(root))
    append_jsonl(_proposals_path(root), proposal)
    return proposal


def get_development_idea(root: Path, idea_id: str) -> Dict[str, Any] | None:
    normalized_idea_id = str(idea_id or "").strip()
    if not normalized_idea_id:
        return None
    for row in reversed(read_jsonl(_ideas_path(root))):
        if row.get("idea_id") == normalized_idea_id:
            return row
    return None


def list_development_ideas(root: Path, status: str | None = None, limit: int = 50) -> List[Dict[str, Any]]:
    rows = read_jsonl(_ideas_path(root))
    if status:
        rows = [row for row in rows if row.get("status") == status]
    rows.sort(key=lambda row: (row.get("created_at", ""), row.get("idea_id", "")), reverse=True)
    return rows[: max(1, int(limit))]


def get_development_proposal(root: Path, proposal_id: str) -> Dict[str, Any] | None:
    normalized_proposal_id = str(proposal_id or "").strip()
    if not normalized_proposal_id:
        return None
    for row in reversed(read_jsonl(_proposals_path(root))):
        if row.get("proposal_id") == normalized_proposal_id:
            return row
    return None


def list_development_proposals(root: Path, approval_status: str | None = None, limit: int = 50) -> List[Dict[str, Any]]:
    rows = read_jsonl(_proposals_path(root))
    if approval_status:
        rows = [row for row in rows if row.get("approval_status") == approval_status]
    rows.sort(key=lambda row: (row.get("created_at", ""), row.get("proposal_id", "")), reverse=True)
    return rows[: max(1, int(limit))]


def approve_development_proposal(
    root: Path,
    proposal_id: str,
    decision: str,
    reviewer: str = "user",
    notes: str = "",
) -> Dict[str, Any]:
    normalized_proposal_id = str(proposal_id or "").strip()
    normalized_decision = str(decision or "").strip().lower()
    if normalized_decision not in {"approved", "rejected"}:
        raise ValueError("decision must be `approved` or `rejected`")

    rows = read_jsonl(_proposals_path(root))
    updated: Dict[str, Any] | None = None
    for row in rows:
        if row.get("proposal_id") != normalized_proposal_id:
            continue
        row["approval_status"] = normalized_decision
        row["reviewed_at"] = utc_now()
        row["reviewer"] = reviewer
        if notes.strip():
            row["review_notes"] = notes.strip()
        updated = row
        break
    if updated is None:
        raise FileNotFoundError(f"Development proposal not found: {proposal_id}")

    _write_proposals(root, rows)
    review_event = {
        "proposal_id": normalized_proposal_id,
        "reviewed_at": updated["reviewed_at"],
        "reviewer": reviewer,
        "decision": normalized_decision,
        "notes": notes.strip(),
    }
    _write_proposal_review(root, review_event)
    return updated


def build_proposal_task_pack(
    root: Path,
    proposal_id: str,
    task_type: str = "implementation",
    constraints: List[str] | None = None,
) -> Dict[str, Any]:
    proposal = get_development_proposal(root, proposal_id)
    if proposal is None:
        raise FileNotFoundError(f"Development proposal not found: {proposal_id}")
    if proposal.get("approval_status") != "approved":
        raise ValueError("Development proposal must be approved before building a task pack")

    source_idea = dict(proposal.get("source_idea", {}))
    request = str(source_idea.get("desired_effect") or source_idea.get("raw_idea") or proposal_id).strip()
    domains = ["development_layer"]
    surface_family = str(proposal.get("target_surface_family", "")).strip()
    if surface_family:
        domains.append(surface_family)
    refresh_codebase_overview(root)
    pack = build_task_pack(
        root=root,
        task_id=proposal_id,
        request=request,
        task_type=task_type,
        domain_overlays=domains,
        constraints=_normalize_string_list(constraints) + [f"proposal_id:{proposal_id}"],
    )

    rows = read_jsonl(_proposals_path(root))
    for row in rows:
        if row.get("proposal_id") != proposal_id:
            continue
        row["task_pack_ref"] = {
            "task_id": proposal_id,
            "json_path": str(root / "context" / "task_packs" / f"{proposal_id}.json"),
            "markdown_path": str(root / "context" / "task_packs" / f"{proposal_id}.md"),
        }
        break
    _write_proposals(root, rows)
    return {
        "proposal_id": proposal_id,
        "task_pack": pack,
        "task_pack_ref": {
            "task_id": proposal_id,
            "json_path": str(root / "context" / "task_packs" / f"{proposal_id}.json"),
            "markdown_path": str(root / "context" / "task_packs" / f"{proposal_id}.md"),
        },
    }
