"""Corpus-backed bounded-view certification harness for Cognitive Aperture (R-014)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Mapping
from unittest import mock

from .bounded_view_disclosure_adapter import (
    bounded_view_epistemic_backend_enabled,
    collect_bounded_view_evidence,
    merge_bounded_view_evidence_into_bundle,
)
from .metaphysical_kernel_runtime import FoundationRuntime
from .reasoning_bridge import _assemble_bridge_context_bundle_impl, ensure_reasoning_runtime


MODULE_ID = "kernel.disclosure.bounded_view_certification_harness"
CERTIFICATION_SUITE_ID = "chat_converter_seed_v2_bounded_view_certification"
HARNESS_VERSION = "1.0"

CERTIFICATION_THRESHOLDS = {
    "branch_isolation_rate": 1.0,
    "abstention_correctness_rate": 1.0,
    "flag_off_no_query_rate": 1.0,
    "bridge_integration_rate": 1.0,
}

PUBLIC_API = (
    "MODULE_ID",
    "CERTIFICATION_SUITE_ID",
    "HARNESS_VERSION",
    "CERTIFICATION_THRESHOLDS",
    "seed_certification_corpus",
    "evaluate_branch_isolation_probe",
    "evaluate_abstention_probe",
    "evaluate_flag_off_probe",
    "evaluate_bridge_integration_probe",
    "run_bounded_view_certification_suite",
    "check_certification_thresholds",
    "render_certification_summary",
)
__all__ = list(PUBLIC_API)


def _runtime_config(root: Path) -> None:
    config_dir = root / "product" / "inner_world_v1" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "runtime.json").write_text(
        json.dumps(
            {
                "disclosure": {
                    "bounded_view": {
                        "epistemic_backend_v1": True,
                        "max_nodes": 6,
                        "max_depth": 2,
                    }
                }
            }
        ),
        encoding="utf-8",
    )


def _event(**overrides: object) -> dict:
    payload = {
        "event_id": "event-bv-cert-001",
        "session_id": "session-bv-cert-001",
        "timestamp": "2026-07-19T12:00:00+00:00",
        "actor": "user:test",
        "kind": "request",
        "content": "Control loops may be inhibiting initiative.",
    }
    payload.update(overrides)
    return payload


def _seed_branch_claim(runtime: FoundationRuntime, *, branch_id: str, scope_id: str) -> str:
    fragment = runtime.capture_from_conversation_event(_event())
    prov_id = fragment["envelope"]["provenance_id"]
    runtime.ensure_scope(scope_id)
    runtime.ensure_branch(branch_id)
    claim = runtime.assert_claim(
        predicate="has_level",
        arguments=["low"],
        branch_id=branch_id,
        scope_id=scope_id,
        claimant=f"user:{branch_id}",
        provenance_id=prov_id,
    )
    return str(claim["envelope"]["id"])


def _grant(*, branch_id: str, scope_id: str, root_record_ids: list[str]) -> dict:
    return {
        "grant_id": "grant-bv-cert",
        "request_id": "req-bv-cert",
        "envelope": "bounded",
        "effective_layers": ["kernel"],
        "effective_refs": [f"kernel:{record_id}" for record_id in root_record_ids],
        "dimensions": [],
        "shape_maturity": "candidate",
        "cross_ocean": False,
        "token_budget": 900,
        "persistence_mode": "gated",
        "explicit_pins": list(root_record_ids),
        "narrowing_reasons": [],
        "deny_precedence_applied": False,
        "requested_grant_ref": "grant-bv-cert",
        "provenance": {"branch_id": branch_id, "scope_id": scope_id},
    }


def seed_certification_corpus(root: Path) -> Dict[str, Any]:
    _runtime_config(root)
    runtime_dir = root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    ensure_reasoning_runtime(root)
    runtime = FoundationRuntime(root, actor="user:test")
    scope_id = "scope-bv-cert"
    claim_a = _seed_branch_claim(runtime, branch_id="branch_a", scope_id=scope_id)
    claim_b = _seed_branch_claim(runtime, branch_id="branch_b", scope_id=scope_id)
    return {
        "scope_id": scope_id,
        "claim_a": claim_a,
        "claim_b": claim_b,
    }


def evaluate_branch_isolation_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    meta = seed_certification_corpus(root)
    scope_id = str(probe.get("scope_id", meta["scope_id"]) or meta["scope_id"])
    claim_a = str(probe.get("claim_a", meta["claim_a"]) or meta["claim_a"])
    claim_b = str(probe.get("claim_b", meta["claim_b"]) or meta["claim_b"])
    evidence_a = collect_bounded_view_evidence(
        root,
        _grant(branch_id="branch_a", scope_id=scope_id, root_record_ids=[claim_a]),
    )
    evidence_b = collect_bounded_view_evidence(
        root,
        _grant(branch_id="branch_b", scope_id=scope_id, root_record_ids=[claim_b]),
    )
    ids_a = {block["block_id"] for block in evidence_a["blocks"]}
    ids_b = {block["block_id"] for block in evidence_b["blocks"]}
    isolated = claim_a in ids_a and claim_b not in ids_a and claim_b in ids_b and claim_a not in ids_b
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "branch_isolation",
        "verdict": "pass" if isolated else "fail",
        "result_status_a": evidence_a.get("result_status", ""),
        "result_status_b": evidence_b.get("result_status", ""),
    }


def evaluate_abstention_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    meta = seed_certification_corpus(root)
    scope_id = str(probe.get("scope_id", meta["scope_id"]) or meta["scope_id"])
    claim_a = str(probe.get("claim_a", meta["claim_a"]) or meta["claim_a"])
    bundle: Dict[str, Any] = {}
    merge_bounded_view_evidence_into_bundle(
        root,
        bundle,
        _grant(branch_id="", scope_id=scope_id, root_record_ids=[claim_a]),
        surface="bridge",
    )
    audit = dict(bundle.get("bounded_view_audit", {}) or {})
    abstained = audit.get("result_status") == "abstained_missing_branch_scope"
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "abstention",
        "verdict": "pass" if abstained and "bounded_view_evidence" not in bundle else "fail",
        "result_status": audit.get("result_status", ""),
    }


def evaluate_flag_off_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    meta = seed_certification_corpus(root)
    config_path = root / "product" / "inner_world_v1" / "config" / "runtime.json"
    runtime = json.loads(config_path.read_text(encoding="utf-8"))
    runtime["disclosure"]["bounded_view"]["epistemic_backend_v1"] = False
    config_path.write_text(json.dumps(runtime), encoding="utf-8")
    scope_id = str(probe.get("scope_id", meta["scope_id"]) or meta["scope_id"])
    claim_a = str(probe.get("claim_a", meta["claim_a"]) or meta["claim_a"])
    bundle: Dict[str, Any] = {}
    with mock.patch(
        "conversation_os.bounded_view_disclosure_adapter.collect_bounded_view_evidence"
    ) as collect_mock:
        merge_bounded_view_evidence_into_bundle(
            root,
            bundle,
            _grant(branch_id="branch_a", scope_id=scope_id, root_record_ids=[claim_a]),
            surface="holodeck",
        )
        collect_mock.assert_not_called()
    disabled = (
        not bounded_view_epistemic_backend_enabled(root)
        and bundle.get("bounded_view_audit", {}).get("result_status") == "disabled"
    )
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "flag_off",
        "verdict": "pass" if disabled else "fail",
        "result_status": bundle.get("bounded_view_audit", {}).get("result_status", ""),
    }


def evaluate_bridge_integration_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    meta = seed_certification_corpus(root)
    scope_id = str(probe.get("scope_id", meta["scope_id"]) or meta["scope_id"])
    claim_a = str(probe.get("claim_a", meta["claim_a"]) or meta["claim_a"])
    grant = _grant(branch_id="branch_a", scope_id=scope_id, root_record_ids=[claim_a])
    context_state = {
        "context_id": "ctx-bv-cert",
        "request_id": "req-bv-cert",
        "active_topic": "bounded epistemic evidence",
        "depth_mode": "focused",
        "attributes": {"session_id": "", "caller_hints": {}},
    }
    from .disclosure_contracts import EffectiveGrant

    with mock.patch(
        "conversation_os.reasoning_bridge.build_effective_grant_from_context",
        return_value=EffectiveGrant.from_dict(grant),
    ):
        bundle = _assemble_bridge_context_bundle_impl(root, context_state)
    integrated = (
        "bounded_view_evidence" in bundle
        and int(bundle.get("bounded_view_audit", {}).get("block_count", 0) or 0) > 0
        and bundle.get("bounded_view_audit", {}).get("result_status") == "disclosed"
    )
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "bridge_integration",
        "verdict": "pass" if integrated else "fail",
        "block_count": int(bundle.get("bounded_view_audit", {}).get("block_count", 0) or 0),
        "result_status": bundle.get("bounded_view_audit", {}).get("result_status", ""),
    }


def check_certification_thresholds(metrics: Mapping[str, Any], thresholds: Mapping[str, Any]) -> Dict[str, Any]:
    checks = {
        "branch_isolation_rate": float(metrics.get("branch_isolation_rate", 0)) >= float(
            thresholds.get("branch_isolation_rate", 1.0)
        ),
        "abstention_correctness_rate": float(metrics.get("abstention_correctness_rate", 0)) >= float(
            thresholds.get("abstention_correctness_rate", 1.0)
        ),
        "flag_off_no_query_rate": float(metrics.get("flag_off_no_query_rate", 0)) >= float(
            thresholds.get("flag_off_no_query_rate", 1.0)
        ),
        "bridge_integration_rate": float(metrics.get("bridge_integration_rate", 0)) >= float(
            thresholds.get("bridge_integration_rate", 1.0)
        ),
    }
    return {"passed": all(checks.values()), "checks": checks}


def _rate(numerator: int, denominator: int, *, default: float = 1.0) -> float:
    if denominator <= 0:
        return default
    return round(numerator / denominator, 4)


def run_bounded_view_certification_suite(
    root: Path,
    probe_suite: Mapping[str, Any] | Path | str,
    *,
    seed: bool = True,
) -> Dict[str, Any]:
    if isinstance(probe_suite, (str, Path)):
        payload = json.loads(Path(probe_suite).read_text(encoding="utf-8"))
    else:
        payload = dict(probe_suite)

    corpus_meta = seed_certification_corpus(root) if seed else {}
    probes = list(payload.get("probes", []) or [])
    results: List[Dict[str, Any]] = []
    for probe in probes:
        category = str(probe.get("category", "") or "")
        if category == "abstention":
            results.append(evaluate_abstention_probe(root, probe))
        elif category == "flag_off":
            results.append(evaluate_flag_off_probe(root, probe))
        elif category == "bridge_integration":
            results.append(evaluate_bridge_integration_probe(root, probe))
        else:
            results.append(evaluate_branch_isolation_probe(root, probe))

    branch_rows = [row for row in results if row.get("category") == "branch_isolation"]
    abstention_rows = [row for row in results if row.get("category") == "abstention"]
    flag_rows = [row for row in results if row.get("category") == "flag_off"]
    bridge_rows = [row for row in results if row.get("category") == "bridge_integration"]
    thresholds = dict(payload.get("thresholds") or CERTIFICATION_THRESHOLDS)
    metrics = {
        "branch_isolation_rate": _rate(
            sum(1 for row in branch_rows if row.get("verdict") == "pass"),
            len(branch_rows),
        ),
        "abstention_correctness_rate": _rate(
            sum(1 for row in abstention_rows if row.get("verdict") == "pass"),
            len(abstention_rows),
        ),
        "flag_off_no_query_rate": _rate(sum(1 for row in flag_rows if row.get("verdict") == "pass"), len(flag_rows)),
        "bridge_integration_rate": _rate(
            sum(1 for row in bridge_rows if row.get("verdict") == "pass"),
            len(bridge_rows),
        ),
    }
    threshold_check = check_certification_thresholds(metrics, thresholds)
    return {
        "schema_version": HARNESS_VERSION,
        "baseline_suite_id": str(payload.get("baseline_suite_id", CERTIFICATION_SUITE_ID)),
        "fixture_revision": str(payload.get("fixture_revision", "")),
        "corpus_meta": corpus_meta,
        "harness_version": HARNESS_VERSION,
        "thresholds": thresholds,
        "metrics": metrics,
        "probe_count": len(results),
        "pass_count": sum(1 for row in results if row.get("verdict") == "pass"),
        "service_certified": threshold_check["passed"],
        "results": results,
        "threshold_check": threshold_check,
    }


def render_certification_summary(report: Mapping[str, Any]) -> str:
    lines = [
        f"# Bounded-view certification — {report.get('baseline_suite_id', CERTIFICATION_SUITE_ID)}",
        "",
        f"- service_certified: {report.get('service_certified', False)}",
        f"- probe_count: {report.get('probe_count', 0)}",
        "",
        "## Metrics",
    ]
    for key, value in dict(report.get("metrics", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Probes")
    for row in list(report.get("results", []) or []):
        lines.append(f"- {row.get('probe_id')}: {row.get('verdict')}")
    return "\n".join(lines) + "\n"
