from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


MODULE_ID = "adapter.workspace.workspace_client"
CONTRACT_VERSION = "1.0"
PUBLIC_API = ("MODULE_ID", "CONTRACT_VERSION", "WorkspaceClient", "WorkspaceClientError")
__all__ = list(PUBLIC_API)


class WorkspaceClientError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 0, response_body: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class WorkspaceClient:
    def __init__(self, base_url: str, *, timeout: float = 10.0) -> None:
        normalized = str(base_url or "").strip().rstrip("/")
        if not normalized:
            raise ValueError("base_url is required")
        self.base_url = normalized
        self.api_base = normalized if normalized.endswith("/api") else f"{normalized}/api"
        self.timeout = timeout

    def _request(
        self,
        workspace_id: str,
        action: str,
        *,
        method: str = "GET",
        query: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.api_base}/workspaces/{workspace_id}/{action}"
        clean_query = {key: value for key, value in dict(query or {}).items() if value not in (None, "")}
        if clean_query:
            url = f"{url}?{urlencode(clean_query)}"
        request_payload = dict(payload or {})
        idempotency_key = str(request_payload.pop("_idempotency_key", "") or "").strip()
        body = None if payload is None else json.dumps(request_payload).encode("utf-8")
        request = Request(url, data=body, method=method)
        request.add_header("Accept", "application/json")
        if body is not None:
            request.add_header("Content-Type", "application/json")
        if idempotency_key:
            request.add_header("Idempotency-Key", idempotency_key)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            try:
                message = str(json.loads(response_body).get("error", response_body))
            except json.JSONDecodeError:
                message = response_body or str(exc)
            raise WorkspaceClientError(message, status_code=exc.code, response_body=response_body) from exc
        except URLError as exc:
            raise WorkspaceClientError(f"Workspace service unavailable: {exc.reason}") from exc

    def status(self, workspace_id: str) -> dict[str, Any]:
        return self._request(workspace_id, "status")

    def catalog(self) -> dict[str, Any]:
        return self._collection_request("workspaces")

    def _collection_request(
        self,
        path: str,
        *,
        method: str = "GET",
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.api_base}/{path.lstrip('/')}"
        request_payload = dict(payload or {})
        idempotency_key = str(request_payload.pop("_idempotency_key", "") or "").strip()
        body = None if payload is None else json.dumps(request_payload).encode("utf-8")
        request = Request(url, data=body, method=method)
        request.add_header("Accept", "application/json")
        if body is not None:
            request.add_header("Content-Type", "application/json")
        if idempotency_key:
            request.add_header("Idempotency-Key", idempotency_key)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            response_body = exc.read().decode("utf-8", errors="replace")
            try:
                message = str(json.loads(response_body).get("error", response_body))
            except json.JSONDecodeError:
                message = response_body or str(exc)
            raise WorkspaceClientError(message, status_code=exc.code, response_body=response_body) from exc
        except URLError as exc:
            raise WorkspaceClientError(f"Workspace service unavailable: {exc.reason}") from exc

    def create_workspace(self, manifest: dict[str, Any], *, idempotency_key: str = "") -> dict[str, Any]:
        return self._collection_request("workspaces", method="POST", payload={"manifest": manifest, "_idempotency_key": idempotency_key})

    def import_workspace(self, snapshot: dict[str, Any], *, dry_run: bool = False, imported_from: str = "workspace-client", idempotency_key: str = "") -> dict[str, Any]:
        return self._collection_request(
            "workspaces/import",
            method="POST",
            payload={"snapshot": snapshot, "dry_run": dry_run, "imported_from": imported_from, "_idempotency_key": idempotency_key},
        )

    def archive_workspace(self, workspace_id: str, *, reason: str = "", idempotency_key: str = "") -> dict[str, Any]:
        return self._request(workspace_id, "archive", method="POST", payload={"reason": reason, "_idempotency_key": idempotency_key})

    def tasks(self, workspace_id: str) -> dict[str, Any]:
        return self._request(workspace_id, "tasks")

    def gate(self, workspace_id: str) -> dict[str, Any]:
        return self._request(workspace_id, "gate")

    def prepare(self, workspace_id: str, **query: Any) -> dict[str, Any]:
        return self._request(workspace_id, "prepare", query=query)

    def context(self, workspace_id: str, **query: Any) -> dict[str, Any]:
        return self._request(workspace_id, "context", query=query)

    def runs(self, workspace_id: str, *, task_id: str = "") -> dict[str, Any]:
        return self._request(workspace_id, "runs", query={"task_id": task_id})

    def reasoning(self, workspace_id: str, *, task_id: str = "", run_id: str = "") -> dict[str, Any]:
        return self._request(workspace_id, "reasoning", query={"task_id": task_id, "run_id": run_id})

    def progress(self, workspace_id: str, *, task_id: str) -> dict[str, Any]:
        return self._request(workspace_id, "progress", query={"task_id": task_id})

    def continuity(self, workspace_id: str, *, task_id: str = "") -> dict[str, Any]:
        return self._request(workspace_id, "continuity", query={"task_id": task_id})

    def record_reasoning(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "reasoning", method="POST", payload=payload)

    def begin_run(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "runs", method="POST", payload=payload)

    def heartbeat_run(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "run-heartbeat", method="POST", payload=payload)

    def end_run(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "run-end", method="POST", payload=payload)

    def recover_stale_runs(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "run-recover-stale", method="POST", payload=payload)

    def claim(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "claim", method="POST", payload=payload)

    def handoff(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "handoff", method="POST", payload=payload)

    def decision(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "decision", method="POST", payload=payload)

    def verify(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "verify", method="POST", payload=payload)

    def blocker(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "blocker", method="POST", payload=payload)

    def complete(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "complete", method="POST", payload=payload)

    def create_task(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "tasks", method="POST", payload=payload)

    def update_task(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "task-update", method="POST", payload=payload)

    def resolve_blocker(self, workspace_id: str, **payload: Any) -> dict[str, Any]:
        return self._request(workspace_id, "blocker-resolve", method="POST", payload=payload)
