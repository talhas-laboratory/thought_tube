import json
import os
import shutil
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock

from conversation_os.cli import init_repo
from conversation_os.mtsf_extraction_skill import (
    build_skill_input_envelope,
    resolve_deep_extraction_draft,
)
from conversation_os.mtsf_llm_backend import (
    LlmExtractionError,
    build_mtsf_extraction_messages,
    list_llm_backend_candidates,
    request_openrouter_chat_completion,
    resolve_mtsf_llm_settings,
    run_llm_extraction_chain,
)
from conversation_os.storage import read_json, write_json

REPO_ROOT = Path(__file__).resolve().parents[1]

TRIANGULATION_EVENTS = [
    {
        "actor": "user",
        "content": (
            "Explain how the same query would be processed without any prior context, "
            "with relevant prior context, and with unrelated prior context in latent topology."
        ),
    }
]
MANIFEST = {
    "title": "Topology import",
    "source_type": "imported_transcript",
    "domains": ["research"],
}


def _reference_draft_payload() -> dict:
    draft_path = (
        REPO_ROOT
        / "docs/frameworks/metaphysical-thought-space/evals/semantic-shape-extraction/drafts/latent-triangulation.reference.json"
    )
    return json.loads(draft_path.read_text(encoding="utf-8"))


def _mock_openrouter_response(draft: dict, *, model: str = "openai/gpt-4o-mini") -> mock.Mock:
    body = {
        "choices": [{"message": {"content": json.dumps(draft)}}],
        "model": model,
        "usage": {"prompt_tokens": 120, "completion_tokens": 80, "total_tokens": 200},
    }
    response = mock.Mock()
    response.read.return_value = json.dumps(body).encode("utf-8")
    response.__enter__ = mock.Mock(return_value=response)
    response.__exit__ = mock.Mock(return_value=False)
    return response


class MtsfLlmBackendTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        init_repo(self.root)
        docs_link = self.root / "docs"
        if docs_link.exists() or docs_link.is_symlink():
            if docs_link.is_symlink() or docs_link.is_file():
                docs_link.unlink()
            else:
                shutil.rmtree(docs_link)
        os.symlink(REPO_ROOT / "docs", docs_link, target_is_directory=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_runtime(self, payload: dict) -> None:
        runtime_path = self.root / "product" / "inner_world_v1" / "config" / "runtime.json"
        runtime_path.parent.mkdir(parents=True, exist_ok=True)
        write_json(runtime_path, payload)

    def test_resolve_settings_prefers_mtsf_env_over_runtime(self) -> None:
        self._write_runtime(
            {
                "chat_backend": "heuristic",
                "mtsf_llm": {
                    "api_key": "runtime-key",
                    "model": "anthropic/claude-3.5-sonnet",
                },
            }
        )
        with mock.patch.dict(
            os.environ,
            {
                "MTSF_OPENROUTER_API_KEY": "env-key",
                "MTSF_OPENROUTER_MODEL": "openai/gpt-4o",
            },
            clear=False,
        ):
            settings = resolve_mtsf_llm_settings(self.root)
        self.assertEqual(settings["api_key"], "env-key")
        self.assertEqual(settings["model"], "openai/gpt-4o")
        self.assertTrue(settings["openrouter_enabled"])
        self.assertFalse(settings["openclaw_enabled"])

    def test_list_candidates_auto_skips_disabled_backends(self) -> None:
        self._write_runtime(
            {
                "chat_backend": "heuristic",
                "mtsf_llm": {"api_key": "test-key", "backend_order": ["openclaw", "openrouter"]},
            }
        )
        auto_candidates = list_llm_backend_candidates(self.root, llm_preference="auto")
        self.assertEqual(auto_candidates, ["openrouter"])
        api_candidates = list_llm_backend_candidates(self.root, llm_preference="api")
        self.assertEqual(api_candidates, ["openrouter"])

    def test_list_candidates_force_includes_openclaw_when_configured(self) -> None:
        self._write_runtime(
            {
                "chat_backend": "openclaw_local",
                "mtsf_llm": {"api_key": "test-key"},
            }
        )
        candidates = list_llm_backend_candidates(self.root, llm_preference="force")
        self.assertEqual(candidates, ["openclaw", "openrouter"])

    def test_build_messages_include_envelope_and_skill_excerpt(self) -> None:
        envelope = build_skill_input_envelope(
            session_id="sess-llm",
            events=TRIANGULATION_EVENTS,
            manifest=MANIFEST,
            raw_content=TRIANGULATION_EVENTS[0]["content"],
        )
        messages = build_mtsf_extraction_messages(
            system_prompt="system",
            skill_excerpt="skill excerpt",
            envelope=envelope,
            session_id="sess-llm",
        )
        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("skill excerpt", messages[0]["content"])
        self.assertIn("Topology import", messages[1]["content"])

    def test_request_openrouter_chat_completion_parses_success(self) -> None:
        draft = _reference_draft_payload()
        with mock.patch(
            "conversation_os.mtsf_llm_backend.urlopen",
            return_value=_mock_openrouter_response(draft),
        ):
            result = request_openrouter_chat_completion(
                api_key="test-key",
                model="openai/gpt-4o-mini",
                messages=[{"role": "user", "content": "emit draft"}],
            )
        self.assertEqual(result["backend_id"], "openrouter")
        self.assertIn("draft_id", result["content"])

    def test_request_openrouter_chat_completion_raises_on_empty_choices(self) -> None:
        response = mock.Mock()
        response.read.return_value = json.dumps({"choices": []}).encode("utf-8")
        response.__enter__ = mock.Mock(return_value=response)
        response.__exit__ = mock.Mock(return_value=False)
        with mock.patch("conversation_os.mtsf_llm_backend.urlopen", return_value=response):
            with self.assertRaises(LlmExtractionError) as ctx:
                request_openrouter_chat_completion(
                    api_key="test-key",
                    model="openai/gpt-4o-mini",
                    messages=[{"role": "user", "content": "emit draft"}],
                )
        self.assertEqual(ctx.exception.backend_id, "openrouter")

    def test_run_chain_uses_openrouter_when_configured(self) -> None:
        self._write_runtime({"chat_backend": "heuristic", "mtsf_llm": {"api_key": "test-key"}})
        envelope = build_skill_input_envelope(
            session_id="sess-openrouter",
            events=TRIANGULATION_EVENTS,
            manifest=MANIFEST,
            raw_content=TRIANGULATION_EVENTS[0]["content"],
        )
        draft = _reference_draft_payload()

        def _parse(text: str) -> dict:
            from conversation_os.mtsf_extraction_skill import parse_extraction_draft_from_text

            parsed = parse_extraction_draft_from_text(
                self.root,
                text,
                session_id="sess-openrouter",
                envelope=envelope,
            )
            parsed["session_id"] = "sess-openrouter"
            return parsed

        with mock.patch(
            "conversation_os.mtsf_llm_backend.urlopen",
            return_value=_mock_openrouter_response(draft),
        ):
            result = run_llm_extraction_chain(
                self.root,
                session_id="sess-openrouter",
                envelope=envelope,
                system_prompt="system",
                skill_excerpt="skill",
                parse_draft=_parse,
                llm_preference="api",
            )
        self.assertEqual(result["source"], "llm")
        self.assertEqual(result["selected_backend"], "openrouter")
        self.assertEqual(result["draft"]["provenance"]["model_id"], "openrouter:openai/gpt-4o-mini")

    def test_run_chain_falls_through_after_openclaw_failure(self) -> None:
        self._write_runtime(
            {
                "chat_backend": "openclaw_local",
                "mtsf_llm": {"api_key": "test-key"},
            }
        )
        envelope = build_skill_input_envelope(
            session_id="sess-fallback",
            events=TRIANGULATION_EVENTS,
            manifest=MANIFEST,
            raw_content=TRIANGULATION_EVENTS[0]["content"],
        )
        draft = _reference_draft_payload()

        def _parse(text: str) -> dict:
            from conversation_os.mtsf_extraction_skill import parse_extraction_draft_from_text

            parsed = parse_extraction_draft_from_text(
                self.root,
                text,
                session_id="sess-fallback",
                envelope=envelope,
            )
            parsed["session_id"] = "sess-fallback"
            return parsed

        with mock.patch(
            "conversation_os.mtsf_llm_backend._attempt_openclaw",
            side_effect=LlmExtractionError("openclaw_down", backend_id="openclaw"),
        ), mock.patch(
            "conversation_os.mtsf_llm_backend.urlopen",
            return_value=_mock_openrouter_response(draft),
        ):
            result = run_llm_extraction_chain(
                self.root,
                session_id="sess-fallback",
                envelope=envelope,
                system_prompt="system",
                skill_excerpt="skill",
                parse_draft=_parse,
                llm_preference="auto",
            )
        self.assertEqual(result["selected_backend"], "openrouter")
        self.assertEqual(len(result["backend_attempts"]), 1)
        self.assertEqual(result["backend_attempts"][0]["backend"], "openclaw")

    def test_run_chain_raises_with_attempt_trace_when_all_backends_fail(self) -> None:
        self._write_runtime({"chat_backend": "heuristic", "mtsf_llm": {"api_key": "test-key"}})
        envelope = build_skill_input_envelope(
            session_id="sess-fail",
            events=TRIANGULATION_EVENTS,
            manifest=MANIFEST,
            raw_content=TRIANGULATION_EVENTS[0]["content"],
        )

        def _parse(_text: str) -> dict:
            raise ValueError("invalid_json")

        with mock.patch(
            "conversation_os.mtsf_llm_backend.urlopen",
            return_value=_mock_openrouter_response({"not": "a draft"}),
        ):
            with self.assertRaises(LlmExtractionError) as ctx:
                run_llm_extraction_chain(
                    self.root,
                    session_id="sess-fail",
                    envelope=envelope,
                    system_prompt="system",
                    skill_excerpt="skill",
                    parse_draft=_parse,
                    llm_preference="api",
                )
        self.assertEqual(ctx.exception.attempts[0]["backend"], "openrouter")

    def test_resolve_auto_uses_openrouter_when_available(self) -> None:
        self._write_runtime({"chat_backend": "heuristic", "mtsf_llm": {"api_key": "test-key"}})
        draft = _reference_draft_payload()
        with mock.patch(
            "conversation_os.mtsf_llm_backend.urlopen",
            return_value=_mock_openrouter_response(draft),
        ):
            result = resolve_deep_extraction_draft(
                self.root,
                session_id="sess-resolve-llm",
                events=TRIANGULATION_EVENTS,
                manifest=MANIFEST,
                llm_preference="auto",
            )
        self.assertEqual(result["source"], "llm")
        self.assertEqual(result["backend_id"], "openrouter")
        self.assertIn("openrouter:", result["draft"]["provenance"]["model_id"])

    def test_resolve_auto_writes_trace_and_falls_back_to_open_evidence(self) -> None:
        events = [
            {
                "actor": "assistant",
                "content": (
                    "I'll treat that sort as liminal spatial psychological horror where architecture "
                    "behaves like a subconscious maze. Closest to Backrooms / liminal-space horror."
                ),
            }
        ]
        result = resolve_deep_extraction_draft(
            self.root,
            session_id="sess-trace",
            events=events,
            manifest=MANIFEST,
            llm_preference="auto",
        )
        self.assertEqual(result["source"], "open_evidence")
        self.assertIn("fallback_reason", result)
        trace_path = self.root / "memory" / "sessions" / "sess-trace" / "mtsf" / "llm_extraction_trace.json"
        self.assertTrue(trace_path.exists())
        trace = read_json(trace_path, default={})
        self.assertEqual(trace["selected_source"], "open_evidence")
        self.assertEqual(trace["llm_preference"], "auto")

    def test_resolve_force_raises_without_backends(self) -> None:
        with self.assertRaises(LlmExtractionError):
            resolve_deep_extraction_draft(
                self.root,
                session_id="sess-force-fail",
                events=TRIANGULATION_EVENTS,
                manifest=MANIFEST,
                llm_preference="force",
            )


if __name__ == "__main__":
    unittest.main()
