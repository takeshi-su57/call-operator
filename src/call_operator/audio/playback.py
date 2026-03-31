"""Audio playback — sends synthesized speech back into the meeting."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from call_operator.adapters.base import AudioChunk, MeetingAdapter

logger = logging.getLogger(__name__)


async def playback_stage(
    in_queue: asyncio.Queue[AudioChunk | None],
    adapter: MeetingAdapter,
) -> None:
    """Pipeline stage: play audio chunks back into the meeting.

    Reads synthesized speech :class:`AudioChunk` objects from *in_queue*
    and sends each to the meeting adapter for playback.  At end-of-stream
    (``None`` sentinel) the stage exits.
    """
    logger.info("playback_stage started")
    chunks_played = 0

    try:
        while True:
            chunk = await in_queue.get()

            if chunk is None:
                break

            try:
                await adapter.play_audio(chunk)
                chunks_played += 1
                logger.debug(
                    "Played chunk: %d bytes, %.1f ms",
                    len(chunk.data),
                    chunk.duration_ms,
                )
                # Pace playback to match audio duration (prevent sending faster than real-time)
                if chunk.duration_ms > 0:
                    await asyncio.sleep(chunk.duration_ms / 1000.0)
            except Exception:  # noqa: BLE001
                logger.exception("playback_stage: failed to play chunk, skipping")
    finally:
        logger.info("playback_stage finished — %d chunks played", chunks_played)
