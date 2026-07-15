# Branch Reasoning — Agent Build Guide

## Mission in the larger system

This program makes disagreement, uncertainty, alternative hypotheses, fictional worlds, and counterfactuals first-class without multiplying identities or forcing one global belief. It consumes Kernel identity, provenance, scope, branch membership, and state-commitment contracts. It owns the rules that determine what a branch inherits, retracts, conflicts with, merges, or may use in inference.

There is no dedicated Branch runtime module yet. That is intentional: BRANCH-001 must first turn §7 into a bounded, testable public contract. Do not hide branch behavior inside a profile, application, migration mapper, or LLM prompt.

## Read this in order

1. Framework v1.1 §7, §20, §§27.2 and 27.16.
2. Kernel's [dependency contract](../../metaphysical-kernel-ontology/derived/dependency-contract-branch-reasoning.md) and [build guide](../../metaphysical-kernel-ontology/derived/AGENT_BUILD_GUIDE.md).
3. This workspace's manifest, gates, decisions, and live task context.
4. [Obligation register](./BRANCH_OBLIGATION_REGISTER.md) and [test/release guide](./BRANCH_TEST_AND_RELEASE_GUIDE.md).

## What this workspace owns

| Own | Do not own |
|---|---|
| Branch inheritance and visibility | Universal record identity or envelope |
| Four-valued support within branch and scope | Global truth or automatic belief selection |
| Explicit negation and conflict classification | Vocabulary meaning or term promotion |
| Merge assessment and unresolved results | State adoption rules |
| Inference request policy, candidate output, abstention | Execution compilation or application-specific shortcuts |
| Branch ensembles and task-scoped weighting | Universal probability claims |

## Semantic model to preserve

A branch is an explicitly scoped coherent selection of records, assumptions, and interpretations. A child branch inherits from its parent as a read rule; it does not physically duplicate shared records. It can retract, replace, add conflicting claims, or alter scope/assumptions.

Support is evaluated within a `(claim, branch, scope)` context. The result is exactly one of `supported_only`, `opposed_only`, `both`, or `unresolved`. It reports evidence status; it does not automatically decide truth. A conflict must be classified: logical contradiction, incompatible measurement, perspective divergence, temporal change, scope difference, semantic ambiguity, or competing causal explanation.

Inference produces candidate Claims with Provenance. On `both`, it must preserve alternatives, branch, ask for clarification, or abstain. Fluency, majority, or narrative coherence is never a valid implicit tie-breaker.

## Step-by-step build sequence

### BRANCH-001 — atomic obligations and interface lock

Write the public data contracts for inheritance query, support assessment, conflict record, merge assessment, and inference context/result. Name the input records from Kernel, output records, error/absence behavior, provenance, scope compatibility, and versioning policy. Use table-driven examples before choosing storage or APIs.

Decide the smallest owner module only after engineering guard. The expected pattern is a focused `metaphysical_branch_*` owner plus tests, not branch conditionals spread across kernel/runtime/application modules. Keep kernel validation responsible for foundational membership and scope facts; the Branch program consumes them.

### BRANCH-002 — support and inheritance semantics

Implement parent-to-child read resolution with explicit retraction/replacement behavior. Build support from linked Evidence and explicit polarity, always scoped. Prove source fragments and referents can be shared while branch-bound Claims and States require membership. Test every four-valued outcome and at least one false-positive conflict that is actually a scope or time difference.

### BRANCH-003 — merge and inference policy

Create a `MergeAssessment`; it reports shared records, compatible additions, conflicts, divergent assumptions, scope differences, identity mappings, and unresolved items. It must never silently choose a winner. Define inference requests with branch/scope/perspective/lifecycle filters, contradiction policy, and candidate-only output. Provide explicit abstention reasons.

### BRANCH-004 — adversarial conformance

Test cross-branch leakage, inherited retraction, conflicting evidence, scope mismatch, merge-without-winner, inference over `both`, source reuse, and bounded traversal. Add a regression case for every repaired ambiguity.

### BRANCH-005 — dependency release

Publish versions and examples for Vocabulary, Conversation/Formation, Shape, Pattern, and Agent programs. State supported operations, unsupported Phase-1 behavior, compatibility, migration, and test evidence. Consumers must pin or declare the consumed version.

## Integration rules

- Kernel G3 is the minimum runtime dependency; Kernel G5 is required for stable consumer release.
- Vocabulary must retain branch-local mappings and cannot promote one branch's term interpretation as universal.
- Shape and Pattern can consume branch-aware selection but cannot infer equivalence or causality from branch coexistence.
- Execution may compile only an explicitly selected and validated branch view; descriptive branches do not become runnable models.

## Stop and escalate when

- branch behavior needs a new universal record concept;
- a conflict classification requires changing vocabulary semantics;
- merge asks the system to pick a winner automatically;
- a consumer wants to use branch weight as a universal truth probability;
- inference would output a State, executable rule, or promoted type directly.

Open a parent change record and coordinate with the actual owner.
