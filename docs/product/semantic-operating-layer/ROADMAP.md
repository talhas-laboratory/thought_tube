# Roadmap

The roadmap keeps sequencing tight. Do not build later phases before the contracts they depend on exist.

## Phase 1 — Spine and Contracts

- Define minimal contracts for each subproject.
- Define shared workspace ownership and Holodeck binding rules.
- Fix known bridge substrate gaps: candidate retrieval timing and session corpus split.
- Add preview-only frame tooling before execution-time frame injection.
- Define semantic gates for false memory, provenance, isolation, and promotion.

## Phase 2 — Working Narrow Slice

- Implement `PurposeState`, `ObjectTopology`, `FrameSpec`, and `SessionEnvelope` in the bridge path.
- Stand up one Holodeck-backed workspace for the first active subproject.
- Add tests for strict session isolation, sidecar isolation, and provenance.
- Connect one workboard task packet to one frame-backed agent handoff.

## Phase 3 — Capture and Correction

- Add provisional capture cards.
- Add correction events and reversible promotion/demotion.
- Add user-facing inspect/correct/discard/promote controls.

## Phase 4 — Lens Packs

- Define first lens pack for product/building work.
- Add lens-specific schemas, evaluators, and packet templates.
- Keep lens packs bounded; do not fork the base ontology.

## Phase 5 — Surfaces

- Add surface profiles for Codex and OpenClaw first.
- Extend to miniapp/mobile after the substrate contracts are stable.
- Verify the same product spine works across tools without hidden state drift.
