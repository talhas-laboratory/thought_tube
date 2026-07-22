from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.corpus_catalog_snapshot import publish_corpus_catalog_snapshot
from conversation_os.disclosure_ports import build_inner_world_ports
from conversation_os.disclosure_receipts import build_audit_receipt, reconstruct_disclosure_result
from conversation_os.evidence_resolver import (
    build_evidence_ref,
    resolve_frame_blocks,
)
from conversation_os.library_tracker import build_corpus_catalog
from conversation_os.shape_candidate_retrieval import CAP_EVIDENCE_RESOLVE
from conversation_os.storage import read_jsonl
from conversation_os.vault_ingest import ingest_text_content


class EvidenceResolverTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "disclosure": {
                        "bounded_evidence_resolution_v1": True,
                        "evidence_resolver": {"bounded_evidence_resolution_v1": True},
                    }
                }
            ),
            encoding="utf-8",
        )
        (self.root / "product" / "inner_world_v1" / "data").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _ingest_fixture(self) -> dict:
        return ingest_text_content(
            self.root,
            title="evidence-resolver-fixture",
            content="# User\n\nResolver fixture content for bounded evidence.\n",
            source_ref="fixture:evidence-resolver",
            source_type="chat_converter_conversation",
            metadata={"branch_id": "branch-evidence", "scope_id": "scope-evidence"},
        )

    def _chunk_row(self) -> dict:
        chunks = read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "chunk_index.jsonl")
        self.assertGreaterEqual(len(chunks), 1)
        return chunks[0]

    def _source_row(self) -> dict:
        sources = read_jsonl(self.root / "product" / "inner_world_v1" / "data" / "source_registry.jsonl")
        self.assertGreaterEqual(len(sources), 1)
        return sources[0]

    def _grant(self, *, corpus_revision: str = "", refs: list[str] | None = None) -> dict:
        return {
            "grant_id": "grant-evidence-001",
            "request_id": "req-evidence-001",
            "envelope": "bounded",
            "effective_layers": ["global"],
            "effective_refs": list(refs or []),
            "token_budget": 1200,
            "authorization": {
                "principal_id": "evidence-resolver-agent",
                "principal_kind": "service",
                "authenticated_by": "unit-test",
                "capabilities": [CAP_EVIDENCE_RESOLVE],
            },
            "provenance": {
                "branch_id": "branch-evidence",
                "scope_id": "scope-evidence",
                "corpus_revision": corpus_revision,
                "byte_budget": 4096,
            },
        }

    def test_resolves_admitted_span_with_point_lookup(self) -> None:
        self._ingest_fixture()
        publish_corpus_catalog_snapshot(self.root)
        catalog = build_corpus_catalog(self.root)
        chunk = self._chunk_row()
        source = self._source_row()
        evidence_ref = build_evidence_ref(
            source_id=source["source_id"],
            fragment_id=chunk["chunk_id"],
            content_hash=__import__("hashlib").sha256(str(chunk["content"]).encode("utf-8")).hexdigest(),
            corpus_revision=catalog["corpus_revision"],
            branch_id="branch-evidence",
            scope_id="scope-evidence",
            source_ref=source["source_ref"],
        )
        blocks = [
            {
                "block_id": "block-001",
                "layer": "global",
                "summary": "compact reference",
                "evidence_ref": evidence_ref,
            }
        ]

        with mock.patch("conversation_os.vault_ingest.load_chunk_index_raw") as chunk_loader:
            result = resolve_frame_blocks(self.root, included_blocks=blocks, effective_grant=self._grant())
        chunk_loader.assert_not_called()

        resolved = result["resolved_blocks"]
        audit = result["resolution_audit"]
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["resolution_status"], "resolved")
        self.assertIn("Resolver fixture content", resolved[0]["bounded_text"])
        self.assertEqual(audit["lookup_count"], 1)
        self.assertGreater(audit["bytes_resolved"], 0)
        self.assertEqual(len(audit["included_spans"]), 1)

    def test_legacy_blocks_passthrough_without_lookup(self) -> None:
        blocks = [{"block_id": "block-legacy", "layer": "session", "summary": "session summary"}]
        result = resolve_frame_blocks(self.root, included_blocks=blocks, effective_grant=self._grant())
        self.assertEqual(result["resolved_blocks"][0]["resolution_status"], "reference_only")
        self.assertEqual(result["resolution_audit"]["lookup_count"], 0)

    def test_tampered_hash_is_omitted(self) -> None:
        self._ingest_fixture()
        chunk = self._chunk_row()
        source = self._source_row()
        evidence_ref = build_evidence_ref(
            source_id=source["source_id"],
            fragment_id=chunk["chunk_id"],
            content_hash="0" * 64,
            corpus_revision="rev",
        )
        result = resolve_frame_blocks(
            self.root,
            included_blocks=[{"block_id": "block-bad-hash", "evidence_ref": evidence_ref}],
            effective_grant=self._grant(),
        )
        self.assertEqual(result["resolved_blocks"], [])
        self.assertEqual(result["resolution_audit"]["omitted"][0]["reason_code"], "hash_mismatch")

    def test_missing_span_is_omitted(self) -> None:
        result = resolve_frame_blocks(
            self.root,
            included_blocks=[
                {
                    "block_id": "block-missing",
                    "evidence_ref": build_evidence_ref(
                        source_id="source-missing",
                        fragment_id="chunk-missing",
                        content_hash="a" * 64,
                        corpus_revision="rev",
                    ),
                }
            ],
            effective_grant=self._grant(),
        )
        self.assertEqual(result["resolution_audit"]["omitted"][0]["reason_code"], "missing_span")

    def test_denied_ref_is_omitted(self) -> None:
        self._ingest_fixture()
        chunk = self._chunk_row()
        source = self._source_row()
        content_hash = __import__("hashlib").sha256(str(chunk["content"]).encode("utf-8")).hexdigest()
        evidence_ref = build_evidence_ref(
            source_id=source["source_id"],
            fragment_id=chunk["chunk_id"],
            content_hash=content_hash,
            corpus_revision="rev",
            source_ref=source["source_ref"],
        )
        result = resolve_frame_blocks(
            self.root,
            included_blocks=[{"block_id": "block-denied", "evidence_ref": evidence_ref}],
            effective_grant=self._grant(refs=["fixture:other-ref"]),
        )
        self.assertEqual(result["resolution_audit"]["omitted"][0]["reason_code"], "denied_ref")

    def test_stale_revision_is_omitted(self) -> None:
        self._ingest_fixture()
        chunk = self._chunk_row()
        source = self._source_row()
        content_hash = __import__("hashlib").sha256(str(chunk["content"]).encode("utf-8")).hexdigest()
        evidence_ref = build_evidence_ref(
            source_id=source["source_id"],
            fragment_id=chunk["chunk_id"],
            content_hash=content_hash,
            corpus_revision="stale-revision",
        )
        result = resolve_frame_blocks(
            self.root,
            included_blocks=[{"block_id": "block-stale", "evidence_ref": evidence_ref}],
            effective_grant=self._grant(corpus_revision="current-revision"),
        )
        self.assertEqual(result["resolution_audit"]["omitted"][0]["reason_code"], "stale_revision")

    def test_budget_stops_whole_block_inclusion(self) -> None:
        self._ingest_fixture()
        chunk = self._chunk_row()
        source = self._source_row()
        content_hash = __import__("hashlib").sha256(str(chunk["content"]).encode("utf-8")).hexdigest()
        evidence_ref = build_evidence_ref(
            source_id=source["source_id"],
            fragment_id=chunk["chunk_id"],
            content_hash=content_hash,
            corpus_revision="rev",
        )
        grant = self._grant()
        grant["provenance"]["byte_budget"] = 1
        result = resolve_frame_blocks(
            self.root,
            included_blocks=[{"block_id": "block-budget", "evidence_ref": evidence_ref}],
            effective_grant=grant,
        )
        self.assertEqual(result["resolution_audit"]["omitted"][0]["reason_code"], "budget_insufficient")

    def test_receipt_reconstruction_identifies_spans_without_text(self) -> None:
        receipt = build_audit_receipt(
            request_id="req-evidence-001",
            surface="bridge",
            result_status="disclosed",
            effective_grant=self._grant(),
            frame_bundle={"included_blocks": [{"block_id": "block-001"}]},
            metrics={
                "included_span_ids": ["chunk-abc123"],
                "bytes_resolved": 42,
                "evidence_lookup_count": 1,
            },
        )
        reconstructed = reconstruct_disclosure_result(receipt)
        self.assertEqual(reconstructed["included_span_ids"], ["chunk-abc123"])
        self.assertNotIn("bounded_text", json.dumps(reconstructed))

    def test_ports_delegate_to_bounded_resolver(self) -> None:
        self._ingest_fixture()
        chunk = self._chunk_row()
        source = self._source_row()
        content_hash = __import__("hashlib").sha256(str(chunk["content"]).encode("utf-8")).hexdigest()
        ports = build_inner_world_ports()
        result = ports.evidence_resolver.resolve_frame_blocks(
            self.root,
            included_blocks=[
                {
                    "block_id": "block-port",
                    "evidence_ref": build_evidence_ref(
                        source_id=source["source_id"],
                        fragment_id=chunk["chunk_id"],
                        content_hash=content_hash,
                        corpus_revision="rev",
                        source_ref=source["source_ref"],
                    ),
                }
            ],
            effective_grant=self._grant(refs=[source["source_ref"]]),
        )
        self.assertEqual(result["resolved_blocks"][0]["resolution_status"], "resolved")

    def test_port_denies_without_authorization_and_does_not_resolve_text(self) -> None:
        self._ingest_fixture()
        chunk = self._chunk_row()
        source = self._source_row()
        content_hash = __import__("hashlib").sha256(str(chunk["content"]).encode("utf-8")).hexdigest()
        grant = self._grant(refs=[source["source_ref"]])
        grant.pop("authorization")
        ports = build_inner_world_ports()
        block = {
            "block_id": "block-port-denied",
            "evidence_ref": build_evidence_ref(
                source_id=source["source_id"],
                fragment_id=chunk["chunk_id"],
                content_hash=content_hash,
                corpus_revision="rev",
                source_ref=source["source_ref"],
            ),
        }
        with mock.patch("conversation_os.evidence_resolver.resolve_frame_blocks") as resolver:
            result = ports.evidence_resolver.resolve_frame_blocks(
                self.root,
                included_blocks=[block],
                effective_grant=grant,
            )
        resolver.assert_not_called()
        self.assertEqual(result["resolved_blocks"], [])
        audit = result["resolution_audit"]
        self.assertEqual(audit["authorization"]["reason_code"], "missing_principal")
        self.assertEqual(audit["omitted"][0]["reason_code"], "authorization_denied")
        self.assertNotIn("Resolver fixture content", json.dumps(result))
