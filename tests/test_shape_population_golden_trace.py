"""Wave 1 golden production trace: ingest through retrieve."""

from __future__ import annotations

import json
from pathlib import Path

from conversation_os.shape_candidate_retrieval import retrieve_after_canonical_apply
from conversation_os.shape_population.candidate_submission import submit_candidate
from conversation_os.shape_population.critique import submit_evaluation
from conversation_os.shape_population.evidence import build_evidence_packet
from conversation_os.shape_population.execution_context import agent_context, human_context
from conversation_os.shape_population.identities import (
    CRITIC_IDENTITY,
    EVALUATOR_IDENTITY,
    HUMAN_APPROVER_ROLE,
    PROPOSER_IDENTITY,
)
from conversation_os.shape_population.model_gateway import ShapeModelGateway, StubModelClient
from conversation_os.shape_population.normalization import normalize_source
from conversation_os.shape_population.orchestrator import (
    apply_approved_promotion_live,
    build_post_ingest_hook,
)
from conversation_os.shape_population.promotion import record_human_decision, request_promotion
from conversation_os.shape_population.storage import ShapePopulationStore
from conversation_os.source_content_store import SourceContentStore
from conversation_os.storage import utc_now
from conversation_os.vault_ingest import ingest_text_content


GOLDEN_SOURCE_TEXT = (
    "A receiver is delayed before reaching the intended goal through a blocked transition.\n"
    "The boundary is the interpretation flow under a bounded aperture.\n"
)


def run_golden_trace(root: Path) -> dict:
    store = ShapePopulationStore(root)
    content_store = SourceContentStore(root)
    hook = build_post_ingest_hook(root, store=store, evaluate=False)

    ingest = ingest_text_content(
        root,
        title="Wave1 golden source",
        content=GOLDEN_SOURCE_TEXT,
        source_ref="manual://wave01-golden",
        metadata={"branch_id": "branch:wave01", "scope_id": "scope:wave01"},
        post_ingest_hooks=[hook],
    )
    assert ingest["post_ingest"]["receipts"][0]["ok"] is True
    job = ingest["post_ingest"]["receipts"][0]["result"]

    # Deterministic intelligence path (mock), still using production modules.
    normalized = normalize_source(
        {
            "content": GOLDEN_SOURCE_TEXT,
            "modality": "plain_text",
            "metadata": {"branch_id": "branch:wave01", "scope_id": "scope:wave01"},
        },
        store=store,
        content_store=content_store,
    )
    ctx_inq = agent_context(
        PROPOSER_IDENTITY,
        capabilities={"shape.evidence.inquire", "shape.candidate.submit"},
        run_id="golden:inquiry",
        model_id="mock",
        prompt_version="golden-1.0",
    )
    packet = build_evidence_packet(
        {
            "segment_ids": [seg.segment_id for seg in normalized.segments],
            "evidence_inquiry": {"question": "What Shape is supported?", "requested_by": PROPOSER_IDENTITY},
        },
        store=store,
        context=ctx_inq,
        content_store=content_store,
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
    candidate = submit_candidate(
        {
            "packet_id": packet.packet_id,
            "title": "Route Confusion Through Blocked Transition",
            "statement": "A receiver is delayed before reaching the intended goal.",
            "boundary": "Interpretation flow under a bounded aperture",
            "mechanism": "Blocked transition delays the receiver",
            "dimensions": ["structural", "temporal"],
            "relations": [
                {
                    "relation_id": "relation:receiver-goal",
                    "relation_type": "delayed_before",
                    "participant_refs": ["referent:receiver", "referent:goal"],
                }
            ],
            "evidence_refs": refs,
            "counter_hypotheses": ["intentional pacing"],
            "uncertainty": "medium",
            "recommended_disposition": "proposed",
            "idempotency_key": "golden-cand-1",
            "branch_id": "branch:wave01",
            "scope_id": "scope:wave01",
        },
        store=store,
        context=agent_context(
            PROPOSER_IDENTITY,
            capabilities={"shape.candidate.submit"},
            run_id="golden:propose",
            model_id="mock",
            prompt_version="golden-1.0",
        ),
    )["candidate"]

    critique = submit_evaluation(
        {
            "candidate_id": candidate["candidate_id"],
            "disposition": "under_review",
            "critique": "Structure holds; need synthesis.",
            "evidence_refs": refs,
            "uncertainty": "medium",
            "relationship_findings": [],
            "idempotency_key": "golden-critique-1",
        },
        store=store,
        context=agent_context(
            CRITIC_IDENTITY,
            capabilities={"shape.evaluation.submit", "shape.comparison.read"},
            run_id="golden:critique",
            model_id="mock",
            prompt_version="golden-1.0",
        ),
    )
    synthesis = submit_evaluation(
        {
            "candidate_id": candidate["candidate_id"],
            "disposition": "recommended",
            "critique": "Synthesized recommendation for promotion.",
            "evidence_refs": refs,
            "uncertainty": "low",
            "relationship_findings": [],
            "idempotency_key": "golden-synth-1",
        },
        store=store,
        context=agent_context(
            CRITIC_IDENTITY,
            capabilities={"shape.evaluation.submit", "shape.comparison.read"},
            run_id="golden:synthesize",
            model_id="mock",
            prompt_version="golden-1.0",
        ),
    )
    evaluation = synthesis["evaluation"]
    requested = request_promotion(
        candidate["candidate_id"],
        evaluation["evaluation_id"],
        "Wave 1 golden promotion",
        refs,
        store=store,
        context=agent_context(
            EVALUATOR_IDENTITY,
            capabilities={"shape.promotion.request"},
            run_id="golden:evaluate",
            model_id="mock",
            prompt_version="golden-1.0",
        ),
        idempotency_key="golden-prom-1",
    )
    request_id = requested["request"]["request_id"]
    approval = record_human_decision(
        request_id,
        store=store,
        approval_reason="Approve Wave 1 golden Shape",
        decision="approved",
        context=human_context(HUMAN_APPROVER_ROLE, capabilities={"shape.promotion.approve"}),
    )
    approval_payload = approval.to_dict() if hasattr(approval, "to_dict") else dict(approval)
    applied = apply_approved_promotion_live(
        request_id,
        store=store,
        context=human_context(
            "shape.canonical_authority",
            capabilities={"shape.promotion.apply", "shape.promotion.approve"},
        ),
        idempotency_key="golden-apply-1",
    )
    canonical_id = applied["canonical_receipt"]["canonical_id"]
    retrieve = retrieve_after_canonical_apply(
        root,
        canonical_id=canonical_id,
        query_text="receiver delayed blocked transition goal",
        branch_id="branch:wave01",
        scope_id="scope:wave01",
        source_refs=[ingest["source_id"]],
    )
    rollback = None
    from conversation_os.shape_population.canonical_port import FoundationCanonicalPort
    from conversation_os.shape_population.execution_context import CAP_PROMOTION_ROLLBACK, service_context

    port = FoundationCanonicalPort(root)
    rollback = port.rollback(
        canonical_id,
        reason="golden correction demonstration",
        idempotency_key="golden-rollback-1",
        context=service_context("golden.trace.rollback", capabilities=(CAP_PROMOTION_ROLLBACK,)),
    )
    stale_retrieve = retrieve_after_canonical_apply(
        root,
        canonical_id=canonical_id,
        query_text="receiver delayed blocked transition goal",
        branch_id="branch:wave01",
        scope_id="scope:wave01",
    )

    archive = {
        "trace_id": "wave01-golden-source-to-shape",
        "generated_at": utc_now(),
        "pipeline": [
            "ingest",
            "normalize",
            "inquiry",
            "evidence",
            "propose",
            "critique",
            "synthesize",
            "evaluate",
            "human_approve",
            "canonical_apply",
            "retrieve",
            "rollback",
        ],
        "ids": {
            "vault_source_id": ingest["source_id"],
            "ingest_job_id": job.get("job_id"),
            "shape_source_id": normalized.source_id,
            "packet_id": packet.packet_id,
            "candidate_id": candidate["candidate_id"],
            "critique_evaluation_id": critique["evaluation"]["evaluation_id"],
            "synthesis_evaluation_id": evaluation["evaluation_id"],
            "promotion_request_id": request_id,
            "approval_id": approval_payload.get("approval_id") or approval_payload.get("decision_event_id"),
            "canonical_id": canonical_id,
            "shape_core_id": applied["canonical_receipt"].get("shape_core_id"),
            "shape_view_id": applied["canonical_receipt"].get("shape_view_id"),
            "owner_version": applied["canonical_receipt"].get("owner_version"),
        },
        "versions": {
            "candidate_schema": candidate.get("schema_version"),
            "proposal_schema": applied["projection"].get("proposal_schema_version"),
            "profile_id": applied["projection"].get("profile_id"),
            "profile_version": applied["projection"].get("profile_version"),
            "prompt_version": "golden-1.0",
            "model_id": "mock",
        },
        "receipts": {
            "ingest_ok": True,
            "canonical_applied": bool(applied["canonical_receipt"].get("applied")),
            "canonical_owner": applied["canonical_receipt"].get("owner"),
            "retrieve_ok": bool(retrieve.get("retrieval_ok")),
            "retrieve_status": retrieve.get("read_back_status"),
            "rollback_stale": bool(rollback.get("stale")),
            "post_rollback_status": stale_retrieve.get("read_back_status"),
        },
        "provenance": {
            "evidence_refs": refs,
            "content_fingerprint": candidate.get("content_fingerprint"),
            "projection_fingerprint": applied["canonical_receipt"].get("projection_fingerprint"),
        },
    }
    out = root / "product" / "inner_world_v1" / "data" / "shape_population" / "golden_trace.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(archive, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    archive["archive_path"] = str(out)
    return archive


def test_wave01_golden_source_to_shape_trace(tmp_path: Path):
    archive = run_golden_trace(tmp_path)
    assert archive["receipts"]["ingest_ok"] is True
    assert archive["receipts"]["canonical_applied"] is True
    assert archive["receipts"]["retrieve_ok"] is True
    assert archive["receipts"]["rollback_stale"] is True
    assert archive["receipts"]["post_rollback_status"] == "stale"
    assert archive["ids"]["canonical_id"].startswith("canonical:")
    assert archive["versions"]["profile_id"] == "profile:shape"
