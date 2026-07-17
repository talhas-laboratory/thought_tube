# CAE-001 — Fail-empty retrieval + tests

**Phase:** 1  
**Priority:** critical  
**Status:** planned (live registration pending)  
**Depends:** CAE-000  
**pillars:** structure, bridge

## Goal

Make `build_retrieval_bundle` fail empty when there is no positive query evidence. Remove confidence-only seeding and forced top-ranked fallback under bounded/strict modes.

## Acceptance

- [ ] Unrelated query → `count=0`
- [ ] Empty query → empty under bounded/strict
- [ ] Alias positive hits still retrieve
- [ ] Pond-less capsules excluded under bounded/strict
- [ ] Tests cover negative and positive cases

## Paths

- `src/conversation_os/knowledge_layer.py`
- `tests/test_*.py` (retrieval / bridge policy)

## Residual risks

- Recall regression — mitigate with alias governance and pond backfill follow-ups
