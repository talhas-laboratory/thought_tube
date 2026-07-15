# Kernel Ontology — Agent Build Guide

## Mission in the larger system

This program owns the smallest shared language in which every later profile and application can model something without creating a competing database or ontology. Its work makes identity, scope, provenance, branches, lifecycle, and profile grounding dependable. It does not decide what a domain means beyond the universal concepts.

The kernel is upstream of every child workspace. A change here is high-leverage and therefore must be additive, versioned, and conformance-tested. The current repository already contains the Phase 1 vertical slice. Treat it as evidence to audit and extend, not as a blank implementation surface.

## Read this in order

1. The parent [program hierarchy plan](../../unified-framework-synthesis/derived/program-workspace-hierarchy-plan.md).
2. Framework v1.1 §§4–6, §§21–25, and §29.
3. [Phase 1 implementation review](../../../workboards/unified-metaphysical-foundation/PHASE-1-IMPLEMENTATION-REVIEW.md).
4. This workspace's `manifest.json`, `GATES.md`, `DECISIONS.md`, and live task context.
5. [Obligation register](./KERNEL_OBLIGATION_REGISTER.md) and [test/release guide](./KERNEL_TEST_AND_RELEASE_GUIDE.md).

## Current implementation map

| Boundary | Existing owner | Role |
|---|---|---|
| Record dataclasses | `src/conversation_os/metaphysical_kernel.py` | Universal envelope and Phase 1 records |
| Validators/loaders | `src/conversation_os/metaphysical_kernel_contracts.py` | Invariants and fixture validation |
| Append-only persistence | `src/conversation_os/metaphysical_kernel_store.py` | Kernel event log and folded view |
| Minimal runtime | `src/conversation_os/metaphysical_kernel_runtime.py` | Capture, claim, state, bounded view, provenance trace |
| Historical migration | `src/conversation_os/metaphysical_kernel_migration.py` | MTSF, SDS, ThoughtShape, Conversation OS mappings |
| Profile registry | `src/conversation_os/metaphysical_kernel_profile_registry.py` | Profile registration and conformance |
| Application boundary | `src/conversation_os/metaphysical_kernel_application_sdk.py` | Shared-store consumer access |

Do not create a new kernel package unless the engineering guard proves the existing owner modules cannot carry the change.

## Non-negotiable semantics

- A `Claim` is not a `State`. State adoption requires a branch-, scope-, provenance-, and actor-bound `StateCommitment`.
- The universal envelope never forces a single `branch_id`; interpretive participation uses `BranchMembership`.
- Source fragments, referents, reusable types, and provenance may be shared across branches without duplication.
- Maturity, epistemic standing, and governance status are three independent axes.
- Every non-raw record has a derivation path to a source, imported authority, or explicit creation.
- Profiles extend kernel records but never redefine kernel semantics. Applications are projections, not alternate stores.

## Step-by-step build sequence

### KERNEL-001 — atomic obligations and contract lock

Convert each assigned paper requirement into an atomic row with source section, record or invariant, current code owner, test, consumer impact, and uncertainty. Reconcile that register against the existing Phase 1 code before proposing any schema change. Identify what is already complete, what is intentionally Phase-1-minimal, and what is genuinely absent.

Produce a versioned public contract describing fields, nullability, cardinality, branch behavior, lifecycle applicability, migration behavior, and forbidden interpretations. Open a parent decision if the paper is ambiguous or an extension would affect other programs.

### KERNEL-002 — persistence and migration fixtures

Use the migration module and fixtures to prove preservation of source identity, provenance, branch membership, commitment links, and semantic-loss warnings. Add a fixture before or alongside each migration behavior. A migration may defer a richer profile concept, but must say so explicitly rather than flattening it into a kernel type.

### KERNEL-003 — minimal runtime operations

Only add operations justified by a contract and at least one downstream consumer. Prefer an end-to-end path through the existing `FoundationRuntime` and SDK over isolated helpers. Every mutation needs provenance, validation, and a reversible or compensating behavior where meaningful.

### KERNEL-004 — conformance suite

Run paper-derived acceptance tests plus adversarial tests: cross-branch contamination, State/Claim collapse, missing provenance, lifecycle collapse, invalid profile redefinition, and invalid commitment links. Add regression fixtures for every repaired defect.

### KERNEL-005 — dependency release

Publish a contract version for Branch and Vocabulary with a compatibility statement, known limits, test evidence, and exact merge SHA. A consumer may design against a draft; it cannot claim integration against it until this gate passes.

## Change protocol

Before code: refresh repo overview, run engineering guard against the smallest existing owner module, read live task context, and claim only one task. During work: preserve append-only logs, add tests with behavior, and record uncertainty. After live coordination changes: publish the workspace projection, check freshness, commit intentional files, and push.

## Stop and escalate when

- a change would redefine a kernel concept to satisfy one profile;
- a branch or vocabulary policy requires changing identity, provenance, or lifecycle rules;
- a migration would discard a raw term or source reference;
- an application needs a separate canonical store;
- two workspaces appear to own the same invariant.

Use the parent workspace to record the decision and create linked provider/consumer work before proceeding.
