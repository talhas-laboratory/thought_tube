# Shape Intelligence Population

This workspace builds the intelligence layer that populates the knowledge ocean with **provisional Shape candidates** when new content arrives. It is separate from `cognitive-aperture-exceptional`, which owns bounded retrieval and disclosure.

## Core decision

Shape extraction is interpretative. Deterministic systems are essential for evidence boundaries, validation, provenance, job control, deduplication, and governance; they should not be the primary mechanism deciding what a Shape means.

```text
new source → existing ingest/chunking/provenance → bounded evidence packets
→ OpenClaw proposer → independent critic → synthesizer
→ deterministic validation and policy checks → provisional candidate store
→ evaluation/review queue → explicit canonical-owner promotion only
```

## Established context

- The Chat Converter seed corpus contains 20 conversation sources, 6,611 chunks, 454 legacy Shape signatures, 55 graph nodes, and 18 edges. It is a seed corpus, not a complete knowledge ocean.
- Legacy Shape generation is mostly deterministic: source → chunks → analysis units → decomposition/meta records → candidate signatures → graph. The 454 signatures are provisional legacy candidates, not canonical Shapes.
- There is currently no canonical Shape profile available to retrieval and no embedding/vector index.
- A local OpenClaw probe showed useful interpretative reasoning, but its existing general-purpose identity failed the strict JSON and least-privilege requirements. Production requires dedicated identities.

## Target system

Three restricted identities operate only on bounded, injection-safe evidence packets:

1. **Proposer**: offers several candidates with claims, evidence spans, boundaries, dimensions, alternatives, and uncertainty.
2. **Critic**: tests for unsupported abstraction, duplication, missed negative evidence, overbroad scope, and contamination.
3. **Synthesizer**: reconciles the proposal and critique into accepted, rejected, or needs-review candidate records; it never promotes canon.

The deterministic control plane owns input admission/redaction; source and segment identity; schema and evidence-span validation; versioning; idempotency; retry and cost limits; candidate persistence; dedupe; telemetry; and promotion-queue routing.

## Hard boundaries

- Candidate population is asynchronous and never blocks normal ingestion or retrieval.
- Every candidate retains source and segment provenance, evidence excerpts, model/prompt/tool versions, and a durable job receipt.
- Untrusted source text is data, never instruction.
- No population identity can auto-promote a candidate.
- No population identity receives broad shell, filesystem, network, registry-write, or promotion authority.
- Legacy deterministic signatures are comparison evidence, never canonical truth.
- Candidate records do not become retrieval-ranking facts without an explicit approved projection.

## Initial work items

| ID | Outcome |
|---|---|
| SIP-001 | Lock evidence-packet and candidate contracts. |
| SIP-002 | Create least-privilege OpenClaw proposer, critic, and synthesizer identities. |
| SIP-003 | Build the deterministic asynchronous population control plane. |
| SIP-004 | Establish golden/adversarial evaluation and governed promotion handoff. |

Each item has a declared contract in the Holodeck: schema/security, identity capability, end-to-end idempotency, and interpretative-quality/promotion evaluation respectively.

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

The live API is coordination truth. Git workspace/workboard files are projections; never hand-edit task status.
