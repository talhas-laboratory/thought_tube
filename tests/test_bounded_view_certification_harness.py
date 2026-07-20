from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.bounded_view_certification_harness import (
    CERTIFICATION_SUITE_ID,
    evaluate_abstention_probe,
    evaluate_bridge_integration_probe,
    evaluate_branch_isolation_probe,
    evaluate_flag_off_probe,
    render_certification_summary,
    run_bounded_view_certification_suite,
    seed_certification_corpus,
)
from conversation_os.bounded_view_disclosure_adapter import merge_bounded_view_evidence_into_bundle
from conversation_os.holodeck_disclosure_adapter import collect_disclosure_knowledge_candidates


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "aperture_baselines" / "v2"
PROBE_SUITE = FIXTURES_DIR / "bounded_view_certification_probes.json"


class BoundedViewCertificationHarnessTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_seed_corpus_creates_kernel_claims(self) -> None:
        meta = seed_certification_corpus(self.root)
        self.assertIn("claim_a", meta)
        self.assertIn("claim_b", meta)

    def test_branch_isolation_probe_passes(self) -> None:
        seed_certification_corpus(self.root)
        result = evaluate_branch_isolation_probe(self.root, {"probe_id": "branch-isolation"})
        self.assertEqual(result["verdict"], "pass")

    def test_abstention_probe_passes(self) -> None:
        seed_certification_corpus(self.root)
        result = evaluate_abstention_probe(self.root, {"probe_id": "abstention"})
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["result_status"], "abstained_missing_branch_scope")

    def test_flag_off_probe_skips_collect(self) -> None:
        seed_certification_corpus(self.root)
        result = evaluate_flag_off_probe(self.root, {"probe_id": "flag-off"})
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["result_status"], "disabled")

    def test_bridge_integration_probe_passes(self) -> None:
        seed_certification_corpus(self.root)
        result = evaluate_bridge_integration_probe(self.root, {"probe_id": "bridge-integration"})
        self.assertEqual(result["verdict"], "pass")
        self.assertGreater(result["block_count"], 0)

    def test_run_suite_generates_machine_readable_report(self) -> None:
        report = run_bounded_view_certification_suite(self.root, PROBE_SUITE)
        self.assertEqual(report["baseline_suite_id"], CERTIFICATION_SUITE_ID)
        self.assertTrue(report["service_certified"])
        self.assertEqual(report["probe_count"], 4)
        summary = render_certification_summary(report)
        self.assertIn("bridge-bundle-includes-bounded-view-evidence", summary)

    def test_holodeck_disclosure_bundle_carries_bounded_view_audit(self) -> None:
        meta = seed_certification_corpus(self.root)
        seed_bundle = {
            "topic_terms": ["bounded", "epistemic"],
            "combined_terms": ["bounded", "epistemic"],
            "workspace_id": "ws-bv-cert",
            "explicit_pins": [meta["claim_a"]],
            "provenance": {"branch_id": "branch_a", "scope_id": meta["scope_id"]},
        }
        disclosure_bundle: dict = {}
        _, layers = collect_disclosure_knowledge_candidates(
            self.root,
            seed_bundle,
            max_source_refs=4,
            disclosure_bundle=disclosure_bundle,
        )
        self.assertIn("bounded_view_epistemic", layers)
        self.assertEqual(disclosure_bundle["bounded_view_audit"]["result_status"], "disclosed")
        self.assertGreater(disclosure_bundle["bounded_view_audit"]["block_count"], 0)

    def test_merge_does_not_mutate_retrieval_bundle_ranking(self) -> None:
        meta = seed_certification_corpus(self.root)
        retrieval_bundle = {
            "query": "bounded epistemic",
            "seed_capsules": [{"capsule_id": "capsule-1", "label": "lexical", "summary": "ranked", "source_refs": ["fixture:a.md"]}],
            "related_capsules": [],
            "count": 1,
        }
        bundle = {"retrieval_bundle": retrieval_bundle}
        merge_bounded_view_evidence_into_bundle(
            self.root,
            bundle,
            {
                "explicit_pins": [meta["claim_a"]],
                "effective_refs": [f"kernel:{meta['claim_a']}"],
                "provenance": {"branch_id": "branch_a", "scope_id": meta["scope_id"]},
            },
            surface="bridge",
        )
        self.assertEqual(bundle["retrieval_bundle"]["count"], 1)
        self.assertIn("bounded_view_evidence", bundle)


if __name__ == "__main__":
    unittest.main()
