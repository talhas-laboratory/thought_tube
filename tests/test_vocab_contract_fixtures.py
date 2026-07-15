"""VOCAB-001 fixture index validation (spec-only; no runtime)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures" / "metaphysical_vocabulary"


class VocabContractFixturesTestCase(unittest.TestCase):
    def test_index_matches_table_case_counts(self) -> None:
        index = json.loads((FIXTURES / "vocab_contract_fixtures.json").read_text(encoding="utf-8"))
        for entry in index["fixture_tables"]:
            with self.subTest(operation=entry["operation"]):
                table = json.loads((ROOT / entry["fixture_file"]).read_text(encoding="utf-8"))
                self.assertEqual(len(table["cases"]), entry["case_count"])

    def test_atomic_obligations_lists_all_tables(self) -> None:
        obligations_path = (
            ROOT
            / "docs"
            / "workspaces"
            / "metaphysical-vocabulary-governance"
            / "derived"
            / "VOCABULARY_ATOMIC_OBLIGATIONS.json"
        )
        obligations = json.loads(obligations_path.read_text(encoding="utf-8"))
        index = json.loads((FIXTURES / "vocab_contract_fixtures.json").read_text(encoding="utf-8"))
        indexed_files = {row["fixture_file"] for row in index["fixture_tables"]}
        obligation_files = {row["fixture_file"] for row in obligations["fixture_tables"]}
        self.assertEqual(indexed_files, obligation_files)

    def test_mapping_kinds_in_obligations(self) -> None:
        obligations = json.loads(
            (
                ROOT
                / "docs"
                / "workspaces"
                / "metaphysical-vocabulary-governance"
                / "derived"
                / "VOCABULARY_ATOMIC_OBLIGATIONS.json"
            ).read_text(encoding="utf-8")
        )
        expected = {"equivalent", "narrower", "broader", "overlaps", "analogous"}
        self.assertEqual(set(obligations["mapping_kinds"]), expected)


if __name__ == "__main__":
    unittest.main()
