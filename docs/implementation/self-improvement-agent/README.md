# Self-Improvement Agent

The self-improvement agent is `thought_tube_self_improve`.

It converts product and system feedback into governed update packets. It does not deploy by default.

## Runtime Contract

- Normal assistant: `thought_tube_router`
- Self-improvement agent: `thought_tube_self_improve`
- Default authority: `propose`
- Production deploy authority: disabled

## Feedback Domains

- `ui_ux`
- `agent_behavior`
- `backend_setup`
- `tool_creation`
- `thought_pipeline_config`
- `bridge_work`
- `deployment_release`

## Required Flow

1. Create a `SystemImprovementPacket`.
2. Triage the packet into a workboard task.
3. Implement with tests.
4. Create a release candidate manifest.
5. Run the gate report.
6. Deploy only if gates pass and rollback exists.
7. Record post-deploy evidence.
