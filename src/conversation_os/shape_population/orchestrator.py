"""Worker-side orchestration for asynchronous Shape population jobs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from conversation_os.shape_population.candidate_submission import submit_candidate
from conversation_os.shape_population.comparison import find_neighbors
from conversation_os.shape_population.contracts import ShapePopulationError, ValidationError
from conversation_os.shape_population.critique import submit_evaluation
from conversation_os.shape_population.evidence import build_evidence_packet
from conversation_os.shape_population.execution_context import (
    CAP_CANDIDATE_SUBMIT,
    CAP_COMPARISON_READ,
    CAP_EVALUATION_SUBMIT,
    CAP_EVIDENCE_INQUIRE,
    CAP_PROMOTION_REQUEST,
    agent_context,
)
from conversation_os.shape_population.identities import (
    CRITIC_IDENTITY,
    EVALUATOR_IDENTITY,
    PROPOSER_IDENTITY,
    SYNTHESIZER_IDENTITY,
)
from conversation_os.shape_population.model_gateway import ShapeModelGateway
from conversation_os.shape_population.normalization import normalize_source
from conversation_os.shape_population.promotion import request_promotion
from conversation_os.shape_population.storage import PopulationStore

MODULE_ID = "kernel.shape_population.orchestrator"
CONTRACT_VERSION = "1.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "ShapePopulationOrchestrator",
    "enqueue_after_ingest",
)
__all__ = list(PUBLIC_API)


def enqueue_after_ingest(source_id: str, *, store: PopulationStore) -> dict[str, Any]:
    """Idempotently enqueue worker-side Shape intelligence after source ingest commits."""

    return store.enqueue_job(source_id=source_id, payload={"source_id": source_id, "enqueued_by": "post_ingest_hook"})


@dataclass
class ShapePopulationOrchestrator:
    store: PopulationStore
    gateway: ShapeModelGateway
    lease_owner: str = "shape-population-worker"
    lease_seconds: int = 300
    max_attempts: int = 3
    comparison_limit: int = 5

    def claim_next_job(self) -> dict[str, Any] | None:
        return self.store.claim_job(lease_owner=self.lease_owner, lease_seconds=self.lease_seconds)

    def run_once(self) -> dict[str, Any] | None:
        job = self.claim_next_job()
        if job is None:
            return None
        return self.process_job(job)

    def _fail(self, job: Mapping[str, Any], exc: Exception, *, retryable: bool) -> dict[str, Any]:
        attempts = int(job.get("attempt_count") or 0)
        exhausted = attempts >= self.max_attempts
        should_retry = bool(retryable and not exhausted)
        result = self.store.fail_job(
            str(job["job_id"]),
            error=str(exc),
            retryable=should_retry,
            lease_owner=self.lease_owner,
        )
        if exhausted and not should_retry and result.get("state") != "dead_letter":
            finish = getattr(self.store, "_finish_job", None)
            if callable(finish):
                return finish(str(job["job_id"]), "dead_letter", str(exc), {"error": str(exc)}, self.lease_owner)
        return result

    def _source_segments(self, source_id: str) -> list[str]:
        source = self.store.get_source(source_id)
        if source is None:
            raise ValidationError(f"unknown source: {source_id}")
        return [str(segment["segment_id"]) for segment in (source.get("segments") or [])]

    def _ensure_source_normalized(self, job: Mapping[str, Any]) -> str:
        payload = dict(job.get("payload") or {})
        source_id = str(job.get("source_id") or payload.get("source_id") or "")
        if not source_id and payload.get("source_request"):
            normalized = normalize_source(dict(payload["source_request"]), store=self.store)
            if normalized.rejected:
                raise ValidationError(f"source normalization rejected: {normalized.rejection_reason}")
            source_id = normalized.source_id
        if not source_id:
            raise ValidationError("population job missing source_id")
        if self.store.get_source(source_id) is None:
            source_request = payload.get("source_request")
            if not isinstance(source_request, Mapping):
                raise ValidationError(f"source {source_id} is not normalized")
            normalized = normalize_source(source_request, store=self.store)
            if normalized.rejected:
                raise ValidationError(f"source normalization rejected: {normalized.rejection_reason}")
            source_id = normalized.source_id
        return source_id

    def _packet_for_source(self, source_id: str, *, run_id: str) -> dict[str, Any]:
        context = agent_context(
            PROPOSER_IDENTITY,
            capabilities=(CAP_EVIDENCE_INQUIRE,),
            run_id=run_id,
            model_id="deterministic-evidence",
            prompt_version=CONTRACT_VERSION,
        )
        packet = build_evidence_packet(
            {
                "segment_ids": self._source_segments(source_id),
                "evidence_inquiry": {
                    "question": "What provisional Shapes are supported by this source?",
                    "anchors": [source_id],
                    "scope": "declared_segments",
                },
            },
            store=self.store,
            context=context,
        )
        return packet.to_dict()

    def process_job(self, job: Mapping[str, Any]) -> dict[str, Any]:
        """Process one claimed job. Ingest only enqueues; intelligence runs here."""

        try:
            job_id = str(job["job_id"])
            source_id = self._ensure_source_normalized(job)
            packet = self._packet_for_source(source_id, run_id=f"{job_id}:evidence")
            proposer_context = agent_context(
                PROPOSER_IDENTITY,
                capabilities=(CAP_CANDIDATE_SUBMIT,),
                run_id=f"{job_id}:proposer",
                model_id="shape-proposer",
                prompt_version=self.gateway.prompt_version,
            )
            proposal = self.gateway.propose(evidence_packet=packet, context=proposer_context)
            submitted = submit_candidate(proposal, store=self.store, context=proposer_context)
            candidate = submitted["candidate"]

            comparison_context = agent_context(
                CRITIC_IDENTITY,
                capabilities=(CAP_COMPARISON_READ,),
                run_id=f"{job_id}:comparison",
                model_id="deterministic-comparison",
                prompt_version=CONTRACT_VERSION,
            )
            comparisons = find_neighbors(
                candidate["candidate_id"],
                store=self.store,
                context=comparison_context,
                limit=self.comparison_limit,
            )

            critic_context = agent_context(
                CRITIC_IDENTITY,
                capabilities=(CAP_EVALUATION_SUBMIT,),
                run_id=f"{job_id}:critic",
                model_id="shape-critic",
                prompt_version=self.gateway.prompt_version,
            )
            critique_payload = self.gateway.critique(
                evidence_packet=packet,
                context=critic_context,
                candidate=candidate,
                comparisons=comparisons,
            )
            critique = submit_evaluation(critique_payload, store=self.store, context=critic_context)

            synth_context = agent_context(
                SYNTHESIZER_IDENTITY,
                capabilities=(CAP_EVALUATION_SUBMIT,),
                run_id=f"{job_id}:synthesizer",
                model_id="shape-synthesizer",
                prompt_version=self.gateway.prompt_version,
            )
            synthesis_payload = self.gateway.synthesize(
                evidence_packet=packet,
                context=synth_context,
                candidate=critique["candidate"],
                critique=critique["evaluation"],
                comparisons=comparisons,
            )
            synthesis = submit_evaluation(synthesis_payload, store=self.store, context=synth_context)

            promotion = None
            if dict(job.get("payload") or {}).get("evaluate"):
                evaluator_context = agent_context(
                    EVALUATOR_IDENTITY,
                    capabilities=(CAP_PROMOTION_REQUEST,),
                    run_id=f"{job_id}:evaluator",
                    model_id="shape-evaluator",
                    prompt_version=self.gateway.prompt_version,
                )
                recommendation = self.gateway.evaluate(
                    evidence_packet=packet,
                    context=evaluator_context,
                    candidate=synthesis["candidate"],
                    evaluation=synthesis["evaluation"],
                )
                if recommendation.get("recommendation") == "request_promotion":
                    promotion = request_promotion(
                        str(recommendation["candidate_id"]),
                        str(recommendation["evaluation_id"]),
                        str(recommendation["rationale"]),
                        [dict(item) for item in (recommendation.get("evidence_refs") or [])],
                        store=self.store,
                        context=evaluator_context,
                    )

            result = {
                "source_id": source_id,
                "packet_id": packet["packet_id"],
                "candidate_id": candidate["candidate_id"],
                "comparison_set_version": comparisons.get("comparison_set_version"),
                "critique_evaluation_id": critique["evaluation"]["evaluation_id"],
                "synthesis_evaluation_id": synthesis["evaluation"]["evaluation_id"],
                "promotion_request_id": None if promotion is None else promotion["request"]["request_id"],
            }
            return self.store.complete_job(job_id, result=result, lease_owner=self.lease_owner)
        except (TimeoutError, ConnectionError) as exc:
            return self._fail(job, exc, retryable=True)
        except ShapePopulationError as exc:
            return self._fail(job, exc, retryable=False)
        except Exception as exc:
            return self._fail(job, exc, retryable=True)
