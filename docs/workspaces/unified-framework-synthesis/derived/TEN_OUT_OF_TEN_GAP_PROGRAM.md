# Ten-out-of-ten gap program

**Workspace:** `unified-framework-synthesis`  
**Status:** implementation-ready audit and program specification  
**Audit date:** 2026-07-21  
**Audited branch:** `cursor/shape-intelligence-remediation-pass` at `4570fec2fb`  
**Normative semantics:** Unified Metaphysical Modeling Framework v1.1  
**Coordination authority:** live workspace API; this document defines work, not task status

## 1. Target

Inner Space qualifies as a ten-out-of-ten epistemic operating system only when it can reliably:

1. preserve heterogeneous evidence without silently changing it;
2. form governed, intelligence-led interpretations;
3. represent entities, qualities, states, roles, relations, compositions, dimensions, and Shapes;
4. distinguish evidence, claims, interpretations, candidates, canon, Patterns, and simulations;
5. retrieve structurally relevant knowledge across domains without flooding context;
6. expose uncertainty, disagreement, branch, scope, time, authority, and provenance;
7. revise or retract derived knowledge without corrupting sources or unrelated branches;
8. support descriptive cybernetics and explicitly compiled execution semantics;
9. learn from outcomes without silently rewriting canonical truth; and
10. outperform strong memory and retrieval baselines under reproducible tests.

A gap is closed only when the production path satisfies its acceptance criteria. A schema, direct unit test, dormant flag, separate branch, mock adapter, or design document is not sufficient by itself.

## 2. Honest current-state snapshot

### Already real

- Durable conversation capture, transcripts, analysis, materialization, and indexing exist.
- The seed ocean contains 20 sources, 6,611 chunks, 1,069 analysis units, about 5,246 semantic capsules, 5,540 knowledge nodes, 33,637 edges, and 40,163 context links.
- Foundation runtime, SDK, profile registry, branch reasoning, vocabulary governance, bounded views, and conformance fixtures exist.
- Quality, Composition, Role, Shape, and Cybernetics profile contracts now exist, including `ShapeCore`, `ShapeView`, composite structure, descriptive dynamics, and future execution hooks.
- Cognitive Aperture has fail-empty admission, grant normalization, deterministic budgets, execution/audit separation, receipts, active-state infrastructure, bounded-view integration, adapters, certification harnesses, and a release gate.
- Hardened Shape Population exists at `origin/codex/shape-population-production-hardening` (`82a1c3589c`); 59 focused tests pass independently.
- Population includes streaming normalization, content-addressed storage, reference-only evidence, authenticated execution contexts, proposer/critic/synthesizer/evaluator roles, SQLite governance, async jobs, human-gated promotion, and an OpenClaw gateway.

### Not yet one system

- The hardened Population branch is not integrated into the audited branch.
- The canonical Shape reader asks for `profile:shape_and_semantic_addressing` and `MetaphysicalKernelRuntime`; the implemented authority is `profile:shape` on `FoundationRuntime`.
- Population candidates are not transactionally mapped into complete canonical Shape/composition/role/cybernetics records.
- Three focused Shape retrieval tests fail: structural promotion, dependency abstention reporting, and AntiMatch hard rejection.
- Checked-in production configuration keeps shared disclosure, persistent receipts, active state, operator metrics, and bounded-view integration disabled.
- The seed ocean has no corpus-wide embedding index and effectively no branch/scope coverage.
- Profile definitions exist in code, but the audited local foundation store is not a populated canonical universe.
- No benchmark proves cross-domain structural retrieval, token efficiency, correction behavior, or agent-task improvement against strong alternatives.

### Audit evidence

```text
Audited integration branch: 152 passed, 3 failed across 155 focused tests.
Hardened Population branch: 59 focused tests passed.
```

## 3. Program-wide invariants

1. Raw evidence and derived interpretation remain separate.
2. Deterministic normalization may preserve, segment, hash, validate, route, budget, and transact; it may not determine Shape meaning.
3. Intelligence proposes and critiques; it does not mint its own authority.
4. Similarity after proposal may generate neighbors; it is not proof of identity, equivalence, causality, or Pattern membership.
5. Candidates remain provisional until authorized promotion succeeds through the canonical owner.
6. Canonical records retain source spans, model/prompt/tool versions, branch, scope, perspective, time, and uncertainty.
7. Multiple interpretations may coexist; disagreement is not averaged away.
8. Retrieval fails empty or abstains when authorization, readiness, or dependencies are absent.
9. Suppressed evidence must be unrepresentable in model-bound payloads.
10. Cybernetic description is not execution. Compilation is explicit, validated, loss-reported, and reversible.
11. Learning may propose policy changes; it may not silently rewrite canonical knowledge.
12. Applications may not create parallel ontologies or bypass kernel/profile authority.
13. Every mutation is idempotent, attributable, auditable, and recoverable.
14. Release claims require production-path evidence, not only mocks or fixtures.

## 4. Blocking gap index

| ID | Blocker | Severity | Owner | Depends on |
|---|---|---:|---|---|
| T10-00 | One integration and release baseline | Critical | foundation/release | none |
| T10-01 | Canonical Shape authority and identity | Critical | Shape profile | T10-00 |
| T10-02 | Population-to-canonical Shape mapping | Critical | Population + Shape | T10-01 |
| T10-03 | Live Shape Population operation | Critical | Population | T10-00, T10-02 |
| T10-04 | Canonical ocean population and migration | Critical | corpus/foundation | T10-02, T10-03 |
| T10-05 | Hybrid semantic/structural indexing | High | retrieval | T10-04 |
| T10-06 | Pattern, AntiMatch, and transfer reasoning | Critical | Pattern profile | T10-02, T10-05 |
| T10-07 | Shape-aware retrieval repair | Critical | Cognitive Aperture | T10-01, T10-05, T10-06 |
| T10-08 | Safe disclosure/state activation | Critical | Aperture/release | T10-07 |
| T10-09 | Temporal, contradiction, revision semantics | High | branch/foundation | T10-04 |
| T10-10 | Executable cybernetic compilation | High | transformation | T10-02, T10-09 |
| T10-11 | Governed outcome learning | High | learning/evaluation | T10-07, T10-10 |
| T10-12 | Authorization, privacy, poisoning resistance | Critical | security | T10-03, T10-08 |
| T10-13 | Multi-agent concurrency/conflicts | High | governance | T10-04, T10-12 |
| T10-14 | Comparative quality benchmarks | Critical | evaluation | T10-05–13 |
| T10-15 | Scale, cost, durability, recovery | Critical | operations | T10-03–08 |
| T10-16 | Observability and lifecycle controls | High | operations | T10-03, T10-08, T10-15 |
| T10-17 | Coherent agent harness | Critical | SDK/harness | T10-08, T10-12 |
| T10-18 | Inspectable Shapes and provenance | Medium | surfaces | T10-17 |
| T10-19 | Repository and release discipline | High | engineering | T10-00 |

## 5. Detailed remediation packets

## T10-00 — Establish one integration and release baseline

**Problem:** independently credible components live on incompatible branches, so “implemented” is ambiguous.

### Instructions

1. Name one integration branch and one release commit as code authority.
2. Produce a reconciliation matrix for every relevant commit: owned paths, conflicts, tests, and disposition (`merge`, `reimplement`, `supersede`, or `reject`).
3. Import hardened Population without stale workspace projections or malformed LFS/JSONL history.
4. Resolve conflicts by authority: framework v1.1 for semantics, live API for coordination, selected Git baseline for code.
5. Delete obsolete adapters only after all consumers migrate.
6. Generate one release manifest containing commit, schema/profile/prompt/model/policy versions, migrations, flags, corpus revision, and benchmark revision.

### Requirements

- All required modules are reachable from one checkout.
- Accepted commits are ancestors of the release or explicitly superseded.
- No duplicate profile identity, parallel canonical store, unresolved conflict marker, or malformed JSONL remains.
- A fresh clone reproduces the environment and focused tests.

### Verification

- Run foundation, Population, retrieval, disclosure, and release suites from the same checkout.
- Compare exported contracts before and after integration.
- Inspect staged paths; never use blind `git add -A`.

## T10-01 — Repair canonical Shape authority

**Problem:** the reader and profile registry disagree on profile ID and runtime class, while broad exception handling conceals programming defects as valid unavailability.

### Instructions

1. Declare `profile:shape` plus its semantic version as canonical unless a reviewed ADR deliberately renames it.
2. Use `FoundationRuntime` and `ProfileRegistry` behind an explicit read interface.
3. Distinguish absent, incompatible, corrupt, unauthorized, empty, and unexpected-failure states.
4. Read projections by branch, scope, perspective, time, maturity, epistemic standing, and governance standing.
5. Keep legacy signatures behind a candidate-only adapter with a dated retirement criterion.
6. Add profile-version negotiation and migration behavior.

### Requirements and tests

- A bootstrapped profile is available; absence returns typed abstention.
- Programming errors fail the release gate instead of becoming “unavailable.”
- Legacy candidates can never appear promoted.
- Projection round trips preserve authority, provenance, lifecycle, branch, scope, and abstraction contract.
- Test available, absent, incompatible, corrupt, unauthorized, empty, and legacy-retirement cases.

## T10-02 — Map Population output into canonical Shape records

**Problem:** generic intelligence candidates do not yet close over the richer canonical ontology.

### Instructions

1. Version a `PopulationCandidate -> CanonicalShapeProposal` contract.
2. Separate observed and unresolved referents; qualities and claimed states; relations and participant roles; boundary, dimension, scale, time, perspective; composition and influence; mechanisms, constraints, feedback, delays, uncertainty; counter-hypotheses and negative evidence.
3. Resolve kernel referents without merging solely by label or embedding similarity.
4. Build `ShapeCore` only from closed validated references and `ShapeView` as a perspective/scope projection.
5. Keep disagreements as separate proposals/views.
6. Apply approval through one transaction/outbox boundary to the canonical owner.
7. Record semantic-loss warnings for unrepresentable fields.
8. Mark canonical locally only after the owner returns a versioned receipt.

### Requirements

- Every promoted Shape terminates in exact spans or explicit creation events.
- No dangling quality, role, relation, participant, or composition reference exists.
- Replay is idempotent; rollback uses compensating events.
- Source withdrawal stales dependent projections without deleting unrelated knowledge.
- Fixtures cover simple, multidimensional, nested-quality, composite, feedback, competing-view, and AntiMatch cases.

## T10-03 — Integrate and operate live Shape Population

**Problem:** 59 tests pass independently, but the workflow is not proven as the deployed post-ingest path.

### Instructions

1. Integrate content storage, normalizer, packet assembler, gateway, identities, SQLite store, worker, orchestrator, promotion port, and ingest hook.
2. Provision dedicated proposer, critic, synthesizer, and evaluator identities from versioned manifests.
3. Give each identity only declared tools and bounded evidence; source content is untrusted data.
4. Keep ingest available if Population fails; persist enqueue failure and retry state.
5. Add leasing, bounded retry, dead letter, idempotency, cancellation, replay, and backpressure.
6. Enforce token, evidence, cost, concurrency, and wall-time budgets.
7. Pin model, prompt, tool-contract, and policy versions in receipts.
8. Support deterministic mock tests and a live OpenClaw canary.

### Requirements

- Large uploads return a source receipt immediately and enqueue async work.
- Worker crashes at any transition lose no job and create no duplicate candidate.
- Model JSON cannot choose identity, authority, approval, canonical status, or runtime metadata.
- Prompt injection cannot gain tools, change policy, or cite outside its packet.
- Human approval precedes canonical apply; rejection is terminal for that request.
- Operators can pause, drain, resume, retry, cancel, and inspect jobs.

### Golden production trace

```text
ingest -> normalize -> inquiry -> evidence -> propose -> critique
-> synthesize -> evaluate -> human approve -> canonical apply -> retrieve
```

Archive every ID, version, and receipt.

## T10-04 — Populate and migrate the canonical knowledge ocean

**Problem:** the substantial legacy ocean and the new foundation do not yet form one canonical branch/scope-aware corpus.

### Instructions

1. Make a versioned `CorpusCatalog` the sole readiness contract.
2. Inventory every source and derived family: count, schema, digest, provenance, branch/scope/time coverage, profile coverage, index capabilities, and staleness.
3. Assign explicit branch/scope to sources and fragments. Ambiguous placement goes to review; do not invent it silently.
4. Reprocess the 20-source seed through the intelligence workflow as a controlled pilot.
5. Preserve 454 deterministic signatures only as legacy candidates/comparison evidence.
6. Deduplicate bytes by content hash while retaining distinct provenance/context events.
7. Build dependency indexes for withdrawal, correction, permission change, and staleness propagation.
8. Support reproducible corpus snapshots and rebuilds from sources plus transformation manifests.

### Requirements

- Certified source digest, provenance, branch, scope, and visibility coverage are 100%, or exclusions are explicit and justified.
- Every derived record ends in a source or explicit authoring event.
- Deterministic rebuilds are identical; intelligence rebuilds are semantically equivalent within a locked tolerance.
- Source removal stales all and only dependent projections.
- Catalog returns not-ready for stale required indexes or incomplete migration.

## T10-05 — Build hybrid semantic and structural indexing

**Problem:** lexical and graph material exists, but no corpus-wide vector/semantic-address layer supports efficient cross-domain candidate generation.

### Instructions

1. Implement replaceable exact, lexical, semantic-address, vector, graph, and structural-fingerprint ports.
2. Embed compact derived representations and bounded fragments, not duplicated whole documents.
3. Record embedding model, dimensions, normalization, input digest, policy, and time for each vector.
4. Fingerprint roles, topology, dimensions, boundary, scale, state configuration, and optional feedback motifs.
5. Use approximate indexes only for candidate pools; verify structurally and, where needed, through intelligence afterward.
6. Support incremental add/update/tombstone, side-by-side re-embedding, migration, rebuild, and rollback.
7. Apply authorization, branch, scope, lifecycle, and time filters before evidence resolution.
8. Keep source bytes content-addressed and referenced, never copied into every index.

### Requirements

- Normal queries never scan the full ocean.
- Stale or corrupt indexes abstain; they never widen retrieval.
- Similarity alone cannot merge or promote.
- Model upgrades can run side by side and roll back.
- Publish footprint, build/update time, recall, and p50/p95/p99 query latency per revision.

## T10-06 — Complete Pattern, AntiMatch, and transfer reasoning

**Problem:** Shape contracts exist, but cross-domain Pattern induction and transfer remain unproven.

### Instructions

1. Implement Pattern as a derived abstraction over a declared Shape population.
2. Represent role mappings, preserved/violated/unknown invariants, abstracted values, boundary/scale correspondences, mechanism differences, and transfer limits.
3. Separate candidate match, validated membership, AntiMatch, and transfer hypothesis records.
4. Require evidence and an abstraction contract for each invariant.
5. Use inexpensive candidate generation followed by structural alignment and independent critique.
6. Preserve rejected analogies and negative examples.
7. Calibrate by domain, Pattern family, evidence density, and reviewer agreement.

### Requirements

- Recover low-vocabulary-overlap cross-domain pairs through shared structure.
- Reject lexically similar but structurally incompatible distractors.
- Explain exactly where an analogy holds, breaks, and abstracts details.
- Never merge Shapes merely because they instantiate a Pattern.
- AntiMatches remain branch/scope-aware and revisable.

### Dataset

Build blinded, expert-adjudicated positive, partial, negative, adversarial, scale-mismatch, boundary-mismatch, temporal-mismatch, and mechanism-mismatch pairs across at least ten unrelated domains.

## T10-07 — Repair and certify Shape-aware retrieval

**Problem:** three focused tests fail because fail-empty/catalog logic returns before Shape results and AntiMatch decisions are represented.

### Instructions

1. Lock the order: authorization -> catalog readiness -> Shape dependency -> positive admission -> ranking -> AntiMatch -> evidence resolution -> budget.
2. Return a typed `shape_retrieval` result for ready, empty, abstained, denied, stale, and failed requests.
3. Keep admission separate from ranking; Shape score may reorder only eligible candidates.
4. Apply hard AntiMatch exclusion before evidence resolution and receipt the reason.
5. Prefer canonical Shapes; label provisional candidates explicitly.
6. Check boundary, scale, dimension, perspective, time, mechanism, branch, and scope compatibility.
7. Test lexical/vector/graph/structural combinations and ablations.

### Requirements

- All focused tests pass, including the three audit failures.
- Structural gold candidates outrank lexical distractors without widening grants.
- AntiMatches never enter execution evidence.
- Missing profile or stale index abstains explicitly.
- Candidate/canonical status survives into bundle and receipt.

## T10-08 — Activate bounded disclosure and state safely

**Problem:** Cognitive Aperture is largely implemented and certified, but checked-in release flags remain legacy/off.

### Instructions

1. Reconcile certification artifacts and environment-specific config under one authority.
2. Roll out: receipt shadow -> shared-service shadow -> bounded-view shadow -> canary disclosure -> persistent receipts -> active state -> metrics -> enforcement.
3. Lock parity/divergence thresholds across Bridge, Holodeck, feed, task packs, and agent harness.
4. Prove incognito performs no durable learning or active-state persistence.
5. Define receipt/state retention, deletion, redaction, access, and backup behavior.
6. Keep rollback configuration-only.

### Requirements

- Release config enables the certified path for a declared cohort.
- Leakage, denial, divergence, budget, error, and latency stay within thresholds for a declared observation window.
- Every execution has a reconstructible receipt or explicit incognito hash-only receipt.
- A kill switch restores legacy execution without corrupting sessions or indexes.
- Full activation requires zero unauthorized disclosure in adversarial and canary review.

## T10-09 — Complete temporal, contradiction, and revision semantics

**Problem:** branches and lifecycle axes exist, but the system cannot yet prove a complete historical account of validity and belief change.

### Instructions

1. Distinguish event, observation, valid, ingest, interpretation, and supersession time.
2. Add point/interval queries for states, qualities, relations, ShapeViews, and Pattern memberships.
3. Represent contradiction, correction, supersession, retraction, expiry, and unresolved conflict without overwrite.
4. Propagate staleness through dependencies.
5. Require branch-aware conflict policy for shared views.
6. Reproduce historical queries against corpus/profile/policy revisions.

### Requirements

- Answer “what did branch B support at time T?” with full provenance.
- Corrections affect current retrieval without rewriting historical receipts.
- Contradictory evidence coexists and is surfaced according to perspective/grant.
- Retraction/expiry leaves no zombie projection queryable as current.

## T10-10 — Add executable cybernetic compilation

**Problem:** descriptive cybernetics and extension hooks exist, but equations, update rules, solvers, and interventions are intentionally not yet executable.

### Instructions

1. Keep the canonical cybernetic record descriptive and execution-neutral.
2. Define versioned types for variables, units, parameters, equations, rules, events, delays, constraints, objectives, observations, interventions, and uncertainty.
3. Compile into derived `ExecutableModelIR` with source mappings and semantic-loss warnings.
4. Validate dimensions, reference closure, stochasticity, initialization, time, numerical bounds, and parameter gaps.
5. Implement one narrow adapter first, preferably rule-based discrete-event execution.
6. Receipt compiler, scenario, parameters, solver, run, and results.
7. Keep predictions as simulation outputs, never observed states or canonical facts.

### Requirements

- One descriptive Shape may compile into alternative models without mutation.
- Missing semantics produces typed abstention or a parameter-gap record.
- Every output traces to model, scenario, parameters, solver, sources, and assumptions.
- Sensitivity/counterfactual runs retain uncertainty and branch separation.
- Execution cannot mutate evidence or canon through side effects.

## T10-11 — Implement governed outcome learning

**Problem:** feedback concepts exist, but useful retrieval and interpretation do not yet improve future policy with proven safeguards.

### Instructions

1. Separate outcome, user preference, reviewer judgment, task success, and factual validation events.
2. Attribute uncertain credit to signals, evidence blocks, matches, disclosure choices, prompts, tools, and model versions.
3. Start with offline proposals and replay evaluation; no online self-modification initially.
4. Maintain control cohorts and counterfactual baselines where appropriate.
5. Gate ranking, prompt, and threshold policy promotion.
6. Detect reward hacking, popularity bias, feedback amplification, and novelty/minority suppression.
7. Roll back policy independently of canonical knowledge.

### Requirements

- Learning cannot alter sources, Shape identity, or approval history.
- Held-out replay improves task metrics without safety/minority regression.
- Each policy records corpus, metrics, approval, canary, and rollback.
- Current decisions can name the prior outcomes that influenced policy.

## T10-12 — Prove authorization, privacy, consent, and poisoning resistance

**Problem:** strong local grant and least-privilege designs need end-to-end adversarial proof.

### Instructions

1. Define principals, capabilities, resource scopes, delegation, expiry, revocation, and human approval in one authorization model.
2. Authorize before search, graph expansion, vector lookup, evidence resolution, prompt construction, and receipt inspection.
3. Encrypt sensitive storage/transport and define key rotation and backup behavior.
4. Implement classification, consent, retention, export, deletion, redaction, legal hold, and derived-data invalidation.
5. Defend against prompt injection, poisoned content/metadata, malicious graph edges, embedding attacks, tool escalation, and covert cross-scope inference.
6. Minimize receipt content and suppress low-cardinality private metrics.
7. Complete threat modeling and independent red-team review before broad activation.

### Requirements

- Cross-tenant/scope, revoked, expired, incognito, and denied tests reveal neither content nor sensitive metadata.
- Deletion/revocation invalidates derived retrieval while retaining only required audit hashes.
- Source text cannot invoke tools or alter identity/instructions.
- Backup restore preserves authorization and deletion tombstones.
- Security events are attributable and alertable without leaking evidence.

## T10-13 — Prove multi-agent concurrency and conflict behavior

**Problem:** workspace coordination exists, but canonical epistemic operations need explicit concurrent semantics.

### Instructions

1. Add optimistic concurrency/version preconditions to mutations.
2. Make proposal, evaluation, approval, promotion, rollback, and retraction idempotent.
3. Preserve distinct agent perspectives and authority contexts.
4. Route incompatible decisions to branches/review rather than last-write-wins.
5. Define delegation and quorum policy for high-impact shared knowledge.
6. Test partitions, delays, replay, worker crashes, and out-of-order completion.

### Requirements

- Idempotent exactly-once effects under at-least-once delivery.
- Concurrent incompatible promotions never silently overwrite.
- Stale writers receive a conflict plus current version.
- Reconciliation never invents consensus.

## T10-14 — Create decisive comparative quality benchmarks

**Problem:** local invariants do not establish category-leading agent utility.

### Instructions

1. Version held-out corpora for factual recall, temporal change, contradiction, continuity, Shape extraction, structural analogy, transfer, privacy, poisoning, and correction.
2. Compare raw long context, lexical/BM25, vector, vector+reranker, conventional graph/GraphRAG, a competitive agent-memory baseline, Inner Space ablations, and complete Inner Space.
3. Use blinded expert adjudication for Shape/analogy quality and report inter-rater agreement.
4. Report precision, recall, nDCG/MRR, calibration, unsupported claims, contradiction detection, transfer, task success, tokens, latency, and cost.
5. Publish failures and confidence intervals; no aggregate may hide a load-bearing failure.
6. Reproduce from a fresh clone and frozen release.

### Candidate thresholds

Lock final thresholds before viewing held-out results. Initial targets:

- 100% source/provenance traceability on certified outputs;
- zero unauthorized evidence disclosure in adversarial tests;
- at least 0.90 factual evidence recall at the declared budget;
- at least 0.80 structural-pair recall@10 and 0.75 blinded precision;
- at most 0.02 known-AntiMatch leakage into execution bundles;
- statistically significant task improvement over the strongest baseline;
- at least 30% median model-bound token reduction at non-inferior quality;
- a locked expected-calibration-error threshold;
- corrections/retractions reflected in 100% of current-view cases.

These are targets, not achieved claims. Changes require a decision recorded before held-out evaluation.

## T10-15 — Prove scale, latency, cost, durability, and recovery

**Problem:** the seed is too small and unit tests too narrow to prove lightweight production operation.

### Instructions

1. Benchmark current, 10x, 100x, and maximum affordable corpus tiers.
2. Measure ingest throughput, normalization memory, queue depth, model cost, index growth, update latency, query p50/p95/p99, evidence bytes, prompt tokens, and end-to-end time.
3. Keep normalization memory bounded by chunk/window, not document size.
4. Add capacity limits, backpressure, admission control, quotas, and graceful degradation.
5. Test process kill, machine restart, database corruption, low disk, network loss, model timeout, duplicate delivery, and stale-index recovery.
6. Define backup, restore, point-in-time recovery, RPO/RTO, and integrity checks.
7. Publish cost per source MB, candidate, canonical Shape, query, and agent task.

### Requirements

- Multi-gigabyte logical streams normalize without loading the complete source.
- Retrieval grows sublinearly with corpus size under declared indexes.
- No failure loses accepted evidence or creates unreceipted canon.
- Recovery objectives pass drills.
- Degraded dependencies reduce capability explicitly; they never widen access.

## T10-16 — Build operator observability and lifecycle controls

**Problem:** receipts and metrics do not yet form an enabled, complete control plane.

### Instructions

1. Correlate source, ingest, job, model run, candidate, evaluation, approval, canon, index, retrieval, execution, and learning events.
2. Dashboard backlog, errors, abstentions, stale indexes, cost, latency, quality drift, denials, and review queues.
3. Add authorized pause, drain, replay, reindex, rebuild, and rollback controls.
4. Define SLOs and alerts for availability, freshness, durability, privacy, quality, and cost.
5. Detect profile, prompt, model, policy, corpus, and embedding drift.
6. Keep telemetry reference-based and privacy-preserving.

### Requirements

- Reconstruct any disclosed block from its receipt and revisions.
- Every stuck job/stale projection has a bounded repair path.
- Alerts distinguish expected abstention from infrastructure failure.
- Recovery drills preserve complete lineage.

## T10-17 — Expose one coherent agent harness

**Problem:** many CLIs, APIs, MCP tools, and Bridge paths expose valuable but inconsistent internal capabilities.

### Instructions

1. Version a small harness around agent intent, not storage operations.
2. Read tools must orient state/branch/scope, retrieve bounded evidence, find similar Shapes, inspect provenance, compare branch/time, and explain uncertainty/conflict.
3. Write tools must capture source, propose interpretation/correction, submit evaluation, request review, and record outcome.
4. Keep promotion, authorization admin, deletion, and policy deployment on separate privileged tools.
5. Return typed status, compact summary, stable IDs, continuation, and optional deeper views.
6. Conform OpenClaw, MCP, CLI, and test adapters to the same contract.

### Requirements

- A fresh authorized agent completes the canonical trace without filesystem/database access.
- Model payloads cannot supply authority fields.
- Equivalent adapter requests yield equivalent grants/evidence decisions.
- Every response labels candidate/canonical status and provenance inspection.
- Compatibility, rate-limit, cancellation, timeout, and conformance tests pass.

## T10-18 — Make Shapes, provenance, and disagreement inspectable

**Problem:** the epistemic advantage is invisible if users see only answers or opaque nodes.

### Instructions

1. Build a bounded Shape inspector for entities, qualities, states, roles, relations, boundary, dimension, scale, time, and perspective.
2. Separate evidence and interpretation visually.
3. Show competing views, counterevidence, uncertainty, lifecycle, and authority.
4. Show Pattern alignment as mappings and differences, never just a score.
5. Show feedback, delay, constraint, observation, intervention, and simulation with status.
6. Provide capability-controlled correct, dispute, approve, reject, retract, and lineage actions.
7. Progressively disclose graphs; never render the full ocean by default.

### Requirements

- Users can answer “why did the agent see/believe this?” without raw JSON.
- Candidate, canonical, simulated, contradicted, and stale content are unmistakable.
- Corrections create governed events rather than editing evidence.
- Expert usability tests detect seeded unsupported relations and false analogies.

## T10-19 — Close repository and release-discipline debt

**Problem:** the atlas reports 28 missing production module manifests, the general release gate carries approved debt, and focused Shape retrieval is red.

### Instructions

1. Add owner/purpose/dependency manifests for all production disclosure and Shape modules.
2. Eliminate or explicitly quarantine public-substrate failures; do not normalize a permanently red hermetic suite.
3. Separate unit/integration tests from live-service tests with markers.
4. Fail release on new debt, stale generated artifacts, profile/contract drift, and unregistered production modules.
5. Lock dependencies and setup; add platform matrix, security scanning, and artifact checksums.
6. Define deprecation/migration windows for public tool/profile contracts.

### Requirements

- Overview refresh/validate has zero errors, warnings, and missing production manifests.
- Hermetic full suite is green from a fresh clone.
- Live suites are reported separately and cannot be confused with unit success.
- Release artifacts trace to source commit and test evidence.

## 6. Ordered execution

### Wave 0 — Make the baseline truthful

1. T10-00 integration baseline.
2. T10-19 discipline for touched modules.
3. Freeze release manifest and benchmark datasets before results influence thresholds.

**Exit:** one checkout, one manifest, reproducible suites, no ambiguity about implemented code.

### Wave 1 — Close the canonical Shape lifecycle

1. T10-01 authority.
2. T10-02 canonical mapping.
3. T10-03 Population integration.
4. Run one approved golden production trace.

**Exit:** a large source becomes a provenance-complete canonical Shape through production.

### Wave 2 — Turn the seed into a governed ocean

1. T10-04 migration/population.
2. T10-05 indexes.
3. T10-09 time/revision.

**Exit:** the certified corpus is branch/scope/time/provenance complete, reproducibly indexed, and correctable.

### Wave 3 — Prove structural intelligence

1. T10-06 Pattern/AntiMatch.
2. T10-07 retrieval.
3. T10-14 first comparative benchmark.

**Exit:** structural matches beat lexical/vector distractors on held-out cross-domain cases and explain limits.

### Wave 4 — Put it safely into daily agent use

1. T10-08 activation.
2. T10-12 security/privacy.
3. T10-13 concurrency.
4. T10-17 harness.
5. T10-18 inspection.

**Exit:** independent agents use a small authorized harness and humans can inspect/correct the epistemic basis.

### Wave 5 — Dynamics, learning, and production proof

1. T10-10 executable cybernetics.
2. T10-11 outcome learning.
3. T10-15 scale/recovery.
4. T10-16 operations.
5. T10-14 final benchmark and independent replication.

**Exit:** useful, efficient, recoverable, and empirically superior—not merely theoretically complete.

## 7. Master release gates

### A — Canonical closure

- One source-to-canonical-Shape-to-retrieved-evidence production path.
- Full provenance and independent lifecycle states.
- No parallel authority or silent fallback.

### B — Structural intelligence

- Held-out cross-domain precision/recall meets locked thresholds.
- AntiMatches, boundary/scale failures, and mechanism differences are enforced and explained.

### C — Epistemic safety

- Evidence, interpretation, claim, canon, Pattern, and simulation remain distinct.
- Contradiction, retraction, uncertainty, and branches remain visible/reversible.

### D — Authorization and privacy

- Zero unauthorized disclosure in adversarial certification.
- Consent, expiry, revocation, deletion, incognito, and restore work end to end.

### E — Agent usefulness

- Independent agents significantly outperform the strongest baseline.
- Model-bound tokens fall materially without quality loss.
- Selection and deeper evidence are inspectable.

### F — Production reliability

- Scale, concurrency, crash, recovery, stale-index, timeout, and rollback pass.
- SLOs and costs hold during a canary period.

### G — Reproducibility

- A fresh environment reproduces contracts, migrations, corpus, indexes, tests, and reports.
- An independent reviewer reproduces the main claims.

## 8. Required task-packet contents

Every task derived from this program must contain:

1. gap ID and one-sentence user/system effect;
2. scope-in and scope-out;
3. semantic authority and owner module;
4. dependencies and exact profile/schema versions;
5. engineering-guard-approved paths;
6. migration and compatibility behavior;
7. authorization, privacy, failure, retry, and rollback behavior;
8. unit, property, integration, adversarial, performance, and smoke tests as applicable;
9. measurable thresholds;
10. exact verification commands/results;
11. changed artifacts and residual risks; and
12. live API update, projection publish, commit, and push evidence.

Code existence is not completion. Production behavior and verification evidence are required.

## 9. Recommended first milestone

Start with T10-00, then T10-01 and T10-02. The shortest decisive milestone is:

```text
large source
-> lossless receipt
-> intelligence-led proposal
-> independent critique/evaluation
-> human approval
-> canonical ShapeCore/ShapeView
-> indexed projection
-> bounded retrieval
-> provenance explanation
-> correction or rollback
```

Until this works from one release checkout, broader capability remains difficult to evaluate and easy to overstate.
