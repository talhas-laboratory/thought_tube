# Inner World Releases

This directory stores release manifests, gate reports, and rollback plans.

Each release directory must include:

- `manifest.json`
- `gate_report.json`
- `rollback_plan.json`

Production deployment should point to one exact release id. Rollback restores the previous release manifest and its artifact/config snapshot.
