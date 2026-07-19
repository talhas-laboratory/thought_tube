from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.disclosure_ports import build_inner_world_ports
from conversation_os.disclosure_receipts import (
    apply_receipt_retention,
    build_audit_receipt,
    get_disclosure_receipt,
    inspect_disclosure_receipt,
    list_disclosure_receipts,
    persistent_receipts_enabled,
    reconstruct_disclosure_result,
    record_bridge_context_receipt,
    record_disclosure_receipt,
)
from conversation_os.holodeck import holodeck_inspect_disclosure_receipt, holodeck_list_disclosure_receipts
from conversation_os.reasoning_bridge import (
    get_context_bundle,
    heuristic_classify_turn,
    inspect_disclosure_receipt as bridge_inspect_disclosure_receipt,
    list_disclosure_receipts as bridge_list_disclosure_receipts,
)
from conversation_os.storage import append_jsonl


class DisclosureReceiptsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "disclosure": {
                        "receipts": {
                            "persistent_receipts_v1": True,
                            "max_entries": 2,
                            "retention_days": 30,
                        }
                    },
                    "knowledge": {
                        "fail_empty_admission_shadow_v1": True,
                        "fail_empty_admission_enforce_v1": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _effective_grant(self, *, envelope: str = "bounded") -> dict:
        return {
            "grant_id": "grant-test-001",
            "request_id": "req-receipt-001",
            "envelope": envelope,
            "effective_layers": ["session", "workspace"],
            "effective_refs": [],
            "dimensions": [],
            "shape_maturity": "candidate",
            "cross_ocean": False,
            "token_budget": 1200,
            "persistence_mode": "gated",
            "explicit_pins": [],
            "narrowing_reasons": [],
            "deny_precedence_applied": False,
            "requested_grant_ref": "grant-test-001",
        }

    def _frame_bundle(self) -> dict:
        return {
            "frame_id": "frame-test-001",
            "assembly_status": "partial",
            "included_blocks": [
                {
                    "block_id": "frame-test-001:session",
                    "layer": "session",
                    "source_ref": "memory/events/session-001.jsonl",
                    "summary": "Recent session continuity",
                },
                {
                    "block_id": "frame-test-001:workspace",
                    "layer": "workspace",
                    "source_ref": "workspace/ws-001/manifest.json",
                    "summary": "Workspace binding",
                },
            ],
        }

    def _frame_audit(self) -> dict:
        return {
            "audit_id": "audit-test-001",
            "frame_id": "frame-test-001",
            "workspace_id": "ws-001",
            "envelope_mode": "bounded",
            "assembly_status": "partial",
            "omitted_blocks": [
                {
                    "block_id": "frame-test-001:global",
                    "layer": "global",
                    "reason_code": "layer_not_disclosed",
                    "summary": "1 retrieval candidate(s)",
                    "source_ref": "docs/plans/chat-bridge.md",
                }
            ],
            "budget_ledger": {
                "token_budget": 1200,
                "orientation_tokens": 42,
                "evidence_tokens": 88,
            },
        }

    def test_build_audit_receipt_excludes_sensitive_text(self) -> None:
        receipt = build_audit_receipt(
            request_id="req-receipt-001",
            surface="bridge",
            result_status="disclosed",
            effective_grant=self._effective_grant(),
            frame_audit=self._frame_audit(),
            frame_bundle=self._frame_bundle(),
            metrics={"included_block_count": 2},
        )
        payload = json.dumps(receipt)
        self.assertNotIn("Recent session continuity", payload)
        self.assertIn("frame-test-001:session", payload)
        self.assertEqual(receipt["retention_mode"], "normal_policy")
        self.assertFalse(receipt["sensitive_text_included"])

    def test_incognito_receipt_stores_hashes_only(self) -> None:
        receipt = build_audit_receipt(
            request_id="req-incognito-001",
            surface="bridge",
            result_status="empty_grant_excludes_all",
            effective_grant=self._effective_grant(envelope="incognito"),
            frame_audit={"audit_id": "audit-incognito", "envelope_mode": "incognito", "omitted_blocks": []},
            frame_bundle={"included_blocks": []},
            metrics={"latency_ms": 8},
        )
        self.assertEqual(receipt["retention_mode"], "hashes_metrics_only")
        self.assertFalse(receipt["sensitive_text_included"])
        for reason in receipt["omission_reasons"]:
            self.assertNotIn("summary", reason)
            self.assertNotIn("source_ref", reason)

    def test_persist_reconstruct_and_inspect(self) -> None:
        self.assertTrue(persistent_receipts_enabled(self.root))
        receipt = record_disclosure_receipt(
            self.root,
            request_id="req-receipt-001",
            result_status="disclosed",
            effective_grant=self._effective_grant(),
            frame_audit=self._frame_audit(),
            frame_bundle=self._frame_bundle(),
            metrics={"included_block_count": 2},
            workspace_id="ws-001",
        )
        loaded = get_disclosure_receipt(self.root, receipt["receipt_id"])
        self.assertIsNotNone(loaded)
        reconstructed = reconstruct_disclosure_result(loaded or {})
        self.assertTrue(reconstructed["reconstructible"])
        self.assertEqual(reconstructed["result_status"], "disclosed")
        self.assertEqual(reconstructed["included_block_ids"], ["frame-test-001:session", "frame-test-001:workspace"])
        self.assertEqual(reconstructed["omitted_block_ids"], ["frame-test-001:global"])

        inspected = inspect_disclosure_receipt(self.root, receipt["receipt_id"])
        self.assertTrue(inspected["found"])
        self.assertEqual(inspected["reconstructed"]["request_id"], "req-receipt-001")

    def test_retention_trims_old_receipts(self) -> None:
        for index in range(3):
            record_disclosure_receipt(
                self.root,
                request_id=f"req-retention-{index}",
                result_status="disclosed",
                effective_grant=self._effective_grant(),
                frame_audit={"audit_id": f"audit-{index}", "omitted_blocks": []},
                frame_bundle={"included_blocks": []},
            )
        remaining = list_disclosure_receipts(self.root, limit=10)
        self.assertEqual(len(remaining), 2)
        self.assertEqual(remaining[0]["request_id"], "req-retention-2")
        result = apply_receipt_retention(self.root)
        self.assertEqual(result["removed"], 0)
        self.assertEqual(result["retained"], 2)

    def test_bridge_context_bundle_records_receipt(self) -> None:
        append_jsonl(
            self.root / "memory" / "events" / "session-receipt-001.jsonl",
            {
                "event_id": "event-1",
                "session_id": "session-receipt-001",
                "timestamp": "2026-06-26T17:10:00+00:00",
                "actor": "user",
                "kind": "message",
                "content": "Build bridge integration receipt path.",
                "attachments": [],
                "tags": [],
                "source_ref": None,
            },
        )
        context = heuristic_classify_turn(
            self.root,
            {
                "request_id": "req-bridge-receipt-001",
                "session_id": "session-receipt-001",
                "raw_text": "Build bridge integration receipt path.",
                "caller_hints": {"workspace_id": "ws-receipt-001"},
                "domain_hints": [],
                "source_refs": [],
            },
        )
        bundle = get_context_bundle(self.root, context)
        receipt = bundle.get("disclosure_receipt", {})
        self.assertIn("receipt_id", receipt)
        self.assertEqual(receipt.get("request_id"), "req-bridge-receipt-001")
        listed = bridge_list_disclosure_receipts(self.root, request_id="req-bridge-receipt-001")
        self.assertEqual(len(listed), 1)
        inspected = bridge_inspect_disclosure_receipt(self.root, receipt["receipt_id"])
        self.assertTrue(inspected["found"])

    def test_holodeck_inspect_wrappers_filter_surface(self) -> None:
        record_disclosure_receipt(
            self.root,
            request_id="req-holodeck-001",
            result_status="disclosed",
            effective_grant=self._effective_grant(),
            frame_audit={"audit_id": "audit-holodeck", "omitted_blocks": []},
            frame_bundle={"included_blocks": []},
            surface="holodeck",
            workspace_id="ws-holodeck-001",
        )
        record_disclosure_receipt(
            self.root,
            request_id="req-bridge-001",
            result_status="disclosed",
            effective_grant=self._effective_grant(),
            frame_audit={"audit_id": "audit-bridge", "omitted_blocks": []},
            frame_bundle={"included_blocks": []},
            surface="bridge",
        )
        holodeck_rows = holodeck_list_disclosure_receipts(self.root, workspace_id="ws-holodeck-001")
        self.assertEqual(len(holodeck_rows), 1)
        self.assertEqual(holodeck_rows[0]["surface"], "holodeck")
        inspected = holodeck_inspect_disclosure_receipt(self.root, holodeck_rows[0]["receipt_id"])
        self.assertTrue(inspected["found"])

    def test_default_receipt_sink_builds_audit_receipt(self) -> None:
        ports = build_inner_world_ports()
        receipt = ports.receipt_sink.record_disclosure_receipt(
            self.root,
            request_id="req-sink-001",
            result_status="disclosed",
            effective_grant=self._effective_grant(),
            frame_audit=self._frame_audit(),
            frame_bundle=self._frame_bundle(),
        )
        self.assertIn("receipt_id", receipt)
        self.assertEqual(len(ports.receipt_sink.records), 1)


if __name__ == "__main__":
    unittest.main()
