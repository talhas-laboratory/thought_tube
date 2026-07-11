# Gates

These gates are mandatory for this product folder.

## Intake Gate

- Problem is stated in one sentence.
- System owner is named.
- Scope-in and scope-out are explicit.
- Relevant sources are linked.
- Unknowns and dependencies are listed.

## Design Gate

- Contract or artifact shape is named.
- Integration point with the spine is stated.
- Failure mode is stated.
- Reversibility path is stated.
- Provenance requirements are stated.
- Source-of-truth file or workspace is stated.

## Implementation Gate

- Changes are scoped to the declared system.
- Cross-system changes update `CONNECTIONS.md`.
- Tests are defined before or alongside implementation.
- Decisions are recorded before being relied on.
- Append-only update is written to `UPDATES.jsonl`.

## Verification Gate

- Exact commands or manual checks are recorded.
- Result is recorded, including failures.
- Semantic behavior is checked, not only import/type correctness.
- Residual risks are listed or `none known`.

## Promotion Gate

- Raw evidence is preserved.
- Interpretation is separated from source text.
- Confidence and reason for promotion are recorded.
- Correction, discard, and rollback paths remain available.

## Done Gate

- Acceptance criteria are satisfied.
- Verification evidence is attached or linked.
- Task state, subproject packet, and update log agree.
- No hidden follow-up is required for the stated scope.
