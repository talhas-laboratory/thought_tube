from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.disclosure_rollout import (
    compare_bridge_rollout_bundles,
    in_canary_cohort,
    resolve_execution_path,
    resolve_surface_rollout_mode,
    shared_path_active,
)
from conversation_os.holodeck_disclosure_adapter import holodeck_disclosure_service_enabled
from conversation_os.reasoning_bridge import disclosure_service_enabled, get_context_bundle, heuristic_classify_turn


class DisclosureRolloutTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_runtime(self, payload: dict) -> None:
        path = self.root / "product" / "inner_world_v1" / "config" / "runtime.json"
        path.write_text(json.dumps(payload), encoding="utf-8")

    def test_release_runtime_keeps_rollout_disabled_until_cutover(self) -> None:
        release_runtime = json.loads(
            (Path(__file__).resolve().parents[1] / "product" / "inner_world_v1" / "config" / "runtime.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(release_runtime["bridge"].get("disclosure_service_v1"))
        self.assertFalse(release_runtime["holodeck"].get("disclosure_service_v1"))
        rollout = release_runtime["disclosure"].get("rollout", {})
        self.assertEqual(rollout.get("bridge"), "legacy")
        self.assertEqual(rollout.get("holodeck"), "legacy")

    def test_enforced_mode_uses_shared_bridge_path(self) -> None:
        self._write_runtime(
            {
                "bridge": {"disclosure_rollout_v1": "enforced"},
                "holodeck": {"disclosure_rollout_v1": "legacy"},
            }
        )
        self.assertEqual(resolve_surface_rollout_mode(self.root, "bridge"), "enforced")
        self.assertTrue(shared_path_active(self.root, "bridge", cohort_key="req-1"))
        context = heuristic_classify_turn(
            self.root,
            {
                "request_id": "req-rollout-001",
                "session_id": "",
                "raw_text": "build bridge integration",
                "caller_hints": {"workspace_id": "ws-rollout"},
                "domain_hints": [],
                "source_refs": [],
            },
        )
        with mock.patch("conversation_os.bridge_disclosure_adapter.disclose_for_bridge") as disclose_mock:
            disclose_mock.return_value = {"disclosure_service_v1": True, "context_state": context}
            bundle = get_context_bundle(self.root, context)
        disclose_mock.assert_called_once()
        self.assertEqual(bundle["disclosure_rollout_mode"], "enforced")

    def test_shadow_mode_executes_legacy_and_records_comparison(self) -> None:
        self._write_runtime({"bridge": {"disclosure_rollout_v1": "shadow"}})
        context = heuristic_classify_turn(
            self.root,
            {
                "request_id": "req-rollout-shadow",
                "session_id": "",
                "raw_text": "build bridge integration",
                "caller_hints": {"workspace_id": "ws-rollout"},
                "domain_hints": [],
                "source_refs": [],
            },
        )
        with mock.patch("conversation_os.reasoning_bridge._assemble_bridge_context_bundle_impl") as legacy_mock:
            with mock.patch("conversation_os.bridge_disclosure_adapter.disclose_for_bridge") as shared_mock:
                legacy_mock.return_value = {
                    "context_state": context,
                    "global_fallback": {"count": 0, "seed_capsules": []},
                }
                shared_mock.return_value = {
                    "context_state": context,
                    "global_fallback": {"count": 1, "seed_capsules": [{"capsule_id": "cap-1"}]},
                }
                bundle = get_context_bundle(self.root, context)
        legacy_mock.assert_called_once()
        shared_mock.assert_called_once()
        self.assertEqual(bundle["disclosure_rollout_mode"], "shadow")
        self.assertFalse(bundle["disclosure_rollout_shadow"]["parity_match"])

    def test_canary_cohort_is_deterministic(self) -> None:
        self._write_runtime(
            {
                "bridge": {"disclosure_rollout_v1": "canary"},
                "disclosure": {"rollout": {"canary_percent": 50, "canary_salt": "test-salt"}},
            }
        )
        first = in_canary_cohort("req-canary-001", percent=50, salt="test-salt")
        second = in_canary_cohort("req-canary-001", percent=50, salt="test-salt")
        self.assertEqual(first, second)
        path = resolve_execution_path(self.root, "bridge", cohort_key="req-canary-001")
        self.assertIn(path, {"legacy", "shared"})

    def test_legacy_boolean_still_maps_to_enforced(self) -> None:
        self._write_runtime({"bridge": {"disclosure_service_v1": True}})
        self.assertEqual(resolve_surface_rollout_mode(self.root, "bridge"), "enforced")
        self.assertTrue(disclosure_service_enabled(self.root))

    def test_holodeck_legacy_boolean_maps_to_legacy(self) -> None:
        self._write_runtime({"holodeck": {"disclosure_service_v1": False}})
        self.assertEqual(resolve_surface_rollout_mode(self.root, "holodeck"), "legacy")
        self.assertFalse(holodeck_disclosure_service_enabled(self.root))

    def test_compare_bridge_rollout_bundles_reports_subset_diff(self) -> None:
        comparison = compare_bridge_rollout_bundles(
            {"global_fallback": {"count": 0, "seed_capsules": []}},
            {"global_fallback": {"count": 1, "seed_capsules": [{"capsule_id": "cap-1"}]}},
        )
        self.assertFalse(comparison["parity_match"])
        self.assertEqual(comparison["shared_subset"]["capsule_ids"], ["cap-1"])


if __name__ == "__main__":
    unittest.main()
