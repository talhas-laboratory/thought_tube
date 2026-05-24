import json
import importlib
import os
import http.cookiejar as cookiejar
import subprocess
import sqlite3
import threading
import shutil
import socket
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
from io import StringIO
from unittest import mock
from pathlib import Path
from urllib import error as urllib_error
from urllib import request as urllib_request

import conversation_os.cost_tracker as cost_tracker_module
import conversation_os.analysis_units as analysis_units_module
import conversation_os.analysis as analysis_module
import conversation_os.chat_backends as chat_backends_module
import conversation_os.cli as cli_module
import conversation_os.codebase_overview as codebase_overview_module
import conversation_os.conversation_learning as conversation_learning_module
import conversation_os.context_bubbles as context_bubbles_module
import conversation_os.conversation_deltas as conversation_deltas_module
import conversation_os.development_intake as development_intake_module
import conversation_os.development_router as development_router_module
import conversation_os.conversation_synthesis as conversation_synthesis_module
import conversation_os.conversation_threads as conversation_threads_module
import conversation_os.engineering_guard as engineering_guard_module
import conversation_os.holodeck as holodeck_module
import conversation_os.judgment as judgment_module
import conversation_os.knowledge_layer as knowledge_layer_module
import conversation_os.library_tracker as library_tracker_module
import conversation_os.long_form as long_form_module
import conversation_os.meta_layer as meta_layer_module
import conversation_os.meta_objects as meta_objects_module
import conversation_os.miniapp as miniapp_module
import conversation_os.models as models_module
import conversation_os.openclaw_miniapp as openclaw_miniapp_module
import conversation_os.pipeline_runner as pipeline_runner_module
import conversation_os.pipelines as pipelines_module
import conversation_os.personal_interface as personal_interface_module
import conversation_os.personal_interface_mcp as personal_interface_mcp_module
import conversation_os.policy_engine as policy_engine_module
import conversation_os.operators as operators_module
import conversation_os.plugins as plugins_module
import conversation_os.product_inner_world as product_inner_world_module
import conversation_os.review_queue as review_queue_module
import conversation_os.routing as routing_module
import conversation_os.runtime_pipeline as runtime_pipeline_module
import conversation_os.services.openclaw_sync as openclaw_sync_module
import conversation_os.storage as storage_module
import conversation_os.thread_abstractions as thread_abstractions_module
import conversation_os.thread_context as thread_context_module
import conversation_os.thought_factory as thought_factory_module
import conversation_os.vault_ingest as vault_ingest_module
import conversation_os.vault_adapters.openclaw_conversations as openclaw_conversations_module
import conversation_os.worldbuilding_studio as worldbuilding_studio_module
import conversation_os.worldbuilding_studio_mcp as worldbuilding_studio_mcp_module
from conversation_os.analysis import refresh_indexes
from conversation_os.analysis_units import build_analysis_units, load_analysis_units
from conversation_os.chat_backends import (
    apply_openclaw_model_control,
    get_openclaw_model_control_state,
    request_openclaw_reply,
    resolve_chat_backend,
    rollback_openclaw_model_control,
    stage_openclaw_agent_model,
)
from conversation_os.cli import init_repo, main, session_append, session_close, session_import, session_start
from conversation_os.holodeck import (
    _collect_completed_run_drift_warnings,
    _collect_constraint_violations,
    _collect_run_drift_warnings,
)
from conversation_os.conversation_synthesis import (
    choose_operator,
    derive_development_signals,
    emit_thought_packet,
    load_formation_synthesis_reviews,
    load_concept_edges,
    load_concept_nodes,
    load_concept_review_queue,
    load_synthesis_packets,
    load_touch_operations,
    match_shapes,
    record_formation_synthesis_review,
    retrieve_candidates,
    stress_test_candidate,
    synthesize_candidate,
)
from conversation_os.conversation_deltas import (
    build_conversation_deltas,
    load_conversation_deltas,
    load_user_expectations,
)
from conversation_os.conversation_threads import (
    build_conversation_threads,
    load_conversation_threads,
    load_thread_links,
)
from conversation_os.engineering_guard import assess_change_request
from conversation_os.thread_abstractions import (
    build_thread_abstractions,
    load_project_lenses,
    load_thread_abstraction_links,
    load_thread_abstractions,
)
from conversation_os.context_bubbles import (
    build_context_bubbles,
    load_bubble_edges,
    load_bubble_memberships,
    load_bubble_transitions,
    load_context_bubbles,
)
from conversation_os.cost_tracker import get_cost_summary, list_cost_events
from conversation_os.development_intake import (
    approve_development_proposal,
    build_development_proposal,
    build_proposal_task_pack,
    get_development_idea,
    get_development_proposal,
    list_development_ideas,
    list_development_proposals,
    record_development_idea,
)
from conversation_os.development_router import route_development_idea
from conversation_os.meta_layer import extract_meta_layer, load_meta_records, meta_layer_dir
from conversation_os.meta_objects import META_LAYER_FILES, META_LAYER_KINDS
from conversation_os.openclaw_miniapp import build_openclaw_bundle
from conversation_os.operators import _detect_patterns
from conversation_os.miniapp import make_miniapp_handler
from conversation_os.personal_interface import (
    build_personal_interface_profile,
    load_bridge_state,
    load_surface_recipe as load_personal_interface_surface_recipe,
    rewrite_outgoing_message,
    translate_idea_to_technical_framing,
)
from conversation_os.product_inner_world import (
    _materialize_connections,
    build_thought_archive,
    build_thought_feed,
    build_mobile_feed,
    build_mobile_library,
    apply_pond_router_preset,
    append_mobile_capture,
    chat_with_thought,
    create_link_alias_resolution,
    delete_thread,
    derive_graph,
    ensure_mobile_capture_session,
    export_state,
    filter_library_sources,
    filter_knowledge_components,
    get_bubble_detail,
    get_chunk_pond_detail,
    get_link_governance_state,
    get_linking_overview,
    get_dimension_model_role_status,
    get_pond_router_status,
    get_retrieval_bundle,
    govern_library_family,
    govern_library_source,
    get_runtime_pipeline,
    get_runtime_status,
    generate_daily_batch,
    get_runtime_overview,
    load_surface_recipe,
    get_source_item_detail,
    get_thought_detail,
    load_pond_routing_feedback,
    record_feedback,
    record_pond_routing_feedback,
    rederive_library,
    reply_in_mobile_session,
    save_mobile_feed_item,
    save_thread,
    search_library_dimensions,
    seed_sources,
    update_pond_router_config,
    update_chunk_pond_detail,
    update_link_governance,
    update_dimension_model_role_binding,
    update_runtime_pipeline_component,
)
from conversation_os.runtime_pipeline import _try_runtime_pipeline_lock, execute_runtime_pipeline
from conversation_os.routing import build_task_pack
from conversation_os.storage import read_json, read_jsonl, session_events_path, task_packs_dir, write_json, write_jsonl
from conversation_os.thought_factory import build_thought_packets
from conversation_os.library_tracker import (
    apply_prune_candidates,
    derive_chunk_dimension_profiles,
    filter_governed_chunks,
    get_chunk_pond_routing_state,
    get_chunk_status,
    get_library_status,
    load_library_governance,
    load_library_tracker_config,
    override_chunk_pond_routing,
    preview_prune_candidates,
    sync_library_sources,
    update_chunk_governance,
    update_chunk_link,
)
from conversation_os.knowledge_layer import (
    add_alias_resolution,
    build_knowledge_layer,
    build_retrieval_bundle,
    govern_context_link,
    load_context_links,
    load_link_governance,
    load_knowledge_edges,
    load_semantic_capsules,
)
from conversation_os.vault_ingest import (
    ingest_text_content,
    load_chunk_index,
    load_chunk_index_raw,
    load_source_registry,
    load_source_registry_raw,
)
from tools.run_inner_world_backend import InnerWorldGPTBridge, build_gpt_openapi, make_gpt_bridge_handler


REPO_ROOT = Path(__file__).resolve().parents[1]


class ConversationOSTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        for filename in [
            "TENETS.md",
            "AGENTS.md",
            "SESSION_PROTOCOL.md",
            "CONTEXT_ROUTING.md",
            "PRODUCT_THESIS.md",
            "pyproject.toml",
        ]:
            shutil.copy(REPO_ROOT / filename, self.root / filename)
        os.symlink(REPO_ROOT / "plugins", self.root / "plugins", target_is_directory=True)
        os.symlink(REPO_ROOT / "context", self.root / "context", target_is_directory=True)
        os.symlink(REPO_ROOT / "src", self.root / "src", target_is_directory=True)
        os.symlink(REPO_ROOT / "tools", self.root / "tools", target_is_directory=True)
        shutil.copytree(
            REPO_ROOT / "docs" / "research" / "substack-article-structure-2026-04-16",
            self.root / "docs" / "research" / "substack-article-structure-2026-04-16",
        )
        (self.root / "docs" / "plans").mkdir(parents=True, exist_ok=True)
        (self.root / "product" / "inner_world_v1").mkdir(parents=True, exist_ok=True)
        os.symlink(
            REPO_ROOT / "product" / "inner_world_v1" / "miniapp",
            self.root / "product" / "inner_world_v1" / "miniapp",
            target_is_directory=True,
        )
        (self.root / "product" / "inner_world_v1" / "config").mkdir(parents=True, exist_ok=True)
        init_repo(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _start_test_miniapp_server(self):
        static_dir = self.root / "static-test"
        static_dir.mkdir(exist_ok=True)
        (static_dir / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
        handler = make_miniapp_handler(self.root, static_dir, [], 12, ["/api"])
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        sock.close()
        server = ThreadingHTTPServer((host, port), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread, f"http://{host}:{port}"

    def _start_test_mobile_miniapp_server(self):
        mobile_dir = self.root / "product" / "mobile_surface_v1"
        mobile_dir.mkdir(parents=True, exist_ok=True)
        (mobile_dir / "index.html").write_text("<html><body>mobile</body></html>", encoding="utf-8")
        (mobile_dir / "manifest.webmanifest").write_text(
            json.dumps(
                {
                    "name": "Inner World Mobile",
                    "short_name": "Inner World",
                    "start_url": "/mobile",
                    "display": "standalone",
                }
            ),
            encoding="utf-8",
        )
        return self._start_test_miniapp_server()

    def _json_request(self, url: str, *, method: str = "GET", payload: dict | None = None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib_request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urllib_request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def _meta_row(
        self,
        *,
        meta_id: str,
        kind: str,
        label: str,
        summary: str,
        source_ref: str,
        chunk_id: str,
        confidence: float = 0.7,
        attributes: dict | None = None,
    ) -> dict:
        return {
            "meta_id": meta_id,
            "kind": kind,
            "label": label,
            "summary": summary,
            "status": "provisional",
            "confidence": confidence,
            "source_refs": [source_ref],
            "chunk_ids": [chunk_id],
            "evidence": [summary],
            "attributes": attributes or {},
        }

    def _write_meta_rows(self, rows: list[dict]) -> None:
        meta_dir = meta_layer_dir(self.root)
        meta_dir.mkdir(parents=True, exist_ok=True)
        for kind in META_LAYER_KINDS:
            write_jsonl(
                meta_dir / META_LAYER_FILES[kind],
                [row for row in rows if row["kind"] == kind],
            )

    def _write_analysis_units(self, rows: list[dict]) -> None:
        write_jsonl(self.root / "product" / "inner_world_v1" / "data" / "analysis_units.jsonl", rows)

    def _write_shape_signatures(self, rows: list[dict]) -> None:
        write_jsonl(self.root / "product" / "inner_world_v1" / "data" / "shape_signatures.jsonl", rows)

    def _write_shape_memory(self, rows: list[dict]) -> None:
        write_jsonl(self.root / "product" / "inner_world_v1" / "data" / "shape_memory.jsonl", rows)

    def _write_library_config(self, payload: dict) -> Path:
        path = self.root / "product" / "inner_world_v1" / "config" / "library_sources.json"
        write_json(path, payload)
        return path

    def _write_personal_interface_profile(self, answers: dict | None = None) -> Path:
        profile = build_personal_interface_profile(
            answers
            or {
                "recent_moment": "kept_momentum",
                "reply_shape": "push_forward",
                "interruption_tolerance": "flag_gently",
                "annoyances": ["too_long"],
                "decision_mode": "compare_tradeoffs",
                "energy": "direct_plain",
            }
        )
        path = self.root / "product" / "personal_interface_v1" / "data" / "profile.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(path, profile)
        return path

    def _write_personal_interface_runtime(self, payload: dict | None = None) -> Path:
        path = self.root / "product" / "personal_interface_v1" / "data" / "runtime.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        write_json(
            path,
            payload
            or {
                "id": "command_json",
                "command": ["rewrite-backend"],
                "timeout_seconds": 10,
            },
        )
        return path

    def test_storage_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(storage_module.MODULE_ID, "kernel.foundation.storage")
        self.assertEqual(storage_module.CONTRACT_VERSION, "1.0")
        for name in storage_module.PUBLIC_API:
            self.assertIn(name, storage_module.__all__)
            self.assertTrue(hasattr(storage_module, name), name)

    def test_models_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(models_module.MODULE_ID, "kernel.foundation.models")
        self.assertEqual(models_module.CONTRACT_VERSION, "1.0")
        for name in models_module.PUBLIC_MODELS:
            self.assertIn(name, models_module.__all__)
            self.assertTrue(hasattr(models_module, name), name)

    def test_shape_signature_model_dataclasses_round_trip_to_plain_dicts(self) -> None:
        for name in [
            "EvidenceSpan",
            "SignatureEntity",
            "SignatureState",
            "SignatureRelation",
            "SignatureFeedbackLoop",
            "SignatureConstraint",
            "SignatureAbsence",
            "SignatureAffordance",
            "CandidateShape",
            "AlternativeInterpretation",
            "SystemDynamicSignature",
            "ShapeGraphNode",
            "ShapeGraphEdge",
            "AnalogyEvaluationPacket",
            "ShapeMemoryItem",
        ]:
            self.assertIn(name, models_module.PUBLIC_MODELS)
            self.assertIn(name, models_module.__all__)
            self.assertTrue(hasattr(models_module, name), name)

        evidence = models_module.EvidenceSpan(
            source_ref="session:session-shape-1",
            chunk_id="chunk-shape-1",
            text="Users do not understand what the product is.",
            kind="direct_quote",
        )
        entity = models_module.SignatureEntity(
            entity_id="entity-features",
            label="Features",
            node_type="entity",
            role="added_elements",
            confidence=0.78,
            evidence=[evidence.to_dict()],
        )
        state = models_module.SignatureState(
            state_id="state-unclear-value",
            label="Unclear perceived value",
            confidence=0.74,
            evidence=[evidence.to_dict()],
        )
        relation = models_module.SignatureRelation(
            relation_id="rel-features-hide-value",
            source_id="entity-features",
            target_id="entity-core-value",
            edge_type="hides",
            operation="accumulate",
            confidence=0.71,
            evidence=[evidence.to_dict()],
        )
        loop = models_module.SignatureFeedbackLoop(
            loop_id="loop-confusion-complexity",
            label="Confusion creates more explanation and more complexity",
            node_ids=["state-unclear-value", "entity-features"],
            edge_ids=["rel-features-hide-value"],
            confidence=0.67,
            evidence=[evidence.to_dict()],
        )
        constraint = models_module.SignatureConstraint(
            constraint_id="constraint-limited-attention",
            label="Limited user attention",
            confidence=0.81,
            evidence=[evidence.to_dict()],
        )
        absence = models_module.SignatureAbsence(
            absence_id="absence-primary-path",
            label="Missing primary path",
            confidence=0.76,
            evidence=[evidence.to_dict()],
        )
        affordance = models_module.SignatureAffordance(
            affordance_id="affordance-onboarding",
            label="Onboarding can reveal the value hierarchy",
            confidence=0.63,
            evidence=[evidence.to_dict()],
        )
        candidate_shape = models_module.CandidateShape(
            shape_name="Signal Dilution Through Accumulation",
            confidence=0.76,
            rationale="Many useful elements compete for attention and hide the core signal.",
        )
        alternative = models_module.AlternativeInterpretation(
            title="Failed Translation of Hidden Value",
            summary="The issue may be messaging rather than accumulation alone.",
            confidence=0.58,
        )
        signature = models_module.SystemDynamicSignature(
            signature_id="signature-product-overload",
            source_ref="session:session-shape-1",
            source_kind="session",
            source_anchor_id="session-shape-1",
            title="Product clarity failure under feature accumulation",
            summary="Feature growth competes with user attention and obscures the core value.",
            system_boundary="Product experience and user interpretation",
            observer_lens="product_strategy_ux",
            entities=[entity.to_dict()],
            states=[state.to_dict()],
            relations=[relation.to_dict()],
            feedback_loops=[loop.to_dict()],
            constraints=[constraint.to_dict()],
            absences=[absence.to_dict()],
            affordances=[affordance.to_dict()],
            failure_mode="Signal dilution through accumulation",
            desired_transformation="Preserve depth while restoring immediate clarity",
            candidate_shapes=[candidate_shape.to_dict()],
            alternative_interpretations=[alternative.to_dict()],
            evidence_spans=[evidence.to_dict()],
            missing_information=["Whether users are confused by quantity or by unclear value framing."],
            confidence=0.76,
            status="provisional",
            version=1,
            created_at="2026-05-24T09:00:00+00:00",
            updated_at="2026-05-24T09:00:00+00:00",
        )
        graph_node = models_module.ShapeGraphNode(
            graph_node_id="graph-node-features",
            signature_id="signature-product-overload",
            node_key="entity-features",
            node_type="entity",
            label="Features",
            role="added_elements",
            confidence=0.78,
            attributes={"source_ref": "session:session-shape-1"},
        )
        graph_edge = models_module.ShapeGraphEdge(
            graph_edge_id="graph-edge-hide-value",
            signature_id="signature-product-overload",
            source_node_key="entity-features",
            target_node_key="entity-core-value",
            edge_type="hides",
            operation="accumulate",
            confidence=0.71,
            attributes={"loop_member": False},
        )
        evaluation = models_module.AnalogyEvaluationPacket(
            evaluation_id="evaluation-overproduced-song",
            signature_id="signature-product-overload",
            analogy_id="analogy-overproduced-song",
            deterministic_score=0.84,
            role_fit=1.0,
            causal_fit=0.88,
            feedback_fit=0.75,
            leverage_fit=0.86,
            material_transfer_fit=0.8,
            anti_match_penalty=0.0,
            llm_rationale="The analogy preserves competing elements, weak hierarchy, and receiver overload.",
            transfers=["competing_elements", "weak_hierarchy", "receiver_overload"],
            does_not_transfer=["literal_sound_frequency"],
            intervention_risks=["music can tolerate ornamental complexity more than a task-oriented product"],
            verdict="strong_match",
            confidence=0.84,
        )
        memory_item = models_module.ShapeMemoryItem(
            memory_id="shape-memory-signal-dilution",
            scope="user",
            scope_key="user-talha",
            shape_name="Signal Dilution Through Accumulation",
            shape_definition="More useful elements are added, but hierarchy does not scale, so the main signal becomes harder to perceive.",
            validated_examples=["signature-product-overload"],
            anti_matches=["analogy-maze"],
            interventions=["define_primary_path", "demote_secondary_features"],
            missing_constraints=["limited_attention"],
            validation_count=3,
            rejection_count=1,
            last_validated_at="2026-05-24T09:00:00+00:00",
            updated_at="2026-05-24T09:00:00+00:00",
        )

        signature_payload = signature.to_dict()
        self.assertEqual(signature_payload["title"], "Product clarity failure under feature accumulation")
        self.assertEqual(signature_payload["entities"][0]["label"], "Features")
        self.assertEqual(signature_payload["relations"][0]["edge_type"], "hides")
        self.assertEqual(signature_payload["candidate_shapes"][0]["shape_name"], "Signal Dilution Through Accumulation")
        self.assertIsInstance(signature_payload["confidence"], float)
        self.assertEqual(graph_node.to_dict()["node_type"], "entity")
        self.assertEqual(graph_edge.to_dict()["operation"], "accumulate")
        self.assertEqual(evaluation.to_dict()["verdict"], "strong_match")
        self.assertEqual(memory_item.to_dict()["validation_count"], 3)

    def test_cost_tracker_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(cost_tracker_module.MODULE_ID, "kernel.runtime.cost_tracker")
        self.assertEqual(cost_tracker_module.CONTRACT_VERSION, "1.0")
        for name in cost_tracker_module.PUBLIC_API:
            self.assertIn(name, cost_tracker_module.__all__)
            self.assertTrue(hasattr(cost_tracker_module, name), name)

    def test_chat_backends_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(chat_backends_module.MODULE_ID, "kernel.runtime.chat_backends")
        self.assertEqual(chat_backends_module.CONTRACT_VERSION, "1.0")
        for name in chat_backends_module.PUBLIC_API:
            self.assertIn(name, chat_backends_module.__all__)
            self.assertTrue(hasattr(chat_backends_module, name), name)

    def test_codebase_overview_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(codebase_overview_module.MODULE_ID, "builder.codebase.codebase_overview")
        self.assertEqual(codebase_overview_module.CONTRACT_VERSION, "1.0")
        for name in codebase_overview_module.PUBLIC_API:
            self.assertIn(name, codebase_overview_module.__all__)
            self.assertTrue(hasattr(codebase_overview_module, name), name)

    def test_validate_codebase_index_reports_stale_generated_artifacts(self) -> None:
        isolated_root = Path(tempfile.mkdtemp())
        tracked_path = isolated_root / "src" / "conversation_os" / "sample_owner.py"
        tracked_path.parent.mkdir(parents=True, exist_ok=True)
        tracked_path.write_text("def sample_owner():\n    return 'ok'\n", encoding="utf-8")

        manifest_path = isolated_root / "context" / "substrate" / "modules" / "sample_owner.json"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "module_id": "kernel.sample.sample_owner",
                    "path": "src/conversation_os/sample_owner.py",
                    "layer": "kernel",
                    "owner": "Sample owner for freshness testing.",
                    "purpose": "Provide a minimal valid manifest so validation can focus on freshness.",
                    "status": "active",
                    "version": "1.0.0",
                    "public_api": ["sample_owner"],
                    "contains": ["sample_owner"],
                    "depends_on": [],
                    "feeds_into": [],
                    "inputs": [],
                    "outputs": [],
                    "state_owned": [],
                    "surfaces_using": [],
                }
            ),
            encoding="utf-8",
        )

        generated_paths = [
            isolated_root / "context" / "substrate" / "CODEBASE_OVERVIEW.md",
            isolated_root / "context" / "substrate" / "CODEBASE_ATLAS.md",
            isolated_root / "context" / "substrate" / "codebase_map.json",
            isolated_root / "context" / "substrate" / "AGENT_OPERATING_BRIEF.md",
            isolated_root / "context" / "substrate" / "registry" / "module_registry.json",
            isolated_root / "context" / "substrate" / "registry" / "module_browse_map.json",
            isolated_root / "context" / "substrate" / "registry" / "dependency_graph.json",
            isolated_root / "context" / "substrate" / "registry" / "surface_index.json",
            isolated_root / "context" / "substrate" / "registry" / "owner_index.json",
        ]
        for path in generated_paths:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{}", encoding="utf-8")

        stale_epoch = 1_700_000_000
        for path in generated_paths:
            os.utime(path, (stale_epoch, stale_epoch))
        os.utime(manifest_path, (stale_epoch, stale_epoch))
        fresh_epoch = stale_epoch + 60
        os.utime(tracked_path, (fresh_epoch, fresh_epoch))

        validation = codebase_overview_module.validate_codebase_index(isolated_root)

        self.assertFalse(validation["fresh"])
        self.assertIn("Generated codebase artifacts are older than the newest tracked source or manifest", validation["stale_reasons"][0])
        self.assertEqual(validation["newest_source_path"], "src/conversation_os/sample_owner.py")

    def test_cli_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(cli_module.MODULE_ID, "assembly.bootstrap.cli")
        self.assertEqual(cli_module.CONTRACT_VERSION, "1.0")
        for name in cli_module.PUBLIC_API:
            self.assertIn(name, cli_module.__all__)
            self.assertTrue(hasattr(cli_module, name), name)

    def test_conversation_learning_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(conversation_learning_module.MODULE_ID, "kernel.analysis.conversation_learning")
        self.assertEqual(conversation_learning_module.CONTRACT_VERSION, "1.0")
        for name in conversation_learning_module.PUBLIC_API:
            self.assertIn(name, conversation_learning_module.__all__)
            self.assertTrue(hasattr(conversation_learning_module, name), name)

    def test_holodeck_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(holodeck_module.MODULE_ID, "builder.holodeck.holodeck")
        self.assertEqual(holodeck_module.CONTRACT_VERSION, "1.0")
        for name in holodeck_module.PUBLIC_API:
            self.assertIn(name, holodeck_module.__all__)
            self.assertTrue(hasattr(holodeck_module, name), name)

    def test_judgment_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(judgment_module.MODULE_ID, "kernel.reasoning.judgment")
        self.assertEqual(judgment_module.CONTRACT_VERSION, "1.0")
        for name in judgment_module.PUBLIC_API:
            self.assertIn(name, judgment_module.__all__)
            self.assertTrue(hasattr(judgment_module, name), name)

    def test_meta_layer_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(meta_layer_module.MODULE_ID, "kernel.meta.meta_layer")
        self.assertEqual(meta_layer_module.CONTRACT_VERSION, "1.0")
        for name in meta_layer_module.PUBLIC_API:
            self.assertIn(name, meta_layer_module.__all__)
            self.assertTrue(hasattr(meta_layer_module, name), name)

    def test_extract_shape_signatures_derives_structural_signature_from_unit_and_meta(self) -> None:
        self._write_analysis_units(
            [
                {
                    "unit_id": "unit-shape-1",
                    "source_id": "source-shape-1",
                    "source_ref": "session:shape-1",
                    "source_type": "conversation",
                    "source_family": "conversation_library",
                    "sensitivity_tier": "private",
                    "title": "Product clarity",
                    "content": (
                        "Our product has many features but users do not understand what it is. "
                        "We keep adding explanations, which makes the surface feel even more complex."
                    ),
                    "section_path": ["Product clarity"],
                    "chunk_ids": ["chunk-shape-1"],
                    "chunk_indexes": [0],
                    "anchor_chunk_id": "chunk-shape-1",
                    "created_at": "2026-05-24T09:00:00+00:00",
                    "metadata": {"speaker_role": "user"},
                    "metadata_dimensions": {},
                    "speaker_role": "user",
                    "speaker_weight": 1.0,
                    "role_sequence": ["user"],
                    "related_chunk_ids": [],
                    "tokens": [
                        "product",
                        "many",
                        "features",
                        "users",
                        "understand",
                        "adding",
                        "explanations",
                        "complex",
                    ],
                }
            ]
        )
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="signal-frame-shape-1",
                    kind="signal_frame",
                    label="Product clarity failure under feature accumulation",
                    summary="More useful elements are added, but hierarchy does not scale, causing the receiver to lose the central signal.",
                    source_ref="session:shape-1",
                    chunk_id="chunk-shape-1",
                    attributes={
                        "tokens": ["product", "features", "clarity"],
                        "transformation_goal": "Restore a dominant primary path without removing depth.",
                        "speaker_role": "user",
                    },
                ),
                self._meta_row(
                    meta_id="question-shape-1",
                    kind="question",
                    label="What exactly confuses users?",
                    summary="Do users feel overwhelmed by quantity, or do they fail to understand the value proposition?",
                    source_ref="session:shape-1",
                    chunk_id="chunk-shape-1",
                    attributes={"tokens": ["users", "quantity", "value"]},
                ),
                self._meta_row(
                    meta_id="tension-shape-1",
                    kind="tension",
                    label="signal dilution",
                    summary="More added elements create attention competition and reduce clarity.",
                    source_ref="session:shape-1",
                    chunk_id="chunk-shape-1",
                    attributes={"tokens": ["features", "clarity", "attention"], "polarity": "protective"},
                ),
                self._meta_row(
                    meta_id="primitive-shape-1",
                    kind="shared_primitive",
                    label="Signal Dilution Through Accumulation",
                    summary="Useful additions crowd out the main signal when hierarchy does not scale.",
                    source_ref="session:shape-1",
                    chunk_id="chunk-shape-1",
                    attributes={
                        "tokens": ["accumulation", "hierarchy", "signal"],
                        "family": "system_dynamic_shape",
                        "primitive_key": "signal_dilution_through_accumulation",
                    },
                ),
            ]
        )

        summary = meta_layer_module.extract_shape_signatures(self.root, ensure_dependencies=False)
        signatures = meta_layer_module.load_shape_signatures(self.root)

        self.assertEqual(summary["shape_signature_count"], 1)
        self.assertEqual(summary["analysis_unit_count"], 1)
        self.assertEqual(summary["meta_record_count"], 4)
        self.assertEqual(len(signatures), 1)

        signature = signatures[0]
        self.assertEqual(
            signature["title"],
            "Product clarity failure under feature accumulation",
        )
        self.assertEqual(signature["failure_mode"], "Signal Dilution Through Accumulation")
        self.assertEqual(signature["candidate_shapes"][0]["shape_name"], "Signal Dilution Through Accumulation")
        self.assertEqual(signature["candidate_shapes"][0]["attributes"]["origin"], "shared_primitive")
        self.assertEqual(signature["desired_transformation"], "Restore a dominant primary path without removing depth.")
        self.assertEqual(signature["evidence_spans"][0]["chunk_id"], "chunk-shape-1")
        self.assertIn("quantity", signature["missing_information"][0].lower())

        entity_roles = {row["role"] for row in signature["entities"]}
        self.assertIn("added_elements", entity_roles)
        self.assertIn("limited_receiver_capacity", entity_roles)
        self.assertIn("source_signal", entity_roles)

        relation_types = {row["edge_type"] for row in signature["relations"]}
        self.assertIn("competes_with", relation_types)
        self.assertIn("hides", relation_types)
        self.assertIn("feeds_back_into", relation_types)

        self.assertTrue(signature["constraints"])
        self.assertTrue(signature["absences"])

    def test_build_shape_graph_projects_signature_nodes_edges_and_feedback_metadata(self) -> None:
        evidence = models_module.EvidenceSpan(
            source_ref="session:shape-graph-1",
            chunk_id="chunk-shape-graph-1",
            text="Our product has many features but users do not understand what it is.",
            kind="direct_quote",
        )
        entities = [
            models_module.SignatureEntity(
                entity_id="entity-features",
                label="Features",
                node_type="entity",
                role="added_elements",
                confidence=0.78,
                evidence=[evidence.to_dict()],
            ).to_dict(),
            models_module.SignatureEntity(
                entity_id="entity-attention",
                label="User attention",
                node_type="resource",
                role="limited_receiver_capacity",
                confidence=0.74,
                evidence=[evidence.to_dict()],
            ).to_dict(),
            models_module.SignatureEntity(
                entity_id="entity-core-value",
                label="Core value",
                node_type="signal",
                role="source_signal",
                confidence=0.76,
                evidence=[evidence.to_dict()],
            ).to_dict(),
            models_module.SignatureEntity(
                entity_id="entity-explanations",
                label="Explanation layer",
                node_type="entity",
                role="coordination_layer",
                confidence=0.68,
                evidence=[evidence.to_dict()],
            ).to_dict(),
        ]
        states = [
            models_module.SignatureState(
                state_id="state-confusion",
                label="Receiver confusion",
                confidence=0.79,
                evidence=[evidence.to_dict()],
            ).to_dict()
        ]
        relations = [
            models_module.SignatureRelation(
                relation_id="relation-features-compete-attention",
                source_id="entity-features",
                target_id="entity-attention",
                edge_type="competes_with",
                operation="accumulate",
                confidence=0.77,
                evidence=[evidence.to_dict()],
            ).to_dict(),
            models_module.SignatureRelation(
                relation_id="relation-features-hide-core-value",
                source_id="entity-features",
                target_id="entity-core-value",
                edge_type="hides",
                operation="accumulate",
                confidence=0.8,
                evidence=[evidence.to_dict()],
            ).to_dict(),
            models_module.SignatureRelation(
                relation_id="relation-confusion-causes-explanations",
                source_id="state-confusion",
                target_id="entity-explanations",
                edge_type="causes",
                operation="amplify",
                confidence=0.71,
                evidence=[evidence.to_dict()],
            ).to_dict(),
            models_module.SignatureRelation(
                relation_id="relation-explanations-feed-features",
                source_id="entity-explanations",
                target_id="entity-features",
                edge_type="feeds_back_into",
                operation="amplify",
                confidence=0.73,
                evidence=[evidence.to_dict()],
            ).to_dict(),
        ]
        feedback_loops = [
            models_module.SignatureFeedbackLoop(
                loop_id="feedback-loop-clarity-complexity",
                label="Confusion drives more explanation, which drives more complexity.",
                node_ids=["state-confusion", "entity-explanations", "entity-features"],
                edge_ids=[
                    "relation-confusion-causes-explanations",
                    "relation-explanations-feed-features",
                ],
                confidence=0.69,
                evidence=[evidence.to_dict()],
            ).to_dict()
        ]
        constraints = [
            models_module.SignatureConstraint(
                constraint_id="constraint-limited-attention",
                label="Limited receiver capacity",
                confidence=0.75,
                evidence=[evidence.to_dict()],
            ).to_dict()
        ]
        absences = [
            models_module.SignatureAbsence(
                absence_id="absence-primary-hierarchy",
                label="Missing primary hierarchy",
                confidence=0.72,
                evidence=[evidence.to_dict()],
            ).to_dict()
        ]
        affordances = [
            models_module.SignatureAffordance(
                affordance_id="affordance-hierarchy-restoration",
                label="Hierarchy can restore the dominant signal",
                confidence=0.67,
                evidence=[evidence.to_dict()],
            ).to_dict()
        ]
        signature = models_module.SystemDynamicSignature(
            signature_id="signature-shape-graph-1",
            source_ref="session:shape-graph-1",
            source_kind="analysis_unit",
            source_anchor_id="unit-shape-graph-1",
            title="Product clarity failure under feature accumulation",
            summary="Added features compete for attention and hide the core value.",
            system_boundary="Product experience and user interpretation",
            observer_lens="structural_interpretation",
            entities=entities,
            states=states,
            relations=relations,
            feedback_loops=feedback_loops,
            constraints=constraints,
            absences=absences,
            affordances=affordances,
            failure_mode="Signal Dilution Through Accumulation",
            desired_transformation="Restore a dominant primary path without removing depth.",
            candidate_shapes=[
                models_module.CandidateShape(
                    shape_name="Signal Dilution Through Accumulation",
                    confidence=0.77,
                    rationale="More elements compete for attention and hide the main signal.",
                ).to_dict()
            ],
            alternative_interpretations=[],
            evidence_spans=[evidence.to_dict()],
            missing_information=[],
            confidence=0.76,
            status="provisional",
            version=1,
            created_at="2026-05-24T10:00:00+00:00",
            updated_at="2026-05-24T10:00:00+00:00",
        ).to_dict()
        self._write_shape_signatures([signature])

        summary = meta_layer_module.build_shape_graph(self.root, ensure_dependencies=False)
        nodes = meta_layer_module.load_shape_graph_nodes(self.root)
        edges = meta_layer_module.load_shape_graph_edges(self.root)

        self.assertEqual(summary["shape_signature_count"], 1)
        self.assertEqual(summary["shape_graph_node_count"], 8)
        self.assertEqual(summary["shape_graph_edge_count"], 4)
        self.assertEqual(summary["invalid_edge_count"], 0)
        self.assertEqual(len(nodes), 8)
        self.assertEqual(len(edges), 4)

        node_keys = {row["node_key"] for row in nodes}
        self.assertIn("entity-features", node_keys)
        self.assertIn("state-confusion", node_keys)
        self.assertIn("constraint-limited-attention", node_keys)
        self.assertIn("absence-primary-hierarchy", node_keys)
        self.assertIn("affordance-hierarchy-restoration", node_keys)
        self.assertTrue(all(row["source_node_key"] in node_keys for row in edges))
        self.assertTrue(all(row["target_node_key"] in node_keys for row in edges))

        loop_edge = next(row for row in edges if row["graph_edge_id"] == "relation-explanations-feed-features")
        self.assertEqual(loop_edge["edge_type"], "feeds_back_into")
        self.assertEqual(
            loop_edge["attributes"]["feedback_loop_ids"],
            ["feedback-loop-clarity-complexity"],
        )

    def test_retrieve_candidates_attaches_shape_signature_hints_to_candidate_attributes(self) -> None:
        evidence = models_module.EvidenceSpan(
            source_ref="session:shape-hints-1",
            chunk_id="chunk-shape-hints-1",
            text="Our product has many features but users do not understand what it is.",
            kind="direct_quote",
        )
        signature = models_module.SystemDynamicSignature(
            signature_id="signature-shape-hints-1",
            source_ref="session:shape-hints-1",
            source_kind="analysis_unit",
            source_anchor_id="unit-shape-hints-1",
            title="Product clarity failure under feature accumulation",
            summary="Added features compete for attention and hide the core value.",
            system_boundary="Product experience",
            observer_lens="structural_interpretation",
            entities=[
                models_module.SignatureEntity(
                    entity_id="entity-features",
                    label="Features",
                    node_type="entity",
                    role="added_elements",
                    confidence=0.78,
                    evidence=[evidence.to_dict()],
                ).to_dict(),
                models_module.SignatureEntity(
                    entity_id="entity-attention",
                    label="User attention",
                    node_type="resource",
                    role="limited_receiver_capacity",
                    confidence=0.74,
                    evidence=[evidence.to_dict()],
                ).to_dict(),
            ],
            states=[],
            relations=[
                models_module.SignatureRelation(
                    relation_id="relation-features-compete-attention",
                    source_id="entity-features",
                    target_id="entity-attention",
                    edge_type="competes_with",
                    operation="accumulate",
                    confidence=0.77,
                    evidence=[evidence.to_dict()],
                ).to_dict()
            ],
            feedback_loops=[],
            constraints=[],
            absences=[],
            affordances=[],
            failure_mode="Signal Dilution Through Accumulation",
            desired_transformation="Restore a dominant primary path.",
            candidate_shapes=[
                models_module.CandidateShape(
                    shape_name="Signal Dilution Through Accumulation",
                    confidence=0.77,
                    rationale="More elements compete for attention and hide the main signal.",
                ).to_dict()
            ],
            alternative_interpretations=[],
            evidence_spans=[evidence.to_dict()],
            missing_information=[],
            confidence=0.76,
            status="provisional",
            version=1,
            created_at="2026-05-24T10:00:00+00:00",
            updated_at="2026-05-24T10:00:00+00:00",
        ).to_dict()
        self._write_shape_signatures([signature])

        pair_rows = [
            {
                "score": 0.52,
                "edge_kind": "relates_to",
                "left": self._meta_row(
                    meta_id="meta-shape-hints-1",
                    kind="signal_frame",
                    label="Product clarity failure under feature accumulation",
                    summary="Added features compete for attention and hide the core value.",
                    source_ref="session:shape-hints-1",
                    chunk_id="chunk-shape-hints-1",
                ),
                "right": self._meta_row(
                    meta_id="meta-unrelated-1",
                    kind="theme",
                    label="Unrelated note",
                    summary="Something else entirely.",
                    source_ref="session:other-1",
                    chunk_id="chunk-other-1",
                ),
            }
        ]

        with mock.patch("conversation_os.knowledge_layer.select_candidate_pairs", return_value=pair_rows):
            candidates = retrieve_candidates(
                self.root,
                {
                    "query_text": "product clarity feature overload",
                    "source_refs": ["session:shape-hints-1"],
                    "meta_refs": [],
                },
                limit=4,
            )

        enriched = next(candidate for candidate in candidates if candidate.meta_id == "meta-shape-hints-1")
        self.assertEqual(enriched.attributes["shape_signature_ids"], ["signature-shape-hints-1"])
        self.assertEqual(
            enriched.attributes["shape_candidate_shapes"],
            ["Signal Dilution Through Accumulation"],
        )
        self.assertEqual(
            enriched.attributes["shape_node_roles"],
            ["added_elements", "limited_receiver_capacity"],
        )
        self.assertEqual(enriched.attributes["shape_edge_types"], ["competes_with"])
        self.assertEqual(enriched.attributes["shape_operations"], ["accumulate"])
        self.assertFalse(enriched.attributes["shape_has_feedback_loop"])

    def test_match_shapes_prefers_structural_overlap_when_shape_hints_exist(self) -> None:
        anchor = conversation_synthesis_module.FormationCandidate(
            candidate_id="anchor-1",
            meta_id="meta-anchor-1",
            kind="signal_frame",
            label="Product clarity failure",
            summary="Many features hide the core value and confuse the user.",
            source_refs=["session:anchor-1"],
            chunk_ids=["chunk-anchor-1"],
            candidate_score=0.78,
            attributes={
                "shape_signature_ids": ["signature-anchor-1"],
                "shape_candidate_shapes": ["Signal Dilution Through Accumulation"],
                "shape_node_roles": [
                    "added_elements",
                    "limited_receiver_capacity",
                    "source_signal",
                    "coordination_layer",
                ],
                "shape_edge_types": ["competes_with", "hides", "feeds_back_into"],
                "shape_operations": ["accumulate", "amplify"],
                "shape_has_feedback_loop": True,
            },
        )
        strong_candidate = conversation_synthesis_module.FormationCandidate(
            candidate_id="candidate-song-1",
            meta_id="meta-song-1",
            kind="transfer_target",
            label="Overproduced song",
            summary="Too many layers compete with the lead melody and crowd the mix.",
            source_refs=["session:song-1"],
            chunk_ids=["chunk-song-1"],
            candidate_score=0.74,
            attributes={
                "shape_signature_ids": ["signature-song-1"],
                "shape_candidate_shapes": ["Signal Dilution Through Accumulation"],
                "shape_node_roles": [
                    "added_elements",
                    "limited_receiver_capacity",
                    "source_signal",
                    "coordination_layer",
                ],
                "shape_edge_types": ["competes_with", "hides", "feeds_back_into"],
                "shape_operations": ["accumulate", "amplify"],
                "shape_has_feedback_loop": True,
            },
        )
        weak_candidate = conversation_synthesis_module.FormationCandidate(
            candidate_id="candidate-maze-1",
            meta_id="meta-maze-1",
            kind="transfer_target",
            label="Maze",
            summary="A user gets confused trying to find the exit through a hidden path.",
            source_refs=["session:maze-1"],
            chunk_ids=["chunk-maze-1"],
            candidate_score=0.74,
            attributes={
                "shape_signature_ids": ["signature-maze-1"],
                "shape_candidate_shapes": ["Search Confusion Through Hidden Route"],
                "shape_node_roles": ["receiver", "blocked_transition", "goal"],
                "shape_edge_types": ["blocks", "delays"],
                "shape_operations": ["delay"],
                "shape_has_feedback_loop": False,
            },
        )

        matches = match_shapes(anchor, [weak_candidate, strong_candidate])

        self.assertEqual(matches[0].candidate_meta_id, "meta-song-1")
        self.assertIn("shape_structure", matches[0].reasons)
        self.assertEqual(matches[0].structural_fit["role_fit"], 1.0)
        self.assertEqual(matches[0].structural_fit["edge_fit"], 1.0)
        self.assertEqual(matches[0].structural_fit["operation_fit"], 1.0)
        self.assertEqual(matches[0].structural_fit["feedback_fit"], 1.0)
        self.assertGreaterEqual(matches[0].structural_fit["structural_score"], 0.9)
        self.assertLess(matches[1].structural_fit["role_fit"], matches[0].structural_fit["role_fit"])
        self.assertLess(matches[1].structural_fit["structural_score"], matches[0].structural_fit["structural_score"])
        self.assertEqual(matches[0].structural_fit["verdict"], "strong_match")
        self.assertEqual(matches[1].structural_fit["verdict"], "reject")
        self.assertGreater(matches[1].structural_fit["anti_match_penalty"], 0.0)
        self.assertGreater(matches[0].score, matches[1].score)

    def test_match_shapes_clamps_rejected_structural_mismatch_score(self) -> None:
        anchor = conversation_synthesis_module.FormationCandidate(
            candidate_id="anchor-low-score-1",
            meta_id="meta-anchor-low-score-1",
            kind="signal_frame",
            label="Product clarity failure",
            summary="Many features obscure the main signal.",
            source_refs=[],
            chunk_ids=[],
            candidate_score=0.01,
            attributes={
                "shape_signature_ids": ["signature-anchor-low-score-1"],
                "shape_node_roles": ["source_signal"],
                "shape_edge_types": ["hides"],
                "shape_operations": ["accumulate"],
                "shape_has_feedback_loop": False,
            },
        )
        candidate = conversation_synthesis_module.FormationCandidate(
            candidate_id="candidate-low-score-1",
            meta_id="meta-candidate-low-score-1",
            kind="transfer_target",
            label="Blocked maze path",
            summary="A route is delayed by a hidden obstruction.",
            source_refs=[],
            chunk_ids=[],
            candidate_score=0.01,
            attributes={
                "shape_signature_ids": ["signature-candidate-low-score-1"],
                "shape_node_roles": ["goal"],
                "shape_edge_types": ["blocks"],
                "shape_operations": ["delay"],
                "shape_has_feedback_loop": True,
            },
        )

        match = match_shapes(anchor, [candidate])[0]

        self.assertEqual(match.structural_fit["verdict"], "reject")
        self.assertIn("shape_mismatch", match.reasons)
        self.assertEqual(match.score, 0.0)

    def test_shape_memory_feedback_persists_validation_and_anti_match_records(self) -> None:
        accepted = meta_layer_module.record_shape_feedback(
            self.root,
            scope="project",
            scope_key="thought-tube",
            shape_name="Signal Dilution Through Accumulation",
            shape_definition="Useful elements accumulate faster than hierarchy, so the main signal becomes harder to perceive.",
            feedback_type="accepted",
            validated_example="signature-product-overload",
            intervention="define_primary_path",
        )
        rejected = meta_layer_module.record_shape_feedback(
            self.root,
            scope="project",
            scope_key="thought-tube",
            shape_name="Signal Dilution Through Accumulation",
            shape_definition="Useful elements accumulate faster than hierarchy, so the main signal becomes harder to perceive.",
            feedback_type="rejected",
            rejected_candidate_id="meta-maze-1",
            anchor_meta_id="meta-anchor-1",
            anti_match_penalty=0.25,
        )

        memory_rows = meta_layer_module.load_shape_memory(self.root)

        self.assertEqual(accepted["shape_name"], "Signal Dilution Through Accumulation")
        self.assertEqual(rejected["rejection_count"], 1)
        self.assertEqual(len(memory_rows), 1)
        self.assertEqual(memory_rows[0]["validation_count"], 1)
        self.assertEqual(memory_rows[0]["rejection_count"], 1)
        self.assertIn("signature-product-overload", memory_rows[0]["validated_examples"])
        self.assertIn("meta-maze-1", memory_rows[0]["anti_matches"])
        self.assertEqual(memory_rows[0]["attributes"]["anti_match_records"][0]["anchor_meta_id"], "meta-anchor-1")
        self.assertEqual(memory_rows[0]["attributes"]["anti_match_records"][0]["candidate_meta_id"], "meta-maze-1")

    def test_recorded_anti_match_penalty_downranks_future_structural_match(self) -> None:
        def build_signature(signature_id: str, source_ref: str) -> dict:
            evidence = models_module.EvidenceSpan(
                source_ref=source_ref,
                chunk_id=f"chunk-{signature_id}",
                text="Users get confused following a route through the system.",
                kind="direct_quote",
            )
            return models_module.SystemDynamicSignature(
                signature_id=signature_id,
                source_ref=source_ref,
                source_kind="analysis_unit",
                source_anchor_id=f"unit-{signature_id}",
                title="Route confusion structure",
                summary="A receiver gets delayed or blocked while trying to reach a goal.",
                system_boundary="User interpretation flow",
                observer_lens="structural_interpretation",
                entities=[
                    models_module.SignatureEntity(
                        entity_id=f"{signature_id}-receiver",
                        label="Receiver",
                        node_type="receiver",
                        role="receiver",
                        confidence=0.8,
                        evidence=[evidence.to_dict()],
                    ).to_dict(),
                    models_module.SignatureEntity(
                        entity_id=f"{signature_id}-path",
                        label="Blocked path",
                        node_type="constraint",
                        role="blocked_transition",
                        confidence=0.76,
                        evidence=[evidence.to_dict()],
                    ).to_dict(),
                    models_module.SignatureEntity(
                        entity_id=f"{signature_id}-goal",
                        label="Goal",
                        node_type="goal",
                        role="goal",
                        confidence=0.74,
                        evidence=[evidence.to_dict()],
                    ).to_dict(),
                ],
                states=[],
                relations=[
                    models_module.SignatureRelation(
                        relation_id=f"{signature_id}-blocks",
                        source_id=f"{signature_id}-path",
                        target_id=f"{signature_id}-receiver",
                        edge_type="blocks",
                        operation="delay",
                        confidence=0.79,
                        evidence=[evidence.to_dict()],
                    ).to_dict()
                ],
                feedback_loops=[],
                constraints=[],
                absences=[],
                affordances=[],
                failure_mode="Route confusion through blocked transition",
                desired_transformation="Restore a visible path to the goal.",
                candidate_shapes=[
                    models_module.CandidateShape(
                        shape_name="Route Confusion Through Blocked Transition",
                        confidence=0.75,
                        rationale="A receiver is delayed or blocked before reaching the intended goal.",
                    ).to_dict()
                ],
                alternative_interpretations=[],
                evidence_spans=[evidence.to_dict()],
                missing_information=[],
                confidence=0.75,
                status="provisional",
                version=1,
                created_at="2026-05-24T10:00:00+00:00",
                updated_at="2026-05-24T10:00:00+00:00",
            ).to_dict()

        self._write_shape_signatures(
            [
                build_signature("signature-anchor-anti", "session:anchor-anti"),
                build_signature("signature-remembered-anti", "session:remembered-anti"),
                build_signature("signature-fresh-anti", "session:fresh-anti"),
            ]
        )

        write_jsonl(
            self.root / "product" / "inner_world_v1" / "data" / "review_queue.jsonl",
            [
                {
                    "review_id": "review-anti-match-1",
                    "queue_type": "formation_synthesis",
                    "status": "needs_review",
                    "created_at": "2026-05-24T10:10:00+00:00",
                    "anti_match_summary": {
                        "anchor_meta_id": "meta-anchor-anti",
                        "candidate_meta_id": "meta-remembered-anti",
                        "operator_key": "abduce_hypothesis",
                        "verdict": "reject",
                        "structural_score": 0.22,
                        "anti_match_penalty": 0.25,
                        "shared_tokens": ["route", "confusion"],
                    },
                }
            ],
        )

        pair_rows = [
            {
                "score": 0.52,
                "edge_kind": "relates_to",
                "left": self._meta_row(
                    meta_id="meta-anchor-anti",
                    kind="signal_frame",
                    label="Route confusion anchor",
                    summary="Users get confused following a route through the system.",
                    source_ref="session:anchor-anti",
                    chunk_id="chunk-anchor-anti",
                ),
                "right": self._meta_row(
                    meta_id="meta-remembered-anti",
                    kind="transfer_target",
                    label="Route confusion analogy alpha",
                    summary="Users get confused following a route through the system.",
                    source_ref="session:remembered-anti",
                    chunk_id="chunk-remembered-anti",
                ),
            },
            {
                "score": 0.52,
                "edge_kind": "relates_to",
                "left": self._meta_row(
                    meta_id="meta-anchor-anti",
                    kind="signal_frame",
                    label="Route confusion anchor",
                    summary="Users get confused following a route through the system.",
                    source_ref="session:anchor-anti",
                    chunk_id="chunk-anchor-anti",
                ),
                "right": self._meta_row(
                    meta_id="meta-fresh-anti",
                    kind="transfer_target",
                    label="Route confusion analogy beta",
                    summary="Users get confused following a route through the system.",
                    source_ref="session:fresh-anti",
                    chunk_id="chunk-fresh-anti",
                ),
            },
        ]

        with mock.patch("conversation_os.knowledge_layer.select_candidate_pairs", return_value=pair_rows):
            candidates = retrieve_candidates(
                self.root,
                {
                    "query_text": "route confusion blocked transition",
                    "source_refs": ["session:anchor-anti"],
                    "meta_refs": ["meta-anchor-anti"],
                },
                limit=6,
            )

        anchor = next(candidate for candidate in candidates if candidate.meta_id == "meta-anchor-anti")
        remembered = next(candidate for candidate in candidates if candidate.meta_id == "meta-remembered-anti")
        fresh = next(candidate for candidate in candidates if candidate.meta_id == "meta-fresh-anti")

        self.assertEqual(remembered.attributes["shape_anti_match_anchor_meta_ids"], ["meta-anchor-anti"])
        self.assertEqual(remembered.attributes["shape_anti_match_penalty"], 0.25)
        self.assertNotIn("shape_anti_match_anchor_meta_ids", fresh.attributes)

        matches = match_shapes(anchor, candidates)
        remembered_match = next(row for row in matches if row.candidate_meta_id == "meta-remembered-anti")
        fresh_match = next(row for row in matches if row.candidate_meta_id == "meta-fresh-anti")

        self.assertIn("anti_match_memory", remembered_match.reasons)
        self.assertLess(remembered_match.structural_fit["structural_score"], fresh_match.structural_fit["structural_score"])
        self.assertLess(remembered_match.score, fresh_match.score)

    def test_shape_memory_beats_review_queue_as_anti_match_source(self) -> None:
        def build_signature(signature_id: str, source_ref: str) -> dict:
            evidence = models_module.EvidenceSpan(
                source_ref=source_ref,
                chunk_id=f"chunk-{signature_id}",
                text="Users get confused following a route through the system.",
                kind="direct_quote",
            )
            return models_module.SystemDynamicSignature(
                signature_id=signature_id,
                source_ref=source_ref,
                source_kind="analysis_unit",
                source_anchor_id=f"unit-{signature_id}",
                title="Route confusion structure",
                summary="A receiver gets delayed or blocked while trying to reach a goal.",
                system_boundary="User interpretation flow",
                observer_lens="structural_interpretation",
                entities=[
                    models_module.SignatureEntity(
                        entity_id=f"{signature_id}-receiver",
                        label="Receiver",
                        node_type="receiver",
                        role="receiver",
                        confidence=0.8,
                        evidence=[evidence.to_dict()],
                    ).to_dict(),
                    models_module.SignatureEntity(
                        entity_id=f"{signature_id}-path",
                        label="Blocked path",
                        node_type="constraint",
                        role="blocked_transition",
                        confidence=0.76,
                        evidence=[evidence.to_dict()],
                    ).to_dict(),
                    models_module.SignatureEntity(
                        entity_id=f"{signature_id}-goal",
                        label="Goal",
                        node_type="goal",
                        role="goal",
                        confidence=0.74,
                        evidence=[evidence.to_dict()],
                    ).to_dict(),
                ],
                states=[],
                relations=[
                    models_module.SignatureRelation(
                        relation_id=f"{signature_id}-blocks",
                        source_id=f"{signature_id}-path",
                        target_id=f"{signature_id}-receiver",
                        edge_type="blocks",
                        operation="delay",
                        confidence=0.79,
                        evidence=[evidence.to_dict()],
                    ).to_dict()
                ],
                feedback_loops=[],
                constraints=[],
                absences=[],
                affordances=[],
                failure_mode="Route confusion through blocked transition",
                desired_transformation="Restore a visible path to the goal.",
                candidate_shapes=[
                    models_module.CandidateShape(
                        shape_name="Route Confusion Through Blocked Transition",
                        confidence=0.75,
                        rationale="A receiver is delayed or blocked before reaching the intended goal.",
                    ).to_dict()
                ],
                alternative_interpretations=[],
                evidence_spans=[evidence.to_dict()],
                missing_information=[],
                confidence=0.75,
                status="provisional",
                version=1,
                created_at="2026-05-24T10:00:00+00:00",
                updated_at="2026-05-24T10:00:00+00:00",
            ).to_dict()

        self._write_shape_signatures(
            [
                build_signature("signature-anchor-memory", "session:anchor-memory"),
                build_signature("signature-remembered-memory", "session:remembered-memory"),
            ]
        )
        self._write_shape_memory(
            [
                models_module.ShapeMemoryItem(
                    memory_id="shape-memory-route-confusion",
                    scope="project",
                    scope_key="thought-tube",
                    shape_name="Route Confusion Through Blocked Transition",
                    shape_definition="A receiver is delayed or blocked before reaching the goal.",
                    anti_matches=["meta-remembered-memory"],
                    rejection_count=1,
                    updated_at="2026-05-24T10:00:00+00:00",
                    attributes={
                        "anti_match_records": [
                            {
                                "anchor_meta_id": "meta-anchor-memory",
                                "candidate_meta_id": "meta-remembered-memory",
                                "anti_match_penalty": 0.3,
                            }
                        ]
                    },
                ).to_dict()
            ]
        )
        write_jsonl(
            self.root / "product" / "inner_world_v1" / "data" / "review_queue.jsonl",
            [
                {
                    "review_id": "review-memory-fallback-1",
                    "queue_type": "formation_synthesis",
                    "status": "needs_review",
                    "created_at": "2026-05-24T10:10:00+00:00",
                    "anti_match_summary": {
                        "anchor_meta_id": "meta-anchor-memory",
                        "candidate_meta_id": "meta-remembered-memory",
                        "anti_match_penalty": 0.1,
                    },
                }
            ],
        )
        pair_rows = [
            {
                "score": 0.52,
                "edge_kind": "relates_to",
                "left": self._meta_row(
                    meta_id="meta-anchor-memory",
                    kind="signal_frame",
                    label="Route confusion anchor",
                    summary="Users get confused following a route through the system.",
                    source_ref="session:anchor-memory",
                    chunk_id="chunk-anchor-memory",
                ),
                "right": self._meta_row(
                    meta_id="meta-remembered-memory",
                    kind="transfer_target",
                    label="Route confusion analogy alpha",
                    summary="Users get confused following a route through the system.",
                    source_ref="session:remembered-memory",
                    chunk_id="chunk-remembered-memory",
                ),
            }
        ]

        with mock.patch("conversation_os.knowledge_layer.select_candidate_pairs", return_value=pair_rows):
            candidates = retrieve_candidates(
                self.root,
                {
                    "query_text": "route confusion blocked transition",
                    "source_refs": ["session:anchor-memory"],
                    "meta_refs": ["meta-anchor-memory"],
                },
                limit=4,
            )

        remembered = next(candidate for candidate in candidates if candidate.meta_id == "meta-remembered-memory")
        self.assertEqual(remembered.attributes["shape_anti_match_penalty"], 0.3)
        self.assertEqual(remembered.attributes["shape_anti_match_source"], "shape_memory")

    def test_synthesize_candidate_preserves_structural_fit_payload(self) -> None:
        match = conversation_synthesis_module.ShapeMatch(
            match_id="shape-match-1",
            anchor_meta_id="meta-anchor-1",
            anchor_kind="signal_frame",
            candidate_meta_id="meta-song-1",
            candidate_kind="transfer_target",
            edge_kind="relates_to",
            score=0.88,
            shared_tokens=["signal", "attention"],
            reasons=["shared_tokens", "shape_structure"],
            operator_hints=["structure_map", "adapt_case"],
            source_refs=["session:anchor-1", "session:song-1"],
            source_item_ids=["chunk-anchor-1", "chunk-song-1"],
            evidence=["anchor evidence", "candidate evidence"],
            structural_fit={
                "role_fit": 1.0,
                "edge_fit": 1.0,
                "operation_fit": 1.0,
                "feedback_fit": 1.0,
                "anti_match_penalty": 0.0,
                "structural_score": 0.92,
                "verdict": "strong_match",
            },
            anchor_label="Product clarity failure",
            candidate_label="Overproduced song",
        )

        decision = choose_operator(match)
        synthesized = synthesize_candidate(match, decision)

        self.assertEqual(synthesized.structural_fit["verdict"], "strong_match")
        self.assertEqual(synthesized.structural_fit["role_fit"], 1.0)
        self.assertEqual(synthesized.structural_fit["anti_match_penalty"], 0.0)

    def test_choose_operator_falls_back_when_structural_verdict_is_reject(self) -> None:
        match = conversation_synthesis_module.ShapeMatch(
            match_id="shape-match-reject-1",
            anchor_meta_id="meta-anchor-1",
            anchor_kind="signal_frame",
            candidate_meta_id="meta-maze-1",
            candidate_kind="transfer_target",
            edge_kind="relates_to",
            score=0.51,
            shared_tokens=["user", "confusion"],
            reasons=["shared_tokens", "shape_structure"],
            operator_hints=["structure_map", "adapt_case"],
            source_refs=["session:anchor-1", "session:maze-1"],
            source_item_ids=["chunk-anchor-1", "chunk-maze-1"],
            evidence=["anchor evidence", "candidate evidence"],
            structural_fit={
                "role_fit": 0.25,
                "edge_fit": 0.0,
                "operation_fit": 0.0,
                "feedback_fit": 0.0,
                "anti_match_penalty": 0.25,
                "structural_score": 0.12,
                "verdict": "reject",
            },
            anchor_label="Product clarity failure",
            candidate_label="Maze",
        )

        decision = choose_operator(match)

        self.assertEqual(decision.operator_key, "abduce_hypothesis")
        self.assertIn("structural", decision.rationale.lower())

    def test_choose_operator_avoids_structure_map_for_memory_penalized_partial_match(self) -> None:
        match = conversation_synthesis_module.ShapeMatch(
            match_id="shape-match-partial-memory-1",
            anchor_meta_id="meta-anchor-1",
            anchor_kind="signal_frame",
            candidate_meta_id="meta-remembered-anti",
            candidate_kind="transfer_target",
            edge_kind="relates_to",
            score=0.66,
            shared_tokens=["route", "confusion"],
            reasons=["shared_tokens", "shape_structure", "anti_match_memory"],
            operator_hints=["structure_map", "blend", "adapt_case"],
            source_refs=["session:anchor-1", "session:remembered-anti"],
            source_item_ids=["chunk-anchor-1", "chunk-remembered-anti"],
            evidence=["anchor evidence", "candidate evidence"],
            structural_fit={
                "role_fit": 1.0,
                "edge_fit": 1.0,
                "operation_fit": 1.0,
                "feedback_fit": 1.0,
                "review_memory_penalty": 0.25,
                "anti_match_penalty": 0.25,
                "structural_score": 0.67,
                "verdict": "partial_match",
            },
            anchor_label="Route confusion anchor",
            candidate_label="Route confusion analogy alpha",
        )

        decision = choose_operator(match)

        self.assertEqual(decision.operator_key, "blend")
        self.assertIn("anti-match", decision.rationale.lower())

    def test_meta_objects_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(meta_objects_module.MODULE_ID, "kernel.meta.meta_objects")
        self.assertEqual(meta_objects_module.CONTRACT_VERSION, "1.0")
        for name in meta_objects_module.PUBLIC_API:
            self.assertIn(name, meta_objects_module.__all__)
            self.assertTrue(hasattr(meta_objects_module, name), name)

    def test_miniapp_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(miniapp_module.MODULE_ID, "surface.inner_world.miniapp")
        self.assertEqual(miniapp_module.CONTRACT_VERSION, "1.0")
        for name in miniapp_module.PUBLIC_API:
            self.assertIn(name, miniapp_module.__all__)
            self.assertTrue(hasattr(miniapp_module, name), name)

    def test_openclaw_conversations_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(openclaw_conversations_module.MODULE_ID, "assembly.adapters.openclaw_conversations")
        self.assertEqual(openclaw_conversations_module.CONTRACT_VERSION, "1.0")
        for name in openclaw_conversations_module.PUBLIC_API:
            self.assertIn(name, openclaw_conversations_module.__all__)
            self.assertTrue(hasattr(openclaw_conversations_module, name), name)

    def test_openclaw_miniapp_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(openclaw_miniapp_module.MODULE_ID, "surface.inner_world.openclaw_miniapp")
        self.assertEqual(openclaw_miniapp_module.CONTRACT_VERSION, "1.0")
        for name in openclaw_miniapp_module.PUBLIC_API:
            self.assertIn(name, openclaw_miniapp_module.__all__)
            self.assertTrue(hasattr(openclaw_miniapp_module, name), name)

    def test_openclaw_sync_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(openclaw_sync_module.MODULE_ID, "assembly.adapters.openclaw_sync")
        self.assertEqual(openclaw_sync_module.CONTRACT_VERSION, "1.0")
        for name in openclaw_sync_module.PUBLIC_API:
            self.assertIn(name, openclaw_sync_module.__all__)
            self.assertTrue(hasattr(openclaw_sync_module, name), name)

    def test_operators_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(operators_module.MODULE_ID, "kernel.reasoning.operators")
        self.assertEqual(operators_module.CONTRACT_VERSION, "1.0")
        for name in operators_module.PUBLIC_API:
            self.assertIn(name, operators_module.__all__)
            self.assertTrue(hasattr(operators_module, name), name)

    def test_personal_interface_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(personal_interface_module.MODULE_ID, "surface.personal.personal_interface")
        self.assertEqual(personal_interface_module.CONTRACT_VERSION, "1.0")
        for name in personal_interface_module.PUBLIC_API:
            self.assertIn(name, personal_interface_module.__all__)
            self.assertTrue(hasattr(personal_interface_module, name), name)
        self.assertNotIn("ensure_personal_interface_runtime", personal_interface_module.__all__)
        self.assertNotIn("load_bridge_state", personal_interface_module.__all__)
        self.assertNotIn("load_personal_interface_profile", personal_interface_module.__all__)
        self.assertNotIn("load_personal_interface_policy_snapshot", personal_interface_module.__all__)
        self.assertIn("start_calibration_interview", personal_interface_module.__all__)
        self.assertIn("rewrite_outgoing_message", personal_interface_module.__all__)
        self.assertIn("translate_idea_to_technical_framing", personal_interface_module.__all__)

    def test_personal_interface_mcp_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(personal_interface_mcp_module.MODULE_ID, "surface.personal.personal_interface_mcp")
        self.assertEqual(personal_interface_mcp_module.CONTRACT_VERSION, "1.0")
        for name in personal_interface_mcp_module.PUBLIC_API:
            self.assertIn(name, personal_interface_mcp_module.__all__)
            self.assertTrue(hasattr(personal_interface_mcp_module, name), name)

    def test_analysis_units_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(analysis_units_module.MODULE_ID, "kernel.analysis.analysis_units")
        self.assertEqual(analysis_units_module.CONTRACT_VERSION, "1.0")
        for name in analysis_units_module.PUBLIC_API:
            self.assertIn(name, analysis_units_module.__all__)
            self.assertTrue(hasattr(analysis_units_module, name), name)

    def test_analysis_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(analysis_module.MODULE_ID, "kernel.analysis.session_analysis")
        self.assertEqual(analysis_module.CONTRACT_VERSION, "1.0")
        for name in analysis_module.PUBLIC_API:
            self.assertIn(name, analysis_module.__all__)
            self.assertTrue(hasattr(analysis_module, name), name)

    def test_development_intake_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(development_intake_module.MODULE_ID, "assembly.development.development_intake")
        self.assertEqual(development_intake_module.CONTRACT_VERSION, "1.0")
        for name in development_intake_module.PUBLIC_API:
            self.assertIn(name, development_intake_module.__all__)
            self.assertTrue(hasattr(development_intake_module, name), name)

    def test_development_router_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(development_router_module.MODULE_ID, "assembly.development.development_router")
        self.assertEqual(development_router_module.CONTRACT_VERSION, "1.0")
        for name in development_router_module.PUBLIC_API:
            self.assertIn(name, development_router_module.__all__)
            self.assertTrue(hasattr(development_router_module, name), name)

    def test_conversation_deltas_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(conversation_deltas_module.MODULE_ID, "kernel.analysis.conversation_deltas")
        self.assertEqual(conversation_deltas_module.CONTRACT_VERSION, "1.0")
        for name in conversation_deltas_module.PUBLIC_API:
            self.assertIn(name, conversation_deltas_module.__all__)
            self.assertTrue(hasattr(conversation_deltas_module, name), name)

    def test_conversation_threads_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(conversation_threads_module.MODULE_ID, "kernel.analysis.conversation_threads")
        self.assertEqual(conversation_threads_module.CONTRACT_VERSION, "1.0")
        for name in conversation_threads_module.PUBLIC_API:
            self.assertIn(name, conversation_threads_module.__all__)
            self.assertTrue(hasattr(conversation_threads_module, name), name)

    def test_thread_abstractions_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(thread_abstractions_module.MODULE_ID, "kernel.analysis.thread_abstractions")
        self.assertEqual(thread_abstractions_module.CONTRACT_VERSION, "1.0")
        for name in thread_abstractions_module.PUBLIC_API:
            self.assertIn(name, thread_abstractions_module.__all__)
            self.assertTrue(hasattr(thread_abstractions_module, name), name)

    def test_context_bubbles_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(context_bubbles_module.MODULE_ID, "kernel.analysis.context_bubbles")
        self.assertEqual(context_bubbles_module.CONTRACT_VERSION, "1.0")
        for name in context_bubbles_module.PUBLIC_API:
            self.assertIn(name, context_bubbles_module.__all__)
            self.assertTrue(hasattr(context_bubbles_module, name), name)

    def test_engineering_guard_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(engineering_guard_module.MODULE_ID, "builder.guard.engineering_guard")
        self.assertEqual(engineering_guard_module.CONTRACT_VERSION, "1.0")
        for name in engineering_guard_module.PUBLIC_API:
            self.assertIn(name, engineering_guard_module.__all__)
            self.assertTrue(hasattr(engineering_guard_module, name), name)

    def test_lookup_codebase_supports_structured_manifest_filters(self) -> None:
        payload = {
            "entries": [
                {
                    "path": "src/conversation_os/personal_interface.py",
                    "kind": "python",
                    "area": "conversation_os",
                    "summary": "Personal interface surface owner.",
                    "symbols": ["rewrite_outgoing_message"],
                    "imports_internal": [],
                    "module_manifest": {
                        "module_id": "surface.personal.personal_interface",
                        "layer": "surface",
                        "status": "active",
                        "owner": "Personal Interface surface owner.",
                        "purpose": "Handle personal-interface rewrite flows.",
                    },
                },
                {
                    "path": "src/conversation_os/library_tracker.py",
                    "kind": "python",
                    "area": "conversation_os",
                    "summary": "Library governance owner.",
                    "symbols": ["rederive_library"],
                    "imports_internal": [],
                    "module_manifest": {
                        "module_id": "kernel.library.library_tracker",
                        "layer": "kernel",
                        "status": "active",
                        "owner": "Library governance owner.",
                        "purpose": "Own library control plane behavior.",
                    },
                },
            ],
            "module_index": {
                "manifests": [
                    {
                        "module_id": "surface.personal.personal_interface",
                        "path": "src/conversation_os/personal_interface.py",
                        "layer": "surface",
                        "owner": "Personal Interface surface owner.",
                        "purpose": "Handle personal-interface rewrite flows.",
                        "status": "active",
                        "surfaces_using": ["personal_interface"],
                    },
                    {
                        "module_id": "kernel.library.library_tracker",
                        "path": "src/conversation_os/library_tracker.py",
                        "layer": "kernel",
                        "owner": "Library governance owner.",
                        "purpose": "Own library control plane behavior.",
                        "status": "active",
                        "surfaces_using": ["inner_world", "personal_interface"],
                    },
                ]
            },
        }

        with mock.patch("conversation_os.codebase_overview.load_codebase_map", return_value=payload):
            personal_results = codebase_overview_module.lookup_codebase(
                self.root,
                "layer:surface surface:personal_interface module:surface.personal.personal_interface",
                limit=5,
            )
            library_results = codebase_overview_module.lookup_codebase(
                self.root,
                "layer:kernel owner:governance module:library_tracker",
                limit=5,
            )

        self.assertEqual([row["path"] for row in personal_results], ["src/conversation_os/personal_interface.py"])
        self.assertEqual([row["path"] for row in library_results], ["src/conversation_os/library_tracker.py"])

    def test_watch_codebase_overview_refreshes_when_fingerprint_changes(self) -> None:
        with (
            mock.patch(
                "conversation_os.codebase_overview.refresh_codebase_overview",
                side_effect=[
                    {"generated_at": "2026-05-22T00:00:00+00:00"},
                    {"generated_at": "2026-05-22T00:00:02+00:00"},
                ],
            ) as refresh_mock,
            mock.patch(
                "conversation_os.codebase_overview._codebase_input_fingerprint",
                side_effect=["alpha", "beta"],
            ),
            mock.patch("conversation_os.codebase_overview.time.sleep", return_value=None),
        ):
            result = codebase_overview_module.watch_codebase_overview(self.root, interval=0.0, max_iterations=1)

        self.assertEqual(refresh_mock.call_count, 2)
        self.assertEqual(result["refresh_count"], 2)
        self.assertEqual(result["iterations"], 1)
        self.assertEqual(result["last_result"]["generated_at"], "2026-05-22T00:00:02+00:00")

    def test_cli_repo_overview_watch_routes_to_owner(self) -> None:
        with mock.patch(
            "conversation_os.cli.watch_codebase_overview",
            return_value={
                "generated_at": "2026-05-22T00:00:03+00:00",
                "refresh_count": 1,
                "iterations": 0,
                "last_fingerprint": "alpha",
                "last_result": {"generated_at": "2026-05-22T00:00:03+00:00"},
            },
        ) as watch_mock:
            output = StringIO()
            old = os.getcwd()
            os.chdir(self.root)
            try:
                with redirect_stdout(output):
                    exit_code = main(["repo-overview", "watch", "--interval", "0.0", "--max-iterations", "0"])
            finally:
                os.chdir(old)
            payload = json.loads(output.getvalue())

        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["refresh_count"], 1)
        watch_mock.assert_called_once_with(self.root.resolve(), interval=0.0, max_iterations=0)

    def test_knowledge_layer_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(knowledge_layer_module.MODULE_ID, "kernel.knowledge.knowledge_layer")
        self.assertEqual(knowledge_layer_module.CONTRACT_VERSION, "1.0")
        for name in knowledge_layer_module.PUBLIC_API:
            self.assertIn(name, knowledge_layer_module.__all__)
            self.assertTrue(hasattr(knowledge_layer_module, name), name)

    def test_library_tracker_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(library_tracker_module.MODULE_ID, "kernel.library.library_tracker")
        self.assertEqual(library_tracker_module.CONTRACT_VERSION, "1.0")
        for name in library_tracker_module.PUBLIC_API:
            self.assertIn(name, library_tracker_module.__all__)
            self.assertTrue(hasattr(library_tracker_module, name), name)

    def test_conversation_synthesis_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(conversation_synthesis_module.MODULE_ID, "kernel.synthesis.conversation_synthesis")
        self.assertEqual(conversation_synthesis_module.CONTRACT_VERSION, "1.0")
        for name in conversation_synthesis_module.PUBLIC_API:
            self.assertIn(name, conversation_synthesis_module.__all__)
            self.assertTrue(hasattr(conversation_synthesis_module, name), name)

    def test_translate_idea_to_technical_framing_uses_translation_profile(self) -> None:
        self._write_personal_interface_profile()

        payload = translate_idea_to_technical_framing(
            self.root,
            "I want a layer that routes raw ideas into modules and proposals.",
            desired_effect="Produce an approved implementation proposal for the right module family.",
            context_notes=["development-layer orchestration"],
        )

        self.assertEqual(payload["profile_source"], "saved_profile")
        self.assertEqual(payload["communication_mode"], "concept_translation")
        self.assertIn("components", payload["target_artifacts"])
        self.assertIn("confirmed_intent", payload["output_contract"])
        self.assertIn("Desired effect: Produce an approved implementation proposal for the right module family.", payload["confirmed_intent"])
        self.assertTrue(payload["compiled_turn_policy"]["instruction_lines"])

    def test_derive_development_signals_returns_reusable_matches(self) -> None:
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="meta-proposal",
                    kind="shared_primitive",
                    label="Development proposal router",
                    summary="Routes ideas into module proposals and recipe changes.",
                    source_ref="session://idea-router",
                    chunk_id="chunk-1",
                    confidence=0.83,
                ),
                self._meta_row(
                    meta_id="meta-variant",
                    kind="transfer_target",
                    label="Module variant recipe",
                    summary="Creates lens-specific variants instead of mutating the base module.",
                    source_ref="session://idea-router",
                    chunk_id="chunk-2",
                    confidence=0.77,
                ),
            ]
        )

        payload = derive_development_signals(
            self.root,
            "Route ideas into module proposals and create variants when a lens diverges.",
            limit=4,
        )

        self.assertEqual(payload["query_text"], "Route ideas into module proposals and create variants when a lens diverges.")
        self.assertTrue(payload["query_tokens"])
        self.assertTrue(payload["formation_candidates"])
        self.assertEqual(payload["formation_candidates"][0]["meta_id"], "meta-proposal")
        self.assertTrue(payload["shape_matches"])
        self.assertTrue(payload["synthesis_candidates"])

    def test_record_development_idea_persists_translation_and_signals(self) -> None:
        self._write_personal_interface_profile()
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="meta-route",
                    kind="shared_primitive",
                    label="Routing owner",
                    summary="Maps ideas to modules and proposals.",
                    source_ref="session://development",
                    chunk_id="chunk-route",
                    confidence=0.81,
                )
            ]
        )

        record = record_development_idea(
            self.root,
            "Route raw ideas into module proposals.",
            desired_effect="Produce a structured proposal.",
            surface_hints=["personal_interface"],
            source_refs=["session://development"],
        )

        reloaded = get_development_idea(self.root, record["idea_id"])
        listed = list_development_ideas(self.root)

        self.assertEqual(record["intent_kind"], "module_extension")
        self.assertEqual(record["surface_hints"], ["personal_interface"])
        self.assertEqual(record["translated_framing"]["communication_mode"], "concept_translation")
        self.assertTrue(record["development_signals"]["formation_candidates"])
        self.assertEqual(reloaded["idea_id"], record["idea_id"])
        self.assertEqual(listed[0]["idea_id"], record["idea_id"])

    def test_build_and_approve_development_proposal_persists_contract(self) -> None:
        self._write_personal_interface_profile()
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="meta-route",
                    kind="shared_primitive",
                    label="Development proposal router",
                    summary="Routes ideas into module proposals and recipe changes.",
                    source_ref="session://development",
                    chunk_id="chunk-1",
                    confidence=0.84,
                ),
                self._meta_row(
                    meta_id="meta-variant",
                    kind="transfer_target",
                    label="Module variant recipe",
                    summary="Creates lens-specific variants instead of mutating the base module.",
                    source_ref="session://development",
                    chunk_id="chunk-2",
                    confidence=0.78,
                ),
            ]
        )
        idea = record_development_idea(
            self.root,
            "Create a variant-oriented development lens for proposal routing.",
            desired_effect="Produce an approval-ready proposal for the right owner.",
            surface_hints=["personal_interface"],
            source_refs=["session://development"],
        )

        proposal = build_development_proposal(self.root, idea["idea_id"])
        approved = approve_development_proposal(self.root, proposal["proposal_id"], "approved", notes="Looks right.")
        reloaded = get_development_proposal(self.root, proposal["proposal_id"])
        listed = list_development_proposals(self.root, approval_status="approved")

        self.assertEqual(proposal["idea_id"], idea["idea_id"])
        self.assertIn(proposal["route_kind"], {"extend_existing", "create_variant", "update_recipe", "create_new_module"})
        self.assertTrue(proposal["target_module_ids"])
        self.assertEqual(approved["approval_status"], "approved")
        self.assertEqual(reloaded["approval_status"], "approved")
        self.assertEqual(listed[0]["proposal_id"], proposal["proposal_id"])

    def test_build_proposal_task_pack_requires_approval_and_links_artifact(self) -> None:
        self._write_personal_interface_profile()
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="meta-route",
                    kind="shared_primitive",
                    label="Development proposal router",
                    summary="Routes ideas into module proposals and recipe changes.",
                    source_ref="session://development",
                    chunk_id="chunk-1",
                    confidence=0.84,
                )
            ]
        )
        idea = record_development_idea(
            self.root,
            "Route implementation ideas into an approved handoff bundle.",
            desired_effect="Build a task pack only after explicit approval.",
            surface_hints=["personal_interface"],
            source_refs=["session://development"],
        )
        proposal = build_development_proposal(self.root, idea["idea_id"])

        with self.assertRaises(ValueError):
            build_proposal_task_pack(self.root, proposal["proposal_id"])

        approve_development_proposal(self.root, proposal["proposal_id"], "approved")
        result = build_proposal_task_pack(self.root, proposal["proposal_id"])
        reloaded = get_development_proposal(self.root, proposal["proposal_id"])

        self.assertEqual(result["proposal_id"], proposal["proposal_id"])
        self.assertTrue(result["task_pack"]["handoff_validation"]["fresh"])
        self.assertTrue((self.root / "context" / "task_packs" / f"{proposal['proposal_id']}.json").exists())
        self.assertEqual(reloaded["task_pack_ref"]["task_id"], proposal["proposal_id"])

    def test_cli_development_flow_records_routes_proposes_and_approves(self) -> None:
        self._write_personal_interface_profile()
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="meta-route",
                    kind="shared_primitive",
                    label="Development proposal router",
                    summary="Routes ideas into module proposals and recipe changes.",
                    source_ref="session://development",
                    chunk_id="chunk-1",
                    confidence=0.84,
                ),
                self._meta_row(
                    meta_id="meta-variant",
                    kind="transfer_target",
                    label="Module variant recipe",
                    summary="Creates lens-specific variants instead of mutating the base module.",
                    source_ref="session://development",
                    chunk_id="chunk-2",
                    confidence=0.78,
                ),
            ]
        )

        old = os.getcwd()
        os.chdir(self.root)
        try:
            record_output = StringIO()
            with redirect_stdout(record_output):
                exit_code = main(
                    [
                        "development",
                        "record",
                        "--idea-text",
                        "Create a variant-oriented development lens for proposal routing.",
                        "--desired-effect",
                        "Produce an approval-ready proposal for the right owner.",
                        "--surface-hints",
                        "personal_interface",
                        "--source-refs",
                        "session://development",
                    ]
                )
            record_payload = json.loads(record_output.getvalue())

            route_output = StringIO()
            with redirect_stdout(route_output):
                route_exit_code = main(
                    [
                        "development",
                        "route",
                        "--idea-id",
                        record_payload["idea_id"],
                    ]
                )
            route_payload = json.loads(route_output.getvalue())

            propose_output = StringIO()
            with redirect_stdout(propose_output):
                propose_exit_code = main(
                    [
                        "development",
                        "propose",
                        "--idea-id",
                        record_payload["idea_id"],
                    ]
                )
            propose_payload = json.loads(propose_output.getvalue())

            approve_output = StringIO()
            with redirect_stdout(approve_output):
                approve_exit_code = main(
                    [
                        "development",
                        "approve",
                        "--proposal-id",
                        propose_payload["proposal_id"],
                        "--decision",
                        "approved",
                        "--build-task-pack",
                    ]
                )
            approve_payload = json.loads(approve_output.getvalue())
        finally:
            os.chdir(old)

        self.assertEqual(exit_code, 0)
        self.assertEqual(route_exit_code, 0)
        self.assertEqual(propose_exit_code, 0)
        self.assertEqual(approve_exit_code, 0)
        self.assertEqual(record_payload["surface_hints"], ["personal_interface"])
        self.assertIn(route_payload["route_kind"], {"extend_existing", "create_variant", "update_recipe", "create_new_module"})
        self.assertEqual(propose_payload["idea_id"], record_payload["idea_id"])
        self.assertEqual(approve_payload["proposal"]["approval_status"], "approved")
        self.assertTrue(approve_payload["task_pack_result"]["task_pack"]["handoff_validation"]["fresh"])

    def test_cli_development_listing_and_lookup_surfaces_persisted_artifacts(self) -> None:
        self._write_personal_interface_profile()
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="meta-route",
                    kind="shared_primitive",
                    label="Development proposal router",
                    summary="Routes ideas into module proposals and recipe changes.",
                    source_ref="session://development",
                    chunk_id="chunk-1",
                    confidence=0.84,
                )
            ]
        )

        idea = record_development_idea(
            self.root,
            "Route implementation ideas into a visible proposal queue.",
            desired_effect="Let operators inspect recorded ideas and proposals from CLI.",
            surface_hints=["personal_interface"],
            source_refs=["session://development"],
        )
        proposal = build_development_proposal(self.root, idea["idea_id"])

        old = os.getcwd()
        os.chdir(self.root)
        try:
            ideas_output = StringIO()
            with redirect_stdout(ideas_output):
                ideas_exit = main(["development", "ideas", "--limit", "5"])
            ideas_payload = json.loads(ideas_output.getvalue())

            idea_output = StringIO()
            with redirect_stdout(idea_output):
                idea_exit = main(["development", "idea", "--idea-id", idea["idea_id"]])
            idea_payload = json.loads(idea_output.getvalue())

            proposals_output = StringIO()
            with redirect_stdout(proposals_output):
                proposals_exit = main(["development", "proposals", "--limit", "5"])
            proposals_payload = json.loads(proposals_output.getvalue())

            proposal_output = StringIO()
            with redirect_stdout(proposal_output):
                proposal_exit = main(["development", "proposal", "--proposal-id", proposal["proposal_id"]])
            proposal_payload = json.loads(proposal_output.getvalue())
        finally:
            os.chdir(old)

        self.assertEqual(ideas_exit, 0)
        self.assertEqual(idea_exit, 0)
        self.assertEqual(proposals_exit, 0)
        self.assertEqual(proposal_exit, 0)
        self.assertEqual(ideas_payload["idea_count"], 1)
        self.assertEqual(ideas_payload["ideas"][0]["idea_id"], idea["idea_id"])
        self.assertIn("idea_preview", ideas_payload["ideas"][0])
        self.assertNotIn("translated_framing", ideas_payload["ideas"][0])
        self.assertEqual(idea_payload["idea_id"], idea["idea_id"])
        self.assertEqual(proposals_payload["proposal_count"], 1)
        self.assertEqual(proposals_payload["proposals"][0]["proposal_id"], proposal["proposal_id"])
        self.assertEqual(proposals_payload["proposals"][0]["approval_status"], "proposed")
        self.assertIn("target_module_ids", proposals_payload["proposals"][0])
        self.assertNotIn("route_snapshot", proposals_payload["proposals"][0])
        self.assertEqual(proposal_payload["proposal_id"], proposal["proposal_id"])

    def test_route_development_idea_prefers_surface_recipe_for_lens_mix(self) -> None:
        idea = {
            "idea_id": "idea-test",
            "raw_idea": "Compose a new lens that mixes personal interface guidance with worldbuilding studio generation.",
            "desired_effect": "Create a reusable lens recipe without mutating the base surfaces.",
            "intent_kind": "lens_composition",
            "surface_hints": ["personal_interface", "worldbuilding"],
            "translated_framing": {
                "target_artifacts": ["components", "policies", "workflows"],
                "context_notes": ["lens composition"],
            },
            "development_signals": {
                "query_tokens": ["lens", "personal", "worldbuilding", "recipe"],
            },
        }

        route = route_development_idea(self.root, idea, limit=5)

        self.assertEqual(route["route_kind"], "update_recipe")
        self.assertEqual(route["target_surface_family"], "personal_interface_v1")
        self.assertTrue(route["candidate_targets"])
        self.assertIn("surface:personal_interface_v1", route["query"])

    def test_thought_factory_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(thought_factory_module.MODULE_ID, "kernel.surface.thought_factory")
        self.assertEqual(thought_factory_module.CONTRACT_VERSION, "1.0")
        for name in thought_factory_module.PUBLIC_API:
            self.assertIn(name, thought_factory_module.__all__)
            self.assertTrue(hasattr(thought_factory_module, name), name)

    def test_long_form_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(long_form_module.MODULE_ID, "kernel.surface.long_form")
        self.assertEqual(long_form_module.CONTRACT_VERSION, "1.0")
        for name in long_form_module.PUBLIC_API:
            self.assertIn(name, long_form_module.__all__)
            self.assertTrue(hasattr(long_form_module, name), name)

    def test_thread_context_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(thread_context_module.MODULE_ID, "kernel.surface.thread_context")
        self.assertEqual(thread_context_module.CONTRACT_VERSION, "1.0")
        for name in thread_context_module.PUBLIC_API:
            self.assertIn(name, thread_context_module.__all__)
            self.assertTrue(hasattr(thread_context_module, name), name)

    def test_product_inner_world_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(product_inner_world_module.MODULE_ID, "surface.inner_world.product_inner_world")
        self.assertEqual(product_inner_world_module.CONTRACT_VERSION, "1.0")
        for name in product_inner_world_module.PUBLIC_API:
            self.assertIn(name, product_inner_world_module.__all__)
            self.assertTrue(hasattr(product_inner_world_module, name), name)
        self.assertNotIn("_materialize_connections", product_inner_world_module.__all__)
        self.assertNotIn("get_runtime_pipeline", product_inner_world_module.__all__)
        self.assertNotIn("update_runtime_pipeline_component", product_inner_world_module.__all__)
        self.assertNotIn("seed_sources", product_inner_world_module.__all__)
        self.assertNotIn("scan_library", product_inner_world_module.__all__)
        self.assertNotIn("sync_library", product_inner_world_module.__all__)
        self.assertNotIn("get_library_status", product_inner_world_module.__all__)
        self.assertNotIn("filter_library_sources", product_inner_world_module.__all__)
        self.assertNotIn("search_library_dimensions", product_inner_world_module.__all__)
        self.assertNotIn("govern_library_source", product_inner_world_module.__all__)
        self.assertNotIn("govern_library_family", product_inner_world_module.__all__)
        self.assertNotIn("rederive_library", product_inner_world_module.__all__)
        self.assertNotIn("get_dimension_model_role_status", product_inner_world_module.__all__)
        self.assertNotIn("get_pond_router_status", product_inner_world_module.__all__)
        self.assertNotIn("get_chunk_pond_detail", product_inner_world_module.__all__)
        self.assertNotIn("update_pond_router_config", product_inner_world_module.__all__)
        self.assertNotIn("apply_pond_router_preset", product_inner_world_module.__all__)
        self.assertNotIn("update_chunk_pond_detail", product_inner_world_module.__all__)
        self.assertNotIn("update_dimension_model_role_binding", product_inner_world_module.__all__)
        self.assertNotIn("load_pond_routing_feedback", product_inner_world_module.__all__)
        self.assertNotIn("record_pond_routing_feedback", product_inner_world_module.__all__)
        self.assertNotIn("classify_assisted_dimension", product_inner_world_module.__all__)
        self.assertNotIn("classify_assisted_pond_route", product_inner_world_module.__all__)
        self.assertNotIn("get_cost_report", product_inner_world_module.__all__)
        self.assertNotIn("get_cost_events", product_inner_world_module.__all__)
        self.assertNotIn("derive_graph", product_inner_world_module.__all__)
        self.assertNotIn("get_runtime_status", product_inner_world_module.__all__)
        self.assertIn("ensure_surface_recipe", product_inner_world_module.__all__)
        self.assertIn("build_thought_feed", product_inner_world_module.__all__)

    def test_append_mobile_capture_appends_session_event_and_returns_ack(self) -> None:
        result = append_mobile_capture(self.root, content="Capture this before it disappears.")

        manifest = read_json(self.root / "memory" / "sessions" / result["session_id"] / "manifest.json", default={})
        events = read_jsonl(session_events_path(self.root, result["session_id"]))

        self.assertEqual(manifest["source_type"], "mobile_surface")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_id"], result["capture_id"])
        self.assertEqual(events[0]["actor"], "user")
        self.assertEqual(events[0]["kind"], "capture")
        self.assertEqual(events[0]["content"], "Capture this before it disappears.")
        self.assertEqual(result["created_at"], events[0]["timestamp"])
        self.assertTrue(result["continue_conversation_available"])

    def test_reply_in_mobile_session_appends_user_and_assistant_events(self) -> None:
        session = ensure_mobile_capture_session(self.root)

        with mock.patch(
            "conversation_os.product_inner_world._request_mobile_session_reply",
            return_value={"content": "Stay with the contradiction and name the pressure plainly.", "backend_id": "stub"},
        ):
            result = reply_in_mobile_session(
                self.root,
                session_id=session["session_id"],
                user_message="What does this capture suggest I should look at next?",
            )

        events = read_jsonl(session_events_path(self.root, session["session_id"]))

        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["actor"], "user")
        self.assertEqual(events[0]["kind"], "message")
        self.assertEqual(events[0]["content"], "What does this capture suggest I should look at next?")
        self.assertEqual(events[1]["actor"], "assistant")
        self.assertEqual(events[1]["kind"], "reply")
        self.assertEqual(events[1]["content"], "Stay with the contradiction and name the pressure plainly.")
        self.assertEqual(result["session_id"], session["session_id"])
        self.assertEqual(result["assistant_message"]["content"], events[1]["content"])

    def test_build_mobile_feed_adapts_existing_thought_feed(self) -> None:
        with mock.patch(
            "conversation_os.product_inner_world.build_thought_feed",
            return_value={
                "generated_at": "2026-05-24T20:00:00+00:00",
                "count": 1,
                "thoughts": [
                    {
                        "thought_id": "thought-1",
                        "insight_id": "insight-1",
                        "title": "Title",
                        "short_text": "Short summary",
                        "feedback_state": "pending",
                        "post_format": "signal",
                        "thread_count": 2,
                        "source_refs": ["source://one"],
                    }
                ],
            },
        ) as mocked:
            feed = build_mobile_feed(self.root, domain_overlays=["research"], limit=5)

        mocked.assert_called_once_with(self.root, limit=5, domain_overlays=["research"])
        self.assertEqual(feed["generated_at"], "2026-05-24T20:00:00+00:00")
        self.assertEqual(feed["count"], 1)
        self.assertEqual(
            feed["items"],
            [
                {
                    "thought_id": "thought-1",
                    "insight_id": "insight-1",
                    "title": "Title",
                    "summary": "Short summary",
                    "feedback_state": "pending",
                    "post_format": "signal",
                    "thread_count": 2,
                    "source_refs": ["source://one"],
                }
            ],
        )

    def test_build_mobile_library_groups_captures_saved_items_and_conversations(self) -> None:
        session = ensure_mobile_capture_session(self.root)
        append_mobile_capture(self.root, session_id=session["session_id"], content="Pocket note.")
        with mock.patch(
            "conversation_os.product_inner_world._request_mobile_session_reply",
            return_value={"content": "Follow the thread and keep it grounded.", "backend_id": "stub"},
        ):
            reply_in_mobile_session(
                self.root,
                session_id=session["session_id"],
                user_message="Help me continue this thought.",
            )

        write_json(
            self.root / "product" / "inner_world_v1" / "data" / "threads" / "thread-saved.json",
            {
                "thread_id": "thread-saved",
                "thought_id": "thought-2",
                "title": "Saved Thought Thread",
                "status": "saved",
                "updated_at": "2026-05-24T20:10:00+00:00",
                "messages": [
                    {"role": "user", "content": "Keep going."},
                    {"role": "assistant", "content": "Name the pressure directly."},
                ],
                "embedded_source_item_ids": ["source-item-1"],
            },
        )

        with mock.patch(
            "conversation_os.product_inner_world.build_thought_archive",
            return_value={
                "thoughts": [
                    {"insight_id": "insight-saved", "title": "Saved", "short_text": "Saved item", "feedback_state": "saved"},
                    {"insight_id": "insight-relevant", "title": "Relevant", "short_text": "Relevant item", "feedback_state": "relevant"},
                    {"insight_id": "insight-later", "title": "Later", "short_text": "Later item", "feedback_state": "revisit_later"},
                    {"insight_id": "insight-pending", "title": "Pending", "short_text": "Pending item", "feedback_state": "pending"},
                ]
            },
        ):
            library = build_mobile_library(self.root)

        self.assertEqual([item["content"] for item in library["captures"]], ["Pocket note."])
        self.assertEqual({item["conversation_type"] for item in library["conversations"]}, {"mobile_session", "saved_thread"})
        self.assertEqual({item["feedback_state"] for item in library["saved_items"]}, {"saved", "relevant", "revisit_later"})
        self.assertEqual(len(library["saved_items"]), 3)

    def test_policy_engine_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(policy_engine_module.MODULE_ID, "kernel.policy.policy_engine")
        self.assertEqual(policy_engine_module.CONTRACT_VERSION, "1.0")
        for name in policy_engine_module.PUBLIC_API:
            self.assertIn(name, policy_engine_module.__all__)
            self.assertTrue(hasattr(policy_engine_module, name), name)

    def test_plugins_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(plugins_module.MODULE_ID, "builder.plugins.plugins")
        self.assertEqual(plugins_module.CONTRACT_VERSION, "1.0")
        for name in plugins_module.PUBLIC_API:
            self.assertIn(name, plugins_module.__all__)
            self.assertTrue(hasattr(plugins_module, name), name)

    def test_review_queue_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(review_queue_module.MODULE_ID, "kernel.governance.review_queue")
        self.assertEqual(review_queue_module.CONTRACT_VERSION, "1.0")
        for name in review_queue_module.PUBLIC_API:
            self.assertIn(name, review_queue_module.__all__)
            self.assertTrue(hasattr(review_queue_module, name), name)

    def test_routing_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(routing_module.MODULE_ID, "kernel.routing.task_pack_routing")
        self.assertEqual(routing_module.CONTRACT_VERSION, "1.0")
        for name in routing_module.PUBLIC_API:
            self.assertIn(name, routing_module.__all__)
            self.assertTrue(hasattr(routing_module, name), name)

    def test_vault_ingest_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(vault_ingest_module.MODULE_ID, "kernel.ingest.vault_ingest")
        self.assertEqual(vault_ingest_module.CONTRACT_VERSION, "1.0")
        for name in vault_ingest_module.PUBLIC_API:
            self.assertIn(name, vault_ingest_module.__all__)
            self.assertTrue(hasattr(vault_ingest_module, name), name)

    def test_worldbuilding_studio_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(worldbuilding_studio_module.MODULE_ID, "surface.worldbuilding.worldbuilding_studio")
        self.assertEqual(worldbuilding_studio_module.CONTRACT_VERSION, "1.0")
        for name in worldbuilding_studio_module.PUBLIC_API:
            self.assertIn(name, worldbuilding_studio_module.__all__)
            self.assertTrue(hasattr(worldbuilding_studio_module, name), name)
        self.assertNotIn("worldbuilding_studio_dir", worldbuilding_studio_module.__all__)
        self.assertNotIn("HiggsfieldCliClient", worldbuilding_studio_module.__all__)
        self.assertIn("create_world", worldbuilding_studio_module.__all__)
        self.assertIn("compile_scene", worldbuilding_studio_module.__all__)

    def test_worldbuilding_studio_mcp_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(worldbuilding_studio_mcp_module.MODULE_ID, "surface.worldbuilding.worldbuilding_studio_mcp")
        self.assertEqual(worldbuilding_studio_mcp_module.CONTRACT_VERSION, "1.0")
        for name in worldbuilding_studio_mcp_module.PUBLIC_API:
            self.assertIn(name, worldbuilding_studio_mcp_module.__all__)
            self.assertTrue(hasattr(worldbuilding_studio_mcp_module, name), name)

    def test_runtime_pipeline_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(runtime_pipeline_module.MODULE_ID, "assembly.runtime.runtime_pipeline")
        self.assertEqual(runtime_pipeline_module.CONTRACT_VERSION, "1.0")
        for name in runtime_pipeline_module.PUBLIC_API:
            self.assertIn(name, runtime_pipeline_module.__all__)
            self.assertTrue(hasattr(runtime_pipeline_module, name), name)

    def test_pipelines_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(pipelines_module.MODULE_ID, "assembly.runtime.pipelines")
        self.assertEqual(pipelines_module.CONTRACT_VERSION, "1.0")
        for name in pipelines_module.PUBLIC_API:
            self.assertIn(name, pipelines_module.__all__)
            self.assertTrue(hasattr(pipelines_module, name), name)

    def test_pipeline_runner_module_exposes_stable_public_boundary(self) -> None:
        self.assertEqual(pipeline_runner_module.MODULE_ID, "assembly.runtime.pipeline_runner")
        self.assertEqual(pipeline_runner_module.CONTRACT_VERSION, "1.0")
        for name in pipeline_runner_module.PUBLIC_API:
            self.assertIn(name, pipeline_runner_module.__all__)
            self.assertTrue(hasattr(pipeline_runner_module, name), name)

    def test_inner_world_surface_recipe_materializes_expected_shape(self) -> None:
        recipe = load_surface_recipe(self.root)

        self.assertEqual(recipe["recipe_id"], "recipe.inner_world.v1")
        self.assertEqual(recipe["surface_id"], "surface.inner_world")
        self.assertEqual(recipe["status"], "transitional")
        self.assertTrue((self.root / "product" / "inner_world_v1" / "config" / "surface_recipe.v1.json").exists())
        self.assertGreaterEqual(len(recipe["module_refs"]), 4)
        self.assertGreaterEqual(len(recipe["adapter_refs"]), 2)
        self.assertIn("memory/events", recipe["state_dependencies"])

    def test_personal_interface_surface_recipe_materializes_expected_shape(self) -> None:
        recipe = load_personal_interface_surface_recipe(self.root)

        self.assertEqual(recipe["recipe_id"], "recipe.personal_interface.v1")
        self.assertEqual(recipe["surface_id"], "surface.personal_interface")
        self.assertEqual(recipe["status"], "transitional")
        self.assertTrue((self.root / "product" / "personal_interface_v1" / "config" / "surface_recipe.v1.json").exists())
        self.assertGreaterEqual(len(recipe["module_refs"]), 2)
        self.assertGreaterEqual(len(recipe["adapter_refs"]), 2)
        self.assertIn("product/personal_interface_v1/data", recipe["state_dependencies"])

    def test_session_lifecycle_materializes_artifacts(self) -> None:
        started = session_start(
            self.root,
            type("Args", (), {"session_id": "session-test", "title": "Build foundation", "participants": "user,agent", "source_type": "live_session", "domains": "research,art"})(),
        )
        self.assertEqual(started["session_id"], "session-test")
        session_append(
            self.root,
            type("Args", (), {"session_id": "session-test", "actor": "user", "kind": "request", "content": "Build the conversation OS foundation.", "attachments": "", "tags": "foundation", "source_ref": None})(),
        )
        session_append(
            self.root,
            type("Args", (), {"session_id": "session-test", "actor": "agent", "kind": "response", "content": "Implemented the initial control plane and plugin model.", "attachments": "", "tags": "implementation", "source_ref": None})(),
        )
        result = session_close(
            self.root,
            type("Args", (), {"session_id": "session-test", "task_id": "handoff-build-foundation", "request": "Continue building the foundation", "task_type": "implementation"})(),
        )
        self.assertIn("ordered_transcript", result["artifact_refs"])
        self.assertTrue((self.root / "memory" / "sessions" / "session-test" / "analysis" / "session_packet.json").exists())
        self.assertTrue((self.root / "memory" / "indexes" / "current_state.md").exists())
        self.assertTrue((task_packs_dir(self.root) / "handoff-build-foundation.json").exists())

    def test_import_parity_generates_same_shape(self) -> None:
        source = self.root / "tmp-import.md"
        source.write_text("User: explore product wedge\nAgent: choose a conservative morning batch.\n", encoding="utf-8")
        result = session_import(
            self.root,
            type("Args", (), {"source_path": str(source), "title": "Imported transcript", "session_id": "import-test", "participants": "importer", "source_type": "imported_transcript", "domains": "entrepreneurship", "tags": "import", "task_id": None, "request": None, "task_type": None})(),
        )
        manifest = read_json(self.root / "memory" / "sessions" / "import-test" / "manifest.json")
        events = read_jsonl(session_events_path(self.root, "import-test"))
        synthesis = read_json(self.root / "memory" / "sessions" / "import-test" / "analysis" / "session_synthesis.json")
        self.assertEqual(manifest["status"], "closed")
        self.assertTrue((self.root / "memory" / "sessions" / "import-test" / "ordered_transcript.md").exists())
        self.assertTrue((self.root / "memory" / "sessions" / "import-test" / "analysis" / "decision_attachments.json").exists())
        self.assertEqual(result["session_id"], "import-test")
        self.assertEqual([event["actor"] for event in events], ["user", "assistant"])
        self.assertEqual([event["kind"] for event in events], ["request", "response"])
        self.assertEqual(synthesis["top_requests"], ["explore product wedge"])

    def test_import_markdown_transcript_splits_turns_and_preserves_learning_signals(self) -> None:
        source = self.root / "tmp-chatgpt-import.md"
        source.write_text(
            "\n".join(
                [
                    "---",
                    'title: "Imported Chat"',
                    'source_url: "https://example.com/share/abc"',
                    "---",
                    "",
                    "## User",
                    "",
                    "How does this product concept become modules and interfaces?",
                    "",
                    "---",
                    "",
                    "## Assistant",
                    "",
                    "It likely becomes a workflow engine, a policy layer, and explicit state transitions.",
                    "",
                    "---",
                    "",
                    "## User",
                    "",
                    "Can you map the architecture into a concrete implementation path?",
                ]
            ),
            encoding="utf-8",
        )
        session_import(
            self.root,
            type("Args", (), {"source_path": str(source), "title": "Imported markdown transcript", "session_id": "markdown-import-test", "participants": "", "source_type": "imported_transcript", "domains": "research", "tags": "import", "task_id": None, "request": None, "task_type": None})(),
        )

        events = read_jsonl(session_events_path(self.root, "markdown-import-test"))
        packet = read_json(self.root / "memory" / "sessions" / "markdown-import-test" / "analysis" / "session_packet.json")
        synthesis = read_json(self.root / "memory" / "sessions" / "markdown-import-test" / "analysis" / "session_synthesis.json")

        self.assertEqual(events[0]["actor"], "importer")
        self.assertEqual(events[0]["kind"], "artifact")
        self.assertEqual(events[1]["actor"], "user")
        self.assertEqual(events[1]["kind"], "request")
        self.assertEqual(events[2]["actor"], "assistant")
        self.assertEqual(events[2]["kind"], "response")
        self.assertEqual(events[3]["actor"], "user")
        self.assertEqual(events[3]["kind"], "request")
        self.assertIn("implementation_mapping", packet["conversation_analysis"]["question_path_types"])
        self.assertEqual(packet["conversation_analysis"]["concept_translation_signal"], "high")
        self.assertEqual(
            synthesis["top_requests"],
            [
                "How does this product concept become modules and interfaces?",
                "Can you map the architecture into a concrete implementation path?",
            ],
        )

    def test_session_close_builds_concept_synthesis_and_task_pack_retrieval(self) -> None:
        session_start(
            self.root,
            type("Args", (), {"session_id": "concept-session", "title": "Relevance graph design", "participants": "user,agent", "source_type": "live_session", "domains": "research,architecture"})(),
        )
        session_append(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": "concept-session",
                    "actor": "user",
                    "kind": "request",
                    "content": "We should use a `relevance graph` to navigate the knowledge bank and support structural retrieval across concepts.",
                    "attachments": "",
                    "tags": "graph",
                    "source_ref": None,
                },
            )(),
        )
        session_append(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": "concept-session",
                    "actor": "assistant",
                    "kind": "response",
                    "content": "The `relevance graph` could support graph traversal, routing, and synthesis across distant ideas.",
                    "attachments": "",
                    "tags": "graph",
                    "source_ref": None,
                },
            )(),
        )
        session_close(
            self.root,
            type("Args", (), {"session_id": "concept-session", "task_id": None, "request": None, "task_type": None})(),
        )

        concept_nodes = load_concept_nodes(self.root)
        touch_rows = load_touch_operations(self.root)
        packet = read_json(self.root / "memory" / "sessions" / "concept-session" / "analysis" / "concept_synthesis.json")
        pack = build_task_pack(self.root, "task-graph", "How should agents route structural retrieval across concepts?", "implementation", ["research"], [])
        runtime = get_runtime_overview(self.root)
        exported = export_state(self.root)

        self.assertTrue(any(row["label"].lower() == "relevance graph" for row in concept_nodes))
        self.assertTrue(any(row["candidate_label"].lower() == "relevance graph" for row in touch_rows))
        self.assertIn("relevance graph", [value.lower() for value in packet["confirmed"] + packet["inferred"]])
        self.assertTrue(any(row["label"].lower() == "relevance graph" for row in pack["relevant_concepts"]))
        self.assertGreaterEqual(runtime["counts"]["concept_nodes"], 1)
        self.assertIn("concept_graph", exported)

    def test_repeated_conversation_reuses_existing_concept_node(self) -> None:
        for session_id, title, content in [
            (
                "concept-a",
                "Relevance graph design",
                "We should use a `relevance graph` to navigate the knowledge bank and support structural retrieval.",
            ),
            (
                "concept-b",
                "Relevance graph extension",
                "The `relevance graph` should also support multi-hop routing across older concepts and reviewable synthesis.",
            ),
        ]:
            session_start(
                self.root,
                type("Args", (), {"session_id": session_id, "title": title, "participants": "user,agent", "source_type": "live_session", "domains": "research"})(),
            )
            session_append(
                self.root,
                type("Args", (), {"session_id": session_id, "actor": "user", "kind": "request", "content": content, "attachments": "", "tags": "graph", "source_ref": None})(),
            )
            session_append(
                self.root,
                type("Args", (), {"session_id": session_id, "actor": "assistant", "kind": "response", "content": "The `relevance graph` creates reusable routing structure for concept retrieval.", "attachments": "", "tags": "graph", "source_ref": None})(),
            )
            session_close(
                self.root,
                type("Args", (), {"session_id": session_id, "task_id": None, "request": None, "task_type": None})(),
            )

        concept_nodes = [row for row in load_concept_nodes(self.root) if row["label"].lower() == "relevance graph"]
        touch_rows = [row for row in load_touch_operations(self.root) if row["candidate_label"].lower() == "relevance graph"]
        synthesis_packets = load_synthesis_packets(self.root)

        self.assertEqual(len(concept_nodes), 1)
        self.assertGreaterEqual(len(touch_rows), 2)
        self.assertEqual(len({row["concept_id"] for row in touch_rows}), 1)
        self.assertEqual(len(synthesis_packets), 2)

    def test_concept_merge_policy_can_force_review(self) -> None:
        write_json(
            self.root / "product" / "inner_world_v1" / "config" / "concept_merge_policy.json",
            {
                "version": 1,
                "auto_merge_threshold": 0.95,
                "review_threshold": 0.4,
                "minimum_threshold": 0.2,
                "max_concepts_per_session": 8,
                "neighbor_boost": 0.18,
                "always_review_touch_types": ["contradicts"],
                "prefer_review_touch_types": ["reframes", "changes_priority"],
                "status_weights": {"active": 1.0, "provisional": 0.82, "needs_review": 0.72, "archived": 0.48},
            },
        )
        session_start(
            self.root,
            type("Args", (), {"session_id": "concept-review", "title": "Relevance graph design", "participants": "user,agent", "source_type": "live_session", "domains": "research"})(),
        )
        session_append(
            self.root,
            type("Args", (), {"session_id": "concept-review", "actor": "user", "kind": "request", "content": "We should use a `relevance graph` to navigate the knowledge bank and support structural retrieval.", "attachments": "", "tags": "graph", "source_ref": None})(),
        )
        session_append(
            self.root,
            type("Args", (), {"session_id": "concept-review", "actor": "assistant", "kind": "response", "content": "The `relevance graph` supports routing and synthesis across concepts.", "attachments": "", "tags": "graph", "source_ref": None})(),
        )
        session_close(
            self.root,
            type("Args", (), {"session_id": "concept-review", "task_id": None, "request": None, "task_type": None})(),
        )

        review_rows = load_concept_review_queue(self.root)
        touch_rows = load_touch_operations(self.root)
        concept_nodes = load_concept_nodes(self.root)
        synthesis_packets = load_synthesis_packets(self.root)

        self.assertTrue(review_rows)
        self.assertTrue(any(row["status"] == "needs_review" for row in touch_rows))
        self.assertTrue(any(row["status"] == "provisional" for row in concept_nodes))
        self.assertEqual(len(synthesis_packets), 1)

    def test_alias_registry_collapses_equivalent_concepts_and_aligns_bubble_provenance(self) -> None:
        write_json(
            self.root / "product" / "inner_world_v1" / "config" / "concept_alias_registry.json",
            {
                "version": 1,
                "concepts": [
                    {
                        "canonical_label": "Relevance Graph",
                        "aliases": ["Knowledge Navigation Graph"],
                        "transfer_terms": ["graph", "retrieval", "routing"],
                    }
                ],
            },
        )

        for session_id, title, content in [
            ("alias-a", "Relevance graph design", "We should use a `relevance graph` to navigate the knowledge bank."),
            ("alias-b", "Knowledge navigation graph", "The `knowledge navigation graph` should route across older concepts."),
        ]:
            session_start(
                self.root,
                type("Args", (), {"session_id": session_id, "title": title, "participants": "user,agent", "source_type": "live_session", "domains": "research"})(),
            )
            session_append(
                self.root,
                type("Args", (), {"session_id": session_id, "actor": "user", "kind": "request", "content": content, "attachments": "", "tags": "graph", "source_ref": None})(),
            )
            session_append(
                self.root,
                type("Args", (), {"session_id": session_id, "actor": "assistant", "kind": "response", "content": "This graph supports retrieval and routing across concept space.", "attachments": "", "tags": "graph", "source_ref": None})(),
            )
            session_close(
                self.root,
                type("Args", (), {"session_id": session_id, "task_id": None, "request": None, "task_type": None})(),
            )

        concept_nodes = [row for row in load_concept_nodes(self.root) if row["label"] == "Relevance Graph"]
        self.assertEqual(len(concept_nodes), 1)
        concept_id = concept_nodes[0]["concept_id"]

        source = self.root / "bubble-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "The knowledge navigation graph should help route across past research and connect related ideas.",
                    "",
                    "# Assistant",
                    "",
                    "Yes, the knowledge navigation graph can structure retrieval and routing.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        derive_graph(self.root, ["research"])

        bubbles = load_context_bubbles(self.root)
        matched = [row for row in bubbles if concept_id in row.get("concept_ids", [])]
        self.assertTrue(matched)

        detail = get_bubble_detail(self.root, matched[0]["bubble_id"], ["research"])
        self.assertGreaterEqual(detail["provenance"]["source_count"], 1)
        self.assertGreaterEqual(detail["provenance"]["chunk_count"], 1)
        self.assertTrue(detail["provenance"]["source_packets"][0]["chunk_excerpts"])
        self.assertEqual(detail["bubble"]["primary_concept_id"], concept_id)

        filtered = filter_knowledge_components(
            self.root,
            query="relevance graph routing",
            component_types=["concept", "bubble"],
            source_ref=str(source.resolve()),
            limit=10,
            domain_overlays=["research"],
        )
        component_types = {row["component_type"] for row in filtered["results"]}
        self.assertIn("bubble", component_types)

    def test_task_pack_is_deterministic(self) -> None:
        session_start(
            self.root,
            type("Args", (), {"session_id": "session-route", "title": "Research planning", "participants": "user,agent", "source_type": "live_session", "domains": "research"})(),
        )
        session_append(
            self.root,
            type("Args", (), {"session_id": "session-route", "actor": "user", "kind": "request", "content": "Need evidence-backed research insight routing.", "attachments": "", "tags": "research", "source_ref": None})(),
        )
        session_close(
            self.root,
            type("Args", (), {"session_id": "session-route", "task_id": None, "request": None, "task_type": None})(),
        )
        pack_a = build_task_pack(self.root, "task-1", "Need research insight routing", "implementation", ["research"], [])
        pack_b = build_task_pack(self.root, "task-1", "Need research insight routing", "implementation", ["research"], [])
        self.assertEqual(pack_a, pack_b)
        self.assertEqual(len(pack_a["tenets"]), 10)
        self.assertTrue(pack_a["relevant_sessions"])
        self.assertIn("product_thesis", pack_a["reference_docs"])
        self.assertIn("handoff_validation", pack_a)
        self.assertTrue(pack_a["handoff_validation"]["fresh"])

    def test_task_pack_build_is_blocked_when_codebase_index_is_not_ready(self) -> None:
        with mock.patch(
            "conversation_os.routing.validate_codebase_index",
            return_value={
                "generated_at": "2026-05-22T00:00:00+00:00",
                "module_manifest_count": 57,
                "error_count": 0,
                "warning_count": 1,
                "missing_manifest_count": 0,
                "fresh": False,
                "stale_reasons": ["Generated codebase artifacts are older than the newest tracked source or manifest."],
                "missing_artifacts": [],
                "newest_source_path": "src/conversation_os/cli.py",
                "newest_generated_path": "context/substrate/AGENT_OPERATING_BRIEF.md",
                "errors": [],
                "warnings": ["1 tracked python modules do not yet have manifests"],
                "missing_paths": [],
            },
        ):
            with self.assertRaises(routing_module.TaskPackRoutingError) as exc:
                build_task_pack(self.root, "task-blocked", "Need research insight routing", "implementation", ["research"], [])

        self.assertEqual(exc.exception.code, "task_pack_index_not_ready")
        self.assertIn("codebase atlas is stale or invalid", exc.exception.message)

    def test_inner_world_batch_contract_and_feedback(self) -> None:
        source = self.root / "seed.txt"
        source.write_text(
            "\n".join(
                [
                    "Research note about evidence thresholds in product design.",
                    "Creative note about rhythm and composition in interfaces.",
                    "Founder note about user friction and onboarding delays.",
                    "Research note comparing mechanism design and user trust.",
                    "Art note about mood, texture, and contrast.",
                    "Entrepreneurship note on wedge strategy and retention.",
                    "Research note on uncertainty, evidence, and mechanism.",
                    "Art note on composition rhythm and gesture.",
                    "Founder note on moat, distribution, and channel.",
                    "Research note on model comparison and evidence quality.",
                    "Creative note connecting texture and workflow rhythm.",
                    "Strategy note on user pain and adoption barrier.",
                    "Research note on theory synthesis and causal models.",
                    "Art note on color contrast and emotional tone.",
                    "Founder note on workflow friction and pricing signal.",
                    "Research note on study findings and synthesis.",
                    "Creative note on form analogy across media.",
                    "Entrepreneurship note on retention and demand signals.",
                    "Research note on assumption gaps and risk.",
                    "Art note on material symbolism and gesture."
                ]
            ),
            encoding="utf-8",
        )
        seed_result = seed_sources(self.root, source)
        self.assertEqual(seed_result["seeded_count"], 20)
        self.assertEqual(seed_result["total_count"], 20)
        derive_result = derive_graph(self.root, ["research", "art", "entrepreneurship"])
        self.assertGreaterEqual(derive_result["connection_count"], 1)
        batch = generate_daily_batch(self.root, limit=5, domain_overlays=["research", "art", "entrepreneurship"])
        self.assertGreaterEqual(batch["count"], 1)
        for insight in batch["insights"]:
            self.assertTrue(insight["source_refs"])
            self.assertIn("confidence_score", insight)
            self.assertIn("reasoning_primitive", insight)
            self.assertIn(insight["evidence_status"], {"grounded", "speculative"})
            self.assertIn("what_changed", insight)
            self.assertIn("why_it_matters_now", insight)
            self.assertIn("feedback_controls", insight)
        source_before = (self.root / "product" / "inner_world_v1" / "data" / "source_items.jsonl").read_text(encoding="utf-8")
        target_id = batch["insights"][-1]["insight_id"]
        previous_index = next(idx for idx, item in enumerate(batch["insights"]) if item["insight_id"] == target_id)
        record_feedback(self.root, target_id, "relevant")
        source_after = (self.root / "product" / "inner_world_v1" / "data" / "source_items.jsonl").read_text(encoding="utf-8")
        self.assertEqual(source_before, source_after)
        batch_after_feedback = generate_daily_batch(self.root, limit=5, domain_overlays=["research", "art", "entrepreneurship"])
        updated_index = next(idx for idx, item in enumerate(batch_after_feedback["insights"]) if item["insight_id"] == target_id)
        self.assertLess(updated_index, previous_index)
        self.assertEqual(
            next(item for item in batch_after_feedback["insights"] if item["insight_id"] == target_id)["feedback_state"],
            "relevant",
        )
        export_payload = export_state(self.root)
        self.assertIn("analysis_units", export_payload)
        self.assertIn("insight_candidates", export_payload)
        self.assertIn("surfaced_insights", export_payload)
        self.assertIn("thought_feed", export_payload)
        runtime = get_runtime_overview(self.root)
        self.assertIn("counts", runtime)
        self.assertEqual(runtime["counts"]["sources"], 1)
        self.assertTrue(runtime["source_families"])

    def test_markdown_seed_uses_semantic_chunks_and_replaces_same_source(self) -> None:
        source = self.root / "seed.md"
        source.write_text(
            "\n".join(
                [
                    "# Product Thesis",
                    "",
                    "Inner World should feel like private social media for one person.",
                    "",
                    "## Surfaces",
                    "",
                    "- Morning Batch is the default surface.",
                    "- Archive is the secondary surface.",
                    "",
                    "## Trust",
                    "",
                    "Every thought should stay grounded in evidence.",
                ]
            ),
            encoding="utf-8",
        )
        first = seed_sources(self.root, source)
        rows = [row for row in read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "source_items.jsonl") if row["source_ref"] == str(source.resolve())]
        self.assertLess(len(rows), 7)
        self.assertTrue(all(row.get("content_kind") for row in rows))
        self.assertTrue(any(row.get("section_path") for row in rows))

        second = seed_sources(self.root, source)
        rows_after = [row for row in read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "source_items.jsonl") if row["source_ref"] == str(source.resolve())]
        self.assertEqual(first["seeded_count"], second["seeded_count"])
        self.assertEqual(len(rows), len(rows_after))

    def test_chat_markdown_inferrs_user_and_assistant_roles(self) -> None:
        source = self.root / "chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "I want the system to preserve ambiguity before forcing structure.",
                    "",
                    "# Assistant",
                    "",
                    "The system should summarize early and simplify the field.",
                    "",
                    "# User",
                    "",
                    "No, the ambiguity has to survive longer before structure arrives.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        chunks = [row for row in read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "chunk_index.jsonl") if row["source_ref"] == str(source.resolve())]
        roles = [row.get("metadata", {}).get("speaker_role") for row in chunks]
        self.assertIn("user", roles)
        self.assertIn("assistant", roles)

        units_summary = build_analysis_units(self.root)
        self.assertGreaterEqual(units_summary["analysis_unit_count"], 2)
        units = [row for row in load_analysis_units(self.root) if row["source_ref"] == str(source.resolve())]
        self.assertIn("user", [row.get("speaker_role") for row in units])
        self.assertIn("assistant", [row.get("speaker_role") for row in units])

    def test_repeated_user_turn_builds_delta_and_expectation_records(self) -> None:
        source = self.root / "delta-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Build a private cognitive layer that preserves ambiguity before structure.",
                    "",
                    "# Assistant",
                    "",
                    "The product should just summarize everything into clear categories immediately.",
                    "",
                    "# User",
                    "",
                    "No, preserve ambiguity first. I do not want premature summary collapse.",
                    "",
                    "# Assistant",
                    "",
                    "Understood. The system should let ambiguity survive, then crystallize structure later.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        result = build_conversation_deltas(self.root)
        self.assertGreaterEqual(result["delta_count"], 1)
        deltas = load_conversation_deltas(self.root)
        expectations = load_user_expectations(self.root)
        self.assertEqual(len(deltas), 1)
        self.assertEqual(deltas[0]["status"], "resolved")
        self.assertTrue(deltas[0]["unsatisfying_assistant_chunk_ids"])
        self.assertTrue(deltas[0]["resolved_assistant_chunk_id"])
        self.assertGreaterEqual(len(expectations), 1)
        self.assertIn("ambiguity", expectations[0]["user_priority_tokens"])

    def test_runtime_pipeline_can_disable_components_and_skip_dependents(self) -> None:
        source = self.root / "runtime-pipeline-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Build a private cognitive layer that preserves ambiguity before structure.",
                    "",
                    "# Assistant",
                    "",
                    "The product should flatten the ambiguity immediately.",
                    "",
                    "# User",
                    "",
                    "No, preserve ambiguity first and only structure later.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        update_runtime_pipeline_component(self.root, "conversation_deltas", enabled=False)

        summary = derive_graph(self.root, ["research"])
        pipeline = get_runtime_pipeline(self.root)
        status_by_id = {row["component_id"]: row for row in pipeline["last_run"]["components"]}

        self.assertEqual(status_by_id["conversation_deltas"]["status"], "disabled")
        self.assertEqual(status_by_id["conversation_threads"]["status"], "skipped_missing_dependencies")
        self.assertEqual(status_by_id["meta_layer"]["status"], "skipped_missing_dependencies")
        self.assertEqual(status_by_id["knowledge_layer"]["status"], "skipped_missing_dependencies")
        self.assertEqual(summary["thread_count"], 0)
        self.assertEqual(summary["concept_node_count"], 0)
        self.assertEqual(summary["connection_count"], 0)

    def test_runtime_pipeline_materializes_shape_signature_and_shape_graph_components(self) -> None:
        source = self.root / "runtime-shape-pipeline-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Our product has many features but users do not understand what it is.",
                    "",
                    "# Assistant",
                    "",
                    "Then the surface should restore hierarchy instead of adding more explanation layers.",
                    "",
                    "# User",
                    "",
                    "Yes, because more explanation is making the product feel even more complex.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")

        derive_graph(self.root, ["research"])
        pipeline = get_runtime_pipeline(self.root)
        status_by_id = {row["component_id"]: row for row in pipeline["last_run"]["components"]}
        shape_signatures = meta_layer_module.load_shape_signatures(self.root)
        shape_nodes = meta_layer_module.load_shape_graph_nodes(self.root)
        shape_edges = meta_layer_module.load_shape_graph_edges(self.root)

        self.assertEqual(status_by_id["shape_signatures"]["status"], "completed")
        self.assertEqual(status_by_id["shape_graph"]["status"], "completed")
        self.assertTrue(
            (self.root / "product" / "inner_world_v1" / "data" / "shape_signatures.jsonl").exists()
        )
        self.assertTrue(
            (self.root / "product" / "inner_world_v1" / "data" / "shape_graph_nodes.jsonl").exists()
        )
        self.assertTrue(
            (self.root / "product" / "inner_world_v1" / "data" / "shape_graph_edges.jsonl").exists()
        )
        self.assertGreaterEqual(len(shape_signatures), 1)
        self.assertGreaterEqual(len(shape_nodes), 1)
        self.assertGreaterEqual(len(shape_edges), 1)

    def test_library_status_and_runtime_overview_expose_shape_artifact_counts(self) -> None:
        source = self.root / "runtime-shape-status-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Our product has many features but users do not understand what it is.",
                    "",
                    "# Assistant",
                    "",
                    "Then the system should restore hierarchy instead of stacking more explanation.",
                    "",
                    "# User",
                    "",
                    "Yes, more explanation is making it feel even more complex.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")

        derive_graph(self.root, ["research"])
        library_status = get_library_status(self.root)
        runtime_overview = get_runtime_overview(self.root)

        self.assertIn("shape_artifacts", library_status)
        self.assertGreaterEqual(library_status["shape_artifacts"]["signature_count"], 1)
        self.assertGreaterEqual(library_status["shape_artifacts"]["graph_node_count"], 1)
        self.assertGreaterEqual(library_status["shape_artifacts"]["graph_edge_count"], 1)
        self.assertEqual(
            runtime_overview["library_tracker"]["shape_artifacts"]["signature_count"],
            library_status["shape_artifacts"]["signature_count"],
        )

    def test_materialize_connections_writes_bounded_summary_payload(self) -> None:
        data_dir = self.root / "product" / "inner_world_v1" / "data"
        edges = []
        for index in range(5105):
            edges.append(
                {
                    "edge_id": f"edge-{index:05d}",
                    "from_id": f"left-{index:05d}",
                    "to_id": f"right-{index:05d}",
                    "kind": "relates_to",
                    "confidence": round(1.0 - (index / 10000.0), 6),
                    "attributes": {
                        "shared_tokens": [f"token-{index % 7}", f"concept-{index % 5}"],
                    },
                }
            )
        write_jsonl(data_dir / "knowledge_edges.jsonl", edges)

        summary = _materialize_connections(self.root)
        payload = read_json(data_dir / "connections.json", default={})

        self.assertEqual(summary["connection_count"], 5105)
        self.assertEqual(summary["included_connection_count"], 5000)
        self.assertTrue(summary["truncated"])
        self.assertEqual(payload["total_connection_count"], 5105)
        self.assertEqual(payload["included_connection_count"], 5000)
        self.assertTrue(payload["truncated"])
        self.assertEqual(len(payload["connections"]), 5000)
        self.assertEqual(payload["connections"][0]["connection_id"], "edge-00000")
        self.assertEqual(payload["connections"][-1]["connection_id"], "edge-04999")

    def test_runtime_overview_exposes_connection_summary_and_top_connections(self) -> None:
        data_dir = self.root / "product" / "inner_world_v1" / "data"
        write_json(
            data_dir / "connections.json",
            {
                "generated_at": "2026-04-22T19:24:40+00:00",
                "total_connection_count": 25,
                "included_connection_count": 6,
                "max_connections": 5000,
                "truncated": True,
                "connections": [
                    {
                        "connection_id": "edge-1",
                        "left_source_ref": "meta-node-a",
                        "right_source_ref": "meta-node-b",
                        "kind": "relates_to",
                        "shared_concepts": ["routing", "graph"],
                        "salient_concepts": ["routing", "graph"],
                        "strength": 0.91,
                    }
                ],
            },
        )

        runtime = get_runtime_overview(self.root)

        self.assertEqual(runtime["counts"]["connections"], 25)
        self.assertEqual(runtime["counts"]["connection_surface"], 6)
        self.assertEqual(runtime["connection_summary"]["total_connection_count"], 25)
        self.assertTrue(runtime["connection_summary"]["truncated"])
        self.assertEqual(runtime["top_connections"][0]["connection_id"], "edge-1")
        self.assertEqual(runtime["top_connections"][0]["shared_concepts"], ["routing", "graph"])

    def test_runtime_overview_and_linking_overview_expose_linking_spine(self) -> None:
        source = self.root / "linking-overview-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Build a semantic capsule layer that can route across ambiguity and structure.",
                    "",
                    "# Assistant",
                    "",
                    "The capsule layer should sit above the corpus and assemble bounded retrieval bundles.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        derive_graph(self.root, ["research"])

        runtime = get_runtime_overview(self.root)
        self.assertGreaterEqual(runtime["counts"]["context_links"], 1)
        self.assertGreaterEqual(runtime["counts"]["semantic_capsules"], 1)
        self.assertTrue(runtime["top_context_links"])
        self.assertTrue(runtime["top_semantic_capsules"])

        linking = get_linking_overview(self.root, query="semantic capsule routing", limit=8, domain_overlays=["research"])
        self.assertGreaterEqual(linking["counts"]["context_links"], 1)
        self.assertGreaterEqual(linking["counts"]["semantic_capsules"], 1)
        self.assertGreaterEqual(linking["retrieval_bundle"]["count"], 1)
        self.assertTrue(linking["top_context_links"])
        self.assertTrue(linking["top_semantic_capsules"])
        self.assertIn("ocean_map", linking)
        self.assertGreaterEqual(linking["ocean_map"]["node_count"], 1)
        self.assertIn("nodes", linking["ocean_map"])

    def test_runtime_pipeline_uses_weighted_order_for_ready_components(self) -> None:
        source = self.root / "runtime-weighted-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Map the product architecture into modules and interfaces.",
                    "",
                    "# Assistant",
                    "",
                    "It should become an interface layer, policies, and state transitions.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        update_runtime_pipeline_component(self.root, "analysis_units", order=20, weight=0.4)
        update_runtime_pipeline_component(self.root, "conversation_deltas", order=20, weight=2.0)

        derive_graph(self.root, ["research"])
        pipeline = get_runtime_pipeline(self.root)
        execution_order = pipeline["last_run"]["execution_order"]

        self.assertLess(
            execution_order.index("conversation_deltas"),
            execution_order.index("analysis_units"),
        )

    def test_runtime_pipeline_can_resume_completed_stage_when_artifact_exists(self) -> None:
        source = self.root / "runtime-resume-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Preserve ambiguity before structure.",
                    "",
                    "# Assistant",
                    "",
                    "Structure should come first.",
                    "",
                    "# User",
                    "",
                    "No, ambiguity first.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")

        derive_graph(self.root, ["research"], only_stage="analysis_units")
        resumed = derive_graph(self.root, ["research"], only_stage="analysis_units", resume=True)
        pipeline = get_runtime_pipeline(self.root)
        status_by_id = {row["component_id"]: row for row in pipeline["last_run"]["components"]}

        self.assertEqual(status_by_id["analysis_units"]["status"], "skipped_completed")
        self.assertEqual(status_by_id["bootstrap_legacy_sources"]["status"], "skipped_completed")
        self.assertEqual(resumed["source_item_count"], get_runtime_overview(self.root)["counts"]["chunks"])

    def test_runtime_pipeline_resume_reruns_stage_when_artifact_missing(self) -> None:
        source = self.root / "runtime-rerun-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Map the product to stable modules.",
                    "",
                    "# Assistant",
                    "",
                    "Use modules, policies, and interfaces.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")

        derive_graph(self.root, ["research"], only_stage="analysis_units")
        (self.root / "product" / "inner_world_v1" / "data" / "analysis_units.jsonl").unlink()

        derive_graph(self.root, ["research"], only_stage="analysis_units", resume=True)
        pipeline = get_runtime_pipeline(self.root)
        status_by_id = {row["component_id"]: row for row in pipeline["last_run"]["components"]}

        self.assertEqual(status_by_id["analysis_units"]["status"], "completed")
        self.assertTrue((self.root / "product" / "inner_world_v1" / "data" / "analysis_units.jsonl").exists())

    def test_runtime_pipeline_force_reruns_completed_stage(self) -> None:
        source = self.root / "runtime-force-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Keep the system inspectable.",
                    "",
                    "# Assistant",
                    "",
                    "Traceability and provenance should stay visible.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")

        derive_graph(self.root, ["research"], only_stage="analysis_units")
        derive_graph(self.root, ["research"], only_stage="analysis_units", resume=True, force=True)
        pipeline = get_runtime_pipeline(self.root)
        status_by_id = {row["component_id"]: row for row in pipeline["last_run"]["components"]}

        self.assertEqual(status_by_id["analysis_units"]["status"], "completed")
        self.assertFalse(status_by_id["analysis_units"].get("resumed_from_last_run", False))

    def test_runtime_pipeline_lock_contention_returns_existing_status(self) -> None:
        source = self.root / "runtime-lock-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Keep the runtime inspectable.",
                    "",
                    "# Assistant",
                    "",
                    "The pipeline should expose clear stage boundaries.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        derive_graph(self.root, ["research"], only_stage="analysis_units")

        with _try_runtime_pipeline_lock(self.root) as handle:
            self.assertIsNotNone(handle)
            result = execute_runtime_pipeline(
                self.root,
                {
                    "analysis_units": {
                        "label": "Build Analysis Units",
                        "requires": [],
                        "run": lambda: {"count": 0},
                        "artifacts": lambda: [self.root / "product" / "inner_world_v1" / "data" / "analysis_units.jsonl"],
                    }
                },
                only_stage="analysis_units",
            )

        self.assertTrue(result["lock_contended"])
        self.assertEqual(result["last_run"]["run_status"], "completed")

    def test_runtime_status_reports_last_completed_stage_and_counts(self) -> None:
        source = self.root / "runtime-status-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Explain the architecture.",
                    "",
                    "# Assistant",
                    "",
                    "It should become inspectable stages.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")

        derive_graph(self.root, ["research"], only_stage="analysis_units")
        status = get_runtime_status(self.root)

        self.assertEqual(status["pipeline_summary"]["run_status"], "completed")
        self.assertEqual(status["pipeline_summary"]["last_completed_stage"], "analysis_units")
        self.assertGreaterEqual(status["counts"]["analysis_units"], 1)

    def test_runtime_status_marks_stale_running_state_as_interrupted(self) -> None:
        write_json(
            self.root / "product" / "inner_world_v1" / "data" / "runtime_pipeline_last_run.json",
            {
                "generated_at": "2026-04-21T21:44:30+00:00",
                "run_started_at": "2026-04-21T21:44:29+00:00",
                "run_finished_at": None,
                "run_status": "running",
                "active_component_id": "context_bubbles",
                "selection_mode": "dependency_weighted",
                "options": {"resume": True, "from_stage": "context_bubbles", "only_stage": None, "force": False},
                "execution_order": ["ensure_pipeline_specs"],
                "components": [
                    {"component_id": "ensure_pipeline_specs", "status": "completed"},
                    {"component_id": "context_bubbles", "status": "running"},
                ],
            },
        )

        status = get_runtime_status(self.root)

        self.assertEqual(status["pipeline_summary"]["run_status"], "interrupted")
        self.assertIsNone(status["pipeline_summary"]["active_stage"])
        self.assertEqual(status["last_run"]["components"][1]["status"], "interrupted")
        self.assertTrue(status["last_run"]["stale_running_state"])

    def test_feed_returns_rebuilding_payload_without_triggering_batch_when_runtime_running(self) -> None:
        write_json(
            self.root / "product" / "inner_world_v1" / "data" / "runtime_pipeline_last_run.json",
            {
                "generated_at": "2026-04-21T20:44:26+00:00",
                "run_started_at": "2026-04-21T20:40:00+00:00",
                "run_finished_at": None,
                "run_status": "running",
                "active_component_id": "context_bubbles",
                "selection_mode": "dependency_weighted",
                "options": {},
                "execution_order": ["analysis_units", "conversation_deltas"],
                "components": [
                    {"component_id": "analysis_units", "status": "completed"},
                    {"component_id": "conversation_deltas", "status": "completed"},
                    {"component_id": "context_bubbles", "status": "running"},
                ],
            },
        )
        write_json(
            self.root / "product" / "inner_world_v1" / "data" / "context_bubbles_progress.json",
            {
                "status": "running",
                "phase": "related_attachment",
                "processed_count": 4000,
                "total_count": 12000,
            },
        )

        with _try_runtime_pipeline_lock(self.root) as handle:
            self.assertIsNotNone(handle)
            with mock.patch("conversation_os.product_inner_world.generate_daily_batch") as generate_batch:
                feed = build_thought_feed(self.root, limit=4, domain_overlays=["research"])

        generate_batch.assert_not_called()
        self.assertEqual(feed["status"], "rebuilding")
        self.assertEqual(feed["pipeline_summary"]["active_stage"], "context_bubbles")
        self.assertEqual(feed["context_bubbles_progress"]["phase"], "related_attachment")
        self.assertEqual(feed["count"], 0)

    def test_single_conversation_end_to_end_import_seed_and_derive(self) -> None:
        transcript = self.root / "single-conversation-e2e.md"
        transcript.write_text(
            "\n".join(
                [
                    "---",
                    "title: Single Conversation E2E",
                    "---",
                    "",
                    "# User",
                    "",
                    "We should use a relevance graph to navigate the knowledge bank, but it must stay tied to raw transcript evidence.",
                    "",
                    "# Assistant",
                    "",
                    "Then the runtime should preserve provenance and route through concept-backed context bubbles instead of loose keyword retrieval.",
                    "",
                    "# User",
                    "",
                    "Also treat cybernetics as an operational control model: state, feedback, routing, and governed updates.",
                    "",
                    "# Assistant",
                    "",
                    "That implies explicit merge policies, confidence thresholds, and review gates when new conversations touch older knowledge.",
                    "",
                    "# User",
                    "",
                    "Imported conversations should become part of the knowledge world, not a side transcript. Keep concept identity canonical so similar ideas do not fragment.",
                    "",
                    "# Assistant",
                    "",
                    "So the clean end state is: import the conversation, extract concepts, build bubbles and knowledge edges, and keep every surfaced idea linked back to source chunks.",
                ]
            ),
            encoding="utf-8",
        )

        import_result = session_import(
            self.root,
            type(
                "Args",
                (),
                {
                    "source_path": str(transcript),
                    "title": "Single Conversation E2E",
                    "participants": None,
                    "session_id": None,
                    "source_type": "chat_converter_conversation",
                    "domains": "research,product_design",
                    "tags": "e2e",
                    "task_id": None,
                    "request": None,
                    "task_type": None,
                },
            )(),
        )
        seed_result = seed_sources(self.root, transcript, "conversation_library")
        derive_result = derive_graph(self.root, ["research", "product_design"])
        status = get_runtime_status(self.root)
        manifest = read_json(self.root / "memory" / "sessions" / import_result["session_id"] / "manifest.json", default={})
        thought_batch = generate_daily_batch(self.root, limit=3, domain_overlays=["research", "product_design"])

        self.assertGreaterEqual(import_result["materialized_cards"], 1)
        self.assertIn("concept_synthesis", manifest.get("artifact_refs", {}))
        self.assertGreaterEqual(seed_result["seeded_count"], 1)
        self.assertGreaterEqual(derive_result["source_item_count"], 1)
        self.assertGreaterEqual(derive_result["thread_count"], 1)
        self.assertGreaterEqual(derive_result["bubble_count"], 1)
        self.assertGreaterEqual(derive_result["connection_count"], 1)
        self.assertEqual(status["pipeline_summary"]["run_status"], "completed")
        self.assertGreaterEqual(status["counts"]["context_bubbles"], 1)
        self.assertGreaterEqual(status["counts"]["knowledge_edges"], 1)
        self.assertTrue((self.root / "product" / "inner_world_v1" / "data" / "context_bubbles.jsonl").exists())
        self.assertTrue((self.root / "product" / "inner_world_v1" / "data" / "knowledge_edges.jsonl").exists())
        self.assertIn(thought_batch["status"] if "status" in thought_batch else "completed", {"completed", "completed_with_warnings", "interrupted", "rebuilding", "runtime_not_ready"})
        self.assertGreaterEqual(len(load_concept_nodes(self.root)), 1)

    def test_staged_derive_can_resume_from_downstream_stage_after_library_sync(self) -> None:
        corpus_dir = self.root / "derive-library"
        corpus_dir.mkdir(parents=True, exist_ok=True)
        (corpus_dir / "conversation-a.md").write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Preserve ambiguity before compression.",
                    "",
                    "# Assistant",
                    "",
                    "The system should flatten everything immediately.",
                    "",
                    "# User",
                    "",
                    "No, keep ambiguity visible before structure.",
                ]
            ),
            encoding="utf-8",
        )
        (corpus_dir / "conversation-b.md").write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Connect related pressures into context bubbles.",
                    "",
                    "# Assistant",
                    "",
                    "The system should trace connections between pressures and tensions.",
                ]
            ),
            encoding="utf-8",
        )
        self._write_library_config(
            {
                "sources": [
                    {
                        "source_id": "derive-files",
                        "kind": "filesystem",
                        "enabled": True,
                        "source_type": "chat_converter_conversation",
                        "source_family": "chat_converter",
                        "roots": [str(corpus_dir)],
                        "include_globs": ["*.md"],
                    }
                ]
            }
        )

        sync_result = sync_library_sources(self.root)
        self.assertEqual(sync_result["ingested_item_count"], 2)

        derive_graph(self.root, ["research"], only_stage="analysis_units")
        final_result = derive_graph(self.root, ["research"], resume=True, from_stage="conversation_deltas")
        pipeline = get_runtime_pipeline(self.root)
        status_by_id = {row["component_id"]: row for row in pipeline["last_run"]["components"]}

        self.assertEqual(status_by_id["analysis_units"]["status"], "skipped_completed")
        self.assertGreaterEqual(final_result["thread_count"], 1)
        self.assertGreaterEqual(get_runtime_overview(self.root)["counts"]["context_bubbles"], 1)

    def test_abstraction_and_bubble_summaries_include_profiling_shape(self) -> None:
        for idx in range(8):
            source = self.root / f"profile-{idx}.md"
            source.write_text(
                "\n".join(
                    [
                        "# User",
                        "",
                        f"Preserve ambiguity before flattening in context {idx}.",
                        "",
                        "# Assistant",
                        "",
                        "The system should become more inspectable and preserve signal texture.",
                        "",
                        "# User",
                        "",
                        "Also connect related pressures into shared bubbles.",
                    ]
                ),
                encoding="utf-8",
            )
            seed_sources(self.root, source, "conversation_library")

        abstraction_summary = build_thread_abstractions(self.root, ["research"], profile=True)
        bubble_summary = build_context_bubbles(self.root, ["research"], profile=True)

        self.assertIn("profiling", abstraction_summary)
        self.assertEqual(abstraction_summary["descriptor_count"], abstraction_summary["raw_thread_count"])
        self.assertGreaterEqual(abstraction_summary["profiling"]["merge_candidate_groups"], 0)
        self.assertIn("profiling", bubble_summary)
        self.assertGreaterEqual(bubble_summary["profiling"]["states_before_merge"], bubble_summary["profiling"]["states_after_merge"])
        self.assertGreaterEqual(bubble_summary["profiling"]["states_before_prune"], bubble_summary["profiling"]["states_after_prune"])
        self.assertGreaterEqual(bubble_summary["profiling"]["edge_pair_checks"], 0)
        progress = read_json(self.root / "product" / "inner_world_v1" / "data" / "context_bubbles_progress.json", default={})
        self.assertEqual(progress.get("status"), "completed")
        self.assertEqual(progress.get("phase"), "completed")
        self.assertGreaterEqual(progress.get("processed_count", 0), progress.get("seed_count", 0))

    def test_follow_up_dynamics_classify_relevance_from_next_user_move(self) -> None:
        source = self.root / "follow-up-dynamics.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "What are external thoughts?",
                    "",
                    "# Assistant",
                    "",
                    "They are aesthetic maps and mood clouds.",
                    "",
                    "# User",
                    "",
                    "No. More literal. Define external thoughts directly.",
                    "",
                    "# Assistant",
                    "",
                    "External thoughts are thoughts made perceivable outside the mind.",
                    "",
                    "# User",
                    "",
                    "Good. How do they help connect notes in practice?",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        build_conversation_deltas(self.root)
        delta = load_conversation_deltas(self.root)[0]
        expectation = load_user_expectations(self.root)[0]

        self.assertEqual(delta["unsatisfying_follow_up_kind"], "correction")
        self.assertEqual(delta["unsatisfying_follow_up_focus"], "question_line")
        self.assertEqual(delta["unsatisfying_relevance_label"], "low")
        self.assertEqual(delta["resolved_follow_up_kind"], "deeper_specificity")
        self.assertEqual(delta["resolved_follow_up_focus"], "answer_line")
        self.assertEqual(delta["resolved_relevance_label"], "high")
        self.assertIn("correction", expectation["rejected_follow_up_kinds"])
        self.assertIn("deeper_specificity", expectation["preferred_follow_up_kinds"])
        self.assertEqual(expectation["conversation_dynamics"]["correction"], 1)
        self.assertEqual(expectation["conversation_dynamics"]["deeper_specificity"], 1)

    def test_meta_layer_weights_user_redline_above_unsatisfying_assistant_text(self) -> None:
        source = self.root / "weighted-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "The ontology should preserve ambiguity before structure and avoid generic flattening.",
                    "",
                    "# Assistant",
                    "",
                    "The best approach is to collapse the ambiguity into neat fixed summaries.",
                    "",
                    "# User",
                    "",
                    "No. Preserve ambiguity first, then structure. That distinction matters.",
                    "",
                    "# Assistant",
                    "",
                    "Then the system should preserve ambiguity long enough for meaningful structure to emerge.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        extract_meta_layer(self.root, ["research"])
        records = load_meta_records(self.root)
        user_records = [row for row in records if row.get("attributes", {}).get("speaker_role") == "user"]
        assistant_records = [row for row in records if row.get("attributes", {}).get("speaker_role") == "assistant"]
        self.assertTrue(user_records)
        self.assertTrue(assistant_records)
        self.assertTrue(all(row.get("attributes", {}).get("semantic_role") == "semantic_line" for row in user_records))
        self.assertTrue(all(row.get("attributes", {}).get("semantic_role") == "approved_context" for row in assistant_records))
        self.assertTrue(any(row.get("attributes", {}).get("user_redline") for row in user_records))

    def test_meta_layer_carries_follow_up_dynamics_on_user_and_approved_context(self) -> None:
        source = self.root / "follow-up-meta.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "What are external thoughts?",
                    "",
                    "# Assistant",
                    "",
                    "They are aesthetic maps and mood clouds.",
                    "",
                    "# User",
                    "",
                    "No. More literal. Define external thoughts directly.",
                    "",
                    "# Assistant",
                    "",
                    "External thoughts are thoughts made perceivable outside the mind.",
                    "",
                    "# User",
                    "",
                    "Good. How do they help connect notes in practice?",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        extract_meta_layer(self.root, ["research"])
        records = load_meta_records(self.root)

        semantic_lines = [
            row
            for row in records
            if row.get("attributes", {}).get("semantic_role") == "semantic_line"
            and row.get("attributes", {}).get("follow_up_kind") == "correction"
        ]
        approved = [
            row
            for row in records
            if row.get("attributes", {}).get("semantic_role") == "approved_context"
            and row.get("attributes", {}).get("follow_up_kind") == "deeper_specificity"
        ]

        self.assertTrue(semantic_lines)
        self.assertTrue(approved)
        self.assertTrue(all(row.get("attributes", {}).get("follow_up_focus") == "question_line" for row in semantic_lines))
        self.assertTrue(all(row.get("attributes", {}).get("assistant_relevance_label") == "low" for row in semantic_lines))
        self.assertTrue(all(row.get("attributes", {}).get("follow_up_focus") == "answer_line" for row in approved))
        self.assertTrue(all(row.get("attributes", {}).get("assistant_relevance_label") == "high" for row in approved))
        self.assertTrue(all(row.get("attributes", {}).get("assistant_relevance_score", 0) >= 0.75 for row in approved))

    def test_unapproved_assistant_turn_does_not_become_knowledge_context(self) -> None:
        source = self.root / "unapproved-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Keep the system open-ended and ambiguity-preserving.",
                    "",
                    "# Assistant",
                    "",
                    "The system should immediately compress everything into rigid summaries.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        extract_meta_layer(self.root, ["research"])
        records = load_meta_records(self.root)
        self.assertTrue(any(row.get("attributes", {}).get("semantic_role") == "semantic_line" for row in records))
        self.assertFalse(any(row.get("attributes", {}).get("speaker_role") == "assistant" for row in records))

    def test_approved_assistant_context_is_embedded_into_knowledge_graph(self) -> None:
        source = self.root / "embedded-context-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "The system should preserve ambiguity before structure.",
                    "",
                    "# Assistant",
                    "",
                    "It should probably summarize aggressively up front.",
                    "",
                    "# User",
                    "",
                    "No. Preserve ambiguity first, then crystallize structure later.",
                    "",
                    "# Assistant",
                    "",
                    "Understood. The system should let ambiguity survive long enough for structure to emerge later.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        extract_meta_layer(self.root, ["research"])
        build_knowledge_layer(self.root)
        records = load_meta_records(self.root)
        edges = load_knowledge_edges(self.root)
        self.assertTrue(any(row.get("attributes", {}).get("semantic_role") == "semantic_line" for row in records))
        self.assertTrue(any(row.get("attributes", {}).get("semantic_role") == "approved_context" for row in records))
        self.assertTrue(any(edge["kind"] == "context_for" for edge in edges))

    def test_thread_layer_detects_interruption_and_return_within_conversation(self) -> None:
        source = self.root / "threaded-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "The system should preserve ambiguity before structure.",
                    "",
                    "# Assistant",
                    "",
                    "It should probably summarize early.",
                    "",
                    "# User",
                    "",
                    "Also, what colors should the interface use?",
                    "",
                    "# Assistant",
                    "",
                    "Muted earth tones could work.",
                    "",
                    "# User",
                    "",
                    "Back to the first point: ambiguity must survive before structure emerges.",
                    "",
                    "# Assistant",
                    "",
                    "Understood. The system should keep ambiguity alive before crystallizing structure.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        result = build_conversation_threads(self.root)
        threads = load_conversation_threads(self.root)
        links = load_thread_links(self.root)

        self.assertGreaterEqual(result["thread_count"], 2)
        ambiguity_thread = next(thread for thread in threads if "ambiguity" in " ".join(thread["topic_signature"]))
        self.assertGreaterEqual(ambiguity_thread["turn_count"], 2)
        self.assertTrue(ambiguity_thread["interruption_count"] >= 1)
        self.assertTrue(any(link["kind"] == "returns_to" for link in links))

    def test_thread_layer_continues_intent_across_sources(self) -> None:
        source_a = self.root / "thread-a.md"
        source_b = self.root / "thread-b.md"
        source_a.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "The system should preserve ambiguity before structure.",
                    "",
                    "# Assistant",
                    "",
                    "It should summarize early.",
                    "",
                    "# User",
                    "",
                    "No, ambiguity has to survive before structure.",
                ]
            ),
            encoding="utf-8",
        )
        source_b.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Returning to the earlier idea: preserve ambiguity first, then let structure emerge.",
                    "",
                    "# Assistant",
                    "",
                    "Yes, ambiguity should remain alive before structure forms.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source_a, "conversation_library")
        seed_sources(self.root, source_b, "conversation_library")
        build_conversation_threads(self.root)
        build_knowledge_layer(self.root)
        threads = load_conversation_threads(self.root)
        links = load_thread_links(self.root)
        edges = load_knowledge_edges(self.root)

        ambiguity_threads = [thread for thread in threads if "ambiguity" in " ".join(thread["topic_signature"])]
        self.assertTrue(ambiguity_threads)
        self.assertTrue(any(link["kind"] == "continues_across_sources" for link in links))
        self.assertTrue(any(edge["kind"] == "thread_continues" for edge in edges))

    def test_knowledge_layer_materializes_context_links_and_capsules(self) -> None:
        source_a = self.root / "link-a.md"
        source_b = self.root / "link-b.md"
        source_a.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "The system should preserve ambiguity before structure emerges.",
                    "",
                    "# Assistant",
                    "",
                    "It should summarize early.",
                    "",
                    "# User",
                    "",
                    "No, ambiguity needs to survive long enough for structure to form.",
                ]
            ),
            encoding="utf-8",
        )
        source_b.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Return to ambiguity-first interaction and let structure arrive later.",
                    "",
                    "# Assistant",
                    "",
                    "So the interaction should keep ambiguity alive before final structure.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source_a, "conversation_library")
        seed_sources(self.root, source_b, "conversation_library")
        extract_meta_layer(self.root, ["research"])
        build_conversation_threads(self.root)
        build_thread_abstractions(self.root, ["research"])
        build_context_bubbles(self.root)
        summary = build_knowledge_layer(self.root)

        context_links = load_context_links(self.root)
        capsules = load_semantic_capsules(self.root)

        self.assertGreater(summary["context_link_count"], 0)
        self.assertGreater(summary["capsule_count"], 0)
        self.assertTrue(any(link["layer"] == "substrate" and link["kind"] == "source_sequence" for link in context_links))
        self.assertTrue(any(link["layer"] == "semantic" for link in context_links))
        self.assertTrue(any(capsule["capsule_type"] == "meta" for capsule in capsules))
        self.assertTrue(any(capsule["capsule_type"] == "thread_abstraction" for capsule in capsules))
        self.assertTrue(any(capsule["capsule_type"] == "bubble" for capsule in capsules))

    def test_retrieval_bundle_assembles_linked_semantic_handles(self) -> None:
        source = self.root / "bundle-source.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Preserve ambiguity before structure so the signal is not flattened too early.",
                    "",
                    "# Assistant",
                    "",
                    "So the system should keep the ambiguity alive before shaping it into structure.",
                    "",
                    "# User",
                    "",
                    "The interaction model should reveal depth later instead of collapsing everything immediately.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        extract_meta_layer(self.root, ["research"])
        build_conversation_threads(self.root)
        build_thread_abstractions(self.root, ["research"])
        build_context_bubbles(self.root)
        build_knowledge_layer(self.root)

        bundle = build_retrieval_bundle(self.root, "ambiguity before structure", limit=6, neighbor_limit=4)

        self.assertGreaterEqual(bundle["count"], 1)
        self.assertTrue(bundle["seed_capsules"])
        self.assertTrue(any("ambiguity" in capsule["label"].lower() or "ambiguity" in capsule["summary"].lower() for capsule in bundle["seed_capsules"]))
        self.assertTrue(bundle["included_links"])
        self.assertTrue(bundle["source_refs"])

    def test_product_surface_exposes_capsule_and_link_filters(self) -> None:
        source = self.root / "link-filter-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Create a retrieval membrane that routes through semantic capsules before hitting the full corpus.",
                    "",
                    "# Assistant",
                    "",
                    "Yes, the retrieval membrane should prefer capsule-first routing and bounded context links.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        derive_graph(self.root, ["research"])

        filtered = filter_knowledge_components(
            self.root,
            query="capsule routing membrane",
            component_types=["capsule", "link"],
            source_ref=str(source.resolve()),
            limit=12,
            domain_overlays=["research"],
        )
        component_types = {row["component_type"] for row in filtered["results"]}
        self.assertIn("capsule", component_types)
        self.assertIn("link", component_types)

        bundle = get_retrieval_bundle(
            self.root,
            query="bounded context links",
            limit=6,
            neighbor_limit=4,
            domain_overlays=["research"],
        )
        self.assertGreaterEqual(bundle["count"], 1)
        self.assertTrue(bundle["included_links"])

    def test_link_governance_can_reject_links_without_mutating_raw_artifacts(self) -> None:
        source_a = self.root / "reject-link-a.md"
        source_b = self.root / "reject-link-b.md"
        source_a.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Preserve ambiguity before structure so the signal can survive.",
                    "",
                    "# Assistant",
                    "",
                    "Yes, ambiguity should stay alive before structure closes in.",
                ]
            ),
            encoding="utf-8",
        )
        source_b.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "The context membrane should keep ambiguity alive long enough for structure to emerge.",
                    "",
                    "# Assistant",
                    "",
                    "That membrane should delay closure until the structure earns it.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source_a, "conversation_library")
        seed_sources(self.root, source_b, "conversation_library")
        derive_graph(self.root, ["research"])

        raw_links_before = read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "context_links.jsonl")
        semantic_link = next(link for link in load_context_links(self.root) if link["layer"] == "semantic")
        result = govern_context_link(self.root, semantic_link["link_id"], governance_status="rejected", notes="Operator rejected this bridge.")

        self.assertEqual(result["policy"]["governance_status"], "rejected")
        resolved = next(link for link in load_context_links(self.root) if link["link_id"] == semantic_link["link_id"])
        self.assertEqual(resolved["status"], "rejected")
        self.assertEqual(resolved["confidence"], 0.0)
        self.assertEqual(raw_links_before, read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "context_links.jsonl"))

        bundle = build_retrieval_bundle(self.root, "ambiguity structure membrane", limit=8, neighbor_limit=6)
        self.assertNotIn(semantic_link["link_id"], {link["link_id"] for link in bundle["included_links"]})

    def test_alias_resolutions_can_seed_retrieval_bundle(self) -> None:
        source = self.root / "alias-bundle.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Protect the signal before you explain it and keep ambiguity alive before structure arrives.",
                    "",
                    "# Assistant",
                    "",
                    "So the interaction should keep the signal alive before structure hardens around it.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        derive_graph(self.root, ["research"])

        target_capsule = next(capsule for capsule in load_semantic_capsules(self.root) if capsule["capsule_type"] in {"bubble", "concept", "meta"})
        add_alias_resolution(
            self.root,
            "signal membrane",
            ref_type=target_capsule["ref_type"],
            ref_id=target_capsule["ref_id"],
            notes="Operator alias for alternate wording.",
        )
        governance = load_link_governance(self.root)
        self.assertTrue(governance["alias_resolutions"])

        bundle = build_retrieval_bundle(self.root, "signal membrane", limit=6, neighbor_limit=4)
        self.assertTrue(bundle["alias_hits"])
        seed_ids = {row["capsule_id"] for row in bundle["seed_capsules"]}
        self.assertIn(target_capsule["capsule_id"], seed_ids)

    def test_formation_synthesis_pipeline_emits_thought_packet_for_strong_match(self) -> None:
        rows = [
            self._meta_row(
                meta_id="meta-ambiguity",
                kind="theme",
                label="Ambiguity Before Structure",
                summary="Keep ambiguity alive long enough for structure to emerge later.",
                source_ref="source-a",
                chunk_id="chunk-a",
                confidence=0.84,
            ),
            self._meta_row(
                meta_id="meta-progressive",
                kind="theme",
                label="Progressive Disclosure Structure",
                summary="Reveal structure later instead of collapsing the signal immediately.",
                source_ref="source-b",
                chunk_id="chunk-b",
                confidence=0.8,
            ),
            self._meta_row(
                meta_id="meta-flatten",
                kind="contradiction",
                label="Premature Summary Collapse",
                summary="Summarize everything immediately and flatten ambiguity.",
                source_ref="source-c",
                chunk_id="chunk-c",
                confidence=0.72,
            ),
        ]
        self._write_meta_rows(rows)
        build_knowledge_layer(self.root)

        seed_packet = {
            "meta_refs": ["meta-ambiguity"],
            "source_refs": ["source-a"],
            "query_text": "ambiguity structure progressive disclosure",
        }
        candidates = retrieve_candidates(self.root, seed_packet, limit=6)

        self.assertGreaterEqual(len(candidates), 2)
        anchor = next(candidate for candidate in candidates if candidate.meta_id == "meta-ambiguity")
        matches = match_shapes(anchor, candidates)
        self.assertTrue(matches)

        strongest = matches[0]
        decision = choose_operator(strongest)
        synthesis = synthesize_candidate(strongest, decision)
        stress = stress_test_candidate(synthesis)
        packet = emit_thought_packet(synthesis, stress)

        self.assertEqual(decision.operator_key, "structure_map")
        self.assertTrue(stress.should_surface)
        self.assertIsNotNone(packet)
        self.assertEqual(packet["reasoning_pipeline"], "formation_synthesis_v1")
        self.assertEqual(packet["shared_primitive_key"], "structure_map")
        self.assertIn("meta-ambiguity", packet["meta_refs"])

    def test_formation_synthesis_pipeline_records_weak_output_in_review_queue(self) -> None:
        rows = [
            self._meta_row(
                meta_id="meta-ambiguity",
                kind="theme",
                label="Ambiguity Before Structure",
                summary="Keep ambiguity alive long enough for structure to emerge later.",
                source_ref="source-a",
                chunk_id="chunk-a",
                confidence=0.82,
            ),
            self._meta_row(
                meta_id="meta-collapse",
                kind="contradiction",
                label="Immediate Summary Collapse",
                summary="Summarize everything immediately and close down ambiguity.",
                source_ref="source-b",
                chunk_id="chunk-b",
                confidence=0.74,
            ),
        ]
        self._write_meta_rows(rows)
        build_knowledge_layer(self.root)

        seed_packet = {
            "meta_refs": ["meta-ambiguity"],
            "source_refs": ["source-a"],
            "query_text": "ambiguity collapse contradiction",
        }
        candidates = retrieve_candidates(self.root, seed_packet, limit=4)
        anchor = next(candidate for candidate in candidates if candidate.meta_id == "meta-ambiguity")
        contradiction = next(candidate for candidate in candidates if candidate.meta_id == "meta-collapse")
        match = next(row for row in match_shapes(anchor, [anchor, contradiction]) if row.candidate_meta_id == "meta-collapse")

        decision = choose_operator(match)
        synthesis = synthesize_candidate(match, decision)
        stress = stress_test_candidate(synthesis)
        packet = emit_thought_packet(synthesis, stress)
        review_row = record_formation_synthesis_review(self.root, seed_packet, synthesis, stress)
        review_rows = load_formation_synthesis_reviews(self.root)

        self.assertEqual(decision.operator_key, "find_counterpoint")
        self.assertFalse(stress.should_surface)
        self.assertIsNone(packet)
        self.assertEqual(review_row["status"], "needs_review")
        self.assertTrue(review_rows)
        self.assertEqual(review_rows[0]["synthesis_id"], synthesis.synthesis_id)

    def test_formation_synthesis_review_records_structural_anti_match_summary(self) -> None:
        seed_packet = {
            "meta_refs": ["meta-anchor-1"],
            "source_refs": ["source-a"],
            "query_text": "product clarity weak analogy",
        }
        synthesis = conversation_synthesis_module.SynthesisCandidate(
            synthesis_id="synthesis-reject-1",
            anchor_meta_id="meta-anchor-1",
            candidate_meta_id="meta-maze-1",
            operator_key="abduce_hypothesis",
            title="Product clarity failure needs review",
            short_text="A weak analogy should stay provisional.",
            summary="The analogy shares vocabulary but not the same system shape.",
            what_changed="The structural match broke under inspection.",
            why_it_matters_now="Direct transfer would target the wrong leverage point.",
            next_action="Review the rejected analogy and look for a stronger structural neighbor.",
            source_refs=["session:anchor-1", "session:maze-1"],
            source_item_ids=["chunk-anchor-1", "chunk-maze-1"],
            meta_refs=["meta-anchor-1", "meta-maze-1"],
            confidence_score=0.49,
            relevance_score=0.52,
            novelty_score=0.41,
            evidence_status="grounded",
            review_status="needs_review",
            shared_primitive_key="abduce_hypothesis",
            shared_primitive_label="Abduce hypothesis",
            reasoning_pipeline="formation_synthesis_v1",
            rationale="The analogy should not be transferred directly.",
            structural_fit={
                "role_fit": 0.25,
                "edge_fit": 0.0,
                "operation_fit": 0.0,
                "feedback_fit": 0.0,
                "anti_match_penalty": 0.25,
                "structural_score": 0.12,
                "verdict": "reject",
            },
            shared_tokens=["user", "confusion"],
            evidence=["anchor evidence", "candidate evidence"],
        )
        stress = conversation_synthesis_module.StressTestResult(
            should_surface=False,
            review_status="needs_review",
            evidence_status="grounded",
            confidence_adjustment=-0.08,
            concerns=["low_confidence"],
        )

        review_row = record_formation_synthesis_review(self.root, seed_packet, synthesis, stress)

        self.assertEqual(review_row["status"], "needs_review")
        self.assertEqual(review_row["anti_match_summary"]["verdict"], "reject")
        self.assertEqual(review_row["anti_match_summary"]["candidate_meta_id"], "meta-maze-1")
        self.assertGreater(review_row["anti_match_summary"]["anti_match_penalty"], 0.0)

    def test_product_surface_exposes_link_governance_wrappers(self) -> None:
        source = self.root / "governed-link-surface.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Build a context membrane that routes through semantic handles.",
                    "",
                    "# Assistant",
                    "",
                    "That membrane should connect the right capsules and suppress weak bridges.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        derive_graph(self.root, ["research"])

        target_link = next(link for link in load_context_links(self.root) if link["layer"] == "semantic")
        updated = update_link_governance(
            self.root,
            link_id=target_link["link_id"],
            governance_status="promoted",
            notes="High-value bridge.",
            domain_overlays=["research"],
        )
        self.assertEqual(updated["resolved_link"]["status"], "promoted")
        self.assertGreater(updated["resolved_link"]["confidence"], target_link["confidence"])

        target_capsule = next(capsule for capsule in load_semantic_capsules(self.root) if capsule["capsule_type"] in {"bubble", "concept", "meta"})
        alias_result = create_link_alias_resolution(
            self.root,
            alias_text="routing membrane",
            ref_type=target_capsule["ref_type"],
            ref_id=target_capsule["ref_id"],
            notes="Operator alias.",
            domain_overlays=["research"],
        )
        self.assertEqual(alias_result["alias_resolution"]["alias_text"], "routing membrane")

        governance = get_link_governance_state(self.root)
        self.assertGreaterEqual(governance["counts"]["link_policy_count"], 1)
        self.assertGreaterEqual(governance["counts"]["active_alias_count"], 1)
        self.assertTrue(governance["recent_link_policies"])
        self.assertTrue(governance["recent_alias_resolutions"])

    def test_thread_abstractions_merge_related_raw_threads_under_project_lens(self) -> None:
        source = self.root / "thread-abstract.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "The interface should feel like fragments first and reveal depth later.",
                    "",
                    "# Assistant",
                    "",
                    "It should just be a normal feed.",
                    "",
                    "# User",
                    "",
                    "No, I mean a twitter versus substack depth model with progressive disclosure.",
                    "",
                    "# User",
                    "",
                    "Also the interaction model should keep the fragment as the entry point before deeper article and chat layers.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        build_conversation_threads(self.root)
        summary = build_thread_abstractions(self.root, ["research"])
        abstractions = load_thread_abstractions(self.root)

        self.assertGreaterEqual(summary["raw_thread_count"], 2)
        interaction = [row for row in abstractions if row["primary_lens_key"] == "interaction_model"]
        self.assertEqual(len(interaction), 1)
        self.assertGreaterEqual(len(interaction[0]["child_thread_ids"]), 2)

    def test_thread_abstractions_assign_distinct_project_lenses(self) -> None:
        source = self.root / "thread-lenses.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "The interface should open as fragments and reveal article depth later.",
                    "",
                    "# User",
                    "",
                    "For the remainder of the chat answer short, literal, and precise.",
                    "",
                    "# User",
                    "",
                    "The color palette and interface composition should feel exact and intentional.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        build_conversation_threads(self.root)
        build_thread_abstractions(self.root, ["research"])
        abstractions = load_thread_abstractions(self.root)

        primary_lenses = {row["primary_lens_key"] for row in abstractions}
        self.assertIn("interaction_model", primary_lenses)
        self.assertIn("answer_shape_governance", primary_lenses)
        self.assertIn("interface_expression", primary_lenses)

    def test_context_for_edges_require_shared_delta_intent_and_are_capped(self) -> None:
        source = self.root / "context-cap-chat.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "What are external thoughts?",
                    "",
                    "# Assistant",
                    "",
                    "They are associative spaces and aesthetic maps.",
                    "",
                    "# User",
                    "",
                    "More literal. Define external thoughts directly.",
                    "",
                    "# Assistant",
                    "",
                    "External thoughts are thoughts made perceivable outside the mind.",
                    "",
                    "# User",
                    "",
                    "Also, what interface colors should we use?",
                    "",
                    "# Assistant",
                    "",
                    "Use muted blue and amber.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        extract_meta_layer(self.root, ["research"])
        build_conversation_threads(self.root)
        build_thread_abstractions(self.root, ["research"])
        build_knowledge_layer(self.root)
        records = {row["meta_id"]: row for row in load_meta_records(self.root)}
        edges = [row for row in load_knowledge_edges(self.root) if row["kind"] == "context_for"]

        counts = {}
        for edge in edges:
            counts[edge["from_id"]] = counts.get(edge["from_id"], 0) + 1
            from_meta = records[edge["from_id"].replace("meta-node-", "")]
            to_meta = records[edge["to_id"].replace("meta-node-", "")]
            shared_intents = set(from_meta.get("attributes", {}).get("delta_intent_keys", [])) & set(
                to_meta.get("attributes", {}).get("delta_intent_keys", [])
            )
            self.assertTrue(shared_intents)
        self.assertTrue(counts)
        self.assertTrue(all(count <= 2 for count in counts.values()))

    def test_context_bubbles_capture_abstract_thread_and_project_lenses(self) -> None:
        source = self.root / "bubble-abstraction.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "The system should preserve ambiguity before structure.",
                    "",
                    "# Assistant",
                    "",
                    "It should summarize early.",
                    "",
                    "# User",
                    "",
                    "No. Preserve ambiguity first, then reveal structure later through the interaction model.",
                    "",
                    "# Assistant",
                    "",
                    "Understood. Let ambiguity survive before structure emerges.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        derive_graph(self.root, ["research"])
        bubbles = load_context_bubbles(self.root)
        self.assertTrue(bubbles)
        self.assertTrue(any(row.get("primary_abstract_thread_id") for row in bubbles))
        self.assertTrue(any(row.get("project_lens_keys") for row in bubbles))

    def test_runtime_exports_include_thread_abstractions_and_project_lenses(self) -> None:
        source = self.root / "runtime-threads.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "The interface should reveal depth progressively.",
                    "",
                    "# User",
                    "",
                    "Answer short and precise.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        derive_graph(self.root, ["research"])
        runtime = get_runtime_overview(self.root)
        exported = export_state(self.root)
        lenses = load_project_lenses(self.root)

        self.assertIn("conversation_threads", runtime["counts"])
        self.assertIn("thread_abstractions", runtime["counts"])
        self.assertIn("project_lenses", runtime["counts"])
        self.assertIn("conversation_threads", exported)
        self.assertIn("thread_abstractions", exported)
        self.assertIn("thread_abstraction_links", exported)
        self.assertIn("project_lenses", exported)
        self.assertGreaterEqual(len(lenses), 8)

    def test_analysis_units_aggregate_related_chunks(self) -> None:
        source = self.root / "analysis-units.md"
        source.write_text(
            "\n".join(
                [
                    "# System",
                    "",
                    "The vault should preserve raw truth.",
                    "",
                    "The meta layer should sit above raw content.",
                    "",
                    "The reasoning layer should connect meaningful structures.",
                    "",
                    "## Feed",
                    "",
                    "The product should surface short thoughts first.",
                    "",
                    "Each thought should expand into a deeper article.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source)
        summary = build_analysis_units(self.root)
        units = load_analysis_units(self.root)

        self.assertLess(summary["analysis_unit_count"], summary["chunk_count"])
        self.assertGreaterEqual(len(units), 2)
        self.assertTrue(any(len(unit["chunk_ids"]) > 1 for unit in units))

    def test_titles_prefer_salient_shared_terms(self) -> None:
        source_a = self.root / "signal-a.txt"
        source_b = self.root / "signal-b.txt"
        source_a.write_text(
            (
                "Inner World is a private cognitive layer that turns saved notes into ranked, "
                "evidence-backed insights you would likely not have seen on your own."
            ),
            encoding="utf-8",
        )
        source_b.write_text(
            (
                "The thesis defines a private cognitive layer that turns conversations into ranked, "
                "evidence-backed insights you would likely not have seen on your own."
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source_a)
        seed_sources(self.root, source_b)
        derive_graph(self.root, ["research"])
        generate_daily_batch(self.root, limit=3, domain_overlays=["research"])
        feed = build_thought_feed(self.root, limit=3, domain_overlays=["research"], regenerate_batch=False)

        self.assertGreaterEqual(feed["count"], 1)
        thought = feed["thoughts"][0]
        self.assertEqual(thought["title"], "This Is Not A Note App")
        self.assertIn("private cognitive layer", thought["short_text"].lower())
        self.assertNotIn("cross-document bridge", thought["short_text"].lower())

    def test_batch_dedupes_duplicate_titles(self) -> None:
        for index, content in enumerate(
            [
                "Morning batch is the default experience for the product.",
                "The product should use a morning batch as the default experience.",
                "Choose morning batch as the default experience and keep archive secondary.",
            ],
            start=1,
        ):
            path = self.root / f"duplicate-{index}.txt"
            path.write_text(content, encoding="utf-8")
            seed_sources(self.root, path)

        derive_graph(self.root, ["research"])
        batch = generate_daily_batch(self.root, limit=5, domain_overlays=["research"])

        titles = [insight["title"] for insight in batch["insights"]]
        self.assertEqual(len(titles), len(set(titles)))

    def test_feed_uses_human_thought_voice_for_known_patterns(self) -> None:
        source_a = self.root / "batch-a.txt"
        source_b = self.root / "batch-b.txt"
        source_a.write_text("Morning Batch should be the default surface for the product.", encoding="utf-8")
        source_b.write_text("A calm morning batch keeps the product from becoming noisy.", encoding="utf-8")
        seed_sources(self.root, source_a)
        seed_sources(self.root, source_b)
        derive_graph(self.root, ["research"])
        generate_daily_batch(self.root, limit=3, domain_overlays=["research"])
        feed = build_thought_feed(self.root, limit=3, domain_overlays=["research"], regenerate_batch=False)

        titles = [thought["title"] for thought in feed["thoughts"]]
        self.assertIn("Morning Batch Is The Native Surface", titles)
        thought = next(item for item in feed["thoughts"] if item["title"] == "Morning Batch Is The Native Surface")
        self.assertNotIn("cross-document bridge", thought["short_text"].lower())
        self.assertIn("calm daily batch", thought["short_text"].lower())
        self.assertTrue(thought["source_item_ids"])

    def test_feed_dedupes_synthesized_titles(self) -> None:
        source_a = self.root / "dupe-a.txt"
        source_b = self.root / "dupe-b.txt"
        source_c = self.root / "dupe-c.txt"
        source_a.write_text("Morning Batch is the default surface.", encoding="utf-8")
        source_b.write_text("A calm morning batch should be the default delivery.", encoding="utf-8")
        source_c.write_text("Morning batch reduces noise and should stay the default surface.", encoding="utf-8")
        seed_sources(self.root, source_a)
        seed_sources(self.root, source_b)
        seed_sources(self.root, source_c)
        derive_graph(self.root, ["research"])
        generate_daily_batch(self.root, limit=6, domain_overlays=["research"])
        feed = build_thought_feed(self.root, limit=6, domain_overlays=["research"], regenerate_batch=False)

        titles = [thought["title"] for thought in feed["thoughts"]]
        self.assertEqual(len(titles), len(set(titles)))

    def test_thought_feed_and_thread_lifecycle(self) -> None:
        source = self.root / "thought-seed.txt"
        source.write_text(
            "\n".join(
                [
                    "Research note on evidence quality and mechanism design.",
                    "Research note on explanation clarity and source grounding.",
                    "Art note on atmosphere, material texture, and contrast.",
                    "Creative note on editorial interfaces and rhythm.",
                    "Founder note on onboarding friction and retention loops.",
                    "Founder note on strategic wedges and adoption barriers.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source)
        derive_graph(self.root, ["research", "art", "entrepreneurship"])
        generate_daily_batch(self.root, limit=4, domain_overlays=["research", "art", "entrepreneurship"])

        feed = build_thought_feed(self.root, limit=4, domain_overlays=["research", "art", "entrepreneurship"])
        self.assertGreaterEqual(feed["count"], 1)
        thought = feed["thoughts"][0]
        self.assertTrue(thought["short_text"])
        self.assertIn("article_markdown", thought)
        self.assertNotIn("↔", thought["title"])
        self.assertNotIn("deeper connection surfaced", thought["short_text"].lower())
        self.assertNotIn("random overlap", thought["short_text"].lower())
        self.assertIn("## The central tension", thought["article_markdown"])
        self.assertIn("## What to do with it", thought["article_markdown"])
        self.assertEqual(thought["post_id"], thought["thought_id"])
        self.assertEqual(thought["reach_mode"], "strict")
        self.assertIn("preview_payload", thought)
        self.assertIn("expand_payload", thought)
        self.assertIn("deep_read_ref", thought)
        self.assertIn("post_context", thought)
        self.assertEqual(thought["preview_payload"]["short_text"], thought["short_text"])
        self.assertEqual(thought["expand_payload"]["thought_id"], thought["thought_id"])
        self.assertEqual(thought["deep_read_ref"]["thought_id"], thought["thought_id"])
        self.assertLessEqual(len(thought["post_context"]["source_snippets"]), 4)
        self.assertLessEqual(len(thought["post_context"]["supporting_meta"]), 3)
        self.assertEqual(thought["post_context"]["thought_id"], thought["thought_id"])

        detail = get_thought_detail(self.root, thought["thought_id"], ["research", "art", "entrepreneurship"])
        self.assertEqual(detail["thought"]["thought_id"], thought["thought_id"])
        self.assertTrue(detail["source_snippets"])
        self.assertIn("feed_post", detail)
        self.assertEqual(detail["feed_post"]["post_id"], thought["post_id"])
        self.assertEqual(detail["feed_post"]["expand_payload"]["thought_id"], thought["thought_id"])
        self.assertEqual(detail["feed_post"]["post_context"]["reach_mode"], "strict")

        archive = build_thought_archive(self.root, ["research", "art", "entrepreneurship"])
        self.assertGreaterEqual(archive["count"], feed["count"])
        self.assertIn("evidence_status", archive["filters"])

        source_detail = get_source_item_detail(
            self.root,
            detail["source_snippets"][0]["source_item_id"],
            ["research", "art", "entrepreneurship"],
        )
        self.assertEqual(
            source_detail["source_item"]["source_item_id"],
            detail["source_snippets"][0]["source_item_id"],
        )
        self.assertIn("path_name", source_detail["source_item"])
        self.assertTrue(source_detail["related_thoughts"])

        chat_result = chat_with_thought(
            self.root,
            thought["thought_id"],
            "Why does this matter now and what should I do with it?",
            domain_overlays=["research", "art", "entrepreneurship"],
        )
        thread = chat_result["thread"]
        self.assertEqual(thread["thought_id"], thought["thought_id"])
        self.assertEqual(thread["status"], "draft")
        self.assertGreaterEqual(len(thread["messages"]), 2)
        self.assertIn("context_summary", chat_result["context"])
        assistant_message = thread["messages"][-1]["content"].lower()
        self.assertNotIn("this thought is surfacing because", assistant_message)
        self.assertIn("it seems to keep circling this", assistant_message)

        saved = save_thread(self.root, thread["thread_id"], ["research", "art", "entrepreneurship"])
        self.assertEqual(saved["status"], "saved")
        self.assertTrue(saved["embedded_source_item_ids"])
        source_items = read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "source_items.jsonl")
        self.assertTrue(any(row.get("thread_id") == thread["thread_id"] for row in source_items))

        deleted = delete_thread(self.root, thread["thread_id"])
        self.assertEqual(deleted["status"], "deleted")

    def test_openclaw_backend_resolution_and_adapter(self) -> None:
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "chat_backend": "openclaw_gateway",
                    "openclaw": {
                        "agent": "telegram",
                        "thinking": "low",
                        "timeout_seconds": 12,
                        "deliver": False,
                    },
                }
            ),
            encoding="utf-8",
        )
        with mock.patch.dict("os.environ", {"INNER_WORLD_CHAT_BACKEND": "openclaw_local"}, clear=False):
            backend = resolve_chat_backend(self.root)
        self.assertEqual(backend["id"], "openclaw_local")
        self.assertEqual(backend["openclaw"]["agent"], "telegram")

        context = {
            "character": "Grounded editorial mirror",
            "system_prompt": "Stay grounded.",
            "source_snippets": [
                {
                    "title": "Snippet A",
                    "source_ref": str(self.root / "a.md"),
                    "excerpt": "Grounded excerpt",
                }
            ],
        }
        thread = {"thread_id": "thread-123", "messages": [{"role": "user", "content": "First"}]}
        completed = mock.Mock(
            returncode=0,
            stdout=json.dumps(
                {
                    "reply": "OpenClaw response",
                    "model": "openclaw-test-model",
                    "usage": {
                        "prompt_tokens": 120,
                        "completion_tokens": 30,
                        "cost_usd": 0.0123,
                    },
                }
            ),
            stderr="",
        )
        with mock.patch("conversation_os.chat_backends.subprocess.run", return_value=completed) as run_mock:
            result = request_openclaw_reply(
                self.root,
                context,
                "What does this thought mean?",
                thread,
                {"id": "openclaw_local", "openclaw": {"agent": "main", "thinking": "minimal", "timeout_seconds": 30, "deliver": False}},
            )
        self.assertEqual(result["content"], "OpenClaw response")
        command = run_mock.call_args.kwargs["args"] if "args" in run_mock.call_args.kwargs else run_mock.call_args.args[0]
        self.assertIn("--local", command)
        self.assertIn("thread-123", command)
        events = list_cost_events(self.root)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["ledger"], "actual")
        self.assertEqual(events[0]["input_tokens"], 120)
        self.assertEqual(events[0]["output_tokens"], 30)
        self.assertEqual(events[0]["usd_cost"], 0.0123)

    def _write_openclaw_control_fixture(self) -> Path:
        config_path = self.root / "openclaw.json"
        config_path.write_text(
            json.dumps(
                {
                    "agents": {
                        "defaults": {
                            "model": {"primary": "google-gemini-cli/gemini-3-pro-preview"},
                            "models": {
                                "google-gemini-cli/gemini-3-pro-preview": {},
                                "minimax/MiniMax-M2.5": {},
                            },
                        },
                        "list": [
                            {"id": "main"},
                            {"id": "telegram", "name": "Telegram", "model": "minimax/MiniMax-M2.5"},
                        ],
                    },
                    "gateway": {"mode": "local", "port": 4242},
                    "models": {
                        "providers": {
                            "minimax": {
                                "models": [
                                    {"id": "MiniMax-M2.5", "name": "MiniMax M2.5"},
                                ]
                            }
                        }
                    },
                }
            ),
            encoding="utf-8",
        )
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "runtime.json").write_text(
            json.dumps({"openclaw": {"config_path": str(config_path)}}),
            encoding="utf-8",
        )
        return config_path

    def test_openclaw_model_control_state_and_staging(self) -> None:
        self._write_openclaw_control_fixture()

        state = get_openclaw_model_control_state(self.root)
        self.assertEqual(state["default_model_id"], "google-gemini-cli/gemini-3-pro-preview")
        self.assertIn("minimax/MiniMax-M2.5", state["available_models"])
        main = next(item for item in state["agents"] if item["agent_id"] == "main")
        telegram = next(item for item in state["agents"] if item["agent_id"] == "telegram")
        self.assertTrue(main["uses_default"])
        self.assertEqual(main["effective_model_id"], "google-gemini-cli/gemini-3-pro-preview")
        self.assertEqual(telegram["effective_model_id"], "minimax/MiniMax-M2.5")

        staged_main = stage_openclaw_agent_model(self.root, "main", "minimax/MiniMax-M2.5")
        self.assertTrue(staged_main["dirty"])
        self.assertEqual(staged_main["change"]["agent_id"], "main")
        self.assertEqual(staged_main["change"]["new_model_id"], "minimax/MiniMax-M2.5")

        staged_telegram = stage_openclaw_agent_model(
            self.root,
            "telegram",
            "google-gemini-cli/gemini-3-pro-preview",
        )
        self.assertTrue(staged_telegram["dirty"])
        state = get_openclaw_model_control_state(self.root)
        telegram = next(item for item in state["agents"] if item["agent_id"] == "telegram")
        self.assertTrue(telegram["has_pending_change"])
        self.assertEqual(telegram["effective_model_id"], "google-gemini-cli/gemini-3-pro-preview")
        control_state = read_json(self.root / "product" / "inner_world_v1" / "data" / "openclaw_model_control_state.json")
        self.assertEqual(control_state["pending_assignments"]["main"], "minimax/MiniMax-M2.5")
        self.assertIsNone(control_state["pending_assignments"]["telegram"])

    def test_openclaw_model_control_apply_updates_config_and_clears_pending(self) -> None:
        config_path = self._write_openclaw_control_fixture()
        stage_openclaw_agent_model(self.root, "main", "minimax/MiniMax-M2.5")

        responses = [
            mock.Mock(returncode=0, stdout="gateway restarted", stderr=""),
            mock.Mock(returncode=0, stdout="healthy", stderr=""),
        ]
        with mock.patch("conversation_os.chat_backends.subprocess.run", side_effect=responses) as run_mock:
            result = apply_openclaw_model_control(self.root)

        self.assertTrue(result["applied"])
        updated = json.loads(config_path.read_text(encoding="utf-8"))
        main = next(item for item in updated["agents"]["list"] if item["id"] == "main")
        self.assertEqual(main["model"], "minimax/MiniMax-M2.5")
        state = get_openclaw_model_control_state(self.root)
        self.assertFalse(state["dirty"])
        self.assertEqual(state["pending_changes"], [])
        self.assertTrue(Path(result["backup_path"]).exists())
        commands = [
            call.kwargs["args"] if "args" in call.kwargs else call.args[0]
            for call in run_mock.call_args_list
        ]
        self.assertEqual(commands[0], ["openclaw", "gateway", "restart"])
        self.assertEqual(commands[1], ["openclaw", "gateway", "health"])

    def test_openclaw_model_control_apply_restores_backup_on_failure(self) -> None:
        config_path = self._write_openclaw_control_fixture()
        original = json.loads(config_path.read_text(encoding="utf-8"))
        stage_openclaw_agent_model(self.root, "main", "minimax/MiniMax-M2.5")

        responses = [
            mock.Mock(returncode=0, stdout="gateway restarted", stderr=""),
            mock.Mock(returncode=1, stdout="", stderr="not healthy"),
            mock.Mock(returncode=0, stdout="rollback restart", stderr=""),
        ]
        with mock.patch("conversation_os.chat_backends.subprocess.run", side_effect=responses):
            with self.assertRaises(RuntimeError):
                apply_openclaw_model_control(self.root)

        restored = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(restored, original)

    def test_openclaw_model_control_rollback_restores_previous_backup(self) -> None:
        config_path = self._write_openclaw_control_fixture()
        stage_openclaw_agent_model(self.root, "main", "minimax/MiniMax-M2.5")

        apply_responses = [
            mock.Mock(returncode=0, stdout="gateway restarted", stderr=""),
            mock.Mock(returncode=0, stdout="healthy", stderr=""),
        ]
        with mock.patch("conversation_os.chat_backends.subprocess.run", side_effect=apply_responses):
            apply_openclaw_model_control(self.root)

        rollback_responses = [
            mock.Mock(returncode=0, stdout="gateway restarted", stderr=""),
            mock.Mock(returncode=0, stdout="healthy", stderr=""),
        ]
        with mock.patch("conversation_os.chat_backends.subprocess.run", side_effect=rollback_responses):
            result = rollback_openclaw_model_control(self.root)

        self.assertTrue(result["rolled_back"])
        restored = json.loads(config_path.read_text(encoding="utf-8"))
        main = next(item for item in restored["agents"]["list"] if item["id"] == "main")
        self.assertNotIn("model", main)

    def test_miniapp_exposes_openclaw_model_control_routes(self) -> None:
        self._write_openclaw_control_fixture()
        server, thread, base_url = self._start_test_miniapp_server()
        try:
            status, state = self._json_request(f"{base_url}/api/openclaw/model-control/state")
            self.assertEqual(status, 200)
            self.assertEqual(state["default_model_id"], "google-gemini-cli/gemini-3-pro-preview")

            status, assign = self._json_request(
                f"{base_url}/api/openclaw/model-control/assign",
                method="POST",
                payload={"agent_id": "main", "model_id": "minimax/MiniMax-M2.5"},
            )
            self.assertEqual(status, 200)
            self.assertTrue(assign["dirty"])
            self.assertEqual(assign["change"]["agent_id"], "main")

            responses = [
                mock.Mock(returncode=0, stdout="gateway restarted", stderr=""),
                mock.Mock(returncode=0, stdout="healthy", stderr=""),
            ]
            with mock.patch("conversation_os.chat_backends.subprocess.run", side_effect=responses):
                status, applied = self._json_request(
                    f"{base_url}/api/openclaw/model-control/apply",
                    method="POST",
                    payload={},
                )
            self.assertEqual(status, 200)
            self.assertTrue(applied["applied"])

            responses = [
                mock.Mock(returncode=0, stdout="gateway restarted", stderr=""),
                mock.Mock(returncode=0, stdout="healthy", stderr=""),
            ]
            with mock.patch("conversation_os.chat_backends.subprocess.run", side_effect=responses):
                status, rolled_back = self._json_request(
                    f"{base_url}/api/openclaw/model-control/rollback",
                    method="POST",
                    payload={},
                )
            self.assertEqual(status, 200)
            self.assertTrue(rolled_back["rolled_back"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_miniapp_openclaw_model_control_route_validation(self) -> None:
        self._write_openclaw_control_fixture()
        server, thread, base_url = self._start_test_miniapp_server()
        try:
            request = urllib_request.Request(
                f"{base_url}/api/openclaw/model-control/assign",
                data=json.dumps({"agent_id": "main"}).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(urllib_error.HTTPError) as error_context:
                urllib_request.urlopen(request)
            self.assertEqual(error_context.exception.code, 400)
            payload = json.loads(error_context.exception.read().decode("utf-8"))
            self.assertEqual(payload["error"], "agent_id_and_model_id_required")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_miniapp_exposes_linking_overview_and_retrieval_bundle_routes(self) -> None:
        source = self.root / "miniapp-linking.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Build semantic capsules that can route through bounded context links.",
                    "",
                    "# Assistant",
                    "",
                    "The system should assemble a small retrieval bundle from those capsules.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        derive_graph(self.root, ["research"])
        server, thread, base_url = self._start_test_miniapp_server()
        try:
            status, overview = self._json_request(f"{base_url}/api/linking-overview?query=semantic+capsules&limit=6")
            self.assertEqual(status, 200)
            self.assertGreaterEqual(overview["counts"]["context_links"], 1)
            self.assertTrue(overview["top_semantic_capsules"])
            self.assertTrue(overview["retrieval_bundle"]["seed_capsules"])

            status, bundle = self._json_request(f"{base_url}/api/retrieval-bundle?query=bounded+context+links&limit=6")
            self.assertEqual(status, 200)
            self.assertGreaterEqual(bundle["count"], 1)
            self.assertTrue(bundle["included_links"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_miniapp_exposes_link_governance_routes(self) -> None:
        source = self.root / "miniapp-link-governance.md"
        source.write_text(
            "\n".join(
                [
                    "# User",
                    "",
                    "Create a capsule routing field with a few strong context bridges.",
                    "",
                    "# Assistant",
                    "",
                    "The routing field should be governable so weak bridges can be rejected later.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        derive_graph(self.root, ["research"])
        target_link = next(link for link in load_context_links(self.root) if link["layer"] == "semantic")
        target_capsule = next(capsule for capsule in load_semantic_capsules(self.root) if capsule["capsule_type"] in {"bubble", "concept", "meta"})

        server, thread, base_url = self._start_test_miniapp_server()
        try:
            status, state = self._json_request(f"{base_url}/api/link-governance-state")
            self.assertEqual(status, 200)
            self.assertIn("counts", state)

            status, link_result = self._json_request(
                f"{base_url}/api/link-governance/link",
                method="POST",
                payload={"link_id": target_link["link_id"], "governance_status": "rejected", "notes": "Weak bridge"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(link_result["resolved_link"]["status"], "rejected")

            status, alias_result = self._json_request(
                f"{base_url}/api/link-governance/alias",
                method="POST",
                payload={
                    "alias_text": "capsule routing field",
                    "ref_type": target_capsule["ref_type"],
                    "ref_id": target_capsule["ref_id"],
                    "notes": "Alternate operator wording",
                },
            )
            self.assertEqual(status, 200)
            self.assertEqual(alias_result["alias_resolution"]["alias_text"], "capsule routing field")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_thought_packets_use_bounded_openclaw_assist_for_generic_candidates(self) -> None:
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "chat_backend": "openclaw_local",
                    "openclaw": {"agent": "main", "thinking": "minimal", "timeout_seconds": 12},
                    "semantic_assist": {"enabled": True, "thought_candidate_limit": 1},
                }
            ),
            encoding="utf-8",
        )
        ingest_text_content(
            self.root,
            title="Thought Source",
            content="The system should protect the signal before it gets flattened by generic explanation.",
            source_ref="thought://semantic",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        source_item = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "thought://semantic")
        base_row = {
            "source_refs": ["thought://semantic"],
            "source_item_ids": [source_item["source_item_id"]],
            "meta_refs": ["meta-1"],
            "shared_terms": ["signal", "flattening"],
            "shared_primitive_key": "novel-pattern",
            "shared_primitive_label": "Novel Pattern",
            "what_changed": "The raw signal keeps collapsing into generic explanation.",
            "why_it_matters_now": "This changes whether the system preserves meaning or flattens it.",
            "next_action": "Review it.",
            "reasoning_pipeline": "cross_pollination_v1+thought_surfacing_v1",
            "primary_bubble_id": "",
            "primary_bubble_label": "",
            "related_bubble_ids": [],
            "review_status": "ready_for_review",
            "evidence_status": "grounded",
            "confidence_score": 0.74,
            "relevance_score": 0.71,
            "novelty_score": 0.69,
            "left_label": "Signal",
            "right_label": "Explanation",
            "unresolved_questions": ["What exactly is being protected?"],
        }
        rows = [
            {
                **base_row,
                "packet_id": "packet-a",
                "insight_id": "insight-a",
                "candidate_title": "Something in signal keeps asking for room",
                "candidate_short_text": "Something in signal keeps asking for room before it gets flattened.",
            },
            {
                **base_row,
                "packet_id": "packet-b",
                "insight_id": "insight-b",
                "candidate_title": "Something in explanation keeps asking for room",
                "candidate_short_text": "Something in explanation keeps asking for room before it gets flattened.",
            },
        ]
        completed = mock.Mock(
            returncode=0,
            stdout=json.dumps(
                {
                    "reply": json.dumps(
                        {
                            "decision": "promote",
                            "title": "Protect The Signal",
                            "short_text": "The raw signal loses force once explanation gets too generic too early.",
                            "confidence": "high",
                            "reason": "This candidate has a clear grounded message.",
                        }
                    )
                }
            ),
            stderr="",
        )

        with mock.patch("conversation_os.thought_factory.subprocess.run", return_value=completed) as run_mock:
            packets = build_thought_packets(self.root, rows, {})

        self.assertEqual(run_mock.call_count, 1)
        self.assertTrue(any(packet["title"] == "Protect The Signal" for packet in packets))
        promoted_packet = next(packet for packet in packets if packet["title"] == "Protect The Signal")
        self.assertEqual(promoted_packet["semantic_assist"]["decision"], "promote")

    def test_thought_packets_respect_openclaw_reject_for_weak_candidate(self) -> None:
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "chat_backend": "openclaw_local",
                    "openclaw": {"agent": "main", "thinking": "minimal", "timeout_seconds": 12},
                    "semantic_assist": {"enabled": True, "thought_candidate_limit": 1},
                }
            ),
            encoding="utf-8",
        )
        ingest_text_content(
            self.root,
            title="Weak Thought Source",
            content="There might be some overlap here, but it is still vague.",
            source_ref="thought://weak",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        source_item = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "thought://weak")
        row = {
            "packet_id": "packet-weak",
            "insight_id": "insight-weak",
            "left_label": "Signal",
            "right_label": "Noise",
            "shared_terms": ["signal"],
            "shared_primitive_key": "novel-pattern",
            "shared_primitive_label": "Novel Pattern",
            "source_refs": ["thought://weak"],
            "source_item_ids": [source_item["source_item_id"]],
            "meta_refs": ["meta-weak"],
            "review_status": "ready_for_review",
            "evidence_status": "grounded",
            "confidence_score": 0.63,
            "novelty_score": 0.55,
            "relevance_score": 0.54,
            "what_changed": "Some overlap appeared.",
            "why_it_matters_now": "It may matter later.",
            "next_action": "Wait.",
            "reasoning_pipeline": "cross_pollination_v1+thought_surfacing_v1",
            "unresolved_questions": ["What is actually new here?"],
            "candidate_title": "Something in signal keeps asking for room",
            "candidate_short_text": "Something in signal keeps asking for room.",
            "primary_bubble_id": "",
            "primary_bubble_label": "",
            "related_bubble_ids": [],
        }
        completed = mock.Mock(
            returncode=0,
            stdout=json.dumps(
                {
                    "reply": json.dumps(
                        {
                            "decision": "reject",
                            "title": "",
                            "short_text": "",
                            "confidence": "medium",
                            "reason": "This is still too vague to surface.",
                        }
                    )
                }
            ),
            stderr="",
        )

        with mock.patch("conversation_os.thought_factory.subprocess.run", return_value=completed):
            packets = build_thought_packets(self.root, [row], {})

        self.assertEqual(packets, [])

    def test_generate_daily_batch_records_equivalent_pipeline_cost(self) -> None:
        source = self.root / "cost-seed.txt"
        source.write_text(
            "\n".join(
                [
                    "Private cognitive layer should keep the signal intact.",
                    "Progressive disclosure should let ambiguity survive long enough to become structure.",
                    "Mechanism bridge reasoning should connect the fragments without flattening them.",
                    "Review before commit keeps the substrate trustworthy.",
                ]
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source)
        derive_graph(self.root, ["research"])
        batch = generate_daily_batch(self.root, limit=2, domain_overlays=["research"])
        self.assertGreaterEqual(batch["count"], 1)
        summary = get_cost_summary(self.root)
        self.assertGreater(summary["totals"]["equivalent_event_count"], 0)
        self.assertGreater(summary["totals"]["equivalent_usd_total"], 0.0)
        self.assertGreater(summary["totals"]["equivalent_total_tokens"], 0)
        self.assertTrue(summary["by_operation"])

    def test_cli_token_dashboard_commands_return_structured_payloads(self) -> None:
        source = self.root / "cost-cli.txt"
        source.write_text(
            "Private cognitive layer and progressive disclosure should become one coherent architecture field.",
            encoding="utf-8",
        )
        seed_sources(self.root, source)
        derive_graph(self.root, ["research"])
        generate_daily_batch(self.root, limit=1, domain_overlays=["research"])

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(["inner-world", "token-dashboard"])
        self.assertEqual(exit_code, 0)
        report_payload = json.loads(stdout.getvalue())
        self.assertIn("totals", report_payload)
        self.assertIn("by_operation", report_payload)
        self.assertIn("by_component", report_payload)

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(["inner-world", "token-events", "--limit", "5"])
        self.assertEqual(exit_code, 0)
        events_payload = json.loads(stdout.getvalue())
        self.assertIn("count", events_payload)
        self.assertIn("events", events_payload)

    def test_openclaw_bundle_generation(self) -> None:
        bundle = build_openclaw_bundle(self.root, app_id="inner-world-test", api_base_url="/apps/api/inner-world-test")
        bundle_dir = Path(bundle["bundle_dir"])
        self.assertTrue((bundle_dir / "app.json").exists())
        self.assertTrue((bundle_dir / "runtime-config.js").exists())
        self.assertTrue((bundle_dir / "world-studio.html").exists())
        self.assertTrue((bundle_dir / "world-studio.css").exists())
        self.assertTrue((bundle_dir / "world-studio.js").exists())
        index_html = (bundle_dir / "index.html").read_text(encoding="utf-8")
        runtime_config = (bundle_dir / "runtime-config.js").read_text(encoding="utf-8")
        self.assertIn("./styles.css", index_html)
        self.assertIn("./app.js", index_html)
        self.assertIn("/apps/api/inner-world-test", runtime_config)

    def test_miniapp_serves_feed_ui_enhancement_assets(self) -> None:
        server, thread, base_url = self._start_test_miniapp_server()
        try:
            with urllib_request.urlopen(f"{base_url}/") as response:
                self.assertEqual(response.status, 200)
                index_html = response.read().decode("utf-8")
            self.assertIn("./feed-ui-enhancement.css", index_html)
            self.assertIn("./feed-ui-enhancement.js", index_html)

            with urllib_request.urlopen(f"{base_url}/feed-ui-enhancement.css") as response:
                self.assertEqual(response.status, 200)
                css = response.read().decode("utf-8")
            self.assertIn(".feed-preview", css)

            with urllib_request.urlopen(f"{base_url}/feed-ui-enhancement.js") as response:
                self.assertEqual(response.status, 200)
                js = response.read().decode("utf-8")
            self.assertIn("window.__INNER_WORLD_FEED_UI_ENHANCED__", js)
            self.assertIn("renderPost = window.renderPost", js)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_miniapp_mobile_feed_requires_session_auth(self) -> None:
        server, thread, base_url = self._start_test_mobile_miniapp_server()
        try:
            with self.assertRaises(urllib_error.HTTPError) as error_context:
                urllib_request.urlopen(f"{base_url}/api/mobile/feed")
            self.assertEqual(error_context.exception.code, 401)
            payload = json.loads(error_context.exception.read().decode("utf-8"))
            self.assertEqual(payload["error"], "auth_required")
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_miniapp_mobile_session_rejects_invalid_password(self) -> None:
        with mock.patch.dict(os.environ, {"INNER_WORLD_MOBILE_PASSWORD": "mobile-pass"}, clear=False):
            server, thread, base_url = self._start_test_mobile_miniapp_server()
            try:
                request = urllib_request.Request(
                    f"{base_url}/api/mobile/session",
                    data=json.dumps({"password": "wrong-pass"}).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with self.assertRaises(urllib_error.HTTPError) as error_context:
                    urllib_request.urlopen(request)
                self.assertEqual(error_context.exception.code, 401)
                payload = json.loads(error_context.exception.read().decode("utf-8"))
                self.assertEqual(payload["error"], "invalid_password")
            finally:
                server.shutdown()
                thread.join(timeout=2)
                server.server_close()

    def test_miniapp_mobile_path_requires_session_auth(self) -> None:
        with mock.patch.dict(os.environ, {"INNER_WORLD_MOBILE_PASSWORD": "mobile-pass"}, clear=False):
            server, thread, base_url = self._start_test_mobile_miniapp_server()
            try:
                with self.assertRaises(urllib_error.HTTPError) as error_context:
                    urllib_request.urlopen(f"{base_url}/mobile")
                self.assertEqual(error_context.exception.code, 401)
                payload = json.loads(error_context.exception.read().decode("utf-8"))
                self.assertEqual(payload["error"], "auth_required")
            finally:
                server.shutdown()
                thread.join(timeout=2)
                server.server_close()

    def test_miniapp_mobile_session_login_sets_cookie_and_serves_manifest(self) -> None:
        with mock.patch.dict(os.environ, {"INNER_WORLD_MOBILE_PASSWORD": "mobile-pass"}, clear=False):
            server, thread, base_url = self._start_test_mobile_miniapp_server()
            try:
                cookie_jar = cookiejar.CookieJar()
                opener = urllib_request.build_opener(urllib_request.HTTPCookieProcessor(cookie_jar))
                request = urllib_request.Request(
                    f"{base_url}/api/mobile/session",
                    data=json.dumps({"password": "mobile-pass"}).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with opener.open(request) as response:
                    self.assertEqual(response.status, 200)
                    payload = json.loads(response.read().decode("utf-8"))
                    self.assertTrue(payload["authenticated"])
                    set_cookie_headers = response.headers.get_all("Set-Cookie") or []
                self.assertTrue(any("inner_world_mobile_session=" in header for header in set_cookie_headers))
                self.assertTrue(any(cookie.name == "inner_world_mobile_session" for cookie in cookie_jar))

                with opener.open(f"{base_url}/manifest.webmanifest") as response:
                    self.assertEqual(response.status, 200)
                    manifest = json.loads(response.read().decode("utf-8"))
                self.assertEqual(manifest["name"], "Inner World Mobile")

                with opener.open(f"{base_url}/mobile") as response:
                    self.assertEqual(response.status, 200)
                    body = response.read().decode("utf-8")
                self.assertIn("mobile", body)
            finally:
                server.shutdown()
                thread.join(timeout=2)
                server.server_close()

    def test_miniapp_mobile_logout_clears_cookie(self) -> None:
        with mock.patch.dict(os.environ, {"INNER_WORLD_MOBILE_PASSWORD": "mobile-pass"}, clear=False):
            server, thread, base_url = self._start_test_mobile_miniapp_server()
            try:
                cookie_jar = cookiejar.CookieJar()
                opener = urllib_request.build_opener(urllib_request.HTTPCookieProcessor(cookie_jar))
                login_request = urllib_request.Request(
                    f"{base_url}/api/mobile/session",
                    data=json.dumps({"password": "mobile-pass"}).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with opener.open(login_request) as response:
                    self.assertEqual(response.status, 200)
                self.assertTrue(any(cookie.name == "inner_world_mobile_session" for cookie in cookie_jar))

                logout_request = urllib_request.Request(
                    f"{base_url}/api/mobile/session/logout",
                    data=b"{}",
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with opener.open(logout_request) as response:
                    self.assertEqual(response.status, 200)
                    payload = json.loads(response.read().decode("utf-8"))
                    set_cookie_headers = response.headers.get_all("Set-Cookie") or []
                self.assertEqual(payload["authenticated"], False)
                self.assertTrue(any("Max-Age=0" in header for header in set_cookie_headers))

                with self.assertRaises(urllib_error.HTTPError) as error_context:
                    opener.open(f"{base_url}/mobile")
                self.assertEqual(error_context.exception.code, 401)
            finally:
                server.shutdown()
                thread.join(timeout=2)
                server.server_close()

    def test_miniapp_mobile_prefix_does_not_gate_unrelated_path(self) -> None:
        with mock.patch.dict(os.environ, {"INNER_WORLD_MOBILE_PASSWORD": "mobile-pass"}, clear=False):
            server, thread, base_url = self._start_test_mobile_miniapp_server()
            try:
                with urllib_request.urlopen(f"{base_url}/mobile.css") as response:
                    self.assertEqual(response.status, 200)
                    body = response.read().decode("utf-8")
                self.assertIn("./feed-ui-enhancement.css", body)
            finally:
                server.shutdown()
                thread.join(timeout=2)
                server.server_close()

    def test_build_openclaw_miniapp_tool_writes_feed_ui_enhancement_assets(self) -> None:
        output_dir = self.root / "bundle-tool-output"
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "build_inner_world_openclaw_miniapp.py"),
                "--app-id",
                "inner-world-tool-test",
                "--api-base-url",
                "/apps/api/inner-world-tool-test",
                "--output-dir",
                str(output_dir),
            ],
            cwd=str(REPO_ROOT),
            check=True,
            capture_output=True,
            text=True,
        )
        payload = json.loads(result.stdout)
        self.assertEqual(payload["app_id"], "inner-world-tool-test")
        self.assertTrue((output_dir / "feed-ui-enhancement.css").exists())
        self.assertTrue((output_dir / "feed-ui-enhancement.js").exists())
        index_html = (output_dir / "index.html").read_text(encoding="utf-8")
        self.assertIn("./feed-ui-enhancement.css", index_html)
        self.assertIn("./feed-ui-enhancement.js", index_html)

    def test_reanalysis_does_not_mutate_raw_events(self) -> None:
        session_start(
            self.root,
            type("Args", (), {"session_id": "session-idempotent", "title": "Idempotence", "participants": "user,agent", "source_type": "live_session", "domains": ""})(),
        )
        session_append(
            self.root,
            type("Args", (), {"session_id": "session-idempotent", "actor": "user", "kind": "request", "content": "Keep raw truth stable.", "attachments": "", "tags": "", "source_ref": None})(),
        )
        raw_before = session_events_path(self.root, "session-idempotent").read_text(encoding="utf-8")
        session_close(
            self.root,
            type("Args", (), {"session_id": "session-idempotent", "task_id": None, "request": None, "task_type": None})(),
        )
        session_close(
            self.root,
            type("Args", (), {"session_id": "session-idempotent", "task_id": None, "request": None, "task_type": None})(),
        )
        raw_after = session_events_path(self.root, "session-idempotent").read_text(encoding="utf-8")
        self.assertEqual(raw_before, raw_after)

    def test_context_bubbles_persist_and_runtime_reports_count(self) -> None:
        source_a = self.root / "bubble-a.md"
        source_b = self.root / "bubble-b.md"
        source_a.write_text(
            "The system should feel like a private cognitive layer with local sovereignty and quiet review.",
            encoding="utf-8",
        )
        source_b.write_text(
            "A private cognitive layer should stay local, preserve sovereignty, and avoid generic flattening.",
            encoding="utf-8",
        )
        seed_sources(self.root, source_a)
        seed_sources(self.root, source_b)

        derive_result = derive_graph(self.root, ["research", "product_design"])

        self.assertIn("bubble_count", derive_result)
        self.assertGreaterEqual(derive_result["bubble_count"], 1)
        self.assertTrue((self.root / "product" / "inner_world_v1" / "data" / "context_bubbles.jsonl").exists())
        self.assertTrue((self.root / "product" / "inner_world_v1" / "data" / "bubble_memberships.jsonl").exists())
        self.assertTrue((self.root / "product" / "inner_world_v1" / "data" / "bubble_edges.jsonl").exists())
        self.assertTrue((self.root / "product" / "inner_world_v1" / "data" / "bubble_transitions.jsonl").exists())

        runtime = get_runtime_overview(self.root)
        self.assertIn("context_bubbles", runtime["counts"])
        self.assertGreaterEqual(runtime["counts"]["context_bubbles"], 1)

        exported = export_state(self.root)
        self.assertIn("context_bubbles", exported)
        self.assertIn("bubble_memberships", exported)
        self.assertIn("bubble_edges", exported)
        self.assertIn("bubble_transitions", exported)

    def test_context_bubbles_reinforce_same_primitive_across_sources(self) -> None:
        source_a = self.root / "private-a.txt"
        source_b = self.root / "private-b.txt"
        source_a.write_text(
            "This product should become a private cognitive layer with local sovereignty and quiet review.",
            encoding="utf-8",
        )
        source_b.write_text(
            "A private cognitive layer should preserve local sovereignty instead of becoming generic SaaS.",
            encoding="utf-8",
        )
        seed_sources(self.root, source_a)
        seed_sources(self.root, source_b)

        derive_graph(self.root, ["research"])
        bubbles = load_context_bubbles(self.root)
        transitions = load_bubble_transitions(self.root)

        private_bubbles = [row for row in bubbles if "private cognitive layer" in row["label"].lower()]
        self.assertEqual(len(private_bubbles), 1)
        bubble = private_bubbles[0]
        self.assertGreaterEqual(len(bubble["source_refs"]), 2)
        self.assertIn("private_cognitive_layer", bubble["dominant_primitives"])
        self.assertTrue(any(row["action"] == "reinforce" and row["bubble_id"] == bubble["bubble_id"] for row in transitions))

    def test_context_bubble_keeps_direction_and_tension_together(self) -> None:
        source = self.root / "bubble-tension.txt"
        source.write_text(
            (
                "The private cognitive layer should stay local and private, "
                "but we need structure without flattening the signal."
            ),
            encoding="utf-8",
        )
        seed_sources(self.root, source)

        derive_graph(self.root, ["research"])
        bubbles = load_context_bubbles(self.root)
        memberships = load_bubble_memberships(self.root)

        self.assertGreaterEqual(len(bubbles), 1)
        target = next(row for row in bubbles if "private cognitive layer" in row["label"].lower())
        self.assertTrue(target["active_tensions"])
        roles = [row["role"] for row in memberships if row["bubble_id"] == target["bubble_id"]]
        self.assertIn("direction", roles)
        self.assertIn("tension", roles)

    def test_context_bubbles_create_contradiction_edges_for_distinct_pressures(self) -> None:
        source_a = self.root / "private-pressure.txt"
        source_b = self.root / "shared-pressure.txt"
        source_a.write_text(
            "The private cognitive layer should stay local, private, quiet, and manual.",
            encoding="utf-8",
        )
        source_b.write_text(
            "The shared collaborative layer should expand broadly, stay public, and explore wider distribution.",
            encoding="utf-8",
        )
        seed_sources(self.root, source_a)
        seed_sources(self.root, source_b)

        derive_graph(self.root, ["research"])
        edges = load_bubble_edges(self.root)

        self.assertTrue(any(edge["kind"] == "contradicts" for edge in edges))

    def test_context_bubbles_ignore_low_signal_seed_candidates(self) -> None:
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="shared_primitive-junk",
                    kind="shared_primitive",
                    label="Yes",
                    summary="A low-signal conversational fragment.",
                    source_ref="junk.txt",
                    chunk_id="chunk-junk",
                    confidence=0.93,
                    attributes={
                        "primitive_key": "yes",
                        "family": "emergent_pattern",
                        "tokens": ["yes"],
                        "source_ref": "junk.txt",
                    },
                ),
                self._meta_row(
                    meta_id="shared_primitive-private",
                    kind="shared_primitive",
                    label="Private Cognitive Layer",
                    summary="The system is a private cognitive layer, not generic SaaS.",
                    source_ref="signal.txt",
                    chunk_id="chunk-signal",
                    confidence=0.91,
                    attributes={
                        "primitive_key": "private_cognitive_layer",
                        "family": "axioms",
                        "tokens": ["private", "cognitive", "layer", "sovereignty"],
                        "source_ref": "signal.txt",
                    },
                ),
            ]
        )

        build_context_bubbles(self.root)
        bubbles = load_context_bubbles(self.root)

        self.assertEqual(len(bubbles), 1)
        self.assertEqual(bubbles[0]["label"], "Private Cognitive Layer")

    def test_context_bubbles_merge_duplicate_labels_when_pressure_matches(self) -> None:
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="shared_primitive-bridge-a",
                    kind="shared_primitive",
                    label="Mechanism Bridge",
                    summary="The system needs a mechanism bridge between raw capture and judgment.",
                    source_ref="bridge-a.txt",
                    chunk_id="chunk-bridge-a",
                    confidence=0.84,
                    attributes={
                        "primitive_key": "mechanism_bridge_capture",
                        "family": "heuristics",
                        "tokens": ["mechanism", "bridge", "capture", "judgment"],
                        "source_ref": "bridge-a.txt",
                    },
                ),
                self._meta_row(
                    meta_id="shared_primitive-bridge-b",
                    kind="shared_primitive",
                    label="Mechanism Bridge",
                    summary="A mechanism bridge should connect local routing to final synthesis.",
                    source_ref="bridge-b.txt",
                    chunk_id="chunk-bridge-b",
                    confidence=0.82,
                    attributes={
                        "primitive_key": "mechanism_bridge_routing",
                        "family": "workflow_patterns",
                        "tokens": ["mechanism", "bridge", "routing", "synthesis"],
                        "source_ref": "bridge-b.txt",
                    },
                ),
            ]
        )

        build_context_bubbles(self.root)
        bubbles = [row for row in load_context_bubbles(self.root) if row["label"] == "Mechanism Bridge"]

        self.assertEqual(len(bubbles), 1)
        self.assertEqual(bubbles[0]["support_count"], 2)
        self.assertEqual(len(bubbles[0]["source_refs"]), 2)

    def test_context_bubbles_do_not_create_edges_from_single_token_overlap(self) -> None:
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="shared_primitive-private",
                    kind="shared_primitive",
                    label="Private Cognitive Layer",
                    summary="The system is a private cognitive layer with local sovereignty.",
                    source_ref="private.txt",
                    chunk_id="chunk-private",
                    confidence=0.9,
                    attributes={
                        "primitive_key": "private_cognitive_layer",
                        "family": "axioms",
                        "tokens": ["private", "cognitive", "layer", "sovereignty"],
                        "source_ref": "private.txt",
                    },
                ),
                self._meta_row(
                    meta_id="shared_primitive-abstraction",
                    kind="shared_primitive",
                    label="Abstraction Layer General",
                    summary="The abstraction layer generalizes routing into a broader model.",
                    source_ref="abstraction.txt",
                    chunk_id="chunk-abstraction",
                    confidence=0.88,
                    attributes={
                        "primitive_key": "abstraction_layer_general",
                        "family": "modeling",
                        "tokens": ["abstraction", "layer", "general", "model"],
                        "source_ref": "abstraction.txt",
                    },
                ),
            ]
        )

        build_context_bubbles(self.root)
        edges = load_bubble_edges(self.root)

        self.assertEqual(edges, [])

    def test_context_bubbles_ignore_generic_tokens_that_would_create_dense_edge_graph(self) -> None:
        rows = []
        for index, unique in enumerate(["vault", "routing", "judgment", "feedback", "archive", "ranking"], start=1):
            rows.append(
                self._meta_row(
                    meta_id=f"shared_primitive-generic-{index}",
                    kind="shared_primitive",
                    label=f"Generic Layer {index}",
                    summary=f"The system layer should center {unique} while preserving local context.",
                    source_ref=f"generic-{index}.txt",
                    chunk_id=f"chunk-generic-{index}",
                    confidence=0.86,
                    attributes={
                        "primitive_key": f"generic_layer_{index}",
                        "family": "modeling",
                        "tokens": ["system", "layer", unique],
                        "source_ref": f"generic-{index}.txt",
                    },
                )
            )
        self._write_meta_rows(rows)

        build_context_bubbles(self.root)
        edges = load_bubble_edges(self.root)

        self.assertEqual(edges, [])

    def test_detect_patterns_ignores_procedural_scaffolding(self) -> None:
        patterns = _detect_patterns(
            (
                "Interprets the idea. Proposes structure. Exposes tensions. "
                "Then the system loops through another example."
            ),
            [],
        )

        self.assertEqual(patterns, [])

    def test_context_bubbles_drop_single_source_fallback_only_states(self) -> None:
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="signal-question",
                    kind="signal_frame",
                    label="- what does this change in the larger system?",
                    summary="raw_signal -> tension -> question -> reviewable_shape",
                    source_ref="single-source.md",
                    chunk_id="chunk-question",
                    confidence=0.72,
                    attributes={
                        "tokens": ["change", "larger", "confirm", "extend", "contradict"],
                        "source_ref": "single-source.md",
                    },
                ),
                self._meta_row(
                    meta_id="interpretation-surface",
                    kind="interpretation",
                    label="surface_reading",
                    summary="- what does this change in the larger system?",
                    source_ref="single-source.md",
                    chunk_id="chunk-question",
                    confidence=0.74,
                    attributes={
                        "tokens": ["change", "larger"],
                        "source_ref": "single-source.md",
                    },
                ),
                self._meta_row(
                    meta_id="interpretation-process",
                    kind="interpretation",
                    label="process_reading",
                    summary="The note is really about the process move from tension to question.",
                    source_ref="single-source.md",
                    chunk_id="chunk-question",
                    confidence=0.69,
                    attributes={
                        "tokens": ["note", "process", "move", "tension", "question"],
                        "source_ref": "single-source.md",
                    },
                ),
                self._meta_row(
                    meta_id="theme-question",
                    kind="theme",
                    label="Change Larger",
                    summary="A recurring thematic cluster around change larger.",
                    source_ref="single-source.md",
                    chunk_id="chunk-question",
                    confidence=0.62,
                    attributes={
                        "tokens": ["change", "larger", "confirm"],
                        "source_ref": "single-source.md",
                    },
                ),
            ]
        )

        build_context_bubbles(self.root)
        bubbles = load_context_bubbles(self.root)

        self.assertEqual(bubbles, [])

    def test_batch_and_feed_carry_primary_bubble_fields(self) -> None:
        source_a = self.root / "bubble-feed-a.txt"
        source_b = self.root / "bubble-feed-b.txt"
        source_a.write_text(
            "A private cognitive layer should stay local and protect signal fidelity.",
            encoding="utf-8",
        )
        source_b.write_text(
            "This private cognitive layer should avoid generic flattening and keep review before commit.",
            encoding="utf-8",
        )
        seed_sources(self.root, source_a)
        seed_sources(self.root, source_b)

        derive_graph(self.root, ["research"])
        batch = generate_daily_batch(self.root, limit=3, domain_overlays=["research"])
        feed = build_thought_feed(self.root, limit=3, domain_overlays=["research"], regenerate_batch=False)

        self.assertGreaterEqual(batch["count"], 1)
        self.assertTrue(all("primary_bubble_id" in row for row in batch["insights"]))
        self.assertTrue(any(row["primary_bubble_id"] for row in batch["insights"]))
        self.assertGreaterEqual(feed["count"], 1)
        self.assertIn("primary_bubble_id", feed["thoughts"][0])
        self.assertIn("primary_bubble_label", feed["thoughts"][0])
        self.assertIn("related_bubble_ids", feed["thoughts"][0])

    def test_feed_diversifies_selection_and_exposes_diagnostics(self) -> None:
        packets_path = self.root / "product" / "inner_world_v1" / "data" / "thought_packets.jsonl"
        packets_path.parent.mkdir(parents=True, exist_ok=True)
        base_packet = {
            "insight_id": "insight-base",
            "article_title": "Deep Read",
            "article_markdown": "## The central tension\n\nA.\n\n## What to do with it\n\nB.",
            "status": "active",
            "review_status": "ready_for_review",
            "evidence_status": "grounded",
            "relevance_score": 0.91,
            "novelty_score": 0.88,
            "source_item_ids": [],
            "meta_refs": [],
            "shared_primitive_key": "pattern",
            "shared_primitive_label": "Pattern",
            "what_changed": "The feed needs a better mix.",
            "why_it_matters_now": "Repeated cards make the feed feel flat.",
            "next_action": "Diversify selection.",
            "reasoning_pipeline": "thought_pipeline",
            "related_bubble_ids": [],
            "feedback_state": "pending",
            "feedback_controls": ["relevant", "dismiss", "revisit_later"],
            "article_sections": [],
            "article_profile": "",
            "article_module_order": [],
            "article_config_snapshot": {},
        }
        packets = [
            base_packet
            | {
                "packet_id": "packet-a",
                "thought_id": "thought-a",
                "title": "Highest Signal Alpha",
                "short_text": "Alpha",
                "confidence_score": 0.98,
                "source_refs": ["source://repeat"],
                "primary_bubble_id": "bubble-repeat",
                "primary_bubble_label": "Repeat",
            },
            base_packet
            | {
                "packet_id": "packet-b",
                "thought_id": "thought-b",
                "title": "Highest Signal Beta",
                "short_text": "Beta",
                "confidence_score": 0.97,
                "source_refs": ["source://repeat"],
                "primary_bubble_id": "bubble-repeat",
                "primary_bubble_label": "Repeat",
            },
            base_packet
            | {
                "packet_id": "packet-c",
                "thought_id": "thought-c",
                "title": "Different Source Cedar",
                "short_text": "Cedar",
                "confidence_score": 0.96,
                "source_refs": ["source://c"],
                "primary_bubble_id": "bubble-c",
                "primary_bubble_label": "Bubble C",
            },
            base_packet
            | {
                "packet_id": "packet-d",
                "thought_id": "thought-d",
                "title": "Different Source Delta",
                "short_text": "Delta",
                "confidence_score": 0.95,
                "source_refs": ["source://d"],
                "primary_bubble_id": "bubble-d",
                "primary_bubble_label": "Bubble D",
            },
        ]
        write_jsonl(packets_path, packets)

        feed = build_thought_feed(self.root, limit=3, domain_overlays=["research"], regenerate_batch=False)

        self.assertEqual(feed["count"], 3)
        thought_ids = [row["thought_id"] for row in feed["thoughts"]]
        self.assertEqual(thought_ids[0], "thought-a")
        self.assertIn("thought-c", thought_ids)
        self.assertIn("thought-d", thought_ids)
        self.assertNotIn("thought-b", thought_ids)
        self.assertIn("diagnostics", feed)
        self.assertEqual(feed["diagnostics"]["selection"]["candidate_pool_count"], 4)
        self.assertEqual(feed["diagnostics"]["selection"]["selected_count"], 3)
        self.assertEqual(feed["diagnostics"]["selection"]["unique_primary_source_count"], 3)
        self.assertEqual(feed["diagnostics"]["selection"]["unique_primary_bubble_count"], 3)

    def test_feed_does_not_rebuild_thread_context_lookups_per_candidate(self) -> None:
        packets_path = self.root / "product" / "inner_world_v1" / "data" / "thought_packets.jsonl"
        packets_path.parent.mkdir(parents=True, exist_ok=True)
        base_packet = {
            "insight_id": "insight-base",
            "article_title": "Deep Read",
            "article_markdown": "## The central tension\n\nA.\n\n## What to do with it\n\nB.",
            "status": "active",
            "review_status": "ready_for_review",
            "evidence_status": "grounded",
            "relevance_score": 0.91,
            "novelty_score": 0.88,
            "source_item_ids": [],
            "meta_refs": [],
            "shared_primitive_key": "pattern",
            "shared_primitive_label": "Pattern",
            "what_changed": "The feed should avoid repeated heavyweight reloads.",
            "why_it_matters_now": "Repeated index loads can pin the server CPU.",
            "next_action": "Reuse shared lookups while building the feed.",
            "reasoning_pipeline": "thought_pipeline",
            "related_bubble_ids": [],
            "feedback_state": "pending",
            "feedback_controls": ["relevant", "dismiss", "revisit_later"],
            "article_sections": [],
            "article_profile": "",
            "article_module_order": [],
            "article_config_snapshot": {},
        }
        packets = [
            base_packet
            | {
                "packet_id": "packet-a",
                "thought_id": "thought-a",
                "title": "Highest Signal Alpha",
                "short_text": "Alpha",
                "confidence_score": 0.98,
                "source_refs": ["source://repeat"],
                "primary_bubble_id": "bubble-repeat",
                "primary_bubble_label": "Repeat",
            },
            base_packet
            | {
                "packet_id": "packet-b",
                "thought_id": "thought-b",
                "title": "Highest Signal Beta",
                "short_text": "Beta",
                "confidence_score": 0.97,
                "source_refs": ["source://repeat"],
                "primary_bubble_id": "bubble-repeat",
                "primary_bubble_label": "Repeat",
            },
            base_packet
            | {
                "packet_id": "packet-c",
                "thought_id": "thought-c",
                "title": "Different Source Cedar",
                "short_text": "Cedar",
                "confidence_score": 0.96,
                "source_refs": ["source://c"],
                "primary_bubble_id": "bubble-c",
                "primary_bubble_label": "Bubble C",
            },
            base_packet
            | {
                "packet_id": "packet-d",
                "thought_id": "thought-d",
                "title": "Different Source Delta",
                "short_text": "Delta",
                "confidence_score": 0.95,
                "source_refs": ["source://d"],
                "primary_bubble_id": "bubble-d",
                "primary_bubble_label": "Bubble D",
            },
        ]
        write_jsonl(packets_path, packets)

        load_counts = {"thought_packets": 0, "meta_records": 0, "chunk_index": 0}
        import conversation_os.thread_context as thread_context
        original_load_thought_packets = thread_context.load_thought_packets
        original_load_meta_records = thread_context.load_meta_records
        original_load_chunk_index = thread_context.load_chunk_index

        def counted_thought_packets(root: Path) -> list[dict]:
            load_counts["thought_packets"] += 1
            return original_load_thought_packets(root)

        def counted_meta_records(root: Path, kinds=None) -> list[dict]:
            load_counts["meta_records"] += 1
            return original_load_meta_records(root, kinds)

        def counted_chunk_index(root: Path) -> list[dict]:
            load_counts["chunk_index"] += 1
            return original_load_chunk_index(root)

        with mock.patch.object(thread_context, "load_thought_packets", side_effect=counted_thought_packets), mock.patch.object(
            thread_context, "load_meta_records", side_effect=counted_meta_records
        ), mock.patch.object(thread_context, "load_chunk_index", side_effect=counted_chunk_index):
            feed = build_thought_feed(self.root, limit=4, domain_overlays=["research"], regenerate_batch=False)

        self.assertEqual(feed["diagnostics"]["selection"]["candidate_pool_count"], 4)
        self.assertLessEqual(load_counts["thought_packets"], 1)
        self.assertLessEqual(load_counts["meta_records"], 1)
        self.assertLessEqual(load_counts["chunk_index"], 1)

    def test_feed_avoids_full_substrate_loads_for_context_enrichment(self) -> None:
        ingest_text_content(
            self.root,
            title="Evidence Source",
            content="Direct evidence to cite in the feed and keep attached to the thought.",
            source_ref="source://evidence",
            source_type="note",
            source_family="test",
        )
        evidence_item = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "source://evidence")

        meta_dir = meta_layer_dir(self.root)
        meta_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(
            meta_dir / META_LAYER_FILES["question"],
            [
                {
                    "meta_id": "question-feed-targeted",
                    "kind": "question",
                    "label": "Open question",
                    "summary": "What is the concrete next move?",
                    "status": "provisional",
                    "confidence": 0.7,
                    "source_refs": ["source://evidence"],
                    "chunk_ids": [evidence_item["source_item_id"]],
                    "evidence": ["Direct evidence to cite in the feed."],
                    "attributes": {},
                }
            ],
        )

        packets_path = self.root / "product" / "inner_world_v1" / "data" / "thought_packets.jsonl"
        packets_path.parent.mkdir(parents=True, exist_ok=True)
        write_jsonl(
            packets_path,
            [
                {
                    "packet_id": "packet-targeted",
                    "thought_id": "thought-targeted",
                    "insight_id": "insight-targeted",
                    "title": "Targeted Feed Context",
                    "short_text": "The feed should resolve only the referenced substrate rows.",
                    "article_title": "Targeted Feed Context",
                    "article_markdown": "## Evidence\n\nDirect evidence to cite.\n\n## Next\n\nUse only the needed rows.",
                    "article_sections": [],
                    "article_profile": "",
                    "article_module_order": [],
                    "article_config_snapshot": {},
                    "status": "active",
                    "review_status": "ready_for_review",
                    "evidence_status": "grounded",
                    "relevance_score": 0.92,
                    "novelty_score": 0.82,
                    "confidence_score": 0.95,
                    "source_refs": ["source://evidence"],
                    "source_item_ids": [evidence_item["source_item_id"]],
                    "meta_refs": ["question-feed-targeted"],
                    "shared_primitive_key": "pattern",
                    "shared_primitive_label": "Pattern",
                    "what_changed": "Feed context lookup is now targeted.",
                    "why_it_matters_now": "The server should not load the full substrate for one card.",
                    "next_action": "Verify the feed context remains evidence-backed.",
                    "reasoning_pipeline": "thought_pipeline",
                    "related_bubble_ids": [],
                    "feedback_state": "pending",
                    "feedback_controls": ["relevant", "dismiss", "revisit_later"],
                    "primary_bubble_id": "bubble-targeted",
                    "primary_bubble_label": "Targeted Bubble",
                }
            ],
        )

        import conversation_os.product_inner_world as product_inner_world

        with mock.patch.object(
            product_inner_world,
            "load_meta_records",
            side_effect=AssertionError("feed should not load the full meta substrate"),
        ), mock.patch.object(
            product_inner_world,
            "_chunk_lookup",
            side_effect=AssertionError("feed should not load the full chunk substrate"),
        ):
            feed = build_thought_feed(self.root, limit=1, domain_overlays=["research"], regenerate_batch=False)

        self.assertEqual(feed["count"], 1)
        thought = feed["thoughts"][0]
        snippets = thought["post_context"]["source_snippets"]
        self.assertEqual(snippets[0]["source_item_id"], evidence_item["source_item_id"])
        supporting_meta_ids = [row["meta_id"] for row in thought["post_context"]["supporting_meta"]]
        self.assertEqual(supporting_meta_ids, ["question-feed-targeted"])

    def test_feed_classifies_post_formats_from_packet_characteristics(self) -> None:
        ingest_text_content(
            self.root,
            title="Evidence Source",
            content="A grounded claim should carry direct evidence and stay inspectable.",
            source_ref="source://evidence",
            source_type="note",
            source_family="test",
        )
        evidence_item = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "source://evidence")

        meta_dir = meta_layer_dir(self.root)
        meta_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(
            meta_dir / META_LAYER_FILES["question"],
            [
                {
                    "meta_id": "meta-question-1",
                    "kind": "question",
                    "label": "Open question",
                    "summary": "What does this tension actually want from the user?",
                    "status": "provisional",
                    "confidence": 0.7,
                    "source_refs": ["source://question"],
                    "chunk_ids": [],
                    "evidence": [],
                    "attributes": {},
                }
            ],
        )
        write_jsonl(
            meta_dir / META_LAYER_FILES["tension"],
            [
                {
                    "meta_id": "meta-tension-1",
                    "kind": "tension",
                    "label": "Live tension",
                    "summary": "The idea is unresolved enough to invite a response.",
                    "status": "provisional",
                    "confidence": 0.72,
                    "source_refs": ["source://question"],
                    "chunk_ids": [],
                    "evidence": [],
                    "attributes": {},
                }
            ],
        )

        packets_path = self.root / "product" / "inner_world_v1" / "data" / "thought_packets.jsonl"
        base_packet = {
            "insight_id": "insight-base",
            "article_title": "Deep Read",
            "article_markdown": "## The central tension\n\nA.\n\n## What to do with it\n\nB.",
            "status": "active",
            "review_status": "ready_for_review",
            "relevance_score": 0.8,
            "novelty_score": 0.75,
            "source_refs": [],
            "source_item_ids": [],
            "meta_refs": [],
            "shared_primitive_key": "pattern",
            "shared_primitive_label": "Pattern",
            "what_changed": "The format should match the packet.",
            "why_it_matters_now": "Format quality is part of feed quality.",
            "next_action": "Classify the post well.",
            "reasoning_pipeline": "thought_pipeline",
            "primary_bubble_id": "",
            "primary_bubble_label": "",
            "related_bubble_ids": [],
            "feedback_state": "pending",
            "feedback_controls": ["relevant", "dismiss", "revisit_later"],
            "article_profile": "",
            "article_module_order": [],
            "article_config_snapshot": {},
            "confidence_score": 0.9,
        }
        packets = [
            base_packet
            | {
                "packet_id": "packet-source",
                "thought_id": "thought-source",
                "title": "Grounded Evidence Post",
                "short_text": "This one should stay tied to evidence.",
                "evidence_status": "grounded",
                "source_refs": ["source://evidence"],
                "source_item_ids": [evidence_item["source_item_id"]],
                "article_sections": [],
            },
            base_packet
            | {
                "packet_id": "packet-question",
                "thought_id": "thought-question",
                "title": "Question Forward Post",
                "short_text": "This one should invite response.",
                "evidence_status": "provisional",
                "meta_refs": ["meta-question-1", "meta-tension-1"],
                "article_sections": [],
            },
            base_packet
            | {
                "packet_id": "packet-essay",
                "thought_id": "thought-essay",
                "title": "Essay Post",
                "short_text": "This one has enough structure to read as a mini essay.",
                "evidence_status": "provisional",
                "article_sections": [{"heading": "A"}, {"heading": "B"}],
            },
            base_packet
            | {
                "packet_id": "packet-sharp",
                "thought_id": "thought-sharp",
                "title": "Sharp Post",
                "short_text": "This one should stay compact.",
                "evidence_status": "provisional",
                "article_sections": [],
            },
        ]
        write_jsonl(packets_path, packets)

        feed = build_thought_feed(self.root, limit=4, domain_overlays=["research"], regenerate_batch=False)

        posts = {row["thought_id"]: row for row in feed["thoughts"]}
        self.assertEqual(posts["thought-source"]["post_format"], "source_backed_card")
        self.assertEqual(posts["thought-question"]["post_format"], "discussion_prompt")
        self.assertEqual(posts["thought-essay"]["post_format"], "mini_essay")
        self.assertEqual(posts["thought-sharp"]["post_format"], "sharp_post")
        self.assertIn("format_reason", posts["thought-source"])
        self.assertEqual(posts["thought-source"]["format_reason"], "grounded_evidence")
        self.assertEqual(posts["thought-question"]["format_reason"], "open_question")
        self.assertEqual(posts["thought-essay"]["format_reason"], "article_structure")
        self.assertEqual(posts["thought-sharp"]["format_reason"], "default_sharp_post")
        self.assertIn("formats", feed["diagnostics"])
        self.assertEqual(feed["diagnostics"]["formats"]["counts"]["source_backed_card"], 1)
        self.assertEqual(feed["diagnostics"]["formats"]["counts"]["discussion_prompt"], 1)
        self.assertEqual(feed["diagnostics"]["formats"]["counts"]["mini_essay"], 1)
        self.assertEqual(feed["diagnostics"]["formats"]["counts"]["sharp_post"], 1)

    def test_feed_interactions_build_taste_profile(self) -> None:
        ingest_text_content(
            self.root,
            title="Taste Source",
            content="Evidence-backed posts should be inspectable and worth returning to.",
            source_ref="source://taste",
            source_type="note",
            source_family="test",
        )
        source_item = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "source://taste")

        packets_path = self.root / "product" / "inner_world_v1" / "data" / "thought_packets.jsonl"
        write_jsonl(
            packets_path,
            [
                {
                    "packet_id": "packet-taste",
                    "thought_id": "thought-taste",
                    "insight_id": "insight-taste",
                    "title": "Taste Post",
                    "short_text": "This post should be learned as a preferred source-backed format.",
                    "article_title": "Taste Deep Read",
                    "article_markdown": "## The central tension\n\nA.\n\n## What to do with it\n\nB.",
                    "status": "active",
                    "review_status": "ready_for_review",
                    "evidence_status": "grounded",
                    "confidence_score": 0.92,
                    "relevance_score": 0.82,
                    "novelty_score": 0.71,
                    "source_refs": ["source://taste"],
                    "source_item_ids": [source_item["source_item_id"]],
                    "meta_refs": [],
                    "shared_primitive_key": "pattern",
                    "shared_primitive_label": "Pattern",
                    "what_changed": "Behavioral learning is now tracked.",
                    "why_it_matters_now": "The backend should learn from actual interaction.",
                    "next_action": "Inspect, discuss, and save what keeps holding attention.",
                    "reasoning_pipeline": "thought_pipeline",
                    "primary_bubble_id": "",
                    "primary_bubble_label": "",
                    "related_bubble_ids": [],
                    "feedback_state": "pending",
                    "feedback_controls": ["relevant", "dismiss", "revisit_later"],
                    "article_sections": [],
                    "article_profile": "",
                    "article_module_order": [],
                    "article_config_snapshot": {},
                }
            ],
        )

        feed = build_thought_feed(self.root, limit=1, domain_overlays=["research"], regenerate_batch=False)
        thought = feed["thoughts"][0]
        self.assertEqual(thought["post_format"], "source_backed_card")

        get_thought_detail(self.root, thought["thought_id"], ["research"])
        chat_result = chat_with_thought(
            self.root,
            thought["thought_id"],
            "Why does this one hold more weight?",
            domain_overlays=["research"],
        )
        save_thread(self.root, chat_result["thread"]["thread_id"], ["research"])
        record_feedback(self.root, thought["insight_id"], "saved")

        learning_events = read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "feed_learning_events.jsonl")
        event_types = [row["event_type"] for row in learning_events]
        self.assertIn("detail_open", event_types)
        self.assertIn("thought_chat", event_types)
        self.assertIn("thread_saved", event_types)
        self.assertIn("explicit_feedback", event_types)

        taste_profile = read_json(self.root / "product" / "inner_world_v1" / "data" / "feed_taste_profile.json")
        self.assertEqual(taste_profile["preferred_formats"][0], "source_backed_card")
        self.assertEqual(taste_profile["signal_counts"]["detail_open"], 1)
        self.assertEqual(taste_profile["signal_counts"]["thought_chat"], 1)
        self.assertEqual(taste_profile["signal_counts"]["thread_saved"], 1)
        self.assertEqual(taste_profile["signal_counts"]["explicit_feedback"], 1)
        self.assertGreater(taste_profile["format_scores"]["source_backed_card"], 0)

        refreshed_feed = build_thought_feed(self.root, limit=1, domain_overlays=["research"], regenerate_batch=False)
        self.assertIn("taste_profile", refreshed_feed["diagnostics"])
        self.assertEqual(refreshed_feed["diagnostics"]["taste_profile"]["preferred_formats"][0], "source_backed_card")

    def test_feed_selection_uses_learned_taste_profile(self) -> None:
        ingest_text_content(
            self.root,
            title="Taste Bias Source",
            content="This source gives the feed direct evidence to cite.",
            source_ref="source://taste-bias",
            source_type="note",
            source_family="test",
        )
        source_item = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "source://taste-bias")

        write_json(
            self.root / "product" / "inner_world_v1" / "data" / "feed_taste_profile.json",
            {
                "updated_at": "2026-04-30T00:00:00+00:00",
                "event_count": 4,
                "signal_counts": {"explicit_feedback": 1},
                "format_counts": {"source_backed_card": 4},
                "format_scores": {"source_backed_card": 7.8, "sharp_post": 0.0},
                "preferred_formats": ["source_backed_card"],
            },
        )

        packets_path = self.root / "product" / "inner_world_v1" / "data" / "thought_packets.jsonl"
        write_jsonl(
            packets_path,
            [
                {
                    "packet_id": "packet-source-pref",
                    "thought_id": "thought-source-pref",
                    "insight_id": "insight-source-pref",
                    "title": "Evidence First",
                    "short_text": "This one should be boosted by learned taste.",
                    "article_title": "Evidence First",
                    "article_markdown": "## The central tension\n\nA.\n\n## What to do with it\n\nB.",
                    "status": "active",
                    "review_status": "ready_for_review",
                    "evidence_status": "supported",
                    "confidence_score": 0.89,
                    "relevance_score": 0.80,
                    "novelty_score": 0.70,
                    "source_refs": ["source://taste-bias"],
                    "source_item_ids": [source_item["source_item_id"]],
                    "meta_refs": [],
                    "shared_primitive_key": "pattern",
                    "shared_primitive_label": "Pattern",
                    "what_changed": "Learned taste should apply in selection.",
                    "why_it_matters_now": "Selection should reflect user preference for evidence-backed posts.",
                    "next_action": "Show the evidence-backed item first.",
                    "reasoning_pipeline": "thought_pipeline",
                    "primary_bubble_id": "",
                    "primary_bubble_label": "",
                    "related_bubble_ids": [],
                    "feedback_state": "pending",
                    "feedback_controls": ["relevant", "dismiss", "revisit_later"],
                    "article_sections": [],
                    "article_profile": "",
                    "article_module_order": [],
                    "article_config_snapshot": {},
                },
                {
                    "packet_id": "packet-sharp-pref",
                    "thought_id": "thought-sharp-pref",
                    "insight_id": "insight-sharp-pref",
                    "title": "Sharper But Not Preferred",
                    "short_text": "This one ranks slightly higher without taste bias.",
                    "article_title": "Sharper But Not Preferred",
                    "article_markdown": "## The central tension\n\nA.\n\n## What to do with it\n\nB.",
                    "status": "active",
                    "review_status": "ready_for_review",
                    "evidence_status": "supported",
                    "confidence_score": 0.93,
                    "relevance_score": 0.80,
                    "novelty_score": 0.70,
                    "source_refs": ["source://taste-bias-alt"],
                    "source_item_ids": [],
                    "meta_refs": [],
                    "shared_primitive_key": "pattern",
                    "shared_primitive_label": "Pattern",
                    "what_changed": "This should lose once taste bias is applied.",
                    "why_it_matters_now": "Taste-aware ordering should be visible.",
                    "next_action": "Do not overrule learned taste with a tiny score edge.",
                    "reasoning_pipeline": "thought_pipeline",
                    "primary_bubble_id": "",
                    "primary_bubble_label": "",
                    "related_bubble_ids": [],
                    "feedback_state": "pending",
                    "feedback_controls": ["relevant", "dismiss", "revisit_later"],
                    "article_sections": [],
                    "article_profile": "",
                    "article_module_order": [],
                    "article_config_snapshot": {},
                },
            ],
        )

        feed = build_thought_feed(self.root, limit=1, domain_overlays=["research"], regenerate_batch=False)

        self.assertEqual(feed["thoughts"][0]["thought_id"], "thought-source-pref")
        self.assertEqual(feed["thoughts"][0]["post_format"], "source_backed_card")
        self.assertIn("taste_adjusted_thought_ids", feed["diagnostics"]["selection"])
        self.assertIn("thought-source-pref", feed["diagnostics"]["selection"]["taste_adjusted_thought_ids"])
        self.assertIn("applied_preferred_formats", feed["diagnostics"]["selection"])
        self.assertIn("source_backed_card", feed["diagnostics"]["selection"]["applied_preferred_formats"])

    def test_feed_payloads_shape_from_learned_taste_profile(self) -> None:
        ingest_text_content(
            self.root,
            title="Taste Shape Source",
            content="This source gives the feed direct evidence to cite in the preview and expansion.",
            source_ref="source://taste-shape",
            source_type="note",
            source_family="test",
        )
        source_item = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "source://taste-shape")

        write_json(
            self.root / "product" / "inner_world_v1" / "data" / "feed_taste_profile.json",
            {
                "updated_at": "2026-04-30T00:00:00+00:00",
                "event_count": 4,
                "signal_counts": {
                    "thought_chat": 2,
                    "thread_saved": 1,
                    "explicit_feedback": 1,
                    "detail_open": 0,
                },
                "format_counts": {"source_backed_card": 4},
                "format_scores": {"source_backed_card": 6.0},
                "preferred_formats": ["source_backed_card"],
            },
        )

        packets_path = self.root / "product" / "inner_world_v1" / "data" / "thought_packets.jsonl"
        write_jsonl(
            packets_path,
            [
                {
                    "packet_id": "packet-shape-pref",
                    "thought_id": "thought-shape-pref",
                    "insight_id": "insight-shape-pref",
                    "title": "Evidence Should Lead",
                    "short_text": "The post should still keep the compact summary text.",
                    "article_title": "Evidence Should Lead",
                    "article_markdown": "## One\n\nA.\n\n## Two\n\nB.\n\n## Three\n\nC.",
                    "status": "active",
                    "review_status": "ready_for_review",
                    "evidence_status": "supported",
                    "confidence_score": 0.91,
                    "relevance_score": 0.81,
                    "novelty_score": 0.72,
                    "source_refs": ["source://taste-shape"],
                    "source_item_ids": [source_item["source_item_id"]],
                    "meta_refs": [],
                    "shared_primitive_key": "pattern",
                    "shared_primitive_label": "Pattern",
                    "what_changed": "The evidence should take the lead in the expansion.",
                    "why_it_matters_now": "The preview should stay compact while still surfacing evidence.",
                    "next_action": "Let the learned taste steer the expansion affordance.",
                    "reasoning_pipeline": "thought_pipeline",
                    "primary_bubble_id": "",
                    "primary_bubble_label": "",
                    "related_bubble_ids": [],
                    "feedback_state": "pending",
                    "feedback_controls": ["relevant", "dismiss", "revisit_later"],
                    "article_sections": [
                        {"heading": "One", "body": "A"},
                        {"heading": "Two", "body": "B"},
                        {"heading": "Three", "body": "C"},
                    ],
                    "article_profile": "",
                    "article_module_order": [],
                    "article_config_snapshot": {},
                }
            ],
        )

        feed = build_thought_feed(self.root, limit=1, domain_overlays=["research"], regenerate_batch=False)
        thought = feed["thoughts"][0]
        preview = thought["preview_payload"]
        expand = thought["expand_payload"]

        self.assertEqual(preview["lead_mode"], "evidence")
        self.assertIn("direct evidence to cite", preview["lead_text"])
        self.assertEqual(preview["cta_label"], "Discuss evidence")
        self.assertEqual(preview["taste_shape"]["compactness"], "depth")
        self.assertEqual(expand["opening_focus"], "evidence")
        self.assertIn("direct evidence to cite", expand["opening_text"])
        self.assertEqual(expand["recommended_interaction"], "thought_chat")
        self.assertEqual(expand["taste_shape"]["interaction_bias"], "thought_chat")
        self.assertEqual(thought["taste_diagnostics"]["lead_rule"], "preferred_format_evidence")
        self.assertEqual(thought["taste_diagnostics"]["interaction_rule"], "thought_chat_dominant")
        self.assertEqual(thought["taste_diagnostics"]["compactness_rule"], "depth_from_chat_and_save")
        self.assertTrue(thought["taste_diagnostics"]["format_preference_match"])
        self.assertIn("taste_posts", feed["diagnostics"])
        self.assertEqual(feed["diagnostics"]["taste_posts"]["thought-shape-pref"]["lead_rule"], "preferred_format_evidence")

    def test_cli_bubbles_commands_return_structured_payloads(self) -> None:
        source = self.root / "bubble-cli.txt"
        source.write_text(
            "The system should become a private cognitive layer with local sovereignty and quiet review.",
            encoding="utf-8",
        )
        seed_sources(self.root, source)
        derive_graph(self.root, ["research"])
        bubble = load_context_bubbles(self.root)[0]

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(["inner-world", "bubbles", "--limit", "5"])
        self.assertEqual(exit_code, 0)
        bubbles_payload = json.loads(stdout.getvalue())
        self.assertGreaterEqual(bubbles_payload["count"], 1)
        self.assertIn("bubbles", bubbles_payload)

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(["inner-world", "bubble", "--bubble-id", bubble["bubble_id"]])
        self.assertEqual(exit_code, 0)
        bubble_payload = json.loads(stdout.getvalue())
        self.assertEqual(bubble_payload["bubble"]["bubble_id"], bubble["bubble_id"])
        self.assertIn("memberships", bubble_payload)
        self.assertIn("edges", bubble_payload)

    def test_init_repo_bootstraps_library_tracker_config(self) -> None:
        config = load_library_tracker_config(self.root)
        self.assertIn("sources", config)
        self.assertGreaterEqual(len(config["sources"]), 4)
        source_ids = {row["source_id"] for row in config["sources"]}
        self.assertIn("chat_converter_saved_conversations", source_ids)
        self.assertIn("openclaw_memory_db", source_ids)
        self.assertTrue((self.root / "product" / "inner_world_v1" / "config" / "library_sources.json").exists())

    def test_library_sync_tracks_files_and_sqlite_rows_incrementally(self) -> None:
        corpus_dir = self.root / "imports"
        corpus_dir.mkdir(parents=True, exist_ok=True)
        chat_file = corpus_dir / "chat.md"
        chat_file.write_text("Private cognitive layer notes should preserve ambiguity.", encoding="utf-8")

        db_path = self.root / "openclaw-memory.sqlite"
        connection = sqlite3.connect(db_path)
        connection.execute("create table memory_items (id integer primary key, title text, content text)")
        connection.execute(
            "insert into memory_items (title, content) values (?, ?)",
            ("Mechanism Bridge", "Mechanism bridge routing should stay grounded in real traces."),
        )
        connection.commit()
        connection.close()

        self._write_library_config(
            {
                "sources": [
                    {
                        "source_id": "chat-files",
                        "kind": "filesystem",
                        "enabled": True,
                        "source_type": "chat_converter_conversation",
                        "source_family": "chat_converter",
                        "roots": [str(corpus_dir)],
                        "include_globs": ["*.md"],
                    },
                    {
                        "source_id": "memory-db",
                        "kind": "sqlite",
                        "enabled": True,
                        "source_type": "openclaw_memory_record",
                        "source_family": "openclaw_memory",
                        "db_paths": [str(db_path)],
                        "include_tables": ["memory_items"],
                        "text_columns": ["title", "content"],
                    },
                ]
            }
        )

        first = sync_library_sources(self.root)
        self.assertEqual(first["counts"]["new"], 2)
        self.assertEqual(first["counts"]["changed"], 0)
        self.assertEqual(first["counts"]["deleted"], 0)
        self.assertEqual(first["ingested_item_count"], 2)

        second = sync_library_sources(self.root)
        self.assertEqual(second["counts"]["new"], 0)
        self.assertEqual(second["counts"]["changed"], 0)
        self.assertEqual(second["counts"]["unchanged"], 2)
        self.assertEqual(second["ingested_item_count"], 0)

        chat_file.write_text(
            "Private cognitive layer notes should preserve ambiguity and review before commit.",
            encoding="utf-8",
        )
        connection = sqlite3.connect(db_path)
        connection.execute(
            "update memory_items set content = ? where id = 1",
            ("Mechanism bridge routing should stay grounded in real traces and tool evidence.",),
        )
        connection.commit()
        connection.close()

        third = sync_library_sources(self.root)
        self.assertEqual(third["counts"]["changed"], 2)
        self.assertEqual(third["ingested_item_count"], 2)

        registry = read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "source_registry.jsonl")
        source_refs = {row["source_ref"] for row in registry}
        self.assertIn(str(chat_file.resolve()), source_refs)
        self.assertIn(f"sqlite://{db_path.resolve()}#memory_items/1", source_refs)

    def test_library_sync_can_bound_pending_ingest_without_double_ingesting_synced_items(self) -> None:
        corpus_dir = self.root / "bounded-imports"
        corpus_dir.mkdir(parents=True, exist_ok=True)
        for idx in range(3):
            (corpus_dir / f"chat-{idx}.md").write_text(f"conversation {idx}", encoding="utf-8")
        self._write_library_config(
            {
                "sources": [
                    {
                        "source_id": "bounded-files",
                        "kind": "filesystem",
                        "enabled": True,
                        "source_type": "chat_converter_conversation",
                        "source_family": "chat_converter",
                        "roots": [str(corpus_dir)],
                        "include_globs": ["*.md"],
                    }
                ]
            }
        )

        first = sync_library_sources(self.root, portion=0.3)
        self.assertEqual(first["counts"]["new"], 3)
        self.assertEqual(first["ingested_item_count"], 1)
        self.assertEqual(first["deferred_item_count"], 2)

        state = read_json(self.root / "product" / "inner_world_v1" / "data" / "library_tracker_state.json")
        self.assertEqual(len(state["tracked_items"]), 1)

        second = sync_library_sources(self.root)
        self.assertEqual(second["counts"]["new"], 2)
        self.assertEqual(second["ingested_item_count"], 2)
        self.assertEqual(second["deferred_item_count"], 0)

        registry = read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "source_registry.jsonl")
        self.assertEqual(len(registry), 3)

    def test_library_sync_purges_deleted_sources(self) -> None:
        corpus_dir = self.root / "tracked"
        corpus_dir.mkdir(parents=True, exist_ok=True)
        source = corpus_dir / "session.md"
        source.write_text("A tracked conversation should be removed when the file disappears.", encoding="utf-8")
        self._write_library_config(
            {
                "sources": [
                    {
                        "source_id": "tracked-files",
                        "kind": "filesystem",
                        "enabled": True,
                        "source_type": "openclaw_conversation",
                        "source_family": "openclaw_conversations",
                        "roots": [str(corpus_dir)],
                        "include_globs": ["*.md"],
                    }
                ]
            }
        )

        sync_library_sources(self.root)
        self.assertTrue(
            any(row["source_ref"] == str(source.resolve()) for row in read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "source_registry.jsonl"))
        )

        source.unlink()
        result = sync_library_sources(self.root)
        self.assertEqual(result["counts"]["deleted"], 1)
        self.assertFalse(
            any(row["source_ref"] == str(source.resolve()) for row in read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "source_registry.jsonl"))
        )

    def test_cli_library_commands_return_structured_payloads(self) -> None:
        corpus_dir = self.root / "library-cli"
        corpus_dir.mkdir(parents=True, exist_ok=True)
        source = corpus_dir / "conversation.md"
        source.write_text("Progressive disclosure should metabolize raw logs into usable structure.", encoding="utf-8")
        self._write_library_config(
            {
                "sources": [
                    {
                        "source_id": "cli-files",
                        "kind": "filesystem",
                        "enabled": True,
                        "source_type": "chat_converter_conversation",
                        "source_family": "chat_converter",
                        "roots": [str(corpus_dir)],
                        "include_globs": ["*.md"],
                    }
                ]
            }
        )

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(["inner-world", "library-scan"])
        self.assertEqual(exit_code, 0)
        scan_payload = json.loads(stdout.getvalue())
        self.assertIn("counts", scan_payload)
        self.assertEqual(scan_payload["counts"]["new"], 1)

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(["inner-world", "library-sync"])
        self.assertEqual(exit_code, 0)
        sync_payload = json.loads(stdout.getvalue())
        self.assertIn("counts", sync_payload)
        self.assertEqual(sync_payload["ingested_item_count"], 1)

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(["inner-world", "library-status"])
        self.assertEqual(exit_code, 0)
        status_payload = json.loads(stdout.getvalue())
        self.assertIn("tracked_item_count", status_payload)
        self.assertEqual(status_payload["tracked_item_count"], 1)
        self.assertEqual(get_library_status(self.root)["tracked_item_count"], 1)

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(
                [
                    "inner-world",
                    "library-govern",
                    "--source-ref",
                    str(source.resolve()),
                    "--status",
                    "exclude_from_runtime",
                    "--notes",
                    "scaffold",
                ]
            )
        self.assertEqual(exit_code, 0)
        govern_payload = json.loads(stdout.getvalue())
        self.assertEqual(govern_payload["policy_record"]["governance_status"], "exclude_from_runtime")
        self.assertEqual(govern_payload["pending_rederive"]["from_stage"], "analysis_units")

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(["inner-world", "library-filter", "--statuses", "exclude_from_runtime"])
        self.assertEqual(exit_code, 0)
        filter_payload = json.loads(stdout.getvalue())
        self.assertEqual(filter_payload["count"], 1)
        self.assertEqual(filter_payload["results"][0]["source_ref"], str(source.resolve()))

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(["inner-world", "library-rederive", "--affected-only", "--dry-run"])
        self.assertEqual(exit_code, 0)
        rederive_payload = json.loads(stdout.getvalue())
        self.assertEqual(rederive_payload["status"], "planned")
        self.assertEqual(rederive_payload["rederive_plan"]["from_stage"], "analysis_units")

    def test_library_governance_excludes_source_from_runtime_without_touching_raw_registry(self) -> None:
        first = self.root / "runtime-first.md"
        second = self.root / "runtime-second.md"
        first.write_text("This source should stay active in runtime.", encoding="utf-8")
        second.write_text("This source should be excluded from runtime.", encoding="utf-8")

        ingest_text_content(
            self.root,
            title="Runtime First",
            content=first.read_text(encoding="utf-8"),
            source_ref=str(first.resolve()),
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        ingest_text_content(
            self.root,
            title="Runtime Second",
            content=second.read_text(encoding="utf-8"),
            source_ref=str(second.resolve()),
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )

        self.assertEqual(len(load_source_registry_raw(self.root)), 2)
        self.assertEqual(len(load_source_registry(self.root)), 2)
        self.assertEqual({row["source_ref"] for row in load_chunk_index(self.root)}, {str(first.resolve()), str(second.resolve())})

        result = govern_library_source(
            self.root,
            source_ref=str(second.resolve()),
            governance_status="exclude_from_runtime",
            notes="noise",
        )

        self.assertEqual(result["policy_record"]["source_ref"], str(second.resolve()))
        self.assertIn("analysis_units", result["pending_rederive"]["affected_stages"])
        self.assertEqual(result["pending_rederive"]["from_stage"], "analysis_units")
        self.assertEqual(len(load_source_registry_raw(self.root)), 2)
        self.assertEqual(len(load_source_registry(self.root)), 1)
        self.assertEqual({row["source_ref"] for row in load_chunk_index(self.root)}, {str(first.resolve())})

        filtered = filter_library_sources(self.root, statuses=["exclude_from_runtime"])
        self.assertEqual(filtered["count"], 1)
        self.assertEqual(filtered["results"][0]["source_ref"], str(second.resolve()))
        self.assertEqual(filtered["results"][0]["policy_origin"], "source")
        self.assertFalse(filtered["results"][0]["include_in_runtime"])

    def test_runtime_chunk_loader_normalizes_conversation_residue_and_preserves_raw_chunks(self) -> None:
        source_ref = "normalize://conversation"
        ingest_text_content(
            self.root,
            title="Assistant: Conversation Import",
            content=(
                "You Said the following in the app browser and the current URL is shown.\n\n"
                "Assistant: The propagation graph should stay traversable across concepts.\n\n"
                "Current URL: http://127.0.0.1:3010/apps/inner-world/\n\n"
                "My request for Codex: refresh the page."
            ),
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )

        raw_chunks = [row for row in load_chunk_index_raw(self.root) if row["source_ref"] == source_ref]
        runtime_chunks = [row for row in load_chunk_index(self.root) if row["source_ref"] == source_ref]

        self.assertGreater(len(raw_chunks), len(runtime_chunks))
        self.assertTrue(any(row["content"].startswith("Assistant:") for row in raw_chunks))
        semantic_chunk = next(row for row in runtime_chunks if "propagation graph" in row["content"].lower())
        self.assertNotIn("Assistant:", semantic_chunk["content"])
        self.assertEqual(semantic_chunk["raw_content"], raw_chunks[1]["content"])
        self.assertTrue(semantic_chunk["normalized_runtime"])

        build_analysis_units(self.root)
        units = [row for row in load_analysis_units(self.root) if row["source_ref"] == source_ref]
        self.assertEqual(len(units), 1)
        self.assertIn("propagation graph should stay traversable", units[0]["content"].lower())
        self.assertNotIn("assistant:", units[0]["content"].lower())
        self.assertNotIn("current url", units[0]["content"].lower())
        self.assertNotIn("you said", units[0]["content"].lower())

    def test_runtime_chunk_loader_leaves_non_conversation_sources_unchanged(self) -> None:
        source_ref = "normalize://server-doc"
        ingest_text_content(
            self.root,
            title="Assistant: Literal Documentation Example",
            content="Assistant: this prefix is part of the documentation example and should remain.",
            source_ref=source_ref,
            source_type="server_content",
            source_family="server_content",
        )

        runtime_chunks = [row for row in load_chunk_index(self.root) if row["source_ref"] == source_ref]

        self.assertEqual(len(runtime_chunks), 1)
        self.assertEqual(
            runtime_chunks[0]["content"],
            "Assistant: this prefix is part of the documentation example and should remain.",
        )
        self.assertNotIn("raw_content", runtime_chunks[0])

    def test_runtime_chunk_loader_honors_source_normalization_profile_raw(self) -> None:
        source_ref = "normalize://raw-profile"
        ingest_text_content(
            self.root,
            title="Assistant: Raw Profile",
            content="Assistant: Keep this exact line because the source asks for raw normalization.",
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        govern_library_source(self.root, source_ref=source_ref, normalization_profile="raw")

        runtime_chunks = [row for row in load_chunk_index(self.root) if row["source_ref"] == source_ref]

        self.assertEqual(len(runtime_chunks), 1)
        self.assertEqual(
            runtime_chunks[0]["content"],
            "Assistant: Keep this exact line because the source asks for raw normalization.",
        )
        self.assertFalse(runtime_chunks[0]["normalized_runtime"])
        self.assertEqual(runtime_chunks[0]["normalization_profile_applied"], "raw")

    def test_runtime_chunk_loader_honors_chunk_normalization_profile_override(self) -> None:
        source_ref = "normalize://chunk-override"
        ingest_text_content(
            self.root,
            title="Chunk Override Source",
            content=(
                "Assistant: Keep the first line raw for provenance.\n\n"
                "Assistant: Refresh the page.\n\n"
                "Assistant: Propagation graph should remain semantically visible."
            ),
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        govern_library_source(self.root, source_ref=source_ref, normalization_profile="raw")
        raw_chunks = [row for row in load_chunk_index_raw(self.root) if row["source_ref"] == source_ref]
        procedural_chunk = next(row for row in raw_chunks if "Refresh the page" in row["content"])
        semantic_chunk_raw = next(row for row in raw_chunks if "Propagation graph should remain semantically visible." in row["content"])
        update_chunk_governance(self.root, procedural_chunk["chunk_id"], normalization_profile="strict")
        update_chunk_governance(self.root, semantic_chunk_raw["chunk_id"], normalization_profile="strict")

        runtime_chunks = [row for row in load_chunk_index(self.root) if row["source_ref"] == source_ref]
        preserved_chunk = next(row for row in runtime_chunks if "Keep the first line raw" in row["content"])
        semantic_chunk = next(row for row in runtime_chunks if "Propagation graph should remain semantically visible." in row["content"])

        self.assertIn("Assistant:", preserved_chunk["content"])
        self.assertEqual(preserved_chunk["normalization_profile_applied"], "raw")
        self.assertNotIn(procedural_chunk["chunk_id"], {row["chunk_id"] for row in runtime_chunks})
        self.assertNotIn("Assistant:", semantic_chunk["content"])
        self.assertEqual(semantic_chunk["normalization_profile_applied"], "strict")

    def test_library_filter_preview_uses_normalized_runtime_chunks(self) -> None:
        source_ref = "normalize://library-preview"
        ingest_text_content(
            self.root,
            title="Library Preview Source",
            content=(
                "You Said\n\n"
                "Assistant: Propagation graph should stay visible in the preview excerpt.\n\n"
                "Current URL: http://127.0.0.1:3010/apps/inner-world/"
            ),
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )

        filtered = filter_library_sources(self.root, source_ref=source_ref, limit=1)

        self.assertEqual(filtered["count"], 1)
        excerpt = filtered["results"][0]["preview_excerpt"].lower()
        self.assertIn("propagation graph should stay visible", excerpt)
        self.assertNotIn("you said", excerpt)
        self.assertNotIn("current url", excerpt)

    def test_reasoning_modules_do_not_bypass_runtime_chunk_loader(self) -> None:
        reasoning_modules = [
            REPO_ROOT / "src" / "conversation_os" / "analysis_units.py",
            REPO_ROOT / "src" / "conversation_os" / "conversation_deltas.py",
            REPO_ROOT / "src" / "conversation_os" / "conversation_threads.py",
            REPO_ROOT / "src" / "conversation_os" / "thread_context.py",
            REPO_ROOT / "src" / "conversation_os" / "thought_factory.py",
            REPO_ROOT / "src" / "conversation_os" / "context_bubbles.py",
            REPO_ROOT / "src" / "conversation_os" / "knowledge_layer.py",
        ]
        for path in reasoning_modules:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("load_chunk_index_raw(", text, msg=f"{path.name} should use the normalized runtime chunk loader")

    def test_library_governance_family_policy_excludes_sources_from_bubbles_only(self) -> None:
        active_ref = "governance://active"
        excluded_ref = "governance://scaffold"
        ingest_text_content(
            self.root,
            title="Active Source",
            content="Active source should still form a bubble.",
            source_ref=active_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        ingest_text_content(
            self.root,
            title="Scaffold Source",
            content="Scaffold source should be removable from bubbles.",
            source_ref=excluded_ref,
            source_type="meta_observatory_artifact",
            source_family="meta_observatory",
        )
        chunk_lookup = {row["source_ref"]: row["chunk_id"] for row in load_chunk_index_raw(self.root)}
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="meta-active-theme",
                    kind="theme",
                    label="Mechanism Bridge",
                    summary="Mechanism bridge should stay visible.",
                    source_ref=active_ref,
                    chunk_id=chunk_lookup[active_ref],
                    attributes={"tokens": ["mechanism", "bridge"]},
                ),
                self._meta_row(
                    meta_id="meta-active-question",
                    kind="question",
                    label="What bridge should be built?",
                    summary="Open question keeps the bubble structurally meaningful.",
                    source_ref=active_ref,
                    chunk_id=chunk_lookup[active_ref],
                    attributes={"tokens": ["bridge", "question"]},
                ),
                self._meta_row(
                    meta_id="meta-scaffold-theme",
                    kind="theme",
                    label="Scaffold Residue",
                    summary="Scaffolding residue should be governable.",
                    source_ref=excluded_ref,
                    chunk_id=chunk_lookup[excluded_ref],
                    attributes={"tokens": ["scaffold", "residue"]},
                ),
                self._meta_row(
                    meta_id="meta-scaffold-question",
                    kind="question",
                    label="Why is scaffolding dominating?",
                    summary="This scaffolding bubble should disappear after governance.",
                    source_ref=excluded_ref,
                    chunk_id=chunk_lookup[excluded_ref],
                    attributes={"tokens": ["scaffold", "dominating"]},
                ),
            ]
        )

        before = build_context_bubbles(self.root, ensure_dependencies=False)
        self.assertGreaterEqual(before["bubble_count"], 2)

        govern_library_family(
            self.root,
            source_family="meta_observatory",
            governance_status="exclude_from_bubbles",
            include_in_bubbles=False,
        )
        after = build_context_bubbles(self.root, ensure_dependencies=False)
        bubbles = load_context_bubbles(self.root)

        self.assertLess(after["bubble_count"], before["bubble_count"])
        self.assertTrue(all(excluded_ref not in row.get("source_refs", []) for row in bubbles))
        self.assertEqual(len(load_source_registry_raw(self.root)), 2)

    def test_context_bubbles_prefer_meaningful_labels_over_transcript_residue(self) -> None:
        source_ref = "bubble://clean-label"
        ingest_text_content(
            self.root,
            title="Clean Label Source",
            content="Cybernetic control loop should coordinate propagation through the system.",
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk_id = next(row["chunk_id"] for row in load_chunk_index_raw(self.root) if row["source_ref"] == source_ref)
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="meta-clean-label-theme",
                    kind="theme",
                    label="You Said",
                    summary="Cybernetic control loop should coordinate propagation through the system.",
                    source_ref=source_ref,
                    chunk_id=chunk_id,
                    confidence=0.94,
                    attributes={"tokens": ["cybernetic", "control", "propagation"]},
                ),
                self._meta_row(
                    meta_id="meta-clean-label-question",
                    kind="question",
                    label="How should the cybernetic control loop stabilize propagation?",
                    summary="Keep the bubble structurally grounded in the actual mechanism.",
                    source_ref=source_ref,
                    chunk_id=chunk_id,
                    confidence=0.72,
                    attributes={"tokens": ["cybernetic", "control", "loop", "propagation"]},
                ),
            ]
        )

        build_context_bubbles(self.root, ensure_dependencies=False)
        labels = [row["label"] for row in load_context_bubbles(self.root)]

        self.assertTrue(any("cybernetic" in label.lower() for label in labels))
        self.assertTrue(all(label.lower() != "you said" for label in labels))

    def test_context_bubbles_can_use_openclaw_assist_for_generic_surface_labels(self) -> None:
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "chat_backend": "openclaw_local",
                    "openclaw": {"agent": "main", "thinking": "minimal", "timeout_seconds": 12},
                    "semantic_assist": {"enabled": True, "bubble_label_limit": 1},
                }
            ),
            encoding="utf-8",
        )
        source_ref = "bubble://semantic-assist"
        ingest_text_content(
            self.root,
            title="Semantic Bubble Source",
            content="Human behavior calibration should guide how the system interprets interaction patterns.",
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk_id = next(row["chunk_id"] for row in load_chunk_index_raw(self.root) if row["source_ref"] == source_ref)
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="meta-semantic-theme",
                    kind="theme",
                    label="Does Human",
                    summary="Human behavior calibration should guide how the system interprets interaction patterns.",
                    source_ref=source_ref,
                    chunk_id=chunk_id,
                    attributes={"tokens": ["human", "behavior", "calibration", "patterns"]},
                ),
                self._meta_row(
                    meta_id="meta-semantic-question",
                    kind="question",
                    label="How should human behavior calibration shape interpretation?",
                    summary="Ground the bubble in the actual calibration mechanism.",
                    source_ref=source_ref,
                    chunk_id=chunk_id,
                    attributes={"tokens": ["human", "behavior", "calibration"]},
                ),
            ]
        )
        completed = mock.Mock(
            returncode=0,
            stdout=json.dumps(
                {
                    "reply": json.dumps(
                        {
                            "label": "Human Behavior Calibration",
                            "confidence": "high",
                            "reason": "The excerpts are about calibration of human behavior patterns.",
                        }
                    )
                }
            ),
            stderr="",
        )

        with mock.patch("conversation_os.context_bubbles.subprocess.run", return_value=completed) as run_mock:
            build_context_bubbles(self.root, ensure_dependencies=False)

        bubble = load_context_bubbles(self.root)[0]
        self.assertEqual(bubble["label"], "Human Behavior Calibration")
        self.assertEqual(bubble["raw_label"], "Does Human")
        self.assertEqual(bubble["semantic_label"], "Human Behavior Calibration")
        self.assertEqual(bubble["semantic_assist"]["confidence"], "high")
        self.assertEqual(run_mock.call_count, 1)

    def test_context_bubbles_drop_residue_only_clusters(self) -> None:
        useful_ref = "bubble://useful"
        residue_ref = "bubble://residue"
        ingest_text_content(
            self.root,
            title="Useful Bubble Source",
            content="Propagation map should stay visible as a real concept.",
            source_ref=useful_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        ingest_text_content(
            self.root,
            title="Residue Bubble Source",
            content="Uploaded Image frame\n\nYou Said\n\nSource",
            source_ref=residue_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk_lookup = {row["source_ref"]: row["chunk_id"] for row in load_chunk_index_raw(self.root)}
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="meta-useful-theme",
                    kind="theme",
                    label="Propagation Map",
                    summary="Propagation map should stay as the visible concept bubble.",
                    source_ref=useful_ref,
                    chunk_id=chunk_lookup[useful_ref],
                    attributes={"tokens": ["propagation", "map"]},
                ),
                self._meta_row(
                    meta_id="meta-useful-question",
                    kind="question",
                    label="How should the propagation map behave?",
                    summary="Useful question keeps the bubble grounded.",
                    source_ref=useful_ref,
                    chunk_id=chunk_lookup[useful_ref],
                    attributes={"tokens": ["propagation", "map", "question"]},
                ),
                self._meta_row(
                    meta_id="meta-residue-theme",
                    kind="theme",
                    label="Uploaded Image",
                    summary="Uploaded Image",
                    source_ref=residue_ref,
                    chunk_id=chunk_lookup[residue_ref],
                    attributes={"tokens": ["uploaded", "image"]},
                ),
                self._meta_row(
                    meta_id="meta-residue-question",
                    kind="question",
                    label="You Said",
                    summary="Source",
                    source_ref=residue_ref,
                    chunk_id=chunk_lookup[residue_ref],
                    attributes={"tokens": ["source", "label"]},
                ),
            ]
        )

        result = build_context_bubbles(self.root, ensure_dependencies=False)
        bubbles = load_context_bubbles(self.root)
        labels = [row["label"].lower() for row in bubbles]

        self.assertEqual(result["bubble_count"], 1)
        self.assertIn("propagation map", labels)
        self.assertNotIn("uploaded image", labels)
        self.assertNotIn("you said", labels)

    def test_library_governance_can_disable_concept_alignment_for_a_family(self) -> None:
        source_ref = "governance://concept-source"
        ingest_text_content(
            self.root,
            title="Concept Source",
            content="Mechanism Bridge should map to a known concept.",
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk_id = next(row["chunk_id"] for row in load_chunk_index_raw(self.root) if row["source_ref"] == source_ref)
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="meta-concept-theme",
                    kind="theme",
                    label="Mechanism Bridge",
                    summary="Mechanism Bridge should align to a canonical concept.",
                    source_ref=source_ref,
                    chunk_id=chunk_id,
                    attributes={"tokens": ["mechanism", "bridge"]},
                ),
                self._meta_row(
                    meta_id="meta-concept-question",
                    kind="question",
                    label="How should the bridge behave?",
                    summary="Keep the bubble alive with a real question.",
                    source_ref=source_ref,
                    chunk_id=chunk_id,
                    attributes={"tokens": ["mechanism", "bridge"]},
                ),
            ]
        )
        concept_dir = self.root / "product" / "inner_world_v1" / "data" / "concept_graph"
        concept_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(
            concept_dir / "concept_nodes.jsonl",
            [
                {
                    "concept_id": "concept-mechanism-bridge",
                    "label": "Mechanism Bridge",
                    "aliases": [],
                    "source_refs": [source_ref],
                    "confidence": 0.9,
                    "attributes": {"transfer_terms": ["mechanism", "bridge"]},
                }
            ],
        )
        write_jsonl(concept_dir / "concept_edges.jsonl", [])
        write_jsonl(concept_dir / "synthesis_packets.jsonl", [])
        write_jsonl(concept_dir / "touch_operations.jsonl", [])
        write_jsonl(concept_dir / "review_queue.jsonl", [])

        build_context_bubbles(self.root, ensure_dependencies=False)
        bubble = load_context_bubbles(self.root)[0]
        self.assertEqual(bubble["primary_concept_id"], "concept-mechanism-bridge")

        govern_library_family(
            self.root,
            source_family="chat_converter",
            include_in_concepts=False,
        )
        build_context_bubbles(self.root, ensure_dependencies=False)
        bubble = load_context_bubbles(self.root)[0]
        self.assertEqual(bubble["primary_concept_id"], "")
        self.assertEqual(bubble["concept_ids"], [])

    def test_chunk_governance_excludes_specific_chunk_without_touching_raw_index(self) -> None:
        source_ref = "chunk://exclude-one"
        ingest_text_content(
            self.root,
            title="Chunk Exclusion",
            content=(
                "# First\n\n"
                "The substrate layer should stay robust.\n\n"
                "# Second\n\n"
                "This chunk should be removable without mutating raw storage.\n\n"
                "# Third\n\n"
                "The remaining chunks should still participate in analysis."
            ),
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        raw_chunks = [row for row in load_chunk_index_raw(self.root) if row["source_ref"] == source_ref]
        self.assertGreaterEqual(len(raw_chunks), 3)
        target_chunk_id = raw_chunks[1]["chunk_id"]
        raw_chunk_ids_before = [row["chunk_id"] for row in raw_chunks]

        govern_result = update_chunk_governance(
            self.root,
            target_chunk_id,
            governance_status="exclude_from_runtime",
            notes="remove noise",
        )

        self.assertIn("analysis_units", govern_result["pending_rederive"]["affected_stages"])
        self.assertEqual(govern_result["pending_rederive"]["from_stage"], "analysis_units")
        raw_chunk_ids_after = [row["chunk_id"] for row in load_chunk_index_raw(self.root) if row["source_ref"] == source_ref]
        self.assertEqual(raw_chunk_ids_before, raw_chunk_ids_after)

        runtime_chunk_ids = {row["chunk_id"] for row in load_chunk_index(self.root) if row["source_ref"] == source_ref}
        self.assertNotIn(target_chunk_id, runtime_chunk_ids)
        self.assertEqual(len(runtime_chunk_ids), len(raw_chunk_ids_before) - 1)

        build_analysis_units(self.root)
        units = [row for row in load_analysis_units(self.root) if row["source_ref"] == source_ref]
        self.assertTrue(units)
        self.assertTrue(all(target_chunk_id not in row["chunk_ids"] for row in units))

    def test_chunk_governance_dimension_overlays_flow_into_governed_chunks_and_analysis_units(self) -> None:
        source_ref = "chunk://dimensions"
        ingest_text_content(
            self.root,
            title="Chunk Dimensions",
            content=(
                "# Overview\n\n"
                "The library should have a real metadata substrate.\n\n"
                "The metadata layer should stay editable."
            ),
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk_id = next(row["chunk_id"] for row in load_chunk_index_raw(self.root) if row["source_ref"] == source_ref)

        update_chunk_governance(
            self.root,
            chunk_id,
            semantic_role="substrate",
            dimension_overlays={
                "topic": ["substrate", "metadata"],
                "speaker_role": "assistant",
                "section_path": ["Curated", "Highlights"],
            },
        )

        governed_chunk = next(row for row in load_chunk_index(self.root) if row["chunk_id"] == chunk_id)
        self.assertEqual(governed_chunk["semantic_role"], "substrate")
        self.assertEqual(governed_chunk["metadata"]["speaker_role"], "assistant")
        self.assertEqual(governed_chunk["section_path"], ["Curated", "Highlights"])
        self.assertEqual(sorted(governed_chunk["metadata_dimensions"]["topic"]), ["metadata", "substrate"])

        build_analysis_units(self.root)
        unit = next(row for row in load_analysis_units(self.root) if chunk_id in row["chunk_ids"])
        self.assertEqual(unit["speaker_role"], "assistant")
        self.assertIn("topic", unit["metadata_dimensions"])
        self.assertEqual(sorted(unit["metadata_dimensions"]["topic"]), ["metadata", "substrate"])

    def test_chunk_filter_and_link_commands_surface_related_chunks(self) -> None:
        source_ref = "chunk://links"
        ingest_text_content(
            self.root,
            title="Chunk Links",
            content=(
                "# One\n\n"
                "First chunk establishes the substrate.\n\n"
                "# Two\n\n"
                "Second chunk sits next to it in the same source.\n\n"
                "# Three\n\n"
                "Third chunk should be manually linked back to the first."
            ),
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        raw_chunks = [row for row in load_chunk_index_raw(self.root) if row["source_ref"] == source_ref]
        raw_chunks.sort(key=lambda row: row["chunk_index"])
        first_chunk_id = raw_chunks[0]["chunk_id"]
        second_chunk_id = raw_chunks[1]["chunk_id"]
        third_chunk_id = raw_chunks[2]["chunk_id"]

        link_result = update_chunk_link(self.root, first_chunk_id, third_chunk_id, notes="manual bridge")
        self.assertEqual(link_result["action"], "upserted")

        filtered = filter_governed_chunks(self.root, source_ref=source_ref, limit=5)
        first_chunk = next(row for row in filtered["results"] if row["chunk_id"] == first_chunk_id)
        self.assertIn(second_chunk_id, first_chunk["related_chunk_ids"])
        self.assertIn(third_chunk_id, first_chunk["related_chunk_ids"])

        status = get_chunk_status(self.root)
        self.assertEqual(status["manual_chunk_link_count"], 1)
        self.assertGreaterEqual(status["connected_chunk_count"], 2)

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(["inner-world", "chunk-filter", "--source-ref", source_ref, "--limit", "5"])
        self.assertEqual(exit_code, 0)
        cli_filter = json.loads(stdout.getvalue())
        self.assertEqual(cli_filter["count"], 3)
        self.assertTrue(any(row["chunk_id"] == first_chunk_id for row in cli_filter["results"]))

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(
                [
                    "inner-world",
                    "chunk-govern",
                    "--chunk-id",
                    first_chunk_id,
                    "--dimensions",
                    "topic=substrate|governance",
                    "--status",
                    "background",
                ]
            )
        self.assertEqual(exit_code, 0)
        cli_govern = json.loads(stdout.getvalue())
        self.assertEqual(sorted(cli_govern["resolved_chunk"]["metadata_dimensions"]["topic"]), ["governance", "substrate"])
        self.assertEqual(cli_govern["resolved_chunk"]["governance_status"], "background")

    def test_prune_preview_detects_chunk_residue_and_reports_impact(self) -> None:
        residue_ref = "prune://chunk-residue"
        ingest_text_content(
            self.root,
            title="Residue Source",
            content="You Said\n\nUploaded Image frame\n\nActual substrate reasoning should remain active.",
            source_ref=residue_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )

        preview = preview_prune_candidates(
            self.root,
            scope="chunk",
            semantic_classes=["transcript_residue", "ui_label_residue"],
            target_status="exclude_from_runtime",
            limit=10,
        )

        self.assertGreaterEqual(preview["match_count"], 2)
        self.assertEqual(preview["rederive_plan"]["from_stage"], "analysis_units")
        chunk_classes = {cls for row in preview["preview"]["chunks"] for cls in row["curation_classes"]}
        self.assertIn("transcript_residue", chunk_classes)
        self.assertIn("ui_label_residue", chunk_classes)
        self.assertGreaterEqual(preview["impact"]["chunk_count"], 2)

    def test_prune_apply_excludes_matched_chunks_without_mutating_raw_storage(self) -> None:
        residue_ref = "prune://apply-chunks"
        ingest_text_content(
            self.root,
            title="Residue Apply",
            content="You Said\n\nUploaded Image frame\n\nKeep this meaningful substrate chunk active.",
            source_ref=residue_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        raw_before = [row["chunk_id"] for row in load_chunk_index_raw(self.root) if row["source_ref"] == residue_ref]

        applied = apply_prune_candidates(
            self.root,
            scope="chunk",
            target_status="exclude_from_runtime",
            semantic_classes=["transcript_residue", "ui_label_residue"],
            notes="remove residue",
            limit=10,
        )

        self.assertEqual(applied["status"], "applied")
        self.assertGreaterEqual(applied["applied_count"], 2)
        raw_after = [row["chunk_id"] for row in load_chunk_index_raw(self.root) if row["source_ref"] == residue_ref]
        self.assertEqual(raw_before, raw_after)
        runtime_chunks = [row["chunk_id"] for row in load_chunk_index(self.root) if row["source_ref"] == residue_ref]
        self.assertLess(len(runtime_chunks), len(raw_before))
        governance = load_library_governance(self.root)
        self.assertGreaterEqual(len(governance.get("prune_actions", [])), 1)
        self.assertEqual(governance["prune_actions"][-1]["scope"], "chunk")
        self.assertEqual(governance["pending_rederive"]["from_stage"], "analysis_units")

    def test_prune_preview_and_apply_can_target_scaffolding_source_with_bubble_impact(self) -> None:
        useful_ref = "prune://useful-source"
        scaffold_ref = "prune://scaffold-source"
        ingest_text_content(
            self.root,
            title="Useful Source",
            content="Mechanism bridge should stay as a product concept.",
            source_ref=useful_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        ingest_text_content(
            self.root,
            title="Scaffold Source",
            content="session_packet metadata source_ref remote_host path_name artifact_refs",
            source_ref=scaffold_ref,
            source_type="meta_observatory_artifact",
            source_family="meta_observatory",
        )
        chunk_lookup = {row["source_ref"]: row["chunk_id"] for row in load_chunk_index_raw(self.root)}
        self._write_meta_rows(
            [
                self._meta_row(
                    meta_id="meta-useful-theme",
                    kind="theme",
                    label="Mechanism Bridge",
                    summary="Useful concept should remain.",
                    source_ref=useful_ref,
                    chunk_id=chunk_lookup[useful_ref],
                    attributes={"tokens": ["mechanism", "bridge"]},
                ),
                self._meta_row(
                    meta_id="meta-useful-question",
                    kind="question",
                    label="What bridge should be built?",
                    summary="Useful question keeps bubble alive.",
                    source_ref=useful_ref,
                    chunk_id=chunk_lookup[useful_ref],
                    attributes={"tokens": ["bridge", "question"]},
                ),
                self._meta_row(
                    meta_id="meta-scaffold-theme",
                    kind="theme",
                    label="Source",
                    summary="session_packet metadata source_ref remote_host path_name artifact_refs",
                    source_ref=scaffold_ref,
                    chunk_id=chunk_lookup[scaffold_ref],
                    attributes={"tokens": ["source", "metadata"]},
                ),
                self._meta_row(
                    meta_id="meta-scaffold-question",
                    kind="question",
                    label="Label",
                    summary="Why is session metadata taking over?",
                    source_ref=scaffold_ref,
                    chunk_id=chunk_lookup[scaffold_ref],
                    attributes={"tokens": ["label", "metadata"]},
                ),
            ]
        )
        build_context_bubbles(self.root, ensure_dependencies=False)

        preview = preview_prune_candidates(
            self.root,
            scope="source",
            semantic_classes=["scaffolding_residue", "metadata_residue"],
            target_status="exclude_from_bubbles",
            limit=10,
        )
        self.assertEqual(preview["matched_source_count"], 1)
        self.assertEqual(preview["preview"]["sources"][0]["source_ref"], scaffold_ref)
        self.assertGreaterEqual(preview["impact"]["bubble_count"], 1)

        applied = apply_prune_candidates(
            self.root,
            scope="source",
            target_status="exclude_from_bubbles",
            semantic_classes=["scaffolding_residue", "metadata_residue"],
            notes="suppress scaffolding bubbles",
            limit=10,
        )
        self.assertEqual(applied["status"], "applied")
        self.assertEqual(applied["applied_count"], 1)
        filtered_sources = filter_library_sources(self.root, source_ref=scaffold_ref, limit=1)
        self.assertEqual(filtered_sources["results"][0]["governance_status"], "exclude_from_bubbles")
        self.assertEqual(len(load_source_registry_raw(self.root)), 2)

    def test_cli_prune_preview_and_apply_return_structured_payloads(self) -> None:
        residue_ref = "prune://cli"
        ingest_text_content(
            self.root,
            title="CLI Residue",
            content="Uploaded Image frame\n\nText block wrapper\n\nPreserve the actual concept chunk.",
            source_ref=residue_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(
                [
                    "inner-world",
                    "prune-preview",
                    "--scope",
                    "chunk",
                    "--semantic-classes",
                    "ui_label_residue",
                    "--status",
                    "exclude_from_runtime",
                ]
            )
        self.assertEqual(exit_code, 0)
        preview_payload = json.loads(stdout.getvalue())
        self.assertIn("impact", preview_payload)
        self.assertGreaterEqual(preview_payload["match_count"], 1)

        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(
                [
                    "inner-world",
                    "prune-apply",
                    "--scope",
                    "chunk",
                    "--semantic-classes",
                    "ui_label_residue",
                    "--status",
                    "exclude_from_runtime",
                    "--notes",
                    "cli prune",
                ]
            )
        self.assertEqual(exit_code, 0)
        apply_payload = json.loads(stdout.getvalue())
        self.assertEqual(apply_payload["status"], "applied")
        self.assertGreaterEqual(apply_payload["applied_count"], 1)

    def test_library_rederive_uses_pending_governance_plan_and_clears_it(self) -> None:
        source_ref = "governance://rederive-source"
        ingest_text_content(
            self.root,
            title="Rebuild Source",
            content="A tiny source is enough to test rederive planning.",
            source_ref=source_ref,
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        govern_library_source(self.root, source_ref=source_ref, governance_status="exclude_from_runtime")

        planned = rederive_library(self.root, affected_only=True, dry_run=True)
        self.assertEqual(planned["status"], "planned")
        self.assertEqual(planned["rederive_plan"]["from_stage"], "analysis_units")

        with mock.patch("conversation_os.product_inner_world.derive_graph", return_value={"bubble_count": 0, "connection_count": 0}) as mocked:
            executed = rederive_library(self.root, affected_only=True, dry_run=False)
        self.assertEqual(executed["status"], "completed")
        mocked.assert_called_once()
        self.assertEqual(mocked.call_args.kwargs["from_stage"], "analysis_units")
        self.assertTrue(mocked.call_args.kwargs["force"])
        self.assertIsNone(load_library_governance(self.root).get("pending_rederive"))

    def test_library_sync_supports_remote_filesystem_sources(self) -> None:
        corpus_dir = self.root / "remote-files"
        corpus_dir.mkdir(parents=True, exist_ok=True)
        source = corpus_dir / "remote-conversation.md"
        source.write_text("Remote substrate should still be tracked over SSH transport.", encoding="utf-8")
        self._write_library_config(
            {
                "sources": [
                    {
                        "source_id": "remote-files",
                        "kind": "filesystem",
                        "enabled": True,
                        "remote_host": "local",
                        "source_type": "chat_converter_conversation",
                        "source_family": "chat_converter",
                        "roots": [str(corpus_dir)],
                        "include_globs": ["*.md"],
                    }
                ]
            }
        )

        result = sync_library_sources(self.root)
        self.assertEqual(result["counts"]["new"], 1)
        self.assertEqual(result["ingested_item_count"], 1)
        registry = read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "source_registry.jsonl")
        self.assertEqual(registry[0]["source_ref"], str(source.resolve()))

    def test_library_sync_supports_remote_sqlite_sources(self) -> None:
        db_path = self.root / "remote-memory.sqlite"
        connection = sqlite3.connect(db_path)
        connection.execute("create table memories (id integer primary key, title text, content text)")
        connection.execute(
            "insert into memories (title, content) values (?, ?)",
            ("Remote Memory", "Remote sqlite transport should expose memory rows."),
        )
        connection.commit()
        connection.close()

        self._write_library_config(
            {
                "sources": [
                    {
                        "source_id": "remote-memory",
                        "kind": "sqlite",
                        "enabled": True,
                        "remote_host": "local",
                        "source_type": "openclaw_memory_record",
                        "source_family": "openclaw_memory",
                        "db_paths": [str(db_path)],
                        "include_tables": ["memories"],
                        "text_columns": ["title", "content"],
                    }
                ]
            }
        )

        result = sync_library_sources(self.root)
        self.assertEqual(result["counts"]["new"], 1)
        self.assertEqual(result["ingested_item_count"], 1)
        registry = read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "source_registry.jsonl")
        self.assertEqual(registry[0]["source_ref"], f"sqlite://{db_path.resolve()}#memories/1")

    def test_pond_router_status_bootstraps_defaults_and_runtime_overview(self) -> None:
        status = get_pond_router_status(self.root)
        self.assertTrue(status["enabled"])
        self.assertEqual(status["mode"], "heuristic")
        self.assertTrue(status["assisted_on_ambiguity"])
        self.assertEqual(status["local_role_id"], "pond_router_local")
        self.assertEqual(status["judge_role_id"], "pond_router_judge")
        self.assertEqual(status["feedback_count"], 0)

        runtime_payload = read_json(self.root / "product" / "inner_world_v1" / "config" / "runtime.json", default={})
        self.assertIn("pond_router", runtime_payload)
        self.assertEqual(runtime_payload["pond_router"]["router_version"], "v1")

        overview = get_runtime_overview(self.root)
        self.assertIn("pond_router", overview)
        self.assertEqual(overview["pond_router"]["mode"], "heuristic")

    def test_pond_router_roles_are_bootstrapped_into_runtime_model_roles(self) -> None:
        role_status = get_dimension_model_role_status(self.root)
        role_ids = {row["role_id"] for row in role_status["bindings"]}
        self.assertIn("pond_router_local", role_ids)
        self.assertIn("pond_router_judge", role_ids)

        update_dimension_model_role_binding(
            self.root,
            role_id="pond_router_local",
            backend="openclaw_gateway",
            model_id="kimi-k2.5",
            enabled=True,
            attributes={"agent": "thought_tube_router"},
        )
        pond_status = get_pond_router_status(self.root)
        self.assertIsNotNone(pond_status["local_role_binding"])
        self.assertTrue(pond_status["local_role_binding"]["bound"])
        self.assertEqual(pond_status["local_role_binding"]["model_id"], "kimi-k2.5")

    def test_update_pond_router_config_can_toggle_runtime_settings(self) -> None:
        result = update_pond_router_config(
            self.root,
            enabled=False,
            mode="off",
            assisted_on_ambiguity=False,
            allow_manual_override=False,
            ambiguity_threshold=0.91,
            router_version="v2",
        )
        status = result["pond_router"]
        self.assertFalse(status["enabled"])
        self.assertEqual(status["mode"], "off")
        self.assertFalse(status["assisted_on_ambiguity"])
        self.assertFalse(status["allow_manual_override"])
        self.assertEqual(status["ambiguity_threshold"], 0.91)
        self.assertEqual(status["router_version"], "v2")

    def test_apply_pond_router_preset_sets_expected_modes(self) -> None:
        status = apply_pond_router_preset(self.root, "manual_only")["pond_router"]
        self.assertTrue(status["enabled"])
        self.assertEqual(status["mode"], "manual_only")

        status = apply_pond_router_preset(self.root, "heuristic")["pond_router"]
        self.assertTrue(status["enabled"])
        self.assertEqual(status["mode"], "heuristic")
        self.assertFalse(status["assisted_on_ambiguity"])

        status = apply_pond_router_preset(self.root, "hybrid")["pond_router"]
        self.assertTrue(status["enabled"])
        self.assertEqual(status["mode"], "hybrid")
        self.assertTrue(status["assisted_on_ambiguity"])

        status = apply_pond_router_preset(self.root, "assisted")["pond_router"]
        self.assertTrue(status["enabled"])
        self.assertEqual(status["mode"], "assisted")

        status = apply_pond_router_preset(self.root, "off")["pond_router"]
        self.assertFalse(status["enabled"])
        self.assertEqual(status["mode"], "off")

    def test_update_pond_router_config_rejects_invalid_values(self) -> None:
        with self.assertRaises(ValueError):
            update_pond_router_config(self.root, mode="invalid-mode")
        with self.assertRaises(ValueError):
            update_pond_router_config(self.root, ambiguity_threshold=1.2)
        with self.assertRaises(ValueError):
            apply_pond_router_preset(self.root, "unknown")

    def test_cli_pond_router_status_outputs_runtime_state(self) -> None:
        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(["inner-world", "pond-router", "status"])
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertTrue(payload["enabled"])
        self.assertEqual(payload["mode"], "heuristic")

    def test_cli_pond_router_preset_updates_mode(self) -> None:
        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(["inner-world", "pond-router", "preset", "--name", "manual_only"])
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "updated")
        self.assertEqual(payload["pond_router"]["mode"], "manual_only")

    def test_cli_pond_router_update_can_toggle_fields(self) -> None:
        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            exit_code = main(
                [
                    "inner-world",
                    "pond-router",
                    "update",
                    "--enabled",
                    "false",
                    "--mode",
                    "off",
                    "--assisted-on-ambiguity",
                    "false",
                    "--allow-manual-override",
                    "false",
                    "--ambiguity-threshold",
                    "0.88",
                ]
            )
        self.assertEqual(exit_code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["status"], "updated")
        self.assertFalse(payload["pond_router"]["enabled"])
        self.assertEqual(payload["pond_router"]["mode"], "off")
        self.assertFalse(payload["pond_router"]["assisted_on_ambiguity"])
        self.assertFalse(payload["pond_router"]["allow_manual_override"])
        self.assertEqual(payload["pond_router"]["ambiguity_threshold"], 0.88)

    def test_cli_holodeck_check_reports_blocked_dependency_health(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-check",
                "--title",
                "Check",
                "--goal",
                "Report rigor",
                "--purpose",
                "Validate structured health output",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-check",
                "--work-item-id",
                "dep-1",
                "--title",
                "Dependency",
                "--kind",
                "task",
                "--status",
                "proposed",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-check",
                "--work-item-id",
                "blocked-1",
                "--title",
                "Blocked Impl",
                "--kind",
                "implementation",
                "--status",
                "blocked",
                "--acceptance-criteria",
                "ship",
                "--guard-status",
                "ready",
                "--depends-on",
                "dep-1",
            ]
        )

        payload = run_cli(["holodeck", "check", "--workspace-id", "hd-check"])

        self.assertFalse(payload["healthy"])
        self.assertTrue(payload["structural_ok"])
        self.assertFalse(payload["execution_ready"])
        self.assertTrue(payload["verification_ok"])
        self.assertEqual(payload["counts"]["execution_blockers"], 1)
        self.assertEqual(payload["counts"]["structural_issues"], 0)
        blocker = payload["execution_blockers"][0]
        self.assertEqual(blocker["work_item_id"], "blocked-1")
        self.assertEqual(blocker["depends_on"], ["dep-1"])
        self.assertTrue(any("dep-1" in reason for reason in blocker["reasons"]))

    def test_cli_holodeck_check_reports_repeated_failing_test_hotspots(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-hotspot",
                "--title",
                "Hotspot",
                "--goal",
                "Surface repeated failing verification",
                "--purpose",
                "Detect failing test hotspots in workspace health",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-hotspot",
                "--work-item-id",
                "impl-1",
                "--title",
                "Implementation",
                "--kind",
                "implementation",
                "--status",
                "in_progress",
                "--guard-status",
                "ready",
                "--acceptance-criteria",
                "ship",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-test",
                "--workspace-id",
                "hd-hotspot",
                "--test-id",
                "test-1",
                "--work-item-id",
                "impl-1",
                "--target-ref",
                "src/conversation_os/cli.py",
                "--test-kind",
                "acceptance",
                "--intent",
                "Validate failing hotspot tracking",
                "--command-or-protocol",
                "pytest tests/test_conversation_os.py -k hotspot",
                "--expected-signal",
                "passing test",
            ]
        )
        run_cli(
            [
                "holodeck",
                "record-test-run",
                "--workspace-id",
                "hd-hotspot",
                "--test-id",
                "test-1",
                "--result",
                "failing",
                "--notes",
                "first failure",
            ]
        )
        run_cli(
            [
                "holodeck",
                "record-test-run",
                "--workspace-id",
                "hd-hotspot",
                "--test-id",
                "test-1",
                "--result",
                "failing",
                "--notes",
                "second failure",
            ]
        )

        payload = run_cli(["holodeck", "check", "--workspace-id", "hd-hotspot"])

        self.assertFalse(payload["verification_ok"])
        self.assertEqual(payload["counts"]["verification_hotspots"], 1)
        hotspot = payload["verification_hotspots"][0]
        self.assertEqual(hotspot["test_id"], "test-1")
        self.assertEqual(hotspot["failure_streak"], 2)
        self.assertEqual(hotspot["latest_result"], "failing")

    def test_cli_holodeck_task_pack_renders_blocker_reasons(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-pack",
                "--title",
                "Pack",
                "--goal",
                "Preserve blockers",
                "--purpose",
                "Validate task-pack blocker rendering",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-pack",
                "--work-item-id",
                "dep-1",
                "--title",
                "Dependency",
                "--kind",
                "task",
                "--status",
                "proposed",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-pack",
                "--work-item-id",
                "blocked-1",
                "--title",
                "Blocked Impl",
                "--kind",
                "implementation",
                "--status",
                "blocked",
                "--acceptance-criteria",
                "ship",
                "--guard-status",
                "ready",
                "--depends-on",
                "dep-1",
            ]
        )

        payload = run_cli(["holodeck", "task-pack", "--workspace-id", "hd-pack", "--task-id", "hd-pack-task"])

        self.assertEqual(payload["workspace_id"], "hd-pack")
        self.assertEqual(payload["workspace_linked_task_pack_ids"], ["hd-pack-task"])
        self.assertEqual(payload["workspace_blocked_items"][0]["work_item_id"], "blocked-1")
        self.assertTrue(
            any("Dependency dep-1 is still proposed and must be done first." in reason for reason in payload["workspace_blocked_items"][0]["blocker_reasons"])
        )
        self.assertTrue(
            any(
                "blocked_work_item: blocked-1::Blocked Impl::Dependency dep-1 is still proposed and must be done first."
                in constraint
                for constraint in payload["constraints"]
            )
        )
        markdown = (task_packs_dir(self.root) / "hd-pack-task.md").read_text(encoding="utf-8")
        self.assertIn("## Blocked Workspace Items", markdown)
        self.assertIn("Dependency dep-1 is still proposed and must be done first.", markdown)

    def test_cli_holodeck_task_pack_carries_workspace_blocker_constraints(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-pack-blocked",
                "--title",
                "Pack Blocked",
                "--goal",
                "Carry workspace blockers",
                "--purpose",
                "Ensure task-pack handoff keeps workspace blocked context",
            ]
        )
        run_cli(
            [
                "holodeck",
                "block",
                "--workspace-id",
                "hd-pack-blocked",
                "--reason",
                "Awaiting vendor approval",
            ]
        )

        payload = run_cli(
            ["holodeck", "task-pack", "--workspace-id", "hd-pack-blocked", "--task-id", "hd-pack-blocked-task"]
        )

        self.assertEqual(payload["workspace_id"], "hd-pack-blocked")
        self.assertEqual(payload["workspace_status"], "blocked")
        self.assertEqual(payload["workspace_blockers"][0]["reason"], "Awaiting vendor approval")
        self.assertTrue(
            any("workspace_status: blocked::Awaiting vendor approval" in constraint for constraint in payload["constraints"])
        )

    def test_cli_holodeck_apply_promotion_creates_memory_card(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-promote",
                "--title",
                "Promote",
                "--goal",
                "Ship shared knowledge",
                "--purpose",
                "Validate promotion apply flow",
                "--domains",
                "conversation_os",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-knowledge",
                "--workspace-id",
                "hd-promote",
                "--record-id",
                "decision-1",
                "--record-kind",
                "decision",
                "--claim-posture",
                "decided",
                "--title",
                "Keep guard output explicit",
                "--statement",
                "Guard failures should explain next steps directly.",
                "--source-refs",
                "plan://holodeck",
            ]
        )
        run_cli(
            [
                "holodeck",
                "promote",
                "--workspace-id",
                "hd-promote",
                "--record-id",
                "decision-1",
                "--promotion-id",
                "promotion-1",
                "--reason",
                "This decision should become global memory.",
            ]
        )

        payload = run_cli(["holodeck", "apply-promotion", "--workspace-id", "hd-promote", "--promotion-id", "promotion-1"])

        card_path = Path(payload["card_path"])
        self.assertTrue(card_path.exists())
        card = read_json(card_path)
        self.assertEqual(payload["card_id"], card["card_id"])
        self.assertEqual(card["card_type"], "decision")
        self.assertEqual(card["status"], "accepted")
        self.assertIn("holodeck", card["tags"])
        self.assertIn("conversation_os", card["domains"])
        self.assertEqual(payload["promotion_state"]["status"], "applied")
        self.assertEqual(payload["snapshot"]["promotion_counts"]["applied"], 1)
        self.assertEqual(payload["snapshot"]["integration_candidates"], [])

    def test_cli_holodeck_apply_promotion_links_integration_target_and_artifact(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-promote-link",
                "--title",
                "Promote Linked",
                "--goal",
                "Ship shared knowledge into an explicit target",
                "--purpose",
                "Validate integration target linkage during promotion apply",
                "--domains",
                "conversation_os",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-integration-target",
                "--workspace-id",
                "hd-promote-link",
                "--target-id",
                "target-memory",
                "--target-kind",
                "memory_card",
                "--title",
                "Global memory promotion",
                "--destination-ref",
                "memory/cards",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-knowledge",
                "--workspace-id",
                "hd-promote-link",
                "--record-id",
                "decision-1",
                "--record-kind",
                "decision",
                "--claim-posture",
                "decided",
                "--title",
                "Keep guard output explicit",
                "--statement",
                "Guard failures should explain next steps directly.",
                "--source-refs",
                "plan://holodeck",
            ]
        )
        run_cli(
            [
                "holodeck",
                "promote",
                "--workspace-id",
                "hd-promote-link",
                "--record-id",
                "decision-1",
                "--promotion-id",
                "promotion-1",
                "--target-id",
                "target-memory",
                "--reason",
                "This decision should become global memory through the declared target.",
            ]
        )

        payload = run_cli(["holodeck", "apply-promotion", "--workspace-id", "hd-promote-link", "--promotion-id", "promotion-1"])
        self.assertEqual(payload["snapshot"]["integration_targets"][0]["target_id"], "target-memory")
        self.assertEqual(payload["snapshot"]["integration_targets"][0]["status"], "applied")

        artifacts = run_cli(["holodeck", "artifacts", "--workspace-id", "hd-promote-link"])
        memory_card = next(item for item in artifacts["artifacts"] if item["artifact_kind"] == "memory_card")
        self.assertEqual(memory_card["attributes"]["integration_target_ids"], ["target-memory"])

    def test_cli_holodeck_check_enforces_constraint_kinds_for_paths_and_non_goals(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-constraint-check",
                "--title",
                "Constraint Check",
                "--goal",
                "Make typed constraints operational",
                "--purpose",
                "Validate allowed_path, blocked_path, and non_goal enforcement",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-constraint",
                "--workspace-id",
                "hd-constraint-check",
                "--constraint-id",
                "con-allow",
                "--constraint-kind",
                "allowed_path",
                "--statement",
                "Only the Holodeck CLI owner surface is allowed.",
                "--applies-to",
                "src/conversation_os/cli.py",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-constraint",
                "--workspace-id",
                "hd-constraint-check",
                "--constraint-id",
                "con-block",
                "--constraint-kind",
                "blocked_path",
                "--statement",
                "Storage ownership is blocked in this slice.",
                "--applies-to",
                "src/conversation_os/storage.py",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-constraint-check",
                "--work-item-id",
                "wi-ui",
                "--title",
                "Build the forbidden UI",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-constraint",
                "--workspace-id",
                "hd-constraint-check",
                "--constraint-id",
                "con-non-goal",
                "--constraint-kind",
                "non_goal",
                "--statement",
                "UI work is not part of this slice.",
                "--applies-to",
                "wi-ui",
            ]
        )
        run_cli(
            [
                "holodeck",
                "event",
                "--workspace-id",
                "hd-constraint-check",
                "--kind",
                "note",
                "--summary",
                "Touched blocked path",
                "--source-refs",
                "src/conversation_os/storage.py",
            ]
        )
        run_cli(
            [
                "holodeck",
                "event",
                "--workspace-id",
                "hd-constraint-check",
                "--kind",
                "note",
                "--summary",
                "Touched unrelated path",
                "--source-refs",
                "docs/notes.md",
            ]
        )

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-constraint-check"])
        self.assertFalse(checked["healthy"])
        self.assertFalse(checked["execution_ready"])
        self.assertEqual(checked["counts"]["constraint_violations"], 4)
        self.assertTrue(
            {
                "blocked_path_touched",
                "source_ref_outside_constraint_allowed_paths",
                "active_non_goal_work_item",
            }.issubset({item["code"] for item in checked["constraint_violations"]})
        )

    def test_cli_holodeck_check_reports_active_knowledge_conflicts(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-conflict",
                "--title",
                "Conflict",
                "--goal",
                "Expose conflicts",
                "--purpose",
                "Validate conflict reporting for contradictory knowledge",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-knowledge",
                "--workspace-id",
                "hd-conflict",
                "--record-id",
                "decision-a",
                "--record-kind",
                "decision",
                "--claim-posture",
                "decided",
                "--title",
                "Ship as CLI-first",
                "--statement",
                "Keep Holodeck as a CLI-first surface for now.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-knowledge",
                "--workspace-id",
                "hd-conflict",
                "--record-id",
                "decision-b",
                "--record-kind",
                "decision",
                "--claim-posture",
                "decided",
                "--title",
                "Ship as CLI-first",
                "--statement",
                "Move Holodeck immediately into a dedicated workspace module.",
            ]
        )

        payload = run_cli(["holodeck", "check", "--workspace-id", "hd-conflict"])

        self.assertFalse(payload["healthy"])
        self.assertTrue(payload["structural_ok"])
        self.assertFalse(payload["conflict_free"])
        self.assertEqual(payload["counts"]["knowledge_conflicts"], 1)
        conflict = payload["knowledge_conflicts"][0]
        self.assertEqual(conflict["record_kind"], "decision")
        self.assertEqual(conflict["title"], "Ship as CLI-first")
        self.assertEqual(sorted(conflict["record_ids"]), ["decision-a", "decision-b"])

        materialized = run_cli(["holodeck", "materialize", "--workspace-id", "hd-conflict"])
        knowledge_path = Path(materialized["materialized_paths"]["knowledge"])
        knowledge_md = knowledge_path.read_text(encoding="utf-8")
        self.assertIn("## Conflicts", knowledge_md)
        self.assertIn("decision-a || decision-b", knowledge_md)

    def test_cli_holodeck_update_knowledge_can_resolve_conflict(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-resolve",
                "--title",
                "Resolve",
                "--goal",
                "Resolve conflict",
                "--purpose",
                "Validate typed knowledge resolution",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-knowledge",
                "--workspace-id",
                "hd-resolve",
                "--record-id",
                "decision-a",
                "--record-kind",
                "decision",
                "--claim-posture",
                "decided",
                "--title",
                "Keep CLI owner",
                "--statement",
                "Keep Holodeck in cli.py for now.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-knowledge",
                "--workspace-id",
                "hd-resolve",
                "--record-id",
                "decision-b",
                "--record-kind",
                "decision",
                "--claim-posture",
                "decided",
                "--title",
                "Keep CLI owner",
                "--statement",
                "Move Holodeck out of cli.py immediately.",
            ]
        )

        before = run_cli(["holodeck", "check", "--workspace-id", "hd-resolve"])
        self.assertEqual(before["counts"]["knowledge_conflicts"], 1)

        updated = run_cli(
            [
                "holodeck",
                "update-knowledge",
                "--workspace-id",
                "hd-resolve",
                "--record-id",
                "decision-b",
                "--status",
                "superseded",
                "--supersedes-record-id",
                "decision-a",
                "--reason",
                "Decision A stays active.",
            ]
        )
        self.assertTrue(updated["updated"])
        self.assertEqual(updated["status"], "superseded")
        self.assertEqual(updated["supersedes_record_id"], "decision-a")

        after = run_cli(["holodeck", "check", "--workspace-id", "hd-resolve"])
        self.assertTrue(after["conflict_free"])
        self.assertEqual(after["counts"]["knowledge_conflicts"], 0)

    def test_cli_holodeck_create_rejects_founder_fields_without_founder_template(self) -> None:
        stdout = StringIO()
        with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
            with self.assertRaises(ValueError) as error:
                main(
                    [
                        "holodeck",
                        "create",
                        "--workspace-id",
                        "hd-template",
                        "--title",
                        "Template Drift",
                        "--goal",
                        "Keep founder fields coherent",
                        "--purpose",
                        "Founder-only fields should require the founder template",
                        "--founder-wedge",
                        "Ship agent substrate first",
                    ]
                )
        self.assertIn("founder template", str(error.exception))

    def test_cli_holodeck_check_reports_missing_founder_template_context(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-founder",
                "--title",
                "Founder Holodeck",
                "--goal",
                "Develop a founder objective",
                "--purpose",
                "Show missing founder context during incubation",
                "--template-key",
                "founder",
                "--founder-wedge",
                "Start with a narrow wedge",
            ]
        )

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-founder"])
        self.assertFalse(checked["template_ok"])
        self.assertEqual(checked["counts"]["template_issues"], 2)
        self.assertEqual(
            {item["field"] for item in checked["template_issues"]},
            {"user", "launch_metric"},
        )

    def test_cli_holodeck_inquiry_planner_surfaces_grounded_founder_questions(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-founder-inquiry",
                "--title",
                "Founder Inquiry",
                "--goal",
                "Shape a founder-facing objective",
                "--purpose",
                "Validate grounded user-facing inquiry planning",
                "--template-key",
                "founder",
                "--founder-wedge",
                "Start with a narrow wedge",
            ]
        )

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-founder-inquiry"])
        self.assertEqual(checked["counts"]["questions_for_user"], 2)
        self.assertEqual(checked["counts"]["inquiries"], 2)
        self.assertTrue(all(item["ask_user"] for item in checked["questions_for_user"]))
        self.assertEqual(
            {item["field"] for item in checked["questions_for_user"]},
            {"user", "launch_metric"},
        )
        self.assertTrue(
            all(
                "template_issue:missing_founder_field" in item["source_signals"][0]
                for item in checked["questions_for_user"]
            )
        )

        task_pack = run_cli(
            ["holodeck", "task-pack", "--workspace-id", "hd-founder-inquiry", "--task-id", "hd-founder-inquiry-task"]
        )
        self.assertTrue(any(item.startswith("user_question: ") for item in task_pack["constraints"]))

    def test_cli_holodeck_inquiry_planner_keeps_verification_gaps_internal(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-inquiry-verify",
                "--title",
                "Inquiry Verification",
                "--goal",
                "Keep internal gaps out of user question flow",
                "--purpose",
                "Validate that verification gaps stay agent-owned",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-inquiry-verify",
                "--work-item-id",
                "wi-verify",
                "--title",
                "Finish without evidence",
                "--status",
                "done",
                "--acceptance-criteria",
                "Need verification evidence before closure",
            ]
        )

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-inquiry-verify"])
        self.assertEqual(checked["counts"]["verification_gaps"], 1)
        self.assertEqual(checked["counts"]["questions_for_user"], 0)
        self.assertTrue(any(item["inquiry_kind"] == "verification" for item in checked["inquiry_queue"]))
        self.assertTrue(all(not item["ask_user"] for item in checked["inquiry_queue"]))

    def test_cli_holodeck_update_clears_founder_fields_when_template_changes(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-template-shift",
                "--title",
                "Template Shift",
                "--goal",
                "Retire founder overlay cleanly",
                "--purpose",
                "Founder fields should not linger after the template changes",
                "--template-key",
                "founder",
                "--founder-wedge",
                "Begin with a narrow wedge",
                "--founder-user",
                "Infra-heavy founder",
                "--founder-launch-metric",
                "Activated projects",
            ]
        )

        updated = run_cli(
            [
                "holodeck",
                "update",
                "--workspace-id",
                "hd-template-shift",
                "--template-key",
                "",
            ]
        )
        self.assertEqual(updated["template_key"], "")
        self.assertEqual(updated["template_fields"], {})

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-template-shift"])
        self.assertTrue(checked["template_ok"])
        self.assertEqual(checked["counts"]["template_issues"], 0)

    def test_cli_holodeck_parent_done_rejected_while_child_open(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-parent",
                "--title",
                "Parent",
                "--goal",
                "Protect parent lifecycle",
                "--purpose",
                "Validate parent-child completion discipline",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-parent",
                "--work-item-id",
                "parent-1",
                "--title",
                "Parent Item",
                "--kind",
                "task",
                "--status",
                "proposed",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-parent",
                "--work-item-id",
                "child-1",
                "--title",
                "Child Item",
                "--kind",
                "task",
                "--status",
                "proposed",
                "--parent-id",
                "parent-1",
            ]
        )

        with self.assertRaises(ValueError) as error:
            run_cli(["holodeck", "update-work-item", "--workspace-id", "hd-parent", "--work-item-id", "parent-1", "--status", "done"])
        self.assertIn("child-1", str(error.exception))

    def test_cli_holodeck_pause_close_reopen_archive_and_list_reflect_lifecycle(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-life",
                "--title",
                "Lifecycle",
                "--goal",
                "Track state",
                "--purpose",
                "Validate close and reopen behavior",
            ]
        )

        paused = run_cli(["holodeck", "pause", "--workspace-id", "hd-life", "--reason", "wait"])
        self.assertEqual(paused["status"], "paused")
        self.assertIsNone(paused["closed_at"])

        paused_list = run_cli(["holodeck", "list", "--status", "paused"])
        self.assertTrue(any(item["workspace_id"] == "hd-life" for item in paused_list["workspaces"]))

        reopened_from_pause = run_cli(["holodeck", "reopen", "--workspace-id", "hd-life", "--reason", "resume"])
        self.assertEqual(reopened_from_pause["status"], "active")
        self.assertIsNone(reopened_from_pause["closed_at"])

        closed = run_cli(["holodeck", "close", "--workspace-id", "hd-life", "--reason", "pause"])
        self.assertEqual(closed["status"], "closed")
        self.assertTrue(closed["closed_at"])

        closed_list = run_cli(["holodeck", "list", "--status", "closed"])
        self.assertTrue(any(item["workspace_id"] == "hd-life" for item in closed_list["workspaces"]))

        reopened = run_cli(["holodeck", "reopen", "--workspace-id", "hd-life", "--reason", "resume"])
        self.assertEqual(reopened["status"], "active")
        self.assertIsNone(reopened["closed_at"])

        active_list = run_cli(["holodeck", "list", "--status", "active"])
        self.assertTrue(any(item["workspace_id"] == "hd-life" for item in active_list["workspaces"]))

        archived = run_cli(["holodeck", "archive", "--workspace-id", "hd-life", "--reason", "done"])
        self.assertEqual(archived["status"], "archived")
        self.assertTrue(archived["closed_at"])

        archived_list = run_cli(["holodeck", "list", "--status", "archived"])
        self.assertTrue(any(item["workspace_id"] == "hd-life" for item in archived_list["workspaces"]))

    def test_cli_holodeck_block_and_reopen_reflect_workspace_health(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-blocked",
                "--title",
                "Blocked Workspace",
                "--goal",
                "Surface workspace-level blocking",
                "--purpose",
                "Make blocked status explicit in lifecycle and health output",
            ]
        )

        blocked = run_cli(
            ["holodeck", "block", "--workspace-id", "hd-blocked", "--reason", "Waiting on external API access"]
        )
        self.assertEqual(blocked["status"], "blocked")
        self.assertEqual(blocked["current_snapshot"]["status"], "blocked")

        status_payload = run_cli(["holodeck", "status", "--workspace-id", "hd-blocked"])
        self.assertEqual(status_payload["status"], "blocked")

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-blocked"])
        self.assertFalse(checked["healthy"])
        self.assertFalse(checked["execution_ready"])
        self.assertEqual(checked["counts"]["workspace_blockers"], 1)
        self.assertEqual(checked["workspace_blockers"][0]["reason"], "Waiting on external API access")

        blocked_list = run_cli(["holodeck", "list", "--status", "blocked"])
        self.assertTrue(any(item["workspace_id"] == "hd-blocked" for item in blocked_list["workspaces"]))

        reopened = run_cli(["holodeck", "reopen", "--workspace-id", "hd-blocked", "--reason", "API access restored"])
        self.assertEqual(reopened["status"], "active")

        after = run_cli(["holodeck", "check", "--workspace-id", "hd-blocked"])
        self.assertTrue(after["healthy"])
        self.assertTrue(after["execution_ready"])
        self.assertEqual(after["counts"]["workspace_blockers"], 0)

    def test_cli_holodeck_maturation_stage_defaults_advances_and_reports(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        created = run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-stage",
                "--title",
                "Stage",
                "--goal",
                "Track idea maturation",
                "--purpose",
                "Validate explicit maturation stage flow",
            ]
        )
        self.assertEqual(created["maturation_stage"], "raw")

        status_before = run_cli(["holodeck", "status", "--workspace-id", "hd-stage"])
        self.assertEqual(status_before["maturation_stage"], "raw")

        advanced = run_cli(
            [
                "holodeck",
                "advance-stage",
                "--workspace-id",
                "hd-stage",
                "--stage",
                "scoping",
                "--reason",
                "Initial context is clear enough to scope",
            ]
        )
        self.assertEqual(advanced["maturation_stage"], "scoping")
        self.assertEqual(advanced["current_snapshot"]["maturation_stage"], "scoping")

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-stage"])
        self.assertEqual(checked["maturation_stage"], "scoping")

        with self.assertRaises(ValueError) as error:
            run_cli(
                [
                    "holodeck",
                    "advance-stage",
                    "--workspace-id",
                    "hd-stage",
                    "--stage",
                    "wandering",
                    "--reason",
                    "invalid",
                ]
            )
        self.assertIn("Invalid maturation stage", str(error.exception))

    def test_cli_holodeck_stage_readiness_reports_scope_gaps_and_task_pack_constraints(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-stage-gaps",
                "--title",
                "Stage Gaps",
                "--goal",
                "Make stage readiness visible",
                "--purpose",
                "Validate scoping readiness checks",
            ]
        )
        run_cli(
            [
                "holodeck",
                "advance-stage",
                "--workspace-id",
                "hd-stage-gaps",
                "--stage",
                "scoping",
                "--reason",
                "Need scope boundaries",
            ]
        )

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-stage-gaps"])
        self.assertFalse(checked["stage_ok"])
        self.assertEqual(checked["counts"]["stage_gaps"], 2)
        self.assertEqual(
            {item["code"] for item in checked["stage_gaps"]},
            {"missing_scope_in", "missing_scope_out"},
        )

        task_pack = run_cli(
            ["holodeck", "task-pack", "--workspace-id", "hd-stage-gaps", "--task-id", "hd-stage-gaps-task"]
        )
        self.assertTrue(any("stage_gap: scoping::missing_scope_in" in item for item in task_pack["constraints"]))

        run_cli(
            [
                "holodeck",
                "update",
                "--workspace-id",
                "hd-stage-gaps",
                "--scope-in",
                "Holodeck stage readiness",
                "--scope-out",
                "New UI",
            ]
        )

        after = run_cli(["holodeck", "check", "--workspace-id", "hd-stage-gaps"])
        self.assertTrue(after["stage_ok"])
        self.assertEqual(after["counts"]["stage_gaps"], 0)

    def test_cli_holodeck_context_records_ground_contextualizing_stage(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-context",
                "--title",
                "Context",
                "--goal",
                "Ground the objective",
                "--purpose",
                "Validate first-class context records",
            ]
        )
        run_cli(
            [
                "holodeck",
                "advance-stage",
                "--workspace-id",
                "hd-context",
                "--stage",
                "contextualizing",
                "--reason",
                "Need grounding context",
            ]
        )

        before = run_cli(["holodeck", "check", "--workspace-id", "hd-context"])
        self.assertFalse(before["stage_ok"])
        self.assertEqual(before["stage_gaps"][0]["code"], "missing_contextualization_outcome")

        created = run_cli(
            [
                "holodeck",
                "add-context",
                "--workspace-id",
                "hd-context",
                "--context-id",
                "ctx-owner",
                "--context-kind",
                "owner_surface",
                "--title",
                "Holodeck CLI owner",
                "--summary",
                "The current implementation surface is src/conversation_os/cli.py.",
                "--domain",
                "conversation_os",
                "--source-refs",
                "src/conversation_os/cli.py",
                "--linked-artifact-ids",
                "artifact-cli",
                "--confidence",
                "0.9",
            ]
        )
        self.assertEqual(created["context_id"], "ctx-owner")

        updated = run_cli(
            [
                "holodeck",
                "update-context",
                "--workspace-id",
                "hd-context",
                "--context-id",
                "ctx-owner",
                "--summary",
                "The current implementation surface remains the Holodeck CLI owner.",
            ]
        )
        self.assertTrue(updated["updated"])
        self.assertEqual(updated["summary"], "The current implementation surface remains the Holodeck CLI owner.")

        after = run_cli(["holodeck", "check", "--workspace-id", "hd-context"])
        self.assertTrue(after["stage_ok"])
        self.assertEqual(after["counts"]["context_records"], 1)
        self.assertEqual(after["context_records"][0]["context_id"], "ctx-owner")

        materialized = run_cli(["holodeck", "materialize", "--workspace-id", "hd-context"])
        context_md = Path(materialized["materialized_paths"]["context"])
        context_json = Path(materialized["materialized_paths"]["context_json"])
        self.assertIn("Holodeck CLI owner", context_md.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(context_json.read_text(encoding="utf-8"))["records"][0]["context_id"], "ctx-owner")

        task_pack = run_cli(["holodeck", "task-pack", "--workspace-id", "hd-context", "--task-id", "hd-context-task"])
        self.assertTrue(any("context_record: ctx-owner::owner_surface::Holodeck CLI owner" in item for item in task_pack["constraints"]))

    def test_cli_holodeck_contextualizing_stage_accepts_novel_outcome_without_fake_anchor(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-context-novel",
                "--title",
                "Novel",
                "--goal",
                "Zephyr",
                "--purpose",
                "Novel",
            ]
        )
        run_cli(
            [
                "holodeck",
                "advance-stage",
                "--workspace-id",
                "hd-context-novel",
                "--stage",
                "contextualizing",
                "--reason",
                "Need contextual grounding",
            ]
        )

        before = run_cli(["holodeck", "check", "--workspace-id", "hd-context-novel"])
        self.assertFalse(before["stage_ok"])
        self.assertEqual(before["stage_gaps"][0]["code"], "missing_contextualization_outcome")

        run_cli(
            [
                "holodeck",
                "event",
                "--workspace-id",
                "hd-context-novel",
                "--kind",
                "contextualization_outcome_recorded",
                "--summary",
                "Bounded retrieval found no strong inherited anchors.",
                "--content",
                "This workspace appears novel relative to current static project knowledge.",
                "--tags",
                "outcome:novel,confidence:bounded",
            ]
        )

        after = run_cli(["holodeck", "check", "--workspace-id", "hd-context-novel"])
        self.assertTrue(after["stage_ok"])
        self.assertEqual(after["counts"]["stage_gaps"], 0)
        self.assertEqual(after["snapshot"]["contextualization_summary"]["status"], "novel")
        self.assertTrue(after["snapshot"]["contextualization_summary"]["resolved"])

    def test_cli_holodeck_contextualize_emits_bounded_inherited_context_and_knowledge(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        plan_path = self.root / "docs" / "plans" / "chat-bridge.md"
        plan_path.write_text(
            "# Chat Bridge\n\n"
            "The chat bridge should preserve the private cognitive layer philosophy and use bounded semantic assist.\n",
            encoding="utf-8",
        )
        meta_dir = meta_layer_dir(self.root)
        meta_dir.mkdir(parents=True, exist_ok=True)
        write_jsonl(
            meta_dir / META_LAYER_FILES["guardrail"],
            [
                {
                    "meta_id": "guardrail-bounded-assist",
                    "kind": "guardrail",
                    "label": "Bounded Semantic Assist",
                    "summary": "Models may improve surfaced semantics, but they must not control core retrieval truth.",
                    "status": "approved_for_surface",
                    "confidence": 0.92,
                    "source_refs": ["docs/plans/bounded-assist.md"],
                    "chunk_ids": [],
                    "evidence": [],
                    "attributes": {},
                }
            ],
        )

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-contextualize",
                "--title",
                "Chat",
                "--goal",
                "Bridge",
                "--purpose",
                "Chat",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-constraint",
                "--workspace-id",
                "hd-contextualize",
                "--constraint-id",
                "con-explicit-contextualize",
                "--constraint-kind",
                "contextualization_opt_out",
                "--statement",
                "Keep automatic contextualization off so this test exercises the explicit command path.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "ingest-artifact",
                "--workspace-id",
                "hd-contextualize",
                "--artifact-kind",
                "plan",
                "--title",
                "Chat Bridge Plan",
                "--source-ref",
                str(plan_path.relative_to(self.root)),
                "--source-type",
                "repo_file",
                "--provenance",
                "canonical",
                "--summary",
                "Chat bridge plan for bounded semantic assist.",
            ]
        )

        result = run_cli(
            [
                "holodeck",
                "contextualize",
                "--workspace-id",
                "hd-contextualize",
                "--reason",
                "Need inherited context before scoping",
            ]
        )

        self.assertEqual(result["status"], "completed")
        self.assertGreaterEqual(result["candidate_count"], 2)
        self.assertGreaterEqual(len(result["emitted_context_ids"]), 1)
        self.assertGreaterEqual(len(result["emitted_record_ids"]), 1)
        self.assertEqual(result["contextualization_summary"]["status"], "inherited")

        status = run_cli(["holodeck", "status", "--workspace-id", "hd-contextualize"])
        self.assertEqual(status["contextualization_summary"]["status"], "inherited")
        self.assertTrue(any(item["context_kind"] == "philosophy_context" for item in status["context_records"]))
        self.assertFalse(status["contextualization_summary"].get("stale", True))

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-contextualize"])
        knowledge = checked["snapshot"]["knowledge_counts"]
        self.assertIn("constraint", knowledge)
        self.assertTrue(checked["contextualization_ok"])
        self.assertTrue(checked["contextualization_fresh"])
        self.assertEqual(checked["contextualization_gaps"], [])

        materialized = run_cli(["holodeck", "materialize", "--workspace-id", "hd-contextualize"])
        contextualization_md = Path(materialized["materialized_paths"]["contextualization"])
        contextualization_json = Path(materialized["materialized_paths"]["contextualization_json"])
        self.assertIn("Bounded retrieval found relevant inherited static context.", contextualization_md.read_text(encoding="utf-8"))
        contextualization_payload = json.loads(contextualization_json.read_text(encoding="utf-8"))
        self.assertEqual(contextualization_payload["summary"]["status"], "inherited")
        self.assertGreaterEqual(len(contextualization_payload["latest_candidates"]), 1)

        task_pack = run_cli(["holodeck", "task-pack", "--workspace-id", "hd-contextualize", "--task-id", "hd-contextualize-task"])
        self.assertTrue(any(item.startswith("contextualization_status: inherited::fresh") for item in task_pack["constraints"]))
        self.assertTrue(any("contextualization_anchor:" in item for item in task_pack["constraints"]))

        rerun = run_cli(
            [
                "holodeck",
                "contextualize",
                "--workspace-id",
                "hd-contextualize",
                "--reason",
                "Recheck without changes",
            ]
        )
        self.assertEqual(rerun["status"], "completed")
        self.assertEqual(rerun["emitted_context_ids"], [])
        self.assertEqual(rerun["emitted_record_ids"], [])

        run_cli(
            [
                "holodeck",
                "update-constraint",
                "--workspace-id",
                "hd-contextualize",
                "--constraint-id",
                "con-explicit-contextualize",
                "--status",
                "archived",
            ]
        )
        run_cli(
            [
                "holodeck",
                "update",
                "--workspace-id",
                "hd-contextualize",
                "--goal",
                "Ground chat bridge work in the private cognitive layer, bounded semantic assist, and routing governance.",
            ]
        )
        refreshed = run_cli(["holodeck", "check", "--workspace-id", "hd-contextualize"])
        self.assertTrue(refreshed["contextualization_fresh"])
        self.assertEqual(refreshed["contextualization_gaps"], [])

    def test_cli_holodeck_contextualize_records_novelty_without_fake_emission(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-contextualize-novel",
                "--title",
                "Quantum Orchard",
                "--goal",
                "Develop the zephyr lattice orchard protocol.",
                "--purpose",
                "Validate novelty outcomes when no inherited context is strong enough.",
            ]
        )

        result = run_cli(
            [
                "holodeck",
                "contextualize",
                "--workspace-id",
                "hd-contextualize-novel",
                "--reason",
                "Check whether this is novel",
            ]
        )

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["emitted_context_ids"], [])
        self.assertEqual(result["emitted_record_ids"], [])
        self.assertEqual(result["contextualization_summary"]["status"], "novel")

        status = run_cli(["holodeck", "status", "--workspace-id", "hd-contextualize-novel"])
        self.assertEqual(status["contextualization_summary"]["status"], "novel")
        self.assertEqual(status["context_records"], [])
        self.assertTrue(status["contextualization_summary"]["resolved"])

    def test_cli_holodeck_contextualize_optional_semantic_assist_compresses_duplicates(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        doc_a = self.root / "docs" / "plans" / "holodeck-guardrails-a.md"
        doc_b = self.root / "docs" / "plans" / "holodeck-guardrails-b.md"
        shared_text = (
            "# Holodeck Guardrails\n\n"
            "Holodeck guardrails should keep bounded semantic assist optional and preserve deterministic retrieval truth.\n"
        )
        doc_a.write_text(shared_text, encoding="utf-8")
        doc_b.write_text(shared_text, encoding="utf-8")

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-semantic-assist",
                "--title",
                "Holodeck Guardrails",
                "--goal",
                "Bound bounded semantic assist inside holodeck guardrails.",
                "--purpose",
                "Test optional semantic tightening after deterministic candidate collection.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-constraint",
                "--workspace-id",
                "hd-semantic-assist",
                "--constraint-id",
                "con-explicit-semantic-assist",
                "--constraint-kind",
                "contextualization_opt_out",
                "--statement",
                "Keep automatic contextualization off so this test exercises explicit semantic assist only.",
            ]
        )

        baseline = run_cli(
            [
                "holodeck",
                "contextualize",
                "--workspace-id",
                "hd-semantic-assist",
                "--mode",
                "suggest",
                "--reason",
                "Collect deterministic duplicate candidates first",
            ]
        )
        duplicate_titles = [
            item["title"]
            for item in baseline["top_candidates"]
            if item.get("title") == "Holodeck Guardrails"
        ]
        self.assertGreaterEqual(len(duplicate_titles), 2)
        self.assertFalse(baseline["semantic_assist_used"])

        assisted = run_cli(
            [
                "holodeck",
                "contextualize",
                "--workspace-id",
                "hd-semantic-assist",
                "--mode",
                "suggest",
                "--allow-semantic-assist",
                "--reason",
                "Tighten duplicate contextualization candidates",
            ]
        )

        self.assertTrue(assisted["semantic_assist_used"])
        self.assertLess(len(assisted["top_candidates"]), len(baseline["top_candidates"]))
        top_candidate = assisted["top_candidates"][0]
        self.assertIn("why_it_matters", top_candidate)
        self.assertGreaterEqual(top_candidate.get("semantic_group_size", 1), 2)
        self.assertEqual(sorted(top_candidate.get("semantic_source_refs", [])), sorted([
            "docs/plans/holodeck-guardrails-a.md",
            "docs/plans/holodeck-guardrails-b.md",
        ]))
        materialized = run_cli(["holodeck", "materialize", "--workspace-id", "hd-semantic-assist"])
        contextualization_payload = json.loads(Path(materialized["materialized_paths"]["contextualization_json"]).read_text(encoding="utf-8"))
        self.assertTrue(contextualization_payload["semantic_assist_used"])
        self.assertIn("why_it_matters", contextualization_payload["latest_candidates"][0])

    def test_cli_holodeck_create_auto_contextualizes_when_seed_is_sufficient(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        created = run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-auto-create",
                "--title",
                "Holodeck Context Bridge",
                "--goal",
                "Ground holodeck context bridge work in the private cognitive layer and bounded semantic assist.",
                "--purpose",
                "Auto-contextualize immediately when enough seed signal exists.",
            ]
        )

        self.assertIn("auto_contextualization", created)
        self.assertTrue(created["auto_contextualization"]["triggered"])
        self.assertEqual(created["auto_contextualization"]["trigger"], "create")
        self.assertFalse(created["auto_contextualization"]["semantic_assist_used"])
        self.assertTrue(created["auto_contextualization"]["contextualization_summary"]["resolved"])

        status = run_cli(["holodeck", "status", "--workspace-id", "hd-auto-create"])
        self.assertTrue(status["contextualization_summary"]["has_run"])
        self.assertTrue(status["contextualization_summary"]["fresh"])

    def test_cli_holodeck_update_auto_reruns_contextualization_when_seed_changes(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        created = run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-auto-update",
                "--title",
                "Routing Grounding",
                "--goal",
                "Ground routing work in holodeck context and bounded semantic assist.",
                "--purpose",
                "Establish an initial contextualization run before the seed changes.",
            ]
        )
        first_run_id = created["auto_contextualization"]["run_id"]

        updated = run_cli(
            [
                "holodeck",
                "update",
                "--workspace-id",
                "hd-auto-update",
                "--goal",
                "Ground routing work in holodeck context, bounded semantic assist, and routing governance.",
            ]
        )
        self.assertIn("auto_contextualization", updated)
        self.assertTrue(updated["auto_contextualization"]["triggered"])
        self.assertEqual(updated["auto_contextualization"]["trigger"], "update")
        self.assertNotEqual(updated["auto_contextualization"]["run_id"], first_run_id)

        status = run_cli(["holodeck", "status", "--workspace-id", "hd-auto-update"])
        self.assertTrue(status["contextualization_summary"]["fresh"])
        self.assertEqual(status["contextualization_summary"]["latest_run_id"], updated["auto_contextualization"]["run_id"])

    def test_cli_holodeck_status_respects_contextualization_opt_out(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        created = run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-auto-opt-out",
                "--title",
                "Auto Context Opt Out",
                "--goal",
                "Ground holodeck context bridge work in the private cognitive layer and bounded semantic assist.",
                "--purpose",
                "Establish an initial automatic contextualization run before opting out.",
            ]
        )
        initial_run_id = created["auto_contextualization"]["run_id"]
        run_cli(
            [
                "holodeck",
                "add-constraint",
                "--workspace-id",
                "hd-auto-opt-out",
                "--constraint-id",
                "con-opt-out",
                "--constraint-kind",
                "contextualization_opt_out",
                "--statement",
                "Do not run automatic contextualization for this workspace yet.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "update",
                "--workspace-id",
                "hd-auto-opt-out",
                "--goal",
                "Ground holodeck context bridge work in the private cognitive layer, bounded semantic assist, and routing governance.",
            ]
        )

        status = run_cli(["holodeck", "status", "--workspace-id", "hd-auto-opt-out"])
        self.assertTrue(status["contextualization_summary"]["has_run"])
        self.assertTrue(status["contextualization_summary"]["stale"])
        self.assertEqual(status["contextualization_summary"]["latest_run_id"], initial_run_id)

    def test_cli_holodeck_constraint_records_bound_scoping_and_task_packs(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-constraints",
                "--title",
                "Constraints",
                "--goal",
                "Bound the work",
                "--purpose",
                "Validate explicit constraint records",
            ]
        )
        run_cli(
            [
                "holodeck",
                "advance-stage",
                "--workspace-id",
                "hd-constraints",
                "--stage",
                "scoping",
                "--reason",
                "Need explicit boundaries",
            ]
        )

        before = run_cli(["holodeck", "check", "--workspace-id", "hd-constraints"])
        self.assertFalse(before["stage_ok"])
        self.assertEqual({item["code"] for item in before["stage_gaps"]}, {"missing_scope_in", "missing_scope_out"})

        created = run_cli(
            [
                "holodeck",
                "add-constraint",
                "--workspace-id",
                "hd-constraints",
                "--constraint-id",
                "con-scope-in",
                "--constraint-kind",
                "scope_in",
                "--statement",
                "Implement only the Holodeck CLI boundary surface.",
                "--applies-to",
                "src/conversation_os/cli.py",
                "--severity",
                "required",
                "--source-refs",
                "docs/plans/2026-04-26-holodeck-workspace-architecture.md",
            ]
        )
        self.assertEqual(created["constraint_id"], "con-scope-in")

        run_cli(
            [
                "holodeck",
                "add-constraint",
                "--workspace-id",
                "hd-constraints",
                "--constraint-id",
                "con-scope-out",
                "--constraint-kind",
                "scope_out",
                "--statement",
                "Do not edit storage ownership in this slice.",
                "--severity",
                "required",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-constraint",
                "--workspace-id",
                "hd-constraints",
                "--constraint-id",
                "con-stop",
                "--constraint-kind",
                "stop_condition",
                "--statement",
                "Stop if the guard is not ready.",
                "--severity",
                "blocking",
            ]
        )

        updated = run_cli(
            [
                "holodeck",
                "update-constraint",
                "--workspace-id",
                "hd-constraints",
                "--constraint-id",
                "con-stop",
                "--statement",
                "Stop if engineering guard is not ready.",
            ]
        )
        self.assertTrue(updated["updated"])
        self.assertEqual(updated["statement"], "Stop if engineering guard is not ready.")

        after = run_cli(["holodeck", "check", "--workspace-id", "hd-constraints"])
        self.assertTrue(after["stage_ok"])
        self.assertEqual(after["counts"]["constraint_records"], 3)
        self.assertEqual(after["counts"]["stop_conditions"], 1)
        self.assertEqual(after["constraint_records"][0]["constraint_id"], "con-scope-in")

        materialized = run_cli(["holodeck", "materialize", "--workspace-id", "hd-constraints"])
        constraints_md = Path(materialized["materialized_paths"]["constraints"])
        constraints_json = Path(materialized["materialized_paths"]["constraints_json"])
        self.assertIn("Stop if engineering guard is not ready.", constraints_md.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(constraints_json.read_text(encoding="utf-8"))["records"][2]["constraint_id"], "con-stop")

        task_pack = run_cli(["holodeck", "task-pack", "--workspace-id", "hd-constraints", "--task-id", "hd-constraints-task"])
        self.assertTrue(any("constraint_record: con-stop::stop_condition::blocking::Stop if engineering guard is not ready." in item for item in task_pack["constraints"]))

    def test_cli_holodeck_integration_targets_ground_integrating_stage(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-integrate",
                "--title",
                "Integration",
                "--goal",
                "Embed the objective",
                "--purpose",
                "Validate explicit integration targets",
            ]
        )
        run_cli(
            [
                "holodeck",
                "advance-stage",
                "--workspace-id",
                "hd-integrate",
                "--stage",
                "integrating",
                "--reason",
                "Need destination before closure",
            ]
        )

        before = run_cli(["holodeck", "check", "--workspace-id", "hd-integrate"])
        self.assertFalse(before["stage_ok"])
        self.assertEqual(before["stage_gaps"][0]["code"], "missing_integration_target")

        created = run_cli(
            [
                "holodeck",
                "add-integration-target",
                "--workspace-id",
                "hd-integrate",
                "--target-id",
                "target-cli",
                "--target-kind",
                "code",
                "--title",
                "Holodeck CLI integration",
                "--destination-ref",
                "src/conversation_os/cli.py",
                "--required-evidence-refs",
                "tests/test_conversation_os.py::test_cli_holodeck_integration_targets_ground_integrating_stage",
                "--source-refs",
                "docs/plans/2026-04-26-holodeck-workspace-architecture.md",
            ]
        )
        self.assertEqual(created["target_id"], "target-cli")

        updated = run_cli(
            [
                "holodeck",
                "update-integration-target",
                "--workspace-id",
                "hd-integrate",
                "--target-id",
                "target-cli",
                "--status",
                "ready",
            ]
        )
        self.assertTrue(updated["updated"])
        self.assertEqual(updated["status"], "ready")

        after = run_cli(["holodeck", "check", "--workspace-id", "hd-integrate"])
        self.assertTrue(after["stage_ok"])
        self.assertEqual(after["counts"]["integration_targets"], 1)
        self.assertEqual(after["integration_targets"][0]["target_id"], "target-cli")

        materialized = run_cli(["holodeck", "materialize", "--workspace-id", "hd-integrate"])
        targets_md = Path(materialized["materialized_paths"]["integration_targets"])
        targets_json = Path(materialized["materialized_paths"]["integration_targets_json"])
        self.assertIn("Holodeck CLI integration", targets_md.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(targets_json.read_text(encoding="utf-8"))["targets"][0]["target_id"], "target-cli")

        task_pack = run_cli(["holodeck", "task-pack", "--workspace-id", "hd-integrate", "--task-id", "hd-integrate-task"])
        self.assertTrue(any("integration_target: target-cli::code::Holodeck CLI integration::src/conversation_os/cli.py" in item for item in task_pack["constraints"]))

    def test_cli_holodeck_run_contracts_bound_execution_and_surface_active_run(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-run",
                "--title",
                "Run Contracts",
                "--goal",
                "Bound agent execution",
                "--purpose",
                "Validate first-class Holodeck run contracts",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-run",
                "--work-item-id",
                "wi-run",
                "--title",
                "Implement run contracts",
                "--kind",
                "task",
            ]
        )

        with self.assertRaises(ValueError) as error:
            run_cli(
                [
                    "holodeck",
                    "start-run",
                    "--workspace-id",
                    "hd-run",
                    "--run-id",
                    "run-missing-stop",
                    "--work-item-id",
                    "wi-run",
                    "--purpose",
                    "This run should be rejected because it has no stop conditions.",
                    "--allowed-paths",
                    "src/conversation_os/cli.py",
                    "--verification-plan",
                    "Run focused Holodeck regression tests.",
                    "--context-budget",
                    "6",
                ]
            )
        self.assertIn("stop condition", str(error.exception).lower())

        started = run_cli(
            [
                "holodeck",
                "start-run",
                "--workspace-id",
                "hd-run",
                "--run-id",
                "run-1",
                "--work-item-id",
                "wi-run",
                "--purpose",
                "Implement the Holodeck run-contract slice.",
                "--allowed-paths",
                "src/conversation_os/cli.py",
                "--allowed-paths",
                "tests/test_conversation_os.py",
                "--blocked-paths",
                "src/conversation_os/storage.py",
                "--allowed-commands",
                "python3 -m unittest",
                "--expected-outputs",
                "run_contracts.md",
                "--verification-plan",
                "Run focused Holodeck tests and the full conversation_os suite.",
                "--context-budget",
                "6",
                "--stop-conditions",
                "Stop if engineering guard is not ready.",
                "--stop-conditions",
                "Stop if the edit requires storage ownership changes.",
            ]
        )
        self.assertEqual(started["run_id"], "run-1")
        self.assertEqual(started["status"], "active")

        status_payload = run_cli(["holodeck", "status", "--workspace-id", "hd-run"])
        self.assertEqual(status_payload["active_run"]["run_id"], "run-1")
        self.assertEqual(status_payload["active_run"]["active_work_item_id"], "wi-run")
        self.assertEqual(status_payload["active_run"]["context_budget"], 6)
        self.assertEqual(status_payload["run_contract_status_counts"]["active"], 1)

        materialized = run_cli(["holodeck", "materialize", "--workspace-id", "hd-run"])
        runs_md = Path(materialized["materialized_paths"]["runs"])
        runs_json = Path(materialized["materialized_paths"]["runs_json"])
        self.assertIn("run-1", runs_md.read_text(encoding="utf-8"))
        self.assertEqual(json.loads(runs_json.read_text(encoding="utf-8"))["active_run"]["run_id"], "run-1")

        task_pack = run_cli(["holodeck", "task-pack", "--workspace-id", "hd-run", "--task-id", "hd-run-task"])
        self.assertTrue(any("active_run: run-1::wi-run::Implement the Holodeck run-contract slice." in item for item in task_pack["constraints"]))
        self.assertTrue(any("run_allowed_path: src/conversation_os/cli.py" in item for item in task_pack["constraints"]))
        self.assertTrue(any("run_stop_condition: Stop if engineering guard is not ready." in item for item in task_pack["constraints"]))

        finished = run_cli(
            [
                "holodeck",
                "finish-run",
                "--workspace-id",
                "hd-run",
                "--run-id",
                "run-1",
                "--status",
                "completed",
                "--summary",
                "Implemented and verified the run-contract slice.",
                "--verification-result",
                "Focused Holodeck tests and the full conversation_os suite passed.",
            ]
        )
        self.assertTrue(finished["updated"])
        self.assertEqual(finished["status"], "completed")
        self.assertTrue(finished["ended_at"])

        after = run_cli(["holodeck", "status", "--workspace-id", "hd-run"])
        self.assertIsNone(after["active_run"])
        self.assertEqual(after["latest_run"]["run_id"], "run-1")
        self.assertEqual(after["latest_run"]["status"], "completed")

    def test_cli_holodeck_check_tracks_required_proof_surfaces_and_local_only_posture(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-proof",
                "--title",
                "Proof Discipline",
                "--goal",
                "Separate local green from live proof",
                "--purpose",
                "Track proof surfaces explicitly inside Holodeck",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-proof",
                "--work-item-id",
                "wi-proof",
                "--title",
                "Implement bridge-facing proof checks",
            ]
        )
        run_cli(
            [
                "holodeck",
                "start-run",
                "--workspace-id",
                "hd-proof",
                "--run-id",
                "run-proof",
                "--work-item-id",
                "wi-proof",
                "--purpose",
                "Finish the proof-surface slice locally before live validation.",
                "--allowed-paths",
                "src/conversation_os/holodeck.py",
                "--verification-plan",
                "Run the focused proof tests locally.",
                "--context-budget",
                "4",
                "--stop-conditions",
                "Stop if proof posture is still ambiguous.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "finish-run",
                "--workspace-id",
                "hd-proof",
                "--run-id",
                "run-proof",
                "--status",
                "completed",
                "--summary",
                "Finished locally.",
                "--verification-result",
                "Focused local proof tests passed.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-constraint",
                "--workspace-id",
                "hd-proof",
                "--constraint-id",
                "proof-local",
                "--constraint-kind",
                "proof_requirement",
                "--statement",
                "Local CLI proof is required before broader claims.",
                "--applies-to",
                "local_cli",
                "--severity",
                "required",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-constraint",
                "--workspace-id",
                "hd-proof",
                "--constraint-id",
                "proof-live",
                "--constraint-kind",
                "proof_requirement",
                "--statement",
                "An external client must prove the live bridge path.",
                "--applies-to",
                "external_client",
                "--severity",
                "required",
            ]
        )
        run_cli(
            [
                "holodeck",
                "event",
                "--workspace-id",
                "hd-proof",
                "--kind",
                "proof_recorded",
                "--summary",
                "Local CLI proof passed.",
                "--source-refs",
                "tests/test_conversation_os.py",
                "--tags",
                "surface:local_cli,status:verified",
            ]
        )

        status_payload = run_cli(["holodeck", "status", "--workspace-id", "hd-proof"])
        self.assertEqual(status_payload["proof_summary"]["proof_posture"], "local_only")
        self.assertEqual(status_payload["proof_summary"]["highest_verified_surface"], "local_cli")
        self.assertEqual(status_payload["proof_summary"]["unverified_required_surfaces"], ["external_client"])

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-proof"])
        self.assertFalse(checked["proof_ok"])
        self.assertEqual(checked["counts"]["proof_gaps"], 1)
        self.assertEqual(checked["proof_gaps"][0]["code"], "required_proof_missing")
        self.assertEqual(checked["proof_gaps"][0]["surface"], "external_client")

        task_pack = run_cli(["holodeck", "task-pack", "--workspace-id", "hd-proof", "--task-id", "hd-proof-task"])
        self.assertTrue(any("proof_verified_surface: local_cli" in item for item in task_pack["constraints"]))
        self.assertTrue(any("proof_gap: external_client" in item for item in task_pack["constraints"]))

    def test_cli_holodeck_check_flags_completed_work_without_declared_proof_requirements(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-proof-missing",
                "--title",
                "Proof Missing",
                "--goal",
                "Catch overclaims from local-only completion",
                "--purpose",
                "Warn when completed work has no declared proof requirements",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-proof-missing",
                "--work-item-id",
                "wi-proof-missing",
                "--title",
                "Complete the slice locally",
            ]
        )
        run_cli(
            [
                "holodeck",
                "start-run",
                "--workspace-id",
                "hd-proof-missing",
                "--run-id",
                "run-proof-missing",
                "--work-item-id",
                "wi-proof-missing",
                "--purpose",
                "Finish the slice locally with no declared proof requirements.",
                "--allowed-paths",
                "src/conversation_os/holodeck.py",
                "--verification-plan",
                "Run the local suite.",
                "--context-budget",
                "2",
                "--stop-conditions",
                "Stop if the change needs live validation.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "finish-run",
                "--workspace-id",
                "hd-proof-missing",
                "--run-id",
                "run-proof-missing",
                "--status",
                "completed",
                "--summary",
                "Completed locally.",
                "--verification-result",
                "Local suite passed.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "event",
                "--workspace-id",
                "hd-proof-missing",
                "--kind",
                "proof_recorded",
                "--summary",
                "Local CLI proof passed.",
                "--tags",
                "surface:local_cli,status:verified",
            ]
        )

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-proof-missing"])
        self.assertFalse(checked["proof_ok"])
        self.assertEqual(checked["counts"]["proof_gaps"], 1)
        self.assertEqual(checked["proof_gaps"][0]["code"], "proof_requirements_missing_for_completed_run")
        self.assertEqual(checked["proof_summary"]["proof_posture"], "local_only")

    def test_cli_holodeck_check_requires_completion_contracts_before_execution(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-contracts",
                "--title",
                "Contract Discipline",
                "--goal",
                "Prevent premature execution",
                "--purpose",
                "Require verification and proof contracts before implementation work is treated as ready.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-contracts",
                "--work-item-id",
                "impl-1",
                "--title",
                "Implement contract-sensitive behavior",
                "--kind",
                "implementation",
                "--status",
                "proposed",
            ]
        )

        before = run_cli(["holodeck", "check", "--workspace-id", "hd-contracts"])
        self.assertFalse(before["healthy"])
        self.assertFalse(before["execution_ready"])
        self.assertEqual(
            {item["code"] for item in before["completion_contract_gaps"]},
            {"missing_test_contract", "missing_proof_contract"},
        )

        run_cli(
            [
                "holodeck",
                "add-test",
                "--workspace-id",
                "hd-contracts",
                "--test-id",
                "test-1",
                "--work-item-id",
                "impl-1",
                "--target-ref",
                "src/conversation_os/holodeck.py",
                "--intent",
                "Verify contract-sensitive readiness behavior",
                "--command-or-protocol",
                "python3 -m unittest tests.test_conversation_os",
                "--expected-signal",
                "New contract checks pass",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-constraint",
                "--workspace-id",
                "hd-contracts",
                "--constraint-id",
                "proof-cli",
                "--constraint-kind",
                "proof_requirement",
                "--statement",
                "CLI behavior must be verified before treating the work as working.",
                "--applies-to",
                "local_cli",
            ]
        )

        after = run_cli(["holodeck", "check", "--workspace-id", "hd-contracts"])
        self.assertEqual(after["completion_contract_gaps"], [])
        self.assertTrue(after["execution_ready"])

    def test_cli_holodeck_check_reports_context_budget_exceeded(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-budget",
                "--title",
                "Budget",
                "--goal",
                "Track context consumption",
                "--purpose",
                "Validate real context-budget warnings",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-budget",
                "--work-item-id",
                "wi-budget",
                "--title",
                "Implement budget telemetry",
            ]
        )
        run_cli(
            [
                "holodeck",
                "start-run",
                "--workspace-id",
                "hd-budget",
                "--run-id",
                "run-budget",
                "--work-item-id",
                "wi-budget",
                "--purpose",
                "Implement the Holodeck context-budget slice.",
                "--allowed-paths",
                "src/conversation_os/cli.py",
                "--allowed-paths",
                "docs/plans/2026-04-26-holodeck-workspace-architecture.md",
                "--verification-plan",
                "Run focused budget tests.",
                "--context-budget",
                "3",
                "--stop-conditions",
                "Stop if the context budget is exceeded.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "log-context",
                "--workspace-id",
                "hd-budget",
                "--summary",
                "Loaded CLI owner surface",
                "--source-refs",
                "src/conversation_os/cli.py",
                "--units",
                "2",
                "--reason",
                "Need the current Holodeck owner implementation.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "log-context",
                "--workspace-id",
                "hd-budget",
                "--summary",
                "Loaded plan details",
                "--source-refs",
                "docs/plans/2026-04-26-holodeck-workspace-architecture.md",
                "--units",
                "2",
                "--reason",
                "Need the remaining backlog details.",
            ]
        )

        status_payload = run_cli(["holodeck", "status", "--workspace-id", "hd-budget"])
        self.assertEqual(status_payload["active_run"]["run_id"], "run-budget")
        self.assertEqual(status_payload["active_run_context_units"], 4)

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-budget"])
        self.assertFalse(checked["drift_free"])
        self.assertEqual(checked["counts"]["drift_warnings"], 1)
        self.assertEqual(checked["drift_warnings"][0]["code"], "context_budget_exceeded")

    def test_cli_holodeck_check_reports_command_drift_against_allowed_commands(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-command",
                "--title",
                "Command Drift",
                "--goal",
                "Track executed commands",
                "--purpose",
                "Validate allowed command enforcement",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-command",
                "--work-item-id",
                "wi-command",
                "--title",
                "Implement command telemetry",
            ]
        )
        run_cli(
            [
                "holodeck",
                "start-run",
                "--workspace-id",
                "hd-command",
                "--run-id",
                "run-command",
                "--work-item-id",
                "wi-command",
                "--purpose",
                "Implement the Holodeck command-telemetry slice.",
                "--allowed-paths",
                "src/conversation_os/cli.py",
                "--verification-plan",
                "Run focused command drift tests.",
                "--context-budget",
                "4",
                "--stop-conditions",
                "Stop if command execution leaves the declared run contract.",
                "--allowed-commands",
                "python3 -m unittest",
            ]
        )
        run_cli(
            [
                "holodeck",
                "log-command",
                "--workspace-id",
                "hd-command",
                "--summary",
                "Ran an undeclared command",
                "--command-ref",
                "uv run pytest tests/test_conversation_os.py",
                "--reason",
                "Investigating command drift behavior.",
            ]
        )

        status_payload = run_cli(["holodeck", "status", "--workspace-id", "hd-command"])
        self.assertEqual(status_payload["active_run"]["run_id"], "run-command")
        self.assertEqual(status_payload["active_run_command_count"], 1)

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-command"])
        self.assertFalse(checked["drift_free"])
        self.assertEqual(checked["counts"]["drift_warnings"], 1)
        self.assertEqual(checked["drift_warnings"][0]["code"], "command_outside_allowed_commands")

    def test_cli_holodeck_check_reports_work_expansion_outside_active_run(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-expansion",
                "--title",
                "Work Expansion",
                "--goal",
                "Catch silent scope expansion",
                "--purpose",
                "Validate run drift for new work items outside the active objective",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-expansion",
                "--work-item-id",
                "wi-active",
                "--title",
                "Implement expansion warning",
            ]
        )
        run_cli(
            [
                "holodeck",
                "start-run",
                "--workspace-id",
                "hd-expansion",
                "--run-id",
                "run-expand",
                "--work-item-id",
                "wi-active",
                "--purpose",
                "Implement the Holodeck work-expansion warning slice.",
                "--allowed-paths",
                "src/conversation_os/cli.py",
                "--verification-plan",
                "Run focused expansion tests.",
                "--context-budget",
                "4",
                "--stop-conditions",
                "Stop if the work expands beyond the declared objective.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-expansion",
                "--work-item-id",
                "wi-new",
                "--title",
                "Unplanned follow-on work",
            ]
        )

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-expansion"])
        self.assertFalse(checked["drift_free"])
        self.assertEqual(checked["counts"]["drift_warnings"], 1)
        self.assertEqual(checked["drift_warnings"][0]["code"], "work_item_expansion_outside_active_run")

    def test_cli_holodeck_check_reports_boundary_warnings_for_stale_and_blocked_path_touch(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-drift",
                "--title",
                "Drift",
                "--goal",
                "Catch boundary drift",
                "--purpose",
                "Validate Holodeck drift warnings",
            ]
        )
        run_cli(
            [
                "holodeck",
                "add-work-item",
                "--workspace-id",
                "hd-drift",
                "--work-item-id",
                "wi-drift",
                "--title",
                "Implement drift checks",
            ]
        )
        run_cli(
            [
                "holodeck",
                "advance-stage",
                "--workspace-id",
                "hd-drift",
                "--stage",
                "developing",
                "--reason",
                "Keep this drift test outside automatic contextualization stages.",
            ]
        )
        run_cli(
            [
                "holodeck",
                "start-run",
                "--workspace-id",
                "hd-drift",
                "--run-id",
                "run-drift",
                "--work-item-id",
                "wi-drift",
                "--purpose",
                "Implement the Holodeck drift-warning slice.",
                "--allowed-paths",
                "src/conversation_os/cli.py",
                "--blocked-paths",
                "src/conversation_os/storage.py",
                "--verification-plan",
                "Run focused drift tests.",
                "--context-budget",
                "4",
                "--stop-conditions",
                "Stop if the work leaves the Holodeck CLI owner surface.",
            ]
        )

        before = run_cli(["holodeck", "check", "--workspace-id", "hd-drift"])
        self.assertEqual(before["counts"]["drift_warnings"], 1)
        self.assertEqual(before["drift_warnings"][0]["code"], "stale_active_run")

        run_cli(
            [
                "holodeck",
                "event",
                "--workspace-id",
                "hd-drift",
                "--kind",
                "note",
                "--summary",
                "Touched blocked path",
                "--source-refs",
                "src/conversation_os/storage.py",
            ]
        )

        after = run_cli(["holodeck", "check", "--workspace-id", "hd-drift"])
        self.assertTrue(
            {"touched_blocked_path", "source_ref_outside_allowed_paths"}.issubset(
                {item["code"] for item in after["drift_warnings"]}
            )
        )

    def test_cli_holodeck_check_reports_completed_run_missing_verification_evidence(self) -> None:
        def run_cli(args: list[str]) -> dict:
            stdout = StringIO()
            with mock.patch("pathlib.Path.cwd", return_value=self.root), redirect_stdout(stdout):
                exit_code = main(args)
            self.assertEqual(exit_code, 0)
            return json.loads(stdout.getvalue())

        run_cli(
            [
                "holodeck",
                "create",
                "--workspace-id",
                "hd-drift-verify",
                "--title",
                "Drift Verification",
                "--goal",
                "Catch malformed completed runs",
                "--purpose",
                "Validate verification drift warnings",
            ]
        )

        write_jsonl(
            self.root / "memory" / "workspaces" / "hd-drift-verify" / "run_contracts.jsonl",
            [
                {
                    "operation": "create",
                    "run_id": "run-bad",
                    "workspace_id": "hd-drift-verify",
                    "active_work_item_id": "",
                    "active_maturation_stage": "developing",
                    "purpose": "Malformed completed run",
                    "allowed_paths": ["src/conversation_os/cli.py"],
                    "blocked_paths": [],
                    "allowed_commands": ["python3 -m unittest"],
                    "expected_outputs": [],
                    "verification_plan": "Run the full suite.",
                    "verification_result": "",
                    "context_budget": 3,
                    "stop_conditions": ["Stop if verification cannot run."],
                    "summary": "Completed without evidence.",
                    "status": "completed",
                    "started_at": "2026-04-28T00:00:00+00:00",
                    "ended_at": "2026-04-28T01:00:00+00:00",
                    "updated_at": "2026-04-28T01:00:00+00:00",
                }
            ],
        )

        checked = run_cli(["holodeck", "check", "--workspace-id", "hd-drift-verify"])
        self.assertEqual(checked["counts"]["drift_warnings"], 1)
        self.assertEqual(checked["drift_warnings"][0]["code"], "completed_run_missing_verification")

    def test_collect_constraint_violations_dedupes_by_constraint_and_target(self) -> None:
        violations = _collect_constraint_violations(
            events=[
                {
                    "source_refs": [
                        "src/conversation_os/storage.py",
                        "docs/notes.md",
                        "docs/notes.md",
                    ]
                }
            ],
            work_items=[
                {
                    "work_item_id": "wi-ui",
                    "status": "in_progress",
                }
            ],
            constraint_records=[
                {
                    "constraint_id": "con-allow",
                    "constraint_kind": "allowed_path",
                    "applies_to": "src/conversation_os/cli.py",
                },
                {
                    "constraint_id": "con-block",
                    "constraint_kind": "blocked_path",
                    "applies_to": "src/conversation_os/storage.py",
                },
                {
                    "constraint_id": "con-non-goal",
                    "constraint_kind": "non_goal",
                    "applies_to": "wi-ui",
                },
            ],
        )

        self.assertEqual(len(violations), 4)
        self.assertEqual(
            {item["code"] for item in violations},
            {
                "blocked_path_touched",
                "source_ref_outside_constraint_allowed_paths",
                "active_non_goal_work_item",
            },
        )

    def test_collect_run_drift_warnings_combines_run_boundaries_and_expansion(self) -> None:
        warnings = _collect_run_drift_warnings(
            events=[
                {
                    "timestamp": "2026-04-28T00:00:01+00:00",
                    "kind": "command_executed",
                    "command_ref": "uv run pytest tests/test_conversation_os.py",
                    "source_refs": ["src/conversation_os/storage.py", "docs/notes.md", "docs/notes.md"],
                }
            ],
            work_item_rows=[
                {
                    "timestamp": "2026-04-28T00:00:02+00:00",
                    "operation": "create",
                    "work_item_id": "wi-new",
                    "payload": {},
                }
            ],
            active_run={
                "run_id": "run-1",
                "started_at": "2026-04-28T00:00:00+00:00",
                "active_work_item_id": "wi-active",
                "allowed_paths": ["src/conversation_os/cli.py"],
                "blocked_paths": ["src/conversation_os/storage.py"],
                "allowed_commands": ["python3 -m unittest"],
                "context_budget": 3,
            },
            snapshot={"active_run_context_units": 5},
        )

        self.assertEqual(
            {item["code"] for item in warnings},
            {
                "command_outside_allowed_commands",
                "touched_blocked_path",
                "source_ref_outside_allowed_paths",
                "context_budget_exceeded",
                "work_item_expansion_outside_active_run",
            },
        )

    def test_collect_completed_run_drift_warnings_only_reports_missing_evidence(self) -> None:
        warnings = _collect_completed_run_drift_warnings(
            [
                {
                    "run_id": "run-good",
                    "status": "completed",
                    "verification_result": "suite passed",
                },
                {
                    "run_id": "run-bad",
                    "status": "completed",
                    "verification_result": "",
                },
                {
                    "run_id": "run-active",
                    "status": "active",
                    "verification_result": "",
                },
            ]
        )

        self.assertEqual(warnings, [
            {
                "code": "completed_run_missing_verification",
                "message": "Completed run run-bad has no verification result.",
                "run_id": "run-bad",
                "source_ref": "",
            }
        ])

    def test_engineering_guard_allows_adjacent_owner_extraction_when_existing_owner_stays_in_scope(self) -> None:
        with (
            mock.patch(
                "conversation_os.engineering_guard.refresh_codebase_overview",
                return_value=None,
            ),
            mock.patch(
                "conversation_os.engineering_guard._path_exists_or_can_exist",
                return_value=True,
            ),
            mock.patch(
                "conversation_os.engineering_guard.lookup_codebase",
                return_value=[
                    {
                        "path": "src/conversation_os/cli.py",
                        "kind": "python",
                        "area": "conversation_os",
                        "summary": "CLI owner",
                        "symbols": [],
                        "score": 10,
                        "matched_tokens": ["holodeck", "owner"],
                    }
                ],
            ),
        ):
            assessed = assess_change_request(
                self.root,
                request="Extract Holodeck workspace logic from the CLI owner into a dedicated module.",
                purpose="Perform a behavior-preserving owner extraction so Holodeck can move into a dedicated adjacent module while cli.py remains in scope as the existing owner.",
                proposed_paths=[
                    "src/conversation_os/cli.py",
                    "src/conversation_os/holodeck.py",
                    "tests/test_conversation_os.py",
                ],
            )

        self.assertTrue(assessed["ready"])
        self.assertEqual(assessed["status"], "ready")
        self.assertEqual(assessed["warnings"], [])

    def test_engineering_guard_blocks_when_codebase_index_is_not_ready(self) -> None:
        with (
            mock.patch(
                "conversation_os.engineering_guard.refresh_codebase_overview",
                return_value=None,
            ),
            mock.patch(
                "conversation_os.engineering_guard.validate_codebase_index",
                return_value={
                    "generated_at": "2026-05-22T00:00:00+00:00",
                    "module_manifest_count": 57,
                    "error_count": 0,
                    "warning_count": 1,
                    "missing_manifest_count": 0,
                    "fresh": False,
                    "stale_reasons": ["Generated codebase artifacts are older than the newest tracked source or manifest (context/substrate/registry/owner_index.json < src/conversation_os/cli.py)."],
                    "missing_artifacts": [],
                    "newest_source_path": "src/conversation_os/cli.py",
                    "newest_generated_path": "context/substrate/registry/owner_index.json",
                    "errors": [],
                    "warnings": ["1 tracked python modules do not yet have manifests"],
                    "missing_paths": [],
                },
            ),
            mock.patch(
                "conversation_os.engineering_guard._path_exists_or_can_exist",
                return_value=True,
            ),
            mock.patch(
                "conversation_os.engineering_guard.lookup_codebase",
                return_value=[
                    {
                        "path": "src/conversation_os/cli.py",
                        "kind": "python",
                        "area": "conversation_os",
                        "summary": "CLI owner",
                        "symbols": [],
                        "score": 10,
                        "matched_tokens": ["index", "guard"],
                    }
                ],
            ),
        ):
            assessed = assess_change_request(
                self.root,
                request="Add codebase index freshness checks to the existing guard and CLI workflow",
                purpose="Block substantive implementation work when the module atlas or manifest validation is stale so agents refresh and validate the index first",
                proposed_paths=[
                    "src/conversation_os/cli.py",
                    "tests/test_conversation_os.py",
                ],
            )

        self.assertFalse(assessed["ready"])
        self.assertEqual(assessed["status"], "needs_index")
        self.assertEqual(assessed["blocking_issues"][0]["code"], "index_not_ready")
        self.assertIn("Codebase index is not ready:", assessed["warnings"][0])

    def test_holodeck_owner_module_exists(self) -> None:
        module = importlib.import_module("conversation_os.holodeck")
        self.assertTrue(hasattr(module, "holodeck_check"))
        self.assertTrue(hasattr(module, "holodeck_task_pack"))

    def test_gpt_bridge_openapi_exposes_holodeck_read_and_consequential_write_paths(self) -> None:
        schema = build_gpt_openapi("https://example.test")

        self.assertIn("/holodeck/list", schema["paths"])
        self.assertIn("/holodeck/status", schema["paths"])
        self.assertIn("/holodeck/check", schema["paths"])
        self.assertIn("/holodeck/task-pack", schema["paths"])
        self.assertIn("/holodeck/create", schema["paths"])
        self.assertIn("/holodeck/start-run", schema["paths"])
        self.assertTrue(schema["paths"]["/holodeck/create"]["post"]["x-openai-isConsequential"])
        self.assertTrue(schema["paths"]["/holodeck/start-run"]["post"]["x-openai-isConsequential"])
        self.assertIn("/holodeck/list", schema["paths"]["/holodeck/status"]["get"]["description"])
        self.assertIn("/holodeck/list", schema["paths"]["/holodeck/check"]["get"]["description"])

    def test_gpt_bridge_holodeck_endpoints_can_create_list_and_start_runs(self) -> None:
        bridge = InnerWorldGPTBridge(root=self.root, action_key="test-key")

        created = bridge.holodeck_create(
            title="Founder Deck",
            goal="Turn an idea into a production-shaped feature",
            purpose="Incubate the feature inside a bounded workspace.",
            success_condition="Ready to integrate",
            scope_in=["founder lens"],
            scope_out=["unrelated cleanup"],
            template_key="founder",
            domains=["founder"],
            founder_wedge="Fast incubation",
            founder_user="Founder",
            founder_moat="Grounded process",
            founder_gtm_risk="Adoption",
            founder_launch_metric="approved_holodecks",
        )

        workspace_id = created["workspace_id"]
        listed = bridge.holodeck_list()
        self.assertTrue(any(item["workspace_id"] == workspace_id for item in listed["workspaces"]))

        status_payload = bridge.holodeck_status(workspace_id)
        self.assertEqual(status_payload["workspace_id"], workspace_id)
        self.assertEqual(status_payload["template_key"], "founder")

        checked = bridge.holodeck_check(workspace_id)
        self.assertEqual(checked["workspace_id"], workspace_id)
        self.assertIn("questions_for_user", checked)

        work_item = bridge.holodeck_add_work_item(
            workspace_id,
            title="Define the founder objective",
            acceptance_criteria=["Objective is explicit"],
        )
        run = bridge.holodeck_start_run(
            workspace_id,
            purpose="Clarify the founder objective without drifting into implementation.",
            work_item_id=work_item["work_item_id"],
            allowed_paths=["docs/plans"],
            allowed_commands=["rg"],
            verification_plan=["Review resulting task pack"],
            stop_conditions=["Stop when objective is crisply framed"],
            context_budget="small",
        )

        self.assertEqual(run["workspace_id"], workspace_id)
        status_after = bridge.holodeck_status(workspace_id)
        self.assertEqual(status_after["active_run"]["run_id"], run["run_id"])

    def test_gpt_bridge_holodeck_missing_workspace_returns_actionable_hint(self) -> None:
        bridge = InnerWorldGPTBridge(root=self.root, action_key="test-key")
        handler = make_gpt_bridge_handler(bridge)
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        sock.close()
        server = ThreadingHTTPServer((host, port), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = urllib_request.Request(
                f"http://{host}:{port}/holodeck/check?workspace_id=inner-world",
                headers={"X-Inner-World-Action-Key": "test-key"},
            )
            with self.assertRaises(urllib_error.HTTPError) as ctx:
                urllib_request.urlopen(request)
            self.assertEqual(ctx.exception.code, 404)
            payload = json.loads(ctx.exception.read().decode("utf-8"))
            self.assertEqual(payload["error"], "workspace_not_found")
            self.assertEqual(payload["workspace_id"], "inner-world")
            self.assertEqual(payload["suggested_action"], "call /holodeck/list before /holodeck/check")
            self.assertEqual(payload["available_workspaces"], [])
        finally:
            server.shutdown()
            server.server_close()

    def test_record_pond_routing_feedback_persists_learning_events(self) -> None:
        recorded = record_pond_routing_feedback(
            self.root,
            event_type="manual_pond_override",
            chunk_id="chunk-pond-1",
            source_ref="pond://inner-space",
            previous_primary_pond="domain_cognitive_science",
            new_primary_pond="project_inner_space",
            previous_pond_layers=["sense_making"],
            new_pond_layers=["product_vision_and_positioning"],
            actor="user",
            routing_method="manual",
            note="this thought belongs to the product basin",
        )
        self.assertEqual(recorded["status"], "recorded")
        rows = load_pond_routing_feedback(self.root)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["event_type"], "manual_pond_override")
        self.assertEqual(rows[0]["new_primary_pond"], "project_inner_space")

        status = get_pond_router_status(self.root)
        self.assertEqual(status["feedback_count"], 1)
        self.assertEqual(status["feedback_event_types"]["manual_pond_override"], 1)
        self.assertEqual(status["learning_summary"]["corrected_chunk_count"], 1)
        self.assertEqual(status["learning_summary"]["manual_override_count"], 1)
        self.assertEqual(
            status["learning_summary"]["top_pond_transitions"][0],
            {
                "previous_primary_pond": "domain_cognitive_science",
                "new_primary_pond": "project_inner_space",
                "count": 1,
            },
        )
        self.assertEqual(
            status["learning_summary"]["weak_primary_ponds"][0],
            {"pond_id": "domain_cognitive_science", "count": 1},
        )
        self.assertEqual(
            status["learning_summary"]["target_primary_ponds"][0],
            {"pond_id": "project_inner_space", "count": 1},
        )
        weak_layers = {row["layer"]: row["count"] for row in status["learning_summary"]["weak_layers"]}
        target_layers = {row["layer"]: row["count"] for row in status["learning_summary"]["target_layers"]}
        self.assertEqual(weak_layers["sense_making"], 1)
        self.assertEqual(target_layers["product_vision_and_positioning"], 1)

    def test_pond_router_learning_summary_aggregates_common_corrections(self) -> None:
        record_pond_routing_feedback(
            self.root,
            event_type="manual_pond_override",
            chunk_id="chunk-1",
            previous_primary_pond="domain_cognitive_science",
            new_primary_pond="project_inner_space",
            previous_pond_layers=["sense_making"],
            new_pond_layers=["frontend_and_capture_ux"],
            actor="user",
            routing_method="manual",
        )
        record_pond_routing_feedback(
            self.root,
            event_type="manual_pond_override",
            chunk_id="chunk-2",
            previous_primary_pond="domain_cognitive_science",
            new_primary_pond="project_inner_space",
            previous_pond_layers=["sense_making"],
            new_pond_layers=["product_vision_and_positioning"],
            actor="user",
            routing_method="manual",
        )
        record_pond_routing_feedback(
            self.root,
            event_type="manual_pond_layer_override",
            chunk_id="chunk-2",
            previous_primary_pond="project_inner_space",
            new_primary_pond="project_inner_space",
            previous_pond_layers=["frontend_and_capture_ux"],
            new_pond_layers=["deployment_and_infrastructure"],
            actor="operator",
            routing_method="manual",
        )

        summary = get_pond_router_status(self.root)["learning_summary"]
        self.assertEqual(summary["corrected_chunk_count"], 2)
        self.assertEqual(summary["manual_override_count"], 2)
        self.assertEqual(summary["layer_override_count"], 1)
        self.assertEqual(
            summary["top_pond_transitions"][0],
            {
                "previous_primary_pond": "domain_cognitive_science",
                "new_primary_pond": "project_inner_space",
                "count": 2,
            },
        )
        self.assertEqual(summary["weak_primary_ponds"][0], {"pond_id": "domain_cognitive_science", "count": 2})
        self.assertEqual(summary["target_primary_ponds"][0], {"pond_id": "project_inner_space", "count": 3})
        weak_layers = {row["layer"]: row["count"] for row in summary["weak_layers"]}
        target_layers = {row["layer"]: row["count"] for row in summary["target_layers"]}
        self.assertEqual(weak_layers["sense_making"], 2)
        self.assertEqual(weak_layers["frontend_and_capture_ux"], 1)
        self.assertEqual(target_layers["frontend_and_capture_ux"], 1)
        self.assertEqual(target_layers["product_vision_and_positioning"], 1)
        self.assertEqual(target_layers["deployment_and_infrastructure"], 1)

    def test_manual_chunk_pond_reroute_emits_learning_feedback(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Frontend",
            content="Thought Tube frontend and capture UX should improve the private cognitive layer.",
            source_ref="pond://manual-reroute",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "pond://manual-reroute")
        self.assertEqual(chunk["primary_pond"], "project_inner_space")

        update_chunk_governance(
            self.root,
            chunk["chunk_id"],
            dimension_overlays={
                "primary_pond": "project_klarorder",
                "pond_layer": ["sales_workflow"],
            },
            notes="manual reroute into product operations pond",
        )
        feedback_rows = load_pond_routing_feedback(self.root)
        self.assertEqual(len(feedback_rows), 1)
        self.assertEqual(feedback_rows[0]["event_type"], "manual_pond_override")
        self.assertEqual(feedback_rows[0]["previous_primary_pond"], "project_inner_space")
        self.assertEqual(feedback_rows[0]["new_primary_pond"], "project_klarorder")
        self.assertEqual(feedback_rows[0]["new_pond_layers"], ["sales_workflow"])

    def test_get_chunk_pond_routing_state_exposes_current_route_and_override_options(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Frontend",
            content="Thought Tube frontend and capture UX should improve the private cognitive layer.",
            source_ref="pond://inspect",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "pond://inspect")

        state = get_chunk_pond_routing_state(self.root, chunk["chunk_id"])
        self.assertEqual(state["primary_pond"], "project_inner_space")
        self.assertIn("frontend_and_capture_ux", state["pond_layers"])
        self.assertFalse(state["manual_override"])
        self.assertTrue(any(row["pond_id"] == "project_inner_space" for row in state["available_ponds"]))
        self.assertIn("frontend_and_capture_ux", state["allowed_layers"])

    def test_override_chunk_pond_routing_applies_manual_route_and_persists_feedback(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Frontend",
            content="Thought Tube frontend and capture UX should improve the private cognitive layer.",
            source_ref="pond://override",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "pond://override")

        result = override_chunk_pond_routing(
            self.root,
            chunk["chunk_id"],
            primary_pond="project_klarorder",
            pond_layers=["sales_workflow"],
            notes="manual move into klarorder sales workflow",
        )
        self.assertEqual(result["action"], "updated")
        self.assertEqual(result["pond_state"]["primary_pond"], "project_klarorder")
        self.assertEqual(result["pond_state"]["pond_layers"], ["sales_workflow"])
        self.assertTrue(result["pond_state"]["manual_override"])
        self.assertEqual(result["pond_state"]["manual_override_primary_pond"], "project_klarorder")
        self.assertEqual(result["pond_state"]["pond_routing_method"], "manual")
        self.assertEqual(result["pond_state"]["pond_confidence"], 1.0)
        self.assertEqual(load_pond_routing_feedback(self.root)[0]["new_primary_pond"], "project_klarorder")

    def test_override_chunk_pond_routing_rejects_invalid_layers(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Frontend",
            content="Thought Tube frontend and capture UX should improve the private cognitive layer.",
            source_ref="pond://invalid-layer",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "pond://invalid-layer")

        with self.assertRaises(ValueError):
            override_chunk_pond_routing(
                self.root,
                chunk["chunk_id"],
                primary_pond="project_inner_space",
                pond_layers=["sales_workflow"],
            )

    def test_override_chunk_pond_routing_can_clear_manual_override(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Frontend",
            content="Thought Tube frontend and capture UX should improve the private cognitive layer.",
            source_ref="pond://clear-override",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "pond://clear-override")
        override_chunk_pond_routing(
            self.root,
            chunk["chunk_id"],
            primary_pond="project_klarorder",
            pond_layers=["sales_workflow"],
            notes="temporary reroute",
        )

        cleared = override_chunk_pond_routing(
            self.root,
            chunk["chunk_id"],
            clear_override=True,
            notes="return to automatic routing",
        )
        self.assertEqual(cleared["action"], "cleared")
        self.assertFalse(cleared["pond_state"]["manual_override"])
        self.assertEqual(cleared["pond_state"]["primary_pond"], "project_inner_space")
        self.assertEqual(cleared["pond_state"]["pond_routing_method"], "heuristic")

    def test_product_chunk_pond_wrappers_delegate_to_substrate_owner(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Frontend",
            content="Thought Tube frontend and capture UX should improve the private cognitive layer.",
            source_ref="pond://product-wrapper",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "pond://product-wrapper")

        detail = get_chunk_pond_detail(self.root, chunk["chunk_id"])
        self.assertEqual(detail["primary_pond"], "project_inner_space")

        updated = update_chunk_pond_detail(
            self.root,
            chunk["chunk_id"],
            primary_pond="project_klarorder",
            pond_layers=["sales_workflow"],
            notes="product wrapper reroute",
        )
        self.assertEqual(updated["pond_state"]["primary_pond"], "project_klarorder")
        self.assertEqual(updated["pond_state"]["pond_routing_method"], "manual")

    def test_miniapp_chunk_pond_routes_support_inspect_update_and_clear(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Frontend",
            content="Thought Tube frontend and capture UX should improve the private cognitive layer.",
            source_ref="pond://miniapp-reroute",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "pond://miniapp-reroute")
        server, thread, base_url = self._start_test_miniapp_server()
        try:
            status, detail = self._json_request(f"{base_url}/api/chunk/{chunk['chunk_id']}/pond-routing")
            self.assertEqual(status, 200)
            self.assertEqual(detail["primary_pond"], "project_inner_space")
            self.assertFalse(detail["manual_override"])

            status, updated = self._json_request(
                f"{base_url}/api/chunk/{chunk['chunk_id']}/pond-routing",
                method="POST",
                payload={
                    "primary_pond": "project_klarorder",
                    "pond_layers": ["sales_workflow"],
                    "notes": "miniapp reroute",
                },
            )
            self.assertEqual(status, 200)
            self.assertEqual(updated["pond_state"]["primary_pond"], "project_klarorder")
            self.assertTrue(updated["pond_state"]["manual_override"])

            status, cleared = self._json_request(
                f"{base_url}/api/chunk/{chunk['chunk_id']}/pond-routing",
                method="POST",
                payload={"clear_override": True, "notes": "clear reroute"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(cleared["pond_state"]["primary_pond"], "project_inner_space")
            self.assertFalse(cleared["pond_state"]["manual_override"])
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_miniapp_chunk_pond_routes_validate_payloads(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Frontend",
            content="Thought Tube frontend and capture UX should improve the private cognitive layer.",
            source_ref="pond://miniapp-invalid",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "pond://miniapp-invalid")
        server, thread, base_url = self._start_test_miniapp_server()
        try:
            with self.assertRaises(urllib_error.HTTPError) as invalid_layers:
                self._json_request(
                    f"{base_url}/api/chunk/{chunk['chunk_id']}/pond-routing",
                    method="POST",
                    payload={"pond_layers": "sales_workflow"},
                )
            self.assertEqual(invalid_layers.exception.code, 400)

            with self.assertRaises(urllib_error.HTTPError) as missing_chunk:
                self._json_request(f"{base_url}/api/chunk/missing-chunk/pond-routing")
            self.assertEqual(missing_chunk.exception.code, 404)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_chunk_pond_routing_flows_into_dimension_profiles(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Frontend",
            content="Thought Tube frontend and capture UX should improve the private cognitive layer.",
            source_ref="pond://inner-space",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        chunk = load_chunk_index(self.root)[0]
        self.assertEqual(chunk["primary_pond"], "project_inner_space")
        self.assertIn("frontend_and_capture_ux", chunk["pond_layers"])
        self.assertGreater(chunk["pond_confidence"], 0.0)
        self.assertIn("Matched pond", chunk["pond_routing_justification"])

        profiles_payload = derive_chunk_dimension_profiles(self.root, chunk_rows=[chunk], persist=False)
        profile_map = {
            row["dimension_id"]: row
            for row in profiles_payload["profiles"]
        }
        self.assertEqual(profile_map["primary_pond"]["primary_value"], "project_inner_space")
        self.assertIn("frontend_and_capture_ux", profile_map["pond_layer"]["normalized_values"])

    def test_hybrid_pond_router_can_escalate_ambiguous_chunks_to_assisted_route(self) -> None:
        with mock.patch(
            "conversation_os.library_tracker.get_pond_router_status",
            return_value={
                "enabled": True,
                "mode": "hybrid",
                "assisted_on_ambiguity": True,
                "allow_manual_override": True,
                "ambiguity_threshold": 0.99,
                "router_version": "v2",
                "local_role_id": "pond_router_local",
                "judge_role_id": "pond_router_judge",
            },
        ), mock.patch(
            "conversation_os.library_tracker.classify_assisted_pond_route",
            return_value={
                "primary_pond": "project_klarorder",
                "touched_layers": ["sales_workflow"],
                "confidence": 0.93,
                "justification": "Ambiguous workflow language resolved toward Klarorder.",
                "model_role": "pond_router_local",
                "model_signature": "kimi-k2.5",
            },
        ):
            ingest_text_content(
                self.root,
                title="Ambiguous Workflow",
                content="Workflow and operator process should be routed correctly.",
                source_ref="pond://ambiguous",
                source_type="chat_converter_conversation",
                source_family="chat_converter",
            )
            chunk = next(row for row in load_chunk_index(self.root) if row["source_ref"] == "pond://ambiguous")
            self.assertEqual(chunk["primary_pond"], "project_klarorder")
            self.assertEqual(chunk["pond_layers"], ["sales_workflow"])
            self.assertEqual(chunk["pond_routing_method"], "assisted")
            self.assertEqual(chunk["pond_router_version"], "v2")
            self.assertEqual(chunk["pond_model_role"], "pond_router_local")
            self.assertEqual(chunk["pond_model_signature"], "kimi-k2.5")

    def test_dimension_search_respects_pond_boundaries_and_cross_pond_toggle(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Workflow",
            content="Thought Tube frontend workflow and capture UX should improve the private cognitive layer.",
            source_ref="pond://inner-space",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        ingest_text_content(
            self.root,
            title="Klarorder Workflow",
            content="B2B order processing workflow automation and sales workflow need cleanup.",
            source_ref="pond://klarorder",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )

        bounded = search_library_dimensions(
            self.root,
            dimensions=["source_family"],
            dimension_filters={"source_family": ["chat_converter"]},
            primary_pond="project_klarorder",
            limit=10,
        )
        self.assertEqual(bounded["filters"]["resolved_primary_pond"], "project_klarorder")
        self.assertTrue(bounded["results"])
        self.assertTrue(all(row["primary_pond"] == "project_klarorder" for row in bounded["results"]))

        cross = search_library_dimensions(
            self.root,
            dimensions=["source_family"],
            dimension_filters={"source_family": ["chat_converter"]},
            primary_pond="project_klarorder",
            include_cross_pond=True,
            limit=10,
        )
        ponds = {row["primary_pond"] for row in cross["results"]}
        self.assertIn("project_klarorder", ponds)
        self.assertIn("project_inner_space", ponds)
        self.assertTrue(any(row["cross_pond"] for row in cross["results"]))

    def test_retrieval_bundle_is_pond_bounded_unless_cross_pond_enabled(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Frontend",
            content="Thought Tube frontend and capture UX should improve the private cognitive layer.",
            source_ref="pond://inner-space",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        ingest_text_content(
            self.root,
            title="Klarorder Workflow",
            content="B2B order processing workflow automation and sales workflow need cleanup.",
            source_ref="pond://klarorder",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        data_dir = self.root / "product" / "inner_world_v1" / "data"
        write_jsonl(
            data_dir / "semantic_capsules.jsonl",
            [
                {
                    "capsule_id": "capsule-inner",
                    "capsule_type": "concept",
                    "ref_type": "concept",
                    "ref_id": "concept-inner",
                    "label": "Frontend Capture",
                    "summary": "frontend capture ux",
                    "status": "stable",
                    "confidence": 0.9,
                    "source_refs": ["pond://inner-space"],
                    "evidence_refs": [],
                    "linked_ref_ids": [],
                    "attributes": {},
                },
                {
                    "capsule_id": "capsule-klar",
                    "capsule_type": "concept",
                    "ref_type": "concept",
                    "ref_id": "concept-klar",
                    "label": "Order Workflow",
                    "summary": "workflow automation",
                    "status": "stable",
                    "confidence": 0.8,
                    "source_refs": ["pond://klarorder"],
                    "evidence_refs": [],
                    "linked_ref_ids": [],
                    "attributes": {},
                },
            ],
        )
        write_jsonl(
            data_dir / "context_links.jsonl",
            [
                {
                    "link_id": "link-1",
                    "layer": "semantic",
                    "kind": "related",
                    "from_ref_type": "concept",
                    "from_ref_id": "concept-inner",
                    "to_ref_type": "concept",
                    "to_ref_id": "concept-klar",
                    "status": "provisional",
                    "confidence": 0.9,
                    "evidence_refs": ["pond://inner-space", "pond://klarorder"],
                    "attributes": {},
                }
            ],
        )

        bounded = build_retrieval_bundle(self.root, "frontend capture ux")
        self.assertEqual(bounded["anchor_pond"], "project_inner_space")
        self.assertEqual([row["label"] for row in bounded["seed_capsules"]], ["Frontend Capture"])
        self.assertEqual(bounded["related_capsules"], [])

        cross = build_retrieval_bundle(self.root, "frontend capture ux", include_cross_pond=True)
        self.assertEqual(cross["anchor_pond"], "project_inner_space")
        self.assertEqual([row["label"] for row in cross["seed_capsules"]], ["Frontend Capture"])
        self.assertEqual([row["label"] for row in cross["related_capsules"]], ["Order Workflow"])

    def test_cross_pond_links_are_tagged_as_bridge_candidates_and_downweighted(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Frontend",
            content="Thought Tube frontend and capture UX should improve the private cognitive layer.",
            source_ref="pond://inner-space",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        ingest_text_content(
            self.root,
            title="Klarorder Workflow",
            content="B2B order processing workflow automation and sales workflow need cleanup.",
            source_ref="pond://klarorder",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        data_dir = self.root / "product" / "inner_world_v1" / "data"
        write_jsonl(
            data_dir / "semantic_capsules.jsonl",
            [
                {
                    "capsule_id": "capsule-inner",
                    "capsule_type": "concept",
                    "ref_type": "concept",
                    "ref_id": "concept-inner",
                    "label": "Frontend Capture",
                    "summary": "frontend capture ux",
                    "status": "stable",
                    "confidence": 0.9,
                    "source_refs": ["pond://inner-space"],
                    "evidence_refs": [],
                    "linked_ref_ids": [],
                    "attributes": {},
                },
                {
                    "capsule_id": "capsule-klar",
                    "capsule_type": "concept",
                    "ref_type": "concept",
                    "ref_id": "concept-klar",
                    "label": "Order Workflow",
                    "summary": "workflow automation",
                    "status": "stable",
                    "confidence": 0.8,
                    "source_refs": ["pond://klarorder"],
                    "evidence_refs": [],
                    "linked_ref_ids": [],
                    "attributes": {},
                },
            ],
        )
        write_jsonl(
            data_dir / "context_links.jsonl",
            [
                {
                    "link_id": "link-bridge",
                    "layer": "semantic",
                    "kind": "related",
                    "from_ref_type": "concept",
                    "from_ref_id": "concept-inner",
                    "to_ref_type": "concept",
                    "to_ref_id": "concept-klar",
                    "status": "provisional",
                    "confidence": 0.9,
                    "evidence_refs": ["pond://inner-space", "pond://klarorder"],
                    "attributes": {},
                }
            ],
        )

        link = load_context_links(self.root)[0]
        self.assertTrue(link["cross_pond"])
        self.assertEqual(link["bridge_status"], "candidate")
        self.assertEqual(link["from_pond_profile"]["primary_pond"], "project_inner_space")
        self.assertEqual(link["to_pond_profile"]["primary_pond"], "project_klarorder")
        self.assertAlmostEqual(link["confidence"], 0.82, places=2)

    def test_promoted_cross_pond_bridge_can_flow_without_cross_pond_toggle(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Frontend",
            content="Thought Tube frontend and capture UX should improve the private cognitive layer.",
            source_ref="pond://inner-space",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        ingest_text_content(
            self.root,
            title="Klarorder Workflow",
            content="B2B order processing workflow automation and sales workflow need cleanup.",
            source_ref="pond://klarorder",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        data_dir = self.root / "product" / "inner_world_v1" / "data"
        write_jsonl(
            data_dir / "semantic_capsules.jsonl",
            [
                {
                    "capsule_id": "capsule-inner",
                    "capsule_type": "concept",
                    "ref_type": "concept",
                    "ref_id": "concept-inner",
                    "label": "Frontend Capture",
                    "summary": "frontend capture ux",
                    "status": "stable",
                    "confidence": 0.9,
                    "source_refs": ["pond://inner-space"],
                    "evidence_refs": [],
                    "linked_ref_ids": [],
                    "attributes": {},
                },
                {
                    "capsule_id": "capsule-klar",
                    "capsule_type": "concept",
                    "ref_type": "concept",
                    "ref_id": "concept-klar",
                    "label": "Order Workflow",
                    "summary": "workflow automation",
                    "status": "stable",
                    "confidence": 0.8,
                    "source_refs": ["pond://klarorder"],
                    "evidence_refs": [],
                    "linked_ref_ids": [],
                    "attributes": {},
                },
            ],
        )
        write_jsonl(
            data_dir / "context_links.jsonl",
            [
                {
                    "link_id": "link-bridge",
                    "layer": "semantic",
                    "kind": "related",
                    "from_ref_type": "concept",
                    "from_ref_id": "concept-inner",
                    "to_ref_type": "concept",
                    "to_ref_id": "concept-klar",
                    "status": "provisional",
                    "confidence": 0.9,
                    "evidence_refs": ["pond://inner-space", "pond://klarorder"],
                    "attributes": {},
                }
            ],
        )
        govern_context_link(self.root, "link-bridge", governance_status="promoted", notes="intentional bridge")

        bounded = build_retrieval_bundle(self.root, "frontend capture ux")
        self.assertEqual(bounded["anchor_pond"], "project_inner_space")
        self.assertEqual([row["label"] for row in bounded["related_capsules"]], ["Order Workflow"])
        governed_link = load_context_links(self.root)[0]
        self.assertEqual(governed_link["bridge_status"], "promoted")
        self.assertGreater(governed_link["confidence"], 0.9)

    def test_miniapp_pond_aware_search_api_and_cross_pond_toggle(self) -> None:
        ingest_text_content(
            self.root,
            title="Inner World Workflow",
            content="Thought Tube frontend workflow and capture UX should improve the private cognitive layer.",
            source_ref="pond://inner-space",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        ingest_text_content(
            self.root,
            title="Klarorder Workflow",
            content="B2B order processing workflow automation and sales workflow need cleanup.",
            source_ref="pond://klarorder",
            source_type="chat_converter_conversation",
            source_family="chat_converter",
        )
        server, thread, base_url = self._start_test_miniapp_server()
        try:
            status, bounded = self._json_request(
                f"{base_url}/api/dimension-search?dimension=source_family&dimension_filter.source_family=chat_converter&primary_pond=project_klarorder"
            )
            self.assertEqual(status, 200)
            self.assertEqual(bounded["filters"]["resolved_primary_pond"], "project_klarorder")
            self.assertTrue(all(row["primary_pond"] == "project_klarorder" for row in bounded["results"]))

            status, cross = self._json_request(
                f"{base_url}/api/dimension-search?dimension=source_family&dimension_filter.source_family=chat_converter&primary_pond=project_klarorder&include_cross_pond=true"
            )
            self.assertEqual(status, 200)
            self.assertTrue(any(row["cross_pond"] for row in cross["results"]))
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    def test_rewrite_outgoing_message_updates_shared_bridge_state(self) -> None:
        self._write_personal_interface_profile()
        self._write_personal_interface_runtime()

        completed = mock.Mock(
            returncode=0,
            stdout=json.dumps({"adapted_text": "Short answer."}),
            stderr="",
        )
        with mock.patch("conversation_os.personal_interface.subprocess.run", return_value=completed):
            result = rewrite_outgoing_message(
                self.root,
                draft_text="Here is a longer draft that should be tightened.",
                user_message="I am overwhelmed right now. Keep it short and direct.",
                conversation_window=[{"role": "user", "content": "I am overwhelmed right now."}],
                caller_hints={"desired_depth": "short", "goal": "clarify_thinking"},
                client_context={"source_scope": "scoped_ocean", "conversation_turn_count": 3},
            )

        state = load_bridge_state(self.root)
        self.assertEqual(state["latest_rewrite_event_id"], result["rewrite_event_id"])
        self.assertEqual(state["current_mood"]["label"], "stressed")
        self.assertEqual(len(state["mood_history"]), 1)
        self.assertEqual(state["context"]["client_context"]["source_scope"], "scoped_ocean")
        self.assertEqual(state["presentation"]["current_mode"], "development_flow")
        self.assertEqual(state["presentation"]["communication_mode"], "scaffolded_guidance")
        self.assertIn("compress_response", state["presentation"]["applied_tactics"])
        pattern_keys = {row["pattern_key"] for row in state["behavior_patterns"]}
        self.assertIn("prefers_concise_answers", pattern_keys)
        self.assertIn("prefers_direct_language", pattern_keys)
        self.assertIn("requests_short_depth", pattern_keys)

    def test_rewrite_outgoing_message_tracks_quick_mood_history(self) -> None:
        self._write_personal_interface_profile()
        self._write_personal_interface_runtime()

        completed = mock.Mock(
            returncode=0,
            stdout=json.dumps({"adapted_text": "Adapted reply."}),
            stderr="",
        )
        with mock.patch("conversation_os.personal_interface.subprocess.run", return_value=completed):
            rewrite_outgoing_message(
                self.root,
                draft_text="First draft.",
                user_message="I am overwhelmed. Keep it tight.",
                caller_hints={"desired_depth": "short"},
                client_context={"conversation_turn_count": 1},
            )
            rewrite_outgoing_message(
                self.root,
                draft_text="Second draft.",
                user_message="I am curious what patterns connect these ideas.",
                caller_hints={"desired_depth": "deep", "goal": "generate_options"},
                client_context={"conversation_turn_count": 2},
            )

        state = load_bridge_state(self.root)
        self.assertEqual(state["current_mood"]["label"], "exploratory")
        self.assertEqual([row["label"] for row in state["mood_history"]], ["stressed", "exploratory"])
        self.assertLessEqual(len(state["mood_history"]), 6)


if __name__ == "__main__":
    unittest.main()
