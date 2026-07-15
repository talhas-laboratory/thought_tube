# Kernel Ontology — Obligation Register

This is the executable reading map for KERNEL-001. Refine each row into atomic records in the parent coverage registry before G1.

**KERNEL-001 output:** the machine-readable matrix lives in [`KERNEL_ATOMIC_OBLIGATIONS.json`](./KERNEL_ATOMIC_OBLIGATIONS.json) and the locked public boundary in [`KERNEL_PUBLIC_CONTRACT_LOCK.md`](./KERNEL_PUBLIC_CONTRACT_LOCK.md). “Existing” means a Phase 1 owner exists, not that the full paper obligation is closed.

| Area | Normative obligation | Existing evidence | Required next evidence |
|---|---|---|---|
| §4.1 | Common envelope with identity, scope, version, provenance, three lifecycle axes, visibility | `KernelRecordEnvelope`, contract fixtures | Field-by-field compatibility and migration contract |
| §4.2 | Twelve universal concepts are the only kernel concepts | Record dataclasses cover the Phase 1 MVP plus profile objects | Gap analysis for missing concepts and explicit profile deferrals |
| §4.3 | Governed `ProfileDefinition`; profiles compose but never redefine | Profile registry and invalid redefinition fixture | Dependency DAG, migration, bounded-view, and abstention contract review |
| §§5.1–5.12 | Formal behavior for source, referent, scope, state, occurrence, relation, claim, perspective, evidence, provenance, branch, type | Phase 1 contracts/validators cover a subset | Per-record field and invariant matrix; add only evidence-backed missing fields |
| §5.13 | Conservative identity/reference management | Existing referent handling and migration rules | `IdentityPolicy` design, uncertain identity relation tests, consumer impact review |
| §5.14 | Mode of being through type and scope, not one universal exclusive list | Type records and scope fields | Explicit type/scope constraints and competing classification examples |
| §5.15 | Explicit branch membership and branch-neutral reuse | `BranchMembership` validators and fixtures | Contract consumed by Branch program and cross-branch regression suite |
| §5.16 | Explicit state commitment and dependent invalidation | `StateCommitment` validators and adversarial fixtures | Staleness propagation contract for Shape, Transformation, Execution consumers |
| §§6.1–6.12 | Testable invariants | Contract tests and Phase 1 review | One named test/fixture per invariant and a coverage report |
| §§21–22 | Progressive formalization and orthogonal lifecycle | Lifecycle literals and validation | Transition policy, invalid transitions, promotion/deprecation propagation |
| §§23–25 | One logical system, versioning, formalization layers, minimal schemas | Store/runtime/registry modules | Public compatibility policy and module-boundary audit |
| §29 | Ruthlessly minimal first implementation | Phase 1 slice | Evidence that additions remain necessary and bounded |

## Required atomic-obligation fields

Every row produced from this register must contain `obligation_id`, source quote or precise section, interpretation, owner module, public contract version, migration impact, tests/fixtures, downstream consumers, completion state, and unresolved question. Never mark an obligation implemented merely because a dataclass has the same name.
