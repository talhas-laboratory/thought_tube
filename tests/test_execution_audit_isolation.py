from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.chat_backends import compose_execution_message, trim_context_bundle
from conversation_os.disclosure_contracts import validate_execution_bundle
from conversation_os.reasoning_bridge import (
    assemble_frame_bundle,
    execution_audit_isolation_enabled,
    get_context_bundle,
    split_frame_assembly,
)


class ExecutionAuditIsolationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        runtime = self.root / "product" / "inner_world_v1" / "config"
        runtime.mkdir(parents=True)
        (runtime / "runtime.json").write_text(
            json.dumps({"bridge": {"execution_audit_isolation_v1": True}}),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_split_frame_assembly_removes_suppression_from_execution_bundle(self) -> None:
        assembly = {
            "bundle_id": "bundle-001",
            "frame_id": "frame-001",
            "request_id": "req-001",
            "session_id": "session-001",
            "workspace_id": "ws-001",
            "envelope_mode": "strict",
            "assembly_status": "partial",
            "included_blocks": [
                {
                    "block_id": "block-session",
                    "layer": "session",
                    "summary": "1 session event(s)",
                    "source_ref": "memory/events/session-001.jsonl",
                    "disclosure_state": "included",
                }
            ],
            "suppressed_blocks": [
                {
                    "block_id": "block-global",
                    "layer": "global",
                    "summary": "2 retrieval candidate(s)",
                    "source_ref": "retrieval:topic",
                    "disclosure_state": "suppressed",
                }
            ],
            "rejected_selectors": [],
            "provenance_summary": {
                "source_refs": ["memory/events/session-001.jsonl", "retrieval:topic"],
                "included_layer_count": 1,
                "suppressed_layer_count": 1,
            },
            "assembly_metrics": {"suppressed_block_count": 1, "estimated_token_cost": 100},
        }
        execution_bundle, frame_audit = split_frame_assembly(assembly)

        validate_execution_bundle(execution_bundle)
        self.assertNotIn("suppressed_blocks", execution_bundle)
        self.assertNotIn("disclosure_state", execution_bundle["included_blocks"][0])
        self.assertEqual(len(frame_audit["omitted_blocks"]), 1)
        self.assertEqual(frame_audit["omitted_blocks"][0]["reason_code"], "layer_not_disclosed")

    def test_compose_execution_message_omits_suppression_when_isolated(self) -> None:
        bundle = {
            "context_state": {"bundle_layers": ["session"]},
            "session_envelope": {"mode": "strict"},
            "frame_spec": {"frame_id": "frame-001"},
            "frame_bundle": {
                "frame_id": "frame-001",
                "assembly_status": "partial",
                "included_blocks": [{"layer": "session", "summary": "1 session event(s)"}],
            },
            "execution_audit_isolation_v1": True,
            "session_local": [{"actor": "user", "content": "hello"}],
            "workspace_local": {},
            "user_local": {},
            "global_fallback": {"count": 0},
        }
        message = compose_execution_message(
            {
                "active_topic": "topic",
                "user_goal": "build",
                "reasoning_posture": "implementation",
                "pipeline_id": "pipeline",
                "bridge_behaviors": [],
                "steering_constraints": [],
                "context_policy": {"mode": "semantic_narrow", "depth_mode": "contextual"},
            },
            trim_context_bundle(bundle),
            "user text",
        )
        self.assertNotIn("Suppressed frame blocks:", message)
        self.assertNotIn("suppressed", message.lower())

    def test_get_context_bundle_attaches_frame_audit_when_isolation_enabled(self) -> None:
        context = {
            "request_id": "req-isolation-001",
            "active_topic": "bridge integration",
            "active_workspace_id": "ws-isolation",
            "user_goal": "build",
            "reasoning_posture": "implementation",
            "depth_mode": "contextual",
            "bundle_layers": ["session", "workspace"],
            "source_refs": [],
            "attributes": {
                "session_id": "",
                "context_policy": {
                    "mode": "semantic_narrow",
                    "depth_mode": "contextual",
                    "token_budget": 1200,
                    "include_layers": ["session"],
                    "exclude_layers": ["global", "user"],
                    "cross_ocean": False,
                    "retrieval_limit": 4,
                    "neighbor_limit": 2,
                },
            },
        }
        with mock.patch("conversation_os.reasoning_bridge.build_retrieval_bundle") as retrieval_mock:
            with mock.patch("conversation_os.reasoning_bridge.load_bridge_state") as bridge_state_mock:
                retrieval_mock.return_value = {
                    "query": "bridge integration",
                    "count": 1,
                    "source_refs": ["retrieval:bridge"],
                }
                bridge_state_mock.return_value = {
                    "behavior_patterns": [{"pattern_key": "prefer_sparse_context"}],
                    "personalization": {},
                    "presentation": {"current_mode": "sparse"},
                }
                bundle = get_context_bundle(self.root, context)

        self.assertTrue(bundle["execution_audit_isolation_v1"])
        self.assertNotIn("suppressed_blocks", bundle["frame_bundle"])
        self.assertGreaterEqual(len(bundle["frame_audit"]["suppressed_blocks"]), 1)
        self.assertEqual(bundle["frame_bundle"]["frame_audit_id"], bundle["frame_audit"]["audit_id"])

    def test_rollback_flag_restores_legacy_suppression_on_frame_bundle(self) -> None:
        runtime_path = self.root / "product" / "inner_world_v1" / "config" / "runtime.json"
        runtime_path.write_text(
            json.dumps({"bridge": {"execution_audit_isolation_v1": False}}),
            encoding="utf-8",
        )
        self.assertFalse(execution_audit_isolation_enabled(self.root))
        assembly = assemble_frame_bundle(
            {"request_id": "req-rollback", "attributes": {"session_id": ""}, "active_workspace_id": "ws-1"},
            frame_spec={"frame_id": "frame-rollback", "selectors": [{"selector_id": "sel-global", "layer": "global"}]},
            envelope={"mode": "strict"},
            disclosed_layers=["session"],
            session_rows=[],
            workspace_layer={},
            user_patterns=[{"pattern_key": "x"}],
            bridge_state={},
            retrieval_bundle={"count": 1, "source_refs": ["retrieval:x"]},
        )
        self.assertIn("suppressed_blocks", assembly)
        self.assertGreaterEqual(len(assembly["suppressed_blocks"]), 1)


if __name__ == "__main__":
    unittest.main()
