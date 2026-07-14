from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .workspace_catalog import workspace_catalog
from .workspace_coordination import list_workspace_blockers, list_workspace_tasks, list_workspace_tests
from .workspace_runs import list_workspace_runs
from .workspace_store import FileWorkspaceStore, WorkspaceStore


def workspace_health(root: Path, workspace_id: str, *, store: WorkspaceStore | None = None) -> dict[str, Any]:
    store = store or FileWorkspaceStore(root)
    revision = next((row["revision"] for row in workspace_catalog(store)["workspaces"] if row["workspace_id"] == workspace_id), "")
    warnings: list[dict[str, str]] = []
    for run in list_workspace_runs(root, workspace_id, store=store):
        if run.get("status") == "stale": warnings.append({"code":"stale_run", "remediation":"Recover stale runs to release linked claims."})
    if list_workspace_blockers(root, workspace_id, limit=100, store=store): warnings.append({"code":"active_blocker", "remediation":"Resolve or explicitly hand off active blockers."})
    for task in list_workspace_tasks(root, workspace_id, limit=1000, store=store):
        if task.get("status") == "done" and not any(t.get("latest_result") == "passing" for t in list_workspace_tests(root, workspace_id, task_id=task.get("task_id", ""), limit=50, store=store)):
            warnings.append({"code":"unverified_completion", "remediation":"Record passing verification evidence for completed task."}); break
    path = root / "docs" / "workspaces" / workspace_id / "CONTINUITY.md"
    marker = re.search(r"canonical_revision: ([^\n ]+)", path.read_text(encoding="utf-8")) if path.exists() else None
    if not marker or marker.group(1) != revision: warnings.append({"code":"stale_export", "remediation":"Republish the continuity export."})
    return {"workspace_id":workspace_id,"revision":revision,"healthy":not warnings,"warnings":warnings}
