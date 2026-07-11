from __future__ import annotations

import unittest

from conversation_os.note_agent_state import infer_note_agent_state


class NoteAgentStateTestCase(unittest.TestCase):
    def test_infer_dump_mode_for_short_mobile_capture(self) -> None:
        state = infer_note_agent_state(
            {
                "surface": "mobile_capture",
                "raw_text": "Need to remember to call Jonas.",
                "caller_hints": {},
            },
            [],
        )

        self.assertEqual(state["user_state"]["mode"], "dump")
        self.assertEqual(state["retrieval_policy"]["retrieval_mode"], "session_only")
        self.assertEqual(state["response_mode"]["mode"], "silent_ack")

    def test_infer_reflective_mode_widens_retrieval_for_note_chat(self) -> None:
        state = infer_note_agent_state(
            {
                "surface": "thought_chat",
                "raw_text": "I think this note keeps circling the same identity tension. What does that suggest?",
                "caller_hints": {"thought_id": "thought-001"},
            },
            [{"actor": "user", "content": "I keep coming back to the same pattern."}],
        )

        self.assertEqual(state["user_state"]["mode"], "reflective")
        self.assertEqual(state["retrieval_policy"]["retrieval_mode"], "session_plus_ocean")
        self.assertEqual(state["response_mode"]["mode"], "resonance")


if __name__ == "__main__":
    unittest.main()
