from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from .analysis import refresh_indexes
from .meta_layer import load_meta_records
from .models import MemoryCard
from .routing import build_task_pack, enrich_task_pack_with_workspace
from .storage import (
    append_jsonl,
    cards_dir,
    ensure_dir,
    make_id,
    read_json,
    read_jsonl,
    session_dir,
    slugify,
    task_packs_dir,
    utc_now,
    workspace_artifact_links_path as _workspace_artifact_links_path,
    workspace_context_dir as _workspace_context_dir,
    workspace_dir as _workspace_dir,
    workspace_events_path as _workspace_events_path,
    workspace_exists as _workspace_exists,
    workspace_ids as _workspace_ids,
    workspace_knowledge_records_path as _workspace_knowledge_records_path,
    workspace_manifest_path as _workspace_manifest_path,
    workspace_materialized_paths as _workspace_materialized_paths,
    workspace_promotions_path as _workspace_promotions_path,
    workspace_source_paths as _workspace_source_paths,
    workspace_test_cases_path as _workspace_test_cases_path,
    workspace_test_runs_path as _workspace_test_runs_path,
    workspace_work_item_events_path as _workspace_work_item_events_path,
    write_json,
    write_markdown,
)
from .cli import _split_csv, _split_many
from .vault_ingest import tokenize

MODULE_ID = "builder.holodeck.holodeck"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "_collect_constraint_violations",
    "_collect_run_drift_warnings",
    "_collect_completed_run_drift_warnings",
    "holodeck_create",
    "holodeck_event",
    "holodeck_log_context",
    "holodeck_log_command",
    "holodeck_ingest_artifact",
    "holodeck_link_session",
    "holodeck_update",
    "holodeck_advance_stage",
    "holodeck_add_work_item",
    "holodeck_update_work_item",
    "holodeck_add_test",
    "holodeck_record_test_run",
    "holodeck_start_run",
    "holodeck_finish_run",
    "holodeck_add_context",
    "holodeck_update_context",
    "holodeck_add_constraint",
    "holodeck_update_constraint",
    "holodeck_add_integration_target",
    "holodeck_update_integration_target",
    "holodeck_add_knowledge",
    "holodeck_update_knowledge",
    "holodeck_promote",
    "holodeck_update_promotion",
    "holodeck_apply_promotion",
    "holodeck_artifacts",
    "holodeck_contextualize",
    "holodeck_list",
    "holodeck_pause",
    "holodeck_block",
    "holodeck_close",
    "holodeck_reopen",
    "holodeck_archive",
    "holodeck_materialize",
    "holodeck_status",
    "holodeck_check",
    "holodeck_task_pack",
)
__all__ = list(PUBLIC_API)

HOLODECK_MATURATION_STAGES = {
    "raw",
    "contextualizing",
    "scoping",
    "developing",
    "verifying",
    "integrating",
    "complete",
    "abandoned",
}

HOLODECK_RUN_ACTIVE_STATUSES = {"planned", "active", "blocked"}

HOLODECK_RUN_TERMINAL_STATUSES = {"completed", "stopped", "blocked", "abandoned"}
HOLODECK_AUTO_CONTEXTUALIZATION_STAGES = {"raw", "contextualizing", "scoping"}

HOLODECK_PROOF_SURFACE_ORDER = {
    "local_code": 1,
    "local_cli": 2,
    "local_http": 3,
    "deployed_service": 4,
    "external_client": 5,
    "user_validated": 6,
}

HOLODECK_CONTEXTUALIZATION_STOPWORDS = {
    "about",
    "across",
    "after",
    "agent",
    "allow",
    "allows",
    "also",
    "auto",
    "automatic",
    "before",
    "between",
    "build",
    "built",
    "clear",
    "clearly",
    "context",
    "develop",
    "enough",
    "feature",
    "goal",
    "good",
    "ground",
    "inherited",
    "idea",
    "implement",
    "implementation",
    "inside",
    "into",
    "local",
    "need",
    "novelty",
    "outcome",
    "outcomes",
    "project",
    "record",
    "records",
    "relevant",
    "scope",
    "should",
    "static",
    "strong",
    "still",
    "system",
    "their",
    "there",
    "these",
    "this",
    "through",
    "typed",
    "using",
    "validate",
    "work",
    "workspace",
}

def _workspace_context_records_path(root: Path, workspace_id: str) -> Path:
    return _workspace_dir(root, workspace_id) / "context_records.jsonl"

def _workspace_constraint_records_path(root: Path, workspace_id: str) -> Path:
    return _workspace_dir(root, workspace_id) / "constraint_records.jsonl"

def _workspace_integration_targets_path(root: Path, workspace_id: str) -> Path:
    return _workspace_dir(root, workspace_id) / "integration_targets.jsonl"

def _workspace_run_contracts_path(root: Path, workspace_id: str) -> Path:
    return _workspace_dir(root, workspace_id) / "run_contracts.jsonl"

def _workspace_contextualization_runs_path(root: Path, workspace_id: str) -> Path:
    return _workspace_dir(root, workspace_id) / "contextualization_runs.jsonl"

def _workspace_contextualization_candidates_path(root: Path, workspace_id: str) -> Path:
    return _workspace_dir(root, workspace_id) / "contextualization_candidates.jsonl"

def _load_workspace_manifest(root: Path, workspace_id: str) -> dict:
    manifest = read_json(_workspace_manifest_path(root, workspace_id), default=None)
    if manifest is None:
        raise FileNotFoundError(f"Workspace not found: {workspace_id}")
    return manifest


def _proof_surface_rank(surface: str) -> int:
    return HOLODECK_PROOF_SURFACE_ORDER.get(str(surface or "").strip(), 999)


def _tag_value(tags: list[str], prefix: str) -> str:
    needle = f"{prefix}:"
    for tag in tags:
        if tag.startswith(needle):
            return tag[len(needle) :].strip()
    return ""


def _proof_records_from_events(events: list[dict]) -> list[dict]:
    records: list[dict] = []
    for event in events:
        tags = list(event.get("tags", []))
        surface = _tag_value(tags, "surface")
        if event.get("kind") != "proof_recorded" and not surface:
            continue
        if not surface:
            continue
        records.append(
            {
                "proof_id": event.get("event_id", ""),
                "surface": surface,
                "status": _tag_value(tags, "status") or "verified",
                "summary": event.get("summary", ""),
                "notes": event.get("content", ""),
                "source_refs": list(event.get("source_refs", [])),
                "timestamp": event.get("timestamp", ""),
                "actor": event.get("actor", "agent"),
            }
        )
    records.sort(key=lambda item: (item.get("timestamp", ""), item.get("proof_id", "")))
    return records


def _proof_summary(snapshot: dict, events: list[dict], constraint_records: list[dict]) -> dict:
    required_surfaces = sorted(
        {
            item.get("applies_to", "").strip()
            for item in constraint_records
            if item.get("status", "active") == "active"
            and item.get("constraint_kind") == "proof_requirement"
            and item.get("applies_to", "").strip()
        },
        key=_proof_surface_rank,
    )
    proof_records = _proof_records_from_events(events)
    latest_by_surface: dict[str, dict] = {}
    for item in proof_records:
        latest_by_surface[item["surface"]] = item
    verified_surfaces = sorted(
        [surface for surface, item in latest_by_surface.items() if item.get("status") == "verified"],
        key=_proof_surface_rank,
    )
    failed_surfaces = sorted(
        [surface for surface, item in latest_by_surface.items() if item.get("status") == "failed"],
        key=_proof_surface_rank,
    )
    pending_surfaces = sorted(
        [surface for surface, item in latest_by_surface.items() if item.get("status") == "pending"],
        key=_proof_surface_rank,
    )
    unverified_required_surfaces = [surface for surface in required_surfaces if surface not in verified_surfaces]
    highest_verified_surface = verified_surfaces[-1] if verified_surfaces else ""
    highest_verified_rank = _proof_surface_rank(highest_verified_surface) if highest_verified_surface else 0
    if not verified_surfaces:
        proof_posture = "unproven"
    elif highest_verified_rank <= _proof_surface_rank("local_http"):
        proof_posture = "local_only"
    else:
        proof_posture = "target_surface_verified"
    return {
        "required_surfaces": required_surfaces,
        "verified_surfaces": verified_surfaces,
        "failed_surfaces": failed_surfaces,
        "pending_surfaces": pending_surfaces,
        "unverified_required_surfaces": unverified_required_surfaces,
        "highest_verified_surface": highest_verified_surface or None,
        "proof_posture": proof_posture,
        "proof_records": proof_records,
    }


def _contextualization_summary(context_records: list[dict], events: list[dict]) -> dict:
    active_context_records = [item for item in context_records if item.get("status", "active") == "active"]
    if active_context_records:
        return {
            "status": "inherited",
            "resolved": True,
            "anchor_count": len(active_context_records),
            "latest_outcome": None,
            "message": f"{len(active_context_records)} active context anchor(s) ground this workspace.",
        }

    latest_outcome = None
    for event in sorted(events, key=lambda item: (item.get("timestamp", ""), item.get("event_id", ""))):
        if event.get("kind") != "contextualization_outcome_recorded":
            continue
        latest_outcome = {
            "event_id": event.get("event_id", ""),
            "outcome": _tag_value(list(event.get("tags", [])), "outcome").strip().lower() or "unresolved",
            "summary": event.get("summary", ""),
            "notes": event.get("content", ""),
            "timestamp": event.get("timestamp", ""),
        }
    if latest_outcome is None:
        return {
            "status": "unresolved",
            "resolved": False,
            "anchor_count": 0,
            "latest_outcome": None,
            "message": "No contextualization outcome has been recorded yet.",
        }

    status = latest_outcome.get("outcome", "unresolved")
    resolved = status in {"inherited", "novel"}
    message_map = {
        "novel": "Bounded retrieval found no strong inherited anchors and the workspace is treated as novel.",
        "inherited": "A contextualization run reported inherited grounding without retained local anchors.",
        "insufficient": "Contextualization did not yet have enough signal to resolve inherited context versus novelty.",
    }
    return {
        "status": status,
        "resolved": resolved,
        "anchor_count": 0,
        "latest_outcome": latest_outcome,
        "message": message_map.get(status, latest_outcome.get("summary", "") or "Contextualization outcome recorded."),
    }


def _normalized_context_terms(value: str) -> list[str]:
    terms = []
    for token in tokenize(value or ""):
        normalized = token.strip().lower()
        if len(normalized) < 4 or normalized in HOLODECK_CONTEXTUALIZATION_STOPWORDS:
            continue
        terms.append(normalized)
    return terms


def _merge_terms(*groups: list[str], limit: int = 16) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for group in groups:
        for term in group:
            if term in seen:
                continue
            seen.add(term)
            merged.append(term)
            if len(merged) >= limit:
                return merged
    return merged


def _linked_session_seed_terms(root: Path, manifest: dict) -> list[str]:
    session_terms: list[list[str]] = []
    for session_id in manifest.get("linked_session_ids", []):
        manifest_path = session_dir(root, session_id) / "manifest.json"
        if not manifest_path.exists():
            continue
        session_manifest = read_json(manifest_path)
        session_terms.append(
            _normalized_context_terms(
                " ".join(
                    [
                        session_manifest.get("title", ""),
                        session_manifest.get("summary", ""),
                        session_manifest.get("status", ""),
                    ]
                )
            )
        )
    return _merge_terms(*session_terms, limit=12)


def _knowledge_seed_terms(root: Path, workspace_id: str) -> list[str]:
    rows = _reduce_knowledge_records(read_jsonl(_workspace_knowledge_records_path(root, workspace_id)))
    relevant_rows = [
        item
        for item in rows
        if item.get("status", "active") == "active" and item.get("record_kind") in {"requirement", "open_question"}
    ]
    return _merge_terms(
        *[
            _normalized_context_terms(" ".join([item.get("title", ""), item.get("statement", "")]))
            for item in relevant_rows
        ],
        limit=12,
    )


def _seed_bundle(root: Path, workspace_id: str, manifest: dict, artifacts: list[dict], work_items: list[dict]) -> dict:
    title_terms = _normalized_context_terms(manifest.get("label", ""))
    goal_terms = _normalized_context_terms(manifest.get("goal", ""))
    purpose_terms = _normalized_context_terms(manifest.get("purpose", ""))
    success_terms = _normalized_context_terms(manifest.get("success_condition", ""))
    founder_terms = _merge_terms(
        *[_normalized_context_terms(str(value)) for value in manifest.get("template_fields", {}).values() if value],
        limit=12,
    )
    session_terms = _linked_session_seed_terms(root, manifest)
    scope_terms = _merge_terms(
        *[_normalized_context_terms(value) for value in manifest.get("scope_in", []) + manifest.get("scope_out", [])],
        limit=12,
    )
    artifact_terms = _merge_terms(
        *[
            _normalized_context_terms(" ".join([item.get("title", ""), item.get("summary", ""), item.get("source_ref", "")]))
            for item in artifacts
        ],
        limit=12,
    )
    work_item_terms = _merge_terms(
        *[
            _normalized_context_terms(
                " ".join(
                    [
                        item.get("title", ""),
                        " ".join(item.get("acceptance_criteria", [])),
                        " ".join(item.get("constraints", [])),
                    ]
                )
            )
            for item in work_items
        ],
        limit=12,
    )
    knowledge_terms = _knowledge_seed_terms(root, workspace_id)
    owner_module_terms = _merge_terms(
        *[
            _normalized_context_terms(Path(item.get("source_ref", "")).stem.replace("-", " "))
            for item in artifacts
            if item.get("source_ref", "")
        ],
        limit=8,
    )
    system_terms = [term for term in _merge_terms(title_terms, goal_terms, purpose_terms, artifact_terms, work_item_terms, session_terms, founder_terms, knowledge_terms, limit=20) if term in {
        "bridge",
        "bounded",
        "context",
        "contextualization",
        "holodeck",
        "knowledge",
        "private",
        "cognitive",
        "semantic",
        "assist",
        "thread",
        "routing",
        "proof",
        "integration",
    }]
    domain_terms = _merge_terms(_normalized_context_terms(" ".join(manifest.get("domain_overlays", []))), owner_module_terms, limit=8)
    topic_terms = _merge_terms(title_terms, goal_terms, purpose_terms, work_item_terms, session_terms, founder_terms, limit=16)
    constraint_terms = _merge_terms(scope_terms, knowledge_terms, limit=12)
    bundle = {
        "topic_terms": topic_terms,
        "domain_terms": domain_terms,
        "system_terms": system_terms,
        "artifact_terms": artifact_terms,
        "constraint_terms": constraint_terms,
        "owner_module_terms": owner_module_terms,
        "session_terms": session_terms,
        "knowledge_terms": knowledge_terms,
        "founder_terms": founder_terms,
    }
    combined = _merge_terms(
        bundle["topic_terms"],
        bundle["domain_terms"],
        bundle["system_terms"],
        bundle["artifact_terms"],
        bundle["constraint_terms"],
        bundle["owner_module_terms"],
        bundle["session_terms"],
        bundle["knowledge_terms"],
        bundle["founder_terms"],
        limit=32,
    )
    bundle["combined_terms"] = combined
    bundle["workspace_id"] = workspace_id
    bundle["seed_fingerprint"] = hashlib.sha256("::".join(combined).encode("utf-8")).hexdigest()[:16] if combined else "empty"
    return bundle


def _resolve_workspace_source_ref(root: Path, source_ref: str) -> Path | None:
    if not source_ref:
        return None
    candidate = Path(source_ref)
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    resolved = (root / source_ref).resolve()
    try:
        resolved.relative_to(root.resolve())
    except ValueError:
        return None
    return resolved if resolved.exists() else None


def _candidate_snippet(text: str, matched_terms: list[str], limit: int = 220) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    lower_terms = set(matched_terms)
    for line in lines:
        line_terms = set(_normalized_context_terms(line))
        if line_terms & lower_terms:
            return line[:limit]
    joined = " ".join(lines)
    return joined[:limit]


def _doc_heading(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip()
    return path.stem.replace("-", " ").replace("_", " ").strip().title()


def _score_matched_terms(text_terms: set[str], seed_terms: list[str], *, layer_priority: int) -> tuple[int, list[str]]:
    matched = sorted(set(seed_terms) & text_terms)
    if len(matched) < 3:
        return 0, []
    score = len(matched) * 10 + layer_priority * 3
    return score, matched


def _collect_workspace_projection_candidates(
    root: Path,
    seed_terms: list[str],
    artifacts: list[dict],
    *,
    max_source_refs: int,
) -> tuple[list[dict], list[str]]:
    candidates: list[dict] = []
    consulted_layers: list[str] = []
    seen_source_refs: set[str] = set()

    def append_candidate(candidate: dict) -> None:
        source_ref = candidate.get("source_ref", "")
        if source_ref in seen_source_refs:
            return
        seen_source_refs.add(source_ref)
        candidates.append(candidate)

    product_thesis_path = root / "PRODUCT_THESIS.md"
    if product_thesis_path.exists():
        consulted_layers.append("product_thesis")
        text = product_thesis_path.read_text(encoding="utf-8")
        score, matched = _score_matched_terms(set(_normalized_context_terms(text)), seed_terms, layer_priority=5)
        if matched:
            append_candidate(
                {
                    "candidate_kind": "context",
                    "source_layer": "product_thesis",
                    "source_ref": "PRODUCT_THESIS.md",
                    "title": _doc_heading(product_thesis_path),
                    "statement": _candidate_snippet(text, matched),
                    "matched_terms": matched,
                    "score": score,
                    "confidence": min(0.96, 0.55 + len(matched) * 0.06),
                }
            )

    consulted_layers.append("artifact_docs")
    for artifact in artifacts:
        path = _resolve_workspace_source_ref(root, artifact.get("source_ref", ""))
        if path is None or not path.is_file() or path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8")
        score, matched = _score_matched_terms(set(_normalized_context_terms(text)), seed_terms, layer_priority=4)
        if matched:
            append_candidate(
                {
                    "candidate_kind": "context",
                    "source_layer": "artifact_doc",
                    "source_ref": artifact.get("source_ref", str(path.relative_to(root))),
                    "title": artifact.get("title", "") or _doc_heading(path),
                    "statement": _candidate_snippet(text, matched),
                    "matched_terms": matched,
                    "score": score,
                    "confidence": min(0.94, 0.52 + len(matched) * 0.06),
                    "linked_artifact_id": artifact.get("artifact_id", ""),
                }
            )

    consulted_layers.append("plan_docs")
    for path in sorted((root / "docs" / "plans").glob("*.md"))[:max_source_refs]:
        text = path.read_text(encoding="utf-8")
        score, matched = _score_matched_terms(set(_normalized_context_terms(text)), seed_terms, layer_priority=3)
        if matched:
            append_candidate(
                {
                    "candidate_kind": "context",
                    "source_layer": "plan_doc",
                    "source_ref": str(path.relative_to(root)),
                    "title": _doc_heading(path),
                    "statement": _candidate_snippet(text, matched),
                    "matched_terms": matched,
                    "score": score,
                    "confidence": min(0.9, 0.5 + len(matched) * 0.05),
                }
            )

    return candidates, consulted_layers


def _collect_legacy_meta_layer_candidates(root: Path, seed_terms: list[str]) -> tuple[list[dict], list[str]]:
    """Legacy Holodeck term-matching scorer; isolated when disclosure_service_v1 is enabled."""
    candidates: list[dict] = []
    consulted_layers = ["meta_layer"]
    for row in load_meta_records(root, kinds=["guardrail", "direction", "shared_primitive", "question"]):
        text = " ".join([row.get("label", ""), row.get("summary", "")])
        score, matched = _score_matched_terms(set(_normalized_context_terms(text)), seed_terms, layer_priority=4)
        if matched:
            candidates.append(
                {
                    "candidate_kind": "knowledge",
                    "source_layer": f"meta_{row.get('kind', 'meta')}",
                    "source_ref": ",".join(row.get("source_refs", [])) or row.get("meta_id", ""),
                    "title": row.get("label", row.get("meta_id", "")),
                    "statement": row.get("summary", ""),
                    "matched_terms": matched,
                    "score": score,
                    "confidence": min(0.93, float(row.get("confidence", 0.6))),
                    "meta_kind": row.get("kind", ""),
                }
            )
    return candidates, consulted_layers


def _collect_contextualization_candidates(root: Path, workspace_id: str, seed_bundle: dict, artifacts: list[dict], max_source_refs: int) -> tuple[list[dict], list[str]]:
    seed_terms = list(seed_bundle.get("combined_terms", []))
    candidates, consulted_layers = _collect_workspace_projection_candidates(
        root,
        seed_terms,
        artifacts,
        max_source_refs=max_source_refs,
    )

    try:
        from .holodeck_disclosure_adapter import (
            collect_disclosure_knowledge_candidates,
            holodeck_disclosure_service_enabled,
        )

        disclosure_enabled = holodeck_disclosure_service_enabled(root)
    except Exception:
        disclosure_enabled = False

    if disclosure_enabled:
        knowledge_candidates, knowledge_layers = collect_disclosure_knowledge_candidates(
            root,
            seed_bundle,
            max_source_refs=max_source_refs,
        )
    else:
        knowledge_candidates, knowledge_layers = _collect_legacy_meta_layer_candidates(root, seed_terms)

    candidates.extend(knowledge_candidates)
    consulted_layers.extend(knowledge_layers)
    candidates.sort(key=lambda item: (-item.get("score", 0), -float(item.get("confidence", 0)), item.get("title", "")))
    return candidates[: max_source_refs * 4], consulted_layers


def _context_candidate_kind(candidate: dict) -> str:
    title = f"{candidate.get('title', '')} {candidate.get('statement', '')}".lower()
    if candidate.get("source_layer") == "product_thesis" or "private cognitive layer" in title:
        return "philosophy_context"
    if any(token in title for token in ["holodeck", "thread", "context bubble", "knowledge", "bounded semantic assist", "semantic assist"]):
        return "existing_system"
    return "adjacent_project_context"


def _knowledge_candidate_kind(candidate: dict) -> str:
    source_layer = candidate.get("source_layer", "")
    if source_layer == "meta_guardrail":
        return "constraint"
    if source_layer == "meta_direction":
        return "decision"
    if source_layer == "meta_question":
        return "open_question"
    return "insight"


def _semantic_label(value: str) -> str:
    label = " ".join((value or "").replace("_", " ").replace("-", " ").split()).strip()
    if not label:
        return ""
    parts = label.split()
    if len(parts) > 3 and all(item.isdigit() for item in parts[:3]):
        label = " ".join(parts[3:])
    return label[:120]


def _semantic_duplicate_key(candidate: dict) -> tuple[str, str, str]:
    return (
        candidate.get("candidate_kind", ""),
        _semantic_label(candidate.get("title", "")).lower(),
        " ".join(_normalized_context_terms(candidate.get("statement", ""))[:8]),
    )


def _semantic_why_it_matters(candidate: dict) -> str:
    matched_terms = list(candidate.get("matched_terms", []))[:3]
    source_layer = candidate.get("source_layer", "candidate").replace("_", " ")
    if matched_terms:
        return f"Reinforces {', '.join(matched_terms)} from {source_layer}."
    return f"Provides contextual reinforcement from {source_layer}."


def _apply_semantic_assist(candidates: list[dict]) -> tuple[list[dict], bool]:
    if not candidates:
        return [], False
    grouped: dict[tuple[str, str, str], list[dict]] = {}
    for candidate in candidates:
        grouped.setdefault(_semantic_duplicate_key(candidate), []).append(candidate)
    assisted: list[dict] = []
    used = False
    for group in grouped.values():
        primary = dict(group[0])
        primary["semantic_label"] = _semantic_label(primary.get("title", "")) or primary.get("title", "")
        primary["why_it_matters"] = _semantic_why_it_matters(primary)
        primary["semantic_group_size"] = len(group)
        primary["semantic_source_refs"] = list(dict.fromkeys([item.get("source_ref", "") for item in group if item.get("source_ref")]))
        if len(group) > 1:
            used = True
            primary["matched_terms"] = sorted({term for item in group for term in item.get("matched_terms", [])})
            primary["score"] = max(item.get("score", 0) for item in group)
            primary["confidence"] = max(float(item.get("confidence", 0.0)) for item in group)
        if primary.get("semantic_label") and primary["semantic_label"] != primary.get("title", ""):
            used = True
        assisted.append(primary)
    assisted.sort(key=lambda item: (-item.get("score", 0), -float(item.get("confidence", 0)), item.get("semantic_label", item.get("title", ""))))
    return assisted, used


def _context_dedupe_key(item: dict) -> tuple[str, str, str]:
    return (
        item.get("context_kind", "").strip().lower(),
        item.get("title", "").strip().lower(),
        ",".join(sorted(item.get("source_refs", []))),
    )


def _knowledge_dedupe_key(item: dict) -> tuple[str, str, str]:
    return (
        item.get("record_kind", "").strip().lower(),
        item.get("title", "").strip().lower(),
        item.get("statement", "").strip().lower(),
    )


def _append_contextualization_outcome_event(root: Path, workspace_id: str, *, outcome: str, summary: str, reason: str, source_refs: list[str]) -> dict:
    return _append_workspace_event(
        root,
        workspace_id,
        actor="agent",
        kind="contextualization_outcome_recorded",
        summary=summary,
        content=reason,
        source_refs=source_refs[:6],
        tags=[f"outcome:{outcome}"],
    )


def _has_contextualization_opt_out(constraint_records: list[dict]) -> bool:
    return any(
        item.get("status", "active") == "active" and item.get("constraint_kind") == "contextualization_opt_out"
        for item in constraint_records
    )


def _run_contextualization_pass(
    root: Path,
    workspace_id: str,
    *,
    mode: str,
    trigger: str,
    reason: str,
    max_source_refs: int,
    max_anchors: int,
    max_context_records: int,
    max_knowledge_records: int,
    allow_semantic_assist: bool,
    include_snapshot: bool,
) -> dict:
    manifest = _load_workspace_manifest(root, workspace_id)
    artifacts = _load_workspace_artifacts(root, workspace_id)
    work_items = _annotate_work_items(_reduce_work_items(read_jsonl(_workspace_work_item_events_path(root, workspace_id))))
    seed_bundle = _seed_bundle(root, workspace_id, manifest, artifacts, work_items)
    started_at = utc_now()
    run_id = make_id("contextualization-run")
    candidates, consulted_layers = _collect_contextualization_candidates(
        root,
        workspace_id,
        seed_bundle,
        artifacts,
        max_source_refs=max(1, int(max_source_refs)),
    )
    candidates = candidates[: max(1, int(max_anchors))]
    semantic_assist_used = False
    if allow_semantic_assist:
        candidates, semantic_assist_used = _apply_semantic_assist(candidates)
    emitted_candidates, emitted_context_ids, emitted_record_ids = _emit_contextualization_records(
        root,
        workspace_id,
        run_id=run_id,
        candidates=candidates,
        mode=mode,
        max_context_records=max(0, int(max_context_records)),
        max_knowledge_records=max(0, int(max_knowledge_records)),
    )

    outcome = "unresolved"
    outcome_summary = ""
    if mode == "apply":
        if len(seed_bundle.get("combined_terms", [])) < 2:
            outcome = "insufficient"
            outcome_summary = "Contextualization did not yet have enough seed signal."
        elif any(item.get("disposition") in {"emitted_context", "duplicate_existing", "emitted_record"} for item in emitted_candidates):
            outcome = "inherited"
            outcome_summary = "Bounded retrieval found relevant inherited static context."
        else:
            outcome = "novel"
            outcome_summary = "Bounded retrieval found no strong inherited anchors."
        _append_contextualization_outcome_event(
            root,
            workspace_id,
            outcome=outcome,
            summary=outcome_summary,
            reason=reason,
            source_refs=[item.get("source_ref", "") for item in emitted_candidates if item.get("source_ref")],
        )

    ended_at = utc_now()
    run_row = {
        "run_id": run_id,
        "workspace_id": workspace_id,
        "mode": mode,
        "trigger": trigger,
        "reason": reason,
        "seed_fingerprint": seed_bundle.get("seed_fingerprint", ""),
        "semantic_assist_used": semantic_assist_used,
        "input_summary": {
            key: value
            for key, value in seed_bundle.items()
            if key
            in {
                "topic_terms",
                "domain_terms",
                "system_terms",
                "artifact_terms",
                "constraint_terms",
                "owner_module_terms",
                "session_terms",
                "knowledge_terms",
                "founder_terms",
                "combined_terms",
            }
        },
        "source_layers_consulted": consulted_layers,
        "candidate_count": len(emitted_candidates),
        "emitted_context_ids": emitted_context_ids,
        "emitted_record_ids": emitted_record_ids,
        "status": "completed",
        "started_at": started_at,
        "ended_at": ended_at,
    }
    append_jsonl(_workspace_contextualization_runs_path(root, workspace_id), run_row)
    for index, candidate in enumerate(emitted_candidates, start=1):
        append_jsonl(
            _workspace_contextualization_candidates_path(root, workspace_id),
            {
                "candidate_id": f"candidate-{run_id.split('-')[-1]}-{index:03d}",
                "run_id": run_id,
                "workspace_id": workspace_id,
                "candidate_kind": candidate.get("candidate_kind", ""),
                "source_layer": candidate.get("source_layer", ""),
                "source_ref": candidate.get("source_ref", ""),
                "title": candidate.get("title", ""),
                "statement": candidate.get("statement", ""),
                "matched_terms": list(candidate.get("matched_terms", [])),
                "score": candidate.get("score", 0),
                "confidence": round(float(candidate.get("confidence", 0.0)), 2),
                "semantic_label": candidate.get("semantic_label", ""),
                "why_it_matters": candidate.get("why_it_matters", ""),
                "semantic_group_size": int(candidate.get("semantic_group_size", 1) or 1),
                "semantic_source_refs": list(candidate.get("semantic_source_refs", [])),
                "disposition": candidate.get("disposition", "retained"),
                "emitted_context_id": candidate.get("emitted_context_id", ""),
                "emitted_record_id": candidate.get("emitted_record_id", ""),
            },
        )
    _append_workspace_event(
        root,
        workspace_id,
        actor="agent",
        kind="contextualization_run_completed",
        summary=f"Completed contextualization run {run_id}",
        content=reason,
        source_refs=[item.get("source_ref", "") for item in emitted_candidates if item.get("source_ref")][:6],
        tags=[mode, outcome, f"trigger:{trigger}"] if mode == "apply" else [mode, f"trigger:{trigger}"],
    )
    result = {
        "workspace_id": workspace_id,
        "run_id": run_id,
        "mode": mode,
        "trigger": trigger,
        "status": "completed",
        "semantic_assist_used": semantic_assist_used,
        "seed_fingerprint": seed_bundle.get("seed_fingerprint", ""),
        "source_layers_consulted": consulted_layers,
        "candidate_count": len(emitted_candidates),
        "emitted_context_ids": emitted_context_ids,
        "emitted_record_ids": emitted_record_ids,
        "top_candidates": emitted_candidates[:10],
    }
    if include_snapshot:
        snapshot = _materialize_workspace_snapshot(root, workspace_id, write_files=False)
        result["contextualization_summary"] = snapshot.get("contextualization_summary", {})
    return result


def _maybe_auto_contextualize(root: Path, workspace_id: str, *, trigger: str, reason: str) -> dict:
    manifest = _load_workspace_manifest(root, workspace_id)
    if manifest.get("status", "active") != "active":
        return {"triggered": False, "trigger": trigger, "reason": "workspace_inactive"}
    if manifest.get("maturation_stage", "raw") not in HOLODECK_AUTO_CONTEXTUALIZATION_STAGES:
        return {"triggered": False, "trigger": trigger, "reason": "stage_not_eligible"}

    artifacts = _load_workspace_artifacts(root, workspace_id)
    work_items = _annotate_work_items(_reduce_work_items(read_jsonl(_workspace_work_item_events_path(root, workspace_id))))
    events = read_jsonl(_workspace_events_path(root, workspace_id))
    context_records = [
        item
        for item in _reduce_context_records(read_jsonl(_workspace_context_records_path(root, workspace_id)))
        if item.get("status", "active") == "active"
    ]
    constraint_records = [
        item
        for item in _reduce_constraint_records(read_jsonl(_workspace_constraint_records_path(root, workspace_id)))
        if item.get("status", "active") == "active"
    ]
    if _has_contextualization_opt_out(constraint_records):
        return {"triggered": False, "trigger": trigger, "reason": "opted_out"}

    summary, latest_run, _, seed_bundle = _contextualization_state(
        root,
        workspace_id,
        manifest=manifest,
        artifacts=artifacts,
        work_items=work_items,
        context_records=context_records,
        events=events,
    )
    if len(seed_bundle.get("combined_terms", [])) < 3:
        return {"triggered": False, "trigger": trigger, "reason": "insufficient_seed", "seed_fingerprint": seed_bundle.get("seed_fingerprint", "")}
    if latest_run and not summary.get("stale"):
        return {
            "triggered": False,
            "trigger": trigger,
            "reason": "already_fresh",
            "run_id": latest_run.get("run_id", ""),
            "seed_fingerprint": seed_bundle.get("seed_fingerprint", ""),
        }
    result = _run_contextualization_pass(
        root,
        workspace_id,
        mode="apply",
        trigger=trigger,
        reason=reason,
        max_source_refs=4,
        max_anchors=4,
        max_context_records=2,
        max_knowledge_records=2,
        allow_semantic_assist=False,
        include_snapshot=False,
    )
    return {"triggered": True, **result}


def _latest_contextualization_run(rows: list[dict]) -> dict | None:
    latest = None
    for row in rows:
        if row.get("run_id"):
            latest = row
    return latest


def _contextualization_state(
    root: Path,
    workspace_id: str,
    *,
    manifest: dict,
    artifacts: list[dict],
    work_items: list[dict],
    context_records: list[dict],
    events: list[dict],
) -> tuple[dict, dict | None, list[dict], dict]:
    summary = _contextualization_summary(context_records, events)
    latest_outcome = None
    for event in sorted(events, key=lambda item: (item.get("timestamp", ""), item.get("event_id", ""))):
        if event.get("kind") != "contextualization_outcome_recorded":
            continue
        latest_outcome = {
            "event_id": event.get("event_id", ""),
            "outcome": _tag_value(list(event.get("tags", [])), "outcome").strip().lower() or "unresolved",
            "summary": event.get("summary", ""),
            "notes": event.get("content", ""),
            "timestamp": event.get("timestamp", ""),
        }
    runs = read_jsonl(_workspace_contextualization_runs_path(root, workspace_id))
    latest_run = _latest_contextualization_run(runs)
    candidates = read_jsonl(_workspace_contextualization_candidates_path(root, workspace_id))
    latest_candidates = []
    if latest_run is not None:
        latest_candidates = [
            item
            for item in candidates
            if item.get("run_id") == latest_run.get("run_id", "")
        ]
        latest_candidates.sort(key=lambda item: (-float(item.get("score", 0) or 0), item.get("candidate_id", "")))
    seed_bundle = _seed_bundle(root, workspace_id, manifest, artifacts, work_items)
    current_seed_fingerprint = seed_bundle.get("seed_fingerprint", "")
    stale = bool(
        latest_run
        and latest_run.get("seed_fingerprint", "")
        and latest_run.get("seed_fingerprint", "") != current_seed_fingerprint
    )
    fresh = bool(latest_run) and not stale
    enriched = {
        **summary,
        "has_run": latest_run is not None,
        "stale": stale,
        "fresh": fresh,
        "seed_fingerprint": current_seed_fingerprint,
        "latest_run_id": latest_run.get("run_id") if latest_run else None,
        "latest_candidate_count": len(latest_candidates),
        "source_layers_consulted": list(latest_run.get("source_layers_consulted", [])) if latest_run else [],
    }
    if latest_outcome is not None:
        enriched["latest_outcome"] = latest_outcome
        if latest_outcome.get("summary"):
            enriched["message"] = latest_outcome["summary"]
    return enriched, latest_run, latest_candidates[:10], seed_bundle


def _emit_contextualization_records(
    root: Path,
    workspace_id: str,
    *,
    run_id: str,
    candidates: list[dict],
    mode: str,
    max_context_records: int,
    max_knowledge_records: int,
) -> tuple[list[dict], list[str], list[str]]:
    emitted_candidates: list[dict] = []
    emitted_context_ids: list[str] = []
    emitted_record_ids: list[str] = []
    existing_contexts = _reduce_context_records(read_jsonl(_workspace_context_records_path(root, workspace_id)))
    existing_context_keys = {_context_dedupe_key(item) for item in existing_contexts if item.get("status", "active") == "active"}
    existing_knowledge = _reduce_knowledge_records(read_jsonl(_workspace_knowledge_records_path(root, workspace_id)))
    existing_knowledge_keys = {_knowledge_dedupe_key(item) for item in existing_knowledge if item.get("status", "active") == "active"}

    context_budget = max_context_records
    knowledge_budget = max_knowledge_records
    for candidate in candidates:
        candidate_row = dict(candidate)
        candidate_row["run_id"] = run_id
        candidate_row["disposition"] = "retained"
        candidate_row["emitted_context_id"] = ""
        candidate_row["emitted_record_id"] = ""

        if mode == "suggest":
            candidate_row["disposition"] = "suggested"
            emitted_candidates.append(candidate_row)
            continue

        if candidate.get("candidate_kind") == "context" and context_budget > 0:
            source_refs = list(candidate.get("semantic_source_refs", [])) or ([candidate.get("source_ref", "")] if candidate.get("source_ref") else [])
            payload = {
                "context_kind": _context_candidate_kind(candidate),
                "title": candidate.get("semantic_label", "") or candidate.get("title", ""),
                "summary": candidate.get("statement", ""),
                "domain": "conversation_os",
                "source_refs": source_refs,
            }
            key = _context_dedupe_key(payload)
            if key in existing_context_keys:
                candidate_row["disposition"] = "duplicate_existing"
                emitted_candidates.append(candidate_row)
                continue
            context_id = make_id("context")
            append_jsonl(
                _workspace_context_records_path(root, workspace_id),
                {
                    "operation": "create",
                    "context_id": context_id,
                    "workspace_id": workspace_id,
                    "context_kind": payload["context_kind"],
                    "title": payload["title"],
                    "summary": payload["summary"],
                    "domain": payload["domain"],
                    "status": "active",
                    "confidence": round(float(candidate.get("confidence", 0.6)), 2),
                    "source_refs": payload["source_refs"],
                    "linked_artifact_ids": [candidate.get("linked_artifact_id", "")] if candidate.get("linked_artifact_id") else [],
                    "created_at": utc_now(),
                    "updated_at": utc_now(),
                },
            )
            existing_context_keys.add(key)
            emitted_context_ids.append(context_id)
            context_budget -= 1
            candidate_row["disposition"] = "emitted_context"
            candidate_row["emitted_context_id"] = context_id
            emitted_candidates.append(candidate_row)
            continue

        if candidate.get("candidate_kind") == "knowledge" and knowledge_budget > 0:
            source_refs = list(candidate.get("semantic_source_refs", [])) or ([candidate.get("source_ref", "")] if candidate.get("source_ref") else [])
            payload = {
                "record_kind": _knowledge_candidate_kind(candidate),
                "title": candidate.get("semantic_label", "") or candidate.get("title", ""),
                "statement": candidate.get("statement", ""),
            }
            key = _knowledge_dedupe_key(payload)
            if key in existing_knowledge_keys:
                candidate_row["disposition"] = "duplicate_existing"
                emitted_candidates.append(candidate_row)
                continue
            record_id = make_id("knowledge")
            append_jsonl(
                _workspace_knowledge_records_path(root, workspace_id),
                {
                    "operation": "create",
                    "record_id": record_id,
                    "workspace_id": workspace_id,
                    "record_kind": payload["record_kind"],
                    "claim_posture": "inferred",
                    "title": payload["title"],
                    "statement": payload["statement"],
                    "confidence": round(float(candidate.get("confidence", 0.6)), 2),
                    "status": "active",
                    "source_refs": source_refs,
                    "related_work_item_ids": [],
                    "supersedes_record_id": "",
                    "created_at": utc_now(),
                    "updated_at": utc_now(),
                },
            )
            existing_knowledge_keys.add(key)
            emitted_record_ids.append(record_id)
            knowledge_budget -= 1
            candidate_row["disposition"] = "emitted_record"
            candidate_row["emitted_record_id"] = record_id
            emitted_candidates.append(candidate_row)
            continue

        candidate_row["disposition"] = "budget_suppressed"
        emitted_candidates.append(candidate_row)

    return emitted_candidates, emitted_context_ids, emitted_record_ids

def _append_workspace_event(
    root: Path,
    workspace_id: str,
    *,
    actor: str,
    kind: str,
    summary: str,
    content: str = "",
    source_refs: list[str] | None = None,
    related_work_item_ids: list[str] | None = None,
    related_test_ids: list[str] | None = None,
    tags: list[str] | None = None,
    context_units: int = 0,
    command_ref: str = "",
) -> dict:
    event = {
        "event_id": make_id("workspace-event"),
        "workspace_id": workspace_id,
        "timestamp": utc_now(),
        "actor": actor,
        "kind": kind,
        "summary": summary,
        "content": content,
        "source_refs": source_refs or [],
        "related_work_item_ids": related_work_item_ids or [],
        "related_test_ids": related_test_ids or [],
        "tags": tags or [],
        "context_units": context_units,
        "command_ref": command_ref,
    }
    append_jsonl(_workspace_events_path(root, workspace_id), event)
    return event

def _append_work_item_event(
    root: Path,
    workspace_id: str,
    work_item_id: str,
    operation: str,
    payload: dict,
    *,
    actor: str = "agent",
    source_refs: list[str] | None = None,
) -> dict:
    event = {
        "event_id": make_id("work-item-event"),
        "workspace_id": workspace_id,
        "work_item_id": work_item_id,
        "operation": operation,
        "timestamp": utc_now(),
        "actor": actor,
        "payload": payload,
        "source_refs": source_refs or [],
    }
    append_jsonl(_workspace_work_item_events_path(root, workspace_id), event)
    return event

def _reduce_work_items(rows: list[dict]) -> list[dict]:
    items: dict[str, dict] = {}
    ordered_rows = [
        row
        for _index, row in sorted(
            enumerate(rows),
            key=lambda entry: (entry[1].get("timestamp", ""), entry[0]),
        )
    ]
    for row in ordered_rows:
        work_item_id = row["work_item_id"]
        payload = row.get("payload", {})
        operation = row.get("operation")
        if operation == "create":
            items[work_item_id] = {
                "work_item_id": work_item_id,
                "title": payload.get("title", work_item_id),
                "kind": payload.get("kind", "task"),
                "status": payload.get("status", "proposed"),
                "priority": payload.get("priority", "medium"),
                "owner": payload.get("owner", ""),
                "parent_id": payload.get("parent_id", ""),
                "depends_on": list(payload.get("depends_on", [])),
                "linked_artifacts": list(payload.get("linked_artifacts", [])),
                "linked_tests": list(payload.get("linked_tests", [])),
                "guard_status": payload.get("guard_status", "not_required"),
                "guard_request": payload.get("guard_request", ""),
                "guard_purpose": payload.get("guard_purpose", ""),
                "guard_paths": list(payload.get("guard_paths", [])),
                "acceptance_criteria": list(payload.get("acceptance_criteria", [])),
                "constraints": list(payload.get("constraints", [])),
                "updated_at": row.get("timestamp", ""),
                "created_at": row.get("timestamp", ""),
            }
            continue
        item = items.get(work_item_id)
        if item is None:
            continue
        if operation == "set_status":
            item["status"] = payload.get("status", item["status"])
        elif operation == "set_owner":
            item["owner"] = payload.get("owner", item["owner"])
        elif operation == "set_priority":
            item["priority"] = payload.get("priority", item["priority"])
        elif operation == "set_parent":
            item["parent_id"] = payload.get("parent_id", item["parent_id"])
        elif operation == "set_dependencies":
            item["depends_on"] = list(payload.get("depends_on", item["depends_on"]))
        elif operation == "set_linked_artifacts":
            item["linked_artifacts"] = list(payload.get("linked_artifacts", item["linked_artifacts"]))
        elif operation == "set_linked_tests":
            item["linked_tests"] = list(payload.get("linked_tests", item["linked_tests"]))
        elif operation == "set_guard":
            item["guard_status"] = payload.get("guard_status", item["guard_status"])
            item["guard_request"] = payload.get("guard_request", item["guard_request"])
            item["guard_purpose"] = payload.get("guard_purpose", item["guard_purpose"])
            item["guard_paths"] = list(payload.get("guard_paths", item["guard_paths"]))
        elif operation == "set_acceptance":
            item["acceptance_criteria"] = list(payload.get("acceptance_criteria", item["acceptance_criteria"]))
        elif operation == "set_constraints":
            item["constraints"] = list(payload.get("constraints", item["constraints"]))
        item["updated_at"] = row.get("timestamp", item.get("updated_at", ""))
    return sorted(
        items.values(),
        key=lambda item: (
            item.get("status", ""),
            item.get("priority", ""),
            item.get("title", ""),
            item.get("work_item_id", ""),
        ),
    )

def _latest_test_runs(rows: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for row in sorted(rows, key=lambda item: (item.get("timestamp", ""), item.get("run_id", ""))):
        latest[row["test_id"]] = row
    return latest

def _test_failure_streaks(rows: list[dict]) -> dict[str, dict]:
    streaks: dict[str, dict] = {}
    grouped: dict[str, list[dict]] = {}
    for row in sorted(rows, key=lambda item: (item.get("timestamp", ""), item.get("run_id", ""))):
        grouped.setdefault(row["test_id"], []).append(row)
    for test_id, test_rows in grouped.items():
        streak = 0
        latest_result = ""
        latest_timestamp = ""
        for row in reversed(test_rows):
            result = row.get("result", "")
            if not latest_result:
                latest_result = result
                latest_timestamp = row.get("timestamp", "")
            if result == "passing":
                break
            if result in {"failing", "blocked", "not_run"}:
                streak += 1
                continue
            break
        streaks[test_id] = {
            "failure_streak": streak,
            "latest_result": latest_result,
            "latest_run_at": latest_timestamp,
        }
    return streaks

def _reduce_tests(test_cases: list[dict], test_runs: list[dict]) -> list[dict]:
    latest_runs = _latest_test_runs(test_runs)
    failure_streaks = _test_failure_streaks(test_runs)
    reduced = []
    for case in sorted(test_cases, key=lambda item: (item.get("created_at", ""), item.get("test_id", ""))):
        latest_run = latest_runs.get(case["test_id"])
        failure_state = failure_streaks.get(case["test_id"], {})
        reduced.append(
            {
                **case,
                "latest_result": latest_run.get("result") if latest_run else "not_run",
                "latest_run_at": latest_run.get("timestamp") if latest_run else "",
                "latest_evidence_ref": latest_run.get("evidence_ref") if latest_run else "",
                "failure_streak": failure_state.get("failure_streak", 0),
            }
        )
    return reduced

def _count_by(items: list[dict], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(item.get(key, "") or "unknown")
        counts[value] = counts.get(value, 0) + 1
    return counts

def _reduce_knowledge_records(rows: list[dict]) -> list[dict]:
    records: dict[str, dict] = {}
    for row in sorted(
        rows,
        key=lambda item: (
            item.get("updated_at", item.get("created_at", "")),
            item.get("record_id", ""),
        ),
    ):
        record_id = row.get("record_id")
        if not record_id:
            continue
        operation = row.get("operation", "create")
        if operation == "create" or record_id not in records:
            created_at = row.get("created_at", row.get("updated_at", ""))
            records[record_id] = {
                "record_id": record_id,
                "workspace_id": row.get("workspace_id", ""),
                "record_kind": row.get("record_kind", ""),
                "claim_posture": row.get("claim_posture", ""),
                "title": row.get("title", record_id),
                "statement": row.get("statement", ""),
                "confidence": row.get("confidence", 0.5),
                "status": row.get("status", "active"),
                "source_refs": list(row.get("source_refs", [])),
                "related_work_item_ids": list(row.get("related_work_item_ids", [])),
                "supersedes_record_id": row.get("supersedes_record_id", ""),
                "created_at": created_at,
                "updated_at": row.get("updated_at", created_at),
            }
            continue
        record = records[record_id]
        for field in ["record_kind", "claim_posture", "title", "statement", "status", "supersedes_record_id"]:
            if field in row and row.get(field) not in (None, ""):
                record[field] = row[field]
        if "confidence" in row and row.get("confidence") is not None:
            record["confidence"] = row["confidence"]
        if "source_refs" in row:
            record["source_refs"] = list(row.get("source_refs", []))
        if "related_work_item_ids" in row:
            record["related_work_item_ids"] = list(row.get("related_work_item_ids", []))
        record["updated_at"] = row.get("updated_at", record.get("updated_at", ""))
    return sorted(records.values(), key=lambda item: (item.get("created_at", ""), item.get("record_id", "")))

def _reduce_context_records(rows: list[dict]) -> list[dict]:
    records: dict[str, dict] = {}
    for row in sorted(
        rows,
        key=lambda item: (
            item.get("updated_at", item.get("created_at", "")),
            item.get("context_id", ""),
        ),
    ):
        context_id = row.get("context_id")
        if not context_id:
            continue
        operation = row.get("operation", "create")
        if operation == "create" or context_id not in records:
            created_at = row.get("created_at", row.get("updated_at", ""))
            records[context_id] = {
                "context_id": context_id,
                "workspace_id": row.get("workspace_id", ""),
                "context_kind": row.get("context_kind", ""),
                "title": row.get("title", context_id),
                "summary": row.get("summary", ""),
                "domain": row.get("domain", ""),
                "status": row.get("status", "active"),
                "confidence": row.get("confidence", 0.5),
                "source_refs": list(row.get("source_refs", [])),
                "linked_artifact_ids": list(row.get("linked_artifact_ids", [])),
                "created_at": created_at,
                "updated_at": row.get("updated_at", created_at),
            }
            continue
        record = records[context_id]
        for field in ["context_kind", "title", "summary", "domain", "status"]:
            if field in row and row.get(field) not in (None, ""):
                record[field] = row[field]
        if "confidence" in row and row.get("confidence") is not None:
            record["confidence"] = row["confidence"]
        if "source_refs" in row:
            record["source_refs"] = list(row.get("source_refs", []))
        if "linked_artifact_ids" in row:
            record["linked_artifact_ids"] = list(row.get("linked_artifact_ids", []))
        record["updated_at"] = row.get("updated_at", record.get("updated_at", ""))
    return sorted(records.values(), key=lambda item: (item.get("created_at", ""), item.get("context_id", "")))

def _reduce_constraint_records(rows: list[dict]) -> list[dict]:
    records: dict[str, dict] = {}
    for row in sorted(
        rows,
        key=lambda item: (
            item.get("updated_at", item.get("created_at", "")),
            item.get("constraint_id", ""),
        ),
    ):
        constraint_id = row.get("constraint_id")
        if not constraint_id:
            continue
        operation = row.get("operation", "create")
        if operation == "create" or constraint_id not in records:
            created_at = row.get("created_at", row.get("updated_at", ""))
            records[constraint_id] = {
                "constraint_id": constraint_id,
                "workspace_id": row.get("workspace_id", ""),
                "constraint_kind": row.get("constraint_kind", ""),
                "statement": row.get("statement", ""),
                "applies_to": row.get("applies_to", ""),
                "severity": row.get("severity", "required"),
                "status": row.get("status", "active"),
                "source_refs": list(row.get("source_refs", [])),
                "created_at": created_at,
                "updated_at": row.get("updated_at", created_at),
            }
            continue
        record = records[constraint_id]
        for field in ["constraint_kind", "statement", "applies_to", "severity", "status"]:
            if field in row and row.get(field) not in (None, ""):
                record[field] = row[field]
        if "source_refs" in row:
            record["source_refs"] = list(row.get("source_refs", []))
        record["updated_at"] = row.get("updated_at", record.get("updated_at", ""))
    return sorted(records.values(), key=lambda item: (item.get("created_at", ""), item.get("constraint_id", "")))

def _reduce_integration_targets(rows: list[dict]) -> list[dict]:
    targets: dict[str, dict] = {}
    for row in sorted(
        rows,
        key=lambda item: (
            item.get("updated_at", item.get("created_at", "")),
            item.get("target_id", ""),
        ),
    ):
        target_id = row.get("target_id")
        if not target_id:
            continue
        operation = row.get("operation", "create")
        if operation == "create" or target_id not in targets:
            created_at = row.get("created_at", row.get("updated_at", ""))
            targets[target_id] = {
                "target_id": target_id,
                "workspace_id": row.get("workspace_id", ""),
                "target_kind": row.get("target_kind", ""),
                "title": row.get("title", target_id),
                "destination_ref": row.get("destination_ref", ""),
                "required_evidence_refs": list(row.get("required_evidence_refs", [])),
                "status": row.get("status", "candidate"),
                "source_refs": list(row.get("source_refs", [])),
                "created_at": created_at,
                "updated_at": row.get("updated_at", created_at),
            }
            continue
        target = targets[target_id]
        for field in ["target_kind", "title", "destination_ref", "status"]:
            if field in row and row.get(field) not in (None, ""):
                target[field] = row[field]
        if "required_evidence_refs" in row:
            target["required_evidence_refs"] = list(row.get("required_evidence_refs", []))
        if "source_refs" in row:
            target["source_refs"] = list(row.get("source_refs", []))
        target["updated_at"] = row.get("updated_at", target.get("updated_at", ""))
    return sorted(targets.values(), key=lambda item: (item.get("created_at", ""), item.get("target_id", "")))

def _reduce_run_contracts(rows: list[dict]) -> list[dict]:
    runs: dict[str, dict] = {}
    for row in sorted(
        rows,
        key=lambda item: (
            item.get("updated_at", item.get("started_at", "")),
            item.get("run_id", ""),
        ),
    ):
        run_id = row.get("run_id")
        if not run_id:
            continue
        operation = row.get("operation", "create")
        if operation == "create" or run_id not in runs:
            started_at = row.get("started_at", row.get("updated_at", ""))
            runs[run_id] = {
                "run_id": run_id,
                "workspace_id": row.get("workspace_id", ""),
                "active_work_item_id": row.get("active_work_item_id", ""),
                "active_maturation_stage": row.get("active_maturation_stage", ""),
                "purpose": row.get("purpose", ""),
                "allowed_paths": list(row.get("allowed_paths", [])),
                "blocked_paths": list(row.get("blocked_paths", [])),
                "allowed_commands": list(row.get("allowed_commands", [])),
                "expected_outputs": list(row.get("expected_outputs", [])),
                "verification_plan": row.get("verification_plan", ""),
                "verification_result": row.get("verification_result", ""),
                "context_budget": row.get("context_budget", 0),
                "stop_conditions": list(row.get("stop_conditions", [])),
                "summary": row.get("summary", ""),
                "status": row.get("status", "active"),
                "started_at": started_at,
                "ended_at": row.get("ended_at"),
                "updated_at": row.get("updated_at", started_at),
            }
            continue
        run = runs[run_id]
        for field in [
            "active_work_item_id",
            "active_maturation_stage",
            "purpose",
            "verification_plan",
            "verification_result",
            "summary",
            "status",
            "ended_at",
        ]:
            if field in row and row.get(field) not in (None, ""):
                run[field] = row[field]
        for field in ["allowed_paths", "blocked_paths", "allowed_commands", "expected_outputs", "stop_conditions"]:
            if field in row:
                run[field] = list(row.get(field, []))
        if "context_budget" in row and row.get("context_budget") is not None:
            run["context_budget"] = row.get("context_budget", run.get("context_budget", 0))
        run["updated_at"] = row.get("updated_at", run.get("updated_at", ""))
    return sorted(runs.values(), key=lambda item: (item.get("started_at", ""), item.get("run_id", "")))

def _active_run_contract(runs: list[dict]) -> dict | None:
    active = [
        item
        for item in runs
        if item.get("status", "active") in HOLODECK_RUN_ACTIVE_STATUSES and not item.get("ended_at")
    ]
    if not active:
        return None
    active.sort(key=lambda item: (item.get("updated_at", item.get("started_at", "")), item.get("run_id", "")), reverse=True)
    return active[0]

def _latest_run_contract(runs: list[dict]) -> dict | None:
    if not runs:
        return None
    ordered = sorted(runs, key=lambda item: (item.get("updated_at", item.get("started_at", "")), item.get("run_id", "")), reverse=True)
    return ordered[0]

def _events_after_run_start(events: list[dict], run: dict | None) -> list[dict]:
    if not run:
        return []
    run_id = run.get("run_id", "")
    start_index = None
    for index, item in enumerate(events):
        if item.get("kind") != "run_started":
            continue
        if run_id and run_id not in item.get("summary", ""):
            continue
        start_index = index
    if start_index is None:
        started_at = run.get("started_at", "")
        return [item for item in events if item.get("timestamp", "") >= started_at]
    return events[start_index + 1 :]

def _context_units_for_run(events: list[dict], run: dict | None) -> int:
    return sum(
        int(item.get("context_units", 0) or 0)
        for item in _events_after_run_start(events, run)
    )

def _command_count_for_run(events: list[dict], run: dict | None) -> int:
    return sum(
        1
        for item in _events_after_run_start(events, run)
        if item.get("kind") == "command_executed" and item.get("command_ref")
    )

def _append_unique_issue(
    items: list[dict],
    seen_keys: set[tuple[str, str, str]],
    *,
    key: tuple[str, str, str],
    payload: dict,
) -> None:
    if key in seen_keys:
        return
    seen_keys.add(key)
    items.append(payload)

def _constraint_maps(constraint_records: list[dict]) -> tuple[dict[str, list[str]], dict[str, list[str]], dict[str, list[str]]]:
    allowed_constraint_paths: dict[str, list[str]] = {}
    blocked_constraint_paths: dict[str, list[str]] = {}
    non_goal_targets: dict[str, list[str]] = {}
    for item in constraint_records:
        applies_values = _split_csv(item.get("applies_to", ""))
        if item.get("constraint_kind") == "allowed_path":
            for value in applies_values:
                allowed_constraint_paths.setdefault(value, []).append(item["constraint_id"])
        elif item.get("constraint_kind") == "blocked_path":
            for value in applies_values:
                blocked_constraint_paths.setdefault(value, []).append(item["constraint_id"])
        elif item.get("constraint_kind") == "non_goal":
            for value in applies_values:
                non_goal_targets.setdefault(value, []).append(item["constraint_id"])
    return allowed_constraint_paths, blocked_constraint_paths, non_goal_targets

def _collect_constraint_violations(events: list[dict], work_items: list[dict], constraint_records: list[dict]) -> list[dict]:
    allowed_constraint_paths, blocked_constraint_paths, non_goal_targets = _constraint_maps(constraint_records)
    allowed_constraint_ids = sorted({item for ids in allowed_constraint_paths.values() for item in ids})
    violations: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()
    if allowed_constraint_paths or blocked_constraint_paths:
        for event in events:
            for source_ref in event.get("source_refs", []):
                if source_ref in blocked_constraint_paths:
                    for constraint_id in blocked_constraint_paths[source_ref]:
                        _append_unique_issue(
                            violations,
                            seen_keys,
                            key=("blocked_path_touched", constraint_id, source_ref),
                            payload={
                                "code": "blocked_path_touched",
                                "message": f"Constraint {constraint_id} blocks path {source_ref}, but workspace activity referenced it.",
                                "constraint_id": constraint_id,
                                "source_ref": source_ref,
                                "work_item_id": "",
                            },
                        )
                if allowed_constraint_paths and source_ref not in allowed_constraint_paths:
                    for constraint_id in allowed_constraint_ids:
                        _append_unique_issue(
                            violations,
                            seen_keys,
                            key=("source_ref_outside_constraint_allowed_paths", constraint_id, source_ref),
                            payload={
                                "code": "source_ref_outside_constraint_allowed_paths",
                                "message": f"Workspace activity referenced {source_ref}, which is outside the declared allowed_path constraints.",
                                "constraint_id": constraint_id,
                                "source_ref": source_ref,
                                "work_item_id": "",
                            },
                        )
    if non_goal_targets:
        terminal_statuses = {"done"}
        for item in work_items:
            if item["work_item_id"] not in non_goal_targets or item.get("status") in terminal_statuses:
                continue
            for constraint_id in non_goal_targets[item["work_item_id"]]:
                _append_unique_issue(
                    violations,
                    seen_keys,
                    key=("active_non_goal_work_item", constraint_id, item["work_item_id"]),
                    payload={
                        "code": "active_non_goal_work_item",
                        "message": f"Constraint {constraint_id} marks work item {item['work_item_id']} as a non-goal, but it is still active in the workspace.",
                        "constraint_id": constraint_id,
                        "source_ref": "",
                        "work_item_id": item["work_item_id"],
                    },
                )
    return violations

def _collect_run_drift_warnings(
    events: list[dict],
    work_item_rows: list[dict],
    active_run: dict | None,
    snapshot: dict,
) -> list[dict]:
    if not active_run:
        return []
    run_id = active_run.get("run_id", "")
    started_at = active_run.get("started_at", "")
    context_used = snapshot.get("active_run_context_units", 0)
    context_budget = int(active_run.get("context_budget", 0) or 0)
    non_progress_kinds = {"run_started", "workspace_created", "work_item_created", "work_started"}
    run_events = [
        item
        for item in _events_after_run_start(events, active_run)
        if item.get("kind") not in non_progress_kinds
    ]
    expansion_rows = [
        item
        for item in work_item_rows
        if item.get("timestamp", "") >= started_at
        and item.get("operation") == "create"
        and item.get("work_item_id") != active_run.get("active_work_item_id", "")
        and not item.get("payload", {}).get("parent_id", "")
    ]
    warnings: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()
    if not run_events:
        if expansion_rows:
            for row in expansion_rows:
                _append_unique_issue(
                    warnings,
                    seen_keys,
                    key=("work_item_expansion_outside_active_run", run_id, row.get("work_item_id", "")),
                    payload={
                        "code": "work_item_expansion_outside_active_run",
                        "message": f"Run {run_id or 'unknown'} created new work item {row.get('work_item_id', 'unknown')} outside the declared active work item.",
                        "run_id": run_id,
                        "source_ref": "",
                    },
                )
        else:
            _append_unique_issue(
                warnings,
                seen_keys,
                key=("stale_active_run", run_id, ""),
                payload={
                    "code": "stale_active_run",
                    "message": f"Active run {run_id or 'unknown'} has no progress events after it started.",
                    "run_id": run_id,
                    "source_ref": "",
                },
            )
    else:
        for row in expansion_rows:
            _append_unique_issue(
                warnings,
                seen_keys,
                key=("work_item_expansion_outside_active_run", run_id, row.get("work_item_id", "")),
                payload={
                    "code": "work_item_expansion_outside_active_run",
                    "message": f"Run {run_id or 'unknown'} created new work item {row.get('work_item_id', 'unknown')} outside the declared active work item.",
                    "run_id": run_id,
                    "source_ref": "",
                },
            )

    allowed_paths = set(active_run.get("allowed_paths", []))
    blocked_paths = set(active_run.get("blocked_paths", []))
    allowed_commands = set(active_run.get("allowed_commands", []))
    for event in run_events:
        command_ref = event.get("command_ref", "")
        if event.get("kind") == "command_executed" and command_ref and allowed_commands and command_ref not in allowed_commands:
            _append_unique_issue(
                warnings,
                seen_keys,
                key=("command_outside_allowed_commands", run_id, command_ref),
                payload={
                    "code": "command_outside_allowed_commands",
                    "message": f"Run {run_id or 'unknown'} executed command outside allowed_commands: {command_ref}.",
                    "run_id": run_id,
                    "source_ref": "",
                },
            )
        for source_ref in event.get("source_refs", []):
            if blocked_paths and source_ref in blocked_paths:
                _append_unique_issue(
                    warnings,
                    seen_keys,
                    key=("touched_blocked_path", run_id, source_ref),
                    payload={
                        "code": "touched_blocked_path",
                        "message": f"Run {run_id or 'unknown'} touched blocked path {source_ref}.",
                        "run_id": run_id,
                        "source_ref": source_ref,
                    },
                )
            if allowed_paths and source_ref not in allowed_paths:
                _append_unique_issue(
                    warnings,
                    seen_keys,
                    key=("source_ref_outside_allowed_paths", run_id, source_ref),
                    payload={
                        "code": "source_ref_outside_allowed_paths",
                        "message": f"Run {run_id or 'unknown'} touched source ref outside allowed paths: {source_ref}.",
                        "run_id": run_id,
                        "source_ref": source_ref,
                    },
                )
    if context_budget > 0 and context_used > context_budget:
        _append_unique_issue(
            warnings,
            seen_keys,
            key=("context_budget_exceeded", run_id, ""),
            payload={
                "code": "context_budget_exceeded",
                "message": f"Run {run_id or 'unknown'} used {context_used} context units against budget {context_budget}.",
                "run_id": run_id,
                "source_ref": "",
            },
        )
    return warnings

def _collect_completed_run_drift_warnings(run_contracts: list[dict]) -> list[dict]:
    warnings: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()
    for run in run_contracts:
        if run.get("status") != "completed" or run.get("verification_result"):
            continue
        run_id = run.get("run_id", "")
        _append_unique_issue(
            warnings,
            seen_keys,
            key=("completed_run_missing_verification", run_id, ""),
            payload={
                "code": "completed_run_missing_verification",
                "message": f"Completed run {run_id or 'unknown'} has no verification result.",
                "run_id": run_id,
                "source_ref": "",
            },
        )
    return warnings

def _normalize_conflict_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())

def _detect_knowledge_conflicts(records: list[dict]) -> list[dict]:
    conflictable_kinds = {"decision", "requirement", "constraint"}
    grouped: dict[tuple[str, str], list[dict]] = {}
    for record in records:
        record_kind = record.get("record_kind", "")
        title = _normalize_conflict_text(record.get("title", ""))
        if record.get("status", "active") != "active" or record_kind not in conflictable_kinds or not title:
            continue
        grouped.setdefault((record_kind, title), []).append(record)

    conflicts: list[dict] = []
    for (record_kind, normalized_title), group in grouped.items():
        statements = {_normalize_conflict_text(item.get("statement", "")) for item in group if _normalize_conflict_text(item.get("statement", ""))}
        if len(group) < 2 or len(statements) < 2:
            continue
        conflicts.append(
            {
                "conflict_key": f"{record_kind}:{normalized_title}",
                "record_kind": record_kind,
                "title": group[0].get("title", normalized_title),
                "record_ids": [item["record_id"] for item in group],
                "claim_postures": sorted({item.get("claim_posture", "") for item in group if item.get("claim_posture", "")}),
                "statements": [item.get("statement", "") for item in group],
            }
        )
    conflicts.sort(key=lambda item: (item.get("record_kind", ""), item.get("title", "")))
    return conflicts

def _reduce_promotions(rows: list[dict]) -> list[dict]:
    promotions: dict[str, dict] = {}
    for row in sorted(rows, key=lambda item: (item.get("timestamp", item.get("promoted_at", "")), item.get("promotion_id", ""))):
        promotion_id = row.get("promotion_id")
        if not promotion_id:
            continue
        operation = row.get("operation", "create")
        if operation == "create":
            promotions[promotion_id] = {
                "promotion_id": promotion_id,
                "workspace_id": row.get("workspace_id", ""),
                "source_kind": row.get("source_kind", ""),
                "source_record_id": row.get("source_record_id", ""),
                "target_kind": row.get("target_kind", ""),
                "status": row.get("status", "candidate"),
                "title": row.get("title", promotion_id),
                "statement": row.get("statement", ""),
                "record_kind": row.get("record_kind", ""),
                "claim_posture": row.get("claim_posture", ""),
                "reason": row.get("reason", ""),
                "summary": row.get("summary", ""),
                "source_refs": list(row.get("source_refs", [])),
                "related_work_item_ids": list(row.get("related_work_item_ids", [])),
                "linked_target_ids": list(row.get("linked_target_ids", [])),
                "created_at": row.get("promoted_at", row.get("timestamp", "")),
                "updated_at": row.get("promoted_at", row.get("timestamp", "")),
            }
            continue
        promotion = promotions.get(promotion_id)
        if promotion is None:
            continue
        if operation == "set_status":
            promotion["status"] = row.get("status", promotion.get("status", "candidate"))
            promotion["reason"] = row.get("reason", promotion.get("reason", ""))
            if row.get("summary"):
                promotion["summary"] = row["summary"]
        if "linked_target_ids" in row:
            promotion["linked_target_ids"] = list(row.get("linked_target_ids", []))
        promotion["updated_at"] = row.get("timestamp", promotion.get("updated_at", ""))
    return sorted(
        promotions.values(),
        key=lambda item: (
            item.get("status", ""),
            item.get("updated_at", ""),
            item.get("promotion_id", ""),
        ),
    )

def _active_promotion_candidates(promotions: list[dict]) -> list[dict]:
    archived_statuses = {"applied", "archived", "rejected"}
    active = [item for item in promotions if item.get("status", "candidate") not in archived_statuses]
    active.sort(key=lambda item: (item.get("updated_at", item.get("created_at", "")), item.get("promotion_id", "")), reverse=True)
    return active

def _founder_fields_from_args(args: argparse.Namespace) -> dict[str, str]:
    fields = {
        "wedge": getattr(args, "founder_wedge", None),
        "user": getattr(args, "founder_user", None),
        "moat": getattr(args, "founder_moat", None),
        "gtm_risk": getattr(args, "founder_gtm_risk", None),
        "launch_metric": getattr(args, "founder_launch_metric", None),
    }
    return {key: value for key, value in fields.items() if value not in (None, "")}

def _validate_template_manifest_state(*, template_key: str, template_fields: dict[str, str]) -> None:
    if template_fields and template_key != "founder":
        raise ValueError("founder template fields require template_key=founder.")

def _validate_maturation_stage(stage: str) -> str:
    if stage not in HOLODECK_MATURATION_STAGES:
        allowed = ", ".join(sorted(HOLODECK_MATURATION_STAGES))
        raise ValueError(f"Invalid maturation stage: {stage}. Allowed stages: {allowed}")
    return stage

def _validate_run_start_status(status: str) -> str:
    if status not in {"planned", "active"}:
        raise ValueError("Run start status must be planned or active.")
    return status

def _validate_run_finish_status(status: str) -> str:
    if status not in HOLODECK_RUN_TERMINAL_STATUSES:
        allowed = ", ".join(sorted(HOLODECK_RUN_TERMINAL_STATUSES))
        raise ValueError(f"Run finish status must be one of: {allowed}.")
    return status

def _stage_gap(stage: str, code: str, message: str) -> dict:
    return {
        "stage": stage,
        "code": code,
        "message": message,
    }

def _stage_gaps_for_snapshot(snapshot: dict) -> list[dict]:
    stage = snapshot.get("maturation_stage", "raw")
    gaps: list[dict] = []
    if stage == "raw":
        return gaps
    if stage == "contextualizing":
        contextualization = dict(snapshot.get("contextualization_summary", {}))
        status = contextualization.get("status", "unresolved")
        if not contextualization.get("resolved"):
            if status == "insufficient":
                gaps.append(
                    _stage_gap(
                        stage,
                        "insufficient_contextualization_signals",
                        "Contextualizing requires either inherited anchors or an explicit novelty outcome once bounded retrieval has enough signal.",
                    )
                )
            else:
                gaps.append(
                    _stage_gap(
                        stage,
                        "missing_contextualization_outcome",
                        "Contextualizing requires either inherited context anchors or an explicit novelty outcome.",
                    )
                )
    if stage == "scoping":
        constraint_counts = snapshot.get("constraint_counts", {})
        if not snapshot.get("scope_in") and not constraint_counts.get("scope_in"):
            gaps.append(_stage_gap(stage, "missing_scope_in", "Scoping requires at least one in-scope boundary."))
        if not snapshot.get("scope_out") and not constraint_counts.get("scope_out"):
            gaps.append(_stage_gap(stage, "missing_scope_out", "Scoping requires at least one out-of-scope boundary."))
    if stage == "developing":
        if not snapshot.get("active_items") and not snapshot.get("work_item_counts"):
            gaps.append(_stage_gap(stage, "missing_work_items", "Developing requires at least one work item."))
        if not snapshot.get("pending_tests") and not snapshot.get("test_counts"):
            gaps.append(_stage_gap(stage, "missing_verification_shape", "Developing requires at least one declared test."))
    if stage == "verifying" and not snapshot.get("test_counts"):
        gaps.append(_stage_gap(stage, "missing_tests", "Verifying requires declared tests or acceptance evidence."))
    if stage == "integrating" and not snapshot.get("integration_candidates") and not snapshot.get("integration_targets"):
        gaps.append(_stage_gap(stage, "missing_integration_target", "Integrating requires at least one promotion or integration target."))
    if stage == "complete":
        if snapshot.get("workspace_blockers") or snapshot.get("blocked_items"):
            gaps.append(_stage_gap(stage, "active_blockers", "Complete requires no active workspace or work-item blockers."))
        if snapshot.get("knowledge_conflicts"):
            gaps.append(_stage_gap(stage, "unresolved_conflicts", "Complete requires no unresolved knowledge conflicts."))
        applied_targets = [
            item for item in snapshot.get("integration_targets", [])
            if item.get("status") == "applied"
        ]
        if not snapshot.get("integration_candidates") and not snapshot.get("promotion_counts", {}).get("applied") and not applied_targets:
            gaps.append(_stage_gap(stage, "missing_integration_evidence", "Complete requires integration evidence or applied promotion."))
    return gaps


def _collect_completion_contract_gaps(
    *,
    manifest: dict,
    work_items: list[dict],
    tests: list[dict],
    constraint_records: list[dict],
    integration_targets: list[dict],
    active_promotions: list[dict],
) -> list[dict]:
    relevant_items = [
        item
        for item in work_items
        if item.get("status") not in {"blocked", "done", "cancelled", "abandoned"}
    ]
    if not relevant_items:
        return []

    gaps: list[dict] = []
    proof_requirements = [
        item
        for item in constraint_records
        if item.get("status", "active") == "active" and item.get("constraint_kind") == "proof_requirement"
    ]
    if not tests:
        gaps.append(
            {
                "code": "missing_test_contract",
                "message": "Active workspace work requires at least one declared test or verification protocol before it is execution-ready.",
            }
        )
    if not proof_requirements:
        gaps.append(
            {
                "code": "missing_proof_contract",
                "message": "Active workspace work requires declared proof surfaces before local green can be treated as working.",
            }
        )
    needs_integration_contract = (
        manifest.get("maturation_stage") in {"integrating", "complete"}
        or bool(active_promotions)
        or any(item.get("status") in {"ready", "in_progress", "done"} for item in relevant_items)
    )
    if needs_integration_contract and not integration_targets and not active_promotions:
        gaps.append(
            {
                "code": "missing_integration_contract",
                "message": "Work approaching integration requires at least one integration target or active promotion.",
            }
        )
    return gaps

def _template_issues_for_manifest(manifest: dict) -> list[dict]:
    template_key = manifest.get("template_key", "")
    template_fields = dict(manifest.get("template_fields", {}))
    issues: list[dict] = []
    if template_key == "founder":
        for field in ("wedge", "user", "launch_metric"):
            if template_fields.get(field):
                continue
            issues.append(
                {
                    "code": "missing_founder_field",
                    "template_key": "founder",
                    "field": field,
                    "message": f"Founder template is missing {field}.",
                }
            )
    elif template_fields:
        issues.append(
            {
                "code": "template_field_mismatch",
                "template_key": template_key or "none",
                "field": "template_fields",
                "message": "Template fields are present without template_key=founder.",
            }
        )
    return issues

def _inquiry_priority_key(item: dict) -> tuple[int, int, int, str]:
    impact_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return (
        0 if item.get("ask_user") else 1,
        0 if item.get("blocking") else 1,
        impact_rank.get(item.get("impact", "medium"), 9),
        item.get("inquiry_id", ""),
    )

def _append_inquiry(inquiries: list[dict], seen_ids: set[str], payload: dict) -> None:
    inquiry_id = payload["inquiry_id"]
    if inquiry_id in seen_ids:
        return
    seen_ids.add(inquiry_id)
    inquiries.append(payload)

def _founder_field_question(field: str) -> tuple[str, str]:
    mapping = {
        "wedge": (
            "What is the narrow initial wedge for this founder objective?",
            "Without a defined wedge, the objective can sprawl before it proves value.",
        ),
        "user": (
            "Who is the exact founder user this objective is for?",
            "Without a concrete user, the objective can drift into generic strategy instead of a bounded problem.",
        ),
        "launch_metric": (
            "What launch metric will tell us this founder objective is working?",
            "Without a launch metric, the system cannot tell whether the objective is becoming production-shaped or just accumulating work.",
        ),
    }
    return mapping.get(
        field,
        (
            f"What should the founder field `{field}` be for this objective?",
            "The founder template is missing required grounding for this objective.",
        ),
    )

def _derive_inquiry_queue(
    *,
    snapshot: dict,
    template_issues: list[dict] | None = None,
    stage_gaps: list[dict] | None = None,
    knowledge_conflicts: list[dict] | None = None,
    verification_gaps: list[dict] | None = None,
    verification_hotspots: list[dict] | None = None,
    guard_gaps: list[dict] | None = None,
    constraint_violations: list[dict] | None = None,
) -> tuple[list[dict], list[dict]]:
    template_issues = list(template_issues if template_issues is not None else snapshot.get("template_issues", []))
    stage_gaps = list(stage_gaps if stage_gaps is not None else snapshot.get("stage_gaps", []))
    knowledge_conflicts = list(knowledge_conflicts if knowledge_conflicts is not None else snapshot.get("knowledge_conflicts", []))
    verification_gaps = list(verification_gaps or [])
    verification_hotspots = list(verification_hotspots or [])
    guard_gaps = list(guard_gaps or [])
    constraint_violations = list(constraint_violations or [])

    inquiries: list[dict] = []
    seen_ids: set[str] = set()

    for item in template_issues:
        if item.get("code") != "missing_founder_field":
            continue
        field = item.get("field", "")
        question, why = _founder_field_question(field)
        _append_inquiry(
            inquiries,
            seen_ids,
            {
                "inquiry_id": f"template:{item.get('code')}:{field}",
                "inquiry_kind": "user_input",
                "ask_user": True,
                "blocking": False,
                "impact": "high",
                "field": field,
                "question": question,
                "why_this_matters": why,
                "source_signals": [f"template_issue:{item.get('code')}:{field}"],
                "resolution_path": [f"Fill founder field `{field}` in the Holodeck template fields."],
            },
        )

    for item in stage_gaps:
        code = item.get("code", "")
        stage = item.get("stage", "")
        if code == "missing_scope_in":
            _append_inquiry(
                inquiries,
                seen_ids,
                {
                    "inquiry_id": f"stage:{stage}:{code}",
                    "inquiry_kind": "scope",
                    "ask_user": True,
                    "blocking": True,
                    "impact": "high",
                    "question": "What is explicitly in scope for this objective right now?",
                    "why_this_matters": "Without an in-scope boundary, the objective cannot be shaped into a reliable implementation thread.",
                    "source_signals": [f"stage_gap:{stage}:{code}"],
                    "resolution_path": ["Add at least one scope_in boundary to the Holodeck manifest or constraints."],
                },
            )
        elif code == "missing_scope_out":
            _append_inquiry(
                inquiries,
                seen_ids,
                {
                    "inquiry_id": f"stage:{stage}:{code}",
                    "inquiry_kind": "scope",
                    "ask_user": True,
                    "blocking": True,
                    "impact": "high",
                    "question": "What is explicitly out of scope for this objective right now?",
                    "why_this_matters": "Without an out-of-scope boundary, the objective can expand faster than the system can ground and verify it.",
                    "source_signals": [f"stage_gap:{stage}:{code}"],
                    "resolution_path": ["Add at least one scope_out boundary to the Holodeck manifest or constraints."],
                },
            )
        elif code in {"missing_context", "missing_tests", "missing_verification_shape", "missing_integration_target", "missing_integration_evidence"}:
            _append_inquiry(
                inquiries,
                seen_ids,
                {
                    "inquiry_id": f"stage:{stage}:{code}",
                    "inquiry_kind": "verification" if "test" in code or "verification" in code else "integration" if "integration" in code else "scope",
                    "ask_user": False,
                    "blocking": code in {"missing_tests", "missing_verification_shape"},
                    "impact": "medium" if code == "missing_context" else "high",
                    "question": item.get("message", ""),
                    "why_this_matters": item.get("message", ""),
                    "source_signals": [f"stage_gap:{stage}:{code}"],
                    "resolution_path": [item.get("message", "")],
                },
            )

    for item in knowledge_conflicts:
        record_kind = item.get("record_kind", "decision")
        title = item.get("title", item.get("conflict_key", "this issue"))
        _append_inquiry(
            inquiries,
            seen_ids,
            {
                "inquiry_id": f"knowledge_conflict:{record_kind}:{title}",
                "inquiry_kind": "decision",
                "ask_user": True,
                "blocking": True,
                "impact": "high",
                "question": f"Which conflicting {record_kind} should remain active for `{title}`?",
                "why_this_matters": "Conflicting active knowledge creates drift because the system cannot tell which position should govern later work.",
                "source_signals": [f"knowledge_conflict:{record_kind}:{title}"],
                "resolution_path": ["Resolve or supersede the conflicting knowledge records so only one active position remains."],
                "record_ids": list(item.get("record_ids", [])),
            },
        )

    for item in verification_gaps:
        work_item_id = item.get("work_item_id", "")
        reason = item.get("reason", "missing_verification")
        _append_inquiry(
            inquiries,
            seen_ids,
            {
                "inquiry_id": f"verification_gap:{work_item_id}:{reason}",
                "inquiry_kind": "verification",
                "ask_user": False,
                "blocking": True,
                "impact": "high",
                "question": f"What verification evidence is still missing for work item `{work_item_id}`?",
                "why_this_matters": "A done work item without passing evidence weakens readiness and makes later promotion unsafe.",
                "source_signals": [f"verification_gap:{reason}:{work_item_id}"],
                "resolution_path": ["Record a passing test run or equivalent verification evidence for the completed work item."],
                "work_item_id": work_item_id,
            },
        )

    for item in verification_hotspots:
        test_id = item.get("test_id", "")
        _append_inquiry(
            inquiries,
            seen_ids,
            {
                "inquiry_id": f"verification_hotspot:{test_id}",
                "inquiry_kind": "verification",
                "ask_user": False,
                "blocking": False,
                "impact": "medium",
                "question": f"Why is test `{test_id}` repeatedly failing or not passing yet?",
                "why_this_matters": "Repeated verification failure indicates unstable understanding or unstable implementation at a critical boundary.",
                "source_signals": [f"verification_hotspot:{test_id}"],
                "resolution_path": ["Investigate the failing test and either fix the target behavior or update the declared verification shape."],
                "test_id": test_id,
            },
        )

    for item in guard_gaps:
        work_item_id = item.get("work_item_id", "")
        _append_inquiry(
            inquiries,
            seen_ids,
            {
                "inquiry_id": f"guard_gap:{work_item_id}",
                "inquiry_kind": "decision",
                "ask_user": False,
                "blocking": True,
                "impact": "high",
                "question": f"What concrete guard scope is missing for work item `{work_item_id}`?",
                "why_this_matters": "Implementation work without a ready engineering guard can expand before its boundary is explicitly approved.",
                "source_signals": [f"guard_gap:{work_item_id}"],
                "resolution_path": ["Assess the engineering guard for this work item and bring guard_status to ready before execution."],
                "work_item_id": work_item_id,
            },
        )

    for item in constraint_violations:
        code = item.get("code", "")
        anchor = item.get("work_item_id") or item.get("source_ref") or item.get("constraint_id", "")
        _append_inquiry(
            inquiries,
            seen_ids,
            {
                "inquiry_id": f"constraint_violation:{code}:{anchor}",
                "inquiry_kind": "scope",
                "ask_user": False,
                "blocking": True,
                "impact": "high",
                "question": item.get("message", ""),
                "why_this_matters": "Constraint violations mean the workspace is no longer operating inside its declared boundary.",
                "source_signals": [f"constraint_violation:{code}:{anchor}"],
                "resolution_path": ["Resolve the violating work or update the declared boundary explicitly."],
            },
        )

    inquiries.sort(key=_inquiry_priority_key)
    questions_for_user = [item for item in inquiries if item.get("ask_user")][:3]
    return inquiries, questions_for_user

def _load_workspace_artifacts(root: Path, workspace_id: str) -> list[dict]:
    artifacts = read_jsonl(_workspace_artifact_links_path(root, workspace_id))
    deduped: dict[tuple[str, str, str], dict] = {}
    for row in sorted(artifacts, key=lambda item: (item.get("linked_at", ""), item.get("artifact_id", ""))):
        key = (
            row.get("artifact_kind", ""),
            row.get("source_ref", ""),
            row.get("title", ""),
        )
        deduped[key] = row
    reduced = list(deduped.values())
    reduced.sort(key=lambda item: (item.get("linked_at", ""), item.get("artifact_id", "")), reverse=True)
    return reduced

def _append_workspace_artifact_link(root: Path, workspace_id: str, artifact: dict) -> dict:
    artifacts = _load_workspace_artifacts(root, workspace_id)
    for existing in artifacts:
        if (
            existing.get("artifact_kind") == artifact.get("artifact_kind")
            and existing.get("source_ref") == artifact.get("source_ref")
            and existing.get("title") == artifact.get("title")
        ):
            return existing | {"deduped": True}
    append_jsonl(_workspace_artifact_links_path(root, workspace_id), artifact)
    return artifact | {"deduped": False}

def _requires_ready_guard(kind: str) -> bool:
    return kind in {"bug", "feature", "implementation"}

def _is_closed_work_item_status(status: str) -> bool:
    return status in {"done", "archived"}

def _work_item_children_by_parent(work_items_by_id: dict[str, dict]) -> dict[str, list[dict]]:
    children: dict[str, list[dict]] = {}
    for item in work_items_by_id.values():
        parent_id = item.get("parent_id", "")
        if not parent_id:
            continue
        children.setdefault(parent_id, []).append(item)
    return children

def _parent_chain_contains(work_items_by_id: dict[str, dict], start_parent_id: str, target_id: str) -> bool:
    seen: set[str] = set()
    current_id = start_parent_id
    while current_id:
        if current_id == target_id:
            return True
        if current_id in seen:
            return False
        seen.add(current_id)
        current = work_items_by_id.get(current_id)
        if current is None:
            return False
        current_id = current.get("parent_id", "")
    return False

def _dependency_chain_contains(work_items_by_id: dict[str, dict], start_dependency_id: str, target_id: str) -> bool:
    seen: set[str] = set()
    stack = [start_dependency_id]
    while stack:
        current_id = stack.pop()
        if current_id == target_id:
            return True
        if current_id in seen:
            continue
        seen.add(current_id)
        current = work_items_by_id.get(current_id)
        if current is None:
            continue
        stack.extend(list(current.get("depends_on", [])))
    return False

def _relationship_state_for_work_item(
    work_items_by_id: dict[str, dict],
    *,
    work_item_id: str,
    parent_id: str,
    depends_on: list[str],
    require_closed_dependencies: bool,
    require_closed_children: bool,
) -> dict:
    children_by_parent = _work_item_children_by_parent(work_items_by_id)
    reasons: list[str] = []
    missing_dependency_ids: list[str] = []
    open_dependency_ids: list[str] = []
    open_child_ids: list[str] = []

    if parent_id:
        if parent_id == work_item_id:
            reasons.append("A work item cannot be its own parent.")
        elif parent_id not in work_items_by_id:
            reasons.append(f"Parent work item does not exist: {parent_id}")
        elif _parent_chain_contains(work_items_by_id, parent_id, work_item_id):
            reasons.append(f"Parent relationship would create a cycle through {parent_id}.")

    seen_dependencies: set[str] = set()
    for dependency_id in depends_on:
        if not dependency_id or dependency_id in seen_dependencies:
            continue
        seen_dependencies.add(dependency_id)
        if dependency_id == work_item_id:
            reasons.append("A work item cannot depend on itself.")
            continue
        dependency = work_items_by_id.get(dependency_id)
        if dependency is None:
            missing_dependency_ids.append(dependency_id)
            reasons.append(f"Dependency does not exist: {dependency_id}")
            continue
        if _dependency_chain_contains(work_items_by_id, dependency_id, work_item_id):
            reasons.append(f"Dependency relationship would create a cycle through {dependency_id}.")
            continue
        if require_closed_dependencies and not _is_closed_work_item_status(dependency.get("status", "")):
            open_dependency_ids.append(dependency_id)
            reasons.append(
                f"Dependency {dependency_id} is still {dependency.get('status', 'unknown')} and must be done first."
            )

    if require_closed_children:
        for child in children_by_parent.get(work_item_id, []):
            if not _is_closed_work_item_status(child.get("status", "")):
                open_child_ids.append(child["work_item_id"])
                reasons.append(
                    f"Child work item {child['work_item_id']} is still {child.get('status', 'unknown')}."
                )

    return {
        "blocker_reasons": reasons,
        "missing_dependency_ids": missing_dependency_ids,
        "open_dependency_ids": open_dependency_ids,
        "open_child_ids": open_child_ids,
    }

def _annotate_work_items(work_items: list[dict]) -> list[dict]:
    work_items_by_id = {item["work_item_id"]: dict(item) for item in work_items}
    children_by_parent = _work_item_children_by_parent(work_items_by_id)
    annotated: list[dict] = []
    for item in work_items:
        relationship = _relationship_state_for_work_item(
            work_items_by_id,
            work_item_id=item["work_item_id"],
            parent_id=item.get("parent_id", ""),
            depends_on=list(item.get("depends_on", [])),
            require_closed_dependencies=item.get("status") in {"blocked", "ready", "in_progress", "done"},
            require_closed_children=item.get("status") in {"blocked", "done"},
        )
        annotated.append(
            item
            | relationship
            | {
                "child_ids": [child["work_item_id"] for child in children_by_parent.get(item["work_item_id"], [])],
            }
        )
    return annotated

def _validate_work_item_transition(
    *,
    work_items_by_id: dict[str, dict],
    work_item_id: str,
    kind: str,
    status: str,
    parent_id: str,
    depends_on: list[str],
    acceptance_criteria: list[str],
    guard_status: str,
) -> None:
    if status in {"ready", "in_progress"} and not acceptance_criteria:
        raise ValueError("Acceptance criteria are required before a work item can be ready or in progress.")
    if status in {"ready", "in_progress"} and _requires_ready_guard(kind) and guard_status != "ready":
        raise ValueError("Implementation-oriented work items require guard_status=ready before they can be ready or in progress.")
    relationship = _relationship_state_for_work_item(
        work_items_by_id,
        work_item_id=work_item_id,
        parent_id=parent_id,
        depends_on=depends_on,
        require_closed_dependencies=status in {"ready", "in_progress", "done"},
        require_closed_children=status == "done",
    )
    if relationship["blocker_reasons"]:
        raise ValueError(" ".join(relationship["blocker_reasons"]))

def _workspace_diary_lines(
    workspace_id: str,
    events: list[dict],
    work_item_rows: list[dict],
    test_runs: list[dict],
    knowledge: list[dict],
    promotions: list[dict],
) -> list[str]:
    diary_rows: list[dict] = []
    for event in events:
        line = f"- {event.get('timestamp', '')} [{event.get('kind', 'note')}] {event.get('summary', '') or event.get('content', '')}"
        if event.get("context_units", 0):
            line = f"{line} :: context_units={event.get('context_units', 0)}"
        diary_rows.append(
            {
                "timestamp": event.get("timestamp", ""),
                "sort_id": event.get("event_id", ""),
                "line": line,
            }
        )
    for row in work_item_rows:
        payload = row.get("payload", {})
        operation = row.get("operation", "update")
        work_item_id = row.get("work_item_id", "")
        if operation == "create":
            detail = payload.get("title", work_item_id)
        elif operation == "set_status":
            detail = f"{work_item_id} -> {payload.get('status', '')}"
        elif operation == "set_owner":
            detail = f"{work_item_id} owner -> {payload.get('owner', '') or 'unassigned'}"
        elif operation == "set_priority":
            detail = f"{work_item_id} priority -> {payload.get('priority', '')}"
        elif operation == "set_parent":
            detail = f"{work_item_id} parent -> {payload.get('parent_id', '') or 'none'}"
        elif operation == "set_dependencies":
            detail = f"{work_item_id} dependencies updated"
        elif operation == "set_linked_artifacts":
            detail = f"{work_item_id} linked artifacts updated"
        elif operation == "set_linked_tests":
            detail = f"{work_item_id} linked tests updated"
        elif operation == "set_guard":
            detail = f"{work_item_id} guard -> {payload.get('guard_status', '')}"
        elif operation == "set_acceptance":
            detail = f"{work_item_id} acceptance updated"
        elif operation == "set_constraints":
            detail = f"{work_item_id} constraints updated"
        else:
            detail = work_item_id
        diary_rows.append(
            {
                "timestamp": row.get("timestamp", ""),
                "sort_id": row.get("event_id", ""),
                "line": f"- {row.get('timestamp', '')} [work_item:{operation}] {detail}",
            }
        )
    for row in test_runs:
        diary_rows.append(
            {
                "timestamp": row.get("timestamp", ""),
                "sort_id": row.get("run_id", ""),
                "line": f"- {row.get('timestamp', '')} [test_run:{row.get('result', 'unknown')}] {row.get('test_id', '')}",
            }
        )
    for row in knowledge:
        diary_rows.append(
            {
                "timestamp": row.get("created_at", ""),
                "sort_id": row.get("record_id", ""),
                "line": f"- {row.get('created_at', '')} [knowledge:{row.get('record_kind', 'note')}] {row.get('title', row.get('record_id', ''))}",
            }
        )
    for row in promotions:
        diary_rows.append(
            {
                "timestamp": row.get("updated_at", row.get("created_at", "")),
                "sort_id": row.get("promotion_id", ""),
                "line": f"- {row.get('updated_at', row.get('created_at', ''))} [promotion:{row.get('status', 'candidate')}] {row.get('title', row.get('promotion_id', ''))}",
            }
        )

    diary_rows.sort(key=lambda item: (item.get("timestamp", ""), item.get("sort_id", "")))
    lines = [f"# Holodeck Diary — {workspace_id}", ""]
    lines.extend([row["line"] for row in diary_rows] or ["- none"])
    return lines

def _materialize_workspace_snapshot(root: Path, workspace_id: str, *, write_files: bool) -> dict:
    manifest = _load_workspace_manifest(root, workspace_id)
    events = read_jsonl(_workspace_events_path(root, workspace_id))
    artifact_links = _load_workspace_artifacts(root, workspace_id)
    work_item_rows = read_jsonl(_workspace_work_item_events_path(root, workspace_id))
    work_items = _annotate_work_items(_reduce_work_items(work_item_rows))
    test_run_rows = read_jsonl(_workspace_test_runs_path(root, workspace_id))
    tests = _reduce_tests(
        read_jsonl(_workspace_test_cases_path(root, workspace_id)),
        test_run_rows,
    )
    knowledge = _reduce_knowledge_records(read_jsonl(_workspace_knowledge_records_path(root, workspace_id)))
    context_records = _reduce_context_records(read_jsonl(_workspace_context_records_path(root, workspace_id)))
    constraint_records = _reduce_constraint_records(read_jsonl(_workspace_constraint_records_path(root, workspace_id)))
    integration_targets = _reduce_integration_targets(read_jsonl(_workspace_integration_targets_path(root, workspace_id)))
    run_contracts = _reduce_run_contracts(read_jsonl(_workspace_run_contracts_path(root, workspace_id)))
    promotions = _reduce_promotions(read_jsonl(_workspace_promotions_path(root, workspace_id)))

    blocked_items = [item for item in work_items if item.get("status") == "blocked" or item.get("blocker_reasons")]
    active_items = [
        item
        for item in work_items
        if item.get("status") in {"ready", "in_progress"} and not item.get("blocker_reasons")
    ]
    pending_tests = [item for item in tests if item.get("latest_result") != "passing"]
    verification_hotspots = [
        {
            "test_id": item["test_id"],
            "work_item_id": item["work_item_id"],
            "intent": item["intent"],
            "latest_result": item["latest_result"],
            "failure_streak": item.get("failure_streak", 0),
        }
        for item in tests
        if item.get("failure_streak", 0) >= 2
    ]
    active_knowledge = [item for item in knowledge if item.get("status", "active") == "active"]
    active_context_records = [item for item in context_records if item.get("status", "active") == "active"]
    active_constraint_records = [item for item in constraint_records if item.get("status", "active") == "active"]
    active_integration_targets = [item for item in integration_targets if item.get("status", "candidate") != "archived"]
    active_run = _active_run_contract(run_contracts)
    latest_run = _latest_run_contract(run_contracts)
    active_run_context_units = _context_units_for_run(events, active_run)
    active_run_command_count = _command_count_for_run(events, active_run)
    proof_summary = _proof_summary(snapshot={}, events=events, constraint_records=active_constraint_records)
    contextualization_summary, latest_contextualization_run, latest_contextualization_candidates, current_contextualization_seed = _contextualization_state(
        root,
        workspace_id,
        manifest=manifest,
        artifacts=artifact_links,
        work_items=work_items,
        context_records=active_context_records,
        events=events,
    )
    knowledge_conflicts = _detect_knowledge_conflicts(active_knowledge)
    integration_candidates = _active_promotion_candidates(promotions)
    founder_fields = manifest.get("template_fields", {}) if manifest.get("template_key") == "founder" else {}
    template_issues = _template_issues_for_manifest(manifest)

    snapshot = {
        "workspace_id": workspace_id,
        "label": manifest.get("label", workspace_id),
        "status": manifest.get("status", "active"),
        "status_reason": manifest.get("status_reason", ""),
        "maturation_stage": manifest.get("maturation_stage", "raw"),
        "goal": manifest.get("goal", ""),
        "purpose": manifest.get("purpose", ""),
        "success_condition": manifest.get("success_condition", ""),
        "scope_in": list(manifest.get("scope_in", [])),
        "scope_out": list(manifest.get("scope_out", [])),
        "template_key": manifest.get("template_key", ""),
        "template_fields": founder_fields,
        "domain_overlays": manifest.get("domain_overlays", []),
        "linked_session_ids": manifest.get("linked_session_ids", []),
        "linked_task_pack_ids": manifest.get("linked_task_pack_ids", []),
        "artifact_count": len(artifact_links),
        "artifact_counts": _count_by(artifact_links, "artifact_kind"),
        "event_count": len(events),
        "work_item_counts": _count_by(work_items, "status"),
        "test_counts": _count_by(tests, "latest_result"),
        "knowledge_counts": _count_by(active_knowledge, "record_kind"),
        "context_count": len(active_context_records),
        "context_counts": _count_by(active_context_records, "context_kind"),
        "constraint_count": len(active_constraint_records),
        "constraint_counts": _count_by(active_constraint_records, "constraint_kind"),
        "integration_target_count": len(active_integration_targets),
        "integration_target_counts": _count_by(active_integration_targets, "target_kind"),
        "run_contract_count": len(run_contracts),
        "run_contract_status_counts": _count_by(run_contracts, "status"),
        "promotion_counts": _count_by(promotions, "status"),
        "knowledge_conflict_count": len(knowledge_conflicts),
        "template_ok": not template_issues,
        "template_issues": template_issues[:10],
        "verification_hotspots": verification_hotspots[:5],
        "workspace_blockers": (
            [{"status": "blocked", "reason": manifest.get("status_reason", "") or "workspace marked blocked"}]
            if manifest.get("status") == "blocked"
            else []
        ),
        "active_items": active_items[:5],
        "blocked_items": blocked_items[:5],
        "pending_tests": pending_tests[:5],
        "open_questions": [item for item in active_knowledge if item.get("record_kind") == "open_question"][:5],
        "context_records": active_context_records[:10],
        "constraint_records": active_constraint_records[:10],
        "knowledge_conflicts": knowledge_conflicts[:5],
        "integration_candidates": integration_candidates[:5],
        "integration_targets": active_integration_targets[:10],
        "run_contracts": run_contracts[:10],
        "active_run": active_run,
        "active_run_context_units": active_run_context_units,
        "active_run_command_count": active_run_command_count,
        "latest_run": latest_run,
        "artifacts": artifact_links[:10],
        "contextualization_summary": contextualization_summary,
        "latest_contextualization_run": latest_contextualization_run,
        "latest_contextualization_candidates": latest_contextualization_candidates,
        "current_contextualization_seed": current_contextualization_seed,
        "proof_summary": {
            **proof_summary,
            "proof_records": proof_summary["proof_records"][:20],
        },
    }
    stage_gaps = _stage_gaps_for_snapshot(snapshot)
    snapshot["stage_ok"] = not stage_gaps
    snapshot["stage_gaps"] = stage_gaps[:10]
    inquiry_queue, questions_for_user = _derive_inquiry_queue(snapshot=snapshot)
    snapshot["inquiry_queue"] = inquiry_queue[:20]
    snapshot["questions_for_user"] = questions_for_user
    snapshot["inquiry_counts"] = _count_by(inquiry_queue, "inquiry_kind")

    if not write_files:
        return snapshot

    materialized = _workspace_materialized_paths(root, workspace_id)
    materialized["diary"] = _workspace_context_dir(root, workspace_id) / "diary.md"
    materialized["artifacts"] = _workspace_context_dir(root, workspace_id) / "artifacts.md"
    materialized["artifacts_json"] = _workspace_context_dir(root, workspace_id) / "artifacts.json"
    materialized["context"] = _workspace_context_dir(root, workspace_id) / "context.md"
    materialized["context_json"] = _workspace_context_dir(root, workspace_id) / "context.json"
    materialized["constraints"] = _workspace_context_dir(root, workspace_id) / "constraints.md"
    materialized["constraints_json"] = _workspace_context_dir(root, workspace_id) / "constraints.json"
    materialized["integration_targets"] = _workspace_context_dir(root, workspace_id) / "integration_targets.md"
    materialized["integration_targets_json"] = _workspace_context_dir(root, workspace_id) / "integration_targets.json"
    materialized["runs"] = _workspace_context_dir(root, workspace_id) / "runs.md"
    materialized["runs_json"] = _workspace_context_dir(root, workspace_id) / "runs.json"
    materialized["contextualization"] = _workspace_context_dir(root, workspace_id) / "contextualization.md"
    materialized["contextualization_json"] = _workspace_context_dir(root, workspace_id) / "contextualization.json"
    materialized["proof"] = _workspace_context_dir(root, workspace_id) / "proof.md"
    materialized["proof_json"] = _workspace_context_dir(root, workspace_id) / "proof.json"
    materialized["founder"] = _workspace_context_dir(root, workspace_id) / "founder.md"
    write_json(materialized["summary"], snapshot)
    write_json(materialized["board_json"], {"work_items": work_items, "counts": snapshot["work_item_counts"]})
    write_json(materialized["tests_json"], {"tests": tests, "counts": snapshot["test_counts"]})
    write_json(
        materialized["knowledge_json"],
        {"records": active_knowledge, "counts": snapshot["knowledge_counts"], "conflicts": knowledge_conflicts},
    )
    write_json(materialized["artifacts_json"], {"artifacts": artifact_links, "counts": snapshot["artifact_counts"]})
    write_json(materialized["context_json"], {"records": active_context_records, "counts": snapshot["context_counts"]})
    write_json(materialized["constraints_json"], {"records": active_constraint_records, "counts": snapshot["constraint_counts"]})
    write_json(
        materialized["integration_targets_json"],
        {"targets": active_integration_targets, "counts": snapshot["integration_target_counts"]},
    )
    write_json(
        materialized["runs_json"],
        {
            "runs": run_contracts,
            "counts": snapshot["run_contract_status_counts"],
            "active_run": active_run,
            "active_run_context_units": active_run_context_units,
            "active_run_command_count": active_run_command_count,
            "latest_run": latest_run,
        },
    )
    write_json(
        materialized["contextualization_json"],
        {
            "summary": snapshot["contextualization_summary"],
            "latest_run": snapshot.get("latest_contextualization_run"),
            "latest_candidates": snapshot.get("latest_contextualization_candidates", []),
            "current_seed": snapshot.get("current_contextualization_seed", {}),
            "semantic_assist_used": bool((snapshot.get("latest_contextualization_run") or {}).get("semantic_assist_used", False)),
        },
    )
    write_json(materialized["proof_json"], snapshot["proof_summary"])
    write_json(
        materialized["integration_candidates_json"],
        {"promotions": promotions, "counts": snapshot["promotion_counts"]},
    )

    brief_lines = [
        f"# Holodeck Brief — {snapshot['label']}",
        "",
        f"- workspace_id: {workspace_id}",
        f"- status: {snapshot['status']}",
        f"- status_reason: {snapshot['status_reason'] or 'none'}",
        f"- maturation_stage: {snapshot['maturation_stage']}",
        f"- goal: {snapshot['goal'] or 'none'}",
        f"- purpose: {snapshot['purpose'] or 'none'}",
        f"- success_condition: {snapshot['success_condition'] or 'none'}",
        f"- linked_sessions: {', '.join(snapshot['linked_session_ids']) if snapshot['linked_session_ids'] else 'none'}",
        f"- linked_task_packs: {', '.join(snapshot['linked_task_pack_ids']) if snapshot['linked_task_pack_ids'] else 'none'}",
        "",
        "## Active Work",
        "",
    ]
    brief_lines.extend(
        [f"- {item['work_item_id']}: {item['title']} [{item['status']}]" for item in active_items] or ["- none"]
    )
    brief_lines.extend(["", "## Context", ""])
    brief_lines.extend(
        [
            f"- {item['context_id']}::{item['context_kind']}::{item['title']} [{item.get('domain') or 'general'}]"
            for item in active_context_records[:5]
        ]
        or ["- none"]
    )
    brief_lines.extend(["", "## Contextualization", ""])
    brief_lines.append(
        f"- status: {snapshot['contextualization_summary'].get('status', 'unresolved')} :: {'fresh' if snapshot['contextualization_summary'].get('fresh') else 'stale' if snapshot['contextualization_summary'].get('stale') else 'not_run'}"
    )
    brief_lines.append(f"- semantic_assist_used: {bool((snapshot.get('latest_contextualization_run') or {}).get('semantic_assist_used', False))}")
    brief_lines.append(f"- message: {snapshot['contextualization_summary'].get('message', 'none')}")
    brief_lines.extend(["", "## Constraints", ""])
    brief_lines.extend(
        [
            f"- {item['constraint_id']}::{item['constraint_kind']}::{item['severity']} :: {item['statement']}"
            for item in active_constraint_records[:5]
        ]
        or ["- none"]
    )
    brief_lines.extend(["", "## Blockers", ""])
    brief_lines.extend([f"- workspace :: {item['reason']}" for item in snapshot["workspace_blockers"]] or [])
    brief_lines.extend(
        [
            f"- {item['work_item_id']}: {item['title']} [{item['status']}] :: {'; '.join(item.get('blocker_reasons', [])) or 'explicitly blocked'}"
            for item in blocked_items
        ]
        or ["- none"]
    )
    brief_lines.extend(["", "## Pending Tests", ""])
    brief_lines.extend([f"- {item['test_id']}: {item['intent']}" for item in pending_tests] or ["- none"])
    brief_lines.extend(["", "## Active Run", ""])
    if active_run:
        brief_lines.extend(
            [
                f"- run_id: {active_run['run_id']}",
                f"- purpose: {active_run.get('purpose') or 'none'}",
                f"- work_item: {active_run.get('active_work_item_id') or 'none'}",
                f"- stage: {active_run.get('active_maturation_stage') or 'none'}",
                f"- context_usage: {active_run_context_units}/{active_run.get('context_budget', 0)}",
                f"- command_count: {active_run_command_count}",
                f"- verification_plan: {active_run.get('verification_plan') or 'none'}",
            ]
        )
    else:
        brief_lines.append("- none")
    brief_lines.extend(["", "## Integration Targets", ""])
    brief_lines.extend(
        [
            f"- {item['target_id']}::{item['target_kind']}::{item['title']} -> {item.get('destination_ref') or 'none'} [{item.get('status', 'candidate')}]"
            for item in active_integration_targets[:5]
        ]
        or ["- none"]
    )
    brief_lines.extend(["", "## Stage Gaps", ""])
    brief_lines.extend([f"- {item['stage']}::{item['code']}: {item['message']}" for item in stage_gaps] or ["- none"])
    brief_lines.extend(["", "## Verification Hotspots", ""])
    brief_lines.extend(
        [f"- {item['test_id']}: {item['intent']} :: {item['latest_result']} x{item['failure_streak']}" for item in verification_hotspots]
        or ["- none"]
    )
    brief_lines.extend(["", "## Proof Posture", ""])
    brief_lines.append(f"- posture: {snapshot['proof_summary']['proof_posture']}")
    brief_lines.append(
        f"- required_surfaces: {', '.join(snapshot['proof_summary']['required_surfaces']) if snapshot['proof_summary']['required_surfaces'] else 'none'}"
    )
    brief_lines.append(
        f"- verified_surfaces: {', '.join(snapshot['proof_summary']['verified_surfaces']) if snapshot['proof_summary']['verified_surfaces'] else 'none'}"
    )
    brief_lines.append(
        f"- unverified_required_surfaces: {', '.join(snapshot['proof_summary']['unverified_required_surfaces']) if snapshot['proof_summary']['unverified_required_surfaces'] else 'none'}"
    )
    brief_lines.extend(["", "## Knowledge Conflicts", ""])
    brief_lines.extend(
        [
            f"- {item['record_kind']}::{item['title']} :: {' || '.join(item['record_ids'])}"
            for item in knowledge_conflicts[:5]
        ]
        or ["- none"]
    )
    if founder_fields:
        brief_lines.extend(["", "## Founder Context", ""])
        brief_lines.extend([f"- {key}: {value}" for key, value in founder_fields.items()] or ["- none"])
    brief_lines.extend(["", "## Template Issues", ""])
    brief_lines.extend([f"- {item['field']}: {item['message']}" for item in template_issues] or ["- none"])
    write_markdown(materialized["brief"], "\n".join(brief_lines))

    board_lines = [
        f"# Holodeck Board — {snapshot['label']}",
        "",
        "| ID | Status | Kind | Priority | Guard | Parent | Depends | Blockers | Task | Acceptance |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in work_items:
        acceptance = "; ".join(item.get("acceptance_criteria", [])) or "none"
        parent = item.get("parent_id") or "none"
        depends = ", ".join(item.get("depends_on", [])) or "none"
        guard = item.get("guard_status") or "not_required"
        blockers = "; ".join(item.get("blocker_reasons", [])) or "none"
        board_lines.append(
            f"| {item['work_item_id']} | `{item['status']}` | {item['kind']} | {item['priority']} | `{guard}` | {parent} | {depends} | {blockers} | {item['title']} | {acceptance} |"
        )
    if not work_items:
        board_lines.append("| none | `none` | none | none | none | none | none | none | none | none |")
    write_markdown(materialized["board"], "\n".join(board_lines))

    test_lines = [
        f"# Holodeck Tests — {snapshot['label']}",
        "",
        "| Test ID | Work Item | Kind | Latest Result | Intent | Evidence |",
        "|---|---|---|---|---|---|",
    ]
    for item in tests:
        evidence = item.get("latest_evidence_ref") or "none"
        test_lines.append(
            f"| {item['test_id']} | {item['work_item_id']} | {item['test_kind']} | `{item['latest_result']}` | {item['intent']} | {evidence} |"
        )
    if not tests:
        test_lines.append("| none | none | none | `not_run` | none | none |")
    write_markdown(materialized["tests"], "\n".join(test_lines))

    proof_lines = [
        f"# Holodeck Proof — {snapshot['label']}",
        "",
        f"- posture: {snapshot['proof_summary']['proof_posture']}",
        f"- highest_verified_surface: {snapshot['proof_summary']['highest_verified_surface'] or 'none'}",
        f"- required_surfaces: {', '.join(snapshot['proof_summary']['required_surfaces']) if snapshot['proof_summary']['required_surfaces'] else 'none'}",
        f"- verified_surfaces: {', '.join(snapshot['proof_summary']['verified_surfaces']) if snapshot['proof_summary']['verified_surfaces'] else 'none'}",
        f"- unverified_required_surfaces: {', '.join(snapshot['proof_summary']['unverified_required_surfaces']) if snapshot['proof_summary']['unverified_required_surfaces'] else 'none'}",
        "",
        "## Proof Records",
        "",
    ]
    proof_lines.extend(
        [
            f"- {item['timestamp']}::{item['surface']}::{item['status']} :: {item['summary'] or item['notes'] or item['proof_id']}"
            for item in snapshot["proof_summary"]["proof_records"]
        ]
        or ["- none"]
    )
    write_markdown(materialized["proof"], "\n".join(proof_lines))

    knowledge_lines = [
        f"# Holodeck Knowledge — {snapshot['label']}",
        "",
        "| Kind | Posture | Title | Confidence | Statement |",
        "|---|---|---|---|---|",
    ]
    for item in active_knowledge:
        knowledge_lines.append(
            f"| {item['record_kind']} | {item['claim_posture']} | {item['title']} | {item['confidence']} | {item['statement']} |"
        )
    if not active_knowledge:
        knowledge_lines.append("| none | none | none | 0.0 | none |")
    knowledge_lines.extend(["", "## Conflicts", ""])
    knowledge_lines.extend(
        [
            f"- {item['record_kind']}::{item['title']} :: {' || '.join(item['record_ids'])} :: {' <> '.join(item['statements'])}"
            for item in knowledge_conflicts
        ]
        or ["- none"]
    )
    write_markdown(materialized["knowledge"], "\n".join(knowledge_lines))
    context_lines = [
        f"# Holodeck Context — {snapshot['label']}",
        "",
        "| Context ID | Kind | Domain | Status | Confidence | Title | Summary |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in active_context_records:
        context_lines.append(
            f"| {item['context_id']} | {item['context_kind']} | {item.get('domain') or 'general'} | `{item.get('status', 'active')}` | {item.get('confidence', 0.5)} | {item['title']} | {item.get('summary', '') or 'none'} |"
        )
    if not active_context_records:
        context_lines.append("| none | none | general | `none` | 0.0 | none | none |")
    write_markdown(materialized["context"], "\n".join(context_lines))
    contextualization_lines = [
        f"# Holodeck Contextualization — {snapshot['label']}",
        "",
        f"- status: {snapshot['contextualization_summary'].get('status', 'unresolved')}",
        f"- resolved: {snapshot['contextualization_summary'].get('resolved', False)}",
        f"- fresh: {snapshot['contextualization_summary'].get('fresh', False)}",
        f"- stale: {snapshot['contextualization_summary'].get('stale', False)}",
        f"- latest_run: {snapshot['contextualization_summary'].get('latest_run_id') or 'none'}",
        f"- seed_fingerprint: {snapshot['contextualization_summary'].get('seed_fingerprint') or 'none'}",
        f"- semantic_assist_used: {bool((snapshot.get('latest_contextualization_run') or {}).get('semantic_assist_used', False))}",
        "",
        f"- message: {snapshot['contextualization_summary'].get('message', 'none')}",
        "",
        "## Source Layers",
        "",
    ]
    contextualization_lines.extend(
        [f"- {item}" for item in snapshot["contextualization_summary"].get("source_layers_consulted", [])] or ["- none"]
    )
    contextualization_lines.extend(["", "## Latest Candidates", ""])
    contextualization_lines.extend(
        [
            f"- {item.get('source_layer', 'unknown')}::{item.get('disposition', 'retained')}::{item.get('semantic_label', item.get('title', ''))} :: {item.get('why_it_matters', item.get('statement', ''))}"
            for item in snapshot.get("latest_contextualization_candidates", [])
        ]
        or ["- none"]
    )
    write_markdown(materialized["contextualization"], "\n".join(contextualization_lines))
    constraint_lines = [
        f"# Holodeck Constraints — {snapshot['label']}",
        "",
        "| Constraint ID | Kind | Severity | Status | Applies To | Statement |",
        "|---|---|---|---|---|---|",
    ]
    for item in active_constraint_records:
        constraint_lines.append(
            f"| {item['constraint_id']} | {item['constraint_kind']} | {item.get('severity', 'required')} | `{item.get('status', 'active')}` | {item.get('applies_to') or 'workspace'} | {item.get('statement', '') or 'none'} |"
        )
    if not active_constraint_records:
        constraint_lines.append("| none | none | required | `none` | workspace | none |")
    write_markdown(materialized["constraints"], "\n".join(constraint_lines))
    write_markdown(
        materialized["diary"],
        "\n".join(_workspace_diary_lines(workspace_id, events, work_item_rows, test_run_rows, knowledge, promotions)),
    )
    artifact_lines = [
        f"# Holodeck Artifacts — {snapshot['label']}",
        "",
        "| Artifact ID | Kind | Title | Source | Status |",
        "|---|---|---|---|---|",
    ]
    for item in artifact_links:
        artifact_lines.append(
            f"| {item['artifact_id']} | {item['artifact_kind']} | {item['title']} | {item.get('source_ref', 'none')} | {item.get('status', 'active')} |"
        )
    if not artifact_links:
        artifact_lines.append("| none | none | none | none | none |")
    write_markdown(materialized["artifacts"], "\n".join(artifact_lines))
    integration_target_lines = [
        f"# Holodeck Integration Targets — {snapshot['label']}",
        "",
        "| Target ID | Kind | Status | Destination | Required Evidence | Title |",
        "|---|---|---|---|---|---|",
    ]
    for item in active_integration_targets:
        required_evidence = ", ".join(item.get("required_evidence_refs", [])) or "none"
        integration_target_lines.append(
            f"| {item['target_id']} | {item['target_kind']} | `{item.get('status', 'candidate')}` | {item.get('destination_ref') or 'none'} | {required_evidence} | {item['title']} |"
        )
    if not active_integration_targets:
        integration_target_lines.append("| none | none | `none` | none | none | none |")
    write_markdown(materialized["integration_targets"], "\n".join(integration_target_lines))
    run_lines = [
        f"# Holodeck Runs — {snapshot['label']}",
        "",
        "| Run ID | Status | Work Item | Stage | Budget | Purpose | Verification | Stop Conditions |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in run_contracts:
        stop_conditions = "; ".join(item.get("stop_conditions", [])) or "none"
        run_lines.append(
            f"| {item['run_id']} | `{item.get('status', 'active')}` | {item.get('active_work_item_id') or 'none'} | {item.get('active_maturation_stage') or 'none'} | {item.get('context_budget', 0)} | {item.get('purpose') or 'none'} | {item.get('verification_plan') or 'none'} | {stop_conditions} |"
        )
    if not run_contracts:
        run_lines.append("| none | `none` | none | none | 0 | none | none | none |")
    write_markdown(materialized["runs"], "\n".join(run_lines))
    if founder_fields:
        founder_lines = [
            f"# Holodeck Founder Context — {snapshot['label']}",
            "",
            f"- wedge: {founder_fields.get('wedge', 'none')}",
            f"- user: {founder_fields.get('user', 'none')}",
            f"- moat: {founder_fields.get('moat', 'none')}",
            f"- gtm_risk: {founder_fields.get('gtm_risk', 'none')}",
            f"- launch_metric: {founder_fields.get('launch_metric', 'none')}",
        ]
        write_markdown(materialized["founder"], "\n".join(founder_lines))
    elif materialized["founder"].exists():
        materialized["founder"].unlink()

    promotion_lines = [
        f"# Holodeck Integration Candidates — {snapshot['label']}",
        "",
        "| Promotion ID | Source Kind | Target Kind | Status | Title | Reason |",
        "|---|---|---|---|---|---|",
    ]
    for item in promotions:
        promotion_lines.append(
            f"| {item['promotion_id']} | {item['source_kind']} | {item['target_kind']} | `{item['status']}` | {item['title']} | {item['reason']} |"
        )
    if not promotions:
        promotion_lines.append("| none | none | none | `none` | none | none |")
    write_markdown(materialized["integration_candidates"], "\n".join(promotion_lines))

    handoff_lines = [
        f"# Holodeck Handoff — {snapshot['label']}",
        "",
        f"- goal: {snapshot['goal'] or 'none'}",
        f"- purpose: {snapshot['purpose'] or 'none'}",
        f"- success_condition: {snapshot['success_condition'] or 'none'}",
        f"- status: {snapshot['status']}",
        f"- status_reason: {snapshot['status_reason'] or 'none'}",
        f"- maturation_stage: {snapshot['maturation_stage']}",
        "",
        "## Next Work",
        "",
    ]
    handoff_lines.extend(
        [f"- {item['work_item_id']}: {item['title']} [{item['status']}]" for item in active_items] or ["- none"]
    )
    handoff_lines.extend(["", "## Context", ""])
    handoff_lines.extend(
        [
            f"- {item['context_id']}::{item['context_kind']}::{item['title']} :: {item.get('summary', '') or 'none'}"
            for item in active_context_records[:5]
        ]
        or ["- none"]
    )
    handoff_lines.extend(["", "## Constraints", ""])
    handoff_lines.extend(
        [
            f"- {item['constraint_id']}::{item['constraint_kind']}::{item['severity']} :: {item['statement']}"
            for item in active_constraint_records[:5]
        ]
        or ["- none"]
    )
    handoff_lines.extend(["", "## Blockers", ""])
    handoff_lines.extend([f"- workspace :: {item['reason']}" for item in snapshot["workspace_blockers"]] or [])
    handoff_lines.extend(
        [
            f"- {item['work_item_id']}: {item['title']} [{item['status']}] :: {'; '.join(item.get('blocker_reasons', [])) or 'explicitly blocked'}"
            for item in blocked_items
        ]
        or ["- none"]
    )
    handoff_lines.extend(["", "## Pending Tests", ""])
    handoff_lines.extend([f"- {item['test_id']}: {item['intent']}" for item in pending_tests] or ["- none"])
    handoff_lines.extend(["", "## Active Run", ""])
    if active_run:
        handoff_lines.extend(
            [
                f"- {active_run['run_id']} :: {active_run.get('purpose') or 'none'}",
                f"- work_item: {active_run.get('active_work_item_id') or 'none'}",
                f"- stage: {active_run.get('active_maturation_stage') or 'none'}",
                f"- context_usage: {active_run_context_units}/{active_run.get('context_budget', 0)}",
                f"- command_count: {active_run_command_count}",
                f"- stop_conditions: {'; '.join(active_run.get('stop_conditions', [])) or 'none'}",
            ]
        )
    else:
        handoff_lines.append("- none")
    handoff_lines.extend(["", "## Integration Targets", ""])
    handoff_lines.extend(
        [
            f"- {item['target_id']}::{item['target_kind']}::{item['title']} -> {item.get('destination_ref') or 'none'} [{item.get('status', 'candidate')}]"
            for item in active_integration_targets[:5]
        ]
        or ["- none"]
    )
    handoff_lines.extend(["", "## Stage Gaps", ""])
    handoff_lines.extend([f"- {item['stage']}::{item['code']}: {item['message']}" for item in stage_gaps] or ["- none"])
    handoff_lines.extend(["", "## Verification Hotspots", ""])
    handoff_lines.extend(
        [f"- {item['test_id']}: {item['intent']} :: {item['latest_result']} x{item['failure_streak']}" for item in verification_hotspots]
        or ["- none"]
    )
    handoff_lines.extend(["", "## Knowledge Conflicts", ""])
    handoff_lines.extend(
        [
            f"- {item['record_kind']}::{item['title']} :: {' || '.join(item['record_ids'])}"
            for item in knowledge_conflicts[:5]
        ]
        or ["- none"]
    )
    handoff_lines.extend(["", "## Integration Candidates", ""])
    handoff_lines.extend(
        [f"- {item['title']} [{item['status']}] -> {item['target_kind']}" for item in integration_candidates[:5]]
        or ["- none"]
    )
    handoff_lines.extend(["", "## Artifacts", ""])
    handoff_lines.extend([f"- {item['artifact_kind']}: {item['title']}" for item in artifact_links[:5]] or ["- none"])
    if founder_fields:
        handoff_lines.extend(["", "## Founder Context", ""])
        handoff_lines.extend([f"- {key}: {value}" for key, value in founder_fields.items()] or ["- none"])
    handoff_lines.extend(["", "## Template Issues", ""])
    handoff_lines.extend([f"- {item['field']}: {item['message']}" for item in template_issues] or ["- none"])
    handoff_lines.extend(["", "## Linked Sessions", ""])
    handoff_lines.extend([f"- {item}" for item in snapshot["linked_session_ids"]] or ["- none"])
    write_markdown(materialized["handoff"], "\n".join(handoff_lines))

    blocked_summary = "none"
    if snapshot["workspace_blockers"]:
        blocked_summary = f"workspace :: {snapshot['workspace_blockers'][0]['reason']}"
    elif blocked_items:
        primary_reason = blocked_items[0].get("blocker_reasons", ["explicitly blocked"])[0]
        blocked_summary = f"{blocked_items[0]['title']} :: {primary_reason}"

    mobile_lines = [
        f"# {snapshot['label']}",
        "",
        f"- goal: {snapshot['goal'] or 'none'}",
        f"- stage: {snapshot['maturation_stage']}",
        f"- run: {active_run['run_id'] if active_run else 'none'}",
        f"- active: {active_items[0]['title'] if active_items else 'none'}",
        f"- blocked: {blocked_summary}",
        f"- next_test: {pending_tests[0]['intent'] if pending_tests else 'none'}",
        f"- promote: {integration_candidates[0]['title'] if integration_candidates else 'none'}",
        f"- launch_metric: {founder_fields.get('launch_metric', 'none') if founder_fields else 'none'}",
    ]
    write_markdown(materialized["mobile"], "\n".join(mobile_lines))
    return snapshot | {"materialized_paths": {key: str(value) for key, value in materialized.items()}}

def holodeck_create(root: Path, args: argparse.Namespace) -> dict:
    workspace_id = args.workspace_id or make_id("workspace")
    if _workspace_exists(root, workspace_id):
        raise ValueError(f"Workspace already exists: {workspace_id}")
    ensure_dir(_workspace_dir(root, workspace_id))
    ensure_dir(_workspace_context_dir(root, workspace_id))
    template_fields = _founder_fields_from_args(args)
    _validate_template_manifest_state(template_key=args.template_key or "", template_fields=template_fields)
    for path in _workspace_source_paths(root, workspace_id):
        ensure_dir(path.parent)
        path.touch(exist_ok=True)
    manifest = {
        "workspace_id": workspace_id,
        "label": args.title,
        "status": "active",
        "maturation_stage": "raw",
        "goal": args.goal,
        "purpose": args.purpose,
        "success_condition": args.success_condition or "",
        "scope_in": list(args.scope_in or []),
        "scope_out": list(args.scope_out or []),
        "template_key": args.template_key or "",
        "template_fields": template_fields,
        "domain_overlays": _split_csv(args.domains),
        "linked_session_ids": [],
        "linked_task_pack_ids": [],
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "closed_at": None,
    }
    write_json(_workspace_manifest_path(root, workspace_id), manifest)
    _append_workspace_event(
        root,
        workspace_id,
        actor="agent",
        kind="workspace_created",
        summary=f"Created Holodeck {args.title}",
        content=args.purpose,
    )
    auto_contextualization = _maybe_auto_contextualize(
        root,
        workspace_id,
        trigger="create",
        reason="Automatic contextualization after workspace creation.",
    )
    if auto_contextualization.get("triggered"):
        auto_contextualization["contextualization_summary"] = _materialize_workspace_snapshot(root, workspace_id, write_files=False).get(
            "contextualization_summary",
            {},
        )
    return manifest | {"auto_contextualization": auto_contextualization}


def holodeck_event(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    return _append_workspace_event(
        root,
        args.workspace_id,
        actor=args.actor,
        kind=args.kind,
        summary=args.summary,
        content=args.content or "",
        source_refs=_split_csv(args.source_refs),
        related_work_item_ids=_split_csv(args.work_item_ids),
        related_test_ids=_split_csv(args.test_ids),
        tags=_split_csv(args.tags),
        context_units=args.context_units or 0,
        command_ref=args.command_ref or "",
    )


def holodeck_log_context(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    if args.units <= 0:
        raise ValueError("Context units must be greater than zero.")
    return _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="context_loaded",
        summary=args.summary,
        content=args.reason or "",
        source_refs=_split_csv(args.source_refs),
        related_work_item_ids=_split_csv(args.work_item_ids),
        tags=["context_load"],
        context_units=args.units,
    )


def holodeck_log_command(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    return _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="command_executed",
        summary=args.summary,
        content=args.reason or "",
        source_refs=_split_csv(args.source_refs),
        related_work_item_ids=_split_csv(args.work_item_ids),
        tags=["command_exec"],
        command_ref=args.command_ref,
    )


def holodeck_ingest_artifact(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    artifact = {
        "artifact_id": args.artifact_id or make_id("artifact"),
        "workspace_id": args.workspace_id,
        "artifact_kind": args.artifact_kind,
        "title": args.title,
        "source_ref": args.source_ref,
        "source_type": args.source_type,
        "provenance": args.provenance or "linked",
        "summary": args.summary or "",
        "status": args.status or "active",
        "linked_at": utc_now(),
        "attributes": {},
    }
    artifact = _append_workspace_artifact_link(root, args.workspace_id, artifact)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="artifact_linked",
        summary=f"Linked artifact {args.title}",
        content=args.summary or "",
        source_refs=[args.source_ref],
    )
    return artifact | {
        "auto_contextualization": _maybe_auto_contextualize(
            root,
            args.workspace_id,
            trigger="ingest_artifact",
            reason="Automatic contextualization after artifact ingestion.",
        )
    }


def holodeck_link_session(root: Path, args: argparse.Namespace) -> dict:
    manifest = _load_workspace_manifest(root, args.workspace_id)
    session_manifest_path = session_dir(root, args.session_id) / "manifest.json"
    if not session_manifest_path.exists():
        raise FileNotFoundError(f"Session not found: {args.session_id}")
    linked_sessions = list(manifest.get("linked_session_ids", []))
    if args.session_id not in linked_sessions:
        linked_sessions.append(args.session_id)
    manifest["linked_session_ids"] = linked_sessions
    manifest["updated_at"] = utc_now()
    write_json(_workspace_manifest_path(root, args.workspace_id), manifest)
    artifact = {
        "artifact_id": make_id("artifact"),
        "workspace_id": args.workspace_id,
        "artifact_kind": "session",
        "title": args.session_id,
        "source_ref": f"session:{args.session_id}",
        "source_type": "session_manifest",
        "provenance": "linked",
        "summary": "Linked session context",
        "status": "active",
        "linked_at": utc_now(),
        "attributes": {},
    }
    _append_workspace_artifact_link(root, args.workspace_id, artifact)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="artifact_linked",
        summary=f"Linked session {args.session_id}",
        source_refs=[f"session:{args.session_id}"],
    )
    return {
        "workspace_id": args.workspace_id,
        "linked_session_ids": linked_sessions,
        "auto_contextualization": _maybe_auto_contextualize(
            root,
            args.workspace_id,
            trigger="link_session",
            reason="Automatic contextualization after linking session context.",
        ),
    }


def holodeck_update(root: Path, args: argparse.Namespace) -> dict:
    manifest = _load_workspace_manifest(root, args.workspace_id)
    changed_fields = []
    next_template_key = manifest.get("template_key", "")
    if args.title is not None:
        manifest["label"] = args.title
        changed_fields.append("label")
    if args.goal is not None:
        manifest["goal"] = args.goal
        changed_fields.append("goal")
    if args.purpose is not None:
        manifest["purpose"] = args.purpose
        changed_fields.append("purpose")
    if args.success_condition is not None:
        manifest["success_condition"] = args.success_condition
        changed_fields.append("success_condition")
    if args.scope_in is not None:
        manifest["scope_in"] = list(args.scope_in)
        changed_fields.append("scope_in")
    if args.scope_out is not None:
        manifest["scope_out"] = list(args.scope_out)
        changed_fields.append("scope_out")
    if args.template_key is not None:
        manifest["template_key"] = args.template_key
        next_template_key = args.template_key
        changed_fields.append("template_key")
        if next_template_key != "founder" and manifest.get("template_fields"):
            manifest["template_fields"] = {}
            changed_fields.append("template_fields")
    if args.domains is not None:
        manifest["domain_overlays"] = _split_csv(args.domains)
        changed_fields.append("domain_overlays")
    founder_updates = _founder_fields_from_args(args)
    if founder_updates:
        _validate_template_manifest_state(template_key=next_template_key, template_fields=founder_updates)
        template_fields = dict(manifest.get("template_fields", {}))
        template_fields.update(founder_updates)
        manifest["template_fields"] = template_fields
        changed_fields.extend([f"founder:{key}" for key in founder_updates])
    if not changed_fields:
        return manifest | {"updated_fields": []}
    manifest["updated_at"] = utc_now()
    write_json(_workspace_manifest_path(root, args.workspace_id), manifest)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="workspace_updated",
        summary=f"Updated Holodeck {manifest.get('label', args.workspace_id)}",
        content=", ".join(changed_fields),
        tags=changed_fields,
    )
    auto_contextualization = _maybe_auto_contextualize(
        root,
        args.workspace_id,
        trigger="update",
        reason="Automatic contextualization after workspace update.",
    )
    if auto_contextualization.get("triggered"):
        auto_contextualization["contextualization_summary"] = _materialize_workspace_snapshot(root, args.workspace_id, write_files=False).get(
            "contextualization_summary",
            {},
        )
    return manifest | {"updated_fields": changed_fields, "auto_contextualization": auto_contextualization}


def holodeck_advance_stage(root: Path, args: argparse.Namespace) -> dict:
    manifest = _load_workspace_manifest(root, args.workspace_id)
    stage = _validate_maturation_stage(args.stage)
    if manifest.get("maturation_stage", "raw") == stage:
        return manifest | {"already_in_stage": True}
    previous_stage = manifest.get("maturation_stage", "raw")
    manifest["maturation_stage"] = stage
    manifest["updated_at"] = utc_now()
    write_json(_workspace_manifest_path(root, args.workspace_id), manifest)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="maturation_stage_changed",
        summary=f"Advanced maturation stage from {previous_stage} to {stage}",
        content=args.reason or "",
        tags=[previous_stage, stage],
    )
    snapshot = _materialize_workspace_snapshot(root, args.workspace_id, write_files=True)
    return manifest | {"previous_maturation_stage": previous_stage, "current_snapshot": snapshot}


def _workspace_has_passing_test(root: Path, workspace_id: str, work_item_id: str) -> bool:
    work_items = {
        item["work_item_id"]: item
        for item in _reduce_work_items(read_jsonl(_workspace_work_item_events_path(root, workspace_id)))
    }
    linked_tests = set(work_items.get(work_item_id, {}).get("linked_tests", []))
    tests = _reduce_tests(
        read_jsonl(_workspace_test_cases_path(root, workspace_id)),
        read_jsonl(_workspace_test_runs_path(root, workspace_id)),
    )
    return any(
        item.get("latest_result") == "passing"
        and (item.get("work_item_id") == work_item_id or item.get("test_id") in linked_tests)
        for item in tests
    )


def holodeck_add_work_item(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    work_item_id = args.work_item_id or f"work-item-{slugify(args.title)}-{make_id('w')[-4:]}"
    work_items_by_id = {
        item["work_item_id"]: item
        for item in _reduce_work_items(read_jsonl(_workspace_work_item_events_path(root, args.workspace_id)))
    }
    acceptance = list(args.acceptance_criteria or [])
    guard_status = args.guard_status or "not_required"
    work_items_by_id[work_item_id] = {
        "work_item_id": work_item_id,
        "title": args.title,
        "kind": args.kind,
        "status": args.status,
        "priority": args.priority,
        "owner": args.owner or "",
        "parent_id": args.parent_id or "",
        "depends_on": list(args.depends_on or []),
        "linked_artifacts": list(args.linked_artifacts or []),
        "linked_tests": list(args.linked_tests or []),
        "guard_status": guard_status,
        "guard_request": args.guard_request or "",
        "guard_purpose": args.guard_purpose or "",
        "guard_paths": _split_csv(args.guard_paths),
        "acceptance_criteria": acceptance,
        "constraints": list(args.constraints or []),
    }
    _validate_work_item_transition(
        work_items_by_id=work_items_by_id,
        work_item_id=work_item_id,
        kind=args.kind,
        status=args.status,
        parent_id=args.parent_id or "",
        depends_on=list(args.depends_on or []),
        acceptance_criteria=acceptance,
        guard_status=guard_status,
    )
    event = _append_work_item_event(
        root,
        args.workspace_id,
        work_item_id,
        "create",
        {
            "title": args.title,
            "kind": args.kind,
            "status": args.status,
            "priority": args.priority,
            "owner": args.owner or "",
            "parent_id": args.parent_id or "",
            "depends_on": list(args.depends_on or []),
            "linked_artifacts": list(args.linked_artifacts or []),
            "linked_tests": list(args.linked_tests or []),
            "guard_status": guard_status,
            "guard_request": args.guard_request or "",
            "guard_purpose": args.guard_purpose or "",
            "guard_paths": _split_csv(args.guard_paths),
            "acceptance_criteria": acceptance,
            "constraints": list(args.constraints or []),
        },
    )
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="work_started",
        summary=f"Created work item {args.title}",
        related_work_item_ids=[work_item_id],
    )
    return {
        "work_item_id": work_item_id,
        "event_id": event["event_id"],
        "auto_contextualization": _maybe_auto_contextualize(
            root,
            args.workspace_id,
            trigger="add_work_item",
            reason="Automatic contextualization after work-item expansion.",
        ),
    }


def holodeck_update_work_item(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    work_items_by_id = {
        item["work_item_id"]: item
        for item in _reduce_work_items(read_jsonl(_workspace_work_item_events_path(root, args.workspace_id)))
    }
    current = work_items_by_id.get(args.work_item_id)
    if current is None:
        raise FileNotFoundError(f"Work item not found: {args.work_item_id}")
    emitted = []
    next_acceptance = list(args.acceptance_criteria) if args.acceptance_criteria is not None else list(current.get("acceptance_criteria", []))
    next_guard_status = args.guard_status or current.get("guard_status", "not_required")
    target_status = args.status or current.get("status", "proposed")
    next_parent_id = args.parent_id if args.parent_id is not None else current.get("parent_id", "")
    next_depends_on = list(args.depends_on) if args.depends_on is not None else list(current.get("depends_on", []))
    next_linked_tests = list(args.linked_tests) if args.linked_tests is not None else list(current.get("linked_tests", []))
    candidate = dict(current)
    candidate["status"] = target_status
    candidate["parent_id"] = next_parent_id
    candidate["depends_on"] = next_depends_on
    candidate["linked_tests"] = next_linked_tests
    candidate["acceptance_criteria"] = next_acceptance
    candidate["guard_status"] = next_guard_status
    work_items_by_id[args.work_item_id] = candidate
    _validate_work_item_transition(
        work_items_by_id=work_items_by_id,
        work_item_id=args.work_item_id,
        kind=current.get("kind", "task"),
        status=target_status,
        parent_id=next_parent_id,
        depends_on=next_depends_on,
        acceptance_criteria=next_acceptance,
        guard_status=next_guard_status,
    )
    if target_status == "done" and not _workspace_has_passing_test(root, args.workspace_id, args.work_item_id):
        raise ValueError("A work item cannot be marked done without at least one passing linked test.")
    if args.status:
        emitted.append(_append_work_item_event(root, args.workspace_id, args.work_item_id, "set_status", {"status": args.status}))
    if args.owner is not None:
        emitted.append(_append_work_item_event(root, args.workspace_id, args.work_item_id, "set_owner", {"owner": args.owner}))
    if args.priority:
        emitted.append(_append_work_item_event(root, args.workspace_id, args.work_item_id, "set_priority", {"priority": args.priority}))
    if args.parent_id is not None:
        emitted.append(_append_work_item_event(root, args.workspace_id, args.work_item_id, "set_parent", {"parent_id": args.parent_id}))
    if args.depends_on is not None:
        emitted.append(
            _append_work_item_event(
                root,
                args.workspace_id,
                args.work_item_id,
                "set_dependencies",
                {"depends_on": list(args.depends_on)},
            )
        )
    if args.linked_artifacts is not None:
        emitted.append(
            _append_work_item_event(
                root,
                args.workspace_id,
                args.work_item_id,
                "set_linked_artifacts",
                {"linked_artifacts": list(args.linked_artifacts)},
            )
        )
    if args.linked_tests is not None:
        emitted.append(
            _append_work_item_event(
                root,
                args.workspace_id,
                args.work_item_id,
                "set_linked_tests",
                {"linked_tests": list(args.linked_tests)},
            )
        )
    if any(value is not None for value in [args.guard_status, args.guard_request, args.guard_purpose, args.guard_paths]):
        emitted.append(
            _append_work_item_event(
                root,
                args.workspace_id,
                args.work_item_id,
                "set_guard",
                {
                    "guard_status": args.guard_status or current.get("guard_status", "not_required"),
                    "guard_request": args.guard_request or current.get("guard_request", ""),
                    "guard_purpose": args.guard_purpose or current.get("guard_purpose", ""),
                    "guard_paths": _split_csv(args.guard_paths) if args.guard_paths is not None else list(current.get("guard_paths", [])),
                },
            )
        )
    if args.acceptance_criteria is not None:
        emitted.append(
            _append_work_item_event(
                root,
                args.workspace_id,
                args.work_item_id,
                "set_acceptance",
                {"acceptance_criteria": list(args.acceptance_criteria)},
            )
        )
    if args.constraints is not None:
        emitted.append(
            _append_work_item_event(
                root,
                args.workspace_id,
                args.work_item_id,
                "set_constraints",
                {"constraints": list(args.constraints)},
            )
        )
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="work_started" if args.status in {"ready", "in_progress"} else "note",
        summary=f"Updated work item {args.work_item_id}",
        related_work_item_ids=[args.work_item_id],
    )
    return {"work_item_id": args.work_item_id, "updated_events": [row["event_id"] for row in emitted]}


def holodeck_add_test(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    work_items = {item["work_item_id"]: item for item in _reduce_work_items(read_jsonl(_workspace_work_item_events_path(root, args.workspace_id)))}
    if args.work_item_id not in work_items:
        raise FileNotFoundError(f"Work item not found: {args.work_item_id}")
    test_id = args.test_id or f"test-{slugify(args.intent)}-{make_id('t')[-4:]}"
    payload = {
        "test_id": test_id,
        "workspace_id": args.workspace_id,
        "target_ref": args.target_ref,
        "work_item_id": args.work_item_id,
        "test_kind": args.test_kind,
        "intent": args.intent,
        "command_or_protocol": args.command_or_protocol,
        "expected_signal": args.expected_signal,
        "risk_level": args.risk_level,
        "status": "planned",
        "created_at": utc_now(),
    }
    append_jsonl(_workspace_test_cases_path(root, args.workspace_id), payload)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="test_recorded",
        summary=f"Added test {test_id}",
        related_work_item_ids=[args.work_item_id],
        related_test_ids=[test_id],
    )
    return payload


def holodeck_record_test_run(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    test_cases = {item["test_id"]: item for item in read_jsonl(_workspace_test_cases_path(root, args.workspace_id))}
    if args.test_id not in test_cases:
        raise FileNotFoundError(f"Test not found: {args.test_id}")
    payload = {
        "run_id": make_id("test-run"),
        "workspace_id": args.workspace_id,
        "test_id": args.test_id,
        "timestamp": utc_now(),
        "actor": "agent",
        "result": args.result,
        "evidence_ref": args.evidence_ref or "",
        "notes": args.notes or "",
        "command_or_protocol": args.command_or_protocol or test_cases[args.test_id].get("command_or_protocol", ""),
    }
    append_jsonl(_workspace_test_runs_path(root, args.workspace_id), payload)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="test_recorded",
        summary=f"Recorded test run for {args.test_id}",
        related_work_item_ids=[test_cases[args.test_id]["work_item_id"]],
        related_test_ids=[args.test_id],
        source_refs=[args.evidence_ref] if args.evidence_ref else [],
    )
    return payload


def holodeck_start_run(root: Path, args: argparse.Namespace) -> dict:
    manifest = _load_workspace_manifest(root, args.workspace_id)
    run_status = _validate_run_start_status(args.status)
    work_item_id = args.work_item_id or ""
    stage = args.stage or ""
    if not work_item_id and not stage:
        raise ValueError("Run contracts require either an active work item or an active maturation stage.")
    if stage:
        _validate_maturation_stage(stage)
    if work_item_id:
        work_items = {
            item["work_item_id"]: item
            for item in _reduce_work_items(read_jsonl(_workspace_work_item_events_path(root, args.workspace_id)))
        }
        if work_item_id not in work_items:
            raise FileNotFoundError(f"Work item not found: {work_item_id}")
    stop_conditions = _split_many(args.stop_conditions)
    if not stop_conditions:
        raise ValueError("Run contracts require at least one stop condition.")
    runs = _reduce_run_contracts(read_jsonl(_workspace_run_contracts_path(root, args.workspace_id)))
    current_active = _active_run_contract(runs)
    if current_active is not None:
        raise ValueError(f"An active run already exists: {current_active['run_id']}")
    started_at = utc_now()
    payload = {
        "operation": "create",
        "run_id": args.run_id or make_id("run"),
        "workspace_id": args.workspace_id,
        "active_work_item_id": work_item_id,
        "active_maturation_stage": stage,
        "purpose": args.purpose,
        "allowed_paths": _split_many(args.allowed_paths),
        "blocked_paths": _split_many(args.blocked_paths),
        "allowed_commands": _split_many(args.allowed_commands),
        "expected_outputs": _split_many(args.expected_outputs),
        "verification_plan": args.verification_plan,
        "verification_result": "",
        "context_budget": args.context_budget,
        "stop_conditions": stop_conditions,
        "summary": "",
        "status": run_status,
        "started_at": started_at,
        "ended_at": None,
        "updated_at": started_at,
    }
    append_jsonl(_workspace_run_contracts_path(root, args.workspace_id), payload)
    tags = [value for value in [run_status, stage or manifest.get("maturation_stage", "raw")] if value]
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="run_started",
        summary=f"Started run contract {payload['run_id']}",
        content=args.purpose,
        source_refs=list(payload["allowed_paths"]),
        related_work_item_ids=[work_item_id] if work_item_id else [],
        tags=tags,
    )
    return payload


def holodeck_finish_run(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    finish_status = _validate_run_finish_status(args.status)
    if finish_status == "completed" and not args.verification_result:
        raise ValueError("Completed runs require a verification result.")
    runs = {
        item["run_id"]: item
        for item in _reduce_run_contracts(read_jsonl(_workspace_run_contracts_path(root, args.workspace_id)))
    }
    current = runs.get(args.run_id)
    if current is None:
        raise FileNotFoundError(f"Run contract not found: {args.run_id}")
    if current.get("ended_at"):
        return current | {"updated": False}
    payload = {
        "operation": "update",
        "run_id": args.run_id,
        "workspace_id": args.workspace_id,
        "status": finish_status,
        "summary": args.summary or current.get("summary", ""),
        "verification_result": args.verification_result or current.get("verification_result", ""),
        "ended_at": utc_now(),
        "updated_at": utc_now(),
    }
    append_jsonl(_workspace_run_contracts_path(root, args.workspace_id), payload)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="run_finished",
        summary=f"Finished run contract {args.run_id}",
        content=args.summary or args.verification_result or "",
        related_work_item_ids=[current["active_work_item_id"]] if current.get("active_work_item_id") else [],
        source_refs=list(current.get("allowed_paths", [])),
        tags=[finish_status],
    )
    updated = {
        **current,
        **{key: value for key, value in payload.items() if key not in {"operation", "workspace_id"}},
    }
    return updated | {"updated": True}


def holodeck_add_context(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    created_at = utc_now()
    payload = {
        "operation": "create",
        "context_id": args.context_id or make_id("context"),
        "workspace_id": args.workspace_id,
        "context_kind": args.context_kind,
        "title": args.title,
        "summary": args.summary,
        "domain": args.domain or "",
        "status": args.status,
        "confidence": args.confidence,
        "source_refs": _split_csv(args.source_refs),
        "linked_artifact_ids": _split_csv(args.linked_artifact_ids),
        "created_at": created_at,
        "updated_at": created_at,
    }
    append_jsonl(_workspace_context_records_path(root, args.workspace_id), payload)
    event_tags = [value for value in [args.context_kind, args.domain] if value]
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="context_recorded",
        summary=f"Added context record {args.title}",
        content=args.summary,
        source_refs=payload["source_refs"],
        tags=event_tags,
    )
    return payload


def holodeck_update_context(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    context_records = {
        item["context_id"]: item
        for item in _reduce_context_records(read_jsonl(_workspace_context_records_path(root, args.workspace_id)))
    }
    current = context_records.get(args.context_id)
    if current is None:
        raise FileNotFoundError(f"Context record not found: {args.context_id}")
    payload = {
        "operation": "update",
        "context_id": args.context_id,
        "workspace_id": args.workspace_id,
        "updated_at": utc_now(),
    }
    if args.context_kind is not None:
        payload["context_kind"] = args.context_kind
    if args.title is not None:
        payload["title"] = args.title
    if args.summary is not None:
        payload["summary"] = args.summary
    if args.domain is not None:
        payload["domain"] = args.domain
    if args.status is not None:
        payload["status"] = args.status
    if args.confidence is not None:
        payload["confidence"] = args.confidence
    if args.source_refs is not None:
        payload["source_refs"] = _split_csv(args.source_refs)
    if args.linked_artifact_ids is not None:
        payload["linked_artifact_ids"] = _split_csv(args.linked_artifact_ids)
    if len(payload) == 4:
        return current | {"updated": False}
    append_jsonl(_workspace_context_records_path(root, args.workspace_id), payload)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="context_updated",
        summary=f"Updated context record {args.context_id}",
        content=args.reason or args.summary or "",
        source_refs=_split_csv(args.source_refs) if args.source_refs is not None else list(current.get("source_refs", [])),
        tags=[value for value in [payload.get("context_kind", current.get("context_kind", ""))] if value],
    )
    updated = {
        **current,
        **{key: value for key, value in payload.items() if key not in {"operation", "workspace_id"}},
    }
    return updated | {"updated": True}


def holodeck_add_constraint(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    created_at = utc_now()
    payload = {
        "operation": "create",
        "constraint_id": args.constraint_id or make_id("constraint"),
        "workspace_id": args.workspace_id,
        "constraint_kind": args.constraint_kind,
        "statement": args.statement,
        "applies_to": args.applies_to or "",
        "severity": args.severity,
        "status": args.status,
        "source_refs": _split_csv(args.source_refs),
        "created_at": created_at,
        "updated_at": created_at,
    }
    append_jsonl(_workspace_constraint_records_path(root, args.workspace_id), payload)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="constraint_recorded",
        summary=f"Added constraint record {payload['constraint_id']}",
        content=args.statement,
        source_refs=payload["source_refs"],
        tags=[value for value in [args.constraint_kind, args.severity] if value],
    )
    return payload


def holodeck_update_constraint(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    constraint_records = {
        item["constraint_id"]: item
        for item in _reduce_constraint_records(read_jsonl(_workspace_constraint_records_path(root, args.workspace_id)))
    }
    current = constraint_records.get(args.constraint_id)
    if current is None:
        raise FileNotFoundError(f"Constraint record not found: {args.constraint_id}")
    payload = {
        "operation": "update",
        "constraint_id": args.constraint_id,
        "workspace_id": args.workspace_id,
        "updated_at": utc_now(),
    }
    if args.constraint_kind is not None:
        payload["constraint_kind"] = args.constraint_kind
    if args.statement is not None:
        payload["statement"] = args.statement
    if args.applies_to is not None:
        payload["applies_to"] = args.applies_to
    if args.severity is not None:
        payload["severity"] = args.severity
    if args.status is not None:
        payload["status"] = args.status
    if args.source_refs is not None:
        payload["source_refs"] = _split_csv(args.source_refs)
    if len(payload) == 4:
        return current | {"updated": False}
    append_jsonl(_workspace_constraint_records_path(root, args.workspace_id), payload)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="constraint_updated",
        summary=f"Updated constraint record {args.constraint_id}",
        content=args.reason or args.statement or "",
        source_refs=_split_csv(args.source_refs) if args.source_refs is not None else list(current.get("source_refs", [])),
        tags=[value for value in [payload.get("constraint_kind", current.get("constraint_kind", ""))] if value],
    )
    updated = {
        **current,
        **{key: value for key, value in payload.items() if key not in {"operation", "workspace_id"}},
    }
    return updated | {"updated": True}


def holodeck_add_integration_target(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    created_at = utc_now()
    payload = {
        "operation": "create",
        "target_id": args.target_id or make_id("integration-target"),
        "workspace_id": args.workspace_id,
        "target_kind": args.target_kind,
        "title": args.title,
        "destination_ref": args.destination_ref,
        "required_evidence_refs": _split_csv(args.required_evidence_refs),
        "status": args.status,
        "source_refs": _split_csv(args.source_refs),
        "created_at": created_at,
        "updated_at": created_at,
    }
    append_jsonl(_workspace_integration_targets_path(root, args.workspace_id), payload)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="integration_target_recorded",
        summary=f"Added integration target {payload['target_id']}",
        content=args.destination_ref,
        source_refs=payload["source_refs"],
        tags=[value for value in [args.target_kind, args.status] if value],
    )
    return payload


def holodeck_update_integration_target(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    integration_targets = {
        item["target_id"]: item
        for item in _reduce_integration_targets(read_jsonl(_workspace_integration_targets_path(root, args.workspace_id)))
    }
    current = integration_targets.get(args.target_id)
    if current is None:
        raise FileNotFoundError(f"Integration target not found: {args.target_id}")
    payload = {
        "operation": "update",
        "target_id": args.target_id,
        "workspace_id": args.workspace_id,
        "updated_at": utc_now(),
    }
    if args.target_kind is not None:
        payload["target_kind"] = args.target_kind
    if args.title is not None:
        payload["title"] = args.title
    if args.destination_ref is not None:
        payload["destination_ref"] = args.destination_ref
    if args.required_evidence_refs is not None:
        payload["required_evidence_refs"] = _split_csv(args.required_evidence_refs)
    if args.status is not None:
        payload["status"] = args.status
    if args.source_refs is not None:
        payload["source_refs"] = _split_csv(args.source_refs)
    if len(payload) == 4:
        return current | {"updated": False}
    append_jsonl(_workspace_integration_targets_path(root, args.workspace_id), payload)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="integration_target_updated",
        summary=f"Updated integration target {args.target_id}",
        content=args.reason or args.destination_ref or "",
        source_refs=_split_csv(args.source_refs) if args.source_refs is not None else list(current.get("source_refs", [])),
        tags=[value for value in [payload.get("target_kind", current.get("target_kind", "")), payload.get("status", current.get("status", ""))] if value],
    )
    updated = {
        **current,
        **{key: value for key, value in payload.items() if key not in {"operation", "workspace_id"}},
    }
    return updated | {"updated": True}


def holodeck_add_knowledge(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    created_at = utc_now()
    payload = {
        "operation": "create",
        "record_id": args.record_id or make_id("knowledge"),
        "workspace_id": args.workspace_id,
        "record_kind": args.record_kind,
        "claim_posture": args.claim_posture,
        "title": args.title,
        "statement": args.statement,
        "confidence": args.confidence,
        "status": args.status,
        "source_refs": _split_csv(args.source_refs),
        "related_work_item_ids": _split_csv(args.work_item_ids),
        "supersedes_record_id": "",
        "created_at": created_at,
        "updated_at": created_at,
    }
    append_jsonl(_workspace_knowledge_records_path(root, args.workspace_id), payload)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="decision_noted" if args.record_kind == "decision" else "note",
        summary=f"Added knowledge record {args.title}",
        content=args.statement,
        source_refs=payload["source_refs"],
        related_work_item_ids=payload["related_work_item_ids"],
    )
    return payload


def holodeck_update_knowledge(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    knowledge_records = {
        item["record_id"]: item
        for item in _reduce_knowledge_records(read_jsonl(_workspace_knowledge_records_path(root, args.workspace_id)))
    }
    current = knowledge_records.get(args.record_id)
    if current is None:
        raise FileNotFoundError(f"Knowledge record not found: {args.record_id}")
    payload = {
        "operation": "update",
        "record_id": args.record_id,
        "workspace_id": args.workspace_id,
        "updated_at": utc_now(),
    }
    if args.status is not None:
        payload["status"] = args.status
    if args.supersedes_record_id is not None:
        payload["supersedes_record_id"] = args.supersedes_record_id
    if args.title is not None:
        payload["title"] = args.title
    if args.statement is not None:
        payload["statement"] = args.statement
    if args.confidence is not None:
        payload["confidence"] = args.confidence
    if args.claim_posture is not None:
        payload["claim_posture"] = args.claim_posture
    if args.source_refs is not None:
        payload["source_refs"] = _split_csv(args.source_refs)
    if args.work_item_ids is not None:
        payload["related_work_item_ids"] = _split_csv(args.work_item_ids)
    if len(payload) == 4:
        return current | {"updated": False}
    append_jsonl(_workspace_knowledge_records_path(root, args.workspace_id), payload)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="decision_noted" if current.get("record_kind") == "decision" else "note",
        summary=f"Updated knowledge record {args.record_id}",
        content=args.reason or args.statement or "",
        source_refs=_split_csv(args.source_refs) if args.source_refs is not None else list(current.get("source_refs", [])),
        related_work_item_ids=_split_csv(args.work_item_ids) if args.work_item_ids is not None else list(current.get("related_work_item_ids", [])),
    )
    updated = {
        **current,
        **{k: v for k, v in payload.items() if k not in {"operation", "workspace_id"}},
    }
    return updated | {"updated": True}


def holodeck_promote(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    knowledge_records = {
        item["record_id"]: item
        for item in _reduce_knowledge_records(read_jsonl(_workspace_knowledge_records_path(root, args.workspace_id)))
    }
    integration_targets = {
        item["target_id"]: item
        for item in _reduce_integration_targets(read_jsonl(_workspace_integration_targets_path(root, args.workspace_id)))
    }
    record = knowledge_records.get(args.record_id)
    if record is None:
        raise FileNotFoundError(f"Knowledge record not found: {args.record_id}")
    linked_target_ids = _split_many(args.target_ids)
    for target_id in linked_target_ids:
        if target_id not in integration_targets:
            raise FileNotFoundError(f"Integration target not found: {target_id}")
    payload = {
        "operation": "create",
        "promotion_id": args.promotion_id or make_id("promotion"),
        "workspace_id": args.workspace_id,
        "source_kind": "knowledge_record",
        "source_record_id": args.record_id,
        "target_kind": args.target_kind,
        "status": args.status,
        "title": args.title or record.get("title", args.record_id),
        "statement": record.get("statement", ""),
        "record_kind": record.get("record_kind", ""),
        "claim_posture": record.get("claim_posture", ""),
        "reason": args.reason,
        "summary": args.summary or record.get("statement", ""),
        "source_refs": list(record.get("source_refs", [])),
        "related_work_item_ids": list(record.get("related_work_item_ids", [])),
        "linked_target_ids": linked_target_ids,
        "promoted_at": utc_now(),
    }
    append_jsonl(_workspace_promotions_path(root, args.workspace_id), payload)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="promotion_noted",
        summary=f"Promoted knowledge record {args.record_id}",
        content=args.reason,
        source_refs=payload["source_refs"],
        related_work_item_ids=payload["related_work_item_ids"],
    )
    return payload


def holodeck_update_promotion(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    promotions = {
        item["promotion_id"]: item
        for item in _reduce_promotions(read_jsonl(_workspace_promotions_path(root, args.workspace_id)))
    }
    current = promotions.get(args.promotion_id)
    if current is None:
        raise FileNotFoundError(f"Promotion not found: {args.promotion_id}")
    payload = {
        "operation": "set_status",
        "promotion_id": args.promotion_id,
        "workspace_id": args.workspace_id,
        "status": args.status,
        "reason": args.reason,
        "summary": args.summary or "",
        "timestamp": utc_now(),
    }
    append_jsonl(_workspace_promotions_path(root, args.workspace_id), payload)
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="promotion_updated",
        summary=f"Updated promotion {args.promotion_id} to {args.status}",
        content=args.reason,
        source_refs=list(current.get("source_refs", [])),
        related_work_item_ids=list(current.get("related_work_item_ids", [])),
    )
    return current | {
        "status": args.status,
        "reason": args.reason,
        "updated_at": payload["timestamp"],
    }


def holodeck_apply_promotion(root: Path, args: argparse.Namespace) -> dict:
    manifest = _load_workspace_manifest(root, args.workspace_id)
    promotions = {
        item["promotion_id"]: item
        for item in _reduce_promotions(read_jsonl(_workspace_promotions_path(root, args.workspace_id)))
    }
    integration_targets = {
        item["target_id"]: item
        for item in _reduce_integration_targets(read_jsonl(_workspace_integration_targets_path(root, args.workspace_id)))
    }
    current = promotions.get(args.promotion_id)
    if current is None:
        raise FileNotFoundError(f"Promotion not found: {args.promotion_id}")
    if current.get("target_kind") != "memory_card":
        raise ValueError(f"Promotion target_kind must be memory_card, got: {current.get('target_kind')}")

    title = args.title or current.get("title") or current["promotion_id"]
    summary = args.summary or current.get("summary") or current.get("statement") or title
    record_kind = current.get("record_kind", "")
    card_type = args.card_type or (
        "decision" if record_kind == "decision" else "open_question" if record_kind == "open_question" else "state"
    )
    status = "accepted" if card_type == "decision" else "open" if card_type == "open_question" else "active"
    card_id = args.card_id or f"{card_type}-{args.workspace_id}-{current['promotion_id']}"
    source_refs = list(dict.fromkeys(list(current.get("source_refs", [])) + [f"workspace:{args.workspace_id}", f"promotion:{args.promotion_id}"]))
    tags = list(
        dict.fromkeys(
            [
                "holodeck",
                args.workspace_id,
                record_kind or "knowledge",
                current.get("claim_posture", "") or "claim",
                "promoted",
            ]
        )
    )
    card = MemoryCard(
        card_id=card_id,
        card_type=card_type,
        title=title,
        summary=summary,
        source_refs=source_refs,
        domains=list(manifest.get("domain_overlays", [])),
        status=status,
        tags=tags,
    )
    card_path = cards_dir(root) / f"{card.card_id}.json"
    write_json(card_path, card.to_dict())
    refresh_indexes(root)

    status_payload = argparse.Namespace(
        workspace_id=args.workspace_id,
        promotion_id=args.promotion_id,
        status="applied",
        reason=args.reason or f"Applied to memory card {card.card_id}",
        summary=summary,
    )
    promotion_state = holodeck_update_promotion(root, status_payload)

    artifact = {
        "artifact_id": make_id("artifact"),
        "workspace_id": args.workspace_id,
        "artifact_kind": "memory_card",
        "title": card.card_id,
        "source_ref": str(card_path),
        "source_type": "memory_card_json",
        "provenance": "generated",
        "summary": f"Promoted to global memory card {card.card_id}",
        "status": "active",
        "linked_at": utc_now(),
        "attributes": {
            "card_type": card.card_type,
            "integration_target_ids": list(current.get("linked_target_ids", [])),
        },
    }
    _append_workspace_artifact_link(root, args.workspace_id, artifact)
    integration_target_updates: list[dict] = []
    for target_id in current.get("linked_target_ids", []):
        target = integration_targets.get(target_id)
        if target is None:
            raise FileNotFoundError(f"Integration target not found: {target_id}")
        target_source_refs = list(dict.fromkeys(list(target.get("source_refs", [])) + [str(card_path)]))
        target_update = {
            "operation": "update",
            "target_id": target_id,
            "workspace_id": args.workspace_id,
            "status": "applied",
            "source_refs": target_source_refs,
            "updated_at": utc_now(),
        }
        append_jsonl(_workspace_integration_targets_path(root, args.workspace_id), target_update)
        integration_target_updates.append({**target, "status": "applied", "source_refs": target_source_refs})
    _append_workspace_event(
        root,
        args.workspace_id,
        actor="agent",
        kind="promotion_applied",
        summary=f"Applied promotion {args.promotion_id} to memory card {card.card_id}",
        source_refs=[str(card_path)],
        related_work_item_ids=list(current.get("related_work_item_ids", [])),
        tags=list(current.get("linked_target_ids", [])),
    )
    snapshot = _materialize_workspace_snapshot(root, args.workspace_id, write_files=True)
    return {
        "workspace_id": args.workspace_id,
        "promotion_id": args.promotion_id,
        "card_id": card.card_id,
        "card_path": str(card_path),
        "promotion_state": promotion_state,
        "integration_target_updates": integration_target_updates,
        "snapshot": snapshot,
    }


def holodeck_artifacts(root: Path, args: argparse.Namespace) -> dict:
    _load_workspace_manifest(root, args.workspace_id)
    artifacts = _load_workspace_artifacts(root, args.workspace_id)
    if args.artifact_kind:
        artifacts = [item for item in artifacts if item.get("artifact_kind") == args.artifact_kind]
    return {
        "workspace_id": args.workspace_id,
        "artifact_counts": _count_by(artifacts, "artifact_kind"),
        "artifacts": artifacts,
    }


def holodeck_load_active_state_continuity(root: Path, workspace_id: str) -> dict | None:
    from .active_state_continuity import load_latest_snapshot_for_workspace

    return load_latest_snapshot_for_workspace(root, workspace_id)


def holodeck_list_disclosure_receipts(
    root: Path,
    *,
    workspace_id: str = "",
    limit: int = 20,
) -> list[dict]:
    from .disclosure_receipts import list_disclosure_receipts

    return list_disclosure_receipts(
        root,
        surface="holodeck",
        workspace_id=workspace_id,
        limit=limit,
    )


def holodeck_inspect_disclosure_receipt(root: Path, receipt_id: str) -> dict:
    from .disclosure_receipts import inspect_disclosure_receipt

    return inspect_disclosure_receipt(root, receipt_id)


def holodeck_contextualize(root: Path, args: argparse.Namespace) -> dict:
    return _run_contextualization_pass(
        root,
        args.workspace_id,
        mode=args.mode,
        trigger="manual",
        reason=args.reason or "",
        max_source_refs=max(1, int(args.max_source_refs or 6)),
        max_anchors=max(1, int(args.max_anchors or 8)),
        max_context_records=max(0, int(args.max_context_records or 4)),
        max_knowledge_records=max(0, int(args.max_knowledge_records or 4)),
        allow_semantic_assist=bool(args.allow_semantic_assist),
        include_snapshot=True,
    )


def holodeck_list(root: Path, args: argparse.Namespace) -> dict:
    workspaces = []
    for workspace_id in _workspace_ids(root):
        manifest = _load_workspace_manifest(root, workspace_id)
        status = manifest.get("status", "active")
        if args.status and status != args.status:
            continue
        summary = _materialize_workspace_snapshot(root, workspace_id, write_files=False)
        workspaces.append(
            {
                "workspace_id": workspace_id,
                "label": manifest.get("label", workspace_id),
                "status": status,
                "goal": manifest.get("goal", ""),
                "updated_at": manifest.get("updated_at", ""),
                "closed_at": manifest.get("closed_at"),
                "active_item_count": len(summary.get("active_items", [])),
                "blocked_item_count": len(summary.get("blocked_items", [])),
                "pending_test_count": len(summary.get("pending_tests", [])),
                "integration_candidate_count": len(summary.get("integration_candidates", [])),
        "linked_task_pack_count": len(manifest.get("linked_task_pack_ids", [])),
                "status_reason": manifest.get("status_reason", ""),
            }
        )
    workspaces.sort(
        key=lambda item: (
            item.get("status", ""),
            item.get("updated_at", ""),
            item.get("workspace_id", ""),
        ),
        reverse=True,
    )
    return {"workspaces": workspaces}


def _transition_workspace_status(
    root: Path,
    workspace_id: str,
    *,
    target_status: str,
    reason: str,
    event_kind: str,
    event_summary: str,
    terminal: bool,
) -> dict:
    manifest = _load_workspace_manifest(root, workspace_id)
    current_status = manifest.get("status", "active")
    if current_status == target_status:
        return manifest | {"already_in_status": True}
    manifest["status"] = target_status
    manifest["updated_at"] = utc_now()
    if terminal:
        manifest["closed_at"] = manifest["updated_at"]
    elif target_status == "active":
        manifest["closed_at"] = None
    manifest["status_reason"] = "" if target_status == "active" else (reason or "")
    write_json(_workspace_manifest_path(root, workspace_id), manifest)
    _append_workspace_event(
        root,
        workspace_id,
        actor="agent",
        kind=event_kind,
        summary=event_summary,
        content=reason or "",
    )
    snapshot = _materialize_workspace_snapshot(root, workspace_id, write_files=True)
    result_key = "final_snapshot" if terminal else "current_snapshot"
    return manifest | {result_key: snapshot}


def holodeck_pause(root: Path, args: argparse.Namespace) -> dict:
    manifest = _load_workspace_manifest(root, args.workspace_id)
    if manifest.get("status") == "archived":
        return manifest | {"already_archived": True}
    return _transition_workspace_status(
        root,
        args.workspace_id,
        target_status="paused",
        reason=args.reason or "",
        event_kind="workspace_paused",
        event_summary=f"Paused Holodeck {manifest.get('label', args.workspace_id)}",
        terminal=False,
    )


def holodeck_block(root: Path, args: argparse.Namespace) -> dict:
    manifest = _load_workspace_manifest(root, args.workspace_id)
    if manifest.get("status") == "archived":
        return manifest | {"already_archived": True}
    return _transition_workspace_status(
        root,
        args.workspace_id,
        target_status="blocked",
        reason=args.reason or "",
        event_kind="workspace_blocked",
        event_summary=f"Blocked Holodeck {manifest.get('label', args.workspace_id)}",
        terminal=False,
    )


def holodeck_close(root: Path, args: argparse.Namespace) -> dict:
    manifest = _load_workspace_manifest(root, args.workspace_id)
    if manifest.get("status") == "closed":
        return manifest | {"already_closed": True}
    if manifest.get("status") == "archived":
        return manifest | {"already_archived": True}
    return _transition_workspace_status(
        root,
        args.workspace_id,
        target_status="closed",
        reason=args.reason or "",
        event_kind="workspace_closed",
        event_summary=f"Closed Holodeck {manifest.get('label', args.workspace_id)}",
        terminal=True,
    )


def holodeck_reopen(root: Path, args: argparse.Namespace) -> dict:
    manifest = _load_workspace_manifest(root, args.workspace_id)
    if manifest.get("status") == "active":
        return manifest | {"already_open": True}
    if manifest.get("status") == "archived":
        return manifest | {"already_archived": True}
    return _transition_workspace_status(
        root,
        args.workspace_id,
        target_status="active",
        reason=args.reason or "",
        event_kind="workspace_reopened",
        event_summary=f"Reopened Holodeck {manifest.get('label', args.workspace_id)}",
        terminal=False,
    )


def holodeck_archive(root: Path, args: argparse.Namespace) -> dict:
    manifest = _load_workspace_manifest(root, args.workspace_id)
    if manifest.get("status") == "archived":
        return manifest | {"already_archived": True}
    return _transition_workspace_status(
        root,
        args.workspace_id,
        target_status="archived",
        reason=args.reason or "",
        event_kind="workspace_archived",
        event_summary=f"Archived Holodeck {manifest.get('label', args.workspace_id)}",
        terminal=True,
    )


def holodeck_materialize(root: Path, args: argparse.Namespace) -> dict:
    _maybe_auto_contextualize(
        root,
        args.workspace_id,
        trigger="materialize",
        reason="Automatic contextualization before workspace materialization.",
    )
    return _materialize_workspace_snapshot(root, args.workspace_id, write_files=True)


def holodeck_status(root: Path, args: argparse.Namespace) -> dict:
    _maybe_auto_contextualize(
        root,
        args.workspace_id,
        trigger="status",
        reason="Automatic contextualization before reading workspace status.",
    )
    return _materialize_workspace_snapshot(root, args.workspace_id, write_files=False)


def holodeck_check(root: Path, args: argparse.Namespace) -> dict:
    _maybe_auto_contextualize(
        root,
        args.workspace_id,
        trigger="check",
        reason="Automatic contextualization before workspace health check.",
    )
    manifest = _load_workspace_manifest(root, args.workspace_id)
    snapshot = _materialize_workspace_snapshot(root, args.workspace_id, write_files=False)
    events = read_jsonl(_workspace_events_path(root, args.workspace_id))
    work_item_rows = read_jsonl(_workspace_work_item_events_path(root, args.workspace_id))
    work_items = _annotate_work_items(
        _reduce_work_items(work_item_rows)
    )
    tests = _reduce_tests(
        read_jsonl(_workspace_test_cases_path(root, args.workspace_id)),
        read_jsonl(_workspace_test_runs_path(root, args.workspace_id)),
    )
    promotions = _reduce_promotions(read_jsonl(_workspace_promotions_path(root, args.workspace_id)))
    active_knowledge = [
        item
        for item in _reduce_knowledge_records(read_jsonl(_workspace_knowledge_records_path(root, args.workspace_id)))
        if item.get("status", "active") == "active"
    ]
    knowledge_conflicts = _detect_knowledge_conflicts(active_knowledge)
    template_issues = _template_issues_for_manifest(manifest)
    workspace_blockers = list(snapshot.get("workspace_blockers", []))
    verification_hotspots = list(snapshot.get("verification_hotspots", []))
    stage_gaps = list(snapshot.get("stage_gaps", []))
    context_records = list(snapshot.get("context_records", []))
    constraint_records = list(snapshot.get("constraint_records", []))
    integration_targets = list(snapshot.get("integration_targets", []))
    run_contracts = list(snapshot.get("run_contracts", []))
    active_run = snapshot.get("active_run")
    proof_summary = dict(snapshot.get("proof_summary", {}))
    stop_conditions = [item for item in constraint_records if item.get("constraint_kind") == "stop_condition"]
    constraint_violations = _collect_constraint_violations(events, work_items, constraint_records)
    drift_warnings = _collect_run_drift_warnings(events, work_item_rows, active_run, snapshot)
    drift_warnings.extend(_collect_completed_run_drift_warnings(run_contracts))

    structural_issues: list[dict] = []
    execution_blockers: list[dict] = []
    verification_gaps: list[dict] = []
    guard_gaps: list[dict] = []
    proof_gaps: list[dict] = []

    for item in work_items:
        structural_reasons: list[str] = []
        structural_reasons.extend([f"missing_dependency:{value}" for value in item.get("missing_dependency_ids", [])])
        if any("cycle" in reason or "cannot be its own" in reason or "does not exist" in reason for reason in item.get("blocker_reasons", [])):
            structural_reasons.extend(
                [
                    reason
                    for reason in item.get("blocker_reasons", [])
                    if "cycle" in reason or "cannot be its own" in reason or "does not exist" in reason
                ]
            )
        if structural_reasons:
            structural_issues.append(
                {
                    "work_item_id": item["work_item_id"],
                    "title": item["title"],
                    "status": item["status"],
                    "reasons": structural_reasons,
                }
            )

        if item.get("blocker_reasons"):
            execution_blockers.append(
                {
                    "work_item_id": item["work_item_id"],
                    "title": item["title"],
                    "status": item["status"],
                    "reasons": list(item.get("blocker_reasons", [])),
                    "depends_on": list(item.get("depends_on", [])),
                    "child_ids": list(item.get("child_ids", [])),
                }
            )

        if item.get("status") in {"ready", "in_progress"} and _requires_ready_guard(item.get("kind", "task")) and item.get("guard_status") != "ready":
            guard_gaps.append(
                {
                    "work_item_id": item["work_item_id"],
                    "title": item["title"],
                    "status": item["status"],
                    "guard_status": item.get("guard_status", "not_required"),
                }
            )

        if item.get("status") == "done" and not _workspace_has_passing_test(root, args.workspace_id, item["work_item_id"]):
            verification_gaps.append(
                {
                    "work_item_id": item["work_item_id"],
                    "title": item["title"],
                    "status": item["status"],
                    "reason": "done_without_passing_test",
                }
            )

    pending_tests = [
        {
            "test_id": item["test_id"],
            "work_item_id": item["work_item_id"],
            "intent": item["intent"],
            "latest_result": item["latest_result"],
        }
        for item in tests
        if item.get("latest_result") != "passing"
    ]
    active_promotions = [
        {
            "promotion_id": item["promotion_id"],
            "title": item["title"],
            "target_kind": item["target_kind"],
            "status": item["status"],
        }
        for item in _active_promotion_candidates(promotions)
    ]
    completion_contract_gaps = _collect_completion_contract_gaps(
        manifest=manifest,
        work_items=work_items,
        tests=tests,
        constraint_records=constraint_records,
        integration_targets=integration_targets,
        active_promotions=active_promotions,
    )
    inquiry_queue, questions_for_user = _derive_inquiry_queue(
        snapshot=snapshot,
        template_issues=template_issues,
        stage_gaps=stage_gaps,
        knowledge_conflicts=knowledge_conflicts,
        verification_gaps=verification_gaps,
        verification_hotspots=verification_hotspots,
        guard_gaps=guard_gaps,
        constraint_violations=constraint_violations,
    )
    latest_run = snapshot.get("latest_run")
    contextualization_summary = dict(snapshot.get("contextualization_summary", {}))
    contextualization_gaps: list[dict] = []
    contextualization_warnings: list[dict] = []
    contextualization_opted_out = _has_contextualization_opt_out(constraint_records)
    if contextualization_opted_out:
        contextualization_warnings.append(
            {
                "code": "contextualization_auto_opt_out_active",
                "message": "Automatic contextualization is explicitly opted out for this workspace.",
            }
        )
    elif not contextualization_summary.get("has_run"):
        if len(snapshot.get("current_contextualization_seed", {}).get("combined_terms", [])) >= 3:
            contextualization_gaps.append(
                {
                    "code": "no_contextualization_run",
                    "message": "The workspace has enough seed signal for contextualization, but no contextualization run has been recorded yet.",
                }
            )
        else:
            contextualization_gaps.append(
                {
                    "code": "insufficient_seed_signals",
                    "message": "The workspace does not yet have enough seed signal for high-confidence static contextualization.",
                }
            )
    elif contextualization_summary.get("stale"):
        contextualization_gaps.append(
            {
                "code": "stale_contextualization",
                "message": "The latest contextualization run is stale relative to the current workspace seed fingerprint.",
            }
        )
    elif contextualization_summary.get("status") == "insufficient":
        contextualization_gaps.append(
            {
                "code": "insufficient_seed_signals",
                "message": "The latest contextualization run could not resolve inherited anchors versus novelty with enough signal.",
            }
        )
    latest_candidates = list(snapshot.get("latest_contextualization_candidates", []))
    if contextualization_summary.get("status") == "inherited" and not snapshot.get("context_records"):
        contextualization_warnings.append(
            {
                "code": "no_high_signal_anchors",
                "message": "Contextualization reported inherited relevance but no retained context anchors are currently active.",
            }
        )
    duplicate_count = sum(1 for item in latest_candidates if item.get("disposition") == "duplicate_existing")
    if latest_candidates and duplicate_count >= max(3, len(latest_candidates)):
        contextualization_warnings.append(
            {
                "code": "candidate_noise_high",
                "message": "Most recent contextualization candidates collapsed into duplicates, suggesting low-signal retrieval noise.",
            }
        )
    if latest_run and latest_run.get("status") == "completed" and not proof_summary.get("required_surfaces"):
        proof_gaps.append(
            {
                "code": "proof_requirements_missing_for_completed_run",
                "message": (
                    "Completed work has no declared proof requirements. "
                    "Separate local green from target-surface proof before treating the work as working."
                ),
                "run_id": latest_run.get("run_id", ""),
            }
        )
    for surface in proof_summary.get("unverified_required_surfaces", []):
        proof_gaps.append(
            {
                "code": "required_proof_missing",
                "surface": surface,
                "message": f"Required proof surface '{surface}' is not yet verified.",
            }
        )

    has_issues = any(
        [
            structural_issues,
            execution_blockers,
            verification_gaps,
            guard_gaps,
            constraint_violations,
            knowledge_conflicts,
            template_issues,
            workspace_blockers,
            verification_hotspots,
            stage_gaps,
            completion_contract_gaps,
            drift_warnings,
            proof_gaps,
        ]
    )
    return {
        "workspace_id": args.workspace_id,
        "label": manifest.get("label", args.workspace_id),
        "status": manifest.get("status", "active"),
        "maturation_stage": manifest.get("maturation_stage", "raw"),
        "goal": manifest.get("goal", ""),
        "status_reason": manifest.get("status_reason", ""),
        "healthy": not has_issues,
        "structural_ok": not structural_issues,
        "execution_ready": not execution_blockers and not guard_gaps and not workspace_blockers and not constraint_violations and not completion_contract_gaps,
        "verification_ok": not verification_gaps and not verification_hotspots,
        "proof_ok": not proof_gaps,
        "verification_hotspots_ok": not verification_hotspots,
        "drift_free": not drift_warnings,
        "constraints_ok": not constraint_violations,
        "conflict_free": not knowledge_conflicts,
        "template_ok": not template_issues,
        "stage_ok": not stage_gaps,
        "completion_contract_ok": not completion_contract_gaps,
        "contextualization_ok": not contextualization_gaps,
        "contextualization_fresh": bool(contextualization_summary.get("fresh")),
        "counts": {
            "work_items": len(work_items),
            "tests": len(tests),
            "pending_tests": len(pending_tests),
            "active_promotions": len(active_promotions),
            "structural_issues": len(structural_issues),
            "execution_blockers": len(execution_blockers),
            "verification_gaps": len(verification_gaps),
            "guard_gaps": len(guard_gaps),
            "knowledge_conflicts": len(knowledge_conflicts),
            "template_issues": len(template_issues),
            "workspace_blockers": len(workspace_blockers),
            "verification_hotspots": len(verification_hotspots),
            "stage_gaps": len(stage_gaps),
            "completion_contract_gaps": len(completion_contract_gaps),
            "contextualization_gaps": len(contextualization_gaps),
            "contextualization_warnings": len(contextualization_warnings),
            "context_records": len(context_records),
            "constraint_records": len(constraint_records),
            "stop_conditions": len(stop_conditions),
            "integration_targets": len(integration_targets),
            "run_contracts": len(run_contracts),
            "active_runs": 1 if active_run else 0,
            "constraint_violations": len(constraint_violations),
            "drift_warnings": len(drift_warnings),
            "proof_gaps": len(proof_gaps),
            "inquiries": len(inquiry_queue),
            "questions_for_user": len(questions_for_user),
        },
        "structural_issues": structural_issues,
        "execution_blockers": execution_blockers,
        "verification_gaps": verification_gaps,
        "verification_hotspots": verification_hotspots,
        "guard_gaps": guard_gaps,
        "constraint_violations": constraint_violations,
        "knowledge_conflicts": knowledge_conflicts,
        "template_issues": template_issues,
        "stage_gaps": stage_gaps,
        "completion_contract_gaps": completion_contract_gaps,
        "contextualization_gaps": contextualization_gaps,
        "contextualization_warnings": contextualization_warnings,
        "context_records": context_records,
        "constraint_records": constraint_records,
        "stop_conditions": stop_conditions,
        "integration_targets": integration_targets,
        "run_contracts": run_contracts,
        "active_run": active_run,
        "drift_warnings": drift_warnings,
        "proof_gaps": proof_gaps,
        "proof_summary": proof_summary,
        "workspace_blockers": workspace_blockers,
        "pending_tests": pending_tests,
        "active_promotions": active_promotions,
        "inquiry_queue": inquiry_queue,
        "questions_for_user": questions_for_user,
        "snapshot": snapshot,
    }


def holodeck_task_pack(root: Path, args: argparse.Namespace) -> dict:
    manifest = _load_workspace_manifest(root, args.workspace_id)
    _maybe_auto_contextualize(
        root,
        args.workspace_id,
        trigger="task_pack",
        reason="Automatic contextualization before task-pack generation.",
    )
    snapshot = _materialize_workspace_snapshot(root, args.workspace_id, write_files=True)
    request = args.request or manifest.get("goal") or manifest.get("label") or args.workspace_id
    constraints = [
        f"workspace_id: {args.workspace_id}",
        f"workspace_status: {snapshot.get('status', 'active')}::{snapshot.get('status_reason', '') or 'none'}",
        f"maturation_stage: {snapshot.get('maturation_stage', 'raw')}",
        f"purpose: {manifest.get('purpose', '') or 'none'}",
        f"success_condition: {manifest.get('success_condition', '') or 'none'}",
    ]
    constraints.extend(
        f"stage_gap: {item['stage']}::{item['code']}::{item['message']}"
        for item in snapshot.get("stage_gaps", [])
    )
    constraints.extend(
        f"context_record: {item['context_id']}::{item['context_kind']}::{item['title']}"
        for item in snapshot.get("context_records", [])
    )
    contextualization_summary = dict(snapshot.get("contextualization_summary", {}))
    constraints.append(
        f"contextualization_status: {contextualization_summary.get('status', 'unresolved')}::{'fresh' if contextualization_summary.get('fresh') else 'stale' if contextualization_summary.get('stale') else 'not_run'}"
    )
    constraints.append(f"contextualization_message: {contextualization_summary.get('message', 'none')}")
    constraints.extend(
        f"contextualization_anchor: {item['context_id']}::{item['context_kind']}::{item['title']}"
        for item in snapshot.get("context_records", [])[:5]
    )
    constraints.extend(
        f"contextualization_inferred_record: {item['record_id']}::{item['record_kind']}::{item['title']}"
        for item in [
            row
            for row in _reduce_knowledge_records(read_jsonl(_workspace_knowledge_records_path(root, args.workspace_id)))
            if row.get("claim_posture") == "inferred" and row.get("status", "active") == "active"
        ][:5]
    )
    constraints.extend(
        f"constraint_record: {item['constraint_id']}::{item['constraint_kind']}::{item.get('severity', 'required')}::{item['statement']}"
        for item in snapshot.get("constraint_records", [])
    )
    constraints.extend(
        f"workspace_blocker: {item['reason']}"
        for item in snapshot.get("workspace_blockers", [])
    )
    constraints.extend(
        f"active_work_item: {item['work_item_id']}::{item['title']}::{item['status']}"
        for item in snapshot.get("active_items", [])
    )
    constraints.extend(
        f"blocked_work_item: {item['work_item_id']}::{item['title']}::{'; '.join(item.get('blocker_reasons', [])) or 'explicitly blocked'}"
        for item in snapshot.get("blocked_items", [])
    )
    constraints.extend(
        f"pending_test: {item['test_id']}::{item['intent']}"
        for item in snapshot.get("pending_tests", [])
    )
    constraints.extend(
        f"integration_candidate: {item['promotion_id']}::{item['title']}::{item['target_kind']}"
        for item in snapshot.get("integration_candidates", [])
    )
    constraints.extend(
        f"integration_target: {item['target_id']}::{item['target_kind']}::{item['title']}::{item.get('destination_ref', '') or 'none'}"
        for item in snapshot.get("integration_targets", [])
    )
    constraints.extend(
        f"inquiry: {item['inquiry_id']}::{item['inquiry_kind']}::{item['impact']}::{'user' if item.get('ask_user') else 'agent'}"
        for item in snapshot.get("inquiry_queue", [])
    )
    constraints.extend(
        f"user_question: {item['inquiry_id']}::{item['question']}"
        for item in snapshot.get("questions_for_user", [])
    )
    proof_summary = dict(snapshot.get("proof_summary", {}))
    if proof_summary:
        constraints.append(f"proof_posture: {proof_summary.get('proof_posture', 'unproven')}")
        constraints.extend(f"proof_required_surface: {item}" for item in proof_summary.get("required_surfaces", []))
        constraints.extend(f"proof_verified_surface: {item}" for item in proof_summary.get("verified_surfaces", []))
        constraints.extend(f"proof_gap: {item}" for item in proof_summary.get("unverified_required_surfaces", []))
    active_run = snapshot.get("active_run")
    if active_run:
        constraints.append(
            f"active_run: {active_run['run_id']}::{active_run.get('active_work_item_id') or active_run.get('active_maturation_stage') or 'none'}::{active_run.get('purpose') or 'none'}"
        )
        constraints.append(
            f"run_context_usage: {snapshot.get('active_run_context_units', 0)}/{active_run.get('context_budget', 0)}"
        )
        constraints.extend(f"run_allowed_path: {item}" for item in active_run.get("allowed_paths", []))
        constraints.extend(f"run_blocked_path: {item}" for item in active_run.get("blocked_paths", []))
        constraints.extend(f"run_allowed_command: {item}" for item in active_run.get("allowed_commands", []))
        constraints.extend(f"run_expected_output: {item}" for item in active_run.get("expected_outputs", []))
        if active_run.get("verification_plan"):
            constraints.append(f"run_verification_plan: {active_run['verification_plan']}")
        constraints.extend(f"run_stop_condition: {item}" for item in active_run.get("stop_conditions", []))
    pack = build_task_pack(
        root=root,
        task_id=args.task_id,
        request=request,
        task_type=args.task_type or "implementation",
        domain_overlays=manifest.get("domain_overlays", []),
        constraints=constraints,
    )
    json_path = task_packs_dir(root) / f"{args.task_id}.json"
    md_path = task_packs_dir(root) / f"{args.task_id}.md"
    pack = enrich_task_pack_with_workspace(
        root=root,
        task_id=args.task_id,
        workspace_id=args.workspace_id,
        pack=pack,
        manifest=manifest,
        snapshot=snapshot,
        constraints=constraints,
    )
    pack["workspace_status"] = snapshot.get("status", "active")
    pack["workspace_status_reason"] = snapshot.get("status_reason", "")
    pack["workspace_blockers"] = list(snapshot.get("workspace_blockers", []))
    linked_task_pack_ids = list(manifest.get("linked_task_pack_ids", []))
    if args.task_id not in linked_task_pack_ids:
        linked_task_pack_ids.append(args.task_id)
        manifest["linked_task_pack_ids"] = linked_task_pack_ids
        manifest["updated_at"] = utc_now()
        write_json(_workspace_manifest_path(root, args.workspace_id), manifest)
        artifact = {
            "artifact_id": make_id("artifact"),
            "workspace_id": args.workspace_id,
            "artifact_kind": "task_pack",
            "title": args.task_id,
            "source_ref": str(json_path),
            "source_type": "task_pack_json",
            "provenance": "generated",
            "summary": f"Generated task pack {args.task_id}",
            "status": "active",
            "linked_at": utc_now(),
            "attributes": {
                "task_pack_markdown_ref": str(md_path),
            },
        }
        _append_workspace_artifact_link(root, args.workspace_id, artifact)
        _append_workspace_event(
            root,
            args.workspace_id,
            actor="agent",
            kind="artifact_linked",
            summary=f"Linked task pack {args.task_id}",
            source_refs=[str(json_path), str(md_path)],
        )
        pack["workspace_linked_task_pack_ids"] = linked_task_pack_ids
    else:
        pack["workspace_linked_task_pack_ids"] = linked_task_pack_ids
    write_json(json_path, pack)
    return pack
