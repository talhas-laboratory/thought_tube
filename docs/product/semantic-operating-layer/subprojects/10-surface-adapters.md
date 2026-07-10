# Surface Adapters

Status: `seeded`  
Owner: `unassigned`  
First contract: `SurfaceProfile`

## Responsibility

Map the same semantic substrate into each tool without forking the ontology.

## Scope In

- Codex
- OpenClaw
- MCP bridge
- miniapp
- mobile
- future agent surfaces

## Scope Out

- one-off surface-specific product logic
- duplicate memory stores

## Integration

Consumes bridge contracts and product gates. Feeds execution constraints, persistence defaults, and correction affordances.

## First Tasks

- Define `SurfaceProfile` schema.
- Create Codex and OpenClaw profiles first.
- Test that surface differences do not change core frame semantics.

## Active Implementation Slice

**Mobile Thought Capture** — immersive capture web app for `product/mobile_surface_v1/`

- Workboard: [sol-frontend-mobile-capture](/Users/talhauddin/software/inner_space/docs/workboards/sol-frontend-mobile-capture/README.md)
- Spec: [SPEC.md](/Users/talhauddin/software/inner_space/docs/workboards/sol-frontend-mobile-capture/SPEC.md)
- Source: [conv_20260627_125956_smooth-microgestures-on-mobile](/Users/talhauddin/software/inner_space/mobile_artifacts/2026-06-27/conv_20260627_125956_smooth-microgestures-on-mobile/manifest.json)
- Contracts: `CaptureSurface`, `ScrollEngine`, `GestureZone`, `CaptureModeState`

## Acceptance Criteria

- Same frame/policy/envelope contract works across surfaces.
- Surface defaults are explicit.
- Privacy and persistence behavior are visible.
