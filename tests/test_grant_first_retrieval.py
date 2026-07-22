from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.reasoning_bridge import get_context_bundle, heuristic_classify_turn
from conversation_os.storage import append_jsonl


class GrantFirstRetrievalTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "bridge": {
                        "effective_grant_normalization_v1": True,
                        "execution_audit_isolation_v1": True,
                    },
                    "knowledge": {
                        "fail_empty_admission_shadow_v1": True,
                        "fail_empty_admission_enforce_v1": True,
                    },
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _context_with_policy(self, policy: dict, *, explicit_pins: list[str] | None = None) -> dict:
        context = heuristic_classify_turn(
            self.root,
            {
                "request_id": "req-grant-first-001",
                "session_id": "",
                "raw_text": "build bridge integration",
                "caller_hints": {"workspace_id": "workspace-grant-first-001"},
                "domain_hints": [],
                "source_refs": [],
            },
        )
        attributes = dict(context.get("attributes", {}) or {})
        attributes["context_policy"] = policy
        if explicit_pins is not None:
            attributes["explicit_pins"] = list(explicit_pins)
        context["attributes"] = attributes
        context["depth_mode"] = policy.get("depth_mode", context.get("depth_mode"))
        if policy.get("envelope_mode"):
            attributes.setdefault("caller_hints", {})["envelope_mode"] = policy["envelope_mode"]
        return context

    def _write_pinned_capsule(self) -> None:
        append_jsonl(
            self.root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl",
            {
                "capsule_id": "capsule-pin-001",
                "capsule_type": "concept",
                "label": "Pinned bridge note",
                "summary": "Operator pinned this capsule for strict recall.",
                "confidence": 0.42,
                "ref_type": "concept",
                "ref_id": "concept-pin-001",
                "source_refs": ["docs/plans/pinned-bridge.md"],
                "attributes": {},
            },
        )

    @mock.patch("conversation_os.reasoning_bridge.build_retrieval_bundle")
    def test_incognito_skips_candidate_search(self, search_mock: mock.MagicMock) -> None:
        context = self._context_with_policy(
            {
                "mode": "none",
                "depth_mode": "incognito",
                "token_budget": 0,
                "include_layers": ["session", "global"],
                "exclude_layers": [],
                "cross_ocean": False,
                "retrieval_limit": 6,
                "neighbor_limit": 4,
            }
        )
        search_mock.return_value = {"count": 0, "seed_capsules": [], "related_capsules": [], "source_refs": []}
        bundle = get_context_bundle(self.root, context)
        search_mock.assert_not_called()
        self.assertEqual(bundle["effective_grant"]["envelope"], "incognito")
        self.assertEqual(bundle["global_fallback"]["count"], 0)

    @mock.patch("conversation_os.reasoning_bridge.build_retrieval_bundle")
    def test_denied_global_skips_candidate_search(self, search_mock: mock.MagicMock) -> None:
        context = self._context_with_policy(
            {
                "mode": "semantic_narrow",
                "depth_mode": "contextual",
                "token_budget": 900,
                "include_layers": ["session", "workspace", "user", "global"],
                "exclude_layers": ["global", "user"],
                "cross_ocean": False,
                "retrieval_limit": 6,
                "neighbor_limit": 4,
            }
        )
        search_mock.return_value = {"count": 0, "seed_capsules": [], "related_capsules": [], "source_refs": []}
        bundle = get_context_bundle(self.root, context)
        search_mock.assert_not_called()
        self.assertEqual(bundle["session_envelope"]["mode"], "strict")
        self.assertNotIn("global", bundle["context_state"]["bundle_layers"])

    @mock.patch("conversation_os.reasoning_bridge.build_retrieval_bundle")
    def test_grant_first_passes_envelope_mode_and_explicit_pins(self, search_mock: mock.MagicMock) -> None:
        self._write_pinned_capsule()
        context = self._context_with_policy(
            {
                "mode": "semantic_narrow",
                "depth_mode": "contextual",
                "token_budget": 900,
                "include_layers": ["session", "workspace", "global"],
                "exclude_layers": [],
                "cross_ocean": False,
                "retrieval_limit": 4,
                "neighbor_limit": 2,
                "envelope_mode": "strict",
            },
            explicit_pins=["capsule:capsule-pin-001"],
        )
        search_mock.return_value = {
            "query": "build bridge integration",
            "seed_capsules": [],
            "related_capsules": [],
            "included_links": [],
            "source_refs": [],
            "count": 0,
            "alias_hits": [],
            "anchor_pond": "",
            "include_cross_pond": False,
            "envelope_mode": "strict",
        }
        get_context_bundle(self.root, context)
        search_mock.assert_called_once()
        kwargs = search_mock.call_args.kwargs
        self.assertEqual(kwargs["envelope_mode"], "strict")
        self.assertEqual(kwargs["explicit_pins"], ["capsule:capsule-pin-001"])
        self.assertFalse(kwargs["include_cross_pond"])

    @mock.patch("conversation_os.reasoning_bridge.build_retrieval_bundle")
    def test_explicit_pin_layer_invokes_search_without_governed_global(self, search_mock: mock.MagicMock) -> None:
        context = self._context_with_policy(
            {
                "mode": "semantic_narrow",
                "depth_mode": "contextual",
                "token_budget": 900,
                "include_layers": ["session"],
                "exclude_layers": ["global", "user", "workspace"],
                "cross_ocean": False,
                "retrieval_limit": 4,
                "neighbor_limit": 2,
                "envelope_mode": "strict",
            },
            explicit_pins=["capsule:capsule-pin-001"],
        )
        search_mock.return_value = {
            "query": "build bridge integration",
            "seed_capsules": [],
            "related_capsules": [],
            "included_links": [],
            "source_refs": [],
            "count": 0,
            "alias_hits": [],
            "anchor_pond": "",
            "include_cross_pond": False,
            "envelope_mode": "strict",
        }
        get_context_bundle(self.root, context)
        search_mock.assert_called_once()
        self.assertEqual(search_mock.call_args.kwargs["explicit_pins"], ["capsule:capsule-pin-001"])


if __name__ == "__main__":
    unittest.main()
