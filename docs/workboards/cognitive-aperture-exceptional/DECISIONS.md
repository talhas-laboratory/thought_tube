# Decisions

## D-001 — Four-layer disclosure law

**Status:** accepted
**Authority:** ADR-001

Execution follows orient → grant → evidence → receipt. Receipts are audit/handoff artifacts, not the primary steering mind.

## D-002 — Modular ownership boundary

**Status:** accepted
**Authority:** ADR-002

This workspace owns disclosure only. Ingestion, canonical records, Shape promotion, embeddings, and surface presentation remain external dependencies behind explicit ports.

## D-003 — One source, derived references

**Status:** accepted

Raw source text is stored once. Fragments, indexes, Shape projections, evidence blocks, and receipts preserve IDs, spans, provenance, and hashes rather than duplicating the source.

## D-004 — Canonical and provisional Shapes

**Status:** accepted

Canonical Shape identity/promotion belongs to the Unified Metaphysical Framework Shape profile. Legacy `meta_layer` signatures may enter retrieval only as explicitly provisional candidates through an adapter. The aperture never promotes them.

## D-005 — Execution and audit separation

**Status:** accepted

ExecutionBundle cannot represent suppressed/omitted material. AuditReceipt owns omission details. This is enforced by contract, not prompt wording.

## D-006 — Admission before ranking

**Status:** accepted

Positive relevance evidence admits candidates. Ranking operates only on admitted candidates. Confidence alone is never positive evidence.

## D-007 — Deterministic whole-block budgets

**Status:** accepted

Evidence is budgeted as provenance-preserving blocks. Required evidence that cannot fit produces an explicit status instead of silent semantic truncation.

## D-008 — Incremental adoption

**Status:** accepted

Bridge adopts first, Holodeck second. Feed and task packs follow only after conformance and performance gates. No big-bang surface migration.

## Open decisions

- Kernel bounded-view integration versus explicit demotion — CAE-011.
- Harness probe fixtures for budget, leakage, provenance, and Shape/AntiMatch categories — CAE-006B (thresholds for recall/latency recorded in D-011).

## D-009 — Shape projection reader schema and legacy retention (CAE-014)

**Status:** accepted
**Authority:** ADR-002, GAP_MAP G-2

`ShapeProjectionReader` contract version `1.0` lives in `src/conversation_os/shape_projection_reader.py`. Canonical reads use `profile:shape_and_semantic_addressing` when registered; until then the reader abstains on canonical promotion and exposes legacy `meta_layer` signatures only as explicit `candidate` projections with branch, scope, boundary, abstraction contract, scale, and provenance. AntiMatch records are read as `anti_match` projections. The aperture cannot promote Shape or Pattern status through this port. Legacy JSONL remains the provisional candidate source until the canonical profile registers and adapter conformance passes (`CAE-014-legacy-retained-until-canonical-profile`).

## D-010 — Versioned disclosure contracts (CAE-015)

**Status:** accepted
**Authority:** ADR-001, ADR-002, design §5–11

Disclosure contracts version `1.0` live in `src/conversation_os/disclosure_contracts.py`. Public types are `ApertureRequest`, `ActiveStateSnapshot`, `RequestedGrant`, `EffectiveGrant`, `CandidateRef`, `EvidenceBlock`, `ExecutionBundle`, and `AuditReceipt`, with explicit result statuses and envelope defaults. `normalize_effective_grant()` applies envelope defaults and deny precedence once; downstream modules consume only `EffectiveGrant`. `ExecutionBundle` validation rejects suppression fields at the type boundary; `AuditReceipt` owns omissions and enforces incognito retention (`hashes_metrics_only`, no sensitive text). Fixtures under `tests/fixtures/disclosure_contracts/v1/` cover every contract and result status.

## D-011 — Pre-enforcement baseline harness (CAE-006A)

**Status:** accepted
**Authority:** GAP_MAP §7, CHAT_CONVERTER_SEED_CORPUS_V1

`aperture_baseline_harness` version `1.0` lives in `src/conversation_os/aperture_baseline_harness.py`. Versioned probe fixtures under `tests/fixtures/aperture_baselines/v1/` and published results under `derived/baselines/chat_converter_seed_v1.{json,md}` record corpus revision `db340a77323741710f5f2a9512123271505c13880a3f72ac4c3e11c19fc4ccad`, approved Stage A thresholds, and the near-neighbour known failure (`biological cognition agent memory` → `understanding-the-nature-of-thought`). The harness maps probes to explicit disclosure result statuses and distinguishes pass, no_hits, known_failure, abstained, denied, and error verdicts before enforcement work begins.

## D-012 — Execution/audit isolation (CAE-002)

**Status:** accepted
**Authority:** ADR-001, D-005, disclosure contracts

Bridge frame assembly splits `frame_bundle` (execution-safe, no suppressed fields) from `frame_audit` (omitted blocks and reasons). `compose_execution_message()` omits suppressed content when `execution_audit_isolation_v1` is enabled (default). Rollback via `runtime.json` → `bridge.execution_audit_isolation_v1: false`.

## D-013 — Effective grant normalization (CAE-003A)

**Status:** accepted
**Authority:** disclosure contracts, design §9

`build_effective_grant_from_context()` normalizes policy and session envelope once into `EffectiveGrant` via `disclosure_contracts.normalize_effective_grant()`. Downstream bundle layers consume `effective_layers_to_bridge_layers()` output. Envelope matrix differences (open/bounded/strict/incognito) and deny precedence are enforced at this boundary. Rollback via `bridge.effective_grant_normalization_v1: false`.

## D-014 — Fail-empty admission (CAE-001)

**Status:** accepted
**Authority:** GAP_MAP G1, ADR-001

`candidate_admission` version `1.0` separates positive admission signals from ranking features in `build_retrieval_bundle()`. Confidence alone is not an admission signal; unrelated bounded/strict queries return `empty_no_positive_match` when enforcement is enabled. Shadow decisions are recorded in `shadow_admission`; rollback via `knowledge.fail_empty_admission_enforce_v1: false` (legacy fallback preserved when enforce is off).

## D-015 — Deterministic budget allocator (CAE-003B)

**Status:** accepted
**Authority:** D-007, design §8, disclosure contracts

`disclosure_budget_allocator` version `1.0` uses estimator `1.0` (whitespace token count) and reservation version `1.0` (`system_tokens=120`, `answer_tokens=256`, `orientation_max_tokens=120`). `apply_frame_budget_to_assembly()` selects whole frame blocks in layer priority order before execution composition; optional blocks drop with a ledger recorded in `frame_audit.drop_ledger` only. Required blocks that cannot fit return `abstained_insufficient_budget`. Rollback via `bridge.deterministic_budget_enforcement_v1: false`.
