# OpenClaw Shape Intelligence Readiness

## Current baseline

Local OpenClaw gateway health was confirmed. A probe through the existing `thought_tube_router` produced useful interpretative hypotheses, evidence, counter-hypotheses, and uncertainty, but returned fenced JSON despite a strict-output request and operated with a broad general-purpose prompt/tool surface. It is a capability signal, not a production population identity.

## Production requirements

1. Dedicated proposer, critic, and synthesizer identities with least-privilege tools.
2. Bounded injection-safe evidence packets; source text is data, never instruction.
3. Strict structured candidate/evaluation output with parser rejection or repair policy.
4. Independent critique; proposer and critic cannot be the same identity/run.
5. Deterministic validation of schema, evidence refs, status, authorization, and policy.
6. Durable idempotent jobs, bounded retries/costs, and receipts containing prompt/model/tool versions.
7. Asynchronous operation isolated from ordinary ingestion and retrieval.
8. No automatic canonical promotion; a designated agent may recommend and a human must approve.
9. Golden, adversarial, semantic-quality, and continuity evaluations.
10. Explicit privacy, retention, observability, and operations contracts.

## Readiness conclusion

OpenClaw supplies the intelligence substrate. The remaining work is to shape dedicated identities and connect them only to the three population-agent tools: `submit_candidate`, `find_comparison_candidates`, and `submit_evaluation`.
