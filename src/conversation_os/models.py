from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


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
