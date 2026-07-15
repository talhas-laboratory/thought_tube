# Branch Reasoning — Public Contract Lock v1.0.0

**Task:** `BRANCH-001-atomic-obligation-and-interface-lock`
**Workspace:** `metaphysical-branch-reasoning`
**Authority:** [Framework v1.1](../../unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md) §7, §20, §27.2, §27.16
**Kernel contract consumed:** [`KERNEL_PUBLIC_CONTRACT_LOCK.md`](../../metaphysical-kernel-ontology/derived/KERNEL_PUBLIC_CONTRACT_LOCK.md) `CONTRACT_VERSION=1.1.0`
**Obligation register:** [`BRANCH_OBLIGATION_REGISTER.md`](./BRANCH_OBLIGATION_REGISTER.md)

This document locks the **public branch reasoning contract boundary** after BRANCH-001. Downstream programs (Vocabulary, Conversation/Formation, Shape, Pattern, Agent) may depend on the version, operation names, input/output record types, invariants, and explicit deferrals named here. They must not embed private branch logic.

No runtime owner module is introduced by BRANCH-001. The planned owner is `src/conversation_os/metaphysical_branch_reasoning.py` (`MODULE_ID=branch.metaphysical.reasoning`), subject to engineering guard approval at BRANCH-002.

---

## Contract version

| Field | Value |
|---|---|
| `BRANCH_CONTRACT_VERSION` | `1.0.0` |
| Semantic authority | Framework v1.1 §7, §20, §27.2, §27.16 |
| Kernel dependency | `CONTRACT_VERSION=1.1.0` (kernel.metaphysical.records) |
| Compatibility | Additive within 1.0.x; breaking changes require contract version bump and parent decision |

---

## Kernel types consumed (read-only; do not redefine)

| Kernel type | Section | Used by |
|---|---|---|
| `ModelBranch` | §5.11 | InheritanceQuery, SupportAssessment, MergeAssessment, InferenceContext |
| `BranchMembership` | §5.15 | InheritanceQuery (membership check) |
| `Claim` | §5.7 | SupportAssessment, ConflictRecord, MergeAssessment, InferenceContext |
| `Scope` | §5.3 | SupportAssessment (scoped evaluation) |
| `Provenance` | §5.10 | InferenceResult (candidate provenance) |
| `SourceFragment`, `Referent` | §5.1, §5.2 | BranchNeutralSourceReuse contract |
| `StateCommitment` | §5.16 | Boundary: Branch must not infer State from Claim |
| `EpistemicStatus` | §22.1 | SupportValue mapping |
| `MaturityStatus`, `GovernanceStatus` | §22.1 | InferenceContext lifecycle filters |

`BRANCH_BOUND_RECORD_KINDS = {claim, state, state_commitment}` (from kernel; branch membership is required for these).

---

## Operation contracts

### 1. InheritanceQuery — §7.2

**Purpose:** Given a child branch and a record ID, determine the record's read-visibility in that branch.

**Inputs:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `child_branch_id` | `str` (ModelBranch.id) | yes | |
| `record_id` | `str` (KernelRecordEnvelope.id) | yes | |
| `branch_ancestry` | list of `(branch_id, parent_branch_id)` | yes | Ordered parent chain, most-local first |
| `membership_entries` | list of `BranchMembership` | yes | All memberships for this record across ancestry |

**Output:**

| Field | Type | Notes |
|---|---|---|
| `record_id` | `str` | Echo of input |
| `child_branch_id` | `str` | Echo of input |
| `visibility` | `InheritanceOutcome` | See table below |
| `effective_membership_kind` | `MembershipKind \| null` | Most-local applicable membership, or null |
| `resolved_in_branch_id` | `str \| null` | Which branch's entry governs; null on `absent` |
| `provenance_id` | `str` | Provenance of the resolution decision |

**InheritanceOutcome values:**

| Value | Meaning | Condition |
|---|---|---|
| `inherited` | Visible via parent chain; no local override | Parent has `asserted` or `derived` membership; child has no entry |
| `asserted` | Locally added in child | Child has `asserted` or `derived` membership |
| `retracted` | Explicitly removed in child | Child has `retracted` membership |
| `replaced` | Child's entry supersedes parent | Child has `asserted`; parent also has `asserted` for same record |
| `hidden` | Marked invisible without retraction | Child has `hidden` membership |
| `absent` | Not a member of this branch at all | No membership found in child or any ancestor |

**Absence / error behavior:**

| Condition | Behavior |
|---|---|
| `child_branch_id` not found in ancestry | Return `absent`; raise `BranchNotFoundError` if required |
| `record_id` has no membership in child or ancestors | Return `absent` with `effective_membership_kind=null` |
| Circular ancestry detected | Raise `BranchCircularAncestryError` |
| Branch-bound record kind without any BranchMembership | Return `absent`; do not treat as globally visible |

**Invariants:**
- Inheritance is a read rule only; the contract never physically duplicates records.
- A `retracted` entry in any branch in the child-to-root path shadows ancestor assertions.
- Branch-neutral record kinds (`source_fragment`, `referent`, `scope`, `provenance`, `model_branch`, `branch_membership`) are readable without membership check (see §27.16).

**Scope compatibility rule:**
- If the query includes an `effective_scope_id` filter, only memberships where `effective_scope_id` matches (or is a parent scope) are considered visible.

---

### 2. SupportAssessment — §7.3

**Purpose:** Within a branch and scope, evaluate the four-valued support status of a claim proposition.

**Inputs:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `branch_id` | `str` | yes | Evaluation branch |
| `scope_id` | `str` | yes | Evaluation scope |
| `claim_proposition` | `ClaimProposition` | yes | Predicate + arguments being evaluated |
| `evidence_claims` | list of `Claim` | yes | All claims in scope with their polarity |
| `include_inherited` | `bool` | yes | Whether to traverse parent branch inheritance |

**Output:**

| Field | Type | Notes |
|---|---|---|
| `branch_id` | `str` | Echo |
| `scope_id` | `str` | Echo |
| `claim_proposition` | `ClaimProposition` | Echo |
| `support_value` | `SupportValue` | See table below |
| `affirmative_claim_ids` | list of `str` | Claims with matching proposition and `polarity=affirmative` |
| `negative_claim_ids` | list of `str` | Claims with matching proposition and `polarity=negative` |
| `provenance_id` | `str` | Provenance of this assessment |

**SupportValue (four-valued — §7.3):**

| Value | Meaning | Condition |
|---|---|---|
| `supported_only` | Supported and not opposed | ≥1 affirmative claim; 0 negative claims in scope |
| `opposed_only` | Opposed and not supported | ≥1 negative claim; 0 affirmative claims in scope |
| `both` | Supported and opposed | ≥1 affirmative AND ≥1 negative claim in scope |
| `unresolved` | Neither supported nor opposed | 0 affirmative; 0 negative claims in scope |

**Mapping to kernel EpistemicStatus:**

| SupportValue | Suggested `epistemic_status` on output record |
|---|---|
| `supported_only` | `supported` |
| `opposed_only` | `opposed` |
| `both` | `both` |
| `unresolved` | `unresolved` |

**Absence / error behavior:**

| Condition | Behavior |
|---|---|
| Branch not found | Raise `BranchNotFoundError` |
| Scope not found | Raise `ScopeNotFoundError` |
| No claims in scope | Return `unresolved`; `affirmative_claim_ids=[]`, `negative_claim_ids=[]` |
| Claim is `retracted` in branch | Excluded from assessment |
| `evidence_claims` contains a branch-bound claim without membership | Raise `ClaimMembershipError` |

**Invariants:**
- This is an evidence status report, not a truth selection.
- `both` must never be collapsed to either `supported_only` or `opposed_only` without explicit retraction.
- Fluency, majority count, or narrative coherence is never a valid tie-breaker.
- Scope matching is required: a claim from a different scope does not count even if the proposition matches.

---

### 3. ConflictRecord — §7.4

**Purpose:** Classify the nature of apparent disagreement between two or more claims.

**Inputs:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `claim_a_id` | `str` | yes | |
| `claim_b_id` | `str` | yes | |
| `claim_a` | `Claim` | yes | Full claim record |
| `claim_b` | `Claim` | yes | Full claim record |
| `context_notes` | `str` | no | Free-text context from agent |

**Output:**

| Field | Type | Notes |
|---|---|---|
| `claim_a_id` | `str` | Echo |
| `claim_b_id` | `str` | Echo |
| `conflict_kind` | `ConflictKind` | See table below |
| `is_logical_contradiction` | `bool` | True only for `logical_contradiction` |
| `explanation` | `str` | Human-readable classification reason |
| `residual_risk` | `str` | What remains unresolved |
| `provenance_id` | `str` | Provenance of this conflict record |

**ConflictKind values (§7.4):**

| Value | Meaning | Example |
|---|---|---|
| `logical_contradiction` | Direct negation of same proposition in same scope | "A causes B" vs "A does NOT cause B" in scope X |
| `measurement_incompatible` | Different measured values for same property | Temperature reading: 100°C vs 98°C |
| `perspective_divergence` | Same situation, different claimants, different conclusions | Agent A: "effective" vs Agent B: "ineffective" |
| `temporal_change` | Claim was true at T1, different claim true at T2 | Population in 2010 vs 2020 |
| `scope_difference` | Claims hold in different scopes | Local vs global scope |
| `semantic_ambiguity` | Apparent conflict due to term ambiguity | "heavy" means different things |
| `causal_competing` | Different causal explanations for same phenomenon | Two competing hypotheses |

**Invariants:**
- Negation must be explicit (`polarity=negative`); implicit negation is not allowed.
- `scope_difference` is never automatically classified as `logical_contradiction`.
- `temporal_change` is never automatically classified as `logical_contradiction`.
- `perspective_divergence` is never automatically classified as `logical_contradiction`.
- `is_logical_contradiction=true` requires same scope, same proposition predicate/arguments, and opposite polarity.

**Absence / error behavior:**

| Condition | Behavior |
|---|---|
| Either claim not found | Raise `ClaimNotFoundError` |
| Same claim ID for both inputs | Raise `SelfConflictError` |
| Insufficient context to classify | Return `conflict_kind=semantic_ambiguity` with explanation noting ambiguity |

---

### 4. MergeAssessment — §7.5

**Purpose:** Assess compatibility between two branches without selecting a winner.

**Inputs:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `branch_a_id` | `str` | yes | |
| `branch_b_id` | `str` | yes | |
| `records_a` | list of record envelopes | yes | All records visible in branch A |
| `records_b` | list of record envelopes | yes | All records visible in branch B |
| `scope_id` | `str` | no | Limit assessment to one scope |

**Output:**

| Field | Type | Notes |
|---|---|---|
| `branch_a_id` | `str` | Echo |
| `branch_b_id` | `str` | Echo |
| `shared_record_ids` | list of `str` | Records present in both branches |
| `compatible_additions` | list of `str` | Records in one branch that do not conflict with the other |
| `conflicts` | list of `ConflictEntry` | Conflicting claim pairs with `conflict_kind` |
| `divergent_assumptions` | list of `str` | ModelBranch assumptions present in one but not both |
| `scope_differences` | list of `str` | Scope IDs that appear in one branch only |
| `unresolved_identity_mappings` | list of `str` | Referent IDs that could map to the same entity but are unconfirmed |
| `merge_verdict` | `MergeVerdict` | See table below |
| `provenance_id` | `str` | Provenance of this assessment |

**MergeVerdict values:**

| Value | Meaning |
|---|---|
| `compatible` | No conflicts; safe to merge |
| `partially_compatible` | Some conflicts; merge requires explicit conflict resolution before adoption |
| `incompatible` | Fundamental contradictions; merge blocked without branch decision |

**ConflictEntry (within MergeAssessment):**

| Field | Type |
|---|---|
| `claim_a_id` | `str` |
| `claim_b_id` | `str` |
| `conflict_kind` | `ConflictKind` |

**Invariants:**
- A merge MUST NOT silently choose a winner (§7.5).
- Conflicting claims remain unresolved in the output; the output reports status, not resolution.
- `compatible_additions` requires explicit membership and scope compatibility, not just proposition absence.
- Source fragments and referents that are branch-neutral may appear in `shared_record_ids` without requiring membership reconciliation.

**Absence / error behavior:**

| Condition | Behavior |
|---|---|
| Either branch not found | Raise `BranchNotFoundError` |
| Empty record lists | Return `merge_verdict=compatible` with all lists empty |
| Scope filter provided but not found | Raise `ScopeNotFoundError` |

---

### 5. InferenceContext and InferenceResult — §7.6

**Purpose:** Declare an inference request over selected records; produce candidate claims with provenance; handle `both` safely.

#### 5a. InferenceContext (input contract)

| Field | Type | Required | Notes |
|---|---|---|---|
| `branches` | list of `str` | yes | Branch IDs for record selection |
| `scope_id` | `str` | yes | Evaluation scope |
| `perspective` | `str` | no | Claimant perspective filter (optional) |
| `accepted_maturity_statuses` | list of `MaturityStatus` | yes | Lifecycle filter |
| `accepted_epistemic_statuses` | list of `EpistemicStatus` | yes | Epistemic filter |
| `accepted_governance_statuses` | list of `GovernanceStatus` | yes | Governance filter |
| `relation_families` | list of `str` | no | Relation type filters |
| `contradiction_policy` | `ContradictionPolicy` | yes | See table below |
| `output_status` | `EpistemicStatus` | yes | Must be `candidate` |
| `inference_kind` | `InferenceKind` | yes | See table below |
| `max_depth` | `int` | yes | Traversal depth bound (§20) |

**ContradictionPolicy values:**

| Value | Meaning |
|---|---|
| `preserve` | Preserve both conclusions when `both` is encountered |
| `branch` | Create a new sub-branch for each alternative |
| `clarify` | Emit clarification request instead of conclusions |
| `abstain` | Return abstention record; no conclusions emitted |

**InferenceKind values (§7.6):**

| Value | Framework section |
|---|---|
| `definitional` | §7.6 definitional inference |
| `structural` | §7.6 structural inference |
| `temporal` | §7.6 temporal inference |
| `causal_hypothesis` | §7.6 causal hypothesis generation |
| `agent_belief` | §7.6 agent belief inference |
| `executable_state` | §7.6 executable-state inference |

#### 5b. InferenceResult (output contract)

| Field | Type | Notes |
|---|---|---|
| `inference_context_provenance_id` | `str` | Links to InferenceContext provenance |
| `output_claims` | list of `CandidateClaimOutput` | Candidate claims, each with provenance |
| `abstention` | `AbstentionRecord \| null` | Present when `contradiction_policy=abstain` or no candidates possible |
| `branched_sub_contexts` | list of `InferenceContext` | Present when `contradiction_policy=branch` |
| `clarification_request` | `ClarificationRequest \| null` | Present when `contradiction_policy=clarify` |

**CandidateClaimOutput:**

| Field | Type | Notes |
|---|---|---|
| `proposition` | `ClaimProposition` | Inferred predicate + arguments |
| `branch_id` | `str` | Branch the candidate belongs to |
| `scope_id` | `str` | Scope the candidate holds in |
| `epistemic_status` | `EpistemicStatus` | Always `candidate` |
| `provenance_id` | `str` | Derivation trace |
| `source_claim_ids` | list of `str` | Supporting input claims |
| `polarity` | `Literal["affirmative", "negative"]` | |

**AbstentionRecord:**

| Field | Type | Notes |
|---|---|---|
| `reason` | `AbstentionReason` | See table below |
| `explanation` | `str` | Human-readable detail |
| `unresolved_claim_ids` | list of `str` | Claims causing the abstention |

**AbstentionReason values:**

| Value | Meaning |
|---|---|
| `both_support_status` | `both` encountered and policy is `abstain` |
| `insufficient_evidence` | Not enough affirmative claims to infer |
| `scope_incompatible` | Candidate would violate scope boundary |
| `membership_missing` | Required BranchMembership absent |
| `contradiction_policy_halt` | Contradiction policy prevented output |

**Invariants:**
- `output_status` must be `candidate`; inference never promotes to `supported`, `committed`, or `state`.
- Causal hypothesis generation never promotes beyond `candidate` without evidence or explicit stipulation (§7.6).
- Fluency or narrative coherence is never a valid tie-breaker on `both`.
- If `contradiction_policy=preserve`: output must contain both the affirmative and negative candidate.
- If `contradiction_policy=abstain`: `output_claims` must be empty.

**Absence / error behavior:**

| Condition | Behavior |
|---|---|
| Branch not found | Raise `BranchNotFoundError` |
| Scope not found | Raise `ScopeNotFoundError` |
| `output_status` is not `candidate` | Raise `InvalidInferenceOutputStatusError` |
| `max_depth` exceeded | Truncate traversal; set `residual_risk` in abstention |
| No candidates found | Return `abstention` with `reason=insufficient_evidence` |

---

### 6. BranchEnsemble — §7.7

**Purpose:** Maintain a task-relative weighted collection of branches for uncertain problems.

**Contract:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `ensemble_id` | `str` | yes | |
| `branches` | list of `BranchWeight` | yes | Each has `branch_id` and `weight` |
| `weighting_basis` | `str` | yes | e.g. `evidence_fit`, `prior_probability` |
| `normalization_scope` | `str` | yes | Task or context scope for weight normalization |
| `task_id` | `str` | yes | Weights are relative to this task only |
| `provenance_id` | `str` | yes | |

**BranchWeight:**

| Field | Type |
|---|---|
| `branch_id` | `str` |
| `weight` | `float` (0.0–1.0) |
| `weight_provenance_id` | `str` |

**Invariants:**
- Weights are task-relative only; they must not be interpreted as universal truth probabilities (§7.7).
- A formal probabilistic model is required before weights may be used as universal probabilities.
- Weights do not override SupportAssessment or ConflictRecord results.

---

### 7. BoundedView — §20.3

**Purpose:** Task-specific branch-scoped traversal with explicit inclusion rules and depth bound.

**Contract:**

| Field | Type | Required | Notes |
|---|---|---|---|
| `branch_id` | `str` | yes | |
| `scope_id` | `str` | yes | |
| `root_record_ids` | list of `str` | yes | Starting points |
| `relation_filters` | list of `str` | no | Permitted relation type families |
| `max_depth` | `int` | yes | Hard traversal depth limit |
| `relevance_budget` | `int \| null` | no | Optional record count limit |
| `perspective` | `str \| null` | no | Claimant filter |
| `materialization_policy` | `Literal["eager","lazy"]` | yes | |

**Invariants:**
- Every traversal must specify branch, scope, and max_depth (§20.1).
- `max_depth` prevents leakage across branch boundaries (§27.14).
- Deep or weakly relevant structures returned as expandable handles when `materialization_policy=lazy` (§20.4).

---

### 8. BranchNeutralSourceReuse — §27.16

**Purpose:** State that source fragments and referents can be shared across branches without duplication or forced interpretive agreement.

**Rule:**

- `source_fragment` and `referent` records with `branch_id=null` (no BranchMembership required) are readable in any branch.
- Branch-local interpretations (Claims, States) linked to the same source have distinct IDs and their own BranchMembership.
- No branch's interpretation of a shared source is treated as authoritative for another branch.

**Fixture acceptance test:**
- One `source_fragment` ID can appear in `provenance.source_refs` for Claims in two different branches.
- Each branch's Claim has its own `branch_id` and BranchMembership; the source fragment has neither.

---

## Outcome tables (by fixture reference)

| Table | Fixture file | §7 area |
|---|---|---|
| Inheritance outcomes | `tests/fixtures/metaphysical_branch/inheritance_outcome_table.json` | §7.2 |
| Support outcomes (4-valued) | `tests/fixtures/metaphysical_branch/support_outcome_table.json` | §7.3 |
| Conflict classification | `tests/fixtures/metaphysical_branch/conflict_outcome_table.json` | §7.4 |
| Merge assessment | `tests/fixtures/metaphysical_branch/merge_outcome_table.json` | §7.5 |
| Inference policy | `tests/fixtures/metaphysical_branch/inference_outcome_table.json` | §7.6 |

Master index: `tests/fixtures/metaphysical_branch/branch_contract_fixtures.json`

---

## Versioning and compatibility policy

| Change type | Policy |
|---|---|
| New optional field on existing operation | Minor version bump (1.0.x); must add to obligation register |
| New operation | Minor version bump; must add gate and tests |
| Breaking field rename or removal | Major version bump; requires parent decision record |
| New ConflictKind value | Minor version bump |
| New AbstentionReason value | Minor version bump |
| InheritanceOutcome new value | Minor version bump |

---

## Deferred items (not in 1.0.0 public surface)

| Item | Framework section | Reason for deferral |
|---|---|---|
| `Perspective` record | §5.8 | Kernel defers; use `claimant + branch` as proxy |
| `Evidence` record | §5.9 | Kernel defers; use `provenance + claim linkage` as proxy |
| Lifecycle transition policy | §22 | Kernel KERNEL-004 gap; branch inherits same deferral |
| Probabilistic weight operations | §7.7 | No formal probabilistic model in Phase 1 |
| Ensemble weight as truth probability | §7.7 | Explicitly excluded; not in Phase 1 |
| Executable-state inference output | §7.6 | Causal outputs never exceed `candidate` in Phase 1 |

---

## Residual risks

| Risk ID | Description | Mitigation |
|---|---|---|
| BRANCH-R-001 | Scope compatibility rule for inheritance may need refinement once `Scope` hierarchy is defined | Flag as open; revisit at BRANCH-002 |
| BRANCH-R-002 | `BranchEnsemble` weight normalization is task-relative but normalization algorithm is unspecified | Document as unspecified; consumer must supply normalization at Phase 1 |
| BRANCH-R-003 | `perspective` field in InferenceContext is optional; absence behavior needs runtime testing | Flag for BRANCH-002 fixture |
| BRANCH-R-004 | `causal_hypothesis` inference kind boundary with `executable_state` needs adversarial test | Flag for BRANCH-004 adversarial suite |

---

## Verification commands (BRANCH-001)

```bash
# Repository overview is current
python3 tools/conversation_os.py repo-overview refresh

# Engineering guard (spec/doc work; no Python source changes in BRANCH-001)
python3 tools/conversation_os.py engineering-guard assess \
  --request "BRANCH-001 contract document and fixtures" \
  --purpose "Deliver branch contract tables before runtime; no Python source changes." \
  --proposed-paths "docs/workspaces/metaphysical-branch-reasoning/derived/BRANCH_PUBLIC_CONTRACT_LOCK.md,tests/fixtures/metaphysical_branch/branch_contract_fixtures.json"

# Kernel contract tests must still pass after BRANCH-001 doc changes
PYTHONPATH=src python3 -m unittest tests.test_kernel_atomic_obligations tests.test_metaphysical_kernel_contracts -v

# Contract fixture schema validation (future — BRANCH-002 will add the runner)
# pytest -q tests/test_metaphysical_branch_reasoning.py
```

Note: The engineering guard `review_targets` status for BRANCH-001 is expected and documented. BRANCH-001 produces documentation and JSON fixtures only. The guard `ready` gate applies to runtime Python source changes, which begin at BRANCH-002 after this contract is accepted.

---

## Downstream dependency statement

Vocabulary, Conversation/Formation, Shape, Pattern, and Agent programs may draft against this contract. They cannot pass their own G5 integration until BRANCH-005 publishes merge SHA evidence. Until then, consume `BRANCH_CONTRACT_VERSION=1.0.0` and this document as the semantic boundary.
