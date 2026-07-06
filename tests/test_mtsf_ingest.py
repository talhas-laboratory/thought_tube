import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import init_repo, session_close, session_import, session_start
from conversation_os.mtsf_ingest import (
    build_fast_extraction_draft,
    materialize_session_mtsf_ingest,
    should_run_mtsf_ingest,
)
from conversation_os.mtsf_projector import session_shape_index_path
from conversation_os.storage import read_json, read_jsonl, session_events_path

REPO_ROOT = Path(__file__).resolve().parents[1]


class MtsfIngestTestCase(unittest.TestCase):
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

    def test_should_skip_off_mode(self) -> None:
        events = [{"actor": "user", "content": "latent topology and context field discussion"}]
        self.assertFalse(should_run_mtsf_ingest("off", events))

    def test_build_fast_draft_detects_triangulation(self) -> None:
        events = [
            {
                "actor": "user",
                "content": (
                    "Explain how the same query would be processed without any prior context, "
                    "with relevant prior context, and with unrelated prior context in latent topology."
                ),
            }
        ]
        manifest = {
            "title": "Topology import",
            "source_type": "imported_transcript",
            "domains": ["research"],
        }
        draft = build_fast_extraction_draft(session_id="sess-1", events=events, manifest=manifest)
        self.assertEqual(draft["capture_mode"], "fast")
        self.assertGreaterEqual(len(draft["entities"]), 2)
        self.assertGreaterEqual(len(draft["candidate_shapes"]), 1)
        self.assertEqual(len(draft["stencil_drafts"]), 1)
        self.assertIn("seed:stencil-context-warps-topology", draft["stencil_drafts"][0]["evidence"]["source_refs"])

    def test_session_close_runs_ingest_pipeline(self) -> None:
        session_id = "ingest-close-test"
        session_start(
            self.root,
            type(
                "Args",
                (),
                {
                    "session_id": session_id,
                    "title": "Latent topology import",
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
                    "content": (
                        "Explain processing without any prior context, with relevant prior context, "
                        "and unrelated prior context across latent topology and symmetry."
                    ),
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
                    "mtsf_mode": "fast",
                },
            )(),
        )
        self.assertEqual(result["mtsf_ingest"]["mtsf_ingest"], "completed")
        self.assertIn("mtsf_extraction_draft", result["artifact_refs"])
        self.assertIn("mtsf_shape_index", result["artifact_refs"])
        index = read_json(session_shape_index_path(self.root, session_id))
        self.assertIn("stencil-context-warps-topology", index["stencils"])

    def test_session_import_with_mtsf_mode_off_skips_ingest(self) -> None:
        source = self.root / "topology-import.md"
        source.write_text(
            "User: Explain latent topology with prior context.\nAssistant: Context modulates the path.\n",
            encoding="utf-8",
        )
        result = session_import(
            self.root,
            type(
                "Args",
                (),
                {
                    "source_path": str(source),
                    "title": "Topology",
                    "session_id": "import-mtsf-off",
                    "participants": "importer",
                    "source_type": "imported_transcript",
                    "domains": "research",
                    "tags": "",
                    "task_id": None,
                    "request": None,
                    "task_type": None,
                    "mtsf_mode": "off",
                },
            )(),
        )
        self.assertEqual(result["mtsf_ingest"]["mtsf_ingest"], "skipped")
        self.assertFalse((self.root / "memory" / "sessions" / "import-mtsf-off" / "mtsf" / "extraction_draft.json").exists())

    def test_session_import_runs_ingest_by_default(self) -> None:
        source = self.root / "topology-import-default.md"
        source.write_text(
            "\n".join(
                [
                    "User: Explain how the same query would be processed without any prior context,",
                    "with relevant prior context, and with unrelated prior context in latent topology.",
                    "Assistant: The context field modulates the effective topology.",
                ]
            ),
            encoding="utf-8",
        )
        result = session_import(
            self.root,
            type(
                "Args",
                (),
                {
                    "source_path": str(source),
                    "title": "Topology default ingest",
                    "session_id": "import-mtsf-default",
                    "participants": "importer",
                    "source_type": "imported_transcript",
                    "domains": "research",
                    "tags": "",
                    "task_id": None,
                    "request": None,
                    "task_type": None,
                    "mtsf_mode": "fast",
                },
            )(),
        )
        self.assertEqual(result["mtsf_ingest"]["mtsf_ingest"], "completed")
        draft = read_json(
            self.root / "memory" / "sessions" / "import-mtsf-default" / "mtsf" / "extraction_draft.json"
        )
        self.assertEqual(draft["provenance"]["model_id"], "mtsf_ingest.fast")
        events = read_jsonl(session_events_path(self.root, "import-mtsf-default"))
        self.assertGreaterEqual(len(events), 2)


if __name__ == "__main__":
    unittest.main()
