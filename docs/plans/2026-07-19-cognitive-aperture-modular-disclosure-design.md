# Modular Cognitive Aperture Design

**Status:** accepted for planning
**Workspace:** `cognitive-aperture-exceptional`
**Date:** 2026-07-19
**Decision:** the aperture workspace owns disclosure, not ingestion or canonical Shape formation

## 1. Outcome

Build a small, deterministic disclosure service that places an agent in the correct knowledge neighborhood without copying the knowledge ocean into prompts or creating another truth store.

The service accepts a request, current state, and disclosure policy. It returns either:

- a bounded execution bundle containing thin orientation and authorized evidence; or
- an explicit abstention with a machine-readable reason.

It also emits a separate audit receipt. Suppressed material is never present in the execution-bound object.

## 2. Ownership boundary

### This workspace owns

- requested-policy normalization into one effective grant;
- fail-empty candidate admission;
- deterministic evidence selection and budgeting;
- execution-safe projection;
- audit receipts and disclosure metrics;
- Bridge and Holodeck adapters first;
- conformance tests for later surface adapters.

### This workspace does not own

- raw source ingestion, parsing, or chunking;
- canonical identity, branch, scope, provenance, or lifecycle storage;
- canonical Shape derivation or promotion;
- embedding generation or vector-store operations;
- domain-specific ontology;
- surface-specific presentation or persistence.

Those capabilities remain behind explicit read contracts. The aperture may report that a dependency is not ready; it must not silently recreate it.

## 3. Architectural context

```text
External ingestion and canonical modeling
  raw source -> fragments -> records -> semantic addresses -> candidate/promoted Shapes
                                      |
                                      v
                         versioned retrieval projections
                                      |
                                      v
Disclosure service
  request -> state -> effective grant -> candidate gate -> evidence resolve
          -> budget -> ExecutionBundle + AuditReceipt
                                      |
                         +------------+------------+
                         |                         |
                      Bridge                   Holodeck
                    adapter/view              adapter/view
```

The raw source is stored once. Chunks, indexes, Shape projections, and receipts retain references to it rather than copying the source text into parallel stores.

## 4. Required external ports

The disclosure service depends on narrow interfaces rather than concrete storage modules.

### `CorpusCatalog`

Reports corpus revision, readiness, source visibility, branch/scope coverage, and index capabilities. A corpus is not ready merely because files exist.

Required readiness fields:

- `corpus_revision`;
- source, fragment, and indexed-record counts;
- provenance coverage;
- branch/scope coverage;
- semantic-address coverage;
- Shape projection coverage;
- stale/interrupted pipeline indicators;
- supported candidate-search signals.

### `CandidateSearch`

Returns compact candidate references, never arbitrary prompt text. It may use lexical, alias, semantic-address, structural, embedding, explicit-pin, or governed-graph signals.

Every candidate must declare its positive admission signals. Confidence alone is not an admission signal.

### `ShapeProjectionReader`

Reads branch- and scope-bound Shape projections from the canonical framework profile. Provisional legacy signatures may be exposed only when labeled `candidate` and tied to source evidence.

The reader must distinguish:

- candidate Shape;
- promoted/validated Shape;
- Pattern membership;
- rejected match / AntiMatch;
- unavailable Shape profile.

### `EvidenceResolver`

Resolves selected references to bounded evidence blocks with source spans, sensitivity, branch, scope, and integrity metadata. Resolution is lazy: only admitted candidates are opened.

### `ReceiptSink`

Stores audit receipts under an explicit retention policy. Incognito receipts contain operational metrics and hashes only; they must not persist sensitive evidence text.

## 5. Core contracts

### `ApertureRequest`

Contains request ID, surface, user turn, session/workspace IDs, explicit pins, requested depth, and caller capabilities. It contains no inferred permission.

### `ActiveStateSnapshot`

A versioned, bounded snapshot of current topic, purpose, object, tension, posture, lens, branch, scope, and source revision. It is derived from the current turn and already-authorized local continuity—not undisclosed global evidence.

### `RequestedGrant`

Captures caller intent: requested layers, references, dimensions, Shape maturity, cross-ocean behavior, envelope, budgets, and persistence mode.

### `EffectiveGrant`

The only policy consumed downstream. It is the result of:

```text
requested grant
+ envelope defaults
+ workspace and source policy
+ branch/scope visibility
+ explicit pins
- explicit denials
= effective grant
```

Denials always win. The contract records requested versus effective values and every narrowing reason.

### `CandidateRef`

A compact pointer with candidate kind, source/projection ID, branch, scope, maturity, positive admission signals, ranking features, and provenance reference. Candidate admission and ranking are separate decisions.

### `EvidenceBlock`

An indivisible budgeting unit containing bounded text, token estimate, source span, inclusion reason, sensitivity, branch, scope, and content hash.

### `ExecutionBundle`

Contains only:

- capped orientation;
- thin steering constraints;
- admitted evidence blocks;
- public provenance references;
- applied budget summary.

It cannot represent omitted or suppressed content. This is a type-level security boundary.

### `AuditReceipt`

Contains request and corpus revisions, requested/effective grant, candidate decisions, included block IDs, omitted IDs and reasons, budget ledger, policy hashes, surface, and result status. Sensitive text is referenced, not duplicated.

## 6. Disclosure algorithm

1. Validate dependency readiness and request identity.
2. Build `ActiveStateSnapshot` from authorized local state.
3. Normalize policy exactly once into `EffectiveGrant`.
4. Ask `CandidateSearch` for compact references within the granted search space.
5. Apply the positive relevance gate.
6. Apply branch, scope, privacy, maturity, Shape, and AntiMatch filters.
7. Rank only admitted candidates.
8. Lazily resolve evidence for the smallest ranked set that can satisfy the request.
9. Allocate the evidence budget deterministically by whole block.
10. Build `ExecutionBundle` and `AuditReceipt` separately.
11. Return bundle, explicit empty result, or explicit abstention.

No-match is a successful empty disclosure, not an exception. Dependency failure, stale index, invalid policy, and denied access are distinct abstention reasons.

## 7. Shape-aware retrieval

Embeddings and keywords retrieve candidates; they do not establish Shape equivalence.

Shape-aware admission proceeds through:

```text
candidate recall
-> address / role / relation / dynamic alignment
-> boundary and scale compatibility
-> mechanism and temporal checks
-> AntiMatch checks
-> evidence resolution
-> candidate, confirmed match, or abstention
```

Similarity is a vector, not an unexplained scalar. At minimum it may include lexical, semantic-address, role, relation, dynamic, temporal, valence, scale, perspective, and evidence dimensions. Aggregation weights must be named by the query purpose.

The aperture never promotes a candidate Shape or Pattern. Promotion remains a canonical framework operation.

## 8. Budget model

`token_budget` is a ledger, not a decorative field.

The budget contract defines:

- tokenizer or deterministic estimator version;
- reserved system and answer capacity;
- orientation maximum;
- evidence maximum;
- per-layer and per-block caps;
- block priority rules;
- pinned-block behavior;
- overflow and abstention behavior.

Evidence blocks are included whole. If a required block cannot fit, the service abstains or returns an explicit insufficient-budget result; it does not silently cut the evidence into misleading fragments.

For equal inputs, corpus revision, policy version, and configuration, selection and budgeting must be deterministic.

## 9. Envelope invariants

| Mode | Default access | Cross-ocean | Durable learning | Receipt retention |
|---|---|---|---|---|
| `open` | session, workspace, user, governed global | policy-gated | gated | normal policy |
| `bounded` | session, workspace; user only if granted | off | gated | normal policy |
| `strict` | session and explicit pins | off | session-local/manual | minimal |
| `incognito` | ephemeral turn/session input only | off | disabled | hashes/metrics only |

Incognito restrictions must be enforced at retrieval and write boundaries, not through prompt instructions.

## 10. Lightweight and efficiency rules

- Store source text once; use IDs and hashes elsewhere.
- Search compact indexes before resolving evidence text.
- Never scan the full ocean on a request path.
- Bound graph expansion by grant, depth, count, and time.
- Cache only derived candidate results keyed by corpus revision, policy hash, and normalized query.
- Never cache unauthorized evidence or incognito content.
- Use one disclosure decision contract with small surface adapters.
- Introduce no learned reranker until deterministic baselines and failure analysis justify it.
- Keep optional Shape reasoning lazy; simple factual retrieval should not pay its cost.

## 11. Reliability and error model

Every result uses one of these explicit statuses:

- `disclosed`;
- `empty_no_positive_match`;
- `empty_grant_excludes_all`;
- `abstained_dependency_not_ready`;
- `abstained_stale_index`;
- `abstained_invalid_policy`;
- `abstained_insufficient_budget`;
- `denied_visibility`;
- `failed_internal`.

Failures must not fall back to broader retrieval. Retries must be idempotent by request ID and corpus revision. Receipts must make the exact decision reconstructible.

## 12. Conformance and evaluation

### Contract tests

- deny precedence and envelope matrix;
- execution object cannot contain suppression fields;
- deterministic budgeting and selection;
- incognito has no retrieval or durable write side effects;
- adapters cannot bypass the effective grant.

### Retrieval suites

- unrelated query returns empty;
- empty query returns empty under bounded/strict;
- aliases and explicit pins retrieve expected evidence;
- missing pond/address metadata fails closed where required;
- stale indexes abstain rather than broaden;
- positive fixtures preserve acceptable recall.

### Shape suites

- multi-dimensional source yields distinct local Shape candidates;
- structural match beats superficial lexical similarity;
- AntiMatch prevents a known false analogy;
- candidate Shape is never reported as validated Pattern membership;
- source spans and branch/scope remain intact.

### System metrics

- neighborhood precision and recall;
- negative-query false-open rate;
- distractor inclusion and harm;
- budget obedience;
- leakage rate;
- provenance coverage;
- p50/p95 latency and resolved-byte count;
- empty and abstention reason distribution.

## 13. Migration and rollout

1. Establish a representative, versioned fixture corpus.
2. Measure current behavior before enforcement.
3. Introduce contracts and adapters behind feature flags.
4. Remove the suppression leak immediately.
5. Run fail-empty and grant normalization in shadow mode.
6. Backfill missing metadata and compare positive recall.
7. Enforce on Bridge with rollback configuration.
8. Add Holodeck and prove adapter parity.
9. Add other surfaces only after conformance and performance gates pass.

No big-bang rewrite is permitted. Each stage must be reversible and must leave the previous production path available until the new path passes its release gate.

## 14. Success condition

The design succeeds when Bridge and Holodeck use the same disclosure contract; unrelated requests open nothing; authorized Shape evidence can be found without loading its source document wholesale; budgets and privacy modes are mechanically enforced; execution cannot receive suppressed material; and every decision is reconstructible from a compact receipt.
