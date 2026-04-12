import os
import unittest
from unittest.mock import MagicMock, patch

from app.core.react_turn_manager import ReActTurnManager
from app.models.message import Message
from app.models.vocabulary import MessageRole


class TestReActSyntheticTools(unittest.TestCase):
    def setUp(self):
        self.orchestrator = MagicMock()
        self.orchestrator.logger = MagicMock()
        self.orchestrator.llm_connector = MagicMock()
        self.orchestrator.tool_registry = MagicMock()
        self.orchestrator.vector_store = MagicMock()
        self.orchestrator.ui_queue = MagicMock()

        self.manager = ReActTurnManager(self.orchestrator)
        self.turn_id = "test_turn_123"

    def test_get_history_no_synthetic_messages(self):
        working_history = [Message(role=MessageRole.USER, content="Hello", turn_id=self.turn_id)]
        synthetic_tool_messages: dict[str, Message] = {}

        res = self.manager._get_request_history_with_synthetic_tools(
            working_history, synthetic_tool_messages, self.turn_id
        )

        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].content, "Hello")

    @patch.dict(os.environ, {"SYNTHETIC_TOOLS_COMPAT_MODE": "false"})
    def test_get_history_strict_mode(self):
        working_history = [Message(role=MessageRole.USER, content="Hello", turn_id=self.turn_id)]
        synthetic_tool_messages = {
            "tool1": Message(role=MessageRole.TOOL, tool_call_id="id1", name="tool1", content="result1", turn_id=self.turn_id)
        }

        res = self.manager._get_request_history_with_synthetic_tools(
            working_history, synthetic_tool_messages, self.turn_id
        )

        # Strict mode adds 2 messages: Assistant tool_calls + Tool results
        self.assertEqual(len(res), 3)
        self.assertEqual(res[1].role, MessageRole.ASSISTANT)
        self.assertEqual(res[2].role, MessageRole.TOOL)
        # Verify assistant message contains guidance
        self.assertIn("I will search the codex", res[1].content or "")
        self.assertIn("proactively use the provided tools", res[1].content or "")

    @patch.dict(os.environ, {"SYNTHETIC_TOOLS_COMPAT_MODE": "true"})
    def test_get_history_compat_mode(self):
        working_history = [
            Message(role=MessageRole.USER, content="Original User Message", turn_id=self.turn_id)
        ]
        synthetic_tool_messages = {
            "passive_rag_context": Message(role=MessageRole.TOOL, tool_call_id="id1", name="tool1", content="result1", turn_id=self.turn_id)
        }

        res = self.manager._get_request_history_with_synthetic_tools(
            working_history, synthetic_tool_messages, self.turn_id
        )

        # Compat mode merges into last USER message
        self.assertEqual(len(res), 1)
        self.assertIn("### RELEVANT CONTEXT (RAG)", res[0].content or "")
        # Verify RAG section contains guidance
        self.assertIn("This is a sample of information from the codex", res[0].content or "")

    @patch.dict(os.environ, {"SYNTHETIC_TOOLS_COMPAT_MODE": "true"})
    def test_get_history_compat_mode_no_user_message(self):
        working_history = [
            Message(role=MessageRole.SYSTEM, content="System Prompt", turn_id=self.turn_id)
        ]
        synthetic_tool_messages = {
            "available_tools": Message(role=MessageRole.TOOL, tool_call_id="id1", name="tool1", content="result1", turn_id=self.turn_id)
        }

        res = self.manager._get_request_history_with_synthetic_tools(
            working_history, synthetic_tool_messages, self.turn_id
        )

        self.assertEqual(len(res), 2)
        self.assertIn("### AVAILABLE TOOLS", res[0].content or "")
        # Verify tools section contains guidance
        self.assertIn("These are the available tools", res[0].content or "")


if __name__ == "__main__":
    unittest.main()
