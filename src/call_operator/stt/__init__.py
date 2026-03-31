"""Speech-to-Text providers and pipeline stage."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from call_operator.stt.base import STTProvider, Transcript

if TYPE_CHECKING:
    import asyncio

    from call_operator.adapters.base import AudioChunk

logger = logging.getLogger(__name__)

__all__ = ["STTProvider", "Transcript", "stt_stage"]


async def stt_stage(
    in_queue: asyncio.Queue[AudioChunk | None],
    out_queue: asyncio.Queue[Transcript | None],
    provider: STTProvider,
) -> None:
    """Pipeline stage: convert speech audio chunks into transcripts.

    Reads :class:`AudioChunk` objects from *in_queue*, passes each to
    *provider.transcribe()*, and forwards non-``None`` results to
    *out_queue*.  At end-of-stream (``None`` sentinel) the provider is
    flushed so any remaining buffered audio is transcribed.
    """
    logger.info("stt_stage started")
    await provider.start()

    chunks_processed = 0
    transcripts_produced = 0

    try:
        while True:
            chunk = await in_queue.get()

            # Sentinel — flush and exit
            if chunk is None:
                break

            chunks_processed += 1
            try:
                transcript = await provider.transcribe(chunk)
            except Exception:  # noqa: BLE001
                logger.exception("stt_stage: transcription failed, skipping chunk")
                continue
            if transcript is not None:
                transcripts_produced += 1
                await out_queue.put(transcript)

        # Flush remaining buffered audio
        final = await provider.flush()
        if final is not None:
            transcripts_produced += 1
            await out_queue.put(final)
    finally:
        await provider.stop()
        await out_queue.put(None)
        logger.info(
            "stt_stage finished — %d chunks, %d transcripts",
            chunks_processed,
            transcripts_produced,
        )
