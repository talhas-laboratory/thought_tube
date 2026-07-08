# Shape Utility Eval Suite

End-to-end tests for whether MTSF **shape mechanisms** produce useful structure in real-world inputs.

## Why this suite exists

The `semantic-shape-extraction` evals only **validate pre-written reference drafts**. They do not run the pipeline on live text. Pilot activation replay injects synthetic `ActivationContext` objects. Neither proves real-world utility.

This suite runs the **actual extraction + activation path** and scores outcomes against falsifiable expectations.

## Utility criteria (scoring rubric)

| Criterion | Question | Pass signal |
|-----------|----------|-------------|
| **Discriminability** | Do different inputs produce different shape signatures? | Paired inputs share <50% entity/shape overlap |
| **Grounding** | Are shapes backed by evidence spans from source text? | ≥1 evidence span per entity; no forbidden fragments |
| **Honesty** | Does the system avoid over-interpretation? | Negative controls stay sparse; forbidden shapes absent |
| **Relational depth** | Are candidate shapes relational, not tag bags? | `relational_configuration` present; ≥1 relation when entities≥2 |
| **Activation signal** | Does activation discriminate session modes? | Triangulation text → distinct context-field shapes |
| **Cross-register** | Does non-pilot vocabulary still produce structure? | Backrooms/hallway inputs get entities without pilot-only terms |
| **Downstream hook** | Can results feed graph/index? | validation_ok + materialize-ready entity count ≥ min |

## Tiers

| Tier | ID prefix | What runs |
|------|-----------|-----------|
| T1 | `eval-utility-extract-*` | `resolve_deep_extraction_draft` on raw text |
| T2 | `eval-utility-activation-*` | ingest + `materialize_session_mtsf` on event substrate |
| T3 | `eval-utility-pair-*` | two inputs; discrimination expectations |
| T4 | `eval-utility-negative-*` | must stay sparse / must not fire pilot shapes |

## Running

```bash
python3 tools/conversation_os.py mtsf run-shape-utility-evals
python3 tools/conversation_os.py mtsf run-shape-utility-evals --llm auto
```

## Interpreting results

- **High pass on T1/T4 only** → extraction scaffold works; activation/shapes are decorative
- **High pass on T2** → activation rules fire on real inferred signals (not just fixtures)
- **T3 failures** → shapes collapse everything into same pilot vocabulary (not useful)
- **Stencil match rate near zero on non-pilot inputs** → seed library too narrow (expected today)
