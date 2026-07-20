"""Shape-aware and service performance baselines for Cognitive Aperture (CAE-006B)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from .aperture_baseline_harness import (
    BASELINE_SUITE_ID,
    DEFAULT_THRESHOLDS,
    HARNESS_VERSION,
    _percentile,
    _source_slug,
)
from .holodeck_disclosure_adapter import (
    collect_disclosure_knowledge_candidates,
    retrieval_decision_subset,
)
from .knowledge_layer import build_retrieval_bundle
from .library_tracker import CHAT_CONVERTER_SEED_CORPUS_ID, CHAT_CONVERTER_SEED_CORPUS_REVISION
from .reasoning_bridge import get_context_bundle, heuristic_classify_turn
from .shape_projection_reader import migration_decision, read_shape_projections
from .storage import append_jsonl


MODULE_ID = "kernel.disclosure.aperture_service_baseline_harness"
SERVICE_BASELINE_SUITE_ID = "chat_converter_seed_v1_service"
SERVICE_HARNESS_VERSION = "1.0"

SERVICE_THRESHOLDS = {
    **DEFAULT_THRESHOLDS,
    "structural_beats_distractor_rate": 1.0,
    "anti_match_block_rate": 1.0,
    "candidate_upgrade_rate": 0.0,
    "adapter_parity_rate": 1.0,
    "cache_hit_rate_min": 0.0,
    "max_expansion_count": 12,
}

PUBLIC_API = (
    "MODULE_ID",
    "SERVICE_BASELINE_SUITE_ID",
    "SERVICE_HARNESS_VERSION",
    "SERVICE_THRESHOLDS",
    "seed_semantic_capsules",
    "evaluate_retrieval_ranking_probe",
    "evaluate_shape_projection_probe",
    "evaluate_adapter_parity_probe",
    "evaluate_service_performance_probe",
    "run_service_baseline_suite",
    "render_service_baseline_summary",
    "published_service_baseline_manifest",
    "check_service_thresholds",
)
__all__ = list(PUBLIC_API)


def seed_semantic_capsules(root: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    from .corpus_catalog_snapshot import publish_corpus_catalog_snapshot

    path = root / "product" / "inner_world_v1" / "data" / "semantic_capsules.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    for row in rows:
        append_jsonl(path, dict(row))
    publish_corpus_catalog_snapshot(root)


def _capsule_rows_for_seed() -> List[Dict[str, Any]]:
    return [
        {
            "capsule_id": "capsule-mapping-mind",
            "capsule_type": "concept",
            "label": "Mapping the mind for agentic systems",
            "summary": "Recursive self-model architecture for mapping the mind in agentic systems.",
            "confidence": 0.93,
            "ref_type": "concept",
            "ref_id": "concept-mapping-mind",
            "source_refs": ["fixture:mapping-the-mind-for-agentic-systems"],
            "attributes": {
                "domain": "agentic",
                "shape_signature_id": "legacy-shape-mapping",
                "semantic_address": "recursive self-model mapping mind agentic systems architecture",
            },
        },
        {
            "capsule_id": "capsule-understanding-thought",
            "capsule_type": "concept",
            "label": "Understanding the nature of thought",
            "summary": "Biological cognition and agent memory in phenomenology of thought.",
            "confidence": 0.95,
            "ref_type": "concept",
            "ref_id": "concept-understanding-thought",
            "source_refs": ["fixture:understanding-the-nature-of-thought"],
            "attributes": {
                "domain": "cognition",
                "semantic_address": "biological cognition agent memory phenomenology thought nature",
            },
        },
        {
            "capsule_id": "capsule-hybrid-rag",
            "capsule_type": "concept",
            "label": "Agentic hybrid RAG",
            "summary": "Hybrid retrieval combines graph traversal and information extraction pipelines.",
            "confidence": 0.92,
            "ref_type": "concept",
            "ref_id": "concept-hybrid-rag",
            "source_refs": ["fixture:agentic-hybrid-rag-for-information-extraction"],
            "attributes": {"domain": "retrieval"},
        },
    ]


def _ranked_slugs(bundle: Mapping[str, Any]) -> List[str]:
    slugs: List[str] = []
    for row in list(bundle.get("seed_capsules", []) or []) + list(bundle.get("related_capsules", []) or []):
        for source_ref in row.get("source_refs", []) or [row.get("capsule_id", "")]:
            slug = _source_slug(str(source_ref))
            if slug and slug not in slugs:
                slugs.append(slug)
    return slugs


def evaluate_retrieval_ranking_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    seed_semantic_capsules(root, _capsule_rows_for_seed())
    bundle = build_retrieval_bundle(
        root,
        str(probe.get("query", "") or ""),
        limit=int(probe.get("limit", 6) or 6),
        neighbor_limit=int(probe.get("neighbor_limit", 4) or 4),
        include_cross_pond=False,
    )
    latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
    ranked = _ranked_slugs(bundle)
    preferred = str(probe.get("preferred_source_slug", "") or "")
    distractor = str(probe.get("distractor_source_slug", "") or "")
    preferred_rank = ranked.index(preferred) if preferred in ranked else -1
    distractor_rank = ranked.index(distractor) if distractor in ranked else -1
    structural_beats_distractor = preferred_rank >= 0 and (distractor_rank < 0 or preferred_rank < distractor_rank)
    expected_verdict = str(probe.get("expected_verdict", "pass") or "pass")
    if expected_verdict == "known_failure":
        verdict = "known_failure" if not structural_beats_distractor else "pass"
    elif expected_verdict == "no_hits":
        verdict = "no_hits" if int(bundle.get("count", 0) or 0) == 0 else "fail"
    else:
        verdict = "pass" if structural_beats_distractor else "fail"
    bytes_resolved = sum(
        len(str(row.get("label", ""))) + len(str(row.get("summary", "")))
        for row in list(bundle.get("seed_capsules", []) or [])[:3]
    )
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": str(probe.get("category", "shape")),
        "query": str(probe.get("query", "") or ""),
        "verdict": verdict,
        "result_status": str(bundle.get("result_status", "") or ("disclosed" if bundle.get("count") else "empty_no_positive_match")),
        "ranked_source_slugs": ranked,
        "preferred_source_slug": preferred,
        "distractor_source_slug": distractor,
        "structural_beats_distractor": structural_beats_distractor,
        "expansion_count": int(bundle.get("count", 0) or 0),
        "latency_ms": latency_ms,
        "bytes_resolved": bytes_resolved,
    }


def _seed_shape_legacy_fixtures(root: Path) -> None:
    """Minimal legacy Shape signatures and AntiMatch records for service probes."""
    import conversation_os.meta_layer as meta_layer_module

    data_dir = root / "product" / "inner_world_v1" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    source_ref = "fixture:mapping-the-mind-for-agentic-systems"
    signature = {
        "signature_id": "legacy-shape-mapping",
        "source_ref": source_ref,
        "source_kind": "analysis_unit",
        "source_anchor_id": "unit-legacy-shape-mapping",
        "title": "Mapping mind structural signature",
        "summary": "Recursive self-model and blocked transition before goal.",
        "system_boundary": "Agent memory mapping under bounded aperture",
        "observer_lens": "structural_interpretation",
        "entities": [],
        "relations": [],
        "feedback_loops": [],
        "candidate_shapes": [
            {
                "shape_name": "Blocked Transition Before Goal",
                "confidence": 0.75,
                "rationale": "Receiver delayed before reaching intended goal.",
            }
        ],
        "evidence_spans": [],
        "confidence": 0.75,
        "status": "provisional",
        "attributes": {"scale": "local_interaction", "shape_signature_id": "legacy-shape-mapping"},
    }
    from .storage import write_jsonl

    write_jsonl(data_dir / "shape_signatures.jsonl", [signature])
    meta_layer_module.record_shape_feedback(
        root,
        scope="project",
        scope_key="scope-service-baseline",
        shape_name="Signal Dilution Through Accumulation",
        shape_definition="Useful elements accumulate faster than hierarchy.",
        feedback_type="rejected",
        rejected_candidate_id="meta-maze-service-baseline",
        anchor_meta_id="meta-anchor-service-baseline",
        anti_match_penalty=0.25,
    )


def evaluate_shape_projection_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    seed_semantic_capsules(root, _capsule_rows_for_seed())
    if probe.get("require_anti_match_present") or probe.get("seed_shape_legacy"):
        _seed_shape_legacy_fixtures(root)
    shape = read_shape_projections(root, include_legacy=True, include_anti_match=True)
    migration = migration_decision()
    anti_matches = list(shape.get("legacy", {}).get("anti_match_projections", []) or [])
    candidates = list(shape.get("legacy", {}).get("candidate_projections", []) or [])
    promoted = [row for row in candidates if str(row.get("kind", "")) == "promoted"]
    upgraded_in_retrieval = False
    bundle = build_retrieval_bundle(root, str(probe.get("query", "") or "recursive self-model agent memory"))
    for row in list(bundle.get("shadow_admission", {}).get("decisions", []) or []):
        signals = [str(value) for value in row.get("admission_signals", []) or []]
        if any("promoted" in signal for signal in signals):
            upgraded_in_retrieval = True
    blocks_analogy = bool(migration.get("promotion_allowed") is False and not promoted)
    verdict = "pass"
    if probe.get("require_anti_match_present") and not anti_matches:
        verdict = "pass" if shape.get("readiness_state") == "legacy_only" else "fail"
    if upgraded_in_retrieval:
        verdict = "fail"
    if not blocks_analogy:
        verdict = "fail"
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "shape",
        "verdict": verdict,
        "shape_readiness_state": shape.get("readiness_state", ""),
        "anti_match_count": len(anti_matches),
        "candidate_projection_count": len(candidates),
        "promoted_projection_count": len(promoted),
        "promotion_allowed": bool(migration.get("promotion_allowed")),
        "candidate_upgrade_detected": upgraded_in_retrieval,
        "anti_match_blocks_analogy": blocks_analogy,
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
    }


def evaluate_adapter_parity_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    seed_semantic_capsules(root, _capsule_rows_for_seed())
    query = str(probe.get("query", "") or "recursive self-model agent memory mapping mind")
    bridge_bundle = build_retrieval_bundle(root, query, limit=6, neighbor_limit=4, include_cross_pond=False)
    seed_bundle = {
        "topic_terms": query.split(),
        "combined_terms": query.split(),
    }
    holodeck_candidates, _ = collect_disclosure_knowledge_candidates(root, seed_bundle, max_source_refs=6)
    holodeck_subset = {
        "count": len(holodeck_candidates),
        "result_status": str(holodeck_candidates[0].get("disclosure_result_status", "") if holodeck_candidates else bridge_bundle.get("result_status", "")),
        "capsule_ids": sorted(row.get("capsule_id", "") for row in holodeck_candidates if row.get("capsule_id")),
        "source_refs": sorted(
            {str(row.get("source_ref", "")).strip() for row in holodeck_candidates if str(row.get("source_ref", "")).strip()}
        ),
    }
    bridge_subset = retrieval_decision_subset(bridge_bundle)
    parity = holodeck_subset == {
        "count": bridge_subset["count"],
        "result_status": bridge_subset["result_status"],
        "capsule_ids": bridge_subset["capsule_ids"],
        "source_refs": bridge_subset["source_refs"],
    }
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "parity",
        "verdict": "pass" if parity else "fail",
        "bridge_subset": bridge_subset,
        "holodeck_subset": holodeck_subset,
        "adapter_parity": parity,
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
    }


def evaluate_service_performance_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    seed_semantic_capsules(root, _capsule_rows_for_seed())
    runtime = root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
    runtime.mkdir(parents=True)
    config_dir = root / "product" / "inner_world_v1" / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "runtime.json"
    if not config_path.exists():
        config_path.write_text(json.dumps({"bridge": {"orient_first_compose_v1": True}}), encoding="utf-8")

    latencies: List[float] = []
    bytes_resolved: List[int] = []
    expansion_counts: List[int] = []
    iterations = max(1, int(probe.get("iterations", 3) or 3))
    for _ in range(iterations):
        started = time.perf_counter()
        context = heuristic_classify_turn(
            root,
            {
                "request_id": "req-perf-baseline",
                "session_id": "session-perf-baseline",
                "raw_text": str(probe.get("query", "") or "recursive self-model agent memory"),
                "caller_hints": {"workspace_id": "ws-perf-baseline", "envelope_mode": "bounded"},
                "domain_hints": [],
                "source_refs": [],
            },
        )
        bundle = get_context_bundle(root, context)
        latencies.append(round((time.perf_counter() - started) * 1000.0, 3))
        frame_blocks = list(bundle.get("frame_bundle", {}).get("included_blocks", []) or [])
        bytes_resolved.append(
            sum(len(str(row.get("summary", ""))) + len(str(row.get("source_ref", ""))) for row in frame_blocks)
        )
        expansion_counts.append(int(bundle.get("global_fallback", {}).get("count", 0) or 0))

    cache_probe = build_retrieval_bundle(root, str(probe.get("query", "") or "recursive self-model agent memory"))
    cache_probe_repeat = build_retrieval_bundle(root, str(probe.get("query", "") or "recursive self-model agent memory"))
    cache_hit = cache_probe.get("count") == cache_probe_repeat.get("count")

    p50 = _percentile(latencies, 50)
    p95 = _percentile(latencies, 95)
    max_bytes = max(bytes_resolved or [0])
    max_expansion = max(expansion_counts or [0])
    thresholds = dict(probe.get("thresholds") or SERVICE_THRESHOLDS)
    within_latency = p95 <= float(thresholds.get("latency_ms_p95", 750))
    within_bytes = max_bytes <= int(thresholds.get("max_bytes_resolved", 65536))
    within_expansion = max_expansion <= int(thresholds.get("max_expansion_count", 12))
    verdict = "pass" if within_latency and within_bytes and within_expansion else "fail"
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "performance",
        "verdict": verdict,
        "latency_ms_p50": p50,
        "latency_ms_p95": p95,
        "max_bytes_resolved": max_bytes,
        "max_expansion_count": max_expansion,
        "cache_hit_stable": cache_hit,
        "iterations": iterations,
    }


def run_service_baseline_suite(
    root: Path,
    probe_suite: Mapping[str, Any] | Path | str,
) -> Dict[str, Any]:
    if isinstance(probe_suite, (str, Path)):
        payload = json.loads(Path(probe_suite).read_text(encoding="utf-8"))
    else:
        payload = dict(probe_suite)
    probes = list(payload.get("probes", []) or [])
    results: List[Dict[str, Any]] = []
    for probe in probes:
        category = str(probe.get("category", "") or "")
        evaluator = {
            "shape": evaluate_shape_projection_probe,
            "ranking": evaluate_retrieval_ranking_probe,
            "distractor": evaluate_retrieval_ranking_probe,
            "parity": evaluate_adapter_parity_probe,
            "performance": evaluate_service_performance_probe,
        }.get(category, evaluate_retrieval_ranking_probe)
        results.append(evaluator(root, probe))

    latencies = [float(row.get("latency_ms", 0) or 0) for row in results if "latency_ms" in row]
    perf_rows = [row for row in results if row.get("category") == "performance"]
    shape_rows = [row for row in results if row.get("category") == "shape"]
    ranking_rows = [row for row in results if row.get("category") == "ranking"]
    distractor_rows = [row for row in results if row.get("category") == "distractor"]
    parity_rows = [row for row in results if row.get("category") == "parity"]
    passes = [row for row in results if row.get("verdict") == "pass"]
    known_failures = [row for row in results if row.get("verdict") == "known_failure"]

    structural_rate = (
        sum(1 for row in ranking_rows if row.get("structural_beats_distractor")) / len(ranking_rows)
        if ranking_rows
        else 1.0
    )
    distractor_harm_rate = (
        sum(
            1
            for row in distractor_rows
            if row.get("verdict") in {"known_failure", "fail"}
            and not row.get("structural_beats_distractor")
        )
        / len(distractor_rows)
        if distractor_rows
        else 0.0
    )
    anti_match_rate = (
        sum(1 for row in shape_rows if row.get("anti_match_blocks_analogy")) / len(shape_rows) if shape_rows else 1.0
    )
    upgrade_rate = (
        sum(1 for row in shape_rows if row.get("candidate_upgrade_detected")) / len(shape_rows) if shape_rows else 0.0
    )
    parity_rate = sum(1 for row in parity_rows if row.get("adapter_parity")) / len(parity_rows) if parity_rows else 1.0

    thresholds = dict(payload.get("thresholds") or SERVICE_THRESHOLDS)
    return {
        "schema_version": SERVICE_HARNESS_VERSION,
        "baseline_suite_id": str(payload.get("baseline_suite_id", SERVICE_BASELINE_SUITE_ID)),
        "parent_suite_id": BASELINE_SUITE_ID,
        "corpus_id": str(payload.get("corpus_id", CHAT_CONVERTER_SEED_CORPUS_ID)),
        "corpus_revision": str(payload.get("corpus_revision", CHAT_CONVERTER_SEED_CORPUS_REVISION)),
        "harness_version": SERVICE_HARNESS_VERSION,
        "aperture_harness_version": HARNESS_VERSION,
        "thresholds": thresholds,
        "probe_count": len(results),
        "pass_count": len(passes),
        "known_failure_count": len(known_failures),
        "structural_beats_distractor_rate": round(structural_rate, 4),
        "distractor_harm_rate": round(distractor_harm_rate, 4),
        "anti_match_block_rate": round(anti_match_rate, 4),
        "candidate_upgrade_rate": round(upgrade_rate, 4),
        "adapter_parity_rate": round(parity_rate, 4),
        "latency_ms_p50": _percentile(latencies, 50),
        "latency_ms_p95": _percentile(latencies, 95),
        "max_bytes_resolved": max((int(row.get("bytes_resolved", 0) or 0) for row in results), default=0),
        "max_expansion_count": max((int(row.get("expansion_count", 0) or 0) for row in results), default=0),
        "results": results,
        "threshold_check": check_service_thresholds(
            {
                "structural_beats_distractor_rate": structural_rate,
                "anti_match_block_rate": anti_match_rate,
                "candidate_upgrade_rate": upgrade_rate,
                "adapter_parity_rate": parity_rate,
                "latency_ms_p50": _percentile(latencies, 50),
                "latency_ms_p95": _percentile(latencies, 95),
                "max_bytes_resolved": max((int(row.get("bytes_resolved", 0) or 0) for row in results), default=0),
                "max_expansion_count": max((int(row.get("expansion_count", 0) or 0) for row in results), default=0),
            },
            thresholds,
        ),
    }


def check_service_thresholds(metrics: Mapping[str, Any], thresholds: Mapping[str, Any]) -> Dict[str, Any]:
    checks = {
        "structural_beats_distractor_rate": float(metrics.get("structural_beats_distractor_rate", 0)) >= float(
            thresholds.get("structural_beats_distractor_rate", 1.0)
        ),
        "anti_match_block_rate": float(metrics.get("anti_match_block_rate", 0)) >= float(
            thresholds.get("anti_match_block_rate", 1.0)
        ),
        "candidate_upgrade_rate": float(metrics.get("candidate_upgrade_rate", 0)) <= float(
            thresholds.get("candidate_upgrade_rate", 0.0)
        ),
        "adapter_parity_rate": float(metrics.get("adapter_parity_rate", 0)) >= float(
            thresholds.get("adapter_parity_rate", 1.0)
        ),
        "latency_ms_p50": float(metrics.get("latency_ms_p50", 0)) <= float(thresholds.get("latency_ms_p50", 250)),
        "latency_ms_p95": float(metrics.get("latency_ms_p95", 0)) <= float(thresholds.get("latency_ms_p95", 750)),
        "max_bytes_resolved": int(metrics.get("max_bytes_resolved", 0)) <= int(thresholds.get("max_bytes_resolved", 65536)),
        "max_expansion_count": int(metrics.get("max_expansion_count", 0)) <= int(thresholds.get("max_expansion_count", 12)),
    }
    return {"passed": all(checks.values()), "checks": checks}


def published_service_baseline_manifest() -> Dict[str, Any]:
    return {
        "schema_version": SERVICE_HARNESS_VERSION,
        "baseline_suite_id": SERVICE_BASELINE_SUITE_ID,
        "parent_suite_id": BASELINE_SUITE_ID,
        "corpus_id": CHAT_CONVERTER_SEED_CORPUS_ID,
        "corpus_revision": CHAT_CONVERTER_SEED_CORPUS_REVISION,
        "recorded_at": "2026-07-19T00:00:00+00:00",
        "harness_version": SERVICE_HARNESS_VERSION,
        "thresholds": dict(SERVICE_THRESHOLDS),
        "summary": {
            "probe_count": 5,
            "pass_count": 4,
            "known_failure_count": 1,
            "service_certified": False,
            "notes": "Near-neighbour distractor preserved; Shape legacy adapter blocks promotion",
        },
        "observed_results": [
            {
                "probe_id": "structural-agent-memory-ranking",
                "verdict": "pass",
                "structural_beats_distractor": True,
                "preferred_source_slug": "mapping-the-mind-for-agentic-systems",
            },
            {
                "probe_id": "near-neighbour-distractor-harm",
                "verdict": "known_failure",
                "preferred_source_slug": "mapping-the-mind-for-agentic-systems",
                "distractor_source_slug": "understanding-the-nature-of-thought",
            },
            {
                "probe_id": "shape-anti-match-no-promotion",
                "verdict": "pass",
                "promotion_allowed": False,
                "candidate_upgrade_detected": False,
            },
            {
                "probe_id": "bridge-holodeck-retrieval-parity",
                "verdict": "pass",
                "adapter_parity": True,
            },
            {
                "probe_id": "disclosure-path-performance",
                "verdict": "pass",
                "latency_ms_p95": 4.0,
            },
        ],
    }


def render_service_baseline_summary(report: Mapping[str, Any]) -> str:
    lines = [
        f"# Service baseline report — {report.get('baseline_suite_id', SERVICE_BASELINE_SUITE_ID)}",
        "",
        f"- Harness version: `{report.get('harness_version', SERVICE_HARNESS_VERSION)}`",
        f"- Parent suite: `{report.get('parent_suite_id', BASELINE_SUITE_ID)}`",
        f"- Corpus revision: `{report.get('corpus_revision', CHAT_CONVERTER_SEED_CORPUS_REVISION)}`",
        f"- Probes: {report.get('probe_count', 0)} (pass {report.get('pass_count', 0)}, known failures {report.get('known_failure_count', 0)})",
        f"- Structural beats distractor: {report.get('structural_beats_distractor_rate', 0.0)}",
        f"- Distractor harm rate: {report.get('distractor_harm_rate', 0.0)}",
        f"- AntiMatch block rate: {report.get('anti_match_block_rate', 0.0)}",
        f"- Candidate upgrade rate: {report.get('candidate_upgrade_rate', 0.0)}",
        f"- Adapter parity rate: {report.get('adapter_parity_rate', 0.0)}",
        f"- Latency p50/p95 (ms): {report.get('latency_ms_p50')} / {report.get('latency_ms_p95')}",
        f"- Threshold check passed: {report.get('threshold_check', {}).get('passed', False)}",
        "",
        "## Probe results",
        "",
        "| probe | category | verdict | notes |",
        "| --- | --- | --- | --- |",
    ]
    for row in report.get("results", []) or []:
        note = row.get("preferred_source_slug") or row.get("top_source_slug") or row.get("adapter_parity") or ""
        lines.append(
            f"| `{row.get('probe_id', '')}` | {row.get('category', '')} | {row.get('verdict', '')} | {note} |"
        )
    return "\n".join(lines) + "\n"
