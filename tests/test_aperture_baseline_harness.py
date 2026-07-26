from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.aperture_baseline_harness import (
    BASELINE_SUITE_ID,
    DEFAULT_THRESHOLDS,
    _derive_verdict,
    classify_result_status,
    evaluate_probe,
    load_probe_suite,
    published_baseline_manifest,
    render_baseline_summary,
    run_baseline_suite,
)
from conversation_os.library_tracker import CHAT_CONVERTER_SEED_CORPUS_ID as CORPUS_ID
from conversation_os.library_tracker import CHAT_CONVERTER_SEED_CORPUS_REVISION as CORPUS_REVISION
from conversation_os.vault_ingest import ingest_text_content

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "aperture_baselines" / "v1"
BASELINE_JSON = (
    Path(__file__).resolve().parents[1]
    / "docs/workspaces/cognitive-aperture-exceptional/derived/baselines/chat_converter_seed_v1.json"
)


class ApertureBaselineHarnessTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _ingest_seed_sources(self) -> None:
        fixtures = [
            (
                "agentic-hybrid-rag-for-information-extraction",
                "Hybrid retrieval combines graph traversal and information extraction pipelines.",
            ),
            (
                "context-in-embedding-spaces",
                "Semantic context lives in embedding spaces and residual stream geometry metaphors.",
            ),
            (
                "mapping-the-mind-for-agentic-systems",
                "Mapping the mind for agentic systems covers recursive self-model and agent memory architecture.",
            ),
            (
                "understanding-the-nature-of-thought",
                "Understanding the nature of thought explores biological cognition and phenomenology.",
            ),
        ]
        for slug, content in fixtures:
            ingest_text_content(
                self.root,
                title=slug,
                content=f"# Fixture\n\n{content}\n",
                source_ref=f"fixture:{slug}",
                source_type="chat_converter_conversation",
                source_family="chat_converter",
                metadata={"fixture_only": True, "slug": slug},
            )

    def test_published_manifest_matches_derived_baseline_json(self) -> None:
        published = published_baseline_manifest()
        recorded = json.loads(BASELINE_JSON.read_text(encoding="utf-8"))
        self.assertEqual(published["corpus_id"], recorded["corpus_id"])
        self.assertEqual(published["corpus_revision"], recorded["corpus_revision"])
        self.assertEqual(published["summary"]["known_failure_count"], recorded["summary"]["known_failure_count"])
        self.assertEqual(len(published["observed_results"]), len(recorded["observed_results"]))

    def test_classify_result_status_distinguishes_empty_abstention_denial_and_failure(self) -> None:
        catalog_ready = {"readiness_state": "ready", "retrieval_allowed": True}
        self.assertEqual(
            classify_result_status(probe={"category": "negative"}, hits=[], catalog=catalog_ready),
            "empty_no_positive_match",
        )
        self.assertEqual(
            classify_result_status(
                probe={"category": "privacy", "simulate_denial": True},
                hits=[{"source_ref": "fixture:a"}],
                catalog=catalog_ready,
            ),
            "denied_visibility",
        )
        self.assertEqual(
            classify_result_status(
                probe={"category": "positive"},
                hits=[],
                catalog={"readiness_state": "stale", "retrieval_allowed": False},
            ),
            "abstained_stale_index",
        )
        self.assertEqual(
            classify_result_status(
                probe={"category": "positive"},
                hits=[],
                catalog=catalog_ready,
                error="boom",
            ),
            "failed_internal",
        )

    def test_positive_and_negative_probes_on_synthetic_corpus(self) -> None:
        self._ingest_seed_sources()
        suite = load_probe_suite(FIXTURES_DIR / "probes.json")
        selected = {
            probe["probe_id"]: probe
            for probe in suite["probes"]
            if probe["probe_id"]
            in {
                "exact-hybrid-rag-file",
                "out-of-domain-quantum-gardening",
            }
        }
        positive = evaluate_probe(self.root, selected["exact-hybrid-rag-file"])
        negative = evaluate_probe(self.root, selected["out-of-domain-quantum-gardening"])

        self.assertEqual(positive["verdict"], "pass")
        self.assertEqual(positive["result_status"], "disclosed")
        self.assertIn("agentic-hybrid-rag", positive["top_source_slug"])
        self.assertEqual(negative["verdict"], "no_hits")
        self.assertEqual(negative["result_status"], "empty_no_positive_match")

    def test_near_neighbour_failure_is_recorded_and_classified(self) -> None:
        suite = load_probe_suite(FIXTURES_DIR / "probes.json")
        probe = next(row for row in suite["probes"] if row["probe_id"] == "near-neighbour-agent-memory")
        published = published_baseline_manifest()
        recorded = next(
            row for row in published["observed_results"] if row["probe_id"] == "near-neighbour-agent-memory"
        )
        self.assertEqual(recorded["verdict"], "known_failure")
        self.assertEqual(recorded["observed_top_source_slug"], "understanding-the-nature-of-thought")

        wrong_hit = {
            "source_ref": "fixture:understanding-the-nature-of-thought",
            "title": "understanding-the-nature-of-thought",
        }
        verdict = _derive_verdict(
            probe=probe,
            hits=[wrong_hit],
            top_slug="understanding-the-nature-of-thought",
            result_status="disclosed",
            error="",
        )
        self.assertEqual(verdict, "known_failure")

    def test_run_baseline_suite_emits_machine_readable_metrics(self) -> None:
        self._ingest_seed_sources()
        mini_suite = {
            "baseline_suite_id": BASELINE_SUITE_ID,
            "corpus_id": CORPUS_ID,
            "corpus_revision": CORPUS_REVISION,
            "thresholds": DEFAULT_THRESHOLDS,
            "probes": [
                probe
                for probe in load_probe_suite(FIXTURES_DIR / "probes.json")["probes"]
                if probe["probe_id"]
                in {
                    "exact-hybrid-rag-file",
                    "out-of-domain-quantum-gardening",
                    "near-neighbour-agent-memory",
                    "privacy-denied-visibility",
                    "readiness-stale-index",
                    "internal-failure",
                }
            ],
        }
        report = run_baseline_suite(self.root, mini_suite)
        self.assertEqual(report["corpus_revision"], CORPUS_REVISION)
        self.assertIn("result_status_counts", report)
        self.assertIn("latency_ms_p50", report)
        self.assertGreaterEqual(report["pass_count"], 1)
        summary = render_baseline_summary(report)
        self.assertIn("privacy-denied-visibility", summary)
        self.assertIn("empty_no_positive_match", summary)

    def test_thresholds_are_versioned_in_probe_fixture(self) -> None:
        suite = load_probe_suite(FIXTURES_DIR / "probes.json")
        self.assertEqual(suite["corpus_revision"], CORPUS_REVISION)
        self.assertEqual(suite["thresholds"]["negative_false_open_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
