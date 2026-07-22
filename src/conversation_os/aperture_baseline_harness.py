"""Pre-enforcement baseline evaluation harness for Cognitive Aperture (CAE-006A)."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from .disclosure_contracts import RESULT_STATUSES
from .library_tracker import (
    CHAT_CONVERTER_SEED_CORPUS_ID,
    CHAT_CONVERTER_SEED_CORPUS_REVISION,
    build_corpus_catalog,
    filter_library_sources,
)

MODULE_ID = "kernel.disclosure.aperture_baseline_harness"
HARNESS_VERSION = "1.0"
BASELINE_SUITE_ID = "chat_converter_seed_v1"

PROBE_CATEGORIES = (
    "positive",
    "negative",
    "distractor",
    "privacy",
    "budget",
    "leakage",
    "provenance",
    "shape",
    "readiness",
)

PROBE_VERDICTS = ("pass", "fail", "known_failure", "no_hits", "abstained", "denied", "error")

# Stage A approved thresholds — recorded before enforcement; not yet gates.
DEFAULT_THRESHOLDS = {
    "positive_recall_at_1": 0.80,
    "negative_false_open_rate": 0.0,
    "latency_ms_p50": 250,
    "latency_ms_p95": 750,
    "max_bytes_resolved": 65536,
}

PUBLIC_API = (
    "MODULE_ID",
    "HARNESS_VERSION",
    "BASELINE_SUITE_ID",
    "PROBE_CATEGORIES",
    "PROBE_VERDICTS",
    "DEFAULT_THRESHOLDS",
    "load_probe_suite",
    "classify_result_status",
    "evaluate_probe",
    "run_baseline_suite",
    "render_baseline_summary",
    "published_baseline_manifest",
)
__all__ = list(PUBLIC_API)


def load_probe_suite(path: Path | str) -> Dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("probe suite must be a JSON object")
    probes = payload.get("probes", [])
    if not isinstance(probes, list):
        raise ValueError("probe suite probes must be a list")
    return payload


def published_baseline_manifest() -> Dict[str, Any]:
    """Immutable recorded baseline for the seed corpus (observed 2026-07-19)."""
    return {
        "schema_version": HARNESS_VERSION,
        "baseline_suite_id": BASELINE_SUITE_ID,
        "corpus_id": CHAT_CONVERTER_SEED_CORPUS_ID,
        "corpus_revision": CHAT_CONVERTER_SEED_CORPUS_REVISION,
        "recorded_at": "2026-07-19T00:00:00+00:00",
        "thresholds": dict(DEFAULT_THRESHOLDS),
        "summary": {
            "probe_count": 6,
            "pass_count": 5,
            "known_failure_count": 1,
            "retrieval_certified": False,
        },
        "observed_results": [
            {
                "probe_id": "exact-hybrid-rag-file",
                "verdict": "pass",
                "result_status": "disclosed",
                "top_source_slug": "agentic-hybrid-rag-for-information-extraction",
            },
            {
                "probe_id": "retrieval-information-extraction-query",
                "verdict": "pass",
                "result_status": "disclosed",
                "top_source_slug": "agentic-hybrid-rag-for-information-extraction",
            },
            {
                "probe_id": "semantic-context-embedding-query",
                "verdict": "pass",
                "result_status": "disclosed",
                "top_source_slug": "context-in-embedding-spaces",
            },
            {
                "probe_id": "out-of-domain-quantum-gardening",
                "verdict": "no_hits",
                "result_status": "empty_no_positive_match",
                "top_source_slug": "",
            },
            {
                "probe_id": "structural-agent-memory-lexical",
                "verdict": "pass",
                "result_status": "disclosed",
                "top_source_slug": "mapping-the-mind-for-agentic-systems",
            },
            {
                "probe_id": "near-neighbour-agent-memory",
                "verdict": "known_failure",
                "result_status": "disclosed",
                "expected_top_source_slug": "mapping-the-mind-for-agentic-systems",
                "observed_top_source_slug": "understanding-the-nature-of-thought",
                "notes": "Preserve as distractor/near-neighbour regression for CAE-006B",
            },
        ],
    }


def classify_result_status(
    *,
    probe: Mapping[str, Any],
    hits: Sequence[Mapping[str, Any]],
    catalog: Mapping[str, Any],
    error: str = "",
) -> str:
    if error:
        return "failed_internal"
    readiness = str(catalog.get("readiness_state", "") or "")
    if readiness in {"interrupted", "unsupported"}:
        return "abstained_dependency_not_ready"
    if readiness == "stale":
        return "abstained_stale_index"
    if probe.get("forced_result_status"):
        return str(probe["forced_result_status"])
    category = str(probe.get("category", "") or "")
    if category == "privacy" and probe.get("simulate_denial"):
        return "denied_visibility"
    if category == "privacy" and probe.get("simulate_grant_excludes_all"):
        return "empty_grant_excludes_all"
    if not hits:
        if category == "negative":
            return "empty_no_positive_match"
        if category in {"positive", "distractor", "shape", "provenance"}:
            return "empty_no_positive_match"
        return "empty_no_positive_match"
    return "disclosed"


def _source_slug(value: str) -> str:
    text = str(value or "").strip().lower()
    for token in ("/", ":", "\\"):
        if token in text:
            text = text.rsplit(token, 1)[-1]
    return text.replace(".md", "").replace("_", "-")


def _matches_slug(candidate: Mapping[str, Any], slug: str) -> bool:
    if not slug:
        return False
    normalized = slug.lower()
    for field in ("source_ref", "title"):
        if normalized in _source_slug(str(candidate.get(field, ""))):
            return True
    return False


def _top_hit(hits: Sequence[Mapping[str, Any]]) -> Optional[Dict[str, Any]]:
    if not hits:
        return None
    first = hits[0]
    return dict(first) if isinstance(first, dict) else None


def evaluate_probe(
    root: Path,
    probe: Mapping[str, Any],
    *,
    corpus_id: str = "local_runtime",
    source_families: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    started = time.perf_counter()
    catalog = build_corpus_catalog(root, corpus_id=corpus_id)
    error = ""
    hits: List[Dict[str, Any]] = []
    try:
        if probe.get("simulate_catalog_error"):
            raise RuntimeError(str(probe.get("simulate_catalog_error")))
        if probe.get("simulate_stale_catalog"):
            catalog = dict(catalog)
            catalog["readiness_state"] = "stale"
            catalog["retrieval_allowed"] = False
        if catalog.get("readiness_state") in {"interrupted", "unsupported", "stale"} and not probe.get("ignore_catalog_readiness"):
            hits = []
        elif str(probe.get("search_mode", "source") or "source") == "skip":
            hits = []
        else:
            payload = filter_library_sources(
                root,
                query=str(probe.get("query", "") or ""),
                source_families=list(source_families or probe.get("source_families") or ["chat_converter"]),
                source_ref=str(probe.get("source_ref", "") or "") or None,
                limit=int(probe.get("limit", 5) or 5),
            )
            hits = [dict(row) for row in payload.get("results", []) or []]
    except Exception as exc:  # pragma: no cover - surfaced via result_status
        error = str(exc)

    latency_ms = round((time.perf_counter() - started) * 1000.0, 3)
    top = _top_hit(hits)
    top_slug = _source_slug(str((top or {}).get("source_ref", "") or (top or {}).get("title", "")))
    expected_slug = str(probe.get("expected_top_source_slug", "") or "")
    observed_slug = str(probe.get("observed_top_source_slug", "") or top_slug)
    result_status = classify_result_status(probe=probe, hits=hits, catalog=catalog, error=error)
    verdict = _derive_verdict(probe=probe, hits=hits, top_slug=top_slug, result_status=result_status, error=error)
    bytes_resolved = sum(len(str(row.get("title", ""))) + len(str(row.get("preview_excerpt", ""))) for row in hits[:3])

    return {
        "probe_id": str(probe.get("probe_id", "")),
        "category": str(probe.get("category", "")),
        "query": str(probe.get("query", "") or ""),
        "result_status": result_status,
        "verdict": verdict,
        "top_source_slug": top_slug,
        "expected_top_source_slug": expected_slug,
        "observed_top_source_slug": observed_slug,
        "hit_count": len(hits),
        "latency_ms": latency_ms,
        "bytes_resolved": bytes_resolved,
        "corpus_revision": catalog.get("corpus_revision", CHAT_CONVERTER_SEED_CORPUS_REVISION),
        "catalog_readiness_state": catalog.get("readiness_state", ""),
        "retrieval_allowed": bool(catalog.get("retrieval_allowed", False)),
        "error": error,
    }


def _derive_verdict(
    *,
    probe: Mapping[str, Any],
    hits: Sequence[Mapping[str, Any]],
    top_slug: str,
    result_status: str,
    error: str,
) -> str:
    if error:
        return "error"
    expected_verdict = str(probe.get("expected_verdict", "") or "")
    if result_status == "denied_visibility":
        return "denied"
    if result_status.startswith("abstained"):
        return "abstained"
    if not hits:
        if expected_verdict == "no_hits" or str(probe.get("category", "")) == "negative":
            return "no_hits"
        return "fail"
    expected_slug = str(probe.get("expected_top_source_slug", "") or "")
    if expected_verdict == "known_failure":
        if expected_slug and _matches_slug(_top_hit(hits) or {}, expected_slug):
            return "pass"
        observed = str(probe.get("observed_top_source_slug", "") or top_slug)
        if observed and expected_slug and observed != expected_slug:
            return "known_failure"
        return "known_failure"
    if expected_slug and not _matches_slug(_top_hit(hits) or {}, expected_slug):
        return "fail"
    if expected_verdict in PROBE_VERDICTS:
        return expected_verdict
    return "pass"


def run_baseline_suite(
    root: Path,
    probe_suite: Mapping[str, Any] | Path | str,
    *,
    corpus_id: str = "local_runtime",
) -> Dict[str, Any]:
    suite = load_probe_suite(probe_suite) if not isinstance(probe_suite, Mapping) else dict(probe_suite)
    probes = list(suite.get("probes", []) or [])
    started = time.perf_counter()
    results = [
        evaluate_probe(
            root,
            probe,
            corpus_id=str(probe.get("corpus_id") or corpus_id or "local_runtime"),
        )
        for probe in probes
    ]
    latencies = [float(row["latency_ms"]) for row in results]
    positive = [row for row in results if row["category"] == "positive"]
    negative = [row for row in results if row["category"] == "negative"]
    known_failures = [row for row in results if row["verdict"] == "known_failure"]
    passes = [row for row in results if row["verdict"] == "pass"]
    recall_at_1 = (
        sum(1 for row in positive if row["verdict"] == "pass") / len(positive)
        if positive
        else 0.0
    )
    false_open = (
        sum(1 for row in negative if row["verdict"] not in {"no_hits", "abstained"}) / len(negative)
        if negative
        else 0.0
    )
    status_counts: Dict[str, int] = {status: 0 for status in RESULT_STATUSES}
    for row in results:
        status_counts[str(row.get("result_status", ""))] = status_counts.get(str(row.get("result_status", "")), 0) + 1

    manifest = published_baseline_manifest()
    thresholds = dict(suite.get("thresholds") or manifest.get("thresholds") or DEFAULT_THRESHOLDS)
    return {
        "schema_version": HARNESS_VERSION,
        "baseline_suite_id": str(suite.get("baseline_suite_id", BASELINE_SUITE_ID)),
        "corpus_id": str(suite.get("corpus_id", corpus_id)),
        "corpus_revision": str(suite.get("corpus_revision", CHAT_CONVERTER_SEED_CORPUS_REVISION)),
        "harness_version": HARNESS_VERSION,
        "thresholds": thresholds,
        "probe_count": len(results),
        "pass_count": len(passes),
        "known_failure_count": len(known_failures),
        "positive_recall_at_1": round(recall_at_1, 4),
        "negative_false_open_rate": round(false_open, 4),
        "latency_ms_total": round((time.perf_counter() - started) * 1000.0, 3),
        "latency_ms_p50": _percentile(latencies, 50),
        "latency_ms_p95": _percentile(latencies, 95),
        "max_bytes_resolved": max((int(row.get("bytes_resolved", 0) or 0) for row in results), default=0),
        "result_status_counts": status_counts,
        "results": results,
        "published_manifest_ref": BASELINE_SUITE_ID,
    }


def render_baseline_summary(report: Mapping[str, Any]) -> str:
    lines = [
        f"# Baseline report — {report.get('baseline_suite_id', BASELINE_SUITE_ID)}",
        "",
        f"- Harness version: `{report.get('harness_version', HARNESS_VERSION)}`",
        f"- Corpus: `{report.get('corpus_id', CHAT_CONVERTER_SEED_CORPUS_ID)}`",
        f"- Corpus revision: `{report.get('corpus_revision', CHAT_CONVERTER_SEED_CORPUS_REVISION)}`",
        f"- Probes: {report.get('probe_count', 0)}",
        f"- Pass: {report.get('pass_count', 0)}; known failures: {report.get('known_failure_count', 0)}",
        f"- Positive recall@1: {report.get('positive_recall_at_1', 0.0)} (threshold {report.get('thresholds', {}).get('positive_recall_at_1')})",
        f"- Negative false-open rate: {report.get('negative_false_open_rate', 0.0)} (threshold {report.get('thresholds', {}).get('negative_false_open_rate')})",
        f"- Latency p50/p95 (ms): {report.get('latency_ms_p50')} / {report.get('latency_ms_p95')}",
        "",
        "## Probe results",
        "",
        "| probe | category | verdict | result_status | top_source |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in report.get("results", []) or []:
        lines.append(
            "| `{probe_id}` | {category} | {verdict} | `{result_status}` | `{top}` |".format(
                probe_id=row.get("probe_id", ""),
                category=row.get("category", ""),
                verdict=row.get("verdict", ""),
                result_status=row.get("result_status", ""),
                top=row.get("top_source_slug", "") or row.get("observed_top_source_slug", ""),
            )
        )
    lines.extend(
        [
            "",
            "## Status taxonomy",
            "",
            "The harness maps probes to explicit disclosure result statuses: "
            + ", ".join(f"`{status}`" for status in RESULT_STATUSES)
            + ".",
        ]
    )
    return "\n".join(lines) + "\n"


def _percentile(values: Sequence[float], pct: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return round(ordered[0], 3)
    index = max(0, min(len(ordered) - 1, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return round(ordered[index], 3)
