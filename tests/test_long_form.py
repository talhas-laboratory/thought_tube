import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import init_repo
from conversation_os.storage import write_json, write_jsonl
from conversation_os.thought_factory import build_thought_packets


REPO_ROOT = Path(__file__).resolve().parents[1]


class LongFormOrchestrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        for filename in [
            "TENETS.md",
            "AGENTS.md",
            "SESSION_PROTOCOL.md",
            "CONTEXT_ROUTING.md",
            "PRODUCT_THESIS.md",
            "pyproject.toml",
        ]:
            shutil.copy(REPO_ROOT / filename, self.root / filename)
        shutil.copytree(REPO_ROOT / "docs" / "research", self.root / "docs" / "research")
        init_repo(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _sample_packet(self) -> dict:
        return {
            "packet_id": "promotion-sample",
            "insight_id": "insight-sample",
            "candidate_title": "Protect The Signal Before You Explain It",
            "candidate_short_text": "Premature structure tends to flatten the live signal before it becomes usable.",
            "source_refs": [str((self.root / "source-a.md").resolve())],
            "source_item_ids": ["item-1"],
            "meta_refs": ["meta-1", "meta-2"],
            "shared_terms": ["signal", "structure", "review"],
            "shared_primitive_key": "cognitive_fidelity",
            "shared_primitive_label": "Cognitive fidelity",
            "review_status": "approved_for_surface",
            "evidence_status": "grounded",
            "confidence_score": 0.82,
            "relevance_score": 0.76,
            "novelty_score": 0.71,
            "what_changed": "The product becomes stronger when ambiguity survives long enough to reveal the real pattern.",
            "why_it_matters_now": "If structure lands too early, the result gets cleaner but less true to the underlying material.",
            "next_action": "Preserve ambiguity early, then commit structure only after the signal survives review.",
            "reasoning_pipeline": "cross_pollination_v1+thought_surfacing_v1",
            "unresolved_questions": [
                "How much ambiguity should remain before the user loses trust?",
                "Which structures are safe to harden automatically?",
            ],
        }

    def _sample_snippets(self) -> list[dict]:
        return [
            {
                "source_item_id": "item-1",
                "title": "Inner World Thesis",
                "source_type": "markdown",
                "source_ref": str((self.root / "source-a.md").resolve()),
                "excerpt": "The system should preserve ambiguity early and only crystallize structure after review.",
            },
            {
                "source_item_id": "item-2",
                "title": "Morning Batch Notes",
                "source_type": "markdown",
                "source_ref": str((self.root / "source-b.md").resolve()),
                "excerpt": "A bounded batch gives enough distance for judgment without turning the feed into noise.",
            },
        ]

    def test_build_long_form_article_emits_structured_payload(self) -> None:
        from conversation_os.long_form import build_long_form_article

        article = build_long_form_article(
            self.root,
            self._sample_packet(),
            self._sample_snippets(),
            "Protect The Signal Before You Explain It",
            "The live material gets weaker when the system decides what it means before the pattern has actually formed.",
        )

        self.assertEqual(article["profile"], "explainer_default")
        self.assertTrue(article["sections"])
        self.assertTrue(article["module_order"])
        self.assertEqual(article["sections"][0]["module_id"], "promise-frame")
        self.assertIn("tension-and-stakes", article["module_order"])
        self.assertIn("pattern-and-transfer", article["module_order"])
        self.assertTrue(article["markdown"].startswith("# Protect The Signal Before You Explain It\n"))
        self.assertIn("## The central tension", article["markdown"])
        self.assertIn("## What the material actually shows", article["markdown"])
        self.assertIn("## The reusable pattern", article["markdown"])
        self.assertIn("## What to do with it", article["markdown"])

    def test_runtime_config_can_disable_modules_without_code_changes(self) -> None:
        from conversation_os.long_form import build_long_form_article

        write_json(
            self.root / "product" / "inner_world_v1" / "config" / "long_form.json",
            {
                "profile": "explainer_default",
                "modules": {
                    "evidence-ladder": {"enabled": False},
                    "entry-vector": {"enabled": True, "weight": "heavy"},
                },
            },
        )

        article = build_long_form_article(
            self.root,
            self._sample_packet(),
            self._sample_snippets(),
            "Protect The Signal Before You Explain It",
            "The live material gets weaker when the system decides what it means before the pattern has actually formed.",
        )

        module_ids = [section["module_id"] for section in article["sections"]]
        self.assertIn("entry-vector", module_ids)
        self.assertNotIn("evidence-ladder", module_ids)
        self.assertNotIn("## What the material actually shows", article["markdown"])

    def test_build_thought_packets_persists_long_form_metadata(self) -> None:
        chunk_index_path = self.root / "product" / "inner_world_v1" / "data" / "chunk_index.jsonl"
        write_jsonl(
            chunk_index_path,
            [
                {
                    "source_item_id": "item-1",
                    "title": "Inner World Thesis",
                    "source_type": "markdown",
                    "source_ref": str((self.root / "source-a.md").resolve()),
                    "content": "The system should preserve ambiguity early and only crystallize structure after review.",
                }
            ],
        )

        packets = build_thought_packets(self.root, [self._sample_packet()], {})

        self.assertEqual(len(packets), 1)
        thought = packets[0]
        self.assertIn("article_markdown", thought)
        self.assertIn("article_sections", thought)
        self.assertIn("article_profile", thought)
        self.assertIn("article_module_order", thought)
        self.assertIn("article_config_snapshot", thought)
        self.assertTrue(thought["article_sections"])
        self.assertEqual(thought["article_profile"], "explainer_default")
        self.assertIn("tension-and-stakes", thought["article_module_order"])
        self.assertIn("## The central tension", thought["article_markdown"])

    def test_long_form_uses_full_source_content_not_preview_excerpt(self) -> None:
        from conversation_os.long_form import build_long_form_article

        full_text = (
            "Indirect effect on the soul: Because the rational soul is immaterial, celestial bodies could not touch it "
            "directly. But by shaping bodily temperament and social environment, they influenced the arena in which the "
            "soul develops, thus indirectly affecting one's spiritual path."
        )
        article = build_long_form_article(
            self.root,
            self._sample_packet(),
            [
                {
                    "source_item_id": "item-1",
                    "title": "Assistant · Indirect effect on the soul:Because the rational soul is immaterial…",
                    "full_title": "Indirect effect on the soul: Because the rational soul is immaterial",
                    "source_type": "markdown",
                    "source_ref": str((self.root / "source-a.md").resolve()),
                    "excerpt": "Indirect effect on the soul:Because the rational soul is immaterial, celestial bodies could not touch it directly. But by shaping bodily temperament and social environment, they i…",
                    "content": full_text,
                }
            ],
            "Protect The Signal Before You Explain It",
            "The live material gets weaker when the system decides what it means before the pattern has actually formed.",
        )

        self.assertIn("they influenced the arena in which the soul develops", article["markdown"])
        self.assertNotIn("they i…", article["markdown"])


if __name__ == "__main__":
    unittest.main()
