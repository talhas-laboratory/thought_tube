# Build Packet — Critique, Comparison, and `submit_evaluation`

Read [Implementation Foundations](../../shape-intelligence-population/derived/IMPLEMENTATION_FOUNDATIONS.md) first.

## Owner and interfaces

Create `src/conversation_os/shape_population/critique.py`. The critic/synthesizer receive only:

- `find_comparison_candidates(candidate_id, limit, policy_version)` → evidence-backed possible neighbors.
- `submit_evaluation(payload)` → critique, disposition, revisions, evidence, uncertainty, and relationship findings.

Comparison results use only `possible_same`, `possibly_adjacent`, `possibly_conflicting`, or `possibly_distinct`; they never return authoritative equivalence.

## Rules

Comparison is unavailable before a candidate has been accepted as a provisional record. Critic identity must be distinct from proposer identity/run. The synthesizer preserves disagreement rather than forcing agreement. Evaluation may recommend but cannot promote.

## Fixtures and tests

Create `tests/fixtures/shape_population/critique/` with same-like, adjacent, conflicting, distinct, false-merge, false-split, unsupported, and contaminated cases.

`tests/test_shape_population_critique.py` must prove: comparison precondition; bounded result/provenance; distinct identity; no canonical tool; evaluation schema; relationship vocabulary; safe ambiguous disposition; adversarial false merge/split; evaluator rubric checks for grounding, challenge quality, and uncertainty. Add a continuity test that candidate evidence and boundary survive critique unless an explicit revision says why.

Run: `pytest tests/test_shape_population_critique.py -q`.
