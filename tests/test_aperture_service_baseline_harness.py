from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.aperture_service_baseline_harness import (
    SERVICE_BASELINE_SUITE_ID,
    SERVICE_THRESHOLDS,
    evaluate_adapter_parity_probe,
    evaluate_retrieval_ranking_probe,
    evaluate_shape_projection_probe,
    published_service_baseline_manifest,
    render_service_baseline_summary,
    run_service_baseline_suite,
)
from conversation_os.library_tracker import CHAT_CONVERTER_SEED_CORPUS_ID as CORPUS_ID
from conversation_os.library_tracker import CHAT_CONVERTER_SEED_CORPUS_REVISION as CORPUS_REVISION

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "aperture_baselines" / "v1"
SERVICE_BASELINE_JSON = (
    Path(__file__).resolve().parents[1]
    / "docs/workspaces/cognitive-aperture-exceptional/derived/baselines/chat_converter_seed_v1_service.json"
)


class ApertureServiceBaselineHarnessTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_published_manifest_matches_derived_service_baseline_json(self) -> None:
        published = published_service_baseline_manifest()
        recorded = json.loads(SERVICE_BASELINE_JSON.read_text(encoding="utf-8"))
        self.assertEqual(published["baseline_suite_id"], recorded["baseline_suite_id"])
        self.assertEqual(published["corpus_revision"], recorded["corpus_revision"])
        self.assertEqual(published["summary"]["known_failure_count"], recorded["summary"]["known_failure_count"])
        self.assertEqual(len(published["observed_results"]), len(recorded["observed_results"]))

    def test_structural_ranking_beats_distractor(self) -> None:
        suite = json.loads((FIXTURES_DIR / "service_probes.json").read_text(encoding="utf-8"))
        probe = next(
            row for row in suite["probes"] if row["probe_id"] == "structural-agent-memory-ranking"
        )
        result = evaluate_retrieval_ranking_probe(self.root, probe)
        self.assertEqual(result["verdict"], "pass")
        self.assertTrue(result["structural_beats_distractor"])
        self.assertIn("mapping-the-mind-for-agentic-systems", result["ranked_source_slugs"][0])

    def test_near_neighbour_distractor_is_recorded_as_known_failure(self) -> None:
        suite = json.loads((FIXTURES_DIR / "service_probes.json").read_text(encoding="utf-8"))
        probe = next(row for row in suite["probes"] if row["probe_id"] == "near-neighbour-distractor-harm")
        result = evaluate_retrieval_ranking_probe(self.root, probe)
        self.assertEqual(result["verdict"], "known_failure")
        self.assertFalse(result["structural_beats_distractor"])
        self.assertEqual(result["ranked_source_slugs"][0], "understanding-the-nature-of-thought")

    def test_shape_probe_blocks_promotion_and_upgrades(self) -> None:
        suite = json.loads((FIXTURES_DIR / "service_probes.json").read_text(encoding="utf-8"))
        probe = next(row for row in suite["probes"] if row["probe_id"] == "shape-anti-match-no-promotion")
        result = evaluate_shape_projection_probe(self.root, probe)
        self.assertEqual(result["verdict"], "pass")
        self.assertFalse(result["promotion_allowed"])
        self.assertFalse(result["candidate_upgrade_detected"])
        self.assertGreaterEqual(result["anti_match_count"], 1)

    def test_bridge_holodeck_adapter_parity(self) -> None:
        suite = json.loads((FIXTURES_DIR / "service_probes.json").read_text(encoding="utf-8"))
        probe = next(row for row in suite["probes"] if row["probe_id"] == "bridge-holodeck-retrieval-parity")
        result = evaluate_adapter_parity_probe(self.root, probe)
        self.assertEqual(result["verdict"], "pass")
        self.assertTrue(result["adapter_parity"])

    def test_run_service_baseline_suite_emits_machine_readable_metrics(self) -> None:
        report = run_service_baseline_suite(self.root, FIXTURES_DIR / "service_probes.json")
        self.assertEqual(report["baseline_suite_id"], SERVICE_BASELINE_SUITE_ID)
        self.assertEqual(report["corpus_id"], CORPUS_ID)
        self.assertEqual(report["corpus_revision"], CORPUS_REVISION)
        self.assertEqual(report["probe_count"], 5)
        self.assertEqual(report["known_failure_count"], 1)
        self.assertGreaterEqual(report["pass_count"], 4)
        self.assertIn("adapter_parity_rate", report)
        self.assertIn("threshold_check", report)
        self.assertTrue(report["threshold_check"]["passed"])
        summary = render_service_baseline_summary(report)
        self.assertIn("near-neighbour-distractor-harm", summary)
        self.assertIn("bridge-holodeck-retrieval-parity", summary)

    def test_service_thresholds_are_versioned_in_probe_fixture(self) -> None:
        suite = json.loads((FIXTURES_DIR / "service_probes.json").read_text(encoding="utf-8"))
        self.assertEqual(suite["corpus_revision"], CORPUS_REVISION)
        self.assertEqual(suite["thresholds"]["candidate_upgrade_rate"], 0.0)
        self.assertEqual(SERVICE_THRESHOLDS["adapter_parity_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
