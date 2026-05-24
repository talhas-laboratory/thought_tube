from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


MODULE_ID = "kernel.foundation.models"
CONTRACT_VERSION = "1.0"
PUBLIC_MODELS = (
    "ConversationEvent",
    "SessionManifest",
    "TaskContextPack",
    "DevelopmentIdeaRecord",
    "DevelopmentProposal",
    "MemoryCard",
    "InsightCandidate",
    "SurfacedInsight",
    "ThoughtFeedItem",
    "ThoughtThreadMessage",
    "ThoughtThread",
    "SourceRegistryEntry",
    "ChunkRecord",
    "MetaLayerRecord",
    "ConversationThread",
    "ConversationThreadLink",
    "ProjectLens",
    "ThreadAbstraction",
    "ThreadAbstractionLink",
    "KnowledgeNode",
    "KnowledgeEdge",
    "ContextBubble",
    "BubbleMembership",
    "BubbleEdge",
    "BubbleTransition",
    "LLMCostEvent",
    "ThoughtPacket",
    "ConceptNode",
    "ConceptEdge",
    "TouchOperation",
    "SynthesisPacket",
    "EvidenceSpan",
    "SignatureEntity",
    "SignatureState",
    "SignatureRelation",
    "SignatureFeedbackLoop",
    "SignatureConstraint",
    "SignatureAbsence",
    "SignatureAffordance",
    "CandidateShape",
    "AlternativeInterpretation",
    "SystemDynamicSignature",
    "ShapeGraphNode",
    "ShapeGraphEdge",
    "AnalogyEvaluationPacket",
    "ShapeMemoryItem",
    "DimensionSpec",
    "ModelRoleBinding",
    "ChunkDimensionProfile",
    "DimensionRun",
)
__all__ = ["MODULE_ID", "CONTRACT_VERSION", *PUBLIC_MODELS]


@dataclass
class ConversationEvent:
    event_id: str
    session_id: str
    timestamp: str
    actor: str
    kind: str
    content: str
    attachments: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    source_ref: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionManifest:
    session_id: str
    title: str
    started_at: str
    ended_at: Optional[str]
    participants: List[str]
    source_type: str
    status: str
    artifact_refs: Dict[str, str]
    domains: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskContextPack:
    task_id: str
    request: str
    task_type: str
    domain_overlays: List[str]
    tenets: List[str]
    relevant_sessions: List[Dict[str, Any]]
    relevant_cards: List[Dict[str, Any]]
    active_plans: List[Dict[str, Any]]
    constraints: List[str]
    open_questions: List[str]
    next_actions: List[str]
    reference_docs: Dict[str, str] = field(default_factory=dict)
    relevant_concepts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DevelopmentIdeaRecord:
    idea_id: str
    created_at: str
    raw_idea: str
    desired_effect: str
    intent_kind: str
    surface_hints: List[str] = field(default_factory=list)
    source_session_id: Optional[str] = None
    source_refs: List[str] = field(default_factory=list)
    translated_framing: Dict[str, Any] = field(default_factory=dict)
    development_signals: Dict[str, Any] = field(default_factory=dict)
    status: str = "recorded"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DevelopmentProposal:
    proposal_id: str
    idea_id: str
    created_at: str
    route_kind: str
    target_module_ids: List[str] = field(default_factory=list)
    target_surface_family: str = ""
    rationale: str = ""
    confidence: float = 0.0
    version_plan: Dict[str, Any] = field(default_factory=dict)
    recipe_plan: Dict[str, Any] = field(default_factory=dict)
    scope_in: List[str] = field(default_factory=list)
    scope_out: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    approval_status: str = "proposed"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MemoryCard:
    card_id: str
    card_type: str
    title: str
    summary: str
    source_refs: List[str]
    domains: List[str]
    status: str
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InsightCandidate:
    insight_id: str
    title: str
    summary: str
    source_refs: List[str]
    source_item_ids: List[str]
    reasoning_primitive: str
    surprise_score: float
    confidence_score: float
    evidence_status: str
    action_hint: str
    feedback_state: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SurfacedInsight:
    insight_id: str
    title: str
    what_changed: str
    source_refs: List[str]
    source_item_ids: List[str]
    reasoning_primitive: str
    surprise_score: float
    confidence_score: float
    evidence_status: str
    why_it_matters_now: str
    next_action: str
    feedback_state: str
    feedback_controls: List[str] = field(
        default_factory=lambda: ["relevant", "dismiss", "revisit_later"]
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThoughtFeedItem:
    thought_id: str
    insight_id: str
    title: str
    short_text: str
    article_title: str
    article_markdown: str
    source_refs: List[str]
    source_item_ids: List[str]
    reasoning_primitive: str
    surprise_score: float
    confidence_score: float
    evidence_status: str
    why_it_matters_now: str
    next_action: str
    feedback_state: str
    primary_bubble_id: str = ""
    primary_bubble_label: str = ""
    related_bubble_ids: List[str] = field(default_factory=list)
    feedback_controls: List[str] = field(
        default_factory=lambda: ["relevant", "dismiss", "revisit_later"]
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThoughtThreadMessage:
    message_id: str
    role: str
    content: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThoughtThread:
    thread_id: str
    thought_id: str
    title: str
    status: str
    created_at: str
    updated_at: str
    character: str
    system_prompt: str
    context_summary: str
    source_refs: List[str]
    reasoning_primitive: str
    backend_id: str
    messages: List[Dict[str, Any]]
    embedded_source_item_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SourceRegistryEntry:
    source_id: str
    title: str
    source_ref: str
    source_type: str
    source_family: str
    sensitivity_tier: str
    content_hash: str
    chunk_count: int
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChunkRecord:
    chunk_id: str
    source_id: str
    source_item_id: str
    chunk_index: int
    title: str
    content: str
    content_kind: str
    source_ref: str
    source_type: str
    source_family: str
    sensitivity_tier: str
    created_at: str
    section_path: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MetaLayerRecord:
    meta_id: str
    kind: str
    label: str
    summary: str
    status: str
    confidence: float
    source_refs: List[str]
    chunk_ids: List[str]
    evidence: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConversationThread:
    thread_id: str
    topic_signature: List[str]
    source_refs: List[str]
    user_chunk_ids: List[str]
    approved_context_chunk_ids: List[str]
    turn_count: int
    interruption_count: int
    delta_intent_keys: List[str] = field(default_factory=list)
    source_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConversationThreadLink:
    link_id: str
    kind: str
    from_thread_id: str
    to_thread_id: str
    source_refs: List[str]
    confidence: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProjectLens:
    lens_key: str
    label: str
    thesis_hint: str
    keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThreadAbstraction:
    abstract_thread_id: str
    label: str
    primary_lens_key: str
    secondary_lens_keys: List[str]
    thesis: str
    child_thread_ids: List[str]
    source_refs: List[str]
    delta_intent_keys: List[str]
    dominant_tensions: List[str]
    answer_shape_constraints: List[str]
    approved_context_meta_ids: List[str]
    expectation_ids: List[str]
    resolution_state: str
    confidence: float
    semantic_line_meta_ids: List[str] = field(default_factory=list)
    project_lens_keys: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThreadAbstractionLink:
    link_id: str
    kind: str
    from_id: str
    to_id: str
    confidence: float
    evidence_refs: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeNode:
    node_id: str
    kind: str
    label: str
    status: str
    confidence: float
    source_refs: List[str]
    ref_id: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeEdge:
    edge_id: str
    kind: str
    from_id: str
    to_id: str
    status: str
    confidence: float
    evidence_refs: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ContextBubble:
    bubble_id: str
    label: str
    thesis: str
    status: str
    confidence: float
    support_count: int
    source_refs: List[str]
    chunk_ids: List[str]
    meta_ids: List[str]
    dominant_primitives: List[str] = field(default_factory=list)
    active_tensions: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    domain_lenses: List[str] = field(default_factory=list)
    primary_abstract_thread_id: str = ""
    supporting_thread_ids: List[str] = field(default_factory=list)
    project_lens_keys: List[str] = field(default_factory=list)
    primary_concept_id: str = ""
    concept_ids: List[str] = field(default_factory=list)
    related_bubble_ids: List[str] = field(default_factory=list)
    created_at: str = ""
    last_reinforced_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BubbleMembership:
    membership_id: str
    bubble_id: str
    meta_id: str
    role: str
    confidence: float
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BubbleEdge:
    edge_id: str
    kind: str
    from_bubble_id: str
    to_bubble_id: str
    confidence: float
    shared_terms: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class BubbleTransition:
    transition_id: str
    bubble_id: str
    action: str
    meta_id: Optional[str]
    related_bubble_id: Optional[str]
    reason: str
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LLMCostEvent:
    event_id: str
    timestamp: str
    ledger: str
    component: str
    operation: str
    provider: str
    model: str
    pricing_profile: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    usd_cost: Optional[float]
    currency: str = "USD"
    status: str = "recorded"
    token_source: str = "actual"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ThoughtPacket:
    packet_id: str
    thought_id: str
    insight_id: str
    title: str
    short_text: str
    article_title: str
    article_markdown: str
    status: str
    review_status: str
    evidence_status: str
    confidence_score: float
    relevance_score: float
    novelty_score: float
    source_refs: List[str]
    source_item_ids: List[str]
    meta_refs: List[str]
    shared_primitive_key: str
    shared_primitive_label: str
    what_changed: str
    why_it_matters_now: str
    next_action: str
    reasoning_pipeline: str
    primary_bubble_id: str = ""
    primary_bubble_label: str = ""
    related_bubble_ids: List[str] = field(default_factory=list)
    feedback_state: str = "pending"
    feedback_controls: List[str] = field(
        default_factory=lambda: ["relevant", "dismiss", "revisit_later"]
    )
    article_sections: List[Dict[str, Any]] = field(default_factory=list)
    article_profile: str = ""
    article_module_order: List[str] = field(default_factory=list)
    article_config_snapshot: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConceptNode:
    concept_id: str
    label: str
    summary: str
    abstract_pattern: str
    transfer_shape: str
    aliases: List[str]
    artifact_refs: List[str]
    source_refs: List[str]
    session_ids: List[str]
    status: str
    confidence: float
    created_at: str
    updated_at: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ConceptEdge:
    edge_id: str
    kind: str
    from_id: str
    to_id: str
    status: str
    confidence: float
    shared_terms: List[str]
    source_refs: List[str]
    session_ids: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TouchOperation:
    touch_id: str
    synthesis_id: str
    session_id: str
    concept_id: str
    concept_label: str
    candidate_label: str
    touch_type: str
    decision: str
    status: str
    confidence: float
    source_refs: List[str]
    artifact_refs: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SynthesisPacket:
    synthesis_id: str
    session_id: str
    title: str
    summary: str
    status: str
    confidence: float
    source_refs: List[str]
    confirmed: List[str] = field(default_factory=list)
    inferred: List[str] = field(default_factory=list)
    contested: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    concept_candidates: List[Dict[str, Any]] = field(default_factory=list)
    touch_operations: List[Dict[str, Any]] = field(default_factory=list)
    conversation_analysis: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvidenceSpan:
    source_ref: str
    chunk_id: str
    text: str
    kind: str
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SignatureEntity:
    entity_id: str
    label: str
    node_type: str
    role: str
    confidence: float
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SignatureState:
    state_id: str
    label: str
    confidence: float
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SignatureRelation:
    relation_id: str
    source_id: str
    target_id: str
    edge_type: str
    operation: str
    confidence: float
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SignatureFeedbackLoop:
    loop_id: str
    label: str
    node_ids: List[str]
    edge_ids: List[str]
    confidence: float
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SignatureConstraint:
    constraint_id: str
    label: str
    confidence: float
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SignatureAbsence:
    absence_id: str
    label: str
    confidence: float
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SignatureAffordance:
    affordance_id: str
    label: str
    confidence: float
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CandidateShape:
    shape_name: str
    confidence: float
    rationale: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AlternativeInterpretation:
    title: str
    summary: str
    confidence: float
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SystemDynamicSignature:
    signature_id: str
    source_ref: str
    source_kind: str
    source_anchor_id: str
    title: str
    summary: str
    system_boundary: str
    observer_lens: str
    entities: List[Dict[str, Any]] = field(default_factory=list)
    states: List[Dict[str, Any]] = field(default_factory=list)
    relations: List[Dict[str, Any]] = field(default_factory=list)
    feedback_loops: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    absences: List[Dict[str, Any]] = field(default_factory=list)
    affordances: List[Dict[str, Any]] = field(default_factory=list)
    failure_mode: str = ""
    desired_transformation: str = ""
    candidate_shapes: List[Dict[str, Any]] = field(default_factory=list)
    alternative_interpretations: List[Dict[str, Any]] = field(default_factory=list)
    evidence_spans: List[Dict[str, Any]] = field(default_factory=list)
    missing_information: List[str] = field(default_factory=list)
    confidence: float = 0.0
    status: str = "provisional"
    version: int = 1
    created_at: str = ""
    updated_at: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShapeGraphNode:
    graph_node_id: str
    signature_id: str
    node_key: str
    node_type: str
    label: str
    role: str = ""
    confidence: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShapeGraphEdge:
    graph_edge_id: str
    signature_id: str
    source_node_key: str
    target_node_key: str
    edge_type: str
    operation: str = ""
    confidence: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalogyEvaluationPacket:
    evaluation_id: str
    signature_id: str
    analogy_id: str
    deterministic_score: float
    role_fit: float
    causal_fit: float
    feedback_fit: float
    leverage_fit: float
    material_transfer_fit: float
    anti_match_penalty: float
    llm_rationale: str
    transfers: List[str] = field(default_factory=list)
    does_not_transfer: List[str] = field(default_factory=list)
    intervention_risks: List[str] = field(default_factory=list)
    verdict: str = ""
    confidence: float = 0.0
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ShapeMemoryItem:
    memory_id: str
    scope: str
    scope_key: str
    shape_name: str
    shape_definition: str
    validated_examples: List[str] = field(default_factory=list)
    anti_matches: List[str] = field(default_factory=list)
    interventions: List[str] = field(default_factory=list)
    missing_constraints: List[str] = field(default_factory=list)
    validation_count: int = 0
    rejection_count: int = 0
    last_validated_at: str = ""
    updated_at: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DimensionSpec:
    dimension_id: str
    label: str
    description: str
    applies_to: List[str]
    derive_mode: str
    enabled: bool = True
    requires_model: bool = False
    preferred_role: str = ""
    fallback_mode: str = "deterministic"
    comparison_strategy: str = "overlap"
    search_weight_default: float = 1.0
    cache_version: str = "v1"
    allowed_values: List[str] = field(default_factory=list)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ModelRoleBinding:
    role_id: str
    backend: str
    model_id: str
    enabled: bool = True
    fallback_role_id: str = ""
    endpoint: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChunkDimensionProfile:
    profile_id: str
    chunk_id: str
    source_ref: str
    dimension_id: str
    primary_value: str
    normalized_values: List[str]
    confidence: float
    method: str
    version: str
    updated_at: str
    evidence: List[str] = field(default_factory=list)
    model_role: str = ""
    model_signature: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DimensionRun:
    run_id: str
    dimension_id: str
    status: str
    started_at: str
    completed_at: Optional[str]
    chunk_count: int
    processed_count: int
    skipped_count: int
    cache_hit_count: int
    model_roles: List[str] = field(default_factory=list)
    method_counts: Dict[str, int] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
