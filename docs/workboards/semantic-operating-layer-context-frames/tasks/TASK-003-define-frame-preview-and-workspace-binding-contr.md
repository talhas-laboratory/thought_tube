# TASK-003-define-frame-preview-and-workspace-binding-contr: Define frame preview and workspace binding contract

Status: backlog
Owner: unassigned
Current gate: intake

## Problem

The product spine names `FrameSpec`, `FrameBundle`, and `SessionEnvelope`, but before this pass they were only labels. That leaves implementation free to blur membership, disclosure, session isolation, and learning behavior.

We need one explicit contract reference so bridge work, tests, and agent handoff all mean the same thing when they talk about:

- frame assembly
- preview behavior
- strict versus incognito isolation
- workspace-bound context

## Scope

In:

- define detailed contract language for `FrameSpec`
- define detailed contract language for `FrameBundle`
- define detailed contract language for `SessionEnvelope`
- define first mode semantics for `open`, `bounded`, `strict`, and `incognito`
- bind the subproject packet to a single contract reference in the product spine

Out:

- executable UI preview work
- full schema validation code
- promotion/evaluator implementation beyond contract language
- generalized workspace protocol outside context frames

## Acceptance Criteria

- the product spine contains one detailed contract reference for frame/envelope terms
- the subproject packet links to that contract reference
- membership, disclosure, and learning boundaries are explicitly separated
- `strict` and `incognito` are defined as different modes
- the first contract test matrix is named

## Plan

- add a dedicated contract doc to the product spine
- link the subproject packet to the contract doc
- reflect the contract split in shared connection language
- use the contract doc as the implementation and testing anchor

## Verification Evidence

- Product-spine documentation pass completed.

## Updates

- Created: `2026-06-26T16:51:56.533891+00:00`

## Handoff Notes

- None yet.
