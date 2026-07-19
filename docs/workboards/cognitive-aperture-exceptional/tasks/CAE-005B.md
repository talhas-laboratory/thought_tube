Status: backlog
# CAE-005B — Holodeck adapter and parity

**Stage:** C
**Priority:** high
**Depends on:** CAE-005A
**Owner paths:** `holodeck.py` adapter, contextualization tests

## Outcome

Holodeck uses the shared disclosure service for knowledge/static context while retaining workspace-specific projection.

## Acceptance

- independent admission/scoring is retired or explicitly isolated;
- equivalent Bridge/Holodeck requests yield equivalent disclosure decisions;
- workspace grants and provenance remain intact;
- latency, feature flag, and rollback pass.
