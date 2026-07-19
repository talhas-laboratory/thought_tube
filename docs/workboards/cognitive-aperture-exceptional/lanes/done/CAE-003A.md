Status: done
Owner: cursor-stage-b-review
# CAE-003A — Effective grant and envelope matrix

**Stage:** B
**Priority:** critical
**Depends on:** CAE-015, CAE-006A
**Owner paths:** `models.py`, `reasoning_bridge.py`, policy tests

## Outcome

Requested policy is normalized once into an immutable `EffectiveGrant`; deny precedence and envelope side effects are mechanically enforced.

## Acceptance

- one normalization boundary replaces downstream reinterpretation;
- open/bounded/strict/incognito access and persistence differ as specified;
- denials override defaults, inferred depth, pins, and ranking;
- incognito invokes no ocean retrieval or durable learning;
- complete matrix and rollback tests pass.
