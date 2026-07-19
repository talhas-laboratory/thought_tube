from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.bounded_view_disclosure_adapter import (
    bounded_view_epistemic_backend_enabled,
    collect_bounded_view_evidence,
    extract_bounded_view_grant_context,
    map_bounded_view_to_evidence_blocks,
)
from conversation_os.disclosure_ports import build_inner_world_ports
from conversation_os.metaphysical_kernel_runtime import FoundationRuntime
from conversation_os.metaphysical_kernel_store import foundation_events_path


class BoundedViewDisclosureAdapterTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "disclosure": {
                        "bounded_view": {"epistemic_backend_v1": True, "max_nodes": 6, "max_depth": 2}
                    }
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)
        self.runtime = FoundationRuntime(self.root, actor="user:test")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _event(self, **overrides: object) -> dict:
        payload = {
            "event_id": "event-bv-001",
            "session_id": "session-bv-001",
            "timestamp": "2026-07-19T12:00:00+00:00",
            "actor": "user:test",
            "kind": "request",
            "content": "Control loops may be inhibiting initiative.",
        }
        payload.update(overrides)
        return payload

    def _seed_branch_claim(self, *, branch_id: str, scope_id: str) -> str:
        fragment = self.runtime.capture_from_conversation_event(self._event())
        prov_id = fragment["envelope"]["provenance_id"]
        self.runtime.ensure_scope(scope_id)
        self.runtime.ensure_branch(branch_id)
        claim = self.runtime.assert_claim(
            predicate="has_level",
            arguments=["low"],
            branch_id=branch_id,
            scope_id=scope_id,
            claimant=f"user:{branch_id}",
            provenance_id=prov_id,
        )
        return str(claim["envelope"]["id"])

    def _grant(self, *, branch_id: str, scope_id: str, root_record_ids: list[str]) -> dict:
        return {
            "grant_id": "grant-bv-001",
            "request_id": "req-bv-001",
            "envelope": "bounded",
            "effective_layers": ["kernel"],
            "effective_refs": [f"kernel:{record_id}" for record_id in root_record_ids],
            "dimensions": [],
            "shape_maturity": "candidate",
            "cross_ocean": False,
            "token_budget": 900,
            "persistence_mode": "gated",
            "explicit_pins": list(root_record_ids),
            "narrowing_reasons": [],
            "deny_precedence_applied": False,
            "requested_grant_ref": "grant-bv-001",
            "provenance": {"branch_id": branch_id, "scope_id": scope_id},
        }

    def test_branch_scope_conformance_isolates_competing_branches(self) -> None:
        scope_id = "scope-bv-conformance"
        claim_a = self._seed_branch_claim(branch_id="branch_a", scope_id=scope_id)
        claim_b = self._seed_branch_claim(branch_id="branch_b", scope_id=scope_id)

        evidence_a = collect_bounded_view_evidence(
            self.root,
            self._grant(branch_id="branch_a", scope_id=scope_id, root_record_ids=[claim_a]),
        )
        evidence_b = collect_bounded_view_evidence(
            self.root,
            self._grant(branch_id="branch_b", scope_id=scope_id, root_record_ids=[claim_b]),
        )

        ids_a = {block["block_id"] for block in evidence_a["blocks"]}
        ids_b = {block["block_id"] for block in evidence_b["blocks"]}
        self.assertIn(claim_a, ids_a)
        self.assertNotIn(claim_b, ids_a)
        self.assertIn(claim_b, ids_b)
        self.assertNotIn(claim_a, ids_b)
        self.assertEqual(evidence_a["result_status"], "disclosed")
        self.assertTrue(all(block["branch_id"] == "branch_a" for block in evidence_a["blocks"]))

    def test_evidence_blocks_are_reference_only_without_duplicating_records(self) -> None:
        scope_id = "scope-bv-reference"
        claim_id = self._seed_branch_claim(branch_id="branch_main", scope_id=scope_id)
        events_before = foundation_events_path(self.root).read_text(encoding="utf-8")

        evidence = collect_bounded_view_evidence(
            self.root,
            self._grant(branch_id="branch_main", scope_id=scope_id, root_record_ids=[claim_id]),
        )
        events_after = foundation_events_path(self.root).read_text(encoding="utf-8")
        self.assertEqual(events_before, events_after)

        payload = json.dumps(evidence)
        self.assertIn(f"kernel:{claim_id}", payload)
        self.assertNotIn("Control loops may be inhibiting initiative.", payload)
        self.assertTrue(all(block["provenance"]["reference_only"] for block in evidence["blocks"]))

    def test_missing_branch_or_scope_abstains(self) -> None:
        scope_id = "scope-bv-abstain"
        claim_id = self._seed_branch_claim(branch_id="branch_main", scope_id=scope_id)
        grant = self._grant(branch_id="", scope_id=scope_id, root_record_ids=[claim_id])
        result = collect_bounded_view_evidence(self.root, grant)
        self.assertEqual(result["result_status"], "abstained_missing_branch_scope")
        self.assertEqual(result["count"], 0)

    def test_flag_disabled_returns_disabled_without_query(self) -> None:
        config_path = self.root / "product" / "inner_world_v1" / "config" / "runtime.json"
        runtime = json.loads(config_path.read_text(encoding="utf-8"))
        runtime["disclosure"]["bounded_view"]["epistemic_backend_v1"] = False
        config_path.write_text(json.dumps(runtime), encoding="utf-8")

        scope_id = "scope-bv-disabled"
        claim_id = self._seed_branch_claim(branch_id="branch_main", scope_id=scope_id)
        result = collect_bounded_view_evidence(
            self.root,
            self._grant(branch_id="branch_main", scope_id=scope_id, root_record_ids=[claim_id]),
        )
        self.assertFalse(bounded_view_epistemic_backend_enabled(self.root))
        self.assertEqual(result["result_status"], "disabled")
        self.assertEqual(result["blocks"], [])

    def test_disclosure_port_routes_through_adapter(self) -> None:
        scope_id = "scope-bv-port"
        claim_id = self._seed_branch_claim(branch_id="branch_main", scope_id=scope_id)
        ports = build_inner_world_ports()
        evidence = ports.bounded_view.collect_bounded_view_evidence(
            self.root,
            self._grant(branch_id="branch_main", scope_id=scope_id, root_record_ids=[claim_id]),
        )
        self.assertGreater(evidence["count"], 0)
        self.assertEqual(evidence["blocks"][0]["provenance"]["surface"], "bounded_view")

    def test_map_bounded_view_to_evidence_blocks_preserves_provenance(self) -> None:
        view = {
            "nodes": [
                {
                    "record_id": "claim-001",
                    "record_kind": "claim",
                    "depth": 0,
                    "branch_id": "branch_main",
                    "epistemic_status": "asserted",
                }
            ]
        }
        blocks = map_bounded_view_to_evidence_blocks(
            view,
            branch_id="branch_main",
            scope_id="scope_main",
            max_nodes=4,
        )
        self.assertEqual(blocks[0]["source_ref"], "kernel:claim-001")
        self.assertEqual(blocks[0]["scope_id"], "scope_main")
        context = extract_bounded_view_grant_context(
            self._grant(branch_id="branch_main", scope_id="scope_main", root_record_ids=["claim-001"])
        )
        self.assertEqual(context["branch_id"], "branch_main")
        self.assertEqual(context["scope_id"], "scope_main")


if __name__ == "__main__":
    unittest.main()
