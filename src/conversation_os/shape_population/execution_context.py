"""Trusted execution context for Shape Population tools and services."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable

from conversation_os.shape_population.contracts import AuthorizationError
from conversation_os.storage import make_id, utc_now

MODULE_ID = "kernel.shape_population.execution_context"
CONTRACT_VERSION = "1.0.0"

CAP_EVIDENCE_INQUIRE = "shape.evidence.inquire"
CAP_CANDIDATE_SUBMIT = "shape.candidate.submit"
CAP_COMPARISON_READ = "shape.comparison.read"
CAP_EVALUATION_SUBMIT = "shape.evaluation.submit"
CAP_PROMOTION_REQUEST = "shape.promotion.request"
CAP_PROMOTION_APPROVE = "shape.promotion.approve"
CAP_PROMOTION_APPLY = "shape.promotion.apply"
CAP_PROMOTION_ROLLBACK = "shape.promotion.rollback"

SHAPE_CAPABILITIES = frozenset(
    {
        CAP_EVIDENCE_INQUIRE,
        CAP_CANDIDATE_SUBMIT,
        CAP_COMPARISON_READ,
        CAP_EVALUATION_SUBMIT,
        CAP_PROMOTION_REQUEST,
        CAP_PROMOTION_APPROVE,
        CAP_PROMOTION_APPLY,
        CAP_PROMOTION_ROLLBACK,
    }
)
AGENT_CAPABILITIES = frozenset(
    {
        CAP_EVIDENCE_INQUIRE,
        CAP_CANDIDATE_SUBMIT,
        CAP_COMPARISON_READ,
        CAP_EVALUATION_SUBMIT,
    }
)
HUMAN_REVIEW_CAPABILITIES = frozenset({CAP_PROMOTION_APPROVE})
SERVICE_CAPABILITIES = frozenset(
    {
        CAP_EVIDENCE_INQUIRE,
        CAP_COMPARISON_READ,
        CAP_PROMOTION_APPLY,
        CAP_PROMOTION_ROLLBACK,
    }
)

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "CAP_EVIDENCE_INQUIRE",
    "CAP_CANDIDATE_SUBMIT",
    "CAP_COMPARISON_READ",
    "CAP_EVALUATION_SUBMIT",
    "CAP_PROMOTION_REQUEST",
    "CAP_PROMOTION_APPROVE",
    "CAP_PROMOTION_APPLY",
    "CAP_PROMOTION_ROLLBACK",
    "SHAPE_CAPABILITIES",
    "AGENT_CAPABILITIES",
    "HUMAN_REVIEW_CAPABILITIES",
    "SERVICE_CAPABILITIES",
    "ExecutionContext",
    "require_capability",
    "agent_context",
    "human_context",
    "service_context",
)
__all__ = list(PUBLIC_API)


@dataclass(frozen=True)
class ExecutionContext:
    principal_id: str
    principal_kind: str
    authenticated_by: str
    capabilities: frozenset[str] = field(default_factory=frozenset)
    correlation_id: str = ""
    run_id: str = ""
    model_id: str = ""
    prompt_version: str = ""
    tool_contract_version: str = CONTRACT_VERSION
    issued_at: str = ""
    deadline_at: str = ""

    def __post_init__(self) -> None:
        if self.principal_kind not in {"service", "agent", "human"}:
            raise AuthorizationError("principal_kind must be service, agent, or human")
        if not self.correlation_id:
            object.__setattr__(self, "correlation_id", make_id("corr"))
        if not self.issued_at:
            object.__setattr__(self, "issued_at", utc_now())
        if not self.deadline_at:
            object.__setattr__(self, "deadline_at", "9999-12-31T23:59:59+00:00")
        for field_name in ("principal_id", "authenticated_by", "tool_contract_version"):
            if not str(getattr(self, field_name) or "").strip():
                raise AuthorizationError(f"execution context missing {field_name}")
        object.__setattr__(self, "capabilities", frozenset(self.capabilities))
        unknown = self.capabilities - SHAPE_CAPABILITIES
        if unknown:
            raise AuthorizationError(f"unknown Shape capability: {sorted(unknown)[0]}")

    def with_capabilities(self, capabilities: Iterable[str]) -> "ExecutionContext":
        return replace(self, capabilities=frozenset(capabilities))

    def require_capability(self, capability: str) -> None:
        require_capability(self, capability)


def require_capability(ctx: ExecutionContext, cap: str) -> None:
    if cap not in ctx.capabilities:
        raise AuthorizationError(f"{ctx.principal_id} lacks capability {cap}")


def _context(
    *,
    principal_id: str,
    principal_kind: str,
    authenticated_by: str,
    capabilities: Iterable[str],
    correlation_id: str = "",
    run_id: str = "",
    model_id: str = "",
    prompt_version: str = "",
    tool_contract_version: str = CONTRACT_VERSION,
    issued_at: str = "",
    deadline_at: str = "",
) -> ExecutionContext:
    return ExecutionContext(
        principal_id=principal_id,
        principal_kind=principal_kind,
        authenticated_by=authenticated_by,
        capabilities=frozenset(capabilities),
        correlation_id=correlation_id or make_id("corr"),
        run_id=run_id,
        model_id=model_id,
        prompt_version=prompt_version,
        tool_contract_version=tool_contract_version,
        issued_at=issued_at or utc_now(),
        deadline_at=deadline_at or "9999-12-31T23:59:59+00:00",
    )


def agent_context(
    principal_id: str = "shape.agent",
    *,
    capabilities: Iterable[str] = AGENT_CAPABILITIES,
    authenticated_by: str = "openclaw",
    correlation_id: str = "",
    run_id: str = "",
    model_id: str = "test-model",
    prompt_version: str = "test-prompt",
    tool_contract_version: str = CONTRACT_VERSION,
    issued_at: str = "",
    deadline_at: str = "",
) -> ExecutionContext:
    return _context(
        principal_id=principal_id,
        principal_kind="agent",
        authenticated_by=authenticated_by,
        capabilities=capabilities,
        correlation_id=correlation_id,
        run_id=run_id or make_id("run"),
        model_id=model_id,
        prompt_version=prompt_version,
        tool_contract_version=tool_contract_version,
        issued_at=issued_at,
        deadline_at=deadline_at,
    )


def human_context(
    principal_id: str = "human.reviewer",
    *,
    capabilities: Iterable[str] = HUMAN_REVIEW_CAPABILITIES,
    authenticated_by: str = "session",
    correlation_id: str = "",
    tool_contract_version: str = CONTRACT_VERSION,
    issued_at: str = "",
    deadline_at: str = "",
) -> ExecutionContext:
    return _context(
        principal_id=principal_id,
        principal_kind="human",
        authenticated_by=authenticated_by,
        capabilities=capabilities,
        correlation_id=correlation_id,
        tool_contract_version=tool_contract_version,
        issued_at=issued_at,
        deadline_at=deadline_at,
    )


def service_context(
    principal_id: str = "shape.service",
    *,
    capabilities: Iterable[str] = SERVICE_CAPABILITIES,
    authenticated_by: str = "service-token",
    correlation_id: str = "",
    run_id: str = "",
    tool_contract_version: str = CONTRACT_VERSION,
    issued_at: str = "",
    deadline_at: str = "",
) -> ExecutionContext:
    return _context(
        principal_id=principal_id,
        principal_kind="service",
        authenticated_by=authenticated_by,
        capabilities=capabilities,
        correlation_id=correlation_id,
        run_id=run_id,
        tool_contract_version=tool_contract_version,
        issued_at=issued_at,
        deadline_at=deadline_at,
    )
