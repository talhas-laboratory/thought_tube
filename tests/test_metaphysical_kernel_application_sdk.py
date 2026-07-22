from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from conversation_os.metaphysical_kernel_application_sdk import (
    WORLD_STUDIO_APPLICATION_ID,
    WORKSPACE_CURATOR_APPLICATION_ID,
    ApplicationContext,
    FoundationApplicationSdk,
    world_studio_capture_scene,
    workspace_curator_capture_insight,
)


class MetaphysicalKernelApplicationSdkTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.root = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _world_sdk(self) -> FoundationApplicationSdk:
        return FoundationApplicationSdk(
            self.root,
            ApplicationContext(
                application_id=WORLD_STUDIO_APPLICATION_ID,
                actor="user:worldbuilder",
                branch_id="branch_world_alpha",
                scope_id="scope_fictional",
            ),
        )

    def _curator_sdk(self) -> FoundationApplicationSdk:
        return FoundationApplicationSdk(
            self.root,
            ApplicationContext(
                application_id=WORKSPACE_CURATOR_APPLICATION_ID,
                actor="user:curator",
                branch_id="branch_workspace_main",
                scope_id="scope_workspace_unified",
            ),
        )

    def test_world_studio_consumer_uses_shared_kernel_without_private_ontology(self) -> None:
        result = world_studio_capture_scene(
            self._world_sdk(),
            world_id="world-aurora",
            scene_text="A harbor city under violet fog.",
            element_label="Harbor district",
        )
        self.assertEqual(result["application"], WORLD_STUDIO_APPLICATION_ID)
        self.assertTrue(result["capture"]["success"])
        self.assertTrue(result["claim"]["success"])
        self.assertEqual(result["formation"]["projection"]["profile_record_type"], "formation")
        self.assertTrue(result["provenance_trace"]["projection"]["complete"])
        self.assertTrue(result["validation"]["projection"]["passed"])

    def test_workspace_curator_consumer_can_commit_state(self) -> None:
        result = workspace_curator_capture_insight(
            self._curator_sdk(),
            workspace_id="unified-framework-synthesis",
            statement="Kernel contracts precede profile implementation.",
            adopt_as_state=True,
        )
        self.assertEqual(result["application"], WORKSPACE_CURATOR_APPLICATION_ID)
        self.assertTrue(result["capture"]["success"])
        self.assertIn("adoption", result)
        self.assertTrue(result["adoption"]["success"])
        self.assertEqual(result["hold"]["projection"]["profile_record_type"], "hold")

    def test_two_consumers_share_canonical_store_and_profile(self) -> None:
        world = world_studio_capture_scene(
            self._world_sdk(),
            world_id="world-beta",
            scene_text="Desert observatory at dusk.",
            element_label="Observatory",
        )
        curator = workspace_curator_capture_insight(
            self._curator_sdk(),
            workspace_id="unified-framework-synthesis",
            statement="Two applications can share the kernel.",
        )
        self.assertTrue(world["validation"]["projection"]["passed"])
        self.assertTrue(curator["validation"]["projection"]["passed"])

        runtime = self._world_sdk().runtime
        bundle = runtime.current_bundle()
        self.assertGreaterEqual(len(bundle["source_fragments"]), 2)
        self.assertGreaterEqual(len(bundle["claims"]), 2)
        self.assertEqual(runtime.validate_current_bundle(), [])

    def test_unauthorized_application_abstains_without_corrupting_bundle(self) -> None:
        sdk = FoundationApplicationSdk(
            self.root,
            ApplicationContext(
                application_id="app:denied",
                actor="user:denied",
                branch_id="branch_denied",
                scope_id="scope_denied",
                authorized=False,
            ),
        )
        before = len(sdk.runtime.current_bundle()["source_fragments"])
        result = sdk.capture_source(
            content_pointer="memory://denied",
            integrity_hash="sha256:denied",
        )
        after = len(sdk.runtime.current_bundle()["source_fragments"])
        self.assertTrue(result.abstained)
        self.assertFalse(result.success)
        self.assertEqual(before, after)

    def test_context_budget_abstains_before_projection(self) -> None:
        sdk = FoundationApplicationSdk(
            self.root,
            ApplicationContext(
                application_id=WORLD_STUDIO_APPLICATION_ID,
                actor="user:worldbuilder",
                branch_id="branch_budget",
                scope_id="scope_budget",
                context_budget=1,
            ),
        )
        first = sdk.capture_source(
            content_pointer="world-studio://budget/1",
            integrity_hash="sha256:1",
        )
        second = sdk.build_bounded_view(root_record_ids=[first.record_ids["source_fragment_id"]])
        self.assertTrue(first.success)
        self.assertTrue(second.abstained)
        self.assertEqual(second.reason, "context_budget_exceeded")

    def test_derive_shape_abstains_without_corrupting_canonical_records(self) -> None:
        sdk = self._world_sdk()
        capture = sdk.capture_source(
            content_pointer="world-studio://shape",
            integrity_hash="sha256:shape",
        )
        claim = sdk.assert_claim(
            predicate="candidate_shape",
            arguments=["anchor"],
            provenance_id=capture.provenance_id,
        )
        shape = sdk.derive_shape(anchor_claim_id=claim.record_ids["claim_id"])
        self.assertTrue(shape.abstained)
        self.assertIn("profile:shape", shape.reason)
        self.assertNotIn("profile:shape_and_semantic_addressing", shape.reason)
        self.assertEqual(sdk.runtime.validate_current_bundle(), [])

    def test_sdk_mutations_return_compensating_operations(self) -> None:
        sdk = self._curator_sdk()
        capture = sdk.capture_source(
            content_pointer="workspace://compensation",
            integrity_hash="sha256:comp",
        )
        self.assertTrue(capture.compensating_operation.startswith("retract:"))
        trace = sdk.trace_provenance(start_record_id=capture.record_ids["source_fragment_id"])
        self.assertEqual(trace.compensating_operation, "none_required")


if __name__ == "__main__":
    unittest.main()
