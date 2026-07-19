Status: backlog
# CAE-005A — Disclosure service and Bridge adapter

**Stage:** C
**Priority:** high
**Depends on:** Stage B gate
**Owner paths:** new service/facade selected by guard, Bridge adapter, focused tests

## Outcome

Extract the proven Bridge disclosure path behind storage-independent ports without changing its verified decisions.

## Acceptance

- service depends on catalog/search/Shape/evidence/receipt ports;
- no product surface is imported by the service;
- Bridge parity fixtures pass;
- no full-ocean scan or unbounded walk;
- feature flag and rollback pass;
- p50/p95 and resolved-byte baseline recorded.
