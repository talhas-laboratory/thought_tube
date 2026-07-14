# Meta Agent

This directory holds repo-local contracts for the Telegram-first Inner Space meta agent.

It stores schemas and versioned policy, not raw Telegram traffic.

Raw inbox, outbox, approval queues, and session logs belong in the OpenClaw meta workspace on the server.

Deploy evidence for approved releases is written under `product/inner_world_v1/releases/<release_id>/`, including `manifest.json`, `gate_report.json`, `rollback_plan.json`, and `post_deploy_smoke.json`.
