"""Corpus-backed Feed certification harness for Cognitive Aperture (R-013)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from .aperture_baseline_harness import HARNESS_VERSION as APERTURE_HARNESS_VERSION, _percentile, _source_slug
from .corpus_catalog_snapshot import (
    compute_generation_marker,
    corpus_catalog_snapshot_path,
    invalidate_corpus_catalog_cache,
    load_corpus_catalog_for_request,
    publish_corpus_catalog_snapshot,
)
from .feed_disclosure_adapter import (
    build_feed_effective_grant,
    collect_feed_evidence_pairs,
    feed_evidence_decision_subset,
    record_feed_disclosure_receipt,
)
from .knowledge_layer import build_retrieval_bundle
from .library_tracker import CHAT_CONVERTER_SEED_CORPUS_ID, CHAT_CONVERTER_SEED_CORPUS_REVISION
from .storage import append_jsonl, utc_now
from .vault_ingest import ingest_text_content


MODULE_ID = "kernel.disclosure.feed_certification_harness"
CERTIFICATION_SUITE_ID = "chat_converter_seed_v2_feed_certification"
HARNESS_VERSION = "2.0"

CERTIFICATION_THRESHOLDS = {
    "positive_precision_rate": 1.0,
    "bridge_parity_rate": 1.0,
    "negative_abstention_rate": 1.0,
    "abstention_correctness_rate": 1.0,
    "receipt_persistence_rate": 1.0,
    "provenance_preservation_rate": 1.0,
    "latency_ms_p95": 750,
    "max_catalog_lookup_ms": 50,
    "max_bytes_resolved": 65536,
}

PUBLIC_API = (
    "MODULE_ID",
    "CERTIFICATION_SUITE_ID",
    "HARNESS_VERSION",
    "CERTIFICATION_THRESHOLDS",
    "seed_certification_corpus",
    "evaluate_positive_probe",
    "evaluate_bridge_parity_probe",
    "evaluate_negative_probe",
    "evaluate_abstention_probe",
    "evaluate_receipt_probe",
    "evaluate_resource_probe",
    "run_feed_certification_suite",
    "check_certification_thresholds",
    "guard_known_failure_probes",
    "render_certification_summary",
    "build_published_baseline",
)
__all__ = list(PUBLIC_API)


class CertificationRegressionError(RuntimeError):
    """Raised when a waived known-failure probe regresses without approval."""


def _runtime_config(root: Path) -> None:
    config_dir = root / "product" / "inner_world_v1" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "runtime.json").write_text(
        json.dumps(
            {
                "feed": {
                    "disclosure_service_v1": True,
                    "evidence_retrieval_limit": 8,
                    "evidence_neighbor_limit": 4,
                },
                "knowledge": {
                    "fail_empty_admission_shadow_v1": True,
                    "fail_empty_admission_enforce_v1": True,
                },
                "disclosure": {
                    "persistent_receipts_v1": True,
                    "receipts": {
                        "persistent_receipts_v1": True,
                        "rollout": {
                            "bridge": "enforced",
                            "holodeck": "enforced",
                            "feed": "enforced",
                            "task_pack": "legacy",
                        },
                    },
                },
            }
        ),
        encoding="utf-8",
    )


def _feed_capsule_rows() -> List[Dict[str, Any]]:
    return [
        {
            "capsule_id": "capsule-feed-left",
            "capsule_type": "concept",
            "label": "Research insight",
            "summary": "Research insight about progressive disclosure and bounded feed evidence.",
            "confidence": 0.9,
            "ref_type": "concept",
            "ref_id": "concept-feed-left",
            "source_refs": ["fixture:research-insight.md"],
            "attributes": {"domain": "research"},
        },
        {
            "capsule_id": "capsule-feed-right",
            "capsule_type": "concept",
            "label": "Product design tension",
            "summary": "Product design tension between surprise and bounded evidence selection.",
            "confidence": 0.88,
            "ref_type": "concept",
            "ref_id": "concept-feed-right",
            "source_refs": ["fixture:product-design.md"],
            "attributes": {"domain": "product"},
        },
        {
            "capsule_id": "capsule-feed-distractor",
            "capsule_type": "concept",
            "label": "Unrelated gardening notes",
            "summary": "Quantum gardening unrelated topic with no feed evidence overlap.",
            "confidence": 0.7,
            "ref_type": "concept",
            "ref_id": "concept-feed-distractor",
            "source_refs": ["fixture:quantum-gardening.md"],
            "attributes": {"domain": "gardening"},
        },
    ]


def seed_certification_corpus(root: Path) -> Dict[str, Any]:
    """Seed corpus-backed fixtures for feed certification."""
    _runtime_config(root)
    data_dir = root / "product" / "inner_world_v1" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    runtime = root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
    runtime.mkdir(parents=True, exist_ok=True)

    ingest_text_content(
        root,
        title="research-insight-fixture",
        content="# User\n\nResearch insight about progressive disclosure and bounded feed evidence.\n",
        source_ref="fixture:research-insight.md",
        source_type="chat_converter_conversation",
        metadata={"branch_id": "branch-feed-001", "scope_id": "scope-feed-001"},
    )
    ingest_text_content(
        root,
        title="product-design-fixture",
        content="# User\n\nProduct design tension between surprise and bounded evidence selection.\n",
        source_ref="fixture:product-design.md",
        source_type="chat_converter_conversation",
        metadata={"branch_id": "branch-feed-001", "scope_id": "scope-feed-001"},
    )
    ingest_text_content(
        root,
        title="quantum-gardening-fixture",
        content="# User\n\nQuantum gardening unrelated topic with no feed evidence overlap.\n",
        source_ref="fixture:quantum-gardening.md",
        source_type="chat_converter_conversation",
        metadata={"branch_id": "branch-feed-001", "scope_id": "scope-feed-001"},
    )

    capsule_path = data_dir / "semantic_capsules.jsonl"
    if capsule_path.exists():
        capsule_path.unlink()
    for row in _feed_capsule_rows():
        append_jsonl(capsule_path, row)

    snapshot = publish_corpus_catalog_snapshot(root)
    return {
        "corpus_id": CHAT_CONVERTER_SEED_CORPUS_ID,
        "corpus_revision": snapshot["catalog"].get("corpus_revision", CHAT_CONVERTER_SEED_CORPUS_REVISION),
        "generation_marker": snapshot.get("generation_marker", compute_generation_marker(root)),
    }


def _domain_overlays(probe: Mapping[str, Any]) -> List[str]:
    return [str(value).strip() for value in probe.get("domain_overlays", []) or [] if str(value).strip()]


def _pair_limit(probe: Mapping[str, Any]) -> int:
    return max(1, int(probe.get("limit", 4) or 4))


def _pair_source_refs(pairs: Sequence[Mapping[str, Any]]) -> List[str]:
    refs: List[str] = []
    for pair in pairs:
        for source_ref in pair.get("evidence_refs", []) or []:
            ref = str(source_ref).strip()
            if ref and ref not in refs:
                refs.append(ref)
    return sorted(refs)


def _pair_source_slugs(pairs: Sequence[Mapping[str, Any]]) -> List[str]:
    slugs: List[str] = []
    for ref in _pair_source_refs(pairs):
        slug = _source_slug(ref)
        if slug and slug not in slugs:
            slugs.append(slug)
    return slugs


def _preferred_slug_present(pairs: Sequence[Mapping[str, Any]], preferred: str) -> bool:
    if not preferred:
        return True
    return preferred in _pair_source_slugs(pairs)


def _pair_bytes(pairs: Sequence[Mapping[str, Any]]) -> int:
    total = 0
    for pair in pairs:
        for side in ("left", "right"):
            row = pair.get(side, {}) or {}
            total += len(str(row.get("label", ""))) + len(str(row.get("summary", "")))
    return total


def _collect_pairs(root: Path, probe: Mapping[str, Any]) -> tuple[List[Dict[str, Any]], Dict[str, Any], List[str], float]:
    started = time.perf_counter()
    pairs, retrieval_bundle, layers = collect_feed_evidence_pairs(
        root,
        limit=_pair_limit(probe),
        domain_overlays=_domain_overlays(probe),
    )
    latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
    return pairs, retrieval_bundle, layers, latency_ms


def evaluate_positive_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    pairs, retrieval_bundle, layers, latency_ms = _collect_pairs(root, probe)
    preferred = str(probe.get("preferred_source_slug", "") or "")
    has_pairs = bool(pairs)
    has_provenance = all(bool(pair.get("disclosure_provenance")) for pair in pairs) if pairs else False
    has_grant = all(bool(pair.get("disclosure_grant")) for pair in pairs) if pairs else False
    preferred_ok = _preferred_slug_present(pairs, preferred)
    verdict = "pass" if has_pairs and has_provenance and has_grant and preferred_ok else "fail"
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "positive",
        "expected_verdict": str(probe.get("expected_verdict", "pass") or "pass"),
        "verdict": verdict,
        "pair_count": len(pairs),
        "source_slugs": _pair_source_slugs(pairs),
        "preferred_source_slug": preferred,
        "has_provenance": has_provenance,
        "result_status": str(retrieval_bundle.get("result_status", "") or ""),
        "consulted_layers": list(layers),
        "latency_ms": latency_ms,
        "bytes_resolved": _pair_bytes(pairs),
    }


def evaluate_bridge_parity_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    overlays = _domain_overlays(probe)
    query = " ".join(overlays) if overlays else "context insight connection evidence"
    pairs, retrieval_bundle, layers, latency_ms = _collect_pairs(root, probe)
    bridge_bundle = build_retrieval_bundle(
        root,
        query,
        limit=8,
        neighbor_limit=4,
        include_cross_pond=False,
    )
    bridge_subset = feed_evidence_decision_subset(bridge_bundle)
    feed_subset = feed_evidence_decision_subset(retrieval_bundle)
    admitted_refs = _pair_source_refs(pairs)
    parity_ok = bridge_subset["source_refs"] == admitted_refs and feed_subset["source_refs"] == admitted_refs
    verdict = "pass" if parity_ok and bool(pairs) else "fail"
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "bridge_parity",
        "expected_verdict": str(probe.get("expected_verdict", "pass") or "pass"),
        "verdict": verdict,
        "bridge_source_refs": list(bridge_subset.get("source_refs", []) or []),
        "feed_source_refs": list(feed_subset.get("source_refs", []) or []),
        "pair_source_refs": admitted_refs,
        "parity_ok": parity_ok,
        "pair_count": len(pairs),
        "consulted_layers": list(layers),
        "latency_ms": latency_ms,
        "bytes_resolved": _pair_bytes(pairs),
    }


def evaluate_negative_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    pairs, retrieval_bundle, layers, latency_ms = _collect_pairs(root, probe)
    expected = str(probe.get("expected_verdict", "no_pairs") or "no_pairs")
    if not pairs:
        verdict = "no_pairs" if expected in {"no_pairs", "pass"} else "fail"
    else:
        verdict = "fail"
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "negative",
        "expected_verdict": expected,
        "verdict": verdict,
        "pair_count": len(pairs),
        "source_slugs": _pair_source_slugs(pairs),
        "result_status": str(retrieval_bundle.get("result_status", "") or ""),
        "consulted_layers": list(layers),
        "latency_ms": latency_ms,
        "bytes_resolved": _pair_bytes(pairs),
    }


def evaluate_abstention_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    mode = str(probe.get("abstention_mode", "missing_catalog") or "missing_catalog")
    if mode == "missing_catalog":
        snapshot_path = corpus_catalog_snapshot_path(root)
        if snapshot_path.exists():
            snapshot_path.unlink()
        invalidate_corpus_catalog_cache(root)
    pairs, retrieval_bundle, layers, latency_ms = _collect_pairs(root, probe)
    status = str(retrieval_bundle.get("result_status", "") or "")
    abstained = status in {
        "abstained_stale_index",
        "abstained_dependency_not_ready",
        "empty_no_positive_match",
    }
    verdict = "pass" if abstained and not pairs else "fail"
    if mode == "missing_catalog":
        publish_corpus_catalog_snapshot(root)
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "abstention",
        "expected_verdict": str(probe.get("expected_verdict", "abstained") or "abstained"),
        "verdict": verdict,
        "abstention_mode": mode,
        "pair_count": len(pairs),
        "result_status": status,
        "consulted_layers": list(layers),
        "latency_ms": latency_ms,
        "bytes_resolved": _pair_bytes(pairs),
    }


def evaluate_receipt_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    pairs, retrieval_bundle, layers, latency_ms = _collect_pairs(root, probe)
    grant = pairs[0]["disclosure_grant"] if pairs else build_feed_effective_grant(root, _domain_overlays(probe)).to_dict()
    receipt = record_feed_disclosure_receipt(
        root,
        retrieval_bundle=retrieval_bundle,
        effective_grant=grant,
        pair_count=len(pairs),
    )
    persisted = bool(receipt and receipt.get("surface") == "feed")
    verdict = "pass" if persisted else "fail"
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "receipt",
        "expected_verdict": str(probe.get("expected_verdict", "pass") or "pass"),
        "verdict": verdict,
        "receipt_persisted": persisted,
        "receipt_surface": str((receipt or {}).get("surface", "") or ""),
        "pair_count": len(pairs),
        "consulted_layers": list(layers),
        "latency_ms": latency_ms,
        "bytes_resolved": _pair_bytes(pairs),
    }


def evaluate_resource_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    iterations = max(1, int(probe.get("iterations", 3) or 3))
    latencies: List[float] = []
    catalog_latencies: List[float] = []
    bytes_resolved: List[int] = []
    for _ in range(iterations):
        catalog_started = time.perf_counter()
        load_corpus_catalog_for_request(root)
        catalog_latencies.append(round((time.perf_counter() - catalog_started) * 1000.0, 3))
        result = evaluate_positive_probe(root, {**probe, "category": "positive"})
        latencies.append(float(result.get("latency_ms", 0) or 0))
        bytes_resolved.append(int(result.get("bytes_resolved", 0) or 0))
    p95 = _percentile(latencies, 95)
    catalog_p95 = _percentile(catalog_latencies, 95)
    max_bytes = max(bytes_resolved or [0])
    thresholds = dict(probe.get("thresholds") or CERTIFICATION_THRESHOLDS)
    verdict = "pass"
    if p95 > float(thresholds.get("latency_ms_p95", 750)):
        verdict = "fail"
    if catalog_p95 > float(thresholds.get("max_catalog_lookup_ms", 50)):
        verdict = "fail"
    if max_bytes > int(thresholds.get("max_bytes_resolved", 65536)):
        verdict = "fail"
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "resource",
        "verdict": verdict,
        "latency_ms_p95": p95,
        "catalog_lookup_ms_p95": catalog_p95,
        "max_bytes_resolved": max_bytes,
        "iterations": iterations,
    }


def check_certification_thresholds(metrics: Mapping[str, Any], thresholds: Mapping[str, Any]) -> Dict[str, Any]:
    checks = {
        "positive_precision_rate": float(metrics.get("positive_precision_rate", 0)) >= float(
            thresholds.get("positive_precision_rate", 1.0)
        ),
        "bridge_parity_rate": float(metrics.get("bridge_parity_rate", 0)) >= float(thresholds.get("bridge_parity_rate", 1.0)),
        "negative_abstention_rate": float(metrics.get("negative_abstention_rate", 0)) >= float(
            thresholds.get("negative_abstention_rate", 1.0)
        ),
        "abstention_correctness_rate": float(metrics.get("abstention_correctness_rate", 0)) >= float(
            thresholds.get("abstention_correctness_rate", 1.0)
        ),
        "receipt_persistence_rate": float(metrics.get("receipt_persistence_rate", 0)) >= float(
            thresholds.get("receipt_persistence_rate", 1.0)
        ),
        "provenance_preservation_rate": float(metrics.get("provenance_preservation_rate", 0)) >= float(
            thresholds.get("provenance_preservation_rate", 1.0)
        ),
        "latency_ms_p95": float(metrics.get("latency_ms_p95", 0)) <= float(thresholds.get("latency_ms_p95", 750)),
        "max_catalog_lookup_ms": float(metrics.get("catalog_lookup_ms_p95", 0)) <= float(
            thresholds.get("max_catalog_lookup_ms", 50)
        ),
        "max_bytes_resolved": int(metrics.get("max_bytes_resolved", 0)) <= int(thresholds.get("max_bytes_resolved", 65536)),
    }
    return {"passed": all(checks.values()), "checks": checks}


def guard_known_failure_probes(report: Mapping[str, Any]) -> None:
    for row in list(report.get("results", []) or []):
        if str(row.get("expected_verdict", "")) != "known_failure":
            continue
        if row.get("waived"):
            continue
        if row.get("verdict") == "pass":
            raise CertificationRegressionError(
                f"Probe {row.get('probe_id')} regressed from known_failure to pass without waiver"
            )


def _rate(numerator: int, denominator: int, *, default: float = 1.0) -> float:
    if denominator <= 0:
        return default
    return round(numerator / denominator, 4)


def run_feed_certification_suite(
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
        if category == "bridge_parity":
            results.append(evaluate_bridge_parity_probe(root, probe))
        elif category == "negative":
            results.append(evaluate_negative_probe(root, probe))
        elif category == "abstention":
            results.append(evaluate_abstention_probe(root, probe))
        elif category == "receipt":
            results.append(evaluate_receipt_probe(root, probe))
        elif category == "resource":
            results.append(evaluate_resource_probe(root, probe))
        else:
            results.append(evaluate_positive_probe(root, probe))

    positive_rows = [row for row in results if row.get("category") == "positive"]
    bridge_rows = [row for row in results if row.get("category") == "bridge_parity"]
    negative_rows = [row for row in results if row.get("category") == "negative"]
    abstention_rows = [row for row in results if row.get("category") == "abstention"]
    receipt_rows = [row for row in results if row.get("category") == "receipt"]
    resource_rows = [row for row in results if row.get("category") == "resource"]
    known_failures = [row for row in results if row.get("verdict") == "known_failure"]

    latencies = [float(row.get("latency_ms", 0) or 0) for row in results if "latency_ms" in row]
    resource = resource_rows[0] if resource_rows else {}

    metrics = {
        "positive_precision_rate": _rate(
            sum(1 for row in positive_rows if row.get("verdict") == "pass"),
            len(positive_rows),
        ),
        "bridge_parity_rate": _rate(sum(1 for row in bridge_rows if row.get("verdict") == "pass"), len(bridge_rows)),
        "negative_abstention_rate": _rate(
            sum(1 for row in negative_rows if row.get("verdict") in {"no_pairs", "pass"}),
            len(negative_rows),
        ),
        "abstention_correctness_rate": _rate(
            sum(1 for row in abstention_rows if row.get("verdict") == "pass"),
            len(abstention_rows),
        ),
        "receipt_persistence_rate": _rate(
            sum(1 for row in receipt_rows if row.get("verdict") == "pass"),
            len(receipt_rows),
        ),
        "provenance_preservation_rate": _rate(
            sum(1 for row in positive_rows if row.get("has_provenance")),
            len(positive_rows),
        ),
        "latency_ms_p95": float(resource.get("latency_ms_p95", _percentile(latencies, 95)) or 0),
        "catalog_lookup_ms_p95": float(resource.get("catalog_lookup_ms_p95", 0) or 0),
        "max_bytes_resolved": max((int(row.get("bytes_resolved", 0) or 0) for row in results), default=0),
    }
    thresholds = dict(payload.get("thresholds") or CERTIFICATION_THRESHOLDS)
    threshold_check = check_certification_thresholds(metrics, thresholds)
    unwaived_known_failures = [row for row in known_failures if not row.get("waived")]
    service_certified = threshold_check["passed"] and not unwaived_known_failures

    report = {
        "schema_version": HARNESS_VERSION,
        "baseline_suite_id": str(payload.get("baseline_suite_id", CERTIFICATION_SUITE_ID)),
        "fixture_revision": str(payload.get("fixture_revision", "")),
        "parent_suite_id": str(payload.get("parent_suite_id", "")),
        "corpus_id": str(payload.get("corpus_id", corpus_meta.get("corpus_id", CHAT_CONVERTER_SEED_CORPUS_ID))),
        "corpus_revision": str(
            payload.get("corpus_revision", corpus_meta.get("corpus_revision", CHAT_CONVERTER_SEED_CORPUS_REVISION))
        ),
        "harness_version": HARNESS_VERSION,
        "aperture_harness_version": APERTURE_HARNESS_VERSION,
        "generation_marker": corpus_meta.get("generation_marker", ""),
        "thresholds": thresholds,
        "metrics": metrics,
        "probe_count": len(results),
        "pass_count": sum(1 for row in results if row.get("verdict") == "pass"),
        "known_failure_count": len(known_failures),
        "service_certified": service_certified,
        "results": results,
        "threshold_check": threshold_check,
    }
    guard_known_failure_probes(report)
    return report


def render_certification_summary(report: Mapping[str, Any]) -> str:
    lines = [
        f"# Feed certification — {report.get('baseline_suite_id', CERTIFICATION_SUITE_ID)}",
        "",
        f"- fixture_revision: {report.get('fixture_revision', '')}",
        f"- corpus_revision: {report.get('corpus_revision', '')}",
        f"- service_certified: {report.get('service_certified', False)}",
        f"- probe_count: {report.get('probe_count', 0)}",
        f"- known_failure_count: {report.get('known_failure_count', 0)}",
        "",
        "## Metrics",
    ]
    for key, value in dict(report.get("metrics", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append("## Probes")
    for row in list(report.get("results", []) or []):
        lines.append(f"- {row.get('probe_id')}: {row.get('verdict')}")
    lines.append("")
    lines.append("## Threshold check")
    lines.append("")
    for key, value in dict(report.get("threshold_check", {}).get("checks", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.extend(
        [
            "",
            f"- Harness: `src/conversation_os/feed_certification_harness.py`",
            f"- Fixture: `tests/fixtures/aperture_baselines/v2/feed_certification_probes.json`",
        ]
    )
    return "\n".join(lines) + "\n"


def build_published_baseline(report: Mapping[str, Any]) -> Dict[str, Any]:
    observed_results: List[Dict[str, Any]] = []
    for row in list(report.get("results", []) or []):
        observed: Dict[str, Any] = {
            "probe_id": row.get("probe_id"),
            "category": row.get("category"),
            "verdict": row.get("verdict"),
        }
        for key in (
            "pair_count",
            "source_slugs",
            "preferred_source_slug",
            "has_provenance",
            "parity_ok",
            "bridge_source_refs",
            "feed_source_refs",
            "pair_source_refs",
            "result_status",
            "receipt_persisted",
            "latency_ms_p95",
            "catalog_lookup_ms_p95",
            "max_bytes_resolved",
        ):
            if key in row:
                observed[key] = row[key]
        observed_results.append(observed)

    notes = (
        "Corpus-backed Feed certification v2; bridge parity and provenance verified against "
        "chat_converter seed fixtures"
    )
    if not report.get("service_certified"):
        notes += "; service_certified false until all release thresholds pass"

    return {
        "schema_version": HARNESS_VERSION,
        "baseline_suite_id": report.get("baseline_suite_id", CERTIFICATION_SUITE_ID),
        "parent_suite_id": report.get("parent_suite_id", ""),
        "fixture_revision": report.get("fixture_revision", ""),
        "corpus_id": report.get("corpus_id", CHAT_CONVERTER_SEED_CORPUS_ID),
        "corpus_revision": report.get("corpus_revision", CHAT_CONVERTER_SEED_CORPUS_REVISION),
        "recorded_at": utc_now(),
        "harness_version": HARNESS_VERSION,
        "aperture_harness_version": report.get("aperture_harness_version", APERTURE_HARNESS_VERSION),
        "generation_marker": report.get("generation_marker", ""),
        "thresholds": dict(report.get("thresholds", {}) or CERTIFICATION_THRESHOLDS),
        "metrics": dict(report.get("metrics", {}) or {}),
        "summary": {
            "probe_count": report.get("probe_count", 0),
            "pass_count": report.get("pass_count", 0),
            "known_failure_count": report.get("known_failure_count", 0),
            "service_certified": bool(report.get("service_certified")),
            "notes": notes,
        },
        "threshold_check": dict(report.get("threshold_check", {}) or {}),
        "observed_results": observed_results,
    }
