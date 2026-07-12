# Workspace Handoff — Unified Metaphysical Framework Foundation

**Workspace:** `unified-framework-synthesis`  
**Task pack:** `unified-metaphysical-foundation-schema-lock`

## Canonical context

The synthesis phase is complete. Version 1.1 is now the canonical foundation for modeling arbitrary metaphysical spaces and for building reusable application infrastructure.

The system direction is:

```text
universal record kernel
→ governed profile runtime
→ bounded reasoning and execution services
→ application SDK
→ Thought Tube, World Studio, Curator, and future applications
```

MTSF, SDS, ThoughtShape, and earlier synthesis documents remain preserved as provenance and migration evidence. They must not be implemented as parallel systems.

## Primary surfaces for agents

| Need | Read |
|------|------|
| **Live workspace state** | `python3 tools/workspace_coordination.py context --workspace-id unified-framework-synthesis --agent-id <agent> --surface <surface> --session-id <session>` |
| **Normative framework** | `sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md` |
| Published live continuity | `CONTINUITY.md` |
| Foundation build sequence | `derived/foundation-build-plan.md` |
| Focused implementation context | `continuity/task-pack.md` |
| Generated Conversation OS task pack | `context/task_packs/unified-metaphysical-foundation-schema-lock.md` |
| Historical thread arc | `continuity/thread-transcript.md` |
| Historical analyses | `analyses/` |
| Historical source frameworks | `sources/` + `docs/frameworks/` |
| Machine catalog | `manifest.json` |

## Constraints

- The live workspace service is authoritative for task and coordination state
- Git workspace files are projections and must not be treated as live mutable state
- One kernel, governed profiles, and application projections
- Version 1.1 wins on primitive status, naming, lifecycle, branching, Shape semantics, profiles, compilation, and build order
- Historical sources are not runtime owners
- Do not build broad surfaces before foundation conformance gates pass
- Capture and provenance must work when semantic extraction is unavailable
- Claims do not become represented States without explicit `StateCommitment`
- Runtime packets are bounded projections, not canonical stores
- Run `engineering-guard assess` before code
- Task packs are curated — use transcript + analyses for full depth

## Next actions

1. Lock schemas for `SourceFragment`, `Referent`, `Scope`, `State`, `Claim`, `RelationInstance`, `Provenance`, `ModelBranch`, `BranchMembership`, and `StateCommitment`.
2. Lock maturity, epistemic, and governance lifecycle state machines.
3. Define `ProfileDefinition`, dependency validation, and profile conformance results.
4. Create migration fixtures mapping current records and historical framework concepts into the canonical model.
5. Implement the Phase 1 vertical slice and adversarial invariant tests.

The generated handoff pack is `context/task_packs/unified-metaphysical-foundation-schema-lock.{json,md}`. Use it together with the workspace task pack; the workspace copy carries the canonical scope and constraints, while the generated pack carries current session and repository context.

## Blockers

The historical workspace id `unified-framework-synthesis-4f48` remains in the live catalog as a stale synthesis-era record. Do not use it for new work; use `unified-framework-synthesis`.

Nine ignored module manifests advertised absent cloud-agent modules as active. They were preserved under `context/substrate/planned_modules/` so the current codebase index describes only locally present owners.

## Integration targets

- `src/conversation_os/models.py` — current shared record owner; candidate host for the first contracts
- `src/conversation_os/storage.py` — append-only and file-backed durability primitives
- `src/conversation_os/conversation_synthesis.py` — existing Formation, Shape, and operator concepts requiring migration
- `src/conversation_os/routing.py` — task-pack and workspace handoff enrichment
- `src/conversation_os/personal_interface.py` — application projection for user-local calibration, not kernel ownership
- `src/conversation_os/worldbuilding_studio.py` — application projection and a future conformance consumer

## Verification

- Canonical paper version: `1.1`
- Live workspace id: `unified-framework-synthesis`
- Workspace policy: `AGENTS.md`
- Codebase overview validation: must report zero errors and warnings before implementation
- Historical session: `cursor-unified-framework-synthesis-4f48`
