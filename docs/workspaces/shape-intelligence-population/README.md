# Shape Intelligence Population

This workspace builds the intelligence layer that populates the knowledge ocean with **provisional Shape candidates** when new content arrives. It is deliberately separate from `cognitive-aperture-exceptional`, which owns bounded retrieval and disclosure.

## The decision that created this workspace

Shape extraction is interpretative. A deterministic pipeline is valuable for evidence boundaries, validation, deduplication, provenance, job control, and governance; it should not be the primary mechanism deciding what a Shape means. The system therefore uses constrained intelligence inside a deterministic control plane.

```text
new source / large document
        ↓
existing ingest + chunking + provenance
        ↓
bounded evidence packets
        ↓
OpenClaw proposer → independent critic → synthesizer
        ↓
deterministic schema, evidence, policy, and dedupe checks
        ↓
provisional candidate store + evaluation queue
        ↓
canonical-owner review / explicit promotion only
```

## What is already true

- The initial Chat Converter seed corpus contains 20 conversation sources, 6,611 chunks, 454 legacy Shape signatures, 55 graph nodes, and 18 edges. It is a useful seed, not a complete knowledge ocean.
- The legacy Shape pipeline is mostly deterministic: source → chunks → analysis units → decomposition/meta records → candidate signatures → graph. Those signatures are provisional legacy candidates, not canonical Shapes.
- The current corpus has no canonical Shape profile available to retrieval and no embedding/vector index. It must not be described as a finished canonical Shape system.
- A local OpenClaw probe showed that `thought_tube_router` can propose coherent interpretative hypotheses, boundaries, evidence, alternatives, and uncertainty. It did not satisfy a strict machine-output contract and ran with a broad prompt/tool surface, so it is not a production population identity.
- The OpenClaw gateway is healthy locally; remote-host status has not been established from this machine.

## Target design

Three narrowly scoped OpenClaw identities operate over bounded, injection-safe evidence packets:

1. **Proposer** — produces multiple provisional Shape hypotheses with claims, evidence spans, boundaries, dimensions, counter-hypotheses, and calibrated uncertainty.
2. **Critic** — independently tests each proposal for unsupported abstraction, duplicate/near-duplicate structure, missing negative evidence, overbroad scope, and instruction contamination.
3. **Synthesizer** — reconciles the candidate and critique into an accepted, rejected, or needs-review candidate. It never promotes canon.

The deterministic plane owns: input admission, redaction, source/segment identity, JSON/schema validation, evidence-span verification, versioning, idempotency, cost and retry limits, candidate persistence, similarity/deduplication, telemetry, and the promotion queue.

## Non-negotiable boundaries

- Candidate generation is asynchronous and does not block ordinary ingestion or retrieval.
- Every candidate must preserve exact source and segment provenance, evidence excerpts, model/prompt/tool versions, and a repeatable job receipt.
- Untrusted source text is data, never instruction. The agent receives it only inside an explicit evidence envelope.
- No agent can auto-promote a candidate to canonical Shape status.
- No agent receives broad shell, filesystem, network, or source-registry write authority.
- Existing deterministic legacy signatures may be used as comparison evidence, not promoted as truth.
- Retrieval consumers may read only approved candidate/canonical projections appropriate to their contract; candidate records do not become retrieval ranking facts by default.

## Delivery gates

The first implementation is ready only when it meets the readiness requirements in the linked assessment: dedicated least-privilege identities, bounded evidence packets, strict schema, independent critique, deterministic enforcement, durable idempotent jobs, asynchronous operation, governed promotion, evaluation/observability, privacy controls, and documented operations.

## Read first

1. [OpenClaw readiness and requirements](../cognitive-aperture-exceptional/derived/OPENCLAW_SHAPE_INTELLIGENCE_READINESS.md)
2. [Cognitive Aperture remediation gaps](../cognitive-aperture-exceptional/derived/REMEDIATION_GAP_OVERVIEW.md)
3. [Unified framework workspace](../unified-framework-synthesis/README.md)
4. [Workspace agent protocol](../WORKSPACE-AGENT-PROTOCOL.md)
5. [Workspace-specific sync contract](derived/sync-contract.md)

## Agent boot

```bash
source ~/.config/inner-space-workspace.env 2>/dev/null || true
python3 tools/workspace_coordination.py context \
  --workspace-id shape-intelligence-population \
  --agent-id <agent> --surface <surface> --session-id <session>
python3 tools/workspace_projection_sync.py check \
  --workspace-id shape-intelligence-population
```

Live API is coordination truth. Git files here and under `docs/workboards/` are published projections; never hand-edit task status.
