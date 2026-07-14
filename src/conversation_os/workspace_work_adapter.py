from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List

from .workspace_client import WorkspaceClient


MODULE_ID = "adapter.workspace.workspace_work_adapter"
CONTRACT_VERSION = "1.0"
PUBLIC_API = ("MODULE_ID", "CONTRACT_VERSION", "WorkspaceWorkAdapter")
__all__ = list(PUBLIC_API)


@dataclass(frozen=True)
class WorkspaceWorkAdapter:
    """One small lifecycle contract for connected agent surfaces."""

    client: WorkspaceClient
    workspace_id: str
    agent_id: str
    device_id: str
    surface: str
    session_id: str

    def begin(
        self,
        *,
        task_id: str,
        intent: str,
        claimed_paths: List[str] | None = None,
        source_revision: str = "",
        next_action: str = "",
        idempotency_key: str = "",
    ) -> dict[str, Any]:
        run = self.client.begin_run(
            self.workspace_id,
            task_id=task_id,
            agent_id=self.agent_id,
            device_id=self.device_id,
            surface=self.surface,
            session_id=self.session_id,
            intent=intent,
            claimed_paths=list(claimed_paths or []),
            source_revision=source_revision,
            _idempotency_key=idempotency_key,
        )
        if next_action:
            self.client.record_reasoning(
                self.workspace_id,
                task_id=task_id,
                agent_id=self.agent_id,
                surface=self.surface,
                session_id=self.session_id,
                run_id=run["run_id"],
                kind="next_action",
                summary=next_action,
                rationale="Declared at the start of the agent work attempt.",
                _idempotency_key=f"{idempotency_key}:next-action" if idempotency_key else "",
            )
        return run

    def heartbeat(self, *, run_id: str, update: str = "", rationale: str = "", idempotency_key: str = "") -> dict[str, Any]:
        run = self.client.heartbeat_run(
            self.workspace_id,
            run_id=run_id,
            agent_id=self.agent_id,
            _idempotency_key=idempotency_key,
        )
        if update:
            self.client.record_reasoning(
                self.workspace_id,
                task_id=run["task_id"],
                agent_id=self.agent_id,
                surface=self.surface,
                session_id=self.session_id,
                run_id=run_id,
                kind="observation",
                summary=update,
                rationale=rationale or "Recorded during a run heartbeat.",
                _idempotency_key=f"{idempotency_key}:update" if idempotency_key else "",
            )
        return run

    def handoff(self, *, run_id: str, next_action: str, rationale: str, idempotency_key: str = "") -> dict[str, Any]:
        runs = self.client.runs(self.workspace_id)["runs"]
        run = next((row for row in runs if row.get("run_id") == run_id), None)
        if run is None:
            raise FileNotFoundError(f"Run not found: {run_id}")
        self.client.handoff(
            self.workspace_id,
            task_id=run["task_id"],
            agent_id=self.agent_id,
            surface=self.surface,
            session_id=self.session_id,
            summary="Agent work handoff.",
            reasoning=rationale,
            next_action=next_action,
            run_id=run_id,
            source_revision=run.get("source_revision", ""),
            _idempotency_key=f"{idempotency_key}:task-handoff" if idempotency_key else "",
        )
        self.client.record_reasoning(
            self.workspace_id,
            task_id=run["task_id"],
            agent_id=self.agent_id,
            surface=self.surface,
            session_id=self.session_id,
            run_id=run_id,
            kind="next_action",
            summary=next_action,
            rationale=rationale,
            _idempotency_key=f"{idempotency_key}:next-action" if idempotency_key else "",
        )
        return self.client.end_run(
            self.workspace_id,
            run_id=run_id,
            agent_id=self.agent_id,
            status="handed_off",
            reason=rationale,
            _idempotency_key=idempotency_key,
        )
