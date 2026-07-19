Status: done
Owner: cursor-cloud-reviewer
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

## Verification

- **Commit:** `7b86d47` on branch `cursor/cognitive-aperture-gap-map-24c7` (PR #32).
- **Command:** `. .venv/bin/activate && PYTHONPATH=src pytest -q tests/test_holodeck_disclosure_parity.py`
- **Result:** Holodeck admitted capsule IDs and source refs match Bridge `retrieval_decision_subset()` for the same query; legacy meta-layer path isolated when flag disabled.
- **Changed paths:** `src/conversation_os/holodeck_disclosure_adapter.py`, `holodeck.py` (adapter wiring), `tests/test_holodeck_disclosure_parity.py`.
- **Feature flag:** `holodeck.disclosure_service_v1` (default `false`).
- **Decision:** D-018.
- **Reviewer:** Stage C/D independent review (`5ac2934`) — approved.

## Rollback / risk

- Set `holodeck.disclosure_service_v1: false` to restore `_collect_legacy_meta_layer_candidates()` path.
- Residual risk: workspace projection layers (`product_thesis`, `artifact_doc`, `plan_doc`) remain Holodeck-owned; parity is defined on knowledge retrieval subset only.
