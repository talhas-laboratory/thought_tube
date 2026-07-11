from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from unittest import mock

from conversation_os.release_management import evaluate_release_gates


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "tools" / "deploy_inner_world_to_openclaw.py"
sys.path.append(str(SCRIPT_PATH.parent))
SPEC = importlib.util.spec_from_file_location("deploy_inner_world_to_openclaw", SCRIPT_PATH)
assert SPEC and SPEC.loader
deploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy)


def test_release_gates_block_missing_required_checks() -> None:
    report = evaluate_release_gates(
        required_checks=["python_tests", "rollback_dry_run"],
        completed_checks=["python_tests"],
    )
    assert report["status"] == "blocked"
    assert report["missing_checks"] == ["rollback_dry_run"]


def test_release_gates_pass_when_required_checks_complete() -> None:
    report = evaluate_release_gates(
        required_checks=["python_tests", "rollback_dry_run"],
        completed_checks=["rollback_dry_run", "python_tests"],
    )
    assert report["status"] == "passed"
    assert report["missing_checks"] == []


def test_assert_release_gate_requires_report_when_not_bypassed(tmp_path: Path) -> None:
    args = deploy.build_parser().parse_args([])
    with mock.patch.object(deploy, "SystemExit", SystemExit):
        try:
            deploy.assert_release_gate(args)
        except SystemExit as exc:
            assert "--release-gate-report is required" in str(exc)
        else:
            raise AssertionError("expected SystemExit")


def test_assert_release_gate_accepts_passing_report(tmp_path: Path) -> None:
    report_path = tmp_path / "gate_report.json"
    report_path.write_text('{"status":"passed","missing_checks":[]}\n', encoding="utf-8")
    args = deploy.build_parser().parse_args(["--release-gate-report", str(report_path)])
    deploy.assert_release_gate(args)
