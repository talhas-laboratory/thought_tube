from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .analysis import analyze_session, materialize_cards, materialize_transcript, refresh_indexes, update_manifest
from .codebase_overview import lookup_codebase, refresh_codebase_overview, validate_codebase_index, watch_codebase_overview
from .conversation_learning import parse_conversation_transcript
from .cost_tracker import ensure_cost_tracker_bootstrap, get_cost_summary, list_cost_events
from .development_intake import (
    _summarize_development_idea,
    _summarize_development_proposal,
    approve_development_proposal,
    build_development_proposal,
    build_proposal_task_pack,
    get_development_idea,
    get_development_proposal,
    list_development_ideas,
    list_development_proposals,
    record_development_idea,
)
from .development_router import route_development_idea
from .engineering_guard import assess_change_request
from .mtsf_extraction import (
    assess_quarantine,
    materialize_extraction_draft,
    run_extraction_evals,
    validate_extraction_draft,
)
from .mtsf_projector import (
    default_shape_index_path,
    materialize_stencil_projection,
    project_extraction_draft,
    resolve_stencil_projections,
)
from .mtsf_kernel import run_replay_scenarios
from .mtsf_session import materialize_session_mtsf
from .mtsf_stencils import validate_seed_library
from .library_tracker import (
    apply_pond_router_preset as apply_pond_router_preset_admin,
    apply_prune_candidates,
    derive_graph,
    ensure_library_tracker_bootstrap,
    filter_governed_chunks,
    filter_library_sources as filter_library_sources_admin,
    get_chunk_status,
    get_pond_router_status as get_pond_router_status_admin,
    govern_library_family as govern_library_family_admin,
    govern_library_source as govern_library_source_admin,
    get_library_status as get_library_tracker_status,
    preview_prune_candidates,
    rederive_library as rederive_library_admin,
    scan_library_sources,
    sync_library_sources,
    update_pond_router_config as update_pond_router_config_admin,
    update_chunk_governance,
    update_chunk_link,
)
from .miniapp import serve_miniapp
from .models import ConversationEvent, MemoryCard, SessionManifest
from .chat_backends import diagnose_openclaw_telegram_config, migrate_openclaw_telegram_bindings
from .openclaw_miniapp import build_openclaw_bundle, install_openclaw_bundle
from .personal_interface import (
    PersonalInterfaceError,
    answer_calibration_question,
    doctor_personal_interface,
    get_profile_snapshot,
    ingest_learning_conversation,
    record_rewrite_feedback,
    rewrite_conversation_turn,
    rewrite_outgoing_message,
    start_calibration_interview,
)
from .conversation_synthesis import rebuild_conversation_concepts
from .product_inner_world import (
    build_thought_archive,
    build_thought_feed,
    chat_with_thought,
    delete_thread,
    export_state,
    filter_knowledge_components,
    get_bubble_detail,
    get_runtime_status,
    generate_daily_batch,
    list_bubbles,
    get_source_item_detail,
    get_thread_detail,
    get_thought_detail,
    record_feedback,
    save_thread,
)
from .routing import TaskPackRoutingError, build_task_pack, enrich_task_pack_with_workspace
from .runtime_pipeline import (
    get_runtime_pipeline_status,
    update_runtime_pipeline_component as update_runtime_pipeline_component_config,
)
from .storage import (
    append_jsonl,
    ensure_dir,
    make_id,
    read_json,
    read_jsonl,
    repo_root_from,
    cards_dir,
    session_dir,
    session_events_path,
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
from .vault_ingest import ingest_source_file
from .worldbuilding_studio import (
    answer_population_question as worldstudio_answer_population_question,
    bind_motion_object as worldstudio_bind_motion_object,
    compile_scene as worldstudio_compile_scene,
    compile_scene_from_canon as worldstudio_compile_scene_from_canon,
    compile_motion_plan as worldstudio_compile_motion_plan,
    compile_visual_context as worldstudio_compile_visual_context,
    create_character_profile as worldstudio_create_character_profile,
    create_motion_object as worldstudio_create_motion_object,
    create_world as worldstudio_create_world,
    execute_higgsfield_packet as worldstudio_execute_higgsfield_packet,
    evaluate_output as worldstudio_evaluate_output,
    generate_canon as worldstudio_generate_canon,
    ingest_visual_reference as worldstudio_ingest_visual_reference,
    inspect_motion_system as worldstudio_inspect_motion_system,
    inspect_visual_world as worldstudio_inspect_visual_world,
    list_execution_runs as worldstudio_list_execution_runs,
    get_world_studio_guide as worldstudio_get_guide,
    get_population_session as worldstudio_get_population_session,
    get_packet_bundle as worldstudio_get_packet_bundle,
    ingest_evidence as worldstudio_ingest_evidence,
    project_world_graph as worldstudio_project_graph,
    get_world as worldstudio_get_world,
    inspect_character_system as worldstudio_inspect_character_system,
    inspect_world_evidence as worldstudio_inspect_world_evidence,
    inspect_world_knowledge as worldstudio_inspect_world_knowledge,
    list_worlds as worldstudio_list_worlds,
    next_worldbuilding_question as worldstudio_next_question,
    record_generation_asset as worldstudio_record_generation_asset,
    run_demo as worldstudio_run_demo,
    start_population_session as worldstudio_start_population_session,
    update_character_feature_object as worldstudio_update_character_feature_object,
    update_character_profile_section as worldstudio_update_character_profile_section,
)


MODULE_ID = "assembly.bootstrap.cli"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "init_repo",
    "session_start",
    "session_append",
    "session_checkpoint",
    "session_close",
    "session_import",
    "build_parser",
    "main",
    "guarded_main",
)
__all__ = list(PUBLIC_API)





def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _split_many(values: list[str] | None) -> list[str]:
    items: list[str] = []
    for value in values or []:
        items.extend(_split_csv(value))
    return items










def _parse_bool_flag(value: str | None) -> bool | None:
    if value in (None, ""):
        return None
    return value.lower() == "true"


def _parse_dimension_overrides(value: str | None) -> dict[str, list[str] | str]:
    if not value:
        return {}
    parsed: dict[str, list[str] | str] = {}
    for item in value.split(","):
        text = item.strip()
        if not text or "=" not in text:
            continue
        key, raw_value = text.split("=", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if not key or not raw_value:
            continue
        if "|" in raw_value:
            values = [part.strip() for part in raw_value.split("|") if part.strip()]
            if values:
                parsed[key] = values
        else:
            parsed[key] = raw_value
    return parsed


def _sync_library_admin(root: Path, *, max_items: int | None = None, portion: float | None = None) -> dict:
    result = sync_library_sources(root, max_items=max_items, portion=portion)
    result["rebuild_required"] = bool(result["ingested_item_count"] or result["purged_item_count"])
    result["runtime"] = None
    return result


def _extract_frontmatter_block(text: str) -> str:
    match = re.match(r"(?s)\A(---\n.*?\n---)\s*", text)
    return match.group(1).strip() if match else ""


def _import_actor_and_kind(role: str) -> tuple[str, str]:
    normalized = role.lower()
    if normalized == "user":
        return "user", "request"
    if normalized == "assistant":
        return "assistant", "response"
    return normalized, "note"


def _summarize_development_ideas(rows: list[dict]) -> list[dict]:
    return [_summarize_development_idea(row) for row in rows]


def _summarize_development_proposals(rows: list[dict]) -> list[dict]:
    return [_summarize_development_proposal(row) for row in rows]


def init_repo(root: Path) -> dict:
    paths = [
        root / "memory" / "events",
        root / "memory" / "sessions",
        root / "memory" / "cards",
        root / "memory" / "workspaces",
        root / "context" / "task_packs",
        root / "context" / "workspaces",
        root / "product" / "inner_world_v1" / "data",
        root / "product" / "inner_world_v1" / "config",
        root / "product" / "inner_world_v1" / "exports",
        root / "product" / "personal_interface_v1" / "data",
        root / "product" / "personal_interface_v1" / "data" / "calibration",
    ]
    for path in paths:
        ensure_dir(path)
    ensure_library_tracker_bootstrap(root)
    ensure_cost_tracker_bootstrap(root)
    overview = refresh_codebase_overview(root)
    return {"initialized": [str(path) for path in paths], "repo_overview": overview}


def session_start(root: Path, args: argparse.Namespace) -> dict:
    session_id = args.session_id or make_id("session")
    manifest = SessionManifest(
        session_id=session_id,
        title=args.title,
        started_at=utc_now(),
        ended_at=None,
        participants=_split_csv(args.participants) or ["user", "agent"],
        source_type=args.source_type,
        status="active",
        artifact_refs={},
        domains=_split_csv(args.domains),
    )
    ensure_dir(session_dir(root, session_id))
    update_manifest(root, manifest)
    ensure_dir(session_events_path(root, session_id).parent)
    session_events_path(root, session_id).touch(exist_ok=True)
    return manifest.to_dict()


def session_append(root: Path, args: argparse.Namespace) -> dict:
    event = ConversationEvent(
        event_id=make_id("event"),
        session_id=args.session_id,
        timestamp=utc_now(),
        actor=args.actor,
        kind=args.kind,
        content=args.content,
        attachments=_split_csv(args.attachments),
        tags=_split_csv(args.tags),
        source_ref=args.source_ref,
    )
    append_jsonl(session_events_path(root, args.session_id), event.to_dict())
    return event.to_dict()


def session_checkpoint(root: Path, args: argparse.Namespace) -> dict:
    refs = materialize_transcript(root, args.session_id)
    manifest_payload = session_dir(root, args.session_id) / "manifest.json"
    manifest = SessionManifest(**__import__("json").loads(manifest_payload.read_text(encoding="utf-8")))
    manifest.artifact_refs.update(refs)
    manifest.status = "checkpointed"
    update_manifest(root, manifest)
    return {"session_id": args.session_id, "artifact_refs": refs}


def session_close(root: Path, args: argparse.Namespace) -> dict:
    checkpoint = materialize_transcript(root, args.session_id)
    analysis_refs = analyze_session(root, args.session_id)
    mtsf_refs = materialize_session_mtsf(root, args.session_id)
    cards = materialize_cards(root, args.session_id)
    refresh_indexes(root)
    manifest_payload = session_dir(root, args.session_id) / "manifest.json"
    manifest = SessionManifest(**__import__("json").loads(manifest_payload.read_text(encoding="utf-8")))
    manifest.ended_at = utc_now()
    manifest.status = "closed"
    manifest.artifact_refs.update(checkpoint)
    manifest.artifact_refs.update(analysis_refs)
    manifest.artifact_refs.update(mtsf_refs)
    update_manifest(root, manifest)
    concept_refs = rebuild_conversation_concepts(root)
    session_concept_ref = concept_refs.get("session_refs", {}).get(args.session_id)
    if session_concept_ref:
        manifest.artifact_refs["concept_synthesis"] = session_concept_ref
        update_manifest(root, manifest)
    result = {
        "session_id": args.session_id,
        "artifact_refs": manifest.artifact_refs,
        "materialized_cards": len(cards),
        "concept_nodes": concept_refs.get("concept_count", 0),
        "concept_reviews": concept_refs.get("review_count", 0),
    }
    if args.task_id:
        result["task_pack"] = build_task_pack(
            root=root,
            task_id=args.task_id,
            request=args.request or manifest.title,
            task_type=args.task_type or "session_followup",
            domain_overlays=manifest.domains,
            constraints=[],
        )
    return result


def session_import(root: Path, args: argparse.Namespace) -> dict:
    content = Path(args.source_path).read_text(encoding="utf-8")
    turns = parse_conversation_transcript(content)
    participants = args.participants or ",".join(dict.fromkeys(turn["role"] for turn in turns)) or "importer"
    session_id = args.session_id or make_id("import")
    started = session_start(
        root,
        argparse.Namespace(
            session_id=session_id,
            title=args.title,
            participants=participants,
            source_type=args.source_type,
            domains=args.domains or "",
        ),
    )
    source_ref = str(Path(args.source_path).resolve())
    frontmatter = _extract_frontmatter_block(content)
    if frontmatter:
        session_append(
            root,
            argparse.Namespace(
                session_id=session_id,
                actor="importer",
                kind="artifact",
                content=frontmatter,
                attachments="",
                tags=args.tags or "",
                source_ref=source_ref,
            ),
        )
    if turns:
        for turn in turns:
            actor, kind = _import_actor_and_kind(turn["role"])
            session_append(
                root,
                argparse.Namespace(
                    session_id=session_id,
                    actor=actor,
                    kind=kind,
                    content=turn["content"],
                    attachments="",
                    tags=args.tags or "",
                    source_ref=source_ref,
                ),
            )
    else:
        session_append(
            root,
            argparse.Namespace(
                session_id=session_id,
                actor="importer",
                kind="import",
                content=content,
                attachments="",
                tags=args.tags or "",
                source_ref=source_ref,
            ),
        )
    return session_close(
        root,
        argparse.Namespace(
            session_id=session_id,
            task_id=args.task_id,
            request=args.request or args.title,
            task_type=args.task_type or "import_review",
        ),
    )






























































































def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Conversation OS CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")

    session = sub.add_parser("session")
    session_sub = session.add_subparsers(dest="session_command", required=True)

    start = session_sub.add_parser("start")
    start.add_argument("--session-id")
    start.add_argument("--title", required=True)
    start.add_argument("--participants", default="user,agent")
    start.add_argument("--source-type", default="live_session")
    start.add_argument("--domains", default="")

    append = session_sub.add_parser("append")
    append.add_argument("--session-id", required=True)
    append.add_argument("--actor", required=True)
    append.add_argument("--kind", required=True)
    append.add_argument("--content", required=True)
    append.add_argument("--attachments", default="")
    append.add_argument("--tags", default="")
    append.add_argument("--source-ref")

    checkpoint = session_sub.add_parser("checkpoint")
    checkpoint.add_argument("--session-id", required=True)

    close = session_sub.add_parser("close")
    close.add_argument("--session-id", required=True)
    close.add_argument("--task-id")
    close.add_argument("--request")
    close.add_argument("--task-type")

    importer = session_sub.add_parser("import")
    importer.add_argument("--source-path", required=True)
    importer.add_argument("--title", required=True)
    importer.add_argument("--session-id")
    importer.add_argument("--participants", default="importer")
    importer.add_argument("--source-type", default="imported_transcript")
    importer.add_argument("--domains", default="")
    importer.add_argument("--tags", default="")
    importer.add_argument("--task-id")
    importer.add_argument("--request")
    importer.add_argument("--task-type")

    task_pack = sub.add_parser("task-pack")
    task_sub = task_pack.add_subparsers(dest="task_command", required=True)
    build = task_sub.add_parser("build")
    build.add_argument("--task-id", required=True)
    build.add_argument("--request", required=True)
    build.add_argument("--task-type", default="implementation")
    build.add_argument("--domains", default="")
    build.add_argument("--constraints", default="")

    development = sub.add_parser("development")
    development_sub = development.add_subparsers(dest="development_command", required=True)

    development_record = development_sub.add_parser("record")
    development_record.add_argument("--idea-text", required=True)
    development_record.add_argument("--desired-effect", default="")
    development_record.add_argument("--intent-kind", default="")
    development_record.add_argument("--surface-hints", default="")
    development_record.add_argument("--source-session-id", default="")
    development_record.add_argument("--source-refs", default="")
    development_record.add_argument("--context-notes", default="")

    development_route = development_sub.add_parser("route")
    development_route.add_argument("--idea-id", required=True)
    development_route.add_argument("--limit", type=int, default=6)

    development_ideas = development_sub.add_parser("ideas")
    development_ideas.add_argument("--status", default="")
    development_ideas.add_argument("--limit", type=int, default=20)

    development_idea = development_sub.add_parser("idea")
    development_idea.add_argument("--idea-id", required=True)

    development_propose = development_sub.add_parser("propose")
    development_propose.add_argument("--idea-id", required=True)
    development_propose.add_argument("--open-questions", default="")

    development_proposals = development_sub.add_parser("proposals")
    development_proposals.add_argument("--approval-status", default="")
    development_proposals.add_argument("--limit", type=int, default=20)

    development_proposal = development_sub.add_parser("proposal")
    development_proposal.add_argument("--proposal-id", required=True)

    development_approve = development_sub.add_parser("approve")
    development_approve.add_argument("--proposal-id", required=True)
    development_approve.add_argument("--decision", choices=["approved", "rejected"], required=True)
    development_approve.add_argument("--notes", default="")
    development_approve.add_argument("--reviewer", default="user")
    development_approve.add_argument("--build-task-pack", action="store_true")
    development_approve.add_argument("--task-type", default="implementation")
    development_approve.add_argument("--constraints", default="")

    repo_overview = sub.add_parser("repo-overview")
    repo_overview_sub = repo_overview.add_subparsers(dest="overview_command", required=True)
    repo_overview_sub.add_parser("refresh")
    repo_overview_sub.add_parser("validate")
    overview_watch = repo_overview_sub.add_parser("watch")
    overview_watch.add_argument("--interval", type=float, default=2.0)
    overview_watch.add_argument("--max-iterations", type=int)
    overview_lookup = repo_overview_sub.add_parser("lookup")
    overview_lookup.add_argument("--query", required=True)
    overview_lookup.add_argument("--limit", type=int, default=8)

    engineering_guard = sub.add_parser("engineering-guard")
    engineering_guard_sub = engineering_guard.add_subparsers(dest="guard_command", required=True)
    guard_assess = engineering_guard_sub.add_parser("assess")
    guard_assess.add_argument("--request", required=True)
    guard_assess.add_argument("--purpose", required=True)
    guard_assess.add_argument("--proposed-paths", default="")
    guard_assess.add_argument("--limit", type=int, default=6)

    mtsf = sub.add_parser("mtsf", help="Metaphysical Thought-Space Framework kernel")
    mtsf_sub = mtsf.add_subparsers(dest="mtsf_command", required=True)
    mtsf_sub.add_parser("replay-pilot-002", help="Run Pilot 002 shape activation replay scenarios")
    mtsf_sub.add_parser("validate-stencils", help="Validate seed stencil library and fingerprints")
    mtsf_validate_extraction = mtsf_sub.add_parser(
        "validate-extraction",
        help="Validate an ExtractionDraft JSON file",
    )
    mtsf_validate_extraction.add_argument("--draft-path", required=True)
    mtsf_materialize_extraction = mtsf_sub.add_parser(
        "materialize-extraction",
        help="Validate and materialize an ExtractionDraft into session MTSF artifacts",
    )
    mtsf_materialize_extraction.add_argument("--session-id", required=True)
    mtsf_materialize_extraction.add_argument("--draft-path", required=True)
    mtsf_sub.add_parser("run-extraction-evals", help="Run semantic shape extraction eval suite")
    mtsf_project_extraction = mtsf_sub.add_parser(
        "project-extraction",
        help="Project validated ExtractionDraft stencil drafts into session shape index",
    )
    mtsf_project_extraction.add_argument("--session-id", required=True)
    mtsf_project_extraction.add_argument("--draft-path", required=True)
    mtsf_project_extraction.add_argument(
        "--update-global-index",
        action="store_true",
        help="Also merge into memory/mtsf/shape_index.json when promotion-ready",
    )

    openclaw = sub.add_parser("openclaw")
    openclaw_sub = openclaw.add_subparsers(dest="openclaw_command", required=True)
    openclaw_sub.add_parser("telegram-diagnose")
    telegram_fix = openclaw_sub.add_parser("telegram-fix")
    telegram_fix.add_argument("--apply", action="store_true")

    holodeck = sub.add_parser("holodeck")
    holodeck_sub = holodeck.add_subparsers(dest="holodeck_command", required=True)

    holodeck_create_parser = holodeck_sub.add_parser("create")
    holodeck_create_parser.add_argument("--workspace-id")
    holodeck_create_parser.add_argument("--title", required=True)
    holodeck_create_parser.add_argument("--goal", required=True)
    holodeck_create_parser.add_argument("--purpose", required=True)
    holodeck_create_parser.add_argument("--success-condition", default="")
    holodeck_create_parser.add_argument("--scope-in", action="append")
    holodeck_create_parser.add_argument("--scope-out", action="append")
    holodeck_create_parser.add_argument("--template-key", default="")
    holodeck_create_parser.add_argument("--domains", default="")
    holodeck_create_parser.add_argument("--founder-wedge")
    holodeck_create_parser.add_argument("--founder-user")
    holodeck_create_parser.add_argument("--founder-moat")
    holodeck_create_parser.add_argument("--founder-gtm-risk")
    holodeck_create_parser.add_argument("--founder-launch-metric")

    holodeck_event_parser = holodeck_sub.add_parser("event")
    holodeck_event_parser.add_argument("--workspace-id", required=True)
    holodeck_event_parser.add_argument("--actor", default="agent")
    holodeck_event_parser.add_argument("--kind", required=True)
    holodeck_event_parser.add_argument("--summary", required=True)
    holodeck_event_parser.add_argument("--content", default="")
    holodeck_event_parser.add_argument("--source-refs", default="")
    holodeck_event_parser.add_argument("--work-item-ids", default="")
    holodeck_event_parser.add_argument("--test-ids", default="")
    holodeck_event_parser.add_argument("--tags", default="")
    holodeck_event_parser.add_argument("--context-units", type=int, default=0)
    holodeck_event_parser.add_argument("--command-ref", default="")

    holodeck_context_log_parser = holodeck_sub.add_parser("log-context")
    holodeck_context_log_parser.add_argument("--workspace-id", required=True)
    holodeck_context_log_parser.add_argument("--summary", required=True)
    holodeck_context_log_parser.add_argument("--source-refs", default="")
    holodeck_context_log_parser.add_argument("--work-item-ids", default="")
    holodeck_context_log_parser.add_argument("--units", required=True, type=int)
    holodeck_context_log_parser.add_argument("--reason", default="")

    holodeck_command_log_parser = holodeck_sub.add_parser("log-command")
    holodeck_command_log_parser.add_argument("--workspace-id", required=True)
    holodeck_command_log_parser.add_argument("--summary", required=True)
    holodeck_command_log_parser.add_argument("--command-ref", required=True)
    holodeck_command_log_parser.add_argument("--source-refs", default="")
    holodeck_command_log_parser.add_argument("--work-item-ids", default="")
    holodeck_command_log_parser.add_argument("--reason", default="")

    holodeck_artifact_parser = holodeck_sub.add_parser("ingest-artifact")
    holodeck_artifact_parser.add_argument("--workspace-id", required=True)
    holodeck_artifact_parser.add_argument("--artifact-id")
    holodeck_artifact_parser.add_argument("--artifact-kind", required=True)
    holodeck_artifact_parser.add_argument("--title", required=True)
    holodeck_artifact_parser.add_argument("--source-ref", required=True)
    holodeck_artifact_parser.add_argument("--source-type", default="repo_ref")
    holodeck_artifact_parser.add_argument("--provenance", default="linked")
    holodeck_artifact_parser.add_argument("--summary", default="")
    holodeck_artifact_parser.add_argument("--status", default="active")

    holodeck_artifacts_parser = holodeck_sub.add_parser("artifacts")
    holodeck_artifacts_parser.add_argument("--workspace-id", required=True)
    holodeck_artifacts_parser.add_argument("--artifact-kind", default="")

    holodeck_contextualize_parser = holodeck_sub.add_parser("contextualize")
    holodeck_contextualize_parser.add_argument("--workspace-id", required=True)
    holodeck_contextualize_parser.add_argument("--mode", choices=["suggest", "apply"], default="apply")
    holodeck_contextualize_parser.add_argument("--max-anchors", type=int, default=8)
    holodeck_contextualize_parser.add_argument("--max-source-refs", type=int, default=6)
    holodeck_contextualize_parser.add_argument("--max-context-records", type=int, default=4)
    holodeck_contextualize_parser.add_argument("--max-knowledge-records", type=int, default=4)
    holodeck_contextualize_parser.add_argument("--allow-semantic-assist", action="store_true")
    holodeck_contextualize_parser.add_argument("--reason", default="")

    holodeck_link_session_parser = holodeck_sub.add_parser("link-session")
    holodeck_link_session_parser.add_argument("--workspace-id", required=True)
    holodeck_link_session_parser.add_argument("--session-id", required=True)

    holodeck_update_parser = holodeck_sub.add_parser("update")
    holodeck_update_parser.add_argument("--workspace-id", required=True)
    holodeck_update_parser.add_argument("--title")
    holodeck_update_parser.add_argument("--goal")
    holodeck_update_parser.add_argument("--purpose")
    holodeck_update_parser.add_argument("--success-condition")
    holodeck_update_parser.add_argument("--scope-in", action="append")
    holodeck_update_parser.add_argument("--scope-out", action="append")
    holodeck_update_parser.add_argument("--template-key")
    holodeck_update_parser.add_argument("--domains")
    holodeck_update_parser.add_argument("--founder-wedge")
    holodeck_update_parser.add_argument("--founder-user")
    holodeck_update_parser.add_argument("--founder-moat")
    holodeck_update_parser.add_argument("--founder-gtm-risk")
    holodeck_update_parser.add_argument("--founder-launch-metric")

    holodeck_stage_parser = holodeck_sub.add_parser("advance-stage")
    holodeck_stage_parser.add_argument("--workspace-id", required=True)
    holodeck_stage_parser.add_argument("--stage", required=True)
    holodeck_stage_parser.add_argument("--reason", required=True)

    holodeck_list_parser = holodeck_sub.add_parser("list")
    holodeck_list_parser.add_argument("--status", choices=["active", "paused", "blocked", "closed", "archived"])

    holodeck_work_item_parser = holodeck_sub.add_parser("add-work-item")
    holodeck_work_item_parser.add_argument("--workspace-id", required=True)
    holodeck_work_item_parser.add_argument("--work-item-id")
    holodeck_work_item_parser.add_argument("--title", required=True)
    holodeck_work_item_parser.add_argument("--kind", default="task")
    holodeck_work_item_parser.add_argument("--status", default="proposed")
    holodeck_work_item_parser.add_argument("--priority", default="medium")
    holodeck_work_item_parser.add_argument("--owner", default="")
    holodeck_work_item_parser.add_argument("--parent-id", default="")
    holodeck_work_item_parser.add_argument("--depends-on", action="append")
    holodeck_work_item_parser.add_argument("--linked-artifacts", action="append")
    holodeck_work_item_parser.add_argument("--linked-tests", action="append")
    holodeck_work_item_parser.add_argument("--guard-status", default="")
    holodeck_work_item_parser.add_argument("--guard-request", default="")
    holodeck_work_item_parser.add_argument("--guard-purpose", default="")
    holodeck_work_item_parser.add_argument("--guard-paths", default="")
    holodeck_work_item_parser.add_argument("--acceptance-criteria", action="append")
    holodeck_work_item_parser.add_argument("--constraints", action="append")

    holodeck_work_item_update = holodeck_sub.add_parser("update-work-item")
    holodeck_work_item_update.add_argument("--workspace-id", required=True)
    holodeck_work_item_update.add_argument("--work-item-id", required=True)
    holodeck_work_item_update.add_argument("--status")
    holodeck_work_item_update.add_argument("--priority")
    holodeck_work_item_update.add_argument("--owner")
    holodeck_work_item_update.add_argument("--parent-id")
    holodeck_work_item_update.add_argument("--depends-on", action="append")
    holodeck_work_item_update.add_argument("--linked-artifacts", action="append")
    holodeck_work_item_update.add_argument("--linked-tests", action="append")
    holodeck_work_item_update.add_argument("--guard-status")
    holodeck_work_item_update.add_argument("--guard-request")
    holodeck_work_item_update.add_argument("--guard-purpose")
    holodeck_work_item_update.add_argument("--guard-paths")
    holodeck_work_item_update.add_argument("--acceptance-criteria", action="append")
    holodeck_work_item_update.add_argument("--constraints", action="append")

    holodeck_test_parser = holodeck_sub.add_parser("add-test")
    holodeck_test_parser.add_argument("--workspace-id", required=True)
    holodeck_test_parser.add_argument("--test-id")
    holodeck_test_parser.add_argument("--work-item-id", required=True)
    holodeck_test_parser.add_argument("--target-ref", required=True)
    holodeck_test_parser.add_argument("--test-kind", default="acceptance")
    holodeck_test_parser.add_argument("--intent", required=True)
    holodeck_test_parser.add_argument("--command-or-protocol", required=True)
    holodeck_test_parser.add_argument("--expected-signal", required=True)
    holodeck_test_parser.add_argument("--risk-level", default="medium")

    holodeck_test_run_parser = holodeck_sub.add_parser("record-test-run")
    holodeck_test_run_parser.add_argument("--workspace-id", required=True)
    holodeck_test_run_parser.add_argument("--test-id", required=True)
    holodeck_test_run_parser.add_argument("--result", required=True)
    holodeck_test_run_parser.add_argument("--evidence-ref", default="")
    holodeck_test_run_parser.add_argument("--notes", default="")
    holodeck_test_run_parser.add_argument("--command-or-protocol", default="")

    holodeck_start_run_parser = holodeck_sub.add_parser("start-run")
    holodeck_start_run_parser.add_argument("--workspace-id", required=True)
    holodeck_start_run_parser.add_argument("--run-id")
    holodeck_start_run_parser.add_argument("--work-item-id", default="")
    holodeck_start_run_parser.add_argument("--stage", default="")
    holodeck_start_run_parser.add_argument("--purpose", required=True)
    holodeck_start_run_parser.add_argument("--allowed-paths", action="append")
    holodeck_start_run_parser.add_argument("--blocked-paths", action="append")
    holodeck_start_run_parser.add_argument("--allowed-commands", action="append")
    holodeck_start_run_parser.add_argument("--expected-outputs", action="append")
    holodeck_start_run_parser.add_argument("--verification-plan", required=True)
    holodeck_start_run_parser.add_argument("--context-budget", type=int, default=0)
    holodeck_start_run_parser.add_argument("--stop-conditions", action="append")
    holodeck_start_run_parser.add_argument("--status", default="active")

    holodeck_finish_run_parser = holodeck_sub.add_parser("finish-run")
    holodeck_finish_run_parser.add_argument("--workspace-id", required=True)
    holodeck_finish_run_parser.add_argument("--run-id", required=True)
    holodeck_finish_run_parser.add_argument("--status", required=True)
    holodeck_finish_run_parser.add_argument("--summary", default="")
    holodeck_finish_run_parser.add_argument("--verification-result", default="")

    holodeck_context_parser = holodeck_sub.add_parser("add-context")
    holodeck_context_parser.add_argument("--workspace-id", required=True)
    holodeck_context_parser.add_argument("--context-id")
    holodeck_context_parser.add_argument("--context-kind", required=True)
    holodeck_context_parser.add_argument("--title", required=True)
    holodeck_context_parser.add_argument("--summary", required=True)
    holodeck_context_parser.add_argument("--domain", default="")
    holodeck_context_parser.add_argument("--source-refs", default="")
    holodeck_context_parser.add_argument("--linked-artifact-ids", default="")
    holodeck_context_parser.add_argument("--confidence", type=float, default=0.5)
    holodeck_context_parser.add_argument("--status", default="active")

    holodeck_context_update_parser = holodeck_sub.add_parser("update-context")
    holodeck_context_update_parser.add_argument("--workspace-id", required=True)
    holodeck_context_update_parser.add_argument("--context-id", required=True)
    holodeck_context_update_parser.add_argument("--context-kind")
    holodeck_context_update_parser.add_argument("--title")
    holodeck_context_update_parser.add_argument("--summary")
    holodeck_context_update_parser.add_argument("--domain")
    holodeck_context_update_parser.add_argument("--source-refs")
    holodeck_context_update_parser.add_argument("--linked-artifact-ids")
    holodeck_context_update_parser.add_argument("--confidence", type=float)
    holodeck_context_update_parser.add_argument("--status")
    holodeck_context_update_parser.add_argument("--reason", default="")

    holodeck_constraint_parser = holodeck_sub.add_parser("add-constraint")
    holodeck_constraint_parser.add_argument("--workspace-id", required=True)
    holodeck_constraint_parser.add_argument("--constraint-id")
    holodeck_constraint_parser.add_argument("--constraint-kind", required=True)
    holodeck_constraint_parser.add_argument("--statement", required=True)
    holodeck_constraint_parser.add_argument("--applies-to", default="")
    holodeck_constraint_parser.add_argument("--severity", default="required")
    holodeck_constraint_parser.add_argument("--source-refs", default="")
    holodeck_constraint_parser.add_argument("--status", default="active")

    holodeck_constraint_update_parser = holodeck_sub.add_parser("update-constraint")
    holodeck_constraint_update_parser.add_argument("--workspace-id", required=True)
    holodeck_constraint_update_parser.add_argument("--constraint-id", required=True)
    holodeck_constraint_update_parser.add_argument("--constraint-kind")
    holodeck_constraint_update_parser.add_argument("--statement")
    holodeck_constraint_update_parser.add_argument("--applies-to")
    holodeck_constraint_update_parser.add_argument("--severity")
    holodeck_constraint_update_parser.add_argument("--source-refs")
    holodeck_constraint_update_parser.add_argument("--status")
    holodeck_constraint_update_parser.add_argument("--reason", default="")

    holodeck_integration_target_parser = holodeck_sub.add_parser("add-integration-target")
    holodeck_integration_target_parser.add_argument("--workspace-id", required=True)
    holodeck_integration_target_parser.add_argument("--target-id")
    holodeck_integration_target_parser.add_argument("--target-kind", required=True)
    holodeck_integration_target_parser.add_argument("--title", required=True)
    holodeck_integration_target_parser.add_argument("--destination-ref", required=True)
    holodeck_integration_target_parser.add_argument("--required-evidence-refs", default="")
    holodeck_integration_target_parser.add_argument("--source-refs", default="")
    holodeck_integration_target_parser.add_argument("--status", default="candidate")

    holodeck_integration_target_update_parser = holodeck_sub.add_parser("update-integration-target")
    holodeck_integration_target_update_parser.add_argument("--workspace-id", required=True)
    holodeck_integration_target_update_parser.add_argument("--target-id", required=True)
    holodeck_integration_target_update_parser.add_argument("--target-kind")
    holodeck_integration_target_update_parser.add_argument("--title")
    holodeck_integration_target_update_parser.add_argument("--destination-ref")
    holodeck_integration_target_update_parser.add_argument("--required-evidence-refs")
    holodeck_integration_target_update_parser.add_argument("--source-refs")
    holodeck_integration_target_update_parser.add_argument("--status")
    holodeck_integration_target_update_parser.add_argument("--reason", default="")

    holodeck_knowledge_parser = holodeck_sub.add_parser("add-knowledge")
    holodeck_knowledge_parser.add_argument("--workspace-id", required=True)
    holodeck_knowledge_parser.add_argument("--record-id")
    holodeck_knowledge_parser.add_argument("--record-kind", required=True)
    holodeck_knowledge_parser.add_argument("--claim-posture", required=True)
    holodeck_knowledge_parser.add_argument("--title", required=True)
    holodeck_knowledge_parser.add_argument("--statement", required=True)
    holodeck_knowledge_parser.add_argument("--confidence", type=float, default=0.5)
    holodeck_knowledge_parser.add_argument("--status", default="active")
    holodeck_knowledge_parser.add_argument("--source-refs", default="")
    holodeck_knowledge_parser.add_argument("--work-item-ids", default="")

    holodeck_knowledge_update_parser = holodeck_sub.add_parser("update-knowledge")
    holodeck_knowledge_update_parser.add_argument("--workspace-id", required=True)
    holodeck_knowledge_update_parser.add_argument("--record-id", required=True)
    holodeck_knowledge_update_parser.add_argument("--status", choices=["active", "resolved", "superseded", "rejected"])
    holodeck_knowledge_update_parser.add_argument("--supersedes-record-id")
    holodeck_knowledge_update_parser.add_argument("--title")
    holodeck_knowledge_update_parser.add_argument("--statement")
    holodeck_knowledge_update_parser.add_argument("--confidence", type=float)
    holodeck_knowledge_update_parser.add_argument("--claim-posture")
    holodeck_knowledge_update_parser.add_argument("--source-refs")
    holodeck_knowledge_update_parser.add_argument("--work-item-ids")
    holodeck_knowledge_update_parser.add_argument("--reason", default="")

    holodeck_promote_parser = holodeck_sub.add_parser("promote")
    holodeck_promote_parser.add_argument("--workspace-id", required=True)
    holodeck_promote_parser.add_argument("--record-id", required=True)
    holodeck_promote_parser.add_argument("--promotion-id")
    holodeck_promote_parser.add_argument("--target-kind", default="memory_card")
    holodeck_promote_parser.add_argument("--target-id", dest="target_ids", action="append")
    holodeck_promote_parser.add_argument("--status", default="candidate")
    holodeck_promote_parser.add_argument("--title", default="")
    holodeck_promote_parser.add_argument("--reason", required=True)
    holodeck_promote_parser.add_argument("--summary", default="")

    holodeck_update_promotion_parser = holodeck_sub.add_parser("update-promotion")
    holodeck_update_promotion_parser.add_argument("--workspace-id", required=True)
    holodeck_update_promotion_parser.add_argument("--promotion-id", required=True)
    holodeck_update_promotion_parser.add_argument(
        "--status",
        required=True,
        choices=["candidate", "in_review", "applied", "rejected", "archived"],
    )
    holodeck_update_promotion_parser.add_argument("--reason", required=True)
    holodeck_update_promotion_parser.add_argument("--summary", default="")

    holodeck_apply_promotion_parser = holodeck_sub.add_parser("apply-promotion")
    holodeck_apply_promotion_parser.add_argument("--workspace-id", required=True)
    holodeck_apply_promotion_parser.add_argument("--promotion-id", required=True)
    holodeck_apply_promotion_parser.add_argument("--card-id", default="")
    holodeck_apply_promotion_parser.add_argument("--card-type", choices=["decision", "state", "open_question"])
    holodeck_apply_promotion_parser.add_argument("--title", default="")
    holodeck_apply_promotion_parser.add_argument("--summary", default="")
    holodeck_apply_promotion_parser.add_argument("--reason", default="")

    holodeck_materialize_parser = holodeck_sub.add_parser("materialize")
    holodeck_materialize_parser.add_argument("--workspace-id", required=True)

    holodeck_status_parser = holodeck_sub.add_parser("status")
    holodeck_status_parser.add_argument("--workspace-id", required=True)

    holodeck_check_parser = holodeck_sub.add_parser("check")
    holodeck_check_parser.add_argument("--workspace-id", required=True)

    holodeck_pause_parser = holodeck_sub.add_parser("pause")
    holodeck_pause_parser.add_argument("--workspace-id", required=True)
    holodeck_pause_parser.add_argument("--reason", default="")

    holodeck_block_parser = holodeck_sub.add_parser("block")
    holodeck_block_parser.add_argument("--workspace-id", required=True)
    holodeck_block_parser.add_argument("--reason", default="")

    holodeck_close_parser = holodeck_sub.add_parser("close")
    holodeck_close_parser.add_argument("--workspace-id", required=True)
    holodeck_close_parser.add_argument("--reason", default="")

    holodeck_reopen_parser = holodeck_sub.add_parser("reopen")
    holodeck_reopen_parser.add_argument("--workspace-id", required=True)
    holodeck_reopen_parser.add_argument("--reason", default="")

    holodeck_archive_parser = holodeck_sub.add_parser("archive")
    holodeck_archive_parser.add_argument("--workspace-id", required=True)
    holodeck_archive_parser.add_argument("--reason", default="")

    holodeck_task_pack_parser = holodeck_sub.add_parser("task-pack")
    holodeck_task_pack_parser.add_argument("--workspace-id", required=True)
    holodeck_task_pack_parser.add_argument("--task-id", required=True)
    holodeck_task_pack_parser.add_argument("--request", default="")
    holodeck_task_pack_parser.add_argument("--task-type", default="implementation")

    inner = sub.add_parser("inner-world")
    inner_sub = inner.add_subparsers(dest="inner_command", required=True)

    seed = inner_sub.add_parser("seed")
    seed.add_argument("--source-path", required=True)
    seed.add_argument("--source-type", default="manual_import")

    graph = inner_sub.add_parser("derive")
    graph.add_argument("--domains", default="")
    graph.add_argument("--resume", action="store_true")
    graph.add_argument("--from-stage", default="")
    graph.add_argument("--only-stage", default="")
    graph.add_argument("--force", action="store_true")
    graph.add_argument("--profile", action="store_true")

    batch = inner_sub.add_parser("batch")
    batch.add_argument("--limit", type=int, default=5)
    batch.add_argument("--domains", default="")

    feed = inner_sub.add_parser("feed")
    feed.add_argument("--limit", type=int, default=12)
    feed.add_argument("--domains", default="")

    archive = inner_sub.add_parser("archive")
    archive.add_argument("--domains", default="")

    thought = inner_sub.add_parser("thought")
    thought.add_argument("--thought-id", required=True)
    thought.add_argument("--domains", default="")

    bubbles = inner_sub.add_parser("bubbles")
    bubbles.add_argument("--limit", type=int, default=12)
    bubbles.add_argument("--domains", default="")

    bubble = inner_sub.add_parser("bubble")
    bubble.add_argument("--bubble-id", required=True)
    bubble.add_argument("--domains", default="")

    filter_parser = inner_sub.add_parser("filter")
    filter_parser.add_argument("--query", default="")
    filter_parser.add_argument("--component-types", default="")
    filter_parser.add_argument("--statuses", default="")
    filter_parser.add_argument("--source-ref", default="")
    filter_parser.add_argument("--bubble-id", default="")
    filter_parser.add_argument("--concept-id", default="")
    filter_parser.add_argument("--limit", type=int, default=20)
    filter_parser.add_argument("--domains", default="")

    library_scan = inner_sub.add_parser("library-scan")

    library_sync = inner_sub.add_parser("library-sync")
    library_sync.add_argument("--domains", default="")

    inner_sub.add_parser("library-status")
    library_filter = inner_sub.add_parser("library-filter")
    library_filter.add_argument("--query", default="")
    library_filter.add_argument("--statuses", default="")
    library_filter.add_argument("--source-families", default="")
    library_filter.add_argument("--semantic-roles", default="")
    library_filter.add_argument("--source-ref", default="")
    library_filter.add_argument("--include-in-runtime", choices=["true", "false"])
    library_filter.add_argument("--include-in-bubbles", choices=["true", "false"])
    library_filter.add_argument("--include-in-concepts", choices=["true", "false"])
    library_filter.add_argument("--limit", type=int, default=20)
    library_govern = inner_sub.add_parser("library-govern")
    library_govern.add_argument("--source-ref", required=True)
    library_govern.add_argument("--status", default="")
    library_govern.add_argument("--semantic-role", default="")
    library_govern.add_argument("--normalization-profile", default="")
    library_govern.add_argument("--include-in-runtime", choices=["true", "false"])
    library_govern.add_argument("--include-in-bubbles", choices=["true", "false"])
    library_govern.add_argument("--include-in-concepts", choices=["true", "false"])
    library_govern.add_argument("--include-in-long-form", choices=["true", "false"])
    library_govern.add_argument("--collection-tags", default="")
    library_govern.add_argument("--notes", default="")
    library_govern_family = inner_sub.add_parser("library-govern-family")
    library_govern_family.add_argument("--family", required=True)
    library_govern_family.add_argument("--status", default="")
    library_govern_family.add_argument("--semantic-role", default="")
    library_govern_family.add_argument("--normalization-profile", default="")
    library_govern_family.add_argument("--include-in-runtime", choices=["true", "false"])
    library_govern_family.add_argument("--include-in-bubbles", choices=["true", "false"])
    library_govern_family.add_argument("--include-in-concepts", choices=["true", "false"])
    library_govern_family.add_argument("--include-in-long-form", choices=["true", "false"])
    library_govern_family.add_argument("--collection-tags", default="")
    library_govern_family.add_argument("--notes", default="")
    library_rederive = inner_sub.add_parser("library-rederive")
    library_rederive.add_argument("--affected-only", action="store_true")
    library_rederive.add_argument("--dry-run", action="store_true")
    library_rederive.add_argument("--profile", action="store_true")
    inner_sub.add_parser("chunk-status")
    chunk_filter = inner_sub.add_parser("chunk-filter")
    chunk_filter.add_argument("--query", default="")
    chunk_filter.add_argument("--statuses", default="")
    chunk_filter.add_argument("--source-families", default="")
    chunk_filter.add_argument("--source-ref", default="")
    chunk_filter.add_argument("--content-kinds", default="")
    chunk_filter.add_argument("--speaker-roles", default="")
    chunk_filter.add_argument("--dimensions", default="")
    chunk_filter.add_argument("--include-in-runtime", choices=["true", "false"])
    chunk_filter.add_argument("--limit", type=int, default=20)
    chunk_govern = inner_sub.add_parser("chunk-govern")
    chunk_govern.add_argument("--chunk-id", required=True)
    chunk_govern.add_argument("--status", default="")
    chunk_govern.add_argument("--semantic-role", default="")
    chunk_govern.add_argument("--normalization-profile", default="")
    chunk_govern.add_argument("--include-in-runtime", choices=["true", "false"])
    chunk_govern.add_argument("--include-in-bubbles", choices=["true", "false"])
    chunk_govern.add_argument("--include-in-concepts", choices=["true", "false"])
    chunk_govern.add_argument("--include-in-long-form", choices=["true", "false"])
    chunk_govern.add_argument("--collection-tags", default="")
    chunk_govern.add_argument("--dimensions", default="")
    chunk_govern.add_argument("--clear-dimensions", action="store_true")
    chunk_govern.add_argument("--notes", default="")
    chunk_link = inner_sub.add_parser("chunk-link")
    chunk_link.add_argument("--chunk-id", required=True)
    chunk_link.add_argument("--other-chunk-id", required=True)
    chunk_link.add_argument("--kind", default="manual")
    chunk_link.add_argument("--notes", default="")
    chunk_link.add_argument("--remove", action="store_true")
    prune_preview = inner_sub.add_parser("prune-preview")
    prune_preview.add_argument("--scope", choices=["chunk", "source"], default="chunk")
    prune_preview.add_argument("--query", default="")
    prune_preview.add_argument("--regex", default="")
    prune_preview.add_argument("--statuses", default="")
    prune_preview.add_argument("--source-families", default="")
    prune_preview.add_argument("--source-ref", default="")
    prune_preview.add_argument("--content-kinds", default="")
    prune_preview.add_argument("--speaker-roles", default="")
    prune_preview.add_argument("--semantic-classes", default="")
    prune_preview.add_argument("--dimensions", default="")
    prune_preview.add_argument("--include-in-runtime", choices=["true", "false"])
    prune_preview.add_argument("--status", default="")
    prune_preview.add_argument("--limit", type=int, default=20)
    prune_apply = inner_sub.add_parser("prune-apply")
    prune_apply.add_argument("--scope", choices=["chunk", "source"], default="chunk")
    prune_apply.add_argument("--status", required=True)
    prune_apply.add_argument("--query", default="")
    prune_apply.add_argument("--regex", default="")
    prune_apply.add_argument("--statuses", default="")
    prune_apply.add_argument("--source-families", default="")
    prune_apply.add_argument("--source-ref", default="")
    prune_apply.add_argument("--content-kinds", default="")
    prune_apply.add_argument("--speaker-roles", default="")
    prune_apply.add_argument("--semantic-classes", default="")
    prune_apply.add_argument("--dimensions", default="")
    prune_apply.add_argument("--include-in-runtime", choices=["true", "false"])
    prune_apply.add_argument("--notes", default="")
    prune_apply.add_argument("--limit", type=int, default=20)
    inner_sub.add_parser("runtime-pipeline")
    inner_sub.add_parser("runtime-status")
    pond_router = inner_sub.add_parser("pond-router")
    pond_router_sub = pond_router.add_subparsers(dest="pond_router_command", required=True)
    pond_router_sub.add_parser("status")
    pond_preset = pond_router_sub.add_parser("preset")
    pond_preset.add_argument("--name", required=True, choices=["off", "manual_only", "heuristic", "hybrid", "assisted"])
    pond_update = pond_router_sub.add_parser("update")
    pond_update.add_argument("--enabled", choices=["true", "false"])
    pond_update.add_argument("--mode", choices=["off", "manual_only", "heuristic", "hybrid", "assisted"])
    pond_update.add_argument("--assisted-on-ambiguity", choices=["true", "false"])
    pond_update.add_argument("--allow-manual-override", choices=["true", "false"])
    pond_update.add_argument("--ambiguity-threshold", type=float)
    pond_update.add_argument("--local-role-id", default="")
    pond_update.add_argument("--judge-role-id", default="")
    pond_update.add_argument("--router-version", default="")

    runtime_pipeline_update = inner_sub.add_parser("runtime-pipeline-update")
    runtime_pipeline_update.add_argument("--component-id", required=True)
    runtime_pipeline_update.add_argument("--enabled", choices=["true", "false"])
    runtime_pipeline_update.add_argument("--order", type=int)
    runtime_pipeline_update.add_argument("--weight", type=float)

    cost_report = inner_sub.add_parser("cost-report")
    inner_sub.add_parser("token-dashboard")

    cost_events = inner_sub.add_parser("cost-events")
    cost_events.add_argument("--limit", type=int, default=50)
    token_events = inner_sub.add_parser("token-events")
    token_events.add_argument("--limit", type=int, default=50)

    source = inner_sub.add_parser("source")
    source.add_argument("--source-item-id", required=True)
    source.add_argument("--domains", default="")

    chat = inner_sub.add_parser("chat")
    chat.add_argument("--thought-id", required=True)
    chat.add_argument("--message", required=True)
    chat.add_argument("--thread-id")
    chat.add_argument("--domains", default="")

    thread_save = inner_sub.add_parser("thread-save")
    thread_save.add_argument("--thread-id", required=True)
    thread_save.add_argument("--domains", default="")

    thread_delete = inner_sub.add_parser("thread-delete")
    thread_delete.add_argument("--thread-id", required=True)

    thread = inner_sub.add_parser("thread")
    thread.add_argument("--thread-id", required=True)

    feedback = inner_sub.add_parser("feedback")
    feedback.add_argument("--insight-id", required=True)
    feedback.add_argument("--feedback-state", required=True)

    serve = inner_sub.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8421)
    serve.add_argument("--limit", type=int, default=12)
    serve.add_argument("--domains", default="")
    serve.add_argument("--api-prefixes", default="/api")

    bundle = inner_sub.add_parser("openclaw-bundle")
    bundle.add_argument("--app-id", default="inner-world")
    bundle.add_argument("--title", default="Inner World")
    bundle.add_argument(
        "--description",
        default="Private thought feed, article expansion, and scoped self-chat.",
    )
    bundle.add_argument("--api-base-url", default="/apps/api/inner-world")
    bundle.add_argument("--output-dir")

    install = inner_sub.add_parser("openclaw-install")
    install.add_argument("--apps-root", required=True)
    install.add_argument("--app-id", default="inner-world")
    install.add_argument("--api-base-url", default="/apps/api/inner-world")

    inner_sub.add_parser("export")

    personal = sub.add_parser("personal-interface")
    personal_sub = personal.add_subparsers(dest="personal_command", required=True)

    personal_sub.add_parser("calibrate-start")

    calibrate_answer = personal_sub.add_parser("calibrate-answer")
    calibrate_answer.add_argument("--session-id", required=True)
    calibrate_answer.add_argument("--answer", required=True)

    personal_sub.add_parser("profile")
    personal_sub.add_parser("doctor")

    learn = personal_sub.add_parser("learn")
    learn.add_argument("--source-text", default="")
    learn.add_argument("--source-path", default="")
    learn.add_argument("--source-url", default="")
    learn.add_argument("--source-label", default="")

    rewrite = personal_sub.add_parser("rewrite")
    rewrite.add_argument("--draft-text", required=True)
    rewrite.add_argument("--user-message", required=True)
    rewrite.add_argument("--conversation-window-json", default="")
    rewrite.add_argument("--caller-hints-json", default="")
    rewrite.add_argument("--client-context-json", default="")

    rewrite_turn = personal_sub.add_parser("rewrite-turn")
    rewrite_turn.add_argument("--draft-text", required=True)
    rewrite_turn.add_argument("--conversation-json", required=True)
    rewrite_turn.add_argument("--caller-hints-json", default="")
    rewrite_turn.add_argument("--client-context-json", default="")
    rewrite_turn.add_argument("--window-size", type=int, default=8)

    rewrite_feedback = personal_sub.add_parser("feedback")
    rewrite_feedback.add_argument("--rewrite-event-id", required=True)
    rewrite_feedback.add_argument("--feedback-state", required=True)

    world_studio = sub.add_parser("world-studio")
    world_studio_sub = world_studio.add_subparsers(dest="world_studio_command", required=True)

    world_create = world_studio_sub.add_parser("create-world")
    world_create.add_argument("--name", required=True)
    world_create.add_argument("--summary", default="")
    world_create.add_argument("--primitives", default="")
    world_create.add_argument("--world-rules", action="append")
    world_create.add_argument("--taste-profile-json", default="")
    world_create.add_argument("--constraints-json", default="")

    world_demo = world_studio_sub.add_parser("demo")
    world_demo.add_argument("--scene-text", default="")
    world_demo.add_argument("--duration-seconds", type=int, default=12)
    world_demo.add_argument("--aspect-ratio", default="16:9")

    world_compile = world_studio_sub.add_parser("compile-scene")
    world_compile.add_argument("--world-id", required=True)
    world_compile.add_argument("--scene-text", required=True)
    world_compile.add_argument("--duration-seconds", type=int, default=12)
    world_compile.add_argument("--aspect-ratio", default="16:9")
    world_compile.add_argument("--model-preference", default="cinematic_studio_3_0")

    world_inspect = world_studio_sub.add_parser("inspect-world")
    world_inspect.add_argument("--world-id", default="")

    world_packet = world_studio_sub.add_parser("get-packet")
    world_packet.add_argument("--packet-id", required=True)

    world_asset = world_studio_sub.add_parser("record-asset")
    world_asset.add_argument("--packet-id", required=True)
    world_asset.add_argument("--provider", required=True)
    world_asset.add_argument("--kind", required=True)
    world_asset.add_argument("--url", default="")
    world_asset.add_argument("--path", default="")
    world_asset.add_argument("--media-type", default="video")
    world_asset.add_argument("--metadata-json", default="")

    world_eval = world_studio_sub.add_parser("evaluate-output")
    world_eval.add_argument("--packet-id", required=True)
    world_eval.add_argument("--observed-text", required=True)

    world_pop_start = world_studio_sub.add_parser("populate-start")
    world_pop_start.add_argument("--world-id", default="")
    world_pop_start.add_argument("--name", default="")
    world_pop_start.add_argument("--summary", default="")

    world_pop_answer = world_studio_sub.add_parser("populate-answer")
    world_pop_answer.add_argument("--session-id", required=True)
    world_pop_answer.add_argument("--answer", required=True)

    world_pop_session = world_studio_sub.add_parser("population-session")
    world_pop_session.add_argument("--session-id", required=True)

    world_knowledge = world_studio_sub.add_parser("inspect-knowledge")
    world_knowledge.add_argument("--world-id", required=True)

    world_ingest = world_studio_sub.add_parser("ingest-evidence")
    world_ingest.add_argument("--world-id", required=True)
    world_ingest.add_argument("--source-text", default="")
    world_ingest.add_argument("--source-path", default="")
    world_ingest.add_argument("--source-url", default="")
    world_ingest.add_argument("--source-label", default="")
    world_ingest.add_argument("--note", default="")
    world_ingest.add_argument("--annotations-json", default="")

    world_visual_ingest = world_studio_sub.add_parser("ingest-visual-reference")
    world_visual_ingest.add_argument("--world-id", required=True)
    world_visual_ingest.add_argument("--source-path", default="")
    world_visual_ingest.add_argument("--source-url", default="")
    world_visual_ingest.add_argument("--source-label", default="")
    world_visual_ingest.add_argument("--note", default="")
    world_visual_ingest.add_argument("--categories", default="")
    world_visual_ingest.add_argument("--liked-aspects", action="append")
    world_visual_ingest.add_argument("--negative-constraints", action="append")
    world_visual_ingest.add_argument("--scope", default="global")
    world_visual_ingest.add_argument("--target-entity", default="")

    world_visual_inspect = world_studio_sub.add_parser("inspect-visual-world")
    world_visual_inspect.add_argument("--world-id", required=True)

    world_visual_context = world_studio_sub.add_parser("compile-visual-context")
    world_visual_context.add_argument("--world-id", required=True)
    world_visual_context.add_argument("--query-text", required=True)

    world_motion_create = world_studio_sub.add_parser("create-motion-object")
    world_motion_create.add_argument("--world-id", required=True)
    world_motion_create.add_argument("--label", required=True)
    world_motion_create.add_argument("--scope", required=True)
    world_motion_create.add_argument("--intent", default="")
    world_motion_create.add_argument("--primary-action", default="")
    world_motion_create.add_argument("--body-mechanics", default="")
    world_motion_create.add_argument("--secondary-motion", default="")
    world_motion_create.add_argument("--constraints", default="")
    world_motion_create.add_argument("--negative-constraints", default="")
    world_motion_create.add_argument("--compatible-states", default="")
    world_motion_create.add_argument("--speed", default="")
    world_motion_create.add_argument("--intensity", default="")
    world_motion_create.add_argument("--best-clip-duration", type=int, default=4)
    world_motion_create.add_argument("--prompt-template", default="")

    world_motion_bind = world_studio_sub.add_parser("bind-motion-object")
    world_motion_bind.add_argument("--world-id", required=True)
    world_motion_bind.add_argument("--motion-id", required=True)
    world_motion_bind.add_argument("--target-kind", required=True)
    world_motion_bind.add_argument("--target-id", default="default")
    world_motion_bind.add_argument("--when-tags", default="")
    world_motion_bind.add_argument("--exclude-tags", default="")
    world_motion_bind.add_argument("--priority", type=int, default=1)

    world_motion_inspect = world_studio_sub.add_parser("inspect-motion-system")
    world_motion_inspect.add_argument("--world-id", required=True)

    world_motion_plan = world_studio_sub.add_parser("compile-motion-plan")
    world_motion_plan.add_argument("--world-id", required=True)
    world_motion_plan.add_argument("--scene-text", required=True)
    world_motion_plan.add_argument("--duration-seconds", type=int, default=4)

    world_character_create = world_studio_sub.add_parser("create-character-profile")
    world_character_create.add_argument("--world-id", required=True)
    world_character_create.add_argument("--name", required=True)
    world_character_create.add_argument("--summary", default="")
    world_character_create.add_argument("--role", default="")

    world_character_inspect = world_studio_sub.add_parser("inspect-character-system")
    world_character_inspect.add_argument("--world-id", required=True)
    world_character_inspect.add_argument("--character-id", default="")

    world_character_update = world_studio_sub.add_parser("update-character-profile")
    world_character_update.add_argument("--world-id", required=True)
    world_character_update.add_argument("--character-id", required=True)
    world_character_update.add_argument("--section", required=True)
    world_character_update.add_argument("--value-json", required=True)

    world_character_feature_update = world_studio_sub.add_parser("update-character-feature")
    world_character_feature_update.add_argument("--world-id", required=True)
    world_character_feature_update.add_argument("--feature-id", required=True)
    world_character_feature_update.add_argument("--summary", default="")
    world_character_feature_update.add_argument("--trait-values", default="")
    world_character_feature_update.add_argument("--state-scope", default="")

    world_next = world_studio_sub.add_parser("next-question")
    world_next.add_argument("--world-id", required=True)

    world_evidence = world_studio_sub.add_parser("inspect-evidence")
    world_evidence.add_argument("--world-id", required=True)

    world_canon = world_studio_sub.add_parser("generate-canon")
    world_canon.add_argument("--world-id", required=True)
    world_canon.add_argument("--asset-types", default="")
    world_canon.add_argument("--style-note", default="")

    world_compile_canon = world_studio_sub.add_parser("compile-scene-from-canon")
    world_compile_canon.add_argument("--world-id", required=True)
    world_compile_canon.add_argument("--scene-text", required=True)
    world_compile_canon.add_argument("--duration-seconds", type=int, default=12)
    world_compile_canon.add_argument("--aspect-ratio", default="16:9")
    world_compile_canon.add_argument("--model-preference", default="cinematic_studio_3_0")

    world_execute = world_studio_sub.add_parser("execute-packet")
    world_execute.add_argument("--packet-id", required=True)
    world_execute.add_argument("--mode", choices=["prepared", "live", "auto"], default="auto")

    world_executions = world_studio_sub.add_parser("executions")
    world_executions.add_argument("--packet-id", default="")
    world_executions.add_argument("--world-id", default="")

    world_graph = world_studio_sub.add_parser("inspect-graph")
    world_graph.add_argument("--world-id", required=True)

    world_studio_sub.add_parser("guide")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = repo_root_from()

    if args.command == "init":
        result = init_repo(root)
    elif args.command == "session":
        if args.session_command == "start":
            result = session_start(root, args)
        elif args.session_command == "append":
            result = session_append(root, args)
        elif args.session_command == "checkpoint":
            result = session_checkpoint(root, args)
        elif args.session_command == "close":
            result = session_close(root, args)
        elif args.session_command == "import":
            result = session_import(root, args)
        else:
            raise ValueError(args.session_command)
    elif args.command == "task-pack":
        result = build_task_pack(
            root=root,
            task_id=args.task_id,
            request=args.request,
            task_type=args.task_type,
            domain_overlays=_split_csv(args.domains),
            constraints=_split_csv(args.constraints),
        )
    elif args.command == "development":
        if args.development_command == "record":
            result = record_development_idea(
                root,
                raw_idea=args.idea_text,
                desired_effect=args.desired_effect,
                intent_kind=args.intent_kind,
                surface_hints=_split_csv(args.surface_hints),
                source_session_id=args.source_session_id or None,
                source_refs=_split_csv(args.source_refs),
                context_notes=_split_csv(args.context_notes),
            )
        elif args.development_command == "route":
            result = route_development_idea(root, args.idea_id, limit=args.limit)
        elif args.development_command == "ideas":
            rows = list_development_ideas(
                root,
                status=args.status or None,
                limit=args.limit,
            )
            result = {
                "idea_count": len(rows),
                "ideas": _summarize_development_ideas(rows),
            }
        elif args.development_command == "idea":
            result = get_development_idea(root, args.idea_id)
            if result is None:
                raise FileNotFoundError(f"Development idea not found: {args.idea_id}")
        elif args.development_command == "propose":
            result = build_development_proposal(
                root,
                args.idea_id,
                open_questions=_split_csv(args.open_questions),
            )
        elif args.development_command == "proposals":
            rows = list_development_proposals(
                root,
                approval_status=args.approval_status or None,
                limit=args.limit,
            )
            result = {
                "proposal_count": len(rows),
                "proposals": _summarize_development_proposals(rows),
            }
        elif args.development_command == "proposal":
            result = get_development_proposal(root, args.proposal_id)
            if result is None:
                raise FileNotFoundError(f"Development proposal not found: {args.proposal_id}")
        elif args.development_command == "approve":
            result = approve_development_proposal(
                root,
                args.proposal_id,
                args.decision,
                reviewer=args.reviewer,
                notes=args.notes,
            )
            if args.build_task_pack and args.decision == "approved":
                result = {
                    "proposal": result,
                    "task_pack_result": build_proposal_task_pack(
                        root,
                        args.proposal_id,
                        task_type=args.task_type,
                        constraints=_split_csv(args.constraints),
                    ),
                }
        else:
            raise ValueError(args.development_command)
    elif args.command == "repo-overview":
        if args.overview_command == "refresh":
            result = refresh_codebase_overview(root)
        elif args.overview_command == "validate":
            result = validate_codebase_index(root)
        elif args.overview_command == "watch":
            result = watch_codebase_overview(root, interval=args.interval, max_iterations=args.max_iterations)
        elif args.overview_command == "lookup":
            result = {"results": lookup_codebase(root, args.query, args.limit)}
        else:
            raise ValueError(args.overview_command)
    elif args.command == "engineering-guard":
        if args.guard_command == "assess":
            result = assess_change_request(
                root,
                request=args.request,
                purpose=args.purpose,
                proposed_paths=_split_csv(args.proposed_paths),
                limit=args.limit,
            )
        else:
            raise ValueError(args.guard_command)
    elif args.command == "mtsf":
        if args.mtsf_command == "replay-pilot-002":
            result = run_replay_scenarios(root)
        elif args.mtsf_command == "validate-stencils":
            result = validate_seed_library(root)
        elif args.mtsf_command == "validate-extraction":
            draft = read_json(Path(args.draft_path))
            report = validate_extraction_draft(root, draft)
            quarantine = assess_quarantine(draft, report)
            result = {
                "ok": report.ok,
                "errors": report.errors,
                "warnings": report.warnings,
                "quarantine": quarantine.quarantine,
                "quarantine_reasons": quarantine.reasons,
                "stencil_matches": report.stencil_matches,
            }
        elif args.mtsf_command == "materialize-extraction":
            draft = read_json(Path(args.draft_path))
            result = materialize_extraction_draft(root, args.session_id, draft)
            manifest_path = session_dir(root, args.session_id) / "manifest.json"
            if manifest_path.exists():
                from .analysis import update_manifest
                from .models import SessionManifest

                manifest = SessionManifest(**read_json(manifest_path))
                manifest.artifact_refs.update(result["artifact_refs"])
                update_manifest(root, manifest)
        elif args.mtsf_command == "run-extraction-evals":
            result = run_extraction_evals(root)
        elif args.mtsf_command == "project-extraction":
            draft = read_json(Path(args.draft_path))
            result = materialize_stencil_projection(
                root,
                args.session_id,
                draft,
                update_global_index=bool(args.update_global_index),
            )
            manifest_path = session_dir(root, args.session_id) / "manifest.json"
            if manifest_path.exists() and result.get("artifact_refs"):
                from .analysis import update_manifest
                from .models import SessionManifest

                manifest = SessionManifest(**read_json(manifest_path))
                manifest.artifact_refs.update(result["artifact_refs"])
                update_manifest(root, manifest)
        else:
            raise ValueError(args.mtsf_command)
    elif args.command == "openclaw":
        if args.openclaw_command == "telegram-diagnose":
            result = diagnose_openclaw_telegram_config(root)
        elif args.openclaw_command == "telegram-fix":
            result = migrate_openclaw_telegram_bindings(root, apply=bool(args.apply))
        else:
            raise ValueError(args.openclaw_command)
    elif args.command == "holodeck":
        from . import holodeck as holodeck_module

        if args.holodeck_command == "create":
            result = holodeck_module.holodeck_create(root, args)
        elif args.holodeck_command == "event":
            result = holodeck_module.holodeck_event(root, args)
        elif args.holodeck_command == "log-context":
            result = holodeck_module.holodeck_log_context(root, args)
        elif args.holodeck_command == "log-command":
            result = holodeck_module.holodeck_log_command(root, args)
        elif args.holodeck_command == "ingest-artifact":
            result = holodeck_module.holodeck_ingest_artifact(root, args)
        elif args.holodeck_command == "artifacts":
            result = holodeck_module.holodeck_artifacts(root, args)
        elif args.holodeck_command == "contextualize":
            result = holodeck_module.holodeck_contextualize(root, args)
        elif args.holodeck_command == "link-session":
            result = holodeck_module.holodeck_link_session(root, args)
        elif args.holodeck_command == "update":
            result = holodeck_module.holodeck_update(root, args)
        elif args.holodeck_command == "advance-stage":
            result = holodeck_module.holodeck_advance_stage(root, args)
        elif args.holodeck_command == "list":
            result = holodeck_module.holodeck_list(root, args)
        elif args.holodeck_command == "add-work-item":
            result = holodeck_module.holodeck_add_work_item(root, args)
        elif args.holodeck_command == "update-work-item":
            result = holodeck_module.holodeck_update_work_item(root, args)
        elif args.holodeck_command == "add-test":
            result = holodeck_module.holodeck_add_test(root, args)
        elif args.holodeck_command == "record-test-run":
            result = holodeck_module.holodeck_record_test_run(root, args)
        elif args.holodeck_command == "start-run":
            result = holodeck_module.holodeck_start_run(root, args)
        elif args.holodeck_command == "finish-run":
            result = holodeck_module.holodeck_finish_run(root, args)
        elif args.holodeck_command == "add-context":
            result = holodeck_module.holodeck_add_context(root, args)
        elif args.holodeck_command == "update-context":
            result = holodeck_module.holodeck_update_context(root, args)
        elif args.holodeck_command == "add-constraint":
            result = holodeck_module.holodeck_add_constraint(root, args)
        elif args.holodeck_command == "update-constraint":
            result = holodeck_module.holodeck_update_constraint(root, args)
        elif args.holodeck_command == "add-integration-target":
            result = holodeck_module.holodeck_add_integration_target(root, args)
        elif args.holodeck_command == "update-integration-target":
            result = holodeck_module.holodeck_update_integration_target(root, args)
        elif args.holodeck_command == "add-knowledge":
            result = holodeck_module.holodeck_add_knowledge(root, args)
        elif args.holodeck_command == "update-knowledge":
            result = holodeck_module.holodeck_update_knowledge(root, args)
        elif args.holodeck_command == "promote":
            result = holodeck_module.holodeck_promote(root, args)
        elif args.holodeck_command == "update-promotion":
            result = holodeck_module.holodeck_update_promotion(root, args)
        elif args.holodeck_command == "apply-promotion":
            result = holodeck_module.holodeck_apply_promotion(root, args)
        elif args.holodeck_command == "materialize":
            result = holodeck_module.holodeck_materialize(root, args)
        elif args.holodeck_command == "status":
            result = holodeck_module.holodeck_status(root, args)
        elif args.holodeck_command == "check":
            result = holodeck_module.holodeck_check(root, args)
        elif args.holodeck_command == "pause":
            result = holodeck_module.holodeck_pause(root, args)
        elif args.holodeck_command == "block":
            result = holodeck_module.holodeck_block(root, args)
        elif args.holodeck_command == "close":
            result = holodeck_module.holodeck_close(root, args)
        elif args.holodeck_command == "reopen":
            result = holodeck_module.holodeck_reopen(root, args)
        elif args.holodeck_command == "archive":
            result = holodeck_module.holodeck_archive(root, args)
        elif args.holodeck_command == "task-pack":
            result = holodeck_module.holodeck_task_pack(root, args)
        else:
            raise ValueError(args.holodeck_command)
    elif args.command == "inner-world":
        if args.inner_command == "seed":
            result = ingest_source_file(root, Path(args.source_path), args.source_type)
        elif args.inner_command == "derive":
            result = derive_graph(
                root,
                _split_csv(args.domains),
                resume=args.resume,
                from_stage=args.from_stage or None,
                only_stage=args.only_stage or None,
                force=args.force,
                profile=args.profile,
            )
        elif args.inner_command == "batch":
            result = generate_daily_batch(root, args.limit, _split_csv(args.domains))
        elif args.inner_command == "feed":
            result = build_thought_feed(root, args.limit, _split_csv(args.domains))
        elif args.inner_command == "archive":
            result = build_thought_archive(root, _split_csv(args.domains))
        elif args.inner_command == "thought":
            result = get_thought_detail(root, args.thought_id, _split_csv(args.domains))
        elif args.inner_command == "bubbles":
            result = list_bubbles(root, args.limit, _split_csv(args.domains))
        elif args.inner_command == "bubble":
            result = get_bubble_detail(root, args.bubble_id, _split_csv(args.domains))
        elif args.inner_command == "filter":
            result = filter_knowledge_components(
                root,
                query=args.query,
                component_types=_split_csv(args.component_types),
                statuses=_split_csv(args.statuses),
                source_ref=args.source_ref or None,
                bubble_id=args.bubble_id or None,
                concept_id=args.concept_id or None,
                limit=args.limit,
                domain_overlays=_split_csv(args.domains),
            )
        elif args.inner_command == "library-scan":
            result = scan_library_sources(root)
        elif args.inner_command == "library-sync":
            result = _sync_library_admin(root)
        elif args.inner_command == "library-status":
            result = get_library_tracker_status(root)
        elif args.inner_command == "library-filter":
            result = filter_library_sources_admin(
                root,
                query=args.query,
                statuses=_split_csv(args.statuses),
                source_families=_split_csv(args.source_families),
                semantic_roles=_split_csv(args.semantic_roles),
                source_ref=args.source_ref or None,
                include_in_runtime=_parse_bool_flag(args.include_in_runtime),
                include_in_bubbles=_parse_bool_flag(args.include_in_bubbles),
                include_in_concepts=_parse_bool_flag(args.include_in_concepts),
                limit=args.limit,
            )
        elif args.inner_command == "library-govern":
            result = govern_library_source_admin(
                root,
                source_ref=args.source_ref,
                governance_status=args.status or None,
                semantic_role=args.semantic_role or None,
                normalization_profile=args.normalization_profile or None,
                include_in_runtime=_parse_bool_flag(args.include_in_runtime),
                include_in_bubbles=_parse_bool_flag(args.include_in_bubbles),
                include_in_concepts=_parse_bool_flag(args.include_in_concepts),
                include_in_long_form=_parse_bool_flag(args.include_in_long_form),
                collection_tags=_split_csv(args.collection_tags),
                notes=args.notes or None,
            )
        elif args.inner_command == "library-govern-family":
            result = govern_library_family_admin(
                root,
                source_family=args.family,
                governance_status=args.status or None,
                semantic_role=args.semantic_role or None,
                normalization_profile=args.normalization_profile or None,
                include_in_runtime=_parse_bool_flag(args.include_in_runtime),
                include_in_bubbles=_parse_bool_flag(args.include_in_bubbles),
                include_in_concepts=_parse_bool_flag(args.include_in_concepts),
                include_in_long_form=_parse_bool_flag(args.include_in_long_form),
                collection_tags=_split_csv(args.collection_tags),
                notes=args.notes or None,
            )
        elif args.inner_command == "library-rederive":
            result = rederive_library_admin(
                root,
                affected_only=args.affected_only,
                dry_run=args.dry_run,
                profile=args.profile,
            )
        elif args.inner_command == "chunk-status":
            result = get_chunk_status(root)
        elif args.inner_command == "chunk-filter":
            result = filter_governed_chunks(
                root,
                query=args.query,
                statuses=_split_csv(args.statuses),
                source_families=_split_csv(args.source_families),
                source_ref=args.source_ref or None,
                content_kinds=_split_csv(args.content_kinds),
                speaker_roles=_split_csv(args.speaker_roles),
                dimension_filters=_parse_dimension_overrides(args.dimensions),
                include_in_runtime=_parse_bool_flag(args.include_in_runtime),
                limit=args.limit,
            )
        elif args.inner_command == "chunk-govern":
            result = update_chunk_governance(
                root,
                args.chunk_id,
                governance_status=args.status or None,
                semantic_role=args.semantic_role or None,
                normalization_profile=args.normalization_profile or None,
                include_in_runtime=_parse_bool_flag(args.include_in_runtime),
                include_in_bubbles=_parse_bool_flag(args.include_in_bubbles),
                include_in_concepts=_parse_bool_flag(args.include_in_concepts),
                include_in_long_form=_parse_bool_flag(args.include_in_long_form),
                collection_tags=_split_csv(args.collection_tags),
                dimension_overlays=_parse_dimension_overrides(args.dimensions),
                clear_dimension_overlays=args.clear_dimensions,
                notes=args.notes or None,
            )
        elif args.inner_command == "chunk-link":
            result = update_chunk_link(
                root,
                args.chunk_id,
                args.other_chunk_id,
                kind=args.kind,
                notes=args.notes or None,
                remove=args.remove,
            )
        elif args.inner_command == "prune-preview":
            result = preview_prune_candidates(
                root,
                scope=args.scope,
                query=args.query,
                regex=args.regex,
                statuses=_split_csv(args.statuses),
                source_families=_split_csv(args.source_families),
                source_ref=args.source_ref or None,
                content_kinds=_split_csv(args.content_kinds),
                speaker_roles=_split_csv(args.speaker_roles),
                semantic_classes=_split_csv(args.semantic_classes),
                dimension_filters=_parse_dimension_overrides(args.dimensions),
                include_in_runtime=_parse_bool_flag(args.include_in_runtime),
                target_status=args.status or None,
                limit=args.limit,
            )
        elif args.inner_command == "prune-apply":
            result = apply_prune_candidates(
                root,
                scope=args.scope,
                target_status=args.status,
                query=args.query,
                regex=args.regex,
                statuses=_split_csv(args.statuses),
                source_families=_split_csv(args.source_families),
                source_ref=args.source_ref or None,
                content_kinds=_split_csv(args.content_kinds),
                speaker_roles=_split_csv(args.speaker_roles),
                semantic_classes=_split_csv(args.semantic_classes),
                dimension_filters=_parse_dimension_overrides(args.dimensions),
                include_in_runtime=_parse_bool_flag(args.include_in_runtime),
                notes=args.notes or None,
                limit=args.limit,
            )
        elif args.inner_command == "runtime-pipeline":
            result = get_runtime_pipeline_status(root)
        elif args.inner_command == "runtime-status":
            result = get_runtime_status(root)
        elif args.inner_command == "pond-router":
            if args.pond_router_command == "status":
                result = get_pond_router_status_admin(root)
            elif args.pond_router_command == "preset":
                result = apply_pond_router_preset_admin(root, args.name)
            elif args.pond_router_command == "update":
                result = update_pond_router_config_admin(
                    root,
                    enabled=_parse_bool_flag(args.enabled),
                    mode=args.mode or None,
                    assisted_on_ambiguity=_parse_bool_flag(args.assisted_on_ambiguity),
                    allow_manual_override=_parse_bool_flag(args.allow_manual_override),
                    ambiguity_threshold=args.ambiguity_threshold,
                    local_role_id=args.local_role_id or None,
                    judge_role_id=args.judge_role_id or None,
                    router_version=args.router_version or None,
                )
            else:
                raise ValueError(args.pond_router_command)
        elif args.inner_command == "runtime-pipeline-update":
            enabled = None if args.enabled is None else args.enabled == "true"
            result = update_runtime_pipeline_component_config(
                root,
                args.component_id,
                enabled=enabled,
                order=args.order,
                weight=args.weight,
            )
        elif args.inner_command == "cost-report":
            result = get_cost_summary(root)
        elif args.inner_command == "token-dashboard":
            result = get_cost_summary(root)
        elif args.inner_command == "cost-events":
            events = list_cost_events(root, args.limit)
            result = {"count": len(events), "events": events}
        elif args.inner_command == "token-events":
            events = list_cost_events(root, args.limit)
            result = {"count": len(events), "events": events}
        elif args.inner_command == "source":
            result = get_source_item_detail(root, args.source_item_id, _split_csv(args.domains))
        elif args.inner_command == "chat":
            result = chat_with_thought(
                root,
                args.thought_id,
                args.message,
                args.thread_id,
                _split_csv(args.domains),
            )
        elif args.inner_command == "thread-save":
            result = save_thread(root, args.thread_id, _split_csv(args.domains))
        elif args.inner_command == "thread-delete":
            result = delete_thread(root, args.thread_id)
        elif args.inner_command == "thread":
            result = get_thread_detail(root, args.thread_id)
        elif args.inner_command == "feedback":
            result = record_feedback(root, args.insight_id, args.feedback_state)
        elif args.inner_command == "serve":
            serve_miniapp(
                root,
                args.host,
                args.port,
                _split_csv(args.domains),
                args.limit,
                _split_csv(args.api_prefixes),
            )
            return 0
        elif args.inner_command == "openclaw-bundle":
            result = build_openclaw_bundle(
                root,
                output_dir=Path(args.output_dir).resolve() if args.output_dir else None,
                app_id=args.app_id,
                title=args.title,
                description=args.description,
                api_base_url=args.api_base_url,
            )
        elif args.inner_command == "openclaw-install":
            result = install_openclaw_bundle(
                root,
                apps_root=Path(args.apps_root).expanduser().resolve(),
                app_id=args.app_id,
                api_base_url=args.api_base_url,
            )
        elif args.inner_command == "export":
            result = export_state(root)
        else:
            raise ValueError(args.inner_command)
    elif args.command == "world-studio":
        if args.world_studio_command == "create-world":
            result = worldstudio_create_world(
                root,
                name=args.name,
                summary=args.summary,
                primitives=_split_csv(args.primitives),
                world_rules=_split_many(args.world_rules),
                taste_profile=json.loads(args.taste_profile_json) if args.taste_profile_json else None,
                constraints=json.loads(args.constraints_json) if args.constraints_json else None,
            )
        elif args.world_studio_command == "demo":
            result = worldstudio_run_demo(
                root,
                scene_text=args.scene_text or None,
                duration_seconds=args.duration_seconds,
                aspect_ratio=args.aspect_ratio,
            )
        elif args.world_studio_command == "compile-scene":
            result = worldstudio_compile_scene(
                root,
                args.world_id,
                args.scene_text,
                duration_seconds=args.duration_seconds,
                aspect_ratio=args.aspect_ratio,
                model_preference=args.model_preference,
            )
        elif args.world_studio_command == "inspect-world":
            result = worldstudio_get_world(root, args.world_id) if args.world_id else worldstudio_list_worlds(root)
        elif args.world_studio_command == "get-packet":
            result = worldstudio_get_packet_bundle(root, args.packet_id)
        elif args.world_studio_command == "record-asset":
            result = worldstudio_record_generation_asset(
                root,
                args.packet_id,
                provider=args.provider,
                kind=args.kind,
                url=args.url,
                path=args.path,
                media_type=args.media_type,
                metadata=json.loads(args.metadata_json) if args.metadata_json else {},
            )
        elif args.world_studio_command == "evaluate-output":
            result = worldstudio_evaluate_output(root, args.packet_id, observed_text=args.observed_text)
        elif args.world_studio_command == "populate-start":
            world_id = (args.world_id or "").strip()
            if not world_id:
                name = (args.name or "").strip()
                if not name:
                    raise ValueError("populate-start requires --world-id or --name")
                created = worldstudio_create_world(root, name=name, summary=args.summary or "")
                world_id = created["world_id"]
            result = worldstudio_start_population_session(root, world_id)
        elif args.world_studio_command == "populate-answer":
            result = worldstudio_answer_population_question(root, args.session_id, args.answer)
        elif args.world_studio_command == "population-session":
            result = worldstudio_get_population_session(root, args.session_id)
        elif args.world_studio_command == "inspect-knowledge":
            result = worldstudio_inspect_world_knowledge(root, args.world_id)
        elif args.world_studio_command == "ingest-evidence":
            result = worldstudio_ingest_evidence(
                root,
                args.world_id,
                source_text=args.source_text,
                source_path=args.source_path,
                source_url=args.source_url,
                source_label=args.source_label,
                note=args.note,
                annotations=json.loads(args.annotations_json) if args.annotations_json else {},
            )
        elif args.world_studio_command == "ingest-visual-reference":
            result = worldstudio_ingest_visual_reference(
                root,
                args.world_id,
                source_path=args.source_path,
                source_url=args.source_url,
                source_label=args.source_label,
                note=args.note,
                categories=_split_csv(args.categories),
                liked_aspects=_split_many(args.liked_aspects),
                negative_constraints=_split_many(args.negative_constraints),
                scope=args.scope,
                target_entity=args.target_entity,
            )
        elif args.world_studio_command == "inspect-visual-world":
            result = worldstudio_inspect_visual_world(root, args.world_id)
        elif args.world_studio_command == "compile-visual-context":
            result = worldstudio_compile_visual_context(root, args.world_id, query_text=args.query_text)
        elif args.world_studio_command == "create-motion-object":
            result = worldstudio_create_motion_object(
                root,
                args.world_id,
                label=args.label,
                scope=args.scope,
                intent=args.intent,
                primary_action=args.primary_action,
                body_mechanics=_split_csv(args.body_mechanics),
                secondary_motion=_split_csv(args.secondary_motion),
                constraints=_split_csv(args.constraints),
                negative_constraints=_split_csv(args.negative_constraints),
                compatible_states=_split_csv(args.compatible_states),
                speed=args.speed,
                intensity=args.intensity,
                best_clip_duration=args.best_clip_duration,
                prompt_template=args.prompt_template,
            )
        elif args.world_studio_command == "bind-motion-object":
            result = worldstudio_bind_motion_object(
                root,
                args.world_id,
                motion_id=args.motion_id,
                target_kind=args.target_kind,
                target_id=args.target_id,
                when_tags=_split_csv(args.when_tags),
                exclude_tags=_split_csv(args.exclude_tags),
                priority=args.priority,
            )
        elif args.world_studio_command == "inspect-motion-system":
            result = worldstudio_inspect_motion_system(root, args.world_id)
        elif args.world_studio_command == "compile-motion-plan":
            result = worldstudio_compile_motion_plan(
                root,
                args.world_id,
                scene_text=args.scene_text,
                duration_seconds=args.duration_seconds,
            )
        elif args.world_studio_command == "create-character-profile":
            result = worldstudio_create_character_profile(
                root,
                args.world_id,
                name=args.name,
                summary=args.summary,
                role=args.role,
            )
        elif args.world_studio_command == "inspect-character-system":
            result = worldstudio_inspect_character_system(root, args.world_id, character_id=args.character_id)
        elif args.world_studio_command == "update-character-profile":
            result = worldstudio_update_character_profile_section(
                root,
                args.world_id,
                args.character_id,
                section=args.section,
                value=json.loads(args.value_json),
            )
        elif args.world_studio_command == "update-character-feature":
            result = worldstudio_update_character_feature_object(
                root,
                args.world_id,
                args.feature_id,
                summary=args.summary,
                trait_values=_split_csv(args.trait_values) if args.trait_values else None,
                state_scope=args.state_scope,
            )
        elif args.world_studio_command == "next-question":
            result = worldstudio_next_question(root, args.world_id)
        elif args.world_studio_command == "inspect-evidence":
            result = worldstudio_inspect_world_evidence(root, args.world_id)
        elif args.world_studio_command == "generate-canon":
            result = worldstudio_generate_canon(
                root,
                args.world_id,
                asset_types=_split_csv(args.asset_types),
                style_note=args.style_note,
            )
        elif args.world_studio_command == "compile-scene-from-canon":
            result = worldstudio_compile_scene_from_canon(
                root,
                args.world_id,
                args.scene_text,
                duration_seconds=args.duration_seconds,
                aspect_ratio=args.aspect_ratio,
                model_preference=args.model_preference,
            )
        elif args.world_studio_command == "execute-packet":
            result = worldstudio_execute_higgsfield_packet(root, args.packet_id, mode=args.mode)
        elif args.world_studio_command == "executions":
            result = worldstudio_list_execution_runs(root, packet_id=args.packet_id, world_id=args.world_id)
        elif args.world_studio_command == "inspect-graph":
            result = worldstudio_project_graph(root, args.world_id)
        elif args.world_studio_command == "guide":
            result = worldstudio_get_guide(root)
        else:
            raise ValueError(args.world_studio_command)
    elif args.command == "personal-interface":
        if args.personal_command == "calibrate-start":
            result = start_calibration_interview(root)
        elif args.personal_command == "calibrate-answer":
            result = answer_calibration_question(root, args.session_id, args.answer)
        elif args.personal_command == "profile":
            result = get_profile_snapshot(root)
        elif args.personal_command == "doctor":
            result = doctor_personal_interface(root)
        elif args.personal_command == "learn":
            result = ingest_learning_conversation(
                root,
                source_text=args.source_text or None,
                source_path=args.source_path or None,
                source_url=args.source_url or None,
                source_label=args.source_label or None,
            )
        elif args.personal_command == "rewrite":
            result = rewrite_outgoing_message(
                root,
                draft_text=args.draft_text,
                user_message=args.user_message,
                conversation_window=json.loads(args.conversation_window_json) if args.conversation_window_json else [],
                caller_hints=json.loads(args.caller_hints_json) if args.caller_hints_json else {},
                client_context=json.loads(args.client_context_json) if args.client_context_json else {},
            )
        elif args.personal_command == "rewrite-turn":
            result = rewrite_conversation_turn(
                root,
                draft_text=args.draft_text,
                conversation=json.loads(args.conversation_json),
                caller_hints=json.loads(args.caller_hints_json) if args.caller_hints_json else {},
                client_context=json.loads(args.client_context_json) if args.client_context_json else {},
                window_size=args.window_size,
            )
        elif args.personal_command == "feedback":
            result = record_rewrite_feedback(root, args.rewrite_event_id, args.feedback_state)
        else:
            raise ValueError(args.personal_command)
    else:
        raise ValueError(args.command)

    sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return 0


import json


def guarded_main(argv: list[str] | None = None) -> int:
    try:
        return main(argv)
    except PersonalInterfaceError as exc:
        sys.stdout.write(json.dumps(exc.to_dict(), indent=2, ensure_ascii=False) + "\n")
        return 1
    except TaskPackRoutingError as exc:
        sys.stdout.write(json.dumps(exc.to_dict(), indent=2, ensure_ascii=False) + "\n")
        return 1
