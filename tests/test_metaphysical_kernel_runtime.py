from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.metaphysical_kernel_runtime import (
    BoundedViewQuery,
    FoundationRuntime,
    run_vertical_slice,
)
from conversation_os.metaphysical_kernel_contracts import ContractValidationError
from conversation_os.metaphysical_kernel_store import FoundationStore
from conversation_os.storage import append_jsonl, read_jsonl, session_events_path


class MetaphysicalKernelRuntimeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)
        self.runtime = FoundationRuntime(self.root, actor="user:test")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _event(self, **overrides: object) -> dict:
        payload = {
            "event_id": "event-vertical-001",
            "session_id": "session-vertical-001",
            "timestamp": "2026-07-12T12:00:00+00:00",
            "actor": "user:test",
            "kind": "request",
            "content": "Control loops may be inhibiting initiative.",
        }
        payload.update(overrides)
        return payload

    def test_capture_from_conversation_event_creates_source_fragment(self) -> None:
        fragment = self.runtime.capture_from_conversation_event(self._event())
        self.assertEqual(fragment["envelope"]["record_kind"], "source_fragment")
        self.assertEqual(fragment["envelope"]["maturity_status"], "raw")
        self.assertIn("memory://events/", fragment["content_pointer"])

    def test_append_only_store_preserves_event_history(self) -> None:
        self.runtime.capture_from_conversation_event(self._event())
        events = self.runtime.store.read_events()
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["operation"], "append_record")
        self.assertEqual(events[-1]["operation"], "append_record")

    def test_vertical_slice_end_to_end_without_inference(self) -> None:
        result = run_vertical_slice(
            self.root,
            session_event=self._event(),
            referent_label="Company initiative",
            claim_predicate="inhibits",
            claim_arguments=["control_loop"],
        )
        self.assertEqual(result["validation_errors"], [])
        self.assertTrue(result["provenance_trace"]["complete"])
        self.assertIn(result["source_fragment_id"], result["provenance_trace"]["source_fragment_ids"])
        self.assertGreaterEqual(len(result["bounded_view"]["nodes"]), 1)

    def test_state_adoption_requires_state_commitment(self) -> None:
        result = run_vertical_slice(
            self.root,
            session_event=self._event(),
            referent_label="Initiative",
            claim_predicate="has_level",
            claim_arguments=["low"],
            adopt_state=True,
            state_value="low",
        )
        self.assertIsNotNone(result["adoption"])
        bundle = self.runtime.current_bundle()
        self.assertEqual(len(bundle["state_commitments"]), 1)
        self.assertEqual(len(bundle["states"]), 1)
        self.assertEqual(result["validation_errors"], [])
        self.assertEqual(self.runtime.store.read_events()[-1]["operation"], "append_records")

    def test_invalid_state_adoption_appends_no_events(self) -> None:
        fragment = self.runtime.capture_from_conversation_event(self._event())
        provenance_id = fragment["envelope"]["provenance_id"]
        self.runtime.ensure_scope("scope_atomic")
        self.runtime.ensure_branch("branch_atomic")
        event_count_before = len(self.runtime.store.read_events())

        with self.assertRaises(ContractValidationError):
            self.runtime.commit_state_from_claims(
                source_claim_ids=["claim_missing"],
                branch_id="branch_atomic",
                scope_id="scope_atomic",
                subject_refs=["ref_atomic"],
                state_type="workspace:initiative",
                value="low",
                value_type="ordinal",
                provenance_id=provenance_id,
            )

        self.assertEqual(len(self.runtime.store.read_events()), event_count_before)
        bundle = self.runtime.current_bundle()
        self.assertEqual(bundle["states"], [])
        self.assertEqual(bundle["state_commitments"], [])

    def test_contradictory_branches_remain_isolated(self) -> None:
        fragment = self.runtime.capture_from_conversation_event(self._event())
        prov_id = fragment["envelope"]["provenance_id"]
        scope_id = "scope_branch_test"
        self.runtime.ensure_scope(scope_id)
        self.runtime.ensure_branch("branch_a")
        self.runtime.ensure_branch("branch_b")

        claim_a = self.runtime.assert_claim(
            predicate="has_level",
            arguments=["high"],
            branch_id="branch_a",
            scope_id=scope_id,
            claimant="user:a",
            provenance_id=prov_id,
        )
        claim_b = self.runtime.assert_claim(
            predicate="has_level",
            arguments=["low"],
            branch_id="branch_b",
            scope_id=scope_id,
            claimant="user:b",
            provenance_id=prov_id,
        )

        view_a = self.runtime.query_bounded_view(
            BoundedViewQuery(
                branch_id="branch_a",
                scope_id=scope_id,
                root_record_ids=[claim_a["envelope"]["id"]],
                max_depth=2,
            )
        )
        view_b = self.runtime.query_bounded_view(
            BoundedViewQuery(
                branch_id="branch_b",
                scope_id=scope_id,
                root_record_ids=[claim_b["envelope"]["id"]],
                max_depth=2,
            )
        )
        ids_a = {node.record_id for node in view_a.nodes}
        ids_b = {node.record_id for node in view_b.nodes}
        self.assertIn(claim_a["envelope"]["id"], ids_a)
        self.assertNotIn(claim_b["envelope"]["id"], ids_a)
        self.assertIn(claim_b["envelope"]["id"], ids_b)
        self.assertNotIn(claim_a["envelope"]["id"], ids_b)

    def test_retraction_excludes_claim_from_bounded_view(self) -> None:
        fragment = self.runtime.capture_from_conversation_event(self._event())
        prov_id = fragment["envelope"]["provenance_id"]
        scope_id = "scope_retract"
        self.runtime.ensure_scope(scope_id)
        self.runtime.ensure_branch("branch_main")
        claim = self.runtime.assert_claim(
            predicate="temporary",
            arguments=["value"],
            branch_id="branch_main",
            scope_id=scope_id,
            claimant="user:test",
            provenance_id=prov_id,
        )
        claim_id = claim["envelope"]["id"]

        active_view = self.runtime.query_bounded_view(
            BoundedViewQuery(
                branch_id="branch_main",
                scope_id=scope_id,
                root_record_ids=[claim_id],
                max_depth=2,
            )
        )
        self.assertTrue(any(node.record_id == claim_id for node in active_view.nodes))

        self.runtime.retract_record(claim_id, reason="superseded")
        retracted_view = self.runtime.query_bounded_view(
            BoundedViewQuery(
                branch_id="branch_main",
                scope_id=scope_id,
                root_record_ids=[claim_id],
                max_depth=2,
            )
        )
        self.assertFalse(any(node.record_id == claim_id for node in retracted_view.nodes))
        self.assertGreaterEqual(retracted_view.excluded_retracted, 1)

    def test_bounded_view_fails_closed_on_depth(self) -> None:
        fragment = self.runtime.capture_from_conversation_event(self._event())
        prov_id = fragment["envelope"]["provenance_id"]
        scope_id = "scope_depth"
        self.runtime.ensure_scope(scope_id)
        self.runtime.ensure_branch("branch_main")
        referent = self.runtime.resolve_referent("Depth subject")
        claim = self.runtime.assert_claim(
            predicate="relates",
            arguments=[referent["envelope"]["id"]],
            branch_id="branch_main",
            scope_id=scope_id,
            claimant="user:test",
            provenance_id=prov_id,
        )

        shallow = self.runtime.query_bounded_view(
            BoundedViewQuery(
                branch_id="branch_main",
                scope_id=scope_id,
                root_record_ids=[claim["envelope"]["id"]],
                max_depth=0,
            )
        )
        deep = self.runtime.query_bounded_view(
            BoundedViewQuery(
                branch_id="branch_main",
                scope_id=scope_id,
                root_record_ids=[claim["envelope"]["id"]],
                max_depth=3,
            )
        )
        self.assertLess(len(shallow.nodes), len(deep.nodes))
        self.assertTrue(deep.truncated or len(deep.nodes) >= len(shallow.nodes))

    def test_provenance_trace_terminates_at_source_fragment(self) -> None:
        result = run_vertical_slice(
            self.root,
            session_event=self._event(),
            referent_label="Trace subject",
            claim_predicate="observed",
            claim_arguments=["signal"],
        )
        trace = self.runtime.trace_provenance(result["claim_id"])
        self.assertTrue(trace.complete)
        self.assertIn(result["source_fragment_id"], trace.source_fragment_ids)
        kinds = [step.record_kind for step in trace.steps]
        self.assertIn("claim", kinds)
        self.assertIn("source_fragment", kinds)

    def test_revise_claim_retracts_prior_version(self) -> None:
        fragment = self.runtime.capture_from_conversation_event(self._event())
        prov_id = fragment["envelope"]["provenance_id"]
        scope_id = "scope_revise"
        self.runtime.ensure_scope(scope_id)
        self.runtime.ensure_branch("branch_main")
        original = self.runtime.assert_claim(
            predicate="level",
            arguments=["medium"],
            branch_id="branch_main",
            scope_id=scope_id,
            claimant="user:test",
            provenance_id=prov_id,
        )
        revised = self.runtime.revise_claim(
            superseded_claim_id=original["envelope"]["id"],
            predicate="level",
            arguments=["high"],
            branch_id="branch_main",
            scope_id=scope_id,
            claimant="user:test",
            provenance_id=prov_id,
        )

        folded = self.runtime.store.fold()
        original_record = next(
            item
            for item in folded["claims"]
            if item["envelope"]["id"] == original["envelope"]["id"]
        )
        self.assertEqual(original_record["envelope"]["epistemic_status"], "retracted")
        self.assertEqual(revised["envelope"]["epistemic_status"], "candidate")

    def test_session_append_path_compatible_with_capture_bridge(self) -> None:
        session_id = "session-bridge-001"
        event_payload = {
            "event_id": "event-bridge-001",
            "session_id": session_id,
            "timestamp": "2026-07-12T12:30:00+00:00",
            "actor": "user:founder",
            "kind": "request",
            "content": "Raw thought for foundation capture.",
            "attachments": [],
            "tags": [],
            "source_ref": None,
        }
        append_jsonl(session_events_path(self.root, session_id), event_payload)

        loaded = read_jsonl(session_events_path(self.root, session_id))[0]
        fragment = self.runtime.capture_from_conversation_event(loaded)
        self.assertEqual(
            fragment["content_pointer"],
            f"memory://events/{session_id}/{event_payload['event_id']}",
        )
        self.assertEqual(self.runtime.validate_current_bundle(), [])

    def test_store_fold_keeps_append_only_durability(self) -> None:
        store = FoundationStore(self.root)
        store.append_event(
            "append_record",
            actor="user:test",
            record_kind="source_fragment",
            record={
                "envelope": {
                    "id": "sf_durable",
                    "record_kind": "source_fragment",
                    "type_id": "core:source_fragment",
                    "created_at": "2026-07-12T00:00:00Z",
                    "created_by": "user:test",
                    "provenance_id": "prov_durable",
                    "maturity_status": "raw",
                    "epistemic_status": "not_applicable",
                    "governance_status": "local",
                },
                "media_type": "text",
                "content_pointer": "memory://test",
                "author_or_origin": "user:test",
                "captured_at": "2026-07-12T00:00:00Z",
                "integrity_hash": "sha256:test",
                "source_kind": "user_input",
            },
        )
        store.append_event(
            "append_record",
            actor="user:test",
            record_kind="provenance",
            record={
                "envelope": {
                    "id": "prov_durable",
                    "record_kind": "provenance",
                    "type_id": "core:provenance",
                    "created_at": "2026-07-12T00:00:00Z",
                    "created_by": "user:test",
                    "provenance_id": "prov_durable",
                    "maturity_status": "structured",
                    "epistemic_status": "not_applicable",
                    "governance_status": "local",
                },
                "source_refs": ["sf_durable"],
            },
        )
        self.assertEqual(len(store.read_events()), 2)
        folded = store.fold()
        self.assertEqual(len(folded["source_fragments"]), 1)
        self.assertEqual(folded["source_fragments"][0]["envelope"]["id"], "sf_durable")

    def test_assert_relation_instance_validates_before_append(self) -> None:
        fragment = self.runtime.capture_from_conversation_event(self._event())
        prov_id = fragment["envelope"]["provenance_id"]
        scope_id = "scope_relation"
        self.runtime.ensure_scope(scope_id)
        referent = self.runtime.resolve_referent("Relation subject")
        event_count_before = len(self.runtime.store.read_events())

        with self.assertRaises(ContractValidationError):
            self.runtime.assert_relation_instance(
                type_id="kernel:test:links",
                participants=[{"role": "subject", "ref": referent["envelope"]["id"]}],
                scope_id="",
                provenance_id=prov_id,
            )

        self.assertEqual(len(self.runtime.store.read_events()), event_count_before)

    def test_assert_relation_instance_rejects_incomplete_participant(self) -> None:
        fragment = self.runtime.capture_from_conversation_event(self._event())
        prov_id = fragment["envelope"]["provenance_id"]
        scope_id = "scope_invalid_participant"
        self.runtime.ensure_scope(scope_id)
        event_count_before = len(self.runtime.store.read_events())

        with self.assertRaisesRegex(ContractValidationError, "requires non-empty role and ref"):
            self.runtime.assert_relation_instance(
                type_id="kernel:test:links",
                participants=[{"role": "subject", "ref": ""}],
                scope_id=scope_id,
                provenance_id=prov_id,
            )

        self.assertEqual(len(self.runtime.store.read_events()), event_count_before)

    def test_record_identity_uncertainty_preserves_two_referents(self) -> None:
        fragment = self.runtime.capture_from_conversation_event(self._event())
        prov_id = fragment["envelope"]["provenance_id"]
        scope_id = "scope_identity"
        self.runtime.ensure_scope(scope_id)
        left = self.runtime.resolve_referent("Acme Corp")
        right = self.runtime.resolve_referent("Acme Holdings")

        relation = self.runtime.record_identity_uncertainty(
            left_referent_id=left["envelope"]["id"],
            right_referent_id=right["envelope"]["id"],
            scope_id=scope_id,
            provenance_id=prov_id,
            confidence=0.55,
            rationale="Possible corporate rebrand",
        )

        bundle = self.runtime.current_bundle()
        self.assertEqual(len(bundle["referents"]), 2)
        self.assertEqual(len(bundle["relation_instances"]), 1)
        self.assertEqual(relation["type_id"], "kernel:identity:possibly_same_as")
        self.assertEqual(relation["envelope"]["epistemic_status"], "unresolved")
        self.assertEqual(self.runtime.validate_current_bundle(), [])

    def test_same_as_identity_merge_rejected_at_runtime(self) -> None:
        fragment = self.runtime.capture_from_conversation_event(self._event())
        prov_id = fragment["envelope"]["provenance_id"]
        scope_id = "scope_same_as"
        self.runtime.ensure_scope(scope_id)
        left = self.runtime.resolve_referent("Entity A")
        right = self.runtime.resolve_referent("Entity B")
        event_count_before = len(self.runtime.store.read_events())

        with self.assertRaises(ContractValidationError):
            self.runtime.record_identity_uncertainty(
                left_referent_id=left["envelope"]["id"],
                right_referent_id=right["envelope"]["id"],
                scope_id=scope_id,
                provenance_id=prov_id,
                relation_kind="same_as",
            )

        self.assertEqual(len(self.runtime.store.read_events()), event_count_before)
        self.assertEqual(self.runtime.current_bundle()["relation_instances"], [])

    def test_identity_uncertainty_rejects_unknown_kind_and_invalid_confidence(self) -> None:
        fragment = self.runtime.capture_from_conversation_event(self._event())
        prov_id = fragment["envelope"]["provenance_id"]
        scope_id = "scope_identity_validation"
        self.runtime.ensure_scope(scope_id)
        left = self.runtime.resolve_referent("Validation left")
        right = self.runtime.resolve_referent("Validation right")
        common = {
            "left_referent_id": left["envelope"]["id"],
            "right_referent_id": right["envelope"]["id"],
            "scope_id": scope_id,
            "provenance_id": prov_id,
        }
        event_count_before = len(self.runtime.store.read_events())

        with self.assertRaisesRegex(ContractValidationError, "unsupported identity relation"):
            self.runtime.record_identity_uncertainty(
                **common,
                relation_kind="equivalent_to",
            )
        with self.assertRaisesRegex(ContractValidationError, "between 0 and 1"):
            self.runtime.record_identity_uncertainty(
                **common,
                confidence=1.5,
            )

        self.assertEqual(len(self.runtime.store.read_events()), event_count_before)
        self.assertEqual(self.runtime.current_bundle()["relation_instances"], [])

    def test_identity_uncertainty_visible_in_bounded_view(self) -> None:
        fragment = self.runtime.capture_from_conversation_event(self._event())
        prov_id = fragment["envelope"]["provenance_id"]
        scope_id = "scope_identity_view"
        branch_id = "branch_main"
        self.runtime.ensure_scope(scope_id)
        self.runtime.ensure_branch(branch_id)
        left = self.runtime.resolve_referent("View left")
        right = self.runtime.resolve_referent("View right")
        relation = self.runtime.record_identity_uncertainty(
            left_referent_id=left["envelope"]["id"],
            right_referent_id=right["envelope"]["id"],
            scope_id=scope_id,
            provenance_id=prov_id,
        )

        view = self.runtime.query_bounded_view(
            BoundedViewQuery(
                branch_id=branch_id,
                scope_id=scope_id,
                root_record_ids=[relation["envelope"]["id"]],
                max_depth=2,
            )
        )
        node_ids = {node.record_id for node in view.nodes}
        self.assertIn(left["envelope"]["id"], node_ids)
        self.assertIn(right["envelope"]["id"], node_ids)


if __name__ == "__main__":
    unittest.main()
