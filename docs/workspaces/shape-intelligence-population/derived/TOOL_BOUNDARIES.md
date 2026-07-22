# Shape Intelligence Tool Boundaries

## Decision

The system needs nine underlying capabilities, but it does **not** need nine agent-callable tools.

### Automatic infrastructure

These operations are mandatory pipeline behavior and cannot be bypassed or invoked selectively by population agents:

- `normalize_source` — lossless structural normalization with stable provenance and offsets.
- `build_evidence_packet` — deterministic, bounded, injection-safe execution of an evidence inquiry selected by intelligence or an authorized caller.
- candidate validation — schema, evidence-reference, status, and policy enforcement after intelligent output.
- candidate persistence — transactional versioning and storage after validation.
- job receipts — automatic provenance, model/prompt/tool version, retry, budget, and outcome recording.

### Population-agent tools

The first population identities receive only three tools:

1. `submit_candidate` — submit an evidence-grounded provisional interpretation. Validation, persistence, and receipt generation occur atomically behind this boundary.
2. `find_comparison_candidates` — after a candidate exists, retrieve possible related candidates and their evidence. Intelligence decides same, adjacent, conflicting, or distinct.
3. `submit_evaluation` — submit critique, revisions, disposition, evidence, and calibrated uncertainty.

### Privileged governance operations

- `request_promotion` — available only to an authorized reviewer/governance workflow.
- `apply_promotion` — available only to the canonical Shape authority after an approved request and deterministic checks.

Population identities cannot call either promotion operation.

## Data flow

```text
raw input
→ normalize_source [automatic]
→ intelligence/authorized caller forms evidence inquiry
→ build_evidence_packet [automatic deterministic execution]
→ proposer: submit_candidate
→ validate + persist + receipt [automatic, atomic]
→ critic: find_comparison_candidates
→ critic/synthesizer: submit_evaluation
→ validate + persist + receipt [automatic, atomic]
→ authorized review: request_promotion
→ canonical authority: apply_promotion
```

## Ownership

| Workspace | Posture | Owned surface |
|---|---|---|
| `shape-intelligence-normalization` | automatic infrastructure | `normalize_source` capability |
| `shape-intelligence-evidence` | automatic infrastructure | `build_evidence_packet` capability |
| `shape-intelligence-interpretation` | intelligence-facing | `submit_candidate` |
| `shape-intelligence-critique` | intelligence-facing | `find_comparison_candidates`, `submit_evaluation` |
| `shape-intelligence-governance` | automatic infrastructure | validation, transactional persistence, receipts |
| `shape-intelligence-evaluation-promotion` | privileged governance | evaluation policy, `request_promotion`, `apply_promotion` |

## Non-negotiable invariants

- Normalization is lossless and makes no semantic claims.
- Comparison happens only after intelligence has formed a candidate.
- Similarity supplies comparison material; it never declares semantic equivalence.
- Invalid outputs never reach storage.
- Candidate submission, persistence, and receipt creation cannot partially succeed.
- No population identity can mutate canonical Shape state.
