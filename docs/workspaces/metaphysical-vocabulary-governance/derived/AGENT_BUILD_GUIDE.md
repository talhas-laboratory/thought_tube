# Vocabulary Governance — Agent Build Guide

## Mission in the larger system

This program lets the system develop a shared language without erasing the language that people, domains, or branches actually use. It turns vocabulary evolution into provenance-bearing modeling work rather than a cleanup pass. It consumes Kernel record/type/provenance contracts and Branch-local interpretation rules; it provides safe type, mapping, promotion, deprecation, and migration contracts to every profile and application.

There is no dedicated vocabulary runtime yet. VOCAB-001 is a specification and governance task, not permission to normalize existing data. A useful early implementation may be small, but it must retain raw expression, scope, mapping kind, confidence, steward, version, and migration history.

## Read this in order

1. Framework v1.1 §8, §22, and §27.15.
2. Kernel [dependency contract](../../metaphysical-kernel-ontology/derived/dependency-contract-vocabulary-governance.md).
3. Branch [dependency contract](../../metaphysical-branch-reasoning/derived/dependency-contract-vocabulary-governance.md).
4. The Kernel and Branch build guides, then this workspace's manifest, gates, decisions, and live task context.
5. [Obligation register](./VOCABULARY_OBLIGATION_REGISTER.md) and [test/release guide](./VOCABULARY_TEST_AND_RELEASE_GUIDE.md).

## Five vocabulary levels

| Level | Meaning | Governance behavior |
|---|---|---|
| 1 — Kernel | Stable formal concepts from v1.1 | Only Kernel program may change them |
| 2 — Governed shared | Reusable relation/profile/domain concepts | Promotion, steward, version, compatibility required |
| 3 — Workspace | Project or organization concepts | Explicit scope and local stewardship |
| 4 — Model-local | Meaningful only in one branch/model | Never silently promoted or globalized |
| 5 — Raw expression/aliases | User language before normalization | Preserve verbatim with source/provenance |

Levels are not a quality ranking. They define where a term is valid and what governance is required to reuse it.

## Non-negotiable semantics

- A mapping is a record, not a rewrite. Preserve source type/expression, target, mapping kind, scope, confidence, and provenance.
- `equivalent`, `narrower`, `broader`, `overlaps`, and `analogous` have different consequences. None implies identity unless explicitly confirmed.
- Promotion is optional. The system remains useful with local and raw vocabulary.
- A workspace extension specializes a kernel concept; it never redefines `Claim`, `State`, `SourceFragment`, or another kernel term.
- Ontology evolution versions definitions; prior definitions remain addressable; affected records and stale derivatives are identified; migration is explicit and reversible.
- Branch-local mappings stay branch-local unless a governed process explicitly promotes them.

## Step-by-step build sequence

### VOCAB-001 — atomic obligations and governance lock

Define public records for `TypeDefinition` extension, vocabulary entry, raw expression/alias, term mapping, promotion record, deprecation/replacement, and evolution/migration report. For each, specify owner, fields, lifecycle axes, allowed scope, branch behavior, provenance, and failure/abstention behavior.

Write the promotion rubric: stable usage, clear definition, distinct identity, demonstrated reuse, compatibility, steward, and review outcome. Make it possible to decline promotion without treating the term as invalid.

### VOCAB-002 — registry and non-destructive mapping

Use the Kernel's existing `TypeDefinition` boundary where sufficient. Add a focused owner module only when the contract has two real users and engineering guard approves it. Build lookup and mapping operations that return the source term and mapping metadata, never just a substituted canonical label. Provide branch/scope-aware reads.

### VOCAB-003 — promotion and evolution workflow

Implement explicit proposal, review, approval/rejection, deprecation, replacement, and migration operations. Changing a type creates a version. The workflow identifies affected records, migrations, semantic-loss warnings, stale Shape/compiled artifacts, and downstream consumers. No destructive in-place type edit.

### VOCAB-004 — conformance suite

Test vocabulary preservation, invalid kernel redefinition, invalid parent/type constraints, scope leakage, branch-local promotion failure, ambiguous mapping abstention, reversible migration, and stale dependent notification. Test both machine-readable contracts and a fixture that starts from a user phrase.

### VOCAB-005 — dependency release

Publish type/mapping contract version, supported mapping kinds, promotion workflow, compatibility/migration policy, examples, tests, merge SHA, and known limits. Downstream profiles declare which vocabulary contract version they use.

## Integration rules

- Kernel owns the universal envelope and `TypeDefinition` semantics; Vocabulary owns governed evolution and mapping behavior.
- Branch owns whether an interpretation is local to a branch; Vocabulary records the term relationship without pretending it is globally true.
- Profile workspaces may request terms or extensions; they cannot bypass promotion for shared vocabulary.
- Applications render aliases and canonical labels as views; they do not mutate raw capture or establish semantic identity.

## Stop and escalate when

- a requested type changes a kernel definition;
- a mapping cannot distinguish equivalence from analogy or overlap;
- a user asks to replace raw language permanently;
- a local term is being promoted solely for convenience;
- an ontology change makes Shape, Pattern, or compiled records stale but no propagation owner is identified.

Use a parent decision record and linked tasks for every cross-workspace semantic change.
