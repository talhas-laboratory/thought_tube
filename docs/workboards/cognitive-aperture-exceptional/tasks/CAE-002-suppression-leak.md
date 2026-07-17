# CAE-002 — Remove suppression leak + fix tests

**Phase:** 1  
**Priority:** critical  
**Status:** planned  
**Depends:** CAE-000

## Goal

Execution prompts must not include suppressed/omitted frame block content or summaries. Audit/inspect paths retain omit reasons.

## Acceptance

- [ ] `compose_execution_message` has no suppressed block section for the model
- [ ] Tests that required leak are rewritten
- [ ] Inspect/audit still exposes omit reasons

## Paths

- `src/conversation_os/chat_backends.py`
- related bridge compose tests
