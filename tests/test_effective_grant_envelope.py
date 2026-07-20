from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.reasoning_bridge import (
    build_effective_grant_from_context,
    effective_layers_to_bridge_layers,
    get_context_bundle,
    heuristic_classify_turn,
)


class EffectiveGrantEnvelopeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _context_with_policy(self, policy: dict) -> dict:
        context = heuristic_classify_turn(
            self.root,
            {
                "request_id": "req-grant-001",
                "session_id": "",
                "raw_text": "build bridge integration",
                "caller_hints": {"workspace_id": "workspace-grant-001"},
                "domain_hints": [],
                "source_refs": [],
            },
        )
        attributes = dict(context.get("attributes", {}) or {})
        attributes["context_policy"] = policy
        context["attributes"] = attributes
        context["depth_mode"] = policy.get("depth_mode", context.get("depth_mode"))
        if policy.get("envelope_mode"):
            attributes.setdefault("caller_hints", {})["envelope_mode"] = policy["envelope_mode"]
        return context

    def test_open_envelope_allows_declared_layers(self) -> None:
        policy = {
            "mode": "graph_contextual",
            "depth_mode": "deep",
            "token_budget": 1200,
            "include_layers": ["session", "workspace", "user", "global"],
            "exclude_layers": [],
            "cross_ocean": True,
            "retrieval_limit": 8,
            "neighbor_limit": 4,
            "envelope_mode": "open",
        }
        context = self._context_with_policy(policy)
        context["attributes"]["caller_hints"]["envelope_mode"] = "open"
        bundle = get_context_bundle(self.root, context)
        grant = bundle["effective_grant"]
        self.assertEqual(grant["envelope"], "open")
        self.assertIn("session", bundle["context_state"]["bundle_layers"])

    def test_strict_envelope_blocks_global_and_user(self) -> None:
        policy = {
            "mode": "semantic_narrow",
            "depth_mode": "contextual",
            "token_budget": 900,
            "include_layers": ["session", "workspace", "user", "global"],
            "exclude_layers": ["global", "user"],
            "cross_ocean": False,
            "retrieval_limit": 4,
            "neighbor_limit": 2,
        }
        context = self._context_with_policy(policy)
        bundle = get_context_bundle(self.root, context)
        self.assertEqual(bundle["session_envelope"]["mode"], "strict")
        self.assertNotIn("global", bundle["context_state"]["bundle_layers"])
        self.assertNotIn("user", bundle["context_state"]["bundle_layers"])
        self.assertTrue(
            any(row.get("code") == "explicit_deny" for row in bundle["effective_grant"].get("narrowing_reasons", []))
            or "governed_global" not in bundle["effective_grant"].get("effective_layers", [])
        )

    def test_incognito_disables_ocean_retrieval_and_durable_learning(self) -> None:
        policy = {
            "mode": "none",
            "depth_mode": "incognito",
            "token_budget": 0,
            "include_layers": ["session", "global"],
            "exclude_layers": [],
            "cross_ocean": False,
            "retrieval_limit": 0,
            "neighbor_limit": 0,
        }
        context = self._context_with_policy(policy)
        bundle = get_context_bundle(self.root, context)
        self.assertEqual(bundle["effective_grant"]["envelope"], "incognito")
        self.assertEqual(bundle["effective_grant"]["persistence_mode"], "disabled")
        self.assertNotIn("global", bundle["context_state"]["bundle_layers"])
        self.assertEqual(bundle["global_fallback"]["count"], 0)

    def test_deny_precedence_wins_over_requested_layers(self) -> None:
        session_envelope = {"mode": "bounded", "persistence_mode": "gated", "explicit_excludes": ["user"]}
        policy = {
            "mode": "semantic_narrow",
            "depth_mode": "contextual",
            "token_budget": 1200,
            "include_layers": ["session", "workspace", "user"],
            "exclude_layers": ["user"],
            "cross_ocean": False,
            "retrieval_limit": 4,
            "neighbor_limit": 2,
        }
        grant = build_effective_grant_from_context(
            {"request_id": "req-deny", "source_refs": [], "attributes": {}},
            policy,
            session_envelope,
        )
        bridge_layers = effective_layers_to_bridge_layers(grant, ["session", "workspace", "user"])
        self.assertNotIn("user", bridge_layers)
        self.assertTrue(grant.deny_precedence_applied)


if __name__ == "__main__":
    unittest.main()
