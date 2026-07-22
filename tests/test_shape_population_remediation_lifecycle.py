"""Lifecycle and ingest-hook remediation tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conversation_os.shape_population.model_gateway import ShapeModelGateway, StubModelClient
from conversation_os.shape_population.orchestrator import ShapePopulationOrchestrator, enqueue_after_ingest
from conversation_os.shape_population.storage import ShapePopulationStore
from conversation_os.shape_population.worker import run_worker
from conversation_os.source_content_store import SourceContentStore
from conversation_os.vault_ingest import ingest_text_content


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    return tmp_path


def test_post_ingest_hook_enqueues_without_blocking(root: Path) -> None:
    store = ShapePopulationStore(root)

    def hook(path: Path, *, source_id: str):
        return enqueue_after_ingest(source_id, store=store, vault_root=path)

    result = ingest_text_content(
        root,
        title="Shape source",
        content="A mechanism appears when boundary B holds.\n",
        source_ref="manual://shape-1",
        post_ingest_hooks=[hook],
    )
    assert result["source_id"]
    assert result["post_ingest"]["hook_count"] == 1
    assert result["post_ingest"]["receipts"][0]["ok"] is True
    job = result["post_ingest"]["receipts"][0]["result"]
    assert job["state"] == "queued"
    assert job["payload"]["vault_source_id"] == result["source_id"]

    def boom(path: Path, *, source_id: str):
        raise RuntimeError("worker down")

    result2 = ingest_text_content(
        root,
        title="Shape source 2",
        content="Another line.\n",
        source_ref="manual://shape-2",
        post_ingest_hooks=[boom],
    )
    assert result2["source_id"]
    assert result2["post_ingest"]["receipts"][0]["ok"] is False
    assert "worker down" in result2["post_ingest"]["receipts"][0]["error"]


def test_content_store_dedupe_and_source_bytes_once(root: Path) -> None:
    content = SourceContentStore(root)
    raw = b"repeatable payload " * 1000
    a = content.put_bytes(raw)
    b = content.put_bytes(raw)
    assert a == b
    assert content.get_bytes(a) == raw
    blob_dir = root / "product" / "inner_world_v1" / "data" / "source_content"
    files = [p for p in blob_dir.rglob("*") if p.is_file() and p.suffix != ".json"]
    assert len(files) == 1


def _proposal_for_packet(packet: dict) -> dict:
    block = packet["blocks"][0]
    return {
        "packet_id": packet["packet_id"],
        "title": "Boundary mechanism",
        "statement": "A mechanism appears when boundary B holds.",
        "boundary": "boundary B",
        "mechanism": "appearance under B",
        "dimensions": ["causality"],
        "evidence_refs": [
            {
                "packet_id": packet["packet_id"],
                "block_id": block["block_id"],
                "source_id": block["source_id"],
                "segment_id": block["segment_id"],
                "char_start": block["char_start"],
                "char_end": block["char_end"],
                "text_sha256": block["text_sha256"],
            }
        ],
        "counter_hypotheses": ["coincidence"],
        "uncertainty": "medium",
        "recommended_disposition": "proposed",
    }


def test_ingest_enqueue_process_job_materializes_evidence_text(root: Path) -> None:
    store = ShapePopulationStore(root)
    content_store = SourceContentStore(root)
    source_text = "A mechanism appears when boundary B holds.\n"

    def hook(path: Path, *, source_id: str):
        return enqueue_after_ingest(source_id, store=store, vault_root=path)

    ingested = ingest_text_content(
        root,
        title="Worker source",
        content=source_text,
        source_ref="manual://worker-1",
        post_ingest_hooks=[hook],
    )
    vault_source_id = ingested["source_id"]
    assert ingested["content_hash"]
    assert content_store.get_bytes(ingested["content_hash"]) == source_text.encode("utf-8")

    # Queue stub responses: inquiry, propose, critique, synthesize.
    inquiry = {
        "question": "What mechanism is bounded by B?",
        "segment_ids": [],
        "anchors": [vault_source_id],
        "scope": "declared_segments",
    }
    # proposal packet_id filled by orchestrator after inquiry; stub returns without packet_id first —
    # gateway requires packet_id for proposer. Use a client that inspects the last user message.
    class PacketAwareStub:
        def __init__(self) -> None:
            self.calls: list[dict] = []
            self._phase = 0

        def complete(self, messages, *, tools, timeout):
            self.calls.append({"messages": list(messages), "tools": list(tools), "timeout": timeout})
            user = json.loads(messages[2]["content"])
            if self._phase == 0:
                self._phase += 1
                prior = user.get("prior_artifacts") or {}
                quoted = prior.get("SOURCE_DATA_SEGMENTS") or []
                assert quoted, "inquiry must receive verified segment text"
                quoted_text = " ".join(str(item.get("text") or "") for item in quoted).lower()
                assert "mechanism" in quoted_text and "boundary" in quoted_text, quoted_text
                assert "SOURCE_DATA_SEGMENTS_JSON" in str(prior.get("SOURCE_DATA_MATERIALIZED") or "")
                # Intelligence selects a real subset (here: the only available segment).
                payload = dict(inquiry)
                payload["segment_ids"] = [str(item["segment_id"]) for item in quoted]
                return json.dumps(payload)
            if self._phase == 1:
                self._phase += 1
                # Evidence is materialized into SOURCE_DATA_MATERIALIZED
                materialized = user.get("SOURCE_DATA_MATERIALIZED") or ""
                assert "SOURCE_DATA_BLOCKS_JSON" in materialized
                assert "mechanism" in materialized.lower()
                # Reconstruct packet id from blocks refs
                blocks = user.get("SOURCE_DATA_BLOCKS") or []
                packet_id = blocks[0]["packet_id"] if blocks else "pkt"
                proposal = _proposal_for_packet(
                    {
                        "packet_id": packet_id,
                        "blocks": [dict(blocks[0])],
                    }
                )
                return json.dumps(proposal)
            if self._phase == 2:
                self._phase += 1
                candidate = (user.get("prior_artifacts") or {}).get("candidate") or {}
                return json.dumps(
                    {
                        "candidate_id": candidate.get("candidate_id"),
                        "disposition": "under_review",
                        "critique": "Needs synthesis.",
                        "evidence_refs": candidate.get("evidence_refs") or [],
                        "uncertainty": "medium",
                        "relationship_findings": [],
                    }
                )
            candidate = (user.get("prior_artifacts") or {}).get("candidate") or {}
            return json.dumps(
                {
                    "candidate_id": candidate.get("candidate_id"),
                    "disposition": "recommended",
                    "critique": "Grounded.",
                    "evidence_refs": candidate.get("evidence_refs") or [],
                    "uncertainty": "low",
                    "relationship_findings": [],
                }
            )

    client = PacketAwareStub()
    gateway = ShapeModelGateway(client, content_store=content_store, store=store, repair_attempts=0)
    orchestrator = ShapePopulationOrchestrator(
        store=store,
        gateway=gateway,
        content_store=content_store,
        vault_root=root,
    )
    outcome = orchestrator.run_once()
    assert outcome is not None
    assert outcome["state"] == "completed", outcome.get("last_error")
    assert outcome["result"]["vault_source_id"] == vault_source_id
    assert outcome["result"]["candidate_id"]
    assert outcome["result"]["comparison_set_version"]
    assert store.get_comparison_set(outcome["result"]["comparison_set_version"]) is not None
    shape_source = store.get_source(outcome["result"]["source_id"])
    assert shape_source is not None
    assert shape_source["content_sha256"] == ingested["content_hash"]
    assert len(client.calls) >= 3
    inquire_user = json.loads(client.calls[0]["messages"][2]["content"])
    assert inquire_user["prior_artifacts"]["SOURCE_DATA_SEGMENTS"][0]["text"]
    propose_user = json.loads(client.calls[1]["messages"][2]["content"])
    assert propose_user["SOURCE_DATA_MATERIALIZED"]
    assert "quoted source data" in propose_user["SOURCE_DATA_MATERIALIZED"].lower() or "SOURCE_DATA_BLOCKS_JSON" in propose_user["SOURCE_DATA_MATERIALIZED"]


def test_vault_bridge_requires_original_bytes_not_chunk_reconstruction(root: Path) -> None:
    from conversation_os.shape_population.contracts import ValidationError
    from conversation_os.shape_population.vault_bridge import load_vault_source_bytes, source_request_from_vault

    # Registry-only source without content-store bytes must fail closed.
    store = ShapePopulationStore(root)
    ingested = ingest_text_content(
        root,
        title="Lossless",
        content="Exact original bytes must survive.\n",
        source_ref="manual://lossless-1",
    )
    raw, entry = load_vault_source_bytes(root, ingested["source_id"])
    assert raw == b"Exact original bytes must survive.\n"
    assert entry["content_hash"] == ingested["content_hash"]
    request = source_request_from_vault(root, ingested["source_id"])
    assert request["content_sha256"] == ingested["content_hash"]
    assert request["metadata"]["lossless_original"] is True

    # Remove blob and ensure bridge does not fall back to lossy chunk join.
    blob = root / "product" / "inner_world_v1" / "data" / "source_content"
    for path in blob.rglob("*"):
        if path.is_file() and path.suffix != ".json":
            path.unlink()
    with pytest.raises(ValidationError, match="original vault source bytes unavailable"):
        load_vault_source_bytes(root, ingested["source_id"])
    _ = store  # keep fixture root owned by Shape store path conventions


def test_worker_cli_processes_queued_job(root: Path) -> None:
    store = ShapePopulationStore(root)
    content_store = SourceContentStore(root)

    def hook(path: Path, *, source_id: str):
        return enqueue_after_ingest(source_id, store=store, vault_root=path)

    ingest_text_content(
        root,
        title="CLI source",
        content="CLI mechanism under boundary.\n",
        source_ref="manual://cli-1",
        post_ingest_hooks=[hook],
    )

    class SimpleStub:
        def __init__(self) -> None:
            self.n = 0

        def complete(self, messages, *, tools, timeout):
            user = json.loads(messages[2]["content"])
            self.n += 1
            if self.n == 1:
                segments = (user.get("prior_artifacts") or {}).get("segments") or []
                return json.dumps(
                    {
                        "question": "What shape?",
                        "segment_ids": [str(item["segment_id"]) for item in segments],
                        "anchors": ["cli"],
                        "scope": "declared_segments",
                    }
                )
            if self.n == 2:
                blocks = user.get("SOURCE_DATA_BLOCKS") or []
                packet_id = blocks[0]["packet_id"]
                return json.dumps(_proposal_for_packet({"packet_id": packet_id, "blocks": blocks}))
            candidate = (user.get("prior_artifacts") or {}).get("candidate") or {}
            disposition = "under_review" if self.n == 3 else "recommended"
            return json.dumps(
                {
                    "candidate_id": candidate.get("candidate_id"),
                    "disposition": disposition,
                    "critique": "ok",
                    "evidence_refs": candidate.get("evidence_refs") or [],
                    "uncertainty": "low",
                    "relationship_findings": [],
                }
            )

    gateway = ShapeModelGateway(SimpleStub(), content_store=content_store, store=store, repair_attempts=0)
    result = run_worker(root, limit=1, gateway=gateway)
    assert result["processed"] == 1
    assert result["results"][0]["state"] == "completed"


def test_rejected_promotion_is_terminal(root: Path) -> None:
    from conversation_os.shape_population.candidate_submission import submit_candidate
    from conversation_os.shape_population.contracts import IdempotencyConflictError
    from conversation_os.shape_population.critique import submit_evaluation
    from conversation_os.shape_population.evidence import build_evidence_packet
    from conversation_os.shape_population.execution_context import agent_context, human_context
    from conversation_os.shape_population.identities import (
        CRITIC_IDENTITY,
        EVALUATOR_IDENTITY,
        HUMAN_APPROVER_ROLE,
        PROPOSER_IDENTITY,
    )
    from conversation_os.shape_population.normalization import normalize_source
    from conversation_os.shape_population.promotion import apply_promotion, record_human_decision, request_promotion

    store = ShapePopulationStore(root)
    normalized = normalize_source(
        {"content": "Evidence for a clear mechanism.\n", "modality": "plain_text"},
        store=store,
    )
    ctx_inq = agent_context(
        PROPOSER_IDENTITY,
        capabilities={"shape.evidence.inquire", "shape.candidate.submit"},
    )
    packet = build_evidence_packet(
        {
            "segment_ids": [seg.segment_id for seg in normalized.segments],
            "evidence_inquiry": {"question": "shape?", "requested_by": PROPOSER_IDENTITY},
        },
        store=store,
        context=ctx_inq,
    )
    refs = []
    for block in packet.blocks:
        segment = store.get_segment(block.segment_id)
        refs.append(
            {
                "packet_id": packet.packet_id,
                "block_id": block.block_id,
                "source_id": block.source_id,
                "segment_id": block.segment_id,
                "char_start": block.char_start,
                "char_end": block.char_end,
                "text_sha256": segment["text_sha256"],
            }
        )
    cand = submit_candidate(
        {
            "packet_id": packet.packet_id,
            "title": "Mech",
            "statement": "A causes B",
            "boundary": "B",
            "mechanism": "A->B",
            "dimensions": ["causality"],
            "evidence_refs": refs,
            "counter_hypotheses": ["alt"],
            "uncertainty": "low",
            "recommended_disposition": "proposed",
            "idempotency_key": "term-1",
        },
        store=store,
        context=agent_context(PROPOSER_IDENTITY, capabilities={"shape.candidate.submit"}, run_id="t1", model_id="m", prompt_version="p"),
    )["candidate"]
    evaluation = submit_evaluation(
        {
            "candidate_id": cand["candidate_id"],
            "disposition": "recommended",
            "critique": "ok",
            "evidence_refs": refs,
            "uncertainty": "low",
            "relationship_findings": [],
            "idempotency_key": "term-eval",
        },
        store=store,
        context=agent_context(
            CRITIC_IDENTITY,
            capabilities={"shape.evaluation.submit", "shape.comparison.read"},
            run_id="t2",
            model_id="m",
            prompt_version="p",
        ),
    )["evaluation"]
    requested = request_promotion(
        cand["candidate_id"],
        evaluation["evaluation_id"],
        "ready",
        refs,
        store=store,
        context=agent_context(EVALUATOR_IDENTITY, capabilities={"shape.promotion.request"}, run_id="t3", model_id="m", prompt_version="p"),
        idempotency_key="term-prom",
    )
    request_id = requested["request"]["request_id"]
    record_human_decision(
        request_id,
        store=store,
        approval_reason="not ready",
        decision="rejected",
        context=human_context(HUMAN_APPROVER_ROLE, capabilities={"shape.promotion.approve"}),
    )
    with pytest.raises(IdempotencyConflictError):
        record_human_decision(
            request_id,
            store=store,
            approval_reason="flip flop",
            decision="approved",
            context=human_context(HUMAN_APPROVER_ROLE, capabilities={"shape.promotion.approve"}),
        )
    with pytest.raises(Exception):
        apply_promotion(
            request_id,
            store=store,
            context=human_context(
                "shape.canonical_authority",
                capabilities={"shape.promotion.apply", "shape.promotion.approve"},
            ),
        )
