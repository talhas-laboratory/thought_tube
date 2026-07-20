# Interpretation Remediation Packet

Authority: [central remediation plan](../../shape-intelligence-population/derived/REMEDIATION_IMPLEMENTATION_PLAN.md), especially Phases 1, 4, 7, and 8.

## Required outcome

Create a real, restricted proposer intelligence that interprets normalized evidence and submits provisional Shape candidates through one strict boundary. No heuristic or deterministic Shape extraction is permitted.

## Owned edit surface

- `src/conversation_os/shape_population/contracts.py`
- `src/conversation_os/shape_population/execution_context.py`
- `src/conversation_os/shape_population/model_gateway.py`
- proposer portion of `orchestrator.py`
- proposer OpenClaw configuration and provisioning files
- proposer routing, contract, and semantic tests.

## Ordered implementation

1. Define `ExecutionContext` as runtime-created identity, run, model, capability, and trace metadata. Agent JSON must not contain or override these fields.
2. Define a strict candidate payload with semantic label, description, dimensions, relationships, uncertainty, alternatives, and packet-bound EvidenceRefs. Reject unknown fields, coercion, NaN, prose wrappers, and markdown fences.
3. Expose only `submit_candidate` to the proposer. Validation, transactionality, receipts, and lifecycle transitions remain automatic services behind it.
4. Provision a dedicated OpenClaw proposer identity with least privilege. Its instructions must explain Shapes as interpretive multidimensional semantic objects; they must forbid keyword extraction, similarity-first framing, invented evidence, and promotion claims.
5. Implement a typed `ModelClient` adapter over the existing OpenClaw transport. Require one JSON object, validate before persistence, bound timeout/retries, and record prompt/model/config versions and usage without trusting model-supplied metadata.
6. On invalid output, perform at most the declared repair attempts using validation errors only. Exhaustion moves the job to a reviewable failure/dead-letter state; it never creates a partial candidate.
7. Keep source evidence and instructions in separate message regions. Only packet material may support a proposal.
8. Persist alternatives and uncertainty rather than forcing false certainty or premature deduplication.

## Required tests

- payload cannot self-assign identity, model, run, approval, or capabilities;
- strict JSON rejects fences, leading prose, trailing objects, unknown keys, coercions, and invalid EvidenceRefs;
- stubbed OpenClaw transport proves correct identity, tool allowlist, timeout, repair, usage, and provenance propagation;
- golden semantic cases cover multiple Shapes in one source, implicit Shapes, cross-dimensional Shapes, ambiguity, no-Shape input, prompt injection, and conflicting evidence;
- deterministic replay with stored model output creates the same accepted candidate and receipt.

Use exact structural or bounded comparators for contracts. Use rubric-based semantic evaluation only for interpretive quality, with dimensions for evidence faithfulness, dimensional richness, uncertainty calibration, and non-redundancy.

Run:

```bash
pytest -q tests/test_shape_contracts.py tests/test_shape_model_gateway.py tests/test_shape_proposer.py
pytest -q tests/test_shape_semantic_quality.py -k proposer
```

## Evidence required in the live task

Provisioned identity/config hash; exact schema; tool allowlist; routing test; repair/dead-letter trace; semantic case results with evaluator version; full-suite impact; residual model variability.

## Exit gate

Production orchestration invokes the real proposer identity, candidate meaning comes from intelligence, caller JSON cannot manufacture authority, and every accepted statement is traceable to the exact evidence packet.
