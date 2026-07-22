# T10-17 Coherent agent harness (first slice)

**Task:** `UMF-T10-17-AGENT-HARNESS`  
**Wave:** `UMF-T10-WAVE-04-SAFE-AGENT-USE`  
**Date:** 2026-07-22  
**Owner:** `metaphysical_kernel_application_sdk.py`

## Scope

This slice adds a minimal intent-oriented `AgentHarness` on top of the existing `FoundationApplicationSdk`.

## Contract

- Read intents: `orient`, `retrieve_bounded_evidence`, `inspect_provenance`.
- Write intents: `propose_interpretation`, `request_review`.
- Forbidden intents remain outside the harness: `authorization_admin`, `delete`, `deploy_policy`, `promote`.
- Every response returns typed `ok` / `error` status fields, stable ids, branch/scope, candidate/canonical labels, provenance inspection state, and continuation hints.

## Verification

- `pytest tests/test_metaphysical_kernel_application_sdk.py`

Result: `10 passed`.

## Residuals

- MCP, OpenClaw, rate-limit, timeout, and cancellation adapters remain follow-on slices.
- Shape similarity lookup stays deferred to the bounded inspector/retrieval owners.
