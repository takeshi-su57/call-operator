"""Conversation engine — manages LLM interaction with conversation history."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncio

    from call_operator.config import Settings
    from call_operator.stt.base import Transcript

logger = logging.getLogger(__name__)


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
    # TODO: Initialize LLM via get_llm(settings)
    # TODO: Load system prompt from prompts/conversation.py
    # TODO: Maintain conversation history (list of messages)
    # TODO: Read Transcript from in_queue
    # TODO: Add user message to history
    # TODO: Generate LLM response (async)
    # TODO: Add assistant message to history
    # TODO: Push response text to out_queue
    # TODO: Manage context window (truncate old messages)
    logger.warning("conversation_stage() is not yet implemented.")
