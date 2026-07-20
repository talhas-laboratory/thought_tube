"""Package exports for Shape Intelligence population control plane."""

from __future__ import annotations

from conversation_os.shape_population.candidate_submission import proposer_tool_surface, submit_candidate
from conversation_os.shape_population.canonical_port import (
    FailClosedCanonicalPort,
    LocalRecordingCanonicalPort,
)
from conversation_os.shape_population.comparison import find_neighbors
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
from conversation_os.shape_population.evidence import build_evidence_packet, validate_evidence_ref_against_packet
from conversation_os.shape_population.execution_context import (
    ExecutionContext,
    agent_context,
    human_context,
    require_capability,
    service_context,
)
from conversation_os.shape_population.identities import (
    CRITIC_IDENTITY,
    EVALUATOR_IDENTITY,
    PROPOSER_IDENTITY,
    SYNTHESIZER_IDENTITY,
    population_tool_surface,
)
from conversation_os.shape_population.model_gateway import ShapeModelGateway, StubModelClient
from conversation_os.shape_population.normalization import normalize_source
from conversation_os.shape_population.orchestrator import ShapePopulationOrchestrator, enqueue_after_ingest
from conversation_os.shape_population.promotion import apply_promotion, request_promotion, rollback_promotion
from conversation_os.shape_population.storage import PopulationStore, ShapePopulationStore
from conversation_os.shape_population.worker import build_worker, run_worker

MODULE_ID = "kernel.shape_population"
CONTRACT_VERSION = "1.2.0"

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
    "EVALUATOR_IDENTITY",
    "PopulationStore",
    "ShapePopulationStore",
    "ExecutionContext",
    "agent_context",
    "human_context",
    "service_context",
    "require_capability",
    "normalize_source",
    "build_evidence_packet",
    "validate_evidence_ref_against_packet",
    "submit_candidate",
    "find_comparison_candidates",
    "find_neighbors",
    "submit_evaluation",
    "request_promotion",
    "apply_promotion",
    "rollback_promotion",
    "ShapeModelGateway",
    "StubModelClient",
    "ShapePopulationOrchestrator",
    "enqueue_after_ingest",
    "FailClosedCanonicalPort",
    "LocalRecordingCanonicalPort",
    "proposer_tool_surface",
    "critic_tool_surface",
    "population_tool_surface",
    "build_worker",
    "run_worker",
)
__all__ = list(PUBLIC_API)
