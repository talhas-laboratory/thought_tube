from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.library_tracker import CHAT_CONVERTER_SEED_CORPUS_REVISION
from conversation_os.shape_certification_harness import (
    CERTIFICATION_SUITE_ID,
    CertificationRegressionError,
    evaluate_retrieval_probe,
    guard_known_failure_probes,
    render_certification_summary,
    run_shape_certification_suite,
    seed_certification_corpus,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "aperture_baselines" / "v2"
PROBE_SUITE = FIXTURES_DIR / "shape_certification_probes.json"


class ShapeCertificationHarnessTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_seed_corpus_publishes_catalog_snapshot(self) -> None:
        meta = seed_certification_corpus(self.root)
        self.assertIn("corpus_revision", meta)
        self.assertTrue((self.root / "product" / "inner_world_v1" / "data" / "corpus_catalog_snapshots" / "local_runtime.json").is_file())

    def test_positive_probe_shape_assisted_recall(self) -> None:
        seed_certification_corpus(self.root)
        suite = json.loads(PROBE_SUITE.read_text(encoding="utf-8"))
        probe = next(row for row in suite["probes"] if row["probe_id"] == "positive-shape-assisted-recall")
        result = evaluate_retrieval_probe(self.root, probe)
        self.assertEqual(result["verdict"], "pass")
        self.assertGreaterEqual(result["shape_recall_at_k"], 1.0)

    def test_near_neighbour_stays_known_failure_for_lexical_mode(self) -> None:
        seed_certification_corpus(self.root)
        suite = json.loads(PROBE_SUITE.read_text(encoding="utf-8"))
        probe = next(row for row in suite["probes"] if row["probe_id"] == "near-neighbour-distractor-harm")
        result = evaluate_retrieval_probe(self.root, probe)
        self.assertEqual(result["verdict"], "known_failure")
        self.assertFalse(result["modes"]["lexical"]["structural_beats_distractor"])

    def test_anti_match_probe_rejects_false_analogy(self) -> None:
        seed_certification_corpus(self.root)
        suite = json.loads(PROBE_SUITE.read_text(encoding="utf-8"))
        probe = next(row for row in suite["probes"] if row["probe_id"] == "anti-match-false-analogy")
        report = run_shape_certification_suite(self.root, {"probes": [probe]}, seed=False)
        self.assertEqual(report["results"][0]["verdict"], "pass")

    def test_run_suite_generates_machine_readable_report(self) -> None:
        report = run_shape_certification_suite(self.root, PROBE_SUITE)
        self.assertEqual(report["baseline_suite_id"], CERTIFICATION_SUITE_ID)
        self.assertEqual(report["corpus_revision"], CHAT_CONVERTER_SEED_CORPUS_REVISION)
        self.assertIn("metrics", report)
        self.assertIn("threshold_check", report)
        self.assertIn("generation_marker", report)
        self.assertGreaterEqual(report["probe_count"], 5)
        self.assertGreaterEqual(report["known_failure_count"], 1)
        summary = render_certification_summary(report)
        self.assertIn("near-neighbour-distractor-harm", summary)

    def test_guard_raises_when_known_failure_regresses(self) -> None:
        report = {
            "results": [
                {
                    "probe_id": "near-neighbour-distractor-harm",
                    "expected_verdict": "known_failure",
                    "verdict": "pass",
                }
            ]
        }
        with self.assertRaises(CertificationRegressionError):
            guard_known_failure_probes(report)

    def test_fixture_revision_is_versioned(self) -> None:
        suite = json.loads(PROBE_SUITE.read_text(encoding="utf-8"))
        self.assertEqual(suite["schema_version"], "2.0")
        self.assertTrue(str(suite.get("fixture_revision", "")).startswith("cae-shape-cert-v2"))
