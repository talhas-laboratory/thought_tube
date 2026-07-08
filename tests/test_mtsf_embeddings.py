import os
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import init_repo
from conversation_os.mtsf_embeddings import (
    build_entity_carrier_text,
    build_semantic_cluster_candidate_shapes,
    cosine_similarity,
    embed_entity_carriers,
    materialize_entity_embeddings,
)
from conversation_os.mtsf_extraction_skill import resolve_deep_extraction_draft
from conversation_os.storage import read_json

REPO_ROOT = Path(__file__).resolve().parents[1]


class MtsfEmbeddingsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        init_repo(self.root)
        docs_link = self.root / "docs"
        if docs_link.exists() or docs_link.is_symlink():
            if docs_link.is_symlink() or docs_link.is_file():
                docs_link.unlink()
            else:
                shutil.rmtree(docs_link)
        os.symlink(REPO_ROOT / "docs", docs_link, target_is_directory=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_entity_carrier_text_combines_identity_and_evidence(self) -> None:
        carrier = build_entity_carrier_text(
            {
                "name": "hallway",
                "stable_identity": ["liminal corridor"],
                "evidence": {"spans": ["empty hallway"]},
            }
        )
        self.assertIn("hallway", carrier)
        self.assertIn("liminal corridor", carrier)
        self.assertIn("empty hallway", carrier)

    def test_materialize_entity_embeddings_writes_artifact(self) -> None:
        draft = {
            "draft_id": "mtsf-draft-test",
            "entities": [
                {
                    "proposed_id": "entity-hallway",
                    "name": "hallway",
                    "stable_identity": ["liminal corridor"],
                    "evidence": {"spans": ["empty hallway"]},
                }
            ],
        }
        result = materialize_entity_embeddings(self.root, "embed-session", draft)
        artifact_path = Path(result["artifact_refs"]["mtsf_entity_embeddings"])
        self.assertTrue(artifact_path.exists())
        payload = read_json(artifact_path, default={})
        self.assertGreaterEqual(len(payload.get("entities", [])), 1)
        row = payload["entities"][0]
        self.assertEqual(row["entity_id"], "entity-hallway")
        self.assertIn("vector", row)
        self.assertIn("source_text", row)

    def test_semantic_cluster_shapes_include_provenance(self) -> None:
        entities = [
            {
                "proposed_id": "entity-hallway",
                "name": "hallway",
                "stable_identity": ["liminal corridor"],
                "evidence": {"spans": ["empty hallway"]},
            },
            {
                "proposed_id": "entity-fluorescent-light",
                "name": "fluorescent light",
                "stable_identity": ["cold overhead illumination"],
                "evidence": {"spans": ["cold fluorescent light"]},
            },
        ]
        relations = [
            {
                "source_ref": "entity-hallway",
                "target_ref": "entity-fluorescent-light",
                "level": "entity_entity",
                "relation_type": "evokes",
                "primitive": "resembles",
            }
        ]
        shapes = build_semantic_cluster_candidate_shapes(
            root=self.root,
            text="An empty hallway with cold fluorescent light feels peaceful but also watched.",
            entities=entities,
            relations=relations,
            qualities=[],
            existing_shapes=[],
        )
        self.assertTrue(any(shape.get("provenance", {}).get("source") == "semantic_cluster" for shape in shapes))

    def test_hallway_fixture_produces_entities_and_cluster_shape(self) -> None:
        events = [
            {
                "actor": "user",
                "content": "An empty hallway with cold fluorescent light feels peaceful but also watched.",
            }
        ]
        manifest = {"title": "hallway", "source_type": "text", "domains": []}
        result = resolve_deep_extraction_draft(
            self.root,
            session_id="hallway-session",
            events=events,
            manifest=manifest,
            llm_preference="auto",
        )
        draft = result["draft"]
        names = " ".join(row.get("name", "") for row in draft.get("entities", [])).lower()
        self.assertIn("hallway", names)
        self.assertGreaterEqual(len(draft.get("entities", [])), 2)
        self.assertGreaterEqual(len(draft.get("relations", [])), 1)
        self.assertTrue(
            any(
                shape.get("provenance", {}).get("source") == "semantic_cluster"
                for shape in draft.get("candidate_shapes", [])
            )
        )

    def test_bridge_pair_has_high_cosine(self) -> None:
        left = embed_entity_carriers(
            self.root,
            "left",
            {
                "draft_id": "d1",
                "entities": [
                    {
                        "proposed_id": "entity-subconscious-architecture",
                        "name": "subconscious architecture",
                        "stable_identity": ["built environment"],
                        "evidence": {"spans": ["subconscious maze"]},
                    }
                ],
            },
        )
        right = embed_entity_carriers(
            self.root,
            "right",
            {
                "draft_id": "d2",
                "entities": [
                    {
                        "proposed_id": "entity-context-field",
                        "name": "context field",
                        "stable_identity": ["contextual conditioning"],
                        "evidence": {"spans": ["context field"]},
                    }
                ],
            },
        )
        score = cosine_similarity(
            left["entities"][0]["vector"],
            right["entities"][0]["vector"],
        )
        self.assertGreaterEqual(score, 0.72)


if __name__ == "__main__":
    unittest.main()
