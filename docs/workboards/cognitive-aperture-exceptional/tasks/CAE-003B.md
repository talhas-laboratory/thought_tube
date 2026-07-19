Status: done
Owner: cursor-stage-b-review
# CAE-003B — Deterministic budget allocator

**Stage:** B
**Priority:** critical
**Depends on:** CAE-015, CAE-003A
**Owner paths:** disclosure budget owner, bridge projection, focused tests

## Outcome

Orientation and evidence are selected by a deterministic token/block ledger before execution composition.

## Acceptance

- tokenizer/estimator and reservation rules are versioned;
- evidence is included as whole provenance-preserving blocks;
- no execution bundle exceeds the effective budget;
- identical inputs at one corpus/policy revision are deterministic;
- insufficient required capacity returns explicit status;
- drop ledger appears in audit only.
