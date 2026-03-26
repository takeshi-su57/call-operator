"""Conversation engine — manages LLM interaction with conversation history."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from call_operator.llm.provider import get_llm
from call_operator.prompts.conversation import SYSTEM_PROMPT

if TYPE_CHECKING:
    import asyncio

    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage

    from call_operator.config import Settings
    from call_operator.stt.base import Transcript

logger = logging.getLogger(__name__)


class ConversationEngine:
    """Stateful conversation engine that manages history and generates responses."""

    def __init__(self, settings: Settings) -> None:
        self._llm: BaseChatModel = get_llm(settings)
        self._max_history: int = settings.llm_max_history_messages
        system_content = SYSTEM_PROMPT.format(
            bot_name=settings.bot_name,
            context="",
        )
        self._system_message = SystemMessage(content=system_content)
        self._history: list[BaseMessage] = [self._system_message]

    @property
    def history(self) -> list[BaseMessage]:
        """Return the current conversation history (read-only view)."""
        return list(self._history)

    async def process_transcript(self, text: str) -> str:
        """Add a user message, invoke the LLM, and return the response text."""
        self._history.append(HumanMessage(content=text))

        response = await self._llm.ainvoke(self._history)
        response_text = str(response.content)

        self._history.append(AIMessage(content=response_text))
        self._truncate_history()

        return response_text

    def reset(self) -> None:
        """Clear conversation history back to system prompt only."""
        self._history = [self._system_message]

    def _truncate_history(self) -> None:
        """Keep system message + last N messages within the configured limit."""
        # +1 accounts for the system message at index 0
        max_len = self._max_history + 1
        if len(self._history) > max_len:
            self._history = [self._system_message] + self._history[-self._max_history :]


async def conversation_stage(
    in_queue: asyncio.Queue[Transcript],
    out_queue: asyncio.Queue[str],
    settings: Settings,
) -> None:
    """Pipeline stage: process transcripts via LLM and generate responses.

    Reads transcribed text from in_queue, maintains conversation history,
    generates a response via the configured LLM, and pushes the response
    text to out_queue for TTS.
    """
    engine = ConversationEngine(settings)

    while True:
        transcript = await in_queue.get()
        try:
            logger.debug("Processing transcript: %s", transcript.text[:80])
            response = await engine.process_transcript(transcript.text)
            await out_queue.put(response)
            logger.debug("Generated response: %s", response[:80])
        except Exception:
            logger.exception("Error in conversation stage")
        finally:
            in_queue.task_done()
