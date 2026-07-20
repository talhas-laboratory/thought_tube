"""SQLite migrations for Shape Population workflow authority."""

from __future__ import annotations

import hashlib
import sqlite3
from dataclasses import dataclass
from typing import Iterable

MODULE_ID = "kernel.shape_population.migrations"
CONTRACT_VERSION = "1.1.0"
SCHEMA_VERSION = 2
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "Migration",
    "MIGRATIONS",
    "apply_migrations",
)
__all__ = list(PUBLIC_API)


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    sql: str

    @property
    def checksum(self) -> str:
        return hashlib.sha256(self.sql.encode("utf-8")).hexdigest()


SCHEMA_V1_SQL = """
CREATE TABLE shape_sources (
    source_id TEXT PRIMARY KEY,
    content_sha256 TEXT NOT NULL CHECK (length(content_sha256) > 0),
    content_pointer TEXT NOT NULL CHECK (length(content_pointer) > 0),
    modality TEXT NOT NULL CHECK (length(modality) > 0),
    normalization_version TEXT NOT NULL CHECK (length(normalization_version) > 0),
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE shape_segments (
    segment_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES shape_sources(source_id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    char_start INTEGER NOT NULL CHECK (char_start >= 0),
    char_end INTEGER NOT NULL CHECK (char_end >= char_start),
    byte_start INTEGER CHECK (byte_start IS NULL OR byte_start >= 0),
    byte_end INTEGER CHECK (byte_end IS NULL OR byte_start IS NULL OR byte_end >= byte_start),
    structure_path TEXT NOT NULL DEFAULT '',
    text_sha256 TEXT NOT NULL CHECK (length(text_sha256) > 0),
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_id, ordinal),
    UNIQUE (source_id, structure_path, ordinal)
);

CREATE INDEX ix_shape_segments_source ON shape_segments(source_id, ordinal);

CREATE TABLE evidence_inquiries (
    inquiry_id TEXT PRIMARY KEY,
    requester_principal_id TEXT NOT NULL CHECK (length(requester_principal_id) > 0),
    requester_kind TEXT NOT NULL DEFAULT 'agent'
        CHECK (requester_kind IN ('service', 'agent', 'human')),
    question_scope_json TEXT NOT NULL,
    policy_version TEXT NOT NULL CHECK (length(policy_version) > 0),
    fingerprint TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE evidence_packets (
    packet_id TEXT PRIMARY KEY,
    inquiry_id TEXT NOT NULL REFERENCES evidence_inquiries(inquiry_id) ON DELETE RESTRICT,
    corpus_revision TEXT NOT NULL CHECK (length(corpus_revision) > 0),
    packet_fingerprint TEXT NOT NULL UNIQUE,
    budget_ledger_json TEXT NOT NULL DEFAULT '{}',
    omitted_json TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL CHECK (status IN ('assembling', 'ready', 'empty', 'failed')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE evidence_packet_blocks (
    packet_id TEXT NOT NULL REFERENCES evidence_packets(packet_id) ON DELETE CASCADE,
    block_id TEXT NOT NULL,
    segment_id TEXT NOT NULL REFERENCES shape_segments(segment_id) ON DELETE RESTRICT,
    source_id TEXT NOT NULL REFERENCES shape_sources(source_id) ON DELETE RESTRICT,
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    char_start INTEGER NOT NULL CHECK (char_start >= 0),
    char_end INTEGER NOT NULL CHECK (char_end >= char_start),
    byte_start INTEGER CHECK (byte_start IS NULL OR byte_start >= 0),
    byte_end INTEGER CHECK (byte_end IS NULL OR byte_start IS NULL OR byte_end >= byte_start),
    text_sha256 TEXT NOT NULL CHECK (length(text_sha256) > 0),
    structure_path TEXT NOT NULL DEFAULT '',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (packet_id, block_id),
    UNIQUE (packet_id, ordinal),
    UNIQUE (packet_id, segment_id, char_start, char_end, text_sha256)
);

CREATE INDEX ix_packet_blocks_segment ON evidence_packet_blocks(segment_id);

CREATE TABLE population_jobs (
    job_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    normalization_version TEXT NOT NULL CHECK (length(normalization_version) > 0),
    state TEXT NOT NULL CHECK (
        state IN (
            'queued', 'claimed', 'running', 'completed', 'failed',
            'retryable', 'blocked', 'dead_letter', 'cancelled'
        )
    ),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    lease_owner TEXT,
    lease_expires_at TEXT,
    next_attempt_at TEXT,
    last_error TEXT,
    payload_json TEXT NOT NULL DEFAULT '{}',
    result_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX ux_population_jobs_active_source_revision
ON population_jobs(source_id, normalization_version)
WHERE state NOT IN ('completed', 'failed', 'dead_letter', 'cancelled');

CREATE INDEX ix_population_jobs_claimable
ON population_jobs(state, next_attempt_at, lease_expires_at);

CREATE TABLE candidates (
    candidate_id TEXT PRIMARY KEY,
    packet_id TEXT NOT NULL REFERENCES evidence_packets(packet_id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (
        status IN (
            'proposed', 'under_review', 'rejected', 'needs_evidence',
            'recommended', 'promotion_requested', 'canonical'
        )
    ),
    semantic_payload_json TEXT NOT NULL,
    execution_metadata_json TEXT NOT NULL DEFAULT '{}',
    fingerprint TEXT NOT NULL UNIQUE,
    schema_version TEXT NOT NULL CHECK (length(schema_version) > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_candidates_packet ON candidates(packet_id);
CREATE INDEX ix_candidates_status ON candidates(status);

CREATE TABLE evaluations (
    evaluation_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    disposition TEXT NOT NULL CHECK (
        disposition IN ('under_review', 'recommended', 'rejected', 'needs_evidence')
    ),
    payload_json TEXT NOT NULL,
    execution_metadata_json TEXT NOT NULL DEFAULT '{}',
    fingerprint TEXT NOT NULL UNIQUE,
    schema_version TEXT NOT NULL CHECK (length(schema_version) > 0),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_evaluations_candidate ON evaluations(candidate_id);

CREATE TABLE candidate_events (
    event_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (length(event_type) > 0),
    previous_status TEXT CHECK (
        previous_status IS NULL OR previous_status IN (
            'proposed', 'under_review', 'rejected', 'needs_evidence',
            'recommended', 'promotion_requested', 'canonical'
        )
    ),
    new_status TEXT CHECK (
        new_status IS NULL OR new_status IN (
            'proposed', 'under_review', 'rejected', 'needs_evidence',
            'recommended', 'promotion_requested', 'canonical'
        )
    ),
    actor_context_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_candidate_events_candidate ON candidate_events(candidate_id, created_at);

CREATE TABLE population_receipts (
    receipt_id TEXT PRIMARY KEY,
    operation TEXT NOT NULL CHECK (length(operation) > 0),
    request_id TEXT NOT NULL CHECK (length(request_id) > 0),
    outcome TEXT NOT NULL CHECK (length(outcome) > 0),
    candidate_id TEXT REFERENCES candidates(candidate_id) ON DELETE SET NULL,
    evaluation_id TEXT REFERENCES evaluations(evaluation_id) ON DELETE SET NULL,
    packet_id TEXT REFERENCES evidence_packets(packet_id) ON DELETE SET NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_population_receipts_operation ON population_receipts(operation, request_id);

CREATE TABLE idempotency_keys (
    operation TEXT NOT NULL,
    principal_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    request_fingerprint TEXT NOT NULL,
    result_ids_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (operation, principal_id, idempotency_key)
);

CREATE TABLE promotion_requests (
    request_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id) ON DELETE RESTRICT,
    evaluation_id TEXT NOT NULL REFERENCES evaluations(evaluation_id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (
        status IN ('requested', 'approved', 'applying', 'applied', 'rejected')
    ),
    rationale TEXT NOT NULL DEFAULT '',
    evidence_refs_json TEXT NOT NULL DEFAULT '[]',
    requester_principal_id TEXT NOT NULL CHECK (length(requester_principal_id) > 0),
    fingerprint TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_promotion_requests_candidate ON promotion_requests(candidate_id);
CREATE INDEX ix_promotion_requests_status ON promotion_requests(status);

CREATE TABLE human_decision_events (
    decision_event_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL UNIQUE REFERENCES promotion_requests(request_id) ON DELETE RESTRICT,
    decision TEXT NOT NULL CHECK (decision IN ('approved', 'rejected')),
    human_principal_id TEXT NOT NULL CHECK (length(human_principal_id) > 0),
    reason TEXT NOT NULL CHECK (length(reason) > 0),
    context_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE canonical_projection_receipts (
    receipt_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES promotion_requests(request_id) ON DELETE RESTRICT,
    candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id) ON DELETE RESTRICT,
    operation TEXT NOT NULL CHECK (operation IN ('apply', 'rollback')),
    canonical_id TEXT NOT NULL DEFAULT '',
    canonical_result_json TEXT NOT NULL DEFAULT '{}',
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_canonical_projection_receipts_candidate
ON canonical_projection_receipts(candidate_id, created_at);

CREATE TRIGGER trg_candidate_events_immutable_update
BEFORE UPDATE ON candidate_events
BEGIN
    SELECT RAISE(ABORT, 'candidate_events are immutable');
END;

CREATE TRIGGER trg_candidate_events_immutable_delete
BEFORE DELETE ON candidate_events
BEGIN
    SELECT RAISE(ABORT, 'candidate_events are immutable');
END;

CREATE TRIGGER trg_population_receipts_immutable_update
BEFORE UPDATE ON population_receipts
BEGIN
    SELECT RAISE(ABORT, 'population_receipts are immutable');
END;

CREATE TRIGGER trg_population_receipts_immutable_delete
BEFORE DELETE ON population_receipts
BEGIN
    SELECT RAISE(ABORT, 'population_receipts are immutable');
END;

CREATE TRIGGER trg_human_decision_events_immutable_update
BEFORE UPDATE ON human_decision_events
BEGIN
    SELECT RAISE(ABORT, 'human_decision_events are immutable');
END;

CREATE TRIGGER trg_human_decision_events_immutable_delete
BEFORE DELETE ON human_decision_events
BEGIN
    SELECT RAISE(ABORT, 'human_decision_events are immutable');
END;

-- A rejected request is terminal for that request. A later promotion attempt
-- must create a new evaluation and a new promotion request.
CREATE TRIGGER trg_promotion_requests_rejected_terminal
BEFORE UPDATE OF status ON promotion_requests
WHEN OLD.status = 'rejected' AND NEW.status <> 'rejected'
BEGIN
    SELECT RAISE(ABORT, 'rejected promotion requests are terminal');
END;
"""

SCHEMA_V2_SQL = """
CREATE TABLE comparison_sets (
    comparison_set_version TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL REFERENCES candidates(candidate_id) ON DELETE CASCADE,
    policy_version TEXT NOT NULL CHECK (length(policy_version) > 0),
    retriever_profile_json TEXT NOT NULL DEFAULT '{}',
    neighbors_json TEXT NOT NULL DEFAULT '[]',
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_comparison_sets_candidate ON comparison_sets(candidate_id, created_at);
"""

MIGRATIONS: tuple[Migration, ...] = (
    Migration(version=1, name="shape_population_schema_v1", sql=SCHEMA_V1_SQL),
    Migration(version=2, name="shape_population_comparison_sets_v2", sql=SCHEMA_V2_SQL),
)


def _known_versions(migrations: Iterable[Migration]) -> dict[int, Migration]:
    known = {migration.version: migration for migration in migrations}
    if sorted(known) != list(range(1, len(known) + 1)):
        raise RuntimeError("shape population migrations must be numbered contiguously from 1")
    return known


def _execute_script(conn: sqlite3.Connection, sql: str) -> None:
    statement = ""
    for line in sql.splitlines():
        statement += line + "\n"
        if sqlite3.complete_statement(statement):
            conn.execute(statement)
            statement = ""
    if statement.strip():
        raise RuntimeError("incomplete shape population migration SQL")


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply all known migrations under a single BEGIN IMMEDIATE lock."""

    conn.row_factory = sqlite3.Row
    migrations = _known_versions(MIGRATIONS)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS shape_schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        rows = conn.execute(
            "SELECT version, name, checksum FROM shape_schema_migrations ORDER BY version ASC"
        ).fetchall()
        applied = {int(row["version"]): str(row["checksum"]) for row in rows}
        unknown = sorted(set(applied) - set(migrations))
        if unknown:
            raise RuntimeError(f"unknown shape population migration(s): {unknown}")
        for version, checksum in applied.items():
            expected = migrations[version].checksum
            if checksum != expected:
                raise RuntimeError(
                    f"shape population migration {version} checksum mismatch: "
                    f"stored={checksum} expected={expected}"
                )
        for migration in MIGRATIONS:
            if migration.version in applied:
                continue
            _execute_script(conn, migration.sql)
            conn.execute(
                """
                INSERT INTO shape_schema_migrations (version, name, checksum)
                VALUES (?, ?, ?)
                """,
                (migration.version, migration.name, migration.checksum),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
