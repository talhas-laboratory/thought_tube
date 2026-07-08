from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from .mtsf_extraction import assess_quarantine, validate_extraction_draft
from .mtsf_extraction_skill import resolve_deep_extraction_draft
from .mtsf_ingest import materialize_session_mtsf_ingest
from .mtsf_session import materialize_session_mtsf
from .mtsf_stencils import match_stencil_drafts_to_seed
from .storage import ensure_dir, read_json, session_dir, session_events_path, write_json

MODULE_ID = "kernel.mtsf.shape_eval"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "default_shape_utility_evals_dir",
    "run_shape_utility_evals",
)
__all__ = list(PUBLIC_API)


def default_shape_utility_evals_dir(root: Path) -> Path:
    return (
        root
        / "docs"
        / "frameworks"
        / "metaphysical-thought-space"
        / "evals"
        / "shape-utility"
    )


def _load_fixture(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_fragments(values: Sequence[str]) -> List[str]:
    return [str(value).lower() for value in values if value]


def _entity_names(draft: Dict[str, Any]) -> Set[str]:
    return {str(row.get("name", "")).lower() for row in draft.get("entities", []) if row.get("name")}


def _entity_ids(draft: Dict[str, Any]) -> Set[str]:
    return {str(row.get("proposed_id", "")) for row in draft.get("entities", []) if row.get("proposed_id")}


def _candidate_shape_ids(draft: Dict[str, Any]) -> Set[str]:
    return {
        str(row.get("proposed_id", ""))
        for row in draft.get("candidate_shapes", [])
        if row.get("proposed_id")
    }


def _conversation_text(events: Sequence[Dict[str, Any]]) -> str:
    return "\n".join(str(event.get("content", "")).strip() for event in events if event.get("content"))


def _seed_stencil_match_count(root: Path, draft: Dict[str, Any]) -> int:
    matches = match_stencil_drafts_to_seed(root, draft.get("stencil_drafts", []))
    return sum(1 for row in matches if float(row.get("structural_score", 0.0)) >= 1.0)


def _write_eval_session(
    root: Path,
    *,
    session_id: str,
    events: Sequence[Dict[str, Any]],
    manifest: Dict[str, Any],
) -> None:
    ensure_dir(session_dir(root, session_id))
    events_path = session_events_path(root, session_id)
    ensure_dir(events_path.parent)
    with events_path.open("w", encoding="utf-8") as handle:
        for index, event in enumerate(events):
            payload = {
                "event_id": f"eval-event-{index}",
                "session_id": session_id,
                "actor": event.get("actor", "user"),
                "kind": event.get("kind", "request"),
                "content": event.get("content", ""),
                "tags": [],
            }
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    write_json(
        session_dir(root, session_id) / "manifest.json",
        {
            "session_id": session_id,
            "title": manifest.get("title", session_id),
            "source_type": manifest.get("source_type", "text"),
            "domains": manifest.get("domains", []),
            "status": "eval",
        },
    )


def _extract_draft_for_fixture(
    root: Path,
    fixture: Dict[str, Any],
    *,
    llm_preference: str,
) -> Dict[str, Any]:
    input_payload = fixture["input"]
    session_id = str(input_payload["session_id"])
    events = list(input_payload.get("events", []))
    manifest = {
        "title": fixture.get("id", session_id),
        "source_type": input_payload.get("source_type", "text"),
        "domains": input_payload.get("domains", []),
    }
    result = resolve_deep_extraction_draft(
        root,
        session_id=session_id,
        events=events,
        manifest=manifest,
        raw_content=_conversation_text(events),
        llm_preference=llm_preference,
    )
    draft = result["draft"]
    report = validate_extraction_draft(root, draft)
    quarantine = assess_quarantine(draft, report)
    return {
        "draft": draft,
        "source": result.get("source"),
        "validation_ok": report.ok,
        "quarantine": quarantine.quarantine,
        "warnings": report.warnings,
        "stencil_matches": report.stencil_matches,
        "seed_stencil_matches": _seed_stencil_match_count(root, draft),
    }


def _check_extraction_expectations(
    payload: Dict[str, Any],
    expectations: Dict[str, Any],
) -> List[str]:
    failures: List[str] = []
    draft = payload["draft"]
    names = _entity_names(draft)
    ids = _entity_ids(draft)
    joined_names = " ".join(sorted(names))
    joined_ids = " ".join(sorted(ids))

    if expectations.get("validation_must_pass") and not payload["validation_ok"]:
        failures.append("validation_failed")

    entity_count = len(draft.get("entities", []))
    if entity_count < int(expectations.get("min_entities", 0)):
        failures.append(f"insufficient_entities:{entity_count}")
    if entity_count > int(expectations.get("max_entities", 10_000)):
        failures.append(f"too_many_entities:{entity_count}")

    for fragment in _normalize_fragments(expectations.get("required_entity_name_fragments", [])):
        if fragment not in joined_names:
            failures.append(f"missing_entity_fragment:{fragment}")

    for fragment in _normalize_fragments(expectations.get("forbidden_entity_name_fragments", [])):
        if fragment in joined_names or fragment in joined_ids:
            failures.append(f"forbidden_entity_fragment:{fragment}")

    relation_count = len(draft.get("relations", []))
    if relation_count < int(expectations.get("min_relations", 0)):
        failures.append(f"insufficient_relations:{relation_count}")

    candidate_shapes = draft.get("candidate_shapes", [])
    if len(candidate_shapes) < int(expectations.get("min_candidate_shapes", 0)):
        failures.append(f"insufficient_candidate_shapes:{len(candidate_shapes)}")
    if len(candidate_shapes) > int(expectations.get("max_candidate_shapes", 10_000)):
        failures.append(f"too_many_candidate_shapes:{len(candidate_shapes)}")

    stencil_drafts = draft.get("stencil_drafts", [])
    if len(stencil_drafts) > int(expectations.get("max_stencil_drafts", 10_000)):
        failures.append(f"too_many_stencil_drafts:{len(stencil_drafts)}")

    if expectations.get("require_relational_configuration"):
        if not any(str(row.get("relational_configuration", "")).strip() for row in candidate_shapes):
            failures.append("missing_relational_configuration")

    forbidden_shape_ids = set(expectations.get("forbidden_candidate_shape_ids", []))
    found_forbidden = sorted(_candidate_shape_ids(draft) & forbidden_shape_ids)
    if found_forbidden:
        failures.append(f"forbidden_candidate_shapes:{','.join(found_forbidden)}")

    max_seed_matches = expectations.get("max_stencil_seed_matches")
    if max_seed_matches is not None and payload["seed_stencil_matches"] > int(max_seed_matches):
        failures.append(
            f"too_many_seed_stencil_matches:{payload['seed_stencil_matches']}"
        )

    return failures


def _run_activation_fixture(
    root: Path,
    fixture: Dict[str, Any],
    *,
    llm_preference: str,
) -> Dict[str, Any]:
    input_payload = fixture["input"]
    session_id = str(input_payload["session_id"])
    events = list(input_payload.get("events", []))
    manifest = {
        "title": fixture.get("id", session_id),
        "source_type": input_payload.get("source_type", "live_session"),
        "domains": input_payload.get("domains", []),
    }
    _write_eval_session(root, session_id=session_id, events=events, manifest=manifest)
    mode = str(fixture.get("pipeline", {}).get("mtsf_mode", "deep"))
    materialize_session_mtsf_ingest(root, session_id, mode, llm_preference=llm_preference)
    activation_refs = materialize_session_mtsf(root, session_id)
    snapshot = read_json(Path(activation_refs["mtsf_activation_snapshot"]), default={})
    draft = read_json(session_dir(root, session_id) / "mtsf" / "extraction_draft.json", default={})
    return {
        "snapshot": snapshot,
        "draft": draft,
        "activation_results": snapshot.get("shape_activation_results", []),
    }


def _check_activation_expectations(payload: Dict[str, Any], expectations: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    draft = payload["draft"]
    if len(draft.get("entities", [])) < int(expectations.get("min_entities", 0)):
        failures.append(f"insufficient_entities:{len(draft.get('entities', []))}")

    results_by_entity = {
        str(row.get("entity_id", "")): row for row in payload["activation_results"]
    }
    for entity_id in expectations.get("required_activation_entities", []):
        if entity_id not in results_by_entity:
            failures.append(f"missing_activation_entity:{entity_id}")

    required_shapes = expectations.get("required_dominant_shapes", {})
    for entity_id, allowed in required_shapes.items():
        row = results_by_entity.get(entity_id)
        if not row:
            failures.append(f"missing_activation_entity:{entity_id}")
            continue
        dominant = str(row.get("dominant_shape_id", ""))
        if dominant not in set(allowed):
            failures.append(f"unexpected_dominant_shape:{entity_id}:{dominant}")

    matched_conditions = {
        condition
        for row in payload["activation_results"]
        for condition in row.get("matched_conditions", [])
    }
    if len(matched_conditions) < int(expectations.get("min_matched_conditions", 0)):
        failures.append(f"insufficient_matched_conditions:{len(matched_conditions)}")

    return failures


def _overlap_ratio(left: Set[str], right: Set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _run_pair_fixture(
    root: Path,
    fixture: Dict[str, Any],
    *,
    llm_preference: str,
) -> Dict[str, Any]:
    drafts: Dict[str, Dict[str, Any]] = {}
    for item in fixture.get("pair", []):
        mini_fixture = {
            "id": f"{fixture['id']}::{item['label']}",
            "input": {
                "session_id": item["session_id"],
                "source_type": "text",
                "domains": [],
                "events": item["events"],
            },
        }
        drafts[item["label"]] = _extract_draft_for_fixture(root, mini_fixture, llm_preference=llm_preference)

    labels = [item["label"] for item in fixture.get("pair", [])]
    left = drafts[labels[0]]["draft"]
    right = drafts[labels[1]]["draft"]
    return {
        "drafts": drafts,
        "entity_overlap_ratio": _overlap_ratio(_entity_names(left), _entity_names(right)),
        "candidate_shape_overlap_ratio": _overlap_ratio(_candidate_shape_ids(left), _candidate_shape_ids(right)),
    }


def _check_pair_expectations(payload: Dict[str, Any], expectations: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    if payload["entity_overlap_ratio"] > float(expectations.get("max_entity_overlap_ratio", 1.0)):
        failures.append(f"entity_overlap_too_high:{payload['entity_overlap_ratio']:.2f}")
    if payload["candidate_shape_overlap_ratio"] > float(
        expectations.get("max_candidate_shape_overlap_ratio", 1.0)
    ):
        failures.append(
            f"candidate_shape_overlap_too_high:{payload['candidate_shape_overlap_ratio']:.2f}"
        )
    return failures


def _utility_metrics(payload: Dict[str, Any], *, kind: str) -> Dict[str, Any]:
    if kind == "pair":
        return {
            "entity_overlap_ratio": payload["entity_overlap_ratio"],
            "candidate_shape_overlap_ratio": payload["candidate_shape_overlap_ratio"],
        }
    if kind == "activation":
        draft = payload["draft"]
        return {
            "entity_count": len(draft.get("entities", [])),
            "candidate_shape_count": len(draft.get("candidate_shapes", [])),
            "stencil_draft_count": len(draft.get("stencil_drafts", [])),
            "activation_entity_count": len(payload["activation_results"]),
            "matched_condition_count": len(
                {
                    condition
                    for row in payload["activation_results"]
                    for condition in row.get("matched_conditions", [])
                }
            ),
        }
    draft = payload["draft"]
    return {
        "entity_count": len(draft.get("entities", [])),
        "relation_count": len(draft.get("relations", [])),
        "candidate_shape_count": len(draft.get("candidate_shapes", [])),
        "stencil_draft_count": len(draft.get("stencil_drafts", [])),
        "seed_stencil_matches": payload.get("seed_stencil_matches", 0),
        "extraction_source": payload.get("source"),
    }


def run_shape_utility_evals(
    root: Path,
    *,
    llm_preference: str = "auto",
) -> Dict[str, Any]:
    evals_dir = default_shape_utility_evals_dir(root)
    fixtures = sorted(evals_dir.glob("eval-utility-*.json"))
    runs: List[Dict[str, Any]] = []
    passed = 0

    for fixture_path in fixtures:
        fixture = _load_fixture(fixture_path)
        eval_id = str(fixture.get("id", fixture_path.stem))
        tier = str(fixture.get("tier", ""))
        expectations = fixture.get("expectations", {})
        pipeline = fixture.get("pipeline", {})
        pref = str(pipeline.get("llm_preference", llm_preference))

        if fixture.get("type") == "pair_discrimination":
            payload = _run_pair_fixture(root, fixture, llm_preference=pref)
            failures = _check_pair_expectations(payload, expectations)
            kind = "pair"
        elif tier == "T2":
            payload = _run_activation_fixture(root, fixture, llm_preference=pref)
            failures = _check_activation_expectations(payload, expectations)
            kind = "activation"
        else:
            payload = _extract_draft_for_fixture(root, fixture, llm_preference=pref)
            failures = _check_extraction_expectations(payload, expectations)
            kind = "extraction"

        ok = not failures
        if ok:
            passed += 1
        runs.append(
            {
                "id": eval_id,
                "tier": tier,
                "kind": kind,
                "ok": ok,
                "failures": failures,
                "metrics": _utility_metrics(payload, kind=kind),
                "description": fixture.get("description", ""),
            }
        )

    return {
        "suite": "shape-utility",
        "llm_preference": llm_preference,
        "total": len(fixtures),
        "passed": passed,
        "failed": len(fixtures) - passed,
        "pass_rate": round(passed / len(fixtures), 3) if fixtures else 0.0,
        "runs": runs,
        "interpretation": {
            "extraction_passes": sum(1 for row in runs if row["kind"] == "extraction" and row["ok"]),
            "activation_passes": sum(1 for row in runs if row["kind"] == "activation" and row["ok"]),
            "pair_passes": sum(1 for row in runs if row["kind"] == "pair" and row["ok"]),
            "negative_control_passes": sum(
                1 for row in runs if row["id"].startswith("eval-utility-negative") and row["ok"]
            ),
        },
    }
