from __future__ import annotations

import json

import pytest

from conversation_os.shape_population.contracts import ValidationError
from conversation_os.shape_population.execution_context import CAP_CANDIDATE_SUBMIT, CAP_PROMOTION_REQUEST, agent_context
from conversation_os.shape_population.identities import EVALUATOR_IDENTITY, PROPOSER_IDENTITY
from conversation_os.shape_population.model_gateway import ShapeModelGateway, StubModelClient


def _packet() -> dict:
    return {
        "packet_id": "pkt-1",
        "blocks": [
            {
                "block_id": "blk-1",
                "source_id": "src-1",
                "segment_id": "seg-1",
                "char_start": 0,
                "char_end": 10,
                "text_sha256": "abc",
                "text": "quoted text",
            }
        ],
    }


def test_gateway_routes_role_tools_and_typed_source_blocks() -> None:
    response = {
        "packet_id": "pkt-1",
        "title": "Shape",
        "statement": "A bounded claim.",
        "boundary": "B",
        "mechanism": "M",
        "dimensions": ["d"],
        "evidence_refs": [{"packet_id": "pkt-1", "block_id": "blk-1"}],
        "counter_hypotheses": ["alt"],
        "uncertainty": "low",
        "recommended_disposition": "proposed",
    }
    client = StubModelClient([json.dumps(response)])
    gateway = ShapeModelGateway(client, timeout=12, repair_attempts=0)
    ctx = agent_context(PROPOSER_IDENTITY, capabilities=(CAP_CANDIDATE_SUBMIT,), model_id="m", prompt_version="p")

    assert gateway.propose(evidence_packet=_packet(), context=ctx) == response
    assert client.calls[0]["tools"] == ["submit_candidate"]
    assert client.calls[0]["timeout"] == 12
    user_payload = json.loads(client.calls[0]["messages"][2]["content"])
    assert user_payload["SOURCE_DATA_BLOCKS"][0]["instruction_authority"] is False


def test_gateway_rejects_prose_fences_unknown_and_trusted_fields() -> None:
    ctx = agent_context(PROPOSER_IDENTITY, capabilities=(CAP_CANDIDATE_SUBMIT,), model_id="m", prompt_version="p")
    for raw in (
        "Here is JSON: {}",
        "```json\n{}\n```",
        json.dumps({"packet_id": "pkt-1", "agent_identity": "shape.critic"}),
        json.dumps({"packet_id": "pkt-1", "extra": True}),
    ):
        gateway = ShapeModelGateway(StubModelClient([raw]), repair_attempts=0)
        with pytest.raises(ValidationError):
            gateway.propose(evidence_packet=_packet(), context=ctx)


def test_gateway_bounded_repair_attempt_succeeds_once() -> None:
    good = {
        "packet_id": "pkt-1",
        "title": "Shape",
        "statement": "A bounded claim.",
        "boundary": "B",
        "mechanism": "M",
        "dimensions": ["d"],
        "evidence_refs": [{"packet_id": "pkt-1", "block_id": "blk-1"}],
        "counter_hypotheses": [],
        "uncertainty": "medium",
        "recommended_disposition": "proposed",
    }
    client = StubModelClient(["not json", json.dumps(good)])
    gateway = ShapeModelGateway(client, repair_attempts=1)
    ctx = agent_context(PROPOSER_IDENTITY, capabilities=(CAP_CANDIDATE_SUBMIT,), model_id="m", prompt_version="p")

    assert gateway.propose(evidence_packet=_packet(), context=ctx) == good
    assert len(client.calls) == 2
    assert "validation_error" in client.calls[1]["messages"][-1]["content"]


def test_evaluator_tool_allowlist_is_request_promotion_only() -> None:
    gateway = ShapeModelGateway(StubModelClient([json.dumps({"recommendation": "decline"})]))
    ctx = agent_context(EVALUATOR_IDENTITY, capabilities=(CAP_PROMOTION_REQUEST,), model_id="m", prompt_version="p")

    gateway.evaluate(evidence_packet=_packet(), context=ctx, candidate={}, evaluation={})

    client_tools = gateway.allowed_tools_for_role("evaluator")
    assert client_tools == ["request_promotion"]


def test_inquiry_requires_materialized_text_and_rejects_empty_selection(tmp_path) -> None:
    from conversation_os.shape_population.normalization import normalize_source
    from conversation_os.shape_population.storage import ShapePopulationStore
    from conversation_os.source_content_store import SourceContentStore

    store = ShapePopulationStore(tmp_path)
    content_store = SourceContentStore(tmp_path)
    normalized = normalize_source(
        {"content": "Boundary B constrains mechanism A.\n", "modality": "plain_text"},
        store=store,
        content_store=content_store,
    )
    segments = [segment.to_dict() for segment in normalized.segments]
    ctx = agent_context(PROPOSER_IDENTITY, capabilities=(CAP_CANDIDATE_SUBMIT,), model_id="m", prompt_version="p")

    # Empty selection fails closed.
    gateway = ShapeModelGateway(
        StubModelClient([json.dumps({"question": "q?", "segment_ids": [], "anchors": [], "scope": "declared_segments"})]),
        content_store=content_store,
        store=store,
        repair_attempts=0,
    )
    with pytest.raises(ValidationError, match="did not select"):
        gateway.plan_inquiry(source_id=normalized.source_id, segments=segments, context=ctx)

    # Successful inquiry must receive quoted text in prior artifacts.
    client = StubModelClient(
        [
            json.dumps(
                {
                    "question": "What mechanism is bounded?",
                    "segment_ids": [segments[0]["segment_id"]],
                    "anchors": [normalized.source_id],
                    "scope": "declared_segments",
                }
            )
        ]
    )
    gateway = ShapeModelGateway(client, content_store=content_store, store=store, repair_attempts=0)
    planned = gateway.plan_inquiry(source_id=normalized.source_id, segments=segments, context=ctx)
    assert planned["segment_ids"] == [segments[0]["segment_id"]]
    prior = json.loads(client.calls[0]["messages"][2]["content"])["prior_artifacts"]
    assert prior["SOURCE_DATA_SEGMENTS"][0]["text"]
    assert "constrains mechanism" in prior["SOURCE_DATA_SEGMENTS"][0]["text"]
