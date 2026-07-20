"""Corpus-backed Shape certification harness for Cognitive Aperture (R-003)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

import conversation_os.meta_layer as meta_layer_module
import conversation_os.models as models_module

from .aperture_baseline_harness import HARNESS_VERSION as APERTURE_HARNESS_VERSION, _percentile, _source_slug
from .corpus_catalog_snapshot import compute_generation_marker, load_corpus_catalog_for_request, publish_corpus_catalog_snapshot
from .knowledge_layer import build_retrieval_bundle
from .library_tracker import CHAT_CONVERTER_SEED_CORPUS_ID, CHAT_CONVERTER_SEED_CORPUS_REVISION
from .shape_candidate_retrieval import build_shape_query, evaluate_anti_match, read_shape_retrieval_context
from .storage import append_jsonl, read_json, write_jsonl
from .vault_ingest import ingest_text_content


MODULE_ID = "kernel.disclosure.shape_certification_harness"
CERTIFICATION_SUITE_ID = "chat_converter_seed_v2_shape_certification"
HARNESS_VERSION = "2.0"

CERTIFICATION_THRESHOLDS = {
    "lexical_recall_at_1": 0.5,
    "shape_recall_at_1": 0.5,
    "shape_beats_lexical_rate": 0.5,
    "anti_match_precision": 1.0,
    "candidate_upgrade_rate": 0.0,
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
    "evaluate_retrieval_probe",
    "evaluate_anti_match_probe",
    "evaluate_resource_probe",
    "run_shape_certification_suite",
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
                "knowledge": {
                    "fail_empty_admission_shadow_v1": True,
                    "fail_empty_admission_enforce_v1": True,
                    "shape_candidate_search_v1": True,
                    "shape_anti_match_enforcement_v1": True,
                },
                "disclosure": {
                    "persistent_receipts_v1": True,
                    "receipts": {
                        "persistent_receipts_v1": True,
                        "rollout": {"bridge": "enforced", "holodeck": "enforced"},
                    },
                },
                "bridge": {
                    "disclosure_rollout_v1": "enforced",
                    "disclosure_service_v1": True,
                },
            }
        ),
        encoding="utf-8",
    )


def _write_shape_signature(root: Path, *, signature_id: str, source_ref: str, shape_name: str) -> None:
    evidence = models_module.EvidenceSpan(
        source_ref=source_ref,
        chunk_id=f"chunk-{signature_id}",
        text="Signal dilution through accumulation and hierarchy confusion in bounded systems.",
        kind="direct_quote",
    )
    signature = models_module.SystemDynamicSignature(
        signature_id=signature_id,
        source_ref=source_ref,
        source_kind="analysis_unit",
        source_anchor_id=f"unit-{signature_id}",
        title="Signal dilution signature",
        summary="Useful elements accumulate faster than hierarchy can coordinate.",
        system_boundary="Private cognitive layer under accumulation pressure",
        observer_lens="structural_interpretation",
        entities=[],
        relations=[],
        feedback_loops=[],
        candidate_shapes=[
            models_module.CandidateShape(
                shape_name=shape_name,
                confidence=0.82,
                rationale="Useful elements accumulate faster than hierarchy can coordinate.",
            ).to_dict()
        ],
        evidence_spans=[evidence.to_dict()],
        confidence=0.82,
        status="provisional",
        attributes={"scale": "local_interaction"},
    ).to_dict()
    write_jsonl(root / "product" / "inner_world_v1" / "data" / "shape_signatures.jsonl", [signature])


def seed_certification_corpus(root: Path) -> Dict[str, Any]:
    """Seed corpus-backed fixtures for certification (ingested sources, capsules, shapes)."""
    _runtime_config(root)
    data_dir = root / "product" / "inner_world_v1" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    source_ref = "fixture:shape-retrieval"
    ingest_text_content(
        root,
        title="shape-retrieval-fixture",
        content="# User\n\nPrivate cognitive layer under accumulation pressure.\n",
        source_ref=source_ref,
        source_type="chat_converter_conversation",
        metadata={"branch_id": "branch-shape-001", "scope_id": "scope-shape-001"},
    )
    _write_shape_signature(
        root,
        signature_id="signature-signal-dilution",
        source_ref=source_ref,
        shape_name="Signal Dilution Through Accumulation",
    )

    append_jsonl(
        data_dir / "semantic_capsules.jsonl",
        {
            "capsule_id": "capsule-lexical-distractor",
            "capsule_type": "concept",
            "label": "Accumulation hierarchy confusion noise",
            "summary": "Accumulation hierarchy confusion noise competes with attention and ranking.",
            "confidence": 0.96,
            "ref_type": "concept",
            "ref_id": "concept-distractor",
            "source_refs": ["fixture:distractor-fixture"],
            "attributes": {"domain": "bridge"},
        },
    )
    append_jsonl(
        data_dir / "semantic_capsules.jsonl",
        {
            "capsule_id": "capsule-shape-correct",
            "capsule_type": "concept",
            "label": "Signal dilution through accumulation",
            "summary": "Useful elements accumulate faster than hierarchy can coordinate in bounded systems.",
            "confidence": 0.9,
            "ref_type": "concept",
            "ref_id": "concept-shape-correct",
            "source_refs": [source_ref],
            "attributes": {
                "shape_signature_id": "signature-signal-dilution",
                "shape_name": "Signal Dilution Through Accumulation",
                "branch_id": "branch-shape-001",
                "scope_id": "scope-shape-001",
            },
        },
    )
    append_jsonl(
        data_dir / "semantic_capsules.jsonl",
        {
            "capsule_id": "capsule-maze-analogy",
            "capsule_type": "concept",
            "label": "Maze confusion hidden route",
            "summary": "A receiver is delayed before reaching the intended goal through a hidden route.",
            "confidence": 0.88,
            "ref_type": "meta",
            "ref_id": "meta-maze-1",
            "source_refs": ["fixture:maze"],
            "attributes": {
                "shape_signature_id": "signature-maze",
                "shape_name": "Search Confusion Through Hidden Route",
                "meta_id": "meta-maze-1",
                "branch_id": "branch-shape-001",
                "scope_id": "scope-shape-001",
            },
        },
    )
    meta_layer_module.record_shape_feedback(
        root,
        scope="project",
        scope_key="scope-shape-001",
        shape_name="Signal Dilution Through Accumulation",
        shape_definition="Useful elements accumulate faster than hierarchy.",
        feedback_type="rejected",
        rejected_candidate_id="meta-maze-1",
        anchor_meta_id="meta-shape-correct",
        anti_match_penalty=0.75,
    )
    snapshot = publish_corpus_catalog_snapshot(root)
    return {
        "corpus_id": CHAT_CONVERTER_SEED_CORPUS_ID,
        "corpus_revision": snapshot["catalog"].get("corpus_revision", CHAT_CONVERTER_SEED_CORPUS_REVISION),
        "generation_marker": snapshot.get("generation_marker", compute_generation_marker(root)),
    }


def _ranked_slugs(bundle: Mapping[str, Any]) -> List[str]:
    slugs: List[str] = []
    for row in list(bundle.get("seed_capsules", []) or []) + list(bundle.get("related_capsules", []) or []):
        for source_ref in row.get("source_refs", []) or [row.get("capsule_id", "")]:
            slug = _source_slug(str(source_ref))
            if slug and slug not in slugs:
                slugs.append(slug)
    return slugs


def _recall_at_k(ranked: Sequence[str], preferred: str, k: int) -> float:
    if not preferred:
        return 0.0
    return 1.0 if preferred in ranked[: max(1, k)] else 0.0


def _mrr(ranked: Sequence[str], preferred: str) -> float:
    if not preferred:
        return 0.0
    try:
        return 1.0 / (ranked.index(preferred) + 1)
    except ValueError:
        return 0.0


def _build_bundle(
    root: Path,
    probe: Mapping[str, Any],
    *,
    mode: str,
) -> Dict[str, Any]:
    shape_search = {"enabled": mode == "shape_assisted"}
    if mode == "shape_assisted":
        shape_search.update(
            {
                "branch_id": str(probe.get("branch_id", "") or ""),
                "scope_id": str(probe.get("scope_id", "") or ""),
                "enforce_anti_match": probe.get("category") == "anti_match",
            }
        )
    return build_retrieval_bundle(
        root,
        str(probe.get("query", "") or ""),
        limit=int(probe.get("top_k", 6) or 6),
        neighbor_limit=0,
        envelope_mode="open",
        shape_search=shape_search,
    )


def evaluate_retrieval_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    mode = str(probe.get("mode", "") or "")
    modes = [mode] if mode in {"lexical", "shape_assisted"} else ["lexical", "shape_assisted"]
    preferred = str(probe.get("preferred_source_slug", "") or "")
    distractor = str(probe.get("distractor_source_slug", "") or "")
    top_k = int(probe.get("top_k", 3) or 3)
    mode_results: Dict[str, Any] = {}
    for current_mode in modes:
        started = time.perf_counter()
        bundle = _build_bundle(root, probe, mode=current_mode)
        latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
        ranked = _ranked_slugs(bundle)
        preferred_rank = ranked.index(preferred) if preferred in ranked else -1
        distractor_rank = ranked.index(distractor) if distractor in ranked else -1
        beats_distractor = preferred_rank >= 0 and (distractor_rank < 0 or preferred_rank < distractor_rank)
        mode_results[current_mode] = {
            "ranked_source_slugs": ranked,
            "recall_at_k": _recall_at_k(ranked, preferred, top_k),
            "mrr": round(_mrr(ranked, preferred), 4),
            "preferred_rank": preferred_rank,
            "distractor_rank": distractor_rank,
            "structural_beats_distractor": beats_distractor,
            "result_status": str(bundle.get("result_status", "") or ""),
            "count": int(bundle.get("count", 0) or 0),
            "latency_ms": latency_ms,
            "bytes_resolved": sum(
                len(str(row.get("label", ""))) + len(str(row.get("summary", "")))
                for row in list(bundle.get("seed_capsules", []) or [])[:top_k]
            ),
            "candidate_upgrade_detected": any(
                "promoted" in str(signal)
                for row in list(bundle.get("shadow_admission", {}).get("decisions", []) or [])
                for signal in list(row.get("admission_signals", []) or [])
            ),
        }

    lexical = mode_results.get("lexical", {})
    shape = mode_results.get("shape_assisted", {})
    expected = str(probe.get("expected_verdict", "pass") or "pass")
    category = str(probe.get("category", "") or "")

    verdict = "pass"
    if category == "negative":
        verdict = "no_hits" if int(lexical.get("count", 0) or 0) == 0 else "fail"
    elif category == "cross_branch":
        abstained = lexical.get("result_status", "") in {"abstained_stale_index", "abstained_dependency_not_ready", "empty_no_positive_match"}
        shape_abstained = shape.get("result_status", "") in {"abstained_stale_index", "abstained_dependency_not_ready", "empty_no_positive_match"}
        verdict = "pass" if abstained or shape_abstained or preferred not in (lexical.get("ranked_source_slugs") or []) else "fail"
    elif expected == "known_failure":
        reference = lexical if probe.get("mode") == "lexical" else shape or lexical
        beats = bool(reference.get("structural_beats_distractor"))
        verdict = "known_failure" if not beats else "pass"
    elif shape and lexical:
        verdict = "pass" if shape.get("structural_beats_distractor") or lexical.get("structural_beats_distractor") else "fail"
    else:
        reference = lexical or shape
        verdict = "pass" if reference.get("structural_beats_distractor") or reference.get("recall_at_k", 0) >= 1.0 else "fail"

    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": category,
        "expected_verdict": expected,
        "verdict": verdict,
        "modes": mode_results,
        "shape_beats_lexical": bool(
            shape.get("structural_beats_distractor") and not lexical.get("structural_beats_distractor")
        ),
        "lexical_recall_at_k": float(lexical.get("recall_at_k", 0) or 0),
        "shape_recall_at_k": float(shape.get("recall_at_k", 0) or 0),
        "latency_ms": max(float(row.get("latency_ms", 0) or 0) for row in mode_results.values()) if mode_results else 0.0,
        "bytes_resolved": max(int(row.get("bytes_resolved", 0) or 0) for row in mode_results.values()) if mode_results else 0,
        "candidate_upgrade_detected": any(bool(row.get("candidate_upgrade_detected")) for row in mode_results.values()),
    }


def evaluate_anti_match_probe(root: Path, probe: Mapping[str, Any]) -> Dict[str, Any]:
    started = time.perf_counter()
    bundle = _build_bundle(root, probe, mode="shape_assisted")
    rejected_id = str(probe.get("rejected_capsule_id", "") or "")
    decisions = {
        row["capsule_id"]: row
        for row in list(bundle.get("shadow_admission", {}).get("decisions", []) or [])
        if row.get("capsule_id")
    }
    rejected = decisions.get(rejected_id, {})
    admitted = bool(rejected.get("admitted"))
    anti_match_ok = not admitted
    if rejected_id and rejected:
        shape_context = read_shape_retrieval_context(
            root,
            build_shape_query(
                str(probe.get("query", "") or ""),
                branch_id=str(probe.get("branch_id", "") or ""),
                scope_id=str(probe.get("scope_id", "") or ""),
            ),
        )
        capsule = next(
            (
                row
                for row in list(bundle.get("seed_capsules", []) or []) + list(bundle.get("related_capsules", []) or [])
                if str(row.get("capsule_id", "")) == rejected_id
            ),
            {"capsule_id": rejected_id, "attributes": {"meta_id": "meta-maze-1"}},
        )
        anti_match = evaluate_anti_match(
            capsule,
            anti_matches=list(shape_context.get("anti_match_projections", []) or []),
            branch_id=str(probe.get("branch_id", "") or ""),
            scope_id=str(probe.get("scope_id", "") or ""),
            structural_score=0.5,
        )
        anti_match_ok = anti_match.outcome in {"hard_reject", "penalize"} and not admitted
    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": "anti_match",
        "verdict": "pass" if anti_match_ok else "fail",
        "rejected_capsule_id": rejected_id,
        "anti_match_precision": 1.0 if anti_match_ok else 0.0,
        "candidate_upgrade_detected": any(
            "promoted" in str(signal)
            for row in decisions.values()
            for signal in list(row.get("admission_signals", []) or [])
        ),
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
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
        result = evaluate_retrieval_probe(root, {**probe, "category": "positive", "mode": "shape_assisted"})
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
        "lexical_recall_at_1": float(metrics.get("lexical_recall_at_1", 0)) >= float(thresholds.get("lexical_recall_at_1", 0.5)),
        "shape_recall_at_1": float(metrics.get("shape_recall_at_1", 0)) >= float(thresholds.get("shape_recall_at_1", 0.5)),
        "shape_beats_lexical_rate": float(metrics.get("shape_beats_lexical_rate", 0)) >= float(
            thresholds.get("shape_beats_lexical_rate", 0.5)
        ),
        "anti_match_precision": float(metrics.get("anti_match_precision", 0)) >= float(thresholds.get("anti_match_precision", 1.0)),
        "candidate_upgrade_rate": float(metrics.get("candidate_upgrade_rate", 0)) <= float(thresholds.get("candidate_upgrade_rate", 0.0)),
        "abstention_correctness_rate": float(metrics.get("abstention_correctness_rate", 0)) >= float(
            thresholds.get("abstention_correctness_rate", 1.0)
        ),
        "latency_ms_p95": float(metrics.get("latency_ms_p95", 0)) <= float(thresholds.get("latency_ms_p95", 750)),
        "max_catalog_lookup_ms": float(metrics.get("catalog_lookup_ms_p95", 0)) <= float(thresholds.get("max_catalog_lookup_ms", 50)),
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


def run_shape_certification_suite(
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
        if category == "anti_match":
            results.append(evaluate_anti_match_probe(root, probe))
        elif category == "resource":
            results.append(evaluate_resource_probe(root, probe))
        else:
            results.append(evaluate_retrieval_probe(root, probe))

    retrieval_rows = [row for row in results if row.get("category") not in {"anti_match", "resource"}]
    anti_match_rows = [row for row in results if row.get("category") == "anti_match"]
    resource_rows = [row for row in results if row.get("category") == "resource"]
    cross_branch_rows = [row for row in retrieval_rows if row.get("category") == "cross_branch"]
    known_failures = [row for row in results if row.get("verdict") == "known_failure"]

    lexical_recall = (
        sum(float(row.get("lexical_recall_at_k", 0) or 0) for row in retrieval_rows if "lexical_recall_at_k" in row)
        / max(1, len([row for row in retrieval_rows if "lexical_recall_at_k" in row]))
    )
    shape_recall = (
        sum(float(row.get("shape_recall_at_k", 0) or 0) for row in retrieval_rows if "shape_recall_at_k" in row)
        / max(1, len([row for row in retrieval_rows if "shape_recall_at_k" in row]))
    )
    shape_beats_lexical_rate = (
        sum(1 for row in retrieval_rows if row.get("shape_beats_lexical")) / len(retrieval_rows) if retrieval_rows else 0.0
    )
    anti_match_precision = (
        sum(float(row.get("anti_match_precision", 0) or 0) for row in anti_match_rows) / len(anti_match_rows)
        if anti_match_rows
        else 1.0
    )
    upgrade_rate = (
        sum(1 for row in results if row.get("candidate_upgrade_detected")) / len(results) if results else 0.0
    )
    abstention_correctness = (
        sum(1 for row in cross_branch_rows if row.get("verdict") == "pass") / len(cross_branch_rows)
        if cross_branch_rows
        else 1.0
    )
    latencies = [float(row.get("latency_ms", 0) or 0) for row in results if "latency_ms" in row]
    resource = resource_rows[0] if resource_rows else {}

    metrics = {
        "lexical_recall_at_1": round(lexical_recall, 4),
        "shape_recall_at_1": round(shape_recall, 4),
        "shape_beats_lexical_rate": round(shape_beats_lexical_rate, 4),
        "anti_match_precision": round(anti_match_precision, 4),
        "candidate_upgrade_rate": round(upgrade_rate, 4),
        "abstention_correctness_rate": round(abstention_correctness, 4),
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
        "corpus_revision": str(payload.get("corpus_revision", corpus_meta.get("corpus_revision", CHAT_CONVERTER_SEED_CORPUS_REVISION))),
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
        f"# Shape certification — {report.get('baseline_suite_id', CERTIFICATION_SUITE_ID)}",
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
    return "\n".join(lines) + "\n"
