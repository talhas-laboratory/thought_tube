# Local Agent Boot

1. Read `docs/workspaces/WORKSPACE-AGENT-PROTOCOL.md`.
2. Read `docs/workspaces/shape-intelligence-population/derived/REMEDIATION_IMPLEMENTATION_PLAN.md` completely.
3. Read the remediation packet for the child workspace you own.
4. Pull Git, query live workspace context, and run projection check.
5. Select only a dependency-ready live task; do not implement later phases early.
6. Before code changes, refresh the repo overview and pass the engineering guard with the smallest plausible paths.
7. Test first for every observed bypass. Record commands, results, changed paths, residual risk, and commit SHA in the live task.
8. After each live mutation publish and check the projection, then commit intentionally and push.

Never import the cloud projection commit `cd8047dc3e`, trust model-supplied identity, store source text in evidence packets, let similarity decide meaning, reverse a rejection, or invent a canonical Shape store.
