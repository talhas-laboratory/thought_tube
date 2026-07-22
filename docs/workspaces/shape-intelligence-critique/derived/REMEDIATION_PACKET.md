# Critique and Synthesis Remediation Packet

Authority: [central remediation plan](../../shape-intelligence-population/derived/REMEDIATION_IMPLEMENTATION_PLAN.md), especially Phases 4, 5, and 8.

## Required outcome

After a provisional candidate exists, retrieve bounded neighboring Shapes, then use independent intelligence to criticize and synthesize. Similarity proposes comparison material; it never determines equivalence, merge, or promotion.

## Owned edit surface

- `src/conversation_os/shape_population/comparison.py`
- critic/synthesizer portions of `model_gateway.py` and `orchestrator.py`
- canonical read adapter use through `shape_projection_reader.py`
- critic/synthesizer OpenClaw configs and provisioning
- comparison, critique, and continuity tests.

## Ordered implementation

1. Delete first-N lexical scanning as the production comparison path. Define a `ComparisonRetriever` port returning ranked neighbors with score components, profile/version, provenance, and bounded excerpts.
2. Query only after the candidate is durably accepted. Search candidate title, description, dimensions, relationships, and evidence-derived concepts against the canonical knowledge-ocean read boundary.
3. Enforce top-K, per-neighbor, and total context budgets. Stable tie-breaking must make identical index snapshots reproducible.
4. Provision critic and synthesizer as distinct least-privilege OpenClaw identities. Neither may request/apply promotion.
5. Critic must explicitly assess support, contradictions, missing dimensions, novelty, possible duplicate/merge/split, and uncertainty. It cites candidate evidence and comparison provenance separately.
6. Synthesizer sees proposal, critique, and disagreements. It may revise, split, retain alternatives, or recommend rejection; it must not erase dissent or rewrite evidence provenance.
7. Persist the retrieved comparison set and its index/profile version so later audit does not depend on a changed index.

## Semantic test dataset

Include at minimum: lexical similarity but different meaning; low lexical overlap but same Shape; one source containing multiple Shapes; near duplicate needing merge; broad Shape needing split; contradiction; temporal evolution; cross-dimensional relation; no useful neighbor; adversarial neighbor text.

For retrieval use deterministic relevance labels and metrics such as recall@K plus false-neighbor rate. For critique use a versioned rubric: evidence faithfulness, independence, contradiction detection, dimension coverage, uncertainty preservation, and actionable synthesis. A single model’s unstructured opinion is not a gate.

Run:

```bash
pytest -q tests/test_shape_comparison.py tests/test_shape_critique.py
pytest -q tests/test_shape_semantic_quality.py -k 'comparison or critic or synthesizer'
pytest -q tests/test_shape_continuity.py -k 'proposal_to_critique or critique_to_synthesis'
```

## Evidence required in the live task

Retriever contract and profile; K/budget policy; dataset version; recall and false-neighbor results; independent identity routing; disagreement-preservation examples; full-suite impact and residual index limitations.

## Exit gate

No comparison runs before candidate creation; no retrieval score is converted into a semantic decision; real independent identities execute critique/synthesis; and proposal meaning, evidence, uncertainty, and dissent remain continuous.
