from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

from .storage import utc_now
from .workspace_coordination import load_workspace_manifest
from .workspace_store import FileWorkspaceStore, WorkspaceStore


MODULE_ID = "service.workspace.workspace_observer"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "build_repository_snapshot",
    "latest_workspace_snapshot",
    "observe_workspace",
)
__all__ = list(PUBLIC_API)


def _git(root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ValueError(f"Unable to inspect git repository at {root}") from exc
    return result.stdout


def _path_in_roots(path: str, roots: list[str]) -> bool:
    normalized = str(path or "").strip().strip("/")
    if not normalized:
        return False
    for root in roots:
        normalized_root = str(root or "").strip().strip("/")
        if normalized_root and (normalized == normalized_root or normalized.startswith(normalized_root + "/")):
            return True
    return False


def _change_status(code: str) -> str:
    if code == "??" or "A" in code:
        return "added"
    if "R" in code:
        return "renamed"
    if "C" in code:
        return "copied"
    if "D" in code:
        return "deleted"
    if "U" in code:
        return "conflicted"
    return "modified"


def _parse_status(payload: bytes) -> list[dict[str, str]]:
    entries = payload.decode("utf-8", errors="surrogateescape").split("\0")
    changes: list[dict[str, str]] = []
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        code = entry[:2]
        path = entry[3:]
        change = {"status": _change_status(code), "path": path}
        if "R" in code or "C" in code:
            previous_path = entries[index] if index < len(entries) else ""
            index += 1
            change["previous_path"] = previous_path
        changes.append(change)
    return changes


def build_repository_snapshot(
    root: Path,
    artifact_roots: list[str],
    *,
    excluded_paths: list[str] | None = None,
) -> dict[str, Any]:
    revision = _git(root, "rev-parse", "HEAD").decode("utf-8").strip()
    parsed = _parse_status(_git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all"))
    exclusions = {str(path).strip().strip("/") for path in list(excluded_paths or []) if str(path).strip()}
    changes = [
        row
        for row in parsed
        if (
            _path_in_roots(row["path"], artifact_roots)
            or _path_in_roots(row.get("previous_path", ""), artifact_roots)
        )
        and row["path"].strip("/") not in exclusions
    ]
    changes.sort(key=lambda row: (row["path"], row["status"], row.get("previous_path", "")))
    fingerprint_payload = {"source_revision": revision, "changes": changes}
    fingerprint = hashlib.sha256(
        json.dumps(fingerprint_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": "1.0",
        "source_revision": revision,
        "changes": changes,
        "changed_files": [row["path"] for row in changes],
        "fingerprint": fingerprint,
        "observed_at": utc_now(),
    }


def latest_workspace_snapshot(
    root: Path,
    workspace_id: str,
    *,
    store: WorkspaceStore | None = None,
) -> dict[str, Any]:
    resolved_store = store or FileWorkspaceStore(root)
    rows = resolved_store.read_jsonl(resolved_store.repository_snapshots_path(workspace_id))
    return dict(rows[-1]) if rows else {}


def observe_workspace(
    root: Path,
    workspace_id: str,
    *,
    store: WorkspaceStore | None = None,
) -> dict[str, Any]:
    resolved_store = store or FileWorkspaceStore(root)
    manifest = load_workspace_manifest(root, workspace_id, store=resolved_store)
    from .workspace_atlas import materialize_workspace_atlas, workspace_atlas_paths

    projection_paths = workspace_atlas_paths(root, workspace_id, manifest=manifest, store=resolved_store)
    excluded_paths = []
    for path in projection_paths.values():
        try:
            excluded_paths.append(str(path.relative_to(root)))
        except ValueError:
            continue
    snapshot = build_repository_snapshot(
        root,
        list(manifest.get("artifact_roots", []) or []),
        excluded_paths=excluded_paths,
    )
    previous = latest_workspace_snapshot(root, workspace_id, store=resolved_store)
    recorded = snapshot["fingerprint"] != previous.get("fingerprint")
    if recorded:
        resolved_store.append_jsonl(resolved_store.repository_snapshots_path(workspace_id), snapshot)
        materialize_workspace_atlas(
            root,
            workspace_id,
            repository_snapshot=snapshot,
            store=resolved_store,
        )
    return {"workspace_id": workspace_id, "recorded": recorded, "snapshot": snapshot}
