# Vocabulary Governance — Obligation Register

| Area | Atomic obligation | Deliverable | Minimum test |
|---|---|---|---|
| §8.1 | Five levels are explicit and terms retain their level/scope | Vocabulary entry contract | A raw phrase remains retrievable after mapping |
| §8.2 | Promotion requires evidence and stewardship but is optional | Promotion record/workflow | Local term remains usable after promotion is declined |
| §8.3 | Mapping records express relation, scope, confidence, provenance | Term mapping contract | `analogous` does not behave as identity |
| §8.4 | Shared terms do not force shared interpretation | Read/consumer policy | Branch-local mapping is not exposed as global by default |
| §8.5 | Extensions specialize Kernel and declare constraints | Type extension validator | Attempt to redefine `Claim` or `State` fails |
| §8.6 | Changes are versioned, reversible, and impact-aware | Evolution/migration report | Prior definition resolves and dependent stale artifacts are listed |
| §22 | Governance status and promotion lifecycle remain separate from maturity/epistemic standing | Lifecycle matrix | Approved vocabulary term may still be epistemically unresolved |
| §27.15 | Vocabulary preservation is an acceptance test | Fixture corpus | Source expression, scope, and confidence survive mapping |

## Required mapping fields

`source_type_or_expression`, `target_type`, `mapping_kind`, `scope`, `branch_context` when applicable, `confidence`, `provenance`, `created_by`, `governance_status`, `version`, and `rationale`. Add `identity_confirmation` only when an explicit governing decision establishes actual identity.

## Required evolution fields

`prior_definition`, `new_definition`, compatibility classification, affected records, migration plan, reversibility, semantic-loss warnings, stale dependents, steward, review decision, and effective scope. A simple label rename is still a versioned event if consumers could observe it.
