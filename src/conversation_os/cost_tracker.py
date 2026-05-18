from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .models import LLMCostEvent
from .storage import append_jsonl, make_id, read_json, read_jsonl, utc_now, write_json


def _config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "llm_costs.json"


def _events_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "llm_cost_events.jsonl"


def _default_cost_config() -> Dict[str, Any]:
    return {
        "version": 1,
        "defaults": {
            "equivalent_profile": "heuristic_baseline",
        },
        "equivalent_profiles": {
            "heuristic_baseline": {
                "label": "Heuristic LLM-equivalent baseline",
                "input_cost_per_1k_tokens": 0.001,
                "output_cost_per_1k_tokens": 0.002,
            }
        },
        "actual_profiles": {},
        "model_aliases": {},
    }


def ensure_cost_tracker_bootstrap(root: Path) -> Path:
    path = _config_path(root)
    if not path.exists():
        write_json(path, _default_cost_config())
    return path


def load_cost_config(root: Path) -> Dict[str, Any]:
    ensure_cost_tracker_bootstrap(root)
    return read_json(_config_path(root), default=_default_cost_config())


def estimate_token_count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, str):
        text = value
    else:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    text = text.strip()
    if not text:
        return 0
    return max(1, round(len(text) / 4))


def _profile_cost(profile: Dict[str, Any], input_tokens: int, output_tokens: int) -> float:
    input_rate = float(profile.get("input_cost_per_1k_tokens", 0.0))
    output_rate = float(profile.get("output_cost_per_1k_tokens", 0.0))
    return round((input_tokens / 1000.0) * input_rate + (output_tokens / 1000.0) * output_rate, 6)


def _resolve_actual_profile(config: Dict[str, Any], provider: str, model: str, pricing_profile: str | None) -> tuple[str, Dict[str, Any] | None]:
    profiles = config.get("actual_profiles", {})
    aliases = config.get("model_aliases", {})
    if pricing_profile and pricing_profile in profiles:
        return pricing_profile, profiles[pricing_profile]
    if model and model in profiles:
        return model, profiles[model]
    alias_key = f"{provider}:{model}" if provider and model else ""
    alias_target = aliases.get(alias_key) or aliases.get(model)
    if alias_target and alias_target in profiles:
        return alias_target, profiles[alias_target]
    return pricing_profile or "", None


def record_actual_cost(
    root: Path,
    *,
    component: str,
    operation: str,
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    usd_cost: float | None = None,
    pricing_profile: str | None = None,
    token_source: str = "actual",
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    config = load_cost_config(root)
    resolved_profile, profile = _resolve_actual_profile(config, provider, model, pricing_profile)
    if usd_cost is None and profile is not None:
        usd_cost = _profile_cost(profile, input_tokens, output_tokens)
    status = "recorded" if usd_cost is not None else "missing_pricing"
    event = LLMCostEvent(
        event_id=make_id("llm-cost"),
        timestamp=utc_now(),
        ledger="actual",
        component=component,
        operation=operation,
        provider=provider,
        model=model,
        pricing_profile=resolved_profile,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        usd_cost=usd_cost,
        status=status,
        token_source=token_source,
        metadata=metadata or {},
    ).to_dict()
    append_jsonl(_events_path(root), event)
    return event


def record_equivalent_cost(
    root: Path,
    *,
    component: str,
    operation: str,
    input_tokens: int,
    output_tokens: int,
    pricing_profile: str | None = None,
    model: str = "heuristic-equivalent",
    provider: str = "internal",
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    config = load_cost_config(root)
    profile_id = pricing_profile or config.get("defaults", {}).get("equivalent_profile", "heuristic_baseline")
    profile = config.get("equivalent_profiles", {}).get(profile_id, {})
    usd_cost = _profile_cost(profile, input_tokens, output_tokens)
    event = LLMCostEvent(
        event_id=make_id("llm-cost"),
        timestamp=utc_now(),
        ledger="equivalent",
        component=component,
        operation=operation,
        provider=provider,
        model=model,
        pricing_profile=profile_id,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        usd_cost=usd_cost,
        status="estimated",
        token_source="estimated",
        metadata=metadata or {},
    ).to_dict()
    append_jsonl(_events_path(root), event)
    return event


def list_cost_events(root: Path, limit: int = 50) -> List[Dict[str, Any]]:
    rows = read_jsonl(_events_path(root))
    rows.sort(key=lambda item: (item.get("timestamp", ""), item.get("event_id", "")), reverse=True)
    return rows[:limit]


def get_cost_summary(root: Path) -> Dict[str, Any]:
    rows = read_jsonl(_events_path(root))
    totals = {
        "event_count": len(rows),
        "actual_event_count": 0,
        "equivalent_event_count": 0,
        "actual_usd_total": 0.0,
        "equivalent_usd_total": 0.0,
        "actual_total_tokens": 0,
        "equivalent_total_tokens": 0,
        "total_tokens": 0,
        "missing_pricing_event_count": 0,
    }
    by_component: Dict[str, Dict[str, Any]] = {}
    by_operation: Dict[str, Dict[str, Any]] = {}
    by_model: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        ledger = row.get("ledger", "actual")
        usd_cost = row.get("usd_cost")
        token_count = int(row.get("total_tokens", 0))
        totals["total_tokens"] += token_count
        if ledger == "actual":
            totals["actual_event_count"] += 1
            totals["actual_total_tokens"] += token_count
            if usd_cost is not None:
                totals["actual_usd_total"] = round(totals["actual_usd_total"] + float(usd_cost), 6)
            if row.get("status") == "missing_pricing":
                totals["missing_pricing_event_count"] += 1
        else:
            totals["equivalent_event_count"] += 1
            totals["equivalent_total_tokens"] += token_count
            totals["equivalent_usd_total"] = round(totals["equivalent_usd_total"] + float(usd_cost or 0.0), 6)

        component = row.get("component", "unknown")
        component_bucket = by_component.setdefault(
            component,
            {
                "component": component,
                "event_count": 0,
                "actual_usd_total": 0.0,
                "equivalent_usd_total": 0.0,
                "actual_tokens": 0,
                "equivalent_tokens": 0,
                "total_tokens": 0,
            },
        )
        component_bucket["event_count"] += 1
        component_bucket["total_tokens"] += token_count
        if ledger == "actual":
            component_bucket["actual_tokens"] += token_count
            component_bucket["actual_usd_total"] = round(component_bucket["actual_usd_total"] + float(usd_cost or 0.0), 6)
        else:
            component_bucket["equivalent_tokens"] += token_count
            component_bucket["equivalent_usd_total"] = round(component_bucket["equivalent_usd_total"] + float(usd_cost or 0.0), 6)

        operation = row.get("operation", "unknown")
        operation_bucket = by_operation.setdefault(
            operation,
            {
                "operation": operation,
                "component": component,
                "event_count": 0,
                "actual_tokens": 0,
                "equivalent_tokens": 0,
                "total_tokens": 0,
                "actual_usd_total": 0.0,
                "equivalent_usd_total": 0.0,
            },
        )
        operation_bucket["event_count"] += 1
        operation_bucket["total_tokens"] += token_count
        if ledger == "actual":
            operation_bucket["actual_tokens"] += token_count
            operation_bucket["actual_usd_total"] = round(operation_bucket["actual_usd_total"] + float(usd_cost or 0.0), 6)
        else:
            operation_bucket["equivalent_tokens"] += token_count
            operation_bucket["equivalent_usd_total"] = round(operation_bucket["equivalent_usd_total"] + float(usd_cost or 0.0), 6)

        model_key = row.get("model") or row.get("pricing_profile") or "unknown"
        model_bucket = by_model.setdefault(
            model_key,
            {"model": model_key, "ledger": ledger, "event_count": 0, "usd_total": 0.0, "actual_tokens": 0, "equivalent_tokens": 0, "total_tokens": 0},
        )
        model_bucket["event_count"] += 1
        model_bucket["total_tokens"] += token_count
        if ledger == "actual":
            model_bucket["actual_tokens"] += token_count
        else:
            model_bucket["equivalent_tokens"] += token_count
        model_bucket["usd_total"] = round(model_bucket["usd_total"] + float(usd_cost or 0.0), 6)

    totals["actual_usd_total"] = round(totals["actual_usd_total"], 6)
    totals["equivalent_usd_total"] = round(totals["equivalent_usd_total"], 6)
    return {
        "generated_at": utc_now(),
        "config_path": str(_config_path(root)),
        "events_path": str(_events_path(root)),
        "totals": totals,
        "by_component": sorted(by_component.values(), key=lambda item: (-item["event_count"], item["component"])),
        "by_operation": sorted(by_operation.values(), key=lambda item: (-item["total_tokens"], item["operation"])),
        "by_model": sorted(by_model.values(), key=lambda item: (-item["event_count"], item["model"])),
        "recent_events": list_cost_events(root, limit=12),
    }
