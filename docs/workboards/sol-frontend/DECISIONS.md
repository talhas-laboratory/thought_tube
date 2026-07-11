# Decisions — SOL Frontend

Record durable frontend decisions here. Each entry should cite pillar(s).

## Template

```markdown
### DEC-NNN — Title

- **Date:**
- **Pillars:**
- **Decision:**
- **Rejects:**
- **Rollback:**
- **Sources:**
```

---

### DEC-001 — Eight binding pillars adopted as workspace decision spine

- **Date:** 2026-06-27
- **Pillars:** all (P1–P8)
- **Decision:** All frontend work in `sol-frontend` flows from `PILLARS.md`. Research from chat converter corpus is synthesized into eight pillars, not ad hoc feature lists.
- **Rejects:** Starting implementation without pillar mapping; treating feed, mobile, and miniapp as unrelated UIs.
- **Rollback:** Amend `PILLARS.md` with explicit decision record; never silent drift.
- **Sources:** `mobile_artifacts/2026-06-27/frontend-chat-converter-research-brief.md`; chat converter tier-1 conversations on server.
