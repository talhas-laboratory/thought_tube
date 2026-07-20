# Cognitive Aperture remediation gap overview

**Audit basis:** branch `cursor/cognitive-aperture-gap-map-24c7` at `b361c9d200`
**Audit date:** 2026-07-20
**Purpose:** convert the post-implementation audit into bounded, testable remediation work.
**Coordination rule:** this document proposes task changes; live workspace coordination remains authoritative for status, ownership, blockers, and completion.

## 1. Release conclusion

The implementation contains useful contracts, ports, adapters, budgets, receipts, and focused tests, but it does not yet satisfy the workspace's reliable-v1 promise. The main path is still the legacy path, Shape-aware retrieval is not operational, request-time work scales with corpus size, and two safety boundaries do not fail closed.

The current state should be described as **implemented components behind flags, not a certified Cognitive Aperture release**.

## 2. Gap register

| Gap | Severity | Affected work | Current truth | Required outcome |
| --- | --- | --- | --- | --- |
| R-001 | critical | CAE-006B, CAE-014, CAE-005A | Shapes are read after retrieval and only counted | Shapes participate lazily in candidate recall and structural ranking |
| R-002 | critical | CAE-006B | AntiMatch presence is confused with AntiMatch enforcement | A matching AntiMatch rejects or penalizes a specific false analogy |
| R-003 | high | CAE-006, CAE-006B | “Shape-aware” certification is based on lexical synthetic capsules | Corpus-backed structural, distractor, precision, recall, and resource evidence |
| R-004 | critical | CAE-005, CAE-005A, CAE-005B | Bridge and Holodeck shared-service flags are off | Both primary surfaces use one shared disclosure path in the release configuration |
| R-005 | critical | CAE-001, CAE-003A | Bridge omits envelope mode and explicit pins during candidate search | Retrieval consumes the normalized effective grant before searching |
| R-006 | high | CAE-005A, CAE-013 | Every service request rebuilds catalog state from whole index files | Readiness is a cached, revisioned control-plane snapshot |
| R-007 | high | CAE-005A, CAE-006B | Evidence resolver copies frame rows without resolving evidence | Selected references resolve bounded source spans after admission |
| R-008 | critical | CAE-002, CAE-015 | A contaminated isolated bundle can render suppressed blocks | Model-bound composers reject or erase all suppression/audit fields |
| R-009 | high | CAE-005B | Holodeck artifact source fallback crashes on macOS path aliases | Source-reference fallback is lazy and path-normalized |
| R-010 | critical | CAE-005B | Adapter/config exceptions silently restore legacy retrieval | Dependency failure returns abstention and never widens retrieval |
| R-011 | high | CAE-007 | Receipt persistence is disabled, limiting reconstruction and metrics | Approved surfaces persist compact, privacy-safe receipts with retention |
| R-012 | medium | CAE-008 | Active-state continuity is implemented but inactive | Enable only after persistence, incognito, rollback, and retention proof |
| R-013 | high | CAE-009, CAE-010 | Feed/task-pack adapters are inactive and synthetic-fixture certified | Controlled rollout with production-like corpus parity and surface receipts |
| R-014 | high | CAE-011 | Bounded-view port has no primary-surface consumer | One explicitly granted surface consumes bounded epistemic evidence, or claims are demoted |
| R-015 | medium | CAE-012 | Operator metrics are disabled and depend on incomplete receipts/baselines | Read-only metrics compare certified revisions across active surfaces |
| R-016 | critical | all release tasks | Focused and repository-wide verification are not green | A versioned release gate distinguishes expected legacy failures from regressions |

## 3. Detailed remediation packets

### R-001 — Wire genuine Shape-aware candidate retrieval

**False or missing implementation**

`DisclosureService` calls the Shape reader only after the Bridge bundle has already been assembled. The result is reduced to a projection count. `candidate_admission` treats a `shape_signature_id` as a one-point metadata bonus only when another lexical signal already admitted the capsule. Structural Shape similarity cannot recall a candidate, change the order, enforce boundary/scale compatibility, or block a distractor.

**What to build**

Add a bounded Shape-candidate stage behind the candidate-search port. It must operate over compact Shape projections, never raw documents, and must preserve maturity, branch, scope, system boundary, abstraction contract, scale, and provenance.

**How to build it**

1. Define a `ShapeQuery`/`ShapeCandidateDecision` contract rather than adding Shape fields ad hoc to capsules.
2. Derive a compact query projection from the authorized request orientation; do not derive it from newly retrieved evidence.
3. Ask `ShapeProjectionReaderPort` only for the effective branch, scope, maturity ceiling, and allowed source references.
4. Calculate structural alignment independently from lexical score: relation topology, feedback-loop compatibility, boundary match, scale match, and abstraction compatibility.
5. Return compact candidate references and decision features to candidate admission.
6. Merge lexical, semantic-address, governed-graph, explicit-pin, and Shape signals through one deterministic admission/ranking function.
7. Resolve source spans only for the final admitted candidates.

**Verification gate**

- Create a fixture where the lexical distractor scores higher before Shape evaluation.
- Demonstrate that structural alignment promotes the correct provisional Shape candidate above it.
- Assert preserved branch, scope, boundary, scale, maturity, and source spans.
- Assert that profile-unavailable produces `abstained_dependency_not_ready`, not lexical widening.
- Record expansion count and resolved bytes; no raw-document scan is allowed.

**Completion evidence:** reopen CAE-006B; extend CAE-005A only after port conformance passes.

### R-002 — Make AntiMatch an operational negative signal

**False or missing implementation**

The current baseline reports `anti_match_blocks_analogy` when promotion is globally disabled and no promoted candidate exists. It never matches an AntiMatch against the proposed analogy, and the AntiMatch penalty is not applied to retrieval.

**What to build**

An explicit AntiMatch evaluation stage over Shape candidate decisions. AntiMatch must be a negative structural constraint, not merely a stored record or a ban on promotion.

**How to build it**

1. Extend the Shape read result with normalized AntiMatch constraints: branch, scope, boundary, scale, rejected relation/analogy, evidence, penalty or hard-deny behavior.
2. Match AntiMatches only after a positive Shape candidate exists and before final admission.
3. Apply deterministic outcomes: `hard_reject`, `penalize`, or `not_applicable`.
4. Record the AntiMatch ID and reason in the audit decision; do not include rejected text in the execution bundle.
5. Keep promotion outside the aperture. AntiMatch affects disclosure selection, not canonical Shape status.

**Verification gate**

- The same false analogy passes without the AntiMatch fixture and fails with it.
- An unrelated AntiMatch has no effect.
- Branch/scope-incompatible AntiMatches have no effect.
- Audit reconstructs the rejection without copying sensitive evidence.

### R-003 — Replace the false Shape certification with a real evaluation program

**False or missing implementation**

The service baseline uses three synthetic semantic capsules. Its “structural” test is lexical ranking, the known near-neighbour failure remains unresolved, and neighborhood precision/recall are not published despite being required by CAE-006B.

**What to build**

A versioned, corpus-backed evaluation suite that separately reports lexical recall, Shape-assisted recall, distractor harm, AntiMatch precision, provenance preservation, latency, bytes, and expansion.

**How to build it**

1. Freeze a new fixture revision containing positive, negative, near-neighbour, cross-branch, cross-scope, scale mismatch, boundary mismatch, Shape-positive, and AntiMatch cases.
2. Run lexical-only and Shape-assisted modes over identical queries.
3. Publish top-k precision, recall, mean reciprocal rank, abstention correctness, distractor harm, AntiMatch false-positive/false-negative rates, and candidate-status preservation.
4. Measure cold and warm p50/p95 latency, catalog lookup time, candidate expansion, resolved bytes, and cache hit rate.
5. Set `service_certified: true` only when every release threshold passes and there are no unwaived known failures.

**Verification gate**

- Published JSON is generated from the harness, not manually curated.
- The harness fails if the known near-neighbour query regresses.
- The report identifies fixture and corpus revisions and can be reproduced from a clean checkout.

### R-004 — Perform an explicit shared-service cutover

**False or missing implementation**

The Bridge and Holodeck shared-service flags both ship `false`, so the Definition of Done statement that both surfaces use one service is not true in the release configuration.

**What to build**

A staged cutover that first shadows, then canaries, then enables the shared service for Bridge and Holodeck with observable rollback.

**How to build it**

1. Add `legacy`, `shadow`, `canary`, and `enforced` rollout modes instead of a bare Boolean.
2. In shadow mode, compute both paths but execute only legacy; compare decision subsets, budgets, statuses, and latency.
3. Block canary if R-001–R-010 are incomplete or parity differs beyond approved tolerances.
4. Canary by deterministic request/session cohort and record which path executed.
5. Enable Bridge first, then Holodeck after its parity and platform suites pass.
6. Keep one-command rollback to legacy, but record rollback as an operator event and never silently trigger it on dependency error.

**Verification gate**

- Release configuration has both primary surfaces in `enforced` mode.
- Shadow/canary comparisons are revisioned and stored as compact receipts.
- Rollback smoke test proves restoration without losing audit continuity.

### R-005 — Move effective-grant enforcement in front of retrieval

**False or missing implementation**

Bridge candidate search receives limits and cross-ocean state but not `envelope_mode` or `explicit_pins`. The effective grant is normalized only after retrieval has already happened.

**What to build**

One grant-first execution order: orient → normalize effective grant → candidate search → admission → evidence resolution → compose → receipt.

**How to build it**

1. Build the session envelope and normalized effective grant before candidate search.
2. Pass effective envelope, allowed layers/refs, explicit pins, explicit denials, cross-ocean permission, dimensions, branch, scope, maturity ceiling, and token budget through a typed search request.
3. Remove downstream reinterpretations of those fields.
4. Ensure denials override pins, aliases, inferred depth, and ranking.
5. Skip candidate-search invocation entirely for incognito and denied-global requests.

**Verification gate**

- Spy-port tests assert every effective-grant field received by candidate search.
- Strict missing-membrane metadata fails closed through `get_context_bundle`, not just direct knowledge-layer tests.
- A permitted explicit pin recalls an otherwise unrelated candidate; a denied pin does not.
- Incognito proves the search port was never called.

### R-006 — Remove request-time full-corpus catalog reconstruction

**False or missing implementation**

Each service request loads the complete source registry, chunk index, Shape state, knowledge nodes, and capsules to rebuild readiness and counts. Cost therefore grows with the ocean.

**What to build**

A materialized `CorpusCatalogSnapshot` owned by ingestion/index refresh. The request path should perform an O(1) snapshot read and optional revision check.

**How to build it**

1. Move catalog calculation into pipeline close/refresh and corpus mutation hooks.
2. Persist an atomic snapshot containing revision, counts, coverage, capabilities, readiness, generation time, and source-index watermarks.
3. On a request, read only the snapshot and compare a cheap generation marker.
4. If missing or stale, abstain and enqueue/advertise refresh; never rebuild synchronously or widen retrieval.
5. Add an in-process revision-keyed cache with explicit invalidation.

**Verification gate**

- Instrumented tests assert no source/chunk/capsule loader runs during disclosure.
- Latency remains approximately constant as fixture corpus size increases.
- Interrupted atomic write preserves the last valid snapshot or returns not-ready.

### R-007 — Implement bounded lazy evidence resolution

**False or missing implementation**

`_InnerWorldEvidenceResolver` returns copies of the already included frame rows. It does not resolve source spans, verify provenance, enforce reference bounds, or measure actual bytes.

**What to build**

A resolver that accepts admitted compact references and returns whole, provenance-preserving evidence blocks within the effective grant and byte/token budgets.

**How to build it**

1. Require candidate references to carry source ID, fragment/span ID, content hash, and corpus revision.
2. Resolve only admitted IDs through an indexed point lookup.
3. Validate revision, branch, scope, allowed refs, and hash before reading content.
4. Include whole blocks; never truncate inside a provenance unit.
5. Stop at budget, record omitted IDs/reasons in audit, and keep omitted text out of execution and receipts.
6. Measure actual bytes read/resolved rather than summary-string length.

**Verification gate**

- Tampered hash, stale revision, denied ref, and missing span all abstain or omit explicitly.
- Resolver invocation count equals admitted block count, not corpus size.
- Receipt reconstruction identifies exact included spans without duplicating their text.

### R-008 — Harden every model-bound execution boundary

**False or missing implementation**

`compose_execution_message` renders `suppressed_blocks` when they are present, even if isolation is enabled. It assumes upstream sanitation instead of enforcing the execution contract itself.

**What to build**

Validation and sanitation at every model-bound composer. Audit-only fields must be structurally unrepresentable or rejected.

**How to build it**

1. Validate the input against `ExecutionBundle` immediately before prompt construction.
2. When isolation is enabled, reject any suppression/omission/audit key rather than toggling isolation off.
3. When legacy rollback is explicitly selected, keep the legacy object away from model-bound functions or sanitize it into a new execution object.
4. Enumerate all backend composers and centralize execution-bundle validation.
5. Add unique sentinel values in nested suppression summaries, provenance, receipts, and legacy aliases.

**Verification gate**

- Every composer either raises a typed contract error or emits a prompt without sentinels.
- Fuzz tests cover nested and aliased audit fields.
- Rollback mode cannot send suppressed material.

### R-009 — Fix Holodeck source-reference portability

**False or missing implementation**

The artifact candidate path eagerly evaluates `path.relative_to(root)` as a `dict.get` default. macOS `/var` and `/private/var` aliases make the focused parity test fail even when an explicit source reference exists.

**What to build**

A lazy, normalized source-reference helper used consistently by workspace projection candidates.

**How to build it**

1. Read and validate the explicit `source_ref` first.
2. Only compute a fallback when it is absent.
3. Resolve both root and candidate path before relative conversion.
4. If the file is outside the root, return a typed external reference or reject it according to policy; do not crash.

**Verification gate**

- Test `/var` versus `/private/var`, symlinked roots, explicit refs, missing refs, and outside-root files.
- `tests/test_holodeck_disclosure_parity.py` passes on macOS and Linux.

### R-010 — Replace Holodeck fail-open fallback with abstention

**False or missing implementation**

A broad exception while loading the Holodeck disclosure adapter/config sets the feature to disabled and resumes legacy meta-layer scoring. Dependency failure therefore widens retrieval.

**What to build**

Explicit failure states that preserve the selected rollout mode. A broken enforced/canary service must abstain, not silently become legacy.

**How to build it**

1. Catch only expected configuration/availability exceptions.
2. Return `abstained_dependency_not_ready` with a compact diagnostic code.
3. Permit legacy execution only when the operator-selected mode is `legacy` or an explicit rollback event changed it.
4. Emit a receipt/metric for dependency abstention without sensitive exception text.

**Verification gate**

- Import, config, catalog, and candidate-search failures all abstain.
- A spy proves the legacy scorer is not called in enforced mode.
- Explicit rollback mode still exercises the legacy path.

### R-011 — Activate receipts as release infrastructure

**False or missing implementation**

Receipt construction exists, but persistent receipts are disabled. Cross-request reconstruction, operator metrics, rollout comparisons, and durable failure analysis are therefore unavailable in the shipped configuration.

**What to build**

A bounded retention policy and staged receipt activation for every active surface.

**How to build it**

1. Finalize retention by envelope and surface, including deletion/compaction behavior.
2. Persist IDs, hashes, decisions, budgets, revisions, status, and timing—never raw suppressed evidence.
3. Enable Bridge receipts before shared-service shadow mode.
4. Add Holodeck and later-surface receipts as each adapter enters canary.
5. Provide health checks for write failure, retention lag, and corrupt rows; disclosure should remain safe if observability fails.

**Verification gate**

- One result is reconstructible after process restart.
- Incognito stores hashes/metrics only and honors retention.
- Retention and corruption recovery are tested on the persistent store.

### R-012 — Activate bounded ActiveState continuity deliberately

**False or missing implementation**

Continuity and rollback code exist but the feature is disabled, so the promised cross-turn state behavior is not part of the product.

**What to build**

A canary rollout tied to receipt and retention readiness, without turning state snapshots into another knowledge store.

**How to build it**

1. Keep only purpose, object, tension, posture, lens, branch, scope, and compact refs.
2. Enable for a bounded Bridge cohort after R-011.
3. Verify permitted Bridge-to-Holodeck transition semantics.
4. Add retention-safe rollback behavior when predecessors have expired.
5. Prove incognito creates no durable transition row.

**Verification gate**

- Multi-turn, cross-surface, expiry, rollback, corruption, and incognito suites pass with persistence enabled.

### R-013 — Certify and roll out feed and task-pack adapters

**False or missing implementation**

Both adapters are disabled and their evidence is based mainly on synthetic capsules. Feed synthesis and task-pack enrichment have not been certified against a representative populated corpus.

**What to build**

Treat them as later-surface rollouts after Bridge/Holodeck certification, with surface-specific grants, receipts, and quality gates.

**How to build it**

1. Keep both flags off until R-001–R-011 are complete.
2. Build representative feed and task-pack fixtures from the versioned seed corpus without committing private production content.
3. Verify equivalent candidate decisions against Bridge for equivalent grants while preserving surface presentation.
4. Add surface receipts and explicit empty/abstained UI behavior.
5. Roll out independently; one adapter's failure must not affect another.

**Verification gate**

- Feed proves precision, provenance, latency, and rollback on corpus-backed fixtures.
- Task packs prove no unrelated filler and preserve narrative handoff structure.
- Both abstain on dependency failure.

### R-014 — Complete or demote bounded-view integration

**False or missing implementation**

The bounded-view adapter is exposed through a port but no Bridge or Holodeck request consumes its evidence. Calling it “wired” overstates the implementation.

**What to build**

Choose one of two explicit outcomes:

- **Recommended:** wire it as an optional epistemic evidence source under an effective branch/scope grant; or
- demote it to an available experimental port and remove product integration claims.

**How to build the recommended option**

1. Add bounded-view root IDs to the requested/effective grant contract.
2. Invoke the port only after grant normalization and only when branch and scope are explicit.
3. Convert returned nodes into reference-only candidate/evidence blocks.
4. Feed them through the same admission, budget, resolution, compose, and receipt stages.
5. Never mix epistemic nodes into lexical ranking without a typed feature and conformance test.

**Verification gate**

- Competing branches/scopes remain isolated.
- No foundation record is mutated or duplicated.
- Missing branch/scope abstains, and flag-off makes no bounded-view call.

### R-015 — Enable metrics only over certified, persisted truth

**False or missing implementation**

The operator view is disabled and depends on receipts that are also disabled plus a Shape baseline that is not valid.

**What to build**

A read-only operator view over certified baseline revisions and persisted receipts from active surfaces.

**How to build it**

1. Complete R-003 and R-011 first.
2. Reject or visibly label uncertified baseline revisions.
3. Compare surface, corpus revision, policy hash, rollout mode, result status, latency, bytes, expansion, abstention, and parity.
4. Preserve k-anonymity/minimum-count or equivalent privacy thresholds for aggregates.
5. Keep the endpoint read-only; rollout mutation belongs to a separate authorized control plane.

**Verification gate**

- Metrics reconcile exactly with fixture receipts.
- Incognito aggregation cannot reveal source content or unique queries.
- Unsupported/uncertified revisions are clearly marked and excluded from release claims.

### R-016 — Establish an honest release verification gate

**False or missing implementation**

The focused workspace run produced 110 passes and one Holodeck failure. The full repository run produced 901 passes, 62 failures, and 4 skips. The workboard nevertheless marks all tasks done and records no blocker. Live coordination also reports repository observation `162184b8b04f`, while the audited branch and its remote are at `b361c9d200`, so its repository evidence is stale even though the projection mirror is fresh.

**What to build**

A versioned release gate that separates acknowledged repository debt from Cognitive Aperture regressions and cannot report completion while required suites fail.

**How to build it**

1. Publish an approved baseline of unrelated expected failures with test IDs and reasons; never baseline by failure count alone.
2. Define a Cognitive Aperture release suite covering contracts, catalog, admission, grant, budget, suppression, shared-service parity, Shapes, AntiMatch, evidence resolution, receipts, continuity, later adapters, metrics, and performance.
3. Run the focused suite on Linux and macOS.
4. Run the full repository suite and diff failures by test ID against the approved debt baseline.
5. Block release for any new failure, any required focused failure, any uncertified baseline, or any active known retrieval failure.
6. Reopen affected tasks through the live workspace API and republish projections; do not hand-edit task status.

**Verification gate**

- Required focused suite is fully green on both platforms.
- Full-suite failure set contains no unapproved regression.
- Live tasks, blockers, verification evidence, Git projections, and release commit all agree.

## 4. Recommended execution order

| Phase | Work | Why this order |
| --- | --- | --- |
| 0 — truth reset | R-016; reopen affected tasks and record blockers | Prevents agents from building on a false completion claim |
| 1 — safety boundary | R-005, R-008, R-009, R-010 | Grant, leakage, portability, and fail-closed behavior precede rollout |
| 2 — lightweight substrate | R-006, R-007, R-011 | Removes corpus-scale request work and creates reliable evidence/audit infrastructure |
| 3 — Shape quality | R-001, R-002, R-003 | Builds and proves the missing innovative capability on safe foundations |
| 4 — primary cutover | R-004, then R-012 | Enables Bridge and Holodeck before adding optional state behavior |
| 5 — later surfaces | R-014, R-013, R-015 | Adds bounded-view, feed/task-pack, and metrics only after primary certification |
| 6 — release | R-016 final rerun | Produces one auditable release decision |

Parallelism is safe only within these bounds:

- R-008 and R-009 can run in parallel.
- R-006 and R-007 can run in parallel after their contracts agree on revisioned references.
- R-001 and R-002 should be designed together but implemented as separate modules/tests.
- Feed and task-pack certification can run in parallel after primary cutover.

## 5. Proposed task disposition

These are recommendations for live coordination; they are not status mutations.

| Existing task | Proposed action | Blocking gaps |
| --- | --- | --- |
| CAE-001 | reopen | R-005 |
| CAE-002 | reopen | R-008 |
| CAE-003 / CAE-003A | reopen parent and leaf | R-005 |
| CAE-005 / CAE-005A / CAE-005B | reopen | R-004, R-006, R-007, R-009, R-010 |
| CAE-006 / CAE-006B | reopen | R-001, R-002, R-003 |
| CAE-007 | move to review until enabled/persistent proof | R-011 |
| CAE-008 | keep implemented-but-inactive; add rollout task | R-012 |
| CAE-009 / CAE-010 | keep implemented-but-inactive; add certification tasks | R-013 |
| CAE-011 | reopen or explicitly demote claim | R-014 |
| CAE-012 | move to review until dependencies certify | R-015 |
| CAE-013 | reopen performance portion | R-006 |
| CAE-014 | retain done as read adapter; extend via new Shape-search task | R-001, R-002 |
| CAE-015 | retain contract task; add downstream enforcement task | R-008 |

## 6. Reliable-v1 completion gate

Do not call the workspace complete until all of the following are true:

1. The normalized effective grant exists before any candidate search.
2. Incognito and denied-global requests make zero ocean-search calls.
3. Corpus readiness is read from an atomic revisioned snapshot, not rebuilt per request.
4. Shape projections can improve recall/ranking without becoming canonical truth.
5. AntiMatch demonstrably rejects a matching false analogy.
6. Evidence is resolved lazily by admitted span reference and actual bytes are measured.
7. No model-bound composer accepts or renders suppression/audit content.
8. Dependency failures abstain and never select a broader legacy path.
9. Bridge and Holodeck run the shared service in the release configuration.
10. Active surfaces emit compact privacy-safe receipts with tested retention.
11. Published quality and performance baselines are corpus-backed and certified.
12. Focused suites are green on macOS and Linux; the full suite has no unapproved regressions.
13. Live coordination, Git projections, verification records, and the release commit agree.

## 7. Fresh-agent use

Before implementing any packet:

1. Read `AGENT_BOOT.md`, this overview, `GAP_MAP.md`, ADR-001, ADR-002, and the affected existing task packet.
2. Query live coordination and run projection freshness checks.
3. Reproduce the specific failing or missing behavior before editing.
4. Refresh the codebase overview and pass the engineering guard with the smallest owner paths.
5. Implement one remediation packet at a time.
6. Record exact commands, results, fixture/corpus revisions, changed paths, rollout/rollback operation, and residual risk in live coordination.
7. Publish projections, commit, push, and request independent review.

The first implementation packet should be **R-005 — grant-first retrieval**, followed immediately by **R-008 — execution-boundary isolation**. They close the highest-risk authorization and leakage gaps before any shared-service activation.
