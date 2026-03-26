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


class TestConversationEngine:
    @pytest.mark.asyncio
    async def test_process_transcript_returns_response(self, engine: ConversationEngine) -> None:
        result = await engine.process_transcript("Hello everyone")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_reset_clears_history(self, engine: ConversationEngine) -> None:
        await engine.process_transcript("Hello")
        assert len(engine.history) > 1
        engine.reset()
        assert len(engine.history) == 1
        assert isinstance(engine.history[0], SystemMessage)

    def test_system_prompt_includes_bot_name(self, engine: ConversationEngine) -> None:
        system_msg = engine.history[0]
        assert "AI Assistant" in str(system_msg.content)

    @pytest.mark.asyncio
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

    @pytest.mark.asyncio
    async def test_llm_ainvoke_is_called(
        self, engine: ConversationEngine, mock_llm: AsyncMock
    ) -> None:
        await engine.process_transcript("Hello")
        mock_llm.ainvoke.assert_called_once()
        # After processing, history should be: system + human + AI
        assert len(engine.history) == 3
        assert engine.history[1].content == "Hello"


class TestConversationStage:
    @pytest.mark.asyncio
    async def test_reads_from_queue_and_writes_response(self, mock_settings: MagicMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.return_value = MagicMock(content="Got it.")

        in_queue: asyncio.Queue[Transcript] = asyncio.Queue()
        out_queue: asyncio.Queue[str] = asyncio.Queue()

        in_queue.put_nowait(Transcript(text="Hello", speaker="user1"))

        with patch("call_operator.llm.conversation.get_llm", return_value=mock_llm):
            task = asyncio.create_task(conversation_stage(in_queue, out_queue, mock_settings))
            result = await asyncio.wait_for(out_queue.get(), timeout=2.0)
            task.cancel()

        assert result == "Got it."

    @pytest.mark.asyncio
    async def test_stage_continues_on_error(self, mock_settings: MagicMock) -> None:
        mock_llm = AsyncMock()
        mock_llm.ainvoke.side_effect = [RuntimeError("LLM error"), MagicMock(content="OK")]

        in_queue: asyncio.Queue[Transcript] = asyncio.Queue()
        out_queue: asyncio.Queue[str] = asyncio.Queue()

        in_queue.put_nowait(Transcript(text="First", speaker="user1"))
        in_queue.put_nowait(Transcript(text="Second", speaker="user1"))

        with patch("call_operator.llm.conversation.get_llm", return_value=mock_llm):
            task = asyncio.create_task(conversation_stage(in_queue, out_queue, mock_settings))
            result = await asyncio.wait_for(out_queue.get(), timeout=2.0)
            task.cancel()

        assert result == "OK"
