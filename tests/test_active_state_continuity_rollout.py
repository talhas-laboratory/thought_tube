from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.active_state_continuity import active_state_continuity_enabled
from conversation_os.active_state_continuity_rollout import (
    active_state_continuity_active,
    continuity_rollout_ready,
    resolve_surface_continuity_rollout_mode,
)
from conversation_os.corpus_catalog_snapshot import publish_corpus_catalog_snapshot


class ActiveStateContinuityRolloutTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "disclosure": {
                        "persistent_receipts_v1": True,
                        "receipts": {
                            "persistent_receipts_v1": True,
                            "rollout": {"bridge": "enforced", "holodeck": "enforced"},
                        },
                        "active_state": {
                            "continuity_v1": True,
                            "max_transitions": 50,
                            "rollout": {"bridge": "enforced", "holodeck": "enforced"},
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        (self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime").mkdir(parents=True)
        publish_corpus_catalog_snapshot(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_release_runtime_enables_continuity_after_receipts(self) -> None:
        release_runtime = json.loads(
            (Path(__file__).resolve().parents[1] / "product" / "inner_world_v1" / "config" / "runtime.json").read_text(
                encoding="utf-8"
            )
        )
        active_state = release_runtime["disclosure"]["active_state"]
        self.assertTrue(active_state["continuity_v1"])
        self.assertEqual(active_state["rollout"]["bridge"], "enforced")
        self.assertTrue(release_runtime["disclosure"]["receipts"]["persistent_receipts_v1"])

    def test_continuity_requires_receipt_rollout_readiness(self) -> None:
        self.assertTrue(continuity_rollout_ready(self.root))
        self.assertTrue(active_state_continuity_active(self.root, "bridge"))
        self.assertTrue(active_state_continuity_enabled(self.root))

    def test_continuity_stays_off_without_receipts(self) -> None:
        runtime_path = self.root / "product" / "inner_world_v1" / "config" / "runtime.json"
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        runtime["disclosure"]["receipts"]["persistent_receipts_v1"] = False
        runtime["disclosure"]["persistent_receipts_v1"] = False
        runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
        self.assertFalse(continuity_rollout_ready(self.root))
        self.assertFalse(active_state_continuity_enabled(self.root))

    def test_legacy_surface_rollout_disables_continuity(self) -> None:
        runtime_path = self.root / "product" / "inner_world_v1" / "config" / "runtime.json"
        runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
        runtime["disclosure"]["active_state"]["rollout"]["bridge"] = "legacy"
        runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
        self.assertEqual(resolve_surface_continuity_rollout_mode(self.root, "bridge"), "legacy")
        self.assertFalse(active_state_continuity_enabled(self.root))
