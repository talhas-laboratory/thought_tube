"""BRANCH-005 consumer smoke proofs."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from conversation_os.metaphysical_branch_reasoning import (
    BRANCH_CONTRACT_VERSION,
    KERNEL_CONTRACT_VERSION,
    assess_support,
)


ROOT = Path(__file__).resolve().parents[1]
RELEASE_PATH = (
    ROOT
    / "docs"
    / "workspaces"
    / "metaphysical-branch-reasoning"
    / "derived"
    / "BRANCH_RELEASE_DEPENDENCY_CONTRACT.json"
)


class MetaphysicalBranchConsumerSmokeTestCase(unittest.TestCase):
    def test_vocabulary_governance_consumer_preserves_branch_local_support(self) -> None:
        """Vocabulary consumer: same proposition, different branch-local readings stay isolated."""
        proposition = {"predicate": "maps_to", "arguments": ["term:heavy", "sense:computational"]}
        evidence = [
            {
                "id": "cl_branch_a",
                "branch_id": "branch_vocab_a",
                "scope_id": "scope_glossary",
                "polarity": "affirmative",
                "proposition": proposition,
            },
            {
                "id": "cl_branch_b",
                "branch_id": "branch_vocab_b",
                "scope_id": "scope_glossary",
                "polarity": "negative",
                "proposition": proposition,
            },
        ]

        result_a = assess_support(
            branch_id="branch_vocab_a",
            scope_id="scope_glossary",
            claim_proposition=proposition,
            evidence_claims=evidence,
            include_inherited=False,
        )
        result_b = assess_support(
            branch_id="branch_vocab_b",
            scope_id="scope_glossary",
            claim_proposition=proposition,
            evidence_claims=evidence,
            include_inherited=False,
        )

        self.assertEqual(result_a.support_value, "supported_only")
        self.assertEqual(result_a.affirmative_claim_ids, ["cl_branch_a"])
        self.assertEqual(result_b.support_value, "opposed_only")
        self.assertEqual(result_b.negative_claim_ids, ["cl_branch_b"])

    def test_consumer_pins_released_contract_versions(self) -> None:
        release = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(release["provider_contract_version"], BRANCH_CONTRACT_VERSION)
        self.assertEqual(release["kernel_contract_version_consumed"], KERNEL_CONTRACT_VERSION)


if __name__ == "__main__":
    unittest.main()
