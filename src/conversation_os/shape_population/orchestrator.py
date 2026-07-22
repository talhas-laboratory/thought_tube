"""Worker-side orchestration for asynchronous Shape population jobs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from conversation_os.source_content_store import SourceContentStore
from conversation_os.shape_population.candidate_submission import submit_candidate
from conversation_os.shape_population.canonical_port import live_canonical_port
from conversation_os.shape_population.comparison import find_neighbors
from conversation_os.shape_population.contracts import ShapePopulationError, ValidationError
from conversation_os.shape_population.critique import submit_evaluation
from conversation_os.shape_population.evidence import build_evidence_packet
from conversation_os.shape_population.execution_context import (
    CAP_CANDIDATE_SUBMIT,
    CAP_COMPARISON_READ,
    CAP_EVALUATION_SUBMIT,
    CAP_EVIDENCE_INQUIRE,
    CAP_PROMOTION_APPLY,
    CAP_PROMOTION_REQUEST,
    ExecutionContext,
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
from conversation_os.shape_population.promotion import apply_promotion, request_promotion
from conversation_os.shape_population.storage import PopulationStore, ShapePopulationStore
from conversation_os.shape_population.vault_bridge import merge_job_payload_with_vault, source_request_from_vault

MODULE_ID = "kernel.shape_population.orchestrator"
CONTRACT_VERSION = "1.2.0"
RECOVERY_READINESS_CONTRACT_VERSION = "2026-07-22.t10-15.first"
RECOVERY_READINESS_REQUIRED_DRILLS = (
    "process_restart",
    "database_restore",
    "duplicate_delivery",
    "model_timeout",
    "stale_index_rebuild",
)
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "RECOVERY_READINESS_CONTRACT_VERSION",
    "RECOVERY_READINESS_REQUIRED_DRILLS",
    "ShapePopulationOrchestrator",
    "enqueue_after_ingest",
    "load_shape_population_runtime_config",
    "build_recovery_readiness_report",
    "build_post_ingest_hook",
    "apply_approved_promotion_live",
)
__all__ = list(PUBLIC_API)

PostIngestHook = Callable[..., Any]


def load_shape_population_runtime_config(root: Path | str) -> dict[str, Any]:
    """Read optional live Shape Population settings from runtime.json with safe defaults."""
    defaults = {
        "post_ingest_enqueue": True,
        "evaluate_on_ingest": False,
        "canonical_port": "foundation",
    }
    path = Path(root) / "product" / "inner_world_v1" / "config" / "runtime.json"
    if not path.exists():
        return dict(defaults)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(defaults)
    agents = dict((payload.get("agents") or {}).get("shape_population") or {})
    return {
        **defaults,
        **agents,
        "post_ingest_enqueue": bool(agents.get("post_ingest_enqueue", defaults["post_ingest_enqueue"])),
        "evaluate_on_ingest": bool(agents.get("evaluate_on_ingest", defaults["evaluate_on_ingest"])),
        "canonical_port": str(agents.get("canonical_port") or defaults["canonical_port"]),
    }


def enqueue_after_ingest(
    source_id: str,
    *,
    store: PopulationStore,
    vault_root: Path | str | None = None,
    evaluate: bool = False,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Idempotently enqueue worker-side Shape intelligence after source ingest commits.

    ``source_id`` is the vault source identity. The worker reconstructs content from the
    vault and normalizes it into a Shape source before intelligence runs.
    """

    body = merge_job_payload_with_vault(payload, vault_source_id=source_id, vault_root=vault_root)
    if evaluate:
        body["evaluate"] = True
    if vault_root is None and hasattr(store, "root"):
        body.setdefault("vault_root", str(Path(store.root)))
    return store.enqueue_job(source_id=source_id, payload=body)


def _non_negative_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _objective_minutes(objectives: Mapping[str, Any], key: str, default: int) -> int:
    try:
        return max(0, int(objectives.get(key, default) or default))
    except (TypeError, ValueError):
        return default


def build_recovery_readiness_report(
    operator_status: Mapping[str, Any],
    drill_results: Sequence[Mapping[str, Any]] | None = None,
    *,
    scale_tier: str = "current",
    objectives: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Summarize recovery readiness without asserting unperformed scale results."""

    objectives = dict(objectives or {})
    drill_rows = [dict(row) for row in list(drill_results or [])]
    seen_drills = {str(row.get("drill_id", "") or "") for row in drill_rows}
    required_drills = list(objectives.get("required_drills") or RECOVERY_READINESS_REQUIRED_DRILLS)
    missing_drills = [drill for drill in required_drills if drill not in seen_drills]
    rpo_target = _objective_minutes(objectives, "rpo_minutes", 15)
    rto_target = _objective_minutes(objectives, "rto_minutes", 60)
    controls = dict(operator_status.get("controls") or {})
    queued = _non_negative_int(operator_status.get("queued"))
    claimed = _non_negative_int(operator_status.get("claimed"))
    retryable = _non_negative_int(operator_status.get("retryable"))
    queue_depth = queued + claimed + retryable
    queue_pressure = "normal"
    if bool(controls.get("paused")) or bool(controls.get("drain")):
        queue_pressure = "operator_controlled"
    if retryable > 0 or queue_depth >= _objective_minutes(objectives, "queue_depth_warning", 25):
        queue_pressure = "degraded"

    failed_drills: list[str] = []
    objective_failures: list[str] = []
    unsafe_failures: list[str] = []
    normalized_drills: list[dict[str, Any]] = []
    for row in drill_rows:
        drill_id = str(row.get("drill_id", "") or "")
        rpo = _non_negative_int(row.get("rpo_minutes"))
        rto = _non_negative_int(row.get("rto_minutes"))
        passed = bool(row.get("passed"))
        lineage_preserved = bool(row.get("lineage_preserved", False))
        accepted_evidence_lost = bool(row.get("accepted_evidence_lost", False))
        unreceipted_canon_created = bool(row.get("unreceipted_canon_created", False))
        access_widened = bool(row.get("access_widened", False))
        if not passed:
            failed_drills.append(drill_id)
        if rpo > rpo_target:
            objective_failures.append(f"{drill_id}:rpo_minutes")
        if rto > rto_target:
            objective_failures.append(f"{drill_id}:rto_minutes")
        if not lineage_preserved or accepted_evidence_lost or unreceipted_canon_created or access_widened:
            unsafe_failures.append(drill_id)
        normalized_drills.append(
            {
                "drill_id": drill_id,
                "passed": passed,
                "rpo_minutes": rpo,
                "rto_minutes": rto,
                "lineage_preserved": lineage_preserved,
                "accepted_evidence_lost": accepted_evidence_lost,
                "unreceipted_canon_created": unreceipted_canon_created,
                "access_widened": access_widened,
                "evidence_ref": str(row.get("evidence_ref", "") or ""),
            }
        )

    blockers = []
    if missing_drills:
        blockers.append("missing_required_drills")
    if failed_drills:
        blockers.append("failed_recovery_drills")
    if objective_failures:
        blockers.append("recovery_objective_missed")
    if unsafe_failures:
        blockers.append("lineage_or_access_safety_failure")
    status = "ready_for_review" if not blockers else "blocked"
    return {
        "schema_version": "1.0",
        "contract_id": "ShapePopulationRecoveryReadiness",
        "contract_version": RECOVERY_READINESS_CONTRACT_VERSION,
        "status": status,
        "scale_tier": str(scale_tier or "current"),
        "claim_scope": "declared_drill_evidence_only",
        "multi_gigabyte_scale_claimed": False,
        "queue": {
            "queued": queued,
            "claimed": claimed,
            "retryable": retryable,
            "queue_depth": queue_depth,
            "queue_pressure": queue_pressure,
            "controls": controls,
        },
        "objectives": {"rpo_minutes": rpo_target, "rto_minutes": rto_target},
        "required_drills": required_drills,
        "drills": normalized_drills,
        "missing_drills": missing_drills,
        "failed_drills": failed_drills,
        "objective_failures": objective_failures,
        "unsafe_failures": unsafe_failures,
        "blockers": blockers,
        "residual_gaps": [
            "10x_100x_max_affordable_corpus_benchmarks",
            "process_kill_machine_restart_low_disk_network_loss_drills",
            "cost_per_source_candidate_shape_query_agent_task",
        ],
    }


def build_post_ingest_hook(
    root: Path | str,
    *,
    store: PopulationStore | None = None,
    evaluate: bool | None = None,
) -> PostIngestHook:
    """Build a vault post-ingest hook that enqueues Shape Population without blocking ingest.

    Ingest remains available if enqueue fails: failures are recorded and re-raised so the
    vault hook runner can mark the receipt as not-ok while preserving the source.
    """
    root_path = Path(root)
    population_store = store or ShapePopulationStore(root_path)
    config = load_shape_population_runtime_config(root_path)
    evaluate_flag = bool(config["evaluate_on_ingest"] if evaluate is None else evaluate)

    def hook(path: Path, *, source_id: str) -> dict[str, Any]:
        if not config.get("post_ingest_enqueue", True):
            return {"skipped": True, "reason": "post_ingest_enqueue_disabled"}
        try:
            return enqueue_after_ingest(
                source_id,
                store=population_store,
                vault_root=path,
                evaluate=evaluate_flag,
            )
        except Exception as exc:
            if hasattr(population_store, "record_enqueue_failure"):
                population_store.record_enqueue_failure(source_id=source_id, error=str(exc))
            raise

    return hook


def apply_approved_promotion_live(
    request_id: str,
    *,
    store: PopulationStore,
    context: ExecutionContext,
    idempotency_key: str = "",
) -> dict[str, Any]:
    """Apply an approved promotion through FoundationCanonicalPort (live path)."""
    context.require_capability(CAP_PROMOTION_APPLY)
    root = Path(store.root)
    config = load_shape_population_runtime_config(root)
    if str(config.get("canonical_port") or "foundation") != "foundation":
        raise ValidationError(
            f"live apply requires canonical_port=foundation; got {config.get('canonical_port')}"
        )
    return apply_promotion(
        request_id,
        store=store,
        context=context,
        canonical_port=live_canonical_port(root),
        idempotency_key=idempotency_key,
    )


@dataclass
class ShapePopulationOrchestrator:
    store: PopulationStore
    gateway: ShapeModelGateway
    content_store: SourceContentStore | None = None
    vault_root: Path | str | None = None
    lease_owner: str = "shape-population-worker"
    lease_seconds: int = 300
    max_attempts: int = 3
    comparison_limit: int = 5

    def __post_init__(self) -> None:
        if self.content_store is None:
            root = Path(self.vault_root) if self.vault_root is not None else Path(self.store.root)
            self.content_store = SourceContentStore(root)
        if getattr(self.gateway, "content_store", None) is None:
            self.gateway.content_store = self.content_store
        if getattr(self.gateway, "store", None) is None:
            self.gateway.store = self.store

    def claim_next_job(self) -> dict[str, Any] | None:
        return self.store.claim_job(lease_owner=self.lease_owner, lease_seconds=self.lease_seconds)

    def run_once(self) -> dict[str, Any] | None:
        job = self.claim_next_job()
        if job is None:
            return None
        return self.process_job(job)

    def operator_status(self) -> dict[str, Any]:
        controls = self.store.get_operator_controls() if hasattr(self.store, "get_operator_controls") else {}
        list_jobs = getattr(self.store, "list_jobs", None)
        return {
            "lease_owner": self.lease_owner,
            "controls": controls,
            "queued": len(list_jobs(state="queued")) if callable(list_jobs) else None,
            "claimed": len(list_jobs(state="claimed")) if callable(list_jobs) else None,
            "retryable": len(list_jobs(state="retryable")) if callable(list_jobs) else None,
        }

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

    def _source_segments(self, source_id: str) -> list[dict[str, Any]]:
        source = self.store.get_source(source_id)
        if source is None:
            raise ValidationError(f"unknown source: {source_id}")
        return [dict(segment) for segment in (source.get("segments") or [])]

    def _resolve_vault_root(self, payload: Mapping[str, Any]) -> Path:
        if payload.get("vault_root"):
            return Path(str(payload["vault_root"]))
        if self.vault_root is not None:
            return Path(self.vault_root)
        return Path(self.store.root)

    def _ensure_source_normalized(self, job: Mapping[str, Any]) -> str:
        payload = dict(job.get("payload") or {})
        vault_source_id = str(
            payload.get("vault_source_id") or job.get("source_id") or payload.get("source_id") or ""
        ).strip()
        shape_source_id = str(payload.get("shape_source_id") or "").strip()
        if shape_source_id and self.store.get_source(shape_source_id) is not None:
            return shape_source_id

        if payload.get("source_request") and isinstance(payload.get("source_request"), Mapping):
            normalized = normalize_source(
                dict(payload["source_request"]),
                store=self.store,
                content_store=self.content_store,
            )
            if normalized.rejected:
                raise ValidationError(f"source normalization rejected: {normalized.rejection_reason}")
            return normalized.source_id

        if vault_source_id and self.store.get_source(vault_source_id) is not None:
            return vault_source_id

        if not vault_source_id:
            raise ValidationError("population job missing source_id")

        vault_root = self._resolve_vault_root(payload)
        source_request = source_request_from_vault(
            vault_root,
            vault_source_id,
            content_store=self.content_store,
        )
        normalized = normalize_source(
            source_request,
            store=self.store,
            content_store=self.content_store,
        )
        if normalized.rejected:
            raise ValidationError(f"source normalization rejected: {normalized.rejection_reason}")
        return normalized.source_id

    def _packet_for_source(self, source_id: str, *, run_id: str) -> dict[str, Any]:
        context = agent_context(
            PROPOSER_IDENTITY,
            capabilities=(CAP_EVIDENCE_INQUIRE,),
            run_id=run_id,
            model_id="shape-inquiry",
            prompt_version=self.gateway.prompt_version,
        )
        segments = self._source_segments(source_id)
        inquiry = self.gateway.plan_inquiry(
            source_id=source_id,
            segments=segments,
            context=context,
        )
        segment_ids = [str(item) for item in (inquiry.get("segment_ids") or [])]
        if not segment_ids:
            segment_ids = [str(segment["segment_id"]) for segment in segments]
        packet = build_evidence_packet(
            {
                "segment_ids": segment_ids,
                "evidence_inquiry": {
                    "question": str(inquiry.get("question") or "").strip()
                    or "What provisional Shapes are supported by this source?",
                    "anchors": [str(item) for item in (inquiry.get("anchors") or [source_id])],
                    "scope": str(inquiry.get("scope") or "declared_segments"),
                },
            },
            store=self.store,
            context=context,
            content_store=self.content_store,
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
                capabilities=(CAP_CANDIDATE_SUBMIT, CAP_EVIDENCE_INQUIRE),
                run_id=f"{job_id}:proposer",
                model_id="shape-proposer",
                prompt_version=self.gateway.prompt_version,
            )
            proposal = self.gateway.propose(evidence_packet=packet, context=proposer_context)
            proposal = {
                **proposal,
                "packet_id": packet["packet_id"],
            }
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
                "vault_source_id": str((job.get("payload") or {}).get("vault_source_id") or job.get("source_id") or ""),
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
