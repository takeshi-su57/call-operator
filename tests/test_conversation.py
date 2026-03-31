"""Tests for ConversationEngine and conversation_stage."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from call_operator.llm.conversation import ConversationEngine, conversation_stage
from call_operator.stt.base import Transcript


@pytest.fixture
def mock_llm() -> AsyncMock:
    """A mocked LangChain chat model."""
    llm = AsyncMock()
    llm.ainvoke.return_value = MagicMock(content="I understand, let me help with that.")
    return llm


@pytest.fixture
def engine(mock_settings: MagicMock, mock_llm: AsyncMock) -> ConversationEngine:
    """A ConversationEngine with a mocked LLM."""
    with patch("call_operator.llm.conversation.get_llm", return_value=mock_llm):
        return ConversationEngine(mock_settings)


# ------------------------------------------------------------------
# ConversationEngine tests
# ------------------------------------------------------------------


class TestConversationEngine:
    async def test_process_transcript_returns_response(self, engine: ConversationEngine) -> None:
        result = await engine.process_transcript("Hello everyone")
        assert isinstance(result, str)
        assert len(result) > 0

    async def test_history_accumulates_messages(self, engine: ConversationEngine) -> None:
        await engine.process_transcript("First message")
        await engine.process_transcript("Second message")
        # System + Human + AI + Human + AI = 5
        assert len(engine.history) == 5
        assert isinstance(engine.history[0], SystemMessage)
        assert isinstance(engine.history[1], HumanMessage)
        assert isinstance(engine.history[2], AIMessage)
        assert isinstance(engine.history[3], HumanMessage)
        assert isinstance(engine.history[4], AIMessage)

    async def test_reset_clears_history(self, engine: ConversationEngine) -> None:
        await engine.process_transcript("Hello")
        assert len(engine.history) > 1
        engine.reset()
        assert len(engine.history) == 1
        assert isinstance(engine.history[0], SystemMessage)

    def test_system_prompt_includes_bot_name(self, engine: ConversationEngine) -> None:
        system_msg = engine.history[0]
        assert "AI Assistant" in str(system_msg.content)

    async def test_history_truncation(self, mock_llm: AsyncMock) -> None:
        with (
            patch.dict(
                "os.environ",
                {
                    "LLM_PROVIDER": "openai",
                    "OPENAI_API_KEY": "test-key",
                    "LLM_MAX_HISTORY_MESSAGES": "4",
                },
            ),
            patch("call_operator.llm.conversation.get_llm", return_value=mock_llm),
        ):
            from call_operator.config import Settings

            settings = Settings()
            eng = ConversationEngine(settings)

            # Send 5 exchanges (10 messages) — should truncate to system + 4
            for i in range(5):
                await eng.process_transcript(f"Message {i}")

            assert len(eng.history) == 5  # system + 4 recent messages
            assert isinstance(eng.history[0], SystemMessage)

    async def test_llm_ainvoke_is_called(
        self, engine: ConversationEngine, mock_llm: AsyncMock
    ) -> None:
        await engine.process_transcript("Hello")
        mock_llm.ainvoke.assert_called_once()
        # After processing, history should be: system + human + AI
        assert len(engine.history) == 3
        assert engine.history[1].content == "Hello"

    async def test_get_history(self, engine: ConversationEngine) -> None:
        await engine.process_transcript("Hello")
        history = engine.get_history()
        assert isinstance(history, list)
        assert history[0]["role"] == "system"
        assert history[1]["role"] == "human"
        assert history[1]["content"] == "Hello"
        assert history[2]["role"] == "assistant"

    async def test_summarization_triggers_on_token_limit(self, mock_llm: AsyncMock) -> None:
        mock_llm.ainvoke.side_effect = [
            MagicMock(content="Response 1"),
            MagicMock(content="Response 2"),
            MagicMock(content="Response 3"),
            MagicMock(content="Summary of the conversation."),  # summarization call
            MagicMock(content="Response 4"),
        ]

        with (
            patch.dict(
                "os.environ",
                {
                    "LLM_PROVIDER": "openai",
                    "OPENAI_API_KEY": "test-key",
                    "LLM_MAX_CONTEXT_TOKENS": "50",
                },
            ),
            patch("call_operator.llm.conversation.get_llm", return_value=mock_llm),
        ):
            from call_operator.config import Settings

            settings = Settings()
            eng = ConversationEngine(settings)

        await eng.process_transcript("A" * 100)
        await eng.process_transcript("B" * 100)
        await eng.process_transcript("C" * 100)

        history = eng.get_history()
        summary_found = any(
            "Summary" in msg["content"] for msg in history if msg["role"] == "system"
        )
        assert summary_found


# ------------------------------------------------------------------
# conversation_stage tests
# ------------------------------------------------------------------


class TestConversationStage:
    async def test_reads_from_queue_and_writes_response(self, mock_settings: MagicMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="Got it.")

        in_queue: asyncio.Queue[Transcript | None] = asyncio.Queue()
        out_queue: asyncio.Queue[str | None] = asyncio.Queue()

        in_queue.put_nowait(Transcript(text="Hello", speaker="user1"))
        in_queue.put_nowait(None)

        with patch("call_operator.llm.conversation.get_llm", return_value=mock_llm):
            await conversation_stage(in_queue, out_queue, mock_settings)

        result = out_queue.get_nowait()
        assert result == "Got it."
        assert out_queue.get_nowait() is None

    async def test_stage_continues_on_error(self, mock_settings: MagicMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = [
            RuntimeError("LLM error"),
            MagicMock(content="OK"),
        ]

        in_queue: asyncio.Queue[Transcript | None] = asyncio.Queue()
        out_queue: asyncio.Queue[str | None] = asyncio.Queue()

        in_queue.put_nowait(Transcript(text="First", speaker="user1"))
        in_queue.put_nowait(Transcript(text="Second", speaker="user1"))
        in_queue.put_nowait(None)

        with patch("call_operator.llm.conversation.get_llm", return_value=mock_llm):
            await conversation_stage(in_queue, out_queue, mock_settings)

        result = out_queue.get_nowait()
        assert result == "OK"
        assert out_queue.get_nowait() is None

    async def test_sentinel_propagation(self, mock_settings: MagicMock) -> None:
        in_queue: asyncio.Queue[Transcript | None] = asyncio.Queue()
        out_queue: asyncio.Queue[str | None] = asyncio.Queue()

        in_queue.put_nowait(None)

        with patch("call_operator.llm.conversation.get_llm", return_value=AsyncMock()):
            await conversation_stage(in_queue, out_queue, mock_settings)

        assert out_queue.get_nowait() is None

    async def test_skips_non_final_transcripts(self, mock_settings: MagicMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="Response")

        in_queue: asyncio.Queue[Transcript | None] = asyncio.Queue()
        out_queue: asyncio.Queue[str | None] = asyncio.Queue()

        in_queue.put_nowait(Transcript(text="interim", is_final=False))
        in_queue.put_nowait(Transcript(text="final text", is_final=True))
        in_queue.put_nowait(None)

        with patch("call_operator.llm.conversation.get_llm", return_value=mock_llm):
            await conversation_stage(in_queue, out_queue, mock_settings)

        result = out_queue.get_nowait()
        assert result == "Response"
        mock_llm.ainvoke.assert_called_once()

    async def test_skips_empty_transcripts(self, mock_settings: MagicMock) -> None:
        mock_llm = AsyncMock()

        in_queue: asyncio.Queue[Transcript | None] = asyncio.Queue()
        out_queue: asyncio.Queue[str | None] = asyncio.Queue()

        in_queue.put_nowait(Transcript(text="   ", is_final=True))
        in_queue.put_nowait(Transcript(text="", is_final=True))
        in_queue.put_nowait(None)

        with patch("call_operator.llm.conversation.get_llm", return_value=mock_llm):
            await conversation_stage(in_queue, out_queue, mock_settings)

        mock_llm.ainvoke.assert_not_called()
        assert out_queue.get_nowait() is None

    async def test_debounce_combines_transcripts(self) -> None:
        captured_messages: list[list[object]] = []

        async def capture_ainvoke(messages: list[object]) -> MagicMock:
            # Snapshot the messages at call time (list is mutable)
            captured_messages.append(list(messages))
            return MagicMock(content="Combined response")

        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = capture_ainvoke

        with patch.dict(
            "os.environ",
            {
                "LLM_PROVIDER": "openai",
                "OPENAI_API_KEY": "test-key",
                "CONVERSATION_DEBOUNCE_MS": "200",
            },
        ):
            from call_operator.config import Settings

            settings = Settings()

        in_queue: asyncio.Queue[Transcript | None] = asyncio.Queue()
        out_queue: asyncio.Queue[str | None] = asyncio.Queue()

        # Both transcripts in queue before stage reads — will be combined
        in_queue.put_nowait(Transcript(text="Hello", is_final=True))
        in_queue.put_nowait(Transcript(text="everyone", is_final=True))
        in_queue.put_nowait(None)

        with patch("call_operator.llm.conversation.get_llm", return_value=mock_llm):
            await conversation_stage(in_queue, out_queue, settings)

        # LLM called once with combined text
        assert len(captured_messages) == 1
        messages = captured_messages[0]
        human_msg = str(messages[-1].content)
        assert human_msg == "Hello everyone"

        result = out_queue.get_nowait()
        assert result == "Combined response"
        assert out_queue.get_nowait() is None
