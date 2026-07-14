# Unified Framework Workspace Policy

This workspace is the canonical design authority for the metaphysical modeling foundation.

**Universal protocol:** [`docs/workspaces/WORKSPACE-AGENT-PROTOCOL.md`](../../WORKSPACE-AGENT-PROTOCOL.md)

Authority split:

- semantic truth: the version 1.1 framework paper
- coordination truth: the live workspace service for `unified-framework-synthesis`
- git truth: published continuity, handoff, task-pack, and workboard projections (mirrors only)

## Start here

Read in this order:

1. `README.md`
2. [`docs/workspaces/WORKSPACE-AGENT-PROTOCOL.md`](../../WORKSPACE-AGENT-PROTOCOL.md)
3. `sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md`
4. `derived/handoff.md`
5. `derived/foundation-build-plan.md`
6. `continuity/task-pack.md`

## Canonical precedence

The version 1.1 framework paper is normative. Earlier MTSF, SDS, ThoughtShape, comparative, synthesis, and philosophical documents are provenance and migration evidence.

When an older document conflicts with version 1.1 in primitive status, naming, branch semantics, lifecycle, Shape identity, profile architecture, conversation modeling, compilation, or build order, version 1.1 wins.

Do not delete or rewrite historical sources to make them appear consistent. Preserve their wording and map them through Appendix F of the canonical paper.

## Build discipline

- Build one universal kernel, governed profiles, and application projections.
- Do not recreate MTSF, SDS, ThoughtShape, or product surfaces as parallel ontologies.
- Every proposed implementation must identify the framework section, invariant, profile, acceptance test, and migration impact it serves.
- Capture and provenance must work without semantic extraction.
- State adoption requires explicit `StateCommitment`.
- Runtime packets are projections, not canonical stores.
- Applications may compose profiles but may not weaken kernel or profile invariants.
- Run the repo overview and engineering guard before implementation.
- Build a task pack before handing focused implementation to another agent.
- Query the live workspace before starting task-bound work.
- After live workspace mutations, run `python3 tools/workspace_projection_sync.py publish --workspace-id unified-framework-synthesis` (or `foundation sync-projections`).
- If the canonical framework version or workspace goal changes materially, create a successor workspace id instead of mutating an old live identity.

## Current boundary

The workspace is foundation-ready, not implementation-complete. The immediate task is schema lock and conformance scaffolding for Phases 1 and 2. Do not begin broad surfaces, unrestricted Pattern matching, autonomous compilation, durable personal signatures, or community clustering before their prerequisite gates pass.
