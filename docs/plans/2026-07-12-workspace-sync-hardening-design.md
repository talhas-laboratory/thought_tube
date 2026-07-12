# Workspace Sync Hardening Design

## Decision

Keep the live workspace service as the coordination authority and make its
revision-sensitive read endpoints refresh the repository observation before
assembling state. The refresh is serialized because the service is threaded and
the observer appends an event only when the repository fingerprint changes.

Continuity markdown remains a read-only projection. Its renderer accepts both
the current normalized `task_id` field and the legacy `work_item_id` field so a
projection cannot silently lose the focus task during a schema transition.

## Scope

- `context` refreshes the repository snapshot before returning the agent packet.
- `continuity` refreshes before exporting the bounded handoff projection.
- `gate` refreshes before evaluating repository freshness.
- Deployments write the published Git `HEAD` into the service environment so
  rsync-only remote projections remain revision-bound without a `.git` folder.
- Deployments include the canonical continuity projection so remote health
  checks can verify the same handoff artifact that Cursor reads from Git.
- Observation failures remain best-effort for non-git fixtures and read-only
  deployments; those callers retain the existing unobserved signal.
- No raw event logs or semantic framework sources are changed.

## Verification

- Renderer regression test using a legacy `work_item_id` focus shape.
- Service integration test proving a git `HEAD` revision appears in context
  without a separate observer process.
- Existing workspace continuity, observer, service, and catalog test suites.

## Residual risk

The engineering guard/index on the cloud-derived branch does not yet contain
module manifests for the existing Conversation OS modules. This change keeps
the edit surface to the established workspace owners and records the index
defect for a separate substrate-maintenance task.
