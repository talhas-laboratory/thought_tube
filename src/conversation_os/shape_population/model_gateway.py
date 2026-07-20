"""Strict model gateway for Shape population intelligence roles."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence

from conversation_os.shape_population.contracts import ValidationError
from conversation_os.shape_population.execution_context import ExecutionContext
from conversation_os.shape_population.identities import (
    CRITIC_IDENTITY,
    EVALUATOR_IDENTITY,
    PROPOSER_IDENTITY,
    SYNTHESIZER_IDENTITY,
    get_identity,
)

MODULE_ID = "kernel.shape_population.model_gateway"
CONTRACT_VERSION = "1.0.0"
DEFAULT_TIMEOUT_SECONDS = 45.0
DEFAULT_REPAIR_ATTEMPTS = 1
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "ModelClient",
    "ShapeModelGateway",
    "StubModelClient",
    "ROLE_IDENTITIES",
    "ROLE_OUTPUT_FIELDS",
)
__all__ = list(PUBLIC_API)

Message = Mapping[str, Any]

ROLE_IDENTITIES: dict[str, str] = {
    "proposer": PROPOSER_IDENTITY,
    "critic": CRITIC_IDENTITY,
    "synthesizer": SYNTHESIZER_IDENTITY,
    "evaluator": EVALUATOR_IDENTITY,
}

TRUSTED_RUNTIME_FIELDS = frozenset(
    {
        "agent_identity",
        "identity",
        "principal_id",
        "principal_kind",
        "authenticated_by",
        "capabilities",
        "run_id",
        "model_id",
        "model_version",
        "prompt_version",
        "tool_contract_version",
        "approval_identity",
        "approval_reason",
        "human_principal_id",
        "decision",
        "canonical_id",
        "canonical",
        "status",
        "candidate_id_override",
        "evaluation_id_override",
    }
)

ROLE_OUTPUT_FIELDS: dict[str, frozenset[str]] = {
    "proposer": frozenset(
        {
            "packet_id",
            "title",
            "statement",
            "boundary",
            "mechanism",
            "dimensions",
            "evidence_refs",
            "counter_hypotheses",
            "uncertainty",
            "recommended_disposition",
            "relations",
        }
    ),
    "critic": frozenset(
        {
            "candidate_id",
            "disposition",
            "critique",
            "evidence_refs",
            "uncertainty",
            "relationship_findings",
            "revisions",
        }
    ),
    "synthesizer": frozenset(
        {
            "candidate_id",
            "disposition",
            "critique",
            "evidence_refs",
            "uncertainty",
            "relationship_findings",
            "revisions",
        }
    ),
    "evaluator": frozenset(
        {
            "candidate_id",
            "evaluation_id",
            "recommendation",
            "rationale",
            "evidence_refs",
            "uncertainty",
            "rubric_scores",
        }
    ),
}


class ModelClient(Protocol):
    def complete(self, messages: Sequence[Message], *, tools: Sequence[str], timeout: float) -> str:
        ...


@dataclass
class StubModelClient:
    """Deterministic client for tests; returns queued responses in order."""

    responses: list[str]
    calls: list[dict[str, Any]] = field(default_factory=list)

    def complete(self, messages: Sequence[Message], *, tools: Sequence[str], timeout: float) -> str:
        self.calls.append(
            {
                "messages": [dict(message) for message in messages],
                "tools": list(tools),
                "timeout": timeout,
            }
        )
        if not self.responses:
            raise TimeoutError("stub response queue exhausted")
        return self.responses.pop(0)


def _role(role: str) -> str:
    normalized = str(role or "").strip().lower()
    if normalized not in ROLE_IDENTITIES:
        raise ValidationError(f"unknown Shape model role: {role}")
    return normalized


def _reject_forbidden_text(raw: str) -> None:
    stripped = raw.strip()
    if stripped.startswith("```") or stripped.endswith("```") or "```json" in stripped.lower():
        raise ValidationError("model output must not use markdown fences")
    if not stripped.startswith("{"):
        raise ValidationError("model output must be exactly one JSON object")


def _parse_one_json_object(raw: str) -> dict[str, Any]:
    _reject_forbidden_text(raw)
    decoder = json.JSONDecoder(parse_constant=lambda value: (_ for _ in ()).throw(ValidationError(f"invalid JSON constant: {value}")))
    try:
        value, end = decoder.raw_decode(raw)
    except ValidationError:
        raise
    except json.JSONDecodeError as exc:
        raise ValidationError(f"invalid JSON: {exc.msg}") from exc
    if raw[end:].strip():
        raise ValidationError("model output must contain exactly one JSON object")
    if not isinstance(value, dict):
        raise ValidationError("model output must be a JSON object")
    _reject_non_finite(value)
    return value


def _reject_non_finite(value: Any) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise ValidationError("model output contains non-finite number")
    if isinstance(value, Mapping):
        for item in value.values():
            _reject_non_finite(item)
    elif isinstance(value, list):
        for item in value:
            _reject_non_finite(item)


def _validate_fields(role: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    allowed = ROLE_OUTPUT_FIELDS[role]
    unknown = sorted(set(payload) - allowed)
    if unknown:
        if TRUSTED_RUNTIME_FIELDS.intersection(unknown):
            raise ValidationError(f"model output attempted to set trusted fields: {', '.join(unknown)}")
        raise ValidationError(f"model output contains unknown fields: {', '.join(unknown)}")
    if TRUSTED_RUNTIME_FIELDS.intersection(payload):
        raise ValidationError("model output attempted to set trusted runtime fields")
    return dict(payload)


def _evidence_blocks(evidence_packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for block in evidence_packet.get("blocks") or []:
        if not isinstance(block, Mapping):
            continue
        retained = {
            key: block.get(key)
            for key in (
                "packet_id",
                "block_id",
                "source_id",
                "segment_id",
                "char_start",
                "char_end",
                "text_sha256",
                "instruction_authority",
                "text",
            )
            if key in block
        }
        retained.setdefault("packet_id", evidence_packet.get("packet_id"))
        retained["instruction_authority"] = False
        blocks.append(retained)
    return blocks


class ShapeModelGateway:
    """Shape-specific adapter around a model transport."""

    def __init__(
        self,
        client: ModelClient,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        repair_attempts: int = DEFAULT_REPAIR_ATTEMPTS,
        prompt_version: str = CONTRACT_VERSION,
    ):
        if repair_attempts < 0:
            raise ValidationError("repair_attempts must be non-negative")
        self.client = client
        self.timeout = float(timeout)
        self.repair_attempts = int(repair_attempts)
        self.prompt_version = prompt_version

    def allowed_tools_for_role(self, role: str) -> list[str]:
        identity = get_identity(ROLE_IDENTITIES[_role(role)])
        return sorted(identity.allowed_tools)

    def build_messages(
        self,
        role: str,
        *,
        evidence_packet: Mapping[str, Any] | None = None,
        context: ExecutionContext,
        task: str = "",
        prior: Mapping[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        normalized_role = _role(role)
        identity = get_identity(ROLE_IDENTITIES[normalized_role])
        system = {
            "role": "system",
            "content": (
                f"You are {identity.identity_id}, the Shape population {normalized_role}. "
                "Return exactly one JSON object matching the declared schema. "
                "Do not include markdown fences, prose, tool calls, identity metadata, run metadata, approvals, or canonical claims."
            ),
        }
        developer = {
            "role": "developer",
            "content": json.dumps(
                {
                    "contract_version": CONTRACT_VERSION,
                    "prompt_version": self.prompt_version,
                    "role": normalized_role,
                    "allowed_output_fields": sorted(ROLE_OUTPUT_FIELDS[normalized_role]),
                    "allowed_tools": sorted(identity.allowed_tools),
                    "trusted_context": {
                        "principal_id": context.principal_id,
                        "run_id": context.run_id,
                        "model_id": context.model_id,
                        "prompt_version": context.prompt_version,
                    },
                },
                sort_keys=True,
            ),
        }
        data = {
            "role": "user",
            "content": json.dumps(
                {
                    "task": task,
                    "SOURCE_DATA_BLOCKS": _evidence_blocks(evidence_packet or {}),
                    "prior_artifacts": dict(prior or {}),
                    "source_data_instruction_authority": False,
                },
                sort_keys=True,
                ensure_ascii=False,
            ),
        }
        return [system, developer, data]

    def invoke(
        self,
        role: str,
        *,
        evidence_packet: Mapping[str, Any] | None = None,
        context: ExecutionContext,
        task: str = "",
        prior: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_role = _role(role)
        messages = self.build_messages(
            normalized_role,
            evidence_packet=evidence_packet,
            context=context,
            task=task,
            prior=prior,
        )
        tools = self.allowed_tools_for_role(normalized_role)
        last_error = ""
        for attempt in range(self.repair_attempts + 1):
            attempt_messages = list(messages)
            if attempt and last_error:
                attempt_messages.append(
                    {
                        "role": "developer",
                        "content": json.dumps(
                            {
                                "repair": True,
                                "validation_error": last_error,
                                "instruction": "Return exactly one corrected JSON object and nothing else.",
                            },
                            sort_keys=True,
                        ),
                    }
                )
            try:
                raw = self.client.complete(attempt_messages, tools=tools, timeout=self.timeout)
                return _validate_fields(normalized_role, _parse_one_json_object(raw))
            except (TimeoutError, ValidationError, json.JSONDecodeError) as exc:
                last_error = str(exc)
                if attempt >= self.repair_attempts:
                    raise ValidationError(f"model gateway failed after {attempt + 1} attempt(s): {last_error}") from exc
        raise ValidationError("model gateway failed")

    def propose(self, *, evidence_packet: Mapping[str, Any], context: ExecutionContext, task: str = "") -> dict[str, Any]:
        return self.invoke("proposer", evidence_packet=evidence_packet, context=context, task=task)

    def critique(
        self,
        *,
        evidence_packet: Mapping[str, Any],
        context: ExecutionContext,
        candidate: Mapping[str, Any],
        comparisons: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self.invoke(
            "critic",
            evidence_packet=evidence_packet,
            context=context,
            task="Critique the candidate using packet evidence and comparison provenance.",
            prior={"candidate": dict(candidate), "comparisons": dict(comparisons)},
        )

    def synthesize(
        self,
        *,
        evidence_packet: Mapping[str, Any],
        context: ExecutionContext,
        candidate: Mapping[str, Any],
        critique: Mapping[str, Any],
        comparisons: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self.invoke(
            "synthesizer",
            evidence_packet=evidence_packet,
            context=context,
            task="Synthesize without erasing uncertainty or dissent.",
            prior={"candidate": dict(candidate), "critique": dict(critique), "comparisons": dict(comparisons)},
        )

    def evaluate(
        self,
        *,
        evidence_packet: Mapping[str, Any],
        context: ExecutionContext,
        candidate: Mapping[str, Any],
        evaluation: Mapping[str, Any],
    ) -> dict[str, Any]:
        return self.invoke(
            "evaluator",
            evidence_packet=evidence_packet,
            context=context,
            task="Recommend promotion only when the candidate is promotion-ready.",
            prior={"candidate": dict(candidate), "evaluation": dict(evaluation)},
        )
