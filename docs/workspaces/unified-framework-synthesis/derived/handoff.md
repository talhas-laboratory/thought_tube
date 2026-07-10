# Workspace Handoff — Unified Framework Synthesis

**Workspace:** `unified-framework-synthesis-4f48`  
**Task pack:** `unified-framework-continuity-4f48`

## Context

Jul 2026 Cursor design thread comparing MTSF, SDS, and ThoughtShape; extended with capture tools, Inner Space Curator, community pipeline, cross-agent workspace.

## Primary surfaces for agents

| Need | Read |
|------|------|
| Full thread arc | `continuity/thread-transcript.md` |
| All analyses | `analyses/` (7 files) |
| Source frameworks | `sources/` + `docs/frameworks/` |
| Canonical synthesis | `sources/unified-framework-synthesis.md` |
| Machine catalog | `manifest.json` |

## Constraints

- One ontology — three views, not three stores
- Do not build surfaces before schema lock
- Run `engineering-guard assess` before code
- Task packs are curated — use transcript + analyses for full depth

## Next actions

1. Rearrange decomposed primitives → single unified framework doc
2. Draft ThoughtObject, ReasoningStep, ReasoningSignature schemas
3. Update glossary
4. Implement Phase 1 capture kernel

## Blockers

None — synthesis phase is active.

## Integration targets

- `docs/frameworks/metaphysical-thought-space/` (MTSF schemas)
- `src/conversation_os/mtsf_*.py` (kernel)
- `src/conversation_os/routing.py` (task packs)
- `src/conversation_os/personal_interface.py` (reasoning calibration)

## Verification

- PR #7 contains all committed framework + workspace docs
- Session imported: `cursor-unified-framework-synthesis-4f48`
