"""Shape Intelligence population control plane.

Owns deterministic normalization/evidence assembly, population-agent tools
(submit_candidate, find_comparison_candidates, submit_evaluation), and
privileged promotion operations. See workspace shape-intelligence-population.
"""

from __future__ import annotations

from conversation_os.shape_population.candidate_submission import proposer_tool_surface, submit_candidate
from conversation_os.shape_population.contracts import (
    AUTOMATIC_INFRA_OPS,
    CANDIDATE_STATUSES,
    COMPARISON_RELATIONS,
    POPULATION_AGENT_TOOLS,
    PRIVILEGED_PROMOTION_OPS,
)
from conversation_os.shape_population.critique import (
    critic_tool_surface,
    find_comparison_candidates,
    submit_evaluation,
)
from conversation_os.shape_population.evidence import build_evidence_packet
from conversation_os.shape_population.identities import (
    CRITIC_IDENTITY,
    PROPOSER_IDENTITY,
    SYNTHESIZER_IDENTITY,
    population_tool_surface,
)
from conversation_os.shape_population.normalization import normalize_source
from conversation_os.shape_population.promotion import apply_promotion, request_promotion, rollback_promotion
from conversation_os.shape_population.storage import PopulationStore

MODULE_ID = "kernel.shape_population"
CONTRACT_VERSION = "1.0.0"

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "POPULATION_AGENT_TOOLS",
    "PRIVILEGED_PROMOTION_OPS",
    "AUTOMATIC_INFRA_OPS",
    "CANDIDATE_STATUSES",
    "COMPARISON_RELATIONS",
    "PROPOSER_IDENTITY",
    "CRITIC_IDENTITY",
    "SYNTHESIZER_IDENTITY",
    "PopulationStore",
    "normalize_source",
    "build_evidence_packet",
    "submit_candidate",
    "find_comparison_candidates",
    "submit_evaluation",
    "request_promotion",
    "apply_promotion",
    "rollback_promotion",
    "proposer_tool_surface",
    "critic_tool_surface",
    "population_tool_surface",
)
__all__ = list(PUBLIC_API)
