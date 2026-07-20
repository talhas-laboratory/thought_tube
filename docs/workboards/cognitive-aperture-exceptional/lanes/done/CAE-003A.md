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

## Verification

- **Commit:** `38c7806` on branch `cursor/cognitive-aperture-gap-map-24c7` (PR #32).
- **Command:** `. .venv/bin/activate && PYTHONPATH=src pytest -q tests/test_effective_grant_envelope.py tests/test_reasoning_bridge_policy.py`
- **Result:** open/bounded/strict/incognito envelope matrix passes; deny precedence and `normalize_effective_grant()` boundary enforced once in Bridge.
- **Changed paths:** `reasoning_bridge.py` (`build_effective_grant_from_context`, `effective_layers_to_bridge_layers`), `tests/test_effective_grant_envelope.py`.
- **Feature flag:** `bridge.effective_grant_normalization_v1` (default `true`).
- **Decision:** D-013.

## Rollback / risk

- Set `bridge.effective_grant_normalization_v1: false` to restore downstream reinterpretation of policy/envelope.
- Residual risk: Holodeck/Feed adapters must consume normalized grants when enabled on those surfaces.
