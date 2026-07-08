import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import init_repo
from conversation_os.mtsf_gap_eval import default_gap_closure_evals_dir, run_gap_closure_evals

REPO_ROOT = Path(__file__).resolve().parents[1]
CLOSED_GAPS_PATH = (
    REPO_ROOT
    / "docs"
    / "frameworks"
    / "metaphysical-thought-space"
    / "evals"
    / "gap-closure"
    / "CLOSED_GAPS.json"
)
GAP_PLAN_PATH = REPO_ROOT / "docs" / "frameworks" / "metaphysical-thought-space" / "GAP_PLAN.md"


class MtsfGapClosureTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        init_repo(self.root)
        docs_link = self.root / "docs"
        if docs_link.exists() or docs_link.is_symlink():
            if docs_link.is_symlink() or docs_link.is_file():
                docs_link.unlink()
            else:
                shutil.rmtree(docs_link)
        os.symlink(REPO_ROOT / "docs", docs_link, target_is_directory=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_gap_plan_exists(self) -> None:
        self.assertTrue(GAP_PLAN_PATH.exists())

    def test_every_gap_fixture_is_registered(self) -> None:
        fixtures = sorted(default_gap_closure_evals_dir(REPO_ROOT).glob("gap-G*.json"))
        self.assertGreaterEqual(len(fixtures), 13)
        gap_ids = set()
        for path in fixtures:
            payload = json.loads(path.read_text(encoding="utf-8"))
            gap_ids.add(payload["gap_id"])
            self.assertIn("check", payload)
            self.assertIn("title", payload)
        self.assertIn("G01", gap_ids)
        self.assertIn("G13", gap_ids)

    def test_gap_closure_suite_runs(self) -> None:
        result = run_gap_closure_evals(self.root, llm_preference="auto")
        self.assertEqual(result["suite"], "gap-closure")
        self.assertGreaterEqual(result["total"], 13)
        self.assertEqual(len(result["runs"]), result["total"])
        for row in result["runs"]:
            self.assertIn("gap_id", row)
            self.assertIn("failures", row)
            self.assertIn("closed", row)

    def test_closed_gaps_pass(self) -> None:
        closed_payload = json.loads(CLOSED_GAPS_PATH.read_text(encoding="utf-8"))
        closed_ids = [str(gap_id).upper() for gap_id in closed_payload.get("closed", [])]
        if not closed_ids:
            self.skipTest("No gaps marked closed yet — add IDs to CLOSED_GAPS.json when fixed")

        result = run_gap_closure_evals(self.root, llm_preference="auto", gap_ids=closed_ids)
        failures = {
            row["gap_id"]: row["failures"]
            for row in result["runs"]
            if not row["ok"]
        }
        self.assertEqual(
            failures,
            {},
            f"Closed gaps regressed: {failures}",
        )

    def test_open_gaps_report_failures(self) -> None:
        closed_payload = json.loads(CLOSED_GAPS_PATH.read_text(encoding="utf-8"))
        closed_ids = {str(gap_id).upper() for gap_id in closed_payload.get("closed", [])}
        result = run_gap_closure_evals(self.root, llm_preference="auto")
        all_gap_ids = {str(row["gap_id"]).upper() for row in result["runs"]}
        if closed_ids >= all_gap_ids:
            self.skipTest("All gaps closed — no unresolved failures expected")
        open_failures = [
            row
            for row in result["runs"]
            if not row["ok"] and str(row.get("gap_id", "")).upper() not in closed_ids
        ]
        self.assertGreater(
            len(open_failures),
            0,
            "Expected unresolved gaps to fail until the full gap plan ships",
        )


if __name__ == "__main__":
    unittest.main()
