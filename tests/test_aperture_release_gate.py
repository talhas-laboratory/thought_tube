from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.aperture_release_gate import (
    APPROVED_DEBT_BASELINE_RELATIVE,
    COGNITIVE_APERTURE_FOCUSED_SUITE,
    evaluate_release_gate,
    load_approved_debt_baseline,
    render_release_gate_summary,
    run_focused_suite,
)

FIXTURE_DEBT = Path(__file__).resolve().parent / "fixtures" / "aperture_baselines" / "approved_repository_debt.json"
REPO_ROOT = Path(__file__).resolve().parents[1]


def _green_pytest_result(*, failed_node_ids: list[str] | None = None) -> dict:
    failed = list(failed_node_ids or [])
    fail_count = len(failed)
    stdout = ""
    if failed:
        stdout = "\n".join(f"FAILED {node_id}" for node_id in failed)
        stdout += f"\n{fail_count} failed, 0 passed in 0.01s\n"
    else:
        stdout = "113 passed in 0.50s\n"
    return {
        "returncode": 0 if not failed else 1,
        "pass_count": 0 if failed else 113,
        "fail_count": fail_count,
        "skip_count": 0,
        "error_count": 0,
        "total_count": fail_count if failed else 113,
        "failed_node_ids": failed,
        "green": not failed,
        "stdout_tail": stdout.strip(),
        "command": ["pytest"],
    }


class ApertureReleaseGateTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        debt_dir = self.root / Path(APPROVED_DEBT_BASELINE_RELATIVE).parent
        debt_dir.mkdir(parents=True)
        shutil.copy2(FIXTURE_DEBT, debt_dir / "approved_repository_debt.json")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_debt_baseline_loads(self) -> None:
        baseline = load_approved_debt_baseline(self.root)
        self.assertEqual(baseline["baseline_suite_id"], "approved_repository_debt")
        self.assertGreaterEqual(baseline["summary"]["allowed_failure_count"], 1)
        node_ids = {row["node_id"] for row in baseline["allowed_failures"]}
        self.assertIn(
            "tests/test_engineering_guard.py::EngineeringGuardTestCase::test_load_module_manifests_surfaces_seed_tranche_and_missing_modules",
            node_ids,
        )

    @mock.patch("conversation_os.aperture_release_gate._run_pytest")
    def test_focused_suite_runs_green(self, run_pytest: mock.MagicMock) -> None:
        run_pytest.return_value = _green_pytest_result()
        result = run_focused_suite(self.root)
        run_pytest.assert_called_once_with(self.root, COGNITIVE_APERTURE_FOCUSED_SUITE)
        self.assertTrue(result["green"])
        self.assertEqual(result["fail_count"], 0)
        self.assertEqual(len(result["test_files"]), len(COGNITIVE_APERTURE_FOCUSED_SUITE))

    @mock.patch("conversation_os.aperture_release_gate._run_pytest")
    def test_evaluate_release_gate_returns_ready_when_focused_passes(self, run_pytest: mock.MagicMock) -> None:
        run_pytest.side_effect = [
            _green_pytest_result(),
            {
                **_green_pytest_result(),
                "failed_node_ids": [
                    "tests/test_engineering_guard.py::EngineeringGuardTestCase::test_load_module_manifests_surfaces_seed_tranche_and_missing_modules",
                ],
                "fail_count": 1,
                "green": False,
            },
        ]
        report = evaluate_release_gate(self.root, run_full_suite=True)
        self.assertEqual(report["status"], "ready")
        self.assertEqual(report["new_regressions"], [])
        self.assertIn("Focused suite", render_release_gate_summary(report))

    @mock.patch("conversation_os.aperture_release_gate._run_pytest")
    def test_evaluate_release_gate_blocked_when_simulated_regression(self, run_pytest: mock.MagicMock) -> None:
        regression = "tests/test_disclosure_contracts.py::DisclosureContractsTestCase::test_new_regression_example"
        run_pytest.side_effect = [
            _green_pytest_result(),
            {
                **_green_pytest_result(failed_node_ids=[regression]),
                "fail_count": 1,
                "green": False,
            },
        ]
        report = evaluate_release_gate(self.root, run_full_suite=True)
        self.assertEqual(report["status"], "blocked")
        self.assertIn("unapproved_full_suite_regressions", report["reasons"])
        self.assertEqual(report["new_regressions"], [regression])

    @mock.patch("conversation_os.aperture_release_gate._run_pytest")
    def test_evaluate_release_gate_blocked_when_focused_fails(self, run_pytest: mock.MagicMock) -> None:
        focused_failure = (
            "tests/test_holodeck_disclosure_parity.py::HolodeckDisclosureParityTestCase::"
            "test_collect_contextualization_routes_knowledge_through_disclosure"
        )
        run_pytest.return_value = _green_pytest_result(failed_node_ids=[focused_failure])
        report = evaluate_release_gate(self.root, run_full_suite=False)
        self.assertEqual(report["status"], "blocked")
        self.assertIn("focused_suite_not_green", report["reasons"])
        self.assertIn(focused_failure, report["new_regressions"])


class ApertureReleaseGateIntegrationTestCase(unittest.TestCase):
    def test_repository_debt_fixture_matches_docs_baseline(self) -> None:
        docs_path = REPO_ROOT / APPROVED_DEBT_BASELINE_RELATIVE
        self.assertTrue(docs_path.is_file())
        docs_payload = json.loads(docs_path.read_text(encoding="utf-8"))
        fixture_payload = json.loads(FIXTURE_DEBT.read_text(encoding="utf-8"))
        self.assertEqual(
            docs_payload["summary"]["allowed_failure_count"],
            fixture_payload["summary"]["allowed_failure_count"],
        )
