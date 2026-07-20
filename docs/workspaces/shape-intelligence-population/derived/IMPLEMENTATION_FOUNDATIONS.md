# Shape Intelligence Implementation Foundations

## Canonical lifecycle

`raw source → normalization → evidence packet → proposer → atomic candidate submission → critic/synthesizer → atomic evaluation submission → designated-agent recommendation → human approval → canonical promotion`.

The system has three population-agent tools only: `submit_candidate`, `find_comparison_candidates`, and `submit_evaluation`. All other behavior is deterministic orchestration or privileged governance.

## Shared record invariants

- Every source has `source_id`, immutable content digest, modality, original metadata, and retained raw reference.
- Every segment has `segment_id`, `source_id`, character offsets, byte offsets when available, parent structure path, exact text digest, and deterministic ordering.
- Every evidence reference resolves to a source and segment range; a missing or altered span rejects submission.
- Every model-produced record includes `agent_identity`, model/prompt/tool-contract versions, input packet ID, run ID, and uncertainty.
- Candidate/evaluation submission is atomic: validation, persistence, and receipt either all succeed or none does.
- Candidate status may be `proposed`, `under_review`, `rejected`, `needs_evidence`, `recommended`; only a human approval moves a recommendation to `canonical`.

## Test doctrine

Deterministic nodes use exact fixture assertions. Intelligence nodes use a fixed model stub for routing/contract tests plus golden evidence packs, bounded semantic rubrics, counter-hypothesis requirements, and adversarial cases. No test treats a lexical similarity score as semantic truth.

All implemented work must run its focused pytest command and the relevant integration/continuity suite from the corresponding child packet.
