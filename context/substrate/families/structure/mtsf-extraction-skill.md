# MTSF Deep Extraction Skill

`llm_preference` resolution order:

- `auto` — OpenClaw semantic extraction, then open evidence extractor (default)
- `agent` — Pilot 002 phrase-library replay for CI (`mtsf_ingest.agent_skill`)
- `off` — thin heuristic only
- `force` — OpenClaw only
