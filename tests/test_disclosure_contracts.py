from __future__ import annotations

import json
import unittest
from pathlib import Path

from conversation_os.disclosure_contracts import (
    CONTRACT_VERSION,
    RESULT_STATUSES,
    ApertureRequest,
    ActiveStateSnapshot,
    AuditReceipt,
    CandidateRef,
    ContractValidationError,
    EffectiveGrant,
    EvidenceBlock,
    ExecutionBundle,
    RequestedGrant,
    contract_field_catalog,
    envelope_defaults,
    normalize_effective_grant,
    receipt_retention_for_envelope,
    validate_audit_receipt,
    validate_execution_bundle,
)

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "disclosure_contracts" / "v1"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8"))


class DisclosureContractsTestCase(unittest.TestCase):
    def test_fixture_round_trip_all_contracts(self) -> None:
        models = [
            (ApertureRequest, "aperture_request.json"),
            (ActiveStateSnapshot, "active_state_snapshot.json"),
            (RequestedGrant, "requested_grant.json"),
            (EffectiveGrant, "effective_grant.json"),
            (CandidateRef, "candidate_ref.json"),
            (EvidenceBlock, "evidence_block.json"),
            (ExecutionBundle, "execution_bundle.json"),
            (AuditReceipt, "audit_receipt_disclosed.json"),
        ]
        for model_cls, filename in models:
            payload = _load_fixture(filename)
            restored = model_cls.from_dict(payload)
            self.assertEqual(restored.to_dict(), payload, filename)

    def test_contract_field_catalog_documents_nullability_and_forbidden_keys(self) -> None:
        catalog = contract_field_catalog()
        self.assertEqual(catalog["contract_version"], CONTRACT_VERSION)
        self.assertIn("ApertureRequest", catalog["contracts"])
        execution_spec = catalog["contracts"]["ExecutionBundle"]
        self.assertIn("forbidden_keys", execution_spec)
        self.assertIn("suppressed", execution_spec["forbidden_keys"])
        self.assertEqual(set(catalog["result_statuses"]), set(RESULT_STATUSES))

    def test_envelope_defaults_match_design_matrix(self) -> None:
        bounded = envelope_defaults("bounded")
        self.assertEqual(bounded["default_layers"], ["session", "workspace"])
        self.assertFalse(bounded["cross_ocean"])
        self.assertEqual(bounded["receipt_retention"], "normal_policy")

        incognito = envelope_defaults("incognito")
        self.assertEqual(incognito["default_layers"], ["ephemeral_turn"])
        self.assertEqual(incognito["persistence_mode"], "disabled")
        self.assertEqual(receipt_retention_for_envelope("incognito"), "hashes_metrics_only")

    def test_deny_precedence_removes_explicitly_denied_layers(self) -> None:
        requested = RequestedGrant.from_dict(_load_fixture("requested_grant.json"))
        effective = normalize_effective_grant(requested)

        self.assertNotIn("user", effective.effective_layers)
        self.assertTrue(effective.deny_precedence_applied)
        self.assertTrue(any(reason["code"] == "explicit_deny" for reason in effective.narrowing_reasons))

    def test_model_bound_payload_rejects_suppression_fields(self) -> None:
        from conversation_os.disclosure_contracts import validate_model_bound_payload

        with self.assertRaises(ContractValidationError) as ctx:
            validate_model_bound_payload({"omitted_blocks": [{"reason": "layer_not_disclosed"}]})
        self.assertEqual(ctx.exception.code, "suppression_field_forbidden")

    def test_execution_bundle_rejects_suppression_fields(self) -> None:
        payload = _load_fixture("execution_bundle.json")
        payload["suppressed_layers"] = ["user"]
        with self.assertRaises(ContractValidationError) as ctx:
            validate_execution_bundle(payload)
        self.assertEqual(ctx.exception.code, "suppression_field_forbidden")

        with self.assertRaises(ContractValidationError):
            ExecutionBundle.from_dict(payload)

    def test_execution_bundle_from_dict_validates_by_default(self) -> None:
        bundle = ExecutionBundle.from_dict(_load_fixture("execution_bundle.json"))
        self.assertEqual(bundle.request_id, "req-cae015-aperture")
        self.assertEqual(len(bundle.evidence_blocks), 1)

    def test_audit_receipt_incognito_allows_hashes_only(self) -> None:
        receipt = AuditReceipt.from_dict(_load_fixture("audit_receipt_incognito.json"))
        self.assertEqual(receipt.retention_mode, "hashes_metrics_only")
        self.assertFalse(receipt.sensitive_text_included)
        self.assertEqual(receipt.result_status, "empty_grant_excludes_all")

    def test_audit_receipt_incognito_rejects_sensitive_text_flag(self) -> None:
        payload = _load_fixture("audit_receipt_incognito.json")
        payload["sensitive_text_included"] = True
        with self.assertRaises(ContractValidationError) as ctx:
            validate_audit_receipt(payload, envelope="incognito")
        self.assertEqual(ctx.exception.code, "incognito_sensitive_text_forbidden")

    def test_backward_compatible_legacy_fixture_loads_with_defaults(self) -> None:
        payload = _load_fixture("aperture_request_legacy_v0_9.json")
        request = ApertureRequest.from_dict(payload)
        self.assertEqual(request.request_id, "req-cae015-legacy")
        self.assertEqual(request.explicit_pins, [])
        self.assertEqual(request.requested_depth, "focused")

    def test_forward_compatible_unknown_fields_do_not_break_loading(self) -> None:
        payload = _load_fixture("aperture_request.json")
        payload["future_field"] = "kept-for-forward-compat"
        request = ApertureRequest.from_dict(payload)
        self.assertEqual(request.request_id, payload["request_id"])
        self.assertNotIn("future_field", request.to_dict())

    def test_public_contracts_contain_no_storage_provider_fields(self) -> None:
        forbidden_tokens = ("sqlite", "vector_store", "embedding_provider", "s3_bucket")
        catalog = contract_field_catalog()
        serialized = json.dumps(catalog).lower()
        for token in forbidden_tokens:
            self.assertNotIn(token, serialized)

    def test_result_status_fixture_matches_contract(self) -> None:
        payload = _load_fixture("result_statuses.json")
        self.assertEqual(set(payload["statuses"]), set(RESULT_STATUSES))


if __name__ == "__main__":
    unittest.main()
