import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import init_repo, session_close, session_start
from conversation_os.mtsf_agent_extractor import build_agent_skill_extraction_draft
from conversation_os.mtsf_extraction_skill import (
    build_deep_extraction_draft_heuristic,
    build_skill_input_envelope,
    parse_extraction_draft_from_text,
    resolve_deep_extraction_draft,
)
from conversation_os.mtsf_ingest import build_fast_extraction_draft, materialize_session_mtsf_ingest
from conversation_os.storage import read_json

REPO_ROOT = Path(__file__).resolve().parents[1]

TRIANGULATION_EVENTS = [
    {
        "actor": "user",
        "content": (
            "Explain how the same query would be processed without any prior context, "
            "with relevant prior context, and with unrelated prior context in latent topology."
        ),
    }
]
MANIFEST = {
    "title": "Topology import",
    "source_type": "imported_transcript",
    "domains": ["research"],
}

PILOT_LIKE_TEXT = """
Agents move through a pre-defined, high-dimensional latent manifold. The latent space itself is static
after training. The path is a trajectory on a high-dimensional landscape as hidden states move through
successive layers. Context from previous runs acts as a coordinate shift — a contextual start with KV cache
versus a cold start without prior context. Context warps the effective topology and steers the inference path.
Explain how the same query would be processed without any prior context, with relevant prior context, and
with unrelated prior context. Each concept is a bundle of fibers — independent meaning dimensions.
The thought ocean is a well organized ocean of users thoughts and ideas. Relational stencils capture
directed relational topology — the verbs of force. Entities interact through relationships in a
dynamic state-space entity-relationship-state model. The synthetic subconscious performs spreading
activation and background cross-pollination across the library. The symmetry engine finds structural
isomorphs via symmetric match and antisymmetric shadow via opposite direction and via negativa.
An aha moment is a topological bridge. The system hardens the idea through negative inference.
"""


class MtsfExtractionSkillTestCase(unittest.TestCase):
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

    def test_build_skill_input_envelope(self) -> None:
        envelope = build_skill_input_envelope(
            session_id="sess-deep",
            events=TRIANGULATION_EVENTS,
            manifest=MANIFEST,
            raw_content=TRIANGULATION_EVENTS[0]["content"],
        )
        self.assertEqual(envelope["capture_mode"], "deep")
        self.assertEqual(envelope["session_id"], "sess-deep")
        self.assertIn("skill_refs", envelope)

    def test_deep_heuristic_includes_relations_and_quality_roles(self) -> None:
        draft = build_deep_extraction_draft_heuristic(
            session_id="sess-deep",
            events=TRIANGULATION_EVENTS,
            manifest=MANIFEST,
        )
        self.assertEqual(draft["capture_mode"], "deep")
        self.assertGreaterEqual(len(draft["relations"]), 1)
        self.assertGreaterEqual(len(draft["quality_roles"]), 1)
        self.assertIn("relations", draft["provenance"]["stages_completed"])
        self.assertEqual(draft["provenance"]["model_id"], "mtsf_ingest.deep_heuristic")

    def test_resolve_deep_extraction_falls_back_without_llm(self) -> None:
        result = resolve_deep_extraction_draft(
            self.root,
            session_id="sess-deep",
            events=TRIANGULATION_EVENTS,
            manifest=MANIFEST,
            llm_preference="off",
        )
        self.assertEqual(result["source"], "deep_heuristic")
        self.assertIn("mtsf_skill_input", result["artifact_refs"])
        self.assertGreaterEqual(len(result["draft"]["relations"]), 1)

    def test_resolve_deep_extraction_uses_agent_skill_by_default(self) -> None:
        events = [{"actor": "user", "content": PILOT_LIKE_TEXT}]
        result = resolve_deep_extraction_draft(
            self.root,
            session_id="sess-agent",
            events=events,
            manifest=MANIFEST,
        )
        self.assertEqual(result["source"], "agent_skill")
        self.assertEqual(result["draft"]["provenance"]["model_id"], "mtsf_ingest.agent_skill")
        self.assertGreaterEqual(len(result["draft"]["entities"]), 8)
        self.assertGreaterEqual(len(result["draft"]["relations"]), 5)
        self.assertGreaterEqual(len(result["draft"]["stencil_drafts"]), 3)

    def test_agent_skill_extractor_detects_pilot_entities(self) -> None:
        draft = build_agent_skill_extraction_draft(
            session_id="pilot-agent-test",
            events=[{"actor": "user", "content": PILOT_LIKE_TEXT}],
            manifest=MANIFEST,
            raw_content=PILOT_LIKE_TEXT,
        )
        entity_ids = {row["proposed_id"] for row in draft["entities"]}
        self.assertIn("entity-latent-manifold", entity_ids)
        self.assertIn("entity-thought-ocean", entity_ids)
        self.assertIn("entity-symmetry-engine", entity_ids)
        self.assertIn("entity-synthetic-subconscious", entity_ids)
        self.assertIn("entity-hardened-idea", entity_ids)
        self.assertEqual(draft["capture_mode"], "deep")
        self.assertGreaterEqual(len(draft["stencil_drafts"]), 3)

    def test_parse_extraction_draft_from_reference_fixture(self) -> None:
        draft_path = (
            REPO_ROOT
            / "docs/frameworks/metaphysical-thought-space/evals/semantic-shape-extraction/drafts/latent-triangulation.reference.json"
        )
        reference = json.loads(draft_path.read_text(encoding="utf-8"))
        envelope = build_skill_input_envelope(
            session_id="parse-test",
            events=TRIANGULATION_EVENTS,
            manifest=MANIFEST,
            raw_content=reference["raw_content"],
        )
        parsed = parse_extraction_draft_from_text(
            self.root,
            json.dumps(reference),
            session_id="parse-test",
            envelope=envelope,
        )
        self.assertEqual(parsed["capture_mode"], "deep")
        self.assertGreaterEqual(len(parsed["stencil_drafts"]), 1)

    def test_session_close_deep_mode_materializes_skill_input(self) -> None:
        session_id = "deep-close-test"
        session_start(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": session_id,
                    "title": "Deep topology import",
                    "participants": "user,assistant",
                    "source_type": "imported_transcript",
                    "domains": "research,topology",
                },
            )(),
        )
        from conversation_os.cli import session_append

        session_append(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": session_id,
                    "actor": "user",
                    "kind": "request",
                    "content": TRIANGULATION_EVENTS[0]["content"] + " across symmetry.",
                    "attachments": "",
                    "tags": "",
                    "source_ref": None,
                },
            )(),
        )
        result = session_close(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": session_id,
                    "task_id": None,
                    "request": None,
                    "task_type": None,
                    "mtsf_mode": "deep",
                    "mtsf_llm": "off",
                },
            )(),
        )
        self.assertEqual(result["mtsf_ingest"]["mtsf_ingest"], "completed")
        self.assertEqual(result["mtsf_ingest"]["capture_mode"], "deep")
        self.assertEqual(result["mtsf_ingest"]["extraction_source"], "deep_heuristic")
        draft = read_json(self.root / "memory" / "sessions" / session_id / "mtsf" / "extraction_draft.json")
        self.assertEqual(draft["capture_mode"], "deep")
        self.assertGreaterEqual(len(draft["relations"]), 1)
        self.assertTrue((self.root / "memory" / "sessions" / session_id / "mtsf" / "skill_input.json").exists())

    def test_deep_heuristic_is_richer_than_fast(self) -> None:
        fast = build_fast_extraction_draft(
            session_id="sess-compare",
            events=TRIANGULATION_EVENTS,
            manifest=MANIFEST,
        )
        deep = build_deep_extraction_draft_heuristic(
            session_id="sess-compare",
            events=TRIANGULATION_EVENTS,
            manifest=MANIFEST,
        )
        self.assertEqual(len(fast["relations"]), 0)
        self.assertGreater(len(deep["relations"]), len(fast["relations"]))
        self.assertGreater(len(deep["quality_roles"]), len(fast["quality_roles"]))

    def test_materialize_session_ingest_deep_mode(self) -> None:
        session_id = "deep-ingest-direct"
        session_dir = self.root / "memory" / "sessions" / session_id
        session_dir.mkdir(parents=True)
        (session_dir / "manifest.json").write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "title": "Deep ingest",
                    "started_at": "2026-07-06T12:00:00+00:00",
                    "ended_at": None,
                    "participants": ["user"],
                    "source_type": "imported_transcript",
                    "status": "open",
                    "artifact_refs": {},
                    "domains": ["research"],
                }
            ),
            encoding="utf-8",
        )
        from conversation_os.storage import append_jsonl, session_events_path

        append_jsonl(
            session_events_path(self.root, session_id),
            {
                "event_id": "ev-1",
                "session_id": session_id,
                "actor": "user",
                "kind": "request",
                "content": TRIANGULATION_EVENTS[0]["content"],
                "timestamp": "2026-07-06T12:00:00+00:00",
            },
        )
        result = materialize_session_mtsf_ingest(self.root, session_id, "deep", llm_preference="off")
        self.assertEqual(result["capture_mode"], "deep")
        self.assertGreaterEqual(result["relation_count"], 1)


if __name__ == "__main__":
    unittest.main()
