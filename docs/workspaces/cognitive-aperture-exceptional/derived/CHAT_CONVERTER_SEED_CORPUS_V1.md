# Chat Converter seed corpus v1

## Purpose

Controlled, provenance-preserving seed corpus for the Cognitive Aperture Stage A retrieval baseline. It is deliberately small and varied; it is not a claim that the whole Chat Converter archive is indexed.

## Corpus contract

- Corpus id: `cognitive_aperture_chat_converter_v1`
- Source family/type: `chat_converter` / `chat_converter_conversation`
- Evidence tier: `T2` (conversation export, not canonical doctrine)
- Sources: 20; chunks: 6,611; raw source bytes: 1,119,260
- Original root: `/home/talha/apps/chat_converter/output`
- Each runtime record retains its remote source reference, SSH source URL, verification timestamp, size, and full SHA-256 checksum.

## Sources

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| `2026-01-21_how-can-i-get-my-model-to-think-like-me.md` | 77,084 | `cfb038710216a77d2c266801804dc169a77e0c2fcdf8ce77e6e0b6bc5c04b11a` |
| `2026-01-21_system-prompt-framework-discussion.md` | 49,082 | `4b420c265818db17529d2cd39980973a28d7e51329eb3d1358576fcf7d37fce8` |
| `2026-02-03_understanding-the-nature-of-thought.md` | 37,269 | `8171d069e8df1f4c93650991daf69b07d896f3ff5aa8e2444e359782e1faa837` |
| `2026-02-07_mapping-the-mind-for-agentic-systems.md` | 18,836 | `82ffa4d906cd1500257998d5bb352cfa22316b4455e9cced333839d49b4f3674` |
| `2026-02-09_building-blocks.md` | 102,805 | `7ef537fe99ce8ce085fc763bc6931a346f13e7d4df6bbf34006488b386968031` |
| `2026-02-10_agentic-hybrid-rag-for-information-extraction.md` | 34,948 | `8abc8fb28a52c1845e5ddd4ec2f4a33f333fcf52cfac2ecb02a135949dfe9db4` |
| `2026-02-10_empathy-agents---building-block-architecture.md` | 64,877 | `2d465d34598f3602f4878b0d4a9d380bf3a9fbd270ef91847c10969eda2fd6c5` |
| `2026-02-11_ai-agentic-harness-explained.md` | 41,292 | `df831738ebaa397640b6f3ef7161663cb021f3cdb3430477ee96349d3c7b18b5` |
| `2026-02-13_codebases-relational-or-graph.md` | 59,135 | `426d6673f39d0dc3f88d062593787ab4fe46ef7b890fca260cf250abe6697f74` |
| `2026-02-17_graph-db-for-debugging-complex-systems.md` | 19,221 | `d8a341a5f0224f32a9c823e1172912bdd6988c06131a9a098d9403856714342a` |
| `2026-03-20_chatgpt---thought-tube-overview.md` | 13,852 | `1f615549d171b3bc4ea809c607467c0e585a9ba919189ad8de1dd53cf4eae0c2` |
| `2026-03-21_brain-dump.md` | 131,971 | `5341d33b4d91acba4dc9b9b8be7bbb8445ebe4bf0d1c621ba3424e8ffeff719d` |
| `2026-03-25_ai-reasoning-process-components-frameworks.md` | 40,497 | `480d07a5cea8be496c764a7c88e27c9c8d571047938b66518dca993d37aeb5e9` |
| `2026-03-29_chatgpt---cognitive-trace-concept.md` | 12,878 | `3a4d5fac3c04693bcfe8ae8dc39fbd855993bf84dad9649f15705aa6dce23c32` |
| `2026-04-02_chatgpt---behavioral-archetypes-overview.md` | 77,149 | `8da19893024a38492dbb5216f794c55da73544c0ab7c3950be1d8cec103af98e` |
| `2026-05-05_chatgpt---read_semantic-context-infrastructure.md` | 87,976 | `d46502ee8ee566d931dddfbf0b7a20d3e2c36f59ebba4541a4d900b4c675bc47` |
| `2026-05-05_chatgpt---report-summary-architecture.md` | 187,687 | `98bde1132653fe937b7ba225c9ea53fc96b690312edf0c010b150d9b932f7a16` |
| `2026-05-23_chatgpt---context-in-embedding-spaces.md` | 31,295 | `696846984fb2e73039fe8a9dcac51f23e772f0b2e2f0dae6739b374c483a314c` |
| `2026-06-06_chatgpt---semantic-interfaces-in-reasoning.md` | 22,956 | `bec1b8cea81d5cf4a57b36780fa8b1931a5039bfd383e6782ff0bbd4b581ccaf` |
| `2026-06-26_chatgpt---implicit-semantic-composition.md` | 8,450 | `975a5943ce57b16f0d2118bb375fcec62f02d0ba9071b62b1bc6ce9eeff29bae` |

## Baseline results

| Probe | Expected result | Result |
| --- | --- | --- |
| Exact file: `agentic-hybrid-rag-for-information-extraction` | exact source record | pass |
| Retrieval/information-extraction query | hybrid-RAG document at rank 1 | pass |
| Semantic-context/embedding-space query | embedding-space document at rank 1 | pass |
| Out-of-domain: quantum gardening on extraterrestrial crops | no result | pass |
| Structural: recursive self-model / agent memory | mapping-the-mind evidence | pass (lexical baseline) |

## Remaining evaluation suite

Before enforcement, test: model-imitation; system-prompt framework; nature of thought; biological-to-agent memory mapping; modular building blocks; hybrid retrieval and graph traversal; empathy-agent architecture; generative harnesses; relational codebases; graph debugging; Thought Tube; reasoning frameworks; cognitive traces; behavioral archetypes; semantic-context infrastructure; report architecture; context in embedding spaces; semantic interfaces; implicit composition; and one out-of-domain `NO_HITS` query.

## Known limits

This is a valid chunked, provenance-preserving lexical baseline. It is **not** yet a certified semantic-embedding or canonical-Shape corpus: the current runtime has no materialized embedding index or canonical Shape profiles for these records. CAE-013 must run the full probe suite; CAE-014 must wire readiness/read ports; CAE-006B must evaluate Shape/AntiMatch behavior before aperture enforcement.
