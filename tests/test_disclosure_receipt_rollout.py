from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.corpus_catalog_snapshot import publish_corpus_catalog_snapshot
from conversation_os.disclosure_receipt_rollout import (
    inspect_receipt_store_health,
    persistent_receipts_enabled_for_surface,
    resolve_surface_receipt_rollout_mode,
    retention_limit_for_mode,
)
from conversation_os.disclosure_receipts import (
    disclosure_receipts_path,
    get_disclosure_receipt,
    load_receipt_rows,
    persistent_receipts_enabled,
    reconstruct_disclosure_result,
    record_disclosure_receipt,
)
from conversation_os.reasoning_bridge import get_context_bundle, heuristic_classify_turn
from conversation_os.storage import append_jsonl


class DisclosureReceiptRolloutTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "bridge": {
                        "disclosure_rollout_v1": "enforced",
                        "disclosure_service_v1": True,
                    },
                    "disclosure": {
                        "persistent_receipts_v1": True,
                        "receipts": {
                            "persistent_receipts_v1": True,
                            "max_entries": 50,
                            "rollout": {
                                "bridge": "enforced",
                                "holodeck": "enforced",
                                "feed": "legacy",
                            },
                        },
                    },
                    "knowledge": {
                        "fail_empty_admission_shadow_v1": True,
                        "fail_empty_admission_enforce_v1": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        (self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime").mkdir(parents=True)
        publish_corpus_catalog_snapshot(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_release_runtime_enables_bridge_and_holodeck_receipts(self) -> None:
        release_runtime = json.loads(
            (Path(__file__).resolve().parents[1] / "product" / "inner_world_v1" / "config" / "runtime.json").read_text(
                encoding="utf-8"
            )
        )
        receipts = release_runtime["disclosure"]["receipts"]
        self.assertTrue(receipts["persistent_receipts_v1"])
        self.assertEqual(receipts["rollout"]["bridge"], "enforced")
        self.assertEqual(receipts["rollout"]["holodeck"], "enforced")
        self.assertEqual(receipts["rollout"]["feed"], "enforced")
        self.assertEqual(receipts["rollout"]["task_pack"], "enforced")

    def test_surface_rollout_gates_persistence(self) -> None:
        self.assertTrue(persistent_receipts_enabled_for_surface(self.root, "bridge"))
        self.assertTrue(persistent_receipts_enabled_for_surface(self.root, "holodeck"))
        self.assertFalse(persistent_receipts_enabled_for_surface(self.root, "feed"))
        self.assertEqual(resolve_surface_receipt_rollout_mode(self.root, "feed"), "legacy")

    def test_receipt_survives_process_restart(self) -> None:
        receipt = record_disclosure_receipt(
            self.root,
            request_id="req-restart-001",
            result_status="disclosed",
            effective_grant={
                "grant_id": "grant-restart",
                "request_id": "req-restart-001",
                "envelope": "bounded",
                "effective_layers": ["session"],
            },
            frame_audit={"audit_id": "audit-restart", "omitted_blocks": []},
            frame_bundle={"included_blocks": [{"block_id": "block-restart"}]},
            surface="bridge",
        )
        self.assertTrue(receipt.get("persistence", {}).get("persisted"))

        reloaded = get_disclosure_receipt(self.root, receipt["receipt_id"])
        self.assertIsNotNone(reloaded)
        reconstructed = reconstruct_disclosure_result(reloaded or {})
        self.assertTrue(reconstructed["reconstructible"])
        self.assertEqual(reconstructed["request_id"], "req-restart-001")

    def test_write_failure_does_not_break_receipt_return(self) -> None:
        with mock.patch("conversation_os.disclosure_receipts.append_jsonl", side_effect=OSError("disk full")):
            receipt = record_disclosure_receipt(
                self.root,
                request_id="req-write-fail",
                result_status="disclosed",
                effective_grant={"grant_id": "grant-fail", "request_id": "req-write-fail", "envelope": "bounded"},
                frame_audit={"audit_id": "audit-fail", "omitted_blocks": []},
                frame_bundle={"included_blocks": []},
                surface="bridge",
            )
        self.assertIn("receipt_id", receipt)
        self.assertFalse(receipt.get("persistence", {}).get("persisted"))
        health = inspect_receipt_store_health(self.root)
        self.assertEqual(health["last_issue_code"], "write_failure")

    def test_corrupt_rows_are_repaired_on_read(self) -> None:
        record_disclosure_receipt(
            self.root,
            request_id="req-valid",
            result_status="disclosed",
            effective_grant={"grant_id": "grant-valid", "request_id": "req-valid", "envelope": "bounded"},
            frame_audit={"audit_id": "audit-valid", "omitted_blocks": []},
            frame_bundle={"included_blocks": []},
            surface="bridge",
        )
        path = disclosure_receipts_path(self.root)
        with path.open("a", encoding="utf-8") as handle:
            handle.write("{not valid json}\n")

        rows, corrupt = load_receipt_rows(self.root, repair=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(corrupt), 1)
        health = inspect_receipt_store_health(self.root)
        self.assertEqual(health["corrupt_row_count"], 0)
        self.assertEqual(health["row_count"], 1)

    def test_incognito_uses_tighter_retention_limit(self) -> None:
        self.assertLess(
            retention_limit_for_mode("hashes_metrics_only", max_entries=100),
            retention_limit_for_mode("normal_policy", max_entries=100),
        )

    def test_bridge_context_bundle_persists_receipt_when_rollout_enabled(self) -> None:
        append_jsonl(
            self.root / "memory" / "events" / "session-rollout-001.jsonl",
            {
                "event_id": "event-1",
                "session_id": "session-rollout-001",
                "timestamp": "2026-06-26T17:10:00+00:00",
                "actor": "user",
                "kind": "message",
                "content": "Persist bridge receipt after restart.",
                "attachments": [],
                "tags": [],
                "source_ref": None,
            },
        )
        context = heuristic_classify_turn(
            self.root,
            {
                "request_id": "req-rollout-receipt-001",
                "session_id": "session-rollout-001",
                "raw_text": "Persist bridge receipt after restart.",
                "caller_hints": {"workspace_id": "ws-rollout-001"},
                "domain_hints": [],
                "source_refs": [],
            },
        )
        bundle = get_context_bundle(self.root, context)
        receipt = bundle.get("disclosure_receipt", {})
        self.assertTrue(persistent_receipts_enabled(self.root, surface="bridge"))
        self.assertIn("receipt_id", receipt)
        loaded = get_disclosure_receipt(self.root, receipt["receipt_id"])
        self.assertIsNotNone(loaded)
