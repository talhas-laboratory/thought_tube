"""Bounded application SDK over the metaphysical kernel (framework v1.1 Workstream 4, Gate F4)."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from conversation_os.metaphysical_kernel import ProfileDefinition
from conversation_os.metaphysical_kernel_profile_registry import (
    FIELD_FORMATION_PROFILE_ID,
    FIELD_FORMATION_PROFILE_VERSION,
    ProfileRegistry,
)
from conversation_os.metaphysical_kernel_runtime import (
    BoundedViewQuery,
    FoundationRuntime,
)

MODULE_ID = "kernel.metaphysical.application_sdk"
CONTRACT_VERSION = "1.1.0"

WORLD_STUDIO_APPLICATION_ID = "app:world_studio"
WORKSPACE_CURATOR_APPLICATION_ID = "app:workspace_curator"


@dataclass
class ApplicationContext:
    application_id: str
    actor: str
    branch_id: str
    scope_id: str
    profile_id: str = FIELD_FORMATION_PROFILE_ID
    profile_version: str = FIELD_FORMATION_PROFILE_VERSION
    context_budget: int = 32
    authorized: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SdkMutationResult:
    operation: str
    success: bool
    record_ids: Dict[str, str] = field(default_factory=dict)
    branch_id: str = ""
    scope_id: str = ""
    provenance_id: str = ""
    validation_errors: List[str] = field(default_factory=list)
    compensating_operation: str = ""
    abstained: bool = False
    reason: str = ""
    projection: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class FoundationApplicationSdk:
    """Profile-bound SDK returning identifiers, provenance, and validation for every mutation."""

    def __init__(self, root: Path, context: ApplicationContext) -> None:
        self.root = root
        self.context = context
        self.runtime = FoundationRuntime(root, actor=context.actor)
        self.registry = ProfileRegistry(self.runtime)
        self._budget_spent = 0
        self._ensure_profile_stack()

    def _ensure_profile_stack(self) -> None:
        self.registry.bootstrap_field_formation_profile()
        if not self.registry.get_binding(self.context.application_id):
            self.registry.bind_application(
                application_id=self.context.application_id,
                profile_id=self.context.profile_id,
                profile_version=self.context.profile_version,
                required_invariants=[
                    "no_claim_without_branch_membership",
                    "no_state_without_state_commitment",
                ],
            )

    def _abstain(self, operation: str, reason: str) -> SdkMutationResult:
        return SdkMutationResult(
            operation=operation,
            success=False,
            branch_id=self.context.branch_id,
            scope_id=self.context.scope_id,
            abstained=True,
            reason=reason,
            compensating_operation="none_required",
        )

    def _authorize(self, operation: str) -> Optional[SdkMutationResult]:
        if not self.context.authorized:
            return self._abstain(operation, "authorization_denied")
        return None

    def _consume_budget(self, operation: str, cost: int = 1) -> Optional[SdkMutationResult]:
        if self._budget_spent + cost > self.context.context_budget:
            return self._abstain(operation, "context_budget_exceeded")
        self._budget_spent += cost
        return None

    def _result(
        self,
        operation: str,
        *,
        record_ids: Optional[Dict[str, str]] = None,
        provenance_id: str = "",
        projection: Optional[Dict[str, Any]] = None,
        compensating_operation: str = "",
    ) -> SdkMutationResult:
        validation_errors = self.runtime.validate_current_bundle()
        return SdkMutationResult(
            operation=operation,
            success=not validation_errors,
            record_ids=dict(record_ids or {}),
            branch_id=self.context.branch_id,
            scope_id=self.context.scope_id,
            provenance_id=provenance_id,
            validation_errors=validation_errors,
            compensating_operation=compensating_operation or f"retract:{operation}",
            projection=dict(projection or {}),
        )

    def capture_source(
        self,
        *,
        content_pointer: str,
        integrity_hash: str,
        author_or_origin: Optional[str] = None,
        source_kind: str = "user_input",
    ) -> SdkMutationResult:
        operation = "capture_source"
        denied = self._authorize(operation) or self._consume_budget(operation)
        if denied:
            return denied
        fragment = self.runtime.capture_source_fragment(
            content_pointer=content_pointer,
            author_or_origin=author_or_origin or self.context.actor,
            integrity_hash=integrity_hash,
            source_kind=source_kind,
        )
        self.runtime.ensure_scope(self.context.scope_id)
        self.runtime.ensure_branch(self.context.branch_id)
        return self._result(
            operation,
            record_ids={"source_fragment_id": fragment["envelope"]["id"]},
            provenance_id=str(fragment["envelope"]["provenance_id"]),
        )

    def capture_source_from_event(self, event: Mapping[str, Any]) -> SdkMutationResult:
        operation = "capture_source"
        denied = self._authorize(operation) or self._consume_budget(operation)
        if denied:
            return denied
        fragment = self.runtime.capture_from_conversation_event(event)
        self.runtime.ensure_scope(self.context.scope_id)
        self.runtime.ensure_branch(self.context.branch_id)
        return self._result(
            operation,
            record_ids={"source_fragment_id": fragment["envelope"]["id"]},
            provenance_id=str(fragment["envelope"]["provenance_id"]),
        )

    def create_branch(self, *, branch_kind: str = "interpretation", parent_branch_id: str = "") -> SdkMutationResult:
        operation = "create_branch"
        denied = self._authorize(operation) or self._consume_budget(operation)
        if denied:
            return denied
        branch = self.runtime.ensure_branch(
            self.context.branch_id,
            parent_branch_id=parent_branch_id,
            branch_kind=branch_kind,
        )
        return self._result(
            operation,
            record_ids={"branch_id": branch["envelope"]["id"]},
            provenance_id=str(branch["envelope"]["provenance_id"]),
        )

    def attach_branch_membership(
        self,
        *,
        record_id: str,
        provenance_id: str,
        membership_kind: str = "asserted",
    ) -> SdkMutationResult:
        operation = "attach_branch_membership"
        denied = self._authorize(operation) or self._consume_budget(operation)
        if denied:
            return denied
        membership = self.runtime.attach_branch_membership(
            record_id=record_id,
            branch_id=self.context.branch_id,
            scope_id=self.context.scope_id,
            provenance_id=provenance_id,
            membership_kind=membership_kind,
        )
        return self._result(
            operation,
            record_ids={
                "branch_membership_id": membership["envelope"]["id"],
                "record_id": record_id,
            },
            provenance_id=provenance_id,
        )

    def assert_claim(
        self,
        *,
        predicate: str,
        arguments: List[str],
        provenance_id: str,
    ) -> SdkMutationResult:
        operation = "assert_claim"
        denied = self._authorize(operation) or self._consume_budget(operation)
        if denied:
            return denied
        claim = self.runtime.assert_claim(
            predicate=predicate,
            arguments=arguments,
            branch_id=self.context.branch_id,
            scope_id=self.context.scope_id,
            claimant=self.context.actor,
            provenance_id=provenance_id,
        )
        return self._result(
            operation,
            record_ids={"claim_id": claim["envelope"]["id"]},
            provenance_id=provenance_id,
        )

    def commit_state(
        self,
        *,
        source_claim_ids: List[str],
        subject_refs: List[str],
        state_type: str,
        value: Any,
        value_type: str,
        provenance_id: str,
    ) -> SdkMutationResult:
        operation = "commit_state"
        denied = self._authorize(operation) or self._consume_budget(operation, cost=2)
        if denied:
            return denied
        adoption = self.runtime.commit_state_from_claims(
            source_claim_ids=source_claim_ids,
            branch_id=self.context.branch_id,
            scope_id=self.context.scope_id,
            subject_refs=subject_refs,
            state_type=state_type,
            value=value,
            value_type=value_type,
            provenance_id=provenance_id,
            responsible_actor=self.context.actor,
        )
        return self._result(
            operation,
            record_ids={
                "state_id": adoption["state"]["envelope"]["id"],
                "state_commitment_id": adoption["state_commitment"]["envelope"]["id"],
            },
            provenance_id=provenance_id,
        )

    def hold_field(
        self,
        *,
        content_pointer: str,
        integrity_hash: str,
        hold_reason: str,
    ) -> SdkMutationResult:
        operation = "hold_field"
        denied = self._authorize(operation) or self._consume_budget(operation)
        if denied:
            return denied
        fragment = self.runtime.capture_source_fragment(
            content_pointer=content_pointer,
            author_or_origin=self.context.actor,
            integrity_hash=integrity_hash,
            maturity_status="held",
        )
        return self._result(
            operation,
            record_ids={"source_fragment_id": fragment["envelope"]["id"]},
            provenance_id=str(fragment["envelope"]["provenance_id"]),
            projection={"hold_reason": hold_reason, "profile_record_type": "hold"},
        )

    def derive_formation(
        self,
        *,
        root_referent_id: str,
        supporting_claim_ids: List[str],
        coherence_basis: str,
        stability: str = "provisional",
    ) -> SdkMutationResult:
        operation = "derive_formation"
        denied = self._authorize(operation) or self._consume_budget(operation)
        if denied:
            return denied
        if not coherence_basis:
            return self._abstain(operation, "formation_requires_coherence_basis")
        return self._result(
            operation,
            record_ids={"root_referent_id": root_referent_id},
            projection={
                "profile_record_type": "formation",
                "root_referents": [root_referent_id],
                "supporting_claims": list(supporting_claim_ids),
                "coherence_basis": coherence_basis,
                "stability": stability,
            },
            compensating_operation="release_formation_projection",
        )

    def derive_shape(self, *, anchor_claim_id: str) -> SdkMutationResult:
        operation = "derive_shape"
        denied = self._authorize(operation)
        if denied:
            return denied
        return self._abstain(
            operation,
            "profile:shape_and_semantic_addressing not registered in Phase 1; canonical records preserved",
        )

    def build_bounded_view(self, *, root_record_ids: List[str], max_depth: int = 3) -> SdkMutationResult:
        operation = "build_bounded_view"
        denied = self._authorize(operation) or self._consume_budget(operation)
        if denied:
            return denied
        view = self.runtime.query_bounded_view(
            BoundedViewQuery(
                branch_id=self.context.branch_id,
                scope_id=self.context.scope_id,
                root_record_ids=root_record_ids,
                max_depth=max_depth,
            )
        )
        return self._result(
            operation,
            projection=view.to_dict(),
            compensating_operation="none_required",
        )

    def trace_provenance(self, *, start_record_id: str) -> SdkMutationResult:
        operation = "trace_provenance"
        denied = self._authorize(operation) or self._consume_budget(operation)
        if denied:
            return denied
        trace = self.runtime.trace_provenance(start_record_id)
        return self._result(
            operation,
            record_ids={"start_record_id": start_record_id},
            projection=trace.to_dict(),
            compensating_operation="none_required",
        )

    def register_profile(self, profile: ProfileDefinition) -> SdkMutationResult:
        operation = "register_profile"
        denied = self._authorize(operation) or self._consume_budget(operation, cost=2)
        if denied:
            return denied
        registered = self.registry.register(profile)
        return self._result(
            operation,
            record_ids={"profile_definition_id": registered["envelope"]["id"]},
            provenance_id=str(registered["envelope"]["provenance_id"]),
        )

    def validate_profile(self, *, evaluated_record_id: str = "bundle") -> SdkMutationResult:
        operation = "validate_profile"
        denied = self._authorize(operation) or self._consume_budget(operation)
        if denied:
            return denied
        result = self.registry.evaluate_conformance(
            profile_id=self.context.profile_id,
            profile_version=self.context.profile_version,
            evaluated_record_id=evaluated_record_id,
        )
        return self._result(
            operation,
            record_ids={"conformance_result_id": result.envelope.id},
            provenance_id=result.envelope.provenance_id,
            projection={"passed": result.passed, "violations": list(result.violations)},
        )

    def bind_application_profile(self, *, required_invariants: List[str]) -> SdkMutationResult:
        operation = "bind_application_profile"
        denied = self._authorize(operation) or self._consume_budget(operation)
        if denied:
            return denied
        binding = self.registry.bind_application(
            application_id=self.context.application_id,
            profile_id=self.context.profile_id,
            profile_version=self.context.profile_version,
            required_invariants=required_invariants,
        )
        return self._result(
            operation,
            projection=binding.to_dict(),
            compensating_operation="unbind_application_profile",
        )


def world_studio_capture_scene(
    sdk: FoundationApplicationSdk,
    *,
    world_id: str,
    scene_text: str,
    element_label: str,
) -> Dict[str, Any]:
    """World Studio consumer: fictional-world capture without a private ontology."""
    capture = sdk.capture_source(
        content_pointer=f"world-studio://{world_id}/scene",
        integrity_hash=f"sha256:{world_id}:{len(scene_text)}",
        source_kind="user_input",
    )
    if not capture.success:
        return {"application": WORLD_STUDIO_APPLICATION_ID, "capture": capture.to_dict()}

    referent = sdk.runtime.resolve_referent(element_label)
    claim = sdk.assert_claim(
        predicate="appears_in_scene",
        arguments=[referent["envelope"]["id"], world_id],
        provenance_id=capture.provenance_id,
    )
    formation = sdk.derive_formation(
        root_referent_id=referent["envelope"]["id"],
        supporting_claim_ids=[claim.record_ids.get("claim_id", "")],
        coherence_basis=f"scene evidence from {world_id}",
    )
    view = sdk.build_bounded_view(root_record_ids=[claim.record_ids.get("claim_id", "")])
    trace = sdk.trace_provenance(start_record_id=claim.record_ids.get("claim_id", ""))
    validation = sdk.validate_profile()

    return {
        "application": WORLD_STUDIO_APPLICATION_ID,
        "capture": capture.to_dict(),
        "claim": claim.to_dict(),
        "formation": formation.to_dict(),
        "bounded_view": view.to_dict(),
        "provenance_trace": trace.to_dict(),
        "validation": validation.to_dict(),
    }


def workspace_curator_capture_insight(
    sdk: FoundationApplicationSdk,
    *,
    workspace_id: str,
    statement: str,
    adopt_as_state: bool = False,
) -> Dict[str, Any]:
    """Workspace Curator consumer: workspace knowledge without a private ontology."""
    event = {
        "event_id": f"evt-{workspace_id}",
        "session_id": workspace_id,
        "timestamp": "2026-07-12T14:00:00+00:00",
        "actor": sdk.context.actor,
        "kind": "insight",
        "content": statement,
    }
    capture = sdk.capture_source_from_event(event)
    if not capture.success:
        return {"application": WORKSPACE_CURATOR_APPLICATION_ID, "capture": capture.to_dict()}

    referent = sdk.runtime.resolve_referent(f"workspace:{workspace_id}")
    claim = sdk.assert_claim(
        predicate="workspace_insight",
        arguments=[referent["envelope"]["id"], statement],
        provenance_id=capture.provenance_id,
    )

    adoption: Optional[SdkMutationResult] = None
    if adopt_as_state:
        adoption = sdk.commit_state(
            source_claim_ids=[claim.record_ids.get("claim_id", "")],
            subject_refs=[referent["envelope"]["id"]],
            state_type="workspace:insight",
            value=statement,
            value_type="literal",
            provenance_id=capture.provenance_id,
        )

    held = sdk.hold_field(
        content_pointer=f"workspace://{workspace_id}/open-questions",
        integrity_hash=f"sha256:{workspace_id}:hold",
        hold_reason="awaiting review",
    )
    view = sdk.build_bounded_view(root_record_ids=[claim.record_ids.get("claim_id", "")])
    validation = sdk.validate_profile()

    payload: Dict[str, Any] = {
        "application": WORKSPACE_CURATOR_APPLICATION_ID,
        "capture": capture.to_dict(),
        "claim": claim.to_dict(),
        "hold": held.to_dict(),
        "bounded_view": view.to_dict(),
        "validation": validation.to_dict(),
    }
    if adoption:
        payload["adoption"] = adoption.to_dict()
    return payload


__all__ = [
    "MODULE_ID",
    "CONTRACT_VERSION",
    "WORLD_STUDIO_APPLICATION_ID",
    "WORKSPACE_CURATOR_APPLICATION_ID",
    "ApplicationContext",
    "SdkMutationResult",
    "FoundationApplicationSdk",
    "world_studio_capture_scene",
    "workspace_curator_capture_insight",
]
