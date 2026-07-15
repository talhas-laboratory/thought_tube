"""Workspace OS miniapp API helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from .workspace_dashboard import build_workspace_dashboard_snapshot


def workspace_os_dashboard_payload(root: Path) -> dict[str, Any]:
    return build_workspace_dashboard_snapshot(root)


def _workspace_api_base() -> str:
    return str(os.environ.get("INNER_WORLD_WORKSPACE_API_BASE", "") or "").strip().rstrip("/")


def _proxy_get(path: str, timeout: float = 8.0) -> dict[str, Any]:
    base = _workspace_api_base()
    if not base:
        return {"error": "INNER_WORLD_WORKSPACE_API_BASE not configured"}
    url = f"{base}{path}"
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except URLError as exc:
        return {"error": str(exc.reason if getattr(exc, "reason", None) else exc)}


def workspace_os_live_health() -> dict[str, Any]:
    return _proxy_get("/health")


def workspace_os_live_catalog() -> dict[str, Any]:
    return _proxy_get("/api/workspaces")


def workspace_os_live_context(workspace_id: str) -> dict[str, Any]:
    workspace_id = workspace_id.strip().strip("/")
    if not workspace_id:
        return {"error": "workspace_id required"}
    return _proxy_get(f"/api/workspaces/{workspace_id}/context")


def workspace_os_live_gate(workspace_id: str) -> dict[str, Any]:
    workspace_id = workspace_id.strip().strip("/")
    if not workspace_id:
        return {"error": "workspace_id required"}
    return _proxy_get(f"/api/workspaces/{workspace_id}/gate")
