"""Corpus-backed task-pack certification harness for Cognitive Aperture (R-013)."""

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
from .knowledge_layer import build_retrieval_bundle
from .library_tracker import CHAT_CONVERTER_SEED_CORPUS_ID, CHAT_CONVERTER_SEED_CORPUS_REVISION
from .storage import append_jsonl
from .task_pack_disclosure_adapter import (
    build_task_pack_evidence_query,
    collect_task_pack_evidence,
    enrich_task_pack_with_bounded_evidence,
    load_task_pack_disclosure_config,
    map_retrieval_bundle_to_evidence_blocks,
)
from .vault_ingest import ingest_text_content


MODULE_ID = "kernel.disclosure.task_pack_certification_harness"
CERTIFICATION_SUITE_ID = "chat_converter_seed_v2_task_pack_certification"
HARNESS_VERSION = "2.0"

CERTIFICATION_THRESHOLDS = {
    "positive_overlap_rate": 1.0,
    "bridge_parity_rate": 1.0,
    "negative_zero_block_rate": 1.0,
    "narrative_preservation_rate": 1.0,
    "abstention_correctness_rate": 1.0,
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
    "evaluate_narrative_preservation_probe",
    "evaluate_abstention_probe",
    "evaluate_resource_probe",
    "run_task_pack_certification_suite",
    "check_certification_thresholds",
    "guard_known_failure_probes",
    "render_certification_summary",
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
                "task_pack": {
                    "disclosure_service_v1": True,
                    "max_evidence_blocks": 4,
                    "evidence_retrieval_limit": 6,
                    "evidence_neighbor_limit": 4,
                },
                "knowledge": {
                    "fail_empty_admission_shadow_v1": True,
                    "fail_empty_admission_enforce_v1": True,
                },
            }
        ),
        encoding="utf-8",
    )


def _write_task_pack_capsules(root: Path) -> None:
    data_dir = root / "product" / "inner_world_v1" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    rows = [
        {
            "capsule_id": "capsule-task-pack-left",
            "capsule_type": "concept",
            "label": "Research insight",
            "summary": "Research insight about progressive disclosure and bounded task-pack evidence.",
            "confidence": 0.9,
            "ref_type": "concept",
            "ref_id": "concept-task-pack-left",
            "source_refs": ["fixture:research-insight.md"],
        },
        {
            "capsule_id": "capsule-task-pack-right",
            "capsule_type": "concept",
            "label": "Product design tension",
            "summary": "Product design tension between surprise and bounded evidence selection.",
            "confidence": 0.88,
            "ref_type": "concept",
            "ref_id": "concept-task-pack-right",
            "source_refs": ["fixture:product-design.md"],
        },
    ]
    for row in rows:
        append_jsonl(data_dir / "semantic_capsules.jsonl", row)


def seed_certification_corpus(root: Path) -> Dict[str, Any]:
    """Seed corpus-backed fixtures for task-pack certification."""
    _runtime_config(root)
    ingest_text_content(
        root,
        title="research-insight-fixture",
        content="# User\n\nResearch insight about progressive disclosure and bounded task-pack evidence.\n",
        source_ref="fixture:research-insight.md",
        source_type="chat_converter_conversation",
        metadata={"branch_id": "branch-task-pack-001", "scope_id": "scope-task-pack-001"},
    )
    ingest_text_content(
        root,
        title="product-design-fixture",
        content="# User\n\nProduct design tension between surprise and bounded evidence selection.\n",
        source_ref="fixture:product-design.md",
        source_type="chat_converter_conversation",
        metadata={"branch_id": "branch-task-pack-001", "scope_id": "scope-task-pack-001"},
    )
    _write_task_pack_capsules(root)
    snapshot = publish_corpus_catalog_snapshot(root)
    return {
        "corpus_id": CHAT_CONVERTER_SEED_CORPUS_ID,
        "corpus_revision": snapshot["catalog"].get("corpus_revision", CHAT_CONVERTER_SEED_CORPUS_REVISION),
        "generation_marker": snapshot.get("generation_marker", compute_generation_marker(root)),
    }


def _domain_overlays(probe: Mapping[str, Any]) -> List[str]:
    return [str(value) for value in list(probe.get("domain_overlays", []) or []) if str(value).strip()]


def _bytes_resolved(blocks: Sequence[Mapping[str, Any]]) -> int:
    return sum(len(str(row.get("label", ""))) + len(str(row.get("summary", ""))) for row in blocks)


def evaluate_positive_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    request = str(probe.get("request", "") or "")
    overlays = _domain_overlays(probe)
    evidence = collect_task_pack_evidence(root, request, domain_overlays=overlays)
    latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
    blocks = list(evidence.get("blocks", []) or [])
    count = int(evidence.get("count", 0) or 0)
    preferred = str(probe.get("preferred_source_slug", "") or "")
    has_overlap = bool(blocks) and all(list(block.get("matched_terms", []) or []) for block in blocks)
    preferred_hit = (
        any(_source_slug(str(block.get("source_ref", ""))) == preferred for block in blocks)
        if preferred
        else True
    )
    verdict = "pass" if count > 0 and has_overlap and preferred_hit else "fail"
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "positive",
        "expected_verdict": str(probe.get("expected_verdict", "pass") or "pass"),
        "verdict": verdict,
        "count": count,
        "has_query_overlap": has_overlap,
        "preferred_source_hit": preferred_hit,
        "source_refs": [str(block.get("source_ref", "")) for block in blocks],
        "latency_ms": latency_ms,
        "bytes_resolved": _bytes_resolved(blocks),
    }


def evaluate_bridge_parity_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    request = str(probe.get("request", "") or "")
    overlays = _domain_overlays(probe)
    config = load_task_pack_disclosure_config(root)
    evidence = collect_task_pack_evidence(root, request, domain_overlays=overlays)
    query = build_task_pack_evidence_query(request, overlays)
    bridge_bundle = build_retrieval_bundle(
        root,
        query,
        limit=max(1, int(config["retrieval_limit"])),
        neighbor_limit=max(0, int(config["neighbor_limit"])),
        include_cross_pond=False,
    )
    bridge_blocks = map_retrieval_bundle_to_evidence_blocks(
        bridge_bundle,
        query=query,
        max_blocks=int(config["max_evidence_blocks"]),
    )
    task_refs = sorted(str(block.get("source_ref", "")) for block in list(evidence.get("blocks", []) or []))
    bridge_refs = sorted(str(block.get("source_ref", "")) for block in bridge_blocks)
    parity_ok = task_refs == bridge_refs and int(evidence.get("count", 0) or 0) > 0
    latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "bridge_parity",
        "expected_verdict": str(probe.get("expected_verdict", "pass") or "pass"),
        "verdict": "pass" if parity_ok else "fail",
        "task_pack_source_refs": task_refs,
        "bridge_source_refs": bridge_refs,
        "parity_ok": parity_ok,
        "latency_ms": latency_ms,
        "bytes_resolved": _bytes_resolved(list(evidence.get("blocks", []) or [])),
    }


def evaluate_negative_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    request = str(probe.get("request", "") or "")
    evidence = collect_task_pack_evidence(root, request)
    latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
    count = int(evidence.get("count", 0) or 0)
    blocks = list(evidence.get("blocks", []) or [])
    zero_blocks = count == 0 and not blocks
    verdict = "no_hits" if zero_blocks else "fail"
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "negative",
        "expected_verdict": str(probe.get("expected_verdict", "no_hits") or "no_hits"),
        "verdict": verdict,
        "count": count,
        "zero_blocks": zero_blocks,
        "latency_ms": latency_ms,
        "bytes_resolved": 0,
    }


def evaluate_narrative_preservation_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    request = str(probe.get("request", "") or "")
    task_id = str(probe.get("task_id", "") or "")
    overlays = _domain_overlays(probe)
    pack = {"task_id": task_id, "request": request}
    enriched = enrich_task_pack_with_bounded_evidence(
        root,
        pack,
        request=request,
        domain_overlays=overlays,
    )
    expect_evidence = bool(probe.get("expect_bounded_evidence"))
    preserved = enriched.get("task_id") == task_id and enriched.get("request") == request
    has_bounded = "bounded_evidence" in enriched
    if expect_evidence:
        evidence_ok = has_bounded and int(enriched.get("bounded_evidence", {}).get("count", 0) or 0) > 0
    else:
        evidence_ok = not has_bounded
    verdict = "pass" if preserved and evidence_ok else "fail"
    latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
    blocks = list((enriched.get("bounded_evidence", {}) or {}).get("blocks", []) or [])
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "narrative_preservation",
        "expected_verdict": str(probe.get("expected_verdict", "pass") or "pass"),
        "verdict": verdict,
        "preserved_narrative": preserved,
        "bounded_evidence_present": has_bounded,
        "expect_bounded_evidence": expect_evidence,
        "latency_ms": latency_ms,
        "bytes_resolved": _bytes_resolved(blocks),
    }


def evaluate_abstention_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    snapshot_path = corpus_catalog_snapshot_path(root)
    snapshot_existed = snapshot_path.is_file()
    if snapshot_existed:
        snapshot_path.unlink()
    invalidate_corpus_catalog_cache(root)
    try:
        request = str(probe.get("request", "") or "")
        evidence = collect_task_pack_evidence(root, request)
        count = int(evidence.get("count", 0) or 0)
        blocks = list(evidence.get("blocks", []) or [])
        result_status = str(evidence.get("result_status", "") or "")
        abstained = count == 0 and not blocks
        abstention_status = result_status in {
            "abstained_stale_index",
            "abstained_dependency_not_ready",
            "empty_no_positive_match",
        }
        verdict = "pass" if abstained and abstention_status else "fail"
    finally:
        if snapshot_existed:
            publish_corpus_catalog_snapshot(root)
        else:
            invalidate_corpus_catalog_cache(root)
    latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "abstention",
        "expected_verdict": str(probe.get("expected_verdict", "pass") or "pass"),
        "verdict": verdict,
        "count": count,
        "result_status": result_status,
        "abstained_empty": abstained,
        "latency_ms": latency_ms,
        "bytes_resolved": 0,
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


_PROBE_EVALUATORS = {
    "positive": evaluate_positive_probe,
    "bridge_parity": evaluate_bridge_parity_probe,
    "negative": evaluate_negative_probe,
    "narrative_preservation": evaluate_narrative_preservation_probe,
    "abstention": evaluate_abstention_probe,
    "resource": evaluate_resource_probe,
}


def check_certification_thresholds(metrics: Mapping[str, Any], thresholds: Mapping[str, Any]) -> Dict[str, Any]:
    checks = {
        "positive_overlap_rate": float(metrics.get("positive_overlap_rate", 0)) >= float(
            thresholds.get("positive_overlap_rate", 1.0)
        ),
        "bridge_parity_rate": float(metrics.get("bridge_parity_rate", 0)) >= float(thresholds.get("bridge_parity_rate", 1.0)),
        "negative_zero_block_rate": float(metrics.get("negative_zero_block_rate", 0)) >= float(
            thresholds.get("negative_zero_block_rate", 1.0)
        ),
        "narrative_preservation_rate": float(metrics.get("narrative_preservation_rate", 0)) >= float(
            thresholds.get("narrative_preservation_rate", 1.0)
        ),
        "abstention_correctness_rate": float(metrics.get("abstention_correctness_rate", 0)) >= float(
            thresholds.get("abstention_correctness_rate", 1.0)
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


def run_task_pack_certification_suite(
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
        evaluator = _PROBE_EVALUATORS.get(category)
        if evaluator is None:
            raise ValueError(f"unsupported probe category: {category}")
        results.append(evaluator(root, probe))

    positive_rows = [row for row in results if row.get("category") == "positive"]
    bridge_rows = [row for row in results if row.get("category") == "bridge_parity"]
    negative_rows = [row for row in results if row.get("category") == "negative"]
    narrative_rows = [row for row in results if row.get("category") == "narrative_preservation"]
    abstention_rows = [row for row in results if row.get("category") == "abstention"]
    resource_rows = [row for row in results if row.get("category") == "resource"]
    known_failures = [row for row in results if row.get("verdict") == "known_failure"]

    positive_overlap_rate = (
        sum(1 for row in positive_rows if row.get("verdict") == "pass") / len(positive_rows) if positive_rows else 1.0
    )
    bridge_parity_rate = (
        sum(1 for row in bridge_rows if row.get("verdict") == "pass") / len(bridge_rows) if bridge_rows else 1.0
    )
    negative_zero_block_rate = (
        sum(1 for row in negative_rows if row.get("verdict") in {"pass", "no_hits"}) / len(negative_rows)
        if negative_rows
        else 1.0
    )
    narrative_preservation_rate = (
        sum(1 for row in narrative_rows if row.get("verdict") == "pass") / len(narrative_rows) if narrative_rows else 1.0
    )
    abstention_correctness_rate = (
        sum(1 for row in abstention_rows if row.get("verdict") == "pass") / len(abstention_rows)
        if abstention_rows
        else 1.0
    )
    latencies = [float(row.get("latency_ms", 0) or 0) for row in results if "latency_ms" in row]
    resource = resource_rows[0] if resource_rows else {}

    metrics = {
        "positive_overlap_rate": round(positive_overlap_rate, 4),
        "bridge_parity_rate": round(bridge_parity_rate, 4),
        "negative_zero_block_rate": round(negative_zero_block_rate, 4),
        "narrative_preservation_rate": round(narrative_preservation_rate, 4),
        "abstention_correctness_rate": round(abstention_correctness_rate, 4),
        "latency_ms_p95": _percentile(latencies, 95),
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
        f"# Task-pack certification — {report.get('baseline_suite_id', CERTIFICATION_SUITE_ID)}",
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
    for key, value in dict((report.get("threshold_check", {}) or {}).get("checks", {}) or {}).items():
        lines.append(f"- {key}: {value}")
    lines.append("")
    lines.append(f"- Harness: `src/conversation_os/task_pack_certification_harness.py`")
    lines.append(f"- Fixture: `tests/fixtures/aperture_baselines/v2/task_pack_certification_probes.json`")
    return "\n".join(lines) + "\n"
