from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

from .worldbuilding_studio import (
    answer_population_question,
    bind_motion_object,
    compile_scene,
    compile_scene_from_canon,
    compile_motion_plan,
    compile_visual_context,
    create_character_profile,
    create_motion_object,
    create_world,
    execute_higgsfield_packet,
    evaluate_output,
    generate_canon,
    get_world_studio_guide,
    get_execution_run,
    get_population_session,
    get_packet_bundle,
    ingest_evidence,
    ingest_visual_reference,
    inspect_character_system,
    inspect_motion_system,
    inspect_visual_world,
    inspect_world_evidence,
    inspect_world_knowledge,
    list_execution_runs,
    next_worldbuilding_question,
    record_generation_asset,
    start_population_session,
    update_character_feature_object,
    update_character_profile_section,
)


MODULE_ID = "surface.worldbuilding.worldbuilding_studio_mcp"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "build_worldbuilding_studio_mcp_server",
)
__all__ = list(PUBLIC_API)


def _vendor_paths(root: Path) -> list[Path]:
    return [root / ".vendor" / "mcp_py"]


def _error_payload(exc: Exception) -> Dict[str, Any]:
    return {"error": str(exc) or exc.__class__.__name__}


class _FallbackWorldbuildingStudioServer:
    def __init__(self, root: Path, reason: str) -> None:
        self.root = root
        self.reason = reason
        self.name = "Worldbuilding Video Studio"


def build_worldbuilding_studio_mcp_server(root: Path):
    for vendor_path in _vendor_paths(root):
        if vendor_path.exists() and str(vendor_path) not in sys.path:
            sys.path.insert(0, str(vendor_path))
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        return _FallbackWorldbuildingStudioServer(root, str(exc))

    server = FastMCP(
        name="Worldbuilding Video Studio",
        instructions=(
            "Compiles worldbuilding semantics, taste profiles, bridge objects, visual-adjacent lenses, "
            "and editing grammar into packet-first video generation instructions."
        ),
    )

    @server.tool()
    def worldstudio_create_world(
        name: str,
        summary: str = "",
        primitives: list[str] | None = None,
        world_rules: list[str] | None = None,
    ) -> Dict[str, Any]:
        try:
            return create_world(
                root,
                name=name,
                summary=summary,
                primitives=primitives or [],
                world_rules=world_rules or [],
            )
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_compile_scene(
        world_id: str,
        scene_text: str,
        duration_seconds: int = 12,
        aspect_ratio: str = "16:9",
    ) -> Dict[str, Any]:
        try:
            return compile_scene(
                root,
                world_id,
                scene_text,
                duration_seconds=duration_seconds,
                aspect_ratio=aspect_ratio,
            )
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_compile_scene_from_canon(
        world_id: str,
        scene_text: str,
        duration_seconds: int = 12,
        aspect_ratio: str = "16:9",
    ) -> Dict[str, Any]:
        try:
            return compile_scene_from_canon(
                root,
                world_id,
                scene_text,
                duration_seconds=duration_seconds,
                aspect_ratio=aspect_ratio,
            )
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_get_packet(packet_id: str) -> Dict[str, Any]:
        try:
            return get_packet_bundle(root, packet_id)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_record_asset(
        packet_id: str,
        provider: str,
        kind: str,
        url: str = "",
        path: str = "",
        media_type: str = "video",
        metadata: dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        try:
            return record_generation_asset(
                root,
                packet_id,
                provider=provider,
                kind=kind,
                url=url,
                path=path,
                media_type=media_type,
                metadata=metadata or {},
            )
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_evaluate_output(packet_id: str, observed_text: str) -> Dict[str, Any]:
        try:
            return evaluate_output(root, packet_id, observed_text=observed_text)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_population_start(world_id: str) -> Dict[str, Any]:
        try:
            return start_population_session(root, world_id)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_population_answer(session_id: str, answer: str) -> Dict[str, Any]:
        try:
            return answer_population_question(root, session_id, answer)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_population_session(session_id: str) -> Dict[str, Any]:
        try:
            return get_population_session(root, session_id)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_inspect_knowledge(world_id: str) -> Dict[str, Any]:
        try:
            return inspect_world_knowledge(root, world_id)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_ingest_evidence(
        world_id: str,
        source_text: str = "",
        source_path: str = "",
        source_url: str = "",
        source_label: str = "",
        note: str = "",
        annotations: dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        try:
            return ingest_evidence(
                root,
                world_id,
                source_text=source_text,
                source_path=source_path,
                source_url=source_url,
                source_label=source_label,
                note=note,
                annotations=annotations or {},
            )
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_ingest_visual_reference(
        world_id: str,
        source_path: str = "",
        source_url: str = "",
        source_label: str = "",
        note: str = "",
        categories: list[str] | None = None,
        liked_aspects: list[str] | None = None,
        negative_constraints: list[str] | None = None,
        scope: str = "global",
        target_entity: str = "",
    ) -> Dict[str, Any]:
        try:
            return ingest_visual_reference(
                root,
                world_id,
                source_path=source_path,
                source_url=source_url,
                source_label=source_label,
                note=note,
                categories=categories or [],
                liked_aspects=liked_aspects or [],
                negative_constraints=negative_constraints or [],
                scope=scope,
                target_entity=target_entity,
            )
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_create_motion_object(
        world_id: str,
        label: str,
        scope: str,
        intent: str = "",
        primary_action: str = "",
        body_mechanics: list[str] | None = None,
        secondary_motion: list[str] | None = None,
        constraints: list[str] | None = None,
        negative_constraints: list[str] | None = None,
        compatible_states: list[str] | None = None,
        speed: str = "",
        intensity: str = "",
        best_clip_duration: int = 4,
        prompt_template: str = "",
    ) -> Dict[str, Any]:
        try:
            return create_motion_object(
                root,
                world_id,
                label=label,
                scope=scope,
                intent=intent,
                primary_action=primary_action,
                body_mechanics=body_mechanics or [],
                secondary_motion=secondary_motion or [],
                constraints=constraints or [],
                negative_constraints=negative_constraints or [],
                compatible_states=compatible_states or [],
                speed=speed,
                intensity=intensity,
                best_clip_duration=best_clip_duration,
                prompt_template=prompt_template,
            )
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_bind_motion_object(
        world_id: str,
        motion_id: str,
        target_kind: str,
        target_id: str = "default",
        when_tags: list[str] | None = None,
        exclude_tags: list[str] | None = None,
        priority: int = 1,
    ) -> Dict[str, Any]:
        try:
            return bind_motion_object(
                root,
                world_id,
                motion_id=motion_id,
                target_kind=target_kind,
                target_id=target_id,
                when_tags=when_tags or [],
                exclude_tags=exclude_tags or [],
                priority=priority,
            )
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_inspect_motion_system(world_id: str) -> Dict[str, Any]:
        try:
            return inspect_motion_system(root, world_id)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_compile_motion_plan(world_id: str, scene_text: str, duration_seconds: int = 4) -> Dict[str, Any]:
        try:
            return compile_motion_plan(root, world_id, scene_text=scene_text, duration_seconds=duration_seconds)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_create_character_profile(
        world_id: str,
        name: str,
        summary: str = "",
        role: str = "",
    ) -> Dict[str, Any]:
        try:
            return create_character_profile(root, world_id, name=name, summary=summary, role=role)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_inspect_character_system(world_id: str, character_id: str = "") -> Dict[str, Any]:
        try:
            return inspect_character_system(root, world_id, character_id=character_id)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_update_character_profile(
        world_id: str,
        character_id: str,
        section: str,
        value: dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            return update_character_profile_section(root, world_id, character_id, section=section, value=value)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_update_character_feature(
        world_id: str,
        feature_id: str,
        summary: str = "",
        trait_values: list[str] | None = None,
        state_scope: str = "",
    ) -> Dict[str, Any]:
        try:
            return update_character_feature_object(
                root,
                world_id,
                feature_id,
                summary=summary,
                trait_values=trait_values,
                state_scope=state_scope,
            )
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_next_question(world_id: str) -> Dict[str, Any]:
        try:
            return next_worldbuilding_question(root, world_id)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_inspect_evidence(world_id: str) -> Dict[str, Any]:
        try:
            return inspect_world_evidence(root, world_id)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_inspect_visual_world(world_id: str) -> Dict[str, Any]:
        try:
            return inspect_visual_world(root, world_id)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_compile_visual_context(world_id: str, query_text: str) -> Dict[str, Any]:
        try:
            return compile_visual_context(root, world_id, query_text=query_text)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_generate_canon(
        world_id: str,
        asset_types: list[str] | None = None,
        style_note: str = "",
    ) -> Dict[str, Any]:
        try:
            return generate_canon(root, world_id, asset_types=asset_types or [], style_note=style_note)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_execute_packet(packet_id: str, mode: str = "auto") -> Dict[str, Any]:
        try:
            return execute_higgsfield_packet(root, packet_id, mode=mode)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_list_executions(packet_id: str = "", world_id: str = "") -> Dict[str, Any]:
        try:
            return list_execution_runs(root, packet_id=packet_id, world_id=world_id)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_get_execution(execution_id: str) -> Dict[str, Any]:
        try:
            return get_execution_run(root, execution_id)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    @server.tool()
    def worldstudio_guide() -> Dict[str, Any]:
        try:
            return get_world_studio_guide(root)
        except Exception as exc:  # noqa: BLE001
            return _error_payload(exc)

    return server
