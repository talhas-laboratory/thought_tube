from __future__ import annotations

import contextlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX fallback
    fcntl = None


MODULE_ID = "kernel.foundation.storage"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "utc_now",
    "repo_root_from",
    "slugify",
    "make_id",
    "ensure_dir",
    "read_json",
    "write_json",
    "append_jsonl",
    "read_jsonl",
    "write_jsonl",
    "write_markdown",
    "session_events_path",
    "session_dir",
    "cards_dir",
    "indexes_dir",
    "task_packs_dir",
    "plans_dir",
    "workspace_dir",
    "workspace_context_dir",
    "workspace_manifest_path",
    "workspace_events_path",
    "workspace_activity_events_path",
    "workspace_artifact_links_path",
    "workspace_blockers_path",
    "workspace_claims_path",
    "workspace_decisions_path",
    "workspace_work_item_events_path",
    "workspace_test_cases_path",
    "workspace_test_runs_path",
    "workspace_knowledge_records_path",
    "workspace_promotions_path",
    "workspace_materialized_paths",
    "workspace_source_paths",
    "workspace_exists",
    "workspace_ids",
    "sorted_files",
)
__all__ = list(PUBLIC_API)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def repo_root_from(start: Path | None = None) -> Path:
    if start is None:
        start = Path.cwd()
    current = start.resolve()
    markers = {"TENETS.md", "AGENTS.md", "pyproject.toml"}
    while current != current.parent:
        if any((current / marker).exists() for marker in markers):
            return current
        current = current.parent
    return start.resolve()


def slugify(value: str) -> str:
    import re

    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "item"


def make_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


@contextlib.contextmanager
def _jsonl_lock(path: Path):
    lock_path = path.with_suffix(path.suffix + ".lock")
    ensure_dir(lock_path.parent)
    if fcntl is None:
        lock_path.touch(exist_ok=True)
        yield
        return
    with lock_path.open("a+", encoding="utf-8") as lock_handle:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_dir(path.parent)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    ensure_dir(path.parent)
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    with _jsonl_lock(path):
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
        finally:
            os.close(fd)


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    rows: List[Dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    ensure_dir(path.parent)
    content = "\n".join(json.dumps(row, ensure_ascii=False) for row in rows)
    with _jsonl_lock(path):
        temp_path = path.with_suffix(path.suffix + ".tmp")
        temp_path.write_text(content + ("\n" if rows else ""), encoding="utf-8")
        os.replace(temp_path, path)


def write_markdown(path: Path, content: str) -> None:
    ensure_dir(path.parent)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def session_events_path(root: Path, session_id: str) -> Path:
    return root / "memory" / "events" / f"{session_id}.jsonl"


def session_dir(root: Path, session_id: str) -> Path:
    return root / "memory" / "sessions" / session_id


def cards_dir(root: Path) -> Path:
    return root / "memory" / "cards"


def indexes_dir(root: Path) -> Path:
    return root / "memory" / "indexes"


def task_packs_dir(root: Path) -> Path:
    return root / "context" / "task_packs"


def plans_dir(root: Path) -> Path:
    return root / "docs" / "plans"


def workspace_dir(root: Path, workspace_id: str) -> Path:
    return root / "memory" / "workspaces" / workspace_id


def workspace_context_dir(root: Path, workspace_id: str) -> Path:
    return root / "context" / "workspaces" / workspace_id


def workspace_manifest_path(root: Path, workspace_id: str) -> Path:
    return workspace_dir(root, workspace_id) / "manifest.json"


def workspace_events_path(root: Path, workspace_id: str) -> Path:
    return workspace_dir(root, workspace_id) / "events.jsonl"


def workspace_activity_events_path(root: Path, workspace_id: str) -> Path:
    return workspace_dir(root, workspace_id) / "activity_events.jsonl"


def workspace_artifact_links_path(root: Path, workspace_id: str) -> Path:
    return workspace_dir(root, workspace_id) / "artifact_links.jsonl"


def workspace_blockers_path(root: Path, workspace_id: str) -> Path:
    return workspace_dir(root, workspace_id) / "blockers.jsonl"


def workspace_claims_path(root: Path, workspace_id: str) -> Path:
    return workspace_dir(root, workspace_id) / "claims.jsonl"


def workspace_decisions_path(root: Path, workspace_id: str) -> Path:
    return workspace_dir(root, workspace_id) / "decisions.jsonl"


def workspace_work_item_events_path(root: Path, workspace_id: str) -> Path:
    return workspace_dir(root, workspace_id) / "work_item_events.jsonl"


def workspace_test_cases_path(root: Path, workspace_id: str) -> Path:
    return workspace_dir(root, workspace_id) / "test_cases.jsonl"


def workspace_test_runs_path(root: Path, workspace_id: str) -> Path:
    return workspace_dir(root, workspace_id) / "test_runs.jsonl"


def workspace_knowledge_records_path(root: Path, workspace_id: str) -> Path:
    return workspace_dir(root, workspace_id) / "knowledge_records.jsonl"


def workspace_promotions_path(root: Path, workspace_id: str) -> Path:
    return workspace_dir(root, workspace_id) / "promotions.jsonl"


def workspace_materialized_paths(root: Path, workspace_id: str) -> Dict[str, Path]:
    base = workspace_context_dir(root, workspace_id)
    return {
        "summary": base / "summary.json",
        "brief": base / "brief.md",
        "board_json": base / "board.json",
        "board": base / "board.md",
        "tests_json": base / "tests.json",
        "tests": base / "tests.md",
        "knowledge_json": base / "knowledge.json",
        "knowledge": base / "knowledge.md",
        "integration_candidates_json": base / "integration_candidates.json",
        "integration_candidates": base / "integration_candidates.md",
        "handoff": base / "handoff.md",
        "mobile": base / "mobile.md",
    }


def workspace_source_paths(root: Path, workspace_id: str) -> List[Path]:
    return [
        workspace_events_path(root, workspace_id),
        workspace_activity_events_path(root, workspace_id),
        workspace_artifact_links_path(root, workspace_id),
        workspace_blockers_path(root, workspace_id),
        workspace_claims_path(root, workspace_id),
        workspace_decisions_path(root, workspace_id),
        workspace_work_item_events_path(root, workspace_id),
        workspace_test_cases_path(root, workspace_id),
        workspace_test_runs_path(root, workspace_id),
        workspace_knowledge_records_path(root, workspace_id),
        workspace_promotions_path(root, workspace_id),
    ]


def workspace_exists(root: Path, workspace_id: str) -> bool:
    return workspace_manifest_path(root, workspace_id).exists()


def workspace_ids(root: Path) -> List[str]:
    base = root / "memory" / "workspaces"
    if not base.exists():
        return []
    ids = []
    for path in sorted(base.iterdir()):
        if path.is_dir() and (path / "manifest.json").exists():
            ids.append(path.name)
    return ids


def sorted_files(path: Path, pattern: str) -> Iterable[Path]:
    return sorted(path.glob(pattern))
