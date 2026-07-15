"""VOCAB-005 release dependency contract validation."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RELEASE_PATH = (
    ROOT
    / "docs"
    / "workspaces"
    / "metaphysical-vocabulary-governance"
    / "derived"
    / "VOCAB_RELEASE_DEPENDENCY_CONTRACT.json"
)
BRANCH_ACK = (
    ROOT
    / "docs"
    / "workspaces"
    / "metaphysical-vocabulary-governance"
    / "derived"
    / "branch-provider-acknowledgment.md"
)
ATOMIC_OBLIGATIONS = (
    ROOT
    / "docs"
    / "workspaces"
    / "metaphysical-vocabulary-governance"
    / "derived"
    / "VOCABULARY_ATOMIC_OBLIGATIONS.json"
)


class VocabReleaseContractTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))

    def test_release_packet_has_required_fields(self) -> None:
        required = {
            "provider_contract_version",
            "release_git_revision",
            "kernel_contract_version_consumed",
            "branch_contract_version_consumed",
            "core_invariants",
            "mapping_kinds",
            "verification_ladder",
            "consumer_smoke_proofs",
            "upstream_provider_acknowledgments",
            "known_phase1_limits",
        }
        self.assertTrue(required.issubset(self.release.keys()))

    def test_contract_version_is_1_0_0(self) -> None:
        self.assertEqual(self.release["provider_contract_version"], "1.0.0")
        self.assertEqual(self.release["gate"], "G5")

    def test_release_sha_is_recorded(self) -> None:
        sha = str(self.release.get("release_git_revision", ""))
        self.assertTrue(sha)
        self.assertNotEqual(sha, "RELEASE_SHA_PLACEHOLDER")
        self.assertTrue(re.fullmatch(r"[0-9a-f]{40}", sha), msg=sha)

    def test_mapping_and_promotion_invariants_documented(self) -> None:
        invariants = " ".join(self.release.get("core_invariants", []))
        forbidden = " ".join(self.release.get("forbidden_interpretations", []))
        self.assertIn("mapping_is_record_not_rewrite", invariants)
        self.assertIn("promotion_optional", invariants)
        self.assertIn("forced_normalization", forbidden)

    def test_branch_acknowledgment_matches_consumed_sha(self) -> None:
        branch_sha = self.release["branch_release_git_revision_consumed"]
        text = BRANCH_ACK.read_text(encoding="utf-8")
        self.assertIn(branch_sha, text)

    def test_kernel_dependency_matches_atomic_obligations(self) -> None:
        obligations = json.loads(ATOMIC_OBLIGATIONS.read_text(encoding="utf-8"))
        self.assertEqual(
            self.release["kernel_contract_version_consumed"],
            obligations["kernel_dependency"]["contract_version"],
        )
        self.assertEqual(
            self.release["kernel_release_git_revision_consumed"],
            obligations["kernel_dependency"]["release_git_revision"],
        )

    def test_upstream_ack_paths_exist(self) -> None:
        for row in self.release["upstream_provider_acknowledgments"]:
            self.assertTrue((ROOT / row["ack_path"]).is_file())

    def test_smoke_proof_tests_exist(self) -> None:
        for proof in self.release["consumer_smoke_proofs"]:
            test_ref = str(proof["test"])
            module, _, test_name = test_ref.partition("::")
            module_path = ROOT / module.replace(".", "/")
            self.assertTrue(module_path.with_suffix(".py").is_file(), msg=module)
            source = module_path.with_suffix(".py").read_text(encoding="utf-8")
            self.assertIn(f"def {test_name}", source)


if __name__ == "__main__":
    unittest.main()
