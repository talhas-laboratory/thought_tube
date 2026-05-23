# Holodeck Inquiry Planner Design

Date: 2026-04-28

## Goal
Add a grounded inquiry planner to Holodeck that turns existing workspace gaps, conflicts, and missing evidence into a tracked inquiry queue and a small set of justified user-facing questions.

## Principle
The system should not ask a question just because it can. A question should only be surfaced when:
- the missing answer is externally owned or requires user judgment,
- the answer materially changes scope, direction, or readiness,
- the reason for asking can be grounded in explicit workspace signals.

## Approach
- Derive inquiries from existing Holodeck signals only.
- Classify each inquiry as one of: `user_input`, `decision`, `evidence`, `verification`, `scope`, `integration`.
- Attach explicit grounding:
  - `source_signals`
  - `why_this_matters`
  - `impact`
  - `blocking`
  - `resolution_path`
  - `ask_user`
- Expose the queue through Holodeck status/check/task-pack.
- Produce a small `questions_for_user` list containing only the highest-impact inquiries with `ask_user=true`.

## Non-Goals
- No speculative or filler questions.
- No separate freeform LLM question generator.
- No replacing existing work-item, context, constraint, or knowledge systems.

## Success Condition
- Holodeck can explain what is missing.
- Holodeck can distinguish user-owned gaps from agent-owned gaps.
- User-facing questions are few, grounded, and high impact.
