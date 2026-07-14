from __future__ import annotations

import json
import os
import threading
import uuid
from hashlib import sha256
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from .workspace_coordination import (
    WorkspaceCompletionError,
    claim_workspace_task,
    complete_workspace_task,
    create_workspace_task,
    evaluate_workspace_release_gate,
    prepare_workspace_task,
    record_workspace_blocker,
    record_workspace_decision,
    record_workspace_test_run,
    release_workspace_task_claims,
    resolve_workspace_blocker,
    render_workspace_status,
    render_workspace_tasks,
    update_workspace_task,
)
from .workspace_store import FileWorkspaceStore, WorkspaceStore
from .workspace_store import SQLiteWorkspaceStore
from .workspace_context_packet import assemble_workspace_context_packet
from .workspace_catalog import archive_workspace, create_workspace, import_workspace_snapshot, workspace_catalog
from .workspace_recovery import backup_workspace_database
from .storage import read_json, write_json
from .workspace_runs import begin_workspace_run, end_workspace_run, heartbeat_workspace_run, list_workspace_runs, recover_stale_workspace_runs
from .workspace_reasoning import list_workspace_reasoning, record_workspace_reasoning
from .workspace_progress import derive_workspace_task_progress
from .workspace_continuity import assemble_workspace_continuity_export
from .workspace_observer import observe_workspace
from .workspace_health import workspace_health


MODULE_ID = "service.workspace.workspace_service"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "serve_workspace_service",
)
__all__ = list(PUBLIC_API)


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    payload = handler.rfile.read(length)
    if not payload:
        return {}
    return json.loads(payload.decode("utf-8"))


def _query_value(query: dict[str, list[str]], key: str, default: str = "") -> str:
    return str((query.get(key) or [default])[0] or default)


def _write_json(handler: BaseHTTPRequestHandler, status: int, payload: dict[str, Any]) -> None:
    context = getattr(handler, "_idempotency_context", None)
    if context is not None and 200 <= int(status) < 300:
        with context["lock"]:
            registry = read_json(context["path"], default={}) or {}
            registry[context["key"]] = {
                "workspace_id": context["workspace_id"],
                "action": context["action"],
                "payload_hash": context["payload_hash"],
                "status": int(status),
                "response": payload,
            }
            write_json(context["path"], registry)
        delattr(handler, "_idempotency_context")
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def serve_workspace_service(
    *,
    root: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    store: WorkspaceStore | None = None,
    start: bool = True,
) -> ThreadingHTTPServer:
    workspace_root = root.resolve()
    workspace_store = store or FileWorkspaceStore(workspace_root)
    idempotency_lock = threading.Lock()
    observation_lock = threading.Lock()
    idempotency_path = workspace_root / "state" / "workspace_idempotency.json"

    def refresh_repository_observation(workspace_id: str) -> None:
        """Refresh the repository projection before serving revision-sensitive state.

        The workspace service may also be used against a non-git fixture or a
        read-only export. In those environments observation is best-effort and
        the existing unobserved state remains available to callers.
        """

        with observation_lock:
            try:
                observe_workspace(
                    workspace_root,
                    workspace_id,
                    store=workspace_store,
                    source_revision_override=os.environ.get("INNER_SPACE_REPOSITORY_SOURCE_REVISION", ""),
                )
            except (FileNotFoundError, OSError, ValueError):
                return

    class WorkspaceHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                _write_json(self, HTTPStatus.OK, {"status": "ok"})
                return
            if parsed.path == "/ready":
                try:
                    readiness = workspace_store.readiness()
                except Exception as exc:  # Readiness must convert store failures into a stable HTTP signal.
                    _write_json(self, HTTPStatus.SERVICE_UNAVAILABLE, {"status": "not_ready", "error": str(exc)})
                    return
                _write_json(self, HTTPStatus.OK, readiness)
                return
            if parsed.path == "/api/workspaces":
                _write_json(self, HTTPStatus.OK, workspace_catalog(workspace_store))
                return
            path_parts = [part for part in parsed.path.split("/") if part]
            query = parse_qs(parsed.query, keep_blank_values=True)
            if len(path_parts) < 4 or path_parts[:2] != ["api", "workspaces"]:
                _write_json(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            workspace_id = path_parts[2]
            action = path_parts[3]
            try:
                if action == "prepare":
                    payload = prepare_workspace_task(
                        workspace_root,
                        workspace_id,
                        task_id=_query_value(query, "task_id"),
                        agent_id=_query_value(query, "agent_id"),
                        surface=_query_value(query, "surface"),
                        session_id=_query_value(query, "session_id"),
                        store=workspace_store,
                    )
                    _write_json(self, HTTPStatus.OK, payload)
                    return
                if action == "context":
                    refresh_repository_observation(workspace_id)
                    payload = assemble_workspace_context_packet(
                        workspace_root,
                        workspace_id,
                        task_id=_query_value(query, "task_id"),
                        agent_id=_query_value(query, "agent_id"),
                        surface=_query_value(query, "surface"),
                        session_id=_query_value(query, "session_id"),
                        store=workspace_store,
                    )
                    _write_json(self, HTTPStatus.OK, payload)
                    return
                if action == "gate":
                    refresh_repository_observation(workspace_id)
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        evaluate_workspace_release_gate(workspace_root, workspace_id, store=workspace_store),
                    )
                    return
                if action == "status":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        {"workspace_id": workspace_id, "text": render_workspace_status(workspace_root, workspace_id, store=workspace_store)},
                    )
                    return
                if action == "tasks":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        {"workspace_id": workspace_id, "text": render_workspace_tasks(workspace_root, workspace_id, store=workspace_store)},
                    )
                    return
                if action == "runs":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        {"workspace_id": workspace_id, "runs": list_workspace_runs(workspace_root, workspace_id, task_id=_query_value(query, "task_id"), store=workspace_store)},
                    )
                    return
                if action == "reasoning":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        {"workspace_id": workspace_id, "reasoning": list_workspace_reasoning(workspace_root, workspace_id, task_id=_query_value(query, "task_id"), run_id=_query_value(query, "run_id"), store=workspace_store)},
                    )
                    return
                if action == "progress":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        derive_workspace_task_progress(workspace_root, workspace_id, task_id=_query_value(query, "task_id"), store=workspace_store),
                    )
                    return
                if action == "continuity":
                    refresh_repository_observation(workspace_id)
                    _write_json(self, HTTPStatus.OK, assemble_workspace_continuity_export(workspace_root, workspace_id, task_id=_query_value(query, "task_id"), store=workspace_store))
                    return
                if action == "health":
                    refresh_repository_observation(workspace_id)
                    _write_json(self, HTTPStatus.OK, workspace_health(workspace_root, workspace_id, store=workspace_store))
                    return
            except FileNotFoundError as exc:
                _write_json(self, HTTPStatus.NOT_FOUND, {"error": str(exc)})
                return
            _write_json(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path_parts = [part for part in parsed.path.split("/") if part]
            payload = _read_json_body(self)
            request_key = str(self.headers.get("Idempotency-Key", "") or "").strip()
            if request_key:
                if parsed.path == "/api/workspaces":
                    workspace_id_for_key = str((payload.get("manifest", {}) or payload).get("workspace_id", "") or "").strip()
                    action_for_key = "create"
                elif parsed.path == "/api/workspaces/import":
                    workspace_id_for_key = str((payload.get("snapshot", {}) or {}).get("workspace_id", "") or "").strip()
                    action_for_key = "import"
                else:
                    workspace_id_for_key = path_parts[2] if len(path_parts) >= 3 else ""
                    action_for_key = path_parts[3] if len(path_parts) >= 4 else ""
                if not workspace_id_for_key or not action_for_key:
                    _write_json(self, HTTPStatus.BAD_REQUEST, {"error": "Idempotency-Key requires a workspace operation"})
                    return
                payload_hash = sha256(
                    json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest()
                with idempotency_lock:
                    registry = read_json(idempotency_path, default={}) or {}
                    existing = dict(registry.get(request_key, {}) or {})
                if existing:
                    if (
                        existing.get("workspace_id") != workspace_id_for_key
                        or existing.get("action") != action_for_key
                        or existing.get("payload_hash") != payload_hash
                    ):
                        _write_json(self, HTTPStatus.CONFLICT, {"error": "Idempotency-Key was already used for a different request"})
                        return
                    _write_json(self, HTTPStatus(existing.get("status", HTTPStatus.OK)), dict(existing.get("response", {}) or {}))
                    return
                self._idempotency_context = {
                    "key": request_key,
                    "workspace_id": workspace_id_for_key,
                    "action": action_for_key,
                    "payload_hash": payload_hash,
                    "path": idempotency_path,
                    "lock": idempotency_lock,
                }
            if parsed.path == "/api/workspaces":
                try:
                    _write_json(
                        self,
                        HTTPStatus.CREATED,
                        create_workspace(workspace_store, dict(payload.get("manifest", {}) or payload)),
                    )
                except ValueError as exc:
                    _write_json(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            if parsed.path == "/api/workspaces/import":
                try:
                    snapshot = dict(payload.get("snapshot", {}) or {})
                    dry_run = bool(payload.get("dry_run", False))
                    preview = import_workspace_snapshot(
                        workspace_store,
                        snapshot,
                        dry_run=True,
                        imported_from=str(payload.get("imported_from", "service-client") or "service-client"),
                    )
                    if dry_run or preview["status"] != "planned":
                        _write_json(self, HTTPStatus.OK, preview)
                        return
                    backup = ""
                    if isinstance(workspace_store, SQLiteWorkspaceStore) and workspace_store.workspace_ids():
                        backup_path = (
                            workspace_root
                            / "state"
                            / "workspace-import-backups"
                            / f"workspace-before-import-{uuid.uuid4().hex}.db"
                        )
                        backup = backup_workspace_database(workspace_store.database_path, backup_path)["backup"]
                    result = import_workspace_snapshot(
                        workspace_store,
                        snapshot,
                        imported_from=str(payload.get("imported_from", "service-client") or "service-client"),
                    )
                    result["target_backup"] = backup
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        result,
                    )
                except (FileNotFoundError, ValueError) as exc:
                    _write_json(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            if len(path_parts) < 4 or path_parts[:2] != ["api", "workspaces"]:
                _write_json(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            workspace_id = path_parts[2]
            action = path_parts[3]
            try:
                if action == "archive":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        archive_workspace(workspace_store, workspace_id, reason=str(payload.get("reason", "") or "")),
                    )
                    return
                if action == "runs":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        begin_workspace_run(
                            workspace_root,
                            workspace_id,
                            task_id=str(payload.get("task_id", "") or ""),
                            agent_id=str(payload.get("agent_id", "") or ""),
                            device_id=str(payload.get("device_id", "") or ""),
                            surface=str(payload.get("surface", "") or ""),
                            session_id=str(payload.get("session_id", "") or ""),
                            intent=str(payload.get("intent", "") or ""),
                            source_revision=str(payload.get("source_revision", "") or ""),
                            heartbeat_ttl_seconds=int(payload.get("heartbeat_ttl_seconds", 900) or 900),
                            run_id=str(payload.get("run_id", "") or ""),
                            claimed_paths=[str(item).strip() for item in list(payload.get("claimed_paths", []) or []) if str(item).strip()],
                            store=workspace_store,
                        ),
                    )
                    return
                if action == "run-heartbeat":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        heartbeat_workspace_run(
                            workspace_root,
                            workspace_id,
                            run_id=str(payload.get("run_id", "") or ""),
                            agent_id=str(payload.get("agent_id", "") or ""),
                            store=workspace_store,
                        ),
                    )
                    return
                if action == "run-end":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        end_workspace_run(
                            workspace_root,
                            workspace_id,
                            run_id=str(payload.get("run_id", "") or ""),
                            agent_id=str(payload.get("agent_id", "") or ""),
                            status=str(payload.get("status", "") or ""),
                            reason=str(payload.get("reason", "") or ""),
                            store=workspace_store,
                        ),
                    )
                    return
                if action == "run-recover-stale":
                    _write_json(self, HTTPStatus.OK, {"workspace_id": workspace_id, "recovered": recover_stale_workspace_runs(workspace_root, workspace_id, store=workspace_store)})
                    return
                if action == "reasoning":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        record_workspace_reasoning(
                            workspace_root,
                            workspace_id,
                            task_id=str(payload.get("task_id", "") or ""),
                            agent_id=str(payload.get("agent_id", "") or ""),
                            surface=str(payload.get("surface", "") or ""),
                            session_id=str(payload.get("session_id", "") or ""),
                            kind=str(payload.get("kind", "") or ""),
                            summary=str(payload.get("summary", "") or ""),
                            rationale=str(payload.get("rationale", "") or ""),
                            run_id=str(payload.get("run_id", "") or ""),
                            source_refs=list(payload.get("source_refs", []) or []),
                            confidence=payload.get("confidence"),
                            store=workspace_store,
                        ),
                    )
                    return
                if action == "claim":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        claim_workspace_task(
                            workspace_root,
                            workspace_id,
                            task_id=str(payload.get("task_id", "") or ""),
                            agent_id=str(payload.get("agent_id", "") or ""),
                            surface=str(payload.get("surface", "") or ""),
                            session_id=str(payload.get("session_id", "") or ""),
                            intent=str(payload.get("intent", "") or ""),
                            claimed_paths=[str(item).strip() for item in list(payload.get("claimed_paths", []) or []) if str(item).strip()],
                            ttl_seconds=int(payload.get("ttl_seconds", 3600) or 3600),
                            override=bool(payload.get("override", False)),
                            run_id=str(payload.get("run_id", "") or ""),
                            store=workspace_store,
                        ),
                    )
                    return
                if action == "tasks":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        create_workspace_task(
                            workspace_root,
                            workspace_id,
                            task_id=str(payload.get("task_id", "") or ""),
                            agent_id=str(payload.get("agent_id", "") or ""),
                            surface=str(payload.get("surface", "") or ""),
                            session_id=str(payload.get("session_id", "") or ""),
                            title=str(payload.get("title", "") or ""),
                            reasoning=str(payload.get("reasoning", "") or ""),
                            status=str(payload.get("status", "backlog") or "backlog"),
                            priority=str(payload.get("priority", "medium") or "medium"),
                            owner=str(payload.get("owner", "") or ""),
                            acceptance_criteria=list(payload.get("acceptance_criteria", []) or []),
                            constraints=list(payload.get("constraints", []) or []),
                            depends_on=list(payload.get("depends_on", []) or []),
                            linked_artifacts=list(payload.get("linked_artifacts", []) or []),
                            source_refs=list(payload.get("source_refs", []) or []),
                            parent_task_id=str(payload.get("parent_task_id", "") or ""),
                            store=workspace_store,
                        ),
                    )
                    return
                if action == "task-update":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        update_workspace_task(
                            workspace_root,
                            workspace_id,
                            task_id=str(payload.get("task_id", "") or ""),
                            agent_id=str(payload.get("agent_id", "") or ""),
                            surface=str(payload.get("surface", "") or ""),
                            session_id=str(payload.get("session_id", "") or ""),
                            reasoning=str(payload.get("reasoning", "") or ""),
                            status=payload.get("status"),
                            owner=payload.get("owner"),
                            priority=payload.get("priority"),
                            acceptance_criteria=payload.get("acceptance_criteria"),
                            constraints=payload.get("constraints"),
                            depends_on=payload.get("depends_on"),
                            linked_artifacts=payload.get("linked_artifacts"),
                            source_refs=payload.get("source_refs"),
                            parent_task_id=payload.get("parent_task_id"),
                            store=workspace_store,
                        ),
                    )
                    return
                if action == "handoff":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        release_workspace_task_claims(
                            workspace_root,
                            workspace_id,
                            task_id=str(payload.get("task_id", "") or ""),
                            agent_id=str(payload.get("agent_id", "") or ""),
                            surface=str(payload.get("surface", "") or ""),
                            session_id=str(payload.get("session_id", "") or ""),
                            summary=str(payload.get("summary", "") or ""),
                            reasoning=str(payload.get("reasoning", "") or ""),
                            next_action=str(payload.get("next_action", "") or ""),
                            run_id=str(payload.get("run_id", "") or ""),
                            source_revision=str(payload.get("source_revision", "") or ""),
                            store=workspace_store,
                        ),
                    )
                    return
                if action == "decision":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        record_workspace_decision(
                            workspace_root,
                            workspace_id,
                            task_id=str(payload.get("task_id", "") or ""),
                            agent_id=str(payload.get("agent_id", "") or ""),
                            surface=str(payload.get("surface", "") or ""),
                            session_id=str(payload.get("session_id", "") or ""),
                            summary=str(payload.get("summary", "") or ""),
                            reasoning=str(payload.get("reasoning", "") or ""),
                            store=workspace_store,
                        ),
                    )
                    return
                if action == "verify":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        record_workspace_test_run(
                            workspace_root,
                            workspace_id,
                            task_id=str(payload.get("task_id", "") or ""),
                            agent_id=str(payload.get("agent_id", "") or ""),
                            surface=str(payload.get("surface", "") or ""),
                            session_id=str(payload.get("session_id", "") or ""),
                            test_name=str(payload.get("test_name", "") or ""),
                            result=str(payload.get("result", "") or ""),
                            evidence_ref=str(payload.get("evidence_ref", "") or ""),
                            notes=str(payload.get("notes", "") or ""),
                            command_or_protocol=str(payload.get("command_or_protocol", "") or ""),
                            store=workspace_store,
                        ),
                    )
                    return
                if action == "blocker":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        record_workspace_blocker(
                            workspace_root,
                            workspace_id,
                            task_id=str(payload.get("task_id", "") or ""),
                            agent_id=str(payload.get("agent_id", "") or ""),
                            surface=str(payload.get("surface", "") or ""),
                            session_id=str(payload.get("session_id", "") or ""),
                            reason=str(payload.get("reason", "") or ""),
                            next_action=str(payload.get("next_action", "") or ""),
                            store=workspace_store,
                        ),
                    )
                    return
                if action == "blocker-resolve":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        resolve_workspace_blocker(
                            workspace_root,
                            workspace_id,
                            blocker_id=str(payload.get("blocker_id", "") or ""),
                            agent_id=str(payload.get("agent_id", "") or ""),
                            surface=str(payload.get("surface", "") or ""),
                            session_id=str(payload.get("session_id", "") or ""),
                            reasoning=str(payload.get("reasoning", "") or ""),
                            store=workspace_store,
                        ),
                    )
                    return
                if action == "complete":
                    _write_json(
                        self,
                        HTTPStatus.OK,
                        complete_workspace_task(
                            workspace_root,
                            workspace_id,
                            task_id=str(payload.get("task_id", "") or ""),
                            agent_id=str(payload.get("agent_id", "") or ""),
                            surface=str(payload.get("surface", "") or ""),
                            session_id=str(payload.get("session_id", "") or ""),
                            summary=str(payload.get("summary", "") or ""),
                            reasoning=str(payload.get("reasoning", "") or ""),
                            files_touched=[str(item).strip() for item in list(payload.get("files_touched", []) or []) if str(item).strip()],
                            commands_run=[str(item).strip() for item in list(payload.get("commands_run", []) or []) if str(item).strip()],
                            residual_risks=[str(item).strip() for item in list(payload.get("residual_risks", []) or []) if str(item).strip()],
                            store=workspace_store,
                        ),
                    )
                    return
            except FileNotFoundError as exc:
                _write_json(self, HTTPStatus.NOT_FOUND, {"error": str(exc)})
                return
            except WorkspaceCompletionError as exc:
                _write_json(
                    self,
                    HTTPStatus.BAD_REQUEST,
                    {"error": "completion_gate_failed", "message": str(exc), "missing": exc.missing},
                )
                return
            except ValueError as exc:
                _write_json(self, HTTPStatus.BAD_REQUEST, {"error": str(exc)})
                return
            _write_json(self, HTTPStatus.NOT_FOUND, {"error": "not_found"})

    server = ThreadingHTTPServer((host, port), WorkspaceHandler)
    if start:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
    return server
