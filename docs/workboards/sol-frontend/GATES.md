# Gates — SOL Frontend

Every task must pass these gates. The **Pillar Gate** is unique to this board.

## Pillar Gate

- Task lists affected pillar numbers from `PILLARS.md`.
- Implementation does not violate listed pillar rejections.
- If a pillar is intentionally bent, `DECISIONS.md` has an entry with rollback path.
- UX changes state which surface (Capture vs Development) they target.

## Intake Gate

- Problem stated in one sentence.
- Scope-in and scope-out explicit.
- Pillar mapping present.
- Owner named.

## Readiness Gate

- Relevant artifact roots linked (`mobile_surface_v1`, miniapp, etc.).
- Test or manual verification strategy named.
- Failure mode described.

## Implementation Gate

- Changes scoped to declared files and surfaces.
- No silent ontology forks.
- `UPDATES.jsonl` entry for meaningful progress.

## Verification Gate

- Commands run listed exactly.
- Mobile UX: scroll/gesture checks described with device or viewport notes.
- Residual risks stated.

## Done Gate

- Acceptance criteria met.
- Pillar mapping still accurate after implementation.
- Task index and lane agree.
