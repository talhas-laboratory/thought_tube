# Evaluation and Promotion Remediation Packet

Authority: [central remediation plan](../../shape-intelligence-population/derived/REMEDIATION_IMPLEMENTATION_PLAN.md), especially Phases 4, 6, 8, and 9.

## Required outcome

Permit a designated evaluator to recommend a candidate, require a separately authenticated human decision, and allow only a privileged canonical adapter to apply an approved request exactly once. Rejection is terminal.

## Owned edit surface

- evaluation/promotion contracts and services in `src/conversation_os/shape_population/`
- `src/conversation_os/shape_population/canonical_port.py`
- evaluator OpenClaw config/provisioning
- `src/conversation_os/shape_projection_reader.py` integration
- promotion, authorization, canonical parity, continuity, and rollback tests.

## Ordered implementation

1. Keep the confirmed rejected-then-approved bypass as a failing regression until the new state machine rejects it at both service and database layers.
2. Separate three acts: evaluator recommendation, human decision, canonical apply. A model cannot create the human event; a human event cannot directly mutate canonical storage; an apply cannot infer approval.
3. Use terminal states: `requested -> approved -> applying -> applied`, or `requested -> rejected`. Failure from `applying` records an attempt and returns to an explicitly retryable approved state without manufacturing a new human decision. All other transitions fail.
4. Require authenticated execution contexts and distinct capabilities for evaluator, human reviewer, and canonical writer. Record actor principal, authentication source, time, reason, candidate/evaluation versions, request hash, and trace ID.
5. Provision a designated evaluator identity. It may submit a structured recommendation with rubric scores, uncertainties, and evidence; it cannot approve or apply.
6. Define `CanonicalShapePort` with prepare/validate/apply/read-back operations. Resolve the registered `profile:shape_and_semantic_addressing`; if unavailable, fail closed with an explicit dependency receipt. Do not invent a third canonical JSON store.
7. Before apply, revalidate candidate/evaluation immutability, approval, canonical version precondition, and idempotency. Commit an apply intent; call the port; then record canonical ID/version/digest and read-back parity.
8. If external apply succeeds but local acknowledgement fails, reconciliation must discover the canonical receipt/idempotency key and complete locally without a second canonical write.
9. Define rollback as a new audited canonical version/tombstone through the same owner port, never destructive deletion or SQLite rewind.

## Required tests

- model/reviewer/canonical capability separation;
- no human decision, forged human metadata, double decision, approve after reject, reject after approve, apply before approval, duplicate apply, stale candidate/evaluation, stale canonical version;
- injected failure before call, after external success, and before local acknowledgement;
- restart reconciliation proves exactly-once observable canonical outcome;
- canonical read-back parity includes identity, semantic body, dimensions, relationships, evidence provenance, uncertainty, decision, and version;
- evaluator semantic rubric cases include unsupported confidence, unresolved contradiction, duplicate ambiguity, incomplete provenance, and genuinely promotion-ready candidates.

Run:

```bash
pytest -q tests/test_shape_evaluation.py tests/test_shape_promotion.py tests/test_shape_canonical_port.py
pytest -q tests/test_shape_continuity.py -k 'evaluation or promotion or canonical'
```

## External dependency gate

The canonical Shape profile is currently unavailable. Implementation may complete the port and fail-closed tests, but production promotion cannot be declared ready until Unified Metaphysical Framework ownership registers the canonical profile and a read/write/read parity test passes against it.

## Evidence required in the live task

Authorization matrix; state transition table; real evaluator routing; human-event example; exactly-once recovery trace; canonical parity receipt; rollback rehearsal; full-suite impact; explicit dependency status.

## Exit gate

No intelligence can approve itself, rejection cannot be reversed, apply is authorized and recoverably idempotent, canonical state is owned through the registered profile, and every promotion or rollback has complete human and machine provenance.
