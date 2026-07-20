"""Transactional SQLite store for Shape Population workflow authority."""

from __future__ import annotations

import contextlib
import hashlib
import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Optional

from conversation_os.shape_population.migrations import SCHEMA_VERSION, apply_migrations
from conversation_os.storage import ensure_dir, make_id, repo_root_from, utc_now

MODULE_ID = "kernel.shape_population.storage"
CONTRACT_VERSION = "2.0.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "shape_population_dir",
    "shape_population_db_path",
    "ShapePopulationStore",
    "PopulationStore",
)
__all__ = list(PUBLIC_API)

DATABASE_RELATIVE_PATH = Path("product/inner_world_v1/data/shape_population/shape_population.db")
TERMINAL_JOB_STATES = frozenset({"completed", "failed", "dead_letter", "cancelled"})


def shape_population_dir(root: Path) -> Path:
    return ensure_dir(Path(root) / "product" / "inner_world_v1" / "data" / "shape_population")


def shape_population_db_path(root: Path) -> Path:
    return Path(root) / DATABASE_RELATIVE_PATH


def _json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_loads(payload: str | None, default: Any) -> Any:
    if payload is None or payload == "":
        return default
    return json.loads(payload)


def _fingerprint(payload: Any) -> str:
    return hashlib.sha256(_json_dumps(payload).encode("utf-8")).hexdigest()


def _text_sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _drop_raw_text(payload: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(payload)
    row.pop("text", None)
    row.pop("content", None)
    row.pop("source_text", None)
    row.pop("raw_text", None)
    return row


class ShapePopulationStore:
    """SQLite-backed store using BEGIN IMMEDIATE for state-changing work."""

    def __init__(self, root: Path | str | None = None, *, database_path: Path | str | None = None):
        self.root = Path(root) if root is not None else repo_root_from(Path.cwd())
        self.base = shape_population_dir(self.root)
        self.database_path = Path(database_path) if database_path is not None else shape_population_db_path(self.root)
        ensure_dir(self.database_path.parent)
        self._local = threading.local()
        with self._connect() as conn:
            apply_migrations(conn)

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.database_path), timeout=5.0, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = FULL")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def _active_conn(self) -> sqlite3.Connection | None:
        return getattr(self._local, "conn", None)

    @contextlib.contextmanager
    def transaction(self) -> Iterator["ShapePopulationStore"]:
        active = self._active_conn()
        if active is not None:
            yield self
            return
        conn = self._connect()
        self._local.conn = conn
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield self
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._local.conn = None
            conn.close()

    @contextlib.contextmanager
    def _read_conn(self) -> Iterator[sqlite3.Connection]:
        active = self._active_conn()
        if active is not None:
            yield active
            return
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    def _write(self, fn: Callable[[sqlite3.Connection], Any]) -> Any:
        active = self._active_conn()
        if active is not None:
            return fn(active)
        with self.transaction():
            conn = self._active_conn()
            assert conn is not None
            return fn(conn)

    def put_source(self, source: Mapping[str, Any]) -> None:
        def write(conn: sqlite3.Connection) -> None:
            source_id = str(source["source_id"])
            digest = str(source.get("content_sha256") or source.get("content_digest") or "")
            pointer = str(source.get("content_pointer") or source.get("raw_ref") or source.get("locator") or "")
            if not pointer and digest:
                pointer = f"sha256:{digest}"
            metadata = _drop_raw_text(dict(source.get("metadata") or {}))
            conn.execute(
                """
                INSERT INTO shape_sources (
                    source_id, content_sha256, content_pointer, modality,
                    normalization_version, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                ON CONFLICT(source_id) DO UPDATE SET
                    content_sha256 = excluded.content_sha256,
                    content_pointer = excluded.content_pointer,
                    modality = excluded.modality,
                    normalization_version = excluded.normalization_version,
                    metadata_json = excluded.metadata_json
                """,
                (
                    source_id,
                    digest,
                    pointer,
                    str(source.get("modality") or "unknown"),
                    str(source.get("normalization_version") or "unknown"),
                    _json_dumps(metadata),
                    source.get("created_at") or source.get("ingested_at"),
                ),
            )
            for segment in source.get("segments") or []:
                self._put_segment(conn, segment)

        self._write(write)

    def get_source(self, source_id: str) -> Optional[dict[str, Any]]:
        with self._read_conn() as conn:
            row = conn.execute(
                "SELECT * FROM shape_sources WHERE source_id = ?",
                (source_id,),
            ).fetchone()
            if row is None:
                return None
            segments = conn.execute(
                "SELECT * FROM shape_segments WHERE source_id = ? ORDER BY ordinal ASC",
                (source_id,),
            ).fetchall()
        payload = self._source_from_row(row)
        payload["segments"] = [self._segment_from_row(item) for item in segments]
        return payload

    def put_segment(self, segment: Mapping[str, Any]) -> None:
        self._write(lambda conn: self._put_segment(conn, segment))

    def _put_segment(self, conn: sqlite3.Connection, segment: Mapping[str, Any]) -> None:
        text_sha = str(segment.get("text_sha256") or "")
        if not text_sha and "text" in segment:
            text_sha = _text_sha256(str(segment.get("text") or ""))
        metadata = _drop_raw_text(dict(segment.get("metadata") or {}))
        if "text_ref" in segment:
            metadata["text_ref"] = dict(segment.get("text_ref") or {})
        if "source_content_sha256" in segment:
            metadata["source_content_sha256"] = segment.get("source_content_sha256")
        conn.execute(
            """
            INSERT INTO shape_segments (
                segment_id, source_id, ordinal, char_start, char_end, byte_start,
                byte_end, structure_path, text_sha256, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(segment_id) DO UPDATE SET
                source_id = excluded.source_id,
                ordinal = excluded.ordinal,
                char_start = excluded.char_start,
                char_end = excluded.char_end,
                byte_start = excluded.byte_start,
                byte_end = excluded.byte_end,
                structure_path = excluded.structure_path,
                text_sha256 = excluded.text_sha256,
                metadata_json = excluded.metadata_json
            """,
            (
                str(segment["segment_id"]),
                str(segment["source_id"]),
                int(segment.get("ordinal") or 0),
                int(segment.get("char_start") or 0),
                int(segment.get("char_end") or 0),
                segment.get("byte_start"),
                segment.get("byte_end"),
                str(segment.get("structure_path") or ""),
                text_sha,
                _json_dumps(metadata),
            ),
        )

    def get_segment(self, segment_id: str) -> Optional[dict[str, Any]]:
        with self._read_conn() as conn:
            row = conn.execute(
                "SELECT * FROM shape_segments WHERE segment_id = ?",
                (segment_id,),
            ).fetchone()
        return None if row is None else self._segment_from_row(row)

    def list_segments(self) -> list[dict[str, Any]]:
        with self._read_conn() as conn:
            rows = conn.execute("SELECT * FROM shape_segments ORDER BY source_id, ordinal").fetchall()
        return [self._segment_from_row(row) for row in rows]

    def put_packet(self, packet: Mapping[str, Any]) -> None:
        def write(conn: sqlite3.Connection) -> None:
            inquiry = dict(packet.get("inquiry") or packet.get("evidence_inquiry") or {})
            requester = str(inquiry.get("requested_by") or packet.get("requested_by") or "unknown")
            requester_kind = str(packet.get("requester_kind") or inquiry.get("requester_kind") or "agent")
            policy_version = str(packet.get("policy_version") or "1.0.0")
            inquiry_id = str(packet.get("inquiry_id") or f"inq-{_fingerprint([inquiry, requester, policy_version])[:20]}")
            inquiry_fp = str(packet.get("inquiry_fingerprint") or _fingerprint([inquiry, requester, policy_version]))
            conn.execute(
                """
                INSERT INTO evidence_inquiries (
                    inquiry_id, requester_principal_id, requester_kind,
                    question_scope_json, policy_version, fingerprint
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(inquiry_id) DO UPDATE SET
                    requester_principal_id = excluded.requester_principal_id,
                    requester_kind = excluded.requester_kind,
                    question_scope_json = excluded.question_scope_json,
                    policy_version = excluded.policy_version,
                    fingerprint = excluded.fingerprint
                """,
                (inquiry_id, requester, requester_kind, _json_dumps(inquiry), policy_version, inquiry_fp),
            )
            blocks = [self._packet_block_ref(block) for block in (packet.get("blocks") or [])]
            packet_fp = str(packet.get("packet_fingerprint") or packet.get("fingerprint") or _fingerprint(blocks))
            status = str(packet.get("status") or ("ready" if blocks else "empty"))
            conn.execute(
                """
                INSERT INTO evidence_packets (
                    packet_id, inquiry_id, corpus_revision, packet_fingerprint,
                    budget_ledger_json, omitted_json, status
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(packet_id) DO UPDATE SET
                    inquiry_id = excluded.inquiry_id,
                    corpus_revision = excluded.corpus_revision,
                    packet_fingerprint = excluded.packet_fingerprint,
                    budget_ledger_json = excluded.budget_ledger_json,
                    omitted_json = excluded.omitted_json,
                    status = excluded.status
                """,
                (
                    str(packet["packet_id"]),
                    inquiry_id,
                    str(packet.get("corpus_revision") or "local"),
                    packet_fp,
                    _json_dumps(packet.get("budget") or packet.get("budget_ledger") or {}),
                    _json_dumps(packet.get("omitted") or []),
                    status,
                ),
            )
            conn.execute("DELETE FROM evidence_packet_blocks WHERE packet_id = ?", (str(packet["packet_id"]),))
            for ordinal, block in enumerate(packet.get("blocks") or []):
                self._put_packet_block(conn, str(packet["packet_id"]), block, ordinal)

        self._write(write)

    def get_packet(self, packet_id: str) -> Optional[dict[str, Any]]:
        with self._read_conn() as conn:
            row = conn.execute(
                """
                SELECT p.*, i.question_scope_json, i.policy_version, i.requester_principal_id, i.requester_kind
                FROM evidence_packets p
                JOIN evidence_inquiries i ON i.inquiry_id = p.inquiry_id
                WHERE p.packet_id = ?
                """,
                (packet_id,),
            ).fetchone()
            if row is None:
                return None
            blocks = conn.execute(
                "SELECT * FROM evidence_packet_blocks WHERE packet_id = ? ORDER BY ordinal ASC",
                (packet_id,),
            ).fetchall()
        return {
            "packet_id": str(row["packet_id"]),
            "inquiry_id": str(row["inquiry_id"]),
            "inquiry": _json_loads(row["question_scope_json"], {}),
            "blocks": [self._packet_block_from_row(block) for block in blocks],
            "omitted": _json_loads(row["omitted_json"], []),
            "budget": _json_loads(row["budget_ledger_json"], {}),
            "policy_version": str(row["policy_version"]),
            "corpus_revision": str(row["corpus_revision"]),
            "packet_fingerprint": str(row["packet_fingerprint"]),
            "status": str(row["status"]),
            "safe": str(row["status"]) != "failed",
            "injection_safe_envelope": True,
        }

    def _packet_block_ref(self, block: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "block_id": str(block.get("block_id") or ""),
            "source_id": str(block.get("source_id") or ""),
            "segment_id": str(block.get("segment_id") or ""),
            "char_start": int(block.get("char_start") or 0),
            "char_end": int(block.get("char_end") or 0),
            "text_sha256": str(block.get("text_sha256") or ""),
        }

    def _put_packet_block(
        self,
        conn: sqlite3.Connection,
        packet_id: str,
        block: Mapping[str, Any],
        ordinal: int,
    ) -> None:
        segment = self.get_segment(str(block["segment_id"]))
        text_sha = str(block.get("text_sha256") or "")
        if not text_sha and "text" in block:
            text_sha = _text_sha256(str(block.get("text") or ""))
        if not text_sha and segment is not None:
            text_sha = str(segment.get("text_sha256") or "")
        conn.execute(
            """
            INSERT INTO evidence_packet_blocks (
                packet_id, block_id, segment_id, source_id, ordinal, char_start,
                char_end, byte_start, byte_end, text_sha256, structure_path, metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                packet_id,
                str(block["block_id"]),
                str(block["segment_id"]),
                str(block.get("source_id") or (segment or {}).get("source_id") or ""),
                int(block.get("ordinal") if block.get("ordinal") is not None else ordinal),
                int(block.get("char_start") or 0),
                int(block.get("char_end") or 0),
                block.get("byte_start") if block.get("byte_start") is not None else (segment or {}).get("byte_start"),
                block.get("byte_end") if block.get("byte_end") is not None else (segment or {}).get("byte_end"),
                text_sha,
                str(block.get("structure_path") or (segment or {}).get("structure_path") or ""),
                _json_dumps(_drop_raw_text(dict(block.get("metadata") or {}))),
            ),
        )

    def put_candidate(self, candidate: Mapping[str, Any]) -> None:
        def write(conn: sqlite3.Connection) -> None:
            candidate_id = str(candidate["candidate_id"])
            previous = conn.execute(
                "SELECT status FROM candidates WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
            status = str(candidate.get("status") or "proposed")
            semantic = {
                key: candidate.get(key)
                for key in (
                    "title",
                    "statement",
                    "boundary",
                    "mechanism",
                    "dimensions",
                    "evidence_refs",
                    "counter_hypotheses",
                    "uncertainty",
                    "relations",
                    "recommended_disposition",
                )
                if key in candidate
            }
            execution = {
                key: candidate.get(key)
                for key in (
                    "agent_identity",
                    "model_version",
                    "prompt_version",
                    "tool_contract_version",
                    "run_id",
                    "provenance",
                )
                if key in candidate
            }
            fingerprint = str(
                candidate.get("content_fingerprint")
                or candidate.get("fingerprint")
                or _fingerprint([candidate_id, status, semantic, execution])
            )
            now = self.now()
            conn.execute(
                """
                INSERT INTO candidates (
                    candidate_id, packet_id, status, semantic_payload_json,
                    execution_metadata_json, fingerprint, schema_version,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, ?), COALESCE(?, ?))
                ON CONFLICT(candidate_id) DO UPDATE SET
                    packet_id = excluded.packet_id,
                    status = excluded.status,
                    semantic_payload_json = excluded.semantic_payload_json,
                    execution_metadata_json = excluded.execution_metadata_json,
                    fingerprint = excluded.fingerprint,
                    schema_version = excluded.schema_version,
                    updated_at = excluded.updated_at
                """,
                (
                    candidate_id,
                    str(candidate["packet_id"]),
                    status,
                    _json_dumps(semantic),
                    _json_dumps(execution),
                    fingerprint,
                    str(candidate.get("schema_version") or "1.0.0"),
                    candidate.get("created_at"),
                    now,
                    candidate.get("updated_at"),
                    now,
                ),
            )
            previous_status = None if previous is None else str(previous["status"])
            if previous_status != status:
                self._append_candidate_event(conn, candidate_id, previous_status, status, execution)

        self._write(write)

    def get_candidate(self, candidate_id: str) -> Optional[dict[str, Any]]:
        with self._read_conn() as conn:
            row = conn.execute("SELECT * FROM candidates WHERE candidate_id = ?", (candidate_id,)).fetchone()
        return None if row is None else self._candidate_from_row(row)

    def list_candidates(self) -> list[dict[str, Any]]:
        with self._read_conn() as conn:
            rows = conn.execute("SELECT * FROM candidates ORDER BY created_at ASC, candidate_id ASC").fetchall()
        return [self._candidate_from_row(row) for row in rows]

    def put_evaluation(self, evaluation: Mapping[str, Any]) -> None:
        def write(conn: sqlite3.Connection) -> None:
            payload = {
                key: evaluation.get(key)
                for key in ("critique", "evidence_refs", "uncertainty", "relationship_findings", "revisions")
                if key in evaluation
            }
            execution = {
                key: evaluation.get(key)
                for key in ("agent_identity", "model_version", "prompt_version", "tool_contract_version", "run_id")
                if key in evaluation
            }
            fingerprint = str(
                evaluation.get("content_fingerprint")
                or evaluation.get("fingerprint")
                or _fingerprint([evaluation.get("evaluation_id"), payload, execution])
            )
            conn.execute(
                """
                INSERT INTO evaluations (
                    evaluation_id, candidate_id, disposition, payload_json,
                    execution_metadata_json, fingerprint, schema_version, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                ON CONFLICT(evaluation_id) DO UPDATE SET
                    candidate_id = excluded.candidate_id,
                    disposition = excluded.disposition,
                    payload_json = excluded.payload_json,
                    execution_metadata_json = excluded.execution_metadata_json,
                    fingerprint = excluded.fingerprint,
                    schema_version = excluded.schema_version
                """,
                (
                    str(evaluation["evaluation_id"]),
                    str(evaluation["candidate_id"]),
                    str(evaluation["disposition"]),
                    _json_dumps(payload),
                    _json_dumps(execution),
                    fingerprint,
                    str(evaluation.get("schema_version") or "1.0.0"),
                    evaluation.get("created_at"),
                ),
            )

        self._write(write)

    def get_evaluation(self, evaluation_id: str) -> Optional[dict[str, Any]]:
        with self._read_conn() as conn:
            row = conn.execute(
                "SELECT * FROM evaluations WHERE evaluation_id = ?",
                (evaluation_id,),
            ).fetchone()
        return None if row is None else self._evaluation_from_row(row)

    def put_receipt(self, receipt: Mapping[str, Any]) -> None:
        safe = _drop_raw_text(receipt)

        def write(conn: sqlite3.Connection) -> None:
            conn.execute(
                """
                INSERT INTO population_receipts (
                    receipt_id, operation, request_id, outcome, candidate_id,
                    evaluation_id, packet_id, payload_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                """,
                (
                    str(safe["receipt_id"]),
                    str(safe["operation"]),
                    str(safe["request_id"]),
                    str(safe["outcome"]),
                    safe.get("candidate_id") or None,
                    safe.get("evaluation_id") or None,
                    safe.get("packet_id") or safe.get("provenance", {}).get("packet_id") or None,
                    _json_dumps(safe),
                    safe.get("created_at"),
                ),
            )

        self._write(write)

    def get_receipt(self, receipt_id: str) -> Optional[dict[str, Any]]:
        with self._read_conn() as conn:
            row = conn.execute(
                "SELECT * FROM population_receipts WHERE receipt_id = ?",
                (receipt_id,),
            ).fetchone()
        if row is None:
            return None
        payload = _json_loads(row["payload_json"], {})
        payload.setdefault("receipt_id", str(row["receipt_id"]))
        payload.setdefault("operation", str(row["operation"]))
        payload.setdefault("request_id", str(row["request_id"]))
        payload.setdefault("outcome", str(row["outcome"]))
        payload.setdefault("created_at", str(row["created_at"]))
        return payload

    def get_idempotency(
        self,
        key: str,
        *,
        operation: str = "legacy",
        principal_id: str = "legacy",
    ) -> Optional[dict[str, Any]]:
        with self._read_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM idempotency_keys
                WHERE operation = ? AND principal_id = ? AND idempotency_key = ?
                """,
                (operation, principal_id, key),
            ).fetchone()
        if row is None:
            return None
        payload = _json_loads(row["result_ids_json"], {})
        payload.setdefault("fingerprint", str(row["request_fingerprint"]))
        payload.setdefault("created_at", str(row["created_at"]))
        return payload

    def put_idempotency(
        self,
        key: str,
        record: Mapping[str, Any],
        *,
        operation: str = "legacy",
        principal_id: str = "legacy",
    ) -> None:
        request_fingerprint = str(record.get("fingerprint") or record.get("request_fingerprint") or _fingerprint(record))
        self._write(
            lambda conn: conn.execute(
                """
                INSERT INTO idempotency_keys (
                    operation, principal_id, idempotency_key, request_fingerprint, result_ids_json
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(operation, principal_id, idempotency_key) DO UPDATE SET
                    request_fingerprint = excluded.request_fingerprint,
                    result_ids_json = excluded.result_ids_json
                """,
                (operation, principal_id, key, request_fingerprint, _json_dumps(dict(record))),
            )
        )

    def put_promotion(self, request: Mapping[str, Any]) -> None:
        def write(conn: sqlite3.Connection) -> None:
            now = self.now()
            conn.execute(
                """
                INSERT INTO promotion_requests (
                    request_id, candidate_id, evaluation_id, status, rationale,
                    evidence_refs_json, requester_principal_id, fingerprint,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, COALESCE(?, ?), COALESCE(?, ?))
                ON CONFLICT(request_id) DO UPDATE SET
                    candidate_id = excluded.candidate_id,
                    evaluation_id = excluded.evaluation_id,
                    status = excluded.status,
                    rationale = excluded.rationale,
                    evidence_refs_json = excluded.evidence_refs_json,
                    requester_principal_id = excluded.requester_principal_id,
                    fingerprint = excluded.fingerprint,
                    updated_at = excluded.updated_at
                """,
                (
                    str(request["request_id"]),
                    str(request["candidate_id"]),
                    str(request["evaluation_id"]),
                    str(request.get("status") or "requested"),
                    str(request.get("rationale") or ""),
                    _json_dumps(request.get("evidence_refs") or []),
                    str(request.get("requester_identity") or request.get("requester_principal_id") or "unknown"),
                    str(request.get("content_fingerprint") or request.get("fingerprint") or _fingerprint(request)),
                    request.get("created_at"),
                    now,
                    request.get("updated_at"),
                    now,
                ),
            )

        self._write(write)

    def get_promotion(self, request_id: str) -> Optional[dict[str, Any]]:
        with self._read_conn() as conn:
            row = conn.execute(
                "SELECT * FROM promotion_requests WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        return None if row is None else self._promotion_from_row(row)

    def list_promotions(self) -> list[dict[str, Any]]:
        with self._read_conn() as conn:
            rows = conn.execute("SELECT * FROM promotion_requests ORDER BY created_at ASC").fetchall()
        return [self._promotion_from_row(row) for row in rows]

    def get_human_decision(self, request_id: str) -> Optional[dict[str, Any]]:
        with self._read_conn() as conn:
            row = conn.execute(
                "SELECT * FROM human_decision_events WHERE request_id = ?",
                (request_id,),
            ).fetchone()
        return None if row is None else self._human_decision_from_row(row)

    def put_human_decision(self, event: Mapping[str, Any]) -> None:
        def write(conn: sqlite3.Connection) -> None:
            request_id = str(event["request_id"])
            decision = str(event.get("decision") or "approved")
            conn.execute(
                """
                INSERT INTO human_decision_events (
                    decision_event_id, request_id, decision, human_principal_id,
                    reason, context_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                """,
                (
                    str(event.get("decision_event_id") or event.get("approval_id") or self.new_id("hdec")),
                    request_id,
                    decision,
                    str(event.get("human_principal_id") or event.get("approval_identity") or event.get("principal_id") or ""),
                    str(event.get("reason") or event.get("approval_reason") or ""),
                    _json_dumps(dict(event.get("context") or event.get("context_json") or {})),
                    event.get("created_at"),
                ),
            )
            conn.execute(
                """
                UPDATE promotion_requests
                SET status = ?, updated_at = ?
                WHERE request_id = ?
                """,
                ("approved" if decision == "approved" else "rejected", self.now(), request_id),
            )

        self._write(write)

    def put_approval(self, approval: Mapping[str, Any]) -> None:
        self.put_human_decision(approval)

    def put_comparison_set(self, comparison_set: Mapping[str, Any]) -> None:
        def write(conn: sqlite3.Connection) -> None:
            version = str(comparison_set.get("comparison_set_version") or "")
            candidate_id = str(comparison_set.get("candidate_id") or "")
            if not version or not candidate_id:
                raise ValueError("comparison_set requires candidate_id and comparison_set_version")
            conn.execute(
                """
                INSERT INTO comparison_sets (
                    comparison_set_version, candidate_id, policy_version,
                    retriever_profile_json, neighbors_json, payload_json
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(comparison_set_version) DO UPDATE SET
                    candidate_id = excluded.candidate_id,
                    policy_version = excluded.policy_version,
                    retriever_profile_json = excluded.retriever_profile_json,
                    neighbors_json = excluded.neighbors_json,
                    payload_json = excluded.payload_json
                """,
                (
                    version,
                    candidate_id,
                    str(comparison_set.get("policy_version") or ""),
                    _json_dumps(comparison_set.get("retriever_profile") or {}),
                    _json_dumps(comparison_set.get("neighbors") or []),
                    _json_dumps(dict(comparison_set)),
                ),
            )

        self._write(write)

    def get_comparison_set(self, comparison_set_version: str) -> Optional[dict[str, Any]]:
        with self._read_conn() as conn:
            row = conn.execute(
                "SELECT * FROM comparison_sets WHERE comparison_set_version = ?",
                (comparison_set_version,),
            ).fetchone()
        if row is None:
            return None
        payload = _json_loads(row["payload_json"], {})
        if isinstance(payload, dict) and payload:
            return payload
        return {
            "comparison_set_version": str(row["comparison_set_version"]),
            "candidate_id": str(row["candidate_id"]),
            "policy_version": str(row["policy_version"]),
            "retriever_profile": _json_loads(row["retriever_profile_json"], {}),
            "neighbors": _json_loads(row["neighbors_json"], []),
        }

    def get_approval_for_request(self, request_id: str) -> Optional[dict[str, Any]]:
        event = self.get_human_decision(request_id)
        if event is None or event.get("decision") != "approved":
            return None
        return {
            "approval_id": event["approval_id"],
            "request_id": event["request_id"],
            "approval_identity": event["approval_identity"],
            "approval_reason": event["approval_reason"],
            "decision": event["decision"],
            "created_at": event["created_at"],
            "immutable": True,
        }

    def put_canonical_projection_receipt(self, receipt: Mapping[str, Any]) -> None:
        def write(conn: sqlite3.Connection) -> None:
            result = dict(receipt.get("canonical_result") or receipt.get("projection") or receipt)
            conn.execute(
                """
                INSERT INTO canonical_projection_receipts (
                    receipt_id, request_id, candidate_id, operation, canonical_id,
                    canonical_result_json, idempotency_key, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP))
                ON CONFLICT(receipt_id) DO UPDATE SET
                    canonical_result_json = excluded.canonical_result_json,
                    canonical_id = excluded.canonical_id
                """,
                (
                    str(receipt.get("receipt_id") or self.new_id("canon")),
                    str(receipt["request_id"]),
                    str(receipt["candidate_id"]),
                    str(receipt.get("operation") or "apply"),
                    str(receipt.get("canonical_id") or result.get("canonical_id") or result.get("candidate_id") or ""),
                    _json_dumps(_drop_raw_text(result)),
                    str(receipt.get("idempotency_key") or receipt.get("receipt_id") or self.new_id("canon-idem")),
                    receipt.get("created_at"),
                ),
            )

        self._write(write)

    def get_canonical_projection_receipt(self, key: str) -> Optional[dict[str, Any]]:
        with self._read_conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM canonical_projection_receipts
                WHERE receipt_id = ? OR request_id = ? OR candidate_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (key, key, key),
            ).fetchone()
        return None if row is None else self._canonical_receipt_from_row(row)

    def remove_canonical_projection_receipt(self, key: str) -> None:
        self._write(
            lambda conn: conn.execute(
                """
                DELETE FROM canonical_projection_receipts
                WHERE receipt_id = ? OR request_id = ? OR candidate_id = ?
                """,
                (key, key, key),
            )
        )

    def put_canonical_projection(self, candidate_id: str, projection: Mapping[str, Any]) -> None:
        receipt = {
            "request_id": projection.get("request_id"),
            "candidate_id": candidate_id,
            "operation": "apply",
            "projection": dict(projection),
            "canonical_id": projection.get("canonical_id") or candidate_id,
            "idempotency_key": projection.get("idempotency_key") or f"canonical:{candidate_id}:{projection.get('request_id')}",
        }
        self.put_canonical_projection_receipt(receipt)

    def get_canonical_projection(self, candidate_id: str) -> Optional[dict[str, Any]]:
        receipt = self.get_canonical_projection_receipt(candidate_id)
        if receipt is None or receipt.get("operation") != "apply":
            return None
        return dict(receipt.get("canonical_result") or {})

    def remove_canonical_projection(self, candidate_id: str) -> None:
        self.remove_canonical_projection_receipt(candidate_id)

    def enqueue_job(
        self,
        *,
        source_id: str,
        normalization_version: str = "",
        payload: Mapping[str, Any] | None = None,
        job_id: str = "",
        next_attempt_at: str = "",
    ) -> dict[str, Any]:
        def write(conn: sqlite3.Connection) -> dict[str, Any]:
            version = normalization_version or self._source_normalization_version(conn, source_id)
            existing = conn.execute(
                """
                SELECT * FROM population_jobs
                WHERE source_id = ? AND normalization_version = ?
                  AND state NOT IN ('completed', 'failed', 'dead_letter', 'cancelled')
                """,
                (source_id, version),
            ).fetchone()
            if existing is not None:
                return self._job_from_row(existing)
            now = self.now()
            row_id = job_id or self.new_id("job")
            conn.execute(
                """
                INSERT INTO population_jobs (
                    job_id, source_id, normalization_version, state, next_attempt_at,
                    payload_json, created_at, updated_at
                )
                VALUES (?, ?, ?, 'queued', ?, ?, ?, ?)
                """,
                (row_id, source_id, version, next_attempt_at or None, _json_dumps(dict(payload or {})), now, now),
            )
            row = conn.execute("SELECT * FROM population_jobs WHERE job_id = ?", (row_id,)).fetchone()
            assert row is not None
            return self._job_from_row(row)

        return self._write(write)

    def claim_job(self, *, lease_owner: str, lease_seconds: int = 300) -> Optional[dict[str, Any]]:
        def write(conn: sqlite3.Connection) -> Optional[dict[str, Any]]:
            now = self.now()
            row = conn.execute(
                """
                SELECT * FROM population_jobs
                WHERE (
                    state IN ('queued', 'retryable')
                    OR (state IN ('claimed', 'running') AND lease_expires_at IS NOT NULL AND lease_expires_at <= ?)
                )
                  AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
                ORDER BY COALESCE(next_attempt_at, created_at), created_at
                LIMIT 1
                """,
                (now, now),
            ).fetchone()
            if row is None:
                return None
            lease_expires = utc_now_plus_seconds(lease_seconds)
            conn.execute(
                """
                UPDATE population_jobs
                SET state = 'claimed',
                    attempt_count = attempt_count + 1,
                    lease_owner = ?,
                    lease_expires_at = ?,
                    updated_at = ?
                WHERE job_id = ?
                """,
                (lease_owner, lease_expires, now, row["job_id"]),
            )
            claimed = conn.execute("SELECT * FROM population_jobs WHERE job_id = ?", (row["job_id"],)).fetchone()
            assert claimed is not None
            return self._job_from_row(claimed)

        return self._write(write)

    def complete_job(
        self,
        job_id: str,
        *,
        result: Mapping[str, Any] | None = None,
        lease_owner: str = "",
    ) -> dict[str, Any]:
        return self._finish_job(job_id, "completed", "", result or {}, lease_owner)

    def fail_job(
        self,
        job_id: str,
        *,
        error: str,
        retryable: bool = True,
        lease_owner: str = "",
        next_attempt_at: str = "",
    ) -> dict[str, Any]:
        state = "retryable" if retryable else "failed"

        def write(conn: sqlite3.Connection) -> dict[str, Any]:
            if lease_owner:
                current = conn.execute("SELECT lease_owner FROM population_jobs WHERE job_id = ?", (job_id,)).fetchone()
                if current is not None and current["lease_owner"] not in (None, lease_owner):
                    raise RuntimeError("job lease owner mismatch")
            conn.execute(
                """
                UPDATE population_jobs
                SET state = ?, lease_owner = NULL, lease_expires_at = NULL,
                    next_attempt_at = ?, last_error = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (state, next_attempt_at or None, error, self.now(), job_id),
            )
            row = conn.execute("SELECT * FROM population_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                raise RuntimeError(f"unknown population job: {job_id}")
            return self._job_from_row(row)

        return self._write(write)

    def _finish_job(
        self,
        job_id: str,
        state: str,
        error: str,
        result: Mapping[str, Any],
        lease_owner: str,
    ) -> dict[str, Any]:
        def write(conn: sqlite3.Connection) -> dict[str, Any]:
            if lease_owner:
                current = conn.execute("SELECT lease_owner FROM population_jobs WHERE job_id = ?", (job_id,)).fetchone()
                if current is not None and current["lease_owner"] not in (None, lease_owner):
                    raise RuntimeError("job lease owner mismatch")
            conn.execute(
                """
                UPDATE population_jobs
                SET state = ?, lease_owner = NULL, lease_expires_at = NULL,
                    last_error = ?, result_json = ?, updated_at = ?
                WHERE job_id = ?
                """,
                (state, error, _json_dumps(dict(result)), self.now(), job_id),
            )
            row = conn.execute("SELECT * FROM population_jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                raise RuntimeError(f"unknown population job: {job_id}")
            return self._job_from_row(row)

        return self._write(write)

    def new_id(self, prefix: str) -> str:
        return make_id(prefix)

    def now(self) -> str:
        return utc_now()

    def integrity_check(self) -> str:
        with self._read_conn() as conn:
            return str(conn.execute("PRAGMA integrity_check").fetchone()[0])

    def snapshot(self) -> dict[str, dict[str, Any]]:
        sources = {row["source_id"]: row for row in (self.get_source(item["source_id"]) for item in self._source_ids()) if row}
        segments = {row["segment_id"]: row for row in self.list_segments()}
        candidates = {row["candidate_id"]: row for row in self.list_candidates()}
        promotions = {row["request_id"]: row for row in self.list_promotions()}
        packets: dict[str, Any] = {}
        evaluations: dict[str, Any] = {}
        receipts: dict[str, Any] = {}
        idempotency: dict[str, Any] = {}
        approvals: dict[str, Any] = {}
        canonical_projection: dict[str, Any] = {}
        with self._read_conn() as conn:
            for row in conn.execute("SELECT packet_id FROM evidence_packets ORDER BY packet_id").fetchall():
                packet = self.get_packet(str(row["packet_id"]))
                if packet is not None:
                    packets[str(row["packet_id"])] = packet
            for row in conn.execute("SELECT evaluation_id FROM evaluations ORDER BY evaluation_id").fetchall():
                evaluation = self.get_evaluation(str(row["evaluation_id"]))
                if evaluation is not None:
                    evaluations[str(row["evaluation_id"])] = evaluation
            for row in conn.execute("SELECT receipt_id FROM population_receipts ORDER BY receipt_id").fetchall():
                receipt = self.get_receipt(str(row["receipt_id"]))
                if receipt is not None:
                    receipts[str(row["receipt_id"])] = receipt
            for row in conn.execute("SELECT * FROM idempotency_keys ORDER BY operation, principal_id, idempotency_key").fetchall():
                key = str(row["idempotency_key"])
                idempotency[key] = self.get_idempotency(
                    key,
                    operation=str(row["operation"]),
                    principal_id=str(row["principal_id"]),
                )
            for row in conn.execute("SELECT request_id FROM human_decision_events ORDER BY request_id").fetchall():
                decision = self.get_human_decision(str(row["request_id"]))
                if decision is not None:
                    approvals[str(decision["approval_id"])] = decision
            for row in conn.execute("SELECT candidate_id FROM canonical_projection_receipts ORDER BY candidate_id").fetchall():
                projection = self.get_canonical_projection(str(row["candidate_id"]))
                if projection is not None:
                    canonical_projection[str(row["candidate_id"])] = projection
        return {
            "sources": sources,
            "segments": segments,
            "packets": packets,
            "candidates": candidates,
            "evaluations": evaluations,
            "receipts": receipts,
            "idempotency": idempotency,
            "promotions": promotions,
            "approvals": approvals,
            "canonical_projection": canonical_projection,
        }

    def dump_audit(self) -> str:
        tables = (
            "shape_sources",
            "shape_segments",
            "evidence_inquiries",
            "evidence_packets",
            "evidence_packet_blocks",
            "population_jobs",
            "candidates",
            "evaluations",
            "candidate_events",
            "population_receipts",
            "idempotency_keys",
            "promotion_requests",
            "human_decision_events",
            "canonical_projection_receipts",
            "shape_schema_migrations",
        )
        with self._read_conn() as conn:
            payload = {
                table: [dict(row) for row in conn.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()]
                for table in tables
            }
        return json.dumps(payload, indent=2, sort_keys=True)

    def _source_ids(self) -> list[dict[str, str]]:
        with self._read_conn() as conn:
            rows = conn.execute("SELECT source_id FROM shape_sources ORDER BY source_id").fetchall()
        return [{"source_id": str(row["source_id"])} for row in rows]

    def _append_candidate_event(
        self,
        conn: sqlite3.Connection,
        candidate_id: str,
        previous_status: str | None,
        new_status: str,
        actor_context: Mapping[str, Any],
    ) -> None:
        conn.execute(
            """
            INSERT INTO candidate_events (
                event_id, candidate_id, event_type, previous_status, new_status, actor_context_json, created_at
            )
            VALUES (?, ?, 'status_changed', ?, ?, ?, ?)
            """,
            (
                self.new_id("cevt"),
                candidate_id,
                previous_status,
                new_status,
                _json_dumps(dict(actor_context)),
                self.now(),
            ),
        )

    def _source_normalization_version(self, conn: sqlite3.Connection, source_id: str) -> str:
        row = conn.execute(
            "SELECT normalization_version FROM shape_sources WHERE source_id = ?",
            (source_id,),
        ).fetchone()
        if row is None:
            # Post-ingest enqueue may precede Shape normalization.
            return "pending"
        return str(row["normalization_version"])

    def _source_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "source_id": str(row["source_id"]),
            "content_sha256": str(row["content_sha256"]),
            "content_pointer": str(row["content_pointer"]),
            "raw_ref": str(row["content_pointer"]),
            "locator": str(row["content_pointer"]),
            "modality": str(row["modality"]),
            "normalization_version": str(row["normalization_version"]),
            "metadata": _json_loads(row["metadata_json"], {}),
            "created_at": str(row["created_at"]),
        }

    def _segment_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        metadata = _json_loads(row["metadata_json"], {})
        return {
            "segment_id": str(row["segment_id"]),
            "source_id": str(row["source_id"]),
            "ordinal": int(row["ordinal"]),
            "char_start": int(row["char_start"]),
            "char_end": int(row["char_end"]),
            "byte_start": row["byte_start"],
            "byte_end": row["byte_end"],
            "structure_path": str(row["structure_path"]),
            "text_sha256": str(row["text_sha256"]),
            "metadata": metadata,
            "text_ref": dict(metadata.get("text_ref") or {}),
        }

    def _packet_block_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "packet_id": str(row["packet_id"]),
            "block_id": str(row["block_id"]),
            "source_id": str(row["source_id"]),
            "segment_id": str(row["segment_id"]),
            "ordinal": int(row["ordinal"]),
            "char_start": int(row["char_start"]),
            "char_end": int(row["char_end"]),
            "byte_start": row["byte_start"],
            "byte_end": row["byte_end"],
            "text_sha256": str(row["text_sha256"]),
            "structure_path": str(row["structure_path"]),
            "metadata": _json_loads(row["metadata_json"], {}),
            "envelope": "quoted_data",
            "instruction_authority": False,
        }

    def _candidate_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        semantic = _json_loads(row["semantic_payload_json"], {})
        execution = _json_loads(row["execution_metadata_json"], {})
        return {
            "candidate_id": str(row["candidate_id"]),
            "status": str(row["status"]),
            "packet_id": str(row["packet_id"]),
            **semantic,
            **execution,
            "schema_version": str(row["schema_version"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
            "content_fingerprint": str(row["fingerprint"]),
        }

    def _evaluation_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        payload = _json_loads(row["payload_json"], {})
        execution = _json_loads(row["execution_metadata_json"], {})
        return {
            "evaluation_id": str(row["evaluation_id"]),
            "candidate_id": str(row["candidate_id"]),
            "disposition": str(row["disposition"]),
            **payload,
            **execution,
            "schema_version": str(row["schema_version"]),
            "created_at": str(row["created_at"]),
            "content_fingerprint": str(row["fingerprint"]),
        }

    def _promotion_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "request_id": str(row["request_id"]),
            "candidate_id": str(row["candidate_id"]),
            "evaluation_id": str(row["evaluation_id"]),
            "status": str(row["status"]),
            "rationale": str(row["rationale"]),
            "evidence_refs": _json_loads(row["evidence_refs_json"], []),
            "requester_identity": str(row["requester_principal_id"]),
            "requester_principal_id": str(row["requester_principal_id"]),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
            "content_fingerprint": str(row["fingerprint"]),
        }

    def _human_decision_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "decision_event_id": str(row["decision_event_id"]),
            "approval_id": str(row["decision_event_id"]),
            "request_id": str(row["request_id"]),
            "decision": str(row["decision"]),
            "human_principal_id": str(row["human_principal_id"]),
            "approval_identity": str(row["human_principal_id"]),
            "reason": str(row["reason"]),
            "approval_reason": str(row["reason"]),
            "context": _json_loads(row["context_json"], {}),
            "created_at": str(row["created_at"]),
            "immutable": True,
        }

    def _canonical_receipt_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "receipt_id": str(row["receipt_id"]),
            "request_id": str(row["request_id"]),
            "candidate_id": str(row["candidate_id"]),
            "operation": str(row["operation"]),
            "canonical_id": str(row["canonical_id"]),
            "canonical_result": _json_loads(row["canonical_result_json"], {}),
            "idempotency_key": str(row["idempotency_key"]),
            "created_at": str(row["created_at"]),
        }

    def _job_from_row(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "job_id": str(row["job_id"]),
            "source_id": str(row["source_id"]),
            "normalization_version": str(row["normalization_version"]),
            "state": str(row["state"]),
            "attempt_count": int(row["attempt_count"]),
            "lease_owner": row["lease_owner"],
            "lease_expires_at": row["lease_expires_at"],
            "next_attempt_at": row["next_attempt_at"],
            "last_error": row["last_error"],
            "payload": _json_loads(row["payload_json"], {}),
            "result": _json_loads(row["result_json"], {}),
            "created_at": str(row["created_at"]),
            "updated_at": str(row["updated_at"]),
        }


def utc_now_plus_seconds(seconds: int) -> str:
    from datetime import datetime, timedelta, timezone

    return (datetime.now(timezone.utc).replace(microsecond=0) + timedelta(seconds=seconds)).isoformat()


PopulationStore = ShapePopulationStore
