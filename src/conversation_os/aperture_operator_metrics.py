"""Cross-surface operator metrics derived from receipts and baselines (CAE-012)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence

from .aperture_baseline_harness import BASELINE_SUITE_ID, published_baseline_manifest
from .aperture_service_baseline_harness import (
    SERVICE_BASELINE_SUITE_ID,
    published_service_baseline_manifest,
)
from .disclosure_receipts import disclosure_receipts_path
from .library_tracker import CHAT_CONVERTER_SEED_CORPUS_ID, CHAT_CONVERTER_SEED_CORPUS_REVISION
from .storage import read_json, read_jsonl, utc_now


MODULE_ID = "kernel.disclosure.aperture_operator_metrics"
OPERATOR_VIEW_VERSION = "1.0"
MINIMUM_AGGREGATE_COUNT = 3
OPERATOR_SURFACES = ("bridge", "holodeck", "feed", "task_pack")

PUBLISHED_BASELINE_FILES = (
    ("chat_converter_seed_v1", "docs/workspaces/cognitive-aperture-exceptional/derived/baselines/chat_converter_seed_v1.json"),
    (
        "chat_converter_seed_v1_service",
        "docs/workspaces/cognitive-aperture-exceptional/derived/baselines/chat_converter_seed_v1_service.json",
    ),
    (
        "chat_converter_seed_v2_shape_certification",
        "docs/workspaces/cognitive-aperture-exceptional/derived/baselines/chat_converter_seed_v2_shape_certification.json",
    ),
    (
        "chat_converter_seed_v2_feed_certification",
        "docs/workspaces/cognitive-aperture-exceptional/derived/baselines/chat_converter_seed_v2_feed_certification.json",
    ),
    (
        "chat_converter_seed_v2_task_pack_certification",
        "docs/workspaces/cognitive-aperture-exceptional/derived/baselines/chat_converter_seed_v2_task_pack_certification.json",
    ),
    (
        "chat_converter_seed_v2_bounded_view_certification",
        "docs/workspaces/cognitive-aperture-exceptional/derived/baselines/chat_converter_seed_v2_bounded_view_certification.json",
    ),
)

PUBLIC_API = (
    "MODULE_ID",
    "OPERATOR_VIEW_VERSION",
    "MINIMUM_AGGREGATE_COUNT",
    "OPERATOR_SURFACES",
    "load_operator_metrics_config",
    "operator_metrics_enabled",
    "aggregate_receipt_metrics",
    "certify_baseline_snapshot",
    "load_published_baseline_snapshots",
    "load_surface_rollout_modes",
    "build_lifecycle_observability_view",
    "compare_surfaces_by_revision",
    "build_operator_view",
    "render_operator_view_summary",
    "inspect_operator_view",
)
__all__ = list(PUBLIC_API)


def _runtime_config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime.json"


def load_operator_metrics_config(root: Path) -> Dict[str, Any]:
    runtime = read_json(_runtime_config_path(root), default={}) or {}
    disclosure = runtime.get("disclosure", {}) or {}
    operator = disclosure.get("operator_metrics", {}) or {}
    return {
        "operator_metrics_v1": bool(
            operator.get(
                "operator_metrics_v1",
                disclosure.get("operator_metrics_v1", False),
            )
        ),
        "receipt_limit": max(1, int(operator.get("receipt_limit", 500) or 500)),
    }


def operator_metrics_enabled(root: Path) -> bool:
    return bool(load_operator_metrics_config(root)["operator_metrics_v1"])


def certify_baseline_snapshot(snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    row = dict(snapshot)
    summary = dict(row.get("summary", {}) or {})
    threshold_check = dict(row.get("threshold_check", {}) or {})
    certified = bool(summary.get("service_certified")) or bool(threshold_check.get("passed"))
    row["certification_status"] = "certified" if certified else "uncertified"
    row["eligible_for_release_claims"] = certified
    if not certified:
        row["release_claim_exclusion_reason"] = "baseline_not_certified"
    return row


def load_surface_rollout_modes(root: Path) -> Dict[str, str]:
    from .disclosure_rollout import resolve_surface_rollout_mode

    return {surface: resolve_surface_rollout_mode(root, surface) for surface in OPERATOR_SURFACES}


def _privacy_safe_surface_counts(
    counts: Mapping[str, int],
    *,
    minimum: int = MINIMUM_AGGREGATE_COUNT,
) -> Dict[str, Any]:
    safe: Dict[str, Any] = {}
    for surface, count in sorted(counts.items()):
        value = int(count or 0)
        if value < minimum:
            safe[surface] = {
                "suppressed": True,
                "reason": "below_minimum_aggregate_count",
                "minimum_aggregate_count": minimum,
            }
        else:
            safe[surface] = value
    return safe


def _revision_certification_status(baseline_rows: Sequence[Mapping[str, Any]]) -> str:
    if not baseline_rows:
        return "uncertified"
    statuses = {str(row.get("certification_status", "uncertified") or "uncertified") for row in baseline_rows}
    if statuses == {"certified"}:
        return "certified"
    if "certified" in statuses:
        return "partial"
    return "uncertified"


def _percentile(values: Sequence[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    index = max(0, min(len(ordered) - 1, int(round((percentile / 100.0) * (len(ordered) - 1)))))
    return round(ordered[index], 3)


def _increment(bucket: MutableMapping[str, int], key: str) -> None:
    bucket[key] = int(bucket.get(key, 0) or 0) + 1


def _load_receipt_rows(root: Path, *, surface: str = "", limit: int = 500) -> List[Dict[str, Any]]:
    rows = read_jsonl(disclosure_receipts_path(root))
    filtered: List[Dict[str, Any]] = []
    for row in reversed(rows):
        if surface and str(row.get("surface", "") or "") != surface:
            continue
        filtered.append(dict(row))
        if len(filtered) >= max(1, int(limit)):
            break
    return list(reversed(filtered))


def aggregate_receipt_metrics(receipts: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    rows = [dict(row) for row in receipts]
    by_surface: Dict[str, int] = {}
    by_result_status: Dict[str, int] = {}
    by_envelope: Dict[str, int] = {}
    omission_reason_counts: Dict[str, int] = {}
    by_revision: Dict[str, Dict[str, Any]] = {}
    latency_samples: List[float] = []
    included_block_counts: List[int] = []
    omitted_block_counts: List[int] = []
    admitted_candidate_counts: List[int] = []
    budget_drop_rows = 0

    for row in rows:
        surface = str(row.get("surface", "unknown") or "unknown")
        result_status = str(row.get("result_status", "unknown") or "unknown")
        effective = dict(row.get("effective_grant", {}) or {})
        envelope = str(effective.get("envelope", "unknown") or "unknown")
        revision = str(row.get("corpus_revision", "") or "unknown")
        _increment(by_surface, surface)
        _increment(by_result_status, result_status)
        _increment(by_envelope, envelope)

        revision_row = by_revision.setdefault(
            revision,
            {
                "receipt_count": 0,
                "by_surface": {},
                "by_result_status": {},
                "latency_ms_p50": 0.0,
                "latency_ms_p95": 0.0,
            },
        )
        revision_row["receipt_count"] = int(revision_row["receipt_count"]) + 1
        _increment(revision_row["by_surface"], surface)
        _increment(revision_row["by_result_status"], result_status)

        for omission in list(row.get("omission_reasons", []) or []):
            code = str(omission.get("code", "") or omission.get("reason", "") or "unknown")
            _increment(omission_reason_counts, code)

        metrics = dict(row.get("metrics", {}) or {})
        for key in ("latency_ms", "latency_ms_p50", "latency_ms_p95"):
            if key in metrics:
                try:
                    latency_samples.append(float(metrics[key]))
                except (TypeError, ValueError):
                    continue
        included_block_counts.append(int(metrics.get("included_block_count", len(row.get("included_block_ids", []) or [])) or 0))
        omitted_block_counts.append(int(metrics.get("omitted_block_count", len(row.get("omitted_block_ids", []) or [])) or 0))
        admitted_candidate_counts.append(
            sum(
                1
                for decision in list(row.get("candidate_decisions", []) or [])
                if str(decision.get("decision", "")) == "admitted"
            )
        )
        if row.get("budget_ledger") or any(
            str(item.get("code", "")) == "budget_insufficient"
            for item in list(row.get("omission_reasons", []) or [])
        ):
            budget_drop_rows += 1

    revision_latency: Dict[str, List[float]] = {}
    for row in rows:
        revision = str(row.get("corpus_revision", "") or "unknown")
        metrics = dict(row.get("metrics", {}) or {})
        for key in ("latency_ms", "latency_ms_p50", "latency_ms_p95"):
            if key in metrics:
                try:
                    revision_latency.setdefault(revision, []).append(float(metrics[key]))
                except (TypeError, ValueError):
                    continue
    for revision, samples in revision_latency.items():
        by_revision[revision]["latency_ms_p50"] = _percentile(samples, 50)
        by_revision[revision]["latency_ms_p95"] = _percentile(samples, 95)

    empty_or_abstained = sum(
        count
        for status, count in by_result_status.items()
        if str(status).startswith("empty_") or str(status).startswith("abstained_") or str(status) == "denied_visibility"
    )
    disclosed = int(by_result_status.get("disclosed", 0) or 0)

    return {
        "receipt_count": len(rows),
        "by_surface": dict(sorted(by_surface.items())),
        "by_result_status": dict(sorted(by_result_status.items())),
        "by_envelope": dict(sorted(by_envelope.items())),
        "omission_reason_counts": dict(sorted(omission_reason_counts.items())),
        "by_corpus_revision": by_revision,
        "latency_ms_p50": _percentile(latency_samples, 50),
        "latency_ms_p95": _percentile(latency_samples, 95),
        "avg_included_block_count": round(sum(included_block_counts) / len(included_block_counts), 3)
        if included_block_counts
        else 0.0,
        "avg_omitted_block_count": round(sum(omitted_block_counts) / len(omitted_block_counts), 3)
        if omitted_block_counts
        else 0.0,
        "avg_admitted_candidate_count": round(sum(admitted_candidate_counts) / len(admitted_candidate_counts), 3)
        if admitted_candidate_counts
        else 0.0,
        "budget_pressure_rows": budget_drop_rows,
        "disclosed_rate": round(disclosed / len(rows), 4) if rows else 0.0,
        "empty_or_abstained_rate": round(empty_or_abstained / len(rows), 4) if rows else 0.0,
        "privacy_mode": "aggregated_counts_only",
        "sensitive_fields_excluded": [
            "included_block_ids",
            "effective_grant.effective_refs",
            "omission_reasons.source_ref",
            "content_hashes",
        ],
    }


def load_published_baseline_snapshots(root: Path) -> List[Dict[str, Any]]:
    snapshots: List[Dict[str, Any]] = []
    fallbacks = {
        BASELINE_SUITE_ID: published_baseline_manifest(),
        SERVICE_BASELINE_SUITE_ID: published_service_baseline_manifest(),
    }
    for suite_id, relative_path in PUBLISHED_BASELINE_FILES:
        path = root / relative_path
        if path.exists():
            payload = json.loads(path.read_text(encoding="utf-8"))
        else:
            payload = dict(fallbacks.get(suite_id, {}))
        snapshot = certify_baseline_snapshot(
            {
                "baseline_suite_id": str(payload.get("baseline_suite_id", suite_id)),
                "corpus_id": str(payload.get("corpus_id", CHAT_CONVERTER_SEED_CORPUS_ID)),
                "corpus_revision": str(payload.get("corpus_revision", CHAT_CONVERTER_SEED_CORPUS_REVISION)),
                "harness_version": str(payload.get("harness_version", OPERATOR_VIEW_VERSION)),
                "thresholds": dict(payload.get("thresholds", {}) or {}),
                "summary": dict(payload.get("summary", {}) or {}),
                "threshold_check": dict(payload.get("threshold_check", {}) or {}),
                "observed_results": list(payload.get("observed_results", []) or []),
                "source_path": str(path) if path.exists() else "",
            }
        )
        snapshots.append(snapshot)
    return snapshots


def compare_surfaces_by_revision(
    receipt_metrics: Mapping[str, Any],
    baseline_snapshots: Sequence[Mapping[str, Any]],
    *,
    rollout_modes: Mapping[str, str] | None = None,
    minimum_aggregate_count: int = MINIMUM_AGGREGATE_COUNT,
) -> Dict[str, Any]:
    revisions = sorted(set(receipt_metrics.get("by_corpus_revision", {}) or {}) | {row.get("corpus_revision", "") for row in baseline_snapshots})
    comparisons: List[Dict[str, Any]] = []
    rollout_modes = dict(rollout_modes or {})
    for revision in revisions:
        if not revision:
            continue
        revision_receipts = dict((receipt_metrics.get("by_corpus_revision", {}) or {}).get(revision, {}) or {})
        baseline_rows = [row for row in baseline_snapshots if str(row.get("corpus_revision", "")) == revision]
        surface_counts = dict(revision_receipts.get("by_surface", {}) or {})
        privacy_safe_counts = _privacy_safe_surface_counts(
            surface_counts,
            minimum=minimum_aggregate_count,
        )
        revision_status = _revision_certification_status(baseline_rows)
        eligible_for_release_claims = revision_status == "certified"
        comparison_row: Dict[str, Any] = {
            "corpus_revision": revision,
            "receipt_count": int(revision_receipts.get("receipt_count", 0) or 0),
            "certification_status": revision_status,
            "eligible_for_release_claims": eligible_for_release_claims,
            "surfaces_observed": sorted(surface_counts.keys()),
            "surface_receipt_counts": privacy_safe_counts,
            "result_status_counts": dict(revision_receipts.get("by_result_status", {}) or {}),
            "latency_ms_p50": revision_receipts.get("latency_ms_p50", 0.0),
            "latency_ms_p95": revision_receipts.get("latency_ms_p95", 0.0),
            "rollout_modes": dict(rollout_modes),
            "baseline_suites": [str(row.get("baseline_suite_id", "")) for row in baseline_rows],
            "baseline_summaries": [
                {
                    "baseline_suite_id": row.get("baseline_suite_id", ""),
                    "certification_status": row.get("certification_status", "uncertified"),
                    "eligible_for_release_claims": bool(row.get("eligible_for_release_claims", False)),
                    "pass_count": dict(row.get("summary", {}) or {}).get("pass_count"),
                    "known_failure_count": dict(row.get("summary", {}) or {}).get("known_failure_count"),
                    "service_certified": dict(row.get("summary", {}) or {}).get("service_certified"),
                    "retrieval_certified": dict(row.get("summary", {}) or {}).get("retrieval_certified"),
                    "threshold_check_passed": dict(row.get("threshold_check", {}) or {}).get("passed"),
                }
                for row in baseline_rows
            ],
        }
        if not eligible_for_release_claims:
            comparison_row["uncertified_label"] = "excluded_from_release_claims"
        comparisons.append(comparison_row)
    cross_surface_surfaces = sorted(
        {
            surface
            for row in comparisons
            for surface, count in (row.get("surface_receipt_counts", {}) or {}).items()
            if not (isinstance(count, dict) and count.get("suppressed"))
        }
    )
    return {
        "revision_count": len(comparisons),
        "minimum_aggregate_count": minimum_aggregate_count,
        "comparisons": comparisons,
        "cross_surface_surfaces": cross_surface_surfaces,
        "release_claim_eligible_revisions": [
            row["corpus_revision"]
            for row in comparisons
            if bool(row.get("eligible_for_release_claims"))
        ],
        "release_claim_excluded_revisions": [
            row["corpus_revision"]
            for row in comparisons
            if not bool(row.get("eligible_for_release_claims"))
        ],
    }


def build_lifecycle_observability_view(
    lifecycle_events: Iterable[Mapping[str, Any]],
    *,
    minimum_aggregate_count: int = MINIMUM_AGGREGATE_COUNT,
    stuck_after_seconds: int = 900,
) -> Dict[str, Any]:
    events = [dict(row) for row in lifecycle_events]
    by_family: Dict[str, int] = {}
    by_status: Dict[str, int] = {}
    repair_paths: Dict[str, int] = {}
    drift_signals: Dict[str, int] = {}
    expected_abstentions = 0
    infrastructure_failures = 0
    stale_index_count = 0
    stuck_count = 0
    for row in events:
        family = str(row.get("event_family") or row.get("family") or "unknown")
        status = str(row.get("status") or row.get("result_status") or "unknown")
        _increment(by_family, family)
        _increment(by_status, status)
        if status.startswith("abstained") or status.startswith("empty_") or bool(row.get("expected_abstention")):
            expected_abstentions += 1
        if status in {"infrastructure_failure", "failed", "error"} or bool(row.get("infrastructure_failure")):
            infrastructure_failures += 1
        if status == "stale_index" or bool(row.get("stale_index")):
            stale_index_count += 1
        try:
            age_seconds = int(row.get("age_seconds", 0) or 0)
        except (TypeError, ValueError):
            age_seconds = 0
        if status in {"queued", "claimed", "retryable"} and age_seconds > stuck_after_seconds:
            stuck_count += 1
        repair_code = str(row.get("repair_path") or row.get("repair_code") or "").strip()
        if repair_code:
            _increment(repair_paths, repair_code)
        drift = row.get("drift")
        if isinstance(drift, Mapping):
            for key, value in drift.items():
                if value:
                    _increment(drift_signals, str(key))
        elif row.get("drift_signal"):
            _increment(drift_signals, str(row.get("drift_signal")))

    alerts = {
        "expected_abstention": {
            "count": expected_abstentions,
            "severity": "info" if expected_abstentions else "none",
        },
        "infrastructure_failure": {
            "count": infrastructure_failures,
            "severity": "critical" if infrastructure_failures else "none",
        },
        "stale_index": {
            "count": stale_index_count,
            "severity": "warning" if stale_index_count else "none",
        },
        "stuck_job": {
            "count": stuck_count,
            "severity": "warning" if stuck_count else "none",
        },
    }
    return {
        "schema_version": OPERATOR_VIEW_VERSION,
        "read_only": True,
        "mutation_paths": [],
        "privacy_mode": "aggregate_codes_only",
        "sensitive_fields_excluded": [
            "source_ref",
            "source_text",
            "evidence_text",
            "included_block_ids",
            "effective_grant",
            "principal_id",
        ],
        "event_count": len(events),
        "minimum_aggregate_count": minimum_aggregate_count,
        "by_event_family": _privacy_safe_surface_counts(by_family, minimum=minimum_aggregate_count),
        "by_status": dict(sorted(by_status.items())),
        "alerts": alerts,
        "repair_paths": dict(sorted(repair_paths.items())),
        "drift_signals": dict(sorted(drift_signals.items())),
        "control_surface": {
            "pause": "authorized_operator_control",
            "drain": "authorized_operator_control",
            "replay": "authorized_repair_control",
            "reindex": "authorized_repair_control",
            "rollback": "authorized_release_control",
        },
    }


def build_operator_view(
    root: Path,
    *,
    surface: str = "",
    corpus_revision: str = "",
    receipt_limit: int | None = None,
) -> Dict[str, Any]:
    config = load_operator_metrics_config(root)
    limit = int(receipt_limit or config["receipt_limit"])
    receipts = _load_receipt_rows(root, surface=surface, limit=limit)
    if corpus_revision:
        receipts = [row for row in receipts if str(row.get("corpus_revision", "")) == corpus_revision]
    receipt_metrics = aggregate_receipt_metrics(receipts)
    baseline_snapshots = load_published_baseline_snapshots(root)
    if corpus_revision:
        baseline_snapshots = [row for row in baseline_snapshots if str(row.get("corpus_revision", "")) == corpus_revision]
    rollout_modes = load_surface_rollout_modes(root)
    cross_surface_comparison = compare_surfaces_by_revision(
        receipt_metrics,
        baseline_snapshots,
        rollout_modes=rollout_modes,
    )
    certified_baselines = [row for row in baseline_snapshots if row.get("certification_status") == "certified"]
    return {
        "schema_version": OPERATOR_VIEW_VERSION,
        "generated_at": utc_now(),
        "read_only": True,
        "mutation_paths": [],
        "corpus_id": CHAT_CONVERTER_SEED_CORPUS_ID,
        "corpus_revision_filter": corpus_revision or None,
        "surface_filter": surface or None,
        "minimum_aggregate_count": MINIMUM_AGGREGATE_COUNT,
        "rollout_modes": rollout_modes,
        "receipt_metrics": receipt_metrics,
        "baseline_snapshots": baseline_snapshots,
        "certified_baseline_count": len(certified_baselines),
        "uncertified_baseline_count": len(baseline_snapshots) - len(certified_baselines),
        "cross_surface_comparison": cross_surface_comparison,
        "release_claims": {
            "eligible_revisions": list(cross_surface_comparison.get("release_claim_eligible_revisions", []) or []),
            "excluded_revisions": list(cross_surface_comparison.get("release_claim_excluded_revisions", []) or []),
            "certified_baseline_suite_ids": [
                str(row.get("baseline_suite_id", ""))
                for row in certified_baselines
                if str(row.get("baseline_suite_id", ""))
            ],
        },
    }


def render_operator_view_summary(view: Mapping[str, Any]) -> str:
    metrics = dict(view.get("receipt_metrics", {}) or {})
    lines = [
        "# Aperture operator view",
        "",
        f"- Generated at: `{view.get('generated_at', '')}`",
        f"- Read only: `{view.get('read_only', True)}`",
        f"- Receipt count: {metrics.get('receipt_count', 0)}",
        f"- Disclosed rate: {metrics.get('disclosed_rate', 0.0)}",
        f"- Empty/abstained rate: {metrics.get('empty_or_abstained_rate', 0.0)}",
        f"- Latency p50/p95 (ms): {metrics.get('latency_ms_p50')} / {metrics.get('latency_ms_p95')}",
        "",
        "## Surfaces",
        "",
    ]
    for surface, count in sorted((metrics.get("by_surface", {}) or {}).items()):
        lines.append(f"- `{surface}`: {count}")
    lines.extend(["", "## Result statuses", ""])
    for status, count in sorted((metrics.get("by_result_status", {}) or {}).items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(["", "## Baselines", ""])
    for row in view.get("baseline_snapshots", []) or []:
        summary = dict(row.get("summary", {}) or {})
        status = str(row.get("certification_status", "uncertified") or "uncertified")
        lines.append(
            f"- `{row.get('baseline_suite_id', '')}` revision `{row.get('corpus_revision', '')}` "
            f"[{status}] (pass {summary.get('pass_count', 0)}, known failures {summary.get('known_failure_count', 0)})"
        )
    rollout_modes = dict(view.get("rollout_modes", {}) or {})
    if rollout_modes:
        lines.extend(["", "## Rollout modes", ""])
        for surface, mode in sorted(rollout_modes.items()):
            lines.append(f"- `{surface}`: `{mode}`")
    return "\n".join(lines) + "\n"


def inspect_operator_view(
    root: Path,
    *,
    surface: str = "",
    corpus_revision: str = "",
    receipt_limit: int | None = None,
) -> Dict[str, Any]:
    if not operator_metrics_enabled(root):
        return {
            "enabled": False,
            "read_only": True,
            "reason": "operator_metrics_v1_disabled",
            "rollback": "Set disclosure.operator_metrics.operator_metrics_v1 to true in runtime.json",
        }
    view = build_operator_view(
        root,
        surface=surface,
        corpus_revision=corpus_revision,
        receipt_limit=receipt_limit,
    )
    return {
        "enabled": True,
        "read_only": True,
        "view": view,
        "summary_markdown": render_operator_view_summary(view),
    }
