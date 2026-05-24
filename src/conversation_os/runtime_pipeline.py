from __future__ import annotations

import fcntl
import os
from time import perf_counter
from contextlib import contextmanager
from pathlib import Path
from typing import IO, Any, Dict, Iterator, List, Set

from .storage import ensure_dir, read_json, utc_now, write_json


MODULE_ID = "assembly.runtime.runtime_pipeline"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "DEFAULT_RUNTIME_PIPELINE",
    "ensure_runtime_pipeline_config",
    "load_runtime_pipeline_config",
    "update_runtime_pipeline_component",
    "get_runtime_pipeline_status",
    "write_runtime_pipeline_last_run",
    "execute_runtime_pipeline",
)
__all__ = list(PUBLIC_API)


DEFAULT_RUNTIME_PIPELINE = {
    "version": 1,
    "selection_mode": "dependency_weighted",
    "components": [
        {
            "component_id": "bootstrap_legacy_sources",
            "label": "Bootstrap Legacy Sources",
            "enabled": True,
            "order": 10,
            "weight": 1.0,
        },
        {
            "component_id": "ensure_pipeline_specs",
            "label": "Ensure Pipeline Specs",
            "enabled": True,
            "order": 10,
            "weight": 0.9,
        },
        {
            "component_id": "analysis_units",
            "label": "Build Analysis Units",
            "enabled": True,
            "order": 20,
            "weight": 1.0,
        },
        {
            "component_id": "conversation_deltas",
            "label": "Build Conversation Deltas",
            "enabled": True,
            "order": 20,
            "weight": 1.1,
        },
        {
            "component_id": "meta_layer",
            "label": "Extract Meta Layer",
            "enabled": True,
            "order": 30,
            "weight": 1.2,
        },
        {
            "component_id": "shape_signatures",
            "label": "Extract Shape Signatures",
            "enabled": True,
            "order": 35,
            "weight": 1.05,
        },
        {
            "component_id": "shape_graph",
            "label": "Build Shape Graph",
            "enabled": True,
            "order": 36,
            "weight": 1.0,
        },
        {
            "component_id": "conversation_threads",
            "label": "Build Conversation Threads",
            "enabled": True,
            "order": 30,
            "weight": 1.0,
        },
        {
            "component_id": "thread_abstractions",
            "label": "Build Thread Abstractions",
            "enabled": True,
            "order": 40,
            "weight": 1.1,
        },
        {
            "component_id": "conversation_concepts",
            "label": "Build Conversation Concepts",
            "enabled": True,
            "order": 45,
            "weight": 1.1,
        },
        {
            "component_id": "context_bubbles",
            "label": "Build Context Bubbles",
            "enabled": True,
            "order": 50,
            "weight": 1.0,
        },
        {
            "component_id": "knowledge_layer",
            "label": "Build Knowledge Layer",
            "enabled": True,
            "order": 60,
            "weight": 1.15,
        },
        {
            "component_id": "plugin_primitives",
            "label": "Materialize Plugin Primitives",
            "enabled": True,
            "order": 70,
            "weight": 0.8,
        },
        {
            "component_id": "concept_nodes",
            "label": "Materialize Concept Nodes",
            "enabled": True,
            "order": 80,
            "weight": 0.85,
        },
        {
            "component_id": "connections",
            "label": "Materialize Connections",
            "enabled": True,
            "order": 80,
            "weight": 0.85,
        },
    ],
}


def _config_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "config" / "runtime_pipeline.json"


def _last_run_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "runtime_pipeline_last_run.json"


def _lock_path(root: Path) -> Path:
    return root / "product" / "inner_world_v1" / "data" / "runtime_pipeline.lock"


def _has_active_runtime_pipeline_lock(root: Path) -> bool:
    path = _lock_path(root)
    if not path.exists():
        return False
    with path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return False


def ensure_runtime_pipeline_config(root: Path) -> Path:
    path = _config_path(root)
    ensure_dir(path.parent)
    if not path.exists():
        write_json(path, DEFAULT_RUNTIME_PIPELINE)
    return path


def _merged_components(raw_components: List[Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    merged = {
        row["component_id"]: dict(row)
        for row in DEFAULT_RUNTIME_PIPELINE["components"]
    }
    for row in raw_components or []:
        component_id = row.get("component_id")
        if not component_id:
            continue
        if component_id in merged:
            merged[component_id].update({key: value for key, value in row.items() if key != "component_id"})
        else:
            merged[component_id] = dict(row)
    return sorted(
        merged.values(),
        key=lambda row: (
            int(row.get("order", 999)),
            -float(row.get("weight", 1.0)),
            row["component_id"],
        ),
    )


def load_runtime_pipeline_config(root: Path) -> Dict[str, Any]:
    path = ensure_runtime_pipeline_config(root)
    payload = read_json(path, default={}) or {}
    return {
        "version": int(payload.get("version", DEFAULT_RUNTIME_PIPELINE["version"])),
        "selection_mode": payload.get("selection_mode", DEFAULT_RUNTIME_PIPELINE["selection_mode"]),
        "components": _merged_components(payload.get("components")),
        "config_path": str(path),
        "last_run_path": str(_last_run_path(root)),
    }


def update_runtime_pipeline_component(
    root: Path,
    component_id: str,
    *,
    enabled: bool | None = None,
    order: int | None = None,
    weight: float | None = None,
) -> Dict[str, Any]:
    path = ensure_runtime_pipeline_config(root)
    payload = read_json(path, default={}) or {}
    components = list(payload.get("components", []))
    target = next((row for row in components if row.get("component_id") == component_id), None)
    if target is None:
        default = next(
            (row for row in DEFAULT_RUNTIME_PIPELINE["components"] if row["component_id"] == component_id),
            {"component_id": component_id, "label": component_id.replace("_", " ").title()},
        )
        target = dict(default)
        components.append(target)
    if enabled is not None:
        target["enabled"] = bool(enabled)
    if order is not None:
        target["order"] = int(order)
    if weight is not None:
        target["weight"] = float(weight)
    payload["version"] = int(payload.get("version", DEFAULT_RUNTIME_PIPELINE["version"]))
    payload["selection_mode"] = payload.get("selection_mode", DEFAULT_RUNTIME_PIPELINE["selection_mode"])
    payload["components"] = _merged_components(components)
    write_json(path, payload)
    return load_runtime_pipeline_config(root)


def get_runtime_pipeline_status(root: Path) -> Dict[str, Any]:
    config = load_runtime_pipeline_config(root)
    last_run = read_json(_last_run_path(root), default=None)
    summary = None
    if isinstance(last_run, dict):
        last_run = dict(last_run)
        components = [dict(row) for row in last_run.get("components", [])]
        last_run["components"] = components
        active_lock = _has_active_runtime_pipeline_lock(root)
        if last_run.get("run_status") == "running" and not active_lock:
            active_component_id = last_run.get("active_component_id")
            last_run["run_status"] = "interrupted"
            last_run["stale_running_state"] = True
            last_run["stale_detected_at"] = utc_now()
            last_run["active_component_id"] = None
            for row in components:
                if row.get("status") == "running":
                    row["status"] = "interrupted"
                    row["stale_running_state"] = True
                    if active_component_id and row.get("component_id") == active_component_id:
                        row["stale_active_component_id"] = active_component_id
        components = last_run.get("components", [])
        counts: Dict[str, int] = {}
        active_stage = last_run.get("active_component_id")
        completed_ids: Set[str] = set()
        for row in components:
            status = row.get("status", "unknown")
            counts[status] = counts.get(status, 0) + 1
            if status == "running" and not active_stage:
                active_stage = row.get("component_id")
            if status == "completed":
                completed_ids.add(row.get("component_id", ""))
        last_completed_stage = next(
            (
                component_id
                for component_id in reversed(last_run.get("execution_order", []))
                if component_id in completed_ids
            ),
            None,
        )
        if last_completed_stage is None:
            for row in components:
                if row.get("status") == "completed":
                    last_completed_stage = row.get("component_id")
        summary = {
            "run_status": last_run.get("run_status"),
            "run_started_at": last_run.get("run_started_at"),
            "run_finished_at": last_run.get("run_finished_at"),
            "active_stage": active_stage,
            "last_completed_stage": last_completed_stage,
            "counts": counts,
            "execution_order": last_run.get("execution_order", []),
        }
    return config | {"last_run": last_run, "summary": summary}


def write_runtime_pipeline_last_run(root: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    path = _last_run_path(root)
    ensure_dir(path.parent)
    write_json(path, payload)
    return payload


@contextmanager
def _try_runtime_pipeline_lock(root: Path) -> Iterator[IO[str] | None]:
    path = _lock_path(root)
    ensure_dir(path.parent)
    with path.open("a+", encoding="utf-8") as handle:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield None
            return
        handle.seek(0)
        handle.truncate()
        handle.write(f"pid={os.getpid()} started_at={utc_now()}\n")
        handle.flush()
        try:
            yield handle
        finally:
            handle.seek(0)
            handle.truncate()
            handle.flush()
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _component_artifacts(component: Dict[str, Any]) -> List[str]:
    artifacts = component.get("artifacts", [])
    if callable(artifacts):
        artifacts = artifacts()
    rows: List[str] = []
    for item in artifacts or []:
        if isinstance(item, Path):
            rows.append(str(item))
        elif item:
            rows.append(str(item))
    return rows


def _artifacts_exist(artifacts: List[str]) -> bool:
    return bool(artifacts) and all(Path(path).exists() for path in artifacts)


def _selected_component_ids(
    ordered_components: List[Dict[str, Any]],
    registry: Dict[str, Dict[str, Any]],
    *,
    from_stage: str | None = None,
    only_stage: str | None = None,
) -> Set[str]:
    registry_ids = {component_id for component_id in registry}
    ordered_ids = [row["component_id"] for row in ordered_components if row["component_id"] in registry_ids]
    if from_stage and from_stage not in registry_ids:
        raise KeyError(from_stage)
    if only_stage and only_stage not in registry_ids:
        raise KeyError(only_stage)

    selected: Set[str]
    if only_stage:
        selected = {only_stage}
    elif from_stage:
        selected = set()
        seen = False
        for component_id in ordered_ids:
            if component_id == from_stage:
                seen = True
            if seen:
                selected.add(component_id)
    else:
        selected = set(ordered_ids)

    closure = set(selected)
    stack = list(selected)
    while stack:
        component_id = stack.pop()
        for dependency in registry.get(component_id, {}).get("requires", []):
            if dependency in registry_ids and dependency not in closure:
                closure.add(dependency)
                stack.append(dependency)
    return closure


def _ordered_statuses(
    statuses: Dict[str, Dict[str, Any]],
    component_rows: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    return sorted(
        statuses.values(),
        key=lambda row: (
            int(row.get("order", component_rows.get(row["component_id"], {}).get("order", 999))),
            -float(row.get("weight", component_rows.get(row["component_id"], {}).get("weight", 1.0))),
            row["component_id"],
        ),
    )


def _write_pipeline_snapshot(
    root: Path,
    loaded: Dict[str, Any],
    component_rows: Dict[str, Dict[str, Any]],
    statuses: Dict[str, Dict[str, Any]],
    execution_order: List[str],
    *,
    run_started_at: str,
    run_finished_at: str | None,
    run_status: str,
    active_component_id: str | None,
    options: Dict[str, Any],
) -> Dict[str, Any]:
    return write_runtime_pipeline_last_run(
        root,
        {
            "generated_at": utc_now(),
            "run_started_at": run_started_at,
            "run_finished_at": run_finished_at,
            "run_status": run_status,
            "active_component_id": active_component_id,
            "selection_mode": loaded.get("selection_mode", DEFAULT_RUNTIME_PIPELINE["selection_mode"]),
            "options": options,
            "execution_order": execution_order,
            "components": _ordered_statuses(statuses, component_rows),
        },
    )


def execute_runtime_pipeline(
    root: Path,
    registry: Dict[str, Dict[str, Any]],
    *,
    config: Dict[str, Any] | None = None,
    resume: bool = False,
    from_stage: str | None = None,
    only_stage: str | None = None,
    force: bool = False,
) -> Dict[str, Any]:
    loaded = config or load_runtime_pipeline_config(root)
    with _try_runtime_pipeline_lock(root) as lock_handle:
        if lock_handle is None:
            status = get_runtime_pipeline_status(root)
            return {
                "config": loaded,
                "last_run": status.get("last_run"),
                "results": {},
                "lock_contended": True,
            }
        component_rows = {row["component_id"]: row for row in loaded["components"]}
        statuses: Dict[str, Dict[str, Any]] = {}
        results: Dict[str, Any] = {}
        execution_order: List[str] = []
        previous_last_run = read_json(_last_run_path(root), default={}) or {}
        previous_components = {
            row["component_id"]: row
            for row in previous_last_run.get("components", [])
            if row.get("component_id")
        }
        selected_ids = _selected_component_ids(
            loaded["components"],
            registry,
            from_stage=from_stage,
            only_stage=only_stage,
        )
        options = {
            "resume": bool(resume),
            "from_stage": from_stage,
            "only_stage": only_stage,
            "force": bool(force),
        }
        run_started_at = utc_now()

        for component_id, row in component_rows.items():
            if component_id not in registry:
                statuses[component_id] = {
                    "component_id": component_id,
                    "label": row.get("label", component_id),
                    "status": "unknown_component",
                    "order": int(row.get("order", 999)),
                    "weight": float(row.get("weight", 1.0)),
                    "requires": [],
                }

        enabled_ids = {
            component_id
            for component_id, component in registry.items()
            if component_rows.get(component_id, {}).get("enabled", True) and component_id in selected_ids
        }
        pending = set(enabled_ids)
        satisfied_ids: Set[str] = set()

        for component_id, component in registry.items():
            row = component_rows.get(component_id, {})
            if component_id not in selected_ids:
                statuses[component_id] = {
                    "component_id": component_id,
                    "label": row.get("label", component.get("label", component_id)),
                    "status": "not_selected",
                    "order": int(row.get("order", 999)),
                    "weight": float(row.get("weight", 1.0)),
                    "requires": list(component.get("requires", [])),
                }
                continue
            if component_id not in enabled_ids:
                statuses[component_id] = {
                    "component_id": component_id,
                    "label": row.get("label", component.get("label", component_id)),
                    "status": "disabled",
                    "order": int(row.get("order", 999)),
                    "weight": float(row.get("weight", 1.0)),
                    "requires": list(component.get("requires", [])),
                }

        _write_pipeline_snapshot(
            root,
            loaded,
            component_rows,
            statuses,
            execution_order,
            run_started_at=run_started_at,
            run_finished_at=None,
            run_status="running",
            active_component_id=None,
            options=options,
        )

        while pending:
            progressed = False
            for component_id in sorted(list(pending)):
                component = registry[component_id]
                requires = list(component.get("requires", []))
                disabled_dependencies = [
                    dependency
                    for dependency in requires
                    if dependency not in enabled_ids
                    or statuses.get(dependency, {}).get("status") in {"disabled", "failed", "skipped_missing_dependencies"}
                ]
                if disabled_dependencies:
                    row = component_rows.get(component_id, {})
                    statuses[component_id] = {
                        "component_id": component_id,
                        "label": row.get("label", component.get("label", component_id)),
                        "status": "skipped_missing_dependencies",
                        "order": int(row.get("order", 999)),
                        "weight": float(row.get("weight", 1.0)),
                        "requires": requires,
                        "missing_dependencies": disabled_dependencies,
                    }
                    pending.remove(component_id)
                    _write_pipeline_snapshot(
                        root,
                        loaded,
                        component_rows,
                        statuses,
                        execution_order,
                        run_started_at=run_started_at,
                        run_finished_at=None,
                        run_status="running",
                        active_component_id=None,
                        options=options,
                    )
                    progressed = True

            ready = [
                component_id
                for component_id in pending
                if set(registry[component_id].get("requires", [])) <= satisfied_ids
            ]
            ready.sort(
                key=lambda component_id: (
                    int(component_rows.get(component_id, {}).get("order", 999)),
                    -float(component_rows.get(component_id, {}).get("weight", 1.0)),
                    component_id,
                )
            )
            for component_id in ready:
                component = registry[component_id]
                row = component_rows.get(component_id, {})
                artifact_paths = _component_artifacts(component)
                can_resume = False
                if not force and (resume or from_stage or only_stage):
                    previous = previous_components.get(component_id, {})
                    if previous.get("status") in {"completed", "skipped_completed"} and _artifacts_exist(artifact_paths):
                        can_resume = True
                if can_resume:
                    statuses[component_id] = {
                        "component_id": component_id,
                        "label": row.get("label", component.get("label", component_id)),
                        "status": "skipped_completed",
                        "order": int(row.get("order", 999)),
                        "weight": float(row.get("weight", 1.0)),
                        "requires": list(component.get("requires", [])),
                        "summary": previous_components.get(component_id, {}).get("summary"),
                        "artifacts": artifact_paths,
                        "resumed_from_last_run": True,
                        "started_at": previous_components.get(component_id, {}).get("started_at"),
                        "finished_at": previous_components.get(component_id, {}).get("finished_at"),
                        "duration_seconds": previous_components.get(component_id, {}).get("duration_seconds"),
                    }
                    pending.remove(component_id)
                    satisfied_ids.add(component_id)
                    _write_pipeline_snapshot(
                        root,
                        loaded,
                        component_rows,
                        statuses,
                        execution_order,
                        run_started_at=run_started_at,
                        run_finished_at=None,
                        run_status="running",
                        active_component_id=None,
                        options=options,
                    )
                    progressed = True
                    continue
                started_at = utc_now()
                statuses[component_id] = {
                    "component_id": component_id,
                    "label": row.get("label", component.get("label", component_id)),
                    "status": "running",
                    "order": int(row.get("order", 999)),
                    "weight": float(row.get("weight", 1.0)),
                    "requires": list(component.get("requires", [])),
                    "started_at": started_at,
                    "finished_at": None,
                    "duration_seconds": None,
                    "artifacts": artifact_paths,
                }
                _write_pipeline_snapshot(
                    root,
                    loaded,
                    component_rows,
                    statuses,
                    execution_order,
                    run_started_at=run_started_at,
                    run_finished_at=None,
                    run_status="running",
                    active_component_id=component_id,
                    options=options,
                )
                started_clock = perf_counter()
                try:
                    result = component["run"]()
                except Exception as exc:  # pragma: no cover - surfaced in caller tests
                    finished_at = utc_now()
                    statuses[component_id] = {
                        "component_id": component_id,
                        "label": row.get("label", component.get("label", component_id)),
                        "status": "failed",
                        "order": int(row.get("order", 999)),
                        "weight": float(row.get("weight", 1.0)),
                        "requires": list(component.get("requires", [])),
                        "error": str(exc),
                        "started_at": started_at,
                        "finished_at": finished_at,
                        "duration_seconds": round(perf_counter() - started_clock, 3),
                        "artifacts": artifact_paths,
                    }
                    pending.remove(component_id)
                    _write_pipeline_snapshot(
                        root,
                        loaded,
                        component_rows,
                        statuses,
                        execution_order,
                        run_started_at=run_started_at,
                        run_finished_at=finished_at,
                        run_status="failed",
                        active_component_id=None,
                        options=options,
                    )
                    progressed = True
                    continue
                results[component_id] = result
                execution_order.append(component_id)
                finished_at = utc_now()
                statuses[component_id] = {
                    "component_id": component_id,
                    "label": row.get("label", component.get("label", component_id)),
                    "status": "completed",
                    "order": int(row.get("order", 999)),
                    "weight": float(row.get("weight", 1.0)),
                    "requires": list(component.get("requires", [])),
                    "summary": result,
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "duration_seconds": round(perf_counter() - started_clock, 3),
                    "artifacts": artifact_paths,
                }
                pending.remove(component_id)
                satisfied_ids.add(component_id)
                _write_pipeline_snapshot(
                    root,
                    loaded,
                    component_rows,
                    statuses,
                    execution_order,
                    run_started_at=run_started_at,
                    run_finished_at=None,
                    run_status="running",
                    active_component_id=None,
                    options=options,
                )
                progressed = True

            if progressed:
                continue

            for component_id in sorted(pending):
                component = registry[component_id]
                row = component_rows.get(component_id, {})
                statuses[component_id] = {
                    "component_id": component_id,
                    "label": row.get("label", component.get("label", component_id)),
                    "status": "unresolved_dependencies",
                    "order": int(row.get("order", 999)),
                    "weight": float(row.get("weight", 1.0)),
                    "requires": list(component.get("requires", [])),
                }
            pending.clear()

        run_status = "completed"
        if any(row.get("status") == "failed" for row in statuses.values()):
            run_status = "failed"
        elif any(row.get("status") == "unresolved_dependencies" for row in statuses.values()):
            run_status = "completed_with_warnings"
        last_run = _write_pipeline_snapshot(
            root,
            loaded,
            component_rows,
            statuses,
            execution_order,
            run_started_at=run_started_at,
            run_finished_at=utc_now(),
            run_status=run_status,
            active_component_id=None,
            options=options,
        )
        return {
            "config": loaded,
            "last_run": last_run,
            "results": results,
        }
