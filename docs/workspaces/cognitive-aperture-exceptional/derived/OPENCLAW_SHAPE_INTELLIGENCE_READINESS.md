# OpenClaw Shape Intelligence — Requirements and Readiness Baseline

**Status:** architecture baseline; not a deployment approval  
**Recorded:** 2026-07-20  
**Scope:** interpretative Shape population over bounded evidence  
**Authority:** this document defines the intelligence contract. The live workspace API remains authoritative for task status and promotion decisions.

## Decision

The existing OpenClaw installation provides usable intelligence for Shape interpretation. It must **not** be used unchanged as the Shape population agent.

Keep `thought_tube_router` as the conversational Bridge agent. Shape population needs separate, least-privilege OpenClaw identities and a deterministic workflow boundary that treats all model output as an untrusted proposal.

## What the intelligence must do

The intelligence layer interprets bounded evidence; it does not own the knowledge ocean or promote canonical truth. For every eligible packet it must be able to:

1. State a proposed system boundary, scale, entities, relations, dynamics, constraints, absences, and affordances.
2. Produce candidate Shapes with confidence and a reasoned rationale.
3. Cite only supplied evidence spans and identify material uncertainty.
4. Offer competing explanations and disconfirming evidence.
5. Distinguish a local observation, a recurrent mechanism, and a framework-level Shape.
6. Respect branch, scope, sensitivity, and disclosure-grant boundaries.
7. Never claim canonical validation or write/promote a Shape directly.

## Non-negotiable requirements

| ID | Requirement | Passing evidence |
| --- | --- | --- |
| INT-01 | Dedicated, least-privilege identity | `shape_population_proposer` has a minimal workspace, no unrestricted shell/browser/write tools, and no delivery binding. |
| INT-02 | Bounded, injection-safe evidence | Agent receives a typed packet of allowed spans and treats source text as data, never as instructions. |
| INT-03 | Strict candidate schema | Output validates against `ShapeCandidateProposal`; fences and prose are rejected, never guessed into validity. |
| INT-04 | Interpretative adequacy | Golden cases demonstrate correct boundary, dynamics, uncertainty, and alternatives—not keyword matching. |
| INT-05 | Independent critique | A separately prompted critic returns supports, objections, counterexamples, and accept/revise/reject. |
| INT-06 | Deterministic enforcement | Code validates provenance, grant, branch/scope, evidence coverage, budgets, duplication, and AntiMatch conflicts before storage. |
| INT-07 | Durable, idempotent jobs | Every job records source revision, workflow version, model trace, idempotency key, retry state, and bounded failure result. |
| INT-08 | Asynchronous population | Ingestion completes first; interpretation is queued, deduplicated, throttled, and never blocks new content. |
| INT-09 | Governed promotion | Candidate creation, merge, rejection, and canonical promotion are distinct states; only the canonical owner promotes. |
| INT-10 | Evaluation and observability | Gold/adversarial cases, calibration, schema rate, critic agreement, latency, cost, and human-review outcomes are recorded. |
| INT-11 | Privacy and isolation | Incognito/restricted input creates no durable Shape job; policy-safe receipts are retained. |
| INT-12 | Explicit operations | Approved model, timeout, concurrency, fallback, and rollback are configured and tested. A failure never broadens evidence. |

## Required proposal contract

The proposer returns a versioned JSON object with at least:

```json
{
  "status": "candidate",
  "candidate_shapes": [{"name": "string", "rationale": "string", "confidence": 0.0, "maturity": "candidate"}],
  "system_boundary": "string",
  "scale": "local|interaction|system|ecosystem|unknown",
  "entities": [],
  "relations": [],
  "dynamics": [],
  "constraints": [],
  "absences": [],
  "affordances": [],
  "evidence_spans": [],
  "alternative_interpretations": [],
  "disconfirming_evidence_needed": [],
  "uncertainty": "string"
}
```

The deterministic service, not the model, attaches source IDs, hashes, branch/scope, grant, corpus revision, job identifiers, and receipts.

## Current OpenClaw baseline

### What was tested

- Local OpenClaw version: `2026.2.25`.
- Local gateway health: `ok`.
- Registered dedicated Bridge agent: `thought_tube_router`.
- Configured Bridge model: `moonshot/kimi-k2.5`; mode: `agent`; thinking: `low`; timeout: 25 seconds; delivery: disabled.
- A non-delivered Shape-candidate probe completed successfully in 20.575 seconds.

The bounded synthetic probe asked for candidate Shapes, a system boundary, dynamics, direct evidence spans, counter-hypotheses, and uncertainty. It produced two useful candidate hypotheses, a defensible boundary, a reinforcing feedback-loop interpretation, evidence quotations, counter-hypotheses, and explicit uncertainty.

This proves basic interpretative capability only. It does not certify the workflow.

### Assessment

| Requirement | Status | Evidence / gap |
| --- | --- | --- |
| INT-01 | **fail** | Router is dedicated by name but shares a general workspace, has broad tool access, and reported sandbox mode is off. |
| INT-02 | **fail** | No typed Shape evidence packet or explicit source-as-data/prompt-injection boundary exists. |
| INT-03 | **fail** | Despite an only-JSON instruction, the probe returned JSON inside a Markdown fence. Current Bridge invocation extracts free text and has no Shape schema validator. |
| INT-04 | **provisional pass** | Probe supplied candidates, dynamics, alternatives, and uncertainty. Corpus-backed gold cases are still absent. |
| INT-05 | **fail** | No independent critic identity or critique stage exists. |
| INT-06 | **partial** | Bridge has budgets/isolation controls, but no Shape-population provenance, AntiMatch, or candidate-validation gate. |
| INT-07 | **fail** | OpenClaw sessions persist, but no population-job state, source revision, idempotency key, or retry contract exists. |
| INT-08 | **fail** | No queue or asynchronous Shape population worker exists. |
| INT-09 | **partial** | Legacy Shape reads forbid promotion, but no candidate-review-promotion workflow exists. |
| INT-10 | **fail** | No Shape interpretation evaluation suite, calibration report, or review-quality metrics exist. |
| INT-11 | **partial** | Bridge has incognito concepts, but Shape-job creation and receipt policy are unimplemented. |
| INT-12 | **partial** | Model, thinking, timeout, and heuristic fallback are configured; safe Shape-job fallback semantics are absent. |

## Why not reuse the router unchanged

The probe used roughly 48k effective prompt tokens because general workspace instructions, skills, and tool schemas were injected. That is too broad and expensive for repeated population jobs. It also exposes unrelated tools with sandboxing disabled.

A population agent needs a small immutable instruction set, a narrow read-only toolset, no delivery channel, no direct write capability, and a compact evidence packet. The agent proposes; deterministic code validates and persists.

## Target OpenClaw topology

| Identity | Purpose | Allowed | Forbidden |
| --- | --- | --- | --- |
| `shape_population_proposer` | Evidence-bound candidate proposals | Receive packet; return schema-valid JSON | shell, browser, arbitrary filesystem, messaging, writes, promotion |
| `shape_population_critic` | Challenge boundary, analogy, scale, and evidence | Receive proposal plus identical packet; return JSON critique | writes, messaging, promotion, unrelated retrieval |
| `shape_population_synthesizer` | Compare selected candidates across independent sources | Read explicitly selected candidate set; recommend merge/review | canonical promotion, global scans, source mutation |

All may initially use the same approved model. Independence comes from identity, prompt, bounded input, tools, and audit trail—not merely from choosing different models.

## Minimum workflow

1. Ingestion writes source and retrieval projections normally.
2. A deterministic eligibility gate rejects boilerplate, duplicates, restricted content, and low-signal fragments.
3. An evidence assembler creates a bounded packet: source revision, spans, metadata, same-scope candidates, relevant AntiMatches, and grant.
4. The proposer returns a schema-valid candidate or `abstain`.
5. Deterministic validation rejects unsupported quotes, invalid provenance, out-of-scope claims, duplicate jobs, and policy violations.
6. The critic challenges retained proposals; code records the critique.
7. A candidate is retained, revised, rejected, or queued for cross-source synthesis. No step promotes it.
8. Only a reviewed canonical-owner action can promote a Shape.

## First implementation slice

1. Define `ShapeCandidateProposal` and `ShapeCritique` contracts with JSON-schema tests.
2. Provision `shape_population_proposer` with a minimal OpenClaw workspace and no mutation tools.
3. Implement one deterministic population-job record and one bounded evidence-packet builder.
4. Invoke the proposer asynchronously for an approved fixture corpus.
5. Validate strictly; reject fenced/non-JSON output rather than repairing by guesswork.
6. Add the critic only after proposer output is consistently schema-valid.
7. Publish gold and adversarial evaluation cases before processing the wider ocean.

## Approval gate before broad population

- 100% schema-valid output on the approved fixture suite;
- no evidence quote outside the packet;
- explicit abstention for insufficient evidence;
- no durable job for incognito/restricted source;
- critic catches agreed false analogies and known AntiMatches;
- deterministic retries never duplicate candidate records;
- selected cost, latency, and concurrency budgets pass;
- human review can approve, reject, or request revision without changing source truth;
- the applicable release gate is green.

## Relationship to Cognitive Aperture remediation

This workflow replaces the current primarily deterministic legacy Shape extraction as the producer of new Shape candidates. Candidate retrieval/ranking may consume only proposals that pass this contract; it remains a separate cutover from the Bridge/Holodeck disclosure-service release.
