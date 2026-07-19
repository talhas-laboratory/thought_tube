# Completion Gates

Every task passes the universal gates. Stage gates apply in addition.

## Universal task gates

### Intake

- purpose states the user/system effect;
- owner module and smallest edit surface identified;
- dependencies and scope exclusions recorded.

### Readiness

- live task claimed;
- engineering guard ready for runtime changes;
- acceptance criteria are executable;
- fixture/data prerequisites are available;
- rollback or compensating operation specified.

### Verification

- exact commands and results recorded;
- changed artifacts listed;
- negative and positive behavior both checked;
- provenance/privacy implications checked;
- performance impact measured when on a hot path;
- residual risks stated.

### Review and done

- independent review or explicit maintainer approval recorded;
- no unresolved critical/high blocker;
- live coordination updated with evidence;
- projections published and fresh;
- merge or release reference recorded when applicable.

## Stage A — architecture and dependency readiness

- ADR-001 and ADR-002 accepted.
- Corpus readiness contract reports revision and stale/not-ready state.
- Representative fixture corpus includes positive, negative, distractor, privacy, multi-dimensional Shape, and AntiMatch cases.
- Canonical Shape reader versus provisional legacy adapter decision is tested.
- EffectiveGrant, ExecutionBundle, AuditReceipt, and result statuses are versioned.
- Current behavior baseline is published before enforcement work starts.

## Stage B — Bridge safety

- leak sentinel absent from every model-bound payload.
- open/bounded/strict/incognito access and persistence matrix passes.
- unrelated and empty queries fail empty.
- positive recall remains above the approved fixture threshold.
- all bundles obey deterministic budget rules.
- stale/unready dependencies abstain instead of widening.
- rollback flags tested.

## Stage C — shared service

- Bridge and Holodeck use the same service contract.
- adapter conformance returns equivalent decisions for equivalent inputs.
- receipt reconstructs each result without duplicating sensitive text.
- incognito performs no ocean retrieval or durable learning.
- p50/p95 latency and resolved-byte budgets pass.
- no full-ocean scan or unbounded graph walk occurs.

## Stage D — adapter release

- surface owner approves the adapter projection.
- shared grant/admission/budget rules remain unchanged.
- surface-specific persistence and presentation tests pass.
- adapter feature flag and rollback verified.
- no parallel selector remains active without an explicit retirement decision.
