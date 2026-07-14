from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.reasoning_bridge import get_context_bundle, heuristic_classify_turn
from conversation_os.storage import append_jsonl


class ReasoningBridgePolicyTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _context_with_policy(self, policy: dict) -> dict:
        request = {
            "request_id": "req-policy-001",
            "session_id": "",
            "raw_text": "build bridge integration",
            "caller_hints": {"depth_mode": "deep", "workspace_id": "workspace-policy-001"},
            "domain_hints": [],
            "source_refs": [],
        }
        context = heuristic_classify_turn(self.root, request)
        attributes = dict(context.get("attributes", {}) or {})
        attributes["context_policy"] = policy
        context["attributes"] = attributes
        context["depth_mode"] = policy.get("depth_mode", context.get("depth_mode"))
        return context

    def test_include_layers_allowlist_excludes_undeclared_layers(self) -> None:
        context = self._context_with_policy(
            {
                "mode": "semantic_narrow",
                "depth_mode": "contextual",
                "token_budget": 1200,
                "include_layers": ["session"],
                "exclude_layers": [],
                "cross_ocean": False,
                "retrieval_limit": 6,
                "neighbor_limit": 4,
            }
        )
        bundle = get_context_bundle(self.root, context)
        self.assertEqual(bundle["context_state"]["bundle_layers"], ["session"])
        self.assertEqual(bundle["workspace_local"], {})
        self.assertEqual(bundle["global_fallback"]["count"], 0)

    def test_exclude_layers_removes_blocked_layers(self) -> None:
        context = self._context_with_policy(
            {
                "mode": "semantic_narrow",
                "depth_mode": "contextual",
                "token_budget": 1200,
                "include_layers": ["session", "workspace", "user", "global"],
                "exclude_layers": ["global", "user"],
                "cross_ocean": False,
                "retrieval_limit": 6,
                "neighbor_limit": 4,
            }
        )
        bundle = get_context_bundle(self.root, context)
        self.assertEqual(bundle["context_state"]["bundle_layers"], ["session", "workspace"])
        self.assertEqual(bundle["user_local"]["behavior_patterns"], [])

    def test_cross_ocean_false_disables_cross_pond_expansion(self) -> None:
        context = self._context_with_policy(
            {
                "mode": "graph_contextual",
                "depth_mode": "deep",
                "token_budget": 1200,
                "include_layers": ["global"],
                "exclude_layers": [],
                "cross_ocean": False,
                "retrieval_limit": 8,
                "neighbor_limit": 6,
            }
        )
        with mock.patch("conversation_os.reasoning_bridge.build_retrieval_bundle") as retrieval_mock:
            retrieval_mock.return_value = {"count": 1, "source_refs": [], "include_cross_pond": False}
            bundle = get_context_bundle(self.root, context)
        retrieval_mock.assert_called_once()
        self.assertFalse(retrieval_mock.call_args.kwargs["include_cross_pond"])
        self.assertEqual(bundle["global_fallback"]["count"], 1)

    def test_incognito_disables_global_retrieval(self) -> None:
        context = self._context_with_policy(
            {
                "mode": "none",
                "depth_mode": "incognito",
                "token_budget": 0,
                "include_layers": ["session", "global"],
                "exclude_layers": [],
                "cross_ocean": False,
                "retrieval_limit": 0,
                "neighbor_limit": 0,
            }
        )
        with mock.patch("conversation_os.reasoning_bridge.build_retrieval_bundle") as retrieval_mock:
            bundle = get_context_bundle(self.root, context)
        retrieval_mock.assert_not_called()
        self.assertNotIn("global", bundle["context_state"]["bundle_layers"])
        self.assertEqual(bundle["global_fallback"]["count"], 0)

    def test_get_context_bundle_emits_frame_preview_contracts(self) -> None:
        append_jsonl(
            self.root / "memory" / "events" / "session-policy-002.jsonl",
            {
                "event_id": "event-1",
                "session_id": "session-policy-002",
                "timestamp": "2026-06-26T17:10:00+00:00",
                "actor": "user",
                "kind": "message",
                "content": "Build bridge integration with frame previews.",
                "attachments": [],
                "tags": [],
                "source_ref": None,
            },
        )
        append_jsonl(
            self.root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl",
            {
                "capsule_id": "capsule-1",
                "capsule_type": "concept",
                "label": "Bridge integration",
                "summary": "A bridge path with inspectable context assembly.",
                "confidence": 0.92,
                "ref_type": "concept",
                "ref_id": "concept-bridge",
                "source_refs": ["memory/events/session-policy-002.jsonl"],
                "attributes": {"domain": "bridge"},
            },
        )

        context = heuristic_classify_turn(
            self.root,
            {
                "request_id": "req-policy-002",
                "session_id": "session-policy-002",
                "raw_text": "Build bridge integration with frame previews.",
                "caller_hints": {"workspace_id": "workspace-policy-002"},
                "domain_hints": ["bridge"],
                "source_refs": ["memory/events/session-policy-002.jsonl"],
            },
        )

        bundle = get_context_bundle(self.root, context)

        self.assertTrue(bundle["frame_spec"]["preview_only"])
        self.assertEqual(bundle["frame_bundle"]["frame_id"], bundle["frame_spec"]["frame_id"])
        self.assertEqual(bundle["session_envelope"]["mode"], "bounded")
        self.assertEqual(bundle["frame_bundle"]["assembly_status"], "complete")
        included_layers = {row["layer"] for row in bundle["frame_bundle"]["included_blocks"]}
        self.assertIn("session", included_layers)
        self.assertIn("workspace", included_layers)
        self.assertIn("global", included_layers)

    def test_frame_bundle_tracks_suppressed_layers_separately_from_disclosure(self) -> None:
        context = self._context_with_policy(
            {
                "mode": "semantic_narrow",
                "depth_mode": "contextual",
                "token_budget": 1200,
                "include_layers": ["session", "workspace", "user", "global"],
                "exclude_layers": ["global", "user"],
                "cross_ocean": False,
                "retrieval_limit": 6,
                "neighbor_limit": 4,
            }
        )
        with mock.patch("conversation_os.reasoning_bridge.build_retrieval_bundle") as retrieval_mock:
            with mock.patch("conversation_os.reasoning_bridge.load_bridge_state") as bridge_state_mock:
                retrieval_mock.return_value = {
                    "query": "build bridge integration",
                    "seed_capsules": [{"capsule_id": "capsule-1", "label": "bridge", "summary": "capsule"}],
                    "related_capsules": [],
                    "included_links": [],
                    "source_refs": ["memory/events/session-policy-001.jsonl"],
                    "count": 1,
                    "alias_hits": [],
                    "anchor_pond": "bridge",
                    "include_cross_pond": False,
                }
                bridge_state_mock.return_value = {
                    "behavior_patterns": [{"pattern_key": "prefer_sparse_context"}],
                    "personalization": {},
                    "presentation": {"current_mode": "sparse"},
                }
                bundle = get_context_bundle(self.root, context)

        self.assertEqual(bundle["context_state"]["bundle_layers"], ["session", "workspace"])
        self.assertEqual(bundle["session_envelope"]["mode"], "strict")
        self.assertEqual(bundle["session_envelope"]["explicit_excludes"], ["global", "user"])
        selector_layers = {row["layer"] for row in bundle["frame_spec"]["selectors"]}
        self.assertIn("user", selector_layers)
        self.assertIn("global", selector_layers)
        suppressed_layers = {row["layer"] for row in bundle["frame_bundle"]["suppressed_blocks"]}
        self.assertIn("user", suppressed_layers)
        self.assertIn("global", suppressed_layers)


class BridgeBehaviorSpecsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_load_bridge_behavior_specs_falls_back_to_embedded_rules(self) -> None:
        from conversation_os.reasoning_bridge import BRIDGE_BEHAVIOR_RULES, load_bridge_behavior_specs

        specs = load_bridge_behavior_specs(self.root)
        self.assertEqual(set(specs.keys()), set(BRIDGE_BEHAVIOR_RULES.keys()))

    def test_load_bridge_behavior_specs_reads_config_directory(self) -> None:
        from conversation_os.reasoning_bridge import load_bridge_behavior_specs

        behavior_dir = self.root / "product" / "inner_world_v1" / "config" / "bridge_behaviors"
        behavior_dir.mkdir(parents=True)
        (behavior_dir / "implementation_scaffold.json").write_text(
            json.dumps(
                {
                    "behavior_id": "implementation_scaffold",
                    "priority": 95,
                    "preferred_pipeline": "custom_pipeline_v1",
                    "routing_mode": "override",
                    "reasoning_posture": "implementation",
                    "response_directives": ["custom_step"],
                    "operator_biases": {},
                }
            ),
            encoding="utf-8",
        )

        specs = load_bridge_behavior_specs(self.root)
        self.assertEqual(specs["implementation_scaffold"]["preferred_pipeline"], "custom_pipeline_v1")
        self.assertEqual(specs["implementation_scaffold"]["priority"], 95)

    def test_bridge_candidate_package_uses_loaded_behavior_specs(self) -> None:
        from conversation_os.bridge_controller import build_bridge_candidate_package

        behavior_dir = self.root / "product" / "inner_world_v1" / "config" / "bridge_behaviors"
        behavior_dir.mkdir(parents=True)
        (behavior_dir / "implementation_scaffold.json").write_text(
            json.dumps(
                {
                    "behavior_id": "implementation_scaffold",
                    "priority": 95,
                    "preferred_pipeline": "custom_pipeline_v1",
                    "routing_mode": "override",
                    "reasoning_posture": "implementation",
                    "response_directives": ["custom_step"],
                    "operator_biases": {},
                }
            ),
            encoding="utf-8",
        )
        package = build_bridge_candidate_package(
            self.root,
            {"request_id": "req-001", "session_id": "", "raw_text": "build", "caller_hints": {}},
            retrieval_bundle={"count": 0},
            bridge_state={},
        )
        scaffold = next(row for row in package["behavior_menu"] if row["behavior_id"] == "implementation_scaffold")
        self.assertEqual(scaffold["preferred_pipeline"], "custom_pipeline_v1")


if __name__ == "__main__":
    unittest.main()
