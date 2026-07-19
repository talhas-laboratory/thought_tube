Status: done
Owner: cursor-cloud-reviewer
# CAE-006B — Shape-aware and performance baselines

**Stage:** C
**Priority:** high
**Depends on:** CAE-005B, CAE-007

## Outcome

Prove structural Shape retrieval, AntiMatch behavior, adapter parity, latency, and bounded resource use on the shared service.

## Acceptance

- structural matches beat lexical distractors;
- AntiMatch blocks known false analogy;
- candidate status is never upgraded by retrieval;
- neighborhood precision/recall and distractor harm published;
- p50/p95 latency, bytes resolved, expansion counts, and cache behavior meet approved limits.
