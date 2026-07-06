import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import init_repo
from conversation_os.mtsf_extraction import (
    assess_quarantine,
    default_extraction_evals_dir,
    default_skill_path,
    materialize_extraction_draft,
    run_extraction_evals,
    validate_extraction_draft,
)
from conversation_os.mtsf_stencils import normalize_stencil_draft
from conversation_os.storage import read_json

REPO_ROOT = Path(__file__).resolve().parents[1]


class MtsfExtractionTestCase(unittest.TestCase):
    def test_skill_and_schema_artifacts_exist(self) -> None:
        self.assertTrue(default_skill_path(REPO_ROOT).exists())
        schema = (
            REPO_ROOT
            / "docs"
            / "frameworks"
            / "metaphysical-thought-space"
            / "schemas"
            / "extraction-draft.schema.json"
        )
        self.assertTrue(schema.exists())

    def test_reference_hallway_draft_validates(self) -> None:
        draft_path = (
            default_extraction_evals_dir(REPO_ROOT)
            / "drafts"
            / "hallway-uncanny.reference.json"
        )
        draft = json.loads(draft_path.read_text(encoding="utf-8"))
        report = validate_extraction_draft(REPO_ROOT, draft)
        self.assertTrue(report.ok, json.dumps(report.errors, indent=2))
        quarantine = assess_quarantine(draft, report)
        self.assertFalse(quarantine.quarantine, quarantine.reasons)

    def test_normalize_stencil_draft_assigns_role_ids(self) -> None:
        normalized = normalize_stencil_draft(
            {
                "proposed_name": "test",
                "role_entities": [{"role_type": "field"}, {"role_type": "landscape"}],
                "relation_topology": [
                    {
                        "source_role_ref": "field",
                        "target_role_ref": "landscape",
                        "primitive": "modulates",
                    }
                ],
            }
        )
        role_ids = [row["role_id"] for row in normalized["role_entities"]]
        self.assertEqual(len(role_ids), 2)
        self.assertEqual(normalized["relation_topology"][0]["source_role_id"], role_ids[0])

    def test_extraction_eval_suite_passes(self) -> None:
        report = run_extraction_evals(REPO_ROOT)
        self.assertEqual(report["failed"], 0, json.dumps(report["runs"], indent=2))
        self.assertEqual(report["passed"], 3)

    def test_materialize_extraction_writes_session_artifacts(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        root = Path(tempdir.name)
        init_repo(root)
        docs_link = root / "docs"
        if docs_link.exists() or docs_link.is_symlink():
            if docs_link.is_symlink() or docs_link.is_file():
                docs_link.unlink()
            else:
                shutil.rmtree(docs_link)
        os.symlink(REPO_ROOT / "docs", docs_link, target_is_directory=True)
        session_id = "extraction-session-test"
        session_dir_path = root / "memory" / "sessions" / session_id
        session_dir_path.mkdir(parents=True)
        (session_dir_path / "manifest.json").write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "title": "Extraction test",
                    "started_at": "2026-07-06T12:00:00+00:00",
                    "ended_at": None,
                    "participants": ["user"],
                    "source_type": "live_session",
                    "status": "open",
                    "artifact_refs": {},
                    "domains": [],
                }
            ),
            encoding="utf-8",
        )

        draft_path = (
            default_extraction_evals_dir(REPO_ROOT)
            / "drafts"
            / "fast-capture.reference.json"
        )
        draft = json.loads(draft_path.read_text(encoding="utf-8"))
        draft["session_id"] = session_id
        result = materialize_extraction_draft(root, session_id, draft)
        self.assertTrue(result["validation_ok"])
        self.assertFalse(result["quarantine"])
        snapshot = read_json(session_dir_path / "mtsf" / "extraction_draft.json")
        self.assertEqual(snapshot["status"], "validated")
        self.assertIn("mtsf_extraction_draft", result["artifact_refs"])
        tempdir.cleanup()


if __name__ == "__main__":
    unittest.main()
