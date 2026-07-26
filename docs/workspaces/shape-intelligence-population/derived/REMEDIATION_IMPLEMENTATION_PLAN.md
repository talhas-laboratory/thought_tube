# Shape Intelligence Remediation Implementation Plan

Status: implementation authority for the remediation pass

Baseline reviewed: `origin/cursor/shape-intelligence-tools-61ce` at `cd8047dc3e`

Defective implementation commit to selectively import: `84229d4dab`
Specification baseline containing the corrected intelligence-first contracts: `9dd4a60613`

## 1. Outcome

Deliver an asynchronous, intelligence-led Shape population system in which:

1. every incoming source is losslessly normalized and given stable provenance;
2. an authenticated intelligence identity forms a bounded evidence inquiry;
3. deterministic infrastructure materializes exactly that inquiry without choosing semantic relevance;
4. proposer intelligence emits provisional Shape candidates;
5. deterministic governance accepts only packet-bound, structurally valid records in one durable transaction;
6. comparison retrieval runs only after candidate formation and supplies possible neighbors without deciding equivalence;
7. independent critic/synthesizer intelligence evaluates the proposal and preserves disagreement;
8. a designated evaluator may recommend promotion;
9. a human approval event is required before a privileged canonical adapter can promote;
10. the knowledge ocean stores source content once, keeps evidence packets reference-based, and exposes only approved canonical projections to retrieval.

The pass is complete only when the production path—not merely direct Python calls—demonstrates this lifecycle with authenticated identities, durable receipts, restart-safe jobs, bounded storage, semantic-quality tests, and rollback.

## 2. Chosen approach

### Recommended: modular in-place remediation

Keep `src/conversation_os/shape_population/` as the bounded domain package, replace its JSON store with SQLite, and integrate it through existing owners:

- ingestion: `src/conversation_os/vault_ingest.py`;
- model/OpenClaw transport: `src/conversation_os/chat_backends.py`;
- OpenClaw provisioning: follow `tools/provision_bridge_openclaw_agent.py`;
- runtime configuration: `product/inner_world_v1/config/runtime.json` and `.sample.json`;
- canonical read boundary: `src/conversation_os/shape_projection_reader.py`;
- profile authority: `src/conversation_os/metaphysical_kernel_profile_registry.py`;
- orchestration observability: `src/conversation_os/runtime_pipeline.py` and the Shape-specific worker.

This is the smallest architecture that preserves existing owners and avoids a second orchestration stack.

### Rejected: patch the JSON implementation

Do not add more locks, snapshots, or rollback copies around the ten JSON files. The root failure is multi-record transactional integrity; file-level patches cannot supply process-safe uniqueness, foreign keys, crash recovery, or atomic promotion.

### Deferred: separate LangGraph or microservice

Do not introduce LangGraph in this pass. The workflow is currently a bounded state machine and the repository already has OpenClaw model transport, runtime configuration, and service deployment. Revisit graph orchestration only after the tool contracts, semantic tests, retry model, and observability are stable.

## 3. Non-negotiable boundaries

- Normalization is deterministic and precedes intelligence.
- The evidence inquiry is selected by intelligence or an explicitly authorized caller.
- Evidence assembly is deterministic execution of that inquiry; it never asserts semantic relevance.
- Candidate/evaluation payloads contain model output only. Identity, model, prompt, run, authorization, timing, retry, and cost metadata come from trusted execution context.
- Similarity operates only after a candidate exists and cannot mutate, merge, reject, recommend, or promote.
- Validation checks structure and policy only; critic/evaluator intelligence judges semantic support.
- A designated evaluator recommends. A human approves. `apply_promotion` applies an already-recorded approval and cannot create one.
- Rejection is terminal for one promotion request. A later attempt requires a new evaluation and new request.
- No provisional candidate becomes a retrieval-ranking fact.
- Do not create a third canonical Shape store. Promotion must go through the canonical profile adapter or fail closed while that profile is unavailable.
- Ingestion remains available if Shape processing is degraded. Enqueue failure is visible in a receipt but must not roll back successful source ingestion.

## 4. Phase 0 — reconstruct a safe implementation branch

### Root cause addressed

The implementation branch was created from `55430a43ae`, before the corrected workspace and Cognitive Aperture work. It has two add/add projection conflicts and its cloud checkout appended JSONL events to an unsmudged Git LFS pointer.

### Exact procedure

1. Start from the agreed current integration branch, not from `cursor/shape-intelligence-tools-61ce`.
2. Fetch and fast-forward before creating the remediation branch.
3. Import only implementation-owned paths from `84229d4dab`; do not import either workspace projection commit.

```bash
git fetch origin
git switch <agreed-integration-branch>
git pull --ff-only origin <agreed-integration-branch>
git switch -c cursor/shape-intelligence-remediation

git restore --source=84229d4dab -- \
  src/conversation_os/shape_population \
  tests/test_shape_population_normalization.py \
  tests/test_shape_population_evidence.py \
  tests/test_shape_population_interpretation.py \
  tests/test_shape_population_critique.py \
  tests/test_shape_population_governance.py \
  tests/test_shape_population_promotion.py \
  tests/fixtures/shape_population \
  context/substrate/modules/kernel.shape_population.candidate_submission.json \
  context/substrate/modules/kernel.shape_population.contracts.json \
  context/substrate/modules/kernel.shape_population.critique.json \
  context/substrate/modules/kernel.shape_population.evidence.json \
  context/substrate/modules/kernel.shape_population.governance.json \
  context/substrate/modules/kernel.shape_population.identities.json \
  context/substrate/modules/kernel.shape_population.json \
  context/substrate/modules/kernel.shape_population.normalization.json \
  context/substrate/modules/kernel.shape_population.promotion.json \
  context/substrate/modules/kernel.shape_population.storage.json
```

4. Do not import `cd8047dc3e`.
5. Confirm the staged diff contains no deletion outside the selected paths.
6. Run the engineering guard before editing code:

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py repo-overview lookup --query "Shape population normalization evidence governance OpenClaw projection"
python3 tools/conversation_os.py engineering-guard assess \
  --request "Remediate Shape Intelligence population implementation" \
  --purpose "Turn ingested sources into governed provisional Shape candidates and human-approved canonical projections without blocking ingestion or trusting model-supplied authority" \
  --proposed-paths "src/conversation_os/shape_population,src/conversation_os/vault_ingest.py,src/conversation_os/chat_backends.py,src/conversation_os/shape_projection_reader.py,product/inner_world_v1/config/runtime.json,tests"
```

### Exit gate

- `git diff --name-status <integration-head>...HEAD` contains no unintended deletion.
- Workspace documents come from the current integration branch.
- `docs/workboards/*/UPDATES.jsonl` contain real JSONL after LFS smudge; no file begins with an LFS pointer followed by events.
- The six existing focused suites run, even if remediation regression tests initially fail.

## 5. Phase 1 — freeze strict contracts and trusted execution context

### Files

- modify `src/conversation_os/shape_population/contracts.py`;
- add `src/conversation_os/shape_population/execution_context.py`;
- modify `candidate_submission.py`, `critique.py`, `governance.py`, and `promotion.py`;
- add `tests/test_shape_population_contracts.py`;
- add `tests/test_shape_population_authorization.py`.

### Execution context

Add an immutable `ExecutionContext` supplied by the service/tool adapter, never by model JSON:

```text
principal_id
principal_kind = service | agent | human
authenticated_by
capabilities[]
correlation_id
run_id
model_id                  # empty only for deterministic/human operations
prompt_version            # empty only for deterministic/human operations
tool_contract_version
issued_at
deadline_at
```

Required capabilities:

```text
shape.evidence.inquire
shape.candidate.submit
shape.comparison.read
shape.evaluation.submit
shape.promotion.request
shape.promotion.approve
shape.promotion.apply
shape.promotion.rollback
```

Tool signatures become:

```python
submit_candidate(payload, *, context: ExecutionContext, store: ShapePopulationStore)
find_comparison_candidates(candidate_id, *, context, store, limit, policy_version)
submit_evaluation(payload, *, context, store)
request_promotion(payload, *, context, store)
record_human_decision(payload, *, context, store)
apply_promotion(request_id, *, context, store, canonical_port)
```

Do not accept `agent_identity`, `model_version`, `prompt_version`, `tool_contract_version`, `run_id`, `approval_identity`, timing, retry count, or cost from model payloads. The adapter copies these from `ExecutionContext` into records and receipts.

### Strict payload behavior

- Reject unknown fields. Do not silently ignore `candidate_id`, `status`, `canonical`, or invented metadata.
- Require a non-empty `packet_id` for candidate output.
- Require candidate `title`, `statement`, `boundary`, `mechanism`, `dimensions`, `evidence_refs`, `counter_hypotheses`, `uncertainty`, and `recommended_disposition`.
- Require evaluation `candidate_id`, `critique`, `disposition`, `evidence_refs`, `relationship_findings`, `uncertainty`, and explicit revision operations.
- Replace string revisions such as `"boundary: ..."` with typed operations:

```json
{"op":"replace_boundary","value":"...","reason":"...","evidence_refs":[...]}
```

- Deterministic validation may verify the operation shape and cited evidence, but may not decide whether the revised boundary is semantically superior.

### Evidence reference contract

Every evidence reference is exact and mandatory:

```text
packet_id
block_id
source_id
segment_id
char_start
char_end
text_sha256
```

Candidate admission must query the named packet block and require exact equality for all seven fields. A valid segment elsewhere in the corpus is insufficient.

### Regression tests first

Before implementation, add failing tests named:

- `test_candidate_rejects_segment_not_present_in_packet`;
- `test_candidate_rejects_missing_source_digest_or_offsets`;
- `test_model_payload_cannot_select_identity_or_runtime_metadata`;
- `test_unknown_candidate_fields_fail_closed`;
- `test_empty_run_id_rejected_for_model_operation`;
- `test_untrusted_context_cannot_call_privileged_operation`.

### Exit gate

- The two adversarial bypasses from the review fail before the fix and pass afterward.
- No public tool authorizes from a payload string.
- Exact schema snapshots are versioned and included in receipts.

## 6. Phase 2 — replace JSON snapshots with one SQLite authority

### Files

- rewrite `src/conversation_os/shape_population/storage.py` as `ShapePopulationStore`;
- add `src/conversation_os/shape_population/migrations.py`;
- add `tools/migrate_shape_population_store.py`;
- add `tests/test_shape_population_store.py`;
- expand `tests/test_shape_population_governance.py` and promotion tests.

Use the connection and `BEGIN IMMEDIATE` pattern in `src/conversation_os/workspace_store.py`, with:

```text
PRAGMA foreign_keys = ON
PRAGMA journal_mode = WAL
PRAGMA synchronous = FULL
PRAGMA busy_timeout = 5000
```

Store location:

```text
product/inner_world_v1/data/shape_population/shape_population.db
```

### Minimum schema

Create versioned migrations and these tables:

- `shape_sources`: source ID, content digest, content pointer, modality, normalization version, metadata JSON;
- `shape_segments`: segment ID, source FK, ordinal, char/byte offsets, structure path, text digest; no duplicated text;
- `evidence_inquiries`: inquiry ID, trusted requester, question/scope JSON, policy version;
- `evidence_packets`: packet ID, inquiry FK, corpus revision, packet fingerprint, budget ledger, status;
- `evidence_packet_blocks`: packet/block key, segment FK, exact retained offsets/digest, ordering; no copied source text;
- `population_jobs`: job ID, source FK, state, attempt count, lease owner/expiry, next attempt, last error, timestamps;
- `candidates`: service ID, packet FK, status, semantic payload JSON, execution metadata, fingerprint;
- `evaluations`: service ID, candidate FK, disposition, payload JSON, execution metadata, fingerprint;
- `candidate_events`: append-only lifecycle events with previous/new status and actor context;
- `population_receipts`: append-only operation receipt without raw source text;
- `idempotency_keys`: unique `(operation, principal_id, idempotency_key)` with request fingerprint and result IDs;
- `promotion_requests`: request ID, candidate/evaluation FKs, status and fingerprint;
- `human_decision_events`: immutable decision event, unique request ID;
- `canonical_projection_receipts`: promotion/rollback receipt referencing the canonical owner result.

Use foreign keys, `CHECK` constraints for enumerations, and unique indexes for IDs, packet block membership, idempotency, one active job per source/revision, and one human decision per request.

### Transaction rules

- Candidate submission transaction: validate packet-bound references → insert candidate → append candidate event → insert receipt → insert idempotency result → commit.
- Evaluation transaction: validate candidate/version → insert evaluation → apply typed transition/revision → append event → insert receipt/idempotency → commit.
- Human decision transaction: validate authenticated human capability → insert exactly one decision event → transition request → receipt → commit.
- Promotion transaction: verify prior approved event and current request/candidate versions → call canonical port using an idempotency token → persist returned canonical receipt and local state. If the external canonical port cannot participate atomically, use an outbox row with retry-safe reconciliation; never mark local canonical before the port confirms.
- Rollback uses the same outbox/reconciliation rule.

### Migration

The migration command must:

1. acquire an exclusive migration lock;
2. back up legacy JSON files to a timestamped directory;
3. read and validate all legacy records without writing;
4. report duplicates, missing references, contradictory approvals, and packetless evidence;
5. abort on any unresolved contradiction;
6. import in one SQLite transaction;
7. run `PRAGMA integrity_check` and row-count reconciliation;
8. write a migration receipt;
9. leave legacy JSON read-only until one successful release cycle;
10. support `--dry-run` and idempotent rerun.

Do not import malformed approval histories as valid authorization.

### Required tests

- real two-thread and two-process duplicate submissions;
- injected failure after each individual insert in candidate/evaluation/promotion transactions;
- process termination followed by integrity/recovery check;
- idempotency replay and conflicting-payload rejection;
- concurrent promotion request and decision races;
- database lock timeout and bounded retry;
- migration dry-run, reconciliation, rerun, corrupt input, and rollback.

### Exit gate

- No production path reads or writes the legacy JSON store.
- `PRAGMA integrity_check` returns `ok`.
- Multiprocess tests prove one candidate, one decision, and one receipt for duplicate calls.
- Crash recovery never exposes a canonical local state without a canonical-owner receipt.

## 7. Phase 3 — lossless, scalable normalization and reference-only evidence

### Files

- add generic `src/conversation_os/source_content_store.py`;
- modify `src/conversation_os/vault_ingest.py`;
- rewrite `shape_population/normalization.py` and `evidence.py`;
- add `tests/test_source_content_store.py`;
- expand normalization/evidence fixtures and performance tests.

### Content ownership

Persist raw uploaded content exactly once in a content-addressed store. File-backed sources may retain their immutable file locator when policy allows; transient text/bytes uploads receive a `sha256:` blob pointer. The Shape store contains pointers, offsets, and digests only.

`vault_ingest.ingest_text_content` must:

1. persist or resolve the immutable content pointer;
2. run deterministic normalization;
3. write the existing source/chunk projections;
4. commit normal ingest;
5. enqueue a Shape population job using source ID and normalization revision;
6. return ingest success even if enqueue fails, while returning an explicit Shape enqueue receipt/error.

Do not put Shape-specific semantic branching in `vault_ingest`; call a generic post-ingest hook/adapter.

### Normalizer algorithm

- Stream bytes through an incremental decoder and hasher.
- Preserve exact line endings and Unicode; never normalize whitespace.
- Maintain `char_cursor` and `byte_cursor` incrementally. Never compute byte offsets by repeatedly encoding `text[:offset]`.
- Maintain heading hierarchy, transcript speaker, table, and code-fence state.
- Generate segment IDs from source digest, normalization version, structure path, ordinal, and exact text digest.
- Store segment metadata and offsets, not a second copy of text.
- Remove the default 500,000-character rejection. Enforce an explicit configurable `max_source_bytes`; when exceeded, reject before model work with a durable receipt. The default production profile must support the agreed large-document fixture.
- Normalization memory use must be bounded by one segment plus hashing/decoder state, excluding the content store write buffer.

### Evidence assembler

- Validate positive token/segment/byte budgets and enforce hard maxima.
- Authorize inquiry creation from `ExecutionContext`.
- Apply declared segment IDs and `anchor_ranges`; reject malformed/out-of-segment ranges.
- Compute packet fingerprint from inquiry, policy, corpus revision, and the ordered exact block reference/digest list—not merely requested IDs.
- Persist packet blocks as references only.
- Materialize block text transiently from the content store when invoking intelligence.
- Represent source material with a typed delimiter in the actual model request, not merely `instruction_authority: false` metadata.
- Return explicit omitted reasons and never silently expand beyond the declared inquiry.

### Storage budget gates

For a 100 MB source and 100 repeated inquiries:

- content store growth is approximately one source copy, not 100 packet copies;
- packet metadata growth is proportional to block references;
- no candidate or receipt contains raw evidence text;
- normalization completes within a benchmark budget recorded in `testing_context.json` before implementation begins.

### Required tests

- CRLF/LF, Unicode combining characters, invalid encoding, tables, nested headings, code fences, and transcripts;
- 10 MB, 100 MB, one extremely long line, and many-short-lines fixtures generated at test time outside tracked fixtures;
- linear-time offset benchmark or bounded scaling ratio;
- anchor-range correctness;
- packet fingerprint changes when block content/revision changes;
- unauthorized inquiry rejection;
- negative/zero/excessive budgets;
- 100 repeated packets do not duplicate source text on disk;
- source deletion/alteration causes fail-closed evidence resolution.

## 8. Phase 4 — real OpenClaw intelligence identities

### Files

- add `src/conversation_os/shape_population/model_gateway.py`;
- add `src/conversation_os/shape_population/orchestrator.py`;
- add `tools/provision_shape_population_openclaw_agents.py`;
- add four configs under `product/inner_world_v1/config/agent_configs/`;
- add Shape model roles to `runtime.json` and `runtime.sample.json`;
- add `tests/test_shape_population_model_gateway.py` and identity integration tests.

### Identities

Provision separate OpenClaw agents:

```text
shape_population_proposer
shape_population_critic
shape_population_synthesizer
shape_population_evaluator
```

Each config must declare role, version, model policy, thinking level, timeout, allowed tool names, output schema version, prompt version, and explicit forbidden actions. The agents receive no broad shell, filesystem, network, registry-write, deployment, or canonical-write permission.

### Model gateway

Wrap the existing OpenClaw transport in a Shape-specific adapter. Do not copy the loose JSON extraction currently used by dimension routing.

The adapter must:

- choose the configured role binding;
- build the system prompt from a versioned identity config;
- place evidence only inside typed source-data blocks;
- invoke a provided `ModelClient` port;
- accept exactly one JSON object matching the versioned schema;
- reject Markdown fences, leading/trailing prose, multiple objects, unknown fields, and tool calls outside the role surface;
- retry only transport/timeouts and explicitly repairable syntax, with a hard attempt/cost/deadline budget;
- create execution receipts for every attempt without storing raw evidence;
- never convert a model failure into a fabricated candidate.

### Intelligence responsibilities

- Inquiry planner: inspect source outline/segment manifest and request bounded evidence. It may refine inquiries within budget.
- Proposer: emit zero or more provisional candidates; use `needs_evidence` when support is insufficient.
- Critic: challenge grounding, boundary, alternatives, negative evidence, contamination, and comparisons.
- Synthesizer: preserve unresolved disagreement; it may revise only through typed, evidenced revision operations.
- Evaluator: recommend or decline promotion; it cannot approve or apply.

### Required routing tests

Use a real stubbed `ModelClient`, not a string labeled `stub`:

- assert exact prompt and tool exposure per identity;
- assert source injection text cannot change tools/system policy;
- fenced JSON/prose/invalid JSON triggers bounded repair then failure;
- timeout and retry receipts are exact;
- model-supplied authority fields are rejected;
- unavailable OpenClaw degrades the job to retryable/blocked without blocking ingest;
- evaluator cannot access approval/apply operations.

## 9. Phase 5 — post-candidate comparison and independent critique

### Files

- rewrite `shape_population/critique.py`;
- add `shape_population/comparison.py`;
- integrate through `shape_projection_reader.py` or a dedicated candidate-read port;
- add complete critique fixtures and semantic tests.

### Comparison rules

- Reject comparison when the candidate has not been durably accepted.
- Query only permitted branch/scope/corpus projections.
- Retrieve a bounded candidate pool using the existing knowledge-ocean read boundary. Until embeddings exist, use deterministic lexical/metadata retrieval but score every eligible row before taking top `N`; never return first-insertion order.
- Hard-cap `limit`, total evidence refs, serialized bytes, and query time.
- Include provenance and retrieval-policy version for every neighbor.
- Return `similarity_features` or a non-authoritative `relation_hint`; never return `equivalent`, merge IDs, canonical status changes, or automatic dedupe.
- Include legacy signatures only as explicitly labeled provisional comparison evidence.

### Critique continuity

The critic/synthesizer must preserve candidate statement, boundary, evidence, alternatives, and uncertainty unless a typed revision names:

- the changed field;
- the reason;
- supporting/counter evidence;
- the previous value/fingerprint;
- residual disagreement.

### Required semantic dataset

Create immutable fixtures for:

- clearly same-like but differently worded Shapes;
- lexically similar but semantically distinct Shapes;
- lexically distant but structurally analogous Shapes;
- adjacent Shapes;
- genuinely conflicting Shapes;
- false-merge and false-split regressions;
- unsupported abstraction;
- negative/counter evidence;
- prompt contamination;
- missing comparison service.

Exact tests cover routing, limits, provenance, and field ownership. Bounded/evaluator tests cover challenge quality, grounding, boundary clarity, alternative handling, uncertainty calibration, and disagreement preservation.

## 10. Phase 6 — terminal human decisions and canonical-owner integration

### Files

- rewrite `shape_population/promotion.py`;
- add `shape_population/canonical_port.py`;
- modify `shape_projection_reader.py` only through its canonical-profile boundary;
- add promotion receipts and profile conformance tests.

### State machine

```text
recommended
  -> promotion_requested
      -> approved        # immutable human event
          -> applied
              -> rolled_back (new authority event and receipt)
      -> rejected        # terminal for this request
```

Rules:

- one human decision per request, enforced by a unique database constraint;
- a rejection cannot later become approved;
- approval and apply are separate operations;
- `apply_promotion` requires an existing approved event and cannot accept `approval_reason` as a shortcut;
- the approver must be authenticated as a human principal with `shape.promotion.approve`;
- the applier must hold `shape.promotion.apply` and cannot be the requesting evaluator;
- promotion request evidence must exactly resolve and must match the candidate/evaluation lineage;
- every request, decision, apply, failure, replay, and rollback has an immutable receipt;
- stale candidate/evaluation versions reject apply;
- retries use the same canonical idempotency token.

### Canonical Shape port

Define a narrow port:

```python
class CanonicalShapePort(Protocol):
    def profile_status(self) -> CanonicalProfileStatus: ...
    def apply(self, projection, *, idempotency_key, context) -> CanonicalApplyReceipt: ...
    def rollback(self, canonical_id, *, reason, context) -> CanonicalRollbackReceipt: ...
```

The production adapter must use `profile:shape_and_semantic_addressing` through the metaphysical kernel profile registry. If the profile is unavailable, return `canonical_profile_unavailable` and leave the request approved-but-unapplied. Do not write `canonical_projection.json` as an alternative authority.

Registering the missing UMF profile is an explicit external dependency. Do not invent its record types in this workspace. The semantic contract must be approved in `unified-framework-synthesis` before production canonical apply is enabled.

`shape_projection_reader.py` must read the canonical owner receipt/projection and continue labeling legacy signatures as provisional. Add parity tests proving promoted Shapes are visible only after confirmed apply and disappear or become rollback-marked after confirmed rollback.

## 11. Phase 7 — asynchronous orchestration and recovery

### Files

- complete `shape_population/orchestrator.py`;
- add `shape_population/worker.py`;
- add CLI commands in `src/conversation_os/cli.py`;
- add `ops/systemd/inner-space-shape-population.service.sample` and timer/path trigger if required;
- expose status in the existing backend only after the service contract is tested.

### Job lifecycle

```text
queued
-> normalizing
-> inquiry_planning
-> proposing
-> critiquing
-> synthesizing
-> evaluated
-> recommended | needs_evidence | rejected
```

Operational states `retryable`, `blocked`, `dead_letter`, and `cancelled` are separate from semantic candidate status.

### Worker rules

- Ingestion enqueues and returns; it never waits for a model.
- Claim jobs using a database lease with owner, expiry, heartbeat, and compare-and-set update.
- Each stage is idempotent and records input/output fingerprints.
- Retry only classified transient failures with exponential backoff and jitter; cap attempts, elapsed time, and cost.
- Validation, policy, authorization, and semantic-insufficiency failures are not blind retries.
- Resume from the last committed stage after restart.
- Dead-letter jobs retain receipts and source pointers; they do not contaminate retrieval.
- Operators can inspect, retry, or cancel jobs through explicit commands.

Suggested CLI:

```text
python3 tools/conversation_os.py shape-population enqueue --source-id ...
python3 tools/conversation_os.py shape-population worker --limit 5
python3 tools/conversation_os.py shape-population status [--job-id ...]
python3 tools/conversation_os.py shape-population retry --job-id ...
python3 tools/conversation_os.py shape-population cancel --job-id ...
python3 tools/conversation_os.py shape-population audit --candidate-id ...
```

Do not overload `inner-world batch`; it owns feed generation. The Shape worker may be exposed as a separate runtime component/status surface.

### End-to-end recovery tests

Interrupt after each stage, restart the worker, and assert:

- no duplicate model call after a committed stage;
- no duplicate candidate/evaluation;
- stable provenance and job lineage;
- ingest remains successful;
- unavailable OpenClaw produces retryable state;
- unavailable canonical profile leaves approved-but-unapplied state;
- retrieval never sees provisional or partially promoted rows.

## 12. Phase 8 — semantic-quality and continuity test system

### Test contexts

Create:

```text
tests/fixtures/shape_population/semantic/testing_context.json
tests/fixtures/shape_population/semantic/rubric_profile.json
tests/fixtures/shape_population/semantic/proposer_cases.json
tests/fixtures/shape_population/semantic/critic_cases.json
tests/fixtures/shape_population/semantic/evaluator_cases.json
tests/fixtures/shape_population/continuity/continuity_context.json
tests/fixtures/shape_population/continuity/cases.json
```

`testing_context.json` must explicitly define:

- success: grounded, coherent, bounded, useful provisional interpretation;
- acceptable variation: wording and decomposition may differ when evidence lineage and semantic constraints remain intact;
- prohibited outcomes: invented evidence, instruction following from source data, forced consensus, deterministic semantic scoring, identity spoofing, or automatic canon;
- preservation: evidence lineage, source meaning, uncertainty, counter-hypotheses, and disagreement survive downstream handoffs unless explicitly revised;
- priority: evidence fidelity and uncertainty honesty outrank novelty, elegance, and deduplication.

### Node-level layers

For proposer, critic, synthesizer, and evaluator include:

- positive golden case;
- boundary case;
- ambiguity case;
- adversarial case;
- missing-information case;
- named regression case;
- preservation case where the node revises prior state;
- semantic-adherence case inspecting actual visible output, not metadata.

Use exact oracles for schemas, routes, tools, identities, state ownership, and transitions. Use bounded semantic checks for required meanings, prohibited drift, and preservation. Use an evaluator oracle only for genuinely qualitative dimensions, and require structured dimension scores, cited evidence, hard failures, confidence, and residual uncertainty.

### Continuity packs

At minimum:

1. normalized source → inquiry: inquiry remains traceable to source structure;
2. inquiry → evidence packet: all requested evidence is faithfully materialized and nothing undeclared appears;
3. evidence → proposal: statement/boundary/mechanism remain grounded;
4. proposal → critique: evidence, boundary, alternatives, and uncertainty survive;
5. critique → synthesis: disagreement is preserved or explicitly resolved;
6. evaluation → promotion request: recommendation retains evidence and uncertainty;
7. approval → canonical projection: canonical record matches the approved candidate version;
8. rollback → retrieval: revoked projection is no longer active.

Each continuity case names required meanings, allowed specialization, prohibited workflow/governance drift, and the downstream artifact inspected.

### Quality gates

- No test passes merely because a dictionary contains `non_deterministic_quality: true`.
- No test writes tracked fixture files during execution.
- Every review regression has a named test, including out-of-packet evidence and rejected-request promotion.
- Run deterministic suites on every change; run bounded model-stub semantic suites in CI; run live-model calibration separately and never make ordinary CI depend on external model availability.

## 13. Phase 9 — verification, rollout, and rollback

### Required commands

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py repo-overview validate
pytest tests/test_shape_population_contracts.py -q
pytest tests/test_shape_population_authorization.py -q
pytest tests/test_shape_population_store.py -q
pytest tests/test_shape_population_normalization.py -q
pytest tests/test_shape_population_evidence.py -q
pytest tests/test_shape_population_interpretation.py -q
pytest tests/test_shape_population_critique.py -q
pytest tests/test_shape_population_governance.py -q
pytest tests/test_shape_population_promotion.py -q
pytest tests/test_shape_population_model_gateway.py -q
pytest tests/test_shape_population_orchestrator.py -q
pytest tests/test_shape_population_semantic.py -q
pytest tests/test_shape_population_continuity.py -q
pytest tests/test_shape_projection_reader.py -q
pytest
```

Expected private-repo result: no new failure. If running in the stripped public environment, document only the pre-declared private-substrate failures; no Shape-related or newly introduced failure is acceptable.

### Performance gates

Record machine, fixture digest, and command. Require:

- normalization scaling approximately linear from 10 MB to 100 MB;
- bounded peak memory;
- evidence packet metadata size independent of repeated source-text length;
- indexed comparison query obeys configured latency and result caps;
- duplicate submission/promotion races produce one durable result;
- worker restart resumes without duplicate intelligence outputs.

### Staged rollout

1. `disabled`: schema/migrations deployed, no enqueue.
2. `shadow`: enqueue and run, but candidates cannot request promotion and retrieval cannot see them.
3. `review_only`: human review queue enabled; canonical adapter remains fail-closed.
4. `promotion_canary`: canonical profile available; allow explicitly selected human approvals for a small corpus.
5. `production`: enable normal reviewed promotion only after canary audit.

Feature flags belong in `runtime.json` and default to disabled in `runtime.sample.json` until their gate passes.

### Rollback

- Disable enqueue and stop the Shape worker.
- Preserve SQLite and receipts; never delete audit history.
- Revert runtime flags and agent bindings through a release manifest.
- Reconcile any canonical outbox entries before code rollback.
- Roll back canonical projections through the canonical port, not by deleting local rows.
- Keep existing ingestion, legacy signatures, and Cognitive Aperture reads operational throughout.

## 14. Implementation ordering and ownership

| Order | Workspace | Deliverable | Blocks |
|---|---|---|---|
| 0 | parent | clean branch and projection recovery | everything |
| 1 | governance + interpretation | strict contracts and trusted context | all tool calls |
| 2 | governance | SQLite authority and migration | durable workflow |
| 3 | normalization | content-addressed input and scalable normalizer | evidence |
| 4 | evidence | packet-bound, reference-only evidence | proposer |
| 5 | interpretation | OpenClaw proposer and strict gateway | critique |
| 6 | critique | ranked comparison, critic, synthesizer | evaluation |
| 7 | evaluation-promotion | immutable decision and canonical port | canonical visibility |
| 8 | parent | job worker and end-to-end orchestration | rollout |
| 9 | all | semantic/continuity/performance gates | release |

One agent may execute sequentially. If multiple agents are used, they must not edit the same contract/storage files concurrently. Governance owns shared contracts and merges first; other workspaces build against that committed version.

## 15. Definition of done

The remediation is done only when all statements are true:

- the implementation is based on the current integration branch;
- every live child task contains exact verification evidence and residual risk;
- model payloads cannot claim authority or runtime metadata;
- every evidence reference is exactly packet-bound;
- persistence is SQLite-backed, crash-safe, and multiprocess tested;
- source text is stored once and evidence packets persist references rather than copies;
- large sources are streamed within a declared policy budget;
- real OpenClaw identities and a strict model gateway are provisioned and tested;
- comparison is post-candidate, bounded, ranked, provenance-complete, and non-authoritative;
- rejected promotion requests can never become approved;
- `apply_promotion` requires a prior human event;
- canonical apply uses the registered canonical profile or fails closed;
- the asynchronous worker survives restart and never blocks ingestion;
- node-level semantic and whole-workflow continuity tests inspect real outputs;
- the full relevant suite passes with no new regressions;
- projections are published from live workspace state, committed, pushed, and verified fresh.

## 16. Mandatory handoff protocol

At the beginning of every task:

```bash
git pull --ff-only
source ~/.config/inner-space-workspace.env 2>/dev/null || true
python3 tools/workspace_coordination.py context \
  --workspace-id <workspace-id> --agent-id <agent> --surface implementation --session-id <session>
python3 tools/workspace_projection_sync.py check --workspace-id <workspace-id>
```

After every live task mutation:

```bash
python3 tools/workspace_projection_sync.py publish --workspace-id <workspace-id>
python3 tools/workspace_projection_sync.py check --workspace-id <workspace-id>
```

Before handoff, record exact changed paths, commands, results, residual risks, and commit SHA in the live API. Then publish projections, inspect staged file count, commit intentionally, and push. Never append to an LFS pointer file; ensure LFS objects are smudged before projection publication.
