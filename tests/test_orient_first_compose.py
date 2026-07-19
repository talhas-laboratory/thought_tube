from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.chat_backends import compose_execution_message, trim_context_bundle
from conversation_os.disclosure_contracts import ActiveStateSnapshot
from conversation_os.orient_first_compose import (
    ORIENTATION_MAX_CHARS,
    authorize_second_pass_widen,
    build_active_state_snapshot,
    compose_orient_first_message,
    message_section_index,
    render_orientation_text,
)
from conversation_os.reasoning_bridge import get_context_bundle, heuristic_classify_turn, orient_first_compose_enabled


class OrientFirstComposeTestCase(unittest.TestCase):
    def test_orientation_is_capped(self) -> None:
        snapshot = {
            "topic": "x" * 200,
            "purpose": "y" * 200,
            "object_scope": "same_main",
            "posture": "exploratory",
            "provenance": {"envelope_mode": "bounded"},
        }
        rendered = render_orientation_text(snapshot, max_chars=120)
        self.assertLessEqual(len(rendered), 120)
        self.assertTrue(rendered.endswith("..."))

    def test_snapshot_excludes_undisclosed_global(self) -> None:
        snapshot = build_active_state_snapshot(
            {
                "request_id": "req-orient-001",
                "active_topic": "bridge integration",
                "user_goal": "build",
                "reasoning_posture": "implementation",
                "object_scope": "same_main",
                "attributes": {
                    "session_id": "session-orient-001",
                    "caller_hints": {"workspace_id": "ws-orient", "thought_id": "thought-orient"},
                },
            },
            {
                "active_topic": "bridge integration",
                "user_goal": "build",
                "reasoning_posture": "implementation",
                "object_scope": "same_main",
            },
            workspace_layer={"workspace_id": "ws-orient", "thought_id": "thought-orient"},
            session_envelope={"mode": "bounded"},
        )
        ActiveStateSnapshot.from_dict(snapshot)
        self.assertTrue(snapshot["provenance"]["excludes_undisclosed_global"])
        self.assertNotIn("retrieval", " ".join(snapshot["derived_from"]).lower())

    def test_compose_order_is_orientation_constraints_evidence_user(self) -> None:
        control_packet = {
            "active_topic": "bridge execution",
            "user_goal": "build",
            "reasoning_posture": "implementation",
            "steering_constraints": ["preserve provenance"],
            "context_policy": {"mode": "semantic_narrow", "depth_mode": "contextual"},
        }
        trimmed = {
            "orient_first_compose_v1": True,
            "bundle_layers": ["session"],
            "session_envelope": {"mode": "bounded"},
            "active_state_snapshot": {
                "topic": "bridge execution",
                "purpose": "build",
                "object_scope": "same_main",
                "posture": "implementation",
                "provenance": {"envelope_mode": "bounded"},
            },
            "session_local": [{"actor": "user", "content": "prior turn"}],
            "frame_bundle": {"included_blocks": [], "provenance_summary": {"source_refs": []}},
        }
        message = compose_orient_first_message(control_packet, trimmed, "connect the bridge")
        orientation_idx = message_section_index(message, "Orientation")
        constraints_idx = message_section_index(message, "Steering constraints")
        evidence_idx = message_section_index(message, "Evidence")
        user_idx = message.find("User message:")
        self.assertLess(orientation_idx, constraints_idx)
        self.assertLess(constraints_idx, evidence_idx)
        self.assertLess(evidence_idx, user_idx)

    def test_no_evidence_message_remains_coherent(self) -> None:
        control_packet = {
            "active_topic": "empty aperture",
            "user_goal": "explore",
            "reasoning_posture": "exploratory",
            "steering_constraints": ["stay concise"],
            "context_policy": {"mode": "none", "depth_mode": "focused"},
        }
        trimmed = {
            "orient_first_compose_v1": True,
            "bundle_layers": [],
            "session_envelope": {"mode": "strict"},
            "active_state_snapshot": {
                "topic": "empty aperture",
                "purpose": "explore",
                "object_scope": "same_main",
                "posture": "exploratory",
                "provenance": {"envelope_mode": "strict"},
            },
            "session_local": [],
            "workspace_local": {},
            "user_local": {},
            "global_fallback": {"count": 0, "seed_capsules": []},
            "frame_bundle": {"included_blocks": [], "provenance_summary": {"source_refs": []}},
        }
        message = compose_orient_first_message(control_packet, trimmed, "what can you tell me?")
        self.assertIn("No disclosed evidence blocks are available for this turn", message)
        self.assertIn("Orientation:", message)
        self.assertIn("Steering constraints:", message)

    def test_second_pass_widen_requires_grant(self) -> None:
        allowed, _ = authorize_second_pass_widen(
            base_mode="session_only",
            proposed_mode="bounded_global",
            caller_hints={"second_pass_widen_grant_id": "grant-widen-001"},
        )
        blocked, reason = authorize_second_pass_widen(
            base_mode="session_only",
            proposed_mode="bounded_global",
            caller_hints={},
        )
        self.assertTrue(allowed)
        self.assertFalse(blocked)
        self.assertEqual(reason, "second_pass_widen_requires_new_grant")

    def test_compose_execution_message_uses_orient_first_path(self) -> None:
        control_packet = {
            "active_topic": "bridge execution",
            "user_goal": "build",
            "reasoning_posture": "implementation",
            "steering_constraints": ["preserve provenance"],
            "context_policy": {"mode": "semantic_narrow", "depth_mode": "contextual"},
        }
        bundle = {
            "orient_first_compose_v1": True,
            "bundle_layers": ["session"],
            "session_envelope": {"mode": "bounded"},
            "active_state_snapshot": {
                "topic": "bridge execution",
                "purpose": "build",
                "object_scope": "same_main",
                "posture": "implementation",
                "provenance": {"envelope_mode": "bounded"},
            },
            "session_local": [{"actor": "user", "content": "prior turn"}],
            "frame_bundle": {"included_blocks": [], "provenance_summary": {"source_refs": []}},
        }
        message = compose_execution_message(control_packet, bundle, "connect the bridge")
        self.assertIn("Orientation:", message)
        self.assertLess(message.find("Orientation:"), message.find("Steering constraints:"))
        self.assertLess(message.find("Steering constraints:"), message.find("Evidence:"))


class OrientFirstBundleIntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps({"bridge": {"orient_first_compose_v1": True}}),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_get_context_bundle_includes_active_state_snapshot(self) -> None:
        context = heuristic_classify_turn(
            self.root,
            {
                "request_id": "req-orient-bundle",
                "session_id": "",
                "raw_text": "orient first compose",
                "caller_hints": {"workspace_id": "ws-orient-bundle", "envelope_mode": "bounded"},
                "domain_hints": [],
                "source_refs": [],
            },
        )
        attributes = dict(context.get("attributes", {}) or {})
        attributes["context_policy"] = {
            "mode": "semantic_narrow",
            "depth_mode": "contextual",
            "token_budget": 900,
            "include_layers": ["session", "workspace"],
            "exclude_layers": ["global"],
            "cross_ocean": False,
            "retrieval_limit": 4,
            "neighbor_limit": 2,
            "envelope_mode": "bounded",
        }
        context["attributes"] = attributes
        bundle = get_context_bundle(self.root, context)
        self.assertTrue(orient_first_compose_enabled(self.root))
        self.assertIn("active_state_snapshot", bundle)
        self.assertTrue(bundle["active_state_snapshot"]["provenance"]["excludes_undisclosed_global"])
        trimmed = trim_context_bundle(bundle, attributes["context_policy"])
        message = compose_execution_message(
            {
                "active_topic": context.get("active_topic", ""),
                "user_goal": context.get("user_goal", ""),
                "reasoning_posture": context.get("reasoning_posture", ""),
                "steering_constraints": [],
                "context_policy": attributes["context_policy"],
            },
            trimmed,
            "orient first compose",
        )
        self.assertLess(message.find("Orientation:"), message.find("Evidence:"))
        self.assertLessEqual(
            len(render_orientation_text(bundle["active_state_snapshot"], max_chars=ORIENTATION_MAX_CHARS)),
            ORIENTATION_MAX_CHARS,
        )


if __name__ == "__main__":
    unittest.main()
