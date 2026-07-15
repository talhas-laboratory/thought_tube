"""BRANCH-005 release dependency contract validation."""

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
    / "metaphysical-branch-reasoning"
    / "derived"
    / "BRANCH_RELEASE_DEPENDENCY_CONTRACT.json"
)
VOCAB_ACK = (
    ROOT
    / "docs"
    / "workspaces"
    / "metaphysical-vocabulary-governance"
    / "derived"
    / "branch-provider-acknowledgment.md"
)


class BranchReleaseContractTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))

    def test_release_packet_has_required_fields(self) -> None:
        required = {
            "provider_contract_version",
            "release_git_revision",
            "kernel_contract_version_consumed",
            "core_invariants",
            "verification_ladder",
            "consumer_smoke_proofs",
            "downstream_consumer_contracts",
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

    def test_merge_and_weight_invariants_documented(self) -> None:
        invariants = " ".join(self.release.get("core_invariants", []))
        forbidden = " ".join(self.release.get("forbidden_interpretations", []))
        self.assertIn("merge_never_selects_winner", invariants)
        self.assertIn("ensemble_weights_task_relative", invariants)
        self.assertIn("merge_winner_selection", forbidden)

    def test_vocabulary_acknowledgment_matches_release_sha(self) -> None:
        sha = self.release["release_git_revision"]
        text = VOCAB_ACK.read_text(encoding="utf-8")
        self.assertIn(sha, text)

    def test_consumer_contract_paths_exist(self) -> None:
        for row in self.release["downstream_consumer_contracts"]:
            self.assertTrue((ROOT / row["contract_path"]).is_file())
            self.assertTrue((ROOT / row["consumer_ack_path"]).is_file())

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
