"""Conversation engine — manages LLM interaction with conversation history."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from typing import TYPE_CHECKING

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from call_operator.llm.provider import get_llm
from call_operator.prompts.conversation import SUMMARIZE_PROMPT, SYSTEM_PROMPT

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel
    from langchain_core.messages import BaseMessage

    from call_operator.config import Settings
    from call_operator.stt.base import Transcript

logger = logging.getLogger(__name__)

_FALLBACK_RESPONSE = "I'm having trouble responding right now."


class ConversationEngine:
    """Stateful conversation engine that manages history and generates responses."""

    def __init__(self, settings: Settings) -> None:
        self._llm: BaseChatModel = get_llm(settings)
        self._model_name: str = settings.llm_model
        self._max_history: int = settings.llm_max_history_messages
        self._max_context_tokens: int = settings.llm_max_context_tokens
        self._max_retries: int = settings.retry_max_attempts
        self._retry_base_delay: float = settings.retry_base_delay
        self._retry_max_delay: float = settings.retry_max_delay
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

    def get_history(self) -> list[dict[str, str]]:
        """Return conversation history as a list of dicts for debugging."""
        result: list[dict[str, str]] = []
        for msg in self._history:
            if isinstance(msg, SystemMessage):
                role = "system"
            elif isinstance(msg, HumanMessage):
                role = "human"
            elif isinstance(msg, AIMessage):
                role = "assistant"
            else:
                role = "unknown"
            result.append({"role": role, "content": str(msg.content)})
        return result

    async def process_transcript(self, text: str) -> str:
        """Add a user message, invoke the LLM, and return the response text."""
        self._history.append(HumanMessage(content=text))

        logger.debug("LLM call: history=%d messages, input=%s", len(self._history), text[:80])

        start = time.perf_counter()
        response = None
        last_exc: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = await self._llm.ainvoke(self._history)
                break
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self._max_retries - 1:
                    delay = min(self._retry_base_delay * (2**attempt), self._retry_max_delay)
                    delay *= random.uniform(0.5, 1.5)  # noqa: S311
                    logger.warning(
                        "LLM call failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        self._max_retries,
                        delay,
                        exc,
                    )
                    await asyncio.sleep(delay)

        if response is None:
            logger.error("LLM call failed after %d attempts: %s", self._max_retries, last_exc)
            self._history.append(AIMessage(content=_FALLBACK_RESPONSE))
            return _FALLBACK_RESPONSE

        latency_ms = (time.perf_counter() - start) * 1000

        usage = getattr(response, "usage_metadata", None)
        if isinstance(usage, dict):
            logger.info(
                "LLM response: %.0fms, tokens=%d/%d/%d (in/out/total), model=%s",
                latency_ms,
                usage.get("input_tokens", 0),
                usage.get("output_tokens", 0),
                usage.get("total_tokens", 0),
                self._model_name,
            )
        else:
            logger.info("LLM response: %.0fms, model=%s", latency_ms, self._model_name)

        response_text = str(response.content)
        logger.debug("LLM output: %s", response_text[:80])

        self._history.append(AIMessage(content=response_text))
        self._truncate_history()
        await self._maybe_summarize()

        return response_text

    def reset(self) -> None:
        """Clear conversation history back to system prompt only."""
        self._history = [self._system_message]

    def _truncate_history(self) -> None:
        """Keep system message + last N messages within the configured limit."""
        max_len = self._max_history + 1
        if len(self._history) > max_len:
            self._history = [self._system_message] + self._history[-self._max_history :]

    def _estimate_tokens(self) -> int:
        """Approximate token count of all messages via character count / 4."""
        return sum(len(str(msg.content)) for msg in self._history) // 4

    async def _maybe_summarize(self) -> None:
        """If history exceeds token limit, summarize older messages."""
        try:
            if self._estimate_tokens() <= self._max_context_tokens:
                return

            non_system = self._history[1:]
            if len(non_system) <= 4:
                return

            split = len(non_system) // 2
            older = non_system[:split]
            newer = non_system[split:]

            lines: list[str] = []
            for msg in older:
                role = "Assistant" if isinstance(msg, AIMessage) else "Participant"
                lines.append(f"{role}: {msg.content}")
            conversation_text = "\n".join(lines)

            logger.debug(
                "Summarizing %d older messages (%d chars)", len(older), len(conversation_text)
            )

            prompt = SUMMARIZE_PROMPT.format(conversation_history=conversation_text)

            start = time.perf_counter()
            summary_response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            latency_ms = (time.perf_counter() - start) * 1000
            logger.info("Summarization: %.0fms, model=%s", latency_ms, self._model_name)

            summary_text = str(summary_response.content)
            summary_msg = SystemMessage(content=f"Summary of earlier conversation:\n{summary_text}")

            self._history = [self._system_message, summary_msg, *newer]
        except Exception:  # noqa: BLE001
            logger.warning("Summarization failed, skipping", exc_info=True)


async def conversation_stage(
    in_queue: asyncio.Queue[Transcript | None],
    out_queue: asyncio.Queue[str | None],
    settings: Settings,
) -> None:
    """Pipeline stage: process transcripts via LLM and generate responses.

    Reads transcribed text from *in_queue*, maintains conversation history,
    generates a response via the configured LLM, and pushes the response
    text to *out_queue* for TTS.
    """
    logger.info("conversation_stage started (model=%s)", settings.llm_model)
    engine = ConversationEngine(settings)
    transcripts_processed = 0
    debounce_s = settings.conversation_debounce_ms / 1000.0

    try:
        while True:
            transcript = await in_queue.get()

            if transcript is None:
                break

            if not transcript.is_final:
                continue

            text = transcript.text.strip()
            if not text:
                continue

            # Debounce: collect additional transcripts within the window
            combined = text
            sentinel_received = False
            while debounce_s > 0:
                try:
                    next_item = await asyncio.wait_for(in_queue.get(), timeout=debounce_s)
                except TimeoutError:
                    break

                if next_item is None:
                    sentinel_received = True
                    break

                if not next_item.is_final:
                    continue
                next_text = next_item.text.strip()
                if next_text:
                    combined = f"{combined} {next_text}"

            # Process the (possibly combined) transcript
            try:
                logger.debug("Processing transcript: %s", combined[:80])
                response = await engine.process_transcript(combined)
                transcripts_processed += 1
                await out_queue.put(response)
                logger.debug("Generated response: %s", response[:80])
            except Exception:  # noqa: BLE001
                logger.exception("conversation_stage: LLM call failed, skipping")

            if sentinel_received:
                break
    finally:
        await out_queue.put(None)
        logger.info(
            "conversation_stage finished — %d transcripts processed",
            transcripts_processed,
        )
