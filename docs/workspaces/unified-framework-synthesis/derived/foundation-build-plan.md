# Unified Metaphysical Framework Foundation Build Plan

**Status:** Active execution bridge  
**Authority:** `../sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md`  
**Current boundary:** Schema lock and Phase 1 foundation slice

## Outcome

Build an application substrate in which new products can compose governed metaphysical modeling profiles without creating new ontologies or weakening epistemic guarantees.

```text
canonical paper
→ machine-readable contracts
→ conformance and migration suite
→ executable kernel
→ governed profile runtime
→ application SDK
→ application projections
```

The paper remains the normative source. This plan controls sequencing; it does not redefine framework semantics.

## Architecture

The implementation has three layers:

1. **Universal kernel** — records, identity, branch membership, scope, evidence, provenance, lifecycles, and vocabulary.
2. **Profile runtime** — versioned profile definitions, dependencies, invariants, transformations, projections, and conformance results.
3. **Application SDK** — bounded APIs for selecting profiles, vocabularies, branches, views, and operations.

Applications such as Thought Trace, Inner Space Curator, World Studio, organizational modeling, and simulation are consumers. They are not foundation owners.

## Workstream 0 — Contract extraction

Produce machine-readable specifications for:

- the universal record envelope;
- the twelve kernel concepts;
- `BranchMembership`;
- `StateCommitment`;
- maturity, epistemic, and governance lifecycles;
- `ProfileDefinition` and `ProfileConformanceResult`;
- dependency invalidation and promotion events.

Each contract must cite its framework section and include valid fixtures, invalid fixtures, and migration notes.

### Gate F0

- Terms have one canonical name.
- Every field has type, cardinality, nullability, and lifecycle behavior.
- Branch-neutral and branch-bound records are distinguished.
- Claim-to-State adoption is impossible without `StateCommitment`.
- Lifecycle axes cannot be collapsed into one status.

## Workstream 1 — Historical and current-state migration

Create deterministic fixtures for:

- MTSF entities, assertions, evidence, Shapes, and stencils;
- ThoughtShape dimensions, stations, facets, StateClaims, and Holds;
- SDS states, constraints, loops, movement signatures, and AntiMatches;
- current Conversation OS sessions, events, concepts, formations, cards, workspaces, and knowledge records.

Every mapping must preserve source vocabulary, source identity, confidence, provenance, semantic-loss warnings, and reversibility.

### Gate F1

- No historical source is silently rewritten.
- Analogy never migrates as identity.
- Claim never migrates as State without a commitment fixture.
- Round-trip or loss-report tests exist for every supported source family.

## Workstream 2 — Phase 1 vertical slice

Implement the smallest complete path:

```text
capture SourceFragment
→ create or resolve Referent
→ create Scope and ModelBranch
→ attach BranchMembership
→ create candidate Claim and Evidence
→ optionally commit a represented State
→ revise or retract
→ query a BoundedView
→ traverse complete Provenance
```

Raw capture must succeed when every inference, embedding, LLM, graph projection, and profile service is unavailable.

### Gate F2

- Append-only source durability passes failure-injection tests.
- Contradictory branches remain non-explosive.
- Retraction invalidates dependent projections.
- Unauthorized or unbounded traversal fails closed.
- Every derived record terminates in a source or explicit creation event.

## Workstream 3 — Profile registry

Implement:

- profile registration and semantic versioning;
- acyclic dependency validation;
- profile record-type registration;
- invariant and transformation registration;
- bounded-view and promotion rules;
- application-to-profile bindings;
- migration compatibility checks.

Begin with the Field and Formation Profile. Shape, Conversation, Pattern, Agent, and Execution profiles follow only after the registry proves conformance and version migration.

### Gate F3

- An application cannot register a parallel kernel type.
- A profile cannot redefine kernel semantics.
- Dependency cycles are rejected.
- Profile upgrades identify stale records and projections.
- Application bindings cannot weaken invariants.

## Workstream 4 — Application SDK

Expose bounded contracts such as:

```text
capture_source
create_branch
attach_branch_membership
commit_state
hold_field
derive_formation
derive_shape
build_bounded_view
trace_provenance
register_profile
validate_profile
bind_application_profile
```

The SDK must return identifiers, branch, scope, provenance, validation results, and rollback or compensating-operation information for every mutation.

### Gate F4

- Two materially different applications can use the same kernel and profile contracts.
- Neither application requires a private persistence ontology.
- Authorization and context budgets apply before projection construction.
- A profile or backend may abstain without corrupting the canonical record universe.

## Verification strategy

1. JSON/schema validation for every contract.
2. Property-based tests for identity, branch, lifecycle, provenance, and profile invariants.
3. Golden semantic fixtures from Appendix D of the paper.
4. Migration tests against historical and current record families.
5. Failure-injection tests around raw capture and dependency propagation.
6. End-to-end traces from source to bounded view and source to committed State.
7. Application conformance tests using at least two profile compositions.

No aggregate score may hide failure of a load-bearing invariant.

## Repo implementation posture

Before creating new owners, audit:

- `src/conversation_os/models.py`
- `src/conversation_os/storage.py`
- `src/conversation_os/conversation_synthesis.py`
- `src/conversation_os/knowledge_layer.py`
- `src/conversation_os/holodeck.py`
- `src/conversation_os/pipelines.py`
- `src/conversation_os/operators.py`

Reuse low-level durability and proven behavior where semantics match. Wrap or migrate incompatible semantics explicitly. Do not collapse source and derived layers into one file, and do not insert product-specific behavior into the kernel.

## First focused task

The next task pack should cover only Workstream 0:

> Extract and lock the machine-readable universal envelope, eight-record MVP, `BranchMembership`, `StateCommitment`, and the three lifecycle axes, with valid/invalid fixtures and no runtime behavior beyond validation.

Implementation should not begin until the proposed owner paths pass the engineering guard.
