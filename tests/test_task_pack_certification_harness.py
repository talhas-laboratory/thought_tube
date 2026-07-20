from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.library_tracker import CHAT_CONVERTER_SEED_CORPUS_REVISION
from conversation_os.task_pack_certification_harness import (
    CERTIFICATION_SUITE_ID,
    CertificationRegressionError,
    evaluate_bridge_parity_probe,
    evaluate_negative_probe,
    evaluate_positive_probe,
    guard_known_failure_probes,
    render_certification_summary,
    run_task_pack_certification_suite,
    seed_certification_corpus,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "aperture_baselines" / "v2"
PROBE_SUITE = FIXTURES_DIR / "task_pack_certification_probes.json"


class TaskPackCertificationHarnessTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_seed_corpus_publishes_catalog_snapshot(self) -> None:
        meta = seed_certification_corpus(self.root)
        self.assertIn("corpus_revision", meta)
        self.assertTrue(
            (self.root / "product" / "inner_world_v1" / "data" / "corpus_catalog_snapshots" / "local_runtime.json").is_file()
        )

    def test_positive_probe_returns_bounded_evidence_with_overlap(self) -> None:
        seed_certification_corpus(self.root)
        suite = json.loads(PROBE_SUITE.read_text(encoding="utf-8"))
        probe = next(row for row in suite["probes"] if row["probe_id"] == "positive-bounded-evidence-overlap")
        result = evaluate_positive_probe(self.root, probe)
        self.assertEqual(result["verdict"], "pass")
        self.assertTrue(result["has_query_overlap"])
        self.assertGreater(result["count"], 0)

    def test_bridge_parity_matches_bridge_subset(self) -> None:
        seed_certification_corpus(self.root)
        suite = json.loads(PROBE_SUITE.read_text(encoding="utf-8"))
        probe = next(row for row in suite["probes"] if row["probe_id"] == "bridge-parity-research-query")
        result = evaluate_bridge_parity_probe(self.root, probe)
        self.assertEqual(result["verdict"], "pass")
        self.assertTrue(result["parity_ok"])

    def test_negative_probe_returns_zero_blocks(self) -> None:
        seed_certification_corpus(self.root)
        suite = json.loads(PROBE_SUITE.read_text(encoding="utf-8"))
        probe = next(row for row in suite["probes"] if row["probe_id"] == "negative-unrelated-no-filler")
        result = evaluate_negative_probe(self.root, probe)
        self.assertEqual(result["verdict"], "no_hits")
        self.assertTrue(result["zero_blocks"])

    def test_run_suite_generates_machine_readable_report(self) -> None:
        report = run_task_pack_certification_suite(self.root, PROBE_SUITE)
        self.assertEqual(report["baseline_suite_id"], CERTIFICATION_SUITE_ID)
        self.assertEqual(report["corpus_revision"], CHAT_CONVERTER_SEED_CORPUS_REVISION)
        self.assertIn("metrics", report)
        self.assertIn("threshold_check", report)
        self.assertIn("generation_marker", report)
        self.assertGreaterEqual(report["probe_count"], 6)
        self.assertTrue(report["service_certified"])
        summary = render_certification_summary(report)
        self.assertIn("bridge-parity-research-query", summary)

    def test_guard_raises_when_known_failure_regresses(self) -> None:
        report = {
            "results": [
                {
                    "probe_id": "example-known-failure",
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
        self.assertTrue(str(suite.get("fixture_revision", "")).startswith("cae-task-pack-cert-v2"))
