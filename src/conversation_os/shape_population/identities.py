"""Least-privilege OpenClaw Shape population identity contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict, FrozenSet, Mapping

from conversation_os.shape_population.contracts import (
    POPULATION_AGENT_TOOLS,
    PRIVILEGED_PROMOTION_OPS,
    AuthorizationError,
)

MODULE_ID = "kernel.shape_population.identities"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "PROPOSER_IDENTITY",
    "CRITIC_IDENTITY",
    "SYNTHESIZER_IDENTITY",
    "EVALUATOR_IDENTITY",
    "HUMAN_APPROVER_ROLE",
    "CANONICAL_AUTHORITY_ROLE",
    "IdentityContract",
    "get_identity",
    "assert_tool_allowed",
    "population_tool_surface",
)
__all__ = list(PUBLIC_API)

PROPOSER_IDENTITY = "shape.proposer"
CRITIC_IDENTITY = "shape.critic"
SYNTHESIZER_IDENTITY = "shape.synthesizer"
EVALUATOR_IDENTITY = "shape.evaluator"
HUMAN_APPROVER_ROLE = "shape.human_approver"
CANONICAL_AUTHORITY_ROLE = "shape.canonical_authority"


@dataclass(frozen=True)
class IdentityContract:
    identity_id: str
    role: str
    allowed_tools: FrozenSet[str]
    model_policy: str
    structured_output_required: bool = True
    broad_filesystem: bool = False
    broad_shell: bool = False
    broad_network: bool = False
    registry_write: bool = False
    can_promote: bool = False

    def to_dict(self) -> Dict[str, object]:
        payload = asdict(self)
        payload["allowed_tools"] = sorted(self.allowed_tools)
        return payload


_IDENTITIES: Dict[str, IdentityContract] = {
    PROPOSER_IDENTITY: IdentityContract(
        identity_id=PROPOSER_IDENTITY,
        role="proposer",
        allowed_tools=frozenset({"submit_candidate"}),
        model_policy="strict_json_provisional_shape",
    ),
    CRITIC_IDENTITY: IdentityContract(
        identity_id=CRITIC_IDENTITY,
        role="critic",
        allowed_tools=frozenset({"find_comparison_candidates", "submit_evaluation"}),
        model_policy="strict_json_critique",
    ),
    SYNTHESIZER_IDENTITY: IdentityContract(
        identity_id=SYNTHESIZER_IDENTITY,
        role="synthesizer",
        allowed_tools=frozenset({"find_comparison_candidates", "submit_evaluation"}),
        model_policy="strict_json_synthesis",
    ),
    EVALUATOR_IDENTITY: IdentityContract(
        identity_id=EVALUATOR_IDENTITY,
        role="evaluator",
        allowed_tools=frozenset({"request_promotion", "submit_evaluation", "find_comparison_candidates"}),
        model_policy="strict_json_evaluation",
    ),
    HUMAN_APPROVER_ROLE: IdentityContract(
        identity_id=HUMAN_APPROVER_ROLE,
        role="human_approver",
        allowed_tools=frozenset({"apply_promotion"}),
        model_policy="human",
        can_promote=True,
    ),
    CANONICAL_AUTHORITY_ROLE: IdentityContract(
        identity_id=CANONICAL_AUTHORITY_ROLE,
        role="canonical_authority",
        allowed_tools=frozenset({"apply_promotion"}),
        model_policy="human_or_authority",
        can_promote=True,
    ),
}


def get_identity(identity_id: str) -> IdentityContract:
    identity = _IDENTITIES.get(identity_id)
    if identity is None:
        raise AuthorizationError(f"unknown identity: {identity_id}")
    return identity


def assert_tool_allowed(identity_id: str, tool_name: str) -> IdentityContract:
    identity = get_identity(identity_id)
    if tool_name not in identity.allowed_tools:
        raise AuthorizationError(f"identity {identity_id} cannot call {tool_name}")
    if tool_name in PRIVILEGED_PROMOTION_OPS and identity_id in {
        PROPOSER_IDENTITY,
        CRITIC_IDENTITY,
        SYNTHESIZER_IDENTITY,
    }:
        raise AuthorizationError("population identities cannot call promotion operations")
    return identity


def population_tool_surface(identity_id: str) -> Mapping[str, object]:
    identity = get_identity(identity_id)
    tools = sorted(tool for tool in identity.allowed_tools if tool in POPULATION_AGENT_TOOLS)
    return {
        "identity_id": identity.identity_id,
        "role": identity.role,
        "tools": tools,
        "structured_output_required": identity.structured_output_required,
        "forbidden": {
            "filesystem": not identity.broad_filesystem,
            "shell": not identity.broad_shell,
            "network": not identity.broad_network,
            "registry_write": not identity.registry_write,
            "promotion": not identity.can_promote,
        },
        "prompt_version_capture_required": True,
        "model_version_capture_required": True,
        "tool_contract_version_capture_required": True,
    }
