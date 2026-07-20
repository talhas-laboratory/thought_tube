# Build Packet — Proposer and `submit_candidate`

Read [Implementation Foundations](../../shape-intelligence-population/derived/IMPLEMENTATION_FOUNDATIONS.md) first.

## Owner and interface

Create `src/conversation_os/shape_population/candidate_submission.py` and a dedicated OpenClaw proposer identity. The proposer receives an evidence packet and only `submit_candidate(payload)`.

Candidate payload requires: `packet_id`, title, statement, boundary, mechanism/relations, dimensions, evidence_refs, counter_hypotheses, uncertainty, recommended disposition, and agent/model/prompt versions. Governance assigns `candidate_id` after acceptance. It cannot include `canonical` status or invoke storage directly.

## Intelligence guidance

The proposer generates one or more possible Shapes, distinguishes evidence from inference, includes at least one alternative when ambiguity exists, and says `needs_evidence` when support is insufficient. Quality is evaluated by a reviewer model/human rubric: grounding, explanatory coherence, boundary clarity, alternative consideration, and uncertainty calibration—not deterministic shape scoring.

## Fixtures and tests

Create `tests/fixtures/shape_population/interpretation/` with grounded, ambiguous, multi-shape, insufficient-evidence, contradictory-evidence, and prompt-injection packets.

`tests/test_shape_population_interpretation.py` must use a stubbed model for tool routing and assert: only `submit_candidate` is exposed; invalid JSON/schema or missing evidence refs are rejected; service-assigned IDs are immutable; canonical writes are impossible; timeout/retry is bounded. Add golden semantic cases requiring evidence/counter-hypothesis/uncertainty fields. An intelligence-led critic/evaluator—not deterministic validation—assesses whether an interpretation is unsupported. Record an evaluator rubric with explicit uncertainty rather than exact prose matching.

Run: `pytest tests/test_shape_population_interpretation.py -q`.
