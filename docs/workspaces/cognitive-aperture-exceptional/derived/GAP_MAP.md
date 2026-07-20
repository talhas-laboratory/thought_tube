# Gap Map — Reliable Modular Cognitive Aperture

**Workspace:** `cognitive-aperture-exceptional`
**Version:** 2.0
**Status:** canonical implementation plan
**Date locked:** 2026-07-19
**Architecture:** [`Modular Cognitive Aperture Design`](../../../plans/2026-07-19-cognitive-aperture-modular-disclosure-design.md)

## 1. Objective

Build a lightweight disclosure service that gives an agent the smallest authorized, provenance-backed view of a large private knowledge world and can prove why that view was selected.

The service follows:

```text
orient -> grant -> evidence -> receipt
```

It owns disclosure. It does not own ingestion, canonical records, Shape promotion, embeddings, or surface presentation.

## 2. Non-negotiable invariants

1. No positive match means no evidence opens.
2. Confidence, popularity, or availability alone never admits a candidate.
3. Denials override defaults, inferred intent, pins, and ranking.
4. Suppressed content is unrepresentable in the execution object.
5. Raw source text is stored once; derived artifacts use references and hashes.
6. Every included block has source, branch, scope, and inclusion reason.
7. Every Shape result states candidate versus validated status.
8. Shape derivation and promotion stay outside the aperture.
9. Budgets are deterministic and enforced by whole evidence block.
10. Incognito performs no ocean retrieval or durable learning.
11. Dependency failure never widens retrieval.
12. Surface adapters cannot reinterpret or bypass the effective grant.
13. No full-ocean scan occurs on the request path.
14. Equivalent inputs at the same corpus and policy revision produce equivalent results.
15. Every disclosure, empty result, denial, or abstention produces a reconstructible receipt.

## 3. Current state

### Assets to keep

- `ContextPolicy`, bridge state, layer filtering, and session envelopes;
- `build_retrieval_bundle` capsule and governed-link retrieval;
- Frame contracts and inspect surfaces;
- legacy Shape signatures, structural matching, and AntiMatch memory;
- canonical branch, scope, provenance, and bounded-view kernel;
- Holodeck and workspaces as coordination/adoption surfaces.

### Verified defects

| ID | Defect | Current evidence |
|---|---|---|
| D1 | Retrieval fails open | confidence contributes to every score; fallback forces top seeds |
| D2 | Budget is decorative | `ContextPolicy.token_budget` does not trim the model-bound bundle |
| D3 | Envelope modes overlap | `bounded` defaults to the same layers as `open` |
| D4 | Suppression leaks | execution composer renders suppressed frame blocks |
| D5 | Policy axes overlap | depth, envelope, retrieval mode, and layer policy are reinterpreted downstream |
| D6 | Retrieval mechanisms diverge | Bridge, Holodeck, feed, task packs, and kernel views select independently |
| D7 | Shape authority is split | legacy signatures exist; canonical Shape profile is not registered |
| D8 | Corpus readiness contract is not implemented | a representative corpus and derived projections exist, but no versioned `CorpusCatalog` makes readiness/capabilities enforceable |
| D9 | Metrics are plumbing-heavy | no versioned neighborhood-quality baseline |
| D10 | Live plan is incomplete | only CAE-000…003 registered; generic criteria; no task dependencies |

## 4. Target modules

| Module | Responsibility | Must not own |
|---|---|---|
| `disclosure/contracts` | request, state, grant, candidate, bundle, receipt types | storage or ranking |
| `disclosure/grants` | requested policy -> immutable effective grant | source access implementation |
| `disclosure/candidates` | admission gate and ranking over compact refs | evidence text or promotion |
| `disclosure/budget` | deterministic whole-block allocation | prompt composition |
| `disclosure/service` | orchestration and result status | surface-specific behavior |
| `disclosure/receipts` | compact audit materialization | model-bound content |
| Bridge adapter | bridge state and execution projection | policy reinterpretation |
| Holodeck adapter | workspace grant and projection | independent scorer |

Exact file placement is decided by the engineering guard. Do not create a package until the first two consumers justify it.

## 5. External dependency contracts

### G-1 — Corpus readiness

The aperture requires a `CorpusCatalog` reporting revision, counts, provenance coverage, branch/scope coverage, index capabilities, Shape/address coverage, and stale pipeline state.

**Gate:** a representative fixture corpus contains positive, negative, distractor, privacy, multi-dimensional, and Shape/AntiMatch cases. An empty production corpus may be valid, but it cannot be used to claim retrieval quality.

### G-2 — Canonical Shape read boundary

The aperture reads promoted Shape projections from the canonical framework and provisional legacy signatures through an explicitly candidate-labeled adapter.

**Gate:** no third Shape store; candidate status and provenance survive retrieval; profile-unavailable returns abstention.

## 6. Disclosure gaps

### G0 — Contract lock

Lock ADR-001, ADR-002, effective grant, execution/audit separation, result statuses, and owner boundaries.

### G1 — Fail-empty retrieval

Separate positive admission from ranking. Remove confidence-only admission and forced fallback. Missing required membrane metadata fails closed under bounded/strict.

**Acceptance:** unrelated and empty queries return `empty_no_positive_match`; positive alias/pin fixtures retain expected recall; stale indexes abstain.

### G2 — Effective grant and envelope matrix

Normalize requested policy, envelope defaults, workspace/source constraints, branch/scope visibility, pins, and denials once. Downstream modules consume only `EffectiveGrant`.

**Acceptance:** open, bounded, strict, and incognito differ in access and persistence; deny precedence passes the complete matrix.

### G3 — Execution/audit isolation

Replace the shared leaky frame object at the execution boundary with an `ExecutionBundle` that cannot contain suppressed or omitted fields. Keep suppression reasons in `AuditReceipt` and inspect tools.

**Acceptance:** unique suppression sentinels never appear in any model-bound request; audit still reconstructs the decision.

### G4 — Deterministic budget enforcement

Define tokenizer/estimator version, reserved answer/system capacity, orientation/evidence caps, block priorities, overflow behavior, and a drop ledger.

**Acceptance:** no emitted bundle exceeds its effective budget; identical inputs are deterministic; required evidence that cannot fit produces explicit insufficient-budget status.

### G5 — Orient-first execution

Build orientation from the current turn and already-authorized local continuity. Compose orientation, constraints, evidence, then user turn. Newly retrieved evidence cannot retroactively authorize itself.

**Acceptance:** orientation is capped and precedes evidence; no-global-evidence responses remain coherent; an optional second-pass widen requires a new grant and receipt.

### G6 — Shared disclosure service

Introduce the orchestration boundary only after contracts and two adapters are ready. Bridge adopts first; Holodeck second.

**Acceptance:** both surfaces call the same service and pass adapter conformance; neither imports the other or implements a parallel admission rule.

### G7 — Receipts and observability

Record request/corpus revisions, requested/effective grant, candidate decisions, included/omitted IDs, budget ledger, policy hashes, result status, and surface.

**Acceptance:** one result is reconstructible; incognito receipts store hashes/metrics only; receipt retention is explicit.

### G8 — Shape-aware aperture quality

Support optional Shape candidate recall, structural alignment, boundary/scale checks, AntiMatch filtering, and evidence resolution. Shape reasoning remains lazy.

**Acceptance:** structural match beats a lexical distractor; AntiMatch blocks a known false analogy; candidate is never presented as validated Pattern membership.

### G9 — State continuity

Version a bounded `ActiveStateSnapshot` across allowed surfaces without turning state into another knowledge store.

**Acceptance:** purpose, object, tension, posture, lens, branch, and scope survive permitted transitions; incognito does not persist them.

### G10 — Later surface adapters

Add feed and optional task-pack enrichment only after Bridge/Holodeck release. Preserve task-pack narrative handoff and feed-specific presentation.

### G11 — Kernel bounded-view decision

Use the kernel bounded view only as an optional epistemic evidence backend under an explicit grant, or document it as separate. Do not imply integration until a conformance test exists.

## 7. Evaluation program

Baselines are created before enforcement.

| Suite | Required result |
|---|---|
| `aperture_negative` | unrelated/empty queries fail empty |
| `aperture_positive` | gold evidence/Shape sets meet declared recall target |
| `distractor_harm` | distractor additions do not silently change admitted evidence |
| `grant_matrix` | deny precedence and envelope access/persistence invariants pass |
| `budget_obedience` | all bundles remain within effective budget |
| `leak_suite` | suppressed sentinel absent from model-bound payload |
| `provenance_suite` | every block resolves to source, branch, scope, and hash |
| `shape_alignment` | structural matches and AntiMatches behave as specified |
| `adapter_conformance` | Bridge and Holodeck return equivalent decisions for equivalent inputs |
| `performance` | p50/p95 latency, bytes resolved, graph expansion, and cache behavior published |

Release metrics and fixture revisions live under `derived/baselines/`; no “exceptional” claim is allowed without published numbers.

## 8. Execution order

### Stage A — Plan and dependency readiness

1. **CAE-000** — lock ADRs and contracts.
2. **CAE-013** — define corpus readiness contract and fixture corpus.
3. **CAE-014** — lock canonical Shape read adapter and legacy migration decision.
4. **CAE-015** — lock effective grant, execution bundle, receipt, and result contracts.
5. **CAE-006A** — create baseline evaluation harness and record current behavior.

**Exit:** contracts reviewed; representative corpus versioned; current failures reproducible; no runtime behavior changed.

### Stage B — Stop unsafe behavior

1. **CAE-002** — remove suppression leak through execution/audit type separation.
2. **CAE-003A** — normalize effective grant and envelope matrix.
3. **CAE-001** — implement fail-empty admission in shadow mode, repair metadata, then enforce.
4. **CAE-003B** — enforce deterministic token/block budgets.
5. **CAE-004** — implement orient-first compose.

**Exit:** negative, leak, grant, budget, provenance, and positive-recall gates pass on the Bridge path.

### Stage C — One service, two consumers

1. **CAE-005A** — extract disclosure service around the proven Bridge path.
2. **CAE-005B** — adopt Holodeck through an adapter.
3. **CAE-007** — persist receipts and publish operational metrics.
4. **CAE-008** — add bounded ActiveState continuity.
5. **CAE-006B** — publish Shape-aware and performance baselines.

**Exit:** Bridge and Holodeck pass adapter conformance; receipts reconstruct results; latency budget met.

### Stage D — Controlled expansion

1. **CAE-009** — feed adapter.
2. **CAE-010** — optional task-pack evidence adapter.
3. **CAE-011** — bounded-view wire-or-demote decision.
4. **CAE-012** — cross-surface metrics/operator view.

**Exit:** each adapter has an owner, rollback, conformance evidence, and no duplicate selection logic.

## 9. Rollout rules

- Use feature flags for grant normalization, fail-empty, budget enforcement, and execution-safe projection.
- Measure current behavior before enabling each flag.
- Run shadow decisions without disclosing shadow-selected evidence.
- Backfill missing metadata before enforcing policies that depend on it.
- Roll back by configuration, not data deletion.
- Never migrate all surfaces in one change.
- A task may enter `done` only with exact commands, results, artifacts, and residual risks recorded.

## 10. Definition of Done — reliable v1

All conditions must hold:

1. Corpus readiness and canonical Shape read contracts are implemented or explicitly return not-ready.
2. Bridge and Holodeck use one disclosure service and pass adapter conformance.
3. Fail-empty, grant, leak, budget, provenance, and incognito suites pass.
4. Positive recall does not fall below the approved fixture threshold.
5. Shape retrieval preserves candidate status, branch, scope, abstraction contract, and source spans.
6. No execution object can carry suppressed content.
7. No request path performs a full-ocean scan.
8. p50/p95 latency and resolved-byte baselines meet the approved budget.
9. Every result emits a compact receipt with explicit status.
10. Feature flags and rollback paths are tested.

Optional learned reranking, activation steering, and broad World Studio adoption remain outside reliable v1.
