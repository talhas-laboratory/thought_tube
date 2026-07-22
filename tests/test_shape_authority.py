from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from conversation_os.metaphysical_kernel_application_sdk import (
    ApplicationContext,
    FoundationApplicationSdk,
    WORLD_STUDIO_APPLICATION_ID,
)
from conversation_os.metaphysical_kernel_profile_registry import (
    FIELD_FORMATION_PROFILE_ID,
    FIELD_FORMATION_PROFILE_VERSION,
    SHAPE_PROFILE_ID,
    SHAPE_PROFILE_VERSION,
    ProfileRegistry,
)
from conversation_os.metaphysical_kernel_runtime import FoundationRuntime
from conversation_os.shape_projection_reader import (
    CANONICAL_SHAPE_PROFILE_ID,
    LEGACY_SHAPE_PROFILE_ID,
    migration_decision,
    read_shape_projections,
)


class ShapeAuthorityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _sdk(self, *, authorized: bool = True) -> FoundationApplicationSdk:
        return FoundationApplicationSdk(
            self.root,
            ApplicationContext(
                application_id=WORLD_STUDIO_APPLICATION_ID,
                actor="agent:shape-authority-test",
                branch_id="branch:shape-authority",
                scope_id="scope:shape-authority",
                profile_id=FIELD_FORMATION_PROFILE_ID,
                profile_version=FIELD_FORMATION_PROFILE_VERSION,
                authorized=authorized,
            ),
        )

    def test_canonical_id_is_profile_shape_not_legacy(self) -> None:
        self.assertEqual(CANONICAL_SHAPE_PROFILE_ID, SHAPE_PROFILE_ID)
        self.assertNotEqual(CANONICAL_SHAPE_PROFILE_ID, LEGACY_SHAPE_PROFILE_ID)
        decision = migration_decision()
        self.assertEqual(decision["canonical_profile_id"], SHAPE_PROFILE_ID)
        self.assertEqual(decision["legacy_profile_id"], LEGACY_SHAPE_PROFILE_ID)
        self.assertFalse(decision["promotion_allowed"])

    def test_bootstrap_registers_shape_on_foundation_runtime(self) -> None:
        registry = ProfileRegistry(FoundationRuntime(self.root))
        payload = registry.bootstrap_shape_profile()
        profile = registry.get_profile(SHAPE_PROFILE_ID)

        self.assertEqual(payload["profile_id"], SHAPE_PROFILE_ID)
        self.assertIsNotNone(profile)
        assert profile is not None
        self.assertEqual(profile.profile_version, SHAPE_PROFILE_VERSION)

        read = read_shape_projections(self.root, include_legacy=False)
        self.assertTrue(read["canonical"]["available"])
        self.assertEqual(read["canonical"]["profile_id"], SHAPE_PROFILE_ID)
        self.assertEqual(read["canonical"]["abstention_code"], "empty")

    def test_derive_shape_uses_profile_shape_readiness(self) -> None:
        sdk = self._sdk()
        capture = sdk.capture_source(
            content_pointer="world-studio://shape-authority",
            integrity_hash="sha256:shape-authority",
        )
        claim = sdk.assert_claim(
            predicate="candidate_shape",
            arguments=["anchor"],
            provenance_id=capture.provenance_id,
        )
        result = sdk.derive_shape(anchor_claim_id=claim.record_ids["claim_id"])

        self.assertTrue(result.abstained)
        self.assertIn(SHAPE_PROFILE_ID, result.reason)
        self.assertNotIn(LEGACY_SHAPE_PROFILE_ID, result.reason)
        self.assertTrue(result.reason.startswith("empty:"))
        self.assertIsNotNone(sdk.registry.get_profile(SHAPE_PROFILE_ID))
        self.assertEqual(sdk.runtime.validate_current_bundle(), [])

    def test_derive_shape_unauthorized_is_typed(self) -> None:
        sdk = self._sdk(authorized=False)
        result = sdk.derive_shape(anchor_claim_id="claim:x")
        self.assertTrue(result.abstained)
        self.assertEqual(result.reason, "authorization_denied")


if __name__ == "__main__":
    unittest.main()
