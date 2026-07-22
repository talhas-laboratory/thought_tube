# ADR-003 — Kernel Bounded View as Optional Epistemic Backend

**Status:** accepted  
**Date:** 2026-07-19  
**Workspace:** `cognitive-aperture-exceptional`  
**Task:** CAE-011

## Context

ADR-001 listed kernel bounded views among several partial disclosure mechanisms. GAP_MAP G11 required an explicit decision: wire the metaphysical kernel bounded view as an optional epistemic evidence backend under an explicit grant, or demote it as a separate system and remove integration claims.

The kernel foundation runtime already enforces branch/scope isolation, retraction exclusion, and depth truncation in `query_bounded_view()`. The disclosure aperture already consumes external read ports for corpus, candidate search, and Shape projections (ADR-002). No conformance test previously connected the two systems.

## Decision

**Wire, do not demote.**

The kernel bounded view is exposed to the disclosure program only through `bounded_view_disclosure_adapter` and the `BoundedViewEpistemicPort`. It is an optional, default-off epistemic evidence backend that:

1. Requires an `EffectiveGrant` with explicit `branch_id` and `scope_id` in grant provenance.
2. Requires explicit root record IDs via `explicit_pins` or `kernel:`-prefixed `effective_refs`.
3. Returns reference-only evidence blocks (`kernel:{record_id}`) with branch, scope, depth, and epistemic status metadata.
4. Never copies claim text, source fragments, or other canonical record content into disclosure artifacts.
5. Never writes to the foundation store; read-only queries only.
6. Abstains when branch/scope/roots are missing or the foundation store is unavailable.

The bounded view does **not** replace `CandidateSearch`, `ShapeProjectionReader`, or task-pack/feed adapters. It supplements epistemic graph traversal when a caller holds an explicit grant over kernel record roots.

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Demote as permanently separate | Leaves G11 unresolved; manifest already lists kernel as external dependency with CAE-011 as the only widen point |
| Full bridge-bundle integration in v1 | Would mix epistemic graph nodes into lexical retrieval ranking; deferred until a surface owner requests it |
| Duplicate kernel records into semantic capsules | Violates D-003 one-source rule and ADR-002 ownership boundary |

## Consequences

- Feature flag `disclosure.bounded_view.epistemic_backend_v1` defaults to `false`.
- Conformance tests prove branch isolation, reference-only blocks, and no store mutation.
- Product/architecture docs must not claim bounded view is on the default Bridge/Holodeck path until a surface adapter opts in.
- Rollback is configuration-only.

## Links

- [`ADR-001`](./ADR-001-orient-grant-evidence-receipt.md)
- [`ADR-002`](./ADR-002-modular-disclosure-boundary.md)
- [`GAP_MAP.md`](./GAP_MAP.md) G11
- `src/conversation_os/bounded_view_disclosure_adapter.py`
