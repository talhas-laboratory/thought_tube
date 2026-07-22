# T10-12 Authorization privacy poisoning

## First-slice scope

Task: `UMF-T10-12-AUTH-PRIVACY`

This slice adds fail-closed authorization before the approved Shape-aware retrieval and evidence resolution entry points:

- `shape_candidate_retrieval.build_shape_aware_retrieval_bundle`
- `disclosure_ports._InnerWorldEvidenceResolver.resolve_frame_blocks`

## Behavior

- Shape-aware retrieval requires an authenticated principal, `shape.search` capability, and an effective grant whose refs or branch/scope cover the request.
- Missing Shape authorization returns `denied_visibility` with empty `seed_capsules` and an audit reason code only.
- The default evidence resolver port requires an authenticated principal, `shape.evidence.resolve` capability, and a concrete ref grant before delegating to the bounded resolver.
- Evidence denial returns no `resolved_blocks`, records `authorization_denied` audit rows, and does not call the resolver that can load chunk text.

## Verification

- `pytest tests/test_shape_candidate_retrieval.py tests/test_evidence_resolver.py` -> 20 passed.
- `pytest tests/test_disclosure_service_bridge_parity.py tests/test_disclosure_contracts.py tests/test_disclosure_receipts.py` -> 23 passed, 1 adjacent receipt-count failure reproduced when run alone:
  `tests/test_disclosure_receipts.py::DisclosureReceiptsTestCase::test_bridge_context_bundle_records_receipt`.

## Residuals

- The engineering guard approved the evidence port boundary, not direct edits to `evidence_resolver.py`; direct low-level resolver calls are unchanged.
- The workspace evidence doc paths are required by the task but are not represented in the code overview owner index, so the docs-only guard assessment reported an ownership mismatch.
