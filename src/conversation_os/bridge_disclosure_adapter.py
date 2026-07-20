"""Bridge surface adapter for the shared disclosure service (CAE-005A)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from .disclosure_ports import CandidateSearchPort, DisclosurePorts, build_inner_world_ports
from .disclosure_service import DisclosureService, build_default_disclosure_service


MODULE_ID = "kernel.disclosure.bridge_adapter"
CONTRACT_VERSION = "1.0"

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "assemble_bridge_context_bundle",
    "disclose_for_bridge",
    "create_bridge_disclosure_service",
)
__all__ = list(PUBLIC_API)


def assemble_bridge_context_bundle(
    root: Path,
    context_state: Dict[str, Any],
    *,
    budget: Dict[str, Any] | None = None,
    candidate_search: CandidateSearchPort | None = None,
) -> Dict[str, Any]:
    from .reasoning_bridge import _assemble_bridge_context_bundle_impl

    return _assemble_bridge_context_bundle_impl(
        root,
        context_state,
        budget=budget,
        candidate_search=candidate_search,
    )


def create_bridge_disclosure_service(*, ports: DisclosurePorts | None = None) -> DisclosureService:
    return build_default_disclosure_service(
        assemble_bridge_bundle=assemble_bridge_context_bundle,
        ports=ports or build_inner_world_ports(),
    )


def disclose_for_bridge(
    root: Path,
    context_state: Mapping[str, Any],
    *,
    budget: Mapping[str, Any] | None = None,
    service: DisclosureService | None = None,
) -> Dict[str, Any]:
    active = service or create_bridge_disclosure_service()
    return active.disclose_for_bridge(root, context_state, budget=budget)
