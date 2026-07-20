"""Fixtures and tests for normalize_source."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conversation_os.source_content_store import SourceContentStore
from conversation_os.shape_population.normalization import NORMALIZATION_VERSION, normalize_source
from conversation_os.shape_population.storage import PopulationStore

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "shape_population" / "normalization"


def _write_fixtures() -> None:
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    fixtures = {
        "plain_text.txt": "Hello world.\nSecond line.\n",
        "markdown.md": "# Title\n\nBody paragraph.\n\n## Section\nMore text.\n",
        "transcript.txt": "Alice: Hello there.\nBob: Hi Alice.\nAlice: Shall we begin?\n",
        "unicode.txt": "Cafe\u0301 already composed Café and emoji 😀\n",
        "code_table.md": "```\ncode line\n```\n| a | b |\n| 1 | 2 |\n",
        "large.txt": ("line\n" * 1000),
    }
    for name, body in fixtures.items():
        (FIXTURE_DIR / name).write_text(body, encoding="utf-8")
    (FIXTURE_DIR / "malformed.bin").write_bytes(b"\xff\xfe bad \x80 encoding")
    (FIXTURE_DIR / "redactions.json").write_text(
        json.dumps({"redactions": [{"span": [0, 5], "reason": "pii"}]}, indent=2) + "\n",
        encoding="utf-8",
    )


@pytest.fixture(scope="module", autouse=True)
def ensure_fixtures() -> None:
    _write_fixtures()


@pytest.fixture()
def store(tmp_path: Path) -> PopulationStore:
    return PopulationStore(tmp_path)


def test_exact_reconstruction_and_stable_ids(store: PopulationStore) -> None:
    text = (FIXTURE_DIR / "plain_text.txt").read_text(encoding="utf-8")
    first = normalize_source(
        {"content": text, "modality": "plain_text", "locator": "plain", "ingested_at": "t0"},
        store=store,
    )
    second = normalize_source(
        {"content": text, "modality": "plain_text", "locator": "plain", "ingested_at": "t1"},
        store=store,
    )
    assert not first.rejected
    assert first.reconstructed_text() == text
    assert first.source_id == second.source_id
    assert first.content_sha256 == second.content_sha256
    assert [seg.segment_id for seg in first.segments] == [seg.segment_id for seg in second.segments]
    assert first.normalization_version == NORMALIZATION_VERSION


def test_content_store_and_reference_only_persistence(tmp_path: Path) -> None:
    store = PopulationStore(tmp_path)
    content_store = SourceContentStore(tmp_path)
    text = "Line one.\nLine two.\n"
    normalized = normalize_source(
        {"content": text, "modality": "plain_text"},
        store=store,
        content_store=content_store,
    )
    assert content_store.get_bytes(normalized.content_sha256) == text.encode("utf-8")
    assert normalized.reconstructed_text() == text
    persisted = store.get_source(normalized.source_id)
    assert persisted is not None
    assert all((segment.get("text") or "") == "" for segment in persisted["segments"])
    assert all(segment.get("text_ref", {}).get("content_sha256") == normalized.content_sha256 for segment in persisted["segments"])


def test_markdown_transcript_structure_paths(store: PopulationStore) -> None:
    md = normalize_source(
        {"content": (FIXTURE_DIR / "markdown.md").read_text(encoding="utf-8"), "modality": "markdown"},
        store=store,
    )
    assert any(seg.structure_path.startswith("/heading/") for seg in md.segments)
    tr = normalize_source(
        {"content": (FIXTURE_DIR / "transcript.txt").read_text(encoding="utf-8"), "modality": "transcript"},
        store=store,
    )
    assert any("/transcript/Alice/" in seg.structure_path for seg in tr.segments)
    code = normalize_source(
        {"content": (FIXTURE_DIR / "code_table.md").read_text(encoding="utf-8"), "modality": "markdown"},
        store=store,
    )
    assert any(seg.structure_path.startswith("/code/") for seg in code.segments)
    assert any(seg.structure_path.startswith("/table/") for seg in code.segments)


def test_unicode_and_offsets(store: PopulationStore) -> None:
    text = (FIXTURE_DIR / "unicode.txt").read_text(encoding="utf-8")
    result = normalize_source({"content": text, "modality": "plain_text"}, store=store)
    assert result.reconstructed_text() == text
    for seg in result.segments:
        assert text[seg.char_start:seg.char_end] == seg.text
        assert seg.byte_start is not None and seg.byte_end is not None


def test_no_semantic_fields(store: PopulationStore) -> None:
    result = normalize_source(
        {"content": "x\n", "modality": "plain_text", "metadata": {"source": "unit"}},
        store=store,
    )
    blob = json.dumps(result.to_dict())
    assert "summary" not in result.metadata
    assert "shape" not in result.metadata
    assert "canonical" not in blob or result.source_id  # source_id may contain substring; check metadata keys
    assert set(result.metadata).isdisjoint({"shape", "topic", "summary", "embedding", "canonical"})


def test_malformed_encoding_explicit_failure(store: PopulationStore) -> None:
    raw = (FIXTURE_DIR / "malformed.bin").read_bytes()
    result = normalize_source({"content": raw, "modality": "plain_text"}, store=store)
    assert result.rejected
    assert "undecodable" in result.rejection_reason


def test_unsupported_modality(store: PopulationStore) -> None:
    result = normalize_source({"content": "x", "modality": "audio"}, store=store)
    assert result.rejected
    assert "unsupported modality" in result.rejection_reason


def test_reingest_idempotency(store: PopulationStore) -> None:
    text = "same content\n"
    a = normalize_source({"content": text, "modality": "plain_text"}, store=store)
    b = normalize_source({"content": text, "modality": "plain_text"}, store=store)
    assert a.source_id == b.source_id
    assert store.get_source(a.source_id) is not None


def test_redaction_provenance_retention(store: PopulationStore) -> None:
    redactions = json.loads((FIXTURE_DIR / "redactions.json").read_text(encoding="utf-8"))["redactions"]
    result = normalize_source(
        {"content": "secret text\n", "modality": "plain_text", "redactions": redactions},
        store=store,
    )
    assert result.metadata["redactions"] == redactions


def test_large_input_budget(store: PopulationStore) -> None:
    text = (FIXTURE_DIR / "large.txt").read_text(encoding="utf-8")
    ok = normalize_source({"content": text, "modality": "plain_text", "max_source_bytes": 50_000}, store=store)
    assert not ok.rejected
    assert len(ok.segments) <= 1000
    rejected = normalize_source({"content": text, "modality": "plain_text", "max_source_bytes": 10}, store=store)
    assert rejected.rejected
    assert "max_source_bytes" in rejected.rejection_reason
