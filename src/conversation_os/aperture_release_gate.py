"""Cognitive Aperture release verification gate (R-016)."""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Mapping, MutableMapping, Sequence

MODULE_ID = "kernel.disclosure.aperture_release_gate"
GATE_VERSION = "1.0"
APPROVED_DEBT_BASELINE_RELATIVE = (
    "docs/workspaces/cognitive-aperture-exceptional/derived/baselines/approved_repository_debt.json"
)

COGNITIVE_APERTURE_FOCUSED_SUITE: tuple[str, ...] = (
    "tests/test_shape_certification_harness.py",
    "tests/test_feed_certification_harness.py",
    "tests/test_task_pack_certification_harness.py",
    "tests/test_feed_disclosure_parity.py",
    "tests/test_task_pack_disclosure_parity.py",
    "tests/test_holodeck_disclosure_parity.py",
    "tests/test_bounded_view_certification_harness.py",
    "tests/test_aperture_release_gate.py",
    "tests/test_aperture_baseline_harness.py",
    "tests/test_aperture_service_baseline_harness.py",
    "tests/test_aperture_operator_metrics.py",
    "tests/test_corpus_catalog_snapshot.py",
    "tests/test_evidence_resolver.py",
    "tests/test_disclosure_receipts.py",
    "tests/test_disclosure_receipt_rollout.py",
    "tests/test_active_state_continuity.py",
    "tests/test_active_state_continuity_rollout.py",
    "tests/test_disclosure_service_bridge_parity.py",
)

PUBLIC_API = (
    "MODULE_ID",
    "GATE_VERSION",
    "APPROVED_DEBT_BASELINE_RELATIVE",
    "COGNITIVE_APERTURE_FOCUSED_SUITE",
    "load_approved_debt_baseline",
    "run_focused_suite",
    "evaluate_release_gate",
    "render_release_gate_summary",
)
__all__ = list(PUBLIC_API)

_SUMMARY_RE = re.compile(
    r"(?:(?P<failed>\d+) failed(?:, (?P<errors>\d+) errors?)?(?:, (?P<skipped>\d+) skipped)?(?:, )?)?(?P<passed>\d+) passed",
    re.IGNORECASE,
)
_PASSED_ONLY_RE = re.compile(r"(?P<passed>\d+) passed", re.IGNORECASE)
_FAILED_LINE_RE = re.compile(r"^FAILED\s+(?P<node_id>\S+)\s", re.MULTILINE)


def load_approved_debt_baseline(root: Path | str) -> Dict[str, Any]:
    path = Path(root) / APPROVED_DEBT_BASELINE_RELATIVE
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("approved debt baseline must be a JSON object")
    allowed = payload.get("allowed_failures", [])
    if not isinstance(allowed, list):
        raise ValueError("allowed_failures must be a list")
    return payload


def _approved_failure_ids(baseline: Mapping[str, Any]) -> set[str]:
    return {
        str(row.get("node_id", "") or "")
        for row in baseline.get("allowed_failures", []) or []
        if str(row.get("node_id", "") or "")
    }


def _parse_pytest_result(stdout: str, stderr: str, *, returncode: int) -> Dict[str, Any]:
    combined = "\n".join(part for part in (stdout, stderr) if part)
    failed_node_ids = sorted(set(_FAILED_LINE_RE.findall(combined)))
    pass_count = 0
    fail_count = 0
    skip_count = 0
    error_count = 0

    for line in reversed(combined.splitlines()):
        match = _SUMMARY_RE.search(line)
        if match and match.group("passed"):
            pass_count = int(match.group("passed") or 0)
            fail_count = int(match.group("failed") or 0)
            skip_count = int(match.group("skipped") or 0)
            error_count = int(match.group("errors") or 0)
            break
        passed_only = _PASSED_ONLY_RE.search(line)
        if passed_only:
            pass_count = int(passed_only.group("passed") or 0)
            break

    if fail_count == 0 and failed_node_ids:
        fail_count = len(failed_node_ids)
    total_count = pass_count + fail_count + skip_count + error_count
    return {
        "returncode": returncode,
        "pass_count": pass_count,
        "fail_count": fail_count,
        "skip_count": skip_count,
        "error_count": error_count,
        "total_count": total_count,
        "failed_node_ids": failed_node_ids,
        "green": returncode == 0 and fail_count == 0 and error_count == 0,
        "stdout_tail": "\n".join(combined.splitlines()[-20:]),
    }


def _run_pytest(root: Path, targets: Sequence[str]) -> Dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = "src"
    # Clear ini addopts so quiet mode cannot hide the "N passed" summary line.
    command = ["pytest", "-o", "addopts=", "-q", "--tb=no", *targets]
    result = subprocess.run(
        command,
        cwd=root,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    parsed = _parse_pytest_result(result.stdout, result.stderr, returncode=result.returncode)
    parsed["command"] = command
    return parsed


def run_focused_suite(root: Path | str | None = None) -> Dict[str, Any]:
    root_path = Path(root or Path.cwd())
    result = _run_pytest(root_path, COGNITIVE_APERTURE_FOCUSED_SUITE)
    result["suite_id"] = "cognitive_aperture_focused"
    result["test_files"] = list(COGNITIVE_APERTURE_FOCUSED_SUITE)
    return result


def evaluate_release_gate(
    root: Path | str,
    *,
    run_full_suite: bool = True,
) -> Dict[str, Any]:
    root_path = Path(root)
    focused = run_focused_suite(root_path)
    full_suite: Dict[str, Any] = {}
    new_regressions: List[str] = []
    reasons: List[str] = []

    if not focused.get("green"):
        reasons.append("focused_suite_not_green")

    if run_full_suite:
        full_suite = _run_pytest(root_path, ["tests"])
        full_suite["suite_id"] = "repository_full"
        baseline = load_approved_debt_baseline(root_path)
        allowed_ids = _approved_failure_ids(baseline)
        observed_failures = set(full_suite.get("failed_node_ids", []) or [])
        new_regressions = sorted(observed_failures - allowed_ids)
        if new_regressions:
            reasons.append("unapproved_full_suite_regressions")
    elif not focused.get("green"):
        new_regressions = list(focused.get("failed_node_ids", []) or [])

    status = "ready" if not reasons else "blocked"
    return {
        "status": status,
        "gate_version": GATE_VERSION,
        "reasons": reasons,
        "focused": focused,
        "full_suite": full_suite,
        "new_regressions": new_regressions,
    }


def render_release_gate_summary(report: Mapping[str, Any]) -> str:
    focused = dict(report.get("focused", {}) or {})
    full_suite = dict(report.get("full_suite", {}) or {})
    lines = [
        "# Cognitive Aperture release gate",
        "",
        f"- Status: `{report.get('status', 'blocked')}`",
        f"- Gate version: `{report.get('gate_version', GATE_VERSION)}`",
    ]
    if report.get("reasons"):
        lines.append(f"- Reasons: {', '.join(str(reason) for reason in report.get('reasons', []) or [])}")
    lines.extend(
        [
            "",
            "## Focused suite",
            "",
            f"- Green: `{focused.get('green', False)}`",
            f"- Pass / fail / skip: {focused.get('pass_count', 0)} / {focused.get('fail_count', 0)} / {focused.get('skip_count', 0)}",
            f"- Test files: {len(focused.get('test_files', []) or [])}",
        ]
    )
    if full_suite:
        lines.extend(
            [
                "",
                "## Full repository suite",
                "",
                f"- Green: `{full_suite.get('green', False)}`",
                f"- Pass / fail / skip: {full_suite.get('pass_count', 0)} / {full_suite.get('fail_count', 0)} / {full_suite.get('skip_count', 0)}",
                f"- Allowed debt baseline: `{APPROVED_DEBT_BASELINE_RELATIVE}`",
            ]
        )
    regressions = list(report.get("new_regressions", []) or [])
    lines.extend(["", "## New regressions", ""])
    if regressions:
        for node_id in regressions:
            lines.append(f"- `{node_id}`")
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"
