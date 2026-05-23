# Holodeck Owner Extraction Design

Date: 2026-04-28

## Goal
Move Holodeck workspace logic out of `src/conversation_os/cli.py` into a dedicated owner module while preserving existing behavior, tests, and command-line surface.

## Constraint
The engineering guard currently rejects new owner paths unless they are within an approved ownership surface. A direct extraction to `src/conversation_os/holodeck.py` is therefore blocked.

## Approach
1. Extend the engineering guard so it can approve a new adjacent owner module when:
- the current owner is the top recommended surface,
- the new module lives in the same package,
- the request purpose explicitly states owner extraction or ownership split,
- the existing owner remains in the proposed paths.
2. Re-run the guard for the Holodeck extraction path.
3. Extract Holodeck logic into `src/conversation_os/holodeck.py`, leaving `cli.py` primarily responsible for argument parsing and command dispatch.
4. Preserve the current CLI behavior and regression coverage.

## Boundaries
- No user-facing CLI command changes.
- No raw event format changes.
- No non-Holodeck subsystem refactors.
- Extraction should be mechanical and behavior-preserving.

## Testing
- Add guard-level regression tests for the new adjacent-owner approval rule.
- Add extraction-level regression coverage through the existing `tests/test_conversation_os.py` suite.
- Run `python3 -m py_compile ...` and the full `tests.test_conversation_os` suite after extraction.

## Success Condition
- The engineering guard approves the extraction path.
- Holodeck logic has a dedicated module owner.
- The CLI surface remains behaviorally unchanged.
- Full regression verification remains green.
