# Candidate Governance Remediation Packet

Authority: [central remediation plan](../../shape-intelligence-population/derived/REMEDIATION_IMPLEMENTATION_PLAN.md), especially Phases 1, 2, 6, 7, and 9.

## Required outcome

Replace the unsafe JSON snapshot with a single transactional SQLite authority for jobs, evidence, candidates, evaluations, decisions, receipts, and idempotency. Enforce capabilities and lifecycle rules independently of model output.

## Owned edit surface

- `src/conversation_os/shape_population/storage.py`
- `src/conversation_os/shape_population/migrations.py`
- `src/conversation_os/shape_population/execution_context.py`
- migration/inspection CLI under `tools/`
- governance, migration, concurrency, and recovery tests.

## Ordered implementation

1. Write failing regressions for out-of-packet evidence, identity spoofing, duplicate idempotency keys, partial writes, two writers, killed writer, stale lease, and rejected-then-approved promotion.
2. Introduce numbered, checksumed migrations. On startup acquire migration exclusivity, apply in order, record checksum/time, and refuse unknown or modified migrations.
3. Configure SQLite with foreign keys, WAL, `synchronous=FULL`, and a declared busy timeout. Use `BEGIN IMMEDIATE` for state-changing units, following the repo’s workspace-store pattern.
4. Implement normalized tables for source/segment refs, inquiries, packets/blocks, jobs/attempts/leases, candidates/evidence refs, comparisons, evaluations, events, receipts, idempotency records, promotion requests/decisions, and canonical apply receipts.
5. Add database constraints for legal enums, unique idempotency scope, one terminal human decision per request, foreign-key packet membership, monotonic versions, and immutable accepted artifacts.
6. Commit each command’s state transition, event, receipt, and outbox record in one transaction. Never emit a success receipt before commit.
7. On duplicate idempotency key plus identical request hash, return the original receipt. Same key with different hash is a conflict.
8. Use trusted `ExecutionContext` capabilities at service entry. Payload strings never grant proposer, critic, evaluator, reviewer, or canonical authority.
9. Provide a dry-run migration report and verified one-time import for legacy JSON. Preserve original file read-only until parity checks pass; never append JSON events to an LFS pointer.
10. Add backup/restore and consistency-check commands suitable for rollout and rollback.

## Required tests

- schema upgrade from every supported version and checksum mismatch refusal;
- transaction rollback at every injected failure point;
- multiprocess writers produce no lost update, malformed store, or duplicate receipt;
- process kill followed by restart recovers committed work and safely retries uncommitted work;
- foreign/altered packet refs reject at the database/service boundary;
- all state-machine illegal transitions reject, especially `rejected -> approved/applying/applied`;
- legacy import is idempotent and parity counts/digests match.

Run:

```bash
pytest -q tests/test_shape_storage.py tests/test_shape_migrations.py tests/test_shape_governance.py
pytest -q tests/test_shape_concurrency.py tests/test_shape_recovery.py
```

## Evidence required in the live task

Schema diagram/version; PRAGMA output; migration dry run and parity report; fault-injection matrix; multiprocess results; backup/restore proof; exact commands; full-suite impact; operational limits.

## Exit gate

SQLite is the only mutable Shape workflow authority, all mutations are transactional and capability-checked, legacy data is migrated with parity, and crash/multiprocess tests show no lost, duplicated, or illegally advanced state.
