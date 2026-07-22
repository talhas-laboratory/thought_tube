"""Versioned disclosure contracts for the Cognitive Aperture service (CAE-015)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

MODULE_ID = "kernel.disclosure.contracts"
CONTRACT_VERSION = "1.0"

RESULT_STATUSES = (
    "disclosed",
    "empty_no_positive_match",
    "empty_grant_excludes_all",
    "abstained_dependency_not_ready",
    "abstained_stale_index",
    "abstained_invalid_policy",
    "abstained_insufficient_budget",
    "denied_visibility",
    "failed_internal",
)

ENVELOPE_MODES = ("open", "bounded", "strict", "incognito")

LAYER_IDS = ("session", "workspace", "user", "governed_global", "explicit_pin", "ephemeral_turn")

RETENTION_MODES = ("normal_policy", "minimal", "hashes_metrics_only")

NARROWING_REASON_CODES = (
    "envelope_default",
    "workspace_policy",
    "source_policy",
    "branch_scope_visibility",
    "explicit_pin",
    "explicit_deny",
)

# Type-level security boundary: execution payloads must never carry suppression semantics.
EXECUTION_BUNDLE_FORBIDDEN_KEYS = frozenset(
    {
        "suppressed",
        "suppressed_layers",
        "suppressed_refs",
        "suppressed_blocks",
        "omitted",
        "omitted_blocks",
        "omitted_ids",
        "omission_reason",
        "omission_reasons",
        "excluded",
        "excluded_blocks",
        "hidden",
        "hidden_blocks",
        "deny_reason",
        "deny_reasons",
        "drop_ledger",
        "disclosure_state",
        "audit_only",
        "retrieval_suppressed",
        "negative_sentinel",
        "withheld",
    }
)

EXECUTION_BUNDLE_FORBIDDEN_VALUES = frozenset({"suppressed", "withheld", "omitted", "excluded", "hidden"})

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "RESULT_STATUSES",
    "ENVELOPE_MODES",
    "LAYER_IDS",
    "RETENTION_MODES",
    "NARROWING_REASON_CODES",
    "EXECUTION_BUNDLE_FORBIDDEN_KEYS",
    "ContractValidationError",
    "ApertureRequest",
    "ActiveStateSnapshot",
    "RequestedGrant",
    "EffectiveGrant",
    "CandidateRef",
    "EvidenceBlock",
    "ExecutionBundle",
    "AuditReceipt",
    "EnvironmentSpecPacket",
    "envelope_defaults",
    "receipt_retention_for_envelope",
    "normalize_effective_grant",
    "validate_execution_bundle",
    "validate_model_bound_payload",
    "validate_audit_receipt",
    "validate_environment_spec_packet",
    "build_environment_spec_packet",
    "contract_field_catalog",
)
__all__ = list(PUBLIC_API)


class ContractValidationError(ValueError):
    def __init__(self, code: str, message: str, contract: str = "") -> None:
        self.code = code
        self.contract = contract
        super().__init__(message)


@dataclass
class ApertureRequest:
    request_id: str
    surface: str
    user_turn: str
    session_id: Optional[str] = None
    workspace_id: Optional[str] = None
    explicit_pins: List[str] = field(default_factory=list)
    requested_depth: str = "focused"
    caller_capabilities: List[str] = field(default_factory=list)
    contract_version: str = CONTRACT_VERSION
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, ignore_unknown: bool = True) -> "ApertureRequest":
        data = _coerce_mapping(payload, "ApertureRequest", ignore_unknown=ignore_unknown)
        return cls(
            request_id=str(data.get("request_id", "")),
            surface=str(data.get("surface", "")),
            user_turn=str(data.get("user_turn", "")),
            session_id=_optional_str(data.get("session_id")),
            workspace_id=_optional_str(data.get("workspace_id")),
            explicit_pins=_string_list(data.get("explicit_pins")),
            requested_depth=str(data.get("requested_depth", "focused") or "focused"),
            caller_capabilities=_string_list(data.get("caller_capabilities")),
            contract_version=str(data.get("contract_version", CONTRACT_VERSION) or CONTRACT_VERSION),
            provenance=dict(data.get("provenance", {}) or {}),
        )


@dataclass
class ActiveStateSnapshot:
    snapshot_id: str
    request_id: str
    topic: str
    purpose: str
    object_scope: str
    object_id: str
    tension: str
    posture: str
    lens: str
    branch_id: str
    scope_id: str
    source_revision: str
    derived_from: List[str] = field(default_factory=list)
    contract_version: str = CONTRACT_VERSION
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, ignore_unknown: bool = True) -> "ActiveStateSnapshot":
        data = _coerce_mapping(payload, "ActiveStateSnapshot", ignore_unknown=ignore_unknown)
        return cls(
            snapshot_id=str(data.get("snapshot_id", "")),
            request_id=str(data.get("request_id", "")),
            topic=str(data.get("topic", "")),
            purpose=str(data.get("purpose", "")),
            object_scope=str(data.get("object_scope", "same_main")),
            object_id=str(data.get("object_id", "")),
            tension=str(data.get("tension", "") or ""),
            posture=str(data.get("posture", "") or ""),
            lens=str(data.get("lens", "") or ""),
            branch_id=str(data.get("branch_id", "") or ""),
            scope_id=str(data.get("scope_id", "") or ""),
            source_revision=str(data.get("source_revision", "") or ""),
            derived_from=_string_list(data.get("derived_from")),
            contract_version=str(data.get("contract_version", CONTRACT_VERSION) or CONTRACT_VERSION),
            provenance=dict(data.get("provenance", {}) or {}),
        )


@dataclass
class RequestedGrant:
    grant_id: str
    request_id: str
    envelope: str
    requested_layers: List[str]
    requested_refs: List[str]
    dimensions: List[str]
    shape_maturity: str
    token_budget: int
    persistence_mode: str
    explicit_pins: List[str] = field(default_factory=list)
    explicit_denials: List[str] = field(default_factory=list)
    cross_ocean: Optional[bool] = None
    contract_version: str = CONTRACT_VERSION
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, ignore_unknown: bool = True) -> "RequestedGrant":
        data = _coerce_mapping(payload, "RequestedGrant", ignore_unknown=ignore_unknown)
        envelope = str(data.get("envelope", "bounded") or "bounded")
        _validate_envelope(envelope)
        return cls(
            grant_id=str(data.get("grant_id", "")),
            request_id=str(data.get("request_id", "")),
            envelope=envelope,
            requested_layers=_string_list(data.get("requested_layers")),
            requested_refs=_string_list(data.get("requested_refs")),
            dimensions=_string_list(data.get("dimensions")),
            shape_maturity=str(data.get("shape_maturity", "candidate") or "candidate"),
            token_budget=int(data.get("token_budget", 0) or 0),
            persistence_mode=str(data.get("persistence_mode", "gated") or "gated"),
            explicit_pins=_string_list(data.get("explicit_pins")),
            explicit_denials=_string_list(data.get("explicit_denials")),
            cross_ocean=_optional_bool(data.get("cross_ocean")),
            contract_version=str(data.get("contract_version", CONTRACT_VERSION) or CONTRACT_VERSION),
            provenance=dict(data.get("provenance", {}) or {}),
        )


@dataclass
class EffectiveGrant:
    grant_id: str
    request_id: str
    envelope: str
    effective_layers: List[str]
    effective_refs: List[str]
    dimensions: List[str]
    shape_maturity: str
    cross_ocean: bool
    token_budget: int
    persistence_mode: str
    explicit_pins: List[str]
    narrowing_reasons: List[Dict[str, Any]]
    deny_precedence_applied: bool
    requested_grant_ref: str
    contract_version: str = CONTRACT_VERSION
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, ignore_unknown: bool = True) -> "EffectiveGrant":
        data = _coerce_mapping(payload, "EffectiveGrant", ignore_unknown=ignore_unknown)
        envelope = str(data.get("envelope", "bounded") or "bounded")
        _validate_envelope(envelope)
        return cls(
            grant_id=str(data.get("grant_id", "")),
            request_id=str(data.get("request_id", "")),
            envelope=envelope,
            effective_layers=_string_list(data.get("effective_layers")),
            effective_refs=_string_list(data.get("effective_refs")),
            dimensions=_string_list(data.get("dimensions")),
            shape_maturity=str(data.get("shape_maturity", "candidate") or "candidate"),
            cross_ocean=bool(data.get("cross_ocean", False)),
            token_budget=int(data.get("token_budget", 0) or 0),
            persistence_mode=str(data.get("persistence_mode", "gated") or "gated"),
            explicit_pins=_string_list(data.get("explicit_pins")),
            narrowing_reasons=[dict(item) for item in data.get("narrowing_reasons", []) or []],
            deny_precedence_applied=bool(data.get("deny_precedence_applied", False)),
            requested_grant_ref=str(data.get("requested_grant_ref", "") or ""),
            contract_version=str(data.get("contract_version", CONTRACT_VERSION) or CONTRACT_VERSION),
            provenance=dict(data.get("provenance", {}) or {}),
        )


@dataclass
class CandidateRef:
    candidate_id: str
    kind: str
    source_ref: str
    projection_id: str
    branch_id: str
    scope_id: str
    maturity: str
    admission_signals: List[str]
    ranking_features: Dict[str, float]
    provenance_ref: str
    contract_version: str = CONTRACT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, ignore_unknown: bool = True) -> "CandidateRef":
        data = _coerce_mapping(payload, "CandidateRef", ignore_unknown=ignore_unknown)
        return cls(
            candidate_id=str(data.get("candidate_id", "")),
            kind=str(data.get("kind", "")),
            source_ref=str(data.get("source_ref", "")),
            projection_id=str(data.get("projection_id", "")),
            branch_id=str(data.get("branch_id", "") or ""),
            scope_id=str(data.get("scope_id", "") or ""),
            maturity=str(data.get("maturity", "candidate") or "candidate"),
            admission_signals=_string_list(data.get("admission_signals")),
            ranking_features={str(key): float(value) for key, value in dict(data.get("ranking_features", {}) or {}).items()},
            provenance_ref=str(data.get("provenance_ref", "") or ""),
            contract_version=str(data.get("contract_version", CONTRACT_VERSION) or CONTRACT_VERSION),
        )


@dataclass
class EvidenceBlock:
    block_id: str
    bounded_text: str
    token_estimate: int
    source_span: Dict[str, Any]
    inclusion_reason: str
    sensitivity: str
    branch_id: str
    scope_id: str
    content_hash: str
    provenance_ref: str
    contract_version: str = CONTRACT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, ignore_unknown: bool = True) -> "EvidenceBlock":
        data = _coerce_mapping(payload, "EvidenceBlock", ignore_unknown=ignore_unknown)
        return cls(
            block_id=str(data.get("block_id", "")),
            bounded_text=str(data.get("bounded_text", "")),
            token_estimate=int(data.get("token_estimate", 0) or 0),
            source_span=dict(data.get("source_span", {}) or {}),
            inclusion_reason=str(data.get("inclusion_reason", "") or ""),
            sensitivity=str(data.get("sensitivity", "internal") or "internal"),
            branch_id=str(data.get("branch_id", "") or ""),
            scope_id=str(data.get("scope_id", "") or ""),
            content_hash=str(data.get("content_hash", "") or ""),
            provenance_ref=str(data.get("provenance_ref", "") or ""),
            contract_version=str(data.get("contract_version", CONTRACT_VERSION) or CONTRACT_VERSION),
        )


@dataclass
class ExecutionBundle:
    bundle_id: str
    request_id: str
    orientation: Dict[str, Any]
    steering_constraints: List[str]
    evidence_blocks: List[EvidenceBlock]
    provenance_refs: List[str]
    budget_summary: Dict[str, Any]
    contract_version: str = CONTRACT_VERSION

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["evidence_blocks"] = [block.to_dict() if isinstance(block, EvidenceBlock) else dict(block) for block in self.evidence_blocks]
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, ignore_unknown: bool = True, validate: bool = True) -> "ExecutionBundle":
        data = _coerce_mapping(payload, "ExecutionBundle", ignore_unknown=ignore_unknown)
        if validate:
            validate_execution_bundle(data)
        blocks = [EvidenceBlock.from_dict(item, ignore_unknown=ignore_unknown) for item in data.get("evidence_blocks", []) or []]
        bundle = cls(
            bundle_id=str(data.get("bundle_id", "")),
            request_id=str(data.get("request_id", "")),
            orientation=dict(data.get("orientation", {}) or {}),
            steering_constraints=_string_list(data.get("steering_constraints")),
            evidence_blocks=blocks,
            provenance_refs=_string_list(data.get("provenance_refs")),
            budget_summary=dict(data.get("budget_summary", {}) or {}),
            contract_version=str(data.get("contract_version", CONTRACT_VERSION) or CONTRACT_VERSION),
        )
        return bundle


@dataclass
class AuditReceipt:
    receipt_id: str
    request_id: str
    corpus_revision: str
    requested_grant: Dict[str, Any]
    effective_grant: Dict[str, Any]
    candidate_decisions: List[Dict[str, Any]]
    included_block_ids: List[str]
    omitted_block_ids: List[str]
    omission_reasons: List[Dict[str, Any]]
    budget_ledger: Dict[str, Any]
    policy_hashes: Dict[str, Any]
    surface: str
    result_status: str
    retention_mode: str
    contract_version: str = CONTRACT_VERSION
    content_hashes: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    sensitive_text_included: bool = False
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any], *, ignore_unknown: bool = True, validate: bool = True) -> "AuditReceipt":
        data = _coerce_mapping(payload, "AuditReceipt", ignore_unknown=ignore_unknown)
        result_status = str(data.get("result_status", "") or "")
        _validate_result_status(result_status)
        retention_mode = str(data.get("retention_mode", RETENTION_MODES[0]) or RETENTION_MODES[0])
        receipt = cls(
            receipt_id=str(data.get("receipt_id", "")),
            request_id=str(data.get("request_id", "")),
            corpus_revision=str(data.get("corpus_revision", "") or ""),
            requested_grant=dict(data.get("requested_grant", {}) or {}),
            effective_grant=dict(data.get("effective_grant", {}) or {}),
            candidate_decisions=[dict(item) for item in data.get("candidate_decisions", []) or []],
            included_block_ids=_string_list(data.get("included_block_ids")),
            omitted_block_ids=_string_list(data.get("omitted_block_ids")),
            omission_reasons=[dict(item) for item in data.get("omission_reasons", []) or []],
            budget_ledger=dict(data.get("budget_ledger", {}) or {}),
            policy_hashes=dict(data.get("policy_hashes", {}) or {}),
            surface=str(data.get("surface", "") or ""),
            result_status=result_status,
            retention_mode=retention_mode,
            contract_version=str(data.get("contract_version", CONTRACT_VERSION) or CONTRACT_VERSION),
            content_hashes=_string_list(data.get("content_hashes")),
            metrics=dict(data.get("metrics", {}) or {}),
            sensitive_text_included=bool(data.get("sensitive_text_included", False)),
            provenance=dict(data.get("provenance", {}) or {}),
        )
        if validate:
            validate_audit_receipt(receipt.to_dict())
        return receipt


@dataclass
class EnvironmentSpecPacket:
    packet_id: str
    application_id: str
    actor: str
    branch_id: str
    scope_id: str
    disclosed_tools: List[str]
    auth_boundaries: Dict[str, Any]
    rate_limit: Dict[str, Any]
    timeout_seconds: float
    cancellation: Dict[str, Any]
    read_intents: List[str]
    write_intents: List[str]
    forbidden_intents: List[str]
    contract_version: str = "1.0.0"
    provenance: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(
        cls,
        payload: Mapping[str, Any],
        *,
        ignore_unknown: bool = True,
        validate: bool = True,
    ) -> "EnvironmentSpecPacket":
        data = _coerce_mapping(payload, "EnvironmentSpecPacket", ignore_unknown=ignore_unknown)
        packet = cls(
            packet_id=str(data.get("packet_id", "")),
            application_id=str(data.get("application_id", "")),
            actor=str(data.get("actor", "")),
            branch_id=str(data.get("branch_id", "")),
            scope_id=str(data.get("scope_id", "")),
            disclosed_tools=_string_list(data.get("disclosed_tools")),
            auth_boundaries=dict(data.get("auth_boundaries", {}) or {}),
            rate_limit=dict(data.get("rate_limit", {}) or {}),
            timeout_seconds=float(data.get("timeout_seconds", 0) or 0),
            cancellation=dict(data.get("cancellation", {}) or {}),
            read_intents=_string_list(data.get("read_intents")),
            write_intents=_string_list(data.get("write_intents")),
            forbidden_intents=_string_list(data.get("forbidden_intents")),
            contract_version=str(data.get("contract_version", "1.0.0") or "1.0.0"),
            provenance=dict(data.get("provenance", {}) or {}),
        )
        if validate:
            validate_environment_spec_packet(packet.to_dict())
        return packet


def envelope_defaults(envelope: str) -> Dict[str, Any]:
    _validate_envelope(envelope)
    matrix = {
        "open": {
            "default_layers": ["session", "workspace", "user", "governed_global"],
            "cross_ocean": "policy_gated",
            "persistence_mode": "gated",
            "receipt_retention": "normal_policy",
            "user_layer_requires_grant": False,
        },
        "bounded": {
            "default_layers": ["session", "workspace"],
            "cross_ocean": False,
            "persistence_mode": "gated",
            "receipt_retention": "normal_policy",
            "user_layer_requires_grant": True,
        },
        "strict": {
            "default_layers": ["session", "explicit_pin"],
            "cross_ocean": False,
            "persistence_mode": "session_local_manual",
            "receipt_retention": "minimal",
            "user_layer_requires_grant": True,
        },
        "incognito": {
            "default_layers": ["ephemeral_turn"],
            "cross_ocean": False,
            "persistence_mode": "disabled",
            "receipt_retention": "hashes_metrics_only",
            "user_layer_requires_grant": True,
        },
    }
    defaults = dict(matrix[envelope])
    defaults["envelope"] = envelope
    defaults["contract_version"] = CONTRACT_VERSION
    return defaults


def receipt_retention_for_envelope(envelope: str) -> str:
    return str(envelope_defaults(envelope)["receipt_retention"])


def normalize_effective_grant(
    requested: RequestedGrant | Mapping[str, Any],
    *,
    workspace_layers: Optional[Sequence[str]] = None,
    source_layers: Optional[Sequence[str]] = None,
    branch_visible_layers: Optional[Sequence[str]] = None,
    explicit_pins: Optional[Sequence[str]] = None,
) -> EffectiveGrant:
    grant = requested if isinstance(requested, RequestedGrant) else RequestedGrant.from_dict(requested)
    defaults = envelope_defaults(grant.envelope)
    reasons: List[Dict[str, Any]] = []

    layers = list(defaults["default_layers"])
    reasons.append(
        {
            "code": "envelope_default",
            "field": "effective_layers",
            "requested": list(grant.requested_layers),
            "effective": list(layers),
            "reason": f"Envelope {grant.envelope} default access applied",
        }
    )

    if grant.requested_layers:
        requested_set = set(grant.requested_layers)
        narrowed = [layer for layer in layers if layer in requested_set or layer == "explicit_pin"]
        if narrowed != layers:
            reasons.append(
                {
                    "code": "requested_intersection",
                    "field": "effective_layers",
                    "requested": list(grant.requested_layers),
                    "effective": list(narrowed),
                    "reason": "Requested layers intersected with envelope defaults",
                }
            )
        layers = narrowed or list(layers)

    if defaults.get("user_layer_requires_grant") and "user" in grant.requested_layers and "user" not in layers:
        layers.append("user")
        reasons.append(
            {
                "code": "explicit_grant",
                "field": "effective_layers",
                "requested": list(grant.requested_layers),
                "effective": list(layers),
                "reason": "User layer included only when explicitly requested under bounded/strict/incognito",
            }
        )

    for label, allowed, code in (
        ("workspace_layers", workspace_layers, "workspace_policy"),
        ("source_layers", source_layers, "source_policy"),
        ("branch_visible_layers", branch_visible_layers, "branch_scope_visibility"),
    ):
        if allowed is None:
            continue
        allowed_set = set(allowed)
        filtered = [layer for layer in layers if layer in allowed_set or layer == "explicit_pin"]
        if filtered != layers:
            reasons.append(
                {
                    "code": code,
                    "field": "effective_layers",
                    "requested": list(layers),
                    "effective": list(filtered),
                    "reason": f"{label} narrowed effective access",
                }
            )
        layers = filtered

    pin_values = _dedupe_strings(list(grant.explicit_pins) + list(explicit_pins or []))
    if pin_values:
        if "explicit_pin" not in layers:
            layers.append("explicit_pin")
        reasons.append(
            {
                "code": "explicit_pin",
                "field": "effective_layers",
                "requested": list(grant.explicit_pins),
                "effective": list(layers),
                "reason": "Explicit pins force explicit_pin layer",
            }
        )

    deny_set = set(grant.explicit_denials)
    deny_applied = False
    if deny_set:
        before = list(layers)
        layers = [layer for layer in layers if layer not in deny_set]
        refs = [ref for ref in grant.requested_refs if ref not in deny_set]
        deny_applied = before != layers or refs != grant.requested_refs
        reasons.append(
            {
                "code": "explicit_deny",
                "field": "effective_layers",
                "requested": list(before),
                "effective": list(layers),
                "reason": "Explicit denials always win",
            }
        )
    else:
        refs = list(grant.requested_refs)

    if grant.cross_ocean is None:
        cross_ocean = defaults["cross_ocean"] is True
        if defaults["cross_ocean"] == "policy_gated":
            cross_ocean = "governed_global" in layers
    else:
        cross_ocean = bool(grant.cross_ocean) and defaults["cross_ocean"] != False

    persistence_mode = defaults["persistence_mode"] if grant.envelope == "incognito" else grant.persistence_mode

    return EffectiveGrant(
        grant_id=grant.grant_id,
        request_id=grant.request_id,
        envelope=grant.envelope,
        effective_layers=_dedupe_strings(layers),
        effective_refs=_dedupe_strings(refs),
        dimensions=list(grant.dimensions),
        shape_maturity=grant.shape_maturity,
        cross_ocean=bool(cross_ocean),
        token_budget=max(0, int(grant.token_budget)),
        persistence_mode=str(persistence_mode),
        explicit_pins=pin_values,
        narrowing_reasons=reasons,
        deny_precedence_applied=deny_applied,
        requested_grant_ref=grant.grant_id,
        contract_version=CONTRACT_VERSION,
        provenance=dict(grant.provenance),
    )


def validate_execution_bundle(payload: Mapping[str, Any]) -> None:
    validate_model_bound_payload(payload, label="ExecutionBundle")


def validate_model_bound_payload(payload: Mapping[str, Any], *, label: str = "ModelBoundPayload") -> None:
    """Reject suppression or audit-only fields before model-bound compose."""
    data = _coerce_mapping(payload, label)
    forbidden = _find_forbidden_execution_keys(data)
    if forbidden:
        raise ContractValidationError(
            "suppression_field_forbidden",
            f"{label} cannot carry suppression or audit-only fields; forbidden keys: {sorted(forbidden)}",
            label,
        )


def validate_audit_receipt(payload: Mapping[str, Any], *, envelope: Optional[str] = None) -> None:
    data = _coerce_mapping(payload, "AuditReceipt")
    _validate_result_status(str(data.get("result_status", "") or ""))
    retention_mode = str(data.get("retention_mode", "") or "")
    if retention_mode not in RETENTION_MODES:
        raise ContractValidationError(
            "invalid_retention_mode",
            f"AuditReceipt retention_mode must be one of {RETENTION_MODES}",
            "AuditReceipt",
        )

    envelope_mode = envelope or str(dict(data.get("effective_grant", {}) or {}).get("envelope", "") or "")
    if envelope_mode:
        expected = receipt_retention_for_envelope(envelope_mode)
        if retention_mode != expected and not (envelope_mode == "incognito" and retention_mode == "hashes_metrics_only"):
            if envelope_mode != "open" or retention_mode not in {expected, "normal_policy"}:
                pass

    if retention_mode == "hashes_metrics_only" or envelope_mode == "incognito":
        if data.get("sensitive_text_included"):
            raise ContractValidationError(
                "incognito_sensitive_text_forbidden",
                "Incognito receipts must not include sensitive evidence text",
                "AuditReceipt",
            )
        for block_id in data.get("included_block_ids", []) or []:
            if isinstance(block_id, str) and block_id.startswith("text:"):
                raise ContractValidationError(
                    "incognito_text_reference_forbidden",
                    "Incognito receipts must reference hashes/metrics only",
                    "AuditReceipt",
                )
        for reason in data.get("omission_reasons", []) or []:
            if isinstance(reason, dict) and reason.get("sensitive_text"):
                raise ContractValidationError(
                    "incognito_omission_text_forbidden",
                    "Incognito omission reasons must not carry sensitive text",
                    "AuditReceipt",
                )


def validate_environment_spec_packet(payload: Mapping[str, Any]) -> None:
    data = _coerce_mapping(payload, "EnvironmentSpecPacket")
    for field_name in ("packet_id", "application_id", "actor", "branch_id", "scope_id"):
        if not str(data.get(field_name, "") or ""):
            raise ContractValidationError(
                "missing_required_field",
                f"EnvironmentSpecPacket {field_name} is required",
                "EnvironmentSpecPacket",
            )

    if not _is_string_list(data.get("disclosed_tools")):
        raise ContractValidationError(
            "invalid_disclosed_tools",
            "EnvironmentSpecPacket disclosed_tools must be a non-empty list of strings",
            "EnvironmentSpecPacket",
        )

    auth_boundaries = data.get("auth_boundaries")
    if not isinstance(auth_boundaries, dict):
        raise ContractValidationError(
            "invalid_auth_boundaries",
            "EnvironmentSpecPacket auth_boundaries must be a mapping",
            "EnvironmentSpecPacket",
        )
    for field_name in ("allowed_intents", "forbidden_intents"):
        if field_name not in auth_boundaries or not isinstance(auth_boundaries.get(field_name), list):
            raise ContractValidationError(
                "invalid_auth_boundaries",
                f"EnvironmentSpecPacket auth_boundaries.{field_name} must be a list",
                "EnvironmentSpecPacket",
            )
    if auth_boundaries.get("requires_forbidden_intents") and not auth_boundaries.get("forbidden_intents"):
        raise ContractValidationError(
            "missing_forbidden_intents",
            "EnvironmentSpecPacket auth_boundaries.forbidden_intents cannot be empty when required",
            "EnvironmentSpecPacket",
        )

    rate_limit = data.get("rate_limit")
    if not isinstance(rate_limit, dict):
        raise ContractValidationError(
            "invalid_rate_limit",
            "EnvironmentSpecPacket rate_limit must be a mapping",
            "EnvironmentSpecPacket",
        )
    rpm = rate_limit.get("requests_per_minute")
    if not isinstance(rpm, int) or isinstance(rpm, bool) or rpm < 0:
        raise ContractValidationError(
            "invalid_rate_limit",
            "EnvironmentSpecPacket rate_limit.requests_per_minute must be a non-negative integer",
            "EnvironmentSpecPacket",
        )

    timeout = data.get("timeout_seconds")
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
        raise ContractValidationError(
            "invalid_timeout",
            "EnvironmentSpecPacket timeout_seconds must be greater than zero",
            "EnvironmentSpecPacket",
        )

    cancellation = data.get("cancellation")
    if not isinstance(cancellation, dict):
        raise ContractValidationError(
            "invalid_cancellation",
            "EnvironmentSpecPacket cancellation must be a mapping",
            "EnvironmentSpecPacket",
        )
    if not isinstance(cancellation.get("supported"), bool) or not str(cancellation.get("signal_name", "") or ""):
        raise ContractValidationError(
            "invalid_cancellation",
            "EnvironmentSpecPacket cancellation requires supported bool and signal_name",
            "EnvironmentSpecPacket",
        )

    for field_name in ("read_intents", "write_intents", "forbidden_intents"):
        if field_name not in data or not isinstance(data.get(field_name), list):
            raise ContractValidationError(
                "invalid_intents",
                f"EnvironmentSpecPacket {field_name} must be a list",
                "EnvironmentSpecPacket",
            )


def build_environment_spec_packet(**kwargs: Any) -> EnvironmentSpecPacket:
    packet = EnvironmentSpecPacket(**kwargs)
    validate_environment_spec_packet(packet.to_dict())
    return packet


def contract_field_catalog() -> Dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "module_id": MODULE_ID,
        "contracts": {
            "ApertureRequest": _field_spec(ApertureRequest, provenance=True),
            "ActiveStateSnapshot": _field_spec(ActiveStateSnapshot, provenance=True),
            "RequestedGrant": _field_spec(RequestedGrant, provenance=True),
            "EffectiveGrant": _field_spec(EffectiveGrant, provenance=True),
            "CandidateRef": _field_spec(CandidateRef, provenance=False),
            "EvidenceBlock": _field_spec(EvidenceBlock, provenance=False),
            "ExecutionBundle": _field_spec(ExecutionBundle, provenance=False, forbidden=EXECUTION_BUNDLE_FORBIDDEN_KEYS),
            "AuditReceipt": _field_spec(AuditReceipt, provenance=True),
            "EnvironmentSpecPacket": _field_spec(EnvironmentSpecPacket, provenance=True),
        },
        "result_statuses": list(RESULT_STATUSES),
        "envelope_defaults": {mode: envelope_defaults(mode) for mode in ENVELOPE_MODES},
        "deny_precedence": "explicit_denials always win over pins, branch visibility, workspace/source policy, and envelope defaults",
    }


def _field_spec(model: Any, *, provenance: bool, forbidden: Iterable[str] = ()) -> Dict[str, Any]:
    fields_out: List[Dict[str, Any]] = []
    for item in fields(model):
        nullable = item.default is not None or item.default_factory is not None  # type: ignore[arg-type]
        if item.name in {"contract_version"}:
            cardinality = "1"
        elif item.name.endswith("_id") or item.name in {"surface", "user_turn", "envelope", "result_status", "retention_mode"}:
            cardinality = "1"
        elif item.name.endswith("_refs") or item.name.endswith("_layers") or item.name.endswith("_ids") or item.name.endswith("_signals") or item.name.endswith("_intents") or item.name == "disclosed_tools":
            cardinality = "0..n"
        else:
            cardinality = "0..1" if nullable else "1"
        fields_out.append(
            {
                "name": item.name,
                "type": str(item.type),
                "nullable": nullable,
                "cardinality": cardinality,
            }
        )
    spec: Dict[str, Any] = {"fields": fields_out}
    if provenance:
        spec["provenance"] = "optional caller metadata; never inferred permission"
    if forbidden:
        spec["forbidden_keys"] = sorted(forbidden)
    return spec


def _coerce_mapping(payload: Any, label: str, *, ignore_unknown: bool = True) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise ContractValidationError("invalid_payload", f"{label} must be a mapping", label)
    if ignore_unknown:
        return dict(payload)
    allowed = {item.name for item in fields(_model_for_label(label))} if label in _MODEL_BY_NAME else set(payload)
    unknown = set(payload) - allowed
    if unknown:
        raise ContractValidationError("unknown_fields", f"{label} has unknown fields: {sorted(unknown)}", label)
    return dict(payload)


def _model_for_label(label: str) -> Any:
    return _MODEL_BY_NAME[label]


_MODEL_BY_NAME = {
    "ApertureRequest": ApertureRequest,
    "ActiveStateSnapshot": ActiveStateSnapshot,
    "RequestedGrant": RequestedGrant,
    "EffectiveGrant": EffectiveGrant,
    "CandidateRef": CandidateRef,
    "EvidenceBlock": EvidenceBlock,
    "ExecutionBundle": ExecutionBundle,
    "AuditReceipt": AuditReceipt,
    "EnvironmentSpecPacket": EnvironmentSpecPacket,
}


def _validate_envelope(envelope: str) -> None:
    if envelope not in ENVELOPE_MODES:
        raise ContractValidationError(
            "invalid_envelope",
            f"envelope must be one of {ENVELOPE_MODES}",
            "RequestedGrant",
        )


def _validate_result_status(status: str) -> None:
    if status and status not in RESULT_STATUSES:
        raise ContractValidationError(
            "invalid_result_status",
            f"result_status must be one of {RESULT_STATUSES}",
            "AuditReceipt",
        )


def _string_list(value: Any) -> List[str]:
    if not value:
        return []
    return [str(item) for item in value]


def _is_string_list(value: Any, *, allow_empty: bool = False) -> bool:
    return isinstance(value, list) and (allow_empty or bool(value)) and all(isinstance(item, str) for item in value)


def _optional_str(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    return str(value)


def _optional_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    return bool(value)


def _dedupe_strings(values: Sequence[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def _find_forbidden_execution_keys(payload: Mapping[str, Any], *, prefix: str = "") -> Set[str]:
    forbidden: Set[str] = set()
    for key, value in payload.items():
        key_text = f"{prefix}.{key}" if prefix else str(key)
        normalized = str(key).lower()
        if normalized in EXECUTION_BUNDLE_FORBIDDEN_KEYS or normalized.endswith("_suppressed"):
            forbidden.add(key_text)
        if isinstance(value, str) and value.lower() in EXECUTION_BUNDLE_FORBIDDEN_VALUES:
            forbidden.add(key_text)
        if isinstance(value, dict):
            forbidden.update(_find_forbidden_execution_keys(value, prefix=key_text))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    forbidden.update(_find_forbidden_execution_keys(item, prefix=f"{key_text}[{index}]"))
                elif isinstance(item, str) and item.lower() in EXECUTION_BUNDLE_FORBIDDEN_VALUES:
                    forbidden.add(f"{key_text}[{index}]")
    return forbidden
