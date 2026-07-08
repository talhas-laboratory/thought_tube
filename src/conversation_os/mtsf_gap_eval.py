from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from .mtsf_graph import load_global_content_graph, rebuild_global_content_graph
from .mtsf_ingest import materialize_session_mtsf_ingest
from .mtsf_projector import MERGE_SCORE_THRESHOLD
from .mtsf_session import materialize_session_mtsf
from .mtsf_shape_eval import (
    _check_extraction_expectations,
    _check_pair_expectations,
    _conversation_text,
    _entity_names,
    _extract_draft_for_fixture,
    _run_pair_fixture,
    _write_eval_session,
    run_shape_utility_evals,
)
from .mtsf_stencils import match_stencil_drafts_to_seed
from .storage import read_json, session_dir

MODULE_ID = "kernel.mtsf.gap_eval"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "GAP_PLAN_PATH",
    "default_gap_closure_evals_dir",
    "run_gap_closure_evals",
)
__all__ = list(PUBLIC_API)

GAP_PLAN_PATH = "docs/frameworks/metaphysical-thought-space/GAP_PLAN.md"


def default_gap_closure_evals_dir(root: Path) -> Path:
    return (
        root
        / "docs"
        / "frameworks"
        / "metaphysical-thought-space"
        / "evals"
        / "gap-closure"
    )


def _load_fixture(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _ingest_session(
    root: Path,
    *,
    session_id: str,
    events: Sequence[Dict[str, Any]],
    mtsf_mode: str,
    llm_preference: str,
    domains: Optional[Sequence[str]] = None,
    source_type: str = "imported_transcript",
) -> Dict[str, Any]:
    manifest = {
        "title": session_id,
        "source_type": source_type,
        "domains": list(domains or ["research"]),
    }
    _write_eval_session(root, session_id=session_id, events=events, manifest=manifest)
    return materialize_session_mtsf_ingest(root, session_id, mtsf_mode, llm_preference=llm_preference)


def _candidate_shape_ids_from_draft(draft: Dict[str, Any]) -> Set[str]:
    return {
        str(row.get("proposed_id", ""))
        for row in draft.get("candidate_shapes", [])
        if row.get("proposed_id")
    }


def _check_artifact_field(root: Path, check: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    session_id = str(check["session_id"])
    _ingest_session(
        root,
        session_id=session_id,
        events=check.get("events", []),
        mtsf_mode=str(check.get("mtsf_mode", "deep")),
        llm_preference=str(check.get("llm_preference", "auto")),
    )
    artifact_path = session_dir(root, session_id) / str(check["artifact_relpath"])
    if not artifact_path.exists():
        failures.append(f"missing_artifact:{artifact_path}")
        return failures

    payload = read_json(artifact_path, default={})
    rows = payload.get("entities", payload.get("vectors", []))
    if isinstance(payload, list):
        rows = payload
    if len(rows) < int(check.get("min_vectors", 1)):
        failures.append(f"insufficient_vectors:{len(rows)}")

    required_fields = list(check.get("required_fields", []))
    if rows and required_fields:
        sample = rows[0] if isinstance(rows[0], dict) else {}
        for field in required_fields:
            if field not in sample:
                failures.append(f"missing_field:{field}")
    return failures


def _check_graph_adjacency(root: Path, check: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    graph = load_global_content_graph(root)
    kind = str(check.get("adjacency_kind", "semantic"))
    adjacency = graph.get("adjacency", {}).get(kind, {})
    edge_count = sum(len(neighbors) for neighbors in adjacency.values())
    if edge_count < int(check.get("min_edges", 1)):
        failures.append(f"insufficient_{kind}_edges:{edge_count}")

    required_meta = list(check.get("require_edge_metadata", []))
    if required_meta and adjacency:
        overlays = graph.get("overlays", {}).get(f"{kind}_edges", {})
        if not overlays:
            failures.append(f"missing_{kind}_edge_metadata_overlay")
        else:
            sample = next(iter(overlays.values()), {})
            if isinstance(sample, dict):
                for field in required_meta:
                    if field not in sample:
                        failures.append(f"missing_edge_metadata_field:{field}")
    return failures


def _check_semantic_bridge(root: Path, check: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    session_ids: List[str] = []
    for item in check.get("sessions", []):
        session_id = str(item["session_id"])
        session_ids.append(session_id)
        text = _conversation_text(item.get("events", []))
        for keyword in item.get("forbidden_keywords", []):
            if keyword.lower() in text.lower():
                failures.append(f"forbidden_keyword_present:{session_id}:{keyword}")
        _ingest_session(
            root,
            session_id=session_id,
            events=item.get("events", []),
            mtsf_mode=str(check.get("mtsf_mode", "deep")),
            llm_preference=str(check.get("llm_preference", "auto")),
        )

    if check.get("rebuild_global"):
        rebuild_global_content_graph(root, session_ids=session_ids)

    graph = load_global_content_graph(root)
    semantic = graph.get("adjacency", {}).get("semantic", {})
    if not semantic:
        failures.append("missing_semantic_adjacency")
        return failures

    min_cosine = float(check.get("min_bridge_cosine", 0.72))
    overlays = graph.get("overlays", {}).get("semantic_edges", {})
    found_bridge = False
    nodes = graph.get("nodes", {})
    for node_id, neighbors in semantic.items():
        sid_a = str(nodes.get(node_id, {}).get("source_session_id", ""))
        for neighbor in neighbors:
            sid_b = str(nodes.get(neighbor, {}).get("source_session_id", ""))
            if not sid_a or sid_a == sid_b:
                continue
            meta = overlays.get(f"{node_id}::{neighbor}", overlays.get(neighbor, {}))
            cosine = float(meta.get("cosine", 0.0)) if isinstance(meta, dict) else 0.0
            if cosine >= min_cosine:
                found_bridge = True
                break
        if found_bridge:
            break
    if not found_bridge:
        failures.append(f"no_cross_session_semantic_bridge>={min_cosine}")
    return failures


def _check_pipeline_gap(root: Path, check: Dict[str, Any]) -> List[str]:
    fixture = {
        "id": check.get("session_id", "gap-pipeline"),
        "input": {
            "session_id": check["session_id"],
            "source_type": "text",
            "domains": [],
            "events": check.get("events", []),
        },
    }
    payload = _extract_draft_for_fixture(
        root,
        fixture,
        llm_preference=str(check.get("llm_preference", "auto")),
    )
    failures = _check_extraction_expectations(payload, check.get("expectations", {}))
    required_sources = set(check.get("expectations", {}).get("required_shape_provenance_sources", []))
    if required_sources:
        found_sources = {
            str(shape.get("provenance", {}).get("source", ""))
            for shape in payload["draft"].get("candidate_shapes", [])
        }
        missing = required_sources - found_sources
        if missing:
            failures.append(f"missing_shape_provenance_sources:{','.join(sorted(missing))}")
    return failures


def _check_pair_gap(root: Path, check: Dict[str, Any]) -> List[str]:
    fixture = {
        "id": "gap-pair",
        "type": "pair_discrimination",
        "pair": check.get("pair", []),
        "expectations": {},
    }
    payload = _run_pair_fixture(root, fixture, llm_preference=str(check.get("llm_preference", "auto")))
    expectations = check.get("expectations", {})
    failures = _check_pair_expectations(payload, expectations)
    min_entities = int(expectations.get("min_entities_on_at_least_one_side", 0))
    if min_entities:
        counts = [len(_entity_names(payload["drafts"][label]["draft"])) for label in payload["drafts"]]
        if max(counts) < min_entities:
            failures.append(f"min_entities_on_at_least_one_side:{max(counts)}")
    return failures


def _check_stencil_merge(root: Path, check: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    draft_path = root / str(check["draft_path"])
    draft = read_json(draft_path, default={})
    matches = match_stencil_drafts_to_seed(root, draft.get("stencil_drafts", []))
    min_score = float(check.get("min_structural_score", 0.8))
    best = max((float(row.get("structural_score", 0.0)) for row in matches), default=0.0)
    if best < min_score:
        failures.append(f"stencil_merge_score_below:{best}<{min_score}")
    if check.get("require_matched_seed_id") and not any(row.get("best_seed_match_id") for row in matches):
        failures.append("no_matched_seed_id")
    if MERGE_SCORE_THRESHOLD >= 1.0 and min_score < 1.0:
        failures.append(f"projector_merge_threshold_still_exact:{MERGE_SCORE_THRESHOLD}")
    return failures


def _check_activation_shape(root: Path, check: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    session_id = str(check["session_id"])
    _ingest_session(
        root,
        session_id=session_id,
        events=check.get("events", []),
        mtsf_mode=str(check.get("mtsf_mode", "deep")),
        llm_preference=str(check.get("llm_preference", "auto")),
    )
    refs = materialize_session_mtsf(root, session_id)
    snapshot = read_json(Path(refs["mtsf_activation_snapshot"]), default={})
    fragment = str(check.get("discovered_entity_fragment", "")).lower()
    forbidden = set(check.get("forbidden_dominant_shapes", []))
    matched = False
    for row in snapshot.get("shape_activation_results", []):
        entity_id = str(row.get("entity_id", ""))
        if fragment and fragment not in entity_id.lower():
            continue
        matched = True
        dominant = str(row.get("dominant_shape_id", ""))
        if dominant in forbidden:
            failures.append(f"forbidden_dominant_shape:{entity_id}:{dominant}")
    if fragment and not matched:
        failures.append(f"discovered_entity_not_activated:{fragment}")

    cohesion_path = session_dir(root, session_id) / "mtsf" / "shape_cluster_cohesion.json"
    if not cohesion_path.exists():
        failures.append("missing_shape_cluster_cohesion_artifact")
    else:
        cohesion = read_json(cohesion_path, default={})
        score = float(cohesion.get("score", 0.0))
        if score < float(check.get("min_cluster_cohesion", 0.7)):
            failures.append(f"cluster_cohesion_below:{score}")
    return failures


def _check_suite_live_replay(root: Path, check: Dict[str, Any]) -> List[str]:
    evals_dir = root / "docs" / "frameworks" / "metaphysical-thought-space" / "evals" / "semantic-shape-extraction"
    live_count = 0
    for path in sorted(evals_dir.glob("eval-*.json")):
        fixture = _load_fixture(path)
        if fixture.get("live_pipeline"):
            live_count += 1
        if fixture.get("input", {}).get("raw_content") and fixture.get("reference_only") is False:
            live_count += 1
    if live_count < int(check.get("min_live_fixtures", 1)):
        return [f"insufficient_live_extraction_fixtures:{live_count}"]
    return []


def _check_suite_pass_rate(root: Path, check: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    suite = str(check.get("suite", "shape-utility"))
    if suite != "shape-utility":
        return [f"unsupported_suite:{suite}"]
    result = run_shape_utility_evals(root, llm_preference=str(check.get("llm_preference", "auto")))
    if result.get("passed", 0) < int(check.get("min_passed", 1)):
        failures.append(f"passed_below:{result.get('passed')}")
    if result.get("pass_rate", 0.0) < float(check.get("min_pass_rate", 0.0)):
        failures.append(f"pass_rate_below:{result.get('pass_rate')}")
    return failures


def _check_cross_session(root: Path, check: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    session_ids: List[str] = []
    shape_ids: List[Set[str]] = []
    for item in check.get("sessions", []):
        session_id = str(item["session_id"])
        session_ids.append(session_id)
        _ingest_session(
            root,
            session_id=session_id,
            events=item.get("events", []),
            mtsf_mode=str(check.get("mtsf_mode", "deep")),
            llm_preference=str(check.get("llm_preference", "auto")),
        )
        draft = read_json(session_dir(root, session_id) / "mtsf" / "extraction_draft.json", default={})
        shape_ids.append(_candidate_shape_ids_from_draft(draft))

    rebuild_global_content_graph(root, session_ids=session_ids)
    promotion_path = root / "memory" / "mtsf" / "cross_session_shapes.json"
    if not promotion_path.exists():
        failures.append("missing_cross_session_shapes_artifact")

    fragment = str(check.get("expectations", {}).get("shared_candidate_shape_fragment", "")).lower()
    if fragment and not any(fragment in shape_id.lower() for ids in shape_ids for shape_id in ids):
        failures.append(f"no_shared_candidate_shape_fragment:{fragment}")

    min_refs = int(check.get("expectations", {}).get("min_cross_session_shape_refs", 0))
    if min_refs:
        if not promotion_path.exists():
            failures.append("missing_cross_session_shape_refs")
        else:
            payload = read_json(promotion_path, default={})
            refs = payload.get("cross_session_refs", [])
            if len(refs) < min_refs:
                failures.append(f"insufficient_cross_session_shape_refs:{len(refs)}")
    return failures


def _check_downstream_hook(root: Path, check: Dict[str, Any]) -> List[str]:
    failures: List[str] = []
    hooks = list(check.get("hooks", []))
    implemented = 0
    repo_root = Path(__file__).resolve().parents[2]
    cli_text = (repo_root / "src" / "conversation_os" / "cli.py").read_text(encoding="utf-8")
    graph_text = (repo_root / "src" / "conversation_os" / "mtsf_graph.py").read_text(encoding="utf-8")
    if "graph_follow_intent" in hooks and "--intent" in cli_text and "resolve_traversal_intent" in graph_text:
        implemented += 1
    routing_path = repo_root / "src" / "conversation_os" / "routing.py"
    if "task_pack_shape_hint" in hooks and routing_path.exists():
        if "dominant_shape" in routing_path.read_text(encoding="utf-8"):
            implemented += 1
    if implemented < int(check.get("min_hooks_implemented", 1)):
        failures.append(f"downstream_hooks_implemented:{implemented}")
    return failures


_CHECK_DISPATCH = {
    "artifact_field": _check_artifact_field,
    "graph_adjacency": _check_graph_adjacency,
    "semantic_bridge": _check_semantic_bridge,
    "pipeline": _check_pipeline_gap,
    "pair_discrimination": _check_pair_gap,
    "stencil_merge": _check_stencil_merge,
    "activation_shape": _check_activation_shape,
    "suite_live_replay": _check_suite_live_replay,
    "suite_pass_rate": _check_suite_pass_rate,
    "cross_session": _check_cross_session,
    "downstream_hook": _check_downstream_hook,
}


def run_gap_closure_evals(
    root: Path,
    *,
    gap_ids: Optional[Sequence[str]] = None,
    llm_preference: str = "auto",
) -> Dict[str, Any]:
    evals_dir = default_gap_closure_evals_dir(root)
    fixtures = sorted(evals_dir.glob("gap-G*.json"))
    selected = {str(gap_id).upper() for gap_id in (gap_ids or [])}
    runs: List[Dict[str, Any]] = []
    passed = 0
    required_failed: List[str] = []

    for fixture_path in fixtures:
        fixture = _load_fixture(fixture_path)
        gap_id = str(fixture.get("gap_id", fixture_path.stem))
        if selected and gap_id.upper() not in selected:
            continue
        check = dict(fixture.get("check", {}))
        if "llm_preference" not in check:
            check["llm_preference"] = llm_preference
        check_type = str(check.get("type", ""))
        handler = _CHECK_DISPATCH.get(check_type)
        failures = handler(root, check) if handler else [f"unknown_check_type:{check_type}"]
        ok = not failures
        if ok:
            passed += 1
        elif fixture.get("required", True):
            required_failed.append(gap_id)
        runs.append(
            {
                "gap_id": gap_id,
                "title": fixture.get("title", ""),
                "phase": fixture.get("phase", ""),
                "required": bool(fixture.get("required", True)),
                "check_type": check_type,
                "ok": ok,
                "closed": ok,
                "failures": failures,
            }
        )

    total = len(runs)
    return {
        "suite": "gap-closure",
        "gap_plan": GAP_PLAN_PATH,
        "llm_preference": llm_preference,
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": round(passed / total, 3) if total else 0.0,
        "all_required_closed": not required_failed,
        "required_failed": required_failed,
        "runs": runs,
    }
